"""
Comprehensive Verification Suite for VGK Channel Partners Requirements:
1. Assigned Staff (assigned_staff_id, assigned_staff_name, assigned_staff_emp_code)
2. Manual assignment permissions (Role-based: EA/Mentors/Admins, server-side enforced)
3. Auto-assignment through legitimate softphone call workflow
4. Manual assignment precedence — never overwrite existing assignment
5. Communication History (Calls + Messages)
6. Secure call-recording playback with existing authorization
7. Contacted Days Since (0 = Today, 1 = 1d ago, null = Never)
8. Correct filters (<5 [0-4], 5-10, 11-20, 21-30, >30, never)
9. Editable Active/Inactive/Blocked Status and audit trail
10. Role-based visibility and permissions (Admins see all; regular staff see assigned/registered)
11. 31-column table ordering
"""

import os
import sys
import unittest
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.staff import StaffEmployee, StaffRole
from app.models.staff_accounts import OfficialPartner
from app.models.system_log import DataChangeLog
from app.api.v1.endpoints.vgk_team import (
    _is_vgk_admin,
    _has_full_vgk_visibility,
    list_vgk_members,
    assign_vgk_member,
    update_vgk_member_status,
    record_vgk_call_intent,
    get_vgk_communication_history,
    AssignMemberPayload,
    UpdateMemberStatusPayload,
    get_indian_time
)
from fastapi import HTTPException


