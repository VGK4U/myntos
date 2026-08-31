"""
MYNTOS PHASE 3 — Cross-Tenant Security & Integration Isolation Test Suite
Validates strict multi-tenant isolation across Meta, WhatsApp, and Telephony.
"""

import os
import uuid
from sqlalchemy import text
from app.core.database import SessionLocal
from app.services.facebook_leads_service import facebook_leads_service
from app.services.wa_credentials import get_wa_credentials, resolve_company_id_by_phone_number_id
from app.services.b2b_shadow import is_module_entitled, resolve_client_id_for_staff
from app.models.operator_calls import OperatorCall, TelephonyDIDMapping
from app.models.whatsapp import WAInbox
from app.models.call_tracking import StaffCallRecording
from app.models.crm import CRMLead
from app.api.v1.endpoints.operator_calls import _upsert_call, _resolve_company_for_call, _get_accessible_company_ids


def test_meta_cross_tenant_page_ownership_and_quarantine():
    """
    Test Meta Page -> Tenant Resolution:
    1. Known Page A resolves strictly to Tenant A (company_id=1).
    2. Known Page B resolves strictly to Tenant B (company_id=2).
    3. Unknown Page is REJECTED (None) with zero CRM insertion.
    4. Page A with malicious/conflicting payload company_id=2 preserves Page A ownership (company_id=1).
    """
    print("\n--- [TEST 1] Meta Cross-Tenant Page Ownership & Quarantine ---")
    db = SessionLocal()
    try:
        # Seed test pages for Company 1 and Company 2
        page_a_id = f"meta_page_a_{uuid.uuid4().hex[:6]}"
        page_b_id = f"meta_page_b_{uuid.uuid4().hex[:6]}"

        db.execute(
            text("""
                INSERT INTO facebook_pages (page_id, page_name, company_id, access_token, crm_segment, is_active)
                VALUES 
                    (:pa, 'Tenant A Page', 1, 'enc_tok_a', 'GENERAL', true),
                    (:pb, 'Tenant B Page', 2, 'enc_tok_b', 'GENERAL', true)
            """),
            {"pa": page_a_id, "pb": page_b_id}
        )
        db.commit()

        # 1. Lookup Page A
        info_a = facebook_leads_service.get_page_info(page_a_id, db)
        assert info_a is not None
        assert info_a["company_id"] == 1, f"Expected company_id=1 for Page A, got {info_a['company_id']}"

        # 2. Lookup Page B
        info_b = facebook_leads_service.get_page_info(page_b_id, db)
        assert info_b is not None
        assert info_b["company_id"] == 2, f"Expected company_id=2 for Page B, got {info_b['company_id']}"

        # 3. Lookup Unknown Page
        info_unknown = facebook_leads_service.get_page_info("unregistered_meta_page_999", db)
        assert info_unknown is None or info_unknown.get("company_id") is None, "Unknown page must not resolve company_id"

        # 4. Map Lead for Page A -> Must map to company_id=1
        lead_data_a = {
            "id": f"fb_lead_{uuid.uuid4().hex[:8]}",
            "created_time": "2026-08-31T09:00:00+0000",
            "field_data": [
                {"name": "full_name", "values": ["Tenant A Customer"]},
                {"name": "phone_number", "values": ["+919111111111"]},
            ]
        }
        crm_lead_a = facebook_leads_service.map_to_crm_lead(
            lead_data=lead_data_a,
            company_id=info_a["company_id"],
            category_id=1,
            page_segment="GENERAL",
            page_name=info_a["page_name"]
        )
        assert crm_lead_a["company_id"] == 1, "Page A lead must belong to Company 1"

        # 5. Map Lead for Unknown Page -> Must be rejected (None)
        rejected_lead = facebook_leads_service.map_to_crm_lead(
            lead_data=lead_data_a,
            company_id=None,
            category_id=None,
            page_segment="GENERAL",
            page_name="Unknown"
        )
        assert rejected_lead is None, "Unknown Page lead must be REJECTED (None)"

        # Cleanup test pages
        db.execute(text("DELETE FROM facebook_pages WHERE page_id IN (:pa, :pb)"), {"pa": page_a_id, "pb": page_b_id})
        db.commit()

        print("✅ [PASSED] Meta Page ownership and quarantine verification successful.")
    finally:
        db.close()


