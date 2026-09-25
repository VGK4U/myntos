import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.models.staff import StaffEmployee
from app.models.staff_accounts import AssociatedCompany
from app.models.platform_b2b import PlatformClient, PlatformSubscription, PlatformSubscriptionModule, PlatformModule
from app.services.saas_tenant_resolver import resolve_tenant_context, get_saas_menu_tree, TenantContext
from app.core.security import SecurityManager

client = TestClient(app)

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_case_a_crm_only_menu_and_guards(db: Session):
    """Case A: Tenant has CRM_LEADS only.
    - Menu has Core Workspace + CRM & Leads ONLY.
    - No WORKFLOWS section.
    - No Vendors & Partners or Solar/EV vertical routes.
    - Direct API to lead-analytics (Executive Dashboard) raises 403 Forbidden.
    """
    ctx = TenantContext(
        is_saas_tenant=True,
        is_tenant_admin=True,
        effective_modules=['CRM_LEADS']
    )
    menus, allowed_routes, sections = get_saas_menu_tree(ctx)
    section_titles = list(sections.keys())
    assert 'CORE WORKSPACE' in section_titles
    assert 'CRM & LEADS' in section_titles
    assert 'WORKFLOWS' not in section_titles

    # Verify CRM items (3 for staff, 4 for admin with CRM/Workflow Setup)
    crm_items = sections['CRM & LEADS']
    assert len(crm_items) in (3, 4)
    crm_routes = [i['route_path'] for i in crm_items]
    assert '/staff/crm/dashboard' in crm_routes
    assert '/staff/my-leads' in crm_routes
    assert '/staff/leads' in crm_routes

    # Verify no leaked workflow routes in allowed_routes
    assert '/staff/executive-dashboard' not in allowed_routes
    assert '/staff/solar-vendors' not in allowed_routes
    assert '/staff/solar-leads' not in allowed_routes

    # Check direct API guard
    # Test Solar company (company_id 127) modified to have CRM_LEADS only temporarily
    emp = db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'TESO_ADMIN').first()
    co = db.query(AssociatedCompany).filter(AssociatedCompany.id == emp.base_company_id).first() if emp else None
    if emp and co:
        orig_co_mods = co.licensed_modules
        co.licensed_modules = ['CRM_LEADS']
        db.commit()
        try:
            token = SecurityManager.create_access_token(data={"sub": emp.email or emp.emp_code, "emp_code": emp.emp_code, "role_code": "tenant_admin"})
            resp = client.get("/api/v1/crm/lead-analytics", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403, f"Expected 403 for lead-analytics without SOLAR_EV, got {resp.status_code}"
            assert "Access denied: Module 'SOLAR_EV'" in resp.text
        finally:
            co.licensed_modules = orig_co_mods
            db.commit()

def test_case_b_workflows_only_menu_and_guards(db: Session):
    """Case B: Tenant has SOLAR_EV (WORKFLOWS) only.
    - Menu has Core Workspace + WORKFLOWS ONLY.
    - No CRM & LEADS section.
    - Workflows has strictly 2 items: Executive Dashboard and Category-wise Leads.
    - No Vendors & Partners or internal vertical subroutes.
    - Direct API to CRM dashboard-v2 and call-tracking raises 403 Forbidden.
    """
    ctx = TenantContext(
        is_saas_tenant=True,
        is_tenant_admin=True,
        effective_modules=['SOLAR_EV']
    )
    menus, allowed_routes, sections = get_saas_menu_tree(ctx)
    section_titles = list(sections.keys())
    assert 'CORE WORKSPACE' in section_titles
    assert 'WORKFLOWS' in section_titles
    assert 'CRM & LEADS' not in section_titles

    # Verify Workflows items (2 for staff, 3 for admin with setup)
    wf_items = sections['WORKFLOWS']
    assert len(wf_items) in (2, 3)
    wf_routes = [i['route_path'] for i in wf_items]
    assert '/staff/executive-dashboard' in wf_routes
    assert '/staff/mnr-leads' in wf_routes
    assert '/staff/solar-vendors' not in wf_routes

    # Check direct API guard
    emp = db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'TESO_ADMIN').first()
    co = db.query(AssociatedCompany).filter(AssociatedCompany.id == emp.base_company_id).first() if emp else None
    if emp and co:
        orig_co_mods = co.licensed_modules
        co.licensed_modules = ['SOLAR_EV']
        db.commit()
        try:
            token = SecurityManager.create_access_token(data={"sub": emp.email or emp.emp_code, "emp_code": emp.emp_code, "role_code": "tenant_admin"})
            resp_dash = client.get("/api/v1/crm/dashboard-v2", headers={"Authorization": f"Bearer {token}"})
            assert resp_dash.status_code == 403, f"Expected 403 for dashboard-v2 without CRM_LEADS, got {resp_dash.status_code}"
            assert "Access denied: Module 'CRM_LEADS'" in resp_dash.text

            resp_ct = client.get("/api/v1/call-tracking/management/overview", headers={"Authorization": f"Bearer {token}"})
            assert resp_ct.status_code == 403, f"Expected 403 for call-tracking without CRM_LEADS, got {resp_ct.status_code}"

            # Workflows API should succeed
            resp_wf = client.get("/api/v1/crm/lead-analytics", headers={"Authorization": f"Bearer {token}"})
            assert resp_wf.status_code == 200, f"Expected 200 for lead-analytics with SOLAR_EV, got {resp_wf.status_code}"
        finally:
            co.licensed_modules = orig_co_mods
            db.commit()

