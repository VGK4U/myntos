"""
MyntOS Recharge Scratch Card & Rewards Suite (Tasks 1-6 Audit & Verification)
Verifies:
1. Eligibility rules (Payment Paid + API Success)
2. Budget limits (₹500 max per 100 cards) & <10% ₹10 limit
3. Token security & hiding un-scratched amount in GET /info
4. Atomic claim execution, wallet balance credit & single-claim idempotency
5. Notification Outbox batch processor, retries & terminal failure marking
6. Admin endpoint RBAC authorization enforcement
7. Canonical domain resolution & injection protection
"""

import sys
import os
import unittest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Compatibility patch for Starlette 0.36 + HTTPX 0.28 TestClient
try:
    import httpx
    _orig_httpx_init = httpx.Client.__init__
    def _patched_httpx_init(self, *args, **kwargs):
        kwargs.pop("app", None)
        return _orig_httpx_init(self, *args, **kwargs)
    httpx.Client.__init__ = _patched_httpx_init
except Exception:
    pass

from app.models.base import Base, get_indian_time
from app.models.recharge import RechargeTransaction
from app.models.reward_scratch import RewardCampaign, ScratchCard, RewardLedger, NotificationOutbox
from app.models.user import User
from app.services.scratch_reward_service import allocate_scratch_card, get_or_create_active_campaign
from app.services.notification_outbox_service import (
    enqueue_recharge_scratch_notification,
    build_recharge_scratch_message,
    process_pending_outbox_batch,
    resolve_canonical_origin
)
from app.api.v1.endpoints.scratch_card_api import (
    get_scratch_card_info,
    claim_scratch_card,
    ClaimScratchCardRequest,
    enforce_staff_admin_access
)


class MockStaffUser:
    def __init__(self, emp_code="MR10001", dept_name="Admin"):
        self.emp_code = emp_code
        self.department = type("Department", (), {"name": dept_name})()


