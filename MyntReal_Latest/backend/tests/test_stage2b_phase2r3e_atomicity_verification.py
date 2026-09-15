"""
Stage 2B Phase 2R-3E: Transactional Atomicity Verification Suite
Tests atomicity across crm_leads, crm_lead_phones, and crm_lead_phone_provenances.
All tests run inside an isolated transaction with 100% rollback.
Zero operational DB pollution.
"""

import unittest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import SessionLocal
from app.models.crm import CRMLead, CRMLeadPhone, CRMLeadPhoneProvenance
from app.services.crm_phone_sync_service import sync_lead_phone_identities, normalize_phone


class TestStage2BPhase2R3ETransactionalAtomicity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db: Session = SessionLocal()
        # Capture baseline counts before any tests run
        cls.baseline_leads = cls.db.query(CRMLead).count()
        cls.baseline_phones = cls.db.query(CRMLeadPhone).count()
        cls.baseline_provs = cls.db.query(CRMLeadPhoneProvenance).count()
        print(f"\n[BASELINE] leads={cls.baseline_leads}, phones={cls.baseline_phones}, provs={cls.baseline_provs}")

    @classmethod
    def tearDownClass(cls):
        # Final audit: verify exact row counts match baseline
        current_leads = cls.db.query(CRMLead).count()
        current_phones = cls.db.query(CRMLeadPhone).count()
        current_provs = cls.db.query(CRMLeadPhoneProvenance).count()
        print(f"[FINAL AUDIT] leads={current_leads}, phones={current_phones}, provs={current_provs}")
        assert current_leads == cls.baseline_leads, f"crm_leads mutated: {current_leads} != {cls.baseline_leads}"
        assert current_phones == cls.baseline_phones, f"crm_lead_phones mutated: {current_phones} != {cls.baseline_phones}"
        assert current_provs == cls.baseline_provs, f"crm_lead_phone_provenances mutated: {current_provs} != {cls.baseline_provs}"
        cls.db.close()
        print("✓ Zero operational database mutations verified!")

    def setUp(self):
        # Begin nested savepoint or isolated transaction
        self.tx = self.db.begin_nested()

    def tearDown(self):
        # Roll back savepoint
        self.tx.rollback()

    def test_scenario_a_lead_creation_and_phone_sync_success(self):
        """Scenario A: Lead creation + phone sync success commits atomically."""
        lead = CRMLead(
            tenant_id=1,
            company_id=4,
            name="Atomicity Lead A",
            phone="9871100001",
            status="new",
            source="Manual",
            handler_type="unassigned",
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(lead)
        self.db.flush()

        res = sync_lead_phone_identities(
            db=self.db,
            lead=lead,
            phone_raw=lead.phone,
            source_channel="test_atomicity",
            source_ref="scen_a",
            with_lock=False
        )

        phones = self.db.query(CRMLeadPhone).filter(CRMLeadPhone.lead_id == lead.id).all()
        provs = self.db.query(CRMLeadPhoneProvenance).filter(CRMLeadPhoneProvenance.lead_id == lead.id).all()

        self.assertEqual(len(phones), 1)
        self.assertEqual(len(provs), 1)
        self.assertEqual(phones[0].phone_norm, "9871100001")
        self.assertTrue(phones[0].is_primary)
        self.assertTrue(phones[0].is_active)
        self.assertEqual(provs[0].phone_association_id, phones[0].id)
        print("  ✓ Scenario A Passed: Lead creation + phone sync atomic success")

    def test_scenario_b_lead_creation_phone_association_failure(self):
        """Scenario B: Lead creation + association failure rolls back lead, association, and provenance."""
        lead_id = None
        try:
            nested = self.db.begin_nested()
            lead = CRMLead(
                tenant_id=1,
                company_id=4,
                name="Atomicity Lead B",
                phone="9871100002",
                status="new",
                source="Manual",
                handler_type="unassigned",
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(lead)
            self.db.flush()
            lead_id = lead.id

            # Simulate failure during phone association by injecting invalid tenant_id
            lead.tenant_id = None  # Will cause sync_lead_phone_identities to fail closed
            sync_lead_phone_identities(
                db=self.db,
                lead=lead,
                phone_raw=lead.phone,
                source_channel="test_atomicity",
                source_ref="scen_b",
                with_lock=False
            )
            nested.commit()
            self.fail("Expected ValueError on missing tenant_id")
        except ValueError:
            nested.rollback()

        # Verify full rollback: no lead, no phone, no provenance
        lead_check = self.db.query(CRMLead).filter(CRMLead.id == lead_id).first()
        phone_check = self.db.query(CRMLeadPhone).filter(CRMLeadPhone.lead_id == lead_id).all()
        prov_check = self.db.query(CRMLeadPhoneProvenance).filter(CRMLeadPhoneProvenance.lead_id == lead_id).all()

        self.assertIsNone(lead_check)
        self.assertEqual(len(phone_check), 0)
        self.assertEqual(len(prov_check), 0)
        print("  ✓ Scenario B Passed: Lead creation failure rolled back completely (0 partial state)")

    def test_scenario_c_lead_phone_update_association_success(self):
        """Scenario C: Lead phone update + association success updates atomically."""
        lead = CRMLead(
            tenant_id=1,
            company_id=4,
            name="Atomicity Lead C",
            phone="9871100003",
            status="new",
            source="Manual",
            handler_type="unassigned",
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(lead)
        self.db.flush()

        sync_lead_phone_identities(
            db=self.db,
            lead=lead,
            phone_raw=lead.phone,
            source_channel="test_atomicity",
            source_ref="scen_c_orig",
            with_lock=False
        )

        # Update phone
        lead.phone = "9871100004"
        self.db.flush()

        sync_lead_phone_identities(
            db=self.db,
            lead=lead,
            phone_raw=lead.phone,
            source_channel="test_atomicity",
            source_ref="scen_c_updated",
            with_lock=False
        )

        phones = self.db.query(CRMLeadPhone).filter(CRMLeadPhone.lead_id == lead.id).all()
        provs = self.db.query(CRMLeadPhoneProvenance).filter(CRMLeadPhoneProvenance.lead_id == lead.id).all()

        self.assertEqual(len(phones), 2)
        old_phone = [p for p in phones if p.phone_norm == "9871100003"][0]
        new_phone = [p for p in phones if p.phone_norm == "9871100004"][0]

        self.assertFalse(old_phone.is_active)
        self.assertFalse(old_phone.is_primary)
        self.assertTrue(new_phone.is_active)
        self.assertTrue(new_phone.is_primary)
        self.assertEqual(len(provs), 2)
        print("  ✓ Scenario C Passed: Lead phone update + association success")

    def test_scenario_d_lead_phone_update_association_failure(self):
        """Scenario D: Failure during lead phone update rolls back to previous valid state."""
        lead = CRMLead(
            tenant_id=1,
            company_id=4,
            name="Atomicity Lead D",
            phone="9871100005",
            status="new",
            source="Manual",
            handler_type="unassigned",
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(lead)
        self.db.flush()

        sync_lead_phone_identities(
            db=self.db,
            lead=lead,
            phone_raw=lead.phone,
            source_channel="test_atomicity",
            source_ref="scen_d_orig",
            with_lock=False
        )
        self.db.flush()

        try:
            nested = self.db.begin_nested()
            lead.phone = "9871100006"
            self.db.flush()
            # Force simulated error during association update
            raise RuntimeError("Simulated transient network/DB failure")
            nested.commit()
        except RuntimeError:
            nested.rollback()

        # Verify lead state returned to pre-update state
        self.db.refresh(lead)
        self.assertEqual(lead.phone, "9871100005")
        active_phones = self.db.query(CRMLeadPhone).filter(
            CRMLeadPhone.lead_id == lead.id,
            CRMLeadPhone.is_active == True
        ).all()
        self.assertEqual(len(active_phones), 1)
        self.assertEqual(active_phones[0].phone_norm, "9871100005")
        print("  ✓ Scenario D Passed: Update failure cleanly restored previous state")

    def test_scenario_e_primary_to_alternate_transition(self):
        """Scenario E: Primary phone A transitions to alternate when new phone B is set as primary."""
        lead = CRMLead(
            tenant_id=1,
            company_id=4,
            name="Atomicity Lead E",
            phone="9871100007",
            status="new",
            source="Manual",
            handler_type="unassigned",
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(lead)
        self.db.flush()

        sync_lead_phone_identities(
            db=self.db,
            lead=lead,
            phone_raw=lead.phone,
            source_channel="test_atomicity",
            source_ref="scen_e_init",
            with_lock=False
        )

        # Transition: 9871100008 becomes primary, 9871100007 becomes alternate
        lead.phone = "9871100008"
        lead.alternate_phone = "9871100007"
        self.db.flush()

        sync_lead_phone_identities(
            db=self.db,
            lead=lead,
            phone_raw=lead.phone,
            alternate_phone_raw=lead.alternate_phone,
            source_channel="test_atomicity",
            source_ref="scen_e_transition",
            with_lock=False
        )

        phones = self.db.query(CRMLeadPhone).filter(CRMLeadPhone.lead_id == lead.id).all()
        p_new = [p for p in phones if p.phone_norm == "9871100008"][0]
        p_old = [p for p in phones if p.phone_norm == "9871100007"][0]

        self.assertTrue(p_new.is_primary)
        self.assertEqual(p_new.phone_role, "PRIMARY")
        self.assertTrue(p_new.is_active)

        self.assertFalse(p_old.is_primary)
        self.assertEqual(p_old.phone_role, "ALTERNATE")
        self.assertTrue(p_old.is_active)
        print("  ✓ Scenario E Passed: Primary -> alternate transition atomic")

    def test_scenario_f_phone_removal_deactivation(self):
        """Scenario F: Setting primary phone to None deactivates association."""
        lead = CRMLead(
            tenant_id=1,
            company_id=4,
            name="Atomicity Lead F",
            phone="9871100009",
            status="new",
            source="Manual",
            handler_type="unassigned",
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(lead)
        self.db.flush()

        sync_lead_phone_identities(
            db=self.db,
            lead=lead,
            phone_raw=lead.phone,
            source_channel="test_atomicity",
            source_ref="scen_f_init",
            with_lock=False
        )

        lead.phone = None
        self.db.flush()

        sync_lead_phone_identities(
            db=self.db,
            lead=lead,
            phone_raw=None,
            source_channel="test_atomicity",
            source_ref="scen_f_remove",
            with_lock=False
        )

        phones = self.db.query(CRMLeadPhone).filter(CRMLeadPhone.lead_id == lead.id).all()
        self.assertEqual(len(phones), 1)
        self.assertFalse(phones[0].is_active)
        self.assertFalse(phones[0].is_primary)
        print("  ✓ Scenario F Passed: Primary phone removal deactivated association")

    def test_scenario_g_alternate_removal(self):
        """Scenario G: Setting alternate phone to None deactivates alternate while primary remains active."""
        lead = CRMLead(
            tenant_id=1,
            company_id=4,
            name="Atomicity Lead G",
            phone="9871100010",
            alternate_phone="9871100011",
            status="new",
            source="Manual",
            handler_type="unassigned",
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(lead)
        self.db.flush()

        sync_lead_phone_identities(
            db=self.db,
            lead=lead,
            phone_raw=lead.phone,
            alternate_phone_raw=lead.alternate_phone,
            source_channel="test_atomicity",
            source_ref="scen_g_init",
            with_lock=False
        )

        # Clear alternate
        lead.alternate_phone = None
        self.db.flush()

        sync_lead_phone_identities(
            db=self.db,
            lead=lead,
            phone_raw=lead.phone,
            alternate_phone_raw=None,
            source_channel="test_atomicity",
            source_ref="scen_g_clear_alt",
            with_lock=False
        )

        phones = self.db.query(CRMLeadPhone).filter(CRMLeadPhone.lead_id == lead.id).all()
        p_prim = [p for p in phones if p.phone_norm == "9871100010"][0]
        p_alt = [p for p in phones if p.phone_norm == "9871100011"][0]

        self.assertTrue(p_prim.is_active)
        self.assertTrue(p_prim.is_primary)
        self.assertFalse(p_alt.is_active)
        self.assertFalse(p_alt.is_primary)
        print("  ✓ Scenario G Passed: Alternate removal deactivated alternate; primary intact")

    def test_scenario_h_identical_primary_and_alternate_phones(self):
        """Scenario H: Identical primary and alternate phones produce 1 association and 2 provenances."""
        lead = CRMLead(
            tenant_id=1,
            company_id=4,
            name="Atomicity Lead H",
            phone="+91 98711-00012",
            alternate_phone="09871100012",
            status="new",
            source="Manual",
            handler_type="unassigned",
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(lead)
        self.db.flush()

        sync_lead_phone_identities(
            db=self.db,
            lead=lead,
            phone_raw=lead.phone,
            alternate_phone_raw=lead.alternate_phone,
            source_channel="test_atomicity",
            source_ref="scen_h",
            with_lock=False
        )

        phones = self.db.query(CRMLeadPhone).filter(CRMLeadPhone.lead_id == lead.id).all()
        provs = self.db.query(CRMLeadPhoneProvenance).filter(CRMLeadPhoneProvenance.lead_id == lead.id).all()

        self.assertEqual(len(phones), 1)
        self.assertEqual(phones[0].phone_norm, "9871100012")
        self.assertEqual(len(provs), 2)
        fields = {p.source_field for p in provs}
        self.assertEqual(fields, {"phone", "alternate_phone"})
        print("  ✓ Scenario H Passed: Identical primary/alternate produced 1 association, 2 provenances")


if __name__ == "__main__":
    unittest.main()
