"""
Image Compression Service with Quality Preservation
DC Protocol: Dual evidence (original + compressed), complete audit trail
WVV Protocol: SSIM validation, logging, error handling

Features:
- Pillow-based compression with quality preservation
- SSIM >=0.95 quality validation
- WebP conversion for better compression ratios
- Async processing pipeline
- Complete audit trail creation
"""

import hashlib
import io
import logging
import time
from pathlib import Path
from typing import Optional, Tuple, Dict
from datetime import datetime, timezone

from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


class ImageCompressionError(Exception):
    """Custom exception for image compression failures"""
    pass


class ImageCompressionService:
    """
    Service for compressing images with quality preservation
    DC: Maintains original + compressed versions
    WVV: Validates compression quality via SSIM
    """
    
    # Target compression settings
    TARGET_SIZE_KB = 500  # 500KB max for compressed images
    TARGET_SIZE_BYTES = TARGET_SIZE_KB * 1024
    MIN_SSIM_SCORE = 0.95  # Minimum acceptable quality (architect-mandated)
    
    # Compression format preferences (ordered by efficiency)
    COMPRESSION_FORMATS = ['webp', 'jpeg']
    
    # Quality range for iterative compression
    MIN_QUALITY = 65  # Minimum acceptable quality
    MAX_QUALITY = 95  # Starting quality
    QUALITY_STEP = 5  # Quality reduction per iteration
    
    @staticmethod
    def calculate_checksum(file_path: Path) -> str:
        """
        Calculate SHA-256 checksum of file
        DC: Ensures file integrity verification
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    @staticmethod
    def _ssim_channel(img1: np.ndarray, img2: np.ndarray) -> float:
        C1 = (0.01 * 255) ** 2
        C2 = (0.03 * 255) ** 2
        img1 = img1.astype(np.float64)
        img2 = img2.astype(np.float64)
        mu1 = img1.mean()
        mu2 = img2.mean()
        sigma1_sq = img1.var()
        sigma2_sq = img2.var()
        sigma12 = ((img1 - mu1) * (img2 - mu2)).mean()
        num = (2 * mu1 * mu2 + C1) * (2 * sigma12 + C2)
        den = (mu1 ** 2 + mu2 ** 2 + C1) * (sigma1_sq + sigma2_sq + C2)
        return float(num / den)

    @staticmethod
    def calculate_ssim(original_path: Path, compressed_path: Path) -> float:
        """
        Calculate SSIM (Structural Similarity Index) between two images
        WVV: Quality verification - higher is better (1.0 = identical)
        
        Returns: SSIM score (0-1, target >=0.95)
        """
        try:
            original = Image.open(original_path).convert('RGB')
            compressed = Image.open(compressed_path).convert('RGB')
            
            if original.size != compressed.size:
                compressed = compressed.resize(original.size, Image.Resampling.LANCZOS)
            
            original_array = np.array(original)
            compressed_array = np.array(compressed)
            
            channels = original_array.shape[2]
            scores = [
                ImageCompressionService._ssim_channel(
                    original_array[:, :, c], compressed_array[:, :, c]
                )
                for c in range(channels)
            ]
            return float(np.mean(scores))
            
        except Exception as e:
            logger.error(f"SSIM calculation failed: {str(e)}")
            raise ImageCompressionError(f"Quality validation failed: {str(e)}")
    
    @classmethod
    def compress_image(
        cls,
        original_path: Path,
        target_size_bytes: Optional[int] = None,
        preserve_format: bool = False
    ) -> Tuple[Path, Dict]:
        """
        Compress image to target size while maintaining quality
        WVV: Iterative quality reduction until size target met
        DC: Creates compressed copy, preserves original
        
        Args:
            original_path: Path to original image
            target_size_bytes: Target file size (default: 500KB)
            preserve_format: If True, keep original format (default: False, tries WebP)
        
        Returns:
            Tuple of (compressed_path, metadata_dict)
            
        Raises:
            ImageCompressionError: If compression fails or quality too low
        """
        start_time = time.time()
        target_size = target_size_bytes or cls.TARGET_SIZE_BYTES
        
        logger.info(f"[COMPRESSION START] Original: {original_path.name}, Target: {target_size/1024:.2f}KB")
        
        try:
            # Load original image
            with Image.open(original_path) as img:
                original_format = img.format
                original_mode = img.mode
                original_size_bytes = original_path.stat().st_size
                
                # Convert RGBA to RGB for JPEG/WebP compatibility
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Determine compression formats to try
                formats_to_try = [original_format.lower()] if preserve_format else cls.COMPRESSION_FORMATS
                
                best_result = None
                best_ssim = 0
                
                for fmt in formats_to_try:
                    logger.info(f"[COMPRESSION] Trying format: {fmt.upper()}")
                    
                    # Try compressing with this format
                    result = cls._compress_with_format(
                        img=img,
                        original_path=original_path,
                        target_format=fmt,
                        target_size=target_size,
                        original_size=original_size_bytes
                    )
                    
                    if result and result['ssim_score'] >= cls.MIN_SSIM_SCORE:
                        # Valid result - check if it's the best so far
                        if result['ssim_score'] > best_ssim:
                            best_result = result
                            best_ssim = result['ssim_score']
                        
                        # If we hit target size, use this result
                        if result['compressed_size'] <= target_size:
                            logger.info(f"[COMPRESSION SUCCESS] Format: {fmt.upper()}, Size: {result['compressed_size']/1024:.2f}KB, SSIM: {result['ssim_score']:.4f}")
                            break
                
                if not best_result:
                    raise ImageCompressionError(
                        f"Could not compress image to {target_size/1024:.2f}KB while maintaining SSIM >={cls.MIN_SSIM_SCORE}"
                    )
                
                # Calculate processing time
                processing_time_ms = int((time.time() - start_time) * 1000)
                
                # Prepare metadata
                metadata = {
                    'compressed_path': best_result['compressed_path'],
                    'original_size': original_size_bytes,
                    'compressed_size': best_result['compressed_size'],
                    'compression_ratio': round(best_result['compressed_size'] / original_size_bytes, 4),
                    'ssim_score': best_result['ssim_score'],
                    'processing_method': f"pillow_{best_result['format']}",
                    'processing_duration_ms': processing_time_ms,
                    'original_checksum': cls.calculate_checksum(original_path),
                    'compressed_checksum': cls.calculate_checksum(best_result['compressed_path']),
                    'quality_preserved': best_result['ssim_score'] >= cls.MIN_SSIM_SCORE
                }
                
                logger.info(f"[COMPRESSION COMPLETE] Duration: {processing_time_ms}ms, Ratio: {metadata['compression_ratio']:.2%}")
                
                return best_result['compressed_path'], metadata
                
        except Exception as e:
            logger.error(f"[COMPRESSION FAILED] {str(e)}")
            raise ImageCompressionError(f"Compression failed: {str(e)}")
    
    @classmethod
    def _compress_with_format(
        cls,
        img: Image.Image,
        original_path: Path,
        target_format: str,
        target_size: int,
        original_size: int
    ) -> Optional[Dict]:
        """
        Attempt compression with specific format
        WVV: Iterative quality reduction
        
        Returns: Dict with compressed_path, compressed_size, ssim_score, format
                 None if compression fails
        """
        # Create temporary compressed path
        compressed_path = original_path.parent / f"{original_path.stem}_compressed.{target_format}"
        
        # If original is already smaller than target, just copy it
        if original_size <= target_size:
            logger.info(f"[COMPRESSION] Original already under target, using quality 95")
            quality = 95
        else:
            # Start with high quality
            quality = cls.MAX_QUALITY
        
        while quality >= cls.MIN_QUALITY:
            try:
                # Save with current quality
                if target_format == 'webp':
                    img.save(compressed_path, 'WEBP', quality=quality, method=6)
                elif target_format in ('jpeg', 'jpg'):
                    img.save(compressed_path, 'JPEG', quality=quality, optimize=True)
                else:
                    # Unsupported format
                    return None
                
                compressed_size = compressed_path.stat().st_size
                
                # Check if we met size target
                if compressed_size <= target_size:
                    # Calculate SSIM to verify quality
                    ssim_score = cls.calculate_ssim(original_path, compressed_path)
                    
                    logger.info(f"[COMPRESSION] Quality: {quality}, Size: {compressed_size/1024:.2f}KB, SSIM: {ssim_score:.4f}")
                    
                    if ssim_score >= cls.MIN_SSIM_SCORE:
                        # Success!
                        return {
                            'compressed_path': compressed_path,
                            'compressed_size': compressed_size,
                            'ssim_score': ssim_score,
                            'format': target_format,
                            'quality': quality
                        }
                    else:
                        # Quality too low, try higher quality (accept larger file)
                        logger.warning(f"[COMPRESSION] SSIM {ssim_score:.4f} < {cls.MIN_SSIM_SCORE}, retrying with higher quality")
                        break
                
                # Reduce quality and try again
                quality -= cls.QUALITY_STEP
                
            except Exception as e:
                logger.error(f"[COMPRESSION] Format {target_format} failed at quality {quality}: {str(e)}")
                break
        
        # Clean up failed attempt
        if compressed_path.exists():
            compressed_path.unlink()
        
        return None
    
    @classmethod
    async def compress_and_audit(
        cls,
        original_path: Path,
        uploaded_by: int,
        attachment_id: int,
        db_session
    ) -> Dict:
        """
        Compress image and create audit record
        DC: Complete audit trail with dual evidence
        WVV: Full validation and logging
        
        Args:
            original_path: Path to original image
            uploaded_by: Employee ID who uploaded
            attachment_id: Database ID of attachment record
            db_session: SQLAlchemy session
        
        Returns:
            Dict with compression metadata and audit record ID
        """
        from app.models.staff_tasks import StaffTaskAttachmentAudit
        
        logger.info(f"[AUDIT] Starting compression for attachment {attachment_id}")
        
        try:
            # Perform compression
            compressed_path, metadata = cls.compress_image(original_path)
            
            # Create audit record
            audit_record = StaffTaskAttachmentAudit(
                attachment_id=attachment_id,
                original_filename=original_path.name,
                original_size=metadata['original_size'],
                compressed_size=metadata['compressed_size'],
                original_checksum=metadata['original_checksum'],
                compressed_checksum=metadata['compressed_checksum'],
                compression_ratio=metadata['compression_ratio'],
                ssim_score=metadata['ssim_score'],
                processing_method=metadata['processing_method'],
                processing_duration_ms=metadata['processing_duration_ms'],
                uploaded_by=uploaded_by,
                uploaded_at=datetime.now(timezone.utc)
            )
            
            db_session.add(audit_record)
            db_session.flush()  # Get audit record ID
            
            logger.info(f"[AUDIT] Created audit record {audit_record.id} for attachment {attachment_id}")
            
            return {
                'compressed_path': compressed_path,
                'audit_id': audit_record.id,
                **metadata
            }
            
        except Exception as e:
            logger.error(f"[AUDIT] Failed for attachment {attachment_id}: {str(e)}")
            raise
