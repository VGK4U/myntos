"""
Test Suite: Scratch Card Recharge Tiers, 50% Referral Bonus & Service Lead Creation
Verifies:
1. Tier rules: Recharges < ₹100 strictly capped at max ₹5.00 reward.
2. Recharges >= ₹100 eligible for standard rewards up to ₹25.00 jackpot.
3. Referral tracking: 50% bonus awarded to referrer upon referred claim.
4. Referral limits: Max 5 referral bonuses per referrer.
5. Service interest quick reply creates CRMLead with source='Recharge'.
6. Direct /interest endpoint creates CRMLead with source='Recharge'.
"""

import sys
import os
import unittest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.models.base import Base, get_indian_time
from app.models.recharge import RechargeTransaction
from app.models.reward_scratch import RewardCampaign, ScratchCard, RewardLedger, NotificationOutbox
from app.models.crm import CRMLead
from app.models.user import User
from app.services.scratch_reward_service import allocate_scratch_card, get_or_create_active_campaign
from app.api.v1.endpoints.scratch_card_api import (
    get_scratch_card_info,
    claim_scratch_card,
    ClaimScratchCardRequest,
    register_scratch_interest,
    ScratchInterestRequest
)
from app.api.v1.endpoints.whatsapp import handle_recharge_service_lead