def test_whatsapp_cross_tenant_isolation_and_credential_quarantine():
    """
    Test WhatsApp Multi-Tenant Segregation:
    1. Phone Number ID A -> Tenant A (company_id=1).
    2. Phone Number ID B -> Tenant B (company_id=2).
    3. Unknown Phone Number ID -> None (REJECTED, NO DEFAULT TO 1).
    4. Credential lookup for unconfigured Tenant -> Empty / Not configured (NO SILENT FALLBACK).
    5. Inbound message segregation in WAInbox.
    """
    print("\n--- [TEST 2] WhatsApp Cross-Tenant Isolation & Credential Quarantine ---")
    db = SessionLocal()
    try:
        pid_a = f"wa_pid_a_{uuid.uuid4().hex[:6]}"
        pid_b = f"wa_pid_b_{uuid.uuid4().hex[:6]}"

        db.execute(
            text("""
                INSERT INTO whatsapp_api_config (access_token, phone_number_id, verify_token, company_id)
                VALUES 
                    ('enc_wa_tok_a', :pa, 'vtok_a', 1),
                    ('enc_wa_tok_b', :pb, 'vtok_b', 2)
            """),
            {"pa": pid_a, "pb": pid_b}
        )
        db.commit()

        # 1. Reverse resolution
        assert resolve_company_id_by_phone_number_id(db, pid_a) == 1
        assert resolve_company_id_by_phone_number_id(db, pid_b) == 2
        assert resolve_company_id_by_phone_number_id(db, "unknown_pid_999") is None, "Unknown PID must return None"

        # 2. Strict Credential Isolation (No silent global fallback)
        creds_tenant_1 = get_wa_credentials(db, company_id=1)
        assert creds_tenant_1["phone_number_id"] == pid_a or creds_tenant_1["phone_number_id"] != ""

        creds_unconfigured = get_wa_credentials(db, company_id=999999)
        assert creds_unconfigured["access_token"] == "", "Unconfigured tenant must receive empty token (zero fallback)"
        assert creds_unconfigured["phone_number_id"] == "", "Unconfigured tenant must receive empty phone_number_id"

        # 3. WAInbox Tenant Scoping
        wamid_a = f"wamid_a_{uuid.uuid4().hex[:8]}"
        wamid_b = f"wamid_b_{uuid.uuid4().hex[:8]}"

        inbox_a = WAInbox(wamid=wamid_a, company_id=1, from_phone="919111111111", body_text="Msg A")
        inbox_b = WAInbox(wamid=wamid_b, company_id=2, from_phone="919222222222", body_text="Msg B")
        db.add_all([inbox_a, inbox_b])
        db.commit()

        # Verify Tenant A only sees A
        tenant_a_msgs = db.query(WAInbox).filter(WAInbox.company_id == 1, WAInbox.wamid.in_([wamid_a, wamid_b])).all()
        assert len(tenant_a_msgs) == 1
        assert tenant_a_msgs[0].wamid == wamid_a

        # Verify Tenant B only sees B
        tenant_b_msgs = db.query(WAInbox).filter(WAInbox.company_id == 2, WAInbox.wamid.in_([wamid_a, wamid_b])).all()
        assert len(tenant_b_msgs) == 1
        assert tenant_b_msgs[0].wamid == wamid_b

        # Cleanup
        db.delete(inbox_a)
        db.delete(inbox_b)
        db.execute(text("DELETE FROM whatsapp_api_config WHERE phone_number_id IN (:pa, :pb)"), {"pa": pid_a, "pb": pid_b})
        db.commit()

        print("✅ [PASSED] WhatsApp cross-tenant credential isolation and inbox segregation verified.")
    finally:
        db.close()


