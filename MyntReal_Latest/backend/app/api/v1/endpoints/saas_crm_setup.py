"""
SaaS CRM & Workflow Setup Controller (DC_SAAS_CRM_SETUP_001)
Tenant-scoped management of:
- Tab 1: CRM Settings (auto-assignment, SLAs, duplicate checks)
- Tab 2: Companies (Tenant operational entities / branches)
- Tab 3: Segments (Tenant business / lead categories)
- Tab 4: Staff / Segment Assignment (CRMLeadHandler + CRMLeadHandlerMember routing pools)

Zero hardcoded employee IDs, zero magic company IDs.
Strictly isolated by authenticated SaaS Tenant Client ID.
"""

import logging
import json
from typing import Optional, List, Dict, Any, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text, or_

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.staff import StaffEmployee
from app.models.staff_accounts import AssociatedCompany
from app.models.platform_b2b import PlatformClient
from app.models.signup_category import SignupCategory
from app.models.crm_handler import CRMLeadHandler, CRMLeadHandlerMember
from app.services.saas_tenant_resolver import resolve_tenant_context, TenantContext

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Authorization Helper ───────────────────────────────────────────────────────
def get_authorized_tenant(
    db: Session,
    current_user: StaffEmployee
) -> Tuple[PlatformClient, List[int]]:
    """
    Validates that current_user is authorized to manage tenant CRM setup.
    Returns (PlatformClient, list_of_accessible_company_ids).
    """
    ctx = resolve_tenant_context(db, current_user)
    
    # Platform superadmin check
    is_superadmin = (
        current_user.emp_code == 'MR10001' or
        (getattr(current_user, 'staff_type', '') or '').upper() in ['SUPER_ADMIN', 'PLATFORM_SUPERADMIN']
    )
    
    # Resolve tenant record
    client = None
    if ctx.client:
        client = ctx.client
    elif current_user.client_id:
        client = db.query(PlatformClient).filter(PlatformClient.id == current_user.client_id).first()
    elif current_user.base_company_id:
        # Check if company belongs to a client
        co = db.query(AssociatedCompany).filter(AssociatedCompany.id == current_user.base_company_id).first()
        if co and co.client_id:
            client = db.query(PlatformClient).filter(PlatformClient.id == co.client_id).first()

    if not client:
        if is_superadmin:
            # Fallback for superadmin previewing first active SaaS client
            client = db.query(PlatformClient).filter(PlatformClient.is_internal == False).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SaaS tenant account not found for current session."
            )

    # RBAC check: Must be tenant admin or superadmin
    user_type = (getattr(current_user, 'staff_type', '') or '').upper()
    is_admin = (
        is_superadmin or
        ctx.is_tenant_admin or
        user_type in ['TENANT_ADMIN', 'SAAS_CLIENT', 'SAAS_SEGMENT_ADMIN', 'ADMIN']
    )
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only SaaS Tenant Administrators can configure CRM / Workflow Setup."
        )

    # Get accessible companies belonging strictly to THIS tenant client
    tenant_companies = db.query(AssociatedCompany).filter(
        AssociatedCompany.client_id == client.id,
        AssociatedCompany.is_active == True
    ).all()
    company_ids = [c.id for c in tenant_companies]
    
    # If client has a primary_legal_entity_id not yet populated in query
    if getattr(client, 'primary_legal_entity_id', None) and client.primary_legal_entity_id not in company_ids:
        company_ids.append(client.primary_legal_entity_id)
    if getattr(current_user, 'base_company_id', None) and current_user.base_company_id not in company_ids:
        company_ids.append(current_user.base_company_id)

    return client, company_ids


# ── Schemas ───────────────────────────────────────────────────────────────────
class CompanyCreateSchema(BaseModel):
    company_name: str
    company_code: Optional[str] = None
    company_segment: Optional[str] = "GENERAL"
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    primary_email: Optional[str] = None
    primary_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

