"""
Staff Financial Management System Schemas - DC_SFMS_001
Pydantic Schemas for Financial/Accounts Module
DC Protocol Compliant - Validation at every entry point

Created: Dec 06, 2025
DC Protocol: Write-Verify-Validate at all levels

VGK and EA have equal full permissions on all Accounts module features.
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict, EmailStr
from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


# ==================== ENUMS ====================

class CompanyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class SegmentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class IncomeSourceCategory(str, Enum):
    SALES = "SALES"
    SERVICE = "SERVICE"
    MNR_PAYMENT = "MNR_PAYMENT"
    OTHER = "OTHER"


class VendorStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BLOCKED = "BLOCKED"


class VendorType(str, Enum):
    PRODUCT = "PRODUCT"
    SERVICE = "SERVICE"
    BOTH = "BOTH"


class StockItemStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DISCONTINUED = "DISCONTINUED"


class StockCategory(str, Enum):
    PRODUCT = "PRODUCT"
    SERVICE = "SERVICE"
    CONSUMABLE = "CONSUMABLE"
    RAW_MATERIAL = "RAW_MATERIAL"


# ==================== ASSOCIATED COMPANIES SCHEMAS ====================

class AssociatedCompanyBase(BaseModel):
    """Base schema for Associated Company - aligned with model fields"""
    company_name: str = Field(..., min_length=2, max_length=200, description="Company name")
    company_code: str = Field(..., min_length=2, max_length=20, description="Unique company code")
    company_type: str = Field(default="SUBSIDIARY", description="Company type: PARENT, SUBSIDIARY, PARTNER, VENDOR")
    
    gst_number: Optional[str] = Field(None, max_length=20, description="GST Number")
    pan_number: Optional[str] = Field(None, max_length=15, description="PAN Number")
    cin_number: Optional[str] = Field(None, max_length=25, description="CIN Number")

    phone: Optional[str] = Field(None, max_length=20, description="Primary contact phone number")
    email: Optional[str] = Field(None, max_length=200, description="Primary contact email")
    website: Optional[str] = Field(None, max_length=200, description="Company website URL")

    address: Optional[str] = Field(None, max_length=500, description="Full address")
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=10)
    
    bank_name: Optional[str] = Field(None, max_length=200, description="Bank name")
    bank_branch: Optional[str] = Field(None, max_length=200, description="Bank branch")
    account_number: Optional[str] = Field(None, max_length=30, description="Bank account number")
    ifsc_code: Optional[str] = Field(None, max_length=15, description="IFSC code")
    account_type: str = Field(default="CURRENT", description="Account type: CURRENT, SAVINGS")
    upi_id: Optional[str] = Field(None, max_length=100, description="UPI ID")
    
    model_config = {"extra": "forbid"}
    
    @field_validator('company_code')
    @classmethod
    def validate_company_code(cls, v):
        if v and not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Company code must be alphanumeric with underscores/hyphens only')
        return v.upper().strip() if v else v
    
    @field_validator('company_type')
    @classmethod
    def validate_company_type(cls, v):
        valid_types = ['PARENT', 'SUBSIDIARY', 'PARTNER', 'VENDOR']
        if v and v.upper() not in valid_types:
            raise ValueError(f'Company type must be one of: {valid_types}')
        return v.upper() if v else 'SUBSIDIARY'
    
    @field_validator('gst_number')
    @classmethod
    def validate_gst(cls, v):
        if v:
            v = v.upper().strip()
            if len(v) != 15:
                raise ValueError('GST number must be exactly 15 characters')
        return v
    
    @field_validator('pan_number')
    @classmethod
    def validate_pan(cls, v):
        if v:
            v = v.upper().strip()
            if len(v) != 10:
                raise ValueError('PAN number must be exactly 10 characters')
        return v


class AssociatedCompanyCreate(AssociatedCompanyBase):
    """Schema for creating Associated Company"""
    is_book_keeper: bool = Field(default=False, description="Is this the book keeper company (Mynt Real LLP)")
    is_marketplace_endpoint: bool = Field(default=False, description="Is this the company that sells to marketplace customers (e.g. Lucky Enterprises)")
    is_active: bool = Field(default=True, description="Is company active")


class AssociatedCompanyUpdate(BaseModel):
    """Schema for updating Associated Company - aligned with model fields"""
    company_name: Optional[str] = Field(None, min_length=2, max_length=200)
    company_type: Optional[str] = Field(None, description="PARENT, SUBSIDIARY, PARTNER, VENDOR")
    
    gst_number: Optional[str] = Field(None, max_length=20)
    pan_number: Optional[str] = Field(None, max_length=15)
    cin_number: Optional[str] = Field(None, max_length=25)

    phone: Optional[str] = Field(None, max_length=20, description="Primary contact phone number")
    email: Optional[str] = Field(None, max_length=200, description="Primary contact email")
    website: Optional[str] = Field(None, max_length=200, description="Company website URL")

    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=10)
    
    bank_name: Optional[str] = Field(None, max_length=200)
    bank_branch: Optional[str] = Field(None, max_length=200)
    account_number: Optional[str] = Field(None, max_length=30)
    ifsc_code: Optional[str] = Field(None, max_length=15)
    account_type: Optional[str] = Field(None, description="CURRENT, SAVINGS")
    upi_id: Optional[str] = Field(None, max_length=100)
    
    logo_path: Optional[str] = Field(None, description="Path to company logo")
    stamp_path: Optional[str] = Field(None, description="Path to company stamp image")
    signature_path: Optional[str] = Field(None, description="Path to authorized signature image")
    signatory_name: Optional[str] = Field(None, max_length=200)
    signatory_designation: Optional[str] = Field(None, max_length=100)
    
    is_active: Optional[bool] = None
    is_marketplace_endpoint: Optional[bool] = None

    model_config = {"extra": "forbid"}
    
    @field_validator('gst_number')
    @classmethod
    def validate_gst(cls, v):
        if v:
            v = v.upper().strip()
            if len(v) != 15:
                raise ValueError('GST number must be exactly 15 characters')
        return v
    
    @field_validator('pan_number')
    @classmethod
    def validate_pan(cls, v):
        if v:
            v = v.upper().strip()
            if len(v) != 10:
                raise ValueError('PAN number must be exactly 10 characters')
        return v


class AssociatedCompanyResponse(BaseModel):
    """Response schema for Associated Company - aligned with model fields"""
    id: int
    company_code: str
    company_name: str
    company_type: str
    
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    cin_number: Optional[str] = None

    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None

    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    account_type: Optional[str] = None
    upi_id: Optional[str] = None
    
    logo_path: Optional[str] = None
    stamp_path: Optional[str] = None
    signature_path: Optional[str] = None
    signatory_name: Optional[str] = None
    signatory_designation: Optional[str] = None
    
    receipt_prefix: Optional[str] = None
    invoice_prefix: Optional[str] = None
    
    is_book_keeper: bool
    is_marketplace_endpoint: bool = False
    is_active: bool
    
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class AssociatedCompanyListResponse(BaseModel):
    """Response schema for listing companies"""
    success: bool
    companies: List[AssociatedCompanyResponse]
    total: int
    page: int
    page_size: int


# ==================== COMPANY SEGMENTS SCHEMAS ====================

class CompanySegmentBase(BaseModel):
    """Base schema for Company Segment"""
    segment_name: str = Field(..., min_length=2, max_length=100, description="Segment name")
    segment_code: str = Field(..., min_length=2, max_length=20, description="Unique segment code")
    description: Optional[str] = Field(None, max_length=500)
    
    model_config = {"extra": "forbid"}
    
    @field_validator('segment_code')
    @classmethod
    def validate_segment_code(cls, v):
        if v and not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Segment code must be alphanumeric with underscores/hyphens only')
        return v.upper().strip() if v else v


class CompanySegmentCreate(CompanySegmentBase):
    """Schema for creating Company Segment - aligned with model fields"""
    company_id: int = Field(..., gt=0, description="Associated company ID")
    display_order: int = Field(default=0, ge=0)
    is_active: bool = Field(default=True, description="Is segment active")


class CompanySegmentUpdate(BaseModel):
    """Schema for updating Company Segment - aligned with model fields"""
    segment_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    
    model_config = {"extra": "forbid"}


class CompanySegmentResponse(BaseModel):
    """Response schema for Company Segment - aligned with model fields"""
    id: int
    company_id: int
    company_name: Optional[str] = None
    segment_name: str
    segment_code: str
    description: Optional[str] = None
    display_order: int
    is_default: bool
    is_active: bool
    
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class CompanySegmentListResponse(BaseModel):
    success: bool
    segments: List[CompanySegmentResponse]
    total: int


# ==================== REVENUE CATEGORY SCHEMAS ====================

class RevenueCategoryCreate(BaseModel):
    company_id: int = Field(..., gt=0)
    category_code: str = Field(..., min_length=2, max_length=30)
    category_name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    display_order: int = Field(default=0, ge=0)

    model_config = {"extra": "forbid"}

    @field_validator('category_code')
    @classmethod
    def validate_code(cls, v):
        if v and not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Category code must be alphanumeric with underscores/hyphens only')
        return v.upper().strip() if v else v


class RevenueCategoryUpdate(BaseModel):
    category_name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

    model_config = {"extra": "forbid"}


class RevenueCategoryResponse(BaseModel):
    id: int
    company_id: int
    category_code: str
    category_name: str
    description: Optional[str] = None
    display_order: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ==================== INCOME SOURCE TYPES SCHEMAS ====================

class IncomeSourceTypeBase(BaseModel):
    """Base schema for Income Source Type - aligned with model fields"""
    source_name: str = Field(..., min_length=2, max_length=100, description="Income source name")
    source_code: str = Field(..., min_length=2, max_length=30, description="Unique source code")
    description: Optional[str] = Field(None, max_length=500)
    
    model_config = {"extra": "forbid"}
    
    @field_validator('source_code')
    @classmethod
    def validate_source_code(cls, v):
        if v and not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Source code must be alphanumeric with underscores/hyphens only')
        return v.upper().strip() if v else v


class IncomeSourceTypeCreate(IncomeSourceTypeBase):
    """Schema for creating Income Source Type - aligned with model fields"""
    requires_reference: bool = Field(default=False, description="Whether this source requires a reference")
    reference_type: Optional[str] = Field(None, description="Type of reference: MNR_USER, INVOICE, CONTRACT, CUSTOMER, OTHER")
    is_taxable: bool = Field(default=True, description="Whether income from this source is taxable")
    default_tax_rate: Decimal = Field(default=Decimal("18.00"), ge=0, le=100, description="Default GST/tax rate %")
    requires_receipt: bool = Field(default=True, description="Whether receipt generation is required")
    applicable_companies: List[Union[int, str]] = Field(default=["ALL"], description="List of company IDs/codes or ALL")
    display_order: int = Field(default=0, ge=0)
    is_active: bool = Field(default=True)
    
    @field_validator('reference_type')
    @classmethod
    def validate_reference_type(cls, v):
        valid_types = ['MNR_USER', 'INVOICE', 'CONTRACT', 'CUSTOMER', 'OTHER', None]
        if v and v.upper() not in valid_types:
            raise ValueError(f'Reference type must be one of: {[t for t in valid_types if t]}')
        return v.upper() if v else None


class IncomeSourceTypeUpdate(BaseModel):
    """Schema for updating Income Source Type - aligned with model fields"""
    source_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    requires_reference: Optional[bool] = None
    reference_type: Optional[str] = None
    is_taxable: Optional[bool] = Field(None, description="Whether income from this source is taxable")
    default_tax_rate: Optional[Decimal] = Field(None, ge=0, le=100, description="Default GST/tax rate %")
    requires_receipt: Optional[bool] = Field(None, description="Whether receipt generation is required")
    applicable_companies: Optional[List[Union[int, str]]] = None
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    
    model_config = {"extra": "forbid"}


class IncomeSourceTypeResponse(BaseModel):
    """Response schema for Income Source Type - aligned with model fields"""
    id: int
    source_code: str
    source_name: str
    description: Optional[str] = None
    requires_reference: bool
    reference_type: Optional[str] = None
    is_taxable: bool
    default_tax_rate: Decimal
    requires_receipt: bool
    applicable_companies: List[Union[int, str]] = []
    display_order: int
    is_active: bool
    
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class IncomeSourceTypeListResponse(BaseModel):
    """Response schema for listing income source types"""
    success: bool
    income_source_types: List[IncomeSourceTypeResponse]
    total: int


# ==================== HSN MASTER SCHEMAS ====================

class HSNMasterBase(BaseModel):
    """Base schema for HSN Master - DC_HSN_001"""
    hsn_code: str = Field(..., min_length=4, max_length=20, description="HSN/SAC code")
    description: str = Field(..., min_length=3, max_length=500, description="Item/service description")
    
    cgst_rate: Decimal = Field(default=Decimal("9.00"), ge=0, le=50, description="CGST rate for intra-state")
    sgst_rate: Decimal = Field(default=Decimal("9.00"), ge=0, le=50, description="SGST rate for intra-state")
    igst_rate: Decimal = Field(default=Decimal("18.00"), ge=0, le=50, description="IGST rate for inter-state")
    cess_rate: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0, le=50, description="Cess rate if applicable")
    
    effective_from: Optional[date] = Field(None, description="Date from which rates are effective")
    effective_to: Optional[date] = Field(None, description="Date until which rates are effective")
    
    model_config = {"extra": "forbid"}
    
    @field_validator('hsn_code')
    @classmethod
    def validate_hsn_code(cls, v):
        if v:
            v = v.upper().strip()
            if not v.isalnum():
                raise ValueError('HSN code must be alphanumeric')
        return v


class HSNMasterCreate(HSNMasterBase):
    """Schema for creating HSN Master"""
    is_active: bool = Field(default=True)


class HSNMasterUpdate(BaseModel):
    """Schema for updating HSN Master"""
    hsn_code: Optional[str] = Field(None, min_length=4, max_length=20)
    description: Optional[str] = Field(None, min_length=3, max_length=500)
    
    cgst_rate: Optional[Decimal] = Field(None, ge=0, le=50)
    sgst_rate: Optional[Decimal] = Field(None, ge=0, le=50)
    igst_rate: Optional[Decimal] = Field(None, ge=0, le=50)
    cess_rate: Optional[Decimal] = Field(None, ge=0, le=50)
    
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    is_active: Optional[bool] = None
    
    model_config = {"extra": "forbid"}
    
    @field_validator('hsn_code')
    @classmethod
    def validate_hsn_code(cls, v):
        if v:
            v = v.upper().strip()
            if not v.isalnum():
                raise ValueError('HSN code must be alphanumeric')
        return v


class HSNMasterResponse(BaseModel):
    """Response schema for HSN Master"""
    id: int
    hsn_code: str
    description: str
    
    cgst_rate: Decimal
    sgst_rate: Decimal
    igst_rate: Decimal
    cess_rate: Optional[Decimal] = Decimal("0.00")

    # gst_rate = igst_rate — single computed field so all frontend code can rely on it
    gst_rate: Optional[Decimal] = None

    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    is_active: bool
    
    created_by_id: Optional[int] = None
    updated_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

    @model_validator(mode='after')
    def _compute_gst_rate(self) -> 'HSNMasterResponse':
        self.gst_rate = self.igst_rate
        return self


class HSNMasterListResponse(BaseModel):
    """Response schema for listing HSN codes"""
    success: bool
    hsn_codes: List[HSNMasterResponse]
    total: int


class GSTCalculationRequest(BaseModel):
    """Request schema for GST calculation"""
    hsn_code: str
    seller_state: str = Field(..., description="State of seller (e.g., 'Andhra Pradesh')")
    buyer_state: str = Field(..., description="State of buyer (e.g., 'Delhi')")
    taxable_amount: Decimal = Field(..., gt=0, description="Taxable amount before GST")


class GSTCalculationResponse(BaseModel):
    """Response schema for GST calculation"""
    hsn_code: str
    taxable_amount: Decimal
    is_intra_state: bool
    
    cgst_rate: Decimal
    sgst_rate: Decimal
    igst_rate: Decimal
    cess_rate: Decimal
    
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal
    
    total_gst: Decimal
    total_amount: Decimal


# ==================== PURCHASE INVOICE UPLOAD SCHEMAS (DC_PURCHASE_001) ====================

class PurchaseUploadStatus(str, Enum):
    """Status enum for purchase invoice uploads"""
    UPLOADED = "UPLOADED"
    EXTRACTING = "EXTRACTING"
    EXTRACTED = "EXTRACTED"
    REVIEWED = "REVIEWED"
    CONFIRMED = "CONFIRMED"
    PROCESSED = "PROCESSED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class PurchaseUploadFileType(str, Enum):
    """Supported file types for invoice upload"""
    PDF = "PDF"
    JPEG = "JPEG"
    PNG = "PNG"
    IMAGE = "IMAGE"
    EXCEL = "EXCEL"
    CSV = "CSV"


class ExtractionMethod(str, Enum):
    """Methods for data extraction"""
    OCR = "OCR"
    PDF_PARSER = "PDF_PARSER"
    EXCEL_PARSER = "EXCEL_PARSER"
    CSV_PARSER = "CSV_PARSER"
    MANUAL = "MANUAL"
    AI_EXTRACTION = "AI_EXTRACTION"


class PurchaseInvoiceLineItemBase(BaseModel):
    """Base schema for purchase invoice line item"""
    line_number: int = Field(..., ge=1)
    item_description: str = Field(..., min_length=1, max_length=500)
    
    item_id: Optional[int] = None
    item_code: Optional[str] = Field(None, max_length=30)
    hsn_id: Optional[int] = None
    hsn_code: Optional[str] = Field(None, max_length=20)
    
    quantity: Decimal = Field(default=Decimal("1.000"), ge=0)
    unit_of_measure: str = Field(default="PCS", max_length=20)
    unit_rate: Decimal = Field(default=Decimal("0.00"), ge=0)
    
    discount_percent: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0, le=100)
    discount_amount: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)
    
    gst_rate: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    cgst_rate: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)
    sgst_rate: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)
    igst_rate: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)
    cess_rate: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)
    
    serial_numbers: Optional[List[str]] = None
    imei_numbers: Optional[List[str]] = None
    batch_number: Optional[str] = Field(None, max_length=50)
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    warranty_months: Optional[int] = Field(default=0, ge=0)


class PurchaseInvoiceLineItemCreate(PurchaseInvoiceLineItemBase):
    """Create schema for purchase invoice line item"""
    pass


class PurchaseInvoiceLineItemUpdate(BaseModel):
    """Update schema for purchase invoice line item"""
    item_description: Optional[str] = Field(None, min_length=1, max_length=500)
    item_id: Optional[int] = None
    item_code: Optional[str] = Field(None, max_length=30)
    hsn_id: Optional[int] = None
    hsn_code: Optional[str] = Field(None, max_length=20)
    
    quantity: Optional[Decimal] = Field(None, ge=0)
    unit_of_measure: Optional[str] = Field(None, max_length=20)
    unit_rate: Optional[Decimal] = Field(None, ge=0)
    
    discount_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    gst_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    
    serial_numbers: Optional[List[str]] = None
    imei_numbers: Optional[List[str]] = None
    batch_number: Optional[str] = Field(None, max_length=50)
    warranty_months: Optional[int] = Field(None, ge=0)


class PurchaseInvoiceLineItemResponse(BaseModel):
    """Response schema for purchase invoice line item"""
    id: int
    upload_id: int
    line_number: int
    
    item_id: Optional[int] = None
    item_code: Optional[str] = None
    item_description: str
    hsn_id: Optional[int] = None
    hsn_code: Optional[str] = None
    
    quantity: Decimal
    unit_of_measure: str
    unit_rate: Decimal
    
    gross_amount: Decimal
    discount_percent: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    taxable_amount: Decimal
    
    gst_rate: Decimal
    cgst_rate: Optional[Decimal] = None
    cgst_amount: Optional[Decimal] = None
    sgst_rate: Optional[Decimal] = None
    sgst_amount: Optional[Decimal] = None
    igst_rate: Optional[Decimal] = None
    igst_amount: Optional[Decimal] = None
    cess_rate: Optional[Decimal] = None
    cess_amount: Optional[Decimal] = None
    
    total_tax: Decimal
    line_total: Decimal
    
    serial_numbers: Optional[List[str]] = None
    imei_numbers: Optional[List[str]] = None
    batch_number: Optional[str] = None
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    warranty_months: Optional[int] = None
    warranty_end_date: Optional[date] = None
    
    is_matched: bool
    match_confidence: Optional[Decimal] = None
    
    model_config = {"from_attributes": True}


class PurchaseInvoiceUploadBase(BaseModel):
    """Base schema for purchase invoice upload"""
    company_id: int = Field(..., gt=0)
    segment_id: Optional[int] = None
    vendor_id: Optional[int] = None
    
    vendor_invoice_no: Optional[str] = Field(None, max_length=50)
    vendor_invoice_date: Optional[date] = None
    
    is_igst: bool = Field(default=False)
    seller_state: Optional[str] = Field(None, max_length=100)
    buyer_state: Optional[str] = Field(None, max_length=100)
    
    credit_days: Optional[int] = Field(default=0, ge=0)
    due_date: Optional[date] = None
    is_credit_purchase: bool = Field(default=False)


class PurchaseInvoiceUploadCreate(PurchaseInvoiceUploadBase):
    """Create schema for purchase invoice upload (minimal - file uploaded separately)"""
    file_name: str = Field(..., min_length=1, max_length=200)
    file_type: str = Field(..., description="PDF, JPEG, PNG, EXCEL, CSV")
    
    @field_validator('file_type')
    @classmethod
    def validate_file_type(cls, v):
        valid_types = ['PDF', 'JPEG', 'PNG', 'IMAGE', 'EXCEL', 'CSV']
        if v and v.upper() not in valid_types:
            raise ValueError(f'File type must be one of: {valid_types}')
        return v.upper() if v else 'PDF'


class PurchaseInvoiceUploadUpdate(BaseModel):
    """Update schema for purchase invoice upload - for editing extracted data"""
    vendor_id: Optional[int] = None
    vendor_invoice_no: Optional[str] = Field(None, max_length=50)
    vendor_invoice_date: Optional[date] = None
    
    subtotal: Optional[Decimal] = Field(None, ge=0)
    total_discount: Optional[Decimal] = Field(None, ge=0)
    taxable_amount: Optional[Decimal] = Field(None, ge=0)
    cgst_amount: Optional[Decimal] = Field(None, ge=0)
    sgst_amount: Optional[Decimal] = Field(None, ge=0)
    igst_amount: Optional[Decimal] = Field(None, ge=0)
    cess_amount: Optional[Decimal] = Field(None, ge=0)
    round_off: Optional[Decimal] = None
    grand_total: Optional[Decimal] = Field(None, ge=0)
    
    is_igst: Optional[bool] = None
    seller_state: Optional[str] = Field(None, max_length=100)
    buyer_state: Optional[str] = Field(None, max_length=100)
    
    credit_days: Optional[int] = Field(None, ge=0)
    due_date: Optional[date] = None
    is_credit_purchase: Optional[bool] = None
    
    review_notes: Optional[str] = None
    line_items: Optional[List[PurchaseInvoiceLineItemCreate]] = None


class PurchaseInvoiceUploadResponse(BaseModel):
    """Response schema for purchase invoice upload"""
    id: int
    upload_number: str
    
    company_id: int
    segment_id: Optional[int] = None
    vendor_id: Optional[int] = None
    
    file_path: str
    file_name: str
    file_type: str
    file_size: Optional[int] = None
    
    vendor_invoice_no: Optional[str] = None
    vendor_invoice_date: Optional[date] = None
    
    extraction_confidence: Optional[Decimal] = None
    extraction_method: Optional[str] = None
    
    subtotal: Optional[Decimal] = None
    total_discount: Optional[Decimal] = None
    taxable_amount: Optional[Decimal] = None
    cgst_amount: Optional[Decimal] = None
    sgst_amount: Optional[Decimal] = None
    igst_amount: Optional[Decimal] = None
    cess_amount: Optional[Decimal] = None
    total_tax: Optional[Decimal] = None
    round_off: Optional[Decimal] = None
    grand_total: Optional[Decimal] = None
    
    is_igst: bool
    seller_state: Optional[str] = None
    buyer_state: Optional[str] = None
    
    credit_days: Optional[int] = None
    due_date: Optional[date] = None
    is_credit_purchase: bool
    
    status: str
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    vendor_transaction_id: Optional[int] = None
    
    uploaded_by_id: Optional[int] = None
    reviewed_by_id: Optional[int] = None
    confirmed_by_id: Optional[int] = None
    
    uploaded_at: datetime
    extracted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    
    line_items: Optional[List[PurchaseInvoiceLineItemResponse]] = None
    
    model_config = {"from_attributes": True}


class PurchaseInvoiceUploadListResponse(BaseModel):
    """Response schema for listing purchase invoice uploads"""
    success: bool
    uploads: List[PurchaseInvoiceUploadResponse]
    total: int
    page: int
    page_size: int


class PurchaseInvoiceConfirmRequest(BaseModel):
    """Request schema for confirming a purchase invoice"""
    create_vendor_transaction: bool = Field(default=True, description="Create vendor transaction on confirm")
    update_stock_ledger: bool = Field(default=True, description="Update stock ledger on confirm")
    update_accounts_payable: bool = Field(default=True, description="Create AP entry if credit purchase")
    update_party_ledger: bool = Field(default=True, description="Update party ledger for vendor")
    confirmation_notes: Optional[str] = None


class PurchaseInvoiceRejectRequest(BaseModel):
    """Request schema for rejecting a purchase invoice"""
    rejection_reason: str = Field(..., min_length=5, max_length=500)


# ==================== VENDOR MASTER SCHEMAS ====================

class PaymentTerms(str, Enum):
    """Payment terms enum - aligned with model constraint"""
    ADVANCE = "ADVANCE"
    COD = "COD"
    CREDIT_15 = "CREDIT_15"
    CREDIT_30 = "CREDIT_30"
    CREDIT_45 = "CREDIT_45"
    CREDIT_60 = "CREDIT_60"


class VendorMasterBase(BaseModel):
    """Base schema for Vendor Master - aligned with model fields
    DC_VENDOR_002: Enhanced with 2 contact persons, map links, product associations
    """
    vendor_name: str = Field(..., min_length=2, max_length=200, description="Vendor name")
    vendor_type: str = Field(default="BOTH", description="Vendor type: PRODUCT, SERVICE, BOTH")
    
    contact_person: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=200)
    
    contact_person_1_name: Optional[str] = Field(None, max_length=200, description="Contact Person 1 Name")
    contact_person_1_phone: Optional[str] = Field(None, max_length=20, description="Contact Person 1 Phone")
    contact_person_1_designation: Optional[str] = Field(None, max_length=100, description="Contact Person 1 Designation")
    
    contact_person_2_name: Optional[str] = Field(None, max_length=200, description="Contact Person 2 Name")
    contact_person_2_phone: Optional[str] = Field(None, max_length=20, description="Contact Person 2 Phone")
    contact_person_2_designation: Optional[str] = Field(None, max_length=100, description="Contact Person 2 Designation")
    
    address: Optional[str] = Field(None, description="Full address")
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=10)
    
    map_link_1: Optional[str] = Field(None, max_length=500, description="Google Maps link for location 1")
    map_link_1_label: Optional[str] = Field(None, max_length=100, description="Label for map link 1 (e.g., Office)")
    map_link_2: Optional[str] = Field(None, max_length=500, description="Google Maps link for location 2")
    map_link_2_label: Optional[str] = Field(None, max_length=100, description="Label for map link 2 (e.g., Warehouse)")
    
    gst_number: Optional[str] = Field(None, max_length=20)
    pan_number: Optional[str] = Field(None, max_length=15)
    
    bank_name: Optional[str] = Field(None, max_length=200)
    bank_branch: Optional[str] = Field(None, max_length=200)
    account_number: Optional[str] = Field(None, max_length=30)
    ifsc_code: Optional[str] = Field(None, max_length=15)
    account_holder_name: Optional[str] = Field(None, max_length=200, description="Bank account holder name")
    
    upi_id: Optional[str] = Field(None, max_length=100, description="UPI ID for payments")
    website_url: Optional[str] = Field(None, max_length=300, description="Vendor website URL")
    terms_conditions: Optional[str] = Field(None, description="Custom terms and conditions")
    
    ship_to_address: Optional[str] = Field(None, description="Shipping address")
    ship_to_city: Optional[str] = Field(None, max_length=100)
    ship_to_state: Optional[str] = Field(None, max_length=100)
    ship_to_pincode: Optional[str] = Field(None, max_length=10)
    
    payment_terms: str = Field(default="COD", description="Payment terms: ADVANCE, COD, CREDIT_15, CREDIT_30, CREDIT_45, CREDIT_60")
    credit_limit: Decimal = Field(default=Decimal("0.00"), ge=0)
    credit_days: int = Field(default=0, ge=0, le=365)

    gst_type: str = Field(default="CGST_SGST", description="GST treatment: CGST_SGST (intra-state) or IGST (inter-state)")

    mnre_empanelled: Optional[bool] = Field(None, description="MNRE empanelled status")
    mnre_reg_no: Optional[str] = Field(None, max_length=50, description="MNRE registration number")
    stamp_image_url: Optional[str] = Field(None, description="Vendor stamp image URL")
    rep_signature_url: Optional[str] = Field(None, description="Authorized representative signature image URL (appears on all Vendor Signature with Stamp blocks)")
    tech_signature_url: Optional[str] = Field(None, description="Technician/Site-Engineer signature image URL (Commissioning Report, Site-Eng blocks)")

    model_config = {"extra": "forbid"}
    
    @field_validator('vendor_type')
    @classmethod
    def validate_vendor_type(cls, v):
        valid_types = ['PRODUCT', 'SERVICE', 'BOTH', 'SOLAR']
        if v and v.upper() not in valid_types:
            raise ValueError(f'Vendor type must be one of: {valid_types}')
        return v.upper() if v else 'BOTH'

    @field_validator('gst_type')
    @classmethod
    def validate_gst_type(cls, v):
        valid_types = ['CGST_SGST', 'IGST']
        if v and v.upper() not in valid_types:
            raise ValueError(f'GST type must be one of: {valid_types}')
        return v.upper() if v else 'CGST_SGST'
    
    @field_validator('payment_terms')
    @classmethod
    def validate_payment_terms(cls, v):
        valid_terms = ['ADVANCE', 'COD', 'CREDIT_15', 'CREDIT_30', 'CREDIT_45', 'CREDIT_60']
        if v and v.upper() not in valid_terms:
            raise ValueError(f'Payment terms must be one of: {valid_terms}')
        return v.upper() if v else 'COD'
    
    @field_validator('gst_number')
    @classmethod
    def validate_gst(cls, v):
        if v:
            v = v.upper().strip()
            if len(v) != 15:
                raise ValueError('GST number must be exactly 15 characters')
        return v
    
    @field_validator('pan_number')
    @classmethod
    def validate_pan(cls, v):
        if v:
            v = v.upper().strip()
            if len(v) != 10:
                raise ValueError('PAN number must be exactly 10 characters')
        return v
    
    @field_validator('ifsc_code')
    @classmethod
    def validate_ifsc(cls, v):
        if v:
            v = v.upper().strip()
            if len(v) != 11:
                raise ValueError('IFSC code must be exactly 11 characters')
        return v


class VendorMasterCreate(VendorMasterBase):
    """Schema for creating Vendor Master - aligned with model fields
    DC_VENDOR_002: Enhanced with product associations
    """
    vendor_code: str = Field(..., min_length=2, max_length=20, description="Unique vendor code")
    applicable_companies: Optional[List[Union[int, str]]] = Field(default=["ALL"], description="List of company IDs or codes like 'ALL'")
    product_ids: Optional[List[int]] = Field(default=None, description="List of stock item IDs to associate with this vendor")
    is_active: bool = Field(default=True)

    opening_balance: Decimal = Field(default=Decimal("0.00"), ge=0, description="Opening balance for party ledger")
    opening_balance_type: str = Field(default="CREDIT", description="DEBIT or CREDIT")
    opening_balance_date: Optional[date] = Field(default=None, description="As-of date for opening balance")
    opening_balances: Optional[List[Dict[str, Any]]] = Field(default=None, description="Per-company OB: [{company_id, amount, type, date}]")

    @field_validator('opening_balance_type')
    @classmethod
    def validate_ob_type(cls, v):
        if v and v.upper() not in ('DEBIT', 'CREDIT'):
            raise ValueError("opening_balance_type must be DEBIT or CREDIT")
        return v.upper() if v else 'CREDIT'

    @field_validator('vendor_code')
    @classmethod
    def validate_vendor_code(cls, v):
        if v:
            v = v.upper().strip()
            if not v.replace('_', '').replace('-', '').isalnum():
                raise ValueError('Vendor code must be alphanumeric with underscores/hyphens only')
        return v


class VendorMasterUpdate(BaseModel):
    """Schema for updating Vendor Master - aligned with model fields
    DC_VENDOR_002: Enhanced with 2 contact persons, map links, product associations
    """
    vendor_name: Optional[str] = Field(None, min_length=2, max_length=200)
    vendor_type: Optional[str] = None
    
    contact_person: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=200)
    
    contact_person_1_name: Optional[str] = Field(None, max_length=200)
    contact_person_1_phone: Optional[str] = Field(None, max_length=20)
    contact_person_1_designation: Optional[str] = Field(None, max_length=100)
    
    contact_person_2_name: Optional[str] = Field(None, max_length=200)
    contact_person_2_phone: Optional[str] = Field(None, max_length=20)
    contact_person_2_designation: Optional[str] = Field(None, max_length=100)
    
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=10)
    
    map_link_1: Optional[str] = Field(None, max_length=500)
    map_link_1_label: Optional[str] = Field(None, max_length=100)
    map_link_2: Optional[str] = Field(None, max_length=500)
    map_link_2_label: Optional[str] = Field(None, max_length=100)
    
    gst_number: Optional[str] = Field(None, max_length=20)
    pan_number: Optional[str] = Field(None, max_length=15)
    
    bank_name: Optional[str] = Field(None, max_length=200)
    bank_branch: Optional[str] = Field(None, max_length=200)
    account_number: Optional[str] = Field(None, max_length=30)
    ifsc_code: Optional[str] = Field(None, max_length=15)
    account_holder_name: Optional[str] = Field(None, max_length=200)
    
    upi_id: Optional[str] = Field(None, max_length=100)
    website_url: Optional[str] = Field(None, max_length=300)
    terms_conditions: Optional[str] = None
    
    ship_to_address: Optional[str] = None
    ship_to_city: Optional[str] = Field(None, max_length=100)
    ship_to_state: Optional[str] = Field(None, max_length=100)
    ship_to_pincode: Optional[str] = Field(None, max_length=10)
    
    payment_terms: Optional[str] = None
    credit_limit: Optional[Decimal] = Field(None, ge=0)
    credit_days: Optional[int] = Field(None, ge=0, le=365)

    gst_type: Optional[str] = Field(None, description="GST treatment: CGST_SGST (intra-state) or IGST (inter-state)")

    mnre_empanelled: Optional[bool] = Field(None, description="MNRE empanelled status")
    mnre_reg_no: Optional[str] = Field(None, max_length=50, description="MNRE registration number")
    stamp_image_url: Optional[str] = Field(None, description="Vendor stamp image URL")
    rep_signature_url: Optional[str] = Field(None, description="Authorized representative signature image URL")
    tech_signature_url: Optional[str] = Field(None, description="Technician/Site-Engineer signature image URL for solar documents")

    applicable_companies: Optional[List[Union[int, str]]] = Field(default=None, description="List of company IDs or codes like 'ALL'")
    product_ids: Optional[List[int]] = Field(default=None, description="List of stock item IDs to associate")
    is_active: Optional[bool] = None

    opening_balance: Optional[Decimal] = Field(default=None, ge=0, description="Override opening balance on party ledger")
    opening_balance_type: Optional[str] = Field(default=None, description="DEBIT or CREDIT")
    opening_balance_date: Optional[date] = Field(default=None, description="As-of date for opening balance")
    opening_balances: Optional[List[Dict[str, Any]]] = Field(default=None, description="Per-company OB: [{company_id, amount, type, date}]")

    @field_validator('opening_balance_type')
    @classmethod
    def validate_ob_type(cls, v):
        if v is not None and v.upper() not in ('DEBIT', 'CREDIT'):
            raise ValueError("opening_balance_type must be DEBIT or CREDIT")
        return v.upper() if v else v

    model_config = {"extra": "ignore"}

    @field_validator('vendor_type')
    @classmethod
    def validate_vendor_type(cls, v):
        if v:
            valid_types = ['PRODUCT', 'SERVICE', 'BOTH', 'SOLAR']
            if v.upper() not in valid_types:
                raise ValueError(f'Vendor type must be one of: {valid_types}')
            return v.upper()
        return v

    @field_validator('payment_terms')
    @classmethod
    def validate_payment_terms(cls, v):
        if v:
            valid_terms = ['ADVANCE', 'COD', 'CREDIT_15', 'CREDIT_30', 'CREDIT_45', 'CREDIT_60']
            if v.upper() not in valid_terms:
                raise ValueError(f'Payment terms must be one of: {valid_terms}')
            return v.upper()
        return v

    @field_validator('gst_number', 'pan_number', 'ifsc_code', mode='before')
    @classmethod
    def normalise_code_fields(cls, v):
        if not v:
            return None
        return str(v).upper().strip() or None


class VendorProductAssociationRequest(BaseModel):
    """Request schema for associating products with a vendor"""
    product_ids: List[int] = Field(..., description="List of stock item IDs")
    
    model_config = {"extra": "forbid"}


class PinCodeLookupResponse(BaseModel):
    """Response schema for PIN code lookup"""
    success: bool
    pincode: str
    state: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    message: Optional[str] = None


class VendorMasterResponse(BaseModel):
    """Response schema for Vendor Master - aligned with model fields"""
    id: int
    vendor_code: str
    vendor_name: str
    vendor_type: str
    
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    account_holder_name: Optional[str] = None
    
    upi_id: Optional[str] = None
    website_url: Optional[str] = None
    terms_conditions: Optional[str] = None
    
    ship_to_address: Optional[str] = None
    ship_to_city: Optional[str] = None
    ship_to_state: Optional[str] = None
    ship_to_pincode: Optional[str] = None
    
    payment_terms: Optional[str] = None
    credit_limit: Optional[Decimal] = Decimal("0.00")
    credit_days: Optional[int] = 0

    gst_type: Optional[str] = "CGST_SGST"

    mnre_empanelled: Optional[bool] = None
    mnre_reg_no: Optional[str] = None
    stamp_image_url: Optional[str] = None

    applicable_companies: Optional[Any] = []
    is_active: bool

    opening_balance: Optional[Decimal] = None
    opening_balance_type: Optional[str] = None
    opening_balance_date: Optional[date] = None

    created_by_id: Optional[int] = None
    updated_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class VendorMasterListResponse(BaseModel):
    """Response schema for listing vendors"""
    success: bool
    vendors: List[VendorMasterResponse]
    total: int
    page: int = 1
    page_size: int = 20


# ==================== EXPENSE CATEGORY SCHEMAS (SFMS Staff Access) ====================

class ExpenseMainCategoryCreate(BaseModel):
    """Schema for creating Expense Main Category - SFMS staff system"""
    name: str = Field(..., min_length=2, max_length=100, description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    
    model_config = {"extra": "forbid"}


class ExpenseMainCategoryUpdate(BaseModel):
    """Schema for updating Expense Main Category - SFMS staff system"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    
    model_config = {"extra": "forbid"}


