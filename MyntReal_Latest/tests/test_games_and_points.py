"""
Unit Test Suite: Games, Points & Rewards Integration (MyntReal & VGK4U)
DC Protocol: DC_GAMES_TEST_001 (October 2026)

Verifies:
1. Game session lifecycle: start, rate limiting, and session tokens.
2. Anti-cheat physics timing validation across all 3 games:
   - Snake (minimum 0.35s per food item)
   - Block Drop (minimum 1.5s per cleared line)
   - Endless Runner (minimum 0.7s per 100m distance)
3. Score calculation, personal best recording, and milestone points conversion.
4. CustomerPointsLedger: Append-only loyalty points credit/debit and balance consistency.
5. OfficialPartner VGK Points Ledger: CAMPAIGN_BONUS credit and balance consistency.
6. Single-use Cryptographic Claim Codes (SHA-256):
   - Active code redemption by verified customer.
   - Idempotency guard: Re-claiming same code is strictly rejected (HTTP 400).
   - Invalid code rejection (HTTP 404).
7. Daily point earning limits (50 pts/day cap).
8. Pluggable character configuration for Endless Runner.
"""

import sys
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
from fastapi import HTTPException

# SQLite compatibility shim for PostgreSQL JSONB columns
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.models.base import Base, get_indian_time
from app.models.games_and_points import GameSession, CustomerPointsLedger, GameRewardCode
from app.models.customer_profile import CustomerProfile
from app.models.staff_accounts import OfficialPartner, VGKPointsLedger
from app.services.game_service import (
    start_game_session,
    complete_game_session,
    claim_reward_code,
    validate_anti_cheat_physics,
    calculate_reward_points,
    get_today_earned_points,
    get_user_game_stats,
    DAILY_POINTS_CAP
)


