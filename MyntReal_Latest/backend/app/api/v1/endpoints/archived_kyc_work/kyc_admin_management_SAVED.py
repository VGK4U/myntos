"""
KYC Document Management - Admin Viewing & Approval with Role-Based Access
DC Protocol: Database as single source of truth
Role-Based Masking: Admin (masked after approval), RVZ ID (no masking), Finance Admin (finance data only)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime
import os

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user, get_current_super_admin_user
from app.models.user import User
from app.models.kyc_document import KYCDocument
from pydantic import BaseModel

router = APIRouter()

# Pydantic Models
class DocumentApprovalRequest(BaseModel):
    """Document approval/rejection request"""
    document_id: int
    action: str  # 'approve' or 'reject'
    rejection_reason: Optional[str] = None
    admin_notes: Optional[str] = None

def mask_sensitive_data(value: Optional[str], mask_type: str = 'default') -> str:
    """
    Mask sensitive data based on type
    DC Protocol: Apply masking at API response level, not in database
    """
    if not value:
        return ""
    
    value_str = str(value)
    
    if mask_type == 'aadhaar':
        # Show last 4 digits: ****2345
        if len(value_str) >= 4:
            return '*' * (len(value_str) - 4) + value_str[-4:]
        return '****'
    
    elif mask_type == 'pan':
        # Show last 4 chars: ****5927B
        if len(value_str) >= 4:
            return '*' * (len(value_str) - 4) + value_str[-4:]
        return '****'
    
    elif mask_type == 'account':
        # Show last 4 digits: ****0143
        if len(value_str) >= 4:
            return '*' * (len(value_str) - 4) + value_str[-4:]
        return '****'
    
    elif mask_type == 'phone':
        # Show last 4 digits: ******7891
        if len(value_str) >= 4:
            return '*' * (len(value_str) - 4) + value_str[-4:]
        return '****'
    
    elif mask_type == 'email':
        # Show first 1 and domain: g**@**om
        if '@' in value_str:
            parts = value_str.split('@')
            if len(parts[0]) > 1:
                masked_user = parts[0][0] + '**'
            else:
                masked_user = parts[0]
            if '.' in parts[1]:
                domain_parts = parts[1].split('.')
                masked_domain = '**' + domain_parts[-1]
            else:
                masked_domain = '**'
            return f"{masked_user}@{masked_domain}"
        return 'g**@**om'
    
    return value_str

def apply_role_based_masking(user_data: Dict[str, Any], current_user: User, is_approved: bool) -> Dict[str, Any]:
    """
    Apply role-based data masking
    - Admin: Full data BEFORE approval, masked AFTER approval
    - RVZ ID: Always full data (no masking)
    - Finance Admin: Finance data unmasked, personal data masked
    """
    # RVZ ID: No masking ever
    if current_user.user_type == 'RVZ ID':
        return user_data
    
    # Finance Admin: Finance data unmasked, personal data always masked
    if current_user.user_type == 'Finance Admin':
        user_data['aadhaar_number'] = mask_sensitive_data(user_data.get('aadhaar_number'), 'aadhaar')
        user_data['pan_number'] = mask_sensitive_data(user_data.get('pan_number'), 'pan')
        user_data['phone_number'] = mask_sensitive_data(user_data.get('phone_number'), 'phone')
        user_data['email'] = mask_sensitive_data(user_data.get('email'), 'email')
        # Bank details remain unmasked
        return user_data
    
    # Admin/Super Admin: Mask only AFTER approval
    if is_approved and current_user.user_type in ['Admin', 'Super Admin']:
        user_data['aadhaar_number'] = mask_sensitive_data(user_data.get('aadhaar_number'), 'aadhaar')
        user_data['pan_number'] = mask_sensitive_data(user_data.get('pan_number'), 'pan')
        user_data['bank_account_number'] = mask_sensitive_data(user_data.get('bank_account_number'), 'account')
        user_data['phone_number'] = mask_sensitive_data(user_data.get('phone_number'), 'phone')
        user_data['email'] = mask_sensitive_data(user_data.get('email'), 'email')
    
    return user_data

@router.get("/admin/kyc/users")
async def get_kyc_users_list(
    status_filter: Optional[str] = None,  # 'Pending', 'Approved', 'Rejected', or None for all
    search: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get list of users with KYC document submissions
    DC Protocol: Query kyc_document table, group by user
    """
    # Build base query
    query = db.query(KYCDocument.owner_id).distinct()
    
    # Apply status filter if provided
    if status_filter:
        query = query.filter(KYCDocument.status == status_filter)
    
    # Get unique user IDs with KYC documents
    user_ids = [row[0] for row in query.all()]
    
    # Get user details
    users_query = db.query(User).filter(User.id.in_(user_ids))
    
    # Apply search if provided
    if search:
        users_query = users_query.filter(
            or_(
                User.id.ilike(f"%{search}%"),
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )
    
    users = users_query.all()
    
    # Build response with document counts
    result = []
    for user in users:
        # DC Protocol: Get document stats from database
        docs = db.query(KYCDocument).filter(KYCDocument.owner_id == user.id).all()
        
        pending_count = sum(1 for d in docs if d.status == 'Pending')
        approved_count = sum(1 for d in docs if d.status == 'Approved')
        rejected_count = sum(1 for d in docs if d.status == 'Rejected')
        
        result.append({
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "kyc_status": user.kyc_status,
            "total_documents": len(docs),
            "pending_documents": pending_count,
            "approved_documents": approved_count,
            "rejected_documents": rejected_count
        })
    
    return {
        "success": True,
        "count": len(result),
        "users": result
    }

@router.get("/admin/kyc/user/{user_id}")
async def get_user_kyc_details(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed KYC information for a specific user
    DC Protocol: Database as single source of truth
    Role-Based Masking: Applied based on current_user role and approval status
    """
    # DC Protocol: Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # DC Protocol: Get all documents from database
    documents = db.query(KYCDocument).filter(
        KYCDocument.owner_id == user_id
    ).order_by(KYCDocument.uploaded_at.desc()).all()
    
    # Check if KYC is approved (all required documents approved)
    required_docs = {'aadhar_front', 'aadhar_back', 'pan_card', 'passport_photo'}
    approved_docs = {doc.document_type for doc in documents if doc.status == 'Approved'}
    is_approved = required_docs.issubset(approved_docs)
    
    # Build user data dictionary
    user_data = {
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "phone_number": user.phone_number,
        "aadhaar_number": user.aadhaar_number,
        "pan_number": user.pan_number,
        "bank_account_number": user.bank_account_number,
        "bank_ifsc_code": user.bank_ifsc_code,
        "bank_account_holder": user.bank_account_holder,
        "bank_name": user.bank_name,
        "bank_branch_name": user.bank_branch_name,
        "kyc_status": user.kyc_status,
        "registration_date": user.registration_date.isoformat() if user.registration_date else None
    }
    
    # Apply role-based masking
    user_data = apply_role_based_masking(user_data, current_user, is_approved)
    
    # Build documents list
    documents_list = []
    for doc in documents:
        doc_data = {
            "id": doc.id,
            "document_type": doc.document_type,
            "file_name": doc.file_name,
            "file_path": doc.file_path,
            "file_size": doc.file_size,
            "mime_type": doc.mime_type,
            "status": doc.status,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "reviewed_by_id": doc.reviewed_by_id,
            "reviewed_at": doc.reviewed_at.isoformat() if doc.reviewed_at else None,
            "rejection_reason": doc.rejection_reason,
            "admin_notes": doc.admin_notes
        }
        
        # Add reviewer name if exists
        if doc.reviewed_by_id:
            reviewer = db.query(User).filter(User.id == doc.reviewed_by_id).first()
            doc_data["reviewed_by_name"] = reviewer.name if reviewer else "Unknown"
        else:
            doc_data["reviewed_by_name"] = None
        
        documents_list.append(doc_data)
    
    return {
        "success": True,
        "user": user_data,
        "documents": documents_list,
        "is_approved": is_approved,
        "masking_applied": current_user.user_type != 'RVZ ID' and (is_approved or current_user.user_type == 'Finance Admin')
    }

@router.get("/admin/kyc/document/{document_id}/view")
async def view_document_file(
    document_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    View/download uploaded KYC document file
    DC Protocol: Get file path from kyc_document table only
    Security: Admin/RVZ ID access only
    """
    # DC Protocol: Get document from database
    doc = db.query(KYCDocument).filter(KYCDocument.id == document_id).first()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Validate file path exists (DC Protocol)
    if not doc.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file path not found in database"
        )
    
    # Construct absolute file path
    # DC Protocol: Use path from database as-is
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    full_path = os.path.join(base_dir, doc.file_path.lstrip('/'))
    
    # Validate file exists on filesystem
    if not os.path.exists(full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document file not found on server. Expected path: {doc.file_path}"
        )
    
    # Return file
    return FileResponse(
        path=full_path,
        media_type=doc.mime_type or 'application/octet-stream',
        filename=doc.file_name or f"document_{document_id}"
    )

@router.post("/admin/kyc/document/approve")
async def approve_kyc_document(
    request: DocumentApprovalRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Approve or reject individual KYC document
    DC Protocol: Update kyc_document table status
    """
    # DC Protocol: Get document from database
    doc = db.query(KYCDocument).filter(KYCDocument.id == request.document_id).first()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Validate action
    if request.action not in ['approve', 'reject']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be 'approve' or 'reject'"
        )
    
    # Apply action
    if request.action == 'approve':
        doc.status = 'Approved'
        doc.reviewed_by_id = current_user.id
        doc.reviewed_at = datetime.now()
        doc.admin_notes = request.admin_notes
        doc.rejection_reason = None
    
    elif request.action == 'reject':
        if not request.rejection_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is required"
            )
        doc.status = 'Rejected'
        doc.reviewed_by_id = current_user.id
        doc.reviewed_at = datetime.now()
        doc.rejection_reason = request.rejection_reason
        doc.admin_notes = request.admin_notes
    
    db.commit()
    
    # Check if all required documents are approved for this user
    if request.action == 'approve':
        all_docs = db.query(KYCDocument).filter(
            KYCDocument.owner_id == doc.owner_id
        ).all()
        
        required_docs = {'aadhar_front', 'aadhar_back', 'pan_card', 'passport_photo'}
        approved_docs = {d.document_type for d in all_docs if d.status == 'Approved'}
        
        # DC Protocol: Update user KYC status if all documents approved
        if required_docs.issubset(approved_docs):
            user = db.query(User).filter(User.id == doc.owner_id).first()
            if user:
                user.kyc_status = 'Approved'
                db.commit()
    
    return {
        "success": True,
        "message": f"Document {request.action}d successfully",
        "document_id": doc.id,
        "status": doc.status
    }

@router.post("/admin/kyc/user/{user_id}/approve-all")
async def approve_all_user_documents(
    user_id: str,
    admin_notes: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Bulk approve all pending KYC documents for a user
    DC Protocol: Update all documents in kyc_document table
    """
    # DC Protocol: Get all pending documents
    pending_docs = db.query(KYCDocument).filter(
        and_(
            KYCDocument.owner_id == user_id,
            KYCDocument.status == 'Pending'
        )
    ).all()
    
    if not pending_docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending documents found for this user"
        )
    
    # Approve all documents
    for doc in pending_docs:
        doc.status = 'Approved'
        doc.reviewed_by_id = current_user.id
        doc.reviewed_at = datetime.now()
        doc.admin_notes = admin_notes
        doc.rejection_reason = None
    
    # DC Protocol: Update user KYC status
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.kyc_status = 'Approved'
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Approved {len(pending_docs)} documents for user {user_id}",
        "approved_count": len(pending_docs)
    }
