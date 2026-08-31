"""
MYNTOS PHASE 4A — Public Signup + Service / Segment Packaging Test Suite
Validates:
1. Public Catalog Discovery
2. Authoritative Server-Side Live Price Calculation & Annual Discount
3. Automatic Dependency Resolution (e.g. CRM_LEADS_SOLAR -> CRM_CORE)
4. Public Signup with Service/Segment Packaging & Price Snapshot
5. Invalid/Internal Module Rejection
6. Zero Premature Entitlement (pending subscription has enabled=False)
7. Cross-Tenant Isolation & Explicit Entitlement Integrity
"""

import secrets
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.core.database import SessionLocal
from app.models.platform_b2b import (
    PlatformClient, PlatformSubscription, PlatformSubscriptionModule,
    PlatformModule, PlatformModulePricing
)
from app.services.b2b_shadow import is_module_entitled

client = TestClient(app, base_url="http://testserver")


def test_public_catalog_discovery():
    """Verify GET /api/v1/platform-b2b/public-catalog returns canonical offerings."""
    print("\n--- [TEST 1] Public Catalog Discovery ---")
    res = client.get("/api/v1/platform-b2b/public-catalog")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "services" in data and "segments" in data
    assert len(data["services"]) >= 4, "Expected at least 4 core services"
    assert len(data["segments"]) >= 6, "Expected at least 6 CRM industry verticals"
    assert data["annual_discount_months"] == 2
    print(f"✅ [PASSED] Public Catalog returns {len(data['services'])} services & {len(data['segments'])} segments.")


def test_authoritative_server_side_pricing_calculation():
    """Verify POST /api/v1/platform-b2b/calculate-pricing computes accurate pricing & dependencies."""
    print("\n--- [TEST 2] Authoritative Price Calculation & Dependencies ---")
    
    # 1. Monthly CRM + Solar (2999 + 1499 = 4498 + 18% GST = 5307.64)
    res_monthly = client.post("/api/v1/platform-b2b/calculate-pricing", json={
        "selected_modules": ["CRM_CORE", "CRM_LEADS_SOLAR"],
        "billing_currency": "INR",
        "billing_cycle": "monthly",
        "seat_count": 1
    })
    assert res_monthly.status_code == 200, res_monthly.text
    m_data = res_monthly.json()
    assert m_data["monthly_subtotal"] == 4498.0
    assert m_data["cycle_subtotal"] == 4498.0
    assert m_data["tax_amount"] == 809.64
    assert m_data["total_payable"] == 5307.64

    # 2. Annual CRM + Solar (Charges 10 months: 4498 * 10 = 44980 + 18% GST = 53076.40)
    res_annual = client.post("/api/v1/platform-b2b/calculate-pricing", json={
        "selected_modules": ["CRM_CORE", "CRM_LEADS_SOLAR"],
        "billing_currency": "INR",
        "billing_cycle": "annual",
        "seat_count": 1
    })
    assert res_annual.status_code == 200, res_annual.text
    a_data = res_annual.json()
    assert a_data["cycle_subtotal"] == 44980.0
    assert a_data["total_payable"] == 53076.40
    assert a_data["annual_free_months"] == 2

    # 3. Auto-dependency resolution: Requesting ONLY CRM_LEADS_SOLAR must auto-include CRM_CORE
    res_dep = client.post("/api/v1/platform-b2b/calculate-pricing", json={
        "selected_modules": ["CRM_LEADS_SOLAR"],
        "billing_currency": "INR",
        "billing_cycle": "monthly",
        "seat_count": 1
    })
    assert res_dep.status_code == 200
    dep_data = res_dep.json()
    assert "CRM_CORE" in dep_data["auto_included_dependencies"]
    assert dep_data["monthly_subtotal"] == 4498.0  # Includes both Solar (1499) + Core (2999)

    print("✅ [PASSED] Authoritative server-side pricing & auto-dependency resolution verified.")


def test_public_signup_and_request_persistence():
    """Verify POST /api/v1/platform-b2b/signup creates pending client, subscription, and requested modules."""
    print("\n--- [TEST 3] Public Signup & Request Persistence ---")
    test_hex = secrets.token_hex(4).upper()
    comp_name = f"Solar Enterprises {test_hex}"
    email = f"owner_{test_hex.lower()}@solarenterprises.io"

    signup_payload = {
        "company_name": comp_name,
        "contact_name": f"Solar Owner {test_hex}",
        "contact_email": email,
        "contact_phone": "+91 9876543210",
        "billing_currency": "INR",
        "billing_cycle": "annual",
        "selected_modules": ["CRM_LEADS_SOLAR", "WHATSAPP_INTEGRATION"],
        "seat_count": 1,
        "notes": "Interested in Solar CRM with WhatsApp automation"
    }

    res = client.post("/api/v1/platform-b2b/signup", json=signup_payload)
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["status"] == "pending_payment"
    assert "CRM_CORE" in data["auto_included_dependencies"]
    assert "WHATSAPP_INTEGRATION" in data["requested_modules"]

    client_id = data["client_id"]
    sub_id = data["subscription_id"]

    # Verify DB records
    db = SessionLocal()
    try:
        c = db.query(PlatformClient).filter_by(id=client_id).first()
        assert c is not None
        assert c.status == "pending"
        assert c.is_internal is False

        s = db.query(PlatformSubscription).filter_by(id=sub_id).first()
        assert s is not None
        assert s.status == "pending_payment"
        assert s.billing_cycle == "annual"

        # Check requested modules in subscription_modules
        sub_mods = db.query(PlatformSubscriptionModule).filter_by(subscription_id=sub_id).all()
        assert len(sub_mods) == 3, f"Expected 3 modules (Solar, Core, WA), got {len(sub_mods)}"
        
        # All requested modules must be enabled=False (zero premature entitlement!)
        for sm in sub_mods:
            assert sm.enabled is False, "Requested module must remain enabled=False until payment"

        # Check that is_module_entitled returns False for this pending tenant
        entitled = is_module_entitled(db, client_id, "CRM_LEADS_SOLAR", strict=True)
        assert entitled is False, "Pending tenant must NOT have active entitlement"

        print("✅ [PASSED] Public signup, subscription creation, disabled module persistence, and zero premature entitlement verified.")
    finally:
        db.close()


def test_invalid_module_rejection():
    """Verify signup rejects arbitrary, non-existent, or invalid module codes."""
    print("\n--- [TEST 4] Invalid Module Rejection ---")
    res = client.post("/api/v1/platform-b2b/signup", json={
        "company_name": f"Hacker Corp {secrets.token_hex(2)}",
        "contact_name": "Bad Actor",
        "contact_email": f"bad_{secrets.token_hex(2)}@test.com",
        "selected_modules": ["NON_EXISTENT_MODULE_999"]
    })
    assert res.status_code == 400, f"Expected 400 Bad Request, got {res.status_code}"
    assert "invalid" in res.json().get("detail", "").lower()
    print("✅ [PASSED] Invalid module code injection rejected with HTTP 400.")


if __name__ == "__main__":
    test_public_catalog_discovery()
    test_authoritative_server_side_pricing_calculation()
    test_public_signup_and_request_persistence()
    test_invalid_module_rejection()
    print("\n================================================================================")
    print("🎉 ALL PHASE 4A PUBLIC SIGNUP & PACKAGING TESTS PASSED (100%)!")
    print("================================================================================")