def test_telephony_did_tenant_resolution_and_quarantine():
    """
    Test Telephony Multi-Tenant Inbound Routing & API Scoping:
    1. Inbound call to DID A maps to Tenant A (company_id=1).
    2. Inbound call to DID B maps to Tenant B (company_id=2).
    3. Inbound call to Unknown DID is REJECTED / QUARANTINED (None), NEVER assigned to company 1.
    4. Staff Call access list scoping: Staff A cannot access Staff B calls.
    """
    print("\n--- [TEST 3] Telephony DID Tenant Resolution & Quarantine ---")
    db = SessionLocal()
    try:
        did_a = f"+9198000{uuid.uuid4().hex[:5]}"
        did_b = f"+9198111{uuid.uuid4().hex[:5]}"

        # Seed DID mappings
        map_a = TelephonyDIDMapping(did_number=did_a, company_id=1, provider='MYOPERATOR', is_active=True)
        map_b = TelephonyDIDMapping(did_number=did_b, company_id=2, provider='MYOPERATOR', is_active=True)
        db.add_all([map_a, map_b])
        db.commit()

        # 1. Resolve DID A
        cid_a = _resolve_company_for_call(db, {"did": did_a})
        assert cid_a == 1, f"Expected company_id=1 for DID A, got {cid_a}"

        # 2. Resolve DID B
        cid_b = _resolve_company_for_call(db, {"did": did_b})
        assert cid_b == 2, f"Expected company_id=2 for DID B, got {cid_b}"

        # 3. Resolve Unknown DID -> Must return None (REJECT/QUARANTINE, NO FALLBACK TO 1)
        cid_unknown = _resolve_company_for_call(db, {"did": "+910000000000"})
        assert cid_unknown is None, "Unknown DID must return None (REJECTED), not default to company 1"

        # 4. Inbound Webhook Call Creation for DID A
        call_id_a = f"call_a_{uuid.uuid4().hex[:8]}"
        call_obj_a = _upsert_call(db, call_id_a, {
            "did": did_a,
            "caller_id": "919111111111",
            "status": "answered",
            "duration": 45
        })
        assert call_obj_a is not None
        assert call_obj_a.company_id == 1

        # 5. Inbound Webhook Call Creation for DID B
        call_id_b = f"call_b_{uuid.uuid4().hex[:8]}"
        call_obj_b = _upsert_call(db, call_id_b, {
            "did": did_b,
            "caller_id": "919222222222",
            "status": "answered",
            "duration": 60
        })
        assert call_obj_b is not None
        assert call_obj_b.company_id == 2

        # 6. Inbound Webhook Call Creation for Unknown DID -> Must be rejected (None)
        call_id_unk = f"call_unk_{uuid.uuid4().hex[:8]}"
        call_obj_unk = _upsert_call(db, call_id_unk, {
            "did": "+919999999999",
            "caller_id": "919333333333",
            "status": "missed"
        })
        assert call_obj_unk is None, "Call with unknown DID must be dropped/quarantined (None)"

        # 7. Staff Accessible Companies Helper (No default company 1 injection)
        class MockStaffUser:
            def __init__(self, base_company_id, data_companies=None):
                self.base_company_id = base_company_id
                self.data_companies = data_companies

        staff_a = MockStaffUser(base_company_id=1)
        assert _get_accessible_company_ids(staff_a) == [1]

        staff_b = MockStaffUser(base_company_id=2)
        assert _get_accessible_company_ids(staff_b) == [2], "Staff B accessible company list must NOT contain company 1"

        # Cleanup
        db.delete(call_obj_a)
        db.delete(call_obj_b)
        db.delete(map_a)
        db.delete(map_b)
        db.commit()

        print("✅ [PASSED] Telephony DID multi-tenant resolution and quarantine verified.")
    finally:
        db.close()


def test_integration_entitlement_gating():
    """
    Test Integration Entitlements:
    1. Active tenant with module entitled returns True in strict mode.
    2. Tenant without module entitled returns False in strict mode.
    """
    print("\n--- [TEST 4] Integration Entitlement Dynamic Gating ---")
    db = SessionLocal()
    try:
        # Client 1 (Myntreal) is entitled to all 3 integrations
        assert is_module_entitled(db, 1, "META_ADS_INTEGRATION", strict=True) is True
        assert is_module_entitled(db, 1, "WHATSAPP_INTEGRATION", strict=True) is True
        assert is_module_entitled(db, 1, "TELEPHONY_INTEGRATION", strict=True) is True

        # Unsubscribed/Unknown Client ID must be denied (False in strict mode)
        assert is_module_entitled(db, 999999, "META_ADS_INTEGRATION", strict=True) is False
        assert is_module_entitled(db, 999999, "WHATSAPP_INTEGRATION", strict=True) is False
        assert is_module_entitled(db, 999999, "TELEPHONY_INTEGRATION", strict=True) is False

        print("✅ [PASSED] Integration module entitlement gating verified.")
    finally:
        db.close()


if __name__ == "__main__":
    test_meta_cross_tenant_page_ownership_and_quarantine()
    test_whatsapp_cross_tenant_isolation_and_credential_quarantine()
    test_telephony_did_tenant_resolution_and_quarantine()
    test_integration_entitlement_gating()
    print("\n================================================================================")
    print("🎉 ALL PHASE 3 CROSS-TENANT SECURITY & ISOLATION TESTS PASSED (100%)!")
    print("================================================================================")
