"""
User Feedback & Announcements API
DC Protocol: Approved submissions ARE announcements - single source of truth
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime, date
from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_hybrid
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.user import User
from app.models.feedback import (
    FeedbackCategory, FeedbackSubmission, FeedbackMedia, FeedbackApproval,
    SubmissionType, SubmissionStatus, ApprovalAction, MediaStatus
)
from pydantic import BaseModel, Field, field_validator, model_validator
import os
import shutil
from pathlib import Path
from app.utils.watermark import process_media_watermark, process_media_bytes
from app.utils.media import normalize_media_path
from app.services.object_storage import storage_service
from app.services.universal_upload_service import UniversalUploadService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# ===== Upload Limits Configuration =====
MAX_TOTAL_FILES = 10  # Maximum files per announcement (Admin & RVZ)
MAX_VIDEO_FILES = 5   # Maximum videos per announcement (Admin & RVZ)

# ===== Pydantic Schemas =====

class CategoryResponse(BaseModel):
    id: int
    name: str
    category_name: str  # Frontend expects this field
    description: Optional[str]
    is_active: bool
    
    @model_validator(mode='after')
    def set_category_name(self):
        """Ensure category_name is set for frontend compatibility"""
        if not hasattr(self, 'category_name') or not self.category_name:
            self.category_name = self.name
        return self
    
    class Config:
        from_attributes = True


class MediaResponse(BaseModel):
    id: int
    file_path: str
    file_type: str
    file_size: Optional[int]
    duration: Optional[int]
    media_type: str  # video or photo for frontend
    media_status: Optional[str] = "pending"  # pending/approved/rejected
    is_visible: bool = True  # Individual media visibility
    decided_at: Optional[datetime] = None
    decision_comment: Optional[str] = None
    # DC Protocol (Mar 2026): Video thumbnail for OG share preview
    thumbnail_url: Optional[str] = None

    class Config:
        from_attributes = True


class SubmissionResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    submission_type: str
    category: CategoryResponse
    status: str
    is_visible: bool
    submitted_at: datetime
    approved_at: Optional[datetime]
    media: List[MediaResponse]  # Frontend expects 'media'
    user_name: str
    user_id: str
    
    class Config:
        from_attributes = True


class AnnouncementResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    submission_type: str
    category: CategoryResponse
    approved_at: datetime
    updated_at: datetime  # When last updated
    is_visible: bool
    media: List[MediaResponse]  # Frontend expects 'media'
    
    # User details
    user_id: str
    user_name: str
    city: Optional[str] = None  # From KYC
    
    # Engagement metrics
    average_rating: Optional[float] = 0.0
    total_ratings: int = 0
    shares_count: int = 0
    views_count: int = 0
    
    # Display order (admin-controlled)
    display_order: Optional[int] = None

    # Audience targeting
    visible_to: str = 'both'  # 'mnr', 'vgk', or 'both'

    class Config:
        from_attributes = True


# ===== Helper Functions =====

def get_upload_dir() -> Path:
    """Get or create uploads directory"""
    upload_dir = Path("uploads/feedback")
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def build_media_response(media: FeedbackMedia) -> MediaResponse:
    """Build MediaResponse with normalized path, approval status, and visibility.
    DC Protocol: Serve compressed file when background compression completed — smaller
    files load significantly faster on mobile / slow connections.
    """
    has_compressed = getattr(media, 'has_compressed', False)
    compressed_path = getattr(media, 'compressed_path', None)
    processing_status = getattr(media, 'processing_status', None)
    if has_compressed and compressed_path and processing_status == 'completed':
        effective_path = compressed_path
    else:
        effective_path = media.file_path
    return MediaResponse(
        id=media.id,
        file_path=normalize_media_path(effective_path),
        file_type=media.file_type,
        file_size=media.file_size,
        duration=media.duration,
        media_type='video' if 'video' in (media.file_type or '') else 'photo',
        media_status=media.media_status.value if hasattr(media, 'media_status') and media.media_status else 'pending',
        is_visible=media.is_visible if hasattr(media, 'is_visible') else True,
        decided_at=media.decided_at if hasattr(media, 'decided_at') else None,
        decision_comment=media.decision_comment if hasattr(media, 'decision_comment') else None,
        thumbnail_url=normalize_media_path(media.thumbnail_url) if getattr(media, 'thumbnail_url', None) else None,
    )


def build_category_response(category: FeedbackCategory) -> CategoryResponse:
    """Build CategoryResponse with category_name field"""
    return CategoryResponse(
        id=category.id,
        name=category.name,
        category_name=category.name,
        description=category.description,
        is_active=category.is_active
    )


def validate_admin_role(current_user):
    """
    Validate user has admin privileges - supports both MNR users and Staff.
    DC Protocol: Only high-authority Staff roles (VGK4U Supreme, RVZ, Key Leadership) have admin access.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Staff users: check staff_type first (only high-authority roles)
    staff_type = getattr(current_user, 'staff_type', None)
    user_type = getattr(current_user, 'user_type', '')
    
    logger.info(f"[DC-ADMIN-ROLE] Checking user: staff_type={staff_type}, user_type={user_type}")
    
    if staff_type:
        allowed_staff_types = ['VGK4U', 'VGK4U Supreme', 'RVZ', 'Key Leadership']
        if staff_type in allowed_staff_types:
            logger.info(f"[DC-ADMIN-ROLE] Authorized via staff_type: {staff_type}")
            return
    
    # MNR users: check user_type
    allowed_user_types = ['Admin', 'Super Admin', 'RVZ ID', 'Finance Admin']
    if user_type in allowed_user_types:
        logger.info(f"[DC-ADMIN-ROLE] Authorized via user_type: {user_type}")
        return
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # logger.warning(f"[DC-ADMIN-ROLE] DENIED - staff_type={staff_type}, user_type={user_type}")
    # raise HTTPException(status_code=403, detail="Admin privileges required")


def validate_rvz_role(current_user):
    """
    Validate user is RVZ - supports both MNR users and Staff.
    DC Protocol: Only VGK4U Supreme and RVZ staff have RVZ-level access.
    """
    # Staff users: check staff_type first (only highest authority roles)
    staff_type = getattr(current_user, 'staff_type', None)
    if staff_type:
        allowed_staff_types = ['VGK4U', 'VGK4U Supreme', 'RVZ']
        if staff_type in allowed_staff_types:
            return
    
    # MNR users: check user_type
    user_type = getattr(current_user, 'user_type', '')
    if user_type == 'RVZ ID':
        return
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # raise HTTPException(status_code=403, detail="RVZ privileges required")


# ===== Category Management (RVZ Only) =====

