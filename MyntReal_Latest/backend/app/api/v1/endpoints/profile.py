"""
User Profile Management Endpoints
Handles profile updates, KYC documents, and bank details with approval workflows
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Optional, List
from datetime import datetime, date

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user, get_current_user_hybrid
from app.core.user_update_guard import check_user_update_allowed
from app.models.user import User
from app.models.kyc_document import KYCDocument, BankDetailsApproval
from app.services.file_upload_service import FileUploadService
from app.services.universal_upload_service import UniversalUploadService
from pydantic import BaseModel, EmailStr

router = APIRouter()
file_service = FileUploadService()

# Current Terms and Conditions Version
CURRENT_TERMS_VERSION = "1.0"

# Pydantic models for request/response
class ProfileUpdateRequest(BaseModel):
    """Profile fields that can be edited by user"""
    mobile_number: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    actual_date_of_birth: Optional[date] = None
    certificate_date_of_birth: Optional[date] = None

class KYCNumbersRequest(BaseModel):
    """Aadhaar and PAN numbers"""
    aadhaar_number: Optional[str] = None
    pan_number: Optional[str] = None

class BankDetailsRequest(BaseModel):
    """Bank details for approval workflow"""
    bank_account_number: str
    bank_ifsc_code: str
    bank_account_holder: str
    bank_name: Optional[str] = None
    bank_branch_name: Optional[str] = None
    upi_id: Optional[str] = None

class KYCApprovalRequest(BaseModel):
    """KYC approval/rejection by admin"""
    document_id: int
    action: str  # 'approve' or 'reject'
    rejection_reason: Optional[str] = None

class BankApprovalRequest(BaseModel):
    """Bank details approval by Super Admin/Finance Admin"""
    user_id: str
    action: str  # 'approve' or 'reject'
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None

@router.get("/profile")
async def get_user_profile(
    current_user: User = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
):
    """Get current user's profile details"""
    
    # DC Protocol Fix: Reload user from database to get FRESH data (not stale cached object)
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Force refresh to load ALL columns (including bank details)
    db.refresh(user)
    
    # DEBUG: Print values before serialization
    
    # Get KYC documents (DC Protocol: Use owner_id column, not user_id property)
    kyc_docs = db.query(KYCDocument).filter(
        KYCDocument.owner_id == user.id
    ).all()
    
    # Calculate overall KYC status
    # DC Protocol Feb 2026: Normalize keys for frontend (aadhar_ → aadhaar_)
    db_to_frontend_map = {
        'aadhar_front': 'aadhaar_front',
        'aadhar_back': 'aadhaar_back',
        'pan_card': 'pan_card',
        'passport_photo': 'passport_photo'
    }
    kyc_doc_status = {}
    for doc in kyc_docs:
        frontend_key = db_to_frontend_map.get(doc.document_type, doc.document_type)
        kyc_doc_status[frontend_key] = {
            "status": doc.status,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "rejection_reason": doc.rejection_reason
        }
    
    return {
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "mobile_number": user.phone_number,
        "gender": user.gender,
        "actual_date_of_birth": user.actual_date_of_birth.isoformat() if user.actual_date_of_birth else None,
        "certificate_date_of_birth": user.certificate_date_of_birth.isoformat() if user.certificate_date_of_birth else None,
        "aadhaar_number": user.aadhaar_number,
        "pan_number": user.pan_number,
        "address": {
            "line1": user.address_line1,
            "line2": user.address_line2,
            "city": user.city,
            "state": user.state,
            "postal_code": user.postal_code
        },
        "bank_details": {
            "account_number": user.bank_account_number,
            "ifsc_code": user.bank_ifsc_code,
            "account_holder": user.bank_account_holder,
            "bank_name": user.bank_name,
            "branch": user.bank_branch_name,
            "upi_id": user.upi_id
        },
        "bank_details_status": user.bank_details_status,
        "bank_rejection_reason": user.bank_rejection_reason,
        "kyc_status": user.kyc_status,
        "kyc_documents": kyc_doc_status,
        "profile_updated_at": user.profile_updated_at.isoformat() if user.profile_updated_at else None,
        "accepted_terms_version": user.accepted_terms_version,
        "acceptance_timestamp": user.acceptance_timestamp.isoformat() if user.acceptance_timestamp else None
    }

