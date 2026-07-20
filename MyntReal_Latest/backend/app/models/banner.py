"""
Banner and Communication System Models
Includes: Banner, CustomBanner, BannerSkippedUser, PopupMessage, UserCouponAcceptance, EmailTemplate, BannerMetrics, BannerEventLog
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey, Date, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from datetime import datetime


class Banner(BaseModel):
    """
    Image banner model with approval workflow
    Admin creates → Super Admin/RVZ ID approves
    """
    __tablename__ = 'banner'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    image_content = Column(Text, nullable=True)  # Base64 image data, file path, or URL (can be very long)
    text_content = Column(Text, nullable=True)  # Text content for text-only banners
    banner_type = Column(String(50), nullable=False)  # 'Promotional Offer', 'New EV Launch', 'Special Incentive Announcement'
    linked_campaign_id = Column(Integer, nullable=True)  # Optional link to Bonanza campaign
    status = Column(String(20), default='Pending', nullable=False)  # 'Pending', 'Active', 'Rejected', 'Inactive'
    display_order = Column(Integer, default=0, nullable=False)
    
    # Tracking
    created_by = Column(String(12), nullable=True)  # Staff user_id (nullable for staff creators)
    created_by_staff_id = Column(Integer, nullable=True)  # Staff employee ID (DC Protocol Feb 2026)
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    approved_by = Column(String(12), nullable=True)  # Super Admin/RVZ ID who approved
    approved_date = Column(DateTime, nullable=True)
    
    # Display settings
    display_location = Column(String(50), default='dashboard', nullable=True)  # 'dashboard', 'all_pages', etc.
    
    # Analytics tracking (cached totals)
    total_views = Column(Integer, default=0, nullable=False)
    total_clicks = Column(Integer, default=0, nullable=False)
    last_viewed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Banner {self.title} - {self.status}>'


class CustomBanner(BaseModel):
    """
    Custom text banner created by admin
    No approval needed - can activate immediately
    """
    __tablename__ = 'custom_banner'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)  # Message content (was 'message' in template)
    banner_type = Column(String(50), default='General', nullable=False)  # 'General', 'Announcement', 'Promotion', 'Warning', 'Info'
    priority = Column(Integer, default=2, nullable=False)  # 1=High, 2=Medium, 3=Low
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Display styling
    background_color = Column(String(7), default='#007bff', nullable=False)
    text_color = Column(String(7), default='#ffffff', nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    
    # Display dates
    show_start_date = Column(DateTime, nullable=True)
    show_end_date = Column(DateTime, nullable=True)
    start_date = Column(DateTime, nullable=True)  # Alias for compatibility
    end_date = Column(DateTime, nullable=True)  # Alias for compatibility
    
    # Tracking
    created_by = Column(String(12), nullable=True)  # Staff user_id (nullable for staff creators)
    created_by_staff_id = Column(Integer, nullable=True)  # Staff employee ID (DC Protocol Feb 2026)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)  # Alias for compatibility
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_date = Column(DateTime, nullable=True)  # Alias for compatibility
    updated_by = Column(String(12), nullable=True)
    
    # Display settings
    target_user_types = Column(String(100), nullable=True)  # Comma-separated user types
    display_count = Column(Integer, default=0, nullable=True)
    max_displays = Column(Integer, nullable=True)
    
    # Analytics tracking (cached totals)
    total_views = Column(Integer, default=0, nullable=False)
    total_clicks = Column(Integer, default=0, nullable=False)
    last_viewed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f'<CustomBanner {self.title} - {"Active" if self.is_active else "Inactive"}>'


class BannerSkippedUser(BaseModel):
    """
    Track users who should be skipped from top earners banner display
    Admin can skip/reactivate users
    """
    __tablename__ = 'banner_skipped_user'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(12), nullable=False, unique=True)
    skipped_by = Column(String(12), nullable=False)  # Admin who skipped
    skipped_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)  # Can be reactivated
    reason = Column(Text, nullable=True)
    
    def __repr__(self):
        return f'<BannerSkippedUser {self.user_id}>'


class PopupMessage(BaseModel):
    """
    Popup message with approval workflow
    Admin creates → Super Admin/RVZ ID approves
    """
    __tablename__ = 'popup_message'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    popup_type = Column(String(50), default='General', nullable=False)  # 'General', 'Announcement', 'Warning', 'Info'
    image_url = Column(Text, nullable=True)  # Optional image URL, path, or Base64 data
    
    # Display settings
    target_page = Column(String(50), nullable=False)  # 'After Login', 'Dashboard', 'PIN Activation', 'PIN Purchase', 'Coupon Page'
    popup_size = Column(String(20), default='Medium', nullable=False)  # 'Small', 'Medium', 'Large'
    priority = Column(Integer, default=1, nullable=False)
    background_color = Column(String(7), default='#007bff', nullable=False)
    text_color = Column(String(7), default='#ffffff', nullable=False)
    auto_close_seconds = Column(Integer, nullable=True)  # Auto-close after X seconds, null = manual close
    
    # Display dates
    show_start_date = Column(DateTime, nullable=True)
    show_end_date = Column(DateTime, nullable=True)
    
    # Status and approval
    status = Column(String(20), default='Draft', nullable=False)  # 'Draft', 'Pending', 'Approved', 'Rejected', 'Active', 'Inactive'
    is_active = Column(Boolean, default=False, nullable=False)
    
    # Tracking
    created_by = Column(String(12), nullable=True)  # Staff user_id (nullable for staff creators)
    created_by_staff_id = Column(Integer, nullable=True)  # Staff employee ID (DC Protocol Feb 2026)
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    approved_by = Column(String(12), nullable=True)
    approved_date = Column(DateTime, nullable=True)
    submission_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Analytics tracking (cached totals)
    total_views = Column(Integer, default=0, nullable=False)
    total_clicks = Column(Integer, default=0, nullable=False)
    last_viewed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f'<PopupMessage {self.title} - {self.status}>'


class UserCouponAcceptance(BaseModel):
    """
    Tracks mandatory coupon benefits popup acceptance during first 3 logins
    Shows Terms & Conditions popup 3 times for new users until accepted
    """
    __tablename__ = 'user_coupon_acceptance'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(12), nullable=False)
    login_attempt_number = Column(Integer, nullable=False)  # 1, 2, or 3
    ip_address = Column(String(45), nullable=False)  # IPv6 compatible
    acceptance_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_agent = Column(Text, nullable=True)  # Browser/device information
    accepted_terms_version = Column(String(10), nullable=False, default='1.0')
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<UserCouponAcceptance user={self.user_id} attempt={self.login_attempt_number}>'


class EmailTemplate(BaseModel):
    """
    Email templates for system notifications
    Package updates, KYC approvals, income notifications, etc.
    """
    __tablename__ = 'email_template'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    template_type = Column(String(50), nullable=False)  # 'package_update', 'kyc_approval', 'income_notification', etc.
    subject = Column(String(200), nullable=False)
    html_content = Column(Text, nullable=False)
    text_content = Column(Text, nullable=True)  # Plain text version
    css_content = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Tracking
    created_by = Column(String(12), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<EmailTemplate {self.name} - {self.template_type}>'


class BirthdayMessage(BaseModel):
    """
    Daily rotating birthday messages for birthday banner
    Admin can add/edit/delete custom messages
    System rotates through active messages daily
    """
    __tablename__ = 'birthday_messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    
    # Tracking
    created_by = Column(String(12), ForeignKey('user.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_by = Column(String(12), ForeignKey('user.id'), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<BirthdayMessage {self.id}: {self.message[:30]}...>'


class BirthdaySkippedUser(BaseModel):
    """
    Users excluded from birthday banner display
    Similar to BannerSkippedUser for top performers
    Admin can skip users from showing on birthday banner
    """
    __tablename__ = 'birthday_skipped_users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    skipped_by = Column(String(12), ForeignKey('user.id'), nullable=False)
    reason = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    skipped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reactivated_at = Column(DateTime, nullable=True)
    reactivated_by = Column(String(12), ForeignKey('user.id'), nullable=True)
    
    def __repr__(self):
        return f'<BirthdaySkippedUser user_id={self.user_id} active={self.is_active}>'


class BannerMetrics(BaseModel):
    """
    Daily analytics tracking for all banner types
    Append-only table for immutable metrics history
    DC Protocol: Source of truth for banner performance data
    """
    __tablename__ = 'banner_metrics'
    __table_args__ = (
        UniqueConstraint('banner_id', 'banner_type', 'metric_date', name='unique_banner_metric_date'),
        Index('idx_banner_metrics_lookup', 'banner_id', 'banner_type', 'metric_date'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    banner_id = Column(Integer, nullable=False)
    banner_type = Column(String(50), nullable=False)  # 'image', 'custom', 'popup', 'birthday'
    metric_date = Column(Date, nullable=False)
    views = Column(Integer, default=0, nullable=False)
    clicks = Column(Integer, default=0, nullable=False)
    impressions = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<BannerMetrics {self.banner_type}#{self.banner_id} {self.metric_date}: {self.views}v/{self.clicks}c>'


class BannerEventLog(BaseModel):
    """
    Immutable audit trail for all banner lifecycle events
    R Logs Protocol: Complete history of create/approve/reject/activate actions
    DC Protocol: Never delete or modify - append-only logging
    """
    __tablename__ = 'banner_event_log'
    __table_args__ = (
        Index('idx_banner_event_log_lookup', 'banner_id', 'banner_type', 'created_at'),
        Index('idx_banner_event_log_actor', 'actor_id', 'created_at'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    banner_id = Column(Integer, nullable=False)
    banner_type = Column(String(50), nullable=False)  # 'image', 'custom', 'popup', 'birthday'
    action = Column(String(50), nullable=False)  # 'created', 'approved', 'rejected', 'activated', 'deactivated', 'updated'
    actor_id = Column(String(12), nullable=False)  # User ID who performed action
    actor_name = Column(String(200), nullable=True)  # User name for quick reference
    previous_status = Column(String(20), nullable=True)  # Status before action
    new_status = Column(String(20), nullable=True)  # Status after action
    notes = Column(Text, nullable=True)  # Rejection reason, approval comments, etc.
    metadata_json = Column(Text, nullable=True)  # Additional context as JSON string
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<BannerEventLog {self.banner_type}#{self.banner_id} {self.action} by {self.actor_id}>'


class BannerViewLog(BaseModel):
    """
    Track unique users who viewed/clicked banners
    DC Protocol: Append-only log for unique user tracking
    Used to calculate: unique views, unique clicks per banner
    """
    __tablename__ = 'banner_view_log'
    __table_args__ = (
        UniqueConstraint('banner_id', 'banner_type', 'user_id', 'action', name='unique_banner_view'),
        Index('idx_banner_view_lookup', 'banner_id', 'banner_type', 'action'),
        Index('idx_banner_view_user', 'user_id', 'banner_id', 'banner_type'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    banner_id = Column(Integer, nullable=False)
    banner_type = Column(String(50), nullable=False)  # 'image', 'custom', 'popup', 'birthday', 'top_performers'
    user_id = Column(String(12), nullable=False)  # User who viewed/clicked
    action = Column(String(20), nullable=False)  # 'view' or 'click'
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<BannerViewLog {self.banner_type}#{self.banner_id} {self.action} by {self.user_id}>'
