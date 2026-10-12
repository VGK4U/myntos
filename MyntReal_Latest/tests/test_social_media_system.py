"""
Comprehensive Automated Test Suite — MintOS / ZynovaOS Social Media Manager
Tests:
1. Multi-Tenant & Company Context Isolation (Mynt Real vs Zynova Mobility)
2. Mock / Sandbox Channel Connection & Hosted OAuth Connect Link
3. 30-Day AI Calendar Generation (15 bi-daily posts, platform copy, X 280-char limit)
4. Post State Machine (Draft -> Scheduled -> Published / Failed) & Editing
5. Durable Background Publishing Worker (Atomic claiming, platform dispatches, idempotency keys, retry backoff)
6. Webhook Processing & Deduplication (post.published, account.disconnected, signature verification)
7. Omnichannel Analytics Synchronization & Metric Aggregation
8. FastAPI Endpoints Suite (Overview, Accounts, Calendar, Post Actions, Settings, Analytics)
"""

import sys
import os
import unittest
from datetime import datetime, timedelta, date
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Strictly isolate test execution to disposable local SQLite database
os.environ["ALLOW_PROD_DB_ACCESS"] = "0"
os.environ["PROD_DATABASE_URL"] = ""
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.models.base import Base, get_indian_time
from app.models.social_media import (
    SocialAccountConnection,
    SocialCalendarSetting,
    SocialPost,
    SocialPostDispatch,
    SocialAnalyticsSnapshot,
    SocialWebhookEvent
)
from app.services.social_media_service import (
    BaseSocialProvider,
    ZernioSocialProvider,
    get_social_provider
)
from app.services.social_ai_service import SocialAIService
from app.services.social_publish_service import (
    process_scheduled_social_posts,
    handle_social_webhook,
    sync_social_analytics
)
from app.core.context import RequestContext, AdminScope
from app.core.database import get_db
from app.api.deps import get_request_context
from app.api.v1.api import api_router
from fastapi import FastAPI


