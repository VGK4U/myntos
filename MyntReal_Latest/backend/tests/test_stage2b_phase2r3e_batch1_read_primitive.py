"""
MYNTOS Stage 2B Phase 2R-3E-II Batch 1 Verification Test Suite
Focused verification of Canonical Phone Read Primitive + Dedup Read Migration.

Tests:
1. same company / same normalized phone / multiple leads -> all candidates visible to read primitive
2. same tenant / different company / same normalized phone -> only requested company candidates returned
3. different tenant / same phone -> no result leakage
4. primary phone match -> returned with phone_role='PRIMARY'
5. alternate phone match -> returned with phone_role='ALTERNATE'
6. formatting variations -> same canonical phone_norm
7. multiple candidates -> no arbitrary selection (no MIN/MAX/LIMIT 1)
8. Historical leads 7635 / 7636 -> remain separate candidates and both visible
9. dedup policy -> existing duplicate prevention behavior remains unchanged (HTTP 409)
10. unauthorized / missing company -> no leakage (fail-closed)
"""

import os
import unittest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.crm import CRMLead, CRMLeadPhone
from app.services.crm_phone_sync_service import (
    find_candidate_associations_by_phone,
    find_candidate_leads_by_phone,
    find_leads_by_phone,
    sync_lead_phone_identities,
)
from app.services.crm_dedup_service import (
    normalize_phone,
    find_phone_duplicate,
    find_duplicate_candidates,
    check_phone_duplicate,
    assert_no_phone_duplicate,
)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://viswanathkari:@localhost:5433/myntreal_dev")


