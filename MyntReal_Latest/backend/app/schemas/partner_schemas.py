"""
Official Partner Order Management System - Pydantic Schemas
DC_PARTNER_001: Request/Response validation schemas
"""
from pydantic import BaseModel, Field, field_validator, validator
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class PartnerCategory(str, Enum):
    DEALER = "DEALER"
    DISTRIBUTOR = "DISTRIBUTOR"
    VENDOR = "VENDOR"
    REAL_DREAM_PARTNER = "REAL_DREAM_PARTNER"
    SERVICE_CENTER = "SERVICE_CENTER"  # DC Protocol Jan 2026


class PartnerStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING_APPROVAL = "PENDING_APPROVAL"


class OrderStatus(str, Enum):
    DRAFT = "DRAFT"
    PI_GENERATED = "PI_GENERATED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_CONFIRMED = "PAYMENT_CONFIRMED"
    ROUTED_TO_PRODUCTION = "ROUTED_TO_PRODUCTION"
    ROUTED_TO_PROCUREMENT = "ROUTED_TO_PROCUREMENT"
    IN_MANUFACTURING = "IN_MANUFACTURING"
    PROCUREMENT_IN_PROGRESS = "PROCUREMENT_IN_PROGRESS"
    READY_TO_DISPATCH = "READY_TO_DISPATCH"
    DISPATCHED = "DISPATCHED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


class RoutedTo(str, Enum):
    PRODUCTION = "PRODUCTION"
    PROCUREMENT = "PROCUREMENT"
    DIRECT_DISPATCH = "DIRECT_DISPATCH"


class PaymentMode(str, Enum):
    BANK_TRANSFER = "BANK_TRANSFER"
    CHEQUE = "CHEQUE"
    CASH = "CASH"
    UPI = "UPI"
    NEFT = "NEFT"
    RTGS = "RTGS"
    CREDIT = "CREDIT"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class DispatchStatus(str, Enum):
    PENDING = "PENDING"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    RETURNED = "RETURNED"


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


class PartnerType(str, Enum):
    PRODUCT = "PRODUCT"
    SERVICE = "SERVICE"
    BOTH = "BOTH"


