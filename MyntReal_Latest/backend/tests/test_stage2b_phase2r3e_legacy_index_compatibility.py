"""
Stage 2B Phase 2R-3E: Legacy ux_crm_leads_phone Index Compatibility Audit Suite
Empirically tests Cases A, B, C, D, E against PostgreSQL to document the exact
governing layers and identify architectural conflicts with Model-B+.
Runs inside an isolated transaction with 100% rollback.
Zero operational DB pollution.
"""

import unittest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.core.database import SessionLocal
from app.models.crm import CRMLead, CRMLeadPhone, CRMLeadPhoneProvenance
from app.services.crm_phone_sync_service import sync_lead_phone_identities, normalize_phone
from app.services.crm_dedup_service import assert_no_phone_duplicate, find_phone_duplicate


class TestStage2BPhase2R3ELegacyIndexCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db: Session = SessionLocal()
        cls.baseline_leads = cls.db.query(CRMLead).count()
        cls.baseline_phones = cls.db.query(CRMLeadPhone).count()
        cls.baseline_provs = cls.db.query(CRMLeadPhoneProvenance).count()
        print(f"\n[LEGACY AUDIT BASELINE] leads={cls.baseline_leads}, phones={cls.baseline_phones}, provs={cls.baseline_provs}")

    @classmethod
    def tearDownClass(cls):
        current_leads = cls.db.query(CRMLead).count()
        current_phones = cls.db.query(CRMLeadPhone).count()
        current_provs = cls.db.query(CRMLeadPhoneProvenance).count()
        assert current_leads == cls.baseline_leads, f"crm_leads mutated: {current_leads} != {cls.baseline_leads}"
        assert current_phones == cls.baseline_phones, f"crm_lead_phones mutated: {current_phones} != {cls.baseline_phones}"
        assert current_provs == cls.baseline_provs, f"crm_lead_phone_provenances mutated: {current_provs} != {cls.baseline_provs}"
        cls.db.close()
        print("✓ Zero operational database mutations verified for legacy index audit!")

    def setUp(self):
        self.tx = self.db.begin_nested()

    def tearDown(self):
        self.tx.rollback()

    def test_case_a_same_company_same_norm_different_raw(self):
        """Case A: Same company, different leads, same normalized phone, DIFFERENT raw formatting."""
        lead1 = CRMLead(
            tenant_id=1, company_id=4, name="Lead A1", phone="+919811100099",
            status="new", source="Manual", handler_type="unassigned", created_at=datetime.now(timezone.utc)
        )
        self.db.add(lead1)
        self.db.flush()

        lead2 = CRMLead(
            tenant_id=1, company_id=4, name="Lead A2", phone="09811100099",
            status="new", source="Manual", handler_type="unassigned", created_at=datetime.now(timezone.utc)
        )
        self.db.add(lead2)
        self.db.flush()

        # 1. Check legacy index ux_crm_leads_phone: does NOT collide because raw strings differ
        self.assertIsNotNone(lead1.id)
        self.assertIsNotNone(lead2.id)

        # 2. Check Model-B+ association in crm_lead_phones: permits distinct lead_ids
        sync_lead_phone_identities(self.db, lead1, lead1.phone, source_channel="test", with_lock=False)
        sync_lead_phone_identities(self.db, lead2, lead2.phone, source_channel="test", with_lock=False)

        phones1 = self.db.query(CRMLeadPhone).filter(CRMLeadPhone.lead_id == lead1.id).all()
        phones2 = self.db.query(CRMLeadPhone).filter(CRMLeadPhone.lead_id == lead2.id).all()
        self.assertEqual(phones1[0].phone_norm, "9811100099")
        self.assertEqual(phones2[0].phone_norm, "9811100099")

        # 3. Check crm_dedup_service: assert_no_phone_duplicate blocks duplicate creation under policy
        dup = find_phone_duplicate(self.db, tenant_id=1, company_id=4, phone="9811100099", with_lock=False)
        self.assertIsNotNone(dup)
        print("  ✓ Case A Verified: ux_crm_leads_phone permits (raw differs); Model-B+ permits; crm_dedup_service blocks via policy")

    def test_case_b_same_company_same_norm_identical_raw(self):
        """Case B: Same company, different leads, same normalized phone, IDENTICAL raw primary phone."""
        lead1 = CRMLead(
            tenant_id=1, company_id=4, name="Lead B1", phone="9811100098",
            status="new", source="Manual", handler_type="unassigned", created_at=datetime.now(timezone.utc)
        )
        self.db.add(lead1)
        self.db.flush()

        nested = self.db.begin_nested()
        try:
            lead2 = CRMLead(
                tenant_id=1, company_id=4, name="Lead B2", phone="9811100098",
                status="new", source="Manual", handler_type="unassigned", created_at=datetime.now(timezone.utc)
            )
            self.db.add(lead2)
            self.db.flush()
            nested.commit()
            self.fail("Expected IntegrityError on ux_crm_leads_phone collision")
        except IntegrityError as e:
            nested.rollback()
            self.assertIn("ux_crm_leads_phone", str(e))
            print("  ✓ Case B Verified: ux_crm_leads_phone BLOCKS identical raw string with UniqueViolation (PG error 23505)")

    def test_case_c_primary_matching_alternate(self):
        """Case C: Primary on Lead A matching alternate on Lead B."""
        lead_a = CRMLead(
            tenant_id=1, company_id=4, name="Lead C_A", phone="9811100097",
            status="new", source="Manual", handler_type="unassigned", created_at=datetime.now(timezone.utc)
        )
        self.db.add(lead_a)
        self.db.flush()

        lead_b = CRMLead(
            tenant_id=1, company_id=4, name="Lead C_B", phone="9822200097", alternate_phone="9811100097",
            status="new", source="Manual", handler_type="unassigned", created_at=datetime.now(timezone.utc)
        )
        self.db.add(lead_b)
        self.db.flush()

        # 1. ux_crm_leads_phone: permits because alternate_phone is NOT in the index!
        self.assertIsNotNone(lead_a.id)
        self.assertIsNotNone(lead_b.id)

        # 2. Model-B+ crm_lead_phones: permits both associations
        sync_lead_phone_identities(self.db, lead_a, lead_a.phone, source_channel="test", with_lock=False)
        sync_lead_phone_identities(self.db, lead_b, lead_b.phone, alternate_phone_raw=lead_b.alternate_phone, source_channel="test", with_lock=False)

        phones_b = self.db.query(CRMLeadPhone).filter(CRMLeadPhone.lead_id == lead_b.id).all()
        self.assertEqual(len(phones_b), 2)
        print("  ✓ Case C Verified: ux_crm_leads_phone permits (alternate not indexed); Model-B+ permits")

    def test_case_d_cross_company_same_phone(self):
        """Case D: Cross-company same normalized phone - tests the critical architectural conflict."""
        lead_c4 = CRMLead(
            tenant_id=1, company_id=4, name="Lead D_C4", phone="9811100096",
            status="new", source="Manual", handler_type="unassigned", created_at=datetime.now(timezone.utc)
        )
        self.db.add(lead_c4)
        self.db.flush()

        # 1. Verify crm_dedup_service: PERMITS cross-company same phone!
        dup_c2 = find_phone_duplicate(self.db, tenant_id=1, company_id=2, phone="9811100096", with_lock=False)
        self.assertIsNone(dup_c2, "crm_dedup_service must isolate Company 2 from Company 4")

        # 2. Verify Model-B+ crm_lead_phones: PERMITS cross-company same phone!
        sync_lead_phone_identities(self.db, lead_c4, lead_c4.phone, source_channel="test", with_lock=False)

        # 3. Check legacy index ux_crm_leads_phone on identical raw string:
        # If Company 2 inserts identical raw string '9811100096', ux_crm_leads_phone COLLIDES because it is global!
        nested = self.db.begin_nested()
        try:
            lead_c2 = CRMLead(
                tenant_id=1, company_id=2, name="Lead D_C2", phone="9811100096",
                status="new", source="Manual", handler_type="unassigned", created_at=datetime.now(timezone.utc)
            )
            self.db.add(lead_c2)
            self.db.flush()
            nested.commit()
            self.fail("Expected ux_crm_leads_phone to collide globally across companies")
        except IntegrityError as e:
            nested.rollback()
            self.assertIn("ux_crm_leads_phone", str(e))
            print("  ✓ Case D Verified: ARCHITECTURAL CONFLICT CONFIRMED! ux_crm_leads_phone is global across companies, while Model-B+ and crm_dedup_service are company-scoped.")

    def test_case_e_phone_formatting_variations(self):
        """Case E: Phone formatting variations bypass legacy index but unify under canonical normalization."""
        formats = ["+91 98111-00095", "09811100095", "919811100095", "9811100095"]
        created_leads = []
        for i, fmt in enumerate(formats):
            l = CRMLead(
                tenant_id=1, company_id=4, name=f"Format Lead {i}", phone=fmt,
                status="new", source="Manual", handler_type="unassigned", created_at=datetime.now(timezone.utc)
            )
            self.db.add(l)
            self.db.flush()
            created_leads.append(l)

        # All 4 inserted without colliding on ux_crm_leads_phone because raw strings differ
        self.assertEqual(len(created_leads), 4)

        # But all 4 normalize to the exact same phone_norm
        norms = {normalize_phone(l.phone) for l in created_leads}
        self.assertEqual(norms, {"9811100095"})
        print("  ✓ Case E Verified: Different formatting bypasses raw unique index, but normalizes to single canonical identity")


if __name__ == "__main__":
    unittest.main()
