"""
Bank Details & KYC Admin Approval Endpoints

DC Protocol Feb 2026: 2-Step Staff-Only Workflow
- Step 1: Staff with page access VALIDATES (Pending → Staff Validated)
- Step 2: Accounts/VGK Supreme APPROVES (Staff Validated → Approved)

Legacy Admin workflow preserved for backward compatibility but deprecated.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, extract
from typing import Optional, List
from datetime import datetime, date

from app.core.database import get_db
from app.core.security import (
    get_current_user, 
    get_current_user_hybrid, 
    get_current_admin_user, 
    get_current_super_admin_user, 
    get_current_rvz_user_hybrid,
    require_staff_accounts_or_vgk,
    require_staff_with_page_access
)
from app.models.user import User
from app.models.kyc_document import KYCDocument, BankDetailsApproval
from app.models.staff_accounts import OfficialPartner
from app.core.audit import AuditLogger
from pydantic import BaseModel

router = APIRouter()

# Pydantic models
class BankDetailsSubmitRequest(BaseModel):
    """Bank details submission by user"""
    bank_account_number: str
    bank_ifsc_code: str
    bank_account_holder: str
    bank_name: Optional[str] = None
    bank_branch_name: Optional[str] = None
    upi_id: Optional[str] = None

class KYCApprovalRequest(BaseModel):
    """KYC approval/rejection"""
    document_id: int
    action: str  # 'verify', 'approve', or 'reject'
    rejection_reason: Optional[str] = None

class BankApprovalRequest(BaseModel):
    """Bank approval"""
    user_id: str
    action: str  # 'approve' or 'reject'
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None

# User endpoints
@router.post("/bank-details/submit")
async def submit_bank_details(
    bank_data: BankDetailsSubmitRequest,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
):
    """Submit bank details for approval"""
    
    # Check if already exists
    existing = db.query(BankDetailsApproval).filter(
        BankDetailsApproval.user_id == current_user.id
    ).first()
    
    if existing and existing.status == 'Approved':
        raise HTTPException(
            status_code=400,
            detail="Bank details already approved. Contact admin for changes."
        )
    
    if existing:
        # Update existing submission
        existing.bank_account_number = bank_data.bank_account_number
        existing.bank_ifsc_code = bank_data.bank_ifsc_code
        existing.bank_account_holder = bank_data.bank_account_holder
        existing.bank_name = bank_data.bank_name
        existing.bank_branch_name = bank_data.bank_branch_name
        existing.upi_id = bank_data.upi_id
        existing.status = 'Pending'
        existing.submitted_at = datetime.now()
        existing.rejection_reason = None
    else:
        # Create new submission
        new_bank = BankDetailsApproval(
            user_id=current_user.id,
            bank_account_number=bank_data.bank_account_number,
            bank_ifsc_code=bank_data.bank_ifsc_code,
            bank_account_holder=bank_data.bank_account_holder,
            bank_name=bank_data.bank_name,
            bank_branch_name=bank_data.bank_branch_name,
            upi_id=bank_data.upi_id,
            status='Pending'
        )
        db.add(new_bank)
    
    db.commit()
    
    return {
        "success": True,
        "message": "Bank details submitted for approval",
        "status": "Pending"
    }

@router.get("/bank-details/status")
async def get_bank_details_status(
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
):
    """Get bank details approval status"""
    
    bank_approval = db.query(BankDetailsApproval).filter(
        BankDetailsApproval.user_id == current_user.id
    ).first()
    
    if not bank_approval:
        return {
            "status": "Not Submitted",
            "message": "No bank details submitted yet"
        }
    
    return {
        "status": bank_approval.status,
        "submitted_at": bank_approval.submitted_at.isoformat() if bank_approval.submitted_at else None,
        "bank_account_number": bank_approval.bank_account_number,
        "bank_ifsc_code": bank_approval.bank_ifsc_code,
        "bank_account_holder": bank_approval.bank_account_holder,
        "rejection_reason": bank_approval.rejection_reason,
        "super_admin_approved_at": bank_approval.super_admin_approved_at.isoformat() if bank_approval.super_admin_approved_at else None,
        "finance_admin_approved_at": bank_approval.finance_admin_approved_at.isoformat() if bank_approval.finance_admin_approved_at else None
    }

# Admin endpoints
@router.get("/admin/kyc-pending")
async def get_pending_kyc_documents(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    current_user = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Get pending KYC documents for admin review (paginated for performance)"""
    
    # DC Protocol: Single source = kyc_document table
    # Get total count first (for pagination UI)
    total_count = db.query(KYCDocument).filter(
        KYCDocument.status == 'Pending'
    ).count()
    
    pending_docs = db.query(KYCDocument).filter(
        KYCDocument.status == 'Pending'
    ).order_by(KYCDocument.uploaded_at.desc()).offset(skip).limit(limit).all()
    
    # Group by user
    user_docs = {}
    for doc in pending_docs:
        if doc.owner_id not in user_docs:
            user = db.query(User).filter(User.id == doc.owner_id).first()
            user_docs[doc.owner_id] = {
                "user_id": doc.owner_id,
                "user_name": user.name if user else "Unknown",
                "documents": []
            }
        
        user_docs[doc.owner_id]["documents"].append({
            "id": doc.id,
            "document_type": doc.document_type,
            "file_name": doc.file_name,
            "file_path": doc.file_path,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
        })
    
    return {
        "total_count": total_count,
        "pending_count": len(pending_docs),
        "skip": skip,
        "limit": limit,
        "has_more": (skip + len(pending_docs)) < total_count,
        "users": list(user_docs.values())
    }

