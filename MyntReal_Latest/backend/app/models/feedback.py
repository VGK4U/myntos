from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum, JSON, func
from sqlalchemy.orm import relationship
from app.models.base import Base
import enum

class FeedbackCategory(Base):
    """
    DC Protocol: Single source of truth for feedback categories
    Managed by RVZ only - dynamic category management
    """
    __tablename__ = "feedback_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String(12), ForeignKey("user.id"), nullable=False)  # RVZ ID only
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    submissions = relationship("FeedbackSubmission", back_populates="category")


class SubmissionType(str, enum.Enum):
    """Type of feedback submission"""
    VIDEO = "video"
    PHOTO = "photo"
    TEXT = "text"  # RVZ-only: text announcements without media
    MIXED = "mixed"  # DC Protocol (Jan 24, 2026): Photos + Videos combined


class SubmissionStatus(str, enum.Enum):
    """
    DC Protocol: Status derived from approval actions
    pending → under_review → partially_approved → approved/rejected
    """
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    PARTIALLY_APPROVED = "partially_approved"  # Some media approved, some rejected
    APPROVED = "approved"  # All media approved - becomes announcement
    REJECTED = "rejected"


class MediaStatus(str, enum.Enum):
    """Individual media file approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class FeedbackSubmission(Base):
    """
    DC Protocol: Single source of truth for both submissions AND announcements
    Approved submissions automatically become announcements - no separate table needed
    """
    __tablename__ = "feedback_submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(12), ForeignKey("user.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("feedback_categories.id"), nullable=False, index=True)
    submission_type = Column(Enum(SubmissionType), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.PENDING, nullable=False, index=True)
    
    # Individual media approval tracking
    approved_media_count = Column(Integer, default=0, nullable=False)
    rejected_media_count = Column(Integer, default=0, nullable=False)
    last_reviewed_at = Column(DateTime(timezone=True))
    last_reviewed_by = Column(String(12), ForeignKey("user.id"))
    
    # Visibility control (Admin can hide/unhide announcements)
    is_visible = Column(Boolean, default=True, nullable=False, index=True)
    hidden_by = Column(String(12), ForeignKey("user.id"))  # Admin who hid it
    hidden_at = Column(DateTime(timezone=True))  # When it was hidden
    
    # Engagement metrics
    shares_count = Column(Integer, default=0, nullable=False)  # Track how many times shared
    views_count = Column(Integer, default=0, nullable=False)  # Track how many times viewed
    
    # Display order for announcements (lower number = higher priority, NULL = default order by date)
    display_order = Column(Integer, nullable=True, index=True)
    
    # Timestamps
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    approved_at = Column(DateTime(timezone=True), index=True)  # For announcements filtering
    approved_by = Column(String(12), ForeignKey("user.id"))
    
    # Audience targeting: which platform sees this announcement
    # 'mnr'  → MNR members + MNR staff only
    # 'vgk'  → VGK members + VGK staff only
    # 'both' → visible to everyone (default)
    visible_to = Column(String(10), default='both', nullable=False, index=True)

    # Soft Delete (Dec 2025) - DC Protocol compliant with restore capability
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(String(12), ForeignKey("user.id"), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    category = relationship("FeedbackCategory", back_populates="submissions")
    media_files = relationship("FeedbackMedia", back_populates="submission", cascade="all, delete-orphan")
    approvals = relationship("FeedbackApproval", back_populates="submission", cascade="all, delete-orphan")
    approver = relationship("User", foreign_keys=[approved_by])
    hider = relationship("User", foreign_keys=[hidden_by])


class FeedbackMedia(Base):
    """
    DC Protocol: Single source for media file metadata
    File path stored once, referenced by submission
    Individual media approval status for granular control
    """
    __tablename__ = "feedback_media"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("feedback_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)  # Relative path: /uploads/feedback/{submission_id}/{filename}
    file_type = Column(String(50), nullable=False)  # video/mp4, image/jpeg, etc.
    file_size = Column(Integer)  # Bytes
    duration = Column(Integer)  # For videos: duration in seconds
    original_filename = Column(String(255))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Universal Upload System: Compression fields (DC Protocol)
    compressed_path = Column(String(500))
    compressed_size_bytes = Column(Integer)
    processing_status = Column(String(20), default='pending')
    processed_at = Column(DateTime(timezone=True))
    compressed_checksum = Column(String(64))
    has_compressed = Column(Boolean, default=False)
    uploaded_by_emp_code = Column(String(20))
    
    # DC Protocol: Dual Storage Architecture (object storage vs local)
    original_checksum = Column(String(64))  # SHA-256 before compression/watermark
    original_storage_type = Column(String(20), default='local')  # 'local' or 'object_storage'
    original_storage_key = Column(String(500))  # Actual object storage key (if object_storage)
    
    # DC Protocol: Semantic file naming (Nov 29, 2025)
    download_filename = Column(String(255), nullable=True)  # Semantic download filename
    uses_new_naming = Column(Boolean, default=False, nullable=False)  # Flag for new naming convention
    
    # Individual media approval status
    media_status = Column(Enum(MediaStatus), default=MediaStatus.PENDING, nullable=False, index=True)
    decided_by = Column(String(12), ForeignKey("user.id"))
    decided_at = Column(DateTime(timezone=True))
    decision_comment = Column(Text)
    announced_at = Column(DateTime(timezone=True))  # When approved media was published
    
    # DC Protocol (Mar 2026): Video thumbnail for OG preview + share card
    # Auto-extracted from first frame OR manually chosen by uploader during submission
    thumbnail_url = Column(String(500), nullable=True)

    # Individual media visibility control (separate from approval status)
    is_visible = Column(Boolean, default=True, nullable=False, index=True)
    hidden_by = Column(String(12), ForeignKey("user.id"))
    hidden_at = Column(DateTime(timezone=True))
    
    # Relationships
    submission = relationship("FeedbackSubmission", back_populates="media_files")
    decider = relationship("User", foreign_keys=[decided_by])
    hider = relationship("User", foreign_keys=[hidden_by])


class ApprovalAction(str, enum.Enum):
    """Actions taken during approval workflow"""
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    EDITED = "edited"
    APPROVED = "approved"
    REJECTED = "rejected"


class FeedbackApproval(Base):
    """
    DC Protocol: Audit trail for all approval actions
    Complete history of who did what and when
    Tracks both submission-level and individual media-level decisions
    """
    __tablename__ = "feedback_approvals"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("feedback_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    media_id = Column(Integer, ForeignKey("feedback_media.id", ondelete="CASCADE"))  # NULL = submission-level action
    reviewer_id = Column(String(12), ForeignKey("user.id"), nullable=False)
    reviewer_role = Column(String(20), nullable=False)  # admin, super_admin, rvz
    action = Column(Enum(ApprovalAction), nullable=False)
    comments = Column(Text)
    
    # Edit details (JSON for flexibility)
    edit_details = Column(JSON)  # {crop: {x, y, width, height}, brightness: +20, music: "path/to/music.mp3"}
    
    reviewed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    submission = relationship("FeedbackSubmission", back_populates="approvals")
    reviewer = relationship("User", foreign_keys=[reviewer_id])


class AnnouncementRating(Base):
    """
    User ratings for approved announcements (1-5 stars)
    Users can rate each announcement once
    """
    __tablename__ = "announcement_ratings"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("feedback_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(12), ForeignKey("user.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    submission = relationship("FeedbackSubmission")
    user = relationship("User")
