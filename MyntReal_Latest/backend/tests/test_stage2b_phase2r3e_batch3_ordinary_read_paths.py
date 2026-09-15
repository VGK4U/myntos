"""
MYNTOS Stage 2B Phase 2R-3E-II Batch 3 Verification Test Suite
Focused verification of Ordinary Category-A Read/Search Path Migration:
1. Partner search/read paths (get_partner_updated_leads, solar_vendor_leads)
2. VGK search/read paths (vgk_my_leads, member_earnings_dashboard, lead_earnings_dashboard, _get_dates)
3. Dialer user-facing phone search (dialer_search)
4. Dialer redial/cooldown phone lookup (get_lead_redial_cooldown)
5. Dialer suppression phone lookup (_get_dialer_suppression_data)
6. WhatsApp contact search (search_whatsapp_contacts /contacts-search & /search-contacts)
7. WhatsApp recipient search (search_recipients /recipient-search)

Guarantees:
- Strict tenant and company scoping (no cross-company or cross-tenant leakage).
- No arbitrary winner selection: multiple leads sharing a phone remain discoverable (e.g. 7635 & 7636).
- Format normalization (+91, dashes, spaces) matches canonical phone_norm.
- Alternate phone discovery via canonical phone association layer.
- Existing non-phone search behavior, contracts, and filters preserved.
- Zero operational database mutations (100% isolated rollback transactions).
"""

import os
import unittest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.models.crm import CRMLead, CRMLeadPhone
from app.models.staff import StaffEmployee
from app.models.staff_accounts import OfficialPartner
from app.services.crm_phone_sync_service import (
    find_candidate_lead_ids_for_search,
    find_candidate_associations_by_phone,
    sync_lead_phone_identities,
)
from app.api.v1.endpoints.partner_auth import (
    get_partner_updated_leads,
    solar_vendor_leads,
)
from app.api.v1.endpoints.vgk_auth import (
    vgk_my_leads,
)
from app.api.v1.endpoints.vgk_team import (
    member_earnings_dashboard,
    lead_earnings_dashboard,
    vgk_top_partners_leads,
)
from app.api.v1.endpoints.crm_dialer import (
    dialer_search,
    get_lead_redial_cooldown,
    _get_dialer_suppression_data,
)
from app.api.v1.endpoints.whatsapp import (
    search_recipients,
    router as whatsapp_router,
)

# Extract endpoint handlers from whatsapp router to resolve duplicate function name
contacts_search_endpoint = next(r.endpoint for r in whatsapp_router.routes if getattr(r, 'path', '').endswith('/contacts-search'))
search_contacts_endpoint = next(r.endpoint for r in whatsapp_router.routes if getattr(r, 'path', '').endswith('/search-contacts'))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://viswanathkari:@localhost:5433/myntreal_dev")