@router.post("/admin/kyc-approve")
async def approve_kyc_document(
    approval_data: KYCApprovalRequest,
    current_user = Depends(get_current_rvz_user_hybrid),  # DC Protocol Feb 2026: Staff Portal access
    db: Session = Depends(get_db)
):
    """Admin/Super Admin validate KYC document (Step 1 of 3-step approval)"""
    
    doc = db.query(KYCDocument).filter(KYCDocument.id == approval_data.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if approval_data.action in ['verify', 'approve', 'validate']:
        # Admin or Super Admin validates the document (Step 1)
        doc.reviewed_by_id = current_user.id
        doc.reviewed_at = datetime.now()
        doc.status = 'Validated by Admin'
    
    elif approval_data.action == 'reject':
        doc.rejected_by = current_user.id
        doc.rejected_at = datetime.now()
        doc.rejection_reason = approval_data.rejection_reason
        doc.status = 'Rejected'
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Document {approval_data.action}d successfully - awaiting Finance Admin approval",
        "document_id": doc.id,
        "status": doc.status
    }

@router.get("/admin/kyc-validated")
async def get_validated_kyc_documents(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
):
    """Get validated KYC documents awaiting Finance Admin approval (paginated for performance)"""
    
    if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) != 'Finance Admin':
        raise HTTPException(status_code=403, detail="Only Finance Admin can access this endpoint")
    
    # DC Protocol: Single source = kyc_document table
    total_count = db.query(KYCDocument).filter(
        KYCDocument.status == 'Validated by Admin'
    ).count()
    
    validated_docs = db.query(KYCDocument).filter(
        KYCDocument.status == 'Validated by Admin'
    ).order_by(KYCDocument.reviewed_at.desc()).offset(skip).limit(limit).all()
    
    # Group by user
    user_docs = {}
    for doc in validated_docs:
        if doc.user_id not in user_docs:
            user = db.query(User).filter(User.id == doc.user_id).first()
            user_docs[doc.user_id] = {
                "user_id": doc.user_id,
                "user_name": user.name if user else "Unknown",
                "user_kyc_status": user.kyc_status if user else "Unknown",
                "documents": []
            }
        
        validator = db.query(User).filter(User.id == doc.reviewed_by_id).first()
        user_docs[doc.user_id]["documents"].append({
            "id": doc.id,
            "document_type": doc.document_type,
            "file_name": doc.file_name,
            "file_path": doc.file_path,
            "validated_at": doc.reviewed_at.isoformat() if doc.reviewed_at else None,
            "validated_by": validator.name if validator else "Unknown"
        })
    
    return {
        "success": True,
        "total_count": total_count,
        "validated_count": len(validated_docs),
        "skip": skip,
        "limit": limit,
        "has_more": (skip + len(validated_docs)) < total_count,
        "users": list(user_docs.values())
    }

@router.post("/admin/kyc-approve-finance")
async def finance_admin_approve_kyc(
    approval_data: KYCApprovalRequest,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
):
    """Finance Admin final approval for KYC document (Step 2 of 3-step approval)"""
    
    if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) != 'Finance Admin':
        raise HTTPException(status_code=403, detail="Only Finance Admin can give final approval")
    
    doc = db.query(KYCDocument).filter(KYCDocument.id == approval_data.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.status != 'Validated by Admin':
        raise HTTPException(status_code=400, detail="Document must be validated by Admin/Super Admin first")
    
    if approval_data.action == 'approve':
        # Finance Admin gives final approval
        doc.approved_by_finance_admin = current_user.id
        doc.finance_admin_approved_at = datetime.now()
        doc.finance_admin_notes = approval_data.rejection_reason if approval_data.rejection_reason else None
        doc.status = 'Approved'
        
        # Check if all required documents are approved for this user
        all_user_docs = db.query(KYCDocument).filter(
            KYCDocument.user_id == doc.user_id
        ).all()
        
        required_docs = {'aadhaar_front', 'aadhaar_back', 'pan_card', 'passport_photo'}
        approved_docs = {d.document_type for d in all_user_docs if d.status == 'Approved'}
        
        if required_docs.issubset(approved_docs):
            # Update user's overall KYC status to Approved
            user = db.query(User).filter(User.id == doc.user_id).first()
            if user:
                previous_kyc_status = user.kyc_status
                user.kyc_status = 'Approved'
                
                # 🔥 REAL-TIME WALLET SYNC: Trigger immediate sync if KYC just got approved
                kyc_newly_approved = (previous_kyc_status != 'Approved' and user.kyc_status == 'Approved')
                
                if kyc_newly_approved:
                    # Check if both KYC and Bank are approved for wallet sync
                    if user.kyc_status == 'Approved' and user.bank_details_status == 'Approved':
                        # Trigger real-time wallet sync (DC Protocol Phase 1.6)
                        from app.services.wallet_sync_service import WalletSyncService
                        from app.services.wallet_balance_service import get_earning_wallet
                        from decimal import Decimal
                        import logging
                        
                        logger = logging.getLogger(__name__)
                        wallet_service = WalletSyncService(db)
                        
                        # Get earning balance from materialized view (computed value)
                        earning_balance = get_earning_wallet(db, str(user.id))
                        
                        # Only sync if user has minimum balance (₹1,000)
                        if earning_balance >= wallet_service.MINIMUM_TRANSFER_AMOUNT:
                            logger.warning(f"🔥 REAL-TIME WALLET SYNC triggered for {user.id} (KYC Document Approval) - Earning wallet: ₹{earning_balance}")
                            
                            sync_result = wallet_service.sync_user_wallet_realtime(user)
                            
                            if sync_result['status'] == 'transferred':
                                logger.warning(f"✅ REAL-TIME SYNC SUCCESS: {user.id} - Transferred ₹{sync_result['amount']} to withdrawable wallet")
                            else:
                                logger.warning(f"⚠️ REAL-TIME SYNC RESULT: {user.id} - Status: {sync_result['status']}, Reason: {sync_result.get('reason', 'N/A')}")
                        else:
                            logger.info(f"ℹ️ REAL-TIME SYNC SKIPPED: {user.id} - Earning balance ₹{earning_balance} below minimum ₹{wallet_service.MINIMUM_TRANSFER_AMOUNT}")
    
    elif approval_data.action == 'reject':
        doc.rejected_by = current_user.id
        doc.rejected_at = datetime.now()
        doc.rejection_reason = approval_data.rejection_reason
        doc.status = 'Rejected'
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Document {approval_data.action}d by Finance Admin successfully",
        "document_id": doc.id,
        "status": doc.status
    }

