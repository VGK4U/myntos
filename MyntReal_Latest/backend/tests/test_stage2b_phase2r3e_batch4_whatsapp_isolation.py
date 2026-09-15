"""
MYNTOS Stage 2B Phase 2R-3E Batch 4 Verification Test Suite
Launch-Critical WhatsApp Multi-Tenant Isolation Hardening:
1. whatsapp.py :: get_inbox_thread()
2. whatsapp.py :: claim_whatsapp_conversation()

Test Requirements:
1. Tenant A cannot read Tenant B lead data through get_inbox_thread.
2. Company A cannot read Company B lead data where company access is not granted.
3. Authorized company access still works.
4. Tenant A cannot claim/mutate Tenant B lead/conversation.
5. Company A cannot claim/mutate Company B lead/conversation.
6. Authorized claim still works.
7. Shared phone with multiple leads does not arbitrarily select a winner.
8. Existing WhatsApp response/claim behavior remains intact for authorized cases.
9. Missing/invalid authorization fails closed.

Guarantees:
- Zero operational database mutations (all tests roll back).
- Baseline database verification (4,827 leads, 4,785 phones, 4,787 provenances).
"""

import os
import unittest
from datetime import datetime, timezone, date
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.models.crm import CRMLead, CRMLeadPhone
from app.models.staff import StaffEmployee, StaffCompanyMembership, StaffRole
from app.models.whatsapp import WAInbox
from app.api.v1.endpoints.whatsapp import (
    get_inbox_thread,
    claim_whatsapp_conversation,
    WAClaimConversationPayload,
)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:@localhost:5433/myntreal_dev")