class OfficialPartnerCreate(BaseModel):
    partner_code: str = Field(..., max_length=20, description="Unique partner code")
    partner_name: str = Field(..., max_length=200, description="Partner business name")
    category: PartnerCategory
    partner_type: Optional[PartnerType] = None
    
    contact_person: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    alternate_phone: Optional[str] = Field(None, max_length=20)
    whatsapp_number: Optional[str] = Field(None, max_length=20)
    
    contact_person_1_name: Optional[str] = Field(None, max_length=200)
    contact_person_1_phone: Optional[str] = Field(None, max_length=20)
    contact_person_1_designation: Optional[str] = Field(None, max_length=100)
    
    contact_person_2_name: Optional[str] = Field(None, max_length=200)
    contact_person_2_phone: Optional[str] = Field(None, max_length=20)
    contact_person_2_designation: Optional[str] = Field(None, max_length=100)
    
    gstin: Optional[str] = Field(None, max_length=20)
    pan: Optional[str] = Field(None, max_length=15)
    
    billing_address: Optional[str] = None
    billing_city: Optional[str] = Field(None, max_length=100)
    billing_state: Optional[str] = Field(None, max_length=100)
    billing_pincode: Optional[str] = Field(None, max_length=10)
    
    shipping_address: Optional[str] = None
    shipping_city: Optional[str] = Field(None, max_length=100)
    shipping_state: Optional[str] = Field(None, max_length=100)
    shipping_pincode: Optional[str] = Field(None, max_length=10)
    
    map_link_1: Optional[str] = Field(None, max_length=500)
    map_link_1_label: Optional[str] = Field(None, max_length=100)
    map_link_2: Optional[str] = Field(None, max_length=500)
    map_link_2_label: Optional[str] = Field(None, max_length=100)
    
    bank_name: Optional[str] = Field(None, max_length=200)
    bank_branch: Optional[str] = Field(None, max_length=200)
    account_number: Optional[str] = Field(None, max_length=30)
    ifsc_code: Optional[str] = Field(None, max_length=15)
    payment_scanner_qr_url: Optional[str] = Field(None, max_length=500)
    
    payment_terms: Optional[str] = Field(None, max_length=20)
    credit_limit: Optional[float] = Field(0, ge=0)
    payment_terms_days: Optional[int] = Field(30, ge=0)
    credit_days: Optional[int] = Field(None, ge=0)
    
    company_ids: List[int] = Field(..., description="List of company IDs to assign")
    segment_ids: Optional[List[int]] = Field(None, description="List of segment IDs to assign")
    
    # DC Protocol Jan 2026: Service Center specific fields
    service_coverage_radius_km: Optional[int] = Field(None, ge=1, le=500, description="Service area coverage in km")
    certified_technician_count: Optional[int] = Field(None, ge=0, le=100, description="Number of certified technicians")
    specialized_equipment_list: Optional[str] = Field(None, description="Comma-separated list of specialized equipment")
    service_center_sla_hours: Optional[int] = Field(24, ge=1, le=168, description="Custom SLA in hours")

    # [DC-PARTNER-CONTACTS-001] Dedicated sales & service contacts
    sales_contact_number: Optional[str] = Field(None, max_length=20, description="Sales point-of-contact number")
    sales_contact_name: Optional[str] = Field(None, max_length=200, description="Sales contact name (optional)")
    service_contact_number: Optional[str] = Field(None, max_length=20, description="Service point-of-contact number")
    service_contact_name: Optional[str] = Field(None, max_length=200, description="Service contact name (optional)")

    # [DC-PARTNER-CONTACTS-001] Per-module on/off settings
    module_settings: Optional[Dict[str, Any]] = Field(None, description="Per-module enable flags e.g. {walkins:true, leads:false}")

    # [DC-PARTNER-GST-001] Apr 2026: GST treatment type
    gst_type: Optional[str] = Field('CGST_SGST', max_length=10, description="GST treatment: IGST or CGST_SGST")

    # [DC-PARTNER-KYC-001] May 2026: Aadhaar number text
    aadhaar_number: Optional[str] = Field(None, max_length=20)

    # [DC-PARTNER-TERMS-001] May 2026: Partnership agreement dates, reminder, security deposit
    partner_start_date:   Optional[date] = None
    partner_end_date:     Optional[date] = None
    reminder_days_before: Optional[int]  = Field(None, ge=1, le=365)
    security_deposit:     Optional[float] = Field(None, ge=0)

    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v
    
    @validator('gstin')
    def validate_gstin(cls, v):
        if v and len(v) != 15:
            raise ValueError('GSTIN must be 15 characters')
        return v.upper() if v else v
    
    @validator('pan')
    def validate_pan(cls, v):
        if v and len(v) != 10:
            raise ValueError('PAN must be 10 characters')
        return v.upper() if v else v


