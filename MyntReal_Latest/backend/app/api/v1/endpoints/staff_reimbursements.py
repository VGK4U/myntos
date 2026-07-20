"""
Staff Reimbursement Claims System - DC Protocol Compliant
Multi-Company expense reimbursement with 2-level approval workflow

Workflow: DRAFT → SUBMITTED → MANAGER_APPROVED → FINANCE_APPROVED → SETTLED

DC Protocol: Company-wise data segregation
WVV Protocol: Staff token authentication throughout

Dec 19, 2025: Initial implementation
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func, or_, desc
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal

from app.services.universal_upload_service import UniversalUploadService
from app.services.reimbursement_accounting_service import ReimbursementAccountingService

from app.models.staff_accounts import (
    StaffReimbursementClaim, StaffReimbursementClaimItem,
    AssociatedCompany, CompanySegment, FundAllocation, ExpenseEntry
)
from app.models.staff import StaffEmployee
from app.models.staff_journey import StaffJourney
from app.models.expense_category import ExpenseMainCategory, ExpenseSubCategory
from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.base import get_indian_time

router = APIRouter(prefix="/staff/reimbursements", tags=["Staff Reimbursements"])


def generate_claim_number(db: Session, company_id: int) -> str:
    """Generate unique claim number: REIMB-{COMPANY_CODE}-{YYYYMM}-{SEQ}"""
    company = db.query(AssociatedCompany).filter_by(id=company_id).first()
    company_code = company.company_code[:3].upper() if company else "GEN"
    
    today = get_indian_time()
    year_month = today.strftime("%Y%m")
    
    count = db.query(func.count(StaffReimbursementClaim.id)).filter(
        StaffReimbursementClaim.company_id == company_id,
        StaffReimbursementClaim.claim_number.like(f"REIMB-{company_code}-{year_month}-%")
    ).scalar() or 0
    
    seq = count + 1
    return f"REIMB-{company_code}-{year_month}-{seq:04d}"


def validate_employee_company_access(employee: StaffEmployee, company_id: int):
    """Validate employee has access to the specified company - DC Protocol"""
    if employee.base_company_id == company_id:
        return True
    
    if employee.data_companies and company_id in employee.data_companies:
        return True
    
    raise HTTPException(
        status_code=403,
        detail="You do not have access to this company"
    )


class ClaimItemCreate(BaseModel):
    main_category_id: Optional[int] = None
    sub_category_id: Optional[int] = None
    expense_date: str
    description: str
    vendor_name: Optional[str] = None
    amount: float
    gst_applicable: bool = False
    gst_amount: float = 0
    bill_number: Optional[str] = None
    bill_date: Optional[str] = None
    bill_path: Optional[str] = None
    bill_remarks: Optional[str] = None
    is_travel_expense: bool = False
    travel_mode: Optional[str] = None
    travel_from: Optional[str] = None
    travel_to: Optional[str] = None
    distance_km: Optional[float] = None


class ClaimCreate(BaseModel):
    company_id: int
    segment_id: Optional[int] = None
    journey_id: Optional[int] = None
    is_travel_claim: bool = False
    travel_mode: Optional[str] = None
    travel_from: Optional[str] = None
    travel_to: Optional[str] = None
    distance_km: Optional[float] = None
    mileage_rate: Optional[float] = None
    claim_title: str = Field(..., min_length=5, max_length=200)
    claim_description: Optional[str] = None
    claim_period_from: Optional[str] = None
    claim_period_to: Optional[str] = None
    items: Optional[List[ClaimItemCreate]] = []


class ClaimUpdate(BaseModel):
    segment_id: Optional[int] = None
    journey_id: Optional[int] = None
    is_travel_claim: Optional[bool] = None
    travel_mode: Optional[str] = None
    travel_from: Optional[str] = None
    travel_to: Optional[str] = None
    distance_km: Optional[float] = None
    mileage_rate: Optional[float] = None
    claim_title: Optional[str] = None
    claim_description: Optional[str] = None
    claim_period_from: Optional[str] = None
    claim_period_to: Optional[str] = None


class ApprovalAction(BaseModel):
    remarks: Optional[str] = None


class RejectionAction(BaseModel):
    reason: str = Field(..., min_length=10)


class SettlementAction(BaseModel):
    settlement_mode: str
    settlement_reference: Optional[str] = None
    fund_allocation_id: Optional[int] = None
    remarks: Optional[str] = None


@router.get("/my-claims")
async def get_my_claims(
    company_id: int = Query(..., description="Company ID - DC Protocol"),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Get current employee's claims for a specific company"""
    validate_employee_company_access(current_user, company_id)
    
    query = db.query(StaffReimbursementClaim).filter(
        StaffReimbursementClaim.employee_id == current_user.id,
        StaffReimbursementClaim.company_id == company_id
    )
    
    if status:
        query = query.filter(StaffReimbursementClaim.status == status)
    
    total = query.count()
    claims = query.order_by(desc(StaffReimbursementClaim.created_at)).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "success": True,
        "claims": [c.to_dict() for c in claims],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }


