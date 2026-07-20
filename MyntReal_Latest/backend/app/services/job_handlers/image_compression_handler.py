"""
Image Compression Job Handler
Processes image compression jobs in background thread pool
DC Protocol: Complete audit trail with dual evidence (original + compressed paths)
WVV Protocol: Status tracking, error handling, quality validation
"""

import logging
import traceback
from pathlib import Path
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.staff_tasks import StaffTaskAttachment, StaffTaskAttachmentAudit
from app.models.background_jobs import BackgroundJob
from app.services.background_job_service import BackgroundJobService
from app.services.image_compression_service import ImageCompressionService, ImageCompressionError

logger = logging.getLogger(__name__)


def process_image_compression_job(job_id: int):
    """
    Process image compression job (executed in APScheduler thread pool)
    DC Protocol: Complete audit trail with dual evidence preservation
    WVV Protocol: Status tracking, retry logic, error handling
    
    ARCHITECTURE: Fully synchronous - no async/await (APScheduler ThreadPoolExecutor requirement)
    
    Args:
        job_id: Background job ID from background_jobs table
    
    Job Data Expected:
        - attachment_id: StaffTaskAttachment ID
        - original_path: Path to original image file
        - uploaded_by: Employee ID who uploaded (DC: attribution)
    """
    # DC: Create new database session (CRITICAL: Detached from request session)
    db = SessionLocal()
    
    try:
        # Get job record
        job = BackgroundJobService.get_job_by_id(db, job_id)
        if not job:
            logger.error(f"[COMPRESSION JOB] Job {job_id} not found")
            return
        
        # WVV: Mark job as processing
        job = BackgroundJobService.mark_job_processing(db, job_id)
        if not job:
            logger.error(f"[COMPRESSION JOB] Failed to mark job {job_id} as processing")
            return
        
        # Extract job data
        attachment_id = job.job_data.get('attachment_id')
        original_path_str = job.job_data.get('original_path')
        uploaded_by = job.job_data.get('uploaded_by')  # DC: Employee attribution
        
        if not all([attachment_id, original_path_str, uploaded_by]):
            error_msg = f"Missing required job data: attachment_id={attachment_id}, uploaded_by={uploaded_by}"
            logger.error(f"[COMPRESSION JOB] {error_msg}")
            BackgroundJobService.mark_job_failed(db, job_id, error_msg)
            return
        
        original_path = Path(original_path_str)
        
        logger.info(f"[COMPRESSION JOB] Processing attachment {attachment_id}, file: {original_path.name}")
        
        # Get attachment record
        attachment = db.query(StaffTaskAttachment).filter(
            StaffTaskAttachment.id == attachment_id
        ).first()
        
        if not attachment:
            error_msg = f"Attachment {attachment_id} not found in database"
            logger.error(f"[COMPRESSION JOB] {error_msg}")
            BackgroundJobService.mark_job_failed(db, job_id, error_msg)
            return
        
        # Verify original file exists
        if not original_path.exists():
            error_msg = f"Original file not found: {original_path}"
            logger.error(f"[COMPRESSION JOB] {error_msg}")
            BackgroundJobService.mark_job_failed(db, job_id, error_msg)
            
            # Update attachment status
            attachment.processing_status = 'failed'
            db.commit()
            return
        
        # Perform compression (SYNCHRONOUS - no await!)
        try:
            # Use synchronous compression method
            compressed_path, metadata = ImageCompressionService.compress_image(original_path)
            
            # DC PROTOCOL: Create audit record with ALL required metadata (24 DC-compliant columns)
            uploaded_ip = job.job_data.get('uploaded_ip', None)
            uploaded_device = job.job_data.get('uploaded_device', None)
            
            audit_record = StaffTaskAttachmentAudit(
                attachment_id=attachment_id,
                # Original File Metadata (DC: Immutable Evidence)
                original_filename=original_path.name,
                original_size_bytes=metadata['original_size'],
                original_checksum=metadata['original_checksum'],  # SHA-256
                original_dimensions=None,  # TODO: Extract image dimensions in future
                # Compressed File Metadata
                compressed_size_bytes=metadata['compressed_size'],
                compressed_checksum=metadata['compressed_checksum'],  # CRITICAL: SHA-256 of compressed file
                compressed_dimensions=None,  # TODO: Extract compressed dimensions
                compression_ratio=metadata['compression_ratio'],
                compression_quality=metadata.get('quality', None),  # JPEG quality if available
                # Quality Metrics (WVV: Verification)
                ssim_score=metadata['ssim_score'],
                processing_method=metadata['processing_method'],
                processing_duration_ms=metadata['processing_duration_ms'],
                # Storage Tier Tracking (DC: Audit Trail)
                storage_tier='hot',  # Starts in hot storage
                archived_at=None,  # NULL until cold archiving (future feature)
                archived_by=None,
                archive_reason=None,
                retrieval_count=0,  # Initialize at 0
                last_retrieved_at=None,
                # DC: Employee Attribution
                uploaded_by=uploaded_by,
                uploaded_ip=uploaded_ip,
                uploaded_device=uploaded_device
            )
            
            db.add(audit_record)
            db.flush()
            
            # DC PROTOCOL: Dual evidence preservation + Checksums (self-contained verification)
            # - file_path = ORIGINAL (IMMUTABLE, never changes)
            # - file_size = ORIGINAL SIZE (IMMUTABLE, never changes)
            # - original_checksum = SHA-256 of original (IMMUTABLE, architect-mandated)
            # - compressed_path = COMPRESSED (new optimized version)
            # - compressed_size_bytes = COMPRESSED SIZE (mutable)
            # - compressed_checksum = SHA-256 of compressed (mutable, architect-mandated)
            attachment.compressed_path = str(compressed_path)
            attachment.compressed_size_bytes = metadata['compressed_size']
            attachment.compressed_checksum = metadata['compressed_checksum']  # DC: Store checksum on primary record
            attachment.has_compressed = True
            attachment.processing_status = 'completed'
            # NOTE: file_size and original_checksum remain UNCHANGED (immutable evidence per DC Protocol)
            
            db.commit()
            
            logger.info(f"[COMPRESSION JOB] ✅ Completed attachment {attachment_id}: "
                       f"{metadata['original_size']/1024:.2f}KB → {metadata['compressed_size']/1024:.2f}KB "
                       f"(SSIM: {metadata['ssim_score']:.4f})")
            
            # Mark job as completed with result metadata
            result = {
                'attachment_id': attachment_id,
                'original_size': metadata['original_size'],
                'compressed_size': metadata['compressed_size'],
                'compression_ratio': metadata['compression_ratio'],
                'ssim_score': metadata['ssim_score'],
                'compressed_path': str(compressed_path)
            }
            
            BackgroundJobService.mark_job_completed(db, job_id, result)
            
        except ImageCompressionError as e:
            # Compression failed - keep original file (DC: preserve evidence)
            error_msg = f"Image compression failed: {str(e)}"
            error_traceback = traceback.format_exc()
            
            logger.error(f"[COMPRESSION JOB] {error_msg}")
            logger.debug(f"[COMPRESSION JOB] Traceback: {error_traceback}")
            
            # Update attachment status
            attachment.processing_status = 'failed'
            db.commit()
            
            # WVV: Mark job as failed (will retry if attempts < max_attempts)
            BackgroundJobService.mark_job_failed(db, job_id, error_msg, error_traceback)
            
    except Exception as e:
        # Unexpected error - log and mark job as failed
        error_msg = f"Unexpected error processing compression job: {str(e)}"
        error_traceback = traceback.format_exc()
        
        logger.error(f"[COMPRESSION JOB] {error_msg}")
        logger.debug(f"[COMPRESSION JOB] Traceback: {error_traceback}")
        
        # Mark job as failed
        try:
            BackgroundJobService.mark_job_failed(db, job_id, error_msg, error_traceback)
        except:
            logger.error(f"[COMPRESSION JOB] Failed to update job status for job {job_id}")
    
    finally:
        # Always close database session
        db.close()
