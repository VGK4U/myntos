"""
Tests for Universal History System
Verifies:
  1. Phone normalization and masking behavior.
  2. Entity resolution for CRM leads and VGK members.
  3. Call aggregation, deduplication, and recording stream URL formatting.
  4. Pure read-only messaging behavior.
  5. Lead change history timeline merging audit logs, notes, followups, and assignments.
  6. Authorization checks (RBAC, assigned staff vs non-assigned staff).
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from app.services.universal_history_service import (
    normalize_phone_digits,
    mask_phone_number,
    UniversalHistoryService,
)
from app.models.staff import StaffEmployee, StaffRole
from app.models.crm import CRMLead, CRMLeadAuditLog, CRMLeadNote, CRMLeadFollowUp, CRMLeadAssignment
from app.models.staff_accounts import OfficialPartner


def make_staff(id=1, role_code="STAFF", staff_type="STAFF", emp_code="EMP001", company_id=None):
    r = StaffRole(id=id, role_code=role_code, role_name=role_code, hierarchy_level=50)
    emp = StaffEmployee(
        id=id,
        emp_code=emp_code,
        full_name=f"Staff {id}",
        staff_type=staff_type,
        role=r,
        role_id=r.id,
        date_of_joining=datetime.now().date(),
        password_hash="fake_hash",
    )
    if company_id:
        emp.company_id = company_id
    return emp


class TestUniversalHistoryService(unittest.TestCase):

    def test_phone_normalization(self):
        """Test trailing 10-digit extraction."""
        self.assertEqual(normalize_phone_digits("+91 98765 43210"), "9876543210")
        self.assertEqual(normalize_phone_digits("09876543210"), "9876543210")
        self.assertEqual(normalize_phone_digits("9876543210"), "9876543210")
        self.assertEqual(normalize_phone_digits(""), "")
        self.assertEqual(normalize_phone_digits(None), "")

    def test_phone_masking(self):
        """Test phone masking for non-privileged users."""
        self.assertEqual(mask_phone_number("9876543210", can_unmask=True), "9876543210")
        self.assertEqual(mask_phone_number("9876543210", can_unmask=False), "XXXXXX3210")
        self.assertEqual(mask_phone_number("+91 9876543210", can_unmask=False), "XXXXXX3210")

    def test_can_unmask_phone_privilege(self):
        """Admin/EA roles can unmask; normal staff without capability cannot."""
        admin_user = make_staff(id=1, role_code="SUPERADMIN", staff_type="EA")
        self.assertTrue(UniversalHistoryService.check_can_unmask_phone(admin_user))

        normal_user = make_staff(id=2, role_code="TELECALLER", staff_type="STAFF")
        self.assertFalse(UniversalHistoryService.check_can_unmask_phone(normal_user))

        cap_user = make_staff(id=3, role_code="STAFF", staff_type="STAFF")
        cap_user.capabilities = ["crm.leads.unmask_phone"]
        self.assertTrue(UniversalHistoryService.check_can_unmask_phone(cap_user))

    def test_resolve_crm_lead_authorization(self):
        """Test that unassigned staff cannot view lead history without capability."""
        mock_lead = CRMLead(
            id=101,
            company_id=1,
            name="John Doe",
            phone="9876543210",
            telecaller_id=5,
        )
        assigned_user = make_staff(id=5, role_code="STAFF", staff_type="STAFF", company_id=1)

        mock_db = MagicMock()
        def query_side_effect(model):
            q = MagicMock()
            if model == CRMLead:
                q.filter.return_value.first.return_value = mock_lead
            elif model == StaffEmployee:
                q.filter.return_value.first.return_value = assigned_user
            elif model == CRMLeadPhone:
                q.filter.return_value.all.return_value = []
            return q
        mock_db.query.side_effect = query_side_effect

        res = UniversalHistoryService.resolve_entity(mock_db, "crm_lead", 101, assigned_user)
        self.assertEqual(res["entity_id"], 101)
        self.assertEqual(res["name"], "John Doe")
        self.assertIn("9876543210", res["phone_10digits"])

        unassigned_user = make_staff(id=99, role_code="STAFF", staff_type="STAFF", company_id=1)
        unassigned_user.capabilities = []
        with self.assertRaises(PermissionError):
            UniversalHistoryService.resolve_entity(mock_db, "crm_lead", 101, unassigned_user)

    def test_resolve_vgk_member_authorization(self):
        """Test VGK member resolution preserves member identity without lead conversion."""
        mock_member = OfficialPartner(
            id=202,
            partner_code="VGK202",
            partner_name="Ramesh Partner",
            phone="9123456780",
            whatsapp_number="9123456780",
            category="VGK_TEAM",
            assigned_staff_id=10,
            registered_by_emp_code="EMP010",
            is_active=True,
            is_blocked=False,
        )
        assigned_staff = make_staff(id=10, emp_code="EMP010", role_code="STAFF", staff_type="STAFF")

        mock_db = MagicMock()
        def query_side_effect(model):
            q = MagicMock()
            if model == OfficialPartner:
                q.filter.return_value.first.return_value = mock_member
            elif model == StaffEmployee:
                q.filter.return_value.first.return_value = assigned_staff
            return q
        mock_db.query.side_effect = query_side_effect

        res = UniversalHistoryService.resolve_entity(mock_db, "vgk_member", 202, assigned_staff)
        self.assertEqual(res["entity_type"], "vgk_member")
        self.assertEqual(res["entity_id"], 202)
        self.assertEqual(res["partner_code"], "VGK202")
        self.assertIn("9123456780", res["phone_10digits"])

        # Unassigned staff blocked
        stranger_staff = make_staff(id=77, emp_code="EMP077", role_code="STAFF", staff_type="STAFF")
        with self.assertRaises(PermissionError):
            UniversalHistoryService.resolve_entity(mock_db, "vgk_member", 202, stranger_staff)

    def test_call_deduplication_native_mirrored_softphone(self):
        """Verify mirrored native calls with source='softphone' or device_call_id='vcs_%' are skipped."""
        mock_db = MagicMock()
        # Mock voip returns 1 call
        vcs_dt = datetime(2026, 9, 20, 14, 30, 0)
        vcs_row = (1, "sess_123", vcs_dt, 45, "outbound", "completed", "Agent Bob", "EMP005", "rec_key_1", "AVAILABLE", 101, "9876543210", "9876543210")
        
        # Mock staff_call_logs returns 1 normal GSM call, and 1 mirrored softphone call
        scl_normal_dt = datetime(2026, 9, 21, 10, 0, 0)
        scl_normal_row = (10, scl_normal_dt, "OUTGOING", 30, True, 501, "Agent Alice", "EMP002", "sim", "dev_1", 101, "9876543210")
        scl_mirrored_row = (11, vcs_dt, "OUTGOING", 45, False, None, "Agent Bob", "EMP005", "softphone", "vcs_1", 101, "9876543210")

        execute_results = [
            [vcs_row],  # voip_call_sessions
            [scl_normal_row, scl_mirrored_row],  # staff_call_logs
            [],  # operator_calls
            [],  # crm_dialer_attempts
        ]
        mock_db.execute.return_value.fetchall.side_effect = execute_results

        entity_info = {
            "entity_type": "crm_lead",
            "entity_id": 101,
            "phone_10digits": ["9876543210"],
        }
        res = UniversalHistoryService.get_calls_history(mock_db, entity_info)
        self.assertEqual(res["total_calls"], 2)
        sources = [item["source"] for item in res["items"]]
        self.assertIn("Plivo WebRTC", sources)
        self.assertIn("Native SIM", sources)
        # Mirrored softphone in staff_call_logs was omitted
        self.assertNotIn("vcs_1", [item.get("id") for item in res["items"] if item["source"] == "Native SIM"])

    def test_changes_history_aggregation(self):
        """Verify changes history combines audit logs, notes, followups, and assignments chronologically."""
        mock_db = MagicMock()
        t1 = datetime(2026, 9, 20, 10, 0, 0)
        t2 = datetime(2026, 9, 20, 11, 0, 0)
        t3 = datetime(2026, 9, 20, 12, 0, 0)

        mock_audit = CRMLeadAuditLog(id=1, lead_id=101, field_name="status", old_value="new", new_value="contacted", changed_by_name="Agent Bob", changed_at=t1)
        mock_note = CRMLeadNote(id=2, company_id=1, lead_id=101, note="Customer requested callback", created_by_id="5", created_by_type="staff", created_at=t2)
        mock_fu = CRMLeadFollowUp(id=3, company_id=1, lead_id=101, scheduled_date=t3, status="scheduled", notes="Discuss solar subsidy", created_at=t3)

        def query_side_effect(model):
            q = MagicMock()
            if model == CRMLeadAuditLog:
                q.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_audit]
            elif model == CRMLeadNote:
                q.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_note]
            elif model == CRMLeadFollowUp:
                q.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_fu]
            elif model == CRMLeadAssignment:
                q.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            return q
        mock_db.query.side_effect = query_side_effect

        entity_info = {"entity_type": "crm_lead", "entity_id": 101}
        res = UniversalHistoryService.get_changes_history(mock_db, entity_info, subfilter="all")
        self.assertEqual(res["total_changes"], 3)
        # Should be ordered descending: t3 (followup), t2 (note), t1 (audit)
        self.assertEqual(res["items"][0]["category"], "followup")
        self.assertEqual(res["items"][1]["category"], "note")
        self.assertEqual(res["items"][2]["category"], "audit")

    def test_resolve_vgk_member_by_phone_fallback(self):
        """Verify VGK member resolution resolves via phone when entity_id is 0."""
        mock_partner = OfficialPartner(
            id=303,
            partner_code="VGK303",
            partner_name="Bandi Gangaraju",
            phone="9154432909",
            category="VGK_TEAM",
            is_active=True,
        )
        admin_user = make_staff(id=1, role_code="SUPERADMIN", staff_type="EA")

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_partner

        res = UniversalHistoryService.resolve_entity(
            mock_db,
            entity_type="vgk_member",
            entity_id=0,
            current_user=admin_user,
            phone="+91 91544 32909",
            name="Mr. Bandi Gangaraju"
        )
        self.assertEqual(res["entity_id"], 303)
        self.assertEqual(res["name"], "Bandi Gangaraju")
        self.assertIn("9154432909", res["phone_10digits"])
        self.assertEqual(res["category"], "VGK_TEAM")

    def test_resolve_vgk_member_synthetic_fallback(self):
        """Verify Ground Source without OfficialPartner record gets a synthetic member profile for phone."""
        admin_user = make_staff(id=1, role_code="SUPERADMIN", staff_type="EA")

        mock_db = MagicMock()
        # No partner found
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        res = UniversalHistoryService.resolve_entity(
            mock_db,
            entity_type="vgk_member",
            entity_id=0,
            current_user=admin_user,
            phone="9876500000",
            name="Direct Ground Partner"
        )
        self.assertEqual(res["entity_id"], 0)
        self.assertEqual(res["name"], "Direct Ground Partner")
        self.assertEqual(res["primary_phone"], "9876500000")
        self.assertIn("9876500000", res["phone_10digits"])
        self.assertEqual(res["category"], "VGK Member / Ground Source")

    def test_messages_history_delivery_statuses(self):
        """Verify get_messages_history correctly maps delivery states: failed, read, delivered, sent, received."""
        mock_db = MagicMock()
        t_failed = datetime(2026, 9, 21, 10, 0, 0)
        t_deliv = datetime(2026, 9, 21, 11, 0, 0)
        t_read = datetime(2026, 9, 21, 12, 0, 0)
        t_inbox = datetime(2026, 9, 21, 13, 0, 0)

        # row schema for message_log:
        # id, message_body, sent_at, sender_type, sent_by_name, message_type, current_status, provider, to_number,
        # webhook_data, error_code, error_message, failure_reason, delivered_at, read_at, failed_at, message_sid, from_number, mobile_number
        row_failed = (
            101, "Test Failed", t_failed, "staff", "Agent Bob", "text", "failed", "META", "9876543210",
            None, "131031", "Business Account locked", "Business Account locked: Reason", None, None, t_failed, "wamid.1", None, "9876543210"
        )
        row_deliv = (
            102, "Test Delivered", t_deliv, "staff", "Agent Bob", "text", "delivered", "META", "9876543210",
            None, None, None, None, t_deliv, None, None, "wamid.2", None, "9876543210"
        )
        row_read = (
            103, "Test Read", t_read, "staff", "Agent Bob", "text", "read", "META", "9876543210",
            None, None, None, None, t_deliv, t_read, None, "wamid.3", None, "9876543210"
        )

        # row schema for wa_inbox:
        # id, body_text, from_name, message_type, received_at, media_url, from_phone, media_mime_type, status, wamid
        row_inbox = (
            201, "Hello from lead", "Lead Customer", "text", t_inbox, None, "9876543210", None, "received", "wamid.inb"
        )

        mock_db.execute.return_value.fetchall.side_effect = [
            [row_failed, row_deliv, row_read],  # message_log
            [row_inbox],                        # wa_inbox
            [],                                 # campaign logs
        ]

        entity_info = {"entity_type": "crm_lead", "entity_id": 1, "phone_10digits": ["9876543210"]}
        res = UniversalHistoryService.get_messages_history(mock_db, entity_info)
        items_by_id = {it["id"]: it for it in res["items"]}

        # Failed message assertions
        f_item = items_by_id["ml_101"]
        self.assertEqual(f_item["status"], "failed")
        self.assertEqual(f_item["status_ticks"], "❌")
        self.assertEqual(f_item["status_color"], "#ef4444")
        self.assertIn("Business Account locked", f_item["failure_reason"])

        # Delivered message assertions
        d_item = items_by_id["ml_102"]
        self.assertEqual(d_item["status"], "delivered")
        self.assertEqual(d_item["status_ticks"], "✓✓")
        self.assertEqual(d_item["status_color"], "#94a3b8")

        # Read message assertions
        r_item = items_by_id["ml_103"]
        self.assertEqual(r_item["status"], "read")
        self.assertEqual(r_item["status_ticks"], "✓✓")
        self.assertEqual(r_item["status_color"], "#38bdf8")

        # Inbound received message assertions
        inb_item = items_by_id["wi_201"]
        self.assertEqual(inb_item["status"], "received")
        self.assertEqual(inb_item["status_ticks"], "↙")
        self.assertEqual(inb_item["direction"], "inbound")

    def test_messages_history_media_attachment_resolution(self):
        """Verify media attachments (Meta media IDs, webhook JSON, embedded [Media:...]) are extracted and cleaned."""
        mock_db = MagicMock()
        t1 = datetime(2026, 9, 21, 10, 0, 0)
        t2 = datetime(2026, 9, 21, 11, 0, 0)

        # 1. Message log with embedded [Media: /storage/wa_media/brochure.pdf]
        row_ml = (
            301, "Here is brochure [Media: /storage/wa_media/brochure.pdf]", t1, "staff", "Agent Bob", "document", "sent", "META", "9876543210",
            None, None, None, None, None, None, None, "wamid.doc", None, "9876543210"
        )
        # 2. Inbound wa_inbox with Meta numeric media ID
        row_inb = (
            302, "", "Lead Customer", "image", t2, "1234567890123456", "9876543210", "image/jpeg", "received", "wamid.img"
        )

        mock_db.execute.return_value.fetchall.side_effect = [
            [row_ml],
            [row_inb],
            [],
        ]

        entity_info = {"entity_type": "crm_lead", "entity_id": 1, "phone_10digits": ["9876543210"]}
        res = UniversalHistoryService.get_messages_history(mock_db, entity_info)
        items_by_id = {it["id"]: it for it in res["items"]}

        # Document resolution
        doc_item = items_by_id["ml_301"]
        self.assertEqual(doc_item["media_url"], "/storage/wa_media/brochure.pdf")
        self.assertEqual(doc_item["media_type"], "document")
        self.assertEqual(doc_item["message_text"], "Here is brochure")  # Stripped bracket tag

        # Image resolution
        img_item = items_by_id["wi_302"]
        self.assertEqual(img_item["media_url"], "/api/v1/whatsapp/media/1234567890123456")
        self.assertEqual(img_item["media_type"], "image")
        self.assertEqual(img_item["media_name"], "Photo Attachment")


if __name__ == "__main__":
    unittest.main()

