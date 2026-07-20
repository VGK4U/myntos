"""
Universal Media Compression Job Handler
DC Protocol: Works with ANY table - processes compression jobs for all upload locations
WVV Protocol: Table-agnostic compression with complete audit trail

ARCHITECTURE:
- Synchronous processing (APScheduler ThreadPoolExecutor requirement)
- Dynamic table/column updates based on job_data
- Reuses ImageCompressionService for images
- Reuses VideoCompressionService for videos
- Creates audit records in universal format

SUPPORTED TABLES:
- kyc_documents (MNR user KYC)
- feedback_media (Announcements/Feedback - SUPPORTS VIDEOS)
- staff_task_attachments (Staff tasks)
- staff_employee_kyc documents (Staff KYC)
- staff_journeys (Journey photos)
- ... and any future upload table
"""

import logging
import traceback
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import text
import mimetypes

from app.core.database import SessionLocal
from app.models.background_jobs import BackgroundJob
from app.services.background_job_service import BackgroundJobService
from app.services.image_compression_service import ImageCompressionService, ImageCompressionError
from app.services.video_compression_service import VideoCompressionService, VideoCompressionError
from app.services.object_storage import storage_service

logger = logging.getLogger(__name__)


def download_original_file(
    storage_type: str, 
    storage_key: str, 
    original_checksum: str,
    expected_size: int = None
) -> tuple[Path, bool]:
    """
    DC Protocol: Safe download with validation
    Download original file from object storage or local storage with:
    - Buffered write with flush+fsync
    - Checksum validation before compression
    
    Args:
        storage_type: 'local' or 'object_storage'
        storage_key: Object storage key OR local file path
        original_checksum: Expected SHA-256 checksum
        expected_size: Expected file size in bytes (optional)
        
    Returns:
        Tuple of (local_file_path, is_temp_file)
    """
    import hashlib
    
    if storage_type == 'object_storage':
        # Download from object storage to temp file with validation
        file_data = storage_service.download_file(storage_key)
        
        if not file_data:
            raise Exception(f"Failed to download from object storage: {storage_key}")
        
        # DC Protocol: Validate size before writing
        if expected_size and len(file_data) != expected_size:
            raise Exception(f"Size mismatch: expected {expected_size} bytes, got {len(file_data)} bytes")
        
        # Create temp file with buffered write
        suffix = Path(storage_key).suffix
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        
        # DC Protocol: Buffered write with flush+fsync
        temp_file.write(file_data)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()
        
        # DC Protocol: Validate checksum BEFORE compression
        if original_checksum:
            with open(temp_file.name, 'rb') as f:
                actual_checksum = hashlib.sha256(f.read()).hexdigest()
            
            if actual_checksum != original_checksum:
                os.unlink(temp_file.name)  # Remove corrupt file
                raise Exception(f"Checksum mismatch: expected {original_checksum}, got {actual_checksum}")
        
        logger.info(f"[DC PROTOCOL] ✅ Downloaded & validated from object storage: {storage_key}")
        return (Path(temp_file.name), True)  # is_temp_file=True
    else:
        # Local file - already on disk, validate checksum if provided
        # DC Protocol Fix: Prepend storage root for local files (clean paths in DB)
        # Path: backend/app/services/job_handlers/handler.py -> .parent x5 = workspace root
        local_storage_root = Path(__file__).parent.parent.parent.parent.parent / "frontend" / "storage"
        local_path = local_storage_root / storage_key
        
        if not local_path.exists():
            raise Exception(f"Local file not found: {local_path}")
        
        # DC Protocol: Validate checksum for local files too
        if original_checksum:
            with open(local_path, 'rb') as f:
                actual_checksum = hashlib.sha256(f.read()).hexdigest()
            
            if actual_checksum != original_checksum:
                raise Exception(f"Local file checksum mismatch: expected {original_checksum}, got {actual_checksum}")
        
        logger.info(f"[DC PROTOCOL] ✅ Validated local file: {storage_key}")
        return (local_path, False)  # is_temp_file=False


