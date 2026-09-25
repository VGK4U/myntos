import pytest
import asyncio
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.staff import StaffEmployee
from app.models.staff_accounts import AssociatedCompany
from app.models.platform_b2b import PlatformClient
from app.models.signup_category import SignupCategory
from app.models.crm import CRMLead
from app.models.crm_handler import CRMLeadHandler, CRMLeadHandlerMember
from app.api.v1.endpoints.call_tracking import (
    resolve_call_tracking_scope,
    get_call_management_overview,
    get_staff_call_details
)
from app.api.v1.endpoints.crm import (
    get_segment_routing_pool,
    get_solar_vendors,
    create_lead,
    LeadCreate
)
from app.api.v1.endpoints.saas_crm_setup import (
    get_crm_setup_overview,
    list_tenant_segments,
    create_tenant_segment,
    update_tenant_segment,
    SegmentCreateSchema,
    SegmentUpdateSchema,
    StaffAssignmentItem
)
from fastapi import HTTPException


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def teso_admin(db: Session):
    admin = db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'TESO_ADMIN').first()
    assert admin is not None, "TESO_ADMIN must exist"
    return admin


@pytest.fixture
def platform_admin(db: Session):
    admin = db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'MR10001').first()
    assert admin is not None, "MR10001 platform admin must exist"
    return admin


def test_01_call_tracking_multi_tenant_isolation(db: Session, teso_admin, platform_admin):
    """
    Verify Call Tracking Isolation:
    - SaaS tenant admin sees only their own calls (0 platform calls).
    - Platform admin sees full platform calls (> 0).
    """
    is_saas, saas_staff, saas_cos = resolve_call_tracking_scope(db, teso_admin)
    assert is_saas is True, "teso_admin must be resolved as SaaS tenant"
    assert 127 in saas_cos, "Company 127 must be in SaaS tenant scope"
    assert len(saas_staff) > 0, "SaaS tenant must have staff members"

    # Call management overview for SaaS tenant
    res_saas = asyncio.run(get_call_management_overview(quick_range='last_7', db=db, current_user=teso_admin))
    assert res_saas["success"] is True
    assert res_saas["overview"]["total_calls"] == 0, "SaaS tenant admin must not see platform calls"

    # Call management overview for Platform Admin
    res_platform = asyncio.run(get_call_management_overview(quick_range='last_7', db=db, current_user=platform_admin))
    assert res_platform["success"] is True
    assert res_platform["overview"]["total_calls"] > 0, "Platform admin must see platform calls"


def test_02_call_tracking_cross_tenant_forbidden(db: Session, teso_admin):
    """
    Verify that SaaS tenant cannot access call details of an employee belonging to another tenant / platform.
    """
    # Employee 1 is platform admin outside tenant 190
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_staff_call_details(target_staff_id=1, db=db, current_user=teso_admin))
    assert exc_info.value.status_code == 403
    assert "Access denied" in exc_info.value.detail


def test_03_saas_crm_setup_overview(db: Session, teso_admin):
    """
    Verify /api/v1/saas/crm-setup/overview returns companies, segments, staff routing, and settings.
    """
    overview = get_crm_setup_overview(db=db, current_user=teso_admin)
    assert overview["success"] is True
    assert "companies" in overview
    assert "segments" in overview
    assert "staff_members" in overview
    assert "crm_settings" in overview

    # Verify company 127 is present
    co_ids = [c["id"] for c in overview["companies"]]
    assert 127 in co_ids, "Company 127 must be in tenant companies list"