class TestScratchClaimReferralFlow(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        target_tables = [
            RechargeTransaction.__table__,
            RewardCampaign.__table__,
            ScratchCard.__table__,
            RewardLedger.__table__,
            NotificationOutbox.__table__,
            CRMLead.__table__,
            User.__table__
        ]
        Base.metadata.create_all(bind=self.engine, tables=target_tables)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_recharge_below_100_strictly_max_5_rupees(self):
        """Verifies that recharges under ₹100 never exceed ₹5.00 (500 paise) payout."""
        for amt in [19.0, 49.0, 99.0]:
            for i in range(10):
                tx = RechargeTransaction(
                    mobile_number=f"980000{i:04d}",
                    operator="Jio",
                    amount=amt,
                    payment_status="Paid",
                    api_status="Success"
                )
                self.db.add(tx)
                self.db.commit()

                card, _, is_new = allocate_scratch_card(self.db, tx, brand="Myntreal")
                self.assertIsNotNone(card)
                self.assertTrue(is_new)
                self.assertLessEqual(card.allocated_amount_paise, 500, f"Reward {card.allocated_amount_paise} paise exceeds ₹5 max for ₹{amt} recharge")
                self.assertGreaterEqual(card.allocated_amount_paise, 300)

    def test_recharge_above_100_eligible_for_standard_pool(self):
        """Verifies that recharges >= ₹100 can receive rewards above ₹5 up to ₹25."""
        rewards_seen = set()
        for i in range(30):
            tx = RechargeTransaction(
                mobile_number=f"970000{i:04d}",
                operator="Airtel",
                amount=299.0,
                payment_status="Paid",
                api_status="Success"
            )
            self.db.add(tx)
            self.db.commit()

            card, _, _ = allocate_scratch_card(self.db, tx, brand="Myntreal")
            rewards_seen.add(card.allocated_amount_paise)

        # Confirm some rewards are > 500 paise (₹5.00)
        self.assertTrue(any(r > 500 for r in rewards_seen), "Expected at least some rewards > ₹5 for ₹299 recharges")

    def test_referral_50_percent_bonus_credited_to_referrer(self):
        """Verifies that referrer receives 50% of referred member's scratch reward."""
        # 1. Referrer recharge and card
        ref_user = User(
            id="REF10001",
            name="Referrer John",
            phone_number="9876500001",
            wallet_balance=100.0,
            password="dummy",
            user_type="Member",
            account_status="Active",
            registration_date=get_indian_time()
        )
        self.db.add(ref_user)

        tx_referrer = RechargeTransaction(
            mobile_number="9876500001",
            operator="Jio",
            amount=199.0,
            payment_status="Paid",
            api_status="Success",
            guest_name="Referrer John"
        )
        self.db.add(tx_referrer)
        self.db.commit()

        card_referrer, token_ref, _ = allocate_scratch_card(self.db, tx_referrer, brand="Myntreal")
        self.assertIsNotNone(card_referrer.referral_code)
        ref_code = card_referrer.referral_code

        # Claim referrer card
        claim_ref = ClaimScratchCardRequest(
            token=token_ref,
            name="Referrer John",
            pincode="560001",
            city="Bengaluru",
            state="Karnataka"
        )
        claim_scratch_card(claim_ref, db=self.db)

        # 2. Friend recharge using referrer's code
        tx_friend = RechargeTransaction(
            mobile_number="9876500002",
            operator="Airtel",
            amount=299.0,
            referred_by=ref_code,
            payment_status="Paid",
            api_status="Success",
            guest_name="Friend Alice"
        )
        self.db.add(tx_friend)
        self.db.commit()

        card_friend, token_friend, _ = allocate_scratch_card(self.db, tx_friend, brand="Myntreal")
        self.assertEqual(card_friend.referred_by_card_id, card_referrer.id)

        # Friend claims reward
        friend_reward_rs = card_friend.allocated_amount_paise / 100.0
        claim_friend = ClaimScratchCardRequest(
            token=token_friend,
            name="Friend Alice",
            pincode="560002",
            city="Bengaluru",
            state="Karnataka"
        )
        res_friend = claim_scratch_card(claim_friend, db=self.db)
        self.assertEqual(res_friend["status"], "success")

        # 3. Verify Referrer received 50% referral bonus
        self.db.refresh(card_friend)
        self.assertTrue(card_friend.referral_bonus_paid)

        expected_bonus_paise = card_friend.allocated_amount_paise // 2
        ref_ledger = self.db.query(RewardLedger).filter(
            RewardLedger.transaction_type == "SCRATCH_REFERRAL_BONUS",
            RewardLedger.mobile_number == "9876500001"
        ).first()

        self.assertIsNotNone(ref_ledger)
        self.assertEqual(ref_ledger.amount_paise, expected_bonus_paise)

        # Verify wallet balance incremented by 50%
        self.db.refresh(ref_user)
        self.assertEqual(ref_user.wallet_balance, 100.0 + (card_referrer.allocated_amount_paise / 100.0) + (expected_bonus_paise / 100.0))

        # Verify referral notification outbox queued
        outbox = self.db.query(NotificationOutbox).filter(
            NotificationOutbox.event_type == "RECHARGE_SCRATCH_REFERRAL_BONUS",
            NotificationOutbox.destination_mobile == "9876500001"
        ).first()
        self.assertIsNotNone(outbox)
        self.assertIn("50%", outbox.payload_json)

    def test_referral_maximum_5_members_limit(self):
        """Verifies referrer cannot earn referral bonus from more than 5 members."""
        tx_ref = RechargeTransaction(
            mobile_number="9876511111",
            operator="Jio",
            amount=199.0,
            payment_status="Paid",
            api_status="Success"
        )
        self.db.add(tx_ref)
        self.db.commit()

        card_ref, _, _ = allocate_scratch_card(self.db, tx_ref, brand="Myntreal")
        ref_code = card_ref.referral_code

        # Add 6 referred friends
        for i in range(6):
            tx_f = RechargeTransaction(
                mobile_number=f"98765222{i:02d}",
                operator="Jio",
                amount=199.0,
                referred_by=ref_code,
                payment_status="Paid",
                api_status="Success"
            )
            self.db.add(tx_f)
            self.db.commit()

            card_f, tok_f, _ = allocate_scratch_card(self.db, tx_f, brand="Myntreal")
            claim_f = ClaimScratchCardRequest(
                token=tok_f,
                name=f"Friend {i}",
                pincode="560001",
                city="Bengaluru",
                state="Karnataka"
            )
            claim_scratch_card(claim_f, db=self.db)

        # Count referral bonuses paid for this referrer
        paid_bonuses = self.db.query(ScratchCard).filter(
            ScratchCard.referred_by_card_id == card_ref.id,
            ScratchCard.referral_bonus_paid == True
        ).count()

        self.assertEqual(paid_bonuses, 5, "Referral bonuses should be capped at strictly 5 members")

    def test_quick_reply_service_creates_crm_lead(self):
        """Verifies inbound quick reply 'Interested in Solar' creates CRMLead with source='Recharge'."""
        tx = RechargeTransaction(
            mobile_number="9876533333",
            operator="Airtel",
            amount=299.0,
            payment_status="Paid",
            api_status="Success",
            guest_name="Solar Prospect"
        )
        self.db.add(tx)
        self.db.commit()

        card, tok, _ = allocate_scratch_card(self.db, tx, brand="Myntreal")
        claim_scratch_card(ClaimScratchCardRequest(
            token=tok,
            name="Solar Prospect",
            pincode="560001",
            city="Bengaluru",
            state="Karnataka"
        ), db=self.db)

        # Customer replies 'Interested in Solar'
        lead = handle_recharge_service_lead(
            db=self.db,
            from_phone="9876533333",
            message_text="Interested in Solar",
            from_name="Solar Prospect"
        )

        self.assertIsNotNone(lead)
        self.assertEqual(lead.source, "Recharge")
        self.assertEqual(lead.looking_for, "Solar")
        self.assertEqual(lead.name, "Solar Prospect")
        self.assertEqual(lead.phone, "9876533333")
        self.assertEqual(lead.city, "Bengaluru")
        self.assertEqual(lead.state, "Karnataka")
        self.assertEqual(lead.pincode, "560001")

    def test_direct_interest_endpoint_creates_lead(self):
        """Verifies POST /api/v1/scratch-card/interest creates CRMLead with source='Recharge'."""
        tx = RechargeTransaction(
            mobile_number="9876544444",
            operator="VI",
            amount=199.0,
            payment_status="Paid",
            api_status="Success",
            guest_name="EV Prospect"
        )
        self.db.add(tx)
        self.db.commit()

        card, tok, _ = allocate_scratch_card(self.db, tx, brand="Myntreal")
        claim_scratch_card(ClaimScratchCardRequest(
            token=tok,
            name="EV Prospect",
            pincode="560001",
            city="Bengaluru",
            state="Karnataka"
        ), db=self.db)

        req = ScratchInterestRequest(
            token=tok,
            category="EV"
        )
        res = register_scratch_interest(req, db=self.db)
        self.assertEqual(res["status"], "success")

        lead = self.db.query(CRMLead).filter(CRMLead.id == res["lead_id"]).first()
        self.assertIsNotNone(lead)
        self.assertEqual(lead.source, "Recharge")
        self.assertEqual(lead.looking_for, "EV")
        self.assertEqual(lead.name, "EV Prospect")


if __name__ == "__main__":
    unittest.main()