# Table configuration for compression updates
# Maps table_name -> (compressed_path_column, compressed_size_column, processing_status_column, checksum_column)
TABLE_CONFIGS = {
    'staff_task_attachments': {
        'compressed_path_col': 'compressed_path',
        'compressed_size_col': 'compressed_size_bytes',
        'processing_status_col': 'processing_status',
        'checksum_col': 'compressed_checksum',
        'has_compressed_col': 'has_compressed'
    },
    'kyc_document': {
        'compressed_path_col': 'compressed_path',
        'compressed_size_col': 'compressed_size_bytes',
        'processing_status_col': 'processing_status',
        'checksum_col': 'compressed_checksum',
        'has_compressed_col': 'has_compressed'
    },
    'kyc_documents': {
        'compressed_path_col': 'compressed_path',
        'compressed_size_col': 'compressed_size_bytes',
        'processing_status_col': 'processing_status',
        'checksum_col': 'compressed_checksum',
        'has_compressed_col': 'has_compressed'
    },
    'feedback_media': {
        'compressed_path_col': 'compressed_path',
        'compressed_size_col': 'compressed_size_bytes',
        'processing_status_col': 'processing_status',
        'checksum_col': 'compressed_checksum',
        'has_compressed_col': 'has_compressed'
    },
    'staff_employee_kyc': {
        'compressed_path_col': 'compressed_path',
        'compressed_size_col': 'compressed_size_bytes',
        'processing_status_col': 'processing_status',
        'checksum_col': 'compressed_checksum',
        'has_compressed_col': 'has_compressed'
    },
    'staff_journeys': {
        'compressed_path_col': 'compressed_photo_path',
        'compressed_size_col': 'compressed_photo_size',
        'processing_status_col': 'photo_processing_status',
        'checksum_col': 'compressed_photo_checksum',
        'has_compressed_col': 'has_compressed_photo'
    },
    'staff_task_attachments': {
        'compressed_path_col': 'compressed_path',
        'compressed_size_col': 'compressed_size_bytes',
        'processing_status_col': 'processing_status',
        'checksum_col': 'compressed_checksum',
        'has_compressed_col': 'has_compressed'
    }
}


