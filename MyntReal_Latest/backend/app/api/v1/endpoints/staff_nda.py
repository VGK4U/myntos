"""
Staff NDA Management API Endpoints (DC Protocol Compliant)
- VGK4U: Full CRUD access (create, edit, copy, activate, deactivate)
- HR: Read-only access (view versions, audit logs, pending acceptances)
- All Staff: Accept NDA, view own acceptance history
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, desc
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import re

from app.core.database import get_db
from app.models.staff import (
    StaffEmployee, StaffRole, StaffDepartment,
    StaffNdaVersion, StaffNdaAcceptance, StaffNdaAudit,
    log_nda_audit, get_active_nda_version, get_active_nda_for_staff_type,
    check_nda_acceptance, check_all_pending_agreements, is_nda_applicable_to_staff_type, get_indian_time
)
from app.api.v1.endpoints.staff_auth import get_current_staff_user

router = APIRouter(prefix="/staff/nda", tags=["Staff NDA Management"])

# Role-based access control
VGK4U_ROLES = ["vgk4u"]  # Full edit access
NDA_VIEW_ROLES = ["vgk4u", "hr", "ea"]  # Can view NDA management pages
NDA_EDIT_ROLES = ["vgk4u"]  # Only VGK4U can create/edit


# ============= Pydantic Models =============

# DC Protocol: Valid staff types for NDA assignment (Dec 04, 2025)
# 3 active types + 1 legacy (MN_EMPLOYEE kept for backward compatibility)
VALID_STAFF_TYPES = ['MN_STAFF', 'FREELANCER', 'MYNT_REAL', 'MN_EMPLOYEE']


class NdaVersionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    content_html: str = Field(..., min_length=1)
    applicable_staff_types: List[str] = Field(default=[], description="Staff types this version applies to. Empty = all types.")
    notes: Optional[str] = None
    document_type: str = Field(default='NDA', description="'NDA' = Non-Disclosure Agreement, 'EMPLOYMENT' = Employment Agreement")


class NdaVersionUpdate(BaseModel):
    title: Optional[str] = None
    content_html: Optional[str] = None
    applicable_staff_types: Optional[List[str]] = None
    notes: Optional[str] = None


class NdaAcceptRequest(BaseModel):
    nda_version_id: int


# ============= Helper Functions =============

def get_client_ip(request: Request = None) -> str:
    """Extract client IP address from request with multiple fallbacks (handles None request)"""
    if request is None:
        return "unknown"
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
        if ip and ip != "unknown":
            return ip
    
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip and x_real_ip.strip() and x_real_ip.strip() != "unknown":
        return x_real_ip.strip()
    
    cf_connecting_ip = request.headers.get("CF-Connecting-IP")
    if cf_connecting_ip and cf_connecting_ip.strip():
        return cf_connecting_ip.strip()
    
    if request.client and request.client.host:
        return request.client.host
    
    return "127.0.0.1"


def get_next_version_number(db: Session, source_version: Optional[str] = None, document_type: str = 'NDA') -> str:
    """
    Generate next version number, scoped per document_type so NDA and
    EMPLOYMENT Agreement each have their own independent sequence (1.0, 1.1, …).
    """
    if source_version:
        # Strip any leading alpha prefix (future-proofing)
        clean = source_version.lstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-')
        parts = clean.split(".")
        if len(parts) == 2:
            try:
                major, minor = int(parts[0]), int(parts[1])
                return f"{major}.{minor + 1}"
            except ValueError:
                pass
    
    latest = db.query(StaffNdaVersion).filter(
        StaffNdaVersion.document_type == document_type
    ).order_by(
        desc(StaffNdaVersion.id)
    ).first()
    
    if latest:
        parts = latest.version_number.split(".")
        if len(parts) == 2:
            try:
                major, minor = int(parts[0]), int(parts[1])
                return f"{major}.{minor + 1}"
            except ValueError:
                pass
    
    return "1.0"


def check_nda_edit_permission(current_user: StaffEmployee):
    """Check if user has NDA edit permission (VGK4U only)"""
    if not current_user.role or current_user.role.role_code not in NDA_EDIT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only VGK Mentor can create/edit NDA versions"
        )


def check_nda_view_permission(current_user: StaffEmployee):
    """Check if user has NDA view permission (VGK4U + HR)"""
    if not current_user.role or current_user.role.role_code not in NDA_VIEW_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. VGK4U or HR role required."
        )


def render_nda_content(content_html: str, employee: StaffEmployee) -> str:
    """Replace dynamic placeholders in NDA content"""
    now = get_indian_time()
    
    def ordinal(n):
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"
    
    current_date = f"{ordinal(now.day)} {now.strftime('%B %Y')}"
    
    replacements = {
        "{{current_date}}": current_date,
        "{{employee_name}}": employee.full_name or "",
        "{{employee_code}}": employee.emp_code or "",
        "{{employee_designation}}": employee.designation or "",
        "{{employee_role}}": employee.role.role_name if employee.role else "",
        "{{company_name}}": "MyntReal LLP",
        "{{company_address}}": "Survey No: 156/1, Ground Floor, Main Road, Saripalli, Pendurthi Mandal, Visakhapatnam, Andhra Pradesh, 531173"
    }
    
    result = content_html
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    
    return result


# ============= VGK4U Admin Endpoints =============

@router.get("/versions")
async def list_nda_versions(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    document_type_filter: Optional[str] = Query(None, alias="document_type"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    List all NDA/Employment Agreement versions with filters.
    Access: VGK4U (full), HR (read-only)
    DC-AGREEMENT-TYPE-001: document_type filter added (Jun 2026)
    """
    check_nda_view_permission(current_user)
    
    query = db.query(StaffNdaVersion)
    
    if document_type_filter:
        query = query.filter(StaffNdaVersion.document_type == document_type_filter)
    
    if status_filter and status_filter != "all":
        query = query.filter(StaffNdaVersion.status == status_filter)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                StaffNdaVersion.title.ilike(search_term),
                StaffNdaVersion.version_number.ilike(search_term)
            )
        )
    
    total = query.count()
    
    versions = query.order_by(
        desc(StaffNdaVersion.created_at)
    ).offset((page - 1) * limit).limit(limit).all()
    
    # Stats scoped to the current document_type_filter if provided
    _stats_q = db.query(StaffNdaVersion)
    if document_type_filter:
        _stats_q = _stats_q.filter(StaffNdaVersion.document_type == document_type_filter)
    stats = {
        "total": _stats_q.count(),
        "active": _stats_q.filter(StaffNdaVersion.status == "active").count(),
        "draft": _stats_q.filter(StaffNdaVersion.status == "draft").count(),
        "inactive": _stats_q.filter(StaffNdaVersion.status == "inactive").count()
    }
    
    return {
        "success": True,
        "data": [v.to_dict(include_content=False) for v in versions],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        },
        "stats": stats,
        "can_edit": current_user.role.role_code in NDA_EDIT_ROLES
    }


