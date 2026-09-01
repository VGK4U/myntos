"""
Platform Governance & Change Scope API Endpoints
DC_SAAS_SEGMENT_001: Enforces change scope governance, module catalogs, and public SaaS onboarding.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import date

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.staff import StaffEmployee, StaffRole
from app.models.staff_accounts import AssociatedCompany, PlatformChangeScopeLog, SegmentGovernanceConfig
from app.services.segment_governance import SegmentGovernanceService, SAAS_GLOBAL_MODULE_CATALOG
from app.core.security import SecurityManager

router = APIRouter(prefix="/platform/governance", tags=["Platform Governance"])


class ChangeScopeRecordRequest(BaseModel):
    change_title: str = Field(..., min_length=3, max_length=200)
    change_category: str = Field(default="CONFIG")
    scope_type: str = Field(..., description="SEGMENT_A, SEGMENT_B, CLIENT_SPECIFIC, BOTH_SEGMENTS")
    target_tenant_id: Optional[int] = None
    target_module: Optional[str] = None
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class PublicSaaSSignupRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=200)
    company_code: Optional[str] = Field(None, max_length=20)
    admin_name: str = Field(..., min_length=2, max_length=100)
    admin_phone: str = Field(..., min_length=10, max_length=15)
    admin_email: EmailStr
    city: Optional[str] = None
    state: Optional[str] = None
    selected_modules: Optional[List[str]] = Field(default=["CRM_LEADS", "SERVICE_TICKETS"])
    password: Optional[str] = None


@router.get("/change-logs")
async def get_change_scope_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    scope_filter: Optional[str] = Query(None, description="SEGMENT_A, SEGMENT_B, CLIENT_SPECIFIC, BOTH_SEGMENTS, ALL"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Retrieve audit trail of change scope decisions."""
    logs, total = SegmentGovernanceService.list_change_logs(db, page, page_size, scope_filter)
    return JSONResponse(content={
        "success": True,
        "logs": [l.to_dict() for l in logs],
        "total": total,
        "page": page,
        "page_size": page_size
    })