@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get all categories (RVZ sees all, users see active only)"""
    query = db.query(FeedbackCategory)
    
    if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) != 'RVZ ID' and not include_inactive:
        query = query.filter(FeedbackCategory.is_active == True)
    
    categories = query.order_by(FeedbackCategory.name).all()
    return [build_category_response(cat) for cat in categories]


@router.post("/categories", response_model=CategoryResponse)
async def create_category(
    name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Create new category (RVZ only)"""
    validate_rvz_role(current_user)
    
    # Check for duplicate
    existing = db.query(FeedbackCategory).filter(FeedbackCategory.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    
    category = FeedbackCategory(
        name=name,
        description=description,
        created_by=current_user.id
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return build_category_response(category)


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    name: str = Form(None),
    description: str = Form(None),
    is_active: bool = Form(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Update category (RVZ only)"""
    validate_rvz_role(current_user)
    
    category = db.query(FeedbackCategory).filter(FeedbackCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    if name is not None:
        category.name = name
    if description is not None:
        category.description = description
    if is_active is not None:
        category.is_active = is_active
    
    db.commit()
    db.refresh(category)
    return build_category_response(category)


# ===== User Submission Endpoints =====

@router.post("/submit")
async def submit_feedback(
    title: str = Form(...),
    description: str = Form(None),
    category_id: int = Form(...),
    submission_type: str = Form(...),  # 'video', 'photo', or 'text'
    files: List[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Submit user feedback with media files OR text-only (RVZ only)
    Validation: 1 video (max 60 sec) OR 3-5 photos OR text-only (RVZ only)
    """
    # Validate category
    category = db.query(FeedbackCategory).filter(
        FeedbackCategory.id == category_id,
        FeedbackCategory.is_active == True
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Validate submission type
    if submission_type not in ["video", "photo", "text"]:
        raise HTTPException(status_code=400, detail="Invalid submission type")
    
    # TEXT submissions are RVZ-only
    # DC Protocol: Menu-based access control - page assignment = full access
    # if submission_type == "text" and (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) != 'RVZ ID':
    #     raise HTTPException(status_code=403, detail="Text announcements are restricted to RVZ admin only")
    
    # DC Protocol: Validate upload limits for Admin and RVZ
    if files and len(files) > 0:
        # Check total file limit
        if len(files) > MAX_TOTAL_FILES:
            raise HTTPException(
                status_code=400, 
                detail=f"Maximum {MAX_TOTAL_FILES} files allowed per announcement (you uploaded {len(files)})"
            )
        
        # Check video file limit
        video_count = sum(1 for f in files if f.content_type and f.content_type.startswith('video/'))
        if video_count > MAX_VIDEO_FILES:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {MAX_VIDEO_FILES} video files allowed (you uploaded {video_count})"
            )
    
    # Validate file requirements
    if submission_type == "text":
        # Text submissions don't require files
        if not description or len(description.strip()) < 10:
            raise HTTPException(status_code=400, detail="Text announcements must have description (min 10 characters)")
    else:
        # Video and Photo require files
        if not files or len(files) == 0:
            raise HTTPException(status_code=400, detail=f"{submission_type.capitalize()} submissions require media files")
        
        if submission_type == "video" and (len(files) < 1 or len(files) > 5):
            raise HTTPException(status_code=400, detail="Video submissions must have 1-5 video files")
        if submission_type == "photo" and (len(files) < 1 or len(files) > 10):
            raise HTTPException(status_code=400, detail="Photo submissions must have 1-10 photo files")
    
    # Create submission
    submission = FeedbackSubmission(
        user_id=current_user.id,
        category_id=category_id,
        submission_type=SubmissionType(submission_type),
        title=title,
        description=description,
        status=SubmissionStatus.PENDING
    )
    db.add(submission)
    db.flush()  # Get submission ID
    
    # Save files (skip for text-only submissions)
    if submission_type != "text" and files:
        # Universal Upload System: 5MB max, auto-compression, dual storage
        # TODO CRITICAL: Restore watermark processing for announcements (previously via process_media_bytes)
        # Old flow: process_media_bytes() → storage_service.upload_file()
        # New flow: UniversalUploadService.handle_upload() → auto-compression
        # DECISION NEEDED: Integrate watermarking with compression or apply post-compression
        for idx, file in enumerate(files):
            # Create placeholder media record to get ID
            media = FeedbackMedia(
                submission_id=submission.id,
                file_path="pending",  # Temporary - will be updated
                file_type=file.content_type or "application/octet-stream",
                file_size=0,  # Temporary
                duration=None,
                original_filename=file.filename,
                processing_status='pending'
            )
            db.add(media)
            db.flush()  # Get media ID
            
            # Universal Upload: 5MB for images, 20MB for videos, auto-compression
            try:
                upload_result = await UniversalUploadService.handle_upload(
                    file=file,
                    table_name='feedback_media',
                    record_id=media.id,
                    uploaded_by_id=current_user.id,
                    uploaded_by_type='user',
                    storage_dir='feedback_media',
                    db=db,
                    allow_videos=True  # Enable 20MB video uploads
                )
                
                # Update media record with upload results (DC Protocol: dual storage metadata)
                media.file_path = upload_result['file_path']
                media.file_size = upload_result['file_size']
                media.file_type = upload_result['file_type']
                media.processing_status = 'pending' if upload_result['needs_compression'] else 'completed'
                
                # DC Protocol: Storage architecture metadata
                media.original_checksum = upload_result.get('original_checksum')
                media.original_storage_type = upload_result.get('storage_type', 'local')
                media.original_storage_key = upload_result.get('storage_key')
                
                # DC PROTOCOL: Generate semantic download filename (NEW - Nov 29, 2025)
                try:
                    import pytz
                    from datetime import datetime
                    
                    ist_tz = pytz.timezone('Asia/Kolkata')
                    uploaded_at_ist = datetime.now(ist_tz)
                    
                    download_name = UniversalUploadService.generate_download_filename(
                        segment_key='feedback_media',
                        entity_type='feedback',
                        entity_id=submission.id,
                        attachment_id=media.id,
                        uploader_code=current_user.id,  # User.id IS the MNR ID (e.g., "MNR1800143")
                        original_filename=file.filename,
                        uploaded_at=uploaded_at_ist
                    )
                    
                    media.download_filename = download_name
                    media.uses_new_naming = True
                except HTTPException:
                    raise
                except Exception as fname_error:
                    import logging
                    logging.getLogger(__name__).error(f"Failed to generate download filename for feedback {submission.id}: {str(fname_error)}")
                    raise HTTPException(status_code=500, detail=f"Failed to generate semantic filename: {str(fname_error)}")
                
            except HTTPException as e:
                # DC Protocol: Delete orphaned placeholder media record on upload failure
                db.delete(media)
                db.flush()
                raise e
            except Exception as e:
                # DC Protocol: Delete orphaned placeholder media record on upload failure
                db.delete(media)
                db.rollback()
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to upload {file.filename}: {str(e)}"
                )
    
    # DC Protocol: Validate no placeholder file_path persists before commit
    # This prevents orphaned 'pending' records from corrupting the database
    if submission_type != "text" and files:
        media_records_to_validate = db.query(FeedbackMedia).filter(
            FeedbackMedia.submission_id == submission.id
        ).all()
        
        for media_record in media_records_to_validate:
            if media_record.file_path == 'pending' or media_record.file_size == 0:
                # Critical: Placeholder was not properly updated - rollback
                import logging
                logging.getLogger(__name__).error(
                    f"DC Protocol Violation: Media record {media_record.id} has placeholder file_path='pending' "
                    f"or file_size=0. Rolling back submission {submission.id}."
                )
                db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail="Upload failed: Media metadata not properly initialized. Please try again."
                )
    
    # DC Protocol: Flush media records BEFORE RVZ auto-approval query
    db.flush()
    
    # Create initial submission approval record
    approval = FeedbackApproval(
        submission_id=submission.id,
        reviewer_id=current_user.id,
        reviewer_role="rvz" if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) == 'RVZ ID' else "user",
        action=ApprovalAction.SUBMITTED,
        comments="Initial submission"
    )
    db.add(approval)
    
    # RVZ direct approval for ALL submission types (TEXT, VIDEO, PHOTO)
    if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) == 'RVZ ID':
        approval_time = datetime.now()
        media_records = []  # Initialize for all submission types
        
        submission.status = SubmissionStatus.APPROVED
        submission.approved_at = approval_time
        submission.approved_by = current_user.id
        submission.is_visible = True
        
        # DC Protocol: Mark all associated media as APPROVED with audit trail
        if submission_type in ["video", "photo"]:
            media_records = db.query(FeedbackMedia).filter(
                FeedbackMedia.submission_id == submission.id
            ).all()
            
            for media in media_records:
                media.media_status = MediaStatus.APPROVED
                media.decided_by = current_user.id
                media.decided_at = approval_time
                media.decision_comment = f"RVZ direct approval - {submission_type}"
                media.announced_at = approval_time
        
        # Add RVZ approval record for audit trail
        rvz_approval = FeedbackApproval(
            submission_id=submission.id,
            reviewer_id=current_user.id,
            reviewer_role="rvz",
            action=ApprovalAction.APPROVED,
            comments=f"RVZ {submission_type} announcement - direct approval (media: {len(media_records)})"
        )
        db.add(rvz_approval)
    
    db.commit()

    # DC Protocol (Mar 2026): Include video media IDs in response so client can upload thumbnails
    video_media_ids = []
    if media_records:
        for m in media_records:
            if 'video' in (m.file_type or ''):
                video_media_ids.append({"media_id": m.id, "file_name": m.original_filename or ''})

    return {
        "message": "Text announcement created successfully" if submission_type == "text" else "Announcement submitted successfully",
        "submission_id": submission.id,
        "status": submission.status.value,
        "video_media": video_media_ids,
    }


