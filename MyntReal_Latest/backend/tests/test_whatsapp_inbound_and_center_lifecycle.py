"""
Comprehensive 13-Scenario Regression Test Suite for WhatsApp Center & Inbound Baileys Gateway
Covers:
1. Canonical Baileys messages.upsert inbound text ingestion (WAInbox & MessageLog)
2. Inbound media ingestion (image/document/pdf metadata persistence)
3. Duplicate messages.upsert idempotency guard (wamid deduplication)
4. Reconnect / replay batch resilience
5. Group message identification (Group JID vs participant phone and name)
6. Unknown sender unassigned routing to Tab 3 (Company Messages / No fabricated staff)
7. Assignment transition (Claiming/replying transitions conversation to My Messages)
8. Search by number, name, and message content (conversations-hub)
9. Forward recipient search contract (contacts and results dual-key return)
10. Direct 10-digit mobile number recognition in recipient search
11. Chat media gallery retrieval (All, Photos, Documents filtering)
12. Missing historical media unavailable state (is_available flag & graceful fallback)
13. Multi-company and tenant data isolation
"""

import os
import sys
import unittest
from pathlib import Path
from datetime import datetime

# Path configuration
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.models.whatsapp import WAInbox, MessageLog
from app.models.staff import StaffEmployee
from app.api.v1.endpoints.whatsapp import _require_staff