class OfficialPartnerUpdate(BaseModel):
    partner_name: Optional[str] = Field(None, max_length=200)
    category: Optional[PartnerCategory] = None
    partner_type: Optional[PartnerType] = None
    is_active: Optional[bool] = None
    
    contact_person: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    whatsapp_number: Optional[str] = Field(None, max_length=20)
    
    contact_person_1_name: Optional[str] = Field(None, max_length=200)
    contact_person_1_phone: Optional[str] = Field(None, max_length=20)
    contact_person_1_designation: Optional[str] = Field(None, max_length=100)
    
    contact_person_2_name: Optional[str] = Field(None, max_length=200)
    contact_person_2_phone: Optional[str] = Field(None, max_length=20)
    contact_person_2_designation: Optional[str] = Field(None, max_length=100)
    
    gst_number: Optional[str] = Field(None, max_length=20)
    pan_number: Optional[str] = Field(None, max_length=15)
    
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=10)
    zone: Optional[str] = Field(None, max_length=50)
    
    map_link_1: Optional[str] = Field(None, max_length=500)
    map_link_1_label: Optional[str] = Field(None, max_length=100)
    map_link_2: Optional[str] = Field(None, max_length=500)
    map_link_2_label: Optional[str] = Field(None, max_length=100)
    
    payment_terms: Optional[str] = Field(None, max_length=20)
    credit_limit: Optional[float] = None
    credit_days: Optional[int] = None
    
    bank_name: Optional[str] = Field(None, max_length=200)
    bank_branch: Optional[str] = Field(None, max_length=200)
    account_number: Optional[str] = Field(None, max_length=30)
    ifsc_code: Optional[str] = Field(None, max_length=15)
    payment_scanner_qr_url: Optional[str] = Field(None, max_length=500)
    
    # DC Protocol Jan 2026: Service Center specific fields
    service_coverage_radius_km: Optional[int] = Field(None, ge=1, le=500, description="Service area coverage in km")
    certified_technician_count: Optional[int] = Field(None, ge=0, le=100, description="Number of certified technicians")
    specialized_equipment_list: Optional[str] = Field(None, description="Comma-separated list of specialized equipment")
    service_center_sla_hours: Optional[int] = Field(None, ge=1, le=168, description="Custom SLA in hours")

    # DC_PARTNER_STATUS_001: Login/portal status control (Apr 2026)
    # active=full access; inactive=login blocked; pause=login blocked(temp);
    # expired=login blocked(contract); suspended=login blocked(disciplinary)
    login_status: Optional[str] = Field(None, description="Partner portal status: active/inactive/pause/expired/suspended")

    # [DC-PARTNER-CONTACTS-001] Dedicated sales & service contacts
    sales_contact_number: Optional[str] = Field(None, max_length=20)
    sales_contact_name: Optional[str] = Field(None, max_length=200)
    service_contact_number: Optional[str] = Field(None, max_length=20)
    service_contact_name: Optional[str] = Field(None, max_length=200)

    # [DC-PARTNER-CONTACTS-001] Per-module on/off settings
    module_settings: Optional[Dict[str, Any]] = Field(None, description="Per-module enable flags")

    # [DC-PARTNER-KYC-001/TERMS-001/DOCS-001] May 2026: KYC identity + partnership terms
    aadhaar_number:      Optional[str]   = Field(None, max_length=20)
    partner_start_date:  Optional[date]  = None
    partner_end_date:    Optional[date]  = None
    reminder_days_before: Optional[int]  = Field(None, ge=1, le=365)
    security_deposit:    Optional[float] = Field(None, ge=0)


class OfficialPartnerResponse(BaseModel):
    id: int
    partner_code: str
    partner_name: str
    category: str
    partner_type: Optional[str] = None
    is_active: bool
    
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    
    contact_person_1_name: Optional[str] = None
    contact_person_1_phone: Optional[str] = None
    contact_person_1_designation: Optional[str] = None
    
    contact_person_2_name: Optional[str] = None
    contact_person_2_phone: Optional[str] = None
    contact_person_2_designation: Optional[str] = None
    
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    zone: Optional[str] = None
    
    map_link_1: Optional[str] = None
    map_link_1_label: Optional[str] = None
    map_link_2: Optional[str] = None
    map_link_2_label: Optional[str] = None
    
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    payment_scanner_qr_url: Optional[str] = None
    
    payment_terms: Optional[str] = None
    credit_limit: float = 0
    credit_days: int = 0
    
    legacy_vendor_id: Optional[int] = None

    # [DC-PARTNER-CONTACTS-001]
    sales_contact_number: Optional[str] = None
    sales_contact_name: Optional[str] = None
    service_contact_number: Optional[str] = None
    service_contact_name: Optional[str] = None
    module_settings: Optional[Dict[str, Any]] = None

    companies: Optional[List[Dict[str, Any]]] = None
    segments: Optional[List[Dict[str, Any]]] = None
    company_segments: Optional[List[Dict[str, Any]]] = None
    
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PartnerPricingProfileCreate(BaseModel):
    partner_id: int
    company_id: int
    item_id: int
    
    discount_pct: Optional[float] = Field(None, ge=0, le=100)
    special_rate: Optional[float] = Field(None, ge=0)
    min_order_qty: Optional[float] = Field(None, ge=0)
    
    effective_from: date
    effective_to: Optional[date] = None
    
    @field_validator('effective_to')
    def validate_dates(cls, v, info):
        if v and 'effective_from' in info.data and info.data['effective_from'] is not None:
            if v < info.data['effective_from']:
                raise ValueError('effective_to must be after effective_from')
        return v


