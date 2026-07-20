"""
KYC Document Management Models
Individual document tracking with approval workflow
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, Enum
from sqlalchemy import ForeignKey
from app.models.base import BaseModel, get_indian_time
import enum

# DC Protocol Mar 2026: partner_id column added to support VGK/Official Partner KYC.
# owner_id (user) or partner_id (official_partners) — one is set, the other NULL.

class DocumentType(str, enum.Enum):
    """KYC Document Types"""
    AADHAAR_FRONT = "aadhaar_front"
    AADHAAR_BACK = "aadhaar_back"
    PAN_CARD = "pan_card"
    PASSPORT_PHOTO = "passport_photo"
    PROFILE_PHOTO = "profile_photo"

class DocumentStatus(str, enum.Enum):
    """Document Verification Status"""
    PENDING = "Pending"
    VALIDATED = "Validated by Admin"
    APPROVED = "Approved"
    REJECTED = "Rejected"

class KYCDocument(BaseModel):
    """
    Individual KYC Document tracking
    Each document has its own status and approval flow
    """
    __tablename__ = 'kyc_document'
    
    id = Column(Integer, primary_key=True)
    owner_id = Column(String(12), ForeignKey('user.id'), nullable=True)  # NULL for partner KYC records
    partner_id = Column(Integer, ForeignKey('official_partners.id', ondelete='CASCADE'), nullable=True)  # DC Protocol Mar 2026: VGK/Partner KYC

    # Alias for backward compatibility
    @property
    def user_id(self):
        return self.owner_id
    
    @user_id.setter
    def user_id(self, value):
        self.owner_id = value
    
    # Document Details (matching actual database schema)
    document_type = Column(String(50), nullable=False)
    file_path = Column(String(255), nullable=False)
    file_name = Column(String(255), nullable=True)
    original_filename = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(50), nullable=True)
    
    # Universal Upload System: Compression fields (DC Protocol)
    compressed_path = Column(String(500), nullable=True)
    compressed_size_bytes = Column(Integer, nullable=True)
    processing_status = Column(String(20), default='pending', nullable=True)
    processed_at = Column(DateTime, nullable=True)
    compressed_checksum = Column(String(64), nullable=True)
    has_compressed = Column(Boolean, default=False, nullable=True)
    uploaded_by_emp_code = Column(String(20), nullable=True)
    
    # DC Protocol: Dual Storage Architecture (object storage vs local)
    original_checksum = Column(String(64), nullable=True)  # SHA-256 before compression/watermark
    original_storage_type = Column(String(20), default='local', nullable=True)  # 'local' or 'object_storage'
    original_storage_key = Column(String(500), nullable=True)  # Actual object storage key (if object_storage)
    
    # DC Protocol: Semantic file naming (Nov 29, 2025)
    download_filename = Column(String(255), nullable=True)  # Semantic download filename
    uses_new_naming = Column(Boolean, default=False, nullable=False)  # Flag for new naming convention
    
    # Status & Verification
    status = Column(String(30), default='Pending', nullable=False)
    
    # Versioning
    version = Column(Integer, nullable=True)
    previous_version_id = Column(Integer, nullable=True)
    is_current_version = Column(Boolean, default=True, nullable=True)
    
    # Review/Approval (actual database columns)
    reviewed_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    admin_notes = Column(Text, nullable=True)
    
    # Rejection
    rejection_reason = Column(Text, nullable=True)
    
    # Validation flags
    pan_number_encrypted = Column(Text, nullable=True)
    aadhaar_number_encrypted = Column(Text, nullable=True)
    pan_validated = Column(Boolean, nullable=True)
    aadhaar_validated = Column(Boolean, nullable=True)
    validation_errors = Column(Text, nullable=True)
    
    # Timestamps
    uploaded_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    def __repr__(self):
        return f'<KYCDocument {self.owner_id}: {self.document_type} - {self.status}>'


class BankDetailsApproval(BaseModel):
    """
    Bank Details Approval Workflow
    Requires: Super Admin → Finance Admin approval
    """
    __tablename__ = 'bank_details_approval'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False, unique=True)
    
    # Bank Details (from User model but tracked here for approval)
    bank_account_number = Column(String(50), nullable=False)
    bank_ifsc_code = Column(String(20), nullable=False)
    bank_account_holder = Column(String(100), nullable=False)
    bank_name = Column(String(100), nullable=True)
    bank_branch_name = Column(String(100), nullable=True)
    upi_id = Column(String(100), nullable=True)
    
    # Approval Status
    status = Column(String(20), default='Pending', nullable=False)  # Pending, Approved, Rejected
    
    # Approval Workflow (Super Admin → Finance Admin)
    approved_by_super_admin = Column(String(12), ForeignKey('user.id'), nullable=True)
    super_admin_approved_at = Column(DateTime, nullable=True)
    super_admin_notes = Column(Text, nullable=True)
    
    approved_by_finance_admin = Column(String(12), ForeignKey('user.id'), nullable=True)
    finance_admin_approved_at = Column(DateTime, nullable=True)
    finance_admin_notes = Column(Text, nullable=True)
    
    # Rejection Details
    rejected_by = Column(String(12), ForeignKey('user.id'), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Timestamps
    submitted_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    def __repr__(self):
        return f'<BankDetailsApproval {self.user_id}: {self.status}>'
