"""
Official Partner Order Management System API Endpoints
DC_PARTNER_001: REST API for partner order lifecycle management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.staff import StaffEmployee
from app.models.staff_accounts import OfficialPartner
from app.services.partner_order_service import (
    OfficialPartnerService,
    PartnerOrderService,
    PartnerDispatchService,
    PartnerInvoiceService,
    PartnerAccessError,
    PartnerValidationError,
    PartnerNotFoundError,
    PartnerDuplicateError
)
from app.schemas.partner_schemas import (
    OfficialPartnerCreate,
    OfficialPartnerUpdate,
    OfficialPartnerResponse,
    PartnerPricingProfileCreate,
    PartnerPricingProfileResponse,
    PartnerOrderCreate,
    PartnerOrderUpdate,
    PartnerOrderApproval,
    PartnerOrderRouting,
    PartnerOrderResponse,
    PartnerOrderListResponse,
    PaymentRecordCreate,
    PaymentRecordResponse,
    DispatchCreate,
    DispatchUpdate,
    DispatchResponse,
    InvoiceGenerateRequest,
    InvoiceResponse,
    OrderStatusLogResponse,
    PartnerDashboardStats
)

router = APIRouter(prefix="/partner", tags=["Official Partner Order Management"])


def handle_partner_exception(e: Exception):
    """Convert Partner service exceptions to HTTP exceptions"""
    if isinstance(e, PartnerAccessError):
        raise HTTPException(status_code=403, detail=str(e))
    elif isinstance(e, PartnerValidationError):
        raise HTTPException(status_code=400, detail=str(e))
    elif isinstance(e, PartnerNotFoundError):
        raise HTTPException(status_code=404, detail=str(e))
    elif isinstance(e, PartnerDuplicateError):
        raise HTTPException(status_code=409, detail=str(e))
    else:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/partners", response_model=dict, summary="Create a new official partner")
def create_partner(
    data: OfficialPartnerCreate,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Create a new official partner (Dealer/Distributor/Vendor).
    Requires VGK/EA/Store Manager/Sales Head role.
    """
    try:
        partner = OfficialPartnerService.create_partner(db, data, current_employee)
        # DC Protocol (Apr 2026): Return auto_password so frontend can show share modal
        _auto_pwd = getattr(partner, '_auto_password', partner.partner_code)
        return {
            "success": True,
            "message": f"Partner {partner.partner_code} created successfully",
            "auto_password": _auto_pwd,
            "data": partner.to_dict()
        }
    except Exception as e:
        handle_partner_exception(e)


@router.get("/partners", response_model=dict, summary="List all partners")
def list_partners(
    company_id: Optional[int] = Query(None, description="Filter by company"),
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by code, name, contact"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """List all official partners with optional filters"""
    try:
        partners, total = OfficialPartnerService.list_partners(
            db, company_id, category, status, search, skip, limit
        )
        # DC Protocol (Apr 2026): Bulk-fetch VGK codes for all returned partners by phone match
        _partner_phones = [p.phone for p in partners if p.phone]
        _vgk_by_phone = {}
        if _partner_phones:
            _vgk_rows = db.query(OfficialPartner.phone, OfficialPartner.partner_code, OfficialPartner.is_active).filter(
                OfficialPartner.category == 'VGK_TEAM',
                OfficialPartner.phone.in_(_partner_phones)
            ).all()
            for _row in _vgk_rows:
                if _row[0]:
                    _clean = _row[0].replace(' ', '').replace('-', '')
                    _vgk_by_phone[_clean] = {'code': _row[1], 'is_active': _row[2]}

        result = []
        for p in partners:
            partner_dict = p.to_dict()
            if hasattr(p, 'company_segments') and p.company_segments:
                partner_dict['company_segments'] = [
                    {
                        'company_id': cs.company_id,
                        'segment_id': cs.segment_id,
                        'is_active': cs.is_active
                    }
                    for cs in p.company_segments
                ]
            else:
                partner_dict['company_segments'] = []
            # Attach VGK code if linked
            _phone_clean = (p.phone or '').replace(' ', '').replace('-', '')
            _vgk_info = _vgk_by_phone.get(_phone_clean)
            partner_dict['vgk_code'] = _vgk_info['code'] if _vgk_info else None
            partner_dict['vgk_is_active'] = _vgk_info['is_active'] if _vgk_info else None
            result.append(partner_dict)
        
        return {
            "success": True,
            "data": result,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        handle_partner_exception(e)


@router.get("/partners/all-active", response_model=dict, summary="List all active partners across companies")
def list_all_active_partners(
    category: Optional[str] = Query(None, description="Filter by category (DEALER/DISTRIBUTOR/VENDOR/REAL_DREAMS)"),
    search: Optional[str] = Query(None, description="Search by code, name, contact"),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    List ALL active partners across ALL companies for tagging purposes.
    DC Protocol Exception: Cross-company read allowed for partner tagging.
    WVV Protocol: Requires staff authentication.
    
    Returns only active partners (is_active=True).
    Inactive partners are automatically hidden.
    """
    from sqlalchemy import or_
    
    query = db.query(OfficialPartner).filter(
        OfficialPartner.is_active == True,
        OfficialPartner.category != 'VGK_TEAM'
    )
    
    if category:
        query = query.filter(OfficialPartner.category == category.upper())
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                OfficialPartner.partner_code.ilike(search_term),
                OfficialPartner.partner_name.ilike(search_term),
                OfficialPartner.contact_person.ilike(search_term),
                OfficialPartner.phone.ilike(search_term)
            )
        )
    
    partners = query.order_by(OfficialPartner.partner_name).limit(limit).all()
    
    result = []
    for p in partners:
        result.append({
            'id': p.id,
            'partner_code': p.partner_code,
            'partner_name': p.partner_name,
            'contact_person': p.contact_person,
            'phone': p.phone,
            'category': p.category,
            'is_active': p.is_active
        })
    
    return {
        "success": True,
        "partners": result,
        "total": len(result)
    }