def test_04_segment_lifecycle_with_routing_and_vendor(db: Session, teso_admin):
    """
    Verify creating and updating a segment with:
    - Staff routing pool (CRMLeadHandler / CRMLeadHandlerMember)
    - Vendor legal entity (associated_company with GST)
    """
    staff_member = db.query(StaffEmployee).filter(StaffEmployee.base_company_id == 127).first()
    assert staff_member is not None, "At least one staff member must exist for company 127"

    # 1. Create Segment
    seg_name = f"Test Solar Commercial {datetime.utcnow().strftime('%H%M%S')}"
    create_payload = SegmentCreateSchema(
        company_id=127,
        name=seg_name,
        slug=f"test-solar-{datetime.utcnow().strftime('%H%M%S')}",
        icon="fa-solar-panel",
        description="Commercial rooftop solar projects",
        display_order=5,
        vendor_company_id=127,
        staff_members=[StaffAssignmentItem(employee_id=staff_member.id, assignment_weight=2)]
    )

    created = create_tenant_segment(payload=create_payload, db=db, current_user=teso_admin)
    assert created["success"] is True
    seg_id = created["segment"]["id"]

    # Verify CRMLeadHandler exists
    handler = db.query(CRMLeadHandler).filter(
        CRMLeadHandler.company_id == 127,
        CRMLeadHandler.category_id == seg_id
    ).first()
    assert handler is not None, "CRMLeadHandler must be auto-created for segment"
    assert handler.is_active is True

    # Verify CRMLeadHandlerMember exists
    member = db.query(CRMLeadHandlerMember).filter(
        CRMLeadHandlerMember.handler_id == handler.id,
        CRMLeadHandlerMember.employee_id == staff_member.id
    ).first()
    assert member is not None, "CRMLeadHandlerMember must be auto-created"
    assert member.is_active is True

    # Verify routing pool endpoint
    pool_res = get_segment_routing_pool(category_id=seg_id, db=db, current_employee=teso_admin)
    assert pool_res["success"] is True
    assert len(pool_res["routing_pool"]) == 1
    assert pool_res["routing_pool"][0]["employee_id"] == staff_member.id

    # 2. Update Segment
    update_payload = SegmentUpdateSchema(
        description="Updated commercial rooftop solar projects",
        vendor_company_id=127,
        staff_members=[StaffAssignmentItem(employee_id=staff_member.id, assignment_weight=5)]
    )
    updated = update_tenant_segment(segment_id=seg_id, payload=update_payload, db=db, current_user=teso_admin)
    assert updated["success"] is True

    # Check member is still active
    db.refresh(member)
    assert member.is_active is True


def test_05_lead_creation_auto_routing_by_segment(db: Session, teso_admin):
    """
    Verify that creating a lead under a segment with a routing pool
    auto-assigns the lead to the routed staff member when primary_owner_id is omitted.
    """
    staff_member = db.query(StaffEmployee).filter(StaffEmployee.base_company_id == 127).first()
    assert staff_member is not None

    # Find segment for company 127 (most recently created in test_04)
    handler = db.query(CRMLeadHandler).filter(
        CRMLeadHandler.company_id == 127,
        CRMLeadHandler.is_active == True
    ).order_by(CRMLeadHandler.id.desc()).first()
    assert handler is not None, "Handler must exist for company 127"

    # Create lead without explicit owner
    lead_payload = LeadCreate(
        name="Auto Routed Solar Inquiry",
        phone=f"98{int(datetime.utcnow().timestamp()) % 100000000:08d}",
        category_id=handler.category_id,
        company_id=127,
        status="new"
    )

    lead_res = create_lead(lead_data=lead_payload, company_id=127, db=db, current_employee=teso_admin)
    assert lead_res["success"] is True
    new_lead_id = lead_res["data"]["id"]

    created_lead = db.query(CRMLead).filter(CRMLead.id == new_lead_id).first()
    assert created_lead.primary_owner_id is not None, "Lead must be auto-assigned to routing pool member"
    assert created_lead.primary_owner_id == staff_member.id


def test_06_solar_vendors_scoping_for_saas_tenant(db: Session, teso_admin):
    """
    Verify /api/v1/crm/solar-vendors returns AssociatedCompany legal entities
    with GST number and address for SaaS tenants.
    """
    res = get_solar_vendors(db=db, current_employee=teso_admin)
    assert "vendors" in res
    assert len(res["vendors"]) > 0

    # Ensure the returned vendor is Test Solar with GSTIN
    vendor = next((v for v in res["vendors"] if v["id"] == 127), None)
    assert vendor is not None, "Company 127 must be returned as solar vendor entity"
    assert vendor["vendor_name"] == "Test Solar"
    assert "gst_number" in vendor
    assert "pan_number" in vendor


def test_07_solar_doc_vendor_resolution(db: Session, teso_admin):
    """
    Verify that generating a solar quotation with vendor_id = 127 (AssociatedCompany)
    resolves the SaaS legal entity with GSTIN and does not fail on vendor lookup.
    """
    from app.api.v1.endpoints.crm import generate_solar_doc

    lead = db.query(CRMLead).filter(CRMLead.company_id == 127).first()
    assert lead is not None

    payload = {
        "doc_type": "quotation",
        "vendor_id": 127,
        "kw_size": "3",
        "quote_value": 150000,
        "discount": 0,
        "final_amount": 150000,
        "subsidy": 78000
    }

    # Running generate_solar_doc: it will resolve vendor_id 127
    # Note: May raise 422 if other required customer fields like address/consumer number are missing on test lead,
    # but must NOT raise 404 (Solar vendor not found).
    try:
        res = asyncio.run(generate_solar_doc(lead_id=lead.id, payload=payload, db=db, current_employee=teso_admin))
        assert res is not None
    except HTTPException as e:
        assert e.status_code != 404, f"Should not fail with 404 vendor not found: {e.detail}"
        assert e.status_code in (422, 200, 201), f"Expected validation or success: {e.status_code} - {e.detail}"