class PartnerPricingProfileResponse(BaseModel):
    id: int
    partner_id: int
    company_id: int
    item_id: int
    
    discount_pct: Optional[float]
    special_rate: Optional[float]
    min_order_qty: Optional[float]
    
    effective_from: date
    effective_to: Optional[date]
    is_active: bool
    
    item_name: Optional[str] = None
    company_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrderLineItemCreate(BaseModel):
    item_id: int
    bom_id: Optional[int] = None
    quantity: float = Field(..., gt=0)
    unit_of_measure: UnitOfMeasure = UnitOfMeasure.PCS
    unit_rate: Optional[float] = Field(None, ge=0, description="Override rate, if not provided uses pricing profile or master rate")
    discount_pct: Optional[float] = Field(0, ge=0, le=100)
    notes: Optional[str] = None


class OrderLineItemResponse(BaseModel):
    id: int
    order_id: int
    item_id: int
    bom_id: Optional[int]
    
    quantity: float
    unit_of_measure: str
    unit_rate: float
    discount_pct: float
    discount_amount: float
    tax_rate: float
    tax_amount: float
    line_total: float
    
    manufacturing_order_id: Optional[int]
    stock_available: bool
    requires_manufacturing: bool
    requires_procurement: bool
    
    item_name: Optional[str] = None
    item_code: Optional[str] = None
    
    class Config:
        from_attributes = True


class PartnerOrderCreate(BaseModel):
    partner_id: int
    company_id: int
    segment_id: Optional[int] = None
    
    order_date: Optional[date] = None
    commitment_date: Optional[date] = None
    
    line_items: List[OrderLineItemCreate] = Field(..., min_length=1)
    
    remarks: Optional[str] = None
    placed_by_partner: bool = False
    
    @field_validator('commitment_date')
    def validate_commitment_date(cls, v, info):
        if v and 'order_date' in info.data and info.data['order_date'] is not None:
            if v < info.data['order_date']:
                raise ValueError('commitment_date must be on or after order_date')
        return v


class PartnerOrderUpdate(BaseModel):
    segment_id: Optional[int] = None
    commitment_date: Optional[date] = None
    remarks: Optional[str] = None
    internal_notes: Optional[str] = None


class PartnerOrderApproval(BaseModel):
    approved: bool
    remarks: Optional[str] = None


class PartnerOrderRouting(BaseModel):
    route_to: RoutedTo
    manufacturing_order_id: Optional[int] = None
    remarks: Optional[str] = None


class PartnerOrderResponse(BaseModel):
    id: int
    order_number: str
    pi_number: Optional[str]
    
    partner_id: int
    partner_name: Optional[str] = None
    partner_code: Optional[str] = None
    
    company_id: int
    company_name: Optional[str] = None
    segment_id: Optional[int]
    segment_name: Optional[str] = None
    
    order_date: date
    commitment_date: Optional[date]
    
    status: str
    subtotal: float
    discount_amount: float
    tax_amount: float
    grand_total: float
    
    placed_by_partner: bool
    routed_to: Optional[str]
    manufacturing_order_id: Optional[int]
    
    pi_generated_at: Optional[datetime]
    approved_at: Optional[datetime]
    payment_confirmed_at: Optional[datetime]
    
    line_items: Optional[List[OrderLineItemResponse]] = None
    
    remarks: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class PartnerOrderListResponse(BaseModel):
    id: int
    order_number: str
    pi_number: Optional[str]
    partner_name: str
    company_name: str
    order_date: date
    status: str
    grand_total: float
    item_count: int
    
    class Config:
        from_attributes = True


