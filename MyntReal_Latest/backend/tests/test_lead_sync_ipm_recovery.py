"""
Regression & Invariant Test Suite: Lead Sync & IPM Recovery Pipeline
DC Protocol Sep 2026: Validates atomic ingestion, source ID normalization,
fail-closed template validation, fallback mechanisms, idempotency, and failure logging.

Test Coverage:
1. test_01_ingest_lead_atomic_creates_lead_and_attribution
2. test_02_ingest_lead_atomic_triggers_welcome_ipm
3. test_03_ingest_lead_atomic_triggers_group_alert
4. test_04_process_facebook_lead_routes_through_ingest_atomic
5. test_05_idempotency_duplicate_lead_skipped
6. test_06_idempotency_concurrent_integrity_error_recovery
7. test_07_source_id_normalization_lead_already_exists
8. test_08_sheets_normalization_row_to_crm_lead
9. test_09_sheets_duplicate_check_is_duplicate
10. test_10_unapproved_template_fail_closed
11. test_11_template_fallback_to_approved_thankyou_general
12. test_12_failure_logging_without_exception
"""

import unittest
import time
import json
import re
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from app.core.database import SessionLocal
from app.models.crm import CRMLead
from app.models.meta_attribution import MetaLeadsAttribution
from app.models.whatsapp import MessageLog, WAInbox, WhatsAppTemplate
from app.services.facebook_leads_service import facebook_leads_service
from app.services.sheets_leads_service import row_to_crm_lead, is_duplicate, COL_MAP
from app.services.whatsapp_auto_service import send_lead_welcome, _send_meta, _log_message
from app.api.v1.endpoints.facebook_leads import process_facebook_lead