# DC Protocol (Mar 2026): Upload video thumbnail for share preview + OG image
@router.post("/media/{media_id}/thumbnail")
async def upload_video_thumbnail(
    media_id: int,
    thumbnail: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Upload a video thumbnail (JPEG frame) for a specific media record.
    Called after submission to store the thumbnail used in OG share previews.
    """
    media = db.query(FeedbackMedia).filter(FeedbackMedia.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Verify ownership: the media's submission must belong to current_user
    submission = db.query(FeedbackSubmission).filter(
        FeedbackSubmission.id == media.submission_id,
        FeedbackSubmission.user_id == str(current_user.id)
    ).first()
    if not submission:
        raise HTTPException(status_code=403, detail="Not authorized to update this media")

    # Only allow thumbnail for video media
    if 'video' not in (media.file_type or ''):
        raise HTTPException(status_code=400, detail="Thumbnails only apply to video media")

    # Save thumbnail alongside the video
    thumb_content = await thumbnail.read()
    if len(thumb_content) > 2_000_000:  # 2 MB max for a thumbnail
        raise HTTPException(status_code=400, detail="Thumbnail too large (max 2MB)")

    try:
        upload_dir = get_upload_dir()
        sub_dir = upload_dir / str(media.submission_id)
        sub_dir.mkdir(parents=True, exist_ok=True)
        thumb_filename = f"thumb_{media_id}.jpg"
        thumb_path = sub_dir / thumb_filename
        with open(thumb_path, 'wb') as f:
            f.write(thumb_content)
        relative_thumb = f"/uploads/feedback/{media.submission_id}/{thumb_filename}"
        media.thumbnail_url = relative_thumb
        db.commit()
        return {"thumbnail_url": relative_thumb, "media_id": media_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save thumbnail: {str(e)}")


# DC Protocol (Jan 23, 2026): Supreme Staff Announcement Creation with Auto-Approval
SUPREME_STAFF_TYPES = ['VGK4U_SUPREME', 'RVZ_SUPREME', 'VGK4U', 'VGK4U_EA', 'vgk4u', 'vgk4u_supreme', 'rvz_supreme']

@router.post("/staff/submit")
async def submit_staff_announcement(
    title: str = Form(...),
    description: str = Form(None),
    category_id: int = Form(...),
    submission_type: str = Form(...),  # 'video', 'photo', or 'text'
    files: List[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user)
):
    """
    DC Protocol (Jan 23, 2026): Staff announcement submission with Supreme auto-approval
    - Supreme staff (VGK4U_SUPREME, RVZ_SUPREME, VGK4U, VGK4U_EA) get immediate approval
    - Media limits: 1-10 images, videos up to 3 minutes
    - All uploads go to Object Storage for persistence
    """
    from datetime import datetime
    from app.models.staff import StaffEmployee
    
    # Validate staff user
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(status_code=403, detail="Staff authentication required")
    
    # Check if Supreme staff
    staff_type = getattr(current_user, 'staff_type', '') or ''
    is_supreme = staff_type.upper() in [s.upper() for s in SUPREME_STAFF_TYPES]
    
    # Validate category
    category = db.query(FeedbackCategory).filter(
        FeedbackCategory.id == category_id,
        FeedbackCategory.is_active == True
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Validate submission type
    if submission_type not in ["video", "photo", "text"]:
        raise HTTPException(status_code=400, detail="Invalid submission type")
    
    # Validate file requirements
    if submission_type == "text":
        if not description or len(description.strip()) < 10:
            raise HTTPException(status_code=400, detail="Text announcements must have description (min 10 characters)")
    else:
        if not files or len(files) == 0:
            raise HTTPException(status_code=400, detail=f"{submission_type.capitalize()} submissions require media files")
        
        # DC Protocol: 1-10 images, videos up to 3 mins
        if submission_type == "photo" and len(files) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 images allowed per announcement")
        if submission_type == "video" and len(files) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 video files allowed")
    
    # Get a valid MNR user ID to associate with the announcement
    # Staff announcements are associated with a system/admin MNR user
    admin_user = db.query(User).filter(User.user_type == 'RVZ ID').first()
    if not admin_user:
        admin_user = db.query(User).first()
    if not admin_user:
        raise HTTPException(status_code=500, detail="No valid user found to associate announcement")
    
    # Create submission with auto-approval for Supreme
    initial_status = SubmissionStatus.APPROVED if is_supreme else SubmissionStatus.PENDING
    
    submission = FeedbackSubmission(
        user_id=admin_user.id,
        category_id=category_id,
        submission_type=SubmissionType(submission_type),
        title=title,
        description=description,
        status=initial_status,
        is_visible=is_supreme,  # Immediately visible if Supreme
        approved_at=datetime.utcnow() if is_supreme else None,
        approved_by=str(current_user.id) if is_supreme else None
    )
    db.add(submission)
    db.flush()
    
    # Save files
    if submission_type != "text" and files:
        for idx, file in enumerate(files):
            # Create media record
            media_status = MediaStatus.APPROVED if is_supreme else MediaStatus.PENDING
            media = FeedbackMedia(
                submission_id=submission.id,
                file_path="pending",
                file_type=file.content_type or "application/octet-stream",
                media_status=media_status,
                is_visible=is_supreme,
                media_index=idx
            )
            db.add(media)
            db.flush()
            
            try:
                # Use universal upload service with correct parameter names
                # DC Protocol: Match user submission storage_dir for consistency
                upload_result = await UniversalUploadService.handle_upload(
                    file=file,
                    table_name='feedback_media',
                    record_id=media.id,
                    uploaded_by_id=current_user.id,
                    uploaded_by_type='staff',
                    storage_dir='feedback_media',
                    db=db,
                    allow_videos=True
                )
                
                media.file_path = upload_result["file_path"]
                media.file_size = upload_result.get("file_size", 0)
                media.storage_type = upload_result.get("storage_type", "object_storage")
                
                # Generate download filename
                try:
                    import pytz
                    ist_tz = pytz.timezone('Asia/Kolkata')
                    uploaded_at_ist = datetime.now(ist_tz)
                    
                    # DC Protocol: Use emp_code for staff, id for MNR users
                    uploader_code = getattr(current_user, 'emp_code', None) or str(current_user.id)
                    
                    download_name = UniversalUploadService.generate_download_filename(
                        segment_key='feedback_media',
                        entity_type='feedback',
                        entity_id=submission.id,
                        attachment_id=media.id,
                        uploader_code=uploader_code,
                        original_filename=file.filename or 'media',
                        uploaded_at=uploaded_at_ist
                    )
                    media.download_filename = download_name
                    media.uses_new_naming = True
                except Exception:
                    pass  # Non-critical
                    
            except HTTPException:
                db.delete(media)
                db.flush()
                raise
            except Exception as e:
                db.delete(media)
                db.rollback()
                raise HTTPException(status_code=400, detail=f"Failed to upload {file.filename}: {str(e)}")
    
    db.commit()
    
    status_msg = "approved and visible" if is_supreme else "pending review"
    return {
        "message": f"Announcement created successfully ({status_msg})",
        "submission_id": submission.id,
        "status": submission.status.value,
        "is_visible": submission.is_visible,
        "auto_approved": is_supreme
    }


@router.get("/my-submissions", response_model=List[SubmissionResponse])
async def get_my_submissions(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get current user's submissions"""
    from app.models.staff import StaffEmployee
    
    # DC Protocol: Staff users (with numeric IDs) don't have feedback submissions
    # Only MNR users (with string IDs like MNR182313597) can submit announcements
    if isinstance(current_user, StaffEmployee):
        # Staff users don't have announcements - return empty list
        return []
    
    # MNR user - query with string ID
    submissions = db.query(FeedbackSubmission).filter(
        FeedbackSubmission.user_id == str(current_user.id)
    ).order_by(FeedbackSubmission.submitted_at.desc()).all()
    
    result = []
    for sub in submissions:
        # DC Protocol: Filter out hidden/failed media to prevent 404 errors
        visible_media = [m for m in sub.media_files if m.is_visible and m.processing_status != 'failed']
        
        # DC Protocol: Recalculate submission visibility from media visibility
        has_visible_media = len(visible_media) > 0
        computed_visibility = sub.is_visible and has_visible_media  # Both must be true
        
        result.append(SubmissionResponse(
            id=sub.id,
            title=sub.title,
            description=sub.description,
            submission_type=sub.submission_type.value,
            category=build_category_response(sub.category),
            status=sub.status.value,
            is_visible=computed_visibility,  # Use computed visibility
            submitted_at=sub.submitted_at,
            approved_at=sub.approved_at,
            media=[build_media_response(m) for m in visible_media],
            user_name=sub.user.name if sub.user else sub.user_id,
            user_id=sub.user.id if sub.user else sub.user_id
        ))
    
    return result


# ===== Admin Approval Endpoints =====

@router.get("/pending", response_model=List[SubmissionResponse])
async def get_pending_submissions(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get all pending submissions (Admin only)"""
    validate_admin_role(current_user)
    
    submissions = db.query(FeedbackSubmission).filter(
        FeedbackSubmission.status == SubmissionStatus.PENDING
    ).order_by(FeedbackSubmission.submitted_at.asc()).all()
    
    result = []
    for sub in submissions:
        # DC Protocol: Filter out hidden/failed media to prevent 404 errors
        visible_media = [m for m in sub.media_files if m.is_visible and m.processing_status != 'failed']
        
        # DC Protocol: Recalculate submission visibility from media visibility
        has_visible_media = len(visible_media) > 0
        computed_visibility = sub.is_visible and has_visible_media  # Both must be true
        
        result.append(SubmissionResponse(
            id=sub.id,
            title=sub.title,
            description=sub.description,
            submission_type=sub.submission_type.value,
            category=build_category_response(sub.category),
            status=sub.status.value,
            is_visible=computed_visibility,  # Use computed visibility
            submitted_at=sub.submitted_at,
            approved_at=sub.approved_at,
            media=[build_media_response(m) for m in visible_media],
            user_name=sub.user.name if sub.user else sub.user_id,
            user_id=sub.user.id if sub.user else sub.user_id
        ))
    
    return result


@router.post("/approve/{submission_id}")
async def approve_submission(
    submission_id: int,
    comments: str = Form(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Approve a submission (Admin only)"""
    validate_admin_role(current_user)
    
    submission = db.query(FeedbackSubmission).filter(
        FeedbackSubmission.id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if submission.status != SubmissionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Submission already processed")
    
    # Update submission
    submission.status = SubmissionStatus.APPROVED
    submission.approved_at = datetime.now()
    submission.approved_by = current_user.id
    submission.is_visible = True  # Default to visible when approved
    
    # Create approval record
    approval = FeedbackApproval(
        submission_id=submission_id,
        reviewer_id=current_user.id,
        reviewer_role=(getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))),
        action=ApprovalAction.APPROVED,
        comments=comments
    )
    db.add(approval)
    
    db.commit()
    
    return {
        "message": "Submission approved successfully",
        "submission_id": submission_id,
        "status": "approved"
    }


@router.post("/reject/{submission_id}")
async def reject_submission(
    submission_id: int,
    comments: str = Form(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Reject a submission (Admin only)"""
    validate_admin_role(current_user)
    
    submission = db.query(FeedbackSubmission).filter(
        FeedbackSubmission.id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if submission.status != SubmissionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Submission already processed")
    
    # Update submission
    submission.status = SubmissionStatus.REJECTED
    
    # Create approval record
    approval = FeedbackApproval(
        submission_id=submission_id,
        reviewer_id=current_user.id,
        reviewer_role=(getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))),
        action=ApprovalAction.REJECTED,
        comments=comments
    )
    db.add(approval)
    
    db.commit()
    
    return {
        "message": "Submission rejected",
        "submission_id": submission_id,
        "status": "rejected"
    }


def recalculate_submission_status(submission: FeedbackSubmission, db: Session):
    """
    DC Protocol: Recalculate submission status based on individual media statuses
    Logic:
    - All media approved → APPROVED
    - All media rejected → REJECTED
    - Mix of approved/rejected with no pending → PARTIALLY_APPROVED
    - Has pending media → UNDER_REVIEW or PENDING
    """
    media_files = submission.media_files
    if not media_files:
        return
    
    approved_count = sum(1 for m in media_files if m.media_status == MediaStatus.APPROVED)
    rejected_count = sum(1 for m in media_files if m.media_status == MediaStatus.REJECTED)
    pending_count = sum(1 for m in media_files if m.media_status == MediaStatus.PENDING)
    total_count = len(media_files)
    
    # Update aggregate counts
    submission.approved_media_count = approved_count
    submission.rejected_media_count = rejected_count
    
    # Determine new status
    if approved_count == total_count:
        # All approved
        submission.status = SubmissionStatus.APPROVED
        submission.approved_at = datetime.now()
        submission.is_visible = True
    elif rejected_count == total_count:
        # All rejected
        submission.status = SubmissionStatus.REJECTED
        submission.approved_at = None
        submission.is_visible = False
    elif pending_count == 0 and (approved_count > 0 or rejected_count > 0):
        # Mix of approved/rejected, no pending
        submission.status = SubmissionStatus.PARTIALLY_APPROVED
        if approved_count > 0:
            submission.is_visible = True  # Show approved media
    elif pending_count < total_count:
        # At least one decision made
        submission.status = SubmissionStatus.UNDER_REVIEW
    else:
        # All pending
        submission.status = SubmissionStatus.PENDING
    
    db.flush()


@router.post("/media/approve/{media_id}")
async def approve_media(
    media_id: int,
    comment: str = Form(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Approve individual media file (Admin only)"""
    validate_admin_role(current_user)
    
    media = db.query(FeedbackMedia).filter(FeedbackMedia.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media file not found")
    
    submission = media.submission
    if submission.status == SubmissionStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Submission already fully approved")
    
    # Update media status
    media.media_status = MediaStatus.APPROVED
    media.decided_by = current_user.id
    media.decided_at = datetime.now()
    media.decision_comment = comment
    media.announced_at = datetime.now()
    
    # Update submission tracking
    submission.last_reviewed_by = current_user.id
    submission.last_reviewed_at = datetime.now()
    
    # Create approval audit record
    approval = FeedbackApproval(
        submission_id=submission.id,
        media_id=media_id,
        reviewer_id=current_user.id,
        reviewer_role=(getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))),
        action=ApprovalAction.APPROVED,
        comments=comment
    )
    db.add(approval)
    
    # Recalculate submission status
    recalculate_submission_status(submission, db)
    
    db.commit()
    
    return {
        "message": "Media approved successfully",
        "media_id": media_id,
        "submission_id": submission.id,
        "media_status": "approved",
        "submission_status": submission.status.value,
        "approved_count": submission.approved_media_count,
        "rejected_count": submission.rejected_media_count
    }


@router.post("/media/reject/{media_id}")
async def reject_media(
    media_id: int,
    comment: str = Form(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Reject individual media file (Admin only)"""
    validate_admin_role(current_user)
    
    media = db.query(FeedbackMedia).filter(FeedbackMedia.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media file not found")
    
    submission = media.submission
    if submission.status == SubmissionStatus.REJECTED:
        raise HTTPException(status_code=400, detail="Submission already fully rejected")
    
    # Update media status
    media.media_status = MediaStatus.REJECTED
    media.decided_by = current_user.id
    media.decided_at = datetime.now()
    media.decision_comment = comment
    
    # Update submission tracking
    submission.last_reviewed_by = current_user.id
    submission.last_reviewed_at = datetime.now()
    
    # Create approval audit record
    approval = FeedbackApproval(
        submission_id=submission.id,
        media_id=media_id,
        reviewer_id=current_user.id,
        reviewer_role=(getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))),
        action=ApprovalAction.REJECTED,
        comments=comment
    )
    db.add(approval)
    
    # Recalculate submission status
    recalculate_submission_status(submission, db)
    
    db.commit()
    
    return {
        "message": "Media rejected successfully",
        "media_id": media_id,
        "submission_id": submission.id,
        "media_status": "rejected",
        "submission_status": submission.status.value,
        "approved_count": submission.approved_media_count,
        "rejected_count": submission.rejected_media_count
    }


@router.delete("/media/{media_id}")
async def delete_media_file(
    media_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Delete a media file from a pending submission (Admin only)"""
    validate_admin_role(current_user)
    
    media = db.query(FeedbackMedia).filter(FeedbackMedia.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media file not found")
    
    submission = media.submission
    if submission.status != SubmissionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Can only edit pending submissions")
    
    # Validate media count rules
    remaining_count = len(submission.media_files) - 1
    if submission.submission_type == SubmissionType.VIDEO and remaining_count < 1:
        raise HTTPException(status_code=400, detail="Video submissions must have at least 1 video")
    if submission.submission_type == SubmissionType.PHOTO and remaining_count < 3:
        raise HTTPException(status_code=400, detail="Photo submissions must have at least 3 photos")
    
    # Delete physical file
    file_path = Path("uploads") / media.file_path
    if file_path.exists():
        file_path.unlink()
    
    # Delete database record
    db.delete(media)
    db.commit()
    
    return {
        "message": "Media file deleted successfully",
        "media_id": media_id,
        "remaining_files": remaining_count
    }


@router.post("/media/replace/{media_id}")
async def replace_media_file(
    media_id: int,
    file: UploadFile = File(...),
    edit_metadata: str = Form(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Replace a media file in a pending submission (Admin only) - supports edited images"""
    validate_admin_role(current_user)
    
    media = db.query(FeedbackMedia).filter(FeedbackMedia.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media file not found")
    
    submission = media.submission
    if submission.status != SubmissionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Can only edit pending submissions")
    
    # Validate file type matches submission type
    file_type = file.content_type
    if submission.submission_type == SubmissionType.VIDEO and not file_type.startswith('video/'):
        raise HTTPException(status_code=400, detail="Must upload a video file")
    if submission.submission_type == SubmissionType.PHOTO and not file_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Must upload an image file")
    
    # DC Protocol: Delete old file from Object Storage if exists
    from app.services.object_storage import storage_service
    from app.services.universal_upload_service import UniversalUploadService
    
    old_path = media.file_path
    if old_path and not old_path.startswith('/uploads/'):
        if old_path.startswith('/storage/'):
            old_path = old_path[9:]
        storage_service.delete_file(old_path)
    
    # DC Protocol: Upload new file to Object Storage
    uploader_code = getattr(current_user, 'emp_code', None) or str(current_user.id)
    upload_result = await UniversalUploadService.handle_upload(
        file=file,
        table_name='feedback_media',
        record_id=submission.id,
        uploaded_by_id=current_user.id,
        uploaded_by_type='staff' if hasattr(current_user, 'emp_code') else 'user',
        storage_dir='feedback_media',
        db=db,
        emp_code=uploader_code if hasattr(current_user, 'emp_code') else None,
        allow_videos=(submission.submission_type == SubmissionType.VIDEO)
    )
    
    # Update database record with Object Storage path
    media.file_path = upload_result['file_path']
    media.file_size = upload_result['file_size']
    media.file_type = upload_result['file_type']
    media.original_checksum = upload_result.get('original_checksum')
    media.original_storage_type = upload_result.get('storage_type')
    media.original_storage_key = upload_result.get('storage_key')
    
    # DC Protocol: Reset media approval state for re-review when file is replaced
    # Track previous status for count adjustment
    previous_status = media.media_status
    
    # Reset media to pending state - WVV Protocol compliance
    media.media_status = MediaStatus.PENDING
    media.is_visible = True  # Ensure visible for review
    media.processing_status = 'pending'  # Reset processing status
    media.decided_at = None  # Clear previous decision timestamp
    media.decision_comment = None  # Clear previous decision comment
    
    # Update submission approval counts based on previous media status
    if previous_status == MediaStatus.APPROVED:
        submission.approved_media_count = max(0, submission.approved_media_count - 1)
    elif previous_status == MediaStatus.REJECTED:
        submission.rejected_media_count = max(0, submission.rejected_media_count - 1)
    
    # Create approval record if edit metadata provided (indicates admin edit)
    if edit_metadata:
        import json
        try:
            edit_details = json.loads(edit_metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid edit metadata JSON")
        
        approval = FeedbackApproval(
            submission_id=submission.id,
            reviewer_id=current_user.id,
            reviewer_role=(getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))),
            action=ApprovalAction.EDITED,
            comments=f"Image edited: media_id={media_id}",
            edit_details=edit_details
        )
        db.add(approval)
    
    db.commit()
    
    return {
        "message": "Media file replaced successfully",
        "media_id": media_id,
        "new_file_path": f"/uploads/{relative_path}"
    }


@router.post("/media/add/{submission_id}")
async def add_media_file(
    submission_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Add a media file to a pending submission (Admin only)"""
    validate_admin_role(current_user)
    
    submission = db.query(FeedbackSubmission).filter(
        FeedbackSubmission.id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if submission.status != SubmissionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Can only edit pending submissions")
    
    # Validate media count rules
    current_count = len(submission.media_files)
    if submission.submission_type == SubmissionType.VIDEO and current_count >= 1:
        raise HTTPException(status_code=400, detail="Video submissions can only have 1 video")
    if submission.submission_type == SubmissionType.PHOTO and current_count >= 5:
        raise HTTPException(status_code=400, detail="Photo submissions can have maximum 5 photos")
    
    # Validate file type
    file_type = file.content_type
    if submission.submission_type == SubmissionType.VIDEO and not file_type.startswith('video/'):
        raise HTTPException(status_code=400, detail="Must upload a video file")
    if submission.submission_type == SubmissionType.PHOTO and not file_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Must upload an image file")
    
    # DC Protocol: Upload file to Object Storage
    from app.services.universal_upload_service import UniversalUploadService
    
    uploader_code = getattr(current_user, 'emp_code', None) or str(current_user.id)
    upload_result = await UniversalUploadService.handle_upload(
        file=file,
        table_name='feedback_media',
        record_id=submission_id,
        uploaded_by_id=current_user.id,
        uploaded_by_type='staff' if hasattr(current_user, 'emp_code') else 'user',
        storage_dir='feedback_media',
        db=db,
        emp_code=uploader_code if hasattr(current_user, 'emp_code') else None,
        allow_videos=(submission.submission_type == SubmissionType.VIDEO)
    )
    
    # Create database record with Object Storage path
    media = FeedbackMedia(
        submission_id=submission_id,
        file_path=upload_result['file_path'],
        file_type=upload_result['file_type'],
        file_size=upload_result['file_size'],
        original_filename=upload_result['original_filename'],
        media_status=MediaStatus.PENDING,
        is_visible=True,
        processing_status='pending',
        original_checksum=upload_result.get('original_checksum'),
        original_storage_type=upload_result.get('storage_type'),
        original_storage_key=upload_result.get('storage_key')
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    
    return {
        "message": "Media file added successfully",
        "media_id": media.id,
        "file_path": f"/storage/{upload_result['file_path']}"
    }


# ===== Hide/Unhide Announcements (Admin) =====

@router.post("/hide/{submission_id}")
async def hide_announcement(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Hide an approved announcement from public view (Admin only)"""
    validate_admin_role(current_user)
    
    submission = db.query(FeedbackSubmission).filter(
        FeedbackSubmission.id == submission_id,
        FeedbackSubmission.status == SubmissionStatus.APPROVED
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Approved submission not found")
    
    # DC Protocol: If already hidden, just return success (idempotent operation)
    if not submission.is_visible:
        return {
            "message": "Announcement is already hidden",
            "submission_id": submission_id,
            "is_visible": False
        }
    
    # DC Protocol: Use emp_code for staff, id for MNR users (FK constraint removed)
    actor_id = getattr(current_user, 'emp_code', None) or str(current_user.id)
    submission.is_visible = False
    submission.hidden_by = actor_id
    submission.hidden_at = datetime.now()
    
    db.commit()
    
    return {
        "message": "Announcement hidden successfully",
        "submission_id": submission_id,
        "is_visible": False,
        "hidden_by": actor_id
    }


@router.post("/unhide/{submission_id}")
async def unhide_announcement(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Unhide an announcement (Admin only)"""
    validate_admin_role(current_user)
    
    submission = db.query(FeedbackSubmission).filter(
        FeedbackSubmission.id == submission_id,
        FeedbackSubmission.status == SubmissionStatus.APPROVED
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Approved submission not found")
    
    # DC Protocol: If already visible, just return success (idempotent operation)
    if submission.is_visible:
        return {
            "message": "Announcement is already visible",
            "submission_id": submission_id,
            "is_visible": True
        }
    
    submission.is_visible = True
    submission.hidden_by = None
    submission.hidden_at = None
    
    db.commit()
    
    return {
        "message": "Announcement visible again",
        "submission_id": submission_id,
        "is_visible": True
    }


# ===== Display Order Management (Admin) =====

class DisplayOrderUpdate(BaseModel):
    display_order: Optional[int] = Field(None, description="Display order (lower = higher priority, null = default order)")

@router.patch("/{submission_id}/display-order")
async def update_display_order(
    submission_id: int,
    order_data: DisplayOrderUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: Update announcement display order (Admin/RVZ only)
    Lower numbers appear first, NULL uses default date ordering
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Check admin permissions (user_type 2 = Admin, 3 = RVZ)
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not hasattr(current_user, 'user_type') or current_user.user_type not in [2, 3]:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    submission = db.query(FeedbackSubmission).filter(
        FeedbackSubmission.id == submission_id,
        FeedbackSubmission.is_deleted == False
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    submission.display_order = order_data.display_order
    db.commit()
    
    return {
        "message": "Display order updated",
        "submission_id": submission_id,
        "display_order": submission.display_order
    }

@router.post("/reorder")
async def reorder_announcements(
    orders: List[dict],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: Bulk reorder announcements (Admin/RVZ only)
    Accepts list of {id: int, display_order: int}
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not hasattr(current_user, 'user_type') or current_user.user_type not in [2, 3]:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    updated = 0
    for item in orders:
        if 'id' in item and 'display_order' in item:
            db.query(FeedbackSubmission).filter(
                FeedbackSubmission.id == item['id'],
                FeedbackSubmission.is_deleted == False
            ).update({'display_order': item['display_order']})
            updated += 1
    
    db.commit()
    
    return {
        "message": f"Reordered {updated} announcements",
        "updated_count": updated
    }


# ===== Public Announcements (User View) =====

@router.get("/announcements", response_model=List[AnnouncementResponse])
async def get_announcements(
    category_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    include_hidden: bool = False,
    city: Optional[str] = None,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    limit: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)  # SECURE: Requires authentication
):
    """
    Get approved announcements with filters (REQUIRES AUTHENTICATION)
    Users see only visible items, Admins can see hidden items too
    Sorted by: Top-rated first, then most recent
    
    DC Protocol Fix (Dec 05, 2025): Removed INNER JOIN on FeedbackMedia to support
    text-only announcements. Media filtering is now applied post-query during
    response building, matching the public endpoint behavior.
    """
    from sqlalchemy import func, case
    from app.models.feedback import AnnouncementRating
    
    # Base query with joins for user details and ratings
    # DC Protocol: No INNER JOIN on FeedbackMedia - supports text-only announcements
    query = db.query(
        FeedbackSubmission,
        User.name.label('user_name'),
        User.city.label('city'),
        func.coalesce(func.avg(AnnouncementRating.rating), 0).label('average_rating'),
        func.count(AnnouncementRating.id).label('total_ratings')
    ).join(
        User, FeedbackSubmission.user_id == User.id
    ).outerjoin(
        AnnouncementRating, FeedbackSubmission.id == AnnouncementRating.submission_id
    ).filter(
        # Exclude soft-deleted announcements
        FeedbackSubmission.is_deleted == False,
        # Show submissions with approved or under_review status
        or_(
            FeedbackSubmission.status == SubmissionStatus.APPROVED,
            FeedbackSubmission.status == SubmissionStatus.UNDER_REVIEW
        )
    ).group_by(
        FeedbackSubmission.id,
        User.name,
        User.city
    )
    
    # SECURITY: Force include_hidden=False for non-authenticated users or non-admins
    is_admin = (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) in ["Admin", "Super Admin", "RVZ ID", "Finance Admin"]
    if not is_admin:
        # Force visible-only for non-admins and unauthenticated users
        query = query.filter(FeedbackSubmission.is_visible == True)
    elif not include_hidden:
        # Admin requested visible-only
        query = query.filter(FeedbackSubmission.is_visible == True)
    
    # Category filter
    if category_id:
        query = query.filter(FeedbackSubmission.category_id == category_id)
    
    # Date range filter
    if start_date:
        query = query.filter(FeedbackSubmission.approved_at >= start_date)
    if end_date:
        from datetime import timedelta
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(FeedbackSubmission.approved_at <= end_datetime)
    
    # Location/City filter
    if city:
        query = query.filter(User.city.ilike(f'%{city}%'))
    
    # User ID filter
    if user_id:
        query = query.filter(User.id.ilike(f'%{user_id}%'))
    
    # User Name filter
    if user_name:
        query = query.filter(User.name.ilike(f'%{user_name}%'))
    
    # Sort by: Top-rated first (DESC), then most recent (DESC)
    query = query.order_by(
        func.coalesce(func.avg(AnnouncementRating.rating), 0).desc(),
        FeedbackSubmission.approved_at.desc()
    )
    
    # Execute query
    results = query.all()
    
    # Build response
    response_list = []
    for row in results:
        ann = row[0]  # FeedbackSubmission object
        user_name_value = row[1]  # user_name
        city_value = row[2]  # city
        avg_rating = float(row[3]) if row[3] else 0.0  # average_rating
        total_ratings_value = int(row[4]) if row[4] else 0  # total_ratings
        
        # Only include approved media files in the response
        approved_media = [
            build_media_response(m) for m in ann.media_files 
            if m.media_status == MediaStatus.APPROVED
        ]
        
        # Use approved_at if available, otherwise last_reviewed_at, otherwise submitted_at
        display_datetime = ann.approved_at or ann.last_reviewed_at or ann.submitted_at
        
        response_list.append(AnnouncementResponse(
            id=ann.id,
            title=ann.title,
            description=ann.description,
            submission_type=ann.submission_type.value,
            category=build_category_response(ann.category),
            approved_at=display_datetime,
            updated_at=display_datetime,
            is_visible=ann.is_visible,
            media=approved_media,  # Only approved media - renamed to 'media'
            user_id=ann.user_id,
            user_name=user_name_value or "Unknown",
            city=city_value,
            average_rating=round(avg_rating, 2),
            total_ratings=total_ratings_value,
            shares_count=ann.shares_count or 0,
            views_count=ann.views_count or 0
        ))
    
    return response_list


# ===== Staff Announcements Endpoint (All Status Filters) =====

@router.get("/announcements/staff")
async def get_announcements_staff(
    category_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    city: Optional[str] = None,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    status: Optional[str] = None,
    include_hidden: bool = False,
    include_deleted: bool = False,
    include_all_statuses: bool = False,
    limit: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: Staff announcements endpoint with all status filters
    Supports filtering by: status, hidden, deleted, category, date range, user
    VGK4U Supreme can see all; other staff see based on permissions
    """
    from sqlalchemy import func
    from app.models.feedback import AnnouncementRating
    
    # Validate staff access
    validate_admin_role(current_user)
    
    # Base query with joins for user details and ratings
    query = db.query(
        FeedbackSubmission,
        User.name.label('user_name'),
        User.city.label('city'),
        func.coalesce(func.avg(AnnouncementRating.rating), 0).label('average_rating'),
        func.count(AnnouncementRating.id).label('total_ratings')
    ).join(
        User, FeedbackSubmission.user_id == User.id
    ).outerjoin(
        AnnouncementRating, FeedbackSubmission.id == AnnouncementRating.submission_id
    ).group_by(
        FeedbackSubmission.id,
        User.name,
        User.city
    )
    
    # Status filter
    if status:
        status_upper = status.upper()
        if status_upper == 'HIDDEN':
            query = query.filter(
                FeedbackSubmission.is_visible == False,
                FeedbackSubmission.is_deleted == False
            )
        elif status_upper == 'DELETED':
            query = query.filter(FeedbackSubmission.is_deleted == True)
        elif status_upper == 'APPROVED':
            query = query.filter(
                FeedbackSubmission.status == SubmissionStatus.APPROVED,
                FeedbackSubmission.is_visible == True,
                FeedbackSubmission.is_deleted == False
            )
        else:
            # Map to SubmissionStatus enum
            status_map = {
                'PENDING': SubmissionStatus.PENDING,
                'UNDER_REVIEW': SubmissionStatus.UNDER_REVIEW,
                'PARTIALLY_APPROVED': SubmissionStatus.PARTIALLY_APPROVED,
                'REJECTED': SubmissionStatus.REJECTED
            }
            if status_upper in status_map:
                query = query.filter(
                    FeedbackSubmission.status == status_map[status_upper],
                    FeedbackSubmission.is_deleted == False
                )
    else:
        # Default: include all statuses based on flags
        if not include_deleted:
            query = query.filter(FeedbackSubmission.is_deleted == False)
        if not include_hidden and not include_all_statuses:
            query = query.filter(FeedbackSubmission.is_visible == True)
        if not include_all_statuses:
            query = query.filter(
                or_(
                    FeedbackSubmission.status == SubmissionStatus.APPROVED,
                    FeedbackSubmission.status == SubmissionStatus.UNDER_REVIEW
                )
            )
    
    # Category filter
    if category_id:
        query = query.filter(FeedbackSubmission.category_id == category_id)
    
    # Date range filter
    if start_date:
        query = query.filter(
            or_(
                FeedbackSubmission.approved_at >= start_date,
                FeedbackSubmission.submitted_at >= start_date
            )
        )
    if end_date:
        from datetime import timedelta
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(
            or_(
                FeedbackSubmission.approved_at <= end_datetime,
                FeedbackSubmission.submitted_at <= end_datetime
            )
        )
    
    # Location/City filter
    if city:
        query = query.filter(User.city.ilike(f'%{city}%'))
    
    # User ID filter
    if user_id:
        query = query.filter(User.id.ilike(f'%{user_id}%'))
    
    # User Name filter
    if user_name:
        query = query.filter(User.name.ilike(f'%{user_name}%'))
    
    # Sort by most recent first
    query = query.order_by(FeedbackSubmission.submitted_at.desc())
    
    # Execute query
    results = query.all()
    
    # Build response with extended fields for staff
    response_list = []
    for row in results:
        ann = row[0]
        user_name_value = row[1]
        city_value = row[2]
        avg_rating = float(row[3]) if row[3] else 0.0
        total_ratings_value = int(row[4]) if row[4] else 0
        
        # Include all media for staff view
        all_media = [
            build_media_response(m) for m in ann.media_files
        ]
        
        display_datetime = ann.approved_at or ann.last_reviewed_at or ann.submitted_at
        
        response_list.append({
            "id": ann.id,
            "title": ann.title,
            "description": ann.description,
            "submission_type": ann.submission_type.value if ann.submission_type else None,
            "category": build_category_response(ann.category) if ann.category else None,
            "status": ann.status.value if ann.status else None,
            "approved_at": display_datetime.isoformat() if display_datetime else None,
            "submitted_at": ann.submitted_at.isoformat() if ann.submitted_at else None,
            "updated_at": display_datetime.isoformat() if display_datetime else None,
            "is_visible": ann.is_visible,
            "is_deleted": ann.is_deleted,
            "media": all_media,
            "user_id": ann.user_id,
            "user_name": user_name_value or "Unknown",
            "city": city_value,
            "average_rating": round(avg_rating, 2),
            "total_ratings": total_ratings_value,
            "shares_count": ann.shares_count or 0,
            "views_count": ann.views_count or 0
        })
    
    return response_list


# ===== Public Announcement View (No Auth Required) =====


# ===== Share Tracking Endpoint (No Auth Required) =====

@router.post("/{submission_id}/share")
async def share_announcement(
    submission_id: int,
    db: Session = Depends(get_db)
):
    """Track announcement share (public endpoint, no auth required)"""
    announcement = db.query(FeedbackSubmission).filter(
        FeedbackSubmission.id == submission_id,
        FeedbackSubmission.status == SubmissionStatus.APPROVED,
        FeedbackSubmission.is_visible == True
    ).first()
    
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    announcement.shares_count += 1
    db.commit()
    
    return {"message": "Share tracked", "shares": announcement.shares_count}


# ===== Public Announcements Endpoint (No Auth Required) =====

@router.api_route("/public/announcements", methods=["GET", "HEAD"], response_model=List[AnnouncementResponse])
async def get_public_announcements(
    limit: int = 5,
    category_id: Optional[int] = None,
    platform: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    DC_ANNOUNCE_001: Public announcements endpoint (WVV-compliant, no auth required)
    Supports GET and HEAD requests for proxy infrastructure compatibility
    Returns visible, approved announcements with metadata (ratings, shares, views)
    Limited to 5 announcements by default, max 20
    Optional category_id filter: when provided, returns only that category (e.g. VGK4U Shoutouts)
    DC Protocol (Jan 23, 2026): Optimized with eager loading for speed
    """
    from sqlalchemy import func
    from sqlalchemy.orm import joinedload
    from app.models.feedback import AnnouncementRating

    if limit > 50:
        limit = 50
    if limit < 1:
        limit = 5

    base_filter = [
        FeedbackSubmission.is_visible == True,
        FeedbackSubmission.status == SubmissionStatus.APPROVED
    ]
    if category_id:
        base_filter.append(FeedbackSubmission.category_id == category_id)
    # Audience targeting: filter by platform if provided
    # 'mnr' callers see 'mnr' + 'both'; 'vgk' callers see 'vgk' + 'both'; None sees all
    # DC-FIX: for vgk platform also include anything in the "VGK4U Shoutouts" category
    # regardless of visible_to — staff intent is clear from category choice.
    # Category ID is looked up dynamically so hardcoding is avoided.
    if platform in ('mnr', 'vgk'):
        from sqlalchemy import or_, text as _text
        if platform == 'vgk':
            _vgk_cat_rows = db.execute(
                _text("SELECT id FROM feedback_categories WHERE LOWER(name) LIKE '%vgk%shoutout%' OR LOWER(name) LIKE '%vgk4u shoutout%'")
            ).fetchall()
            _vgk_cat_ids = [r[0] for r in _vgk_cat_rows] or [11]
            _vgk_or_clauses = [
                FeedbackSubmission.visible_to == 'vgk',
                FeedbackSubmission.visible_to == 'both',
            ]
            for _cid in _vgk_cat_ids:
                _vgk_or_clauses.append(FeedbackSubmission.category_id == _cid)
            base_filter.append(or_(*_vgk_or_clauses))
        else:
            base_filter.append(
                or_(FeedbackSubmission.visible_to == platform, FeedbackSubmission.visible_to == 'both')
            )

    subquery = db.query(
        FeedbackSubmission.id,
        func.coalesce(User.name, FeedbackSubmission.user_id).label('user_name'),
        func.coalesce(User.city, '').label('city'),
        func.coalesce(func.avg(AnnouncementRating.rating), 0).label('average_rating'),
        func.count(AnnouncementRating.id).label('total_ratings')
    ).outerjoin(
        User, FeedbackSubmission.user_id == User.id
    ).outerjoin(
        AnnouncementRating, FeedbackSubmission.id == AnnouncementRating.submission_id
    ).filter(
        *base_filter
    ).group_by(
        FeedbackSubmission.id,
        User.name,
        User.city,
        FeedbackSubmission.user_id,
        FeedbackSubmission.display_order,
        FeedbackSubmission.approved_at
    ).order_by(
        FeedbackSubmission.display_order.asc().nullslast(),
        FeedbackSubmission.approved_at.desc()
    ).limit(limit).all()
    
    if not subquery:
        return []
    
    # Step 2: Fetch full announcements with eager-loaded media (single query)
    announcement_ids = [row[0] for row in subquery]
    announcements_map = {}
    
    full_announcements = db.query(FeedbackSubmission).options(
        joinedload(FeedbackSubmission.media_files),
        joinedload(FeedbackSubmission.category)
    ).filter(FeedbackSubmission.id.in_(announcement_ids)).all()
    
    for ann in full_announcements:
        announcements_map[ann.id] = ann
    
    # Build response maintaining original order
    results = []
    for row in subquery:
        ann_id, user_name_val, city_val, avg_rating, total_ratings_val = row
        ann = announcements_map.get(ann_id)
        if ann:
            results.append((ann, user_name_val, city_val, avg_rating, total_ratings_val))
    
    # Build response (DC Protocol: optimized with pre-fetched data)
    response_list = []
    for ann, user_name_value, city_value, avg_rating, total_ratings_value in results:
        avg_rating = float(avg_rating) if avg_rating else 0.0
        total_ratings_value = int(total_ratings_value) if total_ratings_value else 0
        
        approved_media = [
            build_media_response(m) for m in ann.media_files 
            if m.media_status == MediaStatus.APPROVED
        ]
        
        display_datetime = ann.approved_at or ann.last_reviewed_at or ann.submitted_at
        
        response_list.append(AnnouncementResponse(
            id=ann.id,
            title=ann.title,
            description=ann.description,
            submission_type=ann.submission_type.value,
            category=build_category_response(ann.category),
            approved_at=display_datetime,
            updated_at=display_datetime,
            is_visible=ann.is_visible,
            media=approved_media,
            user_id=ann.user_id,
            user_name=user_name_value or "Unknown",
            city=city_value,
            average_rating=round(avg_rating, 2),
            total_ratings=total_ratings_value,
            shares_count=ann.shares_count or 0,
            views_count=ann.views_count or 0,
            visible_to=getattr(ann, 'visible_to', 'both') or 'both'
        ))

    return response_list


@router.get("/public/categories", response_model=List[CategoryResponse])
async def get_public_categories(
    db: Session = Depends(get_db)
):
    """
    Get all active categories - PUBLIC endpoint (no authentication required)
    Used for announcement submission form on login page
    Only returns active categories
    """
    categories = db.query(FeedbackCategory).filter(
        FeedbackCategory.is_active == True
    ).order_by(FeedbackCategory.name).all()
    
    return [build_category_response(cat) for cat in categories]


@router.get("/public/announcement/{announcement_id}", response_model=AnnouncementResponse)
async def get_public_announcement(
    announcement_id: int,
    track_share: bool = False,  # Set to True to increment share count
    track_view: bool = False,  # Set to True to increment view count
    db: Session = Depends(get_db)
):
    """
    Get a single announcement by ID - PUBLIC endpoint (no auth required)
    Used for sharing announcements via WhatsApp, social media, etc.
    Set track_share=True to increment the share counter
    Set track_view=True to increment the view counter
    """
    from sqlalchemy import func
    from app.models.feedback import AnnouncementRating
    
    # Query with user details and ratings
    result = db.query(
        FeedbackSubmission,
        User.name.label('user_name'),
        User.city.label('city'),
        func.coalesce(func.avg(AnnouncementRating.rating), 0).label('average_rating'),
        func.count(AnnouncementRating.id).label('total_ratings')
    ).join(
        User, FeedbackSubmission.user_id == User.id
    ).outerjoin(
        AnnouncementRating, FeedbackSubmission.id == AnnouncementRating.submission_id
    ).filter(
        FeedbackSubmission.id == announcement_id,
        or_(
            FeedbackSubmission.status == SubmissionStatus.APPROVED,
            FeedbackSubmission.status == SubmissionStatus.UNDER_REVIEW
        ),
        FeedbackSubmission.is_visible == True  # Only show visible announcements publicly
    ).group_by(
        FeedbackSubmission.id,
        User.name,
        User.city
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Announcement not found or not visible")
    
    ann = result[0]
    user_name_value = result[1]
    city_value = result[2]
    avg_rating = float(result[3]) if result[3] else 0.0
    total_ratings_value = int(result[4]) if result[4] else 0
    
    # Increment counters if tracking
    if track_share:
        ann.shares_count = (ann.shares_count or 0) + 1
    if track_view:
        ann.views_count = (ann.views_count or 0) + 1
    if track_share or track_view:
        db.commit()
    
    # Only include approved media files in public response
    approved_media = [
        build_media_response(m) for m in ann.media_files 
        if m.media_status == MediaStatus.APPROVED
    ]
    
    # Use approved_at if available, otherwise last_reviewed_at, otherwise submitted_at
    display_datetime = ann.approved_at or ann.last_reviewed_at or ann.submitted_at
    
    return AnnouncementResponse(
        id=ann.id,
        title=ann.title,
        description=ann.description,
        submission_type=ann.submission_type.value,
        category=build_category_response(ann.category),
        approved_at=display_datetime,
        updated_at=display_datetime,
        is_visible=ann.is_visible,
        media=approved_media,  # Only approved media - renamed to 'media'
        user_id=ann.user_id,
        user_name=user_name_value or "Unknown",
        city=city_value,
        average_rating=round(avg_rating, 2),
        total_ratings=total_ratings_value,
        shares_count=ann.shares_count or 0,
        views_count=ann.views_count or 0
    )


# ===== Announcement Rating System =====


# ===== Public Rating Endpoint with Login =====

class RatingWithLoginRequest(BaseModel):
    username: str
    password: str
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")

@router.post("/announcement/{announcement_id}/rate")
async def rate_announcement_with_login(
    announcement_id: int,
    request: RatingWithLoginRequest,
    db: Session = Depends(get_db)
):
    """
    PUBLIC endpoint: Rate an announcement with login credentials
    - Validates user login credentials
    - Ensures one rating per user per announcement
    - Returns updated average rating
    """
    from app.core.security import SecurityManager
    from app.models.feedback import AnnouncementRating
    from sqlalchemy import func
    
    # Validate credentials
    user = db.query(User).filter(User.id == request.username).first()
    if not user or not SecurityManager.verify_password(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MNR ID or password"
        )
    
    # Check if announcement exists and is approved
    announcement = db.query(FeedbackSubmission).filter(
        FeedbackSubmission.id == announcement_id,
        FeedbackSubmission.status == SubmissionStatus.APPROVED,
        FeedbackSubmission.is_visible == True
    ).first()
    
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found or not available"
        )
    
    # Check if user has already rated this announcement
    existing_rating = db.query(AnnouncementRating).filter(
        AnnouncementRating.submission_id == announcement_id,
        AnnouncementRating.user_id == user.id
    ).first()
    
    if existing_rating:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already rated this announcement"
        )
    
    # Create new rating
    new_rating = AnnouncementRating(
        submission_id=announcement_id,
        user_id=user.id,
        rating=request.rating
    )
    db.add(new_rating)
    db.commit()
    
    # Get updated average rating
    avg_rating_result = db.query(
        func.coalesce(func.avg(AnnouncementRating.rating), 0).label('average'),
        func.count(AnnouncementRating.id).label('total')
    ).filter(
        AnnouncementRating.submission_id == announcement_id
    ).first()
    
    return {
        "success": True,
        "message": "Rating submitted successfully",
        "average_rating": round(float(avg_rating_result[0]), 2),
        "total_ratings": int(avg_rating_result[1])
    }


@router.post("/announcements/{submission_id}/rate")
async def rate_announcement(
    submission_id: int,
    rating: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Submit or update a rating for an announcement (1-5 stars)
    Users can rate each announcement once
    """
    from app.models.feedback import AnnouncementRating, FeedbackSubmission, SubmissionStatus
    
    # Validate rating value
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    # Check if announcement exists and has approved media
    submission = db.query(FeedbackSubmission).filter(
        FeedbackSubmission.id == submission_id,
        or_(
            FeedbackSubmission.status == SubmissionStatus.APPROVED,
            FeedbackSubmission.status == SubmissionStatus.UNDER_REVIEW
        )
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Check if user already rated this announcement
    existing_rating = db.query(AnnouncementRating).filter(
        AnnouncementRating.submission_id == submission_id,
        AnnouncementRating.user_id == current_user.id
    ).first()
    
    if existing_rating:
        # Update existing rating
        existing_rating.rating = rating
        existing_rating.updated_at = func.now()
        db.commit()
        message = "Rating updated successfully"
    else:
        # Create new rating
        new_rating = AnnouncementRating(
            submission_id=submission_id,
            user_id=current_user.id,
            rating=rating
        )
        db.add(new_rating)
        db.commit()
        message = "Rating submitted successfully"
    
    # Calculate new average
    avg_rating = db.query(func.avg(AnnouncementRating.rating)).filter(
        AnnouncementRating.submission_id == submission_id
    ).scalar()
    
    rating_count = db.query(func.count(AnnouncementRating.id)).filter(
        AnnouncementRating.submission_id == submission_id
    ).scalar()
    
    return {
        "message": message,
        "submission_id": submission_id,
        "your_rating": rating,
        "average_rating": round(float(avg_rating), 2) if avg_rating else 0,
        "total_ratings": rating_count
    }


@router.get("/announcements/{submission_id}/rating")
async def get_announcement_rating(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Get rating stats for an announcement and user's rating if they rated it
    """
    from app.models.feedback import AnnouncementRating
    
    # Get average rating and count
    avg_rating = db.query(func.avg(AnnouncementRating.rating)).filter(
        AnnouncementRating.submission_id == submission_id
    ).scalar()
    
    rating_count = db.query(func.count(AnnouncementRating.id)).filter(
        AnnouncementRating.submission_id == submission_id
    ).scalar()
    
    # Get user's rating if exists
    user_rating = db.query(AnnouncementRating).filter(
        AnnouncementRating.submission_id == submission_id,
        AnnouncementRating.user_id == current_user.id
    ).first()
    
    return {
        "submission_id": submission_id,
        "average_rating": round(float(avg_rating), 2) if avg_rating else 0,
        "total_ratings": rating_count or 0,
        "user_rating": user_rating.rating if user_rating else None
    }


# ===== DELETE Announcement (RVZ + Admin) =====

@router.delete("/{submission_id}")
async def delete_announcement(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Delete announcement (RVZ can delete own, Admin can delete all)
    Cascade deletes media files from database AND Object Storage
    """
    submission = db.query(FeedbackSubmission).filter(
        FeedbackSubmission.id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Access control: RVZ can delete own, Admin can delete all
    is_admin = (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) in ["Admin", "Super Admin", "Finance Admin", "General Admin"]
    is_rvz = (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) == 'RVZ ID'
    is_vgk = (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) == 'VGK ID'
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not (is_admin or is_rvz or is_vgk):
    #     raise HTTPException(status_code=403, detail="Only RVZ and Admin can delete announcements")
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (is_rvz or is_vgk) and submission.user_id != current_user.id:
    #     raise HTTPException(status_code=403, detail="You can only delete your own announcements")
    
    # Atomic delete workflow: Try storage cleanup first, rollback if fails
    storage_delete_errors = []
    storage_paths_to_delete = []
    
    # Phase 1: Collect all file paths and validate
    for media in submission.media_files:
        file_path = media.file_path
        
        # Handle Object Storage paths (/storage/...)
        if file_path.startswith("/storage/"):
            storage_path = file_path.replace("/storage/", "")
            storage_paths_to_delete.append(("storage", storage_path, media.id))
        
        # Handle legacy filesystem paths (/uploads/...)
        elif file_path.startswith("/uploads/"):
            # Security: Proper path validation to prevent directory traversal
            try:
                uploads_root = Path("uploads").resolve()
                relative_path = file_path.lstrip("/")
                target_path = (uploads_root.parent / relative_path).resolve()
                target_path.relative_to(uploads_root)  # Raises ValueError if outside uploads/
                
                if target_path.exists() and target_path.is_file():
                    storage_paths_to_delete.append(("filesystem", target_path, media.id))
                    
            except ValueError:
                logger.error(f"Path traversal attempt detected: {file_path}")
                raise HTTPException(status_code=400, detail="Invalid file path - path traversal detected")
        
        else:
            logger.warning(f"Unknown file path format: {file_path}")
    
    # Phase 2: Attempt to delete all storage files
    for storage_type, path, media_id in storage_paths_to_delete:
        try:
            if storage_type == "storage":
                storage_service.delete_file(path)
                logger.info(f"Deleted from object storage: {path}")
            elif storage_type == "filesystem":
                path.unlink()
                logger.info(f"Deleted legacy file: {path}")
        except Exception as e:
            error_msg = f"Failed to delete {storage_type} file {path}: {e}"
            logger.error(error_msg)
            storage_delete_errors.append(error_msg)
    
    # If storage cleanup had errors, log them but continue (files may already be deleted)
    if storage_delete_errors:
        logger.warning(f"Storage cleanup had {len(storage_delete_errors)} errors: {storage_delete_errors}")
    
    # Phase 3: Create audit log and delete from database
    audit_log = FeedbackApproval(
        submission_id=submission.id,
        reviewer_id=current_user.id,
        reviewer_role=(getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')).lower().replace(' ', '_'),
        action=ApprovalAction.REJECTED,  # Use REJECTED to indicate deletion
        comments=f"Announcement deleted by {(getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')))}"
    )
    db.add(audit_log)
    db.commit()
    
    # Delete submission (cascades to media and approvals via ORM)
    db.delete(submission)
    db.commit()
    
    return {
        "message": "Announcement deleted successfully",
        "submission_id": submission_id,
        "deleted_by": current_user.id
    }


# ===== Individual Media Hide/Unhide =====

@router.post("/media/{media_id}/hide")
async def hide_media(
    media_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Hide individual photo/video (Admin only)"""
    validate_admin_role(current_user)
    
    media = db.query(FeedbackMedia).filter(FeedbackMedia.id == media_id).first()
    
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    media.is_visible = False
    media.hidden_by = current_user.id
    media.hidden_at = datetime.now()
    
    db.commit()
    
    return {
        "message": "Media hidden successfully",
        "media_id": media_id,
        "is_visible": False
    }


@router.post("/media/{media_id}/unhide")
async def unhide_media(
    media_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Unhide individual photo/video (Admin only)"""
    validate_admin_role(current_user)
    
    media = db.query(FeedbackMedia).filter(FeedbackMedia.id == media_id).first()
    
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    media.is_visible = True
    media.hidden_by = None
    media.hidden_at = None
    
    db.commit()
    
    return {
        "message": "Media visible again",
        "media_id": media_id,
        "is_visible": True
    }


# ===== Production Storage Migration (Admin Only) =====

@router.post("/admin/sync-production-storage")
async def sync_production_storage(
    dry_run: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Migrate workspace files to production Object Storage (Admin only)
    Idempotent - skips already migrated files
    """
    validate_admin_role(current_user)
    
    results = {
        "migrated": [],
        "skipped": [],
        "failed": [],
        "total_processed": 0
    }
    
    # Get all media records
    all_media = db.query(FeedbackMedia).all()
    results["total_processed"] = len(all_media)
    
    for media in all_media:
        file_path = media.file_path.replace("/storage/", "")  # Remove /storage/ prefix
        
        # Check if file already exists in production storage
        if storage_service.file_exists(file_path):
            results["skipped"].append({
                "media_id": media.id,
                "path": file_path,
                "reason": "Already exists in storage"
            })
            continue
        
        # Try to migrate from workspace uploads folder
        workspace_path = Path(f"uploads/{file_path}")
        
        if not workspace_path.exists():
            results["failed"].append({
                "media_id": media.id,
                "path": file_path,
                "error": "Source file not found in workspace"
            })
            continue
        
        if dry_run:
            results["migrated"].append({
                "media_id": media.id,
                "path": file_path,
                "status": "DRY RUN - would migrate"
            })
            continue
        
        # Read and upload file
        try:
            with open(workspace_path, "rb") as f:
                file_data = f.read()
            
            success = storage_service.upload_file(file_path, file_data)
            
            if success:
                results["migrated"].append({
                    "media_id": media.id,
                    "path": file_path,
                    "size": len(file_data)
                })
                logger.info(f"Migrated to production storage: {file_path}")
            else:
                results["failed"].append({
                    "media_id": media.id,
                    "path": file_path,
                    "error": "Upload failed"
                })
        except Exception as e:
            results["failed"].append({
                "media_id": media.id,
                "path": file_path,
                "error": str(e)
            })
            logger.error(f"Migration failed for {file_path}: {e}")
    
    return {
        "message": "Storage migration complete" if not dry_run else "Dry run complete",
        "dry_run": dry_run,
        "summary": {
            "total": results["total_processed"],
            "migrated": len(results["migrated"]),
            "skipped": len(results["skipped"]),
            "failed": len(results["failed"])
        },
        "details": results
    }


# ============================================================================
# SOFT DELETE & RESTORE ENDPOINTS (Dec 2025)
# DC Protocol: RVZ Supreme only - with restore capability
# Provides BOTH soft delete (restorable) and hard delete (permanent) options
# ============================================================================

@router.delete("/announcements/{submission_id}/soft")
async def soft_delete_announcement(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: SOFT DELETE announcement (RVZ Supreme only)
    - Marks announcement as deleted (is_deleted=True)
    - Media files are preserved
    - Can be restored via restore endpoint
    """
    # Access control: Only RVZ and Admin can soft delete
    is_admin = (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) in ["Admin", "Super Admin", "Finance Admin", "General Admin"]
    is_rvz = (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) == 'RVZ ID'
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not (is_admin or is_rvz):
    #     raise HTTPException(status_code=403, detail="Only RVZ Supreme and Admin can delete announcements")
    
    submission = db.query(FeedbackSubmission).filter(
        FeedbackSubmission.id == submission_id,
        FeedbackSubmission.is_deleted == False
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    try:
        # DC Protocol: Use emp_code for staff, id for MNR users (FK constraint removed)
        actor_id = getattr(current_user, 'emp_code', None) or str(current_user.id)
        actor_type = getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')
        
        # Get media count for audit
        media_count = len(submission.media_files)
        
        # Perform soft delete
        from datetime import datetime
        now = datetime.utcnow()
        submission.is_deleted = True
        submission.deleted_at = now
        submission.deleted_by = actor_id
        
        # Create audit log
        audit_log = FeedbackApproval(
            submission_id=submission.id,
            reviewer_id=actor_id,
            reviewer_role=actor_type.lower().replace(' ', '_') if actor_type else 'unknown',
            action=ApprovalAction.REJECTED,
            comments=f"SOFT DELETE by {actor_id} ({actor_type}) - Can be restored"
        )
        db.add(audit_log)
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Announcement '{submission.title}' soft deleted successfully",
            "deleted_id": submission_id,
            "can_restore": True,
            "media_preserved": media_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to soft delete announcement: {str(e)}"
        )


@router.post("/announcements/{submission_id}/restore")
async def restore_announcement(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: RESTORE soft-deleted announcement (VGK4U Supreme MR10001, RVZ, Admin only)
    """
    # Access control: Only VGK4U Supreme (emp_code=MR10001), RVZ and Admin can restore
    staff_type = getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')
    emp_code = getattr(current_user, 'emp_code', '')
    is_admin = staff_type in ["Admin", "Super Admin", "Finance Admin", "General Admin"]
    is_rvz = staff_type == 'RVZ ID'
    is_vgk4u_supreme = emp_code == 'MR10001'  # DC: Check emp_code, not staff_type
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not (is_admin or is_rvz or is_vgk4u_supreme):
    #     raise HTTPException(status_code=403, detail="Only VGK4U Supreme (MR10001), RVZ, and Admin can restore announcements")
    
    submission = db.query(FeedbackSubmission).filter(
        FeedbackSubmission.id == submission_id,
        FeedbackSubmission.is_deleted == True
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Deleted announcement not found")
    
    try:
        # DC Protocol: Use emp_code for staff, id for MNR users (FK constraint removed)
        actor_id = getattr(current_user, 'emp_code', None) or str(current_user.id)
        actor_type = getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')
        
        # Store old values for audit
        old_deleted_at = submission.deleted_at
        old_deleted_by = submission.deleted_by
        
        # Restore announcement
        submission.is_deleted = False
        submission.deleted_at = None
        submission.deleted_by = None
        
        # Create audit log
        audit_log = FeedbackApproval(
            submission_id=submission.id,
            reviewer_id=actor_id,
            reviewer_role=actor_type.lower().replace(' ', '_') if actor_type else 'unknown',
            action=ApprovalAction.APPROVED,
            comments=f"RESTORED by {actor_id} ({actor_type})"
        )
        db.add(audit_log)
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Announcement '{submission.title}' restored successfully",
            "restored_id": submission_id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restore announcement: {str(e)}"
        )


@router.get("/announcements/deleted")
async def list_deleted_announcements(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: List all soft-deleted announcements (VGK4U Supreme MR10001, RVZ, Admin only)
    """
    # Access control: Only VGK4U Supreme (emp_code=MR10001), RVZ and Admin can view deleted
    staff_type = getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')
    emp_code = getattr(current_user, 'emp_code', '')
    is_admin = staff_type in ["Admin", "Super Admin", "Finance Admin", "General Admin"]
    is_rvz = staff_type == 'RVZ ID'
    is_vgk4u_supreme = emp_code == 'MR10001'  # DC: Check emp_code, not staff_type
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not (is_admin or is_rvz or is_vgk4u_supreme):
    #     raise HTTPException(status_code=403, detail="Only VGK4U Supreme (MR10001), RVZ, and Admin can view deleted announcements")
    
    deleted_submissions = db.query(FeedbackSubmission).filter(
        FeedbackSubmission.is_deleted == True
    ).order_by(FeedbackSubmission.deleted_at.desc()).all()
    
    return {
        "success": True,
        "count": len(deleted_submissions),
        "announcements": [
            {
                "id": sub.id,
                "title": sub.title,
                "status": sub.status.value if hasattr(sub.status, 'value') else str(sub.status),
                "submission_type": sub.submission_type.value if hasattr(sub.submission_type, 'value') else str(sub.submission_type),
                "media_count": len(sub.media_files),
                "deleted_at": sub.deleted_at.isoformat() if sub.deleted_at else None,
                "deleted_by": sub.deleted_by
            }
            for sub in deleted_submissions
        ]
    }


@router.delete("/announcements/{submission_id}/hard")
async def hard_delete_announcement(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: HARD DELETE announcement (VGK4U Supreme MR10001, RVZ, Admin only)
    - PERMANENTLY removes announcement from database
    - Also deletes media files from storage
    - CANNOT be restored - use with caution
    """
    # Access control: Only VGK4U Supreme (emp_code=MR10001), RVZ and Admin can hard delete
    staff_type = getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')
    emp_code = getattr(current_user, 'emp_code', '')
    is_admin = staff_type in ["Admin", "Super Admin", "Finance Admin", "General Admin"]
    is_rvz = staff_type == 'RVZ ID'
    is_vgk4u_supreme = emp_code == 'MR10001'  # DC: Check emp_code, not staff_type
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not (is_admin or is_rvz or is_vgk4u_supreme):
    #     raise HTTPException(status_code=403, detail="Only VGK4U Supreme (MR10001), RVZ, and Admin can permanently delete announcements")
    
    # Check both active and soft-deleted announcements
    submission = db.query(FeedbackSubmission).filter(
        FeedbackSubmission.id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    try:
        # Store info for response
        title = submission.title
        media_count = len(submission.media_files)
        
        # Delete media files from storage
        storage_delete_errors = []
        for media in submission.media_files:
            file_path = media.file_path
            try:
                if file_path.startswith("/storage/"):
                    storage_path = file_path.replace("/storage/", "")
                    storage_service.delete_file(storage_path)
                    logger.info(f"Deleted from object storage: {storage_path}")
            except Exception as e:
                storage_delete_errors.append(f"{file_path}: {str(e)}")
                logger.error(f"Failed to delete {file_path}: {e}")
        
        # DC Protocol: Use emp_code for staff, id for MNR users (FK constraint removed)
        actor_id = getattr(current_user, 'emp_code', None) or str(current_user.id)
        actor_type = getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')
        
        # Create audit log before deletion
        audit_log = FeedbackApproval(
            submission_id=submission.id,
            reviewer_id=actor_id,
            reviewer_role=actor_type.lower().replace(' ', '_') if actor_type else 'unknown',
            action=ApprovalAction.REJECTED,
            comments=f"HARD DELETE (PERMANENT) by {actor_id} ({actor_type})"
        )
        db.add(audit_log)
        db.commit()
        
        # Permanently delete submission (cascades to media and approvals)
        db.delete(submission)
        db.commit()
        
        return {
            "success": True,
            "message": f"Announcement '{title}' permanently deleted",
            "deleted_id": submission_id,
            "can_restore": False,
            "media_deleted": media_count,
            "storage_errors": storage_delete_errors if storage_delete_errors else None
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to hard delete announcement: {str(e)}"
        )
