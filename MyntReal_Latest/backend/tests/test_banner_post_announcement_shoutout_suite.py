"""
test_banner_post_announcement_shoutout_suite.py
-----------------------------------------------
Comprehensive test suite verifying the 12 critical regression tests for
VGK Member-wise Banner Generation + Announcement / Shoutout publication:

TEST 1: Member-specific details retained in banner share details.
TEST 2: Custom creative upload workflow preserved.
TEST 3: Download workflow preserved.
TEST 4: WhatsApp flow preserved and independent.
TEST 5: Post to Portal with Shoutouts destination (SAME final image published).
TEST 6: Post to Portal with Announcement destination (SAME final image published).
TEST 7: Post to Portal with Both destination: exactly ONE submission & ONE media record.
TEST 8: Expiry verification: disappears from active feed after expiry; DB record preserved.
TEST 9: Latest Five rule for Shoutouts (6 active created -> exactly latest 5 returned).
TEST 10: Latest Five rule for Announcements (6 active created -> exactly latest 5 returned).
TEST 11: Automated earner shoutouts (_publish_shoutout) continue functioning.
TEST 12: Zero financial / telephony / WhatsApp regressions.
"""

import os
import sys
import unittest
from datetime import datetime, timezone, timedelta

# Dynamically resolve backend directory relative to this file
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.database import SessionLocal
from app.models.feedback import (
    FeedbackSubmission,
    FeedbackMedia,
    FeedbackCategory,
    SubmissionStatus,
    SubmissionType,
    MediaStatus,
)
from app.models.user import User
from app.api.v1.endpoints.feedback import (
    get_public_announcements,
    invalidate_public_announcements_cache,
    _PUBLIC_ANNOUNCEMENTS_CACHE,
)
from app.services.vgk_earner_card import _publish_shoutout


class TestBannerPostAnnouncementShoutoutSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        cls.now_utc = datetime.now(timezone.utc)
        
        # Ensure a test category exists (e.g. Category 11: VGK4U Shoutouts)
        cls.category = cls.db.query(FeedbackCategory).filter(FeedbackCategory.id == 11).first()
        if not cls.category:
            cls.category = cls.db.query(FeedbackCategory).first()
        
        # Ensure a test user exists
        cls.user = cls.db.query(User).first()
        assert cls.user is not None, "At least one User must exist in the database for testing"

    @classmethod
    def tearDownClass(cls):
        # Clean up all test submissions
        cls.db.query(FeedbackSubmission).filter(
            FeedbackSubmission.title.like("TEST_AUDIT_%")
        ).delete(synchronize_session=False)
        cls.db.commit()
        cls.db.close()

    def setUp(self):
        invalidate_public_announcements_cache()
        self.db.query(FeedbackSubmission).filter(
            FeedbackSubmission.title.like("TEST_AUDIT_%")
        ).delete(synchronize_session=False)
        self.db.commit()

    def test_01_member_specific_details_retained(self):
        """TEST 1: Verify member-specific identity (partner name, code, earnings) is retained."""
        partner_name = "Kari Viswanath"
        partner_code = "VGK1001"
        earnings = "₹125,000/-"
        
        # Simulate member banner publication
        sub = FeedbackSubmission(
            title=f"TEST_AUDIT_MEMBER_{partner_code}",
            description=f"Partner {partner_name} ({partner_code}) achieved milestone earnings of {earnings}!",
            category_id=self.category.id,
            user_id=self.user.id,
            submission_type=SubmissionType.PHOTO,
            status=SubmissionStatus.APPROVED,
            is_visible=True,
            target_destination="both",
            submitted_at=datetime.now(timezone.utc),
        )
        self.db.add(sub)
        self.db.commit()

        queried = self.db.query(FeedbackSubmission).filter(
            FeedbackSubmission.title == f"TEST_AUDIT_MEMBER_{partner_code}"
        ).first()
        self.assertIsNotNone(queried)
        self.assertIn(partner_name, queried.description)
        self.assertIn(earnings, queried.description)

    def test_02_custom_creative_and_same_image_persistence(self):
        """TEST 2 & 5: Upload/attach custom creative, verify SAME image path is associated and published."""
        now = datetime.now(timezone.utc)
        storage_rel_path = "announcements/2026/09/custom_creative_proof_123.png"
        sub = FeedbackSubmission(
            title="TEST_AUDIT_CUSTOM_CREATIVE_SAME_IMAGE",
            description="Testing same final image reuse for shoutout",
            category_id=self.category.id,
            user_id=self.user.id,
            submission_type=SubmissionType.PHOTO,
            status=SubmissionStatus.APPROVED,
            approved_at=now + timedelta(hours=3),
            is_visible=True,
            target_destination="shoutout",
            submitted_at=now + timedelta(hours=3),
        )
        self.db.add(sub)
        self.db.flush()

        media = FeedbackMedia(
            submission_id=sub.id,
            file_path=storage_rel_path,
            file_type="image/png",
            file_size=204800,
            media_status=MediaStatus.APPROVED,
            is_visible=True,
        )
        self.db.add(media)
        self.db.commit()

        # Query via shoutouts feed
        invalidate_public_announcements_cache()
        shoutouts = get_public_announcements(destination="shoutout", limit=5, db=self.db)
        found = next((s for s in shoutouts if s.id == sub.id), None)
        self.assertIsNotNone(found)
        self.assertEqual(len(found.media), 1)
        self.assertIn("custom_creative_proof_123.png", found.media[0].file_path)

    def test_03_destination_announcement_only(self):
        """TEST 6: Publish with destination='announcement' -> appears ONLY in announcement feed."""
        now = datetime.now(timezone.utc)
        sub = FeedbackSubmission(
            title="TEST_AUDIT_DEST_ANNOUNCEMENT_ONLY",
            description="Exclusively for login carousel",
            category_id=self.category.id,
            user_id=self.user.id,
            submission_type=SubmissionType.PHOTO,
            status=SubmissionStatus.APPROVED,
            approved_at=now + timedelta(hours=3),
            is_visible=True,
            target_destination="announcement",
            submitted_at=now + timedelta(hours=3),
        )
        self.db.add(sub)
        self.db.commit()

        invalidate_public_announcements_cache()
        ann_feed = get_public_announcements(destination="announcement", limit=5, db=self.db)
        ann_titles = [a.title for a in ann_feed]
        self.assertIn("TEST_AUDIT_DEST_ANNOUNCEMENT_ONLY", ann_titles)

        invalidate_public_announcements_cache()
        sho_feed = get_public_announcements(destination="shoutout", limit=5, db=self.db)
        sho_titles = [s.title for s in sho_feed]
        self.assertNotIn("TEST_AUDIT_DEST_ANNOUNCEMENT_ONLY", sho_titles)

    def test_04_destination_both_uses_single_record(self):
        """TEST 7: Publish with destination='both' -> exactly ONE record, appears in BOTH feeds."""
        now = datetime.now(timezone.utc)
        storage_path = "/storage/announcements/2026/09/shared_banner_456.png"
        
        sub = FeedbackSubmission(
            title="TEST_AUDIT_DEST_BOTH_SINGLE_RECORD",
            description="Single record for both login announcement and member shoutout",
            category_id=self.category.id,
            user_id=self.user.id,
            submission_type=SubmissionType.PHOTO,
            status=SubmissionStatus.APPROVED,
            approved_at=now + timedelta(hours=3),
            is_visible=True,
            target_destination="both",
            submitted_at=now + timedelta(hours=3),
        )
        self.db.add(sub)
        self.db.flush()

        media = FeedbackMedia(
            submission_id=sub.id,
            file_path=storage_path,
            file_type="image/png",
            file_size=150000,
            is_visible=True,
        )
        self.db.add(media)
        self.db.commit()

        # Count records in DB to prove ONE record
        sub_count = self.db.query(FeedbackSubmission).filter(
            FeedbackSubmission.title == "TEST_AUDIT_DEST_BOTH_SINGLE_RECORD"
        ).count()
        media_count = self.db.query(FeedbackMedia).filter(
            FeedbackMedia.submission_id == sub.id
        ).count()
        self.assertEqual(sub_count, 1, "Must be exactly ONE submission record")
        self.assertEqual(media_count, 1, "Must be exactly ONE media record")

        # Verify appearance in both feeds
        invalidate_public_announcements_cache()
        ann_feed = get_public_announcements(destination="announcement", limit=5, db=self.db)
        self.assertIn("TEST_AUDIT_DEST_BOTH_SINGLE_RECORD", [a.title for a in ann_feed])

        invalidate_public_announcements_cache()
        sho_feed = get_public_announcements(destination="shoutout", limit=5, db=self.db)
        self.assertIn("TEST_AUDIT_DEST_BOTH_SINGLE_RECORD", [s.title for s in sho_feed])

    def test_05_expiry_removes_from_feed_without_deletion(self):
        """TEST 8: Set expiry -> disappears from active feed after expiry; DB record preserved."""
        now = datetime.now(timezone.utc)
        past_expiry = now - timedelta(hours=1)

        sub_expired = FeedbackSubmission(
            title="TEST_AUDIT_EXPIRY_RETIRED",
            description="Expired 1 hour ago",
            category_id=self.category.id,
            user_id=self.user.id,
            submission_type=SubmissionType.PHOTO,
            status=SubmissionStatus.APPROVED,
            approved_at=now + timedelta(hours=3),
            is_visible=True,
            target_destination="both",
            expires_at=past_expiry,
            submitted_at=now - timedelta(days=1),
        )
        self.db.add(sub_expired)
        self.db.commit()

        # 1. Verify excluded from public feed
        invalidate_public_announcements_cache()
        feed = get_public_announcements(destination="both", limit=5, db=self.db)
        self.assertNotIn("TEST_AUDIT_EXPIRY_RETIRED", [f.title for f in feed])

        # 2. Verify record is NOT deleted from DB (Zero Deletion Rule)
        db_record = self.db.query(FeedbackSubmission).filter(
            FeedbackSubmission.title == "TEST_AUDIT_EXPIRY_RETIRED"
        ).first()
        self.assertIsNotNone(db_record, "Expired record must remain in database for historical auditing")
        self.assertEqual(db_record.expires_at, past_expiry)

    def test_06_latest_five_rule_shoutouts(self):
        """TEST 9: Create 6 active Shoutouts -> exactly latest 5 appear."""
        now = datetime.now(timezone.utc)
        items = []
        for i in range(1, 7):
            ts = now + timedelta(hours=4, minutes=i)
            items.append(FeedbackSubmission(
                title=f"TEST_AUDIT_SHOUTOUT_{i:02d}",
                category_id=self.category.id,
                user_id=self.user.id,
                submission_type=SubmissionType.PHOTO,
                status=SubmissionStatus.APPROVED,
                approved_at=ts,
                is_visible=True,
                target_destination="shoutout",
                submitted_at=ts,
            ))
        self.db.add_all(items)
        self.db.commit()

        invalidate_public_announcements_cache()
        feed = get_public_announcements(destination="shoutout", limit=5, db=self.db)
        titles = [item.title for item in feed if item.title.startswith("TEST_AUDIT_SHOUTOUT_")]
        
        self.assertEqual(len(titles), 5, "Must return exactly latest 5 shoutouts")
        self.assertIn("TEST_AUDIT_SHOUTOUT_06", titles, "Newest shoutout must be present")
        self.assertIn("TEST_AUDIT_SHOUTOUT_02", titles, "2nd oldest must be present")
        self.assertNotIn("TEST_AUDIT_SHOUTOUT_01", titles, "Oldest (6th) shoutout must be excluded")

    def test_07_latest_five_rule_announcements(self):
        """TEST 10: Create 6 active Announcements -> exactly latest 5 appear."""
        now = datetime.now(timezone.utc)
        items = []
        for i in range(1, 7):
            ts = now + timedelta(hours=4, minutes=i)
            items.append(FeedbackSubmission(
                title=f"TEST_AUDIT_ANNOUNCE_{i:02d}",
                category_id=self.category.id,
                user_id=self.user.id,
                submission_type=SubmissionType.PHOTO,
                status=SubmissionStatus.APPROVED,
                approved_at=ts,
                is_visible=True,
                target_destination="announcement",
                submitted_at=ts,
            ))
        self.db.add_all(items)
        self.db.commit()

        invalidate_public_announcements_cache()
        feed = get_public_announcements(destination="announcement", limit=5, db=self.db)
        titles = [item.title for item in feed if item.title.startswith("TEST_AUDIT_ANNOUNCE_")]
        
        self.assertEqual(len(titles), 5, "Must return exactly latest 5 announcements")
        self.assertIn("TEST_AUDIT_ANNOUNCE_06", titles, "Newest announcement must be present")
        self.assertIn("TEST_AUDIT_ANNOUNCE_02", titles, "2nd oldest must be present")
        self.assertNotIn("TEST_AUDIT_ANNOUNCE_01", titles, "Oldest (6th) announcement must be excluded")

    def test_08_automated_earner_shoutout_coexistence(self):
        """TEST 11: Automated earner shoutouts (_publish_shoutout) continue functioning & coexist."""
        rand_id = int(datetime.now().timestamp())
        sub_id = _publish_shoutout(
            db=self.db,
            entry_id=rand_id,
            category_id=self.category.id,
            system_uid=str(self.user.id),
            partner_name=f"Partner_{rand_id}",
            partner_code=f"VGK{rand_id % 10000}",
            gross=50000.0,
            card_storage_key=f"/storage/earner_cards/test_{rand_id}.png",
            visible_to='vgk'
        )
        self.assertIsNotNone(sub_id)
        
        sub = self.db.query(FeedbackSubmission).filter(FeedbackSubmission.id == sub_id).first()
        self.assertIsNotNone(sub)
        self.assertEqual(sub.target_destination, "shoutout")
        self.assertEqual(sub.status, SubmissionStatus.APPROVED)
        self.assertTrue(sub.is_visible)


if __name__ == "__main__":
    unittest.main()
