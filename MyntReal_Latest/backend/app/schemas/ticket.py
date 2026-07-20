"""
Pydantic schemas for Support Ticketing System
Matching pre-migration Flask system structure
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ===== TICKET SCHEMAS =====

class TicketBase(BaseModel):
    issue_category: str = Field(..., description="Account Issues, Payment Problems, Technical Support, PIN Management, etc.")
    issue_description: str = Field(..., min_length=10)
    priority: str = Field(default="Medium", description="Low, Medium, High, Critical")


class TicketCreate(TicketBase):
    user_id: str


class TicketUpdate(BaseModel):
    issue_category: Optional[str] = None
    issue_description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    admin_response: Optional[str] = None
    resolution_summary: Optional[str] = None


class TicketAssign(BaseModel):
    assigned_to: str
    assignment_reason: Optional[str] = None


class TicketResolve(BaseModel):
    resolution_summary: str
    admin_response: Optional[str] = None


class TicketClose(BaseModel):
    customer_satisfaction: Optional[int] = Field(None, ge=1, le=5)
    force_close: bool = Field(default=False, description="Admin override to close ticket even with pending spare requests")


# ===== SERVICE TICKET ACTION SCHEMAS (DC Protocol Jan 2026) =====

class ServiceTicketAcknowledge(BaseModel):
    notes: Optional[str] = None


class ServiceTicketDiagnose(BaseModel):
    diagnosis_notes: str
    spares_required: bool = False


class ServiceTicketComplete(BaseModel):
    resolution_summary: str


class ServiceTicketClose(BaseModel):
    customer_satisfaction: Optional[int] = Field(default=None, ge=1, le=5, description="Customer satisfaction rating 1-5")
    force_close: bool = Field(default=False, description="Admin override to close ticket even with pending spare requests")


# ===== CUSTOM SPARES SCHEMAS (DC Protocol Jan 2026) =====

class CustomSpareRequest(BaseModel):
    """Schema for requesting custom/free-text spare items"""
    spare_item_name: str = Field(..., min_length=2, max_length=200, description="Custom spare item name")
    spare_description: Optional[str] = Field(None, max_length=500)
    quantity_required: int = Field(default=1, ge=1)
    estimated_cost: Optional[float] = Field(None, ge=0)
    request_notes: Optional[str] = None


class SpareRequestUpdate(BaseModel):
    """Schema for updating spare request details"""
    spare_item_name: Optional[str] = Field(None, max_length=200)
    spare_description: Optional[str] = Field(None, max_length=500)
    quantity_required: Optional[int] = Field(None, ge=1)
    estimated_cost: Optional[float] = Field(None, ge=0)
    request_notes: Optional[str] = None


class SpareVerifyRequest(BaseModel):
    """Schema for verifying/mapping custom spare to actual stock item"""
    stock_item_id: int = Field(..., description="Actual stock item ID to map to")
    spare_item_name: Optional[str] = Field(None, description="Updated item name if different")
    spare_item_code: Optional[str] = Field(None, description="Item code from stock")
    unit_price: Optional[float] = Field(None, ge=0, description="Override unit price")
    gst_rate: Optional[float] = Field(None, ge=0, le=100, description="GST rate percentage")
    hsn_code: Optional[str] = Field(None, max_length=20)
    verification_notes: Optional[str] = None


class SpareRequestResponse(BaseModel):
    """Response schema for spare request"""
    id: int
    ticket_id: int
    spare_item_name: str
    spare_item_code: Optional[str] = None
    spare_description: Optional[str] = None
    quantity_required: int
    estimated_cost: Optional[float] = None
    unit_price: Optional[float] = None
    gst_rate: Optional[float] = None
    total_with_gst: Optional[float] = None
    stock_item_id: Optional[int] = None
    procurement_status: str
    is_custom: bool
    original_item_name: Optional[str] = None
    verified_at: Optional[datetime] = None
    requested_at: datetime
    
    class Config:
        from_attributes = True


class TicketResponse(TicketBase):
    id: int
    ticket_id: str
    user_id: str
    assigned_to: Optional[str] = None
    status: str
    sla_status: str
    sla_deadline: datetime
    created_date: datetime
    assigned_date: Optional[datetime] = None
    in_progress_date: Optional[datetime] = None
    resolved_date: Optional[datetime] = None
    closed_date: Optional[datetime] = None
    escalated_date: Optional[datetime] = None
    escalated_to: Optional[str] = None
    admin_response: Optional[str] = None
    last_response_date: Optional[datetime] = None
    resolution_summary: Optional[str] = None
    resolution_time_hours: Optional[float] = None
    customer_satisfaction: Optional[int] = None
    
    class Config:
        from_attributes = True


# ===== COMMENT SCHEMAS =====

class CommentCreate(BaseModel):
    ticket_id: int
    comment_text: str = Field(..., min_length=1)
    comment_type: str = Field(default="user_response", description="user_response, admin_response, internal_note")
    is_internal: bool = Field(default=False)


class CommentResponse(BaseModel):
    id: int
    ticket_id: int
    comment_text: str
    comment_type: str
    user_id: str
    created_at: datetime
    is_visible_to_user: bool
    is_internal: bool
    
    class Config:
        from_attributes = True


# ===== ATTACHMENT SCHEMAS =====

class AttachmentCreate(BaseModel):
    ticket_id: int
    file_path: str
    original_filename: str
    file_size: int
    mime_type: str
    uploaded_by: str


class AttachmentResponse(BaseModel):
    id: int
    ticket_id: int
    original_filename: str
    file_size: int
    mime_type: str
    uploaded_by: str
    uploaded_at: datetime
    is_scanned: bool
    scan_status: Optional[str] = None
    
    class Config:
        from_attributes = True


# ===== ASSIGNMENT SCHEMAS =====

class AssignmentResponse(BaseModel):
    id: int
    ticket_id: int
    assigned_from: Optional[str] = None
    assigned_to: str
    assigned_date: datetime
    assignment_reason: Optional[str] = None
    is_active: bool
    completed_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ===== LOG SCHEMAS =====

class LogResponse(BaseModel):
    id: int
    ticket_id: int
    action_type: str
    action_description: str
    performed_by: str
    performed_at: datetime
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    comments: Optional[str] = None
    
    class Config:
        from_attributes = True


# ===== DETAILED TICKET VIEW =====

class TicketDetailResponse(TicketResponse):
    comments: List[CommentResponse] = []
    attachments: List[AttachmentResponse] = []
    assignments: List[AssignmentResponse] = []
    activity_logs: List[LogResponse] = []
    
    class Config:
        from_attributes = True


# ===== TIMELINE & ANALYTICS =====

class TicketTimelineStats(BaseModel):
    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    resolved_tickets: int
    closed_tickets: int
    sla_breached_count: int
    average_resolution_time: Optional[float] = None
    customer_satisfaction_avg: Optional[float] = None


class TicketTimelineEntry(BaseModel):
    ticket_id: str
    user_id: str
    user_name: str
    issue_category: str
    created_date: datetime
    resolved_date: Optional[datetime] = None
    resolution_time_hours: Optional[float] = None
    status: str
    sla_status: str
    assigned_to: Optional[str] = None


class TicketTimelineResponse(BaseModel):
    stats: TicketTimelineStats
    tickets: List[TicketTimelineEntry]
    date_range: str


# ===== PUBLIC SERVICE TICKET SCHEMA (DC Protocol Jan 2026) =====

class PublicServiceTicketCreate(BaseModel):
    """Schema for public service ticket creation - no authentication required"""
    customer_name: str = Field(..., min_length=2, max_length=200, description="Customer full name")
    customer_phone: str = Field(..., min_length=10, max_length=20, description="Customer phone number")
    customer_email: Optional[str] = Field(None, max_length=200, description="Customer email address")
    customer_address: Optional[str] = Field(None, max_length=500, description="Customer address")
    issue_category: str = Field(..., min_length=2, max_length=100, description="Issue category")
    issue_description: str = Field(..., min_length=10, max_length=2000, description="Detailed issue description")
    product_name: Optional[str] = Field(None, max_length=200, description="Product name")
    product_serial: Optional[str] = Field(None, max_length=100, description="Product serial number")
    product_model: Optional[str] = Field(None, max_length=100, description="Product model")
    
    class Config:
        json_schema_extra = {
            "example": {
                "customer_name": "John Doe",
                "customer_phone": "9876543210",
                "customer_email": "john@example.com",
                "issue_category": "EV Battery Issue",
                "issue_description": "Battery not charging properly after firmware update"
            }
        }


class PublicServiceTicketResponse(BaseModel):
    """Response schema for public ticket creation"""
    success: bool
    ticket_id: str
    message: str