class TestGamesAndPointsSuite(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        target_tables = [
            CustomerProfile.__table__,
            OfficialPartner.__table__,
            VGKPointsLedger.__table__,
            GameSession.__table__,
            CustomerPointsLedger.__table__,
            GameRewardCode.__table__
        ]
        Base.metadata.create_all(bind=self.engine, tables=target_tables)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.Session()

        # Create sample verified customer
        self.customer = CustomerProfile(
            id=1,
            mobile_number="9876543210",
            customer_name="Rajesh Kumar",
            pincode="530001",
            security_pin_hash="sha256_dummy_hash",
            loyalty_points_balance=100.0,
            is_active=True,
            created_at=get_indian_time()
        )
        self.db.add(self.customer)

        # Create sample channel partner
        self.partner = OfficialPartner(
            id=1,
            partner_name="Venkatesh Rao",
            partner_code="VGK1001",
            category="DEALER",
            phone="9876500001",
            vgk_points_balance=500.0,
            is_active=True,
            created_at=get_indian_time()
        )
        self.db.add(self.partner)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_start_game_session_guest(self):
        """Verify guest player session initialization and default attributes."""
        res = start_game_session(
            db=self.db,
            game_type="SNAKE",
            character_id="volt_fox",
            account_type="GUEST"
        )
        self.assertIn("session_token", res)
        self.assertTrue(res["session_token"].startswith("gs_"))
        self.assertEqual(res["game_type"], "SNAKE")
        self.assertTrue(res["points_eligible"])

        session = self.db.query(GameSession).filter_by(session_token=res["session_token"]).first()
        self.assertIsNotNone(session)
        self.assertEqual(session.status, "ACTIVE")
        self.assertEqual(session.account_type, "GUEST")

    def test_start_game_session_authenticated_customer(self):
        """Verify customer session start links customer_id and character."""
        res = start_game_session(
            db=self.db,
            game_type="ENDLESS_RUNNER",
            character_id="robo_runner",
            account_type="CUSTOMER",
            account_id=self.customer.id
        )
        self.assertEqual(res["character_id"], "robo_runner")

        session = self.db.query(GameSession).filter_by(session_token=res["session_token"]).first()
        self.assertIsNotNone(session)
        self.assertEqual(session.customer_id, self.customer.id)
        self.assertEqual(session.character_id, "robo_runner")

    def test_anti_cheat_snake_physics(self):
        """Test snake speed verification (cannot collect food faster than 350ms/food)."""
        # Cheating attempt: 10 food collected in only 2 seconds (0.2s/food < 0.35s minimum)
        self.assertFalse(validate_anti_cheat_physics(
            game_type="SNAKE",
            score=100,
            level=1,
            lines_cleared=0,
            items_collected=10,
            distance_travelled=0,
            duration_seconds=2
        ))

        # Legitimate attempt: 10 food collected in 12 seconds (1.2s/food >= 0.35s)
        self.assertTrue(validate_anti_cheat_physics(
            game_type="SNAKE",
            score=100,
            level=1,
            lines_cleared=0,
            items_collected=10,
            distance_travelled=0,
            duration_seconds=12
        ))

    def test_anti_cheat_block_drop_physics(self):
        """Test block drop falling timing (cannot clear lines faster than 1.5s/line)."""
        # Cheating attempt: 10 lines cleared in 5 seconds (0.5s/line < 1.5s minimum)
        self.assertFalse(validate_anti_cheat_physics(
            game_type="BLOCK_DROP",
            score=1000,
            level=2,
            lines_cleared=10,
            items_collected=0,
            distance_travelled=0,
            duration_seconds=5
        ))

        # Legitimate attempt: 10 lines cleared in 25 seconds (2.5s/line >= 1.5s)
        self.assertTrue(validate_anti_cheat_physics(
            game_type="BLOCK_DROP",
            score=1000,
            level=2,
            lines_cleared=10,
            items_collected=0,
            distance_travelled=0,
            duration_seconds=25
        ))

    def test_anti_cheat_endless_runner_physics(self):
        """Test endless runner sprint speed (cannot travel faster than 0.7s per 100m)."""
        # Cheating attempt: 1000m travelled in 3 seconds (0.3s/100m < 0.7s minimum)
        self.assertFalse(validate_anti_cheat_physics(
            game_type="ENDLESS_RUNNER",
            score=1000,
            level=1,
            lines_cleared=0,
            items_collected=5,
            distance_travelled=1000,
            duration_seconds=3
        ))

        # Legitimate attempt: 1000m travelled in 30 seconds (3.0s/100m >= 0.7s)
        self.assertTrue(validate_anti_cheat_physics(
            game_type="ENDLESS_RUNNER",
            score=1000,
            level=1,
            lines_cleared=0,
            items_collected=5,
            distance_travelled=1000,
            duration_seconds=30
        ))

    def test_complete_session_anti_cheat_rejection(self):
        """Ensure session completion with impossible physics raises HTTP 400 and abandons session."""
        start_res = start_game_session(db=self.db, game_type="SNAKE")
        token = start_res["session_token"]

        with self.assertRaises(HTTPException) as ctx:
            complete_game_session(
                db=self.db,
                session_token=token,
                score=500,
                level=1,
                lines_cleared=0,
                items_collected=50,
                distance_travelled=0,
                duration_seconds=5  # 50 food in 5s is physically impossible
            )
        self.assertEqual(ctx.exception.status_code, 400)

        session = self.db.query(GameSession).filter_by(session_token=token).first()
        self.assertEqual(session.status, "ABANDONED")

    def test_complete_session_and_customer_direct_credit(self):
        """Verify that when POINTS_ISSUANCE_ACTIVE is True, customer earns points directly into loyalty balance."""
        with patch("app.services.game_service.POINTS_ISSUANCE_ACTIVE", True):
            start_res = start_game_session(
                db=self.db,
                game_type="SNAKE",
                account_type="CUSTOMER",
                account_id=self.customer.id
            )
            token = start_res["session_token"]

            comp_res = complete_game_session(
                db=self.db,
                session_token=token,
                score=150,
                level=2,
                lines_cleared=0,
                items_collected=15,  # 1 milestone (10 food) = 10 pts
                distance_travelled=0,
                duration_seconds=20
            )

            self.assertTrue(comp_res["success"])
            self.assertEqual(comp_res["reward_points"], 10)
            self.assertEqual(comp_res["reward_status"], "CLAIMED")
            self.assertEqual(comp_res["total_balance"], 110.0)

            # Verify customer profile updated
            self.db.refresh(self.customer)
            self.assertEqual(float(self.customer.loyalty_points_balance), 110.0)

            # Verify ledger row created
            ledger = self.db.query(CustomerPointsLedger).filter_by(customer_id=self.customer.id).first()
            self.assertIsNotNone(ledger)
            self.assertEqual(float(ledger.points_credit), 10.0)
            self.assertEqual(ledger.reason_code, "GAME_REWARD")

    def test_complete_session_and_partner_direct_credit(self):
        """Verify that when POINTS_ISSUANCE_ACTIVE is True, partner earns points in VGKPointsLedger."""
        with patch("app.services.game_service.POINTS_ISSUANCE_ACTIVE", True):
            start_res = start_game_session(
                db=self.db,
                game_type="BLOCK_DROP",
                account_type="PARTNER",
                account_id=self.partner.id
            )
            token = start_res["session_token"]

            comp_res = complete_game_session(
                db=self.db,
                session_token=token,
                score=400,
                level=2,
                lines_cleared=8,  # 2 milestones (8 lines) = 20 pts (max session cap)
                items_collected=0,
                distance_travelled=0,
                duration_seconds=30
            )

            self.assertTrue(comp_res["success"])
            self.assertEqual(comp_res["reward_points"], 20)
            self.assertEqual(comp_res["reward_status"], "CLAIMED")

            # Verify partner balance updated
            self.db.refresh(self.partner)
            self.assertEqual(float(self.partner.vgk_points_balance), 520.0)

            # Verify VGKPointsLedger record
            ledger = self.db.query(VGKPointsLedger).filter_by(partner_id=self.partner.id).first()
            self.assertIsNotNone(ledger)
            self.assertEqual(float(ledger.points_credit), 20.0)
            self.assertEqual(ledger.reason_code, "CAMPAIGN_BONUS")

    def test_guest_reward_code_generation_and_single_use_claim(self):
        """Verify guest player receives human-friendly claim code and customer redeems it once."""
        with patch("app.services.game_service.POINTS_ISSUANCE_ACTIVE", True):
            start_res = start_game_session(db=self.db, game_type="ENDLESS_RUNNER", account_type="GUEST")
            token = start_res["session_token"]

            comp_res = complete_game_session(
                db=self.db,
                session_token=token,
                score=550,
                level=1,
                lines_cleared=0,
                items_collected=10,
                distance_travelled=500,  # 2 milestones (250m * 2) = 20 pts
                duration_seconds=40
            )

            self.assertTrue(comp_res["requires_claim"])
            claim_code = comp_res["claim_code"]
            self.assertIsNotNone(claim_code)
            self.assertTrue(claim_code.startswith("PLAY-"))

            # Customer claims code
            claim_res = claim_reward_code(
                db=self.db,
                claim_code=claim_code,
                account_type="CUSTOMER",
                account_id=self.customer.id
            )
            self.assertTrue(claim_res["success"])
            self.assertEqual(claim_res["credited_points"], 20)
            self.assertEqual(claim_res["new_balance"], 120.0)

            # Attempting to claim the exact same code a second time MUST fail
            with self.assertRaises(HTTPException) as ctx:
                claim_reward_code(
                    db=self.db,
                    claim_code=claim_code,
                    account_type="CUSTOMER",
                    account_id=self.customer.id
                )
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("already been redeemed", ctx.exception.detail)

    def test_claim_invalid_code(self):
        """Verify claiming non-existent code raises HTTP 404."""
        with self.assertRaises(HTTPException) as ctx:
            claim_reward_code(
                db=self.db,
                claim_code="PLAY-FAKE-9999",
                account_type="CUSTOMER",
                account_id=self.customer.id
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_daily_points_cap_enforcement(self):
        """Verify daily cap (50 points/day) restricts excessive point crediting."""
        with patch("app.services.game_service.POINTS_ISSUANCE_ACTIVE", True):
            # Session 1: Earn 20 pts
            s1 = start_game_session(db=self.db, game_type="SNAKE", account_type="CUSTOMER", account_id=self.customer.id)
            c1 = complete_game_session(self.db, s1["session_token"], 200, 1, 0, 20, 0, 30)
            self.assertEqual(c1["reward_points"], 20)

            # Session 2: Earn 20 pts (Total: 40)
            s2 = start_game_session(db=self.db, game_type="SNAKE", account_type="CUSTOMER", account_id=self.customer.id)
            c2 = complete_game_session(self.db, s2["session_token"], 200, 1, 0, 20, 0, 30)
            self.assertEqual(c2["reward_points"], 20)

            # Session 3: Only 10 pts remaining in daily cap (Total: 50)
            s3 = start_game_session(db=self.db, game_type="SNAKE", account_type="CUSTOMER", account_id=self.customer.id)
            c3 = complete_game_session(self.db, s3["session_token"], 200, 1, 0, 20, 0, 30)
            self.assertEqual(c3["reward_points"], 10)  # Capped at remaining 10

            # Session 4: Cap reached (0 pts)
            s4 = start_game_session(db=self.db, game_type="SNAKE", account_type="CUSTOMER", account_id=self.customer.id)
            c4 = complete_game_session(self.db, s4["session_token"], 200, 1, 0, 20, 0, 30)
            self.assertEqual(c4["reward_points"], 0)
            self.assertEqual(c4["reward_status"], "NOT_ELIGIBLE")

    def test_user_game_stats_aggregation(self):
        """Verify user stats aggregator returns personal bests and history."""
        s1 = start_game_session(db=self.db, game_type="SNAKE", account_type="CUSTOMER", account_id=self.customer.id)
        complete_game_session(self.db, s1["session_token"], 120, 1, 0, 10, 0, 25)

        s2 = start_game_session(db=self.db, game_type="SNAKE", account_type="CUSTOMER", account_id=self.customer.id)
        complete_game_session(self.db, s2["session_token"], 250, 2, 0, 20, 0, 35)

        stats = get_user_game_stats(self.db, "CUSTOMER", self.customer.id)
        self.assertEqual(stats["best_scores"]["SNAKE"], 250)
        self.assertEqual(len(stats["recent_sessions"]), 2)

    def test_quick_resume_new_and_existing_customer(self):
        """Verify seamless mobile-number resume creates new profile or retrieves existing with JWT token."""
        from app.api.v1.endpoints.games_api import api_quick_resume
        from app.schemas.games import QuickResumeRequest

        # 1. New mobile number
        req_new = QuickResumeRequest(mobile_number="9876501234")
        resp_new = api_quick_resume(req_new, self.db)
        self.assertTrue(resp_new.success)
        self.assertEqual(resp_new.mobile_number, "9876501234")
        self.assertEqual(resp_new.loyalty_points, 0.0)
        self.assertTrue(len(resp_new.token) > 20)

        # 2. Existing mobile number with points
        self.customer.loyalty_points_balance = 75.0
        self.db.commit()

        req_exist = QuickResumeRequest(mobile_number=self.customer.mobile_number)
        resp_exist = api_quick_resume(req_exist, self.db)
        self.assertTrue(resp_exist.success)
        self.assertEqual(resp_exist.customer_id, self.customer.id)
        self.assertEqual(resp_exist.loyalty_points, 75.0)
        self.assertTrue(len(resp_exist.token) > 20)

    def test_start_session_auto_attach_with_mobile(self):
        """Verify api_start_game automatically resolves and attaches customer when mobile_number is provided."""
        from app.api.v1.endpoints.games_api import api_start_game
        from app.schemas.games import GameStartRequest
        from unittest.mock import MagicMock

        mock_req = MagicMock()
        mock_req.headers = {}
        mock_req.cookies = {}
        mock_req.client.host = "127.0.0.1"

        payload = GameStartRequest(game_type="SNAKE", mobile_number="9123456789")
        res = api_start_game(payload, mock_req, self.db)
        self.assertTrue(res.success)
        self.assertTrue(res.session_token.startswith("gs_"))

        # Check DB session has customer account_type
        sess = self.db.query(GameSession).filter_by(session_token=res.session_token).first()
        self.assertIsNotNone(sess)
        self.assertEqual(sess.account_type, "CUSTOMER")
        self.assertIsNotNone(sess.customer_id)


if __name__ == "__main__":
    unittest.main()