class TestScratchRewardSystem(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        
        target_tables = [
            RechargeTransaction.__table__,
            RewardCampaign.__table__,
            ScratchCard.__table__,
            RewardLedger.__table__,
            NotificationOutbox.__table__,
            User.__table__
        ]
        Base.metadata.create_all(bind=self.engine, tables=target_tables)
        self.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.TestingSessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_qualifying_recharge_allocates_single_card(self):
        tx = RechargeTransaction(
            mobile_number="9876543210",
            operator="Jio",
            amount=299.0,
            payment_status="Paid",
            api_status="Success"
        )
        self.db.add(tx)
        self.db.commit()
        self.db.refresh(tx)

        card, raw_token, is_new = allocate_scratch_card(self.db, tx, brand="Zynova Mobility")
        self.assertIsNotNone(card)
        self.assertIsNotNone(raw_token)
        self.assertTrue(is_new)
        self.assertEqual(card.status, "ISSUED")
        self.assertGreaterEqual(card.allocated_amount_paise, 100)

        # Duplicate callback test
        card2, token2, is_new2 = allocate_scratch_card(self.db, tx, brand="Zynova Mobility")
        self.assertEqual(card2.id, card.id)
        self.assertFalse(is_new2)

    def test_ineligible_recharges_do_not_get_card(self):
        tx_pending = RechargeTransaction(
            mobile_number="9876543211",
            operator="Airtel",
            amount=199.0,
            payment_status="Pending",
            api_status="Pending"
        )
        self.db.add(tx_pending)
        
        tx_failed = RechargeTransaction(
            mobile_number="9876543212",
            operator="VI",
            amount=299.0,
            payment_status="Paid",
            api_status="Failed"
        )
        self.db.add(tx_failed)
        self.db.commit()

        card1, _, _ = allocate_scratch_card(self.db, tx_pending)
        card2, _, _ = allocate_scratch_card(self.db, tx_failed)

        self.assertIsNone(card1)
        self.assertIsNone(card2)

    def test_budget_and_ten_rupee_distribution_rules(self):
        campaign = RewardCampaign(
            campaign_name="Test Campaign 100 Cards",
            is_active=True,
            total_budget_paise=50000,
            max_cards=100,
            max_ten_rupee_count=9,
            min_reward_paise=100,
            max_standard_reward_paise=500
        )
        self.db.add(campaign)
        self.db.commit()

        ten_count = 0
        total_allocated = 0

        for i in range(100):
            tx = RechargeTransaction(
                mobile_number=f"9000000{i:03d}",
                operator="Jio",
                amount=199.0,
                payment_status="Paid",
                api_status="Success"
            )
            self.db.add(tx)
            self.db.commit()
            self.db.refresh(tx)

            card, _, is_new = allocate_scratch_card(self.db, tx)
            self.assertIsNotNone(card)
            self.assertTrue(is_new)
            self.assertGreaterEqual(card.allocated_amount_paise, 100)

            total_allocated += card.allocated_amount_paise
            if card.allocated_amount_paise == 1000:
                ten_count += 1

        self.assertLessEqual(ten_count, 9)
        self.assertLessEqual(total_allocated, 50000)

    def test_scratch_info_hides_unscratched_amount(self):
        tx = RechargeTransaction(
            mobile_number="9876543210",
            operator="Jio",
            amount=299.0,
            payment_status="Paid",
            api_status="Success"
        )
        self.db.add(tx)
        self.db.commit()

        card, raw_token, _ = allocate_scratch_card(self.db, tx, brand="Zynova Mobility")
        
        info = get_scratch_card_info(token=raw_token, db=self.db)
        self.assertTrue(info["valid"])
        self.assertEqual(info["status"], "ISSUED")
        self.assertNotIn("revealed_amount_rupees", info) # Secret reward amount hidden prior to scratching

    def test_claim_scratch_card_atomic_credit_and_idempotency(self):
        # Create registered user
        user = User(
            id="MNR99991111",
            name="Test Customer",
            phone_number="9876543210",
            wallet_balance=50.0,
            password="dummy_hash",
            user_type="Member",
            account_status="Active",
            registration_date=get_indian_time()
        )
        self.db.add(user)

        tx = RechargeTransaction(
            mobile_number="9876543210",
            operator="Jio",
            amount=299.0,
            payment_status="Paid",
            api_status="Success"
        )
        self.db.add(tx)
        self.db.commit()

        card, raw_token, _ = allocate_scratch_card(self.db, tx, brand="Zynova Mobility")
        reward_rs = card.allocated_amount_paise / 100.0

        # Claim card first time
        claim_req = ClaimScratchCardRequest(token=raw_token)
        res1 = claim_scratch_card(req=claim_req, db=self.db)
        self.assertEqual(res1["status"], "success")
        self.assertEqual(res1["amount_rupees"], reward_rs)

        # Verify wallet credit
        self.db.refresh(user)
        self.assertEqual(user.wallet_balance, 50.0 + reward_rs)

        # Verify ledger entry created
        ledger = self.db.query(RewardLedger).filter(RewardLedger.scratch_card_id == card.id).first()
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger.amount_paise, card.allocated_amount_paise)

        # Repeat claim call (Idempotency test)
        res2 = claim_scratch_card(req=claim_req, db=self.db)
        self.assertEqual(res2["status"], "already_claimed")
        self.db.refresh(user)
        self.assertEqual(user.wallet_balance, 50.0 + reward_rs) # Balance NOT double-credited

    @patch("app.services.notification_outbox_service.send_direct_whatsapp")
    def test_outbox_batch_processor_retries_and_terminal_failure(self, mock_send_wa):
        # 1. Transient failure
        mock_send_wa.return_value = {"status": "failed", "message": "Network timeout"}

        outbox = enqueue_recharge_scratch_notification(
            db=self.db,
            brand="Zynova Mobility",
            mobile_number="9876543210",
            recharge_amount=299.0,
            transaction_id=101,
            raw_secret_token="TEST_SECRET_TOKEN_XYZ"
        )
        self.assertEqual(outbox.status, "FAILED")
        self.assertEqual(outbox.retry_count, 1)

        # Batch retry 1 (retry_count -> 2)
        stats1 = process_pending_outbox_batch(db=self.db, max_retries=3)
        self.assertEqual(stats1["processed"], 1)
        self.db.refresh(outbox)
        self.assertEqual(outbox.status, "FAILED")
        self.assertEqual(outbox.retry_count, 2)

        # Batch retry 2 (retry_count -> 3 -> PERMANENTLY_FAILED)
        stats2 = process_pending_outbox_batch(db=self.db, max_retries=3)
        self.assertEqual(stats2["processed"], 1)
        self.db.refresh(outbox)
        self.assertEqual(outbox.status, "PERMANENTLY_FAILED")

    def test_admin_endpoint_authorization_guards(self):
        # Anonymous / None user
        with self.assertRaises(HTTPException) as ctx1:
            enforce_staff_admin_access(None)
        self.assertEqual(ctx1.exception.status_code, 401)

        # Unauthorized user (e.g. Sales staff)
        unauth_user = MockStaffUser(emp_code="MR99999", dept_name="Sales")
        with self.assertRaises(HTTPException) as ctx2:
            enforce_staff_admin_access(unauth_user)
        self.assertEqual(ctx2.exception.status_code, 403)

        # Authorized staff (Admin)
        auth_user = MockStaffUser(emp_code="MR10001", dept_name="Admin")
        try:
            enforce_staff_admin_access(auth_user)
        except HTTPException:
            self.fail("enforce_staff_admin_access raised HTTPException unexpectedly for authorized staff.")

    def test_canonical_domain_resolution_prevents_injection(self):
        # Untrusted injection origin -> falls back to trusted canonical origin
        res1 = resolve_canonical_origin(brand="Myntreal", origin_url="https://attacker-domain.com")
        self.assertEqual(res1, "https://www.myntreal.com")

        # Trusted allowlisted origin -> preserved
        res2 = resolve_canonical_origin(brand="MyntReal", origin_url="https://myntreal.com")
        self.assertEqual(res2, "https://myntreal.com")

    def test_scheduler_outbox_job_registered(self):
        """Fix 1 Verification: Test that recharge_scratch_outbox_worker is registered in scheduler."""
        import inspect
        from app.core import scheduler
        source = inspect.getsource(scheduler.init_scheduler)
        self.assertIn("recharge_scratch_outbox_worker", source)
        self.assertIn("process_pending_outbox_batch", source)

    def test_scratch_card_root_route_serves_html(self):
        """Fix 2 Verification: Test that /scratch-card.html and /scratch-card exist and serve HTML."""
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # Request with ?token=xyz
        response = client.get("/scratch-card.html?token=test_token_abc123")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("Myntreal", response.text)
        self.assertIn("scratchCanvas", response.text)

        # Extensionless route
        response_extless = client.get("/scratch-card?token=test_token_abc123")
        self.assertEqual(response_extless.status_code, 200)
        self.assertIn("Myntreal", response_extless.text)

    def test_claim_scratch_card_with_customer_details_and_ack_outbox(self):
        """Verify 2-step claim with Name, PIN, City, State and WhatsApp ack outbox creation."""
        tx = RechargeTransaction(
            mobile_number="9876543299",
            operator="Airtel",
            amount=399.0,
            payment_status="Paid",
            api_status="Success",
            guest_name="Initial Guest"
        )
        self.db.add(tx)
        self.db.commit()

        card, raw_token, _ = allocate_scratch_card(self.db, tx, brand="Myntreal")
        self.assertIsNotNone(card)

        # Claim with full customer details
        claim_req = ClaimScratchCardRequest(
            token=raw_token,
            name="Ramesh Kumar",
            pincode="560001",
            city="Bengaluru",
            state="Karnataka"
        )
        res = claim_scratch_card(req=claim_req, db=self.db)
        self.assertEqual(res["status"], "success")

        # Verify card and transaction updated
        self.db.refresh(card)
        self.db.refresh(tx)
        self.assertEqual(card.status, "CLAIMED")
        self.assertEqual(card.customer_name, "Ramesh Kumar")
        self.assertEqual(card.pincode, "560001")
        self.assertEqual(card.city, "Bengaluru")
        self.assertEqual(card.state, "Karnataka")
        self.assertEqual(tx.guest_name, "Ramesh Kumar")

        # Verify WhatsApp claim acknowledgment outbox entry
        outbox = self.db.query(NotificationOutbox).filter(
            NotificationOutbox.event_type == "RECHARGE_SCRATCH_CLAIM_ACK",
            NotificationOutbox.destination_mobile == "9876543299"
        ).first()
        self.assertIsNotNone(outbox)
        self.assertIn("Ramesh Kumar", outbox.payload_json)
        self.assertIn("+91 85858 52738", outbox.payload_json)
        self.assertIn("Myntreal", outbox.payload_json)
        self.assertNotIn("Zynova", outbox.payload_json)


if __name__ == "__main__":
    unittest.main()
