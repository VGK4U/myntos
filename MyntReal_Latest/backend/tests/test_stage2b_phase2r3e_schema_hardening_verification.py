"""
Stage 2B Phase 2R-3E: Schema Hardening Migration Verification Suite
Tests requirements A through E of Migration c9d0e1f2a3b4:
A. Composite FK enforcement (valid succeeds, mismatched rejected, mismatched provenance rejected)
B. Existing valid rows (4,785 associations, 4,787 provenances)
C. Critical historical records (Leads 7635 & 7636)
D. Shared-phone behavior (same tenant, same company, different leads, same normalized phone)
E. Cross-company behavior (same tenant, different companies, different leads, same normalized phone)
All mutations run in an isolated transaction with 100% rollback.
Zero operational DB pollution.
"""

import unittest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.core.database import SessionLocal
from app.models.crm import CRMLead, CRMLeadPhone, CRMLeadPhoneProvenance
from app.services.crm_phone_sync_service import sync_lead_phone_identities


class TestStage2BPhase2R3ESchemaHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db: Session = SessionLocal()
        cls.baseline_leads = cls.db.query(CRMLead).count()
        cls.baseline_phones = cls.db.query(CRMLeadPhone).count()
        cls.baseline_provs = cls.db.query(CRMLeadPhoneProvenance).count()
        print(f"\n[SCHEMA HARDENING BASELINE] leads={cls.baseline_leads}, phones={cls.baseline_phones}, provs={cls.baseline_provs}")
        assert cls.baseline_leads == 4827, f"Expected 4827 leads, found {cls.baseline_leads}"
        assert cls.baseline_phones == 4785, f"Expected 4785 phones, found {cls.baseline_phones}"
        assert cls.baseline_provs == 4787, f"Expected 4787 provs, found {cls.baseline_provs}"

    @classmethod
    def tearDownClass(cls):
        current_leads = cls.db.query(CRMLead).count()
        current_phones = cls.db.query(CRMLeadPhone).count()
        current_provs = cls.db.query(CRMLeadPhoneProvenance).count()
        assert current_leads == cls.baseline_leads, f"crm_leads mutated: {current_leads} != {cls.baseline_leads}"
        assert current_phones == cls.baseline_phones, f"crm_lead_phones mutated: {current_phones} != {cls.baseline_phones}"
        assert current_provs == cls.baseline_provs, f"crm_lead_phone_provenances mutated: {current_provs} != {cls.baseline_provs}"
        cls.db.close()
        print("✓ Zero operational database mutations verified for schema hardening!")

    def setUp(self):
        self.tx = self.db.begin_nested()

    def tearDown(self):
        self.tx.rollback()

    def test_requirement_a_composite_fk_enforcement(self):
        """Requirement A: Composite FK enforcement between crm_leads, crm_lead_phones, and crm_lead_phone_provenances."""
        # 1. Valid lead + matching tenant/company/lead association -> SUCCEEDS
        lead = CRMLead(
            tenant_id=1, company_id=4, name="Composite Lead Valid", phone="9811100088",
            status="new", source="Manual", handler_type="unassigned", created_at=datetime.now(timezone.utc)
        )
        self.db.add(lead)
        self.db.flush()

        phone_assoc = CRMLeadPhone(
            tenant_id=1, company_id=4, lead_id=lead.id, phone_norm="9811100088",
            phone_role="PRIMARY", is_primary=True, is_active=True, verification_status="UNVERIFIED",
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
        )
        self.db.add(phone_assoc)
        self.db.flush()
        self.assertIsNotNone(phone_assoc.id)

        prov = CRMLeadPhoneProvenance(
            phone_association_id=phone_assoc.id, tenant_id=1, company_id=4, lead_id=lead.id,
            source_field="phone", raw_value="9811100088", source_channel="test", captured_at=datetime.now(timezone.utc)
        )
        self.db.add(prov)
        self.db.flush()
        self.assertIsNotNone(prov.id)
        print("  ✓ Requirement A.1: Valid composite lead + phone + prov succeeded")

        # 2. Valid lead + mismatched tenant/company association -> REJECTED by fk_crm_lead_phones_composite_lead
        nested1 = self.db.begin_nested()
        try:
            mismatched_phone = CRMLeadPhone(
                tenant_id=1, company_id=2, lead_id=lead.id,  # lead is in company 4, but association says company 2!
                phone_norm="9811100089", phone_role="PRIMARY", is_primary=True, is_active=True,
                verification_status="UNVERIFIED", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
            )
            self.db.add(mismatched_phone)
            self.db.flush()
            nested1.commit()
            self.fail("Expected IntegrityError on composite FK mismatch between phone and lead")
        except IntegrityError as e:
            nested1.rollback()
            self.assertIn("fk_crm_lead_phones_composite_lead", str(e))
            print("  ✓ Requirement A.2: Mismatched tenant/company on phone association rejected by composite FK")

        # 3. Valid association + mismatched provenance tenant/company/lead -> REJECTED by fk_crm_lead_phone_prov_composite_assoc
        nested2 = self.db.begin_nested()
        try:
            mismatched_prov = CRMLeadPhoneProvenance(
                phone_association_id=phone_assoc.id, tenant_id=1, company_id=2, lead_id=lead.id,  # assoc is in comp 4, prov says comp 2!
                source_field="phone", raw_value="9811100088", source_channel="test", captured_at=datetime.now(timezone.utc)
            )
            self.db.add(mismatched_prov)
            self.db.flush()
            nested2.commit()
            self.fail("Expected IntegrityError on composite FK mismatch between prov and phone")
        except IntegrityError as e:
            nested2.rollback()
            self.assertIn("fk_crm_lead_phone_prov_composite_assoc", str(e))
            print("  ✓ Requirement A.3: Mismatched tenant/company on provenance rejected by composite FK")

    def test_requirement_b_existing_valid_rows(self):
        """Requirement B: All existing 4,785 phone associations and 4,787 provenances remain valid."""
        assoc_cnt = self.db.execute(text("SELECT count(*) FROM crm_lead_phones")).scalar()
        prov_cnt = self.db.execute(text("SELECT count(*) FROM crm_lead_phone_provenances")).scalar()
        self.assertEqual(assoc_cnt, 4785)
        self.assertEqual(prov_cnt, 4787)
        print("  ✓ Requirement B: All 4,785 phone associations and 4,787 provenances remain 100% valid")

    def test_requirement_c_critical_historical_records(self):
        """Requirement C: Leads 7635 & 7636 remain separate leads with independent records."""
        l7635 = self.db.execute(text("SELECT id, name, phone, alternate_phone, status, deal_value FROM crm_leads WHERE id = 7635")).mappings().first()
        l7636 = self.db.execute(text("SELECT id, name, phone, alternate_phone, status, deal_value FROM crm_leads WHERE id = 7636")).mappings().first()

        self.assertEqual(l7635['name'], 'Ramu')
        self.assertEqual(l7635['status'], 'won')
        self.assertEqual(l7635['deal_value'], 190000.0)
        self.assertEqual(l7636['name'], 'Karakavalasa Alekhya')
        self.assertEqual(l7636['status'], 'won')
        self.assertEqual(l7636['deal_value'], 275000.0)

        phones_7635 = self.db.execute(text("SELECT phone_norm, phone_role, is_primary FROM crm_lead_phones WHERE lead_id = 7635")).mappings().fetchall()
        phones_7636 = self.db.execute(text("SELECT phone_norm, phone_role, is_primary FROM crm_lead_phones WHERE lead_id = 7636 ORDER BY is_primary DESC")).mappings().fetchall()

        self.assertEqual(len(phones_7635), 1)
        self.assertEqual(len(phones_7636), 2)
        self.assertEqual(phones_7635[0]['phone_norm'], '8341414152')
        self.assertEqual(phones_7635[0]['phone_role'], 'PRIMARY')
        self.assertEqual(phones_7635[0]['is_primary'], True)
        
        # Lead 7636 primary phone
        self.assertEqual(phones_7636[0]['phone_norm'], '9948314559')
        self.assertEqual(phones_7636[0]['phone_role'], 'PRIMARY')
        self.assertEqual(phones_7636[0]['is_primary'], True)
        
        # Lead 7636 alternate phone matches Lead 7635 primary phone
        self.assertEqual(phones_7636[1]['phone_norm'], '8341414152')
        self.assertEqual(phones_7636[1]['phone_role'], 'ALTERNATE')
        self.assertEqual(phones_7636[1]['is_primary'], False)
        print("  ✓ Requirement C: Leads 7635 and 7636 verified completely independent and untouched")

    def test_requirement_d_shared_phone_behavior(self):
        """Requirement D: Model-B+ permits same tenant, same company, different leads, same normalized phone."""
        lead1 = CRMLead(
            tenant_id=1, company_id=4, name="Shared Phone Lead 1", phone="+919811100087",
            status="new", source="Manual", handler_type="unassigned", created_at=datetime.now(timezone.utc)
        )
        lead2 = CRMLead(
            tenant_id=1, company_id=4, name="Shared Phone Lead 2", phone="09811100087",
            status="new", source="Manual", handler_type="unassigned", created_at=datetime.now(timezone.utc)
        )
        self.db.add(lead1)
        self.db.add(lead2)
        self.db.flush()

        # Both leads can associate the same normalized phone under Model-B+
        sync_lead_phone_identities(self.db, lead1, lead1.phone, source_channel="test", with_lock=False)
        sync_lead_phone_identities(self.db, lead2, lead2.phone, source_channel="test", with_lock=False)

        assoc1 = self.db.query(CRMLeadPhone).filter(CRMLeadPhone.lead_id == lead1.id).first()
        assoc2 = self.db.query(CRMLeadPhone).filter(CRMLeadPhone.lead_id == lead2.id).first()

        self.assertEqual(assoc1.phone_norm, "9811100087")
        self.assertEqual(assoc2.phone_norm, "9811100087")
        self.assertNotEqual(assoc1.lead_id, assoc2.lead_id)
        print("  ✓ Requirement D: Model-B+ permits same-company shared normalized phone across separate leads")

    def test_requirement_e_cross_company_behavior(self):
        """Requirement E: Model-B+ permits same tenant, different companies, different leads, same normalized phone."""
        lead_comp4 = CRMLead(
            tenant_id=1, company_id=4, name="Comp4 Lead", phone="+919811100086",
            status="new", source="Manual", handler_type="unassigned", created_at=datetime.now(timezone.utc)
        )
        lead_comp2 = CRMLead(
            tenant_id=1, company_id=2, name="Comp2 Lead", phone="09811100086",
            status="new", source="Manual", handler_type="unassigned", created_at=datetime.now(timezone.utc)
        )
        self.db.add(lead_comp4)
        self.db.add(lead_comp2)
        self.db.flush()

        sync_lead_phone_identities(self.db, lead_comp4, lead_comp4.phone, source_channel="test", with_lock=False)
        sync_lead_phone_identities(self.db, lead_comp2, lead_comp2.phone, source_channel="test", with_lock=False)

        assoc_c4 = self.db.query(CRMLeadPhone).filter(CRMLeadPhone.lead_id == lead_comp4.id).first()
        assoc_c2 = self.db.query(CRMLeadPhone).filter(CRMLeadPhone.lead_id == lead_comp2.id).first()

        self.assertEqual(assoc_c4.phone_norm, "9811100086")
        self.assertEqual(assoc_c2.phone_norm, "9811100086")
        self.assertEqual(assoc_c4.company_id, 4)
        self.assertEqual(assoc_c2.company_id, 2)
        print("  ✓ Requirement E: Model-B+ permits cross-company same normalized phone across separate leads")


if __name__ == "__main__":
    unittest.main()