class TestStage2BPhase2R3EIIBatch1ReadPrimitive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(DATABASE_URL)
        cls.SessionLocal = sessionmaker(bind=cls.engine)

    def setUp(self):
        self.conn = self.engine.connect()
        self.trans = self.conn.begin()
        self.session = self.SessionLocal(bind=self.conn)

    def tearDown(self):
        self.session.close()
        self.trans.rollback()
        self.conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 1: Same Company / Same Normalized Phone / Multiple Leads
    # ─────────────────────────────────────────────────────────────────────────
    def test_01_same_company_multiple_leads_visible(self):
        """Verify that when multiple leads share a normalized phone in the same company, all candidates are returned."""
        # Lead 1 has raw "+91 9988112233", Lead 2 has raw "09988112233" (different raw strings, same phone_norm)
        lead1 = CRMLead(tenant_id=1, company_id=4, name="Shared Lead 1", phone="+91 9988112233")
        self.session.add(lead1)
        self.session.flush()
        sync_lead_phone_identities(self.session, lead1, phone_raw=lead1.phone, with_lock=False)

        lead2 = CRMLead(tenant_id=1, company_id=4, name="Shared Lead 2", phone="09988112233")
        self.session.add(lead2)
        self.session.flush()
        sync_lead_phone_identities(self.session, lead2, phone_raw=lead2.phone, with_lock=False)

        # 1. Associations lookup
        assocs = find_candidate_associations_by_phone(
            self.session, tenant_id=1, company_id=4, phone="9988112233"
        )
        self.assertEqual(len(assocs), 2)
        assoc_lead_ids = {a.lead_id for a in assocs}
        self.assertIn(lead1.id, assoc_lead_ids)
        self.assertIn(lead2.id, assoc_lead_ids)

        # 2. Leads lookup
        candidates = find_candidate_leads_by_phone(
            self.session, tenant_id=1, company_id=4, phone="9988112233"
        )
        self.assertEqual(len(candidates), 2)
        candidate_ids = {c.id for c in candidates}
        self.assertIn(lead1.id, candidate_ids)
        self.assertIn(lead2.id, candidate_ids)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 2: Same Tenant / Different Company / Same Normalized Phone
    # ─────────────────────────────────────────────────────────────────────────
    def test_02_company_scoping_strict_isolation(self):
        """Verify cross-company same-phone lookups are strictly isolated."""
        lead_co4 = CRMLead(tenant_id=1, company_id=4, name="Co4 Lead", phone="+91 9977665544")
        self.session.add(lead_co4)
        self.session.flush()
        sync_lead_phone_identities(self.session, lead_co4, phone_raw=lead_co4.phone, with_lock=False)

        lead_co2 = CRMLead(tenant_id=1, company_id=2, name="Co2 Lead", phone="09977665544")
        self.session.add(lead_co2)
        self.session.flush()
        sync_lead_phone_identities(self.session, lead_co2, phone_raw=lead_co2.phone, with_lock=False)

        # Query Company 4 -> only Co4 lead returned
        cand_co4 = find_candidate_leads_by_phone(
            self.session, tenant_id=1, company_id=4, phone="9977665544"
        )
        self.assertEqual(len(cand_co4), 1)
        self.assertEqual(cand_co4[0].id, lead_co4.id)

        # Query Company 2 -> only Co2 lead returned
        cand_co2 = find_candidate_leads_by_phone(
            self.session, tenant_id=1, company_id=2, phone="9977665544"
        )
        self.assertEqual(len(cand_co2), 1)
        self.assertEqual(cand_co2[0].id, lead_co2.id)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 3: Different Tenant / Same Phone
    # ─────────────────────────────────────────────────────────────────────────
    def test_03_tenant_scoping_no_leakage(self):
        """Verify that querying a non-existent or different tenant returns empty results."""
        res = find_candidate_leads_by_phone(
            self.session, tenant_id=999, company_id=4, phone="8341414152"
        )
        self.assertEqual(len(res), 0)

        res_assoc = find_candidate_associations_by_phone(
            self.session, tenant_id=999, company_id=4, phone="8341414152"
        )
        self.assertEqual(len(res_assoc), 0)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 4: Primary Phone Match
    # ─────────────────────────────────────────────────────────────────────────
    def test_04_primary_phone_match_preserves_role(self):
        """Verify primary phone match returns phone_role='PRIMARY' and is_primary=True."""
        lead = CRMLead(tenant_id=1, company_id=4, name="Primary Match Lead", phone="9911223344")
        self.session.add(lead)
        self.session.flush()
        sync_lead_phone_identities(self.session, lead, phone_raw=lead.phone, with_lock=False)

        assocs = find_candidate_associations_by_phone(
            self.session, tenant_id=1, company_id=4, phone="9911223344"
        )
        self.assertEqual(len(assocs), 1)
        self.assertEqual(assocs[0].phone_role, "PRIMARY")
        self.assertTrue(assocs[0].is_primary)
        self.assertEqual(assocs[0].lead_id, lead.id)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 5: Alternate Phone Match
    # ─────────────────────────────────────────────────────────────────────────
    def test_05_alternate_phone_match_preserves_role(self):
        """Verify alternate phone match returns phone_role='ALTERNATE' and is_primary=False."""
        lead = CRMLead(
            tenant_id=1, company_id=4, name="Alt Match Lead",
            phone="9911223355", alternate_phone="9911223366"
        )
        self.session.add(lead)
        self.session.flush()
        sync_lead_phone_identities(
            self.session, lead, phone_raw=lead.phone, alternate_phone_raw=lead.alternate_phone, with_lock=False
        )

        assocs = find_candidate_associations_by_phone(
            self.session, tenant_id=1, company_id=4, phone="9911223366"
        )
        self.assertEqual(len(assocs), 1)
        self.assertEqual(assocs[0].phone_role, "ALTERNATE")
        self.assertFalse(assocs[0].is_primary)
        self.assertEqual(assocs[0].lead_id, lead.id)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 6: Formatting Variations Normalize to Same Phone_Norm
    # ─────────────────────────────────────────────────────────────────────────
    def test_06_formatting_variations(self):
        """Verify formatted phone inputs match the exact same normalized association."""
        lead = CRMLead(tenant_id=1, company_id=4, name="Format Lead", phone="9848022338")
        self.session.add(lead)
        self.session.flush()
        sync_lead_phone_identities(self.session, lead, phone_raw=lead.phone, with_lock=False)

        variations = [
            "+91 98480 22338",
            "+919848022338",
            "98480-22338",
            "09848022338",
            "p:+91 9848022338",
        ]
        for var in variations:
            res = find_candidate_leads_by_phone(
                self.session, tenant_id=1, company_id=4, phone=var
            )
            self.assertEqual(len(res), 1, f"Failed for variation: {var}")
            self.assertEqual(res[0].id, lead.id)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 7: Multiple Candidates — No Arbitrary Selection
    # ─────────────────────────────────────────────────────────────────────────
    def test_07_multiple_candidates_no_arbitrary_selection(self):
        """Verify the read primitive does not truncate or select an arbitrary winner."""
        # 3 leads in company 4 with differing raw strings that normalize to 9900112233
        lead_a = CRMLead(tenant_id=1, company_id=4, name="Candidate Alpha", phone="+91 9900112233")
        lead_b = CRMLead(tenant_id=1, company_id=4, name="Candidate Beta", phone="09900112233")
        lead_c = CRMLead(tenant_id=1, company_id=4, name="Candidate Gamma", phone="9900112233")
        self.session.add_all([lead_a, lead_b, lead_c])
        self.session.flush()
        sync_lead_phone_identities(self.session, lead_a, phone_raw=lead_a.phone, with_lock=False)
        sync_lead_phone_identities(self.session, lead_b, phone_raw=lead_b.phone, with_lock=False)
        sync_lead_phone_identities(self.session, lead_c, phone_raw=lead_c.phone, with_lock=False)

        # find_leads_by_phone returns all 3 distinct leads
        leads = find_leads_by_phone(self.session, tenant_id=1, company_id=4, phone="9900112233")
        self.assertEqual(len(leads), 3)

        # find_duplicate_candidates in crm_dedup_service returns all 3 candidates
        candidates = find_duplicate_candidates(
            self.session, tenant_id=1, company_id=4, phone="9900112233", with_lock=False
        )
        self.assertEqual(len(candidates), 3)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 8: Historical Leads 7635 and 7636
    # ─────────────────────────────────────────────────────────────────────────
    def test_08_historical_leads_7635_7636_separate_candidates(self):
        """Verify existing operational baseline leads 7635 and 7636 are both returned as separate candidates."""
        assocs = find_candidate_associations_by_phone(
            self.session, tenant_id=1, company_id=4, phone="8341414152"
        )
        self.assertEqual(len(assocs), 2)
        roles = {a.lead_id: (a.phone_role, a.is_primary) for a in assocs}
        self.assertIn(7635, roles)
        self.assertIn(7636, roles)
        self.assertEqual(roles[7635], ("PRIMARY", True))
        self.assertEqual(roles[7636], ("ALTERNATE", False))

        leads = find_candidate_leads_by_phone(
            self.session, tenant_id=1, company_id=4, phone="8341414152"
        )
        self.assertEqual(len(leads), 2)
        lead_ids = [l.id for l in leads]
        self.assertIn(7635, lead_ids)
        self.assertIn(7636, lead_ids)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 9: Dedup Policy & HTTP 409 Unchanged
    # ─────────────────────────────────────────────────────────────────────────
    def test_09_dedup_policy_behavior_unchanged(self):
        """Verify check_phone_duplicate and assert_no_phone_duplicate function identically."""
        # 1. Existing lead detection
        res = check_phone_duplicate(
            self.session, tenant_id=1, company_id=4, phone="8341414152", with_lock=False
        )
        self.assertTrue(res.is_duplicate)
        self.assertIn(res.existing_lead_id, (7635, 7636))
        self.assertEqual(res.matched_field, "phone")
        self.assertEqual(res.matched_identity, "8341414152")

        # 2. Duplicate rejection raises HTTP 409
        with self.assertRaises(HTTPException) as ctx:
            assert_no_phone_duplicate(
                self.session, tenant_id=1, company_id=4, phone="8341414152", with_lock=False
            )
        self.assertEqual(ctx.exception.status_code, 409)

        # 3. Non-duplicate phone succeeds without raising
        assert_no_phone_duplicate(
            self.session, tenant_id=1, company_id=4, phone="9999900001", with_lock=False
        )

        # 4. Exclude lead ID works for lead editing self-updates
        lead_solo = CRMLead(tenant_id=1, company_id=4, name="Solo Lead", phone="9988771122")
        self.session.add(lead_solo)
        self.session.flush()
        sync_lead_phone_identities(self.session, lead_solo, phone_raw=lead_solo.phone, with_lock=False)

        # Self-update excludes own ID
        assert_no_phone_duplicate(
            self.session, tenant_id=1, company_id=4,
            phone="9988771122", exclude_lead_id=lead_solo.id, with_lock=False
        )

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 10: Unauthorized Company / Missing Tenancy — Fail-Closed
    # ─────────────────────────────────────────────────────────────────────────
    def test_10_unauthorized_company_fail_closed(self):
        """Verify fail-closed behavior for missing or invalid tenant/company scope."""
        res_no_co = find_candidate_leads_by_phone(
            self.session, tenant_id=1, company_id=None, phone="8341414152"
        )
        self.assertEqual(res_no_co, [])

        res_no_t = find_candidate_leads_by_phone(
            self.session, tenant_id=None, company_id=4, phone="8341414152"
        )
        self.assertEqual(res_no_t, [])

        with self.assertRaises(ValueError):
            find_phone_duplicate(self.session, tenant_id=None, company_id=4, phone="8341414152", with_lock=False)

        with self.assertRaises(ValueError):
            find_phone_duplicate(self.session, tenant_id=1, company_id=None, phone="8341414152", with_lock=False)


if __name__ == "__main__":
    unittest.main()