@router.get("/versions/{version_id}")
async def get_nda_version(
    version_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Get specific NDA version with full content"""
    check_nda_view_permission(current_user)
    
    version = db.query(StaffNdaVersion).filter(StaffNdaVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="NDA version not found")
    
    return {
        "success": True,
        "data": version.to_dict(include_content=True),
        "can_edit": current_user.role.role_code in NDA_EDIT_ROLES and version.status == "draft"
    }


@router.post("/versions")
async def create_nda_version(
    data: NdaVersionCreate = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Create new NDA version (draft status)"""
    check_nda_edit_permission(current_user)
    
    # DC Protocol: Validate staff types (Dec 04, 2025)
    validated_staff_types = []
    if data.applicable_staff_types:
        validated_staff_types = [st for st in data.applicable_staff_types if st in VALID_STAFF_TYPES]
    
    doc_type = data.document_type or 'NDA'
    version_number = get_next_version_number(db, document_type=doc_type)
    
    nda_version = StaffNdaVersion(
        version_number=version_number,
        title=data.title,
        content_html=data.content_html,
        applicable_staff_types=validated_staff_types,
        document_type=doc_type,
        status="draft",
        created_by=current_user.id,
        notes=data.notes
    )
    
    db.add(nda_version)
    db.commit()
    db.refresh(nda_version)
    
    _doc_labels = {'NDA': 'NDA', 'EMPLOYMENT': 'Employment Agreement'}
    _doc_label = _doc_labels.get(doc_type, doc_type)
    log_nda_audit(
        db=db,
        actor_emp_code=current_user.emp_code,
        actor_name=current_user.full_name,
        action="created",
        target_version_id=nda_version.id,
        target_version_number=version_number,
        new_value={"title": data.title, "status": "draft", "document_type": doc_type, "applicable_staff_types": validated_staff_types},
        description=f"Created {_doc_label} version {version_number} for staff types: {validated_staff_types or 'All'}",
        ip_address=get_client_ip(request)
    )
    db.commit()
    
    return {
        "success": True,
        "message": f"{_doc_label} version {version_number} created as draft",
        "data": nda_version.to_dict(include_content=True)
    }


@router.put("/versions/{version_id}")
async def update_nda_version(
    version_id: int,
    data: NdaVersionUpdate = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Update NDA version (draft only)"""
    check_nda_edit_permission(current_user)
    
    version = db.query(StaffNdaVersion).filter(StaffNdaVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="NDA version not found")
    
    if version.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Only draft versions can be edited. Create a copy to modify active/inactive versions."
        )
    
    old_values = {"title": version.title, "notes": version.notes, "applicable_staff_types": version.applicable_staff_types}
    new_values = {}
    
    if data.title is not None:
        version.title = data.title
        new_values["title"] = data.title
    
    if data.content_html is not None:
        version.content_html = data.content_html
        new_values["content_updated"] = True
    
    if data.notes is not None:
        version.notes = data.notes
        new_values["notes"] = data.notes
    
    # DC Protocol: Update applicable staff types (Dec 04, 2025)
    if data.applicable_staff_types is not None:
        validated_staff_types = [st for st in data.applicable_staff_types if st in VALID_STAFF_TYPES]
        version.applicable_staff_types = validated_staff_types
        new_values["applicable_staff_types"] = validated_staff_types
    
    version.updated_by = current_user.id
    version.updated_at = get_indian_time()
    
    log_nda_audit(
        db=db,
        actor_emp_code=current_user.emp_code,
        actor_name=current_user.full_name,
        action="updated",
        target_version_id=version.id,
        target_version_number=version.version_number,
        old_value=old_values,
        new_value=new_values,
        description=f"Updated NDA version {version.version_number}",
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    db.refresh(version)
    
    return {
        "success": True,
        "message": "NDA version updated successfully",
        "data": version.to_dict(include_content=True)
    }


@router.post("/versions/{version_id}/copy")
async def copy_nda_version(
    version_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Copy NDA version to create new draft"""
    check_nda_edit_permission(current_user)
    
    source = db.query(StaffNdaVersion).filter(StaffNdaVersion.id == version_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source NDA version not found")
    
    # DC-AGREEMENT-TYPE-001: preserve document_type when copying so an Employment Agreement
    # copy does not default back to 'NDA', and version numbers stay scoped per type.
    src_doc_type = source.document_type or 'NDA'
    new_version_number = get_next_version_number(db, source.version_number, document_type=src_doc_type)
    
    new_version = StaffNdaVersion(
        version_number=new_version_number,
        title=f"{source.title} (Copy)",
        content_html=source.content_html,
        applicable_staff_types=source.applicable_staff_types or [],  # DC: Copy staff types from source
        document_type=src_doc_type,
        status="draft",
        created_by=current_user.id,
        source_version_id=source.id,
        notes=f"Copied from version {source.version_number}"
    )
    
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    
    log_nda_audit(
        db=db,
        actor_emp_code=current_user.emp_code,
        actor_name=current_user.full_name,
        action="copied",
        target_version_id=new_version.id,
        target_version_number=new_version_number,
        old_value={"source_version_id": source.id, "source_version_number": source.version_number},
        new_value={"new_version_id": new_version.id, "new_version_number": new_version_number},
        description=f"Copied NDA version {source.version_number} to {new_version_number}",
        ip_address=get_client_ip(request)
    )
    db.commit()
    
    return {
        "success": True,
        "message": f"Created new draft version {new_version_number} from {source.version_number}",
        "data": new_version.to_dict(include_content=True)
    }


@router.post("/versions/{version_id}/activate")
async def activate_nda_version(
    version_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Activate NDA version (DC Protocol: Multi-NDA System - Dec 04, 2025)
    
    MULTI-NDA ACTIVATION LOGIC:
    - Multiple NDAs can be active simultaneously for DIFFERENT staff types
    - Only deactivates existing NDAs that have OVERLAPPING staff types
    - Non-overlapping NDAs remain active
    
    Example:
    - NDA v1.0: [MN_STAFF, FREELANCER] - Active
    - NDA v1.1: [MYNT_REAL] - Can be activated (no overlap)
    - Both remain active after v1.1 activation
    
    Example 2:
    - NDA v1.0: [MN_STAFF] - Active
    - NDA v1.1: [MN_STAFF, FREELANCER] - Activating
    - v1.0 gets deactivated (MN_STAFF overlaps)
    """
    check_nda_edit_permission(current_user)
    
    version = db.query(StaffNdaVersion).filter(StaffNdaVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="NDA version not found")
    
    if version.status == "active":
        raise HTTPException(status_code=400, detail="This version is already active")
    
    # DC Protocol: Require at least one staff type for activation (Dec 04, 2025)
    new_staff_types = set(version.applicable_staff_types or [])
    if not new_staff_types:
        raise HTTPException(
            status_code=400, 
            detail="Cannot activate NDA without specifying applicable staff types. Please edit the draft and select at least one staff type."
        )
    
    # DC Protocol: Multi-NDA System (Dec 04, 2025)
    # Find active versions with OVERLAPPING staff types and deactivate only those.
    # DC-AGREEMENT-TYPE-001: MUST scope by document_type — activating an Employment Agreement
    # must never deactivate an NDA, and vice versa. Each type's active versions are independent.
    deactivated_versions = []
    active_ndas = db.query(StaffNdaVersion).filter(
        StaffNdaVersion.status == "active",
        StaffNdaVersion.id != version_id,  # Exclude current version
        StaffNdaVersion.document_type == (version.document_type or 'NDA')  # Same type only
    ).all()
    
    # All valid staff types for treating empty/NULL as "all"
    ALL_STAFF_TYPES = set(VALID_STAFF_TYPES)  # ['MN_STAFF', 'FREELANCER', 'MYNT_REAL', 'MN_EMPLOYEE']
    
    for active_nda in active_ndas:
        raw_existing_types = active_nda.applicable_staff_types or []
        
        # CRITICAL: Empty/NULL means "applies to all" - treat as full set for overlap detection
        if not raw_existing_types:
            existing_types = ALL_STAFF_TYPES  # Global NDA - overlaps with everything
        else:
            existing_types = set(raw_existing_types)
        
        # Check for overlap - if any staff type is common, deactivate
        overlap = new_staff_types.intersection(existing_types)
        
        if overlap:
            # Overlap found - deactivate this NDA
            active_nda.status = "inactive"
            active_nda.deactivated_at = get_indian_time()
            active_nda.deactivated_by = current_user.id
            
            # For audit log, show original value (empty = global) clearly
            audit_existing_types = raw_existing_types if raw_existing_types else ["ALL_TYPES (Global NDA)"]
            is_global_nda = not raw_existing_types
            overlap_description = "ALL TYPES (Global NDA overlaps everything)" if is_global_nda else f"{', '.join(overlap)}"
            
            log_nda_audit(
                db=db,
                actor_emp_code=current_user.emp_code,
                actor_name=current_user.full_name,
                action="deactivated",
                target_version_id=active_nda.id,
                target_version_number=active_nda.version_number,
                old_value={"status": "active", "applicable_staff_types": audit_existing_types, "is_global": is_global_nda},
                new_value={"status": "inactive", "reason": f"Overlapping staff types: {list(overlap)}"},
                description=f"Auto-deactivated NDA version {active_nda.version_number} due to overlapping staff types ({overlap_description}) with newly activated version {version.version_number}",
                ip_address=get_client_ip(request)
            )
            deactivated_versions.append(f"v{active_nda.version_number}")
    
    # Activate the new version
    old_status = version.status
    version.status = "active"
    version.activation_timestamp = get_indian_time()
    version.activated_by = current_user.id
    version.effective_from = get_indian_time()
    
    log_nda_audit(
        db=db,
        actor_emp_code=current_user.emp_code,
        actor_name=current_user.full_name,
        action="activated",
        target_version_id=version.id,
        target_version_number=version.version_number,
        old_value={"status": old_status},
        new_value={"status": "active", "applicable_staff_types": list(new_staff_types)},
        description=f"Activated NDA version {version.version_number} for staff types: {', '.join(new_staff_types)}. Deactivated overlapping: {', '.join(deactivated_versions) if deactivated_versions else 'None'}",
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    
    # DC Protocol: Count only applicable staff types (Dec 04, 2025)
    applicable_types = version.applicable_staff_types or []
    affected_staff = db.query(StaffEmployee).filter(
        StaffEmployee.status == "active",
        StaffEmployee.staff_type.in_(applicable_types) if applicable_types else True
    ).count()
    
    staff_type_labels = ", ".join(applicable_types) if applicable_types else "All"
    
    # Build informative message
    message = f"NDA version {version.version_number} is now active for {staff_type_labels}. {affected_staff} applicable staff members must accept on next login."
    if deactivated_versions:
        message += f" Deactivated overlapping versions: {', '.join(deactivated_versions)}."
    
    # Count total active NDAs after this activation
    total_active = db.query(StaffNdaVersion).filter(
        StaffNdaVersion.status == "active"
    ).count()
    
    return {
        "success": True,
        "message": message,
        "data": version.to_dict(include_content=False),
        "total_active_ndas": total_active,
        "deactivated_versions": deactivated_versions
    }


@router.post("/versions/{version_id}/deactivate")
async def deactivate_nda_version(
    version_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Deactivate NDA version"""
    check_nda_edit_permission(current_user)
    
    version = db.query(StaffNdaVersion).filter(StaffNdaVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="NDA version not found")
    
    if version.status == "inactive":
        raise HTTPException(status_code=400, detail="This version is already inactive")
    
    old_status = version.status
    version.status = "inactive"
    version.deactivated_at = get_indian_time()
    version.deactivated_by = current_user.id
    
    log_nda_audit(
        db=db,
        actor_emp_code=current_user.emp_code,
        actor_name=current_user.full_name,
        action="deactivated",
        target_version_id=version.id,
        target_version_number=version.version_number,
        old_value={"status": old_status},
        new_value={"status": "inactive"},
        description=f"Deactivated NDA version {version.version_number}",
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": f"NDA version {version.version_number} has been deactivated",
        "data": version.to_dict(include_content=False)
    }


# ============= Acceptance Audit Endpoints =============

@router.get("/acceptances")
async def list_nda_acceptances(
    request: Request,
    version_id: Optional[int] = None,
    employee_search: Optional[str] = None,
    role_id: Optional[int] = None,
    department_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """List NDA acceptance audit log with filters"""
    check_nda_view_permission(current_user)
    
    query = db.query(StaffNdaAcceptance).join(
        StaffEmployee, StaffNdaAcceptance.employee_id == StaffEmployee.id
    ).join(
        StaffNdaVersion, StaffNdaAcceptance.nda_version_id == StaffNdaVersion.id
    )
    
    if version_id:
        query = query.filter(StaffNdaAcceptance.nda_version_id == version_id)
    
    if employee_search:
        search_term = f"%{employee_search}%"
        query = query.filter(
            or_(
                StaffEmployee.full_name.ilike(search_term),
                StaffEmployee.emp_code.ilike(search_term)
            )
        )
    
    if role_id:
        query = query.filter(StaffEmployee.role_id == role_id)
    
    if department_id:
        query = query.filter(StaffEmployee.department_id == department_id)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(StaffNdaAcceptance.accepted_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d")
            to_date = to_date.replace(hour=23, minute=59, second=59)
            query = query.filter(StaffNdaAcceptance.accepted_at <= to_date)
        except ValueError:
            pass
    
    total = query.count()
    
    acceptances = query.order_by(
        desc(StaffNdaAcceptance.accepted_at)
    ).offset((page - 1) * limit).limit(limit).all()
    
    roles = db.query(StaffRole).filter(StaffRole.is_active == True).all()
    departments = db.query(StaffDepartment).filter(StaffDepartment.is_active == True).all()
    versions = db.query(StaffNdaVersion).order_by(desc(StaffNdaVersion.created_at)).all()
    
    return {
        "success": True,
        "data": [a.to_dict() for a in acceptances],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        },
        "filters": {
            "roles": [{"id": r.id, "name": r.role_name} for r in roles],
            "departments": [{"id": d.id, "name": d.name} for d in departments],
            "versions": [{"id": v.id, "version_number": v.version_number, "title": v.title} for v in versions]
        }
    }


@router.get("/pending")
async def list_pending_acceptances(
    request: Request,
    role_id: Optional[int] = None,
    department_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    document_type: str = Query('NDA', description="'NDA' or 'EMPLOYMENT'"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC-AGREEMENT-TYPE-001: List employees who haven't accepted the specified agreement type.
    document_type param scopes both the active-version lookup and acceptance check.
    Pending = Employees WITHOUT an acceptance record for the active version of this doc type.
    """
    check_nda_view_permission(current_user)

    from sqlalchemy import distinct

    doc_type = document_type or 'NDA'

    roles = db.query(StaffRole).filter(StaffRole.is_active == True).all()
    departments = db.query(StaffDepartment).filter(StaffDepartment.is_active == True).all()

    # Active version for this doc type
    active_nda = db.query(StaffNdaVersion).filter(
        StaffNdaVersion.status == 'active',
        StaffNdaVersion.document_type == doc_type
    ).order_by(StaffNdaVersion.activation_timestamp.desc().nullslast()).first()

    # Employee IDs who have an acceptance record for an active version of this doc type
    accepted_employee_ids = db.query(distinct(StaffNdaAcceptance.employee_id)).join(
        StaffNdaVersion,
        StaffNdaAcceptance.nda_version_id == StaffNdaVersion.id
    ).filter(
        StaffNdaVersion.status == 'active',
        StaffNdaVersion.document_type == doc_type
    ).all()
    accepted_ids_set = {row[0] for row in accepted_employee_ids}

    # All active employees with optional filters
    employee_query = db.query(StaffEmployee).filter(
        StaffEmployee.status == "active",
        StaffEmployee.is_deleted == False
    )

    if role_id:
        employee_query = employee_query.filter(StaffEmployee.role_id == role_id)
    if department_id:
        employee_query = employee_query.filter(StaffEmployee.department_id == department_id)
    if search:
        search_term = f"%{search}%"
        employee_query = employee_query.filter(
            or_(
                StaffEmployee.full_name.ilike(search_term),
                StaffEmployee.emp_code.ilike(search_term)
            )
        )

    all_filtered_employees = employee_query.all()
    total_active = len(all_filtered_employees)

    pending_employees = []
    accepted_count = 0

    for emp in all_filtered_employees:
        if emp.id in accepted_ids_set:
            accepted_count += 1
        else:
            emp_dict = emp.to_dict()
            emp_dict['applicable_nda_version'] = active_nda.version_number if active_nda else None
            emp_dict['applicable_nda_id'] = active_nda.id if active_nda else None
            pending_employees.append(emp_dict)

    total_pending = len(pending_employees)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_pending = pending_employees[start_idx:end_idx]

    display_nda = None
    if active_nda:
        display_nda = {
            "id": active_nda.id,
            "version_number": active_nda.version_number,
            "title": active_nda.title,
            "document_type": active_nda.document_type or doc_type,
            "activated_at": active_nda.activation_timestamp.isoformat() if active_nda.activation_timestamp else None
        }

    return {
        "success": True,
        "data": paginated_pending,
        "active_nda": display_nda,
        "active_ndas": [display_nda] if display_nda else [],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total_pending,
            "pages": (total_pending + limit - 1) // limit if total_pending > 0 else 0
        },
        "stats": {
            "total_employees": total_active,
            "accepted": accepted_count,
            "pending": total_pending
        },
        "filters": {
            "roles": [{"id": r.id, "name": r.role_name} for r in roles],
            "departments": [{"id": d.id, "name": d.name} for d in departments]
        }
    }


@router.get("/audit")
async def list_nda_audit_logs(
    request: Request,
    action: Optional[str] = None,
    actor_code: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """List NDA management audit logs"""
    check_nda_view_permission(current_user)
    
    query = db.query(StaffNdaAudit)
    
    if action and action != "all":
        query = query.filter(StaffNdaAudit.action == action)
    
    if actor_code:
        query = query.filter(StaffNdaAudit.actor_emp_code.ilike(f"%{actor_code}%"))
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(StaffNdaAudit.timestamp >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d")
            to_date = to_date.replace(hour=23, minute=59, second=59)
            query = query.filter(StaffNdaAudit.timestamp <= to_date)
        except ValueError:
            pass
    
    total = query.count()
    
    logs = query.order_by(
        desc(StaffNdaAudit.timestamp)
    ).offset((page - 1) * limit).limit(limit).all()
    
    action_types = db.query(StaffNdaAudit.action).distinct().all()
    
    return {
        "success": True,
        "data": [l.to_dict() for l in logs],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        },
        "filters": {
            "actions": [a[0] for a in action_types]
        }
    }


@router.get("/stats")
async def get_nda_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get NDA system statistics
    DC Protocol Fix (Dec 05, 2025): Simple compliance calculation - NO EXCEPTIONS
    Compliance = Total Unique Acceptances / Total Active Employees
    Every employee must accept NDA from their login - no staff-type exceptions
    """
    check_nda_view_permission(current_user)
    
    active_nda = get_active_nda_version(db)
    
    total_versions = db.query(StaffNdaVersion).count()
    
    # Count total active employees (simple count, no exceptions)
    total_active_employees = db.query(StaffEmployee).filter(
        StaffEmployee.status == "active",
        StaffEmployee.is_deleted == False
    ).count()
    
    # Count unique employees who have accepted ANY active NDA version
    # DC Protocol: Only count employees with acceptance record for an ACTIVE NDA
    from sqlalchemy import distinct
    accepted_count = db.query(distinct(StaffNdaAcceptance.employee_id)).join(
        StaffNdaVersion,
        StaffNdaAcceptance.nda_version_id == StaffNdaVersion.id
    ).filter(
        StaffNdaVersion.status == 'active'
    ).count()
    
    # Pending = Total - Accepted (simple calculation, no exceptions)
    pending_count = total_active_employees - accepted_count
    
    # Compliance rate = Accepted / Total (no staff-type exceptions)
    compliance_rate = round((accepted_count / total_active_employees * 100), 1) if total_active_employees > 0 else 0
    
    return {
        "success": True,
        "data": {
            "active_nda": active_nda.to_dict(include_content=False) if active_nda else None,
            "total_versions": total_versions,
            "total_active_employees": total_active_employees,
            "accepted_count": accepted_count,
            "pending_count": pending_count,
            "compliance_rate": compliance_rate
        }
    }


# ============= Staff (Employee) Endpoints =============

@router.get("/current")
async def get_current_nda(
    request: Request,
    document_type: str = Query('NDA', description="'NDA' or 'EMPLOYMENT'"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get current active agreement with rendered content for acceptance.
    DC-AGREEMENT-TYPE-001: document_type param added (Jun 2026)
    Returns both 'nda' and 'data' keys for backward compatibility.
    """
    staff_type = current_user.staff_type or 'MN_STAFF'
    active_version = get_active_nda_for_staff_type(db, staff_type, document_type)
    
    if not active_version:
        return {
            "success": True,
            "nda": None,
            "data": None,
            "nda_required": False
        }
    
    needs_acceptance, _ = check_nda_acceptance(db, current_user.id, staff_type, document_type)
    rendered_content = render_nda_content(active_version.content_html, current_user)
    
    _agreement_labels = {'NDA': 'Non-Disclosure Agreement', 'EMPLOYMENT': 'Employment Agreement'}
    nda_obj = {
        "id": active_version.id,
        "version_number": active_version.version_number,
        "title": active_version.title,
        "content_html": rendered_content,
        "document_type": active_version.document_type or document_type,
        "agreement_label": _agreement_labels.get(active_version.document_type or document_type, document_type),
        "effective_from": active_version.effective_from.isoformat() if active_version.effective_from else None
    }
    
    return {
        "success": True,
        "nda": nda_obj,
        "data": nda_obj,
        "nda_required": needs_acceptance
    }


@router.get("/status")
async def check_nda_status(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Check if current user needs to accept NDA"""
    needs_acceptance, active_nda = check_nda_acceptance(db, current_user.id)
    
    return {
        "success": True,
        "nda_required": needs_acceptance,
        "nda_version_id": active_nda.id if active_nda else None,
        "nda_version_number": active_nda.version_number if active_nda else None
    }


@router.post("/accept")
async def accept_nda(
    data: NdaAcceptRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Accept NDA (creates immutable acceptance record)"""
    nda_version = db.query(StaffNdaVersion).filter(
        StaffNdaVersion.id == data.nda_version_id
    ).first()
    
    if not nda_version:
        raise HTTPException(status_code=404, detail="NDA version not found")
    
    if nda_version.status != "active":
        raise HTTPException(status_code=400, detail="Can only accept the active NDA version")
    
    existing = db.query(StaffNdaAcceptance).filter(
        StaffNdaAcceptance.employee_id == current_user.id,
        StaffNdaAcceptance.nda_version_id == data.nda_version_id
    ).first()
    
    if existing:
        return {
            "success": True,
            "message": "NDA already accepted",
            "accepted_at": existing.accepted_at.isoformat()
        }
    
    acceptance = StaffNdaAcceptance(
        employee_id=current_user.id,
        nda_version_id=data.nda_version_id,
        accepted_at=get_indian_time(),
        acceptance_ip=get_client_ip(request),
        acceptance_user_agent=request.headers.get("User-Agent", "")[:500],
        acceptance_snapshot={
            "version_number": nda_version.version_number,
            "title": nda_version.title,
            "document_type": nda_version.document_type or 'NDA',
            "content_hash": hash(nda_version.content_html) % 10**10
        },
        document_type=nda_version.document_type or 'NDA',
        employee_name_at_acceptance=current_user.full_name,
        employee_code_at_acceptance=current_user.emp_code,
        employee_designation_at_acceptance=current_user.designation,
        employee_role_at_acceptance=current_user.role.role_name if current_user.role else None
    )
    
    db.add(acceptance)
    
    log_nda_audit(
        db=db,
        actor_emp_code=current_user.emp_code,
        actor_name=current_user.full_name,
        action="accepted",
        target_version_id=nda_version.id,
        target_version_number=nda_version.version_number,
        new_value={
            "employee_id": current_user.id,
            "employee_code": current_user.emp_code,
            "accepted_at": get_indian_time().isoformat()
        },
        description=f"Employee {current_user.emp_code} accepted NDA version {nda_version.version_number}",
        ip_address=get_client_ip(request)
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": f"NDA version {nda_version.version_number} accepted successfully",
        "accepted_at": acceptance.accepted_at.isoformat()
    }


@router.get("/my-history")
async def get_my_nda_history(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Get current user's NDA acceptance history"""
    acceptances = db.query(StaffNdaAcceptance).filter(
        StaffNdaAcceptance.employee_id == current_user.id
    ).order_by(desc(StaffNdaAcceptance.accepted_at)).all()
    
    return {
        "success": True,
        "data": [a.to_dict() for a in acceptances]
    }