class PaymentRecordCreate(BaseModel):
    amount: float = Field(..., gt=0)
    payment_mode: PaymentMode
    payment_date: date
    
    reference_number: Optional[str] = Field(None, max_length=100)
    bank_name: Optional[str] = Field(None, max_length=100)
    
    remarks: Optional[str] = None


class PaymentRecordResponse(BaseModel):
    id: int
    order_id: int
    amount: float
    payment_mode: str
    payment_date: date
    reference_number: Optional[str]
    verified: bool
    verified_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class DispatchCreate(BaseModel):
    dispatch_date: date
    expected_delivery_date: Optional[date] = None
    
    courier_name: Optional[str] = Field(None, max_length=100)
    awb_number: Optional[str] = Field(None, max_length=100)
    tracking_url: Optional[str] = Field(None, max_length=500)
    
    dispatch_from_segment_id: Optional[int] = None
    
    package_count: Optional[int] = Field(1, ge=1)
    package_weight: Optional[float] = Field(None, ge=0)
    
    remarks: Optional[str] = None


class DispatchUpdate(BaseModel):
    status: Optional[DispatchStatus] = None
    actual_delivery_date: Optional[date] = None
    pod_received: Optional[bool] = None
    pod_remarks: Optional[str] = None
    tracking_url: Optional[str] = None


class DispatchResponse(BaseModel):
    id: int
    order_id: int
    order_number: Optional[str] = None
    
    status: str
    dispatch_date: date
    expected_delivery_date: Optional[date]
    actual_delivery_date: Optional[date]
    
    courier_name: Optional[str]
    awb_number: Optional[str]
    tracking_url: Optional[str]
    
    package_count: int
    package_weight: Optional[float]
    
    pod_received: bool
    pod_remarks: Optional[str]
    
    class Config:
        from_attributes = True


class InvoiceGenerateRequest(BaseModel):
    due_date: Optional[date] = None
    remarks: Optional[str] = None
    terms_conditions: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    order_id: int
    order_number: Optional[str] = None
    partner_id: int
    partner_name: Optional[str] = None
    company_id: int
    company_name: Optional[str] = None
    
    invoice_date: date
    due_date: Optional[date]
    
    subtotal: float
    discount_amount: float
    taxable_amount: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    total_tax: float
    grand_total: float
    amount_in_words: Optional[str]
    
    payment_status: str
    amount_received: float
    balance_due: float
    
    pdf_path: Optional[str]
    irn_number: Optional[str]
    e_way_bill_number: Optional[str]
    
    class Config:
        from_attributes = True


class OrderStatusLogResponse(BaseModel):
    id: int
    order_id: int
    from_status: Optional[str]
    to_status: str
    changed_at: datetime
    changed_by_name: Optional[str] = None
    remarks: Optional[str]
    
    class Config:
        from_attributes = True


class StockCheckRequest(BaseModel):
    item_id: int
    quantity: float
    company_id: int
    segment_id: Optional[int] = None


class StockCheckResponse(BaseModel):
    item_id: int
    item_name: str
    requested_qty: float
    available_qty: float
    is_available: bool
    shortage_qty: float
    can_manufacture: bool
    bom_id: Optional[int] = None


class OrderRoutingDecision(BaseModel):
    order_id: int
    can_fulfill_from_stock: bool
    requires_manufacturing: bool
    requires_procurement: bool
    
    stock_items: List[StockCheckResponse]
    manufacturing_items: List[Dict[str, Any]]
    procurement_items: List[Dict[str, Any]]
    
    recommended_route: RoutedTo


class PartnerDashboardStats(BaseModel):
    total_orders: int
    pending_orders: int
    approved_orders: int
    dispatched_orders: int
    
    total_order_value: float
    pending_payment_value: float
    credit_limit: float
    credit_used: float
    credit_available: float


class BulkOrderStatusUpdate(BaseModel):
    order_ids: List[int]
    new_status: OrderStatus
    remarks: Optional[str] = None