class TestStage2BPhase2R3EBatch4WhatsAppIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(DATABASE_URL, poolclass=NullPool)
        cls.SessionLocal = sessionmaker(bind=cls.engine)

        with cls.engine.connect() as conn:
            cls.baseline_leads = conn.execute(text("SELECT COUNT(*) FROM crm_leads")).scalar()
            cls.baseline_phones = conn.execute(text("SELECT COUNT(*) FROM crm_lead_phones")).scalar()
            cls.baseline_provenances = conn.execute(text("SELECT COUNT(*) FROM crm_lead_phone_provenances")).scalar()

    @classmethod
    def tearDownClass(cls):
        with cls.engine.connect() as conn:
            current_leads = conn.execute(text("SELECT COUNT(*) FROM crm_leads")).scalar()
            current_phones = conn.execute(text("SELECT COUNT(*) FROM crm_lead_phones")).scalar()
            current_provenances = conn.execute(text("SELECT COUNT(*) FROM crm_lead_phone_provenances")).scalar()

        assert current_leads == cls.baseline_leads, f"Leads modified: {current_leads} vs {cls.baseline_leads}"
        assert current_phones == cls.baseline_phones, f"Phones modified: {current_phones} vs {cls.baseline_phones}"
        assert current_provenances == cls.baseline_provenances, f"Provenances modified: {current_provenances} vs {cls.baseline_provenances}"

    def setUp(self):
        self.conn = self.engine.connect()
        self.trans = self.conn.begin()
        self.session = self.SessionLocal(bind=self.conn)

        self.default_role = self.session.query(StaffRole).first()
        role_id = self.default_role.id if self.default_role else 1

        # Create staff fixtures inside test transaction:
        # Staff 1: Tenant 1, Company 1
        self.staff_t1_c1 = StaffEmployee(
            emp_code="TEST_STAFF_T1_C1",
            first_name="Staff",
            last_name="T1C1",
            full_name="Staff T1C1",
            email="staff_t1_c1@test.local",
            tenant_id=1,
            role_id=role_id,
            base_company_id=1,
            data_companies=[1],
            admin_scope="STAFF",
            status="active",
            password_hash="hash",
            date_of_joining=date(2026, 1, 1)
        )
        # Staff 2: Tenant 1, Company 2
        self.staff_t1_c2 = StaffEmployee(
            emp_code="TEST_STAFF_T1_C2",
            first_name="Staff",
            last_name="T1C2",
            full_name="Staff T1C2",
            email="staff_t1_c2@test.local",
            tenant_id=1,
            role_id=role_id,
            base_company_id=2,
            data_companies=[2],
            admin_scope="STAFF",
            status="active",
            password_hash="hash",
            date_of_joining=date(2026, 1, 1)
        )
        # Staff 3: Tenant 158, Company 95 (Tenant 2)
        self.staff_t2_c95 = StaffEmployee(
            emp_code="TEST_STAFF_T2_C95",
            first_name="Staff",
            last_name="T2C95",
            full_name="Staff T2C95",
            email="staff_t2_c95@test.local",
            tenant_id=158,
            role_id=role_id,
            base_company_id=95,
            data_companies=[95],
            admin_scope="STAFF",
            status="active",
            password_hash="hash",
            date_of_joining=date(2026, 1, 1)
        )
        self.session.add_all([self.staff_t1_c1, self.staff_t1_c2, self.staff_t2_c95])
        self.session.flush()

        # Add memberships
        self.session.add_all([
            StaffCompanyMembership(staff_id=self.staff_t1_c1.id, company_id=1, tenant_id=1, is_primary=True, is_active=True),
            StaffCompanyMembership(staff_id=self.staff_t1_c2.id, company_id=2, tenant_id=1, is_primary=True, is_active=True),
            StaffCompanyMembership(staff_id=self.staff_t2_c95.id, company_id=95, tenant_id=158, is_primary=True, is_active=True),
        ])
        self.session.flush()

    def tearDown(self):
        self.session.close()
        if self.trans.is_active:
            self.trans.rollback()
        self.conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Tenant A cannot read Tenant B lead data through get_inbox_thread
    # ─────────────────────────────────────────────────────────────────────────
    def test_01_tenant_a_cannot_read_tenant_b_lead_data(self):
        """Staff in Tenant 1 must never see lead details belonging to Tenant 158."""
        shared_phone = "9888000001"
        lead_t2 = CRMLead(
            name="Confidential Tenant 2 Lead",
            phone=shared_phone,
            tenant_id=158,
            company_id=95,
            budget_min=5000000,
            deal_value=6000000,
            description="Confidential acquisition deal"
        )
        self.session.add(lead_t2)
        self.session.flush()

        # Staff in Tenant 1 requests thread for shared_phone
        res = get_inbox_thread(phone=shared_phone, db=self.session, current_user=self.staff_t1_c1)
        self.assertTrue(res["success"])
        # Must return zero leads from Tenant 2
        crm_leads = res["crm_leads"]
        self.assertEqual(len(crm_leads), 0)
        # Contact info must not leak Tenant 2's confidential customer name
        contact_info = res["contact_info"]
        self.assertNotEqual(contact_info.get("resolved_name"), "Confidential Tenant 2 Lead")
        # Ensure no CRM entry in existing_in
        for item in contact_info.get("existing_in", []):
            self.assertNotEqual(item.get("type"), "crm")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Company A cannot read Company B lead data where access is not granted
    # ─────────────────────────────────────────────────────────────────────────
    def test_02_company_a_cannot_read_company_b_lead_data(self):
        """Staff in Company 1 must not see lead details in Company 2 within same Tenant."""
        shared_phone = "9888000002"
        lead_c2 = CRMLead(
            name="Company 2 Private Lead",
            phone=shared_phone,
            tenant_id=1,
            company_id=2,
            budget_min=1000000,
            deal_value=1200000,
            description="Exclusive Company 2 customer"
        )
        self.session.add(lead_c2)
        self.session.flush()

        # Staff restricted to Company 1 requests thread
        res = get_inbox_thread(phone=shared_phone, db=self.session, current_user=self.staff_t1_c1)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["crm_leads"]), 0)
        self.assertNotEqual(res["contact_info"].get("resolved_name"), "Company 2 Private Lead")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Authorized company access still works
    # ─────────────────────────────────────────────────────────────────────────
    def test_03_authorized_company_access_still_works(self):
        """Staff in Company 1 must see lead details belonging to Company 1."""
        target_phone = "9888000003"
        lead_c1 = CRMLead(
            name="Authorized Company 1 Lead",
            phone=target_phone,
            email="c1_client@test.local",
            tenant_id=1,
            company_id=1,
            budget_min=2000000,
            city="Hyderabad",
            state="Telangana",
            deal_value=2500000,
            description="High intent buyer"
        )
        self.session.add(lead_c1)
        self.session.flush()

        res = get_inbox_thread(phone=target_phone, db=self.session, current_user=self.staff_t1_c1)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["crm_leads"]), 1)
        lead_ret = res["crm_leads"][0]
        self.assertEqual(lead_ret["id"], lead_c1.id)
        self.assertEqual(lead_ret["name"], "Authorized Company 1 Lead")
        self.assertEqual(lead_ret["city"], "Hyderabad")
        self.assertEqual(res["contact_info"]["resolved_name"], "Authorized Company 1 Lead")
        self.assertEqual(res["contact_info"]["existing_in"][0]["id"], lead_c1.id)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Tenant A cannot claim/mutate Tenant B lead or conversation
    # ─────────────────────────────────────────────────────────────────────────
    def test_04_tenant_a_cannot_claim_or_mutate_tenant_b_lead(self):
        """Staff in Tenant 1 claiming a conversation must never mutate a lead or inbox in Tenant 158."""
        target_phone = "9888000004"
        lead_t2 = CRMLead(
            name="Unassigned Tenant 2 Lead",
            phone=target_phone,
            tenant_id=158,
            company_id=95,
            handler_type="unassigned",
            handler_id=None,
            telecaller_id=None
        )
        inbox_t2 = WAInbox(
            from_phone=f"91{target_phone}",
            company_id=95,
            status="new",
            assigned_to_emp_id=None,
            body_text="Inbound from Tenant 2"
        )
        self.session.add_all([lead_t2, inbox_t2])
        self.session.flush()

        payload = WAClaimConversationPayload(phone=target_phone)
        res = claim_whatsapp_conversation(payload=payload, db=self.session, current_user=self.staff_t1_c1)
        self.assertTrue(res["success"])

        # Reload from DB to verify zero mutation
        self.session.refresh(lead_t2)
        self.session.refresh(inbox_t2)
        self.assertEqual(lead_t2.handler_type, "unassigned")
        self.assertIsNone(lead_t2.handler_id)
        self.assertIsNone(lead_t2.telecaller_id)
        self.assertIsNone(inbox_t2.assigned_to_emp_id)
        self.assertEqual(inbox_t2.status, "new")

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Company A cannot claim/mutate Company B lead or conversation
    # ─────────────────────────────────────────────────────────────────────────
    def test_05_company_a_cannot_claim_or_mutate_company_b_lead(self):
        """Staff restricted to Company 1 must never claim or mutate Company 2 lead or inbox."""
        target_phone = "9888000005"
        lead_c2 = CRMLead(
            name="Unassigned Company 2 Lead",
            phone=target_phone,
            tenant_id=1,
            company_id=2,
            handler_type="unassigned",
            handler_id=None,
            telecaller_id=None
        )
        inbox_c2 = WAInbox(
            from_phone=f"91{target_phone}",
            company_id=2,
            status="new",
            assigned_to_emp_id=None,
            body_text="Inbound to Company 2"
        )
        self.session.add_all([lead_c2, inbox_c2])
        self.session.flush()

        payload = WAClaimConversationPayload(phone=target_phone)
        res = claim_whatsapp_conversation(payload=payload, db=self.session, current_user=self.staff_t1_c1)
        self.assertTrue(res["success"])

        self.session.refresh(lead_c2)
        self.session.refresh(inbox_c2)
        self.assertEqual(lead_c2.handler_type, "unassigned")
        self.assertIsNone(lead_c2.handler_id)
        self.assertIsNone(lead_c2.telecaller_id)
        self.assertIsNone(inbox_c2.assigned_to_emp_id)
        self.assertEqual(inbox_c2.status, "new")

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Authorized claim still works
    # ─────────────────────────────────────────────────────────────────────────
    def test_06_authorized_claim_still_works(self):
        """Staff in Company 1 claiming conversation for Company 1 updates inbox and unassigned lead."""
        target_phone = "9888000006"
        lead_c1 = CRMLead(
            name="Unassigned Company 1 Lead",
            phone=target_phone,
            tenant_id=1,
            company_id=1,
            handler_type="unassigned",
            handler_id=None,
            telecaller_id=None
        )
        inbox_c1 = WAInbox(
            from_phone=f"91{target_phone}",
            company_id=1,
            status="new",
            assigned_to_emp_id=None,
            body_text="Inbound to Company 1"
        )
        self.session.add_all([lead_c1, inbox_c1])
        self.session.flush()

        payload = WAClaimConversationPayload(phone=target_phone)
        res = claim_whatsapp_conversation(payload=payload, db=self.session, current_user=self.staff_t1_c1)
        self.assertTrue(res["success"])

        self.session.refresh(lead_c1)
        self.session.refresh(inbox_c1)
        # Lead assigned to staff
        self.assertEqual(lead_c1.handler_type, "staff")
        self.assertEqual(lead_c1.handler_id, self.staff_t1_c1.emp_code)
        self.assertEqual(lead_c1.telecaller_id, self.staff_t1_c1.id)
        # Inbox assigned to staff
        self.assertEqual(inbox_c1.assigned_to_emp_id, self.staff_t1_c1.id)
        self.assertEqual(inbox_c1.status, "in_progress")
        self.assertTrue(inbox_c1.is_read)

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Shared phone with multiple leads does not arbitrarily select a winner
    # ─────────────────────────────────────────────────────────────────────────
    def test_07_shared_phone_does_not_arbitrarily_select_winner(self):
        """When multiple leads share a phone, claim_whatsapp_conversation must not mutate either lead."""
        shared_phone = "9888000007"
        lead_a = CRMLead(
            name="Shared Lead A",
            phone=shared_phone,
            tenant_id=1,
            company_id=1,
            handler_type="unassigned",
            handler_id=None,
            telecaller_id=None
        )
        lead_b = CRMLead(
            name="Shared Lead B",
            phone=None,
            alternate_phone=shared_phone,
            tenant_id=1,
            company_id=1,
            handler_type="unassigned",
            handler_id=None,
            telecaller_id=None
        )
        inbox_shared = WAInbox(
            from_phone=f"91{shared_phone}",
            company_id=1,
            status="new",
            assigned_to_emp_id=None,
            body_text="Inbound on shared phone"
        )
        self.session.add_all([lead_a, lead_b, inbox_shared])
        self.session.flush()

        # Claim without explicit lead_id
        payload = WAClaimConversationPayload(phone=shared_phone)
        res = claim_whatsapp_conversation(payload=payload, db=self.session, current_user=self.staff_t1_c1)
        self.assertTrue(res["success"])

        self.session.refresh(lead_a)
        self.session.refresh(lead_b)
        self.session.refresh(inbox_shared)

        # Neither lead arbitrarily mutated
        self.assertEqual(lead_a.handler_type, "unassigned")
        self.assertIsNone(lead_a.handler_id)
        self.assertEqual(lead_b.handler_type, "unassigned")
        self.assertIsNone(lead_b.handler_id)
        # Inbox record is claimed
        self.assertEqual(inbox_shared.assigned_to_emp_id, self.staff_t1_c1.id)

        # In get_inbox_thread, both candidates must be preserved without truncation
        thread_res = get_inbox_thread(phone=shared_phone, db=self.session, current_user=self.staff_t1_c1)
        self.assertEqual(len(thread_res["crm_leads"]), 2)
        lead_ids = {l["id"] for l in thread_res["crm_leads"]}
        self.assertEqual(lead_ids, {lead_a.id, lead_b.id})

    # ─────────────────────────────────────────────────────────────────────────
    # 8. Existing WhatsApp response & explicit lead claim intact
    # ─────────────────────────────────────────────────────────────────────────
    def test_08_explicit_lead_claim_and_response_contract_intact(self):
        """Passing explicit lead_id mutates only that lead; response contract preserves expected keys."""
        shared_phone = "9888000008"
        lead_x = CRMLead(
            name="Target Lead X",
            phone=shared_phone,
            tenant_id=1,
            company_id=1,
            handler_type="unassigned",
            handler_id=None,
            telecaller_id=None
        )
        lead_y = CRMLead(
            name="Target Lead Y",
            phone=None,
            alternate_phone=shared_phone,
            tenant_id=1,
            company_id=1,
            handler_type="unassigned",
            handler_id=None,
            telecaller_id=None
        )
        self.session.add_all([lead_x, lead_y])
        self.session.flush()

        # Explicitly claim lead_y
        payload = WAClaimConversationPayload(phone=shared_phone, lead_id=lead_y.id)
        res = claim_whatsapp_conversation(payload=payload, db=self.session, current_user=self.staff_t1_c1)
        self.assertTrue(res["success"])

        self.session.refresh(lead_x)
        self.session.refresh(lead_y)
        self.assertEqual(lead_x.handler_type, "unassigned")
        self.assertEqual(lead_y.handler_type, "staff")
        self.assertEqual(lead_y.handler_id, self.staff_t1_c1.emp_code)
        self.assertEqual(lead_y.telecaller_id, self.staff_t1_c1.id)

        # Verify get_inbox_thread contract keys
        thread_res = get_inbox_thread(phone=shared_phone, db=self.session, current_user=self.staff_t1_c1)
        expected_keys = {"success", "phone", "total", "data", "contact_info", "crm_leads", "walkins", "service_tickets", "staff_contacts"}
        self.assertTrue(expected_keys.issubset(set(thread_res.keys())))

    # ─────────────────────────────────────────────────────────────────────────
    # 9. Missing / invalid authorization fails closed
    # ─────────────────────────────────────────────────────────────────────────
    def test_09_missing_or_invalid_authorization_fails_closed(self):
        """Missing tenant or empty company access fails closed with HTTP 403."""
        # 1. Unassigned staff object with no tenant
        staff_no_tenant = StaffEmployee(
            emp_code="NO_TENANT",
            first_name="No",
            last_name="Tenant",
            full_name="No Tenant",
            email="no_tenant@test.local",
            base_company_id=None,
            data_companies=[]
        )
        # Explicitly set tenant_id to None on Python object
        setattr(staff_no_tenant, 'tenant_id', None)

        with self.assertRaises(HTTPException) as ctx:
            get_inbox_thread(phone="9888000009", db=self.session, current_user=staff_no_tenant)
        self.assertEqual(ctx.exception.status_code, 403)

        with self.assertRaises(HTTPException) as ctx:
            claim_whatsapp_conversation(
                payload=WAClaimConversationPayload(phone="9888000009"),
                db=self.session,
                current_user=staff_no_tenant
            )
        self.assertEqual(ctx.exception.status_code, 403)

        # 2. Staff with valid tenant but zero company access
        staff_no_comp = StaffEmployee(
            emp_code="NO_COMP",
            first_name="No",
            last_name="Comp",
            full_name="No Comp",
            email="no_comp@test.local",
            tenant_id=1,
            role_id=self.default_role.id if self.default_role else 1,
            base_company_id=None,
            data_companies=[],
            admin_scope="STAFF",
            status="active",
            password_hash="hash",
            date_of_joining=date(2026, 1, 1)
        )
        self.session.add(staff_no_comp)
        self.session.flush()

        with self.assertRaises(HTTPException) as ctx:
            get_inbox_thread(phone="9888000009", db=self.session, current_user=staff_no_comp)
        self.assertEqual(ctx.exception.status_code, 403)

        with self.assertRaises(HTTPException) as ctx:
            claim_whatsapp_conversation(
                payload=WAClaimConversationPayload(phone="9888000009"),
                db=self.session,
                current_user=staff_no_comp
            )
        self.assertEqual(ctx.exception.status_code, 403)

        # Cross-tenant explicit lead_id claim attempt fails with 403
        lead_t2 = CRMLead(
            name="Forbidden Tenant 2 Lead",
            phone="9888000010",
            tenant_id=158,
            company_id=95
        )
        self.session.add(lead_t2)
        self.session.flush()

        with self.assertRaises(HTTPException) as ctx:
            claim_whatsapp_conversation(
                payload=WAClaimConversationPayload(phone="9888000010", lead_id=lead_t2.id),
                db=self.session,
                current_user=self.staff_t1_c1
            )
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