class ExpenseSubCategoryCreate(BaseModel):
    """Schema for creating Expense Sub Category - SFMS staff system"""
    name: str = Field(..., min_length=2, max_length=100, description="Sub-category name")
    main_category_id: int = Field(..., description="Parent main category ID")
    description: Optional[str] = Field(None, description="Sub-category description")
    
    model_config = {"extra": "forbid"}


class ExpenseSubCategoryUpdate(BaseModel):
    """Schema for updating Expense Sub Category - SFMS staff system"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    
    model_config = {"extra": "forbid"}


class ExpenseSubCategoryResponse(BaseModel):
    """Response schema for Expense Sub Category - SFMS staff system"""
    id: int
    name: str
    description: Optional[str] = None
    main_category_id: int
    is_active: bool
    created_by_id: Optional[str] = None
    updated_by_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ExpenseMainCategoryResponse(BaseModel):
    """Response schema for Expense Main Category with nested sub-categories"""
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    created_by_id: Optional[str] = None
    updated_by_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sub_categories: List[ExpenseSubCategoryResponse] = []
    
    model_config = {"from_attributes": True}


class ExpenseMainCategorySimpleResponse(BaseModel):
    """Response schema for Expense Main Category without nested sub-categories"""
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    created_by_id: Optional[str] = None
    updated_by_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ExpenseMainCategoryListResponse(BaseModel):
    """Response schema for listing main categories"""
    success: bool
    categories: List[ExpenseMainCategoryResponse]
    total: int
    page: int = 1
    page_size: int = 20


class ExpenseSubCategoryListResponse(BaseModel):
    """Response schema for listing sub-categories"""
    success: bool
    sub_categories: List[ExpenseSubCategoryResponse]
    total: int
    page: int = 1
    page_size: int = 20


# ==================== STOCK ITEM MASTER SCHEMAS ====================

class ItemCategory(str, Enum):
    """Item category enum - aligned with model constraint"""
    PRODUCT = "PRODUCT"
    RAW_MATERIAL = "RAW_MATERIAL"
    CONSUMABLE = "CONSUMABLE"
    SPARE_PART = "SPARE_PART"
    ACCESSORY = "ACCESSORY"


class UnitOfMeasure(str, Enum):
    """Unit of measure enum - aligned with model constraint"""
    PCS = "PCS"
    KG = "KG"
    LTR = "LTR"
    MTR = "MTR"
    SET = "SET"
    BOX = "BOX"
    PACK = "PACK"
    PAIR = "PAIR"
    UNIT = "UNIT"


class StockItemMasterBase(BaseModel):
    """Base schema for Stock Item Master - aligned with model fields
    DC_STOCK_003: Multi-company selection with applicable_companies"""
    item_name: str = Field(..., min_length=2, max_length=200, description="Item name")
    item_category: str = Field(default="PRODUCT", description="Category: PRODUCT, RAW_MATERIAL, CONSUMABLE, SPARE_PART, ACCESSORY")
    
    applicable_companies: List[int] = Field(default=[], description="List of company IDs this item is applicable to")
    
    description: Optional[str] = Field(None, description="Item description")
    brand: Optional[str] = Field(None, max_length=150, description="Brand / manufacturer name")
    model_compat: Optional[str] = Field(None, max_length=300, description="Compatible with / Model (from marketplace)")
    specification: Optional[str] = Field(None, description="Item specifications")
    size: Optional[str] = Field(None, max_length=100, description="Item size/dimensions")
    colors: Optional[List[str]] = Field(None, description="Available colors")
    
    unit_of_measure: str = Field(default="PCS", description="Unit: PCS, KG, LTR, MTR, SET, BOX, PACK, PAIR, UNIT")
    hsn_code: Optional[str] = Field(None, max_length=20, description="HSN/SAC code")
    hsn_id: Optional[int] = Field(None, description="Foreign key to HSN Master")
    default_gst_rate: Decimal = Field(default=Decimal("18.00"), ge=0, le=100, description="Default GST rate")
    
    reorder_level: int = Field(default=0, ge=0, description="Reorder level quantity")
    
    purchase_rate: Decimal = Field(default=Decimal("0.00"), ge=0, description="Purchase rate")
    selling_rate: Decimal = Field(default=Decimal("0.00"), ge=0, description="Selling rate")
    
    model_config = {"extra": "forbid"}
    
    @field_validator('item_category')
    @classmethod
    def validate_category(cls, v):
        if not v:
            return 'PRODUCT'
        cleaned = v.upper().strip().replace(' ', '_')
        if len(cleaned) < 2 or len(cleaned) > 50:
            raise ValueError('Item category must be 2–50 characters')
        # DC-STOCK-CAT-001: Allow any valid string — no fixed list restriction
        return cleaned
    
    @field_validator('unit_of_measure')
    @classmethod
    def validate_uom(cls, v):
        valid_uom = ['PCS', 'KG', 'LTR', 'MTR', 'SET', 'BOX', 'PACK', 'PAIR', 'UNIT']
        if v and v.upper() not in valid_uom:
            raise ValueError(f'Unit of measure must be one of: {valid_uom}')
        return v.upper() if v else 'PCS'
    
    @field_validator('hsn_code')
    @classmethod
    def validate_hsn(cls, v):
        if v:
            v = v.strip()
            if v and (not v.isdigit() or len(v) < 4 or len(v) > 8):
                raise ValueError('HSN code must be 4-8 digits')
        return v


class StockItemMasterCreate(StockItemMasterBase):
    """Schema for creating Stock Item Master - aligned with model fields"""
    item_code: Optional[str] = Field(None, min_length=2, max_length=30, description="Unique item code — auto-generated if omitted")
    default_vendor_id: Optional[int] = Field(None, description="Default vendor ID")
    is_active: bool = Field(default=True)
    
    @field_validator('item_code')
    @classmethod
    def validate_item_code(cls, v):
        if v:
            v = v.upper().strip()
            if not v.replace('_', '').replace('-', '').isalnum():
                raise ValueError('Item code must be alphanumeric with underscores/hyphens only')
        return v


class StockItemMasterUpdate(BaseModel):
    """Schema for updating Stock Item Master - aligned with model fields
    DC_STOCK_003: Multi-company selection with applicable_companies
    DC_STOCK_MKTLINK_001: marketplace_sku for single-source-of-truth bridge"""
    item_name: Optional[str] = Field(None, min_length=2, max_length=200)
    item_category: Optional[str] = None
    
    applicable_companies: Optional[List[int]] = Field(None, description="List of company IDs")
    
    description: Optional[str] = None
    brand: Optional[str] = Field(None, max_length=150, description="Brand / manufacturer name")
    model_compat: Optional[str] = Field(None, max_length=300, description="Compatible with / Model")
    specification: Optional[str] = Field(None, description="Item specifications")
    size: Optional[str] = Field(None, max_length=100, description="Item size/dimensions")
    colors: Optional[List[str]] = Field(None, description="Available colors")
    
    unit_of_measure: Optional[str] = None
    hsn_code: Optional[str] = Field(None, max_length=20)
    hsn_id: Optional[int] = None
    default_gst_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    
    reorder_level: Optional[int] = Field(None, ge=0)
    default_vendor_id: Optional[int] = None
    
    purchase_rate: Optional[Decimal] = Field(None, ge=0)
    selling_rate: Optional[Decimal] = Field(None, ge=0)
    
    is_active: Optional[bool] = None
    marketplace_sku: Optional[str] = Field(None, max_length=120, description="Marketplace SKU to link for price+qty sync")
    
    model_config = {"extra": "forbid"}
    
    @field_validator('item_category')
    @classmethod
    def validate_category(cls, v):
        if v:
            cleaned = v.upper().strip().replace(' ', '_')
            if len(cleaned) < 2 or len(cleaned) > 50:
                raise ValueError('Item category must be 2–50 characters')
            # DC-STOCK-CAT-001: Allow any valid string — no fixed list restriction
            return cleaned
        return v
    
    @field_validator('unit_of_measure')
    @classmethod
    def validate_uom(cls, v):
        if v:
            valid_uom = ['PCS', 'KG', 'LTR', 'MTR', 'SET', 'BOX', 'PACK', 'PAIR', 'UNIT']
            if v.upper() not in valid_uom:
                raise ValueError(f'Unit of measure must be one of: {valid_uom}')
            return v.upper()
        return v
    
    @field_validator('hsn_code')
    @classmethod
    def validate_hsn(cls, v):
        if v:
            v = v.strip()
            if v and (not v.isdigit() or len(v) < 4 or len(v) > 8):
                raise ValueError('HSN code must be 4-8 digits')
        return v


class StockItemBulkUploadRow(BaseModel):
    """Schema for a single row in bulk stock item upload"""
    row_number: int
    item_code: str
    item_name: str
    item_category: str = "PRODUCT"
    applicable_companies: Optional[str] = None
    unit_of_measure: str = "PCS"
    description: Optional[str] = None
    specification: Optional[str] = None
    size: Optional[str] = None
    colors: Optional[str] = None
    hsn_code: Optional[str] = None
    default_gst_rate: Optional[Decimal] = Decimal("18.00")
    reorder_level: Optional[int] = 0
    purchase_rate: Optional[Decimal] = Decimal("0.00")
    selling_rate: Optional[Decimal] = Decimal("0.00")


class StockItemBulkUploadError(BaseModel):
    """Schema for bulk upload error details"""
    row_number: int
    item_code: Optional[str] = None
    item_name: Optional[str] = None
    errors: List[str]
    original_data: dict


class StockItemBulkUploadResult(BaseModel):
    """Schema for bulk upload result"""
    success: bool
    total_rows: int
    created_count: int
    error_count: int
    errors: List[StockItemBulkUploadError] = []
    created_items: List[str] = []


class StockItemMasterResponse(BaseModel):
    """Response schema for Stock Item Master - aligned with model fields
    DC_STOCK_003: Multi-company selection with applicable_companies
    DC_STOCK_MKTLINK_001: marketplace_sku + marketplace_linked for bridge status"""
    id: int
    item_code: str
    item_name: str
    item_category: str
    
    applicable_companies: List[int] = []
    
    description: Optional[str] = None
    brand: Optional[str] = None
    model_compat: Optional[str] = None
    specification: Optional[str] = None
    size: Optional[str] = None
    colors: Optional[List[str]] = None
    
    unit_of_measure: str
    hsn_code: Optional[str] = None
    hsn_id: Optional[int] = None
    default_gst_rate: Optional[Decimal] = None
    
    reorder_level: int = 0
    default_vendor_id: Optional[int] = None
    
    purchase_rate: Decimal = Decimal("0.00")
    selling_rate: Decimal = Decimal("0.00")

    marketplace_sku: Optional[str] = None
    marketplace_linked: bool = False
    
    is_active: bool
    
    created_by_id: Optional[int] = None
    updated_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    images: List[dict] = Field(default_factory=list, description="Stock item images")
    primary_image: Optional[str] = Field(None, description="Primary image compressed path for thumbnail")
    
    model_config = {"from_attributes": True}

    @model_validator(mode='after')
    def _set_marketplace_linked(self) -> 'StockItemMasterResponse':
        self.marketplace_linked = bool(self.marketplace_sku)
        return self


class StockItemMasterListResponse(BaseModel):
    """Response schema for listing stock items"""
    success: bool
    stock_items: List[StockItemMasterResponse]
    total: int
    page: int = 1
    page_size: int = 20


# ==================== STOCK ITEM IMAGE SCHEMAS ====================

class StockItemImageResponse(BaseModel):
    """Response schema for Stock Item Images
    DC_STOCK_004: Multiple images per stock item with DC Protocol dual evidence
    """
    id: int
    stock_item_id: int
    original_path: str
    compressed_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    file_name: str
    file_size: Optional[int] = None
    compressed_size: Optional[int] = None
    mime_type: Optional[str] = None
    is_primary: bool = False
    display_order: int = 0
    source_type: str = "upload"
    source_url: Optional[str] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class StockItemImageUploadResponse(BaseModel):
    """Response schema for image upload result"""
    success: bool
    message: str
    image: Optional[StockItemImageResponse] = None


class StockItemImagesListResponse(BaseModel):
    """Response schema for listing stock item images"""
    success: bool
    stock_item_id: int
    images: List[StockItemImageResponse]
    total: int


# ==================== PRICING CONFIGURATION SCHEMAS ====================

class PricingConfigurationBase(BaseModel):
    """Base schema for Pricing Configuration"""
    default_markup_pct: Decimal = Field(default=Decimal("20.00"), ge=0, le=100, 
                                         description="Default markup percentage (20% = cost + 20%)")
    incentive_share_pct: Decimal = Field(default=Decimal("50.00"), ge=0, le=100,
                                          description="Employee incentive share (50% of profit)")
    min_markup_pct: Decimal = Field(default=Decimal("0.00"), ge=0, le=100,
                                     description="Minimum allowed markup (0 = cannot go below cost)")
    
    description: Optional[str] = Field(None, max_length=500)
    
    model_config = {"extra": "forbid"}
    
    @model_validator(mode='after')
    def validate_markup_constraints(self):
        if self.min_markup_pct > self.default_markup_pct:
            raise ValueError('Minimum markup cannot exceed default markup')
        return self


class PricingConfigurationCreate(PricingConfigurationBase):
    """Schema for creating Pricing Configuration"""
    company_id: int = Field(..., gt=0, description="Associated company ID")
    is_active: bool = Field(default=True)


class PricingConfigurationUpdate(BaseModel):
    """Schema for updating Pricing Configuration"""
    default_markup_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    incentive_share_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    min_markup_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    
    model_config = {"extra": "forbid"}


class PricingConfigurationResponse(BaseModel):
    """Response schema for Pricing Configuration"""
    id: int
    company_id: int
    company_name: Optional[str] = None
    config_type: Optional[str] = None
    
    default_markup_pct: Decimal
    incentive_pct: Decimal
    min_markup_pct: Decimal
    max_markup_pct: Optional[Decimal] = None
    allow_below_cost: bool = False
    
    description: Optional[str] = None
    is_active: bool
    
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class PricingConfigurationListResponse(BaseModel):
    """Response schema for listing pricing configurations"""
    success: bool
    pricing_configurations: List[PricingConfigurationResponse]
    total: int


# ==================== COMMON RESPONSE SCHEMAS ====================

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# ==================== PRICE CALCULATION PREVIEW ====================

class PriceCalculationPreview(BaseModel):
    """Preview of price calculation with incentive"""
    purchase_cost: Decimal
    markup_pct: Decimal
    default_price: Decimal
    custom_price: Optional[Decimal] = None
    final_price: Decimal
    profit_per_unit: Decimal
    incentive_pct: Decimal
    incentive_amount: Decimal
    is_below_cost: bool = False
    
    model_config = {"from_attributes": True}


class PriceCalculationRequest(BaseModel):
    """Request for price calculation preview"""
    purchase_cost: Decimal = Field(..., ge=0)
    markup_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    custom_price: Optional[Decimal] = Field(None, ge=0)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    incentive_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    company_id: Optional[int] = None
    
    model_config = {"extra": "forbid"}


# ==================== INCOME ENTRY SCHEMAS ====================

class PaymentMode(str, Enum):
    """Payment mode enum - aligned with model constraint"""
    CASH = "CASH"
    BANK = "BANK"
    UPI = "UPI"
    CHEQUE = "CHEQUE"
    DD = "DD"
    NEFT = "NEFT"
    RTGS = "RTGS"
    CARD = "CARD"


class IncomeStatus(str, Enum):
    """Income entry status enum"""
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class TallyStatus(str, Enum):
    """Tally sync status enum"""
    NOT_SYNCED = "NOT_SYNCED"
    SELECTED = "SELECTED"
    EXPORTED = "EXPORTED"
    SYNCED = "SYNCED"
    MISMATCH = "MISMATCH"
    EXCLUDED = "EXCLUDED"


class IncomeEntryBase(BaseModel):
    company_id: int = Field(..., gt=0, description="Associated company ID")
    segment_id: Optional[int] = Field(None, description="Company segment ID")
    income_source_id: int = Field(..., gt=0, description="Income source type ID")
    revenue_category_id: Optional[int] = Field(None, description="Revenue category ID")
    
    income_date: date = Field(..., description="Date of income")
    amount: Decimal = Field(..., gt=0, description="Income amount")
    
    reference_type: Optional[str] = Field(None, max_length=30, description="Reference type (e.g., MNR_USER, INVOICE)")
    reference_id: Optional[str] = Field(None, max_length=50, description="Reference ID")
    
    payment_mode: str = Field(..., description="Payment mode: CASH, BANK, UPI, CHEQUE, DD, NEFT, RTGS, CARD")
    payment_type: Optional[str] = Field(None, description="High-level payment type: CASH or BANK")
    payment_reference: Optional[str] = Field(None, max_length=100, description="Payment reference number")
    payment_date: Optional[date] = Field(None, description="Date of payment")
    
    payer_name: Optional[str] = Field(None, max_length=200, description="Payer name")
    payer_contact: Optional[str] = Field(None, max_length=50, description="Payer contact")
    payer_address: Optional[str] = Field(None, description="Payer address")
    
    narration: Optional[str] = Field(None, description="Transaction narration")
    show_in_ledger: Optional[bool] = Field(False, description="DC-SHOW-IN-LEDGER-001: if true, this entry posts to the transaction ledger")
    
    model_config = {"extra": "forbid"}
    
    @field_validator('payment_mode')
    @classmethod
    def validate_payment_mode(cls, v):
        valid_modes = ['CASH', 'BANK', 'UPI', 'CHEQUE', 'DD', 'NEFT', 'RTGS', 'CARD']
        if v and v.upper() not in valid_modes:
            raise ValueError(f'Payment mode must be one of: {valid_modes}')
        return v.upper() if v else v

    @field_validator('payment_type')
    @classmethod
    def validate_payment_type(cls, v):
        if v is not None and v.upper() not in ['CASH', 'BANK']:
            raise ValueError('payment_type must be CASH or BANK')
        return v.upper() if v else v


class IncomeEntryCreate(IncomeEntryBase):
    """Schema for creating Income Entry"""
    transaction_type: Optional[str] = Field(None, max_length=20, description="SALES_RETURN for credit notes")
    return_reference: Optional[str] = Field(None, max_length=100, description="Original entry/invoice ref for returns")


class IncomeEntryUpdate(BaseModel):
    company_id: Optional[int] = Field(None, gt=0, description="Override company for the income entry")
    segment_id: Optional[int] = None
    income_source_id: Optional[int] = Field(None, gt=0)
    revenue_category_id: Optional[int] = None
    
    income_date: Optional[date] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    
    reference_type: Optional[str] = Field(None, max_length=30)
    reference_id: Optional[str] = Field(None, max_length=50)
    
    payment_mode: Optional[str] = None
    payment_type: Optional[str] = None
    payment_reference: Optional[str] = Field(None, max_length=100)
    payment_date: Optional[date] = None
    
    payer_name: Optional[str] = Field(None, max_length=200)
    payer_contact: Optional[str] = Field(None, max_length=50)
    payer_address: Optional[str] = None
    
    narration: Optional[str] = None
    show_in_ledger: Optional[bool] = None

    destination_type: Optional[str] = Field(None, max_length=20, description="COMPANY_ACCOUNT or EMPLOYEE")
    destination_company_id: Optional[int] = None
    destination_employee_id: Optional[int] = None
    
    model_config = {"extra": "forbid"}
    
    @field_validator('payment_mode')
    @classmethod
    def validate_payment_mode(cls, v):
        if v:
            valid_modes = ['CASH', 'BANK', 'UPI', 'CHEQUE', 'DD', 'NEFT', 'RTGS', 'CARD']
            if v.upper() not in valid_modes:
                raise ValueError(f'Payment mode must be one of: {valid_modes}')
            return v.upper()
        return v

    @field_validator('payment_type')
    @classmethod
    def validate_payment_type(cls, v):
        if v is not None and v.upper() not in ['CASH', 'BANK']:
            raise ValueError('payment_type must be CASH or BANK')
        return v.upper() if v else v

    @field_validator('destination_type')
    @classmethod
    def validate_destination_type(cls, v):
        if v is not None and v.upper() not in ['COMPANY_ACCOUNT', 'EMPLOYEE', 'SOLAR_VENDOR']:
            raise ValueError('destination_type must be COMPANY_ACCOUNT, EMPLOYEE or SOLAR_VENDOR')
        return v.upper() if v else v


class IncomeEntryStatusUpdate(BaseModel):
    status: str = Field(..., description="New status: CONFIRMED, ESTIMATED, EXCEPTION_TALLY, ADJUSTMENT, TALLY_DONE")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for status change")
    # DC-ESTIMATIONS-001: taxed/estimated confirmation split
    confirmation_type: Optional[str] = Field(None, description="TAXED or ESTIMATED (used when confirming PENDING)")
    bank_account_name: Optional[str] = Field(None, max_length=200, description="Override account name for TAXED posting")
    bank_account_id: Optional[int] = Field(None, description="account_ledger_masters.id for TAXED confirmation")
    payer_name: Optional[str] = Field(None, max_length=200, description="Override payer name for TAXED party ledger")
    company_id: Optional[int] = Field(None, description="Override company for the income entry")
    solar_vendor_id: Optional[int] = Field(None, description="DC-SOLAR-VENDOR-LEDGER-001: solar vendor selected at confirmation")
    # DC-DEST-AT-CONFIRM-001: destination routing settable at confirm time
    destination_type: Optional[str] = Field(None, description="COMPANY_ACCOUNT, EMPLOYEE or SOLAR_VENDOR")
    destination_company_id: Optional[int] = Field(None, description="destination_company_id when COMPANY_ACCOUNT")
    destination_employee_id: Optional[int] = Field(None, description="destination_employee_id when EMPLOYEE")

    model_config = {"extra": "ignore"}

    @field_validator('destination_type')
    @classmethod
    def validate_dest_type(cls, v):
        if v is not None and v.upper() not in ['COMPANY_ACCOUNT', 'EMPLOYEE', 'SOLAR_VENDOR']:
            raise ValueError('destination_type must be COMPANY_ACCOUNT, EMPLOYEE or SOLAR_VENDOR')
        return v.upper() if v else v

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ['PENDING', 'CONFIRMED', 'ESTIMATED', 'EXCEPTION_TALLY', 'ADJUSTMENT', 'TALLY_DONE']
        if v and v.upper() not in valid_statuses:
            raise ValueError(f'Status must be one of: {valid_statuses}')
        return v.upper() if v else v


class IncomeEntryResponse(BaseModel):
    id: int
    entry_number: str
    company_id: int
    segment_id: Optional[int] = None
    income_source_id: int
    revenue_category_id: Optional[int] = None
    crm_transaction_id: Optional[int] = None
    
    income_date: date
    amount: Decimal
    
    transaction_type: Optional[str] = None
    
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    
    payment_mode: str
    payment_type: Optional[str] = None
    payment_reference: Optional[str] = None
    payment_date: Optional[date] = None
    
    payer_name: Optional[str] = None
    payer_contact: Optional[str] = None
    payer_address: Optional[str] = None
    payer_city: Optional[str] = None
    payer_state: Optional[str] = None
    
    narration: Optional[str] = None
    receipt_path: Optional[str] = None
    
    status: str
    
    lead_id: Optional[int] = None
    lead_owner_id: Optional[int] = None
    collected_by_id: Optional[int] = None
    
    confirmed_by_id: Optional[int] = None
    confirmed_at: Optional[datetime] = None
    verified_by_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    
    tally_status: str = "NOT_SYNCED"
    tally_voucher_no: Optional[str] = None

    destination_type: Optional[str] = None
    destination_company_id: Optional[int] = None
    destination_employee_id: Optional[int] = None
    
    ledger_updated: bool = False
    show_in_ledger: bool = False
    
    created_by_id: Optional[int] = None
    updated_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class IncomeEntryListResponse(BaseModel):
    """Response schema for listing income entries"""
    success: bool
    income_entries: List[IncomeEntryResponse]
    total: int
    page: int = 1
    page_size: int = 20


# ==================== VENDOR TRANSACTION SCHEMAS (Phase 2.9) ====================

class VendorTransactionLineItemCreate(BaseModel):
    """Schema for creating a vendor transaction line item"""
    item_id: Optional[int] = None
    item_code: Optional[str] = None
    item_description: str
    hsn_code: Optional[str] = None
    hsn_id: Optional[int] = None
    
    quantity: Decimal = Decimal("1")
    unit_of_measure: str = "PCS"
    unit_rate: Decimal = Decimal("0")
    
    discount_percent: Decimal = Decimal("0")
    
    gst_rate: Decimal = Decimal("0")
    is_igst: bool = False
    
    product_status: Optional[str] = None
    defective_qty: Decimal = Decimal("0")
    ok_qty: Optional[Decimal] = None
    
    service_status: Optional[str] = None
    service_date: Optional[date] = None
    
    @field_validator('quantity')
    @classmethod
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return v
    
    @field_validator('unit_rate')
    @classmethod
    def unit_rate_non_negative(cls, v):
        if v < 0:
            raise ValueError('Unit rate cannot be negative')
        return v
    
    @field_validator('discount_percent')
    @classmethod
    def discount_in_range(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Discount percent must be between 0 and 100')
        return v
    
    @field_validator('gst_rate')
    @classmethod
    def gst_in_range(cls, v):
        if v < 0 or v > 100:
            raise ValueError('GST rate must be between 0 and 100')
        return v
    
    @field_validator('product_status')
    @classmethod
    def product_status_valid(cls, v):
        if v is not None and v not in ['OK', 'DEFECTIVE', 'PARTIAL_DEFECTIVE']:
            raise ValueError('Product status must be OK, DEFECTIVE, or PARTIAL_DEFECTIVE')
        return v
    
    @field_validator('service_status')
    @classmethod
    def service_status_valid(cls, v):
        if v is not None and v not in ['RECEIVED', 'PENDING', 'PARTIAL']:
            raise ValueError('Service status must be RECEIVED, PENDING, or PARTIAL')
        return v


class VendorTransactionLineItemUpdate(BaseModel):
    """Schema for updating a vendor transaction line item"""
    item_description: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_of_measure: Optional[str] = None
    unit_rate: Optional[Decimal] = None
    discount_percent: Optional[Decimal] = None
    gst_rate: Optional[Decimal] = None
    is_igst: Optional[bool] = None
    product_status: Optional[str] = None
    defective_qty: Optional[Decimal] = None
    ok_qty: Optional[Decimal] = None
    service_status: Optional[str] = None
    service_date: Optional[date] = None


class VendorTransactionLineItemResponse(BaseModel):
    """Response schema for a vendor transaction line item"""
    id: int
    transaction_id: int
    line_number: int
    
    item_id: Optional[int] = None
    item_code: Optional[str] = None
    item_description: str
    hsn_code: Optional[str] = None
    hsn_id: Optional[int] = None
    
    quantity: Decimal
    unit_of_measure: str
    unit_rate: Decimal
    
    discount_percent: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    
    gst_rate: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    
    total_amount: Decimal
    
    product_status: Optional[str] = None
    defective_qty: Decimal
    ok_qty: Decimal
    
    service_status: Optional[str] = None
    service_date: Optional[date] = None
    
    stock_updated: bool
    stock_entry_id: Optional[int] = None
    
    created_at: datetime
    
    model_config = {"from_attributes": True}


class VendorTransactionCreate(BaseModel):
    """Schema for creating a vendor transaction header with nested line items"""
    company_id: int
    segment_id: Optional[int] = None
    vendor_id: int
    
    transaction_date: date
    transaction_type: str
    record_type: str
    
    payment_mode: Optional[str] = None
    payment_reference: Optional[str] = None
    payment_date: Optional[date] = None
    
    vendor_invoice_no: Optional[str] = None
    vendor_invoice_date: Optional[date] = None
    invoice_status: str = "NOT_RECEIVED"
    
    category_id: Optional[int] = None
    narration: Optional[str] = None
    remarks: Optional[str] = None
    
    line_items: List[VendorTransactionLineItemCreate] = []
    
    @field_validator('transaction_type')
    @classmethod
    def transaction_type_valid(cls, v):
        valid_types = ['PURCHASE', 'PAYMENT', 'ADVANCE', 'REFUND', 'DEBIT_NOTE', 'CREDIT_NOTE']
        if v not in valid_types:
            raise ValueError(f'Transaction type must be one of: {", ".join(valid_types)}')
        return v
    
    @field_validator('record_type')
    @classmethod
    def record_type_valid(cls, v):
        valid_types = ['PRODUCT', 'SERVICE']
        if v not in valid_types:
            raise ValueError(f'Record type must be one of: {", ".join(valid_types)}')
        return v
    
    @field_validator('invoice_status')
    @classmethod
    def invoice_status_valid(cls, v):
        valid_statuses = ['NOT_RECEIVED', 'PENDING', 'RECEIVED']
        if v not in valid_statuses:
            raise ValueError(f'Invoice status must be one of: {", ".join(valid_statuses)}')
        return v
    
    @field_validator('payment_mode')
    @classmethod
    def payment_mode_valid(cls, v):
        if v is not None:
            valid_modes = ['CASH', 'BANK_TRANSFER', 'UPI', 'CHEQUE', 'CARD', 'NEFT', 'RTGS', 'OTHER']
            if v not in valid_modes:
                raise ValueError(f'Payment mode must be one of: {", ".join(valid_modes)}')
        return v


class VendorTransactionUpdate(BaseModel):
    """Schema for updating a vendor transaction header (DRAFT status only)"""
    segment_id: Optional[int] = None
    transaction_date: Optional[date] = None
    
    payment_mode: Optional[str] = None
    payment_reference: Optional[str] = None
    payment_date: Optional[date] = None
    amount_paid: Optional[Decimal] = None
    
    vendor_invoice_no: Optional[str] = None
    vendor_invoice_date: Optional[date] = None
    invoice_status: Optional[str] = None
    invoice_received_on: Optional[date] = None
    invoice_path: Optional[str] = None
    
    category_id: Optional[int] = None
    narration: Optional[str] = None
    remarks: Optional[str] = None
    
    round_off: Optional[Decimal] = None


class VendorTransactionStatusChange(BaseModel):
    """Schema for changing vendor transaction status"""
    new_status: str
    reason: Optional[str] = None
    
    @field_validator('new_status')
    @classmethod
    def new_status_valid(cls, v):
        valid_statuses = ['DRAFT', 'SUBMITTED', 'APPROVED', 'PAID', 'CANCELLED', 'REJECTED']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v


class VendorTransactionResponse(BaseModel):
    """Response schema for a vendor transaction with nested line items"""
    id: int
    transaction_number: str
    company_id: int
    segment_id: Optional[int] = None
    vendor_id: int
    
    transaction_date: date
    transaction_type: str
    record_type: str
    
    subtotal: Decimal
    total_discount: Decimal
    taxable_amount: Decimal
    total_cgst: Decimal
    total_sgst: Decimal
    total_igst: Decimal
    total_gst: Decimal
    total_tds: Decimal
    round_off: Decimal
    grand_total: Decimal
    
    payment_mode: Optional[str] = None
    payment_reference: Optional[str] = None
    payment_date: Optional[date] = None
    amount_paid: Decimal
    balance_due: Decimal
    
    vendor_invoice_no: Optional[str] = None
    vendor_invoice_date: Optional[date] = None
    invoice_status: str
    invoice_received_on: Optional[date] = None
    invoice_path: Optional[str] = None
    
    category_id: Optional[int] = None
    narration: Optional[str] = None
    remarks: Optional[str] = None
    
    status: str
    
    created_by_id: Optional[int] = None
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    
    tally_status: str
    tally_voucher_no: Optional[str] = None
    
    ledger_updated: bool
    stock_updated: bool
    
    created_at: datetime
    updated_at: datetime
    
    line_items: List[VendorTransactionLineItemResponse] = []
    
    model_config = {"from_attributes": True}


class VendorTransactionSimpleResponse(BaseModel):
    """Simple response schema for vendor transaction (without line items)"""
    id: int
    transaction_number: str
    company_id: int
    vendor_id: int
    transaction_date: date
    transaction_type: str
    record_type: str
    grand_total: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    status: str
    created_at: datetime
    
    model_config = {"from_attributes": True}


class VendorTransactionListResponse(BaseModel):
    """Response schema for listing vendor transactions"""
    success: bool
    transactions: List[VendorTransactionSimpleResponse]
    total: int
    page: int = 1
    page_size: int = 20


# ==================== SERVICE ITEMS USED SCHEMAS (Phase 2.10) ====================

class ServiceItemUsedCreate(BaseModel):
    """Schema for adding a service item used to a transaction"""
    item_id: int
    quantity_used: Decimal = Decimal("1")
    unit_of_measure: str = "PCS"
    custom_price: Optional[Decimal] = None
    
    @field_validator('quantity_used')
    @classmethod
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Quantity used must be greater than 0')
        return v
    
    @field_validator('custom_price')
    @classmethod
    def custom_price_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError('Custom price cannot be negative')
        return v


class ServiceItemUsedUpdate(BaseModel):
    """Schema for updating a service item used"""
    quantity_used: Optional[Decimal] = None
    custom_price: Optional[Decimal] = None
    
    @field_validator('quantity_used')
    @classmethod
    def quantity_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Quantity used must be greater than 0')
        return v


class ServiceItemUsedResponse(BaseModel):
    """Response schema for a service item used with incentive calculation"""
    id: int
    transaction_id: int
    line_number: int
    
    item_id: int
    item_code: str
    item_name: str
    
    available_stock: Decimal
    quantity_used: Decimal
    unit_of_measure: str
    
    purchase_cost: Decimal
    total_cost: Decimal
    
    default_price: Decimal
    custom_price: Optional[Decimal] = None
    final_price: Decimal
    total_selling: Decimal
    
    profit_per_unit: Decimal
    total_profit: Decimal
    incentive_pct: Decimal
    incentive_amount: Decimal
    
    price_below_cost: bool
    is_custom_price: bool
    
    stock_deducted: bool
    stock_entry_id: Optional[int] = None
    incentive_entry_id: Optional[int] = None
    
    created_at: datetime
    
    model_config = {"from_attributes": True}


class ServiceItemUsedListResponse(BaseModel):
    """Response schema for listing service items used in a transaction"""
    success: bool
    items: List[ServiceItemUsedResponse]
    total: int
    total_selling: Decimal
    total_cost: Decimal
    total_profit: Decimal
    total_incentive: Decimal


class ServiceItemUsedCreateResponse(BaseModel):
    """Response schema for adding a service item"""
    success: bool
    message: str
    item: ServiceItemUsedResponse


# ==================== STOCK LEDGER SCHEMAS (Phase 2.11) ====================

class StockLedgerEntryCreate(BaseModel):
    """Schema for creating a stock ledger entry (internal use)"""
    company_id: int
    segment_id: Optional[int] = None
    item_id: int
    transaction_date: date
    entry_type: str
    reference_type: str
    reference_id: int
    reference_number: Optional[str] = None
    quantity_in: Decimal = Decimal("0")
    quantity_out: Decimal = Decimal("0")
    unit_rate: Decimal = Decimal("0")
    narration: Optional[str] = None
    
    @field_validator('entry_type')
    @classmethod
    def entry_type_valid(cls, v):
        valid_types = ['OPENING', 'PURCHASE', 'SALE', 'TRANSFER_IN', 'TRANSFER_OUT', 
                       'RETURN', 'ADJUSTMENT', 'SERVICE_CONSUMPTION', 'DAMAGE', 'WRITE_OFF']
        if v not in valid_types:
            raise ValueError(f'Entry type must be one of: {", ".join(valid_types)}')
        return v
    
    @field_validator('reference_type')
    @classmethod
    def reference_type_valid(cls, v):
        valid_types = ['VENDOR_TXN', 'SALE', 'STOCK_TRANSFER', 'SERVICE', 'ADJUSTMENT', 'OPENING', 'RETURN']
        if v not in valid_types:
            raise ValueError(f'Reference type must be one of: {", ".join(valid_types)}')
        return v


class StockLedgerResponse(BaseModel):
    """Response schema for a stock ledger entry"""
    id: int
    company_id: int
    segment_id: Optional[int] = None
    item_id: int
    item_code: Optional[str] = None
    item_name: Optional[str] = None
    company_name: Optional[str] = None
    
    transaction_date: date
    entry_type: str
    
    reference_type: str
    reference_id: int
    reference_number: Optional[str] = None
    
    quantity_in: Decimal
    quantity_out: Decimal
    unit_rate: Decimal
    total_value: Decimal
    
    balance_qty: Decimal
    balance_value: Decimal
    
    narration: Optional[str] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class StockLedgerListResponse(BaseModel):
    """Response schema for listing stock ledger entries"""
    success: bool
    entries: List[StockLedgerResponse]
    total: int
    page: int = 1
    page_size: int = 20


class StockBalanceResponse(BaseModel):
    """Response schema for stock balance per item"""
    item_id: int
    item_code: str
    item_name: str
    company_id: int
    balance_qty: Decimal
    balance_value: Decimal
    last_transaction_date: Optional[date] = None


class StockBalanceListResponse(BaseModel):
    """Response schema for listing stock balances"""
    success: bool
    balances: List[StockBalanceResponse]
    total: int


# ==================== PARTY LEDGER SCHEMAS (Phase 2.12) ====================

class PartyLedgerEntryCreate(BaseModel):
    """Schema for creating a party ledger entry (internal use)"""
    party_type: str
    party_id: int
    party_name: str
    company_id: int
    segment_id: Optional[int] = None
    transaction_date: date
    entry_type: str
    reference_type: str
    reference_id: int
    reference_number: Optional[str] = None
    debit_amount: Decimal = Decimal("0")
    credit_amount: Decimal = Decimal("0")
    narration: Optional[str] = None
    
    @field_validator('party_type')
    @classmethod
    def party_type_valid(cls, v):
        valid_types = ['VENDOR', 'EMPLOYEE', 'MNR_USER', 'CUSTOMER', 'COMPANY', 'EXTERNAL']
        if v not in valid_types:
            raise ValueError(f'Party type must be one of: {", ".join(valid_types)}')
        return v
    
    @field_validator('entry_type')
    @classmethod
    def entry_type_valid(cls, v):
        valid_types = ['DEBIT', 'CREDIT']
        if v not in valid_types:
            raise ValueError(f'Entry type must be one of: {", ".join(valid_types)}')
        return v
    
    @field_validator('reference_type')
    @classmethod
    def reference_type_valid(cls, v):
        valid_types = ['VENDOR_TXN', 'INCOME', 'EXPENSE', 'FUND_TRANSFER', 'STOCK_TRANSFER', 'RETURN', 'OPENING']
        if v not in valid_types:
            raise ValueError(f'Reference type must be one of: {", ".join(valid_types)}')
        return v


class PartyLedgerResponse(BaseModel):
    """Response schema for a party ledger entry"""
    id: int
    
    party_type: str
    party_id: int
    party_name: str
    
    company_id: int
    segment_id: Optional[int] = None
    
    transaction_date: date
    entry_type: str
    
    reference_type: str
    reference_id: int
    reference_number: Optional[str] = None
    
    debit_amount: Decimal
    credit_amount: Decimal
    running_balance: Decimal
    
    narration: Optional[str] = None
    voucher_type: Optional[str] = None
    particulars: Optional[str] = None
    source_status: Optional[str] = None
    category: Optional[str] = None
    main_category_id: Optional[int] = None
    sub_category_id: Optional[int] = None
    main_category_name: Optional[str] = None
    sub_category_name: Optional[str] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class PartyLedgerListResponse(BaseModel):
    """Response schema for listing party ledger entries"""
    success: bool
    entries: List[PartyLedgerResponse]
    total: int
    page: int = 1
    page_size: int = 20
    opening_balance: Decimal = Decimal("0")
    total_debit: Decimal = Decimal("0")
    total_credit: Decimal = Decimal("0")
    closing_balance: Decimal = Decimal("0")


class PartyBalanceResponse(BaseModel):
    """Response schema for party balance summary"""
    party_type: str
    party_id: int
    party_name: str
    company_id: int
    total_debit: Decimal
    total_credit: Decimal
    balance: Decimal
    last_transaction_date: Optional[date] = None


class PartyBalanceListResponse(BaseModel):
    """Response schema for listing party balances"""
    success: bool
    balances: List[PartyBalanceResponse]
    total: int


# ==================== VENDOR RETURN SCHEMAS (Phase 2.13) ====================

class VendorReturnCreate(BaseModel):
    """Schema for creating a vendor return"""
    transaction_id: int
    line_item_id: Optional[int] = None
    return_date: date
    return_qty: Decimal
    return_value: Decimal
    return_reason: str
    return_remarks: Optional[str] = None
    
    @field_validator('return_reason')
    @classmethod
    def return_reason_valid(cls, v):
        valid_reasons = ['DEFECTIVE', 'WRONG_ITEM', 'DAMAGED', 'QUALITY_ISSUE', 'EXCESS_ORDER', 'OTHER']
        if v not in valid_reasons:
            raise ValueError(f'Return reason must be one of: {", ".join(valid_reasons)}')
        return v
    
    @field_validator('return_qty')
    @classmethod
    def return_qty_positive(cls, v):
        if v <= 0:
            raise ValueError('Return quantity must be greater than 0')
        return v
    
    @field_validator('return_value')
    @classmethod
    def return_value_non_negative(cls, v):
        if v < 0:
            raise ValueError('Return value cannot be negative')
        return v


class VendorReturnResolve(BaseModel):
    """Schema for resolving a vendor return"""
    resolution_type: str
    
    credit_note_number: Optional[str] = None
    credit_note_amount: Optional[Decimal] = None
    credit_note_date: Optional[date] = None
    
    replacement_received: Optional[bool] = None
    replacement_date: Optional[date] = None
    replacement_remarks: Optional[str] = None
    
    refund_amount: Optional[Decimal] = None
    refund_date: Optional[date] = None
    refund_reference: Optional[str] = None
    
    @field_validator('resolution_type')
    @classmethod
    def resolution_type_valid(cls, v):
        valid_types = ['CREDIT_NOTE', 'REPLACEMENT', 'REFUND']
        if v not in valid_types:
            raise ValueError(f'Resolution type must be one of: {", ".join(valid_types)}')
        return v


class VendorReturnStatusChange(BaseModel):
    """Schema for changing vendor return status"""
    status: str
    remarks: Optional[str] = None
    
    @field_validator('status')
    @classmethod
    def status_valid(cls, v):
        valid_statuses = ['INITIATED', 'IN_PROGRESS', 'AWAITING_RESOLUTION', 'RESOLVED', 'CANCELLED']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v


class VendorReturnResponse(BaseModel):
    """Response schema for a vendor return"""
    id: int
    return_number: str
    transaction_id: int
    line_item_id: Optional[int] = None
    company_id: int
    vendor_id: int
    
    return_date: date
    return_qty: Decimal
    return_value: Decimal
    
    return_reason: str
    return_remarks: Optional[str] = None
    
    resolution_type: Optional[str] = None
    resolution_status: str
    
    credit_note_number: Optional[str] = None
    credit_note_amount: Optional[Decimal] = None
    credit_note_date: Optional[date] = None
    
    replacement_received: bool
    replacement_date: Optional[date] = None
    replacement_remarks: Optional[str] = None
    
    refund_amount: Optional[Decimal] = None
    refund_date: Optional[date] = None
    refund_reference: Optional[str] = None
    
    stock_reversed: bool
    reversal_entry_id: Optional[int] = None
    ledger_updated: bool
    
    status: str
    
    created_by_id: Optional[int] = None
    resolved_by_id: Optional[int] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}


class VendorReturnListResponse(BaseModel):
    """Response schema for listing vendor returns"""
    success: bool
    returns: List[VendorReturnResponse]
    total: int
    page: int = 1
    page_size: int = 20


# ==================== STOCK TRANSFER SCHEMAS (Phase 2.14) ====================

class StockTransferCreate(BaseModel):
    """Schema for creating a stock transfer"""
    from_company_id: int
    from_segment_id: Optional[int] = None
    to_company_id: int
    to_segment_id: Optional[int] = None
    transfer_date: date
    item_id: int
    quantity: Decimal
    unit_rate: Decimal
    transfer_type: str = 'INTERNAL'
    narration: Optional[str] = None
    remarks: Optional[str] = None
    
    @field_validator('transfer_type')
    @classmethod
    def transfer_type_valid(cls, v):
        valid_types = ['SALE', 'LOAN', 'INTERNAL', 'RETURN']
        if v not in valid_types:
            raise ValueError(f'Transfer type must be one of: {", ".join(valid_types)}')
        return v
    
    @field_validator('quantity')
    @classmethod
    def quantity_positive(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return v
    
    @field_validator('unit_rate')
    @classmethod
    def unit_rate_non_negative(cls, v):
        if v < 0:
            raise ValueError('Unit rate cannot be negative')
        return v


class StockTransferDispatch(BaseModel):
    """Schema for dispatching a stock transfer"""
    remarks: Optional[str] = None


class StockTransferReceive(BaseModel):
    """Schema for receiving a stock transfer"""
    received_quantity: Optional[Decimal] = None
    remarks: Optional[str] = None


class StockTransferStatusChange(BaseModel):
    """Schema for changing stock transfer status"""
    status: str
    remarks: Optional[str] = None
    
    @field_validator('status')
    @classmethod
    def status_valid(cls, v):
        valid_statuses = ['INITIATED', 'DISPATCHED', 'IN_TRANSIT', 'RECEIVED', 'CANCELLED']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v


class StockTransferResponse(BaseModel):
    """Response schema for a stock transfer"""
    id: int
    transfer_number: str
    
    from_company_id: int
    from_segment_id: Optional[int] = None
    to_company_id: int
    to_segment_id: Optional[int] = None
    
    transfer_date: date
    
    item_id: int
    quantity: Decimal
    unit_rate: Decimal
    total_value: Decimal
    
    transfer_type: str
    narration: Optional[str] = None
    remarks: Optional[str] = None
    
    status: str
    
    dispatched_by_id: Optional[int] = None
    dispatched_at: Optional[datetime] = None
    received_by_id: Optional[int] = None
    received_at: Optional[datetime] = None
    
    from_stock_entry_id: Optional[int] = None
    to_stock_entry_id: Optional[int] = None
    from_party_entry_id: Optional[int] = None
    to_party_entry_id: Optional[int] = None
    
    stock_reversal_entry_id: Optional[int] = None
    from_party_reversal_entry_id: Optional[int] = None
    to_party_reversal_entry_id: Optional[int] = None
    
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class StockTransferListResponse(BaseModel):
    """Response schema for listing stock transfers"""
    success: bool
    transfers: List[StockTransferResponse]
    total: int
    page: int = 1
    page_size: int = 20


class FundAllocationCreate(BaseModel):
    """Schema for creating a fund allocation"""
    company_id: int
    segment_id: Optional[int] = None
    to_employee_id: int
    allocation_date: date
    amount: Decimal = Field(..., gt=0, description="Allocation amount must be positive")
    purpose: Optional[str] = Field(None, max_length=500)
    category_id: Optional[int] = None
    payment_mode: Optional[str] = Field(None, max_length=20)
    payment_reference: Optional[str] = Field(None, max_length=100)
    bank_account_id: Optional[int] = None
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v


class FundAllocationUpdate(BaseModel):
    """Schema for updating a fund allocation"""
    purpose: Optional[str] = Field(None, max_length=500)
    category_id: Optional[int] = None
    payment_mode: Optional[str] = Field(None, max_length=20)
    payment_reference: Optional[str] = Field(None, max_length=100)


class FundAllocationConfirm(BaseModel):
    """Schema for confirming receipt of fund allocation"""
    confirmation_remarks: Optional[str] = Field(None, max_length=500)


class FundAllocationSettle(BaseModel):
    """Schema for settling a fund allocation"""
    settlement_remarks: Optional[str] = Field(None, max_length=500)
    settlement_amount: Optional[Decimal] = Field(None, ge=0, description="Amount to settle (if partial)")


class FundAllocationCancel(BaseModel):
    """Schema for cancelling a fund allocation"""
    cancellation_reason: str = Field(..., min_length=5, max_length=500)


class FundAllocationResponse(BaseModel):
    """Response schema for a fund allocation"""
    id: int
    allocation_number: str
    
    company_id: int
    segment_id: Optional[int] = None
    
    from_employee_id: int
    to_employee_id: int
    
    allocation_date: date
    amount: Decimal
    
    purpose: Optional[str] = None
    category_id: Optional[int] = None
    
    payment_mode: Optional[str] = None
    payment_reference: Optional[str] = None
    
    status: str
    
    balance_remaining: Decimal
    total_expensed: Decimal
    
    settlement_date: Optional[date] = None
    settlement_remarks: Optional[str] = None
    
    confirmed_by_id: Optional[int] = None
    confirmed_at: Optional[datetime] = None
    
    ledger_entry_id: Optional[int] = None
    bank_account_id: Optional[int] = None
    
    from_employee_name: Optional[str] = None
    to_employee_name: Optional[str] = None
    recipient_name: Optional[str] = None
    company_name: Optional[str] = None
    balance_used: Optional[float] = None
    
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class FundAllocationListResponse(BaseModel):
    """Response schema for listing fund allocations"""
    success: bool
    allocations: List[FundAllocationResponse]
    total: int
    page: int = 1
    page_size: int = 20


class ExpenseEntryCreate(BaseModel):
    """Schema for creating an expense entry"""
    on_behalf_of_employee_id: Optional[int] = Field(None, description="DC_EXP_BEHALF_001: Create on behalf of this employee (privileged users + reporting managers only)")
    company_id: int
    segment_id: Optional[int] = None
    fund_allocation_id: Optional[int] = None

    main_category_id: int
    sub_category_id: Optional[int] = None

    expense_date: date
    amount: Decimal = Field(..., gt=0)

    vendor_id: Optional[int] = None
    vendor_name: Optional[str] = Field(None, max_length=200)
    vendor_contact: Optional[str] = Field(None, max_length=50)

    payment_mode: str = Field(..., max_length=20)
    payment_reference: Optional[str] = Field(None, max_length=100)
    bank_account_id: Optional[int] = None
    bank_ledger_category: Optional[str] = Field(None, max_length=20)
    custom_category_name: Optional[str] = Field(None, max_length=100)

    narration: Optional[str] = Field(None, max_length=500)

    bill_number: Optional[str] = Field(None, max_length=50)
    bill_date: Optional[date] = None
    bill_remarks: Optional[str] = Field(None, max_length=500)

    related_entity_type: Optional[str] = Field(None, max_length=20)
    related_entity_id: Optional[str] = Field(None, max_length=50)

    gst_applicable: bool = False
    gst_amount: Decimal = Decimal('0')
    tds_applicable: bool = False
    tds_amount: Decimal = Decimal('0')

    show_in_ledger: Optional[bool] = Field(False, description="DC-SHOW-IN-LEDGER-001: if true, this entry posts to the transaction ledger")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v


class ExpenseEntryUpdate(BaseModel):
    """Schema for updating an expense entry"""
    sub_category_id: Optional[int] = None
    expense_date: Optional[date] = None
    amount: Optional[Decimal] = Field(None, gt=0)

    vendor_id: Optional[int] = None
    vendor_name: Optional[str] = Field(None, max_length=200)
    vendor_contact: Optional[str] = Field(None, max_length=50)

    payment_mode: Optional[str] = Field(None, max_length=20)
    payment_reference: Optional[str] = Field(None, max_length=100)
    bank_account_id: Optional[int] = None
    bank_ledger_category: Optional[str] = Field(None, max_length=20)
    custom_category_name: Optional[str] = Field(None, max_length=100)

    narration: Optional[str] = Field(None, max_length=500)

    bill_number: Optional[str] = Field(None, max_length=50)
    bill_date: Optional[date] = None
    bill_remarks: Optional[str] = Field(None, max_length=500)

    gst_applicable: Optional[bool] = None
    gst_amount: Optional[Decimal] = None
    tds_applicable: Optional[bool] = None
    tds_amount: Optional[Decimal] = None

    show_in_ledger: Optional[bool] = None


class ExpenseEntrySubmit(BaseModel):
    """Schema for submitting an expense entry for approval"""
    submission_remarks: Optional[str] = Field(None, max_length=500)


class ExpenseEntryApprove(BaseModel):
    """Schema for approving/rejecting an expense entry"""
    action: str = Field(..., pattern='^(APPROVE|REJECT|RETURN)$')
    remarks: Optional[str] = Field(None, max_length=500)


class ExpenseEntryMarkPaid(BaseModel):
    """Schema for marking an expense entry as paid (auto-approves + records payment)"""
    payment_utr: Optional[str] = Field(None, max_length=100, description="UTR / reference number for payment")
    bank_account_id: Optional[int] = None
    notes: Optional[str] = Field(None, max_length=500)


class ExpenseEntrySummary(BaseModel):
    """Summary counts for expense entries list"""
    draft_count: int = 0
    submitted_count: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    paid_count: int = 0
    total_approved_amount: Decimal = Decimal('0')
    total_paid_amount: Decimal = Decimal('0')


class ExpenseEntryResponse(BaseModel):
    """Response schema for an expense entry"""
    id: int
    entry_number: str

    company_id: int
    company_name: Optional[str] = None
    segment_id: Optional[int] = None
    fund_allocation_id: Optional[int] = None

    main_category_id: int
    category_name: Optional[str] = None
    sub_category_id: Optional[int] = None

    expense_date: date
    amount: Decimal

    vendor_id: Optional[int] = None
    vendor_name: Optional[str] = None
    vendor_contact: Optional[str] = None

    payment_mode: str
    payment_reference: Optional[str] = None
    bank_account_id: Optional[int] = None
    bank_ledger_category: Optional[str] = None
    custom_category_name: Optional[str] = None

    narration: Optional[str] = None

    bill_number: Optional[str] = None
    bill_date: Optional[date] = None
    bill_path: Optional[str] = None
    bill_remarks: Optional[str] = None

    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None

    gst_applicable: bool = False
    gst_amount: Decimal = Decimal('0')
    tds_applicable: bool = False
    tds_amount: Decimal = Decimal('0')
    net_amount: Decimal = Decimal('0')

    status: str
    tally_status: Optional[str] = None
    tally_voucher_no: Optional[str] = None

    is_paid: bool = False
    paid_at: Optional[datetime] = None
    paid_by_id: Optional[int] = None
    payment_utr: Optional[str] = None

    # DC-RETURN-001: Purchase Return / Debit Note
    is_return: bool = False
    return_reference: Optional[str] = None

    ledger_updated: bool = False
    show_in_ledger: bool = False

    created_by_id: Optional[int] = None
    created_by_name: Optional[str] = None
    approved_by_id: Optional[int] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExpenseEntryListResponse(BaseModel):
    """Response schema for listing expense entries"""
    success: bool
    entries: List[ExpenseEntryResponse]
    total: int
    page: int = 1
    page_size: int = 20
    summary: Optional[ExpenseEntrySummary] = None


class BalanceSheetSummaryResponse(BaseModel):
    """Response schema for balance sheet summary"""
    id: int
    
    company_id: int
    period_type: str
    period_date: date
    financial_year: str
    
    total_income: Decimal
    income_by_source: Optional[dict] = None
    
    total_expense: Decimal
    expense_by_category: Optional[dict] = None
    
    pending_payouts: Decimal
    pending_awards: Decimal
    pending_allowances: Decimal
    total_liability: Decimal
    
    net_balance: Decimal
    available_balance: Decimal
    
    total_receivables: Decimal
    total_payables: Decimal
    
    total_stock_value: Decimal
    items_below_reorder: int
    
    pending_incentives: Decimal
    
    computed_at: datetime
    computed_by: Optional[str] = None
    
    model_config = {"from_attributes": True}


class BalanceSheetComputeRequest(BaseModel):
    """Request schema for computing balance sheet"""
    company_id: int
    period_type: str = Field(..., pattern='^(DAILY|MONTHLY|QUARTERLY|YEARLY)$')
    period_date: date
    force_recompute: bool = False


class BalanceSheetDashboardResponse(BaseModel):
    """Response schema for balance sheet dashboard"""
    success: bool
    summary: Optional[BalanceSheetSummaryResponse] = None
    trend_data: Optional[List[dict]] = None
    alerts: Optional[List[dict]] = None


# ==================== CREDIT SYSTEM ENUMS (DC_CREDIT_001) ====================

class PaymentStatusEnum(str, Enum):
    """Payment status for vendor transactions (Accounts Payable)"""
    PENDING = "PENDING"
    PARTIAL_PAID = "PARTIAL_PAID"
    FULLY_PAID = "FULLY_PAID"
    OVERDUE = "OVERDUE"


class ReceivableStatusEnum(str, Enum):
    """Receivable status for customer invoices (Accounts Receivable)"""
    PENDING = "PENDING"
    PARTIAL_RECEIVED = "PARTIAL_RECEIVED"
    FULLY_RECEIVED = "FULLY_RECEIVED"
    OVERDUE = "OVERDUE"


class CreditTypeEnum(str, Enum):
    """Credit type for aging analysis"""
    PAYABLE = "PAYABLE"
    RECEIVABLE = "RECEIVABLE"


class PaymentTransactionTypeEnum(str, Enum):
    """Payment transaction types"""
    PAYMENT_TO_VENDOR = "PAYMENT_TO_VENDOR"
    RECEIPT_FROM_CUSTOMER = "RECEIPT_FROM_CUSTOMER"
    ADVANCE_PAYMENT = "ADVANCE_PAYMENT"
    ADVANCE_RECEIPT = "ADVANCE_RECEIPT"
    REFUND_TO_CUSTOMER = "REFUND_TO_CUSTOMER"
    REFUND_FROM_VENDOR = "REFUND_FROM_VENDOR"


# ==================== ACCOUNTS PAYABLE SCHEMAS (DC_CREDIT_001) ====================

class AccountsPayableScheduleCreate(BaseModel):
    """Create schema for Accounts Payable Schedule"""
    transaction_id: int = Field(..., description="Vendor transaction ID")
    scheduled_amount: Decimal = Field(..., gt=0, description="Amount scheduled for payment")
    due_date: date = Field(..., description="Payment due date")
    narration: Optional[str] = Field(None, max_length=500)
    
    model_config = {"extra": "forbid"}


class AccountsPayableScheduleResponse(BaseModel):
    """Response schema for Accounts Payable Schedule"""
    id: int
    schedule_number: str
    transaction_id: int
    vendor_id: int
    vendor_name: Optional[str] = None
    company_id: int
    company_name: Optional[str] = None
    
    scheduled_amount: Decimal
    paid_amount: Decimal
    balance_amount: Decimal
    
    due_date: date
    payment_date: Optional[date] = None
    
    payment_mode: Optional[str] = None
    payment_reference: Optional[str] = None
    
    status: str
    days_overdue: Optional[int] = None
    
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class RecordVendorPaymentRequest(BaseModel):
    """Request to record payment to vendor"""
    transaction_id: int = Field(..., description="Vendor transaction ID")
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    payment_date: date = Field(..., description="Date of payment")
    payment_mode: str = Field(..., pattern='^(CASH|BANK|UPI|CHEQUE|DD|NEFT|RTGS|CARD)$')
    payment_reference: Optional[str] = Field(None, max_length=100)
    bank_reference: Optional[str] = Field(None, max_length=100)
    cheque_number: Optional[str] = Field(None, max_length=20)
    cheque_date: Optional[date] = None
    narration: Optional[str] = Field(None, max_length=500)
    
    model_config = {"extra": "forbid"}


class PayablesListResponse(BaseModel):
    """Response for listing accounts payable"""
    success: bool
    payables: List[AccountsPayableScheduleResponse]
    total: int
    total_pending: Decimal
    total_overdue: Decimal
    page: int = 1
    page_size: int = 20


# ==================== ACCOUNTS RECEIVABLE SCHEMAS (DC_CREDIT_001) ====================

class AccountsReceivableScheduleCreate(BaseModel):
    """Create schema for Accounts Receivable Schedule"""
    invoice_id: int = Field(..., description="Invoice ID")
    scheduled_amount: Decimal = Field(..., gt=0, description="Amount scheduled for receipt")
    due_date: date = Field(..., description="Receipt due date")
    narration: Optional[str] = Field(None, max_length=500)
    
    model_config = {"extra": "forbid"}


class AccountsReceivableScheduleResponse(BaseModel):
    """Response schema for Accounts Receivable Schedule"""
    id: int
    schedule_number: str
    invoice_id: int
    invoice_number: Optional[str] = None
    party_type: str
    party_id: Optional[int] = None
    party_name: str
    company_id: int
    company_name: Optional[str] = None
    
    scheduled_amount: Decimal
    received_amount: Decimal
    balance_amount: Decimal
    
    due_date: date
    receipt_date: Optional[date] = None
    
    payment_mode: Optional[str] = None
    payment_reference: Optional[str] = None
    
    status: str
    days_overdue: Optional[int] = None
    
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class RecordCustomerReceiptRequest(BaseModel):
    """Request to record receipt from customer"""
    invoice_id: int = Field(..., description="Invoice ID")
    amount: Decimal = Field(..., gt=0, description="Receipt amount")
    receipt_date: date = Field(..., description="Date of receipt")
    payment_mode: str = Field(..., pattern='^(CASH|BANK|UPI|CHEQUE|DD|NEFT|RTGS|CARD)$')
    payment_reference: Optional[str] = Field(None, max_length=100)
    bank_reference: Optional[str] = Field(None, max_length=100)
    narration: Optional[str] = Field(None, max_length=500)
    
    model_config = {"extra": "forbid"}


class ReceivablesListResponse(BaseModel):
    """Response for listing accounts receivable"""
    success: bool
    receivables: List[AccountsReceivableScheduleResponse]
    total: int
    total_pending: Decimal
    total_overdue: Decimal
    page: int = 1
    page_size: int = 20


# ==================== CREDIT AGING SCHEMAS (DC_CREDIT_001) ====================

class CreditAgingBucket(BaseModel):
    """Aging bucket data"""
    bucket_current: Decimal = Field(default=Decimal('0'))
    bucket_1_30: Decimal = Field(default=Decimal('0'))
    bucket_31_60: Decimal = Field(default=Decimal('0'))
    bucket_61_90: Decimal = Field(default=Decimal('0'))
    bucket_90_plus: Decimal = Field(default=Decimal('0'))
    total_outstanding: Decimal = Field(default=Decimal('0'))
    total_overdue: Decimal = Field(default=Decimal('0'))


class CreditAgingSnapshotResponse(BaseModel):
    """Response schema for Credit Aging Snapshot"""
    id: int
    company_id: int
    company_name: Optional[str] = None
    credit_type: str
    
    party_type: Optional[str] = None
    party_id: Optional[int] = None
    party_name: Optional[str] = None
    
    snapshot_date: date
    
    bucket_current: Decimal
    bucket_1_30: Decimal
    bucket_31_60: Decimal
    bucket_61_90: Decimal
    bucket_90_plus: Decimal
    
    total_outstanding: Decimal
    total_overdue: Decimal
    
    transaction_count: int
    overdue_count: int
    avg_days_outstanding: int
    
    created_at: datetime
    
    model_config = {"from_attributes": True}


class AgingSummaryRequest(BaseModel):
    """Request for aging summary"""
    company_id: int
    credit_type: str = Field(..., pattern='^(PAYABLE|RECEIVABLE)$')
    as_of_date: Optional[date] = None


class AgingSummaryResponse(BaseModel):
    """Response for aging summary with breakdown"""
    success: bool
    credit_type: str
    company_id: int
    company_name: Optional[str] = None
    as_of_date: date
    
    summary: CreditAgingBucket
    by_party: Optional[List[CreditAgingSnapshotResponse]] = None
    
    total_transactions: int
    overdue_transactions: int


# ==================== PAYMENT TRANSACTION SCHEMAS (DC_CREDIT_001) ====================

class PaymentTransactionResponse(BaseModel):
    """Response schema for Payment Transaction"""
    id: int
    transaction_number: str
    transaction_type: str
    
    company_id: int
    company_name: Optional[str] = None
    
    source_type: str
    source_id: int
    source_reference: Optional[str] = None
    
    party_type: str
    party_id: Optional[int] = None
    party_name: str
    
    transaction_date: date
    amount: Decimal
    
    payment_mode: str
    payment_reference: Optional[str] = None
    bank_name: Optional[str] = None
    bank_reference: Optional[str] = None
    
    narration: Optional[str] = None
    status: str
    
    created_by_name: Optional[str] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class PaymentTransactionListResponse(BaseModel):
    """Response for listing payment transactions"""
    success: bool
    transactions: List[PaymentTransactionResponse]
    total: int
    total_amount: Decimal
    page: int = 1
    page_size: int = 20


# ==================== CREDIT DASHBOARD SCHEMAS (DC_CREDIT_001) ====================

class CreditDashboardResponse(BaseModel):
    """Response for credit dashboard overview"""
    success: bool
    
    payables_summary: CreditAgingBucket
    receivables_summary: CreditAgingBucket
    
    net_credit_position: Decimal
    
    payables_count: int
    receivables_count: int
    
    overdue_payables: List[AccountsPayableScheduleResponse]
    overdue_receivables: List[AccountsReceivableScheduleResponse]
    
    recent_payments: List[PaymentTransactionResponse]
    recent_receipts: List[PaymentTransactionResponse]


# ==================== BOM SCHEMAS (DC_BOM_001 - Dec 06, 2025) ====================

class BOMStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    OBSOLETE = "OBSOLETE"
    REJECTED = "REJECTED"


class UnitOfMeasure(str, Enum):
    PCS = "PCS"
    KG = "KG"
    LTR = "LTR"
    MTR = "MTR"
    SET = "SET"
    BOX = "BOX"
    PACK = "PACK"
    PAIR = "PAIR"
    UNIT = "UNIT"


class BOMLineItemBase(BaseModel):
    """Base schema for BOM Line Item"""
    component_id: int = Field(..., description="Stock item ID of the component")
    quantity_required: Decimal = Field(..., gt=0, description="Quantity required per unit of finished product")
    unit_of_measure: UnitOfMeasure = Field(default=UnitOfMeasure.PCS)
    wastage_pct: Optional[Decimal] = Field(default=0, ge=0, le=100, description="Wastage percentage (0-100)")
    sequence_order: Optional[int] = Field(default=1, ge=1)
    is_optional: Optional[bool] = Field(default=False)
    notes: Optional[str] = Field(None, max_length=500)
    
    model_config = {"extra": "forbid"}


class BOMLineItemCreate(BOMLineItemBase):
    """Schema for creating BOM Line Item"""
    change_reason: Optional[str] = Field(None, max_length=500, description="Required when adding to APPROVED BOMs")


class BOMLineItemUpdate(BaseModel):
    """Schema for updating BOM Line Item"""
    quantity_required: Optional[Decimal] = Field(None, gt=0)
    unit_of_measure: Optional[UnitOfMeasure] = None
    wastage_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    sequence_order: Optional[int] = Field(None, ge=1)
    is_optional: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=500)
    change_reason: Optional[str] = Field(None, max_length=500, description="Required when editing APPROVED BOMs")
    
    model_config = {"extra": "forbid"}


class BOMLineItemResponse(BaseModel):
    """Response schema for BOM Line Item"""
    id: int
    bom_id: int
    component_id: int
    component_name: Optional[str] = None
    component_code: Optional[str] = None
    quantity_required: Decimal
    unit_of_measure: str
    wastage_pct: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    sequence_order: int
    is_optional: bool
    notes: Optional[str] = None
    
    model_config = {"from_attributes": True}


class BOMBase(BaseModel):
    """Base schema for Bill of Materials"""
    bom_name: str = Field(..., min_length=2, max_length=200, description="BOM name/description")
    company_id: int = Field(..., description="Associated company ID")
    finished_product_id: int = Field(..., description="Stock item ID of the finished product")
    standard_qty: Decimal = Field(default=1, gt=0, description="Standard quantity to produce")
    unit_of_measure: UnitOfMeasure = Field(default=UnitOfMeasure.PCS)
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    estimated_time_hours: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=1000)
    
    model_config = {"extra": "forbid"}
    
    @model_validator(mode='after')
    def validate_dates(self):
        if self.effective_from and self.effective_to:
            if self.effective_from > self.effective_to:
                raise ValueError('effective_from must be before effective_to')
        return self


class BOMCreate(BOMBase):
    """Schema for creating BOM with line items"""
    line_items: List[BOMLineItemCreate] = Field(..., min_length=1, description="At least one component required")
    
    @field_validator('line_items')
    @classmethod
    def validate_line_items(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one component is required')
        component_ids = [item.component_id for item in v]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError('Duplicate components not allowed in BOM')
        return v


class BOMUpdate(BaseModel):
    """Schema for updating BOM - DC Protocol Re-approval Workflow"""
    bom_name: Optional[str] = Field(None, min_length=2, max_length=200)
    standard_qty: Optional[Decimal] = Field(None, gt=0)
    unit_of_measure: Optional[UnitOfMeasure] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    estimated_time_hours: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None
    change_reason: Optional[str] = Field(None, max_length=500, description="Required when editing APPROVED BOMs - explains why re-approval is needed")


class BOMResponse(BaseModel):
    """Response schema for BOM"""
    id: int
    bom_code: str
    bom_name: str
    description: Optional[str] = None
    company_id: int
    company_name: Optional[str] = None
    finished_product_id: int
    finished_product_name: Optional[str] = None
    finished_product_code: Optional[str] = None
    standard_qty: Decimal
    unit_of_measure: str
    version: int
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    status: str
    estimated_cost: Decimal
    estimated_time_hours: Optional[Decimal] = None
    notes: Optional[str] = None
    is_active: bool
    created_by_name: Optional[str] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    line_items: Optional[List[BOMLineItemResponse]] = None
    
    model_config = {"from_attributes": True}


class BOMListResponse(BaseModel):
    """Response for listing BOMs"""
    success: bool
    boms: List[BOMResponse]
    total: int
    page: int = 1
    page_size: int = 20


class BOMApprovalRequest(BaseModel):
    """Request for BOM approval action"""
    action: str = Field(..., pattern="^(approve|reject)$")
    remarks: Optional[str] = Field(None, max_length=500)


class BOMCopyRequest(BaseModel):
    """Request to copy BOM to new version"""
    new_bom_name: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=500)


# ==================== MANUFACTURING ORDER SCHEMAS (DC_BOM_001) ====================

class ManufacturingOrderStatus(str, Enum):
    PLANNED = "PLANNED"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    CANCELLED = "CANCELLED"
    ON_HOLD = "ON_HOLD"


class ManufacturingPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class ManufacturingLineStatus(str, Enum):
    PENDING = "PENDING"
    ISSUED = "ISSUED"
    PARTIALLY_CONSUMED = "PARTIALLY_CONSUMED"
    CONSUMED = "CONSUMED"
    RETURNED = "RETURNED"


class ManufacturingOrderLineResponse(BaseModel):
    """Response schema for Manufacturing Order Line"""
    id: int
    manufacturing_order_id: int
    component_id: int
    component_name: Optional[str] = None
    component_code: Optional[str] = None
    planned_qty: Decimal
    actual_qty_consumed: Decimal
    wastage_qty: Decimal
    returned_qty: Decimal
    unit_of_measure: str
    planned_cost: Decimal
    actual_cost: Decimal
    status: str
    consumed_at: Optional[datetime] = None
    consumed_by_name: Optional[str] = None
    notes: Optional[str] = None
    
    model_config = {"from_attributes": True}


class ManufacturingOrderBase(BaseModel):
    """Base schema for Manufacturing Order"""
    company_id: int = Field(..., description="Associated company ID")
    bom_id: int = Field(..., description="BOM to use for manufacturing")
    planned_qty: Decimal = Field(..., gt=0, description="Quantity to manufacture")
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    priority: ManufacturingPriority = Field(default=ManufacturingPriority.NORMAL)
    notes: Optional[str] = Field(None, max_length=1000)
    
    model_config = {"extra": "forbid"}
    
    @model_validator(mode='after')
    def validate_dates(self):
        if self.planned_start_date and self.planned_end_date:
            if self.planned_start_date > self.planned_end_date:
                raise ValueError('planned_start_date must be before planned_end_date')
        return self


class ManufacturingOrderCreate(ManufacturingOrderBase):
    """Schema for creating Manufacturing Order"""
    pass


class ManufacturingOrderUpdate(BaseModel):
    """Schema for updating Manufacturing Order"""
    planned_qty: Optional[Decimal] = Field(None, gt=0)
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    priority: Optional[ManufacturingPriority] = None
    notes: Optional[str] = Field(None, max_length=1000)
    remarks: Optional[str] = Field(None, max_length=1000)
    
    model_config = {"extra": "forbid"}


class ManufacturingOrderResponse(BaseModel):
    """Response schema for Manufacturing Order"""
    id: int
    order_number: str
    company_id: int
    company_name: Optional[str] = None
    bom_id: int
    bom_name: Optional[str] = None
    bom_code: Optional[str] = None
    finished_product_id: int
    finished_product_name: Optional[str] = None
    finished_product_code: Optional[str] = None
    planned_qty: Decimal
    actual_qty: Decimal
    rejected_qty: Decimal
    unit_of_measure: str
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    status: str
    priority: str
    estimated_cost: Decimal
    actual_cost: Decimal
    notes: Optional[str] = None
    remarks: Optional[str] = None
    created_by_name: Optional[str] = None
    approved_by_name: Optional[str] = None
    started_by_name: Optional[str] = None
    completed_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    line_items: Optional[List[ManufacturingOrderLineResponse]] = None
    
    model_config = {"from_attributes": True}


class ManufacturingOrderListResponse(BaseModel):
    """Response for listing Manufacturing Orders"""
    success: bool
    orders: List[ManufacturingOrderResponse]
    total: int
    page: int = 1
    page_size: int = 20


class ManufacturingStartRequest(BaseModel):
    """Request to start manufacturing"""
    remarks: Optional[str] = Field(None, max_length=500)


class ManufacturingCompleteRequest(BaseModel):
    """Request to complete manufacturing"""
    actual_qty: Decimal = Field(..., ge=0, description="Actual quantity produced")
    rejected_qty: Optional[Decimal] = Field(default=0, ge=0, description="Rejected quantity")
    remarks: Optional[str] = Field(None, max_length=500)
    
    @model_validator(mode='after')
    def validate_quantities(self):
        if self.actual_qty == 0 and (self.rejected_qty is None or self.rejected_qty == 0):
            raise ValueError('Either actual_qty or rejected_qty must be greater than 0')
        return self


class ManufacturingCancelRequest(BaseModel):
    """Request to cancel manufacturing order"""
    reason: str = Field(..., min_length=5, max_length=500, description="Cancellation reason required")


class ManufacturingUpdateRequest(BaseModel):
    """Request to update Manufacturing Order - DC Protocol compliant
    PLANNED: Full edit allowed
    APPROVED: Edit triggers re-approval (status → PENDING_APPROVAL)
    IN_PROGRESS: Only notes can be edited (fields disabled in frontend)
    """
    planned_qty: Optional[Decimal] = Field(None, gt=0, description="Updated planned quantity")
    priority: Optional[str] = Field(None, pattern="^(LOW|NORMAL|HIGH|URGENT)$")
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=500)
    change_reason: Optional[str] = Field(None, max_length=500, description="Required when editing APPROVED orders")


class ComponentConsumptionUpdate(BaseModel):
    """Update component consumption during manufacturing"""
    component_id: int
    actual_qty_consumed: Decimal = Field(..., ge=0)
    wastage_qty: Optional[Decimal] = Field(default=0, ge=0)
    notes: Optional[str] = Field(None, max_length=500)


class ManufacturingConsumptionRequest(BaseModel):
    """Request to record component consumption"""
    components: List[ComponentConsumptionUpdate] = Field(..., min_length=1)


class StockAvailabilityCheck(BaseModel):
    """Response for component stock availability check"""
    component_id: int
    component_name: str
    component_code: str
    required_qty: Decimal
    available_qty: Decimal
    shortage_qty: Decimal
    is_sufficient: bool


class ManufacturingStockCheckResponse(BaseModel):
    """Response for stock availability check before manufacturing"""
    success: bool
    can_manufacture: bool
    bom_id: int
    planned_qty: Decimal
    components: List[StockAvailabilityCheck]
    message: str


# ==================== SALES INVOICE SCHEMAS ====================

class SalesInvoiceLineItemBase(BaseModel):
    """Base schema for sales invoice line item"""
    item_id: Optional[int] = None
    item_code: Optional[str] = Field(None, max_length=30)
    item_description: str = Field(..., min_length=1, max_length=500)
    
    hsn_id: Optional[int] = None
    hsn_code: Optional[str] = Field(None, max_length=20)
    
    quantity: Decimal = Field(..., gt=0)
    unit_of_measure: str = Field(default='PCS', max_length=20)
    unit_rate: Decimal = Field(..., ge=0)
    mrp: Optional[Decimal] = Field(None, ge=0)
    
    discount_percent: Optional[Decimal] = Field(default=0, ge=0, le=100)
    discount_amount: Optional[Decimal] = Field(default=0, ge=0)
    
    gst_rate: Decimal = Field(default=0, ge=0)
    
    serial_numbers: Optional[List[str]] = None
    imei_numbers: Optional[List[str]] = None
    batch_number: Optional[str] = Field(None, max_length=50)
    warranty_months: Optional[int] = Field(default=0, ge=0)


class SalesInvoiceLineItemCreate(SalesInvoiceLineItemBase):
    """Create schema for sales invoice line item"""
    pass


class SalesInvoiceLineItemResponse(BaseModel):
    """Response schema for sales invoice line item"""
    id: int
    invoice_id: int
    line_number: int
    item_id: Optional[int] = None
    item_code: Optional[str] = None
    item_description: str
    hsn_id: Optional[int] = None
    hsn_code: Optional[str] = None
    quantity: Decimal
    unit_of_measure: str
    unit_rate: Decimal
    mrp: Optional[Decimal] = None
    gross_amount: Decimal
    discount_percent: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    taxable_amount: Decimal
    gst_rate: Decimal
    cgst_amount: Optional[Decimal] = None
    sgst_amount: Optional[Decimal] = None
    igst_amount: Optional[Decimal] = None
    total_tax: Decimal
    line_total: Decimal
    serial_numbers: Optional[List[str]] = None
    imei_numbers: Optional[List[str]] = None
    
    model_config = ConfigDict(from_attributes=True)


class SalesInvoiceBase(BaseModel):
    """Base schema for sales invoice"""
    company_id: int
    segment_id: Optional[int] = None
    invoice_date: date
    
    customer_type: str = Field(default='WALK_IN')
    customer_name: str = Field(..., min_length=1, max_length=200)
    customer_address: Optional[str] = None
    customer_gstin: Optional[str] = Field(None, max_length=20)
    customer_state: Optional[str] = Field(None, max_length=50)
    customer_phone: Optional[str] = Field(None, max_length=20)
    customer_email: Optional[EmailStr] = None
    
    billing_address: Optional[str] = None
    shipping_address: Optional[str] = None
    
    payment_mode: str = Field(default='CASH')
    is_credit_sale: bool = Field(default=False)
    credit_days: Optional[int] = Field(default=0, ge=0)
    
    terms_conditions: Optional[str] = None
    remarks: Optional[str] = None
    
    @field_validator('customer_type')
    @classmethod
    def validate_customer_type(cls, v):
        valid_types = ['WALK_IN', 'REGISTERED', 'PARTNER', 'CORPORATE']
        if v and v.upper() not in valid_types:
            raise ValueError(f'Customer type must be one of: {valid_types}')
        return v.upper() if v else 'WALK_IN'
    
    @field_validator('payment_mode')
    @classmethod
    def validate_payment_mode(cls, v):
        valid_modes = ['CASH', 'CARD', 'UPI', 'NEFT', 'RTGS', 'CHEQUE', 'CREDIT']
        if v and v.upper() not in valid_modes:
            raise ValueError(f'Payment mode must be one of: {valid_modes}')
        return v.upper() if v else 'CASH'


class SalesInvoiceCreate(SalesInvoiceBase):
    """Create schema for sales invoice"""
    line_items: List[SalesInvoiceLineItemCreate] = Field(..., min_length=1)
    
    amount_received: Optional[Decimal] = Field(default=0, ge=0)


class SalesInvoiceUpdate(BaseModel):
    """Update schema for sales invoice (only editable fields)"""
    customer_name: Optional[str] = Field(None, min_length=1, max_length=200)
    customer_address: Optional[str] = None
    customer_phone: Optional[str] = Field(None, max_length=20)
    customer_email: Optional[EmailStr] = None
    billing_address: Optional[str] = None
    shipping_address: Optional[str] = None
    terms_conditions: Optional[str] = None
    remarks: Optional[str] = None


class SalesInvoiceResponse(BaseModel):
    """Response schema for sales invoice"""
    id: int
    invoice_number: str
    invoice_date: date
    company_id: int
    segment_id: Optional[int] = None
    
    customer_type: str
    customer_name: str
    customer_gstin: Optional[str] = None
    customer_state: Optional[str] = None
    customer_phone: Optional[str] = None
    
    is_igst: bool
    subtotal: Decimal
    total_discount: Optional[Decimal] = None
    taxable_amount: Decimal
    cgst_amount: Optional[Decimal] = None
    sgst_amount: Optional[Decimal] = None
    igst_amount: Optional[Decimal] = None
    total_tax: Decimal
    round_off: Optional[Decimal] = None
    grand_total: Decimal
    
    payment_mode: str
    payment_status: str
    amount_received: Optional[Decimal] = None
    balance_due: Optional[Decimal] = None
    
    is_credit_sale: bool
    due_date: Optional[date] = None
    
    status: str
    pdf_path: Optional[str] = None
    
    line_items: Optional[List[SalesInvoiceLineItemResponse]] = None
    
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class SalesInvoiceListResponse(BaseModel):
    """List response for sales invoices"""
    invoices: List[SalesInvoiceResponse]
    total: int
    page: int
    page_size: int
    stats: Optional[dict] = None


class SalesInvoiceConfirmRequest(BaseModel):
    """Request to confirm a sales invoice"""
    amount_received: Decimal = Field(..., ge=0)


class SalesInvoiceCancelRequest(BaseModel):
    """Request to cancel a sales invoice"""
    cancellation_reason: str = Field(..., min_length=5, max_length=500)


# ==================== STOCK VALIDATION SCHEMAS ====================
# DC_STOCK_VALIDATION: Periodic stock validation with VGK Supreme approval

class StockValidationType(str, Enum):
    ON_DEMAND = "ON_DEMAND"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"


class StockValidationStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    VERIFIED = "VERIFIED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ReasonForDifference(str, Enum):
    DAMAGED = "DAMAGED"
    STOLEN = "STOLEN"
    MISCOUNTED = "MISCOUNTED"
    TRANSFER_PENDING = "TRANSFER_PENDING"
    EXPIRED = "EXPIRED"
    QUALITY_ISSUE = "QUALITY_ISSUE"
    OTHER = "OTHER"


class StockValidationSessionCreate(BaseModel):
    """Create a new stock validation session"""
    company_id: int = Field(..., description="Company ID for validation")
    validation_date: date = Field(..., description="Date of validation")
    validation_type: StockValidationType = Field(default=StockValidationType.ON_DEMAND)
    validation_period: Optional[str] = Field(None, max_length=20)
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    item_category: Optional[str] = Field(None, description="Filter by item category")
    color_filter: Optional[str] = Field(None, description="Filter by color")
    auto_populate_items: bool = Field(default=True, description="Auto-populate items from stock")
    
    model_config = {"extra": "forbid"}


class StockValidationSessionUpdate(BaseModel):
    """Update stock validation session"""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    status: Optional[StockValidationStatus] = None
    
    model_config = {"extra": "forbid"}


class StockValidationEntryCreate(BaseModel):
    """Create a new validation entry (for new items)"""
    item_id: int = Field(..., description="Stock item ID")
    physical_qty: Optional[Decimal] = Field(None, ge=0, description="Physical count")
    serial_numbers_found: Optional[List[str]] = Field(None, description="Serial numbers found")
    reason_for_difference: Optional[ReasonForDifference] = None
    difference_notes: Optional[str] = None
    
    model_config = {"extra": "forbid"}


class StockValidationEntryUpdate(BaseModel):
    """Update physical count for a validation entry"""
    physical_qty: Optional[Decimal] = Field(None, ge=0, description="Physical count")
    serial_numbers_found: Optional[List[str]] = Field(None, description="Serial numbers found")
    reason_for_difference: Optional[ReasonForDifference] = None
    difference_notes: Optional[str] = None
    is_verified: Optional[bool] = None
    
    model_config = {"extra": "forbid"}


class StockValidationEntryBulkUpdate(BaseModel):
    """Bulk update entries from Excel import"""
    entries: List[Dict[str, Any]] = Field(..., description="List of entry updates with item_code/item_id and physical_qty")
    
    model_config = {"extra": "forbid"}


class StockValidationApprovalRequest(BaseModel):
    """Request for VGK Supreme approval"""
    action: str = Field(..., description="approve or reject")
    approval_notes: Optional[str] = Field(None, max_length=500)
    rejection_reason: Optional[str] = Field(None, max_length=500)
    
    model_config = {"extra": "forbid"}
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        if v.lower() not in ['approve', 'reject']:
            raise ValueError('Action must be "approve" or "reject"')
        return v.lower()


class StockValidationEntryResponse(BaseModel):
    """Response schema for validation entry"""
    id: int
    session_id: int
    item_id: int
    item_code: str
    item_name: str
    item_category: Optional[str] = None
    specification: Optional[str] = None
    color: Optional[str] = None
    unit_of_measure: str
    system_qty: Decimal
    system_value: Decimal
    physical_qty: Optional[Decimal] = None
    physical_value: Optional[Decimal] = None
    difference_qty: Optional[Decimal] = None
    difference_value: Optional[Decimal] = None
    serial_numbers_expected: Optional[List[str]] = None
    serial_numbers_found: Optional[List[str]] = None
    serial_numbers_missing: Optional[List[str]] = None
    serial_numbers_extra: Optional[List[str]] = None
    reason_for_difference: Optional[str] = None
    difference_notes: Optional[str] = None
    is_verified: bool
    verified_by_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    adjustment_processed: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class StockValidationSessionResponse(BaseModel):
    """Response schema for validation session"""
    id: int
    session_number: str
    company_id: int
    company_name: Optional[str] = None
    validation_date: date
    validation_type: str
    validation_period: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    total_items: int
    items_verified: int
    items_with_discrepancy: int
    total_system_value: Decimal
    total_physical_value: Decimal
    total_difference_value: Decimal
    status: str
    initiated_by_id: Optional[int] = None
    initiated_by_name: Optional[str] = None
    initiated_at: Optional[datetime] = None
    submitted_by_id: Optional[int] = None
    submitted_at: Optional[datetime] = None
    approved_by_id: Optional[int] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    rejected_by_id: Optional[int] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    entries: Optional[List[StockValidationEntryResponse]] = None
    
    model_config = ConfigDict(from_attributes=True)


class StockValidationSessionListResponse(BaseModel):
    """List response for validation sessions"""
    sessions: List[StockValidationSessionResponse]
    total: int
    page: int
    page_size: int
    stats: Optional[dict] = None


class StockValidationAuditLogResponse(BaseModel):
    """Response for validation audit log"""
    id: int
    session_id: int
    entry_id: Optional[int] = None
    action: str
    action_details: Optional[dict] = None
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None
    performed_by_id: int
    performed_by_name: Optional[str] = None
    performed_at: datetime
    ip_address: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class NewStockItemFromValidation(BaseModel):
    """Create new stock item with opening quantity from validation page"""
    item_code: str = Field(..., min_length=2, max_length=30)
    item_name: str = Field(..., min_length=2, max_length=200)
    item_category: str = Field(default="PRODUCT")
    specification: Optional[str] = None
    size: Optional[str] = Field(None, max_length=100)
    colors: Optional[List[str]] = None
    unit_of_measure: str = Field(default="PCS")
    hsn_code: Optional[str] = Field(None, max_length=20)
    purchase_rate: Optional[Decimal] = Field(None, ge=0)
    selling_rate: Optional[Decimal] = Field(None, ge=0)
    opening_quantity: Decimal = Field(..., ge=0, description="Opening stock quantity")
    serial_numbers: Optional[List[str]] = Field(None, description="Serial numbers if applicable")
    
    model_config = {"extra": "forbid"}
    
    @field_validator('item_code')
    @classmethod
    def validate_item_code(cls, v):
        if v:
            return v.upper().strip()
        return v


class AddExistingItemToValidation(BaseModel):
    """Add existing stock item(s) to a validation session"""
    item_ids: List[int] = Field(..., min_length=1, description="List of stock item IDs to add")
    
    model_config = {"extra": "forbid"}


# ==================== PURCHASE INTAKE BATCH SCHEMAS (DC_INTAKE_001) ====================

class IntakeBatchStatus(str, Enum):
    PENDING_RECEIPT = "PENDING_RECEIPT"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    FULLY_RECEIVED = "FULLY_RECEIVED"
    QC_PENDING = "QC_PENDING"
    QC_IN_PROGRESS = "QC_IN_PROGRESS"
    QC_COMPLETE = "QC_COMPLETE"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class IntakeItemQCStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"


class IntakeItemDisposition(str, Enum):
    STOCK = "STOCK"
    RETURN = "RETURN"
    EXCHANGE = "EXCHANGE"
    PENDING_VENDOR = "PENDING_VENDOR"
    SCRAPPED = "SCRAPPED"


class QCChecklistItem(BaseModel):
    """Standard QC checklist item"""
    physical_condition: str = Field(..., description="OK or NOT_OK")
    specification_match: str = Field(..., description="OK or NOT_OK")
    color_match: str = Field(default="NA", description="OK, NOT_OK, or NA")
    packaging_intact: str = Field(default="OK", description="OK or NOT_OK")
    serial_verified: str = Field(default="NA", description="OK, NOT_OK, or NA")
    documentation_complete: str = Field(default="OK", description="OK or NOT_OK")
    quantity_match: str = Field(default="OK", description="OK or NOT_OK")
    remarks: Optional[str] = None
    
    model_config = {"extra": "allow"}
    
    @field_validator('physical_condition', 'specification_match', 'packaging_intact', 'documentation_complete', 'quantity_match')
    @classmethod
    def validate_ok_notok(cls, v):
        valid = ['OK', 'NOT_OK']
        if v and v.upper() not in valid:
            raise ValueError(f'Must be one of: {valid}')
        return v.upper() if v else v
    
    @field_validator('color_match', 'serial_verified')
    @classmethod
    def validate_ok_notok_na(cls, v):
        valid = ['OK', 'NOT_OK', 'NA']
        if v and v.upper() not in valid:
            raise ValueError(f'Must be one of: {valid}')
        return v.upper() if v else v


class PurchaseIntakeItemBase(BaseModel):
    """Base schema for intake item"""
    item_id: Optional[int] = None
    item_code: Optional[str] = Field(None, max_length=30)
    item_name: str = Field(..., min_length=1, max_length=200)
    item_description: Optional[str] = None
    hsn_code: Optional[str] = Field(None, max_length=20)
    serial_number: Optional[str] = Field(None, max_length=100)
    imei_number: Optional[str] = Field(None, max_length=50)
    batch_number: Optional[str] = Field(None, max_length=50)
    unit_of_measure: str = Field(default="PCS", max_length=20)
    unit_rate: Decimal = Field(default=0, ge=0)
    ordered_qty: Decimal = Field(default=0, ge=0)
    specification: Optional[str] = None
    color: Optional[str] = Field(None, max_length=100)
    warranty_months: Optional[int] = Field(None, ge=0)
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    
    model_config = {"extra": "forbid"}


class PurchaseIntakeItemCreate(PurchaseIntakeItemBase):
    """Create schema for intake item"""
    purchase_line_id: Optional[int] = None


class PurchaseIntakeItemUpdate(BaseModel):
    """Update schema for intake item - for recording receipt"""
    received_qty: Decimal = Field(..., ge=0, description="Quantity actually received")
    serial_number: Optional[str] = Field(None, max_length=100)
    imei_number: Optional[str] = Field(None, max_length=50)
    batch_number: Optional[str] = Field(None, max_length=50)
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    warranty_months: Optional[int] = Field(None, ge=0)
    
    model_config = {"extra": "forbid"}


class PurchaseIntakeItemQCSubmit(BaseModel):
    """Submit QC result for intake item"""
    accepted_qty: Decimal = Field(..., ge=0, description="Quantity that passed QC")
    rejected_qty: Decimal = Field(default=0, ge=0, description="Quantity that failed QC")
    qc_checklist: QCChecklistItem
    rejection_reason: Optional[str] = Field(None, description="Required if any rejected")
    rejection_category: Optional[str] = Field(None, max_length=50)
    disposition: Optional[IntakeItemDisposition] = None
    
    model_config = {"extra": "forbid"}
    
    @model_validator(mode='after')
    def validate_rejection(self):
        if self.rejected_qty > 0 and not self.rejection_reason:
            raise ValueError('Rejection reason is required when rejected_qty > 0')
        return self


class PurchaseIntakeItemResponse(BaseModel):
    """Response schema for intake item"""
    id: int
    batch_id: int
    purchase_line_id: Optional[int] = None
    item_id: Optional[int] = None
    item_code: Optional[str] = None
    item_name: str
    item_description: Optional[str] = None
    hsn_code: Optional[str] = None
    serial_number: Optional[str] = None
    imei_number: Optional[str] = None
    batch_number: Optional[str] = None
    unit_of_measure: str
    unit_rate: Decimal
    ordered_qty: Decimal
    received_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal
    ordered_value: Decimal
    received_value: Decimal
    accepted_value: Decimal
    rejected_value: Decimal
    qc_status: str
    qc_checklist: Optional[dict] = None
    disposition: Optional[str] = None
    qc_by_id: Optional[int] = None
    qc_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    rejection_category: Optional[str] = None
    warranty_months: Optional[int] = None
    warranty_start_date: Optional[date] = None
    warranty_end_date: Optional[date] = None
    specification: Optional[str] = None
    color: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class PurchaseIntakeBatchCreate(BaseModel):
    """Create schema for intake batch"""
    purchase_invoice_id: int = Field(..., description="Source purchase invoice ID")
    vendor_id: Optional[int] = None
    receipt_notes: Optional[str] = None
    items: Optional[List[PurchaseIntakeItemCreate]] = None
    
    model_config = {"extra": "forbid"}


class PurchaseIntakeBatchReceive(BaseModel):
    """Record receipt of items in batch"""
    receipt_notes: Optional[str] = None
    items: List[PurchaseIntakeItemUpdate] = Field(..., min_length=1)
    
    model_config = {"extra": "forbid"}


class PurchaseIntakeBatchQCSubmit(BaseModel):
    """Submit QC results for batch"""
    items: List[Dict[str, Any]] = Field(..., min_length=1, description="List of {item_id, qc_data}")
    
    model_config = {"extra": "forbid"}


class PurchaseIntakeBatchApprove(BaseModel):
    """Approve intake batch"""
    approval_notes: Optional[str] = None
    
    model_config = {"extra": "forbid"}


class PurchaseIntakeBatchReject(BaseModel):
    """Reject intake batch"""
    rejection_reason: str = Field(..., min_length=5)
    
    model_config = {"extra": "forbid"}


class PurchaseIntakeBatchResponse(BaseModel):
    """Response schema for intake batch"""
    id: int
    batch_number: str
    company_id: int
    purchase_invoice_id: int
    vendor_id: Optional[int] = None
    vendor_name: Optional[str] = None
    total_ordered_qty: Decimal
    total_received_qty: Decimal
    total_accepted_qty: Decimal
    total_rejected_qty: Decimal
    total_pending_qty: Decimal
    total_ordered_value: Decimal
    total_received_value: Decimal
    total_accepted_value: Decimal
    total_rejected_value: Decimal
    intake_status: str
    received_by_id: Optional[int] = None
    received_at: Optional[datetime] = None
    receipt_notes: Optional[str] = None
    qc_started_at: Optional[datetime] = None
    qc_completed_at: Optional[datetime] = None
    submitted_for_approval_at: Optional[datetime] = None
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    rejected_by_id: Optional[int] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    stock_ledger_updated: bool
    validation_session_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: Optional[List[PurchaseIntakeItemResponse]] = None
    
    model_config = ConfigDict(from_attributes=True)


class PurchaseIntakeBatchListResponse(BaseModel):
    """List response for intake batches"""
    batches: List[PurchaseIntakeBatchResponse]
    total: int
    page: int
    page_size: int


# ==================== INVENTORY LIFECYCLE EVENT SCHEMAS (DC_LIFECYCLE_001) ====================

class LifecycleEventType(str, Enum):
    PURCHASE_ORDERED = "PURCHASE_ORDERED"
    PURCHASE_RECEIVED = "PURCHASE_RECEIVED"
    QC_STARTED = "QC_STARTED"
    QC_PASSED = "QC_PASSED"
    QC_REJECTED = "QC_REJECTED"
    ADDED_TO_STOCK = "ADDED_TO_STOCK"
    REMOVED_FROM_STOCK = "REMOVED_FROM_STOCK"
    TRANSFERRED = "TRANSFERRED"
    DISPATCHED_TO_SERVICE = "DISPATCHED_TO_SERVICE"
    RECEIVED_AT_SERVICE = "RECEIVED_AT_SERVICE"
    DIAGNOSIS_COMPLETE = "DIAGNOSIS_COMPLETE"
    REPAIR_STARTED = "REPAIR_STARTED"
    REPAIR_COMPLETE = "REPAIR_COMPLETE"
    DISPATCHED_TO_VENDOR = "DISPATCHED_TO_VENDOR"
    VENDOR_RECEIVED = "VENDOR_RECEIVED"
    VENDOR_RETURNED = "VENDOR_RETURNED"
    CREDIT_NOTE_ISSUED = "CREDIT_NOTE_ISSUED"
    EXCHANGE_RECEIVED = "EXCHANGE_RECEIVED"
    REPLACEMENT_ISSUED = "REPLACEMENT_ISSUED"
    RETURNED_TO_CUSTOMER = "RETURNED_TO_CUSTOMER"
    SCRAPPED = "SCRAPPED"
    ADJUSTED = "ADJUSTED"


class InventoryLifecycleEventCreate(BaseModel):
    """Create lifecycle event"""
    item_id: Optional[int] = None
    item_code: Optional[str] = Field(None, max_length=30)
    item_name: Optional[str] = Field(None, max_length=200)
    serial_number: Optional[str] = Field(None, max_length=100)
    imei_number: Optional[str] = Field(None, max_length=50)
    batch_number: Optional[str] = Field(None, max_length=50)
    event_type: LifecycleEventType
    source_document_type: Optional[str] = Field(None, max_length=50)
    source_document_id: Optional[int] = None
    source_document_number: Optional[str] = Field(None, max_length=50)
    from_location: Optional[str] = Field(None, max_length=100)
    to_location: Optional[str] = Field(None, max_length=100)
    from_entity_type: Optional[str] = Field(None, max_length=30)
    from_entity_id: Optional[int] = None
    from_entity_name: Optional[str] = Field(None, max_length=200)
    to_entity_type: Optional[str] = Field(None, max_length=30)
    to_entity_id: Optional[int] = None
    to_entity_name: Optional[str] = Field(None, max_length=200)
    quantity: Decimal = Field(default=1, ge=0)
    unit_value: Optional[Decimal] = Field(None, ge=0)
    total_value: Optional[Decimal] = Field(None, ge=0)
    event_data: Optional[dict] = None
    
    model_config = {"extra": "forbid"}


class InventoryLifecycleEventResponse(BaseModel):
    """Response for lifecycle event"""
    id: int
    event_id: str
    company_id: int
    item_id: Optional[int] = None
    item_code: Optional[str] = None
    item_name: Optional[str] = None
    serial_number: Optional[str] = None
    imei_number: Optional[str] = None
    batch_number: Optional[str] = None
    event_type: str
    source_document_type: Optional[str] = None
    source_document_id: Optional[int] = None
    source_document_number: Optional[str] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    from_entity_type: Optional[str] = None
    from_entity_id: Optional[int] = None
    from_entity_name: Optional[str] = None
    to_entity_type: Optional[str] = None
    to_entity_id: Optional[int] = None
    to_entity_name: Optional[str] = None
    quantity: Decimal
    unit_value: Optional[Decimal] = None
    total_value: Optional[Decimal] = None
    event_data: Optional[dict] = None
    event_by_id: Optional[int] = None
    event_by_partner_id: Optional[int] = None
    event_at: datetime
    checksum: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class InventoryLifecycleHistoryResponse(BaseModel):
    """Response for item lifecycle history"""
    serial_number: Optional[str] = None
    item_name: Optional[str] = None
    events: List[InventoryLifecycleEventResponse]
    total: int


# ==================== VENDOR RETURN REQUEST SCHEMAS (DC_RETURN_001) ====================

class VendorReturnType(str, Enum):
    RETURN = "RETURN"
    EXCHANGE = "EXCHANGE"


class VendorReturnStatus(str, Enum):
    CREATED = "CREATED"
    VENDOR_NOTIFIED = "VENDOR_NOTIFIED"
    VENDOR_ACKNOWLEDGED = "VENDOR_ACKNOWLEDGED"
    PICKUP_SCHEDULED = "PICKUP_SCHEDULED"
    IN_TRANSIT = "IN_TRANSIT"
    VENDOR_RECEIVED = "VENDOR_RECEIVED"
    CREDIT_NOTE_PENDING = "CREDIT_NOTE_PENDING"
    CREDIT_NOTE_ISSUED = "CREDIT_NOTE_ISSUED"
    EXCHANGE_DISPATCHED = "EXCHANGE_DISPATCHED"
    EXCHANGE_RECEIVED = "EXCHANGE_RECEIVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class VendorReturnItemStatus(str, Enum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    RECEIVED_BY_VENDOR = "RECEIVED_BY_VENDOR"
    CREDIT_ISSUED = "CREDIT_ISSUED"
    EXCHANGE_DISPATCHED = "EXCHANGE_DISPATCHED"
    EXCHANGE_RECEIVED = "EXCHANGE_RECEIVED"
    CLOSED = "CLOSED"


class VendorReturnItemCreate(BaseModel):
    """Create schema for return item"""
    intake_item_id: Optional[int] = None
    item_id: Optional[int] = None
    item_code: Optional[str] = Field(None, max_length=30)
    item_name: str = Field(..., min_length=1, max_length=200)
    serial_number: Optional[str] = Field(None, max_length=100)
    imei_number: Optional[str] = Field(None, max_length=50)
    batch_number: Optional[str] = Field(None, max_length=50)
    quantity: Decimal = Field(default=1, ge=0)
    unit_rate: Decimal = Field(default=0, ge=0)
    rejection_reason: str = Field(..., min_length=5)
    rejection_category: Optional[str] = Field(None, max_length=50)
    qc_checklist: Optional[dict] = None
    
    model_config = {"extra": "forbid"}


class VendorReturnItemResponse(BaseModel):
    """Response for return item"""
    id: int
    request_id: int
    intake_item_id: Optional[int] = None
    item_id: Optional[int] = None
    item_code: Optional[str] = None
    item_name: str
    serial_number: Optional[str] = None
    imei_number: Optional[str] = None
    batch_number: Optional[str] = None
    quantity: Decimal
    unit_rate: Decimal
    total_value: Decimal
    rejection_reason: Optional[str] = None
    rejection_category: Optional[str] = None
    qc_checklist: Optional[dict] = None
    item_status: str
    exchange_serial_number: Optional[str] = None
    exchange_imei_number: Optional[str] = None
    exchange_qc_status: Optional[str] = None
    exchange_qc_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class VendorReturnRequestCreate(BaseModel):
    """Create schema for return request"""
    vendor_id: int
    intake_batch_id: Optional[int] = None
    request_type: VendorReturnType
    items: List[VendorReturnItemCreate] = Field(..., min_length=1)
    
    model_config = {"extra": "forbid"}


class VendorReturnRequestNotify(BaseModel):
    """Send notification to vendor"""
    notification_method: str = Field(default="EMAIL", description="EMAIL, WHATSAPP, or BOTH")
    custom_message: Optional[str] = None
    
    model_config = {"extra": "forbid"}
    
    @field_validator('notification_method')
    @classmethod
    def validate_method(cls, v):
        valid = ['EMAIL', 'WHATSAPP', 'BOTH']
        if v and v.upper() not in valid:
            raise ValueError(f'Must be one of: {valid}')
        return v.upper() if v else 'EMAIL'


class VendorReturnRequestDispatch(BaseModel):
    """Record dispatch to vendor"""
    dispatch_date: date
    dispatch_courier: Optional[str] = Field(None, max_length=100)
    dispatch_tracking_number: Optional[str] = Field(None, max_length=100)
    dispatch_notes: Optional[str] = None
    
    model_config = {"extra": "forbid"}


class VendorReturnRequestCreditNote(BaseModel):
    """Record credit note received"""
    credit_note_number: str = Field(..., max_length=50)
    credit_note_date: date
    credit_note_amount: Decimal = Field(..., ge=0)
    
    model_config = {"extra": "forbid"}


class VendorReturnRequestResponse(BaseModel):
    """Response for return request"""
    id: int
    request_number: str
    company_id: int
    vendor_id: int
    vendor_name: Optional[str] = None
    intake_batch_id: Optional[int] = None
    request_type: str
    total_items: int
    total_qty: Decimal
    total_value: Decimal
    status: str
    vendor_response_deadline: Optional[datetime] = None
    vendor_acknowledged_at: Optional[datetime] = None
    vendor_remarks: Optional[str] = None
    dispatch_date: Optional[date] = None
    dispatch_courier: Optional[str] = None
    dispatch_tracking_number: Optional[str] = None
    received_by_vendor_at: Optional[datetime] = None
    credit_note_number: Optional[str] = None
    credit_note_date: Optional[date] = None
    credit_note_amount: Optional[Decimal] = None
    exchange_received_at: Optional[datetime] = None
    exchange_qc_status: Optional[str] = None
    sfms_journal_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: Optional[List[VendorReturnItemResponse]] = None
    
    model_config = ConfigDict(from_attributes=True)


class VendorReturnRequestListResponse(BaseModel):
    """List response for return requests"""
    requests: List[VendorReturnRequestResponse]
    total: int
    page: int
    page_size: int


# ==================== SERVICE CENTER RECEIPT SCHEMAS (DC_SERVICE_001) ====================

class ServiceReceiptStatus(str, Enum):
    REGISTERED = "REGISTERED"
    DIAGNOSIS_PENDING = "DIAGNOSIS_PENDING"
    DIAGNOSIS_IN_PROGRESS = "DIAGNOSIS_IN_PROGRESS"
    DIAGNOSED = "DIAGNOSED"
    REPAIR_IN_PROGRESS = "REPAIR_IN_PROGRESS"
    REPAIRED = "REPAIRED"
    REPLACEMENT_PENDING = "REPLACEMENT_PENDING"
    REPLACEMENT_ISSUED = "REPLACEMENT_ISSUED"
    ESCALATED = "ESCALATED"
    RETURNED_TO_CUSTOMER = "RETURNED_TO_CUSTOMER"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class DiagnosisResult(str, Enum):
    REPAIRABLE = "REPAIRABLE"
    REPLACEMENT_REQUIRED = "REPLACEMENT_REQUIRED"
    ESCALATE_TO_VENDOR = "ESCALATE_TO_VENDOR"
    NO_ISSUE_FOUND = "NO_ISSUE_FOUND"
    BEYOND_REPAIR = "BEYOND_REPAIR"


class ServiceCenterReceiptCreate(BaseModel):
    """Create service center receipt"""
    service_ticket_id: Optional[int] = None
    customer_name: Optional[str] = Field(None, max_length=200)
    customer_contact: Optional[str] = Field(None, max_length=20)
    customer_email: Optional[str] = Field(None, max_length=200)
    customer_address: Optional[str] = None
    item_id: Optional[int] = None
    item_code: Optional[str] = Field(None, max_length=30)
    item_name: str = Field(..., min_length=1, max_length=200)
    item_description: Optional[str] = None
    serial_number: Optional[str] = Field(None, max_length=100)
    imei_number: Optional[str] = Field(None, max_length=50)
    item_condition_on_receipt: Optional[dict] = None
    reported_issue: Optional[str] = None
    accessories_received: Optional[List[str]] = None
    warranty_status: Optional[str] = Field(None, max_length=20)
    
    model_config = {"extra": "forbid"}


class ServiceCenterReceiptDiagnosis(BaseModel):
    """Submit diagnosis result"""
    diagnosis_result: DiagnosisResult
    diagnosis_notes: Optional[str] = None
    diagnosis_cost_estimate: Optional[Decimal] = Field(None, ge=0)
    
    model_config = {"extra": "forbid"}


class ServiceCenterReceiptRepair(BaseModel):
    """Record repair completion"""
    repair_notes: Optional[str] = None
    repair_cost: Optional[Decimal] = Field(None, ge=0)
    parts_used: Optional[List[dict]] = None
    
    model_config = {"extra": "forbid"}


class ServiceCenterReceiptReplacement(BaseModel):
    """Record replacement issued"""
    replacement_item_id: Optional[int] = None
    replacement_serial_number: Optional[str] = Field(None, max_length=100)
    
    model_config = {"extra": "forbid"}


class ServiceCenterReceiptReturn(BaseModel):
    """Record return to customer"""
    customer_acknowledgment: Optional[str] = None
    
    model_config = {"extra": "forbid"}


class ServiceCenterReceiptEscalate(BaseModel):
    """Escalate to head office / vendor"""
    escalation_reason: str = Field(..., min_length=5)
    
    model_config = {"extra": "forbid"}


class ServiceCenterReceiptResponse(BaseModel):
    """Response for service center receipt"""
    id: int
    receipt_number: str
    company_id: int
    service_center_id: int
    service_center_name: Optional[str] = None
    service_ticket_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_contact: Optional[str] = None
    customer_email: Optional[str] = None
    item_id: Optional[int] = None
    item_code: Optional[str] = None
    item_name: str
    item_description: Optional[str] = None
    serial_number: Optional[str] = None
    imei_number: Optional[str] = None
    item_condition_on_receipt: Optional[dict] = None
    reported_issue: Optional[str] = None
    accessories_received: Optional[List[str]] = None
    receipt_status: str
    received_at: datetime
    diagnosis_status: Optional[str] = None
    diagnosis_result: Optional[str] = None
    diagnosis_notes: Optional[str] = None
    diagnosis_cost_estimate: Optional[Decimal] = None
    diagnosed_at: Optional[datetime] = None
    repair_status: Optional[str] = None
    repair_notes: Optional[str] = None
    repair_cost: Optional[Decimal] = None
    parts_used: Optional[List[dict]] = None
    repaired_at: Optional[datetime] = None
    replacement_serial_number: Optional[str] = None
    replacement_issued_at: Optional[datetime] = None
    returned_to_customer_at: Optional[datetime] = None
    escalated_to_head_office: bool
    escalation_date: Optional[datetime] = None
    escalation_reason: Optional[str] = None
    warranty_status: Optional[str] = None
    warranty_claim_number: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class ServiceCenterReceiptListResponse(BaseModel):
    """List response for service center receipts"""
    receipts: List[ServiceCenterReceiptResponse]
    total: int
    page: int
    page_size: int


# ==================== SERVICE CENTER DISPATCH SCHEMAS (DC_SERVICE_002) ====================

class DispatchType(str, Enum):
    WARRANTY_CLAIM = "WARRANTY_CLAIM"
    REPLACEMENT_REQUEST = "REPLACEMENT_REQUEST"
    REPAIR_REQUEST = "REPAIR_REQUEST"
    RETURN = "RETURN"


class DispatchStatus(str, Enum):
    DRAFT = "DRAFT"
    DISPATCHED = "DISPATCHED"
    VENDOR_ACKNOWLEDGED = "VENDOR_ACKNOWLEDGED"
    IN_PROCESS = "IN_PROCESS"
    REPLACEMENT_DISPATCHED = "REPLACEMENT_DISPATCHED"
    REPLACEMENT_RECEIVED = "REPLACEMENT_RECEIVED"
    QC_PENDING = "QC_PENDING"
    QC_COMPLETE = "QC_COMPLETE"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class ServiceCenterDispatchCreate(BaseModel):
    """Create service center dispatch to vendor"""
    vendor_id: int
    dispatch_type: DispatchType
    linked_receipt_ids: List[int] = Field(..., min_length=1)
    dispatch_notes: Optional[str] = None
    expected_resolution_date: Optional[date] = None
    
    model_config = {"extra": "forbid"}


class ServiceCenterDispatchSend(BaseModel):
    """Record dispatch sent to vendor"""
    dispatch_courier: Optional[str] = Field(None, max_length=100)
    dispatch_tracking_number: Optional[str] = Field(None, max_length=100)
    dispatch_notes: Optional[str] = None
    
    model_config = {"extra": "forbid"}


class ServiceCenterDispatchVendorAck(BaseModel):
    """Vendor acknowledgment"""
    vendor_remarks: Optional[str] = None
    
    model_config = {"extra": "forbid"}


class ServiceCenterDispatchReplacementReceived(BaseModel):
    """Record replacement received"""
    replacement_courier: Optional[str] = Field(None, max_length=100)
    replacement_tracking_number: Optional[str] = Field(None, max_length=100)
    replacement_qc_notes: Optional[str] = None
    
    model_config = {"extra": "forbid"}


class ServiceCenterDispatchClose(BaseModel):
    """Close dispatch"""
    closure_notes: Optional[str] = None
    
    model_config = {"extra": "forbid"}


class ServiceCenterDispatchResponse(BaseModel):
    """Response for service center dispatch"""
    id: int
    dispatch_number: str
    company_id: int
    service_center_id: int
    service_center_name: Optional[str] = None
    vendor_id: int
    vendor_name: Optional[str] = None
    dispatch_type: str
    total_items: int
    status: str
    dispatched_at: Optional[datetime] = None
    dispatch_courier: Optional[str] = None
    dispatch_tracking_number: Optional[str] = None
    dispatch_notes: Optional[str] = None
    vendor_acknowledged_at: Optional[datetime] = None
    vendor_remarks: Optional[str] = None
    expected_resolution_date: Optional[date] = None
    replacement_dispatched_at: Optional[datetime] = None
    replacement_received_at: Optional[datetime] = None
    replacement_qc_status: Optional[str] = None
    linked_receipt_ids: Optional[List[int]] = None
    closed_at: Optional[datetime] = None
    closure_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class ServiceCenterDispatchListResponse(BaseModel):
    """List response for service center dispatches"""
    dispatches: List[ServiceCenterDispatchResponse]
    total: int
    page: int
    page_size: int