@router.get("/partners/{partner_id}", response_model=dict, summary="Get partner details")
def get_partner(
    partner_id: int = Path(..., description="Partner ID"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Get detailed information about a specific partner"""
    try:
        partner = OfficialPartnerService.get_partner(db, partner_id)
        if not partner:
            raise HTTPException(status_code=404, detail=f"Partner with ID {partner_id} not found")
        
        partner_dict = partner.to_dict()
        try:
            if hasattr(partner, 'company_segments') and partner.company_segments:
                partner_dict['company_segments'] = [
                    {
                        'company_id': cs.company_id,
                        'segment_id': cs.segment_id,
                        'is_active': cs.is_active
                    }
                    for cs in partner.company_segments
                ]
        except Exception:
            partner_dict['company_segments'] = []
        
        return {
            "success": True,
            "data": partner_dict
        }
    except HTTPException:
        raise
    except Exception as e:
        handle_partner_exception(e)


@router.put("/partners/{partner_id}", response_model=dict, summary="Update partner")
def update_partner(
    partner_id: int,
    data: OfficialPartnerUpdate,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Update an existing partner"""
    try:
        partner = OfficialPartnerService.update_partner(db, partner_id, data, current_employee)
        return {
            "success": True,
            "message": "Partner updated successfully",
            "data": partner.to_dict()
        }
    except Exception as e:
        handle_partner_exception(e)


@router.get("/partners/{partner_id}/kyc", response_model=dict, summary="Get partner KYC documents (staff view)")
def get_partner_kyc(
    partner_id: int,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    [DC-PARTNER-KYC-001] Staff views a partner's KYC documents.
    Restricted to VGK4U, EA, RVZ roles.
    """
    from app.models.kyc_document import KYCDocument
    ALLOWED_ROLES = ['VGK4U', 'EA', 'RVZ']
    role_code = current_employee.role.role_code if current_employee.role else None
    if role_code not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Only VGK4U, EA, or RVZ staff can view KYC documents")
    partner = db.query(OfficialPartner).filter(OfficialPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    docs = db.query(KYCDocument).filter(KYCDocument.partner_id == partner_id).all()
    frontend_map = {'aadhar_front': 'aadhaar_front', 'aadhar_back': 'aadhaar_back',
                    'pan_card': 'pan_card', 'passport_photo': 'passport_photo'}
    return {
        "success": True,
        "kyc_status": partner.kyc_status or 'Not Submitted',
        "aadhaar_number": partner.aadhaar_number,
        "documents": [
            {
                "id": d.id,
                "document_type": frontend_map.get(d.document_type, d.document_type),
                "file_name": d.file_name,
                "file_path": d.file_path,
                "status": d.status,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
                "rejection_reason": d.rejection_reason,
                "admin_notes": d.admin_notes,
            }
            for d in docs
        ]
    }


@router.put("/partners/{partner_id}/kyc/{doc_id}/approve", response_model=dict, summary="Approve partner KYC document")
def approve_partner_kyc_doc(
    partner_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """[DC-PARTNER-KYC-001] Approve a specific KYC document. VGK4U, EA, RVZ only."""
    from app.models.kyc_document import KYCDocument
    from app.services.indian_time import get_indian_time as _git
    ALLOWED_ROLES = ['VGK4U', 'EA', 'RVZ']
    role_code = current_employee.role.role_code if current_employee.role else None
    if role_code not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Only VGK4U, EA, or RVZ staff can approve KYC documents")
    doc = db.query(KYCDocument).filter(
        KYCDocument.id == doc_id, KYCDocument.partner_id == partner_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="KYC document not found")
    doc.status = 'Approved'
    doc.rejection_reason = None
    doc.reviewed_by_id = str(current_employee.id)
    doc.reviewed_at = _git()
    all_docs = db.query(KYCDocument).filter(KYCDocument.partner_id == partner_id).all()
    if all_docs and all(d.status == 'Approved' for d in all_docs):
        partner = db.query(OfficialPartner).filter(OfficialPartner.id == partner_id).first()
        if partner:
            partner.kyc_status = 'Approved'
    db.commit()
    return {"success": True, "message": "KYC document approved"}


@router.put("/partners/{partner_id}/kyc/{doc_id}/reject", response_model=dict, summary="Reject partner KYC document")
def reject_partner_kyc_doc(
    partner_id: int,
    doc_id: int,
    reason: str = Query(..., description="Rejection reason"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """[DC-PARTNER-KYC-001] Reject a specific KYC document. VGK4U, EA, RVZ only."""
    from app.models.kyc_document import KYCDocument
    from app.services.indian_time import get_indian_time as _git
    ALLOWED_ROLES = ['VGK4U', 'EA', 'RVZ']
    role_code = current_employee.role.role_code if current_employee.role else None
    if role_code not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Only VGK4U, EA, or RVZ staff can reject KYC documents")
    doc = db.query(KYCDocument).filter(
        KYCDocument.id == doc_id, KYCDocument.partner_id == partner_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="KYC document not found")
    doc.status = 'Rejected'
    doc.rejection_reason = reason
    doc.reviewed_by_id = str(current_employee.id)
    doc.reviewed_at = _git()
    partner = db.query(OfficialPartner).filter(OfficialPartner.id == partner_id).first()
    if partner and partner.kyc_status == 'Approved':
        partner.kyc_status = 'Pending'
    db.commit()
    return {"success": True, "message": "KYC document rejected"}


@router.post("/partners/{partner_id}/upload-agreement", response_model=dict, summary="Upload agreement document for a partner")
async def upload_partner_agreement(
    partner_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """[DC-PARTNER-DOCS-001] Staff uploads an agreement document for a partner. VGK4U, EA, RVZ only."""
    from app.services.universal_upload_service import UniversalUploadService
    ALLOWED_ROLES = ['VGK4U', 'EA', 'RVZ']
    role_code = current_employee.role.role_code if current_employee.role else None
    if role_code not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Only VGK4U, EA, or RVZ staff can upload partner documents")
    partner = db.query(OfficialPartner).filter(OfficialPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    result = await UniversalUploadService.handle_upload(
        file=file,
        table_name='official_partners',
        record_id=partner_id,
        uploaded_by_id=str(current_employee.id),
        uploaded_by_type='staff',
        storage_dir='partner_documents/agreement',
        db=db
    )
    partner.agreement_document_path = result['file_path']
    db.commit()
    return {"success": True, "message": "Agreement document uploaded", "file_path": result['file_path'], "file_name": result['file_name']}


@router.post("/partners/{partner_id}/upload-application", response_model=dict, summary="Upload application document for a partner")
async def upload_partner_application(
    partner_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """[DC-PARTNER-DOCS-001] Staff uploads an application document for a partner. VGK4U, EA, RVZ only."""
    from app.services.universal_upload_service import UniversalUploadService
    ALLOWED_ROLES = ['VGK4U', 'EA', 'RVZ']
    role_code = current_employee.role.role_code if current_employee.role else None
    if role_code not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Only VGK4U, EA, or RVZ staff can upload partner documents")
    partner = db.query(OfficialPartner).filter(OfficialPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    result = await UniversalUploadService.handle_upload(
        file=file,
        table_name='official_partners',
        record_id=partner_id,
        uploaded_by_id=str(current_employee.id),
        uploaded_by_type='staff',
        storage_dir='partner_documents/application',
        db=db
    )
    partner.application_document_path = result['file_path']
    db.commit()
    return {"success": True, "message": "Application document uploaded", "file_path": result['file_path'], "file_name": result['file_name']}


@router.post("/partners/{partner_id}/reset-password", response_model=dict, summary="Reset partner password")
def reset_partner_password(
    partner_id: int,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Reset partner password (VGK4U, VGK, EA, RVZ only)
    DC_PARTNER_AUTH_002: Password reset with audit trail and company scoping
    WVV Protocol: Staff token authentication required
    
    Features:
    - Resets password to partner_code (e.g., DLR001)
    - Unlocks account if locked
    - Full audit trail for compliance
    - DC Protocol: Uses OfficialPartnerService for company-scoped access
    """
    from app.core.security import SecurityManager
    from app.models.staff_accounts import OfficialPartner, PartnerCompanySegment
    from app.models.staff import log_staff_audit
    from datetime import datetime
    
    ALLOWED_ROLES = ['VGK4U', 'VGK', 'EA', 'RVZ', 'MYNT_REAL']
    
    role_code = current_employee.role.role_code if current_employee.role else None
    staff_type = current_employee.staff_type if hasattr(current_employee, 'staff_type') else None
    
    has_permission = role_code in ALLOWED_ROLES or staff_type in ['VGK4U', 'VGK']
    
    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail="Only VGK4U, VGK, EA, RVZ, or MYNT_REAL staff can reset partner passwords"
        )
    
    partner = OfficialPartnerService.get_partner(db, partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail=f"Partner with ID {partner_id} not found")
    
    partner_company_ids = [
        seg.company_id for seg in db.query(PartnerCompanySegment).filter(
            PartnerCompanySegment.partner_id == partner_id,
            PartnerCompanySegment.is_active == True
        ).all()
    ]
    
    new_password = partner.partner_code
    
    was_locked = partner.login_status == 'locked'
    previous_attempts = partner.failed_login_attempts or 0
    old_data = {
        'login_status': partner.login_status,
        'failed_login_attempts': partner.failed_login_attempts,
        'password_changed_at': partner.password_changed_at.isoformat() if partner.password_changed_at else None
    }
    
    try:
        new_password_hash = SecurityManager.get_password_hash(new_password)
        
        partner.password_hash = new_password_hash
        partner.password_changed_at = datetime.utcnow()
        partner.failed_login_attempts = 0
        partner.login_status = 'active'
        
        log_staff_audit(
            db=db,
            employee_id=current_employee.id,
            action="PARTNER_PASSWORD_RESET",
            resource_type="official_partner",
            resource_id=partner.id,
            old_data=old_data,
            new_data={
                "reset_by": current_employee.emp_code,
                "reset_by_id": current_employee.id,
                "partner_code": partner.partner_code,
                "partner_name": partner.partner_name,
                "new_password": "Reset to Partner Code",
                "account_unlocked": True,
                "was_locked": was_locked,
                "previous_failed_attempts": previous_attempts,
                "partner_company_ids": partner_company_ids
            }
        )
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Password reset to Partner Code: {new_password}",
            "partner_code": partner.partner_code,
            "partner_name": partner.partner_name,
            "temporary_password": new_password,
            "was_locked": was_locked,
            "previous_failed_attempts": previous_attempts,
            "reset_by": current_employee.emp_code,
            "note": "Partner should change password on next login"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reset password: {str(e)}")


@router.post("/partners/{partner_id}/create-vgk-login", response_model=dict, summary="Create VGK4U login for a partner")
def create_vgk_login_for_partner(
    partner_id: int = Path(..., description="Official Partner ID"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol (Apr 2026): On-demand VGK4U login creation for an official partner.
    - Checks if a VGK_TEAM member already exists (by phone match)
    - If not, creates one with a random VGK code and returns credentials
    - Password = partner's phone number (mobile)
    - Upline = root VGK07102207
    """
    from app.core.security import SecurityManager
    from decimal import Decimal
    import random

    partner = db.query(OfficialPartner).filter(OfficialPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    if not partner.phone:
        raise HTTPException(status_code=400, detail="Partner has no phone number — cannot create VGK login")

    _clean_phone = partner.phone.replace(' ', '').replace('-', '')
    _existing_vgk = db.query(OfficialPartner).filter(
        OfficialPartner.phone == _clean_phone,
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if _existing_vgk:
        return {
            "success": True,
            "already_exists": True,
            "vgk_code": _existing_vgk.partner_code,
            "vgk_is_active": _existing_vgk.is_active,
            "message": f"VGK login already exists: {_existing_vgk.partner_code}"
        }

    # Find root VGK upline
    _root_vgk = db.query(OfficialPartner).filter(
        OfficialPartner.partner_code == 'VGK07102207'
    ).first()
    _root_vgk_id = _root_vgk.id if _root_vgk else None

    # Generate unique VGK code
    _code = None
    for _ in range(30):
        _c = f"VGK0710{random.randint(1000, 9999)}"
        if not db.query(OfficialPartner).filter(OfficialPartner.partner_code == _c).first():
            _code = _c
            break
    if not _code:
        raise HTTPException(status_code=500, detail="Could not generate unique VGK code — try again")

    _auto_pwd = partner.phone.replace(' ', '')
    _new_vgk = OfficialPartner(
        company_id=partner.company_id or 4,
        partner_code=_code,
        partner_name=partner.partner_name,
        contact_person=partner.contact_person,
        phone=partner.phone,
        whatsapp_number=partner.whatsapp_number,
        email=partner.email,
        category='VGK_TEAM',
        is_active=False,
        login_status='active',
        parent_partner_id=_root_vgk_id,
        vgk_role='VGK_ASSOCIATE',
        vgk_points_balance=Decimal('0'),
        password_hash=SecurityManager.get_password_hash(_auto_pwd),
    )
    db.add(_new_vgk)
    db.flush()

    try:
        from app.services.vgk_commission import add_vgk_points_entry
        add_vgk_points_entry(
            db=db, partner_id=_new_vgk.id,
            points_credit=Decimal('10000'), points_debit=Decimal('0'),
            reason_code='WELCOME_BONUS', reference_type='partner_manual_vgk',
            notes=f'Manual VGK login creation for partner {partner.partner_code}',
            created_by=current_employee.id
        )
    except Exception:
        pass

    db.commit()
    db.refresh(_new_vgk)

    return {
        "success": True,
        "already_exists": False,
        "vgk_code": _code,
        "vgk_is_active": _new_vgk.is_active,
        "auto_password": _auto_pwd,
        "partner_code": partner.partner_code,
        "partner_name": partner.partner_name,
        "message": f"VGK login created: {_code}"
    }


@router.post("/partners/{partner_id}/pricing", response_model=dict, summary="Create pricing profile")
def create_pricing_profile(
    partner_id: int,
    data: PartnerPricingProfileCreate,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Create a pricing profile for a partner"""
    try:
        data.partner_id = partner_id
        profile = OfficialPartnerService.create_pricing_profile(db, data, current_employee)
        return {
            "success": True,
            "message": "Pricing profile created successfully",
            "data": profile.to_dict()
        }
    except Exception as e:
        handle_partner_exception(e)


@router.post("/orders", response_model=dict, summary="Create new order")
def create_order(
    data: PartnerOrderCreate,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Create a new partner order.
    Calculates pricing from partner profiles or master rates.
    Checks stock availability for each line item.
    """
    try:
        order = PartnerOrderService.create_order(db, data, current_employee)
        return {
            "success": True,
            "message": f"Order {order.order_number} created successfully",
            "data": order.to_dict()
        }
    except Exception as e:
        handle_partner_exception(e)


@router.get("/orders", response_model=dict, summary="List orders")
def list_orders(
    company_id: Optional[int] = Query(None),
    partner_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """List partner orders with filters"""
    try:
        orders, total = PartnerOrderService.list_orders(
            db, company_id, partner_id, status, from_date, to_date, search, skip, limit
        )
        
        order_list = []
        for order in orders:
            order_dict = order.to_dict()
            order_dict['partner_name'] = order.partner.partner_name if order.partner else None
            order_dict['partner_code'] = order.partner.partner_code if order.partner else None
            order_dict['item_count'] = len(order.line_items) if order.line_items else 0
            order_list.append(order_dict)
        
        return {
            "success": True,
            "data": order_list,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        handle_partner_exception(e)


@router.get("/orders/pending-fulfillment", response_model=dict, summary="Get pending fulfillment orders")
def get_pending_fulfillment_orders(
    company_id: Optional[int] = Query(None, description="Filter by company"),
    fulfillment_type: Optional[str] = Query(None, description="MANUFACTURING or PROCUREMENT"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC_ORDER_FULFILLMENT_002: Get orders pending manufacturing or procurement.
    Returns orders waiting for stock to become available.
    """
    try:
        orders, total = PartnerOrderService.get_pending_fulfillment_orders(
            db, company_id, current_employee, fulfillment_type, skip, limit
        )
        return {
            "success": True,
            "data": orders,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        handle_partner_exception(e)


@router.get("/orders/stock-short", response_model=dict, summary="Partner orders with proven stock shortage (stock items source of truth)")
def get_stock_short_orders(
    company_id: Optional[int] = Query(None, description="Filter by company"),
    search: Optional[str] = Query(None, description="Search PO# / partner name / phone"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC_PARTNER_STOCK_SHORT_001: Returns partner orders where at least one line
    item has ordered qty > current available stock from StockLedger.
    Single source of truth: stock_item_master + stock_ledger (same as tab-3 low-stock).
    Excludes CANCELLED / DELIVERED orders.
    """
    try:
        from sqlalchemy import func, or_
        from sqlalchemy.orm import joinedload
        from app.models.staff_accounts import (
            PartnerOrder, PartnerOrderLine, StockItemMaster, StockLedger
        )

        # Stock balance subquery — reuses exact same pattern as
        # ProcurementPlanningService.get_low_stock_items in staff_accounts_service.py
        stock_subq = db.query(
            StockLedger.item_id,
            func.sum(StockLedger.quantity_in - StockLedger.quantity_out).label('available_qty')
        ).group_by(StockLedger.item_id).subquery()

        # Orders that have at least one line with ordered qty > available stock
        short_order_ids_subq = db.query(PartnerOrderLine.order_id).outerjoin(
            stock_subq, PartnerOrderLine.item_id == stock_subq.c.item_id
        ).filter(
            PartnerOrderLine.quantity > func.coalesce(stock_subq.c.available_qty, 0)
        ).distinct().subquery()

        query = db.query(PartnerOrder).options(
            joinedload(PartnerOrder.line_items),
            joinedload(PartnerOrder.partner)
        ).filter(
            PartnerOrder.id.in_(db.query(short_order_ids_subq.c.order_id)),
            PartnerOrder.status.notin_(['CANCELLED', 'DELIVERED'])
        )

        if company_id:
            query = query.filter(PartnerOrder.company_id == company_id)
        if search:
            query = query.filter(or_(
                PartnerOrder.po_number.ilike(f'%{search}%'),
                PartnerOrder.customer_name.ilike(f'%{search}%'),
                PartnerOrder.customer_phone.ilike(f'%{search}%'),
            ))

        total = query.count()
        orders = query.order_by(PartnerOrder.created_at.desc()).offset(skip).limit(limit).all()

        # Gather all item_ids across returned orders — load stock + master in 2 queries
        item_ids = {line.item_id for order in orders for line in order.line_items}

        stock_map: dict = {}
        item_master: dict = {}
        if item_ids:
            bal_rows = db.query(
                StockLedger.item_id,
                func.sum(StockLedger.quantity_in - StockLedger.quantity_out).label('bal')
            ).filter(StockLedger.item_id.in_(list(item_ids))).group_by(StockLedger.item_id).all()
            stock_map = {r.item_id: float(r.bal) if r.bal else 0 for r in bal_rows}

            items = db.query(StockItemMaster).filter(StockItemMaster.id.in_(list(item_ids))).all()
            item_master = {i.id: i for i in items}

        results = []
        for order in orders:
            short_lines = []
            for line in order.line_items:
                available = stock_map.get(line.item_id, 0)
                ordered   = float(line.quantity)
                if ordered > available:
                    im = item_master.get(line.item_id)
                    short_lines.append({
                        'item_id':         line.item_id,
                        'item_code':       im.item_code if im else '—',
                        'item_name':       im.item_name if im else '—',
                        'ordered_qty':     ordered,
                        'available_stock': max(0.0, available),
                        'shortage':        round(ordered - max(0.0, available), 3),
                    })

            od = order.to_dict()
            od['partner_name']     = order.partner.partner_name if order.partner else '—'
            od['short_lines']      = short_lines
            od['total_short_lines'] = len(short_lines)
            od['total_shortage']   = round(sum(l['shortage'] for l in short_lines), 3)
            results.append(od)

        return {
            'success': True,
            'orders':  results,
            'total':   total,
            'skip':    skip,
            'limit':   limit,
        }
    except Exception as e:
        handle_partner_exception(e)


@router.get("/orders/pending-approval/list", response_model=dict, summary="Get orders pending approval")
def get_pending_approval_orders(
    company_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Get list of orders pending Store Manager approval"""
    try:
        orders, total = PartnerOrderService.list_orders(
            db=db,
            company_id=company_id,
            status='PENDING_APPROVAL',
            skip=skip,
            limit=limit
        )
        
        order_list = []
        for order in orders:
            order_dict = order.to_dict()
            order_dict['partner_name'] = order.partner.partner_name if order.partner else None
            order_dict['item_count'] = len(order.line_items) if order.line_items else 0
            order_list.append(order_dict)
        
        return {
            "success": True,
            "data": order_list,
            "total": total
        }
    except Exception as e:
        handle_partner_exception(e)


@router.get("/orders/ready-dispatch/list", response_model=dict, summary="Get orders ready for dispatch")
def get_ready_dispatch_orders(
    company_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Get list of orders ready for dispatch"""
    try:
        orders, total = PartnerOrderService.list_orders(
            db=db,
            company_id=company_id,
            status='READY_TO_DISPATCH',
            skip=skip,
            limit=limit
        )
        
        order_list = []
        for order in orders:
            order_dict = order.to_dict()
            order_dict['partner_name'] = order.partner.partner_name if order.partner else None
            order_dict['item_count'] = len(order.line_items) if order.line_items else 0
            order_list.append(order_dict)
        
        return {
            "success": True,
            "data": order_list,
            "total": total
        }
    except Exception as e:
        handle_partner_exception(e)


# Additional endpoints for frontend compatibility

@router.get("/orders/approval-queue", response_model=dict, summary="Get orders pending approval (alias)")
def get_approval_queue(
    company_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Alias for pending-approval/list for frontend compatibility"""
    try:
        orders, total = PartnerOrderService.list_orders(
            db=db,
            company_id=company_id,
            status='PENDING_APPROVAL',
            skip=skip,
            limit=limit
        )
        return {"success": True, "data": [order.to_dict() for order in orders], "total": total}
    except Exception as e:
        handle_partner_exception(e)


@router.get("/orders/dispatch-queue", response_model=dict, summary="Get orders ready for dispatch (alias)")
def get_dispatch_queue(
    company_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Get orders ready for dispatch"""
    try:
        orders, total = PartnerOrderService.list_orders(
            db=db,
            company_id=company_id,
            status='READY_TO_DISPATCH',
            skip=skip,
            limit=limit
        )
        return {"success": True, "data": [order.to_dict() for order in orders], "total": total}
    except Exception as e:
        handle_partner_exception(e)


@router.get("/orders/routing-pending", response_model=dict, summary="Get approved orders pending routing")
def get_routing_pending(
    company_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Get approved orders that need routing decision"""
    try:
        orders, total = PartnerOrderService.list_orders(
            db=db,
            company_id=company_id,
            status='APPROVED',
            skip=skip,
            limit=limit
        )
        return {"success": True, "data": [order.to_dict() for order in orders], "total": total}
    except Exception as e:
        handle_partner_exception(e)


@router.get("/orders/queue/production", response_model=dict, summary="Get orders in production queue")
def get_production_queue(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Get orders routed to production"""
    try:
        orders, total = PartnerOrderService.list_orders(
            db=db,
            company_id=company_id,
            status='IN_PRODUCTION',
            skip=0,
            limit=100
        )
        return {"success": True, "data": [order.to_dict() for order in orders], "total": total}
    except Exception as e:
        handle_partner_exception(e)


@router.get("/orders/queue/procurement", response_model=dict, summary="Get orders in procurement queue")
def get_procurement_queue(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Get orders routed to procurement"""
    try:
        orders, total = PartnerOrderService.list_orders(
            db=db,
            company_id=company_id,
            status='IN_PROCUREMENT',
            skip=0,
            limit=100
        )
        return {"success": True, "data": [order.to_dict() for order in orders], "total": total}
    except Exception as e:
        handle_partner_exception(e)


@router.get("/orders/queue/dispatch", response_model=dict, summary="Get orders in dispatch queue")
def get_direct_dispatch_queue(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Get orders in direct dispatch queue"""
    try:
        orders, total = PartnerOrderService.list_orders(
            db=db,
            company_id=company_id,
            status='READY_TO_DISPATCH',
            skip=0,
            limit=100
        )
        return {"success": True, "data": [order.to_dict() for order in orders], "total": total}
    except Exception as e:
        handle_partner_exception(e)

@router.get("/orders/{order_id}", response_model=dict, summary="Get order details")
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Get detailed information about an order including line items"""
    order = PartnerOrderService.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order with ID {order_id} not found")
    
    order_dict = order.to_dict()
    order_dict['partner_name'] = order.partner.partner_name if order.partner else None
    order_dict['partner_code'] = order.partner.partner_code if order.partner else None
    order_dict['line_items'] = [li.to_dict() for li in order.line_items] if order.line_items else []
    order_dict['status_logs'] = [
        {
            'from_status': sl.from_status,
            'to_status': sl.to_status,
            'changed_at': sl.changed_at.isoformat() if sl.changed_at else None,
            'remarks': sl.remarks
        }
        for sl in order.status_logs
    ] if order.status_logs else []
    order_dict['payment_records'] = [pr.to_dict() for pr in order.payment_records] if order.payment_records else []
    
    if order.dispatch_info:
        order_dict['dispatch'] = order.dispatch_info.to_dict()
    
    return {
        "success": True,
        "data": order_dict
    }


@router.post("/orders/{order_id}/generate-pi", response_model=dict, summary="Generate Proforma Invoice")
def generate_pi(
    order_id: int,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Generate Proforma Invoice (PI) for an order"""
    try:
        order = PartnerOrderService.generate_pi(db, order_id, current_employee)
        return {
            "success": True,
            "message": f"PI {order.pi_number} generated successfully",
            "data": {
                "order_id": order.id,
                "order_number": order.order_number,
                "pi_number": order.pi_number,
                "status": order.status,
                "grand_total": float(order.grand_total)
            }
        }
    except Exception as e:
        handle_partner_exception(e)


@router.post("/orders/{order_id}/submit-approval", response_model=dict, summary="Submit for approval")
def submit_for_approval(
    order_id: int,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Submit order for Store Manager approval"""
    try:
        order = PartnerOrderService.submit_for_approval(db, order_id, current_employee)
        return {
            "success": True,
            "message": "Order submitted for approval",
            "data": order.to_dict()
        }
    except Exception as e:
        handle_partner_exception(e)


@router.post("/orders/{order_id}/approve", response_model=dict, summary="Approve/Reject order")
def approve_order(
    order_id: int,
    data: PartnerOrderApproval,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Approve or reject an order (Store Manager action).
    Requires Store Manager/VGK/EA role.
    """
    try:
        order = PartnerOrderService.approve_order(db, order_id, data, current_employee)
        action = "approved" if data.approved else "rejected"
        return {
            "success": True,
            "message": f"Order {action} successfully",
            "data": order.to_dict()
        }
    except Exception as e:
        handle_partner_exception(e)


@router.post("/orders/{order_id}/payment", response_model=dict, summary="Record payment")
def record_payment(
    order_id: int,
    data: PaymentRecordCreate,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Record a payment against an order"""
    try:
        payment = PartnerOrderService.record_payment(db, order_id, data, current_employee)
        return {
            "success": True,
            "message": f"Payment of {data.amount} recorded successfully",
            "data": payment.to_dict()
        }
    except Exception as e:
        handle_partner_exception(e)


@router.post("/payments/{payment_id}/verify", response_model=dict, summary="Verify payment")
def verify_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Verify a payment record (Finance action)"""
    try:
        payment = PartnerOrderService.verify_payment(db, payment_id, current_employee)
        return {
            "success": True,
            "message": "Payment verified successfully",
            "data": payment.to_dict()
        }
    except Exception as e:
        handle_partner_exception(e)


@router.post("/orders/{order_id}/route", response_model=dict, summary="Route order")
def route_order(
    order_id: int,
    data: PartnerOrderRouting,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Route order to Production, Procurement, or Direct Dispatch.
    Requires Store Manager/VGK/EA role.
    """
    try:
        order = PartnerOrderService.route_order(db, order_id, data, current_employee)
        return {
            "success": True,
            "message": f"Order routed to {data.route_to.value}",
            "data": order.to_dict()
        }
    except Exception as e:
        handle_partner_exception(e)


@router.get("/orders/{order_id}/fulfillability", response_model=dict, summary="Check order fulfillability")
def get_order_fulfillability(
    order_id: int,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC_ORDER_FULFILLMENT_001: Check stock availability for order line items.
    Returns per-item stock status and routing recommendations (PRODUCTION/PROCUREMENT/DIRECT_DISPATCH).
    """
    try:
        result = PartnerOrderService.get_order_fulfillability(db, order_id, current_employee)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        handle_partner_exception(e)


@router.post("/orders/{order_id}/create-manufacturing", response_model=dict, summary="Create manufacturing from order")
def create_manufacturing_from_order(
    order_id: int,
    line_item_ids: List[int] = Query(..., description="Line item IDs to manufacture"),
    priority: str = Query("NORMAL", description="Manufacturing priority"),
    notes: Optional[str] = Query(None, description="Additional notes"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC_ORDER_MANUFACTURING_001: Create Manufacturing Order(s) from Partner Order.
    Automatically creates linked manufacturing orders for items that need production.
    """
    try:
        result = PartnerOrderService.create_manufacturing_from_order(
            db, order_id, line_item_ids, current_employee, priority, notes
        )
        return {
            "success": True,
            "message": f"Created {len(result['manufacturing_orders_created'])} manufacturing order(s)",
            "data": result
        }
    except Exception as e:
        handle_partner_exception(e)


@router.post("/orders/{order_id}/dispatch", response_model=dict, summary="Create dispatch")
def create_dispatch(
    order_id: int,
    data: DispatchCreate,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Create dispatch record for an order"""
    try:
        dispatch = PartnerDispatchService.create_dispatch(db, order_id, data, current_employee)
        return {
            "success": True,
            "message": "Dispatch created successfully",
            "data": dispatch.to_dict()
        }
    except Exception as e:
        handle_partner_exception(e)


@router.put("/dispatches/{dispatch_id}", response_model=dict, summary="Update dispatch")
def update_dispatch(
    dispatch_id: int,
    data: DispatchUpdate,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Update dispatch status/tracking"""
    try:
        dispatch = PartnerDispatchService.update_dispatch(db, dispatch_id, data, current_employee)
        return {
            "success": True,
            "message": "Dispatch updated successfully",
            "data": dispatch.to_dict()
        }
    except Exception as e:
        handle_partner_exception(e)


@router.post("/orders/{order_id}/invoice", response_model=dict, summary="Generate invoice")
def generate_invoice(
    order_id: int,
    data: InvoiceGenerateRequest,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Generate tax invoice for a dispatched order"""
    try:
        invoice = PartnerInvoiceService.generate_invoice(db, order_id, data, current_employee)
        return {
            "success": True,
            "message": f"Invoice {invoice.invoice_number} generated successfully",
            "data": invoice.to_dict()
        }
    except Exception as e:
        handle_partner_exception(e)


@router.get("/invoices", response_model=dict, summary="List invoices")
def list_invoices(
    company_id: Optional[int] = Query(None),
    partner_id: Optional[int] = Query(None),
    payment_status: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """List partner invoices with filters"""
    try:
        invoices, total = PartnerInvoiceService.list_invoices(
            db, company_id, partner_id, payment_status, from_date, to_date, skip, limit
        )
        return {
            "success": True,
            "data": [inv.to_dict() for inv in invoices],
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        handle_partner_exception(e)


@router.get("/invoices/{invoice_id}", response_model=dict, summary="Get invoice details")
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Get detailed information about an invoice"""
    invoice = PartnerInvoiceService.get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice with ID {invoice_id} not found")
    
    return {
        "success": True,
        "data": invoice.to_dict()
    }


@router.get("/dashboard/stats", response_model=dict, summary="Get partner dashboard stats")
def get_dashboard_stats(
    company_id: Optional[int] = Query(None),
    partner_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Get dashboard statistics for partner orders"""
    from sqlalchemy import func
    from app.models.staff_accounts import PartnerOrder, PartnerInvoice, OfficialPartner
    
    query_filters = []
    if company_id:
        query_filters.append(PartnerOrder.company_id == company_id)
    if partner_id:
        query_filters.append(PartnerOrder.partner_id == partner_id)
    
    total_orders = db.query(func.count(PartnerOrder.id)).filter(*query_filters).scalar() or 0
    
    pending_orders = db.query(func.count(PartnerOrder.id)).filter(
        *query_filters,
        PartnerOrder.status.in_(['DRAFT', 'PI_GENERATED', 'PENDING_APPROVAL', 'PAYMENT_PENDING'])
    ).scalar() or 0
    
    approved_orders = db.query(func.count(PartnerOrder.id)).filter(
        *query_filters,
        PartnerOrder.status.in_(['APPROVED', 'PAYMENT_CONFIRMED', 'ROUTED_TO_PRODUCTION', 
                                  'ROUTED_TO_PROCUREMENT', 'IN_MANUFACTURING', 
                                  'PROCUREMENT_IN_PROGRESS', 'READY_TO_DISPATCH'])
    ).scalar() or 0
    
    dispatched_orders = db.query(func.count(PartnerOrder.id)).filter(
        *query_filters,
        PartnerOrder.status.in_(['DISPATCHED', 'IN_TRANSIT', 'DELIVERED', 'CLOSED'])
    ).scalar() or 0
    
    total_order_value = db.query(func.sum(PartnerOrder.grand_total)).filter(*query_filters).scalar() or 0
    
    pending_payment = db.query(func.sum(PartnerInvoice.balance_due)).filter(
        PartnerInvoice.payment_status.in_(['PENDING', 'PARTIAL'])
    )
    if company_id:
        pending_payment = pending_payment.filter(PartnerInvoice.company_id == company_id)
    if partner_id:
        pending_payment = pending_payment.filter(PartnerInvoice.partner_id == partner_id)
    pending_payment_value = pending_payment.scalar() or 0
    
    credit_info = {'credit_limit': 0, 'credit_used': 0, 'credit_available': 0}
    if partner_id:
        partner = db.query(OfficialPartner).filter(OfficialPartner.id == partner_id).first()
        if partner:
            credit_info = {
                'credit_limit': float(partner.credit_limit) if partner.credit_limit else 0,
                'credit_used': float(partner.credit_used) if partner.credit_used else 0,
                'credit_available': float(partner.credit_limit - partner.credit_used) if partner.credit_limit else 0
            }
    
    return {
        "success": True,
        "data": {
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "approved_orders": approved_orders,
            "dispatched_orders": dispatched_orders,
            "total_order_value": float(total_order_value),
            "pending_payment_value": float(pending_payment_value),
            **credit_info
        }
    }










@router.post("/orders/{order_id}/deliver", response_model=dict, summary="Mark order as delivered")
def mark_order_delivered(
    order_id: int,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Mark an order as delivered"""
    try:
        result = PartnerOrderService.update_order_status(
            db=db,
            order_id=order_id,
            new_status='DELIVERED',
            updated_by=current_employee.id
        )
        return {"success": True, "message": "Order marked as delivered", "data": result}
    except Exception as e:
        handle_partner_exception(e)


@router.get("/payments", response_model=dict, summary="List all payments")
def list_payments(
    order_id: Optional[int] = Query(None),
    partner_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """List partner order payments"""
    try:
        payments = PartnerOrderService.list_payments(
            db=db,
            order_id=order_id,
            partner_id=partner_id,
            status=status,
            skip=skip,
            limit=limit
        )
        return {"success": True, "data": payments, "total": len(payments)}
    except Exception as e:
        handle_partner_exception(e)


@router.post("/payments", response_model=dict, summary="Record a new payment")
def create_payment(
    payment_data: dict,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Record a new payment for an order"""
    try:
        result = PartnerOrderService.record_payment(
            db=db,
            order_id=payment_data.get('order_id'),
            amount=payment_data.get('amount'),
            payment_mode=payment_data.get('payment_mode'),
            reference_number=payment_data.get('reference_number'),
            payment_date=payment_data.get('payment_date'),
            remarks=payment_data.get('remarks'),
            recorded_by=current_employee.id
        )
        return {"success": True, "message": "Payment recorded successfully", "data": result}
    except Exception as e:
        handle_partner_exception(e)


@router.post("/payments/{payment_id}/reject", response_model=dict, summary="Reject a payment")
def reject_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Reject a payment"""
    try:
        result = PartnerOrderService.update_payment_status(
            db=db,
            payment_id=payment_id,
            status='REJECTED',
            verified_by=current_employee.id
        )
        return {"success": True, "message": "Payment rejected", "data": result}
    except Exception as e:
        handle_partner_exception(e)


@router.get("/pricing", response_model=dict, summary="List all pricing profiles")
def list_pricing(
    partner_id: Optional[int] = Query(None),
    item_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """List partner pricing profiles"""
    try:
        pricing = PartnerInvoiceService.list_pricing_profiles(
            db=db,
            partner_id=partner_id,
            item_id=item_id,
            skip=skip,
            limit=limit
        )
        return {"success": True, "data": pricing, "total": len(pricing)}
    except Exception as e:
        handle_partner_exception(e)


@router.post("/pricing", response_model=dict, summary="Create a pricing profile")
def create_pricing(
    pricing_data: dict,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Create a pricing profile for a partner"""
    try:
        from app.schemas.partner_schemas import PartnerPricingProfileCreate
        profile_data = PartnerPricingProfileCreate(
            partner_id=pricing_data.get('partner_id'),
            item_id=pricing_data.get('item_id'),
            special_price=pricing_data.get('special_price'),
            discount_percentage=pricing_data.get('discount_percentage'),
            effective_from=pricing_data.get('valid_from') or pricing_data.get('effective_from'),
            effective_to=pricing_data.get('valid_until') or pricing_data.get('effective_to')
        )
        result = OfficialPartnerService.create_pricing_profile(db, profile_data, current_employee)
        return {"success": True, "message": "Pricing profile created", "data": result.to_dict()}
    except Exception as e:
        handle_partner_exception(e)


@router.get("/revenue-dashboard", summary="Get partner revenue dashboard data")
async def get_revenue_dashboard(
    company_id: Optional[int] = Query(None),
    partner_id: Optional[int] = Query(None),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    from sqlalchemy import func
    from app.models.staff_accounts import PartnerOrder
    from datetime import datetime, timedelta
    import pytz

    now = datetime.now(pytz.timezone("Asia/Kolkata"))
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)

    scope_filters = []
    if company_id:
        scope_filters.append(PartnerOrder.company_id == company_id)
    if partner_id:
        scope_filters.append(PartnerOrder.partner_id == partner_id)

    completed_statuses = ['DELIVERED', 'CLOSED', 'APPROVED', 'PAYMENT_CONFIRMED']
    pending_statuses = ['DRAFT', 'PI_GENERATED', 'PENDING_APPROVAL', 'PAYMENT_PENDING']

    try:
        total_revenue = float(db.query(func.coalesce(func.sum(PartnerOrder.grand_total), 0)).filter(
            *scope_filters,
            PartnerOrder.status.in_(completed_statuses)
        ).scalar() or 0)

        this_month = float(db.query(func.coalesce(func.sum(PartnerOrder.grand_total), 0)).filter(
            *scope_filters,
            PartnerOrder.status.in_(completed_statuses),
            PartnerOrder.created_at >= current_month_start
        ).scalar() or 0)

        last_month_val = float(db.query(func.coalesce(func.sum(PartnerOrder.grand_total), 0)).filter(
            *scope_filters,
            PartnerOrder.status.in_(completed_statuses),
            PartnerOrder.created_at >= last_month_start,
            PartnerOrder.created_at < current_month_start
        ).scalar() or 0)

        growth = ((this_month - last_month_val) / last_month_val * 100) if last_month_val > 0 else 0

        pending = float(db.query(func.coalesce(func.sum(PartnerOrder.grand_total), 0)).filter(
            *scope_filters,
            PartnerOrder.status.in_(pending_statuses)
        ).scalar() or 0)

        received = total_revenue

        monthly_breakdown = []
        for i in range(5, -1, -1):
            month_date = now - timedelta(days=30 * i)
            m_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if month_date.month == 12:
                m_end = m_start.replace(year=m_start.year + 1, month=1)
            else:
                m_end = m_start.replace(month=m_start.month + 1)

            amount = float(db.query(func.coalesce(func.sum(PartnerOrder.grand_total), 0)).filter(
                *scope_filters,
                PartnerOrder.status.in_(completed_statuses),
                PartnerOrder.created_at >= m_start,
                PartnerOrder.created_at < m_end
            ).scalar() or 0)

            monthly_breakdown.append({
                "month": m_start.strftime("%b %Y"),
                "amount": amount
            })

        return {
            "success": True,
            "data": {
                "total_revenue": total_revenue,
                "this_month": this_month,
                "last_month": last_month_val,
                "growth_percentage": round(growth, 1),
                "pending_payments": pending,
                "received_payments": received,
                "monthly_breakdown": monthly_breakdown
            }
        }
    except Exception:
        return {
            "success": True,
            "data": {
                "total_revenue": 0,
                "this_month": 0,
                "last_month": 0,
                "growth_percentage": 0,
                "pending_payments": 0,
                "received_payments": 0,
                "monthly_breakdown": []
            }
        }
