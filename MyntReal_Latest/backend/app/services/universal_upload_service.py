"""
Universal Upload Service
DC Protocol: Works with ANY table - MNR & Staff uploads
WVV Protocol: 5MB images, 500KB documents, auto-compression, dual storage

FEATURES:
- Unified 5MB upload limit for images
- Automatic background compression to <500KB
- Dual evidence storage (original + compressed)
- Real-time progress support
- Complete audit trail
- Works with any database table

USAGE:
    result = await UniversalUploadService.handle_upload(
        file=uploaded_file,
        table_name="staff_task_attachments",
        record_id=task_id,
        uploaded_by_id=user.id,
        uploaded_by_type="staff",  # 'staff' or 'user'
        storage_dir="task_attachments",
        db=db_session
    )
"""

import hashlib
import logging
import uuid
import re
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple
from fastapi import UploadFile, HTTPException
from app.services.object_storage import storage_service

logger = logging.getLogger(__name__)


class UniversalUploadService:
    """
    Universal file upload service for ALL upload locations
    DC Protocol: Standardized upload handling with dual evidence
    WVV Protocol: File validation, size limits, type checking
    """
    
    # File size limits (WVV: Standardized across platform)
    MAX_IMAGE_SIZE = 5 * 1024 * 1024      # 5MB for images (will be auto-compressed)
    MAX_DOCUMENT_SIZE = 20 * 1024 * 1024  # 20MB for documents/PDFs (downloadable brochures)
    MAX_VIDEO_SIZE = 20 * 1024 * 1024     # 20MB for videos (will be compressed via ffmpeg)
    
    # Allowed file types
    IMAGE_MIME_TYPES = {
        'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
        'image/webp', 'image/bmp', 'image/tiff',
        'image/heic', 'image/heif',
    }
    
    VIDEO_MIME_TYPES = {
        'video/mp4', 'video/webm', 'video/quicktime', 
        'video/x-msvideo', 'video/avi', 'video/x-matroska', 'video/mkv'
    }
    
    DOCUMENT_MIME_TYPES = {
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'text/plain',
        'text/csv'
    }
    
    ALL_ALLOWED_TYPES = IMAGE_MIME_TYPES | VIDEO_MIME_TYPES | DOCUMENT_MIME_TYPES
    
    # DC Protocol: Functional Segment Codes (NEW - Nov 29, 2025)
    SEGMENT_CODES = {
        # KYC Documents (User + Staff) - Legacy + New Keys
        'mnr_kyc': 'KYC',
        'staff_kyc': 'KYC',
        'kyc_document': 'KYC',      # NEW: MNR KYC Documents (profile.py)
        # Profile Photos (User + Staff) - Legacy + New Keys
        'mnr_profile': 'PROFILE',
        'staff_profile': 'PROFILE',
        'profile_photo': 'PROFILE',  # NEW: MNR Profile Photos (profile.py)
        # Task Management (Attachments + Comments) - Legacy + New Keys
        'task_attachment': 'TASK',
        'comment_attachment': 'TASK',
        'staff_task': 'TASK',        # NEW: Staff Task Attachments (staff_tasks.py)
        # Journey Tracking - Legacy + New Keys
        'journey_photo': 'JOURNEY',
        'staff_journey': 'JOURNEY',  # NEW: Staff Journey Photos (staff_journeys.py)
        # Feedback/Announcements
        'feedback_media': 'FEEDBACK',
        # Payment Processing
        'payment_screenshot': 'PAYMENT',
        # Expense Management (Regular + RVZ)
        'expense_bill': 'EXPENSE',
        'rvz_expense': 'EXPENSE',
        # Support Tickets
        'ticket_attachment': 'TICKET',
        # Attendance Evidence (WVV Protocol)
        'attendance_evidence': 'SAE',
        # Real Dreams - Real Estate Marketplace (Dec 08, 2025)
        'rd_property': 'RDPROP',
        'rd_partner': 'RDPART',
        # Stock Item Images (Jan 2026)
        'stock_item_image': 'STOCK',
        # Solar Lead Documents (Mar 2026)
        'solar_doc': 'SOLDOC',
    }
    
    # DC Protocol: Entity Type Prefixes (NEW - Nov 29, 2025)
    ENTITY_PREFIXES = {
        # User Entities
        'mnr_user': 'U',        # User 123 → U123
        'user': 'U',            # NEW: Generic user reference (profile.py, users.py)
        # Staff Entities
        'staff_employee': 'S',  # Staff 4 → S4
        'staff': 'S',           # NEW: Generic staff reference (staff_employees.py, staff_journeys.py)
        # Task Management
        'task': 'T',            # Task 40 → T40
        'comment': 'CMT',       # Comment 156 → CMT156
        # Journey Tracking
        'journey': 'J',         # Journey 67 → J67
        # Feedback/Announcements
        'feedback': 'F',        # Feedback 31 → F31
        # Payment Processing
        'payment': 'PAY',       # Payment 456 → PAY456
        # Expense Management
        'expense': 'EXP',       # Expense 89 → EXP89
        'rvz_expense': 'RVZEXP', # RVZ Expense 12 → RVZEXP12
        # Support Tickets
        'ticket': 'TKT',        # Ticket 234 → TKT234
        # Attendance Evidence
        'attendance': 'ATT',    # Attendance 12 → ATT12
        # Real Dreams - Real Estate
        'property': 'PROP',     # Property 123 → PROP123
        'rd_partner': 'PART',   # Partner 45 → PART45
        # Stock Items
        'stock_item': 'STK',    # Stock Item 56 → STK56
        # CRM Leads
        'crm_lead': 'CRM',      # CRM Lead 123 → CRM123
    }
    
    # Storage root directory (for compressed/small files)
    # DC Protocol Fix: Use absolute path to ensure correct location regardless of working directory
    STORAGE_ROOT = Path(__file__).parent.parent.parent.parent / "frontend" / "storage"
    
    # Storage thresholds (DC Protocol - Jan 23, 2026: Force ALL files to Object Storage)
    # CRITICAL: Local storage gets wiped on redeploy, causing 404 errors
    OBJECT_STORAGE_THRESHOLD = 0  # ALL files go to Object Storage (prevents 404 on redeploy)
    LOCAL_STORAGE_THRESHOLD = 0   # No files stay local
    
    @classmethod
    def validate_file_type(cls, file: UploadFile, allow_videos: bool = False) -> str:
        """
        Validate file type and return category
        WVV: Type validation before upload
        
        Args:
            file: Uploaded file
            allow_videos: Whether to accept video files (default: False)
        
        Returns: 'image', 'video', or 'document'
        Raises: HTTPException if invalid type
        """
        content_type = file.content_type
        
        if content_type in cls.IMAGE_MIME_TYPES:
            return 'image'
        elif content_type in cls.VIDEO_MIME_TYPES:
            if not allow_videos:
                raise HTTPException(
                    status_code=400,
                    detail="Video files are not allowed for this upload type"
                )
            return 'video'
        elif content_type in cls.DOCUMENT_MIME_TYPES:
            return 'document'
        else:
            allowed_types = "Images, Documents"
            if allow_videos:
                allowed_types += ", Videos"
            raise HTTPException(
                status_code=400,
                detail=f"File type '{content_type}' not allowed. Allowed: {allowed_types}"
            )
    
    @classmethod
    def validate_file_size(cls, file_content: bytes, file_type: str, filename: str) -> int:
        """
        Validate file size based on type
        WVV: Size validation with clear error messages
        
        Returns: File size in bytes
        Raises: HTTPException if too large
        """
        file_size = len(file_content)
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        if file_type == 'image' and file_size < 5 * 1024:
            raise HTTPException(status_code=400, detail=f"Image file is too small ({file_size} bytes). Please upload a proper photo (minimum 5KB).")
        
        if file_type == 'image':
            max_size = cls.MAX_IMAGE_SIZE
            max_size_label = "5MB"
        elif file_type == 'video':
            max_size = cls.MAX_VIDEO_SIZE
            max_size_label = "20MB"
        else:
            max_size = cls.MAX_DOCUMENT_SIZE
            max_size_label = "20MB"
        
        if file_size > max_size:
            size_mb = file_size / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"File '{filename}' ({size_mb:.2f}MB) exceeds maximum size for {file_type}s ({max_size_label})"
            )
        
        return file_size
    
    @classmethod
    def calculate_checksum(cls, file_content: bytes) -> str:
        """
        Calculate SHA-256 checksum
        DC: File integrity verification
        """
        return hashlib.sha256(file_content).hexdigest()
    
    @classmethod
    def generate_download_filename(
        cls,
        segment_key: str,
        entity_type: str,
        entity_id: int,
        attachment_id: int,
        uploader_code: str,
        original_filename: str,
        uploaded_at: datetime
    ) -> str:
        """
        Generate DC/WVV compliant download filename
        
        Format: {SEGMENT}_{ENTITY_ID}_{ATTACHMENT_ID}_{TIMESTAMP}_{UPLOADER}_{ORIGINAL}
        Example: TASK_T40_00024_20251129_063020_MR10009_screenshot.png
        
        DC PROTOCOL:
        - Immutable after generation
        - Includes full audit context (segment, entity, uploader, time)
        - Filesystem-safe characters only
        - Max length: 255 chars (OS compatibility)
        
        Args:
            segment_key: Functional segment ('task_attachment', 'mnr_kyc', etc.)
            entity_type: Entity type ('task', 'mnr_user', 'staff_employee', etc.)
            entity_id: Entity ID (40, 123, etc.)
            attachment_id: Unique attachment ID
            uploader_code: Employee code (MR10009) or Member code (MR10025)
            original_filename: User's uploaded filename
            uploaded_at: Upload timestamp (IST)
            
        Returns:
            Formatted filename string
            
        Raises:
            HTTPException: If segment_key or entity_type not recognized (audit compliance)
        """
        # DC PROTOCOL: Hard-fail on UNKNOWN segments (prevents audit trail corruption)
        # WVV: Validate metadata before filename generation
        if segment_key not in cls.SEGMENT_CODES:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid segment_key '{segment_key}' - must be one of: {', '.join(cls.SEGMENT_CODES.keys())}"
            )
        
        if entity_type not in cls.ENTITY_PREFIXES:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid entity_type '{entity_type}' - must be one of: {', '.join(cls.ENTITY_PREFIXES.keys())}"
            )
        
        # WVV: Validate required parameters
        if not uploader_code or not uploader_code.strip():
            raise HTTPException(
                status_code=500,
                detail="uploader_code is required for download filename generation"
            )
        
        if not original_filename or not original_filename.strip():
            raise HTTPException(
                status_code=500,
                detail="original_filename is required for download filename generation"
            )
        
        # Get functional segment code (guaranteed valid)
        segment_code = cls.SEGMENT_CODES[segment_key]
        
        # Get entity prefix (guaranteed valid)
        entity_prefix = cls.ENTITY_PREFIXES[entity_type]
        
        # Format entity ID with prefix (guaranteed non-empty)
        entity_id_str = f"{entity_prefix}{entity_id}"
        
        # Format timestamp (IST, filesystem-safe)
        # DC: Use YYYYMMDD_HHMMSS format (sortable, no special chars)
        timestamp = uploaded_at.strftime('%Y%m%d_%H%M%S')
        
        # Sanitize original filename
        # DC: Keep extension, sanitize name, limit length
        original_name, ext = os.path.splitext(original_filename)
        
        # WVV: Remove unsafe characters (keep only alphanumeric, underscore, dash)
        sanitized_name = re.sub(r'[^a-zA-Z0-9_-]', '_', original_name)
        
        # WVV: Trim to reasonable length (leave room for other components)
        sanitized_name = sanitized_name[:50]
        
        # DC: Normalize extension (lowercase, max 10 chars)
        sanitized_ext = ext.lower()[:10] if ext else ''
        
        # WVV: Sanitize uploader code (alphanumeric only)
        safe_uploader = re.sub(r'[^a-zA-Z0-9]', '_', uploader_code)[:20]
        
        # Build filename
        # Format: {SEGMENT}_{ENTITY_ID}_{ATTACHMENT_ID}_{TIMESTAMP}_{UPLOADER}_{ORIGINAL}
        download_name = (
            f"{segment_code}_"
            f"{entity_id_str}_"
            f"{attachment_id:05d}_"  # DC: 5-digit padding (00024, 00156)
            f"{timestamp}_"
            f"{safe_uploader}_"
            f"{sanitized_name}{sanitized_ext}"
        )
        
        # DC: Enforce max length (filesystem safety across all OS)
        if len(download_name) > 255:
            # Truncate original name to fit
            overflow = len(download_name) - 255
            max_original_len = max(len(sanitized_name) - overflow, 10)
            sanitized_name = sanitized_name[:max_original_len]
            
            # Rebuild with truncated name
            download_name = (
                f"{segment_code}_{entity_id_str}_{attachment_id:05d}_"
                f"{timestamp}_{safe_uploader}_{sanitized_name}{sanitized_ext}"
            )
        
        return download_name
    
    @classmethod
    async def handle_upload(
        cls,
        file: UploadFile,
        table_name: str,
        record_id: int,
        uploaded_by_id: int,
        uploaded_by_type: str,  # 'staff' or 'user'
        storage_dir: str,
        db,
        emp_code: Optional[str] = None,  # For staff uploads
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None,
        allow_videos: bool = False,  # NEW: Enable video uploads (20MB limit)
        defer_scheduler: bool = False  # DC: Defer APScheduler until after caller commits
    ) -> Dict:
        """
        Handle file upload with validation, storage, and compression queue
        DC Protocol: Complete upload flow with audit trail
        WVV Protocol: Validation at every step
        
        Args:
            file: Uploaded file from FastAPI
            table_name: Database table name (e.g., 'kyc_documents', 'staff_task_attachments')
            record_id: ID of the parent record
            uploaded_by_id: User or Staff ID
            uploaded_by_type: 'staff' or 'user'
            storage_dir: Subdirectory under frontend/storage/ (e.g., 'kyc_documents', 'task_attachments')
            db: Database session
            emp_code: Employee code (for staff uploads)
            ip_address: Uploader IP (optional)
            device_info: Device info (optional)
        
        Returns:
            Dict with upload metadata:
            {
                'file_path': str,
                'file_name': str,
                'file_size': int,
                'file_type': str,
                'original_checksum': str,
                'needs_compression': bool,
                'compression_job_id': Optional[int]
            }
        """
        # VERIFY: File type
        file_type = cls.validate_file_type(file, allow_videos=allow_videos)
        
        # VERIFY: Read file content
        file_content = await file.read()
        
        # VERIFY: File size
        file_size = cls.validate_file_size(file_content, file_type, file.filename)
        
        # VERIFY: Calculate checksum
        original_checksum = cls.calculate_checksum(file_content)
        
        logger.info(f"[UPLOAD] {file.filename} ({file_size/1024:.2f}KB) → {table_name}:{record_id}")
        
        # DC PROTOCOL: Dual Storage Architecture
        # Large files (≥10MB, esp. 20MB videos) → Object Storage (durable, scalable)
        # Small files (<10MB) → Local Storage (fast access for previews)
        
        file_extension = Path(file.filename).suffix
        unique_filename = f"{record_id}_{uuid.uuid4().hex}{file_extension}"
        use_object_storage = file_size >= cls.OBJECT_STORAGE_THRESHOLD
        
        # DC PROTOCOL: Dual Storage Architecture with proper metadata
        if use_object_storage:
            # LARGE FILES: Save to Object Storage
            object_key = f"{storage_dir}/{unique_filename}"  # Pure storage key (no prefix)
            success = storage_service.upload_file(object_key, file_content)
            
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to upload file to object storage"
                )
            
            # Store BOTH for DB: file_path stays clean, metadata stores storage details
            file_path_str = object_key  # Clean path without prefix
            storage_type = 'object_storage'
            storage_key = object_key
            logger.info(f"[UPLOAD] Saved to OBJECT STORAGE: {object_key} ({file_size/1024/1024:.2f}MB)")
            
        else:
            # SMALL FILES: Save to Local Storage
            upload_dir = cls.STORAGE_ROOT / storage_dir
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = upload_dir / unique_filename
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            # DC Protocol Fix (Nov 29, 2025): Store CLEAN path without frontend/storage/ prefix
            # This matches Object Storage format and works with normalize_media_path()
            # Before: "frontend/storage/feedback_media/36_uuid.png" (broken - causes double path)
            # After: "feedback_media/36_uuid.png" (clean - works correctly)
            file_path_str = f"{storage_dir}/{unique_filename}"
            storage_type = 'local'
            storage_key = None  # No storage key for local files
            logger.info(f"[UPLOAD] Saved to LOCAL STORAGE: {file_path} → DB path: {file_path_str} ({file_size/1024:.2f}KB)")
        
        # DC: Determine if compression needed
        needs_compression = (file_type in ['image', 'video'])
        compression_job_id = None
        job_scheduler_params = None  # DC: For deferred scheduling
        
        if needs_compression:
            # Queue compression job
            from app.services.background_job_service import BackgroundJobService
            from app.services.job_handlers.universal_compression_handler import process_universal_compression_job
            from app.core.scheduler import enqueue_background_job
            
            job_data = {
                'table_name': table_name,
                'record_id': record_id,
                'original_path': file_path_str,
                'storage_type': storage_type,  # 'local' or 'object_storage'
                'storage_key': storage_key,  # Actual object storage key (if object_storage)
                'original_checksum': original_checksum,  # DC: SHA-256 before compression
                'uploaded_by_id': uploaded_by_id,
                'uploaded_by_type': uploaded_by_type,
                'emp_code': emp_code,
                'uploaded_ip': ip_address,
                'uploaded_device': device_info
            }
            
            # Create job record in database (within caller's transaction)
            # DC: Use 'universal_media_compression' for both images and videos
            # DC Protocol: Handler metadata auto-populated by BackgroundJobService
            
            # DC Protocol Fix (Nov 29, 2025): Safe integer conversion for created_by
            # User IDs are strings (MNR IDs like "MNR1800143"), Staff IDs are integers
            # background_jobs.created_by is INTEGER, so convert safely
            created_by_value = None
            if uploaded_by_id is not None:
                try:
                    created_by_value = int(uploaded_by_id)
                except (ValueError, TypeError):
                    created_by_value = None  # String IDs (MNR IDs) → None (audit info in job_data)
                    logger.debug(f"[UPLOAD] Non-integer uploaded_by_id '{uploaded_by_id}' - using None for created_by")
            
            job = BackgroundJobService.enqueue_job(
                db=db,
                job_type='universal_media_compression',  # Changed from 'universal_image_compression'
                job_key=f'universal_compress_{table_name}_{record_id}_{uuid.uuid4().hex[:8]}',
                job_data=job_data,
                created_by=created_by_value,
                created_ip=ip_address,
                priority=5,
                max_attempts=3
            )
            
            compression_job_id = job.id
            
            # DC: Defer APScheduler enqueueing if requested (for transaction safety)
            if defer_scheduler:
                # Return SERIALIZABLE job parameters for caller to schedule AFTER commit
                # DC: Function path instead of callable (JSON-safe, no serialization errors)
                job_scheduler_params = {
                    'job_func_module': 'app.services.job_handlers.universal_compression_handler',
                    'job_func_name': 'process_universal_compression_job',
                    'scheduler_job_id': f'exec_compress_{job.id}',
                    'background_job_id': job.id  # DB record ID for job handler
                }
                logger.info(f"[UPLOAD] Created compression job {compression_job_id} for {file.filename} (scheduler deferred)")
            else:
                # Legacy: Immediate scheduling (not transaction-safe!)
                enqueue_background_job(
                    job_func=process_universal_compression_job,
                    job_id=f'exec_compress_{job.id}',
                    args=[job.id]
                )
                logger.info(f"[UPLOAD] Queued compression job {compression_job_id} for {file.filename}")
        
        return {
            'file_path': file_path_str,  # Clean path (no prefix)
            'storage_type': storage_type,  # 'local' or 'object_storage'
            'storage_key': storage_key,  # Object storage key (if object_storage) or None
            'file_name': unique_filename,
            'original_filename': file.filename,
            'file_size': file_size,
            'file_type': file.content_type,
            'original_checksum': original_checksum,  # DC: SHA-256 before processing
            'needs_compression': needs_compression,
            'compression_job_id': compression_job_id,
            'job_scheduler_params': job_scheduler_params  # DC: Deferred scheduler parameters (or None)
        }
    
    @classmethod
    def get_storage_path(cls, storage_dir: str) -> Path:
        """Get full path to storage directory"""
        return cls.STORAGE_ROOT / storage_dir
    
    @classmethod
    def delete_file(cls, file_path: str) -> bool:
        """
        Delete file from storage
        DC: Safe deletion with error handling
        
        Returns: True if deleted, False if file not found
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"[DELETE] Removed file: {file_path}")
                return True
            else:
                logger.warning(f"[DELETE] File not found: {file_path}")
                return False
        except Exception as e:
            logger.error(f"[DELETE] Failed to delete {file_path}: {str(e)}")
            return False