class TestVGKChannelPartnersRequirements(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        # Retrieve test employees
        cls.admin_mr10001 = cls.db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'MR10001').first()
        cls.subash_mr10025 = cls.db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'MR10025').first()
        cls.ea_mr10016 = cls.db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'MR10016').first()
        cls.jagannath_mr10018 = cls.db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'MR10018').first()
        cls.poojitha_mn10016 = cls.db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'MN10016').first()
        cls.regular_agent = cls.db.query(StaffEmployee).filter(StaffEmployee.emp_code.notin_(['MR10001', 'MR10025', 'MR10016', 'MR10018', 'MN10016']), StaffEmployee.status == 'active').first()

        # Find or create a dedicated test VGK partner
        cls.test_partner = cls.db.query(OfficialPartner).filter(
            OfficialPartner.category == 'VGK_TEAM',
            OfficialPartner.partner_code == 'VGK_TEST_VERIFY_99'
        ).first()

        if not cls.test_partner:
            cls.test_partner = OfficialPartner(
                partner_code='VGK_TEST_VERIFY_99',
                partner_name='Test CP Verification Partner',
                category='VGK_TEAM',
                phone='9888877777',
                is_active=True,
                is_blocked=False,
                member_status='ACTIVE',
                registered_by_emp_code='VGK07102207',
                parent_partner_id=31,
                created_at=get_indian_time()
            )
            cls.db.add(cls.test_partner)
            cls.db.commit()
            cls.db.refresh(cls.test_partner)

    @classmethod
    def tearDownClass(cls):
        if cls.test_partner:
            # Clean up audit logs created for test partner
            cls.db.query(DataChangeLog).filter(
                DataChangeLog.table_name == 'official_partners',
                DataChangeLog.record_id == str(cls.test_partner.id)
            ).delete()
            # Clean up test partner
            cls.db.delete(cls.test_partner)
            cls.db.commit()
        cls.db.close()

    def test_01_dynamic_role_based_admin_and_visibility(self):
        """Req 2 & 10: 5-user whitelist visibility (Poojitha, Subash, Yaswanth, Jagannath, Mr10001)."""
        # MR10001 (Admin) -> Full Visibility
        self.assertTrue(_is_vgk_admin(self.admin_mr10001))
        self.assertTrue(_has_full_vgk_visibility(self.admin_mr10001))

        # MR10016 (Yaswanth) -> Full Visibility
        self.assertTrue(_is_vgk_admin(self.ea_mr10016))
        self.assertTrue(_has_full_vgk_visibility(self.ea_mr10016))

        # MR10025 (Subash) -> Full Visibility
        if self.subash_mr10025:
            self.assertTrue(_is_vgk_admin(self.subash_mr10025))
            self.assertTrue(_has_full_vgk_visibility(self.subash_mr10025))

        # MR10018 (Jagannath) -> Full Visibility
        if self.jagannath_mr10018:
            self.assertTrue(_is_vgk_admin(self.jagannath_mr10018))
            self.assertTrue(_has_full_vgk_visibility(self.jagannath_mr10018))

        # MN10016 (Poojitha) -> Full Visibility
        if self.poojitha_mn10016:
            self.assertTrue(_is_vgk_admin(self.poojitha_mn10016))
            self.assertTrue(_has_full_vgk_visibility(self.poojitha_mn10016))

        # Regular agent (NOT in whitelist) -> Restricted
        if self.regular_agent:
            self.assertFalse(_has_full_vgk_visibility(self.regular_agent))

    def test_02_manual_assignment_permissions(self):
        """Req 2: Regular staff cannot assign (403), Admin can assign."""
        payload = AssignMemberPayload(assigned_staff_id=self.ea_mr10016.id, assignment_reason="Testing assignment")

        # 1. Regular staff attempts assignment -> 403 Forbidden
        if self.regular_agent:
            with self.assertRaises(HTTPException) as ctx:
                assign_vgk_member(
                    member_id=self.test_partner.id,
                    payload=payload,
                    current_user=self.regular_agent,
                    db=self.db
                )
            self.assertEqual(ctx.exception.status_code, 403)
            self.assertIn("Forbidden", ctx.exception.detail)

        # 2. Admin assigns partner -> Success
        res = assign_vgk_member(
            member_id=self.test_partner.id,
            payload=payload,
            current_user=self.admin_mr10001,
            db=self.db
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["assigned_staff_id"], self.ea_mr10016.id)

        self.db.refresh(self.test_partner)
        self.assertEqual(self.test_partner.assigned_staff_id, self.ea_mr10016.id)

        # Verify audit log in DataChangeLog
        audit = self.db.query(DataChangeLog).filter(
            DataChangeLog.table_name == 'official_partners',
            DataChangeLog.record_id == str(self.test_partner.id),
            DataChangeLog.field_name == 'assigned_staff_id'
        ).order_by(DataChangeLog.id.desc()).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.new_value, str(self.ea_mr10016.id))

    def test_03_manual_precedence_and_softphone_call_workflow(self):
        """Req 3 & 4: Auto-assignment on softphone call IF unassigned, NEVER overwrite if assigned."""
        # Partner is currently assigned to MR10016 from test_02.
        # Calling as admin (MR10001):
        res = record_vgk_call_intent(
            member_id=self.test_partner.id,
            current_user=self.admin_mr10001,
            db=self.db
        )
        self.assertTrue(res["success"])
        # Assignment MUST NOT change (Manual precedence!)
        self.assertFalse(res["was_assigned"])
        self.assertEqual(res["assigned_staff_id"], self.ea_mr10016.id)
        self.db.refresh(self.test_partner)
        self.assertEqual(self.test_partner.assigned_staff_id, self.ea_mr10016.id)
        self.assertIsNotNone(self.test_partner.last_contact_at)

        # Now manually unassign partner
        unassign_payload = AssignMemberPayload(assigned_staff_id=None, assignment_reason="Unassign for test")
        assign_vgk_member(
            member_id=self.test_partner.id,
            payload=unassign_payload,
            current_user=self.admin_mr10001,
            db=self.db
        )
        self.db.refresh(self.test_partner)
        self.assertIsNone(self.test_partner.assigned_staff_id)

        # Now softphone call intent triggers auto-assignment!
        res2 = record_vgk_call_intent(
            member_id=self.test_partner.id,
            current_user=self.ea_mr10016,
            db=self.db
        )
        self.assertTrue(res2["success"])
        self.assertTrue(res2["was_assigned"])
        self.assertEqual(res2["assigned_staff_id"], self.ea_mr10016.id)
        self.db.refresh(self.test_partner)
        self.assertEqual(self.test_partner.assigned_staff_id, self.ea_mr10016.id)

    def test_04_status_edit_and_blocked_communication_prevention(self):
        """Req 9: Editable Active/Inactive/Blocked status and audit trail."""
        # Regular staff not assigned to partner cannot update status -> 403
        if self.regular_agent:
            with self.assertRaises(HTTPException) as ctx:
                update_vgk_member_status(
                    member_id=self.test_partner.id,
                    payload=UpdateMemberStatusPayload(status="INACTIVE", status_note="Unauthorized try"),
                    current_user=self.regular_agent,
                    db=self.db
                )
            self.assertEqual(ctx.exception.status_code, 403)

        # Assigned staff or Admin CAN update status
        res = update_vgk_member_status(
            member_id=self.test_partner.id,
            payload=UpdateMemberStatusPayload(status="BLOCKED", status_note="Compliance review lock"),
            current_user=self.ea_mr10016,
            db=self.db
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "Blocked")
        self.db.refresh(self.test_partner)
        self.assertTrue(self.test_partner.is_blocked)

        # Calling a BLOCKED member must be strictly prevented
        with self.assertRaises(HTTPException) as ctx:
            record_vgk_call_intent(
                member_id=self.test_partner.id,
                current_user=self.admin_mr10001,
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Blocked", ctx.exception.detail)

        # Restore to ACTIVE
        res_active = update_vgk_member_status(
            member_id=self.test_partner.id,
            payload=UpdateMemberStatusPayload(status="ACTIVE", status_note="Re-activated"),
            current_user=self.admin_mr10001,
            db=self.db
        )
        self.assertTrue(res_active["success"])
        self.assertEqual(res_active["status"], "Active")
        self.db.refresh(self.test_partner)
        self.assertTrue(self.test_partner.is_active)
        self.assertFalse(self.test_partner.is_blocked)

    def test_05_contacted_days_since_calculation_and_filters(self):
        """Req 7 & 8: Contacted Days Since (0=Today, 1=1d ago, etc.) & boundary filters."""
        today_ist = get_indian_time().date()

        # 1. Contacted Today -> 0 days
        self.test_partner.last_contact_at = datetime.combine(today_ist, datetime.min.time()) + timedelta(hours=10)
        self.db.commit()

        res = list_vgk_members(
            search='VGK_TEST_VERIFY_99',
            current_user=self.admin_mr10001,
            db=self.db
        )
        self.assertEqual(len(res["data"]), 1)
        item = res["data"][0]
        self.assertEqual(item["contacted_days_since"], 0)

        # Filter <5 must match (0-4 days)
        res_lt5 = list_vgk_members(
            search='VGK_TEST_VERIFY_99',
            contacted_days='<5',
            current_user=self.admin_mr10001,
            db=self.db
        )
        self.assertEqual(len(res_lt5["data"]), 1)

        # Filter 5-10 must NOT match
        res_5_10 = list_vgk_members(
            search='VGK_TEST_VERIFY_99',
            contacted_days='5-10',
            current_user=self.admin_mr10001,
            db=self.db
        )
        self.assertEqual(len(res_5_10["data"]), 0)

        # 2. Contacted 7 days ago -> 5-10 bucket
        self.test_partner.last_contact_at = datetime.combine(today_ist - timedelta(days=7), datetime.min.time())
        self.db.commit()

        res_7d = list_vgk_members(
            search='VGK_TEST_VERIFY_99',
            contacted_days='5-10',
            current_user=self.admin_mr10001,
            db=self.db
        )
        self.assertEqual(len(res_7d["data"]), 1)
        self.assertEqual(res_7d["data"][0]["contacted_days_since"], 7)

        # 3. Contacted 35 days ago -> >30 bucket
        self.test_partner.last_contact_at = datetime.combine(today_ist - timedelta(days=35), datetime.min.time())
        self.db.commit()

        res_35d = list_vgk_members(
            search='VGK_TEST_VERIFY_99',
            contacted_days='>30',
            current_user=self.admin_mr10001,
            db=self.db
        )
        self.assertEqual(len(res_35d["data"]), 1)
        self.assertEqual(res_35d["data"][0]["contacted_days_since"], 35)

        # 4. Never Contacted (NULL)
        self.test_partner.last_contact_at = None
        self.db.commit()

        res_never = list_vgk_members(
            search='VGK_TEST_VERIFY_99',
            contacted_days='never',
            current_user=self.admin_mr10001,
            db=self.db
        )
        self.assertEqual(len(res_never["data"]), 1)
        self.assertIsNone(res_never["data"][0]["contacted_days_since"])

    def test_06_communication_history_aggregation(self):
        """Req 5 & 6: Communication history aggregation & permission checks."""
        # Partner assigned to MR10016
        # Ordinary staff not assigned cannot view history -> 403
        if self.regular_agent:
            with self.assertRaises(HTTPException) as ctx:
                get_vgk_communication_history(
                    member_id=self.test_partner.id,
                    current_user=self.regular_agent,
                    db=self.db
                )
            self.assertEqual(ctx.exception.status_code, 403)

        # Assigned staff (MR10016) or Admin (MR10001) can view history
        hist = get_vgk_communication_history(
            member_id=self.test_partner.id,
            current_user=self.admin_mr10001,
            db=self.db
        )
        self.assertTrue(hist["success"])
        self.assertEqual(hist["member"]["id"], self.test_partner.id)
        self.assertIn("items", hist)
        self.assertIn("total_calls", hist)
        self.assertIn("total_messages", hist)

    def test_07_sorting_by_last_contact_at(self):
        """Req 8: Sorting by last_contact_at."""
        res = list_vgk_members(
            sort_by='last_contact_at',
            sort_dir='desc',
            page=1,
            page_size=10,
            current_user=self.admin_mr10001,
            db=self.db
        )
        self.assertTrue(res["success"])
    def test_08_server_side_visibility_restriction(self):
        """Req 10: Whitelist visibility — Poojitha and Admins see all; regular staff sees ONLY assigned/registered."""
        # Admin sees full platform members
        res_admin = list_vgk_members(
            current_user=self.admin_mr10001,
            db=self.db
        )
        total_admin = res_admin["total"]
        self.assertGreater(total_admin, 0)

        # Poojitha (MN10016) is in whitelist -> Sees full platform members
        if self.poojitha_mn10016:
            res_poojitha = list_vgk_members(
                current_user=self.poojitha_mn10016,
                db=self.db
            )
            self.assertEqual(res_poojitha["total"], total_admin)

        # Assign test partner to MR10016 (EA), not regular_agent
        self.test_partner.assigned_staff_id = self.ea_mr10016.id
        self.test_partner.registered_by_emp_code = 'VGK07102207'
        self.db.commit()

        # Regular agent (NOT in whitelist) queries members
        if self.regular_agent:
            res_agent = list_vgk_members(
                current_user=self.regular_agent,
                db=self.db
            )
            # Verify EVERY member returned to agent belongs strictly to her
            for m in res_agent["data"]:
                is_assigned_to_agent = (m.get("assigned_staff_id") == self.regular_agent.id)
                is_registered_by_agent = (m.get("registered_by_emp_code") == self.regular_agent.emp_code)
                self.assertTrue(
                    is_assigned_to_agent or is_registered_by_agent,
                    f"Ordinary agent was served member {m.get('partner_code')} not assigned/registered by her!"
                )
            # And test_partner (assigned to MR10016) MUST NOT appear in agent's results
            agent_partner_ids = [m["id"] for m in res_agent["data"]]
            self.assertNotIn(self.test_partner.id, agent_partner_ids)

    def test_09_verify_31_columns_in_frontend(self):
        """Req 11, 12, 13: Verify exact 31-column ordering and sticky styles."""
        html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../frontend/staff_vgk_members.html'))
        self.assertTrue(os.path.exists(html_path))
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract table thead inside Channel Partners card
        import re
        thead_match = re.search(r'id="totalBadge".*?<table>\s*<thead>\s*<tr>(.*?)</tr>\s*</thead>', content, re.DOTALL)
        self.assertIsNotNone(thead_match, "Could not find Channel Partners thead in staff_vgk_members.html")
        thead_html = thead_match.group(1)
        th_elements = re.findall(r'<th\b', thead_html)
        self.assertEqual(len(th_elements), 31, f"Expected exactly 31 table headers, found {len(th_elements)}")

        # Verify colspan="31" is used for loading and error rows
        self.assertIn('colspan="31"', content)

        # Verify sticky headers and first 3 columns
        self.assertIn('mb-sticky-1', content)
        self.assertIn('mb-sticky-2', content)
        self.assertIn('mb-sticky-3', content)
        self.assertIn('.table-scroll-wrap thead th', content)


if __name__ == '__main__':
    unittest.main()