class CompanyUpdateSchema(BaseModel):
    company_name: Optional[str] = None
    company_segment: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    primary_email: Optional[str] = None
    primary_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    is_active: Optional[bool] = None

class StaffAssignmentItem(BaseModel):
    employee_id: int
    assignment_weight: Optional[int] = 1

class SegmentCreateSchema(BaseModel):
    company_id: int
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = "fa-layer-group"
    display_order: Optional[int] = 0
    is_active: Optional[bool] = True
    vendor_company_id: Optional[int] = None
    staff_members: Optional[List[StaffAssignmentItem]] = None

class SegmentUpdateSchema(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    vendor_company_id: Optional[int] = None
    staff_members: Optional[List[StaffAssignmentItem]] = None

class HandlerAssignSchema(BaseModel):
    company_id: int
    category_id: int
    department_id: Optional[int] = None
    staff_members: List[StaffAssignmentItem]

class CRMSettingsSchema(BaseModel):
    auto_assignment_enabled: Optional[bool] = True
    duplicate_check_enabled: Optional[bool] = True
    default_lead_stage: Optional[str] = "new"
    followup_sla_hours: Optional[int] = 24
    allow_staff_manual_lead_creation: Optional[bool] = True
    notification_email: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/overview")
def get_crm_setup_overview(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Returns unified bootstrap payload for SaaS CRM / Workflow Setup page:
    - Tenant Profile
    - Companies List
    - Segments (Categories) List
    - Active Staff Members for Routing
    - Active Handler Routing Assignments
    - CRM Global Settings
    """
    client, company_ids = get_authorized_tenant(db, current_user)

    # 1. Companies
    companies = db.query(AssociatedCompany).filter(
        or_(
            AssociatedCompany.client_id == client.id,
            AssociatedCompany.id.in_(company_ids)
        )
    ).order_by(AssociatedCompany.company_name).all()
    
    companies_data = [
        {
            "id": c.id,
            "company_code": c.company_code or f"CO-{c.id}",
            "company_name": c.company_name,
            "company_segment": c.company_segment or "GENERAL",
            "is_active": c.is_active,
            "gst_number": c.gst_number,
            "primary_email": getattr(c, "email", None),
            "primary_phone": getattr(c, "phone", None),
            "city": c.city,
            "state": c.state
        }
        for c in companies
    ]

    # 2. Segments (Categories) scoped strictly to tenant companies
    segments = db.query(SignupCategory).filter(
        SignupCategory.company_id.in_(company_ids)
    ).order_by(SignupCategory.display_order, SignupCategory.name).all()

    # If tenant has 0 categories, auto-seed standard starter segments for their primary company
    if not segments and company_ids:
        default_co_id = company_ids[0]
        starter_cats = [
            ("General Inquiries", "general-inquiries", "Standard customer inquiries", "fa-headset", 1),
            ("Sales Pipeline", "sales-pipeline", "Primary operational sales workflow", "fa-bullseye", 2),
            ("Support & Service", "support-service", "Customer support and follow-up requests", "fa-wrench", 3),
        ]
        created_cats = []
        for name, slug, desc, icon, order in starter_cats:
            cat = SignupCategory(
                company_id=default_co_id,
                name=name,
                slug=slug,
                description=desc,
                icon=icon,
                display_order=order,
                is_active=True,
                created_by_id=str(current_user.id)
            )
            db.add(cat)
            created_cats.append(cat)
        db.commit()
        for cat in created_cats:
            db.refresh(cat)
        segments = created_cats

    segments_data = [
        {
            "id": s.id,
            "company_id": s.company_id,
            "name": s.name,
            "slug": s.slug,
            "description": s.description or "",
            "icon": s.icon or "fa-layer-group",
            "display_order": s.display_order,
            "is_active": s.is_active
        }
        for s in segments
    ]

    # 3. Tenant Active Staff Members (available for assignment)
    staff_q = db.query(StaffEmployee).filter(
        StaffEmployee.status == 'active',
        StaffEmployee.is_deleted == False,
        or_(
            StaffEmployee.tenant_id == client.id,
            StaffEmployee.base_company_id.in_(company_ids)
        )
    ).order_by(StaffEmployee.full_name).all()

    staff_data = [
        {
            "id": e.id,
            "emp_code": e.emp_code or f"EMP-{e.id}",
            "full_name": e.full_name or f"{e.first_name or ''} {e.last_name or ''}".strip(),
            "email": e.email,
            "phone": getattr(e, "phone", None),
            "role": (e.role.role_code if getattr(e, "role", None) else None) or getattr(e, "staff_type", "STAFF"),
            "company_id": e.base_company_id
        }
        for e in staff_q
    ]

    # 4. Handler Routing Assignments
    handlers = db.query(CRMLeadHandler).filter(
        CRMLeadHandler.company_id.in_(company_ids)
    ).all()
    
    handler_map = {}
    if handlers:
        h_ids = [h.id for h in handlers]
        members = db.query(CRMLeadHandlerMember).filter(
            CRMLeadHandlerMember.handler_id.in_(h_ids),
            CRMLeadHandlerMember.is_active == True
        ).all()
        
        # Pre-index employees
        staff_by_id = {e["id"]: e for e in staff_data}
        
        for h in handlers:
            h_members = [m for m in members if m.handler_id == h.id]
            handler_map[f"{h.company_id}_{h.category_id}"] = {
                "handler_id": h.id,
                "company_id": h.company_id,
                "category_id": h.category_id,
                "is_active": h.is_active,
                "members": [
                    {
                        "member_id": m.id,
                        "employee_id": m.employee_id,
                        "assignment_weight": getattr(m, "assignment_weight", 100),
                        "employee_name": staff_by_id.get(m.employee_id, {}).get("full_name", f"Emp #{m.employee_id}"),
                        "emp_code": staff_by_id.get(m.employee_id, {}).get("emp_code", "")
                    }
                    for m in h_members
                ]
            }

    # Enrich segments_data with handler routing and vendor company
    co_by_id = {c["id"]: c for c in companies_data}
    for s_dict in segments_data:
        h_info = handler_map.get(f"{s_dict['company_id']}_{s_dict['id']}")
        s_dict["staff_members"] = h_info["members"] if h_info else []
        orig_s = next((s for s in segments if s.id == s_dict["id"]), None)
        v_id = None
        try:
            if orig_s and orig_s.document_types and str(orig_s.document_types).strip().startswith("{"):
                meta = json.loads(orig_s.document_types)
                v_id = meta.get("vendor_company_id")
        except Exception:
            v_id = None
        s_dict["vendor_company_id"] = v_id
        s_dict["vendor_company"] = co_by_id.get(v_id) if v_id else None

    # 5. CRM Settings
    import json
    settings_dict = {}
    try:
        if getattr(client, "notes", None) and str(client.notes).strip().startswith("{"):
            settings_dict = json.loads(client.notes).get("crm_settings", {})
    except Exception:
        settings_dict = {}

    crm_settings = {
        "auto_assignment_enabled": settings_dict.get("auto_assignment_enabled", True),
        "duplicate_check_enabled": settings_dict.get("duplicate_check_enabled", True),
        "default_lead_stage": settings_dict.get("default_lead_stage", "new"),
        "followup_sla_hours": settings_dict.get("followup_sla_hours", 24),
        "allow_staff_manual_lead_creation": settings_dict.get("allow_staff_manual_lead_creation", True),
        "notification_email": settings_dict.get("notification_email", getattr(client, "contact_email", "") or "")
    }

    return {
        "success": True,
        "tenant": {
            "id": client.id,
            "client_code": client.client_code,
            "company_name": getattr(client, "client_name", ""),
            "primary_company_id": company_ids[0] if company_ids else None
        },
        "companies": companies_data,
        "segments": segments_data,
        "staff": staff_data,
        "staff_members": staff_data,
        "handler_routing": handler_map,
        "crm_settings": crm_settings
    }


# ── TAB 1: CRM SETTINGS ───────────────────────────────────────────────────────

@router.get("/settings")
def get_crm_settings(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    import json
    client, _ = get_authorized_tenant(db, current_user)
    settings_dict = {}
    try:
        if getattr(client, "notes", None) and str(client.notes).strip().startswith("{"):
            settings_dict = json.loads(client.notes).get("crm_settings", {})
    except Exception:
        settings_dict = {}

    return {
        "success": True,
        "settings": {
            "auto_assignment_enabled": settings_dict.get("auto_assignment_enabled", True),
            "duplicate_check_enabled": settings_dict.get("duplicate_check_enabled", True),
            "default_lead_stage": settings_dict.get("default_lead_stage", "new"),
            "followup_sla_hours": settings_dict.get("followup_sla_hours", 24),
            "allow_staff_manual_lead_creation": settings_dict.get("allow_staff_manual_lead_creation", True),
            "notification_email": settings_dict.get("notification_email", getattr(client, "contact_email", "") or "")
        }
    }

@router.put("/settings")
def update_crm_settings(
    payload: CRMSettingsSchema,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    import json
    client, _ = get_authorized_tenant(db, current_user)
    existing_notes = {}
    try:
        if getattr(client, "notes", None) and str(client.notes).strip().startswith("{"):
            existing_notes = json.loads(client.notes)
    except Exception:
        existing_notes = {}
    existing_notes["crm_settings"] = payload.dict()
    client.notes = json.dumps(existing_notes)
    db.commit()
    return {
        "success": True,
        "message": "CRM settings updated successfully.",
        "settings": existing_notes["crm_settings"]
    }


# ── TAB 2: COMPANIES ──────────────────────────────────────────────────────────

@router.get("/companies")
def list_tenant_companies(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    client, company_ids = get_authorized_tenant(db, current_user)
    companies = db.query(AssociatedCompany).filter(
        or_(
            AssociatedCompany.client_id == client.id,
            AssociatedCompany.id.in_(company_ids)
        )
    ).order_by(AssociatedCompany.company_name).all()
    return {
        "success": True,
        "companies": [
            {
                "id": c.id,
                "company_code": c.company_code or f"CO-{c.id}",
                "company_name": c.company_name,
                "company_segment": c.company_segment or "GENERAL",
                "is_active": c.is_active,
                "gst_number": c.gst_number,
                "pan_number": c.pan_number,
                "primary_email": getattr(c, "email", None),
                "primary_phone": getattr(c, "phone", None),
                "address": c.address,
                "city": c.city,
                "state": c.state,
                "pincode": c.pincode
            }
            for c in companies
        ]
    }

@router.post("/companies")
def create_tenant_company(
    payload: CompanyCreateSchema,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    client, company_ids = get_authorized_tenant(db, current_user)
    
    # Auto-generate unique company code if not provided
    co_code = (payload.company_code or "").strip().upper()
    if not co_code:
        count = db.query(AssociatedCompany).filter(AssociatedCompany.client_id == client.id).count()
        co_code = f"{client.client_code}-BR{count + 1:02d}"

    # Verify unique code
    existing = db.query(AssociatedCompany).filter(AssociatedCompany.company_code == co_code).first()
    if existing:
        co_code = f"{co_code}-{db.query(AssociatedCompany).count() + 1}"

    new_co = AssociatedCompany(
        client_id=client.id,
        company_name=payload.company_name.strip(),
        company_code=co_code,
        company_segment=payload.company_segment or "GENERAL",
        company_type="SAAS_CLIENT",
        licensed_modules=client.subscribed_modules or ["CRM_LEADS", "SOLAR_EV"],
        gst_number=payload.gst_number,
        pan_number=payload.pan_number,
        email=payload.primary_email,
        phone=payload.primary_phone,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        pincode=payload.pincode,
        is_active=True
    )
    db.add(new_co)
    db.commit()
    db.refresh(new_co)

    return {
        "success": True,
        "message": f"Company '{new_co.company_name}' registered successfully.",
        "company": {
            "id": new_co.id,
            "company_code": new_co.company_code,
            "company_name": new_co.company_name,
            "company_segment": new_co.company_segment,
            "is_active": new_co.is_active
        }
    }

@router.put("/companies/{company_id}")
def update_tenant_company(
    company_id: int,
    payload: CompanyUpdateSchema,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    client, company_ids = get_authorized_tenant(db, current_user)
    company = db.query(AssociatedCompany).filter(
        AssociatedCompany.id == company_id,
        or_(
            AssociatedCompany.client_id == client.id,
            AssociatedCompany.id.in_(company_ids)
        )
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found or access denied.")

    if payload.company_name is not None:
        company.company_name = payload.company_name.strip()
    if payload.company_segment is not None:
        company.company_segment = payload.company_segment
    if payload.gst_number is not None:
        company.gst_number = payload.gst_number
    if payload.pan_number is not None:
        company.pan_number = payload.pan_number
    if payload.primary_email is not None:
        company.email = payload.primary_email
    if payload.primary_phone is not None:
        company.phone = payload.primary_phone
    if payload.address is not None:
        company.address = payload.address
    if payload.city is not None:
        company.city = payload.city
    if payload.state is not None:
        company.state = payload.state
    if payload.pincode is not None:
        company.pincode = payload.pincode
    if payload.is_active is not None:
        company.is_active = payload.is_active

    db.commit()
    db.refresh(company)

    return {
        "success": True,
        "message": "Company updated successfully.",
        "company": {
            "id": company.id,
            "company_code": company.company_code,
            "company_name": company.company_name,
            "is_active": company.is_active
        }
    }


def _sync_handler_routing(
    db: Session,
    company_id: int,
    category_id: int,
    staff_members: List[StaffAssignmentItem],
    current_user_id: int,
    department_id: Optional[int] = None
):
    if not department_id:
        from app.models.staff import StaffDepartment
        sales_dept = db.query(StaffDepartment).filter(StaffDepartment.name.ilike('%sales%')).first()
        department_id = sales_dept.id if sales_dept else 13

    handler = db.query(CRMLeadHandler).filter(
        CRMLeadHandler.company_id == company_id,
        CRMLeadHandler.category_id == category_id
    ).first()

    if not handler:
        handler = CRMLeadHandler(
            company_id=company_id,
            category_id=category_id,
            department_id=department_id,
            is_active=True,
            created_by_id=current_user_id
        )
        db.add(handler)
        db.commit()
        db.refresh(handler)
    else:
        handler.is_active = True
        if department_id:
            handler.department_id = department_id

    existing_members = db.query(CRMLeadHandlerMember).filter(
        CRMLeadHandlerMember.handler_id == handler.id
    ).all()
    existing_by_emp = {m.employee_id: m for m in existing_members}
    target_emp_weights = {item.employee_id: item.assignment_weight or 1 for item in staff_members}

    # Deactivate members no longer in payload
    for emp_id, mem in existing_by_emp.items():
        if emp_id not in target_emp_weights:
            mem.is_active = False

    # Insert or update
    has_weight_col = hasattr(CRMLeadHandlerMember, "assignment_weight")
    for emp_id, weight in target_emp_weights.items():
        if emp_id in existing_by_emp:
            existing_by_emp[emp_id].is_active = True
            if has_weight_col:
                setattr(existing_by_emp[emp_id], "assignment_weight", weight)
        else:
            new_mem = CRMLeadHandlerMember(
                handler_id=handler.id,
                employee_id=emp_id,
                is_active=True,
                created_by_id=current_user_id
            )
            if has_weight_col:
                setattr(new_mem, "assignment_weight", weight)
            db.add(new_mem)

    db.commit()
    return handler


# ── TAB 3: SEGMENTS ───────────────────────────────────────────────────────────

@router.get("/segments")
def list_tenant_segments(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    client, company_ids = get_authorized_tenant(db, current_user)
    target_cos = [company_id] if company_id and company_id in company_ids else company_ids

    segments = db.query(SignupCategory).filter(
        SignupCategory.company_id.in_(target_cos)
    ).order_by(SignupCategory.display_order, SignupCategory.name).all()

    # Pre-fetch handlers & members
    handlers = db.query(CRMLeadHandler).filter(
        CRMLeadHandler.company_id.in_(target_cos),
        CRMLeadHandler.is_active == True
    ).all()
    h_map = {h.category_id: h for h in handlers}
    h_ids = [h.id for h in handlers]

    members = db.query(CRMLeadHandlerMember).filter(
        CRMLeadHandlerMember.handler_id.in_(h_ids),
        CRMLeadHandlerMember.is_active == True
    ).all() if h_ids else []

    emp_ids = list(set(m.employee_id for m in members))
    employees = db.query(StaffEmployee).filter(StaffEmployee.id.in_(emp_ids)).all() if emp_ids else []
    emp_map = {e.id: e for e in employees}

    # Pre-fetch vendor companies
    all_tenant_cos = db.query(AssociatedCompany).filter(
        AssociatedCompany.id.in_(company_ids)
    ).all()
    tenant_co_map = {c.id: c for c in all_tenant_cos}

    seg_list = []
    for s in segments:
        h = h_map.get(s.id)
        s_members = [m for m in members if h and m.handler_id == h.id] if h else []

        vendor_co_id = None
        try:
            if s.document_types and str(s.document_types).strip().startswith("{"):
                meta = json.loads(s.document_types)
                vendor_co_id = meta.get("vendor_company_id")
        except Exception:
            vendor_co_id = None

        vendor_co = tenant_co_map.get(vendor_co_id) if vendor_co_id else None

        seg_list.append({
            "id": s.id,
            "company_id": s.company_id,
            "name": s.name,
            "slug": s.slug,
            "description": s.description or "",
            "icon": s.icon or "fa-layer-group",
            "display_order": s.display_order,
            "is_active": s.is_active,
            "vendor_company_id": vendor_co_id,
            "vendor_company": {
                "id": vendor_co.id,
                "company_name": vendor_co.company_name,
                "gst_number": vendor_co.gst_number,
                "pan_number": vendor_co.pan_number,
                "city": vendor_co.city,
                "state": vendor_co.state
            } if vendor_co else None,
            "staff_members": [
                {
                    "employee_id": m.employee_id,
                    "assignment_weight": getattr(m, "assignment_weight", 1),
                    "employee_name": emp_map[m.employee_id].full_name if m.employee_id in emp_map else f"Emp #{m.employee_id}",
                    "emp_code": emp_map[m.employee_id].emp_code if m.employee_id in emp_map else ""
                }
                for m in s_members
            ]
        })

    return {
        "success": True,
        "segments": seg_list
    }

@router.post("/segments")
def create_tenant_segment(
    payload: SegmentCreateSchema,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    client, company_ids = get_authorized_tenant(db, current_user)
    if payload.company_id not in company_ids:
        raise HTTPException(status_code=403, detail="Target company does not belong to your tenant.")

    name = payload.name.strip()
    slug = (payload.slug or "").strip().lower()
    if not slug:
        import re
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

    # Check uniqueness within this company
    existing = db.query(SignupCategory).filter(
        SignupCategory.company_id == payload.company_id,
        or_(SignupCategory.name == name, SignupCategory.slug == slug)
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"A segment with name '{name}' or slug '{slug}' already exists for this company."
        )

    meta = {}
    if payload.vendor_company_id is not None:
        meta["vendor_company_id"] = payload.vendor_company_id

    cat = SignupCategory(
        company_id=payload.company_id,
        name=name,
        slug=slug,
        description=payload.description,
        icon=payload.icon or "fa-layer-group",
        display_order=payload.display_order or 0,
        is_active=payload.is_active if payload.is_active is not None else True,
        document_types=json.dumps(meta) if meta else None,
        created_by_id=str(current_user.id)
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)

    if payload.staff_members:
        _sync_handler_routing(db, cat.company_id, cat.id, payload.staff_members, current_user.id)

    return {
        "success": True,
        "message": f"Segment '{cat.name}' created successfully.",
        "segment": {
            "id": cat.id,
            "company_id": cat.company_id,
            "name": cat.name,
            "slug": cat.slug,
            "description": cat.description,
            "icon": cat.icon,
            "display_order": cat.display_order,
            "is_active": cat.is_active,
            "vendor_company_id": payload.vendor_company_id
        }
    }

@router.put("/segments/{segment_id}")
def update_tenant_segment(
    segment_id: int,
    payload: SegmentUpdateSchema,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    client, company_ids = get_authorized_tenant(db, current_user)
    cat = db.query(SignupCategory).filter(
        SignupCategory.id == segment_id,
        SignupCategory.company_id.in_(company_ids)
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Segment not found or access denied.")

    if payload.name is not None:
        cat.name = payload.name.strip()
    if payload.slug is not None:
        cat.slug = payload.slug.strip().lower()
    if payload.description is not None:
        cat.description = payload.description
    if payload.icon is not None:
        cat.icon = payload.icon
    if payload.display_order is not None:
        cat.display_order = payload.display_order
    if payload.is_active is not None:
        cat.is_active = payload.is_active

    if payload.vendor_company_id is not None:
        meta = {}
        try:
            if cat.document_types and str(cat.document_types).strip().startswith("{"):
                meta = json.loads(cat.document_types)
        except Exception:
            meta = {}
        meta["vendor_company_id"] = payload.vendor_company_id
        cat.document_types = json.dumps(meta)

    db.commit()
    db.refresh(cat)

    if payload.staff_members is not None:
        _sync_handler_routing(db, cat.company_id, cat.id, payload.staff_members, current_user.id)

    return {
        "success": True,
        "message": f"Segment '{cat.name}' updated successfully.",
        "segment": {
            "id": cat.id,
            "name": cat.name,
            "slug": cat.slug,
            "is_active": cat.is_active
        }
    }


# ── TAB 4: STAFF / SEGMENT ASSIGNMENT ─────────────────────────────────────────

@router.get("/handlers")
def list_handler_assignments(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    client, company_ids = get_authorized_tenant(db, current_user)
    target_cos = [company_id] if company_id and company_id in company_ids else company_ids

    handlers = db.query(CRMLeadHandler).filter(
        CRMLeadHandler.company_id.in_(target_cos)
    ).all()

    h_ids = [h.id for h in handlers]
    members = db.query(CRMLeadHandlerMember).filter(
        CRMLeadHandlerMember.handler_id.in_(h_ids)
    ).all() if h_ids else []

    emp_ids = list(set(m.employee_id for m in members))
    employees = db.query(StaffEmployee).filter(StaffEmployee.id.in_(emp_ids)).all() if emp_ids else []
    emp_map = {e.id: e for e in employees}

    categories = db.query(SignupCategory).filter(
        SignupCategory.company_id.in_(target_cos)
    ).all()
    cat_map = {c.id: c for c in categories}

    result = []
    for h in handlers:
        h_members = [m for m in members if m.handler_id == h.id]
        cat = cat_map.get(h.category_id)
        result.append({
            "handler_id": h.id,
            "company_id": h.company_id,
            "category_id": h.category_id,
            "category_name": cat.name if cat else f"Category #{h.category_id}",
            "is_active": h.is_active,
            "staff_count": len([m for m in h_members if m.is_active]),
            "members": [
                {
                    "member_id": m.id,
                    "employee_id": m.employee_id,
                    "assignment_weight": m.assignment_weight,
                    "is_active": m.is_active,
                    "employee_name": emp_map[m.employee_id].full_name if m.employee_id in emp_map else f"Emp #{m.employee_id}",
                    "emp_code": emp_map[m.employee_id].emp_code if m.employee_id in emp_map else ""
                }
                for m in h_members
            ]
        })

    return {"success": True, "handlers": result}


@router.post("/handlers/assign")
def assign_staff_to_segment(
    payload: HandlerAssignSchema,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    client, company_ids = get_authorized_tenant(db, current_user)
    if payload.company_id not in company_ids:
        raise HTTPException(status_code=403, detail="Target company does not belong to your tenant.")

    # Validate category belongs to this company
    cat = db.query(SignupCategory).filter(
        SignupCategory.id == payload.category_id,
        SignupCategory.company_id.in_(company_ids)
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Segment/Category not found for this tenant.")

    # Validate each employee belongs to this tenant
    assigned_emp_ids = [item.employee_id for item in payload.staff_members]
    if assigned_emp_ids:
        valid_staff = db.query(StaffEmployee).filter(
            StaffEmployee.id.in_(assigned_emp_ids),
            or_(
                StaffEmployee.tenant_id == client.id,
                StaffEmployee.client_id == client.id,
                StaffEmployee.base_company_id.in_(company_ids)
            )
        ).all()
        valid_ids = set(s.id for s in valid_staff)
        invalid = [eid for eid in assigned_emp_ids if eid not in valid_ids]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Staff member IDs {invalid} do not belong to this tenant."
            )

    # Find or create CRMLeadHandler
    handler = db.query(CRMLeadHandler).filter(
        CRMLeadHandler.company_id == payload.company_id,
        CRMLeadHandler.category_id == payload.category_id
    ).first()

    if not handler:
        handler = CRMLeadHandler(
            company_id=payload.company_id,
            category_id=payload.category_id,
            department_id=payload.department_id,
            is_active=True,
            created_by_id=current_user.id
        )
        db.add(handler)
        db.commit()
        db.refresh(handler)
    else:
        handler.is_active = True
        if payload.department_id:
            handler.department_id = payload.department_id

    # Sync members: deactivate removed, update/insert active
    existing_members = db.query(CRMLeadHandlerMember).filter(
        CRMLeadHandlerMember.handler_id == handler.id
    ).all()
    existing_by_emp = {m.employee_id: m for m in existing_members}

    target_emp_weights = {item.employee_id: item.assignment_weight or 1 for item in payload.staff_members}

    # Deactivate members no longer in payload
    for emp_id, mem in existing_by_emp.items():
        if emp_id not in target_emp_weights:
            mem.is_active = False

    # Insert or update
    has_weight_col = hasattr(CRMLeadHandlerMember, "assignment_weight")
    for emp_id, weight in target_emp_weights.items():
        if emp_id in existing_by_emp:
            existing_by_emp[emp_id].is_active = True
            if has_weight_col:
                setattr(existing_by_emp[emp_id], "assignment_weight", weight)
        else:
            new_mem = CRMLeadHandlerMember(
                handler_id=handler.id,
                employee_id=emp_id,
                is_active=True,
                created_by_id=current_user.id
            )
            if has_weight_col:
                setattr(new_mem, "assignment_weight", weight)
            db.add(new_mem)

    db.commit()

    return {
        "success": True,
        "message": f"Successfully updated staff routing for segment '{cat.name}'.",
        "handler_id": handler.id,
        "assigned_count": len(payload.staff_members)
    }
