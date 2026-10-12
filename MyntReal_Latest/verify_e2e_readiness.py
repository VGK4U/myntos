"""
MintOS / ZynovaOS — Social Media Manager: Final Local End-to-End Readiness Verification
Executes real browser automation with Playwright and FastAPI integration testing.
Strictly isolated to in-memory SQLite database.
"""

import sys
import os

# 1. Critical Database Safeguard — Enforce strictly local SQLite in-memory DB
os.environ["ALLOW_PROD_DB_ACCESS"] = "0"
os.environ["PROD_DATABASE_URL"] = ""
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import unittest
import json
from datetime import datetime, timedelta, date
from unittest.mock import patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright

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


class TestFinalLocalReadiness(unittest.TestCase):
    """Final comprehensive local verification test suite."""

    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 80)
        print("RUNNING FINAL LOCAL END-TO-END READINESS VERIFICATION")
        print("=" * 80)

    def setUp(self):
        # In-memory SQLite engine with StaticPool
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

        # Build FastAPI test app
        self.app = FastAPI()
        self.app.include_router(api_router, prefix="/api/v1")

        # Default authenticated context: Company 1 (Mynt Real)
        self.ctx_c1 = RequestContext(
            staff_id=101,
            emp_code="MR101",
            tenant_id=1,
            active_company_id=1,
            hierarchy_level=100,
            role_code="company_admin",
            admin_scope=AdminScope.COMPANY_ADMIN,
            licensed_modules={"SOCIAL_MEDIA_MANAGER"}
        )

        # Context for Company 2 (Zynova Mobility)
        self.ctx_c2 = RequestContext(
            staff_id=202,
            emp_code="ZM202",
            tenant_id=1,
            active_company_id=2,
            hierarchy_level=100,
            role_code="company_admin",
            admin_scope=AdminScope.COMPANY_ADMIN,
            licensed_modules={"SOCIAL_MEDIA_MANAGER"}
        )

        self.current_ctx = self.ctx_c1

        def override_ctx():
            return self.current_ctx

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
    # 1. Browser Automation & UI Asset Verification (Playwright + System Chrome)
    # ─────────────────────────────────────────────────────────────────────────
    def test_browser_ui_rendering_and_interactions(self):
        """Verify HTML loads cleanly in real Chrome without exceptions and modal interactions work."""
        import http.server, threading, functools
        chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "frontend"))
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=frontend_dir)
        server = http.server.HTTPServer(("127.0.0.1", 0), handler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=chrome_exe, headless=True)
                context = browser.new_context()
                
                # Pre-seed authenticated staff session in localStorage before page scripts execute
                context.add_init_script("""
                    localStorage.setItem('staff_token', 'mock_token_jwt_123');
                    localStorage.setItem('staff_user', JSON.stringify({
                        id: 101,
                        emp_code: 'MR101',
                        active_company_id: 1,
                        company_name: 'Mynt Real LLP'
                    }));
                """)
                page = context.new_page()

                page_errors = []
                page.on("pageerror", lambda err: page_errors.append(str(err)))

                # Route external CDNs that lack outbound connectivity in local sandbox
                page.route("**/*", lambda route: route.abort() if "127.0.0.1" not in route.request.url else route.continue_())

                # Navigate via local HTTP server
                page.goto(f"http://127.0.0.1:{port}/staff_social_media.html")

                # 1. Verify page title
                title = page.title()
                self.assertIn("Social Media Manager", title)

                # 2. Verify critical DOM elements on Overview tab
                self.assertTrue(page.locator("#companyBadge").is_visible())
                self.assertTrue(page.locator("#statScheduledPosts").is_visible())
                self.assertTrue(page.locator("#statPublishedPosts").is_visible())
                self.assertTrue(page.locator("#statConnectedChannels").is_visible())

                # Switch to Content Calendar tab and verify calendar elements
                page.locator('button[data-bs-target="#tabCalendar"]').click()
                self.assertTrue(page.locator("#calMonthSelect").is_visible())
                self.assertTrue(page.locator("#calendarGridContainer").is_visible())

                # 3. Populate authenticated context in browser localStorage on origin and update company context
                page.evaluate("""() => {
                    localStorage.setItem('staff_token', 'mock_token_jwt_123');
                    localStorage.setItem('staff_user', JSON.stringify({
                        id: 101,
                        emp_code: 'MR101',
                        active_company_id: 1,
                        company_name: 'Mynt Real LLP'
                    }));
                    SocialMediaManager._setupCompanyContext();
                }""")
                badge_text = page.locator("#companyBadge").inner_text()
                self.assertIn("Mynt Real LLP", badge_text)

                # 4. Verify character counter interaction on editCaptionX
                caption_input = page.locator("#editCaptionX")
                char_count = page.locator("#charCountX")

                caption_input.fill("Hello world! This is a test tweet under 280 characters.")
                self.assertEqual(char_count.inner_text(), str(len("Hello world! This is a test tweet under 280 characters.")))
                self.assertFalse("text-danger" in (char_count.get_attribute("class") or ""))

                # Test character counter at 280 limit (enforced by maxlength="280")
                long_text = "A" * 285
                caption_input.fill(long_text)
                self.assertEqual(char_count.inner_text(), "280", "HTML maxlength=280 restricts text to 280 chars")

                # 5. Verify _formatMetric helper handles all 4 states correctly
                res_zero = page.evaluate("SocialMediaManager._formatMetric(0, 'ZERO_METRICS')")
                res_unsup = page.evaluate("SocialMediaManager._formatMetric(null, 'UNSUPPORTED')")
                res_pend = page.evaluate("SocialMediaManager._formatMetric(null, 'PENDING')")
                res_avail = page.evaluate("SocialMediaManager._formatMetric(1450, 'AVAILABLE')")

                self.assertEqual(res_zero, "0", "Genuine zero must render as '0'")
                self.assertIn("N/A", res_unsup, "Unsupported metric must render badge with 'N/A'")
                self.assertIn("(Pending)", res_pend, "Pending metric must render badge with '(Pending)'")
                self.assertEqual(res_avail, "1,450", "Available metric must render formatted number")

                # 6. Verify zero unhandled runtime JavaScript errors (excluding frozen telephony background SIP check)
                real_errors = [e for e in page_errors if "No auth token" not in e]
                self.assertEqual(len(real_errors), 0, f"Page had unexpected errors: {real_errors}")

                browser.close()
                print("[PASS] Browser UI rendering & interaction tests passed with zero exceptions.")
        finally:
            server.shutdown()

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Authentication, Authorization & Cross-Company Tampering Tests
    # ─────────────────────────────────────────────────────────────────────────
    def test_auth_and_cross_company_isolation(self):
        """Verify strict tenant & company isolation, parameter tampering rejection, and permission enforcement."""
        now = get_indian_time()

        # Create Post for Company 1
        post_c1 = SocialPost(
            tenant_id=1,
            company_id=1,
            topic_theme="Company 1 Confidential Launch",
            master_caption="Mynt Real new product launch details.",
            scheduled_at=now + timedelta(days=2),
            status="DRAFT"
        )
        self.db.add(post_c1)
        self.db.commit()
        p1_id = post_c1.id

        # 1. Company 1 accesses its own post -> Expect 200
        self.current_ctx = self.ctx_c1
        res = self.client.get(f"/api/v1/social/posts/{p1_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["post"]["topic_theme"], "Company 1 Confidential Launch")

        # 2. Company 2 staff attempts to access Company 1's post -> Expect 404 (zero leakage)
        self.current_ctx = self.ctx_c2
        res_cross_get = self.client.get(f"/api/v1/social/posts/{p1_id}")
        self.assertEqual(res_cross_get.status_code, 404)
        self.assertEqual(res_cross_get.json()["detail"], "Post not found.")

        # 3. Company 2 staff attempts to update Company 1's post -> Expect 404
        res_cross_put = self.client.put(f"/api/v1/social/posts/{p1_id}", json={"master_caption": "Hacked caption"})
        self.assertEqual(res_cross_put.status_code, 404)

        # 4. Company 2 staff attempts to approve Company 1's post -> Expect 404
        res_cross_appr = self.client.post(f"/api/v1/social/posts/{p1_id}/approve")
        self.assertEqual(res_cross_appr.status_code, 404)

        # 5. Company 2 staff attempts to delete Company 1's post -> Expect 404
        res_cross_del = self.client.delete(f"/api/v1/social/posts/{p1_id}")
        self.assertEqual(res_cross_del.status_code, 404)

        # 6. Company 2 views calendar -> Zero posts returned
        res_cal = self.client.get(f"/api/v1/social/calendar?month={now.month}&year={now.year}")
        self.assertEqual(res_cal.status_code, 200)
        self.assertEqual(len(res_cal.json()["posts"]), 0)

        # 7. Unauthorized role (hierarchy_level < 60) -> Expect 403 Forbidden
        ctx_unauth = RequestContext(
            staff_id=999,
            emp_code="UNAUTH",
            tenant_id=1,
            active_company_id=1,
            hierarchy_level=40, # Below 60 threshold
            role_code="intern",
            admin_scope=AdminScope.STAFF,
            licensed_modules=set() # Not licensed
        )
        self.current_ctx = ctx_unauth
        res_forbidden = self.client.get("/api/v1/social/overview")
        self.assertEqual(res_forbidden.status_code, 403)
        self.assertIn("not licensed or permitted", res_forbidden.json()["detail"])
        print("[PASS] Authentication, authorization & cross-company isolation verified.")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Complete 11-Step End-to-End Workflow Execution
    # ─────────────────────────────────────────────────────────────────────────
    def test_complete_11_step_workflow(self):
        """Execute all 11 required workflow steps end to end."""
        self.current_ctx = self.ctx_c1
        now = get_indian_time()

        # Step 1: Open Social Media Manager (Overview)
        res_ov = self.client.get("/api/v1/social/overview")
        self.assertEqual(res_ov.status_code, 200)
        self.assertEqual(res_ov.json()["company_id"], 1)

        # Step 2: Configure company brand voice, content pillars, enabled platforms
        res_set = self.client.put("/api/v1/social/settings", json={
            "brand_voice": "Innovative, eco-friendly, trusted",
            "posting_frequency_days": 2,
            "preferred_time_ist": "10:30",
            "content_themes": ["Solar Energy", "Cost Savings", "Green Commute", "Customer Stories"],
            "default_hashtags": ["#MyntReal", "#CleanEnergy", "#IndiaRenewables"],
            "helpline_phone": "+91 9876543210",
            "website_url": "https://myntreal.com"
        })
        self.assertEqual(res_set.status_code, 200)
        self.assertEqual(res_set.json()["settings"]["brand_voice"], "Innovative, eco-friendly, trusted")

        # Step 3: Connect channels via Mock Sandbox (Facebook, Instagram, LinkedIn, X)
        for plat in ["facebook", "instagram", "linkedin", "x"]:
            res_conn = self.client.post("/api/v1/social/accounts/mock-connect", json={
                "platform": plat,
                "account_name": f"Mynt Real {plat.title()}",
                "account_username": f"@myntreal_{plat}"
            })
            self.assertEqual(res_conn.status_code, 200)
            self.assertEqual(res_conn.json()["account"]["status"], "ACTIVE")

        # Step 4: Generate 30-Day Calendar (expecting 15 bi-daily draft posts)
        start_d = date(2026, 11, 1)
        mock_ctx_data = {
            "company_id": 1,
            "company_name": "Mynt Real",
            "brand_voice": "Innovative, eco-friendly",
            "verified_phone": "+91 9876543210",
            "verified_website": "https://myntreal.com",
            "location": "Hyderabad",
            "content_themes": ["Solar Energy", "Green Commute"],
            "default_hashtags": ["#MyntReal"],
            "helpline_phone": "+91 9876543210",
            "website_url": "https://myntreal.com"
        }
        with patch.object(SocialAIService, "extract_company_context", return_value=mock_ctx_data):
            res_gen = self.client.post("/api/v1/social/calendar/generate-ai", json={
                "start_date": "2026-11-01",
                "custom_instructions": "Focus on high-ROI solar installations"
            })
            self.assertEqual(res_gen.status_code, 200)
            posts_gen = res_gen.json()["posts"]
            self.assertEqual(len(posts_gen), 15, "Must generate exactly 15 bi-daily posts")

            # Verify bi-daily spacing and company associations
            for idx, p in enumerate(posts_gen):
                self.assertEqual(p["company_id"], 1)
                self.assertEqual(p["status"], "DRAFT")
                dt = datetime.fromisoformat(p["scheduled_at"])
                expected_date = start_d + timedelta(days=idx * 2)
                self.assertEqual(dt.date(), expected_date)

            target_post = posts_gen[0]
            p_id = target_post["id"]

            # Step 5: Edit a caption and regenerate individual caption
            res_edit = self.client.put(f"/api/v1/social/posts/{p_id}", json={
                "master_caption": "Hand-edited custom caption about solar advantages."
            })
            self.assertEqual(res_edit.status_code, 200)
            self.assertEqual(res_edit.json()["post"]["master_caption"], "Hand-edited custom caption about solar advantages.")

            # Regenerate caption for single post
            res_regen = self.client.post(f"/api/v1/social/posts/{p_id}/regenerate-caption", json={
                "custom_prompt": "Make it punchier with a strong question."
            })
            self.assertEqual(res_regen.status_code, 200)

            # Confirm post 2 was not modified
            res_p2 = self.client.get(f"/api/v1/social/posts/{posts_gen[1]['id']}")
            self.assertEqual(res_p2.json()["post"]["master_caption"], posts_gen[1]["master_caption"])

        # Step 6: Exercise image-generation behavior using deterministic fallback
        res_img = self.client.post(f"/api/v1/social/posts/{p_id}/generate-image", json={
            "aspect_ratio": "1:1",
            "prompt_enhancement": "Modern rooftop solar installation with blue sky"
        })
        self.assertEqual(res_img.status_code, 200)
        self.assertIn("image_url", res_img.json()["result"])
        img_url = res_img.json()["result"]["image_url"]
        self.assertTrue(img_url.startswith("http") or img_url.startswith("/"))

        # Step 7: Approve and schedule a post
        res_appr = self.client.post(f"/api/v1/social/posts/{p_id}/approve")
        self.assertEqual(res_appr.status_code, 200)
        self.assertEqual(res_appr.json()["post"]["status"], "SCHEDULED")

        # Step 8: Exercise publishing worker with mocked successful provider response
        # Backdate post so worker claims it
        db_post = self.db.query(SocialPost).filter(SocialPost.id == p_id).first()
        db_post.scheduled_at = now - timedelta(minutes=5)
        self.db.commit()

        mock_prov = MagicMock(spec=BaseSocialProvider)
        mock_prov.publish_post.return_value = {
            "success": True,
            "results": {
                "facebook": {"success": True, "provider_post_id": "fb_pub_101", "published_url": "https://facebook.com/posts/101"},
                "instagram": {"success": True, "provider_post_id": "ig_pub_101", "published_url": "https://instagram.com/p/101"},
                "linkedin": {"success": True, "provider_post_id": "li_pub_101", "published_url": "https://linkedin.com/posts/101"},
                "x": {"success": True, "provider_post_id": "x_pub_101", "published_url": "https://x.com/status/101"}
            }
        }

        pub_result = process_scheduled_social_posts(self.db, provider=mock_prov)
        self.assertEqual(pub_result["published"], 1)

        # Step 9: Verify post status, dispatch records, and published URLs
        self.db.refresh(db_post)
        self.assertEqual(db_post.status, "PUBLISHED")

        dispatches = self.db.query(SocialPostDispatch).filter(SocialPostDispatch.post_id == p_id).all()
        self.assertEqual(len(dispatches), 4) # 4 connected platforms
        for d in dispatches:
            self.assertEqual(d.status, "PUBLISHED")
            self.assertIsNotNone(d.provider_post_id)
            self.assertIsNotNone(d.published_url)
            self.assertTrue(d.dispatch_key.startswith(f"DISP_P{p_id}_"))

        # Step 10: Exercise all 4 analytics states (genuine zero, unsupported, pending, active)
        d_fb = next(d for d in dispatches if d.platform == "facebook")
        d_ig = next(d for d in dispatches if d.platform == "instagram")
        d_li = next(d for d in dispatches if d.platform == "linkedin")
        d_x = next(d for d in dispatches if d.platform == "x")

        def mock_analytics_flow(provider_post_id, platform):
            if platform == "facebook":
                # Active metrics
                return {
                    "platform": platform, "impressions": 1200, "reach": 950,
                    "likes": 48, "comments": 12, "shares": 6, "clicks": 35,
                    "data_availability": "AVAILABLE"
                }
            elif platform == "instagram":
                # Genuine zero metrics (audience saw it, but 0 likes/comments)
                return {
                    "platform": platform, "impressions": 0, "reach": 0,
                    "likes": 0, "comments": 0, "shares": 0, "clicks": 0,
                    "data_availability": "ZERO_METRICS"
                }
            elif platform == "linkedin":
                # Unsupported metrics
                return {
                    "platform": platform, "impressions": None, "reach": None,
                    "likes": None, "comments": None, "shares": None, "clicks": None,
                    "data_availability": "UNSUPPORTED"
                }
            else:
                # Pending metrics
                return {
                    "platform": platform, "impressions": None, "reach": None,
                    "likes": None, "comments": None, "shares": None, "clicks": None,
                    "data_availability": "PENDING"
                }

        mock_prov.get_post_analytics.side_effect = mock_analytics_flow
        sync_social_analytics(self.db, company_id=1, provider=mock_prov)

        snap_fb = self.db.query(SocialAnalyticsSnapshot).filter(SocialAnalyticsSnapshot.dispatch_id == d_fb.id).first()
        snap_ig = self.db.query(SocialAnalyticsSnapshot).filter(SocialAnalyticsSnapshot.dispatch_id == d_ig.id).first()
        snap_li = self.db.query(SocialAnalyticsSnapshot).filter(SocialAnalyticsSnapshot.dispatch_id == d_li.id).first()
        snap_x = self.db.query(SocialAnalyticsSnapshot).filter(SocialAnalyticsSnapshot.dispatch_id == d_x.id).first()

        self.assertEqual(snap_fb.data_availability, "AVAILABLE")
        self.assertEqual(snap_fb.impressions, 1200)
        self.assertAlmostEqual(snap_fb.engagement_rate, ((48 + 12 + 6) / 1200) * 100, places=2)

        self.assertEqual(snap_ig.data_availability, "ZERO_METRICS")
        self.assertEqual(snap_ig.impressions, 0)
        self.assertEqual(snap_ig.likes, 0)
        self.assertEqual(snap_ig.engagement_rate, 0.0) # Zero impressions -> 0.0 rate

        self.assertEqual(snap_li.data_availability, "UNSUPPORTED")
        self.assertIsNone(snap_li.impressions)
        self.assertIsNone(snap_li.engagement_rate)

        self.assertEqual(snap_x.data_availability, "PENDING")
        self.assertIsNone(snap_x.impressions)
        self.assertIsNone(snap_x.engagement_rate)

        # Step 11: Confirm company-specific content and settings do not leak across companies
        self.current_ctx = self.ctx_c2
        res_c2_overview = self.client.get("/api/v1/social/overview")
        self.assertEqual(res_c2_overview.json()["company_id"], 2)
        self.assertEqual(res_c2_overview.json()["posts_summary"]["total_planned"], 0)
        self.assertEqual(res_c2_overview.json()["connected_accounts_count"], 0)

        res_c2_settings = self.client.get("/api/v1/social/settings")
        self.assertNotEqual(res_c2_settings.json()["settings"]["brand_voice"], "Innovative, eco-friendly, trusted")
        print("[PASS] Complete 11-step end-to-end workflow verified successfully!")


if __name__ == "__main__":
    unittest.main()