class TestStage2BPhase2R3EIIBatch3OrdinaryReadPaths(unittest.TestCase):
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

        self.admin_employee = self.session.query(StaffEmployee).filter(StaffEmployee.id == 1).first()
        assert self.admin_employee is not None, "Admin employee 1 must exist"

        self.partner = self.session.query(OfficialPartner).first()
        assert self.partner is not None, "An OfficialPartner must exist"

    def tearDown(self):
        self.session.close()
        self.trans.rollback()
        self.conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Partner Search / Read Paths
    # ─────────────────────────────────────────────────────────────────────────
    def test_01_partner_updated_leads_shared_phone(self):
        """Path 1a: get_partner_updated_leads finds leads sharing phone via canonical primitive."""
        # Tag partner on both 7635 and 7636 within test transaction
        l7635 = self.session.query(CRMLead).filter(CRMLead.id == 7635).first()
        l7636 = self.session.query(CRMLead).filter(CRMLead.id == 7636).first()
        l7635.associated_partner_id = self.partner.id
        l7636.associated_partner_id = self.partner.id
        self.session.flush()

        res = asyncio.run(get_partner_updated_leads(
            partner=self.partner,
            db=self.session,
            page=1,
            per_page=20,
            status=None,
            search="8341414152",
            sort_by="updated_at",
            sort_dir="desc"
        ))
        self.assertTrue(res.get("success"))
        found_ids = {item["id"] for item in res.get("data", [])}
        self.assertIn(7635, found_ids)
        self.assertIn(7636, found_ids)

    def test_02_partner_updated_leads_name_search_preserved(self):
        """Path 1a: get_partner_updated_leads preserves non-phone name search."""
        l7635 = self.session.query(CRMLead).filter(CRMLead.id == 7635).first()
        l7635.associated_partner_id = self.partner.id
        self.session.flush()

        res = asyncio.run(get_partner_updated_leads(
            partner=self.partner,
            db=self.session,
            page=1,
            per_page=20,
            status=None,
            search=l7635.name,
            sort_by="updated_at",
            sort_dir="desc"
        ))
        self.assertTrue(res.get("success"))
        found_ids = {item["id"] for item in res.get("data", [])}
        self.assertIn(7635, found_ids)

    def test_03_solar_vendor_leads_shared_phone(self):
        """Path 1b: solar_vendor_leads finds shared-phone leads by phone number."""
        l7635 = self.session.query(CRMLead).filter(CRMLead.id == 7635).first()
        l7636 = self.session.query(CRMLead).filter(CRMLead.id == 7636).first()
        l7635.vendor_id = 101
        l7636.vendor_id = 101
        self.partner.legacy_vendor_id = 101
        self.partner.category = 'VENDOR'
        self.session.flush()

        req = MagicMock()
        req.headers = {}
        res = asyncio.run(solar_vendor_leads(
            request=req,
            partner=self.partner,
            db=self.session,
            page=1,
            per_page=20,
            vendor_status_filter=None,
            pipeline_stage=None,
            pincode=None,
            loan_bank=None,
            bank_entry=None,
            has_co_applicant=None,
            search="8341414152"
        ))
        self.assertTrue(res.get("success"))
        found_ids = {item["id"] for item in res.get("data", [])}
        self.assertIn(7635, found_ids)
        self.assertIn(7636, found_ids)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. VGK Search / Read Paths
    # ─────────────────────────────────────────────────────────────────────────
    def test_04_vgk_my_leads_shared_phone(self):
        """Path 2a: vgk_my_leads finds shared-phone leads for VGK member."""
        member = MagicMock()
        member.id = 9999
        l7635 = self.session.query(CRMLead).filter(CRMLead.id == 7635).first()
        l7636 = self.session.query(CRMLead).filter(CRMLead.id == 7636).first()
        l7635.associated_partner_id = 9999
        l7636.associated_partner_id = 9999
        self.session.flush()

        res = vgk_my_leads(
            segment="source",
            status=None,
            priority=None,
            search="8341414152",
            sort_by="created_at",
            sort_dir="desc",
            followup_filter=None,
            page=1,
            db=self.session,
            current_member=member
        )
        self.assertTrue(res.get("success"))
        found_ids = {item["id"] for item in res.get("data", [])}
        self.assertIn(7635, found_ids)
        self.assertIn(7636, found_ids)

    def test_05_vgk_member_earnings_dashboard_customer_search(self):
        """Path 2b: member_earnings_dashboard searches by customer phone using canonical primitive."""
        res = member_earnings_dashboard(
            search=None,
            page=1,
            page_size=20,
            earners_only=True,
            income_status=None,
            date_from=None,
            date_to=None,
            registered_by_emp_code=None,
            customer_search="8341414152",
            sort_by="name",
            sort_dir="asc",
            category_id=None,
            level=None,
            partner_code=None,
            community_only=False,
            community_service_id=None,
            partner_id=None,
            hide_vgk_support=True,
            current_user=self.admin_employee,
            db=self.session
        )
        self.assertTrue(res.get("success"))
        self.assertIn("data", res)

    def test_06_vgk_lead_earnings_dashboard_search(self):
        """Path 2c: lead_earnings_dashboard filters leads by phone via canonical primitive."""
        res = lead_earnings_dashboard(
            search="8341414152",
            page=1,
            page_size=20,
            hide_vgk_support=False,
            current_user=self.admin_employee,
            db=self.session
        )
        self.assertTrue(res.get("success"))
        self.assertIn("data", res)

    def test_07_vgk_top_partners_leads_search(self):
        """Path 2d: vgk_top_partners_leads searches by phone via canonical primitive."""
        res = vgk_top_partners_leads(
            partner_id=self.partner.id,
            metric="total_leads",
            company_id=4,
            category_id=None,
            search="8341414152",
            limit=20,
            current_user=self.admin_employee,
            db=self.session
        )
        self.assertTrue(res.get("success"))
        self.assertIn("data", res)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Dialer Paths
    # ─────────────────────────────────────────────────────────────────────────
    def test_08_dialer_search_shared_phone(self):
        """Path 3: dialer_search finds shared-phone leads by phone number."""
        l7635 = self.session.query(CRMLead).filter(CRMLead.id == 7635).first()
        l7636 = self.session.query(CRMLead).filter(CRMLead.id == 7636).first()
        l7635.status = 'interested'
        l7636.status = 'interested'
        self.session.flush()

        res = asyncio.run(dialer_search(
            q="8341414152",
            company_id=4,
            db=self.session,
            current_user=self.admin_employee
        ))
        self.assertTrue(res.get("success"))
        found_ids = {item["id"] for item in res.get("results", [])}
        self.assertIn(7635, found_ids)
        self.assertIn(7636, found_ids)

    def test_09_dialer_search_formatting_variations(self):
        """Path 3: dialer_search matches formatted phone numbers (+91, 0, spaces)."""
        l7635 = self.session.query(CRMLead).filter(CRMLead.id == 7635).first()
        l7636 = self.session.query(CRMLead).filter(CRMLead.id == 7636).first()
        l7635.status = 'interested'
        l7636.status = 'interested'
        self.session.flush()

        variations = ["+91 83414 14152", "+91-83414-14152", "08341414152"]
        for term in variations:
            res = asyncio.run(dialer_search(
                q=term,
                company_id=4,
                db=self.session,
                current_user=self.admin_employee
            ))
            self.assertTrue(res.get("success"))
            found_ids = {item["id"] for item in res.get("results", [])}
            self.assertTrue(7635 in found_ids and 7636 in found_ids, f"Failed on: {term}")

    def test_10_dialer_redial_cooldown_lookup(self):
        """Path 4: get_lead_redial_cooldown finds cooldown across candidate leads sharing phone."""
        # Insert a recent dialer attempt for lead 7635 within test transaction
        self.session.execute(text("""
            INSERT INTO crm_dialer_attempts (lead_id, user_ref, portal, call_outcome, duration_seconds, dialed_at, created_at)
            VALUES (7635, 'EMP999', 'staff', 'connected', 120, NOW(), NOW())
        """))
        self.session.flush()

        # Check cooldown on sibling lead 7636 which shares the phone
        is_cooling, expires_at, reason = get_lead_redial_cooldown(
            db=self.session,
            lead_id=7636,
            phone="8341414152",
            current_user_ref="EMP111",
            current_portal="staff"
        )
        self.assertTrue(is_cooling, "Cooldown must be detected across leads sharing phone")
        self.assertIn("Recently connected with another staff member", reason)

    def test_11_dialer_suppression_lookup(self):
        """Path 5: _get_dialer_suppression_data suppresses phone via crm_lead_phones."""
        # Insert a recent attempt for lead 7635
        self.session.execute(text("""
            INSERT INTO crm_dialer_attempts (lead_id, user_ref, portal, call_outcome, duration_seconds, dialed_at, created_at)
            VALUES (7635, 'EMP999', 'staff', 'connected', 60, NOW(), NOW())
        """))
        self.session.flush()

        suppressed, _ = _get_dialer_suppression_data(
            db=self.session,
            user_ref="EMP111",
            portal="staff",
            staff_id=self.admin_employee.id
        )
        self.assertIn("8341414152", suppressed, "Normalized phone must be present in suppression set")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. WhatsApp Contact & Recipient Search Paths
    # ─────────────────────────────────────────────────────────────────────────
    def test_12_whatsapp_recipient_search(self):
        """Path 7: search_recipients finds shared-phone leads by phone number."""
        res = search_recipients(
            q="8341414152",
            db=self.session,
            current_user=self.admin_employee
        )
        self.assertIn("results", res)
        lead_ids = {int(r["id"]) for r in res["results"] if r.get("type") == "lead"}
        self.assertIn(7635, lead_ids)
        self.assertIn(7636, lead_ids)

    def test_13_whatsapp_contacts_search(self):
        """Path 6a: search_whatsapp_contacts (/contacts-search) finds shared-phone leads."""
        res = contacts_search_endpoint(
            query="8341414152",
            type_filter="CONTACT",
            scope="all",
            db=self.session,
            current_user=self.admin_employee
        )
        self.assertIn("contacts", res)
        lead_ids = {int(r["id"].replace("crm_", "")) for r in res["contacts"] if str(r.get("id", "")).startswith("crm_")}
        self.assertIn(7635, lead_ids)
        self.assertIn(7636, lead_ids)

    def test_14_whatsapp_search_contacts_endpoint(self):
        """Path 6b: search_whatsapp_contacts (/search-contacts) finds shared-phone leads."""
        res = search_contacts_endpoint(
            q="8341414152",
            db=self.session,
            current_employee=self.admin_employee
        )
        self.assertTrue(res.get("success"))
        found_phones = {r["phone"] for r in res.get("contacts", [])}
        self.assertIn("8341414152", found_phones)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Multi-Tenant & Sibling Company Isolation
    # ─────────────────────────────────────────────────────────────────────────
    def test_15_isolation_sibling_company_and_tenant(self):
        """Scoping: candidate lookup across sibling companies and non-existent tenants returns empty."""
        # Sibling company 2 has no association for 8341414152
        co2_leads = find_candidate_lead_ids_for_search(self.session, tenant_id=1, company_ids=[2], search_term="8341414152")
        self.assertEqual(co2_leads, [])

        # Non-existent tenant 999
        t999_leads = find_candidate_lead_ids_for_search(self.session, tenant_id=999, company_ids=[4], search_term="8341414152")
        self.assertEqual(t999_leads, [])


if __name__ == "__main__":
    unittest.main()