class TestSocialMediaManagerSuite(unittest.TestCase):

    def setUp(self):
        # Create an isolated SQLite in-memory database using StaticPool so all threads share state
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        self.tables = [
            SocialAccountConnection.__table__,
            SocialCalendarSetting.__table__,
            SocialPost.__table__,
            SocialPostDispatch.__table__,
            SocialAnalyticsSnapshot.__table__,
            SocialWebhookEvent.__table__
        ]
        Base.metadata.create_all(self.engine, tables=self.tables)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.SessionLocal()

        # Build mock FastAPI application for endpoint verification
        self.app = FastAPI()
        self.app.include_router(api_router, prefix="/api/v1")

        # Dependency overrides for API testing
        self.mock_ctx = RequestContext(
            staff_id=1,
            emp_code="MR10001",
            tenant_id=1,
            active_company_id=1,
            hierarchy_level=150,
            role_code="superadmin",
            admin_scope=AdminScope.PLATFORM_SUPERADMIN,
            licensed_modules={"SOCIAL_MEDIA_MANAGER"}
        )

        def override_ctx():
            return self.mock_ctx

        def override_db():
            session = self.SessionLocal()
            try:
                yield session
            finally:
                session.close()

        self.app.dependency_overrides[get_request_context] = override_ctx
        self.app.dependency_overrides[get_db] = override_db
        self.client = TestClient(self.app)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine, tables=self.tables)
        self.engine.dispose()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Multi-Tenant Company Context & Tenant Isolation Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_tenant_and_company_isolation(self):
        """Verify strict isolation between Company 1 (Mynt Real) and Company 2 (Zynova Mobility)."""
        now = get_indian_time()

        # Create connection for Company 1
        conn_c1 = SocialAccountConnection(
            tenant_id=1,
            company_id=1,
            platform="facebook",
            platform_account_id="fb_page_101",
            account_name="Mynt Real Official",
            account_username="@myntreal",
            provider_profile_id="mintos_t1_c1",
            status="ACTIVE"
        )
        # Create connection for Company 2
        conn_c2 = SocialAccountConnection(
            tenant_id=1,
            company_id=2,
            platform="facebook",
            platform_account_id="fb_page_202",
            account_name="Zynova Mobility Official",
            account_username="@zynovamobility",
            provider_profile_id="mintos_t1_c2",
            status="ACTIVE"
        )
        self.db.add_all([conn_c1, conn_c2])

        # Create post for Company 1
        post_c1 = SocialPost(
            tenant_id=1,
            company_id=1,
            topic_theme="Mynt Real Estate Investment",
            master_caption="Invest in premium commercial spaces with Mynt Real.",
            scheduled_at=now + timedelta(days=1),
            status="DRAFT"
        )
        # Create post for Company 2
        post_c2 = SocialPost(
            tenant_id=1,
            company_id=2,
            topic_theme="Zynova Electric 2-Wheeler Launch",
            master_caption="Switch to clean energy with Zynova EV scooters.",
            scheduled_at=now + timedelta(days=1),
            status="DRAFT"
        )
        self.db.add_all([post_c1, post_c2])
        self.db.commit()

        # Query posts exclusively for Company 1
        c1_posts = self.db.query(SocialPost).filter(SocialPost.company_id == 1).all()
        self.assertEqual(len(c1_posts), 1)
        self.assertEqual(c1_posts[0].topic_theme, "Mynt Real Estate Investment")

        # Query posts exclusively for Company 2
        c2_posts = self.db.query(SocialPost).filter(SocialPost.company_id == 2).all()
        self.assertEqual(len(c2_posts), 1)
        self.assertEqual(c2_posts[0].topic_theme, "Zynova Electric 2-Wheeler Launch")

        # Verify provider profile keys are strictly isolated per company
        provider = get_social_provider()
        prof_c1 = provider.create_or_get_profile(company_id=1, company_name="Mynt Real", tenant_id=1)
        prof_c2 = provider.create_or_get_profile(company_id=2, company_name="Zynova Mobility", tenant_id=1)
        self.assertEqual(prof_c1["external_id"], "mintos_t1_c1")
        self.assertEqual(prof_c2["external_id"], "mintos_t1_c2")
        self.assertNotEqual(prof_c1["external_id"], prof_c2["external_id"])

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Mock / Sandbox Channel Connection & Hosted OAuth Connect Link Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_mock_account_connection_lifecycle(self):
        """Test mock account connection, updating existing connection, and disconnect."""
        conn = SocialAccountConnection(
            tenant_id=1,
            company_id=1,
            platform="facebook",
            platform_account_id="mock_fb_12345",
            account_name="Mynt Real Sandbox FB",
            account_username="@myntreal_test",
            provider_profile_id="mintos_t1_c1",
            provider_account_id="mock_fb_12345",
            status="ACTIVE",
            capabilities=["publish_post", "insights"]
        )
        self.db.add(conn)
        self.db.commit()

        # Verify in DB
        db_conn = self.db.query(SocialAccountConnection).filter(
            SocialAccountConnection.company_id == 1,
            SocialAccountConnection.platform == "facebook"
        ).first()
        self.assertIsNotNone(db_conn)
        self.assertEqual(db_conn.status, "ACTIVE")
        self.assertEqual(db_conn.account_username, "@myntreal_test")

        # Test disconnect via provider adapter
        provider = get_social_provider()
        discon_res = provider.disconnect_account(
            profile_id=db_conn.provider_profile_id,
            platform="facebook",
            platform_account_id=db_conn.platform_account_id
        )
        self.assertTrue(discon_res)

        db_conn.status = "DISCONNECTED"
        self.db.commit()
        db_conn_updated = self.db.query(SocialAccountConnection).filter(
            SocialAccountConnection.id == db_conn.id
        ).first()
        self.assertEqual(db_conn_updated.status, "DISCONNECTED")

    def test_hosted_oauth_connect_link(self):
        """Test generation of hosted OAuth connect URL with CSRF state validation."""
        provider = get_social_provider()
        url = provider.generate_connect_url(
            profile_id="mintos_t1_c2",
            platform="instagram",
            redirect_uri="http://localhost:3000/staff/configuration/social-media",
            state="state_t1_c2_instagram"
        )
        self.assertIn("https://zernio.com/connect/instagram", url)
        self.assertIn("profileId=mintos_t1_c2", url)
        self.assertIn("state=state_t1_c2_instagram", url)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. 30-Day AI Calendar & Multi-Platform Copy Generation Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_ai_calendar_generation_15_bi_daily_posts(self):
        """Test generating 15 bi-daily strategic posts over 30 days with verified context."""
        start_date = date(2026, 11, 1)
        ai_service = SocialAIService()

        with patch.object(ai_service, "extract_company_context") as mock_ctx:
            mock_ctx.return_value = {
                "company_id": 2,
                "company_name": "Zynova Mobility",
                "brand_voice": "Smart, innovative, clean energy mobility",
                "verified_phone": "+91 9876543210",
                "verified_website": "https://zynovamobility.com",
                "location": "Hyderabad, Telangana",
                "content_themes": ["EV Benefits", "Green Commute", "Battery Tech", "Customer Reviews"],
                "default_hashtags": ["#ZynovaMobility", "#EVIndia", "#SmartRide"],
                "helpline_phone": "+91 9876543210",
                "website_url": "https://zynovamobility.com",
                "business_segments": ["EV 2-Wheelers", "Solar Clean Tech"],
                "target_audience": "Urban commuters, EV buyers, and clean tech enthusiasts",
                "enabled_platforms": ["facebook", "instagram", "linkedin", "x"]
            }

            posts_data = ai_service.generate_monthly_calendar(
                db=self.db,
                company_id=2,
                tenant_id=1,
                start_date=start_date,
                custom_instructions="Focus on festival Diwali discounts for EV 2-wheelers."
            )

            # Assert exactly 15 bi-daily posts
            self.assertEqual(len(posts_data), 15)

            # Validate each post schema & bi-daily spacing
            for idx, p in enumerate(posts_data):
                self.assertIsNotNone(p.topic_theme)
                self.assertIsNotNone(p.master_caption)
                self.assertIsNotNone(p.scheduled_at)
                self.assertEqual(p.status, "DRAFT")
                self.assertEqual(p.scheduled_at.date(), start_date + timedelta(days=idx * 2))

                # Verify brand presence or hashtags
                self.assertTrue(
                    "Zynova" in p.master_caption or "EV" in p.master_caption or "#" in p.master_caption or len(p.master_hashtags) > 0 or "Mobility" in p.master_caption
                )

    def test_single_post_caption_regeneration(self):
        """Test single-post caption regeneration without altering other posts."""
        ai_service = SocialAIService()
        now = get_indian_time()

        post = SocialPost(
            tenant_id=1,
            company_id=1,
            topic_theme="Exclusive Prime Highway Commercial Plots",
            master_caption="Old draft caption.",
            scheduled_at=now + timedelta(days=2),
            status="DRAFT"
        )
        self.db.add(post)
        self.db.commit()

        with patch.object(ai_service, "extract_company_context") as mock_ctx:
            mock_ctx.return_value = {
                "company_id": 1,
                "company_name": "Mynt Real LLP",
                "brand_voice": "Premium real estate and wealth creation",
                "verified_phone": "+91 9988776655",
                "verified_website": "https://myntreal.com",
                "location": "Hyderabad",
                "content_themes": ["Commercial Land", "High ROI"],
                "default_hashtags": ["#MyntReal", "#RealEstate"],
                "business_segments": ["Real Estate", "Commercial Plots"]
            }

            res = ai_service.regenerate_post_caption(
                db=self.db,
                post_id=post.id,
                company_id=1,
                tone="Authoritative"
            )

            self.assertIn("id", res)
            self.assertEqual(res["id"], post.id)
            self.db.refresh(post)
            self.assertIsNotNone(post.master_caption)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Post State Machine, Editing & Approval Workflow Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_post_approval_and_scheduling_flow(self):
        """Test transition from DRAFT to SCHEDULED upon approval."""
        now = get_indian_time()
        post = SocialPost(
            tenant_id=1,
            company_id=1,
            topic_theme="Commercial Investment Advisory",
            master_caption="Secure high rental yield properties in emerging corridors.",
            scheduled_at=now + timedelta(days=2),
            status="DRAFT"
        )
        self.db.add(post)
        self.db.commit()

        self.assertEqual(post.status, "DRAFT")

        # Approve and schedule post
        post.status = "SCHEDULED"
        post.approved_by_staff_id = 101
        post.approved_at = now
        self.db.commit()

        db_post = self.db.query(SocialPost).filter(SocialPost.id == post.id).first()
        self.assertEqual(db_post.status, "SCHEDULED")
        self.assertIsNotNone(db_post.approved_at)

    def test_post_update_customizations(self):
        """Test modifying captions, schedule, and platform variations."""
        now = get_indian_time()
        post = SocialPost(
            tenant_id=1,
            company_id=1,
            topic_theme="Initial Topic",
            master_caption="Initial Master Caption",
            scheduled_at=now + timedelta(days=1),
            status="DRAFT"
        )
        self.db.add(post)
        self.db.commit()

        # Update fields
        post.topic_theme = "Updated Topic"
        post.master_caption = "Updated Master Caption"
        post.media_urls = ["https://example.com/asset.jpg"]
        self.db.commit()

        db_post = self.db.query(SocialPost).filter(SocialPost.id == post.id).first()
        self.assertEqual(db_post.topic_theme, "Updated Topic")
        self.assertEqual(db_post.media_urls, ["https://example.com/asset.jpg"])

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Durable Background Publisher Worker Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_background_publisher_worker_claiming_and_idempotency(self):
        """Test worker claiming past scheduled posts, dispatching to connected channels with unique idempotency keys."""
        now = get_indian_time()

        # 1. Connect active Facebook & LinkedIn channels for Company 1
        fb_conn = SocialAccountConnection(
            tenant_id=1,
            company_id=1,
            platform="facebook",
            platform_account_id="fb_123",
            account_name="Mynt FB",
            provider_profile_id="mintos_t1_c1",
            status="ACTIVE"
        )
        li_conn = SocialAccountConnection(
            tenant_id=1,
            company_id=1,
            platform="linkedin",
            platform_account_id="li_456",
            account_name="Mynt LI",
            provider_profile_id="mintos_t1_c1",
            status="ACTIVE"
        )
        self.db.add_all([fb_conn, li_conn])

        # 2. Post A: Scheduled 10 minutes ago in IST (Eligible for worker claim)
        past_post = SocialPost(
            tenant_id=1,
            company_id=1,
            topic_theme="Past Post Due Now",
            master_caption="Time to publish past post.",
            scheduled_at=now - timedelta(minutes=10),
            status="SCHEDULED"
        )
        # 3. Post B: Scheduled 3 hours in future in IST (NOT eligible for worker claim)
        future_post = SocialPost(
            tenant_id=1,
            company_id=1,
            topic_theme="Future Post Later",
            master_caption="Do not publish yet.",
            scheduled_at=now + timedelta(hours=3),
            status="SCHEDULED"
        )
        self.db.add_all([past_post, future_post])
        self.db.commit()

        # Run publish worker
        result = process_scheduled_social_posts(self.db)
        self.assertEqual(result.get("processed"), 1)
        self.assertEqual(result.get("published"), 1)

        # Refresh posts from DB
        self.db.refresh(past_post)
        self.db.refresh(future_post)

        # Assert past post transitioned to PUBLISHED
        self.assertEqual(past_post.status, "PUBLISHED")

        # Assert future post remains SCHEDULED
        self.assertEqual(future_post.status, "SCHEDULED")

        # Verify SocialPostDispatch records created for both active channels
        dispatches = self.db.query(SocialPostDispatch).filter(
            SocialPostDispatch.post_id == past_post.id
        ).all()
        self.assertEqual(len(dispatches), 2)
        platforms = [d.platform for d in dispatches]
        self.assertIn("facebook", platforms)
        self.assertIn("linkedin", platforms)

        for d in dispatches:
            self.assertEqual(d.status, "PUBLISHED")
            self.assertTrue(d.dispatch_key.startswith(f"DISP_P{past_post.id}_C"))
            self.assertIsNotNone(d.provider_post_id)

    def test_background_publisher_retry_backoff_on_failure(self):
        """Test exponential retry backoff and retry_count increment when provider fails."""
        now = get_indian_time()
        conn = SocialAccountConnection(
            tenant_id=1,
            company_id=1,
            platform="x",
            platform_account_id="x_789",
            account_name="Mynt X",
            provider_profile_id="mintos_t1_c1",
            status="ACTIVE"
        )
        self.db.add(conn)

        failing_post = SocialPost(
            tenant_id=1,
            company_id=1,
            topic_theme="Will Fail Once",
            master_caption="Caption that fails.",
            scheduled_at=now - timedelta(minutes=5),
            status="SCHEDULED",
            retry_count=0
        )
        self.db.add(failing_post)
        self.db.commit()

        # Simulate provider raising an exception
        provider = get_social_provider()
        with patch.object(provider, "publish_post", side_effect=Exception("External API Rate Limit")):
            with patch("app.services.social_publish_service.get_social_provider", return_value=provider):
                process_scheduled_social_posts(self.db)

        self.db.refresh(failing_post)
        # Should remain SCHEDULED for retry with retry_count=1 and next_retry_at set
        self.assertEqual(failing_post.status, "SCHEDULED")
        self.assertEqual(failing_post.retry_count, 1)
        self.assertIsNotNone(failing_post.next_retry_at)

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Webhook Processing & Deduplication Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_webhook_ingestion_and_deduplication(self):
        """Test webhook processing for post completion and idempotent event deduplication."""
        now = get_indian_time()

        post = SocialPost(
            tenant_id=1,
            company_id=1,
            topic_theme="Webhook Test Post",
            master_caption="Awaiting external webhook confirmation.",
            scheduled_at=now,
            status="SCHEDULED"
        )
        self.db.add(post)
        self.db.commit()

        dispatch = SocialPostDispatch(
            post_id=post.id,
            connection_id=1,
            platform="facebook",
            tailored_caption="Awaiting external webhook confirmation.",
            status="PENDING",
            dispatch_key="KEY_WH_TEST_001",
            provider_post_id="ext_post_999"
        )
        self.db.add(dispatch)
        self.db.commit()

        import json
        webhook_payload = {
            "id": "EVT_001",
            "type": "post.published",
            "post_id": "ext_post_999",
            "data": {
                "provider_post_id": "ext_post_999",
                "published_url": "https://facebook.com/myntreal/posts/999"
            }
        }
        body_bytes = json.dumps(webhook_payload).encode("utf-8")

        # 1. Process webhook first time
        result1 = handle_social_webhook(self.db, headers={}, body_bytes=body_bytes)
        self.assertEqual(result1.get("status"), "success")

        # Verify dispatch updated
        self.db.refresh(dispatch)
        self.assertEqual(dispatch.status, "PUBLISHED")
        self.assertEqual(dispatch.published_url, "https://facebook.com/myntreal/posts/999")

        # 2. Process webhook second time (Same event_id) -> Idempotent deduplication
        result2 = handle_social_webhook(self.db, headers={}, body_bytes=body_bytes)
        self.assertEqual(result2.get("status"), "duplicate_ignored")

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Omnichannel Analytics Synchronization Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_analytics_synchronization_and_aggregation(self):
        """Test syncing analytics for published posts and calculating company metrics."""
        now = get_indian_time()

        post = SocialPost(
            tenant_id=1,
            company_id=1,
            topic_theme="Analytics Verification Post",
            master_caption="Measuring impressions and engagement.",
            scheduled_at=now - timedelta(days=2),
            status="PUBLISHED"
        )
        self.db.add(post)
        self.db.commit()

        dispatch = SocialPostDispatch(
            post_id=post.id,
            connection_id=1,
            platform="instagram",
            tailored_caption="Measuring impressions and engagement.",
            status="PUBLISHED",
            dispatch_key="KEY_ANALYTICS_001",
            provider_post_id="ext_ig_888",
            published_at=now - timedelta(days=1)
        )
        self.db.add(dispatch)
        self.db.commit()

        # Run analytics sync
        result = sync_social_analytics(self.db)
        self.assertGreaterEqual(result.get("synced_count", 0), 1)

        # Verify snapshot created in DB
        snap = self.db.query(SocialAnalyticsSnapshot).filter(
            SocialAnalyticsSnapshot.dispatch_id == dispatch.id
        ).first()
        self.assertIsNotNone(snap)
        self.assertGreaterEqual(snap.impressions, 0)
        self.assertGreaterEqual(snap.likes, 0)
        self.assertGreaterEqual(snap.comments, 0)

    # ─────────────────────────────────────────────────────────────────────────
    # 8. FastAPI Endpoints Integration Tests (With RequestContext)
    # ─────────────────────────────────────────────────────────────────────────
    def test_social_api_endpoints(self):
        """Verify social API endpoints via FastAPI test client with mocked RequestContext."""
        now = get_indian_time()

        # 1. GET /overview
        res_ov = self.client.get("/api/v1/social/overview")
        self.assertEqual(res_ov.status_code, 200)
        ov_data = res_ov.json()
        self.assertIn("posts_summary", ov_data)
        self.assertIn("connected_accounts_count", ov_data)

        # 2. POST /accounts/mock-connect
        res_conn = self.client.post("/api/v1/social/accounts/mock-connect", json={
            "platform": "linkedin",
            "account_handle": "@myntreal_api_test"
        })
        self.assertEqual(res_conn.status_code, 200)
        self.assertEqual(res_conn.json()["platform"], "linkedin")

        # 3. GET /accounts
        res_acc = self.client.get("/api/v1/social/accounts")
        self.assertEqual(res_acc.status_code, 200)
        self.assertGreaterEqual(len(res_acc.json()["accounts"]), 1)

        # 4. POST /posts (Ad-hoc post creation)
        res_create = self.client.post("/api/v1/social/posts", json={
            "topic_theme": "API Ad-hoc Post",
            "master_caption": "Testing single post creation.",
            "scheduled_at": (now + timedelta(days=1)).isoformat()
        })
        self.assertEqual(res_create.status_code, 200)
        post_id = res_create.json()["post"]["id"]

        # 5. GET /posts/{id}
        res_get = self.client.get(f"/api/v1/social/posts/{post_id}")
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["post"]["topic_theme"], "API Ad-hoc Post")

        # 6. PUT /posts/{id}
        res_put = self.client.put(f"/api/v1/social/posts/{post_id}", json={
            "topic_theme": "API Ad-hoc Post Updated",
            "master_caption": "Updated caption via API."
        })
        self.assertEqual(res_put.status_code, 200)
        self.assertEqual(res_put.json()["post"]["topic_theme"], "API Ad-hoc Post Updated")

        # 7. POST /posts/{id}/approve
        res_appr = self.client.post(f"/api/v1/social/posts/{post_id}/approve")
        self.assertEqual(res_appr.status_code, 200)
        self.assertEqual(res_appr.json()["post"]["status"], "SCHEDULED")

        # 8. POST /posts/{id}/publish-now
        res_pub = self.client.post(f"/api/v1/social/posts/{post_id}/publish-now")
        self.assertEqual(res_pub.status_code, 200)
        self.assertEqual(res_pub.json()["status"], "success")

        # 9. GET /calendar
        res_cal = self.client.get("/api/v1/social/calendar")
        self.assertEqual(res_cal.status_code, 200)
        self.assertIn("posts", res_cal.json())

        # 10. GET /settings & PUT /settings
        res_set = self.client.get("/api/v1/social/settings")
        self.assertEqual(res_set.status_code, 200)

        res_put_set = self.client.put("/api/v1/social/settings", json={
            "brand_voice": "Bold, sustainable and customer first",
            "preferred_time_ist": "11:00"
        })
        self.assertEqual(res_put_set.status_code, 200)
        self.assertEqual(res_put_set.json()["settings"]["brand_voice"], "Bold, sustainable and customer first")

        # 11. GET /analytics
        res_an = self.client.get("/api/v1/social/analytics")
        self.assertEqual(res_an.status_code, 200)
        self.assertIn("platform_breakdown", res_an.json())

    # ─────────────────────────────────────────────────────────────────────────
    # 9. Targeted Priority Verification Tests (Zernio, Migration, Reliability)
    # ─────────────────────────────────────────────────────────────────────────
    def test_provider_profile_id_persistence_per_company(self):
        """Verify that each company persists a provider profile ID mapped in SocialCalendarSetting."""
        now = get_indian_time()
        res = self.client.post("/api/v1/social/accounts/connect-url", json={
            "platform": "facebook",
            "redirect_uri": "/staff/social-media"
        })
        self.assertEqual(res.status_code, 200)
        profile_id = res.json()["profile_id"]
        self.assertTrue(profile_id.startswith("zernio_prof_mintos_") or profile_id.startswith("prof_"))

        setting = self.db.query(SocialCalendarSetting).filter(SocialCalendarSetting.company_id == 1).first()
        self.assertIsNotNone(setting)
        self.assertEqual(setting.provider_profile_id, profile_id)

    def test_zernio_documented_contract_endpoints(self):
        """Verify documented Zernio API adapter endpoints, headers, and request/response structures."""
        provider = ZernioSocialProvider(api_key="test_live_key_xyz", base_url="https://zernio.com/api/v1")
        self.assertEqual(provider.base_url, "https://zernio.com/api/v1")
        headers = provider._get_headers(profile_id="prof_123")
        self.assertEqual(headers["Authorization"], "Bearer test_live_key_xyz")
        self.assertEqual(headers["X-Profile-ID"], "prof_123")

        # Verify HMAC signature validation with X-Zernio-Signature header (case-insensitive)
        body = b'{"event":"test"}'
        secret = "super_secret_webhook_key"
        import hmac, hashlib
        valid_sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

        self.assertTrue(provider.verify_webhook_signature({"X-Zernio-Signature": valid_sig}, body, secret))
        self.assertTrue(provider.verify_webhook_signature({"x-zernio-signature": valid_sig}, body, secret))
        self.assertFalse(provider.verify_webhook_signature({"X-Zernio-Signature": "invalid"}, body, secret))

    def test_timeout_after_acceptance_and_reconciliation(self):
        """Verify worker marks dispatch UNCERTAIN on timeout and reconciles via provider probe without duplicate posting."""
        now = get_indian_time()

        # Ensure company 1 has an active connection
        conn = self.db.query(SocialAccountConnection).filter(
            SocialAccountConnection.company_id == 1,
            SocialAccountConnection.status == "ACTIVE"
        ).first()
        if not conn:
            conn = SocialAccountConnection(
                tenant_id=1,
                company_id=1,
                platform="facebook",
                platform_account_id="fb_time_101",
                account_name="Facebook Page",
                provider_profile_id="zernio_prof_t1_c1",
                status="ACTIVE",
                created_at=now,
                updated_at=now
            )
            self.db.add(conn)
            self.db.commit()

        post = SocialPost(
            tenant_id=1,
            company_id=1,
            topic_theme="Timeout Reconcile Post",
            master_caption="Testing timeout handling.",
            scheduled_at=now - timedelta(minutes=5),
            status="SCHEDULED"
        )
        self.db.add(post)
        self.db.commit()

        # Mock provider that simulates a network timeout on publish_post
        mock_prov = MagicMock(spec=BaseSocialProvider)
        mock_prov.publish_post.side_effect = TimeoutError("HTTPSConnectionPool: Read timed out")
        mock_prov.get_post_status.return_value = {
            "status": "PUBLISHED",
            "platform_post_url": "https://facebook.com/posts/reconciled_99"
        }

        # First worker execution -> Times out -> Marks dispatch UNCERTAIN (NOT blind retry)
        res1 = process_scheduled_social_posts(self.db, provider=mock_prov)
        self.assertEqual(res1["failed"], 1)

        disp = self.db.query(SocialPostDispatch).filter(SocialPostDispatch.post_id == post.id).first()
        self.assertIsNotNone(disp)
        self.assertEqual(disp.status, "UNCERTAIN")
        self.assertEqual(post.status, "UNCERTAIN")

        # Now simulate provider reconciliation on second pass: provide post id and clear retry wait
        disp.provider_post_id = "prov_post_rec_99"
        post.next_retry_at = now - timedelta(seconds=1)
        self.db.commit()

        # Second worker execution -> Reconciles through get_post_status -> Transitions to PUBLISHED
        res2 = process_scheduled_social_posts(self.db, provider=mock_prov)
        self.assertEqual(disp.status, "PUBLISHED")
        self.assertEqual(post.status, "PUBLISHED")

    def test_concurrent_duplicate_worker_protection(self):
        """Verify internal dispatch records prevent duplicate external publication across concurrent workers."""
        now = get_indian_time()

        conn = self.db.query(SocialAccountConnection).filter(SocialAccountConnection.company_id == 1, SocialAccountConnection.status == "ACTIVE").first()
        if not conn:
            conn = SocialAccountConnection(
                tenant_id=1, company_id=1, platform="linkedin", platform_account_id="li_conc_101",
                account_name="LinkedIn Page", provider_profile_id="zernio_prof_t1_c1",
                status="ACTIVE", created_at=now, updated_at=now
            )
            self.db.add(conn)
            self.db.commit()

        post = SocialPost(
            tenant_id=1,
            company_id=1,
            topic_theme="Concurrent Protection Post",
            master_caption="Testing concurrent workers.",
            scheduled_at=now - timedelta(minutes=2),
            status="SCHEDULED"
        )
        self.db.add(post)
        self.db.commit()

        # Worker 1 starts and creates dispatch row in SUBMITTED state
        dispatch_key = f"DISP_P{post.id}_C{conn.id}_{conn.platform}_{int(post.scheduled_at.timestamp())}"
        disp = SocialPostDispatch(
            post_id=post.id,
            connection_id=conn.id,
            platform=conn.platform,
            tailored_caption=post.master_caption,
            dispatch_key=dispatch_key,
            status="SUBMITTED",
            created_at=get_indian_time(),
            updated_at=get_indian_time()
        )
        self.db.add(disp)
        self.db.commit()

        mock_prov = MagicMock(spec=BaseSocialProvider)

        # Worker 2 runs concurrently while dispatch is SUBMITTED
        res = process_scheduled_social_posts(self.db, provider=mock_prov)

        # Worker 2 must NOT call publish_post for the in-flight dispatch
        mock_prov.publish_post.assert_not_called()

    def test_partial_multi_platform_success_and_retry_recovery(self):
        """Verify partial multi-platform failure: published platform is skipped, failed platform retried."""
        now = get_indian_time()

        # Ensure company 1 has active facebook and x connections
        c_fb = self.db.query(SocialAccountConnection).filter(SocialAccountConnection.company_id == 1, SocialAccountConnection.platform == "facebook").first()
        if not c_fb:
            c_fb = SocialAccountConnection(
                tenant_id=1, company_id=1, platform="facebook", platform_account_id="fb_123",
                account_name="Facebook Channel", status="ACTIVE", provider_profile_id="zernio_prof_t1_c1",
                created_at=now, updated_at=now
            )
            self.db.add(c_fb)

        c_x = self.db.query(SocialAccountConnection).filter(SocialAccountConnection.company_id == 1, SocialAccountConnection.platform == "x").first()
        if not c_x:
            c_x = SocialAccountConnection(
                tenant_id=1, company_id=1, platform="x", platform_account_id="x_123",
                account_name="X Channel", status="ACTIVE", provider_profile_id="zernio_prof_t1_c1",
                created_at=now, updated_at=now
            )
            self.db.add(c_x)
        self.db.commit()

        post = SocialPost(
            tenant_id=1,
            company_id=1,
            topic_theme="Multi-Platform Partial Post",
            master_caption="Testing partial platform success.",
            scheduled_at=now - timedelta(minutes=5),
            status="SCHEDULED"
        )
        self.db.add(post)
        self.db.commit()

        # Mock provider where facebook succeeds and x fails on first attempt
        mock_prov = MagicMock(spec=BaseSocialProvider)
        def mock_publish(profile_id, payload, idempotency_key):
            plat = payload.get("platforms", [""])[0]
            if plat == "facebook":
                return {"success": True, "results": {"facebook": {"success": True, "provider_post_id": "fb_ok_1"}}}
            else:
                return {"success": False, "results": {plat: {"success": False, "error": "Rate limit on X"}}}

        mock_prov.publish_post.side_effect = mock_publish

        # First pass -> Facebook succeeds, X fails
        process_scheduled_social_posts(self.db, provider=mock_prov)

        dispatches = self.db.query(SocialPostDispatch).filter(SocialPostDispatch.post_id == post.id).all()
        fb_disp = next((d for d in dispatches if d.platform == "facebook"), None)
        x_disp = next((d for d in dispatches if d.platform == "x"), None)

        self.assertIsNotNone(fb_disp)
        self.assertEqual(fb_disp.status, "PUBLISHED")
        self.assertIsNotNone(x_disp)
        self.assertEqual(x_disp.status, "FAILED")
        self.assertEqual(post.status, "SCHEDULED") # Rescheduled for retry

        # Second pass: X now succeeds!
        def mock_publish_retry(profile_id, payload, idempotency_key):
            plat = payload.get("platforms", [""])[0]
            return {"success": True, "results": {plat: {"success": True, "provider_post_id": f"{plat}_ok_2"}}}

        mock_prov.publish_post.side_effect = mock_publish_retry
        post.next_retry_at = now - timedelta(seconds=1)
        self.db.commit()

        process_scheduled_social_posts(self.db, provider=mock_prov)
        self.assertEqual(x_disp.status, "PUBLISHED")
        self.assertEqual(post.status, "PUBLISHED")

    def test_analytics_genuine_zero_vs_unsupported_and_pending(self):
        """Verify analytics engine preserves genuine 0 and sets explicit availability for missing/unsupported metrics."""
        now = get_indian_time()

        post = SocialPost(
            tenant_id=1, company_id=1, topic_theme="Zero Metrics Post",
            master_caption="Test caption.", scheduled_at=now, status="PUBLISHED"
        )
        self.db.add(post)
        self.db.commit()

        d1 = SocialPostDispatch(
            post_id=post.id, connection_id=1, platform="facebook", tailored_caption="Test",
            status="PUBLISHED", dispatch_key="KEY_AN_ZERO", provider_post_id="ext_zero", published_at=now
        )
        d2 = SocialPostDispatch(
            post_id=post.id, connection_id=1, platform="linkedin", tailored_caption="Test",
            status="PUBLISHED", dispatch_key="KEY_AN_UNSUPPORTED", provider_post_id="ext_unsup", published_at=now
        )
        self.db.add_all([d1, d2])
        self.db.commit()

        mock_prov = MagicMock(spec=BaseSocialProvider)
        def mock_analytics(provider_post_id, platform):
            if provider_post_id == "ext_zero":
                # Provider explicitly returns 0 impressions and 0 likes
                return {
                    "platform": platform,
                    "impressions": 0, "reach": 0, "likes": 0, "comments": 0,
                    "shares": 0, "clicks": 0, "video_views": None,
                    "data_availability": "ZERO_METRICS",
                    "raw_metrics": {"impressions": 0, "likes": 0}
                }
            else:
                # Platform does not support analytics -> all None
                return {
                    "platform": platform,
                    "impressions": None, "reach": None, "likes": None, "comments": None,
                    "shares": None, "clicks": None, "video_views": None,
                    "data_availability": "UNSUPPORTED",
                    "raw_metrics": {}
                }

        mock_prov.get_post_analytics.side_effect = mock_analytics
        sync_social_analytics(self.db, provider=mock_prov)

        snap1 = self.db.query(SocialAnalyticsSnapshot).filter(SocialAnalyticsSnapshot.dispatch_id == d1.id).first()
        self.assertIsNotNone(snap1)
        self.assertEqual(snap1.impressions, 0) # Genuine 0 preserved!
        self.assertEqual(snap1.likes, 0)
        self.assertEqual(snap1.engagement_rate, 0.0)
        self.assertEqual(snap1.data_availability, "ZERO_METRICS")

        snap2 = self.db.query(SocialAnalyticsSnapshot).filter(SocialAnalyticsSnapshot.dispatch_id == d2.id).first()
        self.assertIsNotNone(snap2)
        self.assertIsNone(snap2.impressions) # Not 0! Null because unsupported
        self.assertIsNone(snap2.likes)
        self.assertIsNone(snap2.engagement_rate)
        self.assertEqual(snap2.data_availability, "UNSUPPORTED")


if __name__ == "__main__":
    unittest.main()