class TestLeadSyncIPMRecovery(unittest.TestCase):

    def setUp(self):
        self.db: Session = SessionLocal()
        self.cleanup_lead_ids = []
        self.cleanup_meta_lead_ids = []
        self.cleanup_phones = []

    def unique_phone(self, suffix: int = 0) -> str:
        ts_part = (int(time.time() * 1000) + suffix) % 100000000
        phone = f"+9198{ts_part:08d}"
        self.cleanup_phones.append(phone)
        return phone

    def tearDown(self):
        try:
            for meta_id in self.cleanup_meta_lead_ids:
                self.db.query(MetaLeadsAttribution).filter(
                    MetaLeadsAttribution.meta_lead_id.in_([meta_id, f"l:{meta_id}"])
                ).delete(synchronize_session=False)

            for phone in self.cleanup_phones:
                self.db.query(MessageLog).filter(MessageLog.mobile_number == phone).delete(synchronize_session=False)

            for lid in self.cleanup_lead_ids:
                self.db.query(MetaLeadsAttribution).filter(MetaLeadsAttribution.lead_id == lid).delete(synchronize_session=False)
                self.db.query(WAInbox).filter(WAInbox.lead_id == lid).delete(synchronize_session=False)
                self.db.query(CRMLead).filter(CRMLead.id == lid).delete(synchronize_session=False)

            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    # ── Test 1: Ingest Lead Atomic Creates Lead and Attribution ───────────────
    def test_01_ingest_lead_atomic_creates_lead_and_attribution(self):
        ts = int(time.time() * 1000)
        meta_id = f"test_meta_lead_{ts}"
        phone = self.unique_phone(1)
        self.cleanup_meta_lead_ids.append(meta_id)

        lead_data = {
            "id": meta_id,
            "created_time": "2026-09-13T03:00:00+0000",
            "campaign_id": "camp_123",
            "campaign_name": "Test Campaign",
            "adset_id": "adset_123",
            "ad_id": "ad_123",
            "form_id": "form_123",
            "field_data": [
                {"name": "full_name", "values": ["Test Prospect"]},
                {"name": "phone_number", "values": [phone]},
                {"name": "city", "values": ["Hyderabad"]},
            ]
        }

        with patch("app.services.whatsapp_auto_service.send_lead_welcome") as mock_welcome, \
             patch("app.services.whatsapp_group_alert_service.send_instant_new_lead_group_alert") as mock_alert:
            
            lead = facebook_leads_service.ingest_lead_atomic(
                db=self.db,
                lead_data=lead_data,
                company_id=2,
                category_id=42,
                page_segment="ETC_TRAINING",
                page_name="EV Craze4u",
                form_id="form_123",
                trigger_ipm=False,
                trigger_alert=False
            )

        self.assertIsNotNone(lead)
        self.cleanup_lead_ids.append(lead.id)
        self.assertEqual(lead.company_id, 2)
        self.assertEqual(lead.category_id, 42)
        self.assertEqual(lead.name, "Test Prospect")
        self.assertEqual(lead.phone, phone)

        # Verify MetaLeadsAttribution record created atomically
        att = self.db.query(MetaLeadsAttribution).filter_by(meta_lead_id=meta_id).first()
        self.assertIsNotNone(att)
        self.assertEqual(att.lead_id, lead.id)
        self.assertEqual(att.company_id, 2)
        self.assertEqual(att.meta_form_id, "form_123")

    # ── Test 2: Ingest Lead Atomic Triggers Welcome IPM ────────────────────────
    def test_02_ingest_lead_atomic_triggers_welcome_ipm(self):
        ts = int(time.time() * 1000)
        meta_id = f"test_meta_ipm_{ts}"
        phone = self.unique_phone(2)
        self.cleanup_meta_lead_ids.append(meta_id)

        lead_data = {
            "id": meta_id,
            "created_time": "2026-09-13T03:00:00+0000",
            "field_data": [
                {"name": "full_name", "values": ["IPM Trigger Test"]},
                {"name": "phone_number", "values": [phone]}
            ]
        }

        with patch("app.services.whatsapp_auto_service.send_lead_welcome") as mock_welcome, \
             patch("app.services.whatsapp_group_alert_service.send_instant_new_lead_group_alert"):
            
            lead = facebook_leads_service.ingest_lead_atomic(
                db=self.db,
                lead_data=lead_data,
                company_id=4,
                trigger_ipm=True,
                trigger_alert=False
            )
            self.assertIsNotNone(lead)
            self.cleanup_lead_ids.append(lead.id)
            mock_welcome.assert_called_once_with(
                db=self.db,
                phone=phone,
                lead_name="IPM Trigger Test",
                lead_id=lead.id
            )

    # ── Test 3: Ingest Lead Atomic Triggers Group Alert ────────────────────────
    def test_03_ingest_lead_atomic_triggers_group_alert(self):
        ts = int(time.time() * 1000)
        meta_id = f"test_meta_alert_{ts}"
        phone = self.unique_phone(3)
        self.cleanup_meta_lead_ids.append(meta_id)

        lead_data = {
            "id": meta_id,
            "created_time": "2026-09-13T03:00:00+0000",
            "field_data": [
                {"name": "full_name", "values": ["Group Alert Test"]},
                {"name": "phone_number", "values": [phone]}
            ]
        }

        with patch("app.services.whatsapp_auto_service.send_lead_welcome"), \
             patch("app.services.whatsapp_group_alert_service.send_instant_new_lead_group_alert") as mock_alert:
            
            lead = facebook_leads_service.ingest_lead_atomic(
                db=self.db,
                lead_data=lead_data,
                company_id=4,
                trigger_ipm=False,
                trigger_alert=True
            )
            self.assertIsNotNone(lead)
            self.cleanup_lead_ids.append(lead.id)
            mock_alert.assert_called_once_with(self.db, lead.id)

    # ── Test 4: Webhook and Pull Sync Route Through Ingest Atomic ──────────────
    def test_04_process_facebook_lead_routes_through_ingest_atomic(self):
        import asyncio
        ts = int(time.time() * 1000)
        meta_id = f"test_webhook_{ts}"

        with patch.object(facebook_leads_service, "lead_already_exists", return_value=False), \
             patch.object(facebook_leads_service, "get_page_info", return_value={"company_id": 4, "segment": "SOLAR", "name": "Solar Page"}), \
             patch.object(facebook_leads_service, "fetch_lead_data", return_value={"id": meta_id, "field_data": []}), \
             patch.object(facebook_leads_service, "ingest_lead_atomic") as mock_ingest:
            
            mock_ingest.return_value = MagicMock(id=99999)
            res = asyncio.run(process_facebook_lead(meta_id, page_id="123", form_id="456", db=self.db))
            self.assertIsNotNone(res)
            mock_ingest.assert_called_once()
            call_kwargs = mock_ingest.call_args[1]
            self.assertEqual(call_kwargs["trigger_ipm"], True)
            self.assertEqual(call_kwargs["trigger_alert"], True)

    # ── Test 5: Idempotency: Duplicate Lead Skipped ────────────────────────────
    def test_05_idempotency_duplicate_lead_skipped(self):
        ts = int(time.time() * 1000)
        meta_id = f"test_dedup_{ts}"
        phone = self.unique_phone(5)
        self.cleanup_meta_lead_ids.append(meta_id)

        lead_data = {
            "id": meta_id,
            "created_time": "2026-09-13T03:00:00+0000",
            "field_data": [
                {"name": "full_name", "values": ["Dedup Test"]},
                {"name": "phone_number", "values": [phone]}
            ]
        }

        # First ingestion -> Success
        lead1 = facebook_leads_service.ingest_lead_atomic(
            db=self.db,
            lead_data=lead_data,
            company_id=4,
            trigger_ipm=False,
            trigger_alert=False
        )
        self.assertIsNotNone(lead1)
        self.cleanup_lead_ids.append(lead1.id)

        # Second ingestion with same lead_id -> None (Skipped)
        with patch("app.services.whatsapp_auto_service.send_lead_welcome") as mock_welcome:
            lead2 = facebook_leads_service.ingest_lead_atomic(
                db=self.db,
                lead_data=lead_data,
                company_id=4,
                trigger_ipm=True,
                trigger_alert=True
            )
            self.assertIsNone(lead2)
            mock_welcome.assert_not_called()

    # ── Test 6: Concurrent IntegrityError Handled Safely ───────────────────────
    def test_06_idempotency_concurrent_integrity_error_recovery(self):
        ts = int(time.time() * 1000)
        meta_id = f"test_concurrent_{ts}"
        phone = self.unique_phone(6)
        self.cleanup_meta_lead_ids.append(meta_id)

        # First insert real record
        lead1 = facebook_leads_service.ingest_lead_atomic(
            db=self.db,
            lead_data={"id": meta_id, "field_data": [{"name": "full_name", "values": ["Concurrent Lead"]}, {"name": "phone", "values": [phone]}]},
            company_id=4,
            trigger_ipm=False,
            trigger_alert=False
        )
        self.assertIsNotNone(lead1)
        self.cleanup_lead_ids.append(lead1.id)

        # Now simulate a race where lead_already_exists returned False, but commit raises IntegrityError
        with patch.object(facebook_leads_service, "lead_already_exists", return_value=False), \
             patch.object(self.db, "commit", side_effect=IntegrityError("duplicate key", None, None)):
            recovered_lead = facebook_leads_service.ingest_lead_atomic(
                db=self.db,
                lead_data={"id": meta_id, "field_data": [{"name": "full_name", "values": ["Concurrent Lead"]}, {"name": "phone", "values": [phone]}]},
                company_id=4,
                trigger_ipm=False,
                trigger_alert=False
            )
            # Must return the existing lead without crashing
            self.assertIsNotNone(recovered_lead)
            self.assertEqual(recovered_lead.id, lead1.id)

    # ── Test 7: Source-ID Normalization in lead_already_exists ─────────────────
    def test_07_source_id_normalization_lead_already_exists(self):
        ts = int(time.time() * 1000)
        clean_id = f"norm_{ts}"
        prefixed_id = f"l:{clean_id}"
        phone = self.unique_phone(7)
        self.cleanup_meta_lead_ids.append(clean_id)

        lead = CRMLead(
            name="Source ID Norm Test",
            phone=phone,
            company_id=4,
            source="Social Media",
            source_details=json.dumps({"lead_id": clean_id})
        )
        self.db.add(lead)
        self.db.flush()
        self.cleanup_lead_ids.append(lead.id)

        att = MetaLeadsAttribution(
            company_id=4,
            lead_id=lead.id,
            meta_lead_id=clean_id
        )
        self.db.add(att)
        self.db.commit()

        # Check clean id
        self.assertTrue(facebook_leads_service.lead_already_exists(clean_id, self.db))
        # Check prefixed id 'l:<id>'
        self.assertTrue(facebook_leads_service.lead_already_exists(prefixed_id, self.db))

    # ── Test 8: Sheets Normalization in row_to_crm_lead ────────────────────────
    def test_08_sheets_normalization_row_to_crm_lead(self):
        headers = ["name", "phone", "lead_id"]
        row = ["Sheet Prospect", "p:+919849396975", "l:9988776655"]
        col_map = {"name": 0, "phone": 1, "lead_id": 2}

        crm_data = row_to_crm_lead(row, col_map, company_id=2, source_tag="Google Sheets")
        self.assertIsNotNone(crm_data)
        self.assertEqual(crm_data["phone"], "+919849396975")
        self.assertNotIn("p:", crm_data["phone"])
        self.assertIn("'lead_id': '9988776655'", crm_data["source_details"])
        self.assertNotIn("l:9988776655", crm_data["source_details"])

    # ── Test 9: Sheets Duplicate Check with Prefixed and Clean Forms ──────────
    def test_09_sheets_duplicate_check_is_duplicate(self):
        ts = int(time.time() * 1000)
        clean_lead_id = f"sheet_dup_{ts}"
        phone_num = f"97{ts % 100000000:08d}"
        self.cleanup_meta_lead_ids.append(clean_lead_id)

        lead = CRMLead(
            name="Sheet Dup Test",
            phone=f"+91{phone_num}",
            company_id=2,
            source="Online - M",
            source_details=f"{{'lead_id': '{clean_lead_id}'}}"
        )
        self.db.add(lead)
        self.db.flush()
        self.cleanup_lead_ids.append(lead.id)

        att = MetaLeadsAttribution(
            company_id=2,
            lead_id=lead.id,
            meta_lead_id=clean_lead_id
        )
        self.db.add(att)
        self.db.commit()

        # Test duplicate by clean FB lead ID
        self.assertTrue(is_duplicate(phone=None, email=None, fb_lead_id=clean_lead_id, db=self.db))
        # Test duplicate by prefixed FB lead ID ('l:...')
        self.assertTrue(is_duplicate(phone=None, email=None, fb_lead_id=f"l:{clean_lead_id}", db=self.db))
        # Test duplicate by prefixed phone ('p:...')
        self.assertTrue(is_duplicate(phone=f"p:+91{phone_num}", email=None, fb_lead_id=None, db=self.db))

    # ── Test 10: Unapproved Template Fail-Closed (Zero Freeform Fallback) ──────
    def test_10_unapproved_template_fail_closed(self):
        unapproved_tmpl = MagicMock()
        unapproved_tmpl.id = 9991
        unapproved_tmpl.name = "unapproved_test_tmpl"
        unapproved_tmpl.meta_template_name = "unapproved_test_tmpl"
        unapproved_tmpl.is_meta_approved = False
        unapproved_tmpl.meta_approval_status = "REJECTED"

        # Even with valid phone, must reject cold outbound and return TMPL_NOT_APPROVED
        res = _send_meta(phone="9876543210", message="Hello", template=unapproved_tmpl, db=self.db)
        self.assertFalse(res["success"])
        self.assertEqual(res.get("error_code"), "TMPL_NOT_APPROVED")

        # Freeform text without template outside 24h window must fail-closed with WINDOW_EXPIRED
        res_freeform = _send_meta(phone="9876543210", message="Cold Outbound Text", template=None, db=self.db)
        self.assertFalse(res_freeform["success"])
        self.assertEqual(res_freeform.get("error_code"), "WINDOW_EXPIRED")

    # ── Test 11: Template Fallback to Approved ThanKYou General ───────────────
    def test_11_template_fallback_to_approved_thankyou_general(self):
        approved_thankyou = self.db.query(WhatsAppTemplate).filter_by(
            slug="myntreal_lead_thankyou_general", is_active=True
        ).first()

        if approved_thankyou:
            approved_thankyou.is_meta_approved = True
            self.db.commit()

        phone = self.unique_phone(11)
        lead = CRMLead(
            name="Fallback Test Prospect",
            phone=phone,
            company_id=4
        )
        self.db.add(lead)
        self.db.commit()
        self.cleanup_lead_ids.append(lead.id)

        with patch("app.services.whatsapp_auto_service._send_meta") as mock_send, \
             patch("app.services.whatsapp_auto_service._log_message") as mock_log:
            
            mock_send.return_value = {"success": True, "wamid": "wamid.test_fallback"}
            
            res = send_lead_welcome(
                db=self.db,
                phone=lead.phone,
                lead_name=lead.name,
                lead_id=lead.id
            )
            self.assertTrue(res["success"])

            # Verify that the template sent was myntreal_lead_thankyou_general
            sent_template = mock_send.call_args[0][2]
            self.assertEqual(sent_template.slug, "myntreal_lead_thankyou_general")
            # Verify event_key logged is myntreal_lead_thankyou_general
            logged_event = mock_log.call_args[0][4]
            self.assertEqual(logged_event, "myntreal_lead_thankyou_general")

    # ── Test 12: Failure Logging Without Exception ─────────────────────────────
    def test_12_failure_logging_without_exception(self):
        phone = self.unique_phone(12)

        lead = CRMLead(
            name="Failure Log Test",
            phone=phone,
            company_id=4
        )
        self.db.add(lead)
        self.db.commit()
        self.cleanup_lead_ids.append(lead.id)

        # Simulate Meta API failure: 131031 (Account locked)
        simulated_result = {
            "success": False,
            "reason": "Business Account locked: Business account has been locked.",
            "error_code": "131031",
            "provider_response": {"errors": [{"code": 131031}]}
        }

        # _log_message must execute and create a record in message_log without raising
        _log_message(
            db=self.db,
            phone=phone,
            message="Test Message",
            result=simulated_result,
            event_key="test_failure_event",
            lead_id=lead.id
        )

        log_row = self.db.query(MessageLog).filter(MessageLog.mobile_number == phone).first()
        self.assertIsNotNone(log_row)
        self.assertEqual(log_row.current_status, "failed")
        self.assertEqual(log_row.error_code, "131031")
        self.assertIn("Business account has been locked", log_row.error_message)


if __name__ == "__main__":
    unittest.main()
