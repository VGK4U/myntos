"""
Pydantic schemas for Banner and Communication System
Includes: Banner, Custom Banner, Popup, TOP Performers, Metrics, Event Logs
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Union
from datetime import datetime, date


# ===== BANNER SCHEMAS =====

class BannerBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    image_content: Optional[str] = None
    text_content: Optional[str] = None
    banner_type: str = Field(..., description="Promotional Offer, New EV Launch, Special Incentive Announcement")
    linked_campaign_id: Optional[int] = None
    display_order: int = 0
    display_location: Optional[str] = "dashboard"


class BannerCreate(BannerBase):
    created_by: str


class BannerUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    image_content: Optional[str] = None
    text_content: Optional[str] = None
    banner_type: Optional[str] = None
    linked_campaign_id: Optional[int] = None
    display_order: Optional[int] = None
    display_location: Optional[str] = None


class BannerApproval(BaseModel):
    approved_by: str
    status: str = Field(..., description="Approved or Rejected")
    rejection_reason: Optional[str] = None


class BannerResponse(BannerBase):
    id: int
    status: str
    created_by: Optional[str] = None
    created_by_staff_id: Optional[int] = None
    created_date: datetime
    approved_by: Optional[str] = None
    approved_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ===== CUSTOM BANNER SCHEMAS =====

class CustomBannerBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=1)
    banner_type: str = Field(default="General", description="General, Announcement, Promotion, Warning, Info")
    priority: int = Field(default=2, ge=1, le=3, description="1=High, 2=Medium, 3=Low")
    background_color: str = Field(default="#007bff", pattern="^#[0-9A-Fa-f]{6}$")
    text_color: str = Field(default="#ffffff", pattern="^#[0-9A-Fa-f]{6}$")
    display_order: int = 0
    show_start_date: Optional[datetime] = None
    show_end_date: Optional[datetime] = None
    target_user_types: Optional[str] = None
    max_displays: Optional[int] = None


class CustomBannerCreate(CustomBannerBase):
    created_by: str


class CustomBannerUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    content: Optional[str] = None
    banner_type: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=3)
    background_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    text_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    display_order: Optional[int] = None
    show_start_date: Optional[datetime] = None
    show_end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    updated_by: Optional[str] = None


class CustomBannerResponse(CustomBannerBase):
    id: int
    is_active: bool
    created_by: Optional[str] = None
    created_by_staff_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[str] = None
    display_count: Optional[int] = 0
    
    @field_validator('target_user_types', mode='before')
    @classmethod
    def convert_array_to_string(cls, v):
        """Convert PostgreSQL array to comma-separated string"""
        if v is None:
            return None
        if isinstance(v, list):
            return ','.join(v) if v else None
        return v
    
    class Config:
        from_attributes = True


# ===== TOP PERFORMERS SCHEMAS =====

class TopPerformerData(BaseModel):
    user_id: str
    name: str
    total_earnings: float
    rank: int
    photo_url: Optional[str] = None
    badge: Optional[str] = None
    latest_earning_date: Optional[str] = None


class TopPerformersResponse(BaseModel):
    top_performers: List[TopPerformerData]
    total_count: int
    excluded_count: int
    latest_earning_date: Optional[str] = None


class BannerSkipUserRequest(BaseModel):
    user_id: str
    skipped_by: str
    reason: Optional[str] = None


class BannerSkippedUserResponse(BaseModel):
    id: int
    user_id: str
    skipped_by: str
    skipped_date: datetime
    is_active: bool
    reason: Optional[str] = None
    
    class Config:
        from_attributes = True


# ===== POPUP MESSAGE SCHEMAS =====

class PopupMessageBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=1)
    popup_type: str = Field(default="General", description="General, Announcement, Warning, Info")
    target_page: str = Field(..., description="After Login, Dashboard, PIN Activation, PIN Purchase, Coupon Page")
    popup_size: str = Field(default="Medium", description="Small, Medium, Large")
    priority: int = Field(default=1, ge=1, le=10)
    background_color: str = Field(default="#007bff", pattern="^#[0-9A-Fa-f]{6}$")
    text_color: str = Field(default="#ffffff", pattern="^#[0-9A-Fa-f]{6}$")
    auto_close_seconds: Optional[int] = Field(None, ge=0)
    show_start_date: Optional[datetime] = None
    show_end_date: Optional[datetime] = None
    submission_notes: Optional[str] = None


class PopupMessageCreate(PopupMessageBase):
    created_by: str
    status: str = Field(default="Draft", description="Draft or Pending")


class PopupMessageUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    content: Optional[str] = None
    popup_type: Optional[str] = None
    target_page: Optional[str] = None
    popup_size: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    background_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    text_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    auto_close_seconds: Optional[int] = Field(None, ge=0)
    show_start_date: Optional[datetime] = None
    show_end_date: Optional[datetime] = None
    submission_notes: Optional[str] = None


class PopupMessageApproval(BaseModel):
    approved_by: str
    status: str = Field(..., description="Approved or Rejected")
    rejection_reason: Optional[str] = None


class PopupMessageResponse(PopupMessageBase):
    id: int
    status: str
    is_active: bool
    created_by: Optional[str] = None
    created_by_staff_id: Optional[int] = None
    created_date: datetime
    approved_by: Optional[str] = None
    approved_date: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    class Config:
        from_attributes = True


# ===== USER COUPON ACCEPTANCE SCHEMAS =====

class CouponAcceptanceCheck(BaseModel):
    user_id: str


class CouponAcceptanceCheckResponse(BaseModel):
    should_show_popup: bool
    attempt_number: Optional[int] = None
    remaining_attempts: int = 0


class CouponAcceptanceRecord(BaseModel):
    user_id: str
    login_attempt_number: int = Field(..., ge=1, le=3)
    ip_address: str
    user_agent: Optional[str] = None
    accepted_terms_version: str = "1.0"


class CouponAcceptanceResponse(BaseModel):
    success: bool
    message: str
    attempt_number: int


# ===== EMAIL TEMPLATE SCHEMAS =====

class EmailTemplateBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    template_type: str = Field(..., description="package_update, kyc_approval, income_notification, etc.")
    subject: str = Field(..., min_length=3, max_length=200)
    html_content: str
    text_content: Optional[str] = None
    css_content: Optional[str] = None
    description: Optional[str] = None


class EmailTemplateCreate(EmailTemplateBase):
    created_by: str


class EmailTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    template_type: Optional[str] = None
    subject: Optional[str] = Field(None, min_length=3, max_length=200)
    html_content: Optional[str] = None
    text_content: Optional[str] = None
    css_content: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class EmailTemplateResponse(EmailTemplateBase):
    id: int
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SendEmailRequest(BaseModel):
    user_id: str
    template_type: str
    subject: Optional[str] = None
    additional_data: Optional[dict] = None


class SendEmailResponse(BaseModel):
    success: bool
    message: str
    message_id: Optional[str] = None


# ===== BANNER TRACKING SCHEMAS =====

class BannerTrackingRequest(BaseModel):
    """Schema for tracking banner views and clicks"""
    banner_id: int
    banner_type: str = Field(..., description="image, custom, popup, birthday")
    event: str = Field(..., description="view or click")


# ===== BANNER METRICS SCHEMAS =====

class BannerMetricsResponse(BaseModel):
    """Daily analytics for a banner"""
    id: int
    banner_id: int
    banner_type: str
    metric_date: date
    views: int
    clicks: int
    impressions: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class BannerMetricsSummary(BaseModel):
    """Aggregated metrics summary"""
    total_views: int
    total_clicks: int
    total_impressions: int
    ctr: float  # Click-through rate
    daily_breakdown: List[BannerMetricsResponse]


# ===== BANNER EVENT LOG SCHEMAS =====

class BannerEventLogResponse(BaseModel):
    """Audit trail entry for banner events"""
    id: int
    banner_id: int
    banner_type: str
    action: str
    actor_id: str
    actor_name: Optional[str] = None
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    notes: Optional[str] = None
    metadata_json: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ===== RVZ BANNER OVERSIGHT SCHEMAS =====

class RVZBannerQueueItem(BaseModel):
    """Single banner in RVZ oversight queue"""
    id: int
    banner_type: str  # image, custom, popup, birthday
    title: str
    status: str
    created_by: Optional[str] = None
    created_by_staff_id: Optional[int] = None
    created_by_name: Optional[str] = None
    created_date: datetime
    approved_by: Optional[str] = None
    approved_date: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    # Analytics (cached totals)
    total_views: int
    total_clicks: int
    last_viewed_at: Optional[datetime] = None
    
    # Calculated fields
    ctr: Optional[float] = None  # Click-through rate
    
    class Config:
        from_attributes = True


class RVZBannerQueueResponse(BaseModel):
    """RVZ oversight dashboard response"""
    banners: List[RVZBannerQueueItem]
    summary: dict  # {pending: 12, active: 45, rejected: 8, total_views_7d: 15234}
    total_count: int


class BannerApprovalRequest(BaseModel):
    """RVZ approval/rejection request"""
    action: str = Field(..., description="approve or reject")
    notes: Optional[str] = None  # Rejection reason or approval comments
    approved_by: str


class BannerDetailResponse(BaseModel):
    """Detailed banner info for RVZ approval drawer"""
    banner: RVZBannerQueueItem
    metrics: BannerMetricsSummary
    events: List[BannerEventLogResponse]
    preview_data: dict  # Banner-specific preview data (image URL, content, etc.)