@router.post("/record-change")
async def record_change_scope(
    data: ChangeScopeRecordRequest,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Record an intentional scope boundary for a change."""
    try:
        log = SegmentGovernanceService.record_change_scope(
            db=db,
            change_title=data.change_title,
            scope_type=data.scope_type,
            change_category=data.change_category,
            target_tenant_id=data.target_tenant_id,
            target_module=data.target_module,
            old_value=data.old_value,
            new_value=data.new_value,
            operator=current_user,
            notes=data.notes
        )
        return JSONResponse(content={
            "success": True,
            "message": f"Change recorded with scope '{data.scope_type}'",
            "log": log.to_dict()
        })
    except Exception as e:
        return JSONResponse(status_code=400, content={"success": False, "message": str(e)})


@router.get("/module-catalog")
async def get_saas_module_catalog(
    tenant_id: Optional[int] = Query(None, description="Optional tenant ID to check licensing status"),
    db: Session = Depends(get_db)
):
    """Returns the global Segment B module catalog and licensing breakdown."""
    catalog = []
    for code, info in SAAS_GLOBAL_MODULE_CATALOG.items():
        is_licensed = False
        if tenant_id:
            is_licensed = SegmentGovernanceService.is_module_licensed_for_tenant(db, code, tenant_id)
        catalog.append({
            "module_code": code,
            "name": info["name"],
            "description": info["description"],
            "default_for_saas": info["default_for_saas"],
            "is_licensed_for_tenant": is_licensed
        })
    return JSONResponse(content={
        "success": True,
        "catalog": catalog
    })


# Public SaaS Registration Endpoint
saas_signup_router = APIRouter(prefix="/saas/auth", tags=["SaaS Public Auth"])

@saas_signup_router.post("/signup")
async def public_saas_signup(
    data: PublicSaaSSignupRequest,
    db: Session = Depends(get_db)
):
    """
    Public SaaS Onboarding Flow:
    1. Validates unique customer details
    2. Automatically assigns Segment B (SEGMENT_B_SAAS) & SAAS_CLIENT
    3. Generates sequential ZMP1808XXXX Company Code
    4. Creates Tenant Master Admin with isolated tenant boundary
    5. Returns login credentials & redirect URL
    """
    try:
        # Check duplicate company name
        c_name = data.company_name.strip()
        existing_comp = db.query(AssociatedCompany).filter(
            AssociatedCompany.company_name.ilike(c_name)
        ).first()
        if existing_comp:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"Company '{c_name}' is already registered."}
            )

        # Generate or sanitize company code
        if data.company_code:
            code = data.company_code.upper().strip()
        else:
            # Generate code from company initials
            words = c_name.split()
            code = "".join(w[0] for w in words if w)[:4].upper()
            if len(code) < 3:
                code = (c_name[:4]).upper().replace(" ", "")

        # Ensure code uniqueness
        counter = 1
        base_code = code
        while db.query(AssociatedCompany).filter_by(company_code=code).first():
            code = f"{base_code}{counter}"
            counter += 1

        # Modules
        mods = data.selected_modules if data.selected_modules else ["CRM_LEADS", "SERVICE_TICKETS"]

        # Create Segment B SaaS Company
        company = AssociatedCompany(
            company_name=c_name,
            company_code=code,
            company_type="SAAS_CLIENT",
            company_segment="SEGMENT_B_SAAS",
            phone=data.admin_phone.strip(),
            email=str(data.admin_email).strip().lower(),
            city=data.city.strip() if data.city else None,
            state=data.state.strip() if data.state else None,
            licensed_modules=mods,
            is_active=True
        )
        db.add(company)
        db.commit()
        db.refresh(company)

        # Provision Tenant Master Admin
        tenant_admin_role = db.query(StaffRole).filter(StaffRole.role_code == 'tenant_admin').first()
        role_id = tenant_admin_role.id if tenant_admin_role else 17

        admin_emp_code = f"{company.company_code}_ADMIN"
        if db.query(StaffEmployee).filter_by(emp_code=admin_emp_code).first():
            admin_emp_code = f"{company.company_code}_ADM_{company.id}"

        raw_pwd = data.password if (data.password and len(data.password) >= 6) else admin_emp_code
        tenant_admin = StaffEmployee(
            emp_code=admin_emp_code,
            full_name=data.admin_name.strip(),
            email=str(data.admin_email).strip().lower(),
            phone=data.admin_phone.strip(),
            designation="Tenant Master Administrator",
            role_id=role_id,
            base_company_id=company.id,
            data_companies=[{"company_id": company.id}],
            staff_type="TENANT_ADMIN",
            status="active",
            date_of_joining=date.today(),
            password_hash=SecurityManager.get_password_hash(raw_pwd)
        )
        db.add(tenant_admin)
        db.commit()
        db.refresh(tenant_admin)

        # Record Governance Audit Log
        SegmentGovernanceService.record_change_scope(
            db=db,
            change_title=f"Public SaaS Tenant Signup: {company.company_name} ({company.company_code})",
            scope_type="SEGMENT_B",
            change_category="TENANT_ONBOARDING",
            target_tenant_id=company.id,
            new_value={"company_id": company.id, "company_code": company.company_code, "segment": "SEGMENT_B_SAAS", "modules": mods},
            notes=f"Auto-provisioned via public /saas/signup with admin {admin_emp_code}"
        )

        formatted_company_id = f"ZMP1808{company.id:04d}"
        return JSONResponse(content={
            "success": True,
            "message": "Tenant registration successful! You can now log in to your SaaS workspace.",
            "company_id": formatted_company_id,
            "company_numeric_id": company.id,
            "company_name": company.company_name,
            "company_code": company.company_code,
            "segment": "SEGMENT_B_SAAS",
            "admin_emp_code": admin_emp_code,
            "admin_phone": tenant_admin.phone,
            "login_url": "/saas/login"
        })
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": f"Signup failed: {str(e)}"})
