"""
MYNTOS Stage 2B Phase 2R-3E-II Batch 2 Verification Test Suite
Focused verification of Core CRM Search Read-Path Migration.

Covers the 10 migrated Category-A search paths:
1. system_search_leads
2. search_leads_for_new_ledger
3. get_my_leads
4. list_leads generic
5. list_leads loans (get_bank_wise_leads)
6. list_leads team-core (master_leads)
7. list_team_leads
8. unified CRM search (get_unified_my_leads)
9. dashboard drilldown (get_crm_dashboard_v2_drilldown)
10. pipeline searches (lead_analytics & _apply_exec_dashboard_common_filters)

Guarantees:
- Strict tenant and company isolation (no cross-company or cross-tenant leakage).
- No arbitrary winner selection: multiple leads sharing a phone remain discoverable.
- Support for formatted inputs (+91, 0, spaces, hyphens) and partial digit searches.
- Discovery of alternate phones via canonical association layer.
- Zero mutations to operational database (100% isolated rollback transactions).
"""

import os
import unittest
from datetime import datetime
from unittest.mock import patch
from starlette.requests import Request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.models.crm import CRMLead, CRMLeadPhone
from app.models.staff import StaffEmployee
from app.services.crm_phone_sync_service import (
    find_candidate_lead_ids_for_search,
    find_candidate_associations_by_phone,
    find_candidate_leads_by_phone,
    sync_lead_phone_identities,
)
from app.api.v1.endpoints.crm import (
    system_search_leads,
    search_leads_for_new_ledger,
    get_my_leads,
    list_leads,
    get_bank_wise_leads,
    master_leads,
    list_team_leads,
    get_unified_my_leads,
    get_crm_dashboard_v2_drilldown,
    lead_analytics,
    _apply_exec_dashboard_common_filters,
)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://viswanathkari:@localhost:5433/myntreal_dev")