@router.get("/claims/{claim_id}")
async def get_claim_detail(
    claim_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Get claim details with items - DC Protocol enforced"""
    claim = db.query(StaffReimbursementClaim).options(
        joinedload(StaffReimbursementClaim.items)
    ).filter_by(id=claim_id).first()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    validate_employee_company_access(current_user, claim.company_id)
    
    is_owner = claim.employee_id == current_user.id
    is_manager = current_user.role and current_user.role.role_code in ['manager', 'senior_manager', 'department_head']
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    is_finance = current_user.staff_type in ['VGK4U', 'VGK4U Supreme', 'EA', 'ACCOUNTS']
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not (is_owner or is_manager or is_finance):
    #     raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "success": True,
        "claim": claim.to_dict(include_items=True)
    }


@router.post("/claims")
async def create_claim(
    data: ClaimCreate,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Create new reimbursement claim (DRAFT status)"""
    validate_employee_company_access(current_user, data.company_id)
    
    claim_number = generate_claim_number(db, data.company_id)
    
    claim = StaffReimbursementClaim(
        claim_number=claim_number,
        employee_id=current_user.id,
        company_id=data.company_id,
        segment_id=data.segment_id,
        journey_id=data.journey_id,
        is_travel_claim=data.is_travel_claim,
        travel_mode=data.travel_mode,
        travel_from=data.travel_from,
        travel_to=data.travel_to,
        distance_km=Decimal(str(data.distance_km)) if data.distance_km else None,
        mileage_rate=Decimal(str(data.mileage_rate)) if data.mileage_rate else None,
        claim_title=data.claim_title,
        claim_description=data.claim_description,
        claim_period_from=datetime.strptime(data.claim_period_from, "%Y-%m-%d").date() if data.claim_period_from else None,
        claim_period_to=datetime.strptime(data.claim_period_to, "%Y-%m-%d").date() if data.claim_period_to else None,
        status='DRAFT',
        created_by_id=current_user.id
    )
    
    claim.add_audit_entry('CREATED', current_user.id, {'claim_title': data.claim_title})
    
    db.add(claim)
    db.flush()
    
    total_amount = Decimal('0')
    if data.items:
        for item_data in data.items:
            net_amount = Decimal(str(item_data.amount)) + Decimal(str(item_data.gst_amount))
            total_amount += net_amount
            
            item = StaffReimbursementClaimItem(
                claim_id=claim.id,
                main_category_id=item_data.main_category_id,
                sub_category_id=item_data.sub_category_id,
                expense_date=datetime.strptime(item_data.expense_date, "%Y-%m-%d").date(),
                description=item_data.description,
                vendor_name=item_data.vendor_name,
                amount=Decimal(str(item_data.amount)),
                gst_applicable=item_data.gst_applicable,
                gst_amount=Decimal(str(item_data.gst_amount)),
                net_amount=net_amount,
                bill_number=item_data.bill_number,
                bill_date=datetime.strptime(item_data.bill_date, "%Y-%m-%d").date() if item_data.bill_date else None,
                bill_path=item_data.bill_path,
                bill_remarks=item_data.bill_remarks,
                is_travel_expense=item_data.is_travel_expense,
                travel_mode=item_data.travel_mode,
                travel_from=item_data.travel_from,
                travel_to=item_data.travel_to,
                distance_km=Decimal(str(item_data.distance_km)) if item_data.distance_km else None
            )
            db.add(item)
    
    claim.total_amount = total_amount
    db.commit()
    db.refresh(claim)
    
    return {
        "success": True,
        "message": "Claim created successfully",
        "claim": claim.to_dict()
    }


@router.put("/claims/{claim_id}")
async def update_claim(
    claim_id: int,
    data: ClaimUpdate,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Update draft claim - DC Protocol enforced"""
    claim = db.query(StaffReimbursementClaim).filter_by(id=claim_id).first()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    validate_employee_company_access(current_user, claim.company_id)
    
    if claim.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own claims")
    
    if claim.status != 'DRAFT':
        raise HTTPException(status_code=400, detail="Only draft claims can be edited")
    
    update_fields = data.dict(exclude_unset=True)
    for key, value in update_fields.items():
        if key in ['claim_period_from', 'claim_period_to'] and value:
            value = datetime.strptime(value, "%Y-%m-%d").date()
        if key in ['distance_km', 'mileage_rate'] and value is not None:
            value = Decimal(str(value))
        setattr(claim, key, value)
    
    claim.add_audit_entry('UPDATED', current_user.id, {'fields': list(update_fields.keys())})
    db.commit()
    
    return {
        "success": True,
        "message": "Claim updated successfully",
        "claim": claim.to_dict()
    }


@router.post("/claims/{claim_id}/items")
async def add_claim_item(
    claim_id: int,
    data: ClaimItemCreate,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Add item to draft claim - DC Protocol enforced"""
    claim = db.query(StaffReimbursementClaim).filter_by(id=claim_id).first()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    validate_employee_company_access(current_user, claim.company_id)
    
    if claim.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own claims")
    
    if claim.status != 'DRAFT':
        raise HTTPException(status_code=400, detail="Only draft claims can be edited")
    
    net_amount = Decimal(str(data.amount)) + Decimal(str(data.gst_amount))
    
    item = StaffReimbursementClaimItem(
        claim_id=claim.id,
        main_category_id=data.main_category_id,
        sub_category_id=data.sub_category_id,
        expense_date=datetime.strptime(data.expense_date, "%Y-%m-%d").date(),
        description=data.description,
        vendor_name=data.vendor_name,
        amount=Decimal(str(data.amount)),
        gst_applicable=data.gst_applicable,
        gst_amount=Decimal(str(data.gst_amount)),
        net_amount=net_amount,
        bill_number=data.bill_number,
        bill_date=datetime.strptime(data.bill_date, "%Y-%m-%d").date() if data.bill_date else None,
        bill_path=data.bill_path,
        bill_remarks=data.bill_remarks,
        is_travel_expense=data.is_travel_expense,
        travel_mode=data.travel_mode,
        travel_from=data.travel_from,
        travel_to=data.travel_to,
        distance_km=Decimal(str(data.distance_km)) if data.distance_km else None
    )
    db.add(item)
    
    claim.total_amount = (claim.total_amount or Decimal('0')) + net_amount
    claim.add_audit_entry('ITEM_ADDED', current_user.id, {'description': data.description, 'amount': float(net_amount)})
    
    db.commit()
    db.refresh(item)
    
    return {
        "success": True,
        "message": "Item added successfully",
        "item": item.to_dict(),
        "claim_total": float(claim.total_amount)
    }


@router.delete("/claims/{claim_id}/items/{item_id}")
async def delete_claim_item(
    claim_id: int,
    item_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Delete item from draft claim - DC Protocol enforced"""
    claim = db.query(StaffReimbursementClaim).filter_by(id=claim_id).first()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    validate_employee_company_access(current_user, claim.company_id)
    
    if claim.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own claims")
    
    if claim.status != 'DRAFT':
        raise HTTPException(status_code=400, detail="Only draft claims can be edited")
    
    item = db.query(StaffReimbursementClaimItem).filter_by(id=item_id, claim_id=claim_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    claim.total_amount = (claim.total_amount or Decimal('0')) - (item.net_amount or Decimal('0'))
    claim.add_audit_entry('ITEM_DELETED', current_user.id, {'item_id': item_id, 'amount': float(item.net_amount or 0)})
    
    db.delete(item)
    db.commit()
    
    return {
        "success": True,
        "message": "Item deleted successfully",
        "claim_total": float(claim.total_amount)
    }


@router.post("/claims/{claim_id}/submit")
async def submit_claim(
    claim_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Submit claim for approval - DC Protocol enforced"""
    claim = db.query(StaffReimbursementClaim).options(
        joinedload(StaffReimbursementClaim.items)
    ).filter_by(id=claim_id).first()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    validate_employee_company_access(current_user, claim.company_id)
    
    if claim.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only submit your own claims")
    
    if claim.status != 'DRAFT':
        raise HTTPException(status_code=400, detail="Only draft claims can be submitted")
    
    if not claim.items or len(claim.items) == 0:
        raise HTTPException(status_code=400, detail="Claim must have at least one expense item")
    
    if (claim.total_amount or 0) <= 0:
        raise HTTPException(status_code=400, detail="Claim total must be greater than zero")
    
    claim.status = 'SUBMITTED'
    claim.submitted_at = get_indian_time()
    claim.add_audit_entry('SUBMITTED', current_user.id, {'total_amount': float(claim.total_amount)})
    
    db.commit()
    
    return {
        "success": True,
        "message": "Claim submitted for approval",
        "claim": claim.to_dict()
    }


@router.post("/claims/{claim_id}/withdraw")
async def withdraw_claim(
    claim_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Withdraw submitted claim (revert to draft) - DC Protocol enforced"""
    claim = db.query(StaffReimbursementClaim).filter_by(id=claim_id).first()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    validate_employee_company_access(current_user, claim.company_id)
    
    if claim.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only withdraw your own claims")
    
    if claim.status not in ['SUBMITTED']:
        raise HTTPException(status_code=400, detail="Only submitted claims can be withdrawn")
    
    claim.status = 'DRAFT'
    claim.submitted_at = None
    claim.add_audit_entry('WITHDRAWN', current_user.id, {})
    
    db.commit()
    
    return {
        "success": True,
        "message": "Claim withdrawn successfully",
        "claim": claim.to_dict()
    }


@router.get("/approval-queue")
async def get_approval_queue(
    company_id: int = Query(..., description="Company ID - DC Protocol"),
    approval_level: str = Query("manager", description="manager or finance"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get claims pending approval - DC Protocol enforced
    
    VGK4U (Supreme Admin) can see SUBMITTED claims on finance level for skip-level approval.
    """
    validate_employee_company_access(current_user, company_id)
    
    is_manager = current_user.role and current_user.role.role_code in ['manager', 'senior_manager', 'department_head']
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    is_finance = current_user.staff_type in ['VGK4U', 'VGK4U Supreme', 'EA', 'ACCOUNTS']
    is_supreme = current_user.staff_type in ['VGK4U', 'VGK4U Supreme']
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if approval_level == 'manager' and not (is_manager or is_finance):
    #     raise HTTPException(status_code=403, detail="Manager approval access required")
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if approval_level == 'finance' and not is_finance:
    #     raise HTTPException(status_code=403, detail="Finance approval access required")
    
    # VGK4U (Supreme) can see SUBMITTED + MANAGER_APPROVED on finance level (skip-level capability)
    if approval_level == 'finance' and is_supreme:
        query = db.query(StaffReimbursementClaim).filter(
            StaffReimbursementClaim.company_id == company_id,
            StaffReimbursementClaim.status.in_(['SUBMITTED', 'MANAGER_APPROVED'])
        )
    else:
        status_filter = 'SUBMITTED' if approval_level == 'manager' else 'MANAGER_APPROVED'
        query = db.query(StaffReimbursementClaim).filter(
            StaffReimbursementClaim.company_id == company_id,
            StaffReimbursementClaim.status == status_filter
        )
    
    if approval_level == 'manager' and not is_finance:
        query = query.filter(StaffReimbursementClaim.employee_id != current_user.id)
    
    total = query.count()
    claims = query.order_by(StaffReimbursementClaim.submitted_at.asc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "success": True,
        "claims": [c.to_dict() for c in claims],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "approval_level": approval_level,
        "is_supreme": is_supreme,
        "can_skip_level": is_supreme
    }


@router.post("/claims/{claim_id}/manager-approve")
async def manager_approve_claim(
    claim_id: int,
    data: ApprovalAction,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Manager approval - Level 1 - DC Protocol enforced"""
    is_manager = current_user.role and current_user.role.role_code in ['manager', 'senior_manager', 'department_head']
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    is_finance = current_user.staff_type in ['VGK4U', 'VGK4U Supreme', 'EA', 'ACCOUNTS']
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not (is_manager or is_finance):
    #     raise HTTPException(status_code=403, detail="Manager approval access required")
    
    claim = db.query(StaffReimbursementClaim).filter_by(id=claim_id).first()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    validate_employee_company_access(current_user, claim.company_id)
    
    if claim.status != 'SUBMITTED':
        raise HTTPException(status_code=400, detail="Claim is not in submitted status")
    
    if claim.employee_id == current_user.id and not is_finance:
        raise HTTPException(status_code=400, detail="You cannot approve your own claim")
    
    claim.status = 'MANAGER_APPROVED'
    claim.manager_approved_by_id = current_user.id
    claim.manager_approved_at = get_indian_time()
    claim.manager_remarks = data.remarks
    claim.add_audit_entry('MANAGER_APPROVED', current_user.id, {'remarks': data.remarks})
    
    db.commit()
    
    return {
        "success": True,
        "message": "Claim approved by manager. Pending finance approval.",
        "claim": claim.to_dict()
    }


@router.post("/claims/{claim_id}/finance-approve")
async def finance_approve_claim(
    claim_id: int,
    data: SettlementAction,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Finance approval with settlement and full SFMS ledger integration.
    Level 2 - DC Protocol enforced
    
    VGK4U (Supreme Admin) can skip manager level and directly approve SUBMITTED claims.
    
    Creates:
    - ExpenseEntry record
    - PartyLedger DEBIT entry for employee
    - Updates BalanceSheetSummary
    """
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    is_finance = current_user.staff_type in ['VGK4U', 'VGK4U Supreme', 'EA', 'ACCOUNTS']
    is_supreme = current_user.staff_type in ['VGK4U', 'VGK4U Supreme']
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not is_finance:
    #     raise HTTPException(status_code=403, detail="Finance approval access required")
    
    claim = db.query(StaffReimbursementClaim).options(
        joinedload(StaffReimbursementClaim.items),
        joinedload(StaffReimbursementClaim.employee)
    ).filter_by(id=claim_id).first()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    validate_employee_company_access(current_user, claim.company_id)
    
    # VGK4U (Supreme) can skip manager level - approve directly from SUBMITTED
    if is_supreme and claim.status == 'SUBMITTED':
        # Auto-set manager approval fields for skip-level
        claim.manager_approved_by_id = current_user.id
        claim.manager_approved_at = get_indian_time()
        claim.manager_remarks = "Skip-level approval by VGK4U"
        claim.add_audit_entry('MANAGER_APPROVED', current_user.id, {'skip_level': True, 'remarks': 'VGK4U skip-level approval'})
    elif claim.status != 'MANAGER_APPROVED':
        raise HTTPException(status_code=400, detail="Claim must be manager-approved first")
    
    try:
        accounting_service = ReimbursementAccountingService(db)
        result = accounting_service.settle_claim_with_accounting(
            claim=claim,
            settled_by_id=current_user.id,
            settlement_mode=data.settlement_mode,
            settlement_reference=data.settlement_reference,
            fund_allocation_id=data.fund_allocation_id,
            remarks=data.remarks
        )
        
        claim.finance_approved_by_id = current_user.id
        claim.finance_approved_at = get_indian_time()
        db.commit()
        
        return {
            "success": True,
            "message": "Claim approved, settled, and ledger entries created",
            "claim": claim.to_dict(),
            "accounting": {
                "expense_entry_id": result.get('expense_entry_id'),
                "ledger_entry_id": result.get('ledger_entry_id')
            }
        }
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Settlement failed: {str(e)}")


@router.post("/claims/{claim_id}/reject")
async def reject_claim(
    claim_id: int,
    data: RejectionAction,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Reject claim at any approval stage - DC Protocol enforced"""
    is_manager = current_user.role and current_user.role.role_code in ['manager', 'senior_manager', 'department_head']
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    is_finance = current_user.staff_type in ['VGK4U', 'VGK4U Supreme', 'EA', 'ACCOUNTS']
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not (is_manager or is_finance):
    #     raise HTTPException(status_code=403, detail="Approval access required")
    
    claim = db.query(StaffReimbursementClaim).filter_by(id=claim_id).first()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    validate_employee_company_access(current_user, claim.company_id)
    
    if claim.status not in ['SUBMITTED', 'MANAGER_APPROVED']:
        raise HTTPException(status_code=400, detail="Claim cannot be rejected in current status")
    
    rejection_stage = 'MANAGER' if claim.status == 'SUBMITTED' else 'FINANCE'
    
    claim.status = 'REJECTED'
    claim.rejected_by_id = current_user.id
    claim.rejected_at = get_indian_time()
    claim.rejection_reason = data.reason
    claim.rejection_stage = rejection_stage
    claim.add_audit_entry('REJECTED', current_user.id, {'reason': data.reason, 'stage': rejection_stage})
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Claim rejected at {rejection_stage.lower()} level",
        "claim": claim.to_dict()
    }


@router.get("/summary/company/{company_id}")
async def get_company_claims_summary(
    company_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Get company-wise claims summary - DC Protocol enforced"""
    validate_employee_company_access(current_user, company_id)
    
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    is_finance = current_user.staff_type in ['VGK4U', 'VGK4U Supreme', 'EA', 'ACCOUNTS']
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not is_finance:
    #     raise HTTPException(status_code=403, detail="Finance access required for company summary")
    
    status_counts = db.query(
        StaffReimbursementClaim.status,
        func.count(StaffReimbursementClaim.id),
        func.sum(StaffReimbursementClaim.total_amount)
    ).filter(
        StaffReimbursementClaim.company_id == company_id
    ).group_by(StaffReimbursementClaim.status).all()
    
    summary = {}
    total_claims = 0
    total_amount = Decimal('0')
    
    for status, count, amount in status_counts:
        summary[status] = {
            'count': count,
            'amount': float(amount or 0)
        }
        total_claims += count
        total_amount += amount or Decimal('0')
    
    return {
        "success": True,
        "company_id": company_id,
        "summary": summary,
        "total_claims": total_claims,
        "total_amount": float(total_amount)
    }


@router.get("/my-assigned-companies")
async def get_my_assigned_companies(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Get companies assigned to current employee - DC Protocol with VGK4U bypass"""
    # VGK4U (Supreme Admin) gets access to all companies
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    if current_user.staff_type in ['VGK4U', 'VGK4U Supreme']:
        companies = db.query(AssociatedCompany).filter(
            AssociatedCompany.is_active == True
        ).all()
    else:
        company_ids = []
        
        if current_user.base_company_id:
            company_ids.append(current_user.base_company_id)
        
        if current_user.data_companies:
            company_ids.extend(current_user.data_companies)
        
        company_ids = list(set(company_ids))
        
        if not company_ids:
            return {"success": True, "companies": []}
        
        companies = db.query(AssociatedCompany).filter(
            AssociatedCompany.id.in_(company_ids),
            AssociatedCompany.is_active == True
        ).all()
    
    return {
        "success": True,
        "companies": [{
            'id': c.id,
            'company_code': c.company_code,
            'company_name': c.company_name
        } for c in companies]
    }


@router.get("/expense-categories")
async def get_expense_categories(
    db: Session = Depends(get_db)
):
    """Get all expense categories for claim creation"""
    main_categories = db.query(ExpenseMainCategory).filter(
        ExpenseMainCategory.is_active == True
    ).all()
    
    result = []
    for main_cat in main_categories:
        sub_cats = db.query(ExpenseSubCategory).filter(
            ExpenseSubCategory.main_category_id == main_cat.id,
            ExpenseSubCategory.is_active == True
        ).all()
        
        result.append({
            'id': main_cat.id,
            'name': main_cat.name,
            'description': main_cat.description,
            'sub_categories': [{
                'id': sc.id,
                'name': sc.name,
                'description': sc.description
            } for sc in sub_cats]
        })
    
    return {
        "success": True,
        "categories": result
    }


@router.get("/fund-allocations")
async def get_fund_allocations_for_settlement(
    company_id: int = Query(...),
    status: str = Query('CONFIRMED,PARTIALLY_SETTLED'),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get available fund allocations for reimbursement settlement
    DC Protocol: company_id filtering enforced
    """
    validate_employee_company_access(current_user, company_id)
    
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    is_finance = current_user.staff_type in ['VGK4U', 'VGK4U Supreme', 'EA', 'ACCOUNTS']
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not is_finance:
    #     raise HTTPException(status_code=403, detail="Finance access required")
    
    status_list = [s.strip() for s in status.split(',')]
    
    allocations = db.query(FundAllocation).filter(
        FundAllocation.company_id == company_id,
        FundAllocation.status.in_(status_list),
        FundAllocation.balance_remaining > 0
    ).order_by(desc(FundAllocation.allocation_date)).limit(50).all()
    
    return {
        "success": True,
        "allocations": [{
            'id': a.id,
            'allocation_number': a.allocation_number,
            'amount': float(a.amount),
            'balance_remaining': float(a.balance_remaining),
            'total_expensed': float(a.total_expensed or 0),
            'purpose': a.purpose,
            'status': a.status,
            'allocation_date': a.allocation_date.isoformat() if a.allocation_date else None
        } for a in allocations]
    }


@router.get("/my-journeys")
async def get_my_journeys_for_claim(
    company_id: int = Query(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Get employee's completed journeys that can be linked to claims - DC Protocol enforced"""
    validate_employee_company_access(current_user, company_id)
    
    journeys = db.query(StaffJourney).filter(
        StaffJourney.employee_id == current_user.id,
        StaffJourney.status == 'COMPLETED'
    ).order_by(desc(StaffJourney.start_time)).limit(50).all()
    
    return {
        "success": True,
        "journeys": [{
            'id': j.id,
            'start_time': j.start_time.isoformat() if j.start_time else None,
            'end_time': j.end_time.isoformat() if j.end_time else None,
            'start_location': j.start_location,
            'end_location': j.end_location,
            'purpose': j.purpose.value if j.purpose else None,
            'distance_km': float(j.total_distance_km) if j.total_distance_km else None
        } for j in journeys]
    }


@router.post("/claims/{claim_id}/items/{item_id}/upload-bill")
async def upload_bill_attachment(
    claim_id: int,
    item_id: int,
    file: UploadFile = File(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Upload bill/receipt attachment for a claim item
    DC Protocol: Universal Upload System with 5MB limit, auto-compression
    WVV Protocol: Staff authentication, ownership validation
    
    Dec 19, 2025: Initial implementation
    """
    claim = db.query(StaffReimbursementClaim).filter_by(id=claim_id).first()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    validate_employee_company_access(current_user, claim.company_id)
    
    if claim.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only upload bills for your own claims")
    
    if claim.status != 'DRAFT':
        raise HTTPException(status_code=400, detail="Can only upload bills for draft claims")
    
    item = db.query(StaffReimbursementClaimItem).filter_by(id=item_id, claim_id=claim_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Claim item not found")
    
    file_content = await file.read()
    file_size = len(file_content)
    await file.seek(0)
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    
    MAX_FILE_SIZE = 5 * 1024 * 1024
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size ({round(file_size/1024/1024, 2)}MB) exceeds maximum (5MB)"
        )
    
    allowed_types = {'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 
                     'application/pdf'}
    content_type = file.content_type or 'application/octet-stream'
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{content_type}' not allowed. Accepted: JPG, PNG, GIF, WebP, PDF"
        )
    
    try:
        upload_result = await UniversalUploadService.handle_upload(
            file=file,
            table_name='staff_reimbursement_claim_items',
            record_id=item.id,
            uploaded_by_id=current_user.id,
            uploaded_by_type='staff',
            storage_dir='reimbursement_bills',
            db=db,
            defer_scheduler=True
        )
        
        item.bill_path = upload_result['file_path']
        claim.add_audit_entry('BILL_UPLOADED', current_user.id, {
            'item_id': item.id,
            'file_name': upload_result['original_filename'],
            'file_size': upload_result['file_size']
        })
        
        db.commit()
        
        return {
            "success": True,
            "message": "Bill uploaded successfully",
            "file_path": upload_result['file_path'],
            "file_name": upload_result['file_name'],
            "original_filename": upload_result['original_filename']
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/ledger/company/{company_id}")
async def get_company_expense_ledger(
    company_id: int,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get company expense ledger summary - DC Protocol enforced
    Returns breakdown by category and employee
    """
    validate_employee_company_access(current_user, company_id)
    
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    is_finance = current_user.staff_type in ['VGK4U', 'VGK4U Supreme', 'EA', 'ACCOUNTS']
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not is_finance:
    #     raise HTTPException(status_code=403, detail="Finance access required for ledger view")
    
    accounting_service = ReimbursementAccountingService(db)
    summary = accounting_service.get_company_expense_summary(
        company_id=company_id,
        from_date=from_date,
        to_date=to_date
    )
    
    return {
        "success": True,
        **summary
    }


@router.get("/ledger/employee/{employee_id}")
async def get_employee_expense_ledger(
    employee_id: int,
    company_id: int = Query(...),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get employee expense ledger - DC Protocol enforced
    Returns all reimbursement ledger entries for an employee
    """
    validate_employee_company_access(current_user, company_id)
    
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    is_finance = current_user.staff_type in ['VGK4U', 'VGK4U Supreme', 'EA', 'ACCOUNTS']
    is_self = current_user.id == employee_id
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not (is_finance or is_self):
    #     raise HTTPException(status_code=403, detail="Access denied")
    
    accounting_service = ReimbursementAccountingService(db)
    ledger = accounting_service.get_employee_expense_ledger(
        company_id=company_id,
        employee_id=employee_id,
        from_date=from_date,
        to_date=to_date
    )
    
    return {
        "success": True,
        **ledger
    }


@router.get("/ledger/my-payouts")
async def get_my_reimbursement_payouts(
    company_id: Optional[int] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get current employee's reimbursement payout history - DC Protocol enforced
    """
    target_company = company_id or current_user.base_company_id
    
    if not target_company:
        return {"success": True, "entries": [], "total_count": 0, "total_paid": 0}
    
    validate_employee_company_access(current_user, target_company)
    
    accounting_service = ReimbursementAccountingService(db)
    ledger = accounting_service.get_employee_expense_ledger(
        company_id=target_company,
        employee_id=current_user.id,
        from_date=from_date,
        to_date=to_date
    )
    
    return {
        "success": True,
        **ledger
    }