@router.put("/profile")
async def update_user_profile(
    profile_data: ProfileUpdateRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile (editable fields only)"""
    
    # Check if profile updates are allowed
    check_user_update_allowed(db, 'user_profile_updates')
    
    # DC Protocol Fix: Reload user in this endpoint's db session
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update allowed fields
    if profile_data.mobile_number is not None:
        user.phone_number = profile_data.mobile_number
    
    if profile_data.email is not None:
        # Check if email already exists
        existing = db.query(User).filter(
            and_(User.email == profile_data.email, User.id != user.id)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = profile_data.email
    
    if profile_data.gender is not None:
        user.gender = profile_data.gender
    
    if profile_data.address_line1 is not None:
        user.address_line1 = profile_data.address_line1
    
    if profile_data.address_line2 is not None:
        user.address_line2 = profile_data.address_line2
    
    if profile_data.city is not None:
        user.city = profile_data.city
    
    if profile_data.state is not None:
        user.state = profile_data.state
    
    if profile_data.postal_code is not None:
        user.postal_code = profile_data.postal_code
    
    if profile_data.actual_date_of_birth is not None:
        user.actual_date_of_birth = profile_data.actual_date_of_birth
    
    if profile_data.certificate_date_of_birth is not None:
        user.certificate_date_of_birth = profile_data.certificate_date_of_birth
    
    user.profile_updated_at = datetime.now()
    
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "message": "Profile updated successfully",
        "user_id": user.id
    }

@router.post("/upload-profile-photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload profile photo (Universal Upload: 5MB max, auto-compression to <500KB)"""
    
    # Check if photo updates are allowed
    check_user_update_allowed(db, 'user_photo_updates')
    
    # Check if profile photo document exists
    existing_doc = db.query(KYCDocument).filter(
        and_(
            KYCDocument.owner_id == current_user.id,
            KYCDocument.document_type == 'profile_photo'
        )
    ).first()
    
    # Create/update record first to get ID for upload
    if existing_doc:
        # Reuse existing record
        doc_to_upload = existing_doc
        # DC Protocol: Delete old files from Object Storage (not local)
        from app.services.object_storage import storage_service
        if existing_doc.file_path:
            try:
                storage_service.delete_file(existing_doc.file_path)
            except Exception as e:
                logger.warning(f"[PROFILE] Failed to delete old file from storage: {e}")
        if existing_doc.compressed_path:
            try:
                storage_service.delete_file(existing_doc.compressed_path)
            except Exception as e:
                logger.warning(f"[PROFILE] Failed to delete old compressed file: {e}")
    else:
        # Create new record
        doc_to_upload = KYCDocument(
            user_id=current_user.id,
            document_type='profile_photo',
            status='Pending',
            version=1,
            is_current_version=True
        )
        db.add(doc_to_upload)
        db.flush()  # Get ID for upload
    
    # Universal Upload System: 5MB max, auto-compression, dual storage
    upload_result = await UniversalUploadService.handle_upload(
        file=file,
        table_name='kyc_document',  # DC Protocol: Use SINGULAR to match actual table
        record_id=doc_to_upload.id,
        uploaded_by_id=current_user.id,
        uploaded_by_type='user',
        storage_dir='profile_photos',
        db=db
    )
    
    # Update record with upload results
    doc_to_upload.file_path = upload_result['file_path']
    doc_to_upload.file_name = upload_result['file_name']
    doc_to_upload.original_filename = upload_result['original_filename']
    doc_to_upload.file_size = upload_result['file_size']
    doc_to_upload.mime_type = upload_result['file_type']
    doc_to_upload.processing_status = 'pending' if upload_result['needs_compression'] else 'completed'
    doc_to_upload.uploaded_at = datetime.now()
    
    try:
        import pytz
        
        ist_tz = pytz.timezone('Asia/Kolkata')
        uploaded_at_ist = datetime.now(ist_tz)
        
        download_name = UniversalUploadService.generate_download_filename(
            segment_key='profile_photo',
            entity_type='user',
            entity_id=current_user.id,
            attachment_id=doc_to_upload.id,
            uploader_code=current_user.id,
            original_filename=file.filename or 'photo',
            uploaded_at=uploaded_at_ist
        )
        
        doc_to_upload.download_filename = download_name
        doc_to_upload.uses_new_naming = True
    except Exception as e:
        logger.warning(f"[PROFILE] Non-fatal: Failed to generate download filename for photo {doc_to_upload.id}: {str(e)}")
    
    db.commit()
    
    return {
        "success": True,
        "message": "Profile photo uploaded successfully (auto-compressing in background)",
        "file_name": upload_result['file_name'],
        "status": "Pending verification",
        "compression_queued": upload_result['needs_compression']
    }

@router.post("/upload-kyc-document")
async def upload_kyc_document(
    document_type: str = Form(...),  # aadhaar_front, aadhaar_back, pan_card, passport_photo
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload KYC document (max 1MB, JPG/PNG/PDF)"""
    
    # Check if document uploads are allowed
    check_user_update_allowed(db, 'user_document_uploads')
    
    # Validate document type (accept both 'aadhaar' and 'aadhar' spellings for compatibility)
    # DC Protocol Feb 2026: Normalize to 'aadhar' for database storage
    document_type_mapping = {
        'aadhaar_front': 'aadhar_front',
        'aadhaar_back': 'aadhar_back',
        'aadhar_front': 'aadhar_front',
        'aadhar_back': 'aadhar_back',
        'pan_card': 'pan_card',
        'passport_photo': 'passport_photo'
    }
    
    if document_type not in document_type_mapping:
        valid_types = ['aadhaar_front', 'aadhaar_back', 'pan_card', 'passport_photo']
        raise HTTPException(status_code=400, detail=f"Invalid document type. Must be one of: {', '.join(valid_types)}")
    
    # Normalize document type for database storage
    document_type = document_type_mapping[document_type]
    
    # Check if document already exists
    existing_doc = db.query(KYCDocument).filter(
        and_(
            KYCDocument.owner_id == current_user.id,
            KYCDocument.document_type == document_type
        )
    ).first()
    
    # Allow re-upload if: not exists, Pending, or Rejected. Block if Approved.
    if existing_doc and existing_doc.status == 'Approved':
        raise HTTPException(
            status_code=400,
            detail=f"Cannot upload. Document is already Approved by admin. Contact support if you need to update it."
        )
    
    # DC Protocol Feb 2026 FIX: Proper sequencing to avoid record_id=0 issue
    # Step 1: Create/prepare database record FIRST to get valid ID
    # Step 2: Upload file with correct record_id
    # Step 3: Update record with file details
    
    if existing_doc:
        doc_to_upload = existing_doc
        record_id_for_upload = existing_doc.id
        
        # DC Protocol: Delete old files from Object Storage (not local)
        from app.services.object_storage import storage_service
        if existing_doc.file_path:
            try:
                storage_service.delete_file(existing_doc.file_path)
            except Exception as e:
                logger.warning(f"[KYC] Failed to delete old file from storage: {e}")
        if existing_doc.compressed_path:
            try:
                storage_service.delete_file(existing_doc.compressed_path)
            except Exception as e:
                logger.warning(f"[KYC] Failed to delete old compressed file: {e}")
    else:
        # Create new record with placeholder path to get valid ID
        doc_to_upload = KYCDocument(
            user_id=current_user.id,
            document_type=document_type,
            file_path='pending_upload',  # Placeholder - will be updated after upload
            file_name='pending',
            original_filename=file.filename,
            file_size=1,  # DC Protocol: Placeholder to pass positive_file_size constraint, updated after upload
            mime_type='application/octet-stream',
            processing_status='pending',
            status='Pending',
            version=1,
            is_current_version=True
        )
        db.add(doc_to_upload)
        db.flush()  # Get valid ID for upload
        record_id_for_upload = doc_to_upload.id
    
    # Step 2: Upload file with correct record_id
    upload_result = await UniversalUploadService.handle_upload(
        file=file,
        table_name='kyc_document',  # DC Protocol: Use SINGULAR to match actual table
        record_id=record_id_for_upload,
        uploaded_by_id=current_user.id,
        uploaded_by_type='user',
        storage_dir='kyc_documents',
        db=db
    )
    
    # Update record with upload results
    doc_to_upload.file_path = upload_result['file_path']
    doc_to_upload.file_name = upload_result['file_name']
    doc_to_upload.original_filename = upload_result['original_filename']
    doc_to_upload.file_size = upload_result['file_size']
    doc_to_upload.mime_type = upload_result['file_type']
    doc_to_upload.processing_status = 'pending' if upload_result['needs_compression'] else 'completed'
    doc_to_upload.uploaded_at = datetime.now()
    doc_to_upload.rejection_reason = None
    
    try:
        import pytz
        
        ist_tz = pytz.timezone('Asia/Kolkata')
        uploaded_at_ist = datetime.now(ist_tz)
        
        download_name = UniversalUploadService.generate_download_filename(
            segment_key='kyc_document',
            entity_type='user',
            entity_id=current_user.id,
            attachment_id=doc_to_upload.id,
            uploader_code=current_user.id,
            original_filename=file.filename or 'document',
            uploaded_at=uploaded_at_ist
        )
        
        doc_to_upload.download_filename = download_name
        doc_to_upload.uses_new_naming = True
    except Exception as e:
        logger.warning(f"[KYC] Non-fatal: Failed to generate download filename for doc {doc_to_upload.id}: {str(e)}")
    
    db.commit()
    
    # Update user KYC status to Pending if all documents uploaded
    all_docs = db.query(KYCDocument).filter(
        KYCDocument.owner_id == current_user.id
    ).all()
    
    doc_types_uploaded = {doc.document_type for doc in all_docs}
    required_docs = {'aadhar_front', 'aadhar_back', 'pan_card', 'passport_photo'}
    
    if required_docs.issubset(doc_types_uploaded):
        # DC Protocol Fix: Reload user in this endpoint's db session before updating
        user_to_update = db.query(User).filter(User.id == current_user.id).first()
        if user_to_update:
            user_to_update.kyc_status = 'Pending'
            db.commit()
    
    return {
        "success": True,
        "message": f"{document_type.replace('_', ' ').title()} uploaded successfully",
        "file_name": upload_result['file_name'],
        "status": "Pending verification"
    }

@router.get("/kyc-documents")
async def get_kyc_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all KYC documents for current user"""
    
    docs = db.query(KYCDocument).filter(
        KYCDocument.owner_id == current_user.id
    ).all()
    
    return {
        "user_id": current_user.id,
        "kyc_status": current_user.kyc_status,
        "documents": [
            {
                "id": doc.id,
                "document_type": doc.document_type,
                "file_name": doc.file_name,
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                "status": doc.status,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "rejection_reason": doc.rejection_reason
            }
            for doc in docs
        ]
    }

@router.get("/kyc-document/{document_type}")
async def get_kyc_document_by_type(
    document_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific KYC document file URL for viewing (DC Protocol Feb 2026)"""
    
    # Normalize document type (frontend uses aadhaar_, database uses aadhar_)
    type_mapping = {
        'aadhaar_front': 'aadhar_front',
        'aadhaar_back': 'aadhar_back',
        'aadhar_front': 'aadhar_front',
        'aadhar_back': 'aadhar_back',
        'pan_card': 'pan_card',
        'passport_photo': 'passport_photo'
    }
    
    db_doc_type = type_mapping.get(document_type)
    if not db_doc_type:
        raise HTTPException(status_code=400, detail="Invalid document type")
    
    doc = db.query(KYCDocument).filter(
        KYCDocument.owner_id == current_user.id,
        KYCDocument.document_type == db_doc_type
    ).first()
    
    if not doc or not doc.file_path:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Return file URL for viewing
    return {
        "success": True,
        "document_type": document_type,
        "file_url": f"/storage/{doc.file_path}",
        "file_name": doc.original_filename,
        "status": doc.status,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
    }

@router.put("/kyc-numbers")
async def update_kyc_numbers(
    kyc_data: KYCNumbersRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update Aadhaar and PAN numbers with uniqueness validation"""
    
    # Check if KYC updates are allowed
    check_user_update_allowed(db, 'user_kyc_updates')
    
    # DC Protocol Fix: Reload user in this endpoint's db session
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate and update Aadhaar number
    if kyc_data.aadhaar_number:
        # Validate format (12 digits)
        if not kyc_data.aadhaar_number.isdigit() or len(kyc_data.aadhaar_number) != 12:
            raise HTTPException(status_code=400, detail="Aadhaar number must be exactly 12 digits")
        
        # Check uniqueness
        existing = db.query(User).filter(
            and_(User.aadhaar_number == kyc_data.aadhaar_number, User.id != current_user.id)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Aadhaar number already registered")
        
        user.aadhaar_number = kyc_data.aadhaar_number
    
    # Validate and update PAN number
    if kyc_data.pan_number:
        # Convert to uppercase
        pan_upper = kyc_data.pan_number.upper()
        
        # Validate format (5 letters + 4 digits + 1 letter)
        import re
        if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan_upper):
            raise HTTPException(status_code=400, detail="Invalid PAN format. Must be 5 letters + 4 digits + 1 letter")
        
        # Check uniqueness
        existing = db.query(User).filter(
            and_(User.pan_number == pan_upper, User.id != current_user.id)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="PAN number already registered")
        
        user.pan_number = pan_upper
    
    user.profile_updated_at = datetime.now()
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "message": "KYC numbers updated successfully",
        "aadhaar_number": user.aadhaar_number,
        "pan_number": user.pan_number
    }

@router.put("/bank-details")
async def update_bank_details(
    bank_data: BankDetailsRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update bank details - requires Admin + Finance Admin approval"""
    
    # Check if bank updates are allowed
    check_user_update_allowed(db, 'user_bank_updates')
    
    # DC Protocol Fix: Reload user in this endpoint's db session
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update bank details in User model
    user.bank_name = bank_data.bank_name
    user.bank_account_holder = bank_data.bank_account_holder
    user.bank_account_number = bank_data.bank_account_number
    user.bank_ifsc_code = bank_data.bank_ifsc_code.upper()
    user.bank_branch_name = bank_data.bank_branch_name
    user.upi_id = bank_data.upi_id
    user.profile_updated_at = datetime.now()
    
    # Set status to Pending Admin (first step of approval workflow)
    user.bank_details_status = 'Pending Admin'
    user.bank_admin_approved_by = None
    user.bank_admin_approved_at = None
    user.bank_finance_approved_by = None
    user.bank_finance_approved_at = None
    user.bank_rejection_reason = None
    
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "message": "Bank details submitted for Admin approval",
        "status": user.bank_details_status
    }

class TermsAcceptRequest(BaseModel):
    """Terms acceptance request"""
    version: str

@router.post("/accept-terms")
async def accept_terms(
    terms_data: TermsAcceptRequest,
    current_user: User = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
):
    """Accept terms and conditions"""
    
    # Check if terms acceptance is allowed
    check_user_update_allowed(db, 'user_terms_acceptance')
    
    # DC Protocol Fix: Reload user in this endpoint's db session
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.accepted_terms_version = terms_data.version
    user.acceptance_timestamp = datetime.now()
    
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "message": "Terms and conditions accepted successfully",
        "version": user.accepted_terms_version
    }