def process_universal_compression_job(job_id: int):
    """
    Process universal image compression job (executed in APScheduler thread pool)
    DC Protocol: Complete audit trail with dual evidence preservation for ANY table
    WVV Protocol: Status tracking, retry logic, error handling
    
    ARCHITECTURE: Fully synchronous - no async/await (APScheduler ThreadPoolExecutor requirement)
    
    Args:
        job_id: Background job ID from background_jobs table
    
    Job Data Expected:
        - table_name: Target table name
        - record_id: ID of the record in that table
        - original_path: Path to original image file
        - uploaded_by_id: User/Staff ID who uploaded
        - uploaded_by_type: 'staff' or 'user'
        - emp_code: Employee code (optional, for staff)
        - uploaded_ip: IP address (optional)
        - uploaded_device: Device info (optional)
    """
    # DC: Create new database session (CRITICAL: Detached from request session)
    db = SessionLocal()
    
    try:
        # Get job record
        job = BackgroundJobService.get_job_by_id(db, job_id)
        if not job:
            logger.error(f"[UNIVERSAL COMPRESSION] Job {job_id} not found")
            return
        
        # WVV: Mark job as processing
        job = BackgroundJobService.mark_job_processing(db, job_id)
        if not job:
            logger.error(f"[UNIVERSAL COMPRESSION] Failed to mark job {job_id} as processing")
            return
        
        # Extract job data
        table_name = job.job_data.get('table_name')
        record_id = job.job_data.get('record_id')
        original_path_str = job.job_data.get('original_path')
        uploaded_by_id = job.job_data.get('uploaded_by_id')
        uploaded_by_type = job.job_data.get('uploaded_by_type')
        
        if not all([table_name, record_id, original_path_str, uploaded_by_id, uploaded_by_type]):
            error_msg = f"Missing required job data: table={table_name}, record_id={record_id}, uploader={uploaded_by_id}"
            logger.error(f"[UNIVERSAL COMPRESSION] {error_msg}")
            BackgroundJobService.mark_job_failed(db, job_id, error_msg)
            return
        
        # Get table configuration
        if table_name not in TABLE_CONFIGS:
            error_msg = f"Table '{table_name}' not configured for compression"
            logger.error(f"[UNIVERSAL COMPRESSION] {error_msg}")
            BackgroundJobService.mark_job_failed(db, job_id, error_msg)
            return
        
        config = TABLE_CONFIGS[table_name]
        storage_type = job.job_data.get('storage_type', 'local')
        storage_key = job.job_data.get('storage_key') or original_path_str  # Fallback for old data
        original_checksum = job.job_data.get('original_checksum')
        temp_file_path = None  # Track temp file for cleanup
        
        logger.info(f"[UNIVERSAL COMPRESSION] Processing {table_name}:{record_id}, storage: {storage_type}")
        
        # DC PROTOCOL: Safe download with validation
        try:
            original_path, is_temp_file = download_original_file(
                storage_type=storage_type,
                storage_key=storage_key,
                original_checksum=original_checksum
            )
            
            # Track temp file for cleanup (only if downloaded from object storage)
            if is_temp_file:
                temp_file_path = original_path
                
        except Exception as e:
            error_msg = f"Failed to access original file: {str(e)}"
            logger.error(f"[UNIVERSAL COMPRESSION] {error_msg}")
            BackgroundJobService.mark_job_failed(db, job_id, error_msg)
            
            # Update record status using raw SQL (table-agnostic)
            update_sql = text(f"""
                UPDATE {table_name}
                SET {config['processing_status_col']} = 'failed'
                WHERE id = :record_id
            """)
            db.execute(update_sql, {'record_id': record_id})
            db.commit()
            return
        
        # Detect file type (image vs video) using MIME type
        mime_type, _ = mimetypes.guess_type(str(original_path))
        is_video = mime_type and mime_type.startswith('video/')
        is_image = mime_type and mime_type.startswith('image/')
        
        # Determine if watermark should be applied (for announcements/feedback only)
        apply_watermark = (table_name == 'feedback_media')
        
        logger.info(f"[UNIVERSAL COMPRESSION] File type: {'VIDEO' if is_video else 'IMAGE'}, "
                   f"Watermark: {'YES' if apply_watermark else 'NO'}")
        
        # Perform compression (SYNCHRONOUS - no await!)
        try:
            if is_video:
                # Use video compression service
                compressed_path, metadata = VideoCompressionService.compress_video(
                    original_path,
                    apply_watermark=apply_watermark
                )
            elif is_image:
                # Use image compression service
                compressed_path, metadata = ImageCompressionService.compress_image(original_path)
            else:
                # Unknown file type - skip compression
                error_msg = f"Unknown file type: {mime_type} - skipping compression"
                logger.warning(f"[UNIVERSAL COMPRESSION] {error_msg}")
                BackgroundJobService.mark_job_failed(db, job_id, error_msg)
                
                update_sql = text(f"""
                    UPDATE {table_name}
                    SET {config['processing_status_col']} = 'skipped'
                    WHERE id = :record_id
                """)
                db.execute(update_sql, {'record_id': record_id})
                db.commit()
                return
            
            # Build log message with appropriate metrics
            if is_video:
                logger.info(f"[UNIVERSAL COMPRESSION] ✅ Compressed VIDEO {table_name}:{record_id}: "
                           f"{metadata['original_size']/1024/1024:.2f}MB → {metadata['compressed_size']/1024/1024:.2f}MB "
                           f"({metadata['compression_ratio']:.1f}% reduction, {metadata['compressed_duration']:.1f}s)")
            else:
                logger.info(f"[UNIVERSAL COMPRESSION] ✅ Compressed IMAGE {table_name}:{record_id}: "
                           f"{metadata['original_size']/1024:.2f}KB → {metadata['compressed_size']/1024:.2f}KB "
                           f"(SSIM: {metadata['ssim_score']:.4f})")
            
            # DC PROTOCOL: Move to permanent storage with DETERMINISTIC filename
            # Architect requirement: f"frontend/storage/{table}/compressed/{record_id}_v{timestamp}.{ext}"
            storage_root = Path("frontend/storage")
            final_storage_dir = storage_root / table_name / "compressed"
            final_storage_dir.mkdir(parents=True, exist_ok=True)
            
            # DETERMINISTIC filename: {record_id}_v{timestamp}.{ext}
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            file_extension = compressed_path.suffix  # e.g., .jpg, .mp4
            deterministic_filename = f"{record_id}_v{timestamp}{file_extension}"
            final_compressed_path = final_storage_dir / deterministic_filename
            
            # Move compressed file to deterministic location
            import shutil
            if compressed_path != final_compressed_path:
                shutil.move(str(compressed_path), str(final_compressed_path))
                logger.info(f"[DC PROTOCOL] Moved compressed file: {compressed_path.name} → {deterministic_filename}")
                compressed_path = final_compressed_path
            
            # DC PROTOCOL: Update record with compressed data using raw SQL (table-agnostic)
            update_sql = text(f"""
                UPDATE {table_name}
                SET 
                    {config['compressed_path_col']} = :compressed_path,
                    {config['compressed_size_col']} = :compressed_size,
                    {config['checksum_col']} = :compressed_checksum,
                    {config['has_compressed_col']} = true,
                    {config['processing_status_col']} = 'completed'
                WHERE id = :record_id
            """)
            
            db.execute(update_sql, {
                'record_id': record_id,
                'compressed_path': str(compressed_path),
                'compressed_size': metadata['compressed_size'],
                'compressed_checksum': metadata['compressed_checksum']
            })
            
            db.commit()
            
            # Mark job as completed with result metadata
            result = {
                'table_name': table_name,
                'record_id': record_id,
                'file_type': 'video' if is_video else 'image',
                'original_size': metadata['original_size'],
                'compressed_size': metadata['compressed_size'],
                'compression_ratio': metadata['compression_ratio'],
                'compressed_path': str(compressed_path)
            }
            
            # Add type-specific metadata
            if is_video:
                result['duration'] = metadata.get('compressed_duration')
            else:
                result['ssim_score'] = metadata.get('ssim_score')
            
            BackgroundJobService.mark_job_completed(db, job_id, result)
            
        except (ImageCompressionError, VideoCompressionError) as e:
            # Compression failed - keep original file (DC: preserve evidence)
            media_type = 'Video' if is_video else 'Image'
            error_msg = f"{media_type} compression failed: {str(e)}"
            error_traceback = traceback.format_exc()
            
            logger.error(f"[UNIVERSAL COMPRESSION] {error_msg}")
            logger.debug(f"[UNIVERSAL COMPRESSION] Traceback: {error_traceback}")
            
            # Update record status using raw SQL
            update_sql = text(f"""
                UPDATE {table_name}
                SET {config['processing_status_col']} = 'failed'
                WHERE id = :record_id
            """)
            db.execute(update_sql, {'record_id': record_id})
            db.commit()
            
            # WVV: Mark job as failed (will retry if attempts < max_attempts)
            BackgroundJobService.mark_job_failed(db, job_id, error_msg, error_traceback)
            
    except Exception as e:
        # Unexpected error - log and mark job as failed
        error_msg = f"Unexpected error processing compression job: {str(e)}"
        error_traceback = traceback.format_exc()
        
        logger.error(f"[UNIVERSAL COMPRESSION] {error_msg}")
        logger.debug(f"[UNIVERSAL COMPRESSION] Traceback: {error_traceback}")
        
        # Mark job as failed
        try:
            BackgroundJobService.mark_job_failed(db, job_id, error_msg, error_traceback)
        except:
            logger.error(f"[UNIVERSAL COMPRESSION] Failed to update job status for job {job_id}")
    
    finally:
        # DC PROTOCOL: Cleanup temporary files (from object storage downloads)
        if temp_file_path and temp_file_path.exists():
            try:
                temp_file_path.unlink()
                logger.info(f"[CLEANUP] Removed temp file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"[CLEANUP] Failed to remove temp file: {str(e)}")
        
        # Always close database session
        db.close()