@router.get("/admin/bank-pending")
async def get_pending_bank_details(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    current_user = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Get pending bank details for Admin/Super Admin review (paginated for performance)"""
    
    # DC Protocol: Single source = bank_details_approval table
    total_count = db.query(BankDetailsApproval).filter(
        BankDetailsApproval.status == 'Pending'
    ).count()
    
    pending_banks = db.query(BankDetailsApproval).filter(
        BankDetailsApproval.status == 'Pending'
    ).order_by(BankDetailsApproval.submitted_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "total_count": total_count,
        "pending_count": len(pending_banks),
        "skip": skip,
        "limit": limit,
        "has_more": (skip + len(pending_banks)) < total_count,
        "submissions": [
            {
                "user_id": bank.user_id,
                "user_name": db.query(User.name).filter(User.id == bank.user_id).scalar(),
                "bank_account_number": bank.bank_account_number,
                "bank_ifsc_code": bank.bank_ifsc_code,
                "bank_account_holder": bank.bank_account_holder,
                "bank_name": bank.bank_name,
                "submitted_at": bank.submitted_at.isoformat() if bank.submitted_at else None
            }
            for bank in pending_banks
        ]
    }

@router.post("/admin/bank-approve-super")
async def super_admin_approve_bank(
    approval_data: BankApprovalRequest,
    current_user: User = Depends(get_current_super_admin_user),
    db: Session = Depends(get_db)
):
    """Super Admin approve bank details (first approval)"""
    
    bank = db.query(BankDetailsApproval).filter(
        BankDetailsApproval.user_id == approval_data.user_id
    ).first()
    
    if not bank:
        raise HTTPException(status_code=404, detail="Bank details not found")
    
    if approval_data.action == 'approve':
        bank.approved_by_super_admin = current_user.id
        bank.super_admin_approved_at = datetime.now()
        bank.super_admin_notes = approval_data.notes
        bank.status = 'Approved by Super Admin'
    
    elif approval_data.action == 'reject':
        bank.rejected_by = current_user.id
        bank.rejected_at = datetime.now()
        bank.rejection_reason = approval_data.rejection_reason
        bank.status = 'Rejected'
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Bank details {approval_data.action}d by Super Admin",
        "user_id": bank.user_id,
        "status": bank.status
    }

@router.post("/admin/bank-approve-finance")
async def finance_admin_approve_bank(
    approval_data: BankApprovalRequest,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
):
    """Finance Admin final approval (second approval)"""
    
    if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) != 'Finance Admin':
        raise HTTPException(status_code=403, detail="Only Finance Admin can give final approval")
    
    bank = db.query(BankDetailsApproval).filter(
        BankDetailsApproval.user_id == approval_data.user_id
    ).first()
    
    if not bank:
        raise HTTPException(status_code=404, detail="Bank details not found")
    
    if bank.status != 'Approved by Super Admin':
        raise HTTPException(status_code=400, detail="Super Admin approval required first")
    
    if approval_data.action == 'approve':
        bank.approved_by_finance_admin = current_user.id
        bank.finance_admin_approved_at = datetime.now()
        bank.finance_admin_notes = approval_data.notes
        bank.status = 'Approved'
        
        # Update user bank details
        user = db.query(User).filter(User.id == bank.user_id).first()
        if user:
            previous_bank_status = user.bank_details_status
            
            user.bank_account_number = bank.bank_account_number
            user.bank_ifsc_code = bank.bank_ifsc_code
            user.bank_account_holder = bank.bank_account_holder
            user.bank_name = bank.bank_name
            user.bank_branch_name = bank.bank_branch_name
            user.upi_id = bank.upi_id
            user.bank_details_status = 'Approved'
            
            # 🔥 REAL-TIME WALLET SYNC: Trigger immediate sync if Bank just got approved
            bank_newly_approved = (previous_bank_status != 'Approved' and user.bank_details_status == 'Approved')
            
            if bank_newly_approved:
                # Check if both KYC and Bank are approved for wallet sync
                if user.kyc_status == 'Approved' and user.bank_details_status == 'Approved':
                    # Trigger real-time wallet sync (DC Protocol Phase 1.6)
                    from app.services.wallet_sync_service import WalletSyncService
                    from app.services.wallet_balance_service import get_earning_wallet
                    from decimal import Decimal
                    import logging
                    
                    logger = logging.getLogger(__name__)
                    wallet_service = WalletSyncService(db)
                    
                    # Get earning balance from materialized view (computed value)
                    earning_balance = get_earning_wallet(db, str(user.id))
                    
                    # Only sync if user has minimum balance (₹1,000)
                    if earning_balance >= wallet_service.MINIMUM_TRANSFER_AMOUNT:
                        logger.warning(f"🔥 REAL-TIME WALLET SYNC triggered for {user.id} (Bank Details Approval) - Earning wallet: ₹{earning_balance}")
                        
                        sync_result = wallet_service.sync_user_wallet_realtime(user)
                        
                        if sync_result['status'] == 'transferred':
                            logger.warning(f"✅ REAL-TIME SYNC SUCCESS: {user.id} - Transferred ₹{sync_result['amount']} to withdrawable wallet")
                        else:
                            logger.warning(f"⚠️ REAL-TIME SYNC RESULT: {user.id} - Status: {sync_result['status']}, Reason: {sync_result.get('reason', 'N/A')}")
                    else:
                        logger.info(f"ℹ️ REAL-TIME SYNC SKIPPED: {user.id} - Earning balance ₹{earning_balance} below minimum ₹{wallet_service.MINIMUM_TRANSFER_AMOUNT}")
    
    elif approval_data.action == 'reject':
        bank.rejected_by = current_user.id
        bank.rejected_at = datetime.now()
        bank.rejection_reason = approval_data.rejection_reason
        bank.status = 'Rejected'
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Bank details {approval_data.action}d by Finance Admin",
        "user_id": bank.user_id,
        "status": bank.status
    }

# Admin filter endpoints
@router.get("/admin/birthdays-today")
async def get_birthdays_today(
    dob_type: str = Query('actual', description='actual or certificate'),
    audience: Optional[str] = Query(None, description="Audience: mnr (default) | vgk4u | both", regex="^(mnr|vgk4u|both)$"),
    current_user = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Filter users with birthdays today.
    DC Protocol (Task #33): audience param is OPTIONAL — when omitted, the
    response is byte-identical to the pre-Task-#33 contract (no extra
    audience fields on rows or response). audience='vgk4u' queries
    OfficialPartner (category=VGK_TEAM) using dob_actual, scoped by company
    via PartnerCompanySegment.
    """
    from app.core.audience_resolver import vgk4u_birthday_users
    from app.core.audience_resolver import resolve_company_id_from_user

    today = date.today()
    users_payload = []
    explicit = audience is not None
    eff = audience or 'mnr'
    company_id = resolve_company_id_from_user(current_user, db)

    if eff in ('mnr', 'both'):
        if dob_type == 'actual':
            mnr_users = db.query(User).filter(
                and_(
                    extract('month', User.actual_date_of_birth) == today.month,
                    extract('day', User.actual_date_of_birth) == today.day
                )
            ).all()
        else:
            mnr_users = db.query(User).filter(
                and_(
                    extract('month', User.certificate_date_of_birth) == today.month,
                    extract('day', User.certificate_date_of_birth) == today.day
                )
            ).all()
        for user in mnr_users:
            row = {
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "phone": user.phone_number,
                "dob": user.actual_date_of_birth.isoformat() if dob_type == 'actual' and user.actual_date_of_birth else user.certificate_date_of_birth.isoformat() if user.certificate_date_of_birth else None,
            }
            if explicit:
                row["audience"] = "mnr"
            users_payload.append(row)

    if eff in ('vgk4u', 'both'):
        dob_field = 'dob_actual' if dob_type == 'actual' else 'dob_document'
        partners = vgk4u_birthday_users(db, today, dob_field=dob_field, company_id=company_id)
        for p in partners:
            row = {
                "user_id": p.partner_code,
                "name": p.partner_name or " ".join(filter(None, [p.first_name, p.last_name])) or p.partner_code,
                "email": p.email,
                "phone": p.phone,
                "dob": (p.dob_actual.isoformat() if dob_type == 'actual' and p.dob_actual else (p.dob_document.isoformat() if p.dob_document else None)),
            }
            if explicit:
                row["audience"] = "vgk4u"
            users_payload.append(row)

    response = {
        "date": today.isoformat(),
        "dob_type": dob_type,
        "count": len(users_payload),
        "users": users_payload,
    }
    if explicit:
        response["audience"] = eff
    return response

@router.get("/admin/birthdays-this-month")
async def get_birthdays_this_month(
    dob_type: str = Query('actual', description='actual or certificate'),
    audience: Optional[str] = Query(None, description="Audience: mnr (default) | vgk4u | both", regex="^(mnr|vgk4u|both)$"),
    current_user = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Filter users with birthdays this month.
    DC Protocol (Task #33): audience param is OPTIONAL — when omitted, the
    response is byte-identical to the pre-Task-#33 contract.
    """
    from app.core.audience_resolver import vgk4u_birthday_users_for_month
    from app.core.audience_resolver import resolve_company_id_from_user

    today = date.today()
    users_payload = []
    explicit = audience is not None
    eff = audience or 'mnr'
    company_id = resolve_company_id_from_user(current_user, db)

    if eff in ('mnr', 'both'):
        if dob_type == 'actual':
            mnr_users = db.query(User).filter(
                extract('month', User.actual_date_of_birth) == today.month
            ).all()
        else:
            mnr_users = db.query(User).filter(
                extract('month', User.certificate_date_of_birth) == today.month
            ).all()
        for user in mnr_users:
            row = {
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "phone": user.phone_number,
                "dob": user.actual_date_of_birth.isoformat() if dob_type == 'actual' and user.actual_date_of_birth else user.certificate_date_of_birth.isoformat() if user.certificate_date_of_birth else None,
            }
            if explicit:
                row["audience"] = "mnr"
            users_payload.append(row)

    if eff in ('vgk4u', 'both'):
        dob_field = 'dob_actual' if dob_type == 'actual' else 'dob_document'
        partners = vgk4u_birthday_users_for_month(db, today.month, dob_field=dob_field, company_id=company_id)
        for p in partners:
            row = {
                "user_id": p.partner_code,
                "name": p.partner_name or " ".join(filter(None, [p.first_name, p.last_name])) or p.partner_code,
                "email": p.email,
                "phone": p.phone,
                "dob": (p.dob_actual.isoformat() if dob_type == 'actual' and p.dob_actual else (p.dob_document.isoformat() if p.dob_document else None)),
            }
            if explicit:
                row["audience"] = "vgk4u"
            users_payload.append(row)

    response = {
        "month": today.strftime("%B %Y"),
        "dob_type": dob_type,
        "count": len(users_payload),
        "users": users_payload,
    }
    if explicit:
        response["audience"] = eff
    return response

@router.get("/admin/filter-kyc-status")
async def filter_by_kyc_status(
    status: str = Query('Pending', description='Pending, Verified, or Rejected'),
    current_user = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Filter users by KYC status"""
    
    users = db.query(User).filter(User.kyc_status == status).all()
    
    return {
        "status": status,
        "count": len(users),
        "users": [
            {
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "phone": user.phone_number,
                "kyc_status": user.kyc_status,
                "registration_date": user.registration_date.isoformat() if user.registration_date else None
            }
            for user in users
        ]
    }

@router.get("/admin/filter-bank-status")
async def filter_by_bank_status(
    status: str = Query('Pending', description='Pending, Approved, or Rejected'),
    current_user: User = Depends(get_current_super_admin_user),
    db: Session = Depends(get_db)
):
    """Filter users by bank details approval status"""
    
    bank_approvals = db.query(BankDetailsApproval).filter(
        BankDetailsApproval.status == status
    ).all()
    
    users_data = []
    for bank in bank_approvals:
        user = db.query(User).filter(User.id == bank.user_id).first()
        if user:
            users_data.append({
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "phone": user.phone_number,
                "bank_status": bank.status,
                "bank_account_number": bank.bank_account_number,
                "submitted_at": bank.submitted_at.isoformat() if bank.submitted_at else None
            })
    
    return {
        "status": status,
        "count": len(users_data),
        "users": users_data
    }


# ===== DC PROTOCOL FEB 2026: STAFF-ONLY 2-STEP KYC WORKFLOW =====
# Step 1: Staff Validates (Pending → Staff Validated)
# Step 2: Accounts/VGK Approves (Staff Validated → Approved)

@router.get("/staff/kyc-detail/{kyc_id}")
async def get_kyc_detail_for_staff(
    kyc_id: int,
    current_staff = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Get single KYC document details for Staff
    """
    try:
        doc = db.query(KYCDocument).filter(KYCDocument.id == kyc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="KYC document not found")
        
        user = db.query(User).filter(User.id == doc.owner_id).first()
        
        return {
            "success": True,
            "kyc": {
                "id": doc.id,
                "user_id": doc.owner_id,
                "document_type": doc.document_type,
                "file_path": doc.file_path,
                "status": doc.status,
                "uploaded_at": str(doc.uploaded_at) if doc.uploaded_at else None,
                "approved_at": str(doc.approved_at) if doc.approved_at else None,
                "rejection_reason": doc.rejection_reason
            },
            "employee": {
                "emp_code": user.unique_id if user else None,
                "full_name": user.name if user else "Unknown",
                "email": user.email if user else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class StaffKYCValidateRequest(BaseModel):
    """Staff KYC validation request - accepts kyc_ids or document_ids"""
    kyc_ids: Optional[List[int]] = None
    document_ids: Optional[List[int]] = None
    notes: Optional[str] = None
    
    @property
    def ids(self) -> List[int]:
        """Get the list of IDs, preferring kyc_ids if provided"""
        return self.kyc_ids or self.document_ids or []

class StaffKYCRejectRequest(BaseModel):
    """Staff KYC rejection request"""
    kyc_ids: List[int]
    reason: str

class StaffBankValidateRequest(BaseModel):
    """Staff Bank validation request"""
    user_ids: List[str]
    notes: Optional[str] = None


@router.get("/staff/kyc-pending")
async def get_pending_kyc_for_staff(
    status_filter: str = 'all',
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_staff = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Get KYC documents for Staff validation/approval
    
    Any Staff with page access can view and validate.
    Status values: Pending, Staff Validated, Approved, Rejected
    """
    try:
        # DC Protocol Mar 2026: Only return MNR user KYC records here (owner_id IS NOT NULL)
        # Partner KYC records (partner_id IS NOT NULL) are served by /staff/partner-kyc-pending
        query = db.query(KYCDocument).filter(KYCDocument.owner_id != None)
        
        if status_filter and status_filter.lower() != 'all':
            query = query.filter(KYCDocument.status == status_filter)
        
        query = query.order_by(KYCDocument.uploaded_at.desc())
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        documents = query.offset(skip).limit(limit).all()
        
        # Calculate stats (MNR user docs only)
        all_docs = db.query(KYCDocument).filter(KYCDocument.owner_id != None).all()
        stats = {
            'pending': sum(1 for d in all_docs if d.status == 'Pending'),
            'staff_validated': sum(1 for d in all_docs if d.status == 'Staff Validated'),
            'approved': sum(1 for d in all_docs if d.status == 'Approved'),
            'rejected': sum(1 for d in all_docs if d.status == 'Rejected')
        }
        
        # Group by user
        user_docs = {}
        for doc in documents:
            if doc.owner_id not in user_docs:
                user = db.query(User).filter(User.id == doc.owner_id).first()
                user_docs[doc.owner_id] = {
                    "user_id": doc.owner_id,
                    "user_name": user.name if user else "Unknown",
                    "documents": []
                }
            
            user_docs[doc.owner_id]["documents"].append({
                "id": doc.id,
                "document_type": doc.document_type,
                "file_name": doc.file_name,
                "file_path": doc.file_path,
                "status": doc.status,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "validated_by": doc.reviewed_by_id,
                "validated_at": doc.reviewed_at.isoformat() if doc.reviewed_at else None
            })
        
        return {
            "success": True,
            "total_count": total_count,
            "stats": stats,
            "skip": skip,
            "limit": limit,
            "users": list(user_docs.values())
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )


@router.post("/staff/kyc-validate")
async def staff_validate_kyc(
    request: StaffKYCValidateRequest = Body(...),
    current_staff = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Staff validates KYC documents
    
    Step 1 of 2-step workflow: Pending → Staff Validated
    Any Staff with page access can validate.
    """
    try:
        validated_count = 0
        staff_id = getattr(current_staff, 'emp_code', str(current_staff.id))
        
        for doc_id in request.ids:
            doc = db.query(KYCDocument).filter(
                KYCDocument.id == doc_id,
                KYCDocument.status == 'Pending'
            ).first()
            
            if doc:
                # DC Protocol Fix: Block phantom records (placeholder never updated by upload)
                if doc.file_path == 'pending_upload' or (doc.file_size is not None and doc.file_size <= 1):
                    logger.warning(f"[KYC VALIDATE] Blocked phantom doc id={doc.id}: file_path='{doc.file_path}', file_size={doc.file_size}")
                    continue
                doc.status = 'Staff Validated'
                doc.reviewed_by_id = staff_id
                doc.reviewed_at = datetime.now()
                validated_count += 1
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_staff,
            action='STAFF_VALIDATE_KYC',
            resource_type='KYCDocument',
            details={
                "validated_count": validated_count,
                "kyc_ids": request.ids,
                "staff_id": staff_id,
                "notes": request.notes
            }
        )
        
        return {
            "success": True,
            "message": f"Staff validated {validated_count} KYC document(s). Ready for Accounts/VGK approval.",
            "validated_count": validated_count,
            "workflow": "DC Protocol Feb 2026: 2-Step Staff Workflow"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )


@router.post("/staff/kyc-approve")
async def staff_approve_kyc(
    request: StaffKYCValidateRequest = Body(...),
    current_staff = Depends(require_staff_accounts_or_vgk),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Final KYC approval by Accounts/VGK Supreme
    
    Step 2 of 2-step workflow: Staff Validated → Approved
    
    Only Accounts department or VGK Supreme can approve.
    This action also updates user's overall KYC status if all required docs are approved.
    """
    try:
        approved_count = 0
        users_fully_approved = []
        staff_id = getattr(current_staff, 'emp_code', str(current_staff.id))
        
        for doc_id in request.ids:
            doc = db.query(KYCDocument).filter(
                KYCDocument.id == doc_id,
                KYCDocument.status == 'Staff Validated'
            ).first()
            
            if doc:
                # DC Protocol Fix: Block phantom records (placeholder never updated by upload)
                if doc.file_path == 'pending_upload' or (doc.file_size is not None and doc.file_size <= 1):
                    logger.warning(f"[KYC APPROVE] Blocked phantom doc id={doc.id}: file_path='{doc.file_path}', file_size={doc.file_size}")
                    continue
                doc.status = 'Approved'
                doc.approved_by_finance_admin = staff_id
                doc.finance_admin_approved_at = datetime.now()
                if request.notes:
                    doc.finance_admin_notes = request.notes
                approved_count += 1
                
                # DC Protocol Mar 2026: Handle partner KYC records (partner_id IS NOT NULL)
                if doc.partner_id:
                    all_partner_docs = db.query(KYCDocument).filter(
                        KYCDocument.partner_id == doc.partner_id
                    ).all()
                    required_docs = {'aadhar_front', 'aadhar_back', 'pan_card', 'passport_photo'}
                    approved_docs_set = {d.document_type for d in all_partner_docs if d.status == 'Approved'}
                    if required_docs.issubset(approved_docs_set):
                        partner_rec = db.query(OfficialPartner).filter(OfficialPartner.id == doc.partner_id).first()
                        if partner_rec and partner_rec.kyc_status != 'Approved':
                            partner_rec.kyc_status = 'Approved'
                            users_fully_approved.append(f"PARTNER_{partner_rec.id}")
                else:
                    # Check if all required documents are approved for this MNR user
                    all_user_docs = db.query(KYCDocument).filter(
                        KYCDocument.owner_id == doc.owner_id
                    ).all()
                    required_docs = {'aadhaar_front', 'aadhaar_back', 'pan_card', 'passport_photo'}
                    approved_docs = {d.document_type for d in all_user_docs if d.status == 'Approved'}
                    
                    if required_docs.issubset(approved_docs):
                        user = db.query(User).filter(User.id == doc.owner_id).first()
                        if user and user.kyc_status != 'Approved':
                            user.kyc_status = 'Approved'
                            users_fully_approved.append(user.id)
                            
                            # Trigger wallet sync if both KYC and Bank are approved
                            if user.bank_details_status == 'Approved':
                                from app.services.wallet_sync_service import WalletSyncService
                                from app.services.wallet_balance_service import get_earning_wallet
                                import logging
                                
                                logger = logging.getLogger(__name__)
                                wallet_service = WalletSyncService(db)
                                earning_balance = get_earning_wallet(db, str(user.id))
                                
                                if earning_balance >= wallet_service.MINIMUM_TRANSFER_AMOUNT:
                                    logger.warning(f"🔥 STAFF KYC APPROVAL: Triggering wallet sync for {user.id}")
                                    wallet_service.sync_user_wallet_realtime(user)
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_staff,
            action='STAFF_APPROVE_KYC',
            resource_type='KYCDocument',
            details={
                "approved_count": approved_count,
                "kyc_ids": request.ids,
                "staff_id": staff_id,
                "users_fully_approved": users_fully_approved
            }
        )
        
        return {
            "success": True,
            "message": f"Approved {approved_count} KYC document(s). {len(users_fully_approved)} user(s) now fully KYC approved.",
            "approved_count": approved_count,
            "users_fully_approved": users_fully_approved,
            "workflow": "DC Protocol Feb 2026: 2-Step Staff Workflow (Completed)"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )


@router.post("/staff/kyc-reject")
async def staff_reject_kyc(
    request: StaffKYCRejectRequest = Body(...),
    current_staff = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Reject KYC documents
    
    Any Staff with page access can reject documents.
    Accepts list of kyc_ids for bulk rejection.
    """
    try:
        staff_id = getattr(current_staff, 'emp_code', str(current_staff.id))
        rejected_count = 0
        
        for doc_id in request.kyc_ids:
            doc = db.query(KYCDocument).filter(KYCDocument.id == doc_id).first()
            if doc:
                doc.status = 'Rejected'
                doc.rejected_by = staff_id
                doc.rejected_at = datetime.now()
                doc.rejection_reason = request.reason
                rejected_count += 1
                # DC Protocol Mar 2026: Update partner KYC status on rejection
                if doc.partner_id:
                    partner_rec = db.query(OfficialPartner).filter(OfficialPartner.id == doc.partner_id).first()
                    if partner_rec and partner_rec.kyc_status not in ('Not Submitted',):
                        partner_rec.kyc_status = 'Rejected'
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_staff,
            action='STAFF_REJECT_KYC',
            resource_type='KYCDocument',
            details={
                "kyc_ids": request.kyc_ids,
                "staff_id": staff_id,
                "rejection_reason": request.reason,
                "rejected_count": rejected_count
            }
        )
        
        return {
            "success": True,
            "message": f"{rejected_count} KYC document(s) rejected",
            "rejected_count": rejected_count,
            "status": "Rejected"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )


# ===== STAFF BANK DETAILS 2-STEP WORKFLOW =====

@router.get("/staff/bank-pending")
async def get_pending_bank_for_staff(
    status_filter: str = 'all',
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_staff = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Get bank details for Staff validation/approval
    """
    try:
        query = db.query(BankDetailsApproval)
        
        if status_filter and status_filter.lower() != 'all':
            query = query.filter(BankDetailsApproval.status == status_filter)
        
        query = query.order_by(BankDetailsApproval.submitted_at.desc())
        
        total_count = query.count()
        submissions = query.offset(skip).limit(limit).all()
        
        # Calculate stats
        all_banks = db.query(BankDetailsApproval).all()
        stats = {
            'pending': sum(1 for b in all_banks if b.status == 'Pending'),
            'staff_validated': sum(1 for b in all_banks if b.status == 'Staff Validated'),
            'approved': sum(1 for b in all_banks if b.status == 'Approved'),
            'rejected': sum(1 for b in all_banks if b.status == 'Rejected')
        }
        
        return {
            "success": True,
            "total_count": total_count,
            "stats": stats,
            "submissions": [
                {
                    "user_id": bank.user_id,
                    "user_name": db.query(User.name).filter(User.id == bank.user_id).scalar(),
                    "bank_account_number": bank.bank_account_number,
                    "bank_ifsc_code": bank.bank_ifsc_code,
                    "bank_account_holder": bank.bank_account_holder,
                    "bank_name": bank.bank_name,
                    "status": bank.status,
                    "submitted_at": bank.submitted_at.isoformat() if bank.submitted_at else None,
                    "validated_by": bank.super_admin_approved_by,
                    "validated_at": bank.super_admin_approved_at.isoformat() if bank.super_admin_approved_at else None
                }
                for bank in submissions
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )


@router.post("/staff/bank-validate")
async def staff_validate_bank(
    request: StaffBankValidateRequest = Body(...),
    current_staff = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Staff validates bank details
    
    Step 1: Pending → Staff Validated
    """
    try:
        validated_count = 0
        staff_id = getattr(current_staff, 'emp_code', str(current_staff.id))
        
        for user_id in request.user_ids:
            bank = db.query(BankDetailsApproval).filter(
                BankDetailsApproval.user_id == user_id,
                BankDetailsApproval.status == 'Pending'
            ).first()
            
            if bank:
                bank.status = 'Staff Validated'
                bank.super_admin_approved_by = staff_id
                bank.super_admin_approved_at = datetime.now()
                if request.notes:
                    bank.super_admin_notes = request.notes
                validated_count += 1
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_staff,
            action='STAFF_VALIDATE_BANK',
            resource_type='BankDetailsApproval',
            details={
                "validated_count": validated_count,
                "user_ids": request.user_ids,
                "staff_id": staff_id
            }
        )
        
        return {
            "success": True,
            "message": f"Staff validated {validated_count} bank submission(s). Ready for Accounts/VGK approval.",
            "validated_count": validated_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )


@router.post("/staff/bank-approve")
async def staff_approve_bank(
    request: StaffBankValidateRequest = Body(...),
    current_staff = Depends(require_staff_accounts_or_vgk),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Final bank approval by Accounts/VGK Supreme
    
    Step 2: Staff Validated → Approved
    Also updates user's bank_details_status on the User table.
    """
    try:
        approved_count = 0
        staff_id = getattr(current_staff, 'emp_code', str(current_staff.id))
        
        for user_id in request.user_ids:
            bank = db.query(BankDetailsApproval).filter(
                BankDetailsApproval.user_id == user_id,
                BankDetailsApproval.status == 'Staff Validated'
            ).first()
            
            if bank:
                bank.status = 'Approved'
                bank.finance_admin_approved_by = staff_id
                bank.finance_admin_approved_at = datetime.now()
                if request.notes:
                    bank.finance_admin_notes = request.notes
                
                # Update user's bank details and status
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.bank_name = bank.bank_name
                    user.account_number = bank.bank_account_number
                    user.ifsc_code = bank.bank_ifsc_code
                    user.account_holder = bank.bank_account_holder
                    user.bank_details_status = 'Approved'
                    
                    # Trigger wallet sync if both KYC and Bank are now approved
                    if user.kyc_status == 'Approved':
                        from app.services.wallet_sync_service import WalletSyncService
                        from app.services.wallet_balance_service import get_earning_wallet
                        import logging
                        
                        logger = logging.getLogger(__name__)
                        wallet_service = WalletSyncService(db)
                        earning_balance = get_earning_wallet(db, str(user.id))
                        
                        if earning_balance >= wallet_service.MINIMUM_TRANSFER_AMOUNT:
                            logger.warning(f"🔥 STAFF BANK APPROVAL: Triggering wallet sync for {user.id}")
                            wallet_service.sync_user_wallet_realtime(user)
                
                approved_count += 1
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_staff,
            action='STAFF_APPROVE_BANK',
            resource_type='BankDetailsApproval',
            details={
                "approved_count": approved_count,
                "user_ids": request.user_ids,
                "staff_id": staff_id
            }
        )
        
        return {
            "success": True,
            "message": f"Approved {approved_count} bank submission(s).",
            "approved_count": approved_count,
            "workflow": "DC Protocol Feb 2026: 2-Step Staff Workflow (Completed)"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )


# ─── DC Protocol Mar 2026: Partner KYC Admin ─────────────────────────────────

@router.get("/staff/partner-kyc-pending")
async def get_pending_partner_kyc(
    status_filter: str = 'all',
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_staff = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """DC Protocol Mar 2026: List partner KYC records for staff approval queue.
    Returns VGK members and Official Partners who have uploaded KYC documents.
    The existing validate/approve/reject endpoints handle these records by doc_id."""
    try:
        query = db.query(KYCDocument).filter(KYCDocument.partner_id != None)

        if status_filter and status_filter.lower() != 'all':
            query = query.filter(KYCDocument.status == status_filter)

        query = query.order_by(KYCDocument.uploaded_at.desc())
        total_count = query.count()
        documents = query.offset(skip).limit(limit).all()

        all_partner_docs = db.query(KYCDocument).filter(KYCDocument.partner_id != None).all()
        stats = {
            'pending': sum(1 for d in all_partner_docs if d.status == 'Pending'),
            'staff_validated': sum(1 for d in all_partner_docs if d.status == 'Staff Validated'),
            'approved': sum(1 for d in all_partner_docs if d.status == 'Approved'),
            'rejected': sum(1 for d in all_partner_docs if d.status == 'Rejected')
        }

        partner_docs: dict = {}
        for doc in documents:
            pid = doc.partner_id
            if pid not in partner_docs:
                p = db.query(OfficialPartner).filter(OfficialPartner.id == pid).first()
                partner_docs[pid] = {
                    "partner_id": pid,
                    "partner_code": p.partner_code if p else "—",
                    "partner_name": p.partner_name if p else "Unknown",
                    "category": p.category if p else "—",
                    "kyc_status": (p.kyc_status or 'Not Submitted') if p else "—",
                    "documents": []
                }

            partner_docs[pid]["documents"].append({
                "id": doc.id,
                "document_type": doc.document_type,
                "file_name": doc.file_name,
                "original_filename": getattr(doc, 'original_filename', None) or doc.file_name,
                "file_path": doc.file_path,
                "status": doc.status,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "validated_by": doc.reviewed_by_id,
                "validated_at": doc.reviewed_at.isoformat() if doc.reviewed_at else None,
                "rejection_reason": doc.rejection_reason
            })

        return {
            "success": True,
            "total_count": total_count,
            "stats": stats,
            "skip": skip,
            "limit": limit,
            "partners": list(partner_docs.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