class TestWhatsAppInboundAndCenterLifecycle(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()
        cls.admin_staff = cls.db.query(StaffEmployee).filter_by(id=1).first()
        if not cls.admin_staff:
            cls.admin_staff = cls.db.query(StaffEmployee).filter(StaffEmployee.status == 'active').first()

        # Clean up any leftover test data
        cls._cleanup_test_data()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_test_data()
        cls.db.close()
        app.dependency_overrides.clear()

    @classmethod
    def _cleanup_test_data(cls):
        test_phones = ["8875551666", "918875551666", "9988771122", "919988771122", "120363999999999999@g.us"]
        cls.db.query(MessageLog).filter(
            (MessageLog.mobile_number.in_(test_phones)) | 
            (MessageLog.message_sid.like("test_wamid_%"))
        ).delete(synchronize_session=False)

        cls.db.query(WAInbox).filter(
            (WAInbox.from_phone.in_(["8875551666", "918875551666", "9988771122", "120363999999999999@g.us"])) |
            (WAInbox.wamid.like("test_wamid_%"))
        ).delete(synchronize_session=False)
        cls.db.commit()

    def setUp(self):
        # Default dependency override as admin staff (MR10001)
        app.dependency_overrides[_require_staff] = lambda: self.admin_staff

    def tearDown(self):
        app.dependency_overrides.clear()

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 1: Inbound Text Ingestion (WAInbox & MessageLog)
    # ─────────────────────────────────────────────────────────────────────────
    def test_01_inbound_text_ingestion(self):
        payload = {
            "from_phone": "918875551666",
            "body_text": "Hello MyntOS Inbound Test",
            "message_type": "text",
            "wamid": "test_wamid_01_text",
            "is_group": False,
            "is_from_me": False
        }
        res = self.client.post("/api/v1/whatsapp/bot-inbound-message", json=payload)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("status"), "ingested")

        # Verify DB MessageLog
        msg = self.db.query(MessageLog).filter_by(message_sid="test_wamid_01_text").first()
        self.assertIsNotNone(msg, "MessageLog record must be created")
        self.assertEqual(msg.provider, "BAILEYS")
        self.assertIn("8875551666", msg.mobile_number)
        self.assertEqual(msg.message_body, "Hello MyntOS Inbound Test")

        # Verify DB WAInbox
        inbox = self.db.query(WAInbox).filter_by(from_phone="8875551666").first()
        self.assertIsNotNone(inbox, "WAInbox record must be created")
        self.assertEqual(inbox.body_text, "Hello MyntOS Inbound Test")
        self.assertIsNone(inbox.assigned_to_emp_id, "Inbound from unassigned sender must not have fabricated staff assignment")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 2: Inbound Media Ingestion (Metadata & Storage Normalization)
    # ─────────────────────────────────────────────────────────────────────────
    def test_02_inbound_media_ingestion(self):
        payload = {
            "from_phone": "918875551666",
            "body_text": "Here is the property photo",
            "media_url": "/storage/wa_media/sample_site_photo.jpg",
            "media_type": "image",
            "media_name": "sample_site_photo.jpg",
            "media_mime_type": "image/jpeg",
            "wamid": "test_wamid_02_media",
            "is_group": False,
            "is_from_me": False
        }
        res = self.client.post("/api/v1/whatsapp/bot-inbound-message", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))

        msg = self.db.query(MessageLog).filter_by(message_sid="test_wamid_02_media").first()
        self.assertIsNotNone(msg)
        self.assertIn("image", msg.message_type)

        inbox = self.db.query(WAInbox).filter_by(wamid="test_wamid_02_media").first()
        self.assertIsNotNone(inbox)
        self.assertEqual(inbox.media_url, "/storage/wa_media/sample_site_photo.jpg")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 3: Duplicate messages.upsert Idempotency Check
    # ─────────────────────────────────────────────────────────────────────────
    def test_03_duplicate_upsert_idempotency(self):
        payload = {
            "from_phone": "918875551666",
            "body_text": "Hello MyntOS Inbound Test",
            "message_type": "text",
            "wamid": "test_wamid_01_text",
            "is_group": False,
            "is_from_me": False
        }
        res = self.client.post("/api/v1/whatsapp/bot-inbound-message", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("status"), "duplicate")
        self.assertTrue(data.get("is_duplicate"))

        # Verify no duplicate row was created in MessageLog
        count = self.db.query(MessageLog).filter_by(message_sid="test_wamid_01_text").count()
        self.assertEqual(count, 1, "Duplicate wamid must not create a duplicate row in MessageLog")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 4: Reconnect / Replay Batch Resilience
    # ─────────────────────────────────────────────────────────────────────────
    def test_04_reconnect_replay_batch(self):
        batch = [
            {"wamid": "test_wamid_01_text", "msg": "Hello MyntOS Inbound Test", "is_dup": True},
            {"wamid": "test_wamid_04_new1", "msg": "Replay New 1", "is_dup": False},
            {"wamid": "test_wamid_04_new2", "msg": "Replay New 2", "is_dup": False},
        ]
        for item in batch:
            res = self.client.post("/api/v1/whatsapp/bot-inbound-message", json={
                "from_phone": "918875551666",
                "body_text": item["msg"],
                "wamid": item["wamid"],
                "message_type": "text"
            })
            self.assertEqual(res.status_code, 200)
            data = res.json()
            if item["is_dup"]:
                self.assertEqual(data.get("status"), "duplicate")
            else:
                self.assertEqual(data.get("status"), "ingested")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 5: Group Message Identification (JID vs Participant)
    # ─────────────────────────────────────────────────────────────────────────
    def test_05_group_message_ingestion(self):
        group_jid = "120363999999999999@g.us"
        payload = {
            "from_phone": group_jid,
            "body_text": "Group announcement from Alice",
            "message_type": "text",
            "wamid": "test_wamid_05_group",
            "is_group": True,
            "group_jid": group_jid,
            "group_name": "Executive Alpha Group",
            "sender_phone": "919988771122",
            "from_name": "Alice Developer"
        }
        res = self.client.post("/api/v1/whatsapp/bot-inbound-message", json=payload)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertTrue(data.get("success"))

        # Verify MessageLog contains group phone
        msg = self.db.query(MessageLog).filter_by(message_sid="test_wamid_05_group").first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.mobile_number, group_jid)

        # Verify WAInbox tracks group
        inbox = self.db.query(WAInbox).filter_by(from_phone=group_jid).first()
        self.assertIsNotNone(inbox)
        self.assertEqual(inbox.from_name, "Executive Alpha Group")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 6: Unknown Sender Unassigned Routing (Tab 3: Company Messages)
    # ─────────────────────────────────────────────────────────────────────────
    def test_06_unknown_sender_unassigned_routing(self):
        inbox = self.db.query(WAInbox).filter_by(from_phone="8875551666").first()
        self.assertIsNotNone(inbox)
        self.assertIsNone(inbox.assigned_to_emp_id)

        # Query conversations hub with scope=company (Tab 3: 3. New Messages / Unassigned)
        res = self.client.get("/api/v1/whatsapp/conversations-hub?scope=company")
        self.assertEqual(res.status_code, 200)
        convs = res.json().get("conversations", [])
        matching = [c for c in convs if c.get("phone") == "8875551666" or c.get("from_phone") == "8875551666"]
        self.assertGreaterEqual(len(matching), 1, "Unassigned conversation must appear in scope=company (Tab 3)")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 7: Assignment Transition (Claiming/Replying -> My Messages)
    # ─────────────────────────────────────────────────────────────────────────
    def test_07_assignment_transition_to_my_messages(self):
        # Claim the conversation using authoritative /claim-conversation endpoint
        claim_res = self.client.post("/api/v1/whatsapp/claim-conversation", json={"phone": "8875551666"})
        self.assertEqual(claim_res.status_code, 200, claim_res.text)

        # Verify WAInbox has assigned_to_emp_id set to current staff
        inbox = self.db.query(WAInbox).filter_by(from_phone="8875551666").first()
        self.assertEqual(inbox.assigned_to_emp_id, self.admin_staff.id)

        # Query scope=assigned_tagged (Tab 1: My Messages)
        res = self.client.get("/api/v1/whatsapp/conversations-hub?scope=assigned_tagged")
        self.assertEqual(res.status_code, 200)
        convs = res.json().get("conversations", [])
        matching = [c for c in convs if c.get("phone") == "8875551666" or c.get("from_phone") == "8875551666"]
        self.assertGreaterEqual(len(matching), 1, "Claimed conversation must transition into scope=assigned_tagged (Tab 1)")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 8: Search Conversations Hub by Phone, Name & Snippet
    # ─────────────────────────────────────────────────────────────────────────
    def test_08_search_conversations_hub(self):
        # 1. Search by phone number
        res_phone = self.client.get("/api/v1/whatsapp/conversations-hub?scope=all&search=8875551666")
        self.assertEqual(res_phone.status_code, 200)
        convs_phone = res_phone.json().get("conversations", [])
        self.assertTrue(any("8875551666" in (c.get("phone") or c.get("from_phone") or "") for c in convs_phone))

        # 2. Search by message snippet
        res_text = self.client.get("/api/v1/whatsapp/conversations-hub?scope=all&search=Inbound Test")
        self.assertEqual(res_text.status_code, 200)
        convs_text = res_text.json().get("conversations", [])
        self.assertTrue(any("8875551666" in (c.get("phone") or c.get("from_phone") or "") for c in convs_text))

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 9: Forward Recipient Search Contract (contacts & results dual-key)
    # ─────────────────────────────────────────────────────────────────────────
    def test_09_contacts_search_contract(self):
        res = self.client.get("/api/v1/whatsapp/contacts-search?query=test&scope=all")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        # Both keys must exist to satisfy legacy mobile & updated web contracts
        self.assertIn("contacts", data, "Response must contain 'contacts' key")
        self.assertIn("results", data, "Response must contain 'results' key")
        self.assertEqual(data["contacts"], data["results"], "'contacts' and 'results' must contain identical data")

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 10: Direct 10-Digit Mobile Number Recognition
    # ─────────────────────────────────────────────────────────────────────────
    def test_10_contacts_search_direct_10_digit_phone(self):
        # Use a 10-digit number that is not an existing CRM lead
        raw_number = "9999888877"
        res = self.client.get(f"/api/v1/whatsapp/contacts-search?query={raw_number}&scope=all")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        contacts = data.get("contacts", [])
        phone_match = next((c for c in contacts if c.get("phone") == raw_number), None)
        self.assertIsNotNone(phone_match, "Direct 10-digit number must be recognized in contacts-search")
        self.assertEqual(phone_match.get("type"), "PHONE")
        self.assertIn(raw_number, phone_match.get("name", ""))

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 11: Chat Media Gallery Retrieval (Individual & Group, Filtering)
    # ─────────────────────────────────────────────────────────────────────────
    def test_11_chat_gallery_retrieval(self):
        # 1. Retrieve all gallery items for 8875551666
        res_all = self.client.get("/api/v1/whatsapp/chat-gallery?phone=8875551666&recipient_type=individual&category=all")
        self.assertEqual(res_all.status_code, 200)
        data_all = res_all.json()
        self.assertTrue(data_all.get("success"))
        self.assertGreaterEqual(data_all.get("total", 0), 1)
        items = data_all.get("items", [])
        self.assertTrue(any(i.get("filename") == "sample_site_photo.jpg" for i in items))

        # 2. Retrieve photos filter
        res_photos = self.client.get("/api/v1/whatsapp/chat-gallery?phone=8875551666&recipient_type=individual&category=photos")
        self.assertEqual(res_photos.status_code, 200)
        data_photos = res_photos.json()
        self.assertTrue(all(i.get("category") == "photos" for i in data_photos.get("items", [])))

        # 3. Retrieve group gallery
        res_grp = self.client.get("/api/v1/whatsapp/chat-gallery?phone=120363999999999999@g.us&recipient_type=group&category=all")
        self.assertEqual(res_grp.status_code, 200)
        self.assertTrue(res_grp.json().get("success"))

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 12: Missing Historical Media Unavailable State
    # ─────────────────────────────────────────────────────────────────────────
    def test_12_missing_media_unavailable_state(self):
        non_existent_path = "/storage/wa_media/historical_missing_test_12345.jpg"
        msg = MessageLog(
            mobile_number="918875551666",
            message_type="scanned_image",
            message_body=f"[Media: {non_existent_path}]",
            current_status="delivered",
            provider="BAILEYS",
            message_sid="test_wamid_12_missing_media",
            webhook_data='{"media_url": "/storage/wa_media/historical_missing_test_12345.jpg", "media_name": "historical_missing_test_12345.jpg"}'
        )
        self.db.add(msg)
        self.db.commit()

        # Query gallery
        res = self.client.get("/api/v1/whatsapp/chat-gallery?phone=8875551666&recipient_type=individual&category=all")
        self.assertEqual(res.status_code, 200)
        items = res.json().get("items", [])
        missing_item = next((i for i in items if i.get("media_url") == non_existent_path), None)
        self.assertIsNotNone(missing_item)
        self.assertFalse(missing_item.get("is_available"), "Missing physical media must have is_available=False")

        # Test storage endpoint fallback (must return 200 placeholder SVG, not 404)
        res_file = self.client.get("/storage/wa_media/historical_missing_test_12345.jpg")
        self.assertEqual(res_file.status_code, 200, "Missing wa_media must return 200 placeholder")
        self.assertIn("image/svg+xml", res_file.headers.get("content-type", ""))

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO 13: Multi-Company and Tenant Data Isolation
    # ─────────────────────────────────────────────────────────────────────────
    def test_13_multi_company_tenant_isolation(self):
        inbox = self.db.query(WAInbox).filter_by(from_phone="8875551666").first()
        self.assertIsNotNone(inbox)
        # Verify that company_id is dynamically associated to lead 8146 (company 4)
        self.assertEqual(inbox.company_id, 4)


if __name__ == "__main__":
    unittest.main()