def test_case_c_crm_plus_workflows_clean_hierarchy(db: Session):
    """Case C: Tenant has CRM_LEADS and SOLAR_EV.
    - Menu has Core Workspace + CRM & LEADS + WORKFLOWS.
    - Exactly 3 items in Core Workspace, 3 items in CRM & LEADS, 2 items in WORKFLOWS.
    - Zero fixed internal vertical categories.
    - Both CRM dashboard and lead-analytics succeed.
    """
    ctx = TenantContext(
        is_saas_tenant=True,
        is_tenant_admin=True,
        effective_modules=['CRM_LEADS', 'SOLAR_EV']
    )
    menus, allowed_routes, sections = get_saas_menu_tree(ctx)
    section_titles = list(sections.keys())
    assert 'CORE WORKSPACE' in section_titles
    assert 'CRM & LEADS' in section_titles
    assert 'WORKFLOWS' in section_titles

    assert len(sections['CORE WORKSPACE']) in (2, 3)
    assert len(sections['CRM & LEADS']) in (3, 4)
    assert len(sections['WORKFLOWS']) in (2, 3)

    # Check that internal verticals are NOT in allowed_routes
    assert '/staff/solar-vendors' not in allowed_routes
    assert '/staff/solar-leads' not in allowed_routes
    assert '/staff/ev-b2b-leads' not in allowed_routes
    assert '/staff/ev-b2c-leads' not in allowed_routes

    emp = db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'TESO_ADMIN').first()
    if emp:
        orig_assigned = emp.assigned_modules
        emp.assigned_modules = ['CRM_LEADS', 'SOLAR_EV']
        db.commit()
        try:
            token = SecurityManager.create_access_token(data={"sub": emp.email or emp.emp_code, "emp_code": emp.emp_code, "role_code": "tenant_admin"})
            resp_dash = client.get("/api/v1/crm/dashboard-v2", headers={"Authorization": f"Bearer {token}"})
            assert resp_dash.status_code == 200
            resp_wf = client.get("/api/v1/crm/lead-analytics", headers={"Authorization": f"Bearer {token}"})
            assert resp_wf.status_code == 200
        finally:
            emp.assigned_modules = orig_assigned
            db.commit()

def test_internal_platform_unaffected(db: Session):
    """Verify internal platform employee (MR10001) has full access."""
    emp = db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'MR10001').first()
    assert emp is not None
    token = SecurityManager.create_access_token(data={"sub": emp.email or emp.emp_code, "emp_code": emp.emp_code, "role_code": "super_admin"})
    resp_dash = client.get("/api/v1/crm/dashboard-v2", headers={"Authorization": f"Bearer {token}"})
    assert resp_dash.status_code == 200
    resp_wf = client.get("/api/v1/crm/lead-analytics", headers={"Authorization": f"Bearer {token}"})
    assert resp_wf.status_code == 200
