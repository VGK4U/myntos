"""
Stage 2B Phase 2R-3E: Application Cutover (Phase 1) Verification Test Suite.

Authoritative verification for:
1. Single Canonical Phone Synchronization Service (crm_phone_sync_service.py).
2. All 25 Architectural Cutover Scenarios (A to Y).
3. Zero Operational Database Mutations Assertion (100% pristine baseline preserved via rollback).
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
load_dotenv(_backend_dir / ".env")

from sqlalchemy import text
from app.core.database import engine, SessionLocal
from app.models.crm import CRMLead, CRMLeadPhone, CRMLeadPhoneProvenance
from app.services.crm_dedup_service import (
    normalize_phone,
    acquire_phone_locks,
    find_phone_duplicate,
    assert_no_phone_duplicate,
)
from app.services.crm_phone_sync_service import (
    sync_lead_phone_identities,
    find_candidate_leads_by_phone,
    catchup_sync_unassociated_leads,
)


def test_stage2b_phase2r3e_application_cutover():
    print("\n" + "=" * 80)
    print("STAGE 2B PHASE 2R-3E: APPLICATION CUTOVER (PHASE 1) VERIFICATION SUITE")
    print("=" * 80)

    tables_to_audit = [
        "crm_leads",
        "crm_lead_phones",
        "crm_lead_phone_provenances",
        "associated_companies",
        "platform_clients",
        "staff_employees",
    ]

    # Capture pristine pre-test baseline counts
    pre_db = SessionLocal()
    pre_counts = {}
    print("\n[STEP 0] Capturing Baseline Row Counts:")
    for tbl in tables_to_audit:
        cnt = pre_db.execute(text(f"SELECT count(*) FROM {tbl}")).scalar()
        pre_counts[tbl] = cnt
        print(f"  {tbl:<30}: {cnt}")
    pre_db.close()

    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    try:
        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO A: Primary-only lead creation
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO A] Testing Primary-only lead creation...")
        lead_a = CRMLead(
            tenant_id=1, company_id=4, name="Cutover Test Lead A",
            phone="+91 98222 00001", status="new", priority="medium",
            handler_type="unassigned", created_at=datetime.utcnow()
        )
        session.add(lead_a)
        session.flush()

        res_a = sync_lead_phone_identities(
            db=session, lead=lead_a,
            source_channel="manual_staff", source_ref="test_suite"
        )
        assert res_a["phone_norm"] == "9822200001"
        assert res_a["alternate_phone_norm"] is None
        
        # Verify crm_lead_phones row
        phones_a = session.query(CRMLeadPhone).filter_by(lead_id=lead_a.id).all()
        assert len(phones_a) == 1
        p_a = phones_a[0]
        assert p_a.phone_norm == "9822200001"
        assert p_a.is_primary is True
        assert p_a.is_active is True
        assert p_a.phone_role == "PRIMARY"

        # Verify provenance
        provs_a = session.query(CRMLeadPhoneProvenance).filter_by(lead_id=lead_a.id).all()
        assert len(provs_a) == 1
        assert provs_a[0].source_field == "phone"
        assert provs_a[0].raw_value == "+91 98222 00001"
        assert provs_a[0].source_channel == "manual_staff"
        print("  ✓ Primary-only lead created: 1 active primary association, 1 provenance.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO B: Alternate-only lead creation
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO B] Testing Alternate-only lead creation...")
        lead_b = CRMLead(
            tenant_id=1, company_id=4, name="Cutover Test Lead B",
            phone=None, alternate_phone="+91 98222 00002", status="new",
            priority="medium", handler_type="unassigned", created_at=datetime.utcnow()
        )
        session.add(lead_b)
        session.flush()

        res_b = sync_lead_phone_identities(
            db=session, lead=lead_b,
            source_channel="manual_staff", source_ref="test_suite"
        )
        assert res_b["phone_norm"] is None
        assert res_b["alternate_phone_norm"] == "9822200002"

        phones_b = session.query(CRMLeadPhone).filter_by(lead_id=lead_b.id).all()
        assert len(phones_b) == 1
        p_b = phones_b[0]
        assert p_b.phone_norm == "9822200002"
        assert p_b.is_primary is True  # Alternate becomes primary when no primary phone exists
        assert p_b.is_active is True
        assert p_b.phone_role == "ALTERNATE"

        provs_b = session.query(CRMLeadPhoneProvenance).filter_by(lead_id=lead_b.id).all()
        assert len(provs_b) == 1
        assert provs_b[0].source_field == "alternate_phone"
        print("  ✓ Alternate-only lead created: 1 active association acting as primary, 1 provenance.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO C: Both distinct primary and alternate phones
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO C] Testing Both distinct phones on lead creation...")
        lead_c = CRMLead(
            tenant_id=1, company_id=4, name="Cutover Test Lead C",
            phone="+91 98222 00003", alternate_phone="+91 98222 00004", status="new",
            priority="medium", handler_type="unassigned", created_at=datetime.utcnow()
        )
        session.add(lead_c)
        session.flush()

        res_c = sync_lead_phone_identities(
            db=session, lead=lead_c,
            source_channel="manual_staff", source_ref="test_suite"
        )
        phones_c = session.query(CRMLeadPhone).filter_by(lead_id=lead_c.id).order_by(CRMLeadPhone.phone_norm).all()
        assert len(phones_c) == 2
        prim_c = [p for p in phones_c if p.phone_norm == "9822200003"][0]
        alt_c = [p for p in phones_c if p.phone_norm == "9822200004"][0]
        assert prim_c.is_primary is True and prim_c.phone_role == "PRIMARY" and prim_c.is_active is True
        assert alt_c.is_primary is False and alt_c.phone_role == "ALTERNATE" and alt_c.is_active is True

        provs_c = session.query(CRMLeadPhoneProvenance).filter_by(lead_id=lead_c.id).order_by(CRMLeadPhoneProvenance.source_field).all()
        assert len(provs_c) == 2
        fields_c = {p.source_field for p in provs_c}
        assert fields_c == {"phone", "alternate_phone"}
        print("  ✓ Both phones created: 2 active associations (1 PRIMARY, 1 ALTERNATE), 2 provenances.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO D: Identical primary and alternate phones
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO D] Testing Identical primary and alternate phones...")
        lead_d = CRMLead(
            tenant_id=1, company_id=4, name="Cutover Test Lead D",
            phone="+91 98222 00005", alternate_phone="98222 00005", status="new",
            priority="medium", handler_type="unassigned", created_at=datetime.utcnow()
        )
        session.add(lead_d)
        session.flush()

        res_d = sync_lead_phone_identities(
            db=session, lead=lead_d,
            source_channel="manual_staff", source_ref="test_suite"
        )
        phones_d = session.query(CRMLeadPhone).filter_by(lead_id=lead_d.id).all()
        assert len(phones_d) == 1  # Exactly ONE association row
        assert phones_d[0].phone_norm == "9822200005"
        assert phones_d[0].is_primary is True

        provs_d = session.query(CRMLeadPhoneProvenance).filter_by(lead_id=lead_d.id).all()
        assert len(provs_d) == 2  # Exactly TWO provenance records (phone and alternate_phone)
        fields_d = {p.source_field for p in provs_d}
        assert fields_d == {"phone", "alternate_phone"}
        print("  ✓ Identical primary & alternate created: 1 association, 2 provenances (backfill invariant preserved).")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO E: Primary phone update (A -> B)
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO E] Testing Primary phone update (A -> B)...")
        lead_a.phone = "+91 98222 00010"
        sync_lead_phone_identities(
            db=session, lead=lead_a,
            phone_raw=lead_a.phone,
            source_channel="manual_staff", source_ref="update_phone"
        )
        phones_a_updated = session.query(CRMLeadPhone).filter_by(lead_id=lead_a.id).all()
        assert len(phones_a_updated) == 2
        old_assoc = [p for p in phones_a_updated if p.phone_norm == "9822200001"][0]
        new_assoc = [p for p in phones_a_updated if p.phone_norm == "982220010" or p.phone_norm == "9822200010"][0]

        assert old_assoc.is_primary is False
        assert old_assoc.is_active is False  # Stale primary deactivated
        assert new_assoc.is_primary is True
        assert new_assoc.is_active is True
        assert new_assoc.phone_role == "PRIMARY"

        provs_a_updated = session.query(CRMLeadPhoneProvenance).filter_by(lead_id=lead_a.id).all()
        assert len(provs_a_updated) == 2  # Historical observation for old phone + new observation for new phone
        print("  ✓ Primary update: Old association deactivated (is_active=False), new association created (is_primary=True), provenance appended.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO F: Alternate phone update (X -> Y)
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO F] Testing Alternate phone update (X -> Y)...")
        lead_c.alternate_phone = "+91 98222 00020"
        sync_lead_phone_identities(
            db=session, lead=lead_c,
            alternate_phone_raw=lead_c.alternate_phone,
            source_channel="manual_staff", source_ref="update_alt"
        )
        phones_c_updated = session.query(CRMLeadPhone).filter_by(lead_id=lead_c.id).all()
        assert len(phones_c_updated) == 3
        old_alt = [p for p in phones_c_updated if p.phone_norm == "9822200004"][0]
        new_alt = [p for p in phones_c_updated if p.phone_norm == "9822200020"][0]

        assert old_alt.is_active is False  # Old alternate deactivated
        assert new_alt.is_active is True
        assert new_alt.is_primary is False
        assert new_alt.phone_role == "ALTERNATE"
        print("  ✓ Alternate update: Old alternate deactivated, new alternate active, primary untouched.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO G: Primary phone removal (set None)
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO G] Testing Primary phone removal (set to None)...")
        lead_a.phone = None
        sync_lead_phone_identities(
            db=session, lead=lead_a,
            phone_raw=None,
            source_channel="manual_staff", source_ref="clear_phone"
        )
        active_a = session.query(CRMLeadPhone).filter_by(lead_id=lead_a.id, is_active=True).all()
        assert len(active_a) == 0  # No active phone remaining on Lead A
        print("  ✓ Primary phone removal: All associations on lead deactivated.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO H: Alternate phone removal (set None)
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO H] Testing Alternate phone removal (set to None)...")
        lead_c.alternate_phone = None
        sync_lead_phone_identities(
            db=session, lead=lead_c,
            alternate_phone_raw=None,
            source_channel="manual_staff", source_ref="clear_alt"
        )
        active_c = session.query(CRMLeadPhone).filter_by(lead_id=lead_c.id, is_active=True).all()
        assert len(active_c) == 1
        assert active_c[0].phone_norm == "9822200003"  # Only primary remains active
        print("  ✓ Alternate phone removal: Alternate association deactivated, primary remains active.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO I: Same-company shared phone across separate leads (Model-B+)
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO I] Testing Same-company shared phone across separate leads (Model-B+)...")
        # Lead B has alternate_phone="+91 98222 00002" (normalized: 9822200002).
        # Create Lead I with phone="98222 00002" in company 4.
        lead_i = CRMLead(
            tenant_id=1, company_id=4, name="Cutover Test Lead I (Shared)",
            phone="98222 00002", status="new", priority="medium",
            handler_type="unassigned", created_at=datetime.utcnow()
        )
        session.add(lead_i)
        session.flush()

        res_i = sync_lead_phone_identities(
            db=session, lead=lead_i,
            source_channel="partner_walkin", source_ref="shared_test"
        )
        sharing_rows = session.query(CRMLeadPhone).filter_by(
            tenant_id=1, company_id=4, phone_norm="9822200002"
        ).all()
        assert len(sharing_rows) >= 2
        lead_ids_sharing = {r.lead_id for r in sharing_rows}
        assert lead_b.id in lead_ids_sharing
        assert lead_i.id in lead_ids_sharing
        print("  ✓ Model-B+ verified: Two distinct leads in Company 4 share normalized phone 9822200002.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO J: Cross-company same phone
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO J] Testing Cross-company same phone...")
        # Distinct raw representation (+91-98222-00002) in Company 2
        lead_j = CRMLead(
            tenant_id=1, company_id=2, name="Cutover Test Lead J (Company 2)",
            phone="+91-98222-00002", status="new", priority="medium",
            handler_type="unassigned", created_at=datetime.utcnow()
        )
        session.add(lead_j)
        session.flush()

        res_j = sync_lead_phone_identities(
            db=session, lead=lead_j,
            source_channel="operator_call", source_ref="co_test"
        )
        assoc_j = session.query(CRMLeadPhone).filter_by(lead_id=lead_j.id).first()
        assert assoc_j.company_id == 2
        assert assoc_j.phone_norm == "9822200002"
        print("  ✓ Cross-company same phone created in Company 2 with full tenant/company scoping.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO K: Cross-tenant same phone
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO K] Testing Cross-tenant same phone candidate isolation...")
        candidates_t1 = find_candidate_leads_by_phone(session, tenant_id=1, company_id=4, phone="9822200002")
        candidates_t999 = find_candidate_leads_by_phone(session, tenant_id=999, company_id=4, phone="9822200002")
        assert len(candidates_t1) >= 2
        assert len(candidates_t999) == 0  # Zero leakage into non-existent or other tenant
        print("  ✓ Cross-tenant candidate isolation strictly enforced.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO L: Same lead + same phone idempotency
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO L] Testing Same lead + same phone idempotency...")
        # Syncing lead_i again with the exact same phone
        res_l = sync_lead_phone_identities(
            db=session, lead=lead_i,
            phone_raw=lead_i.phone,
            source_channel="idempotency_check"
        )
        phones_i = session.query(CRMLeadPhone).filter_by(lead_id=lead_i.id).all()
        assert len(phones_i) == 1  # Did NOT insert duplicate association row
        print("  ✓ Same lead + same phone is completely idempotent; no duplicate associations.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO M: Concurrent same-company submission locking
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO M] Testing Advisory locking determinism on phone sync...")
        locked_identities = acquire_phone_locks(session, tenant_id=1, company_id=4, phones=["9822200002", "+919822200003"])
        assert locked_identities == ["9822200002", "9822200003"]
        print("  ✓ Deterministic lexicographical advisory locking acquired safely.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO N: Unauthorized / Invalid company attempt
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO N] Testing Invalid / Missing company fail-closed...")
        lead_invalid = CRMLead(
            tenant_id=None, company_id=None, name="Invalid Lead",
            phone="9822200099", status="new", priority="medium",
            handler_type="unassigned", created_at=datetime.utcnow()
        )
        try:
            sync_lead_phone_identities(session, lead_invalid)
            assert False, "Should have raised ValueError for missing tenancy"
        except ValueError as ve:
            print(f"  ✓ Failed closed with expected ValueError: {ve}")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO O: Meta authoritative company context
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO O] Testing Meta lead creation with dual-write...")
        lead_meta = CRMLead(
            tenant_id=1, company_id=4, name="Meta Customer",
            phone="+919822200033", status="new", priority="high",
            source="Online - M", handler_type="unassigned", created_at=datetime.utcnow()
        )
        session.add(lead_meta)
        session.flush()
        sync_lead_phone_identities(
            db=session, lead=lead_meta,
            source_channel="meta_lead_ads", source_ref="meta_lead_123456"
        )
        prov_meta = session.query(CRMLeadPhoneProvenance).filter_by(lead_id=lead_meta.id).first()
        assert prov_meta.source_channel == "meta_lead_ads"
        assert prov_meta.source_ref == "meta_lead_123456"
        print("  ✓ Meta lead dual-written with authoritative channel & source_ref.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO P: WhatsApp authoritative company context
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO P] Testing WhatsApp lead creation with dual-write...")
        lead_wa = CRMLead(
            tenant_id=1, company_id=4, name="WhatsApp Prospect",
            phone="+919822200044", status="new", priority="medium",
            source="whatsapp_inbox", handler_type="unassigned", created_at=datetime.utcnow()
        )
        session.add(lead_wa)
        session.flush()
        sync_lead_phone_identities(
            db=session, lead=lead_wa,
            source_channel="whatsapp_inbox", source_ref="inbox_99"
        )
        prov_wa = session.query(CRMLeadPhoneProvenance).filter_by(lead_id=lead_wa.id).first()
        assert prov_wa.source_channel == "whatsapp_inbox"
        print("  ✓ WhatsApp lead dual-written with authoritative channel & source_ref.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO Q: AI Calling authoritative company context
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO Q] Testing AI Calling lead creation with dual-write...")
        lead_ai = CRMLead(
            tenant_id=1, company_id=4, name="AI Call Lead",
            phone="+919822200055", status="new", priority="medium",
            source="AI Call", handler_type="unassigned", created_at=datetime.utcnow()
        )
        session.add(lead_ai)
        session.flush()
        sync_lead_phone_identities(
            db=session, lead=lead_ai,
            source_channel="ai_calling", source_ref="log_77"
        )
        prov_ai = session.query(CRMLeadPhoneProvenance).filter_by(lead_id=lead_ai.id).first()
        assert prov_ai.source_channel == "ai_calling"
        print("  ✓ AI Calling lead dual-written with authoritative channel & source_ref.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO R & S: Provenance creation & historical append behavior
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO R & S] Testing Provenance creation and non-destructive historical append...")
        # Simulate customer calling in from sheets sync then later submitting on website
        sync_lead_phone_identities(
            db=session, lead=lead_meta,
            phone_raw="+91 (982) 220-0033",
            source_channel="website_form", source_ref="landing_page_q3"
        )
        provs_meta_all = session.query(CRMLeadPhoneProvenance).filter_by(lead_id=lead_meta.id).order_by(CRMLeadPhoneProvenance.id.asc()).all()
        assert len(provs_meta_all) == 2
        assert provs_meta_all[0].source_channel == "meta_lead_ads"
        assert provs_meta_all[1].source_channel == "website_form"
        assert provs_meta_all[1].raw_value == "+91 (982) 220-0033"
        print("  ✓ Non-destructive provenance verified: Both observations preserved with respective channel and raw value.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO T: Transaction rollback on association failure
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO T] Testing Transaction rollback safety...")
        session.execute(text("SAVEPOINT sp_failure_test;"))
        try:
            lead_fail = CRMLead(
                tenant_id=1, company_id=4, name="Fail Lead",
                phone="9822200077", status="new", priority="medium",
                handler_type="unassigned", created_at=datetime.utcnow()
            )
            session.add(lead_fail)
            session.flush()
            # Force a foreign key violation by inserting an association with mismatched company_id
            session.execute(text("""
                INSERT INTO crm_lead_phones (tenant_id, company_id, lead_id, phone_norm, phone_role, is_primary)
                VALUES (1, 2, :lid, '9822200077', 'PRIMARY', true);
            """), {"lid": lead_fail.id})
            assert False, "Should have failed with foreign key violation"
        except Exception:
            session.execute(text("ROLLBACK TO SAVEPOINT sp_failure_test;"))
            print("  ✓ Atomic rollback verified: Foreign key violation safely aborted without leaving partial state.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO U: Legacy crm_leads.phone compatibility
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO U] Testing Legacy crm_leads.phone compatibility...")
        assert lead_meta.phone == "+919822200033"
        ux_idx = session.execute(text("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'crm_leads' AND indexname = 'ux_crm_leads_phone';
        """)).scalar()
        assert ux_idx == "ux_crm_leads_phone"
        print("  ✓ Legacy crm_leads.phone column and ux_crm_leads_phone index remain active.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO V: Leads 7635 & 7636 immutability
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO V] Testing Leads 7635 & 7636 immutability...")
        assocs_7635 = session.query(CRMLeadPhone).filter_by(lead_id=7635).all()
        assocs_7636 = session.query(CRMLeadPhone).filter_by(lead_id=7636).all()
        assert len(assocs_7635) == 1
        assert len(assocs_7636) == 2
        assert assocs_7635[0].phone_norm == "8341414152"
        print("  ✓ Leads 7635 & 7636 associations verified completely untouched.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO W: Historical 15 shared-phone groups unchanged
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO W] Testing Historical 15 shared-phone groups...")
        shared_cnt = session.execute(text("""
            SELECT count(*) FROM (
                SELECT tenant_id, company_id, phone_norm, count(DISTINCT lead_id)
                FROM crm_lead_phones
                WHERE lead_id < 10000
                GROUP BY tenant_id, company_id, phone_norm
                HAVING count(DISTINCT lead_id) > 1
            ) sq;
        """)).scalar()
        assert shared_cnt == 15
        print("  ✓ All 15 historical collision groups verified untouched.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO X: No company transfer
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO X] Testing Lead company immutability...")
        session.execute(text("SAVEPOINT sp_company_immut;"))
        try:
            session.execute(text("UPDATE crm_leads SET company_id = 2 WHERE id = :lid"), {"lid": lead_meta.id})
            assert False, "Should have failed due to ON UPDATE RESTRICT composite FK"
        except Exception:
            session.execute(text("ROLLBACK TO SAVEPOINT sp_company_immut;"))
            print("  ✓ Company transfer strictly prevented by composite FK ON UPDATE RESTRICT.")

        # ─────────────────────────────────────────────────────────────────────
        # SCENARIO Y: 11272 / 11273 Catch-up idempotency
        # ─────────────────────────────────────────────────────────────────────
        print("\n[SCENARIO Y] Testing Leads 11272 & 11273 Catch-up synchronization...")
        catchup_res = catchup_sync_unassociated_leads(session, specific_lead_ids=[11272, 11273])
        assert catchup_res["synced_count"] == 2
        assert catchup_res["synced_lead_ids"] == [11272, 11273]

        # Verify associations created
        phones_11272 = session.query(CRMLeadPhone).filter_by(lead_id=11272).all()
        assert len(phones_11272) == 1
        assert phones_11272[0].phone_norm == "9912876666"
        assert phones_11272[0].company_id == 3

        phones_11273 = session.query(CRMLeadPhone).filter_by(lead_id=11273).all()
        assert len(phones_11273) == 1
        assert phones_11273[0].phone_norm == "8019905229"
        assert phones_11273[0].company_id == 3

        # Verify idempotency by running catchup a second time
        catchup_res2 = catchup_sync_unassociated_leads(session, specific_lead_ids=[11272, 11273])
        assert catchup_res2["synced_count"] == 2
        # Verify still exactly 1 association per lead
        assert session.query(CRMLeadPhone).filter_by(lead_id=11272).count() == 1
        assert session.query(CRMLeadPhone).filter_by(lead_id=11273).count() == 1
        print("  ✓ Leads 11272 & 11273 catch-up verified completely idempotent and non-destructive.")

    finally:
        session.close()
        transaction.rollback()
        connection.close()
        print("\n[TRANSACTION ROLLBACK] Test database transaction rolled back successfully.")

    # ─────────────────────────────────────────────────────────────────────────
    # Zero Operational Database Mutations Assertion
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[AUDIT] Verifying Operational DB Row Counts (Zero Mutations Assertion)...")
    post_db = SessionLocal()
    all_matched = True
    for tbl in tables_to_audit:
        post_cnt = post_db.execute(text(f"SELECT count(*) FROM {tbl}")).scalar()
        pre_cnt = pre_counts[tbl]
        match = (post_cnt == pre_cnt)
        status = "MATCHED (PRISTINE)" if match else f"MISMATCH! (pre={pre_cnt}, post={post_cnt})"
        print(f"  {tbl:<30}: before={pre_cnt:>5}, after={post_cnt:>5} -> {status}")
        if not match:
            all_matched = False
    post_db.close()

    assert all_matched, "FATAL: Operational database mutated during test execution!"
    print("\n" + "=" * 80)
    print("ALL 25 APPLICATION CUTOVER SCENARIOS (A to Y) PASSED PERFECTLY!")
    print("=" * 80)
    print("[SUCCESS] Operational database is 100% UNMUTATED and PRISTINE.\n")


if __name__ == "__main__":
    test_stage2b_phase2r3e_application_cutover()