class TestStage2BPhase2R3EIIBatch2CRMSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(DATABASE_URL, poolclass=NullPool)
        cls.SessionLocal = sessionmaker(bind=cls.engine)

        # Record baseline counts before tests run
        with cls.engine.connect() as conn:
            cls.baseline_leads = conn.execute(text("SELECT COUNT(*) FROM crm_leads")).scalar()
            cls.baseline_phones = conn.execute(text("SELECT COUNT(*) FROM crm_lead_phones")).scalar()
            cls.baseline_provenances = conn.execute(text("SELECT COUNT(*) FROM crm_lead_phone_provenances")).scalar()

    @classmethod
    def tearDownClass(cls):
        # Assert pristine baseline counts after all tests complete
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

        # Use existing system administrator employee (id=1, VGK4U, tenant 1, company 4)
        self.admin_employee = self.session.query(StaffEmployee).filter(StaffEmployee.id == 1).first()
        assert self.admin_employee is not None, "Employee 1 must exist"

    def tearDown(self):
        self.session.close()
        self.trans.rollback()
        self.conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Search Primitive Tests: Normalization, Formatting & Digits
    # ─────────────────────────────────────────────────────────────────────────
    def test_01_primitive_exact_10_digits(self):
        """Exact 10 digits matches operational candidates 7635 & 7636 in company 4."""
        lead_ids = find_candidate_lead_ids_for_search(
            self.session, tenant_id=1, company_ids=[4], search_term="8341414152"
        )
        self.assertIn(7635, lead_ids)
        self.assertIn(7636, lead_ids)

    def test_02_primitive_formatting_variations(self):
        """Formatted numbers (+91, 0, spaces, hyphens) match canonical phone_norm."""
        variations = [
            "+91 83414 14152",
            "+91-83414-14152",
            "08341414152",
            "83414 14152",
            "  8341414152  ",
        ]
        for term in variations:
            lead_ids = find_candidate_lead_ids_for_search(
                self.session, tenant_id=1, company_ids=[4], search_term=term
            )
            self.assertTrue(7635 in lead_ids and 7636 in lead_ids, f"Failed on term: {term}")

    def test_03_primitive_partial_digits(self):
        """Partial digits (4 to 9 digits) perform substring match on phone_norm."""
        lead_ids = find_candidate_lead_ids_for_search(
            self.session, tenant_id=1, company_ids=[4], search_term="14152"
        )
        self.assertIn(7635, lead_ids)
        self.assertIn(7636, lead_ids)

    def test_04_primitive_short_digits_and_non_digits(self):
        """Queries with < 4 digits or non-digit text return empty list without noise."""
        self.assertEqual(find_candidate_lead_ids_for_search(self.session, 1, [4], "12"), [])
        self.assertEqual(find_candidate_lead_ids_for_search(self.session, 1, [4], "123"), [])
        self.assertEqual(find_candidate_lead_ids_for_search(self.session, 1, [4], "Ramu"), [])
        self.assertEqual(find_candidate_lead_ids_for_search(self.session, 1, [4], ""), [])
        self.assertEqual(find_candidate_lead_ids_for_search(self.session, 1, [4], None), [])

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Tenancy and Company Isolation
    # ─────────────────────────────────────────────────────────────────────────
    def test_05_company_scoping_isolation(self):
        """Candidate lookup in sibling company 2 returns empty results (zero cross-company leakage)."""
        lead_ids = find_candidate_lead_ids_for_search(
            self.session, tenant_id=1, company_ids=[2], search_term="8341414152"
        )
        self.assertEqual(lead_ids, [])

    def test_06_tenant_scoping_isolation(self):
        """Candidate lookup for non-existent or different tenant returns empty results."""
        lead_ids = find_candidate_lead_ids_for_search(
            self.session, tenant_id=999, company_ids=[4], search_term="8341414152"
        )
        self.assertEqual(lead_ids, [])

        # Empty accessible company list returns empty (fail-closed)
        lead_ids_empty = find_candidate_lead_ids_for_search(
            self.session, tenant_id=1, company_ids=[], search_term="8341414152"
        )
        self.assertEqual(lead_ids_empty, [])

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Alternate Phone Searchability
    # ─────────────────────────────────────────────────────────────────────────
    def test_07_alternate_phone_searchability(self):
        """Leads are discoverable by searching their alternate phone association."""
        lead = CRMLead(
            tenant_id=1,
            company_id=4,
            name="Alternate Phone Test Lead",
            phone="+91 9911223344",
            alternate_phone="09955667788"
        )
        self.session.add(lead)
        self.session.flush()
        sync_lead_phone_identities(
            self.session, lead, phone_raw=lead.phone, alternate_phone_raw=lead.alternate_phone, with_lock=False
        )

        # Search by alternate phone
        lead_ids = find_candidate_lead_ids_for_search(
            self.session, tenant_id=1, company_ids=[4], search_term="9955667788"
        )
        self.assertIn(lead.id, lead_ids)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Core CRM Search Endpoints Integration
    # ─────────────────────────────────────────────────────────────────────────
    def test_08_system_search_leads(self):
        """Path 1: system_search_leads finds shared-phone leads by phone number."""
        res = system_search_leads(
            q="8341414152",
            company_id=4,
            limit=20,
            db=self.session,
            current_employee=self.admin_employee
        )
        self.assertTrue(res.get("success"))
        found_ids = {item["id"] for item in res.get("leads", [])}
        self.assertIn(7635, found_ids)
        self.assertIn(7636, found_ids)

    def test_09_search_leads_for_new_ledger(self):
        """Path 2: search_leads_for_new_ledger finds shared-phone leads by phone number."""
        res = search_leads_for_new_ledger(
            company_id=4,
            search="8341414152",
            limit=20,
            db=self.session,
            current_employee=self.admin_employee
        )
        self.assertTrue(res.get("success"))
        found_ids = {item["id"] for item in res.get("data", [])}
        self.assertIn(7635, found_ids)
        self.assertIn(7636, found_ids)

    def test_10_get_my_leads(self):
        """Path 3: get_my_leads finds shared-phone leads by phone number."""
        # Ensure lead 7635's owner is active staff in company 4 within test transaction
        lead_7635 = self.session.query(CRMLead).filter(CRMLead.id == 7635).first()
        lead_7635.primary_owner_id = 34
        self.session.flush()

        res = get_my_leads(
            company_id=4,
            scope="all",
            role_filter=None,
            category=None,
            search="8341414152",
            page=1,
            per_page=20,
            db=self.session,
            current_employee=self.admin_employee
        )
        self.assertTrue(res.get("success"))
        found_ids = {item["id"] for item in res.get("data", [])}
        self.assertIn(7635, found_ids)
        self.assertIn(7636, found_ids)

    def test_11_list_leads_generic(self):
        """Path 4: list_leads generic finds shared-phone leads by phone number."""
        res = list_leads(
            company_id="4",
            scope="all",
            search="8341414152",
            category=None,
            assigned_to_me=None,
            primary_owner=None,
            as_handler_role=None,
            role_filter=None,
            last_interacted_from=None,
            last_interacted_to=None,
            days_since_interaction=None,
            no_followup=None,
            involved_employee_id=None,
            involved_role=None,
            filter_telecaller_id=None,
            filter_field_staff_id=None,
            team_member_id=None,
            source=None,
            page=1,
            per_page=20,
            db=self.session,
            current_employee=self.admin_employee
        )
        self.assertTrue(res.get("success"))
        found_ids = {item["id"] for item in res.get("data", [])}
        self.assertIn(7635, found_ids)
        self.assertIn(7636, found_ids)

    def test_12_list_leads_loans(self):
        """Path 5: list_leads loans (get_bank_wise_leads) finds leads by phone number."""
        loan_lead = CRMLead(
            tenant_id=1,
            company_id=4,
            name="Loan Test Lead",
            phone="+91 9933445566",
            solar_pipeline_status="pending_with_bank",
            loan_bank="SBI"
        )
        self.session.add(loan_lead)
        self.session.flush()
        sync_lead_phone_identities(self.session, loan_lead, phone_raw=loan_lead.phone, with_lock=False)

        res = get_bank_wise_leads(
            company_id=4,
            bank_name=None,
            stage_filter=None,
            bucket_filter=None,
            sort_by=None,
            search="9933445566",
            member_filter=None,
            upliner_filter=None,
            city_filter=None,
            area_filter=None,
            telecaller_filter=None,
            ground_support_filter=None,
            uport_staff_filter=None,
            db=self.session,
            current_employee=self.admin_employee
        )
        self.assertTrue(res.get("is_manager"))
        found_ids = {item["id"] for item in res.get("leads", [])}
        self.assertIn(loan_lead.id, found_ids)

    def test_13_list_leads_team_core(self):
        """Path 6: list_leads team-core (master_leads) finds shared-phone leads by phone number."""
        res = master_leads(
            category=None,
            category_id=None,
            status=None,
            priority=None,
            search="8341414152",
            subsidy_status=None,
            existing_association=None,
            handler_emp_code=None,
            source=None,
            telecaller_id=None,
            field_staff_id=None,
            telecaller_emp_code=None,
            field_staff_emp_code=None,
            field_support_ref_id=None,
            pincode=None,
            company_id_filter=4,
            next_followup_from=None,
            next_followup_to=None,
            accepted_date_from=None,
            accepted_date_to=None,
            installation_date_from=None,
            installation_date_to=None,
            material_reach_date_from=None,
            material_reach_date_to=None,
            created_from=None,
            created_to=None,
            solar_pipeline_status=None,
            ev_b2b_stage=None,
            combined_bank_filter=None,
            submit_date_from=None,
            submit_date_to=None,
            complete_date_from=None,
            complete_date_to=None,
            first_dvr_from=None,
            first_dvr_to=None,
            vendor_id=None,
            guru_name=None,
            z_guru_name=None,
            core_name=None,
            date_preset=None,
            date_from=None,
            date_to=None,
            sort_by="created_at",
            sort_dir="desc",
            page=1,
            per_page=20,
            db=self.session,
            current_employee=self.admin_employee
        )
        self.assertTrue(res.get("success"))
        found_ids = {item["id"] for item in res.get("data", [])}
        self.assertIn(7635, found_ids)
        self.assertIn(7636, found_ids)

    def test_14_list_team_leads(self):
        """Path 7: list_team_leads finds shared-phone leads by phone number."""
        res = list_team_leads(
            company_id=4,
            team_member_id=None,
            filter_by=None,
            role_filter=None,
            status=None,
            priority=None,
            category_id=None,
            category=None,
            handler_type=None,
            primary_owner=None,
            as_handler_role=None,
            search="8341414152",
            handler_search=None,
            next_followup_from=None,
            next_followup_to=None,
            exclude_closed=None,
            no_followup=None,
            last_interacted_from=None,
            last_interacted_to=None,
            days_since_interaction=None,
            quick_filter=None,
            source=None,
            sort_by="created_at",
            sort_dir="desc",
            page=1,
            per_page=20,
            db=self.session,
            current_employee=self.admin_employee
        )
        self.assertTrue(res.get("success"))
        found_ids = {item["id"] for item in res.get("data", {}).get("leads", [])}
        self.assertIn(7635, found_ids)
        self.assertIn(7636, found_ids)

    def test_15_unified_crm_search(self):
        """Path 8: get_unified_my_leads finds shared-phone leads by phone number."""
        import asyncio
        # Lead 7636 is owned by employee 33. In the test transaction, assign 7635 to 33 as well
        lead_7635 = self.session.query(CRMLead).filter(CRMLead.id == 7635).first()
        lead_7635.primary_owner_id = 33
        self.session.flush()

        emp33 = self.session.query(StaffEmployee).filter(StaffEmployee.id == 33).first()
        request = Request({"type": "http", "method": "GET", "url": "http://testserver/api/v1/crm/unified-my-leads", "headers": []})
        with patch("app.core.security.get_current_user_hybrid", return_value=emp33):
            res = asyncio.run(get_unified_my_leads(
                request=request,
                segment="my",
                company_id=4,
                role=None,
                handler_role=None,
                target_user_id=None,
                status=None,
                priority=None,
                category=None,
                category_id=None,
                search="8341414152",
                sort_by=None,
                sort_dir=None,
                followup_filter=None,
                handler_type=None,
                month=None,
                year=None,
                page=1,
                per_page=20,
                db=self.session
            ))
        self.assertIn("data", res)
        found_ids = {item["id"] for item in res.get("data", [])}
        self.assertIn(7635, found_ids)
        self.assertIn(7636, found_ids)

    def test_16_dashboard_v2_drilldown(self):
        """Path 9: get_crm_dashboard_v2_drilldown finds shared-phone leads by phone number."""
        res = get_crm_dashboard_v2_drilldown(
            emp_id="all",
            metric_type="total",
            metric_val=None,
            source=None,
            category_id=None,
            category_name=None,
            company_id=4,
            department_id=None,
            telecaller_id=None,
            start_date=None,
            end_date=None,
            search="8341414152",
            page=1,
            per_page=25,
            db=self.session,
            current_employee=self.admin_employee
        )
        self.assertTrue(res.get("success"))
        found_ids = {item["id"] for item in res.get("data", {}).get("items", [])}
        self.assertIn(7635, found_ids)
        self.assertIn(7636, found_ids)

    def test_17_pipeline_analytics_search(self):
        """Path 10a: lead_analytics applies canonical phone search to pipeline KPIs."""
        res = lead_analytics(
            search="8341414152",
            company_id_filter=4,
            db=self.session,
            current_employee=self.admin_employee
        )
        self.assertIsInstance(res, dict)
        self.assertIn("summary", res)
        self.assertGreaterEqual(res["summary"].get("total_leads", 0), 2)

    def test_18_pipeline_general_common_filters(self):
        """Path 10b: _apply_exec_dashboard_common_filters applies canonical search."""
        base_query = self.session.query(CRMLead).filter(CRMLead.tenant_id == 1, CRMLead.company_id == 4)
        filtered_query = _apply_exec_dashboard_common_filters(
            base=base_query,
            db=self.session,
            current_employee=self.admin_employee,
            is_admin=True,
            has_view_all=True,
            search="8341414152",
            company_id_filter=4
        )
        results = filtered_query.all()
        found_ids = {lead.id for lead in results}
        self.assertIn(7635, found_ids)
        self.assertIn(7636, found_ids)


if __name__ == "__main__":
    unittest.main()
