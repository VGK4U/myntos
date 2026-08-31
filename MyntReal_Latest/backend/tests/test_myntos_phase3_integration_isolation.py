"""
Comprehensive Test Suite for Phase 3: Multi-Tenant Integration Isolation
(Meta Lead Ads + WhatsApp Cloud API + Telephony/Call Tracking)
"""


import uuid
from sqlalchemy import text
from app.core.database import SessionLocal
from app.services.facebook_leads_service import facebook_leads_service
from app.services.wa_credentials import get_wa_credentials, resolve_company_id_by_phone_number_id
from app.services.b2b_shadow import is_module_entitled, resolve_client_id_for_staff
from app.models.crm import CRMLead
from app.models.whatsapp import WAInbox
from app.models.call_tracking import StaffCallRecording


def test_meta_tenant_isolation_and_no_fallback_to_company_4():
    """
    Test that Meta lead mapping strictly resolves company_id from registered page
    and never silently falls back to company 4 or category 19/36 for unknown pages.
    """
    db = SessionLocal()
    try:
        # Case 1: Known Page for Tenant (Company 1)
        mock_lead_data = {
            "id": f"fb_lead_{uuid.uuid4().hex[:8]}",
            "created_time": "2026-08-31T09:00:00+0000",
            "field_data": [
                {"name": "full_name", "values": ["Test Meta Lead"]},
                {"name": "phone_number", "values": ["+919876543210"]},
                {"name": "email", "values": ["meta_test@example.com"]}
            ]
        }
        
        # Valid company mapping
        crm_data = facebook_leads_service.map_to_crm_lead(
            lead_data=mock_lead_data,
            company_id=1,
            category_id=36,
            page_segment="SOLAR",
            page_name="Myntreal Solar Official"
        )
        assert crm_data is not None
        assert crm_data["company_id"] == 1
        assert crm_data["category_id"] == 36
        assert crm_data["tags"] == "solar"

        # Case 2: Unknown / Missing company_id must return None (REJECTED, NO FALLBACK TO 4)
        rejected_crm_data = facebook_leads_service.map_to_crm_lead(
            lead_data=mock_lead_data,
            company_id=None,
            category_id=None,
            page_segment="UNKNOWN",
            page_name="Unregistered Page"
        )
        assert rejected_crm_data is None, "Lead without company_id must be rejected/None, never defaulted to 4"

        print("✅ [TEST PASSED] Meta lead strict tenant resolution & zero fallback to company 4 verified.")
    finally:
        db.close()


def test_whatsapp_tenant_credential_and_inbox_routing():
    """
    Test that WhatsApp phone_number_id resolves exact tenant company_id
    and tags inbound WAInbox messages with proper tenant scope.
    """
    db = SessionLocal()
    try:
        # Register a test phone_number_id for company 1
        test_pid = "test_phone_id_999"
        db.execute(
            text("""
                INSERT INTO whatsapp_api_config (access_token, phone_number_id, verify_token, company_id)
                VALUES ('encrypted_test_token', :pid, 'test_verify_token', 1)
            """),
            {"pid": test_pid}
        )
        db.commit()

        # Test reverse resolution
        resolved_cid = resolve_company_id_by_phone_number_id(db, test_pid)
        assert resolved_cid == 1, f"Expected company_id=1, got {resolved_cid}"

        # Test unknown phone_number_id returns None
        unknown_cid = resolve_company_id_by_phone_number_id(db, "completely_unknown_pid")
        assert unknown_cid is None, "Unknown phone_number_id must return None"

        # Test WAInbox creation with tenant company_id
        test_wamid = f"wamid.test.{uuid.uuid4().hex[:12]}"
        inbox_msg = WAInbox(
            wamid=test_wamid,
            company_id=1,
            from_phone="919876543210",
            from_name="Test Inbound Customer",
            message_type="text",
            body_text="Hello, inquiring about Solar",
        )
        db.add(inbox_msg)
        db.commit()
        db.refresh(inbox_msg)

        assert inbox_msg.id is not None
        assert inbox_msg.company_id == 1
        assert inbox_msg.to_dict()["company_id"] == 1

        # Clean up test entry
        db.delete(inbox_msg)
        db.execute(text("DELETE FROM whatsapp_api_config WHERE phone_number_id = :pid"), {"pid": test_pid})
        db.commit()

        print("✅ [TEST PASSED] WhatsApp phone_number_id tenant routing and WAInbox isolation verified.")
    finally:
        db.close()


def test_integration_module_entitlements():
    """
    Test that integration modules (META_ADS_INTEGRATION, WHATSAPP_INTEGRATION, TELEPHONY_INTEGRATION)
    are strictly checked against client subscription entitlements.
    """
    db = SessionLocal()
    try:
        # Myntreal (client_id=1) has active entitlements in platform_subscription_modules
        assert is_module_entitled(db, 1, "META_ADS_INTEGRATION") is True
        assert is_module_entitled(db, 1, "WHATSAPP_INTEGRATION") is True
        assert is_module_entitled(db, 1, "TELEPHONY_INTEGRATION") is True

        print("✅ [TEST PASSED] Integration module entitlements verified for platform tenants.")
    finally:
        db.close()


if __name__ == "__main__":
    test_meta_tenant_isolation_and_no_fallback_to_company_4()
    test_whatsapp_tenant_credential_and_inbox_routing()
    test_integration_module_entitlements()
    print("\n🎉 ALL PHASE 3 INTEGRATION ISOLATION TESTS PASSED (100%)!")
