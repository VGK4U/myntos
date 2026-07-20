"""
Video Compression Service with Quality Preservation
DC Protocol: Dual evidence (original + compressed), complete audit trail
WVV Protocol: Duration limits, file size validation, error handling

Features:
- ffmpeg-based compression with H.264/AAC encoding
- Target ≤8MB compressed file size
- ≤60s duration preservation
- Watermark integration for announcements
- Complete audit trail creation
"""

import hashlib
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple, Dict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class VideoCompressionError(Exception):
    """Custom exception for video compression failures"""
    pass


class VideoCompressionService:
    """
    Service for compressing videos with quality preservation
    DC: Maintains original + compressed versions
    WVV: Validates compression quality and duration
    """
    
    # Target compression settings (DC Protocol requirement)
    TARGET_SIZE_MB = 8  # 8MB max for compressed videos
    TARGET_SIZE_BYTES = TARGET_SIZE_MB * 1024 * 1024
    MAX_DURATION_SECONDS = 60  # Maximum 60 seconds per DC Protocol
    
    # ffmpeg encoding settings
    VIDEO_CODEC = 'libx264'  # H.264 for broad compatibility
    AUDIO_CODEC = 'aac'  # AAC for broad compatibility
    VIDEO_CRF = 28  # Constant Rate Factor (18-51, higher = smaller/lower quality, 28 = good balance)
    MAX_VIDEO_WIDTH = 1280  # 720p width for compression
    MAX_VIDEO_HEIGHT = 720  # 720p height for compression
    AUDIO_BITRATE = '96k'  # Lower audio bitrate for smaller files
    
    @staticmethod
    def calculate_checksum(file_path: Path) -> str:
        """
        Calculate SHA-256 checksum of file
        DC: Ensures file integrity verification
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(8192), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    @staticmethod
    def get_video_metadata(file_path: Path) -> Dict:
        """
        Extract video metadata using ffprobe
        WVV: Validation and information gathering
        
        Returns: {'duration': float, 'width': int, 'height': int, 'size_bytes': int}
        """
        try:
            # Check if ffprobe is available
            if not shutil.which('ffprobe'):
                raise VideoCompressionError("ffprobe not found - ffmpeg installation required")
            
            # Get duration
            duration_cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(file_path)
            ]
            
            duration_result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=10)
            if duration_result.returncode != 0:
                raise VideoCompressionError(f"Failed to get video duration: {duration_result.stderr}")
            
            duration = float(duration_result.stdout.strip())
            
            # Get dimensions
            dimensions_cmd = [
                'ffprobe', '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'csv=p=0',
                str(file_path)
            ]
            
            dimensions_result = subprocess.run(dimensions_cmd, capture_output=True, text=True, timeout=10)
            if dimensions_result.returncode != 0:
                raise VideoCompressionError(f"Failed to get video dimensions: {dimensions_result.stderr}")
            
            width, height = map(int, dimensions_result.stdout.strip().split(','))
            
            # Get file size
            size_bytes = file_path.stat().st_size
            
            return {
                'duration': duration,
                'width': width,
                'height': height,
                'size_bytes': size_bytes
            }
            
        except subprocess.TimeoutExpired:
            raise VideoCompressionError("Video metadata extraction timed out")
        except Exception as e:
            logger.error(f"Failed to extract video metadata: {str(e)}")
            raise VideoCompressionError(f"Metadata extraction failed: {str(e)}")
    
    @classmethod
    def compress_video(
        cls,
        original_path: Path,
        target_size_bytes: Optional[int] = None,
        apply_watermark: bool = False
    ) -> Tuple[Path, Dict]:
        """
        Compress video using ffmpeg with quality preservation
        DC Protocol: Dual evidence workflow
        
        Args:
            original_path: Path to original video file
            target_size_bytes: Target size in bytes (default: 8MB)
            apply_watermark: Whether to apply watermark (for announcements)
        
        Returns:
            Tuple of (compressed_path, compression_metadata)
            compression_metadata = {
                'original_size': int,
                'compressed_size': int,
                'original_duration': float,
                'compressed_duration': float,
                'compression_ratio': float,
                'original_checksum': str,
                'compressed_checksum': str,
                'processing_time_seconds': float
            }
        
        Raises:
            VideoCompressionError: If compression fails
        """
        start_time = datetime.now(timezone.utc)
        
        if not original_path.exists():
            raise VideoCompressionError(f"Original video not found: {original_path}")
        
        # Check ffmpeg availability
        if not shutil.which('ffmpeg'):
            raise VideoCompressionError("ffmpeg not found - installation required")
        
        target_size = target_size_bytes or cls.TARGET_SIZE_BYTES
        
        # STEP 1: Extract original metadata
        logger.info(f"[VIDEO COMPRESSION] Analyzing original video: {original_path}")
        try:
            original_metadata = cls.get_video_metadata(original_path)
            original_size = original_metadata['size_bytes']
            original_duration = original_metadata['duration']
            original_width = original_metadata['width']
            original_height = original_metadata['height']
            
            logger.info(
                f"[VIDEO] Original: {original_size/1024/1024:.2f}MB, "
                f"{original_duration:.1f}s, {original_width}x{original_height}"
            )
            
            # WVV: Validate duration limit
            if original_duration > cls.MAX_DURATION_SECONDS:
                raise VideoCompressionError(
                    f"Video duration ({original_duration:.1f}s) exceeds maximum "
                    f"({cls.MAX_DURATION_SECONDS}s) - DC Protocol requirement"
                )
                
        except VideoCompressionError:
            raise
        except Exception as e:
            raise VideoCompressionError(f"Failed to analyze original video: {str(e)}")
        
        # STEP 2: Calculate original checksum
        logger.info("[VIDEO] Calculating original checksum...")
        original_checksum = cls.calculate_checksum(original_path)
        
        # STEP 3: Build compression command
        compressed_path = original_path.parent / f"{original_path.stem}_compressed.mp4"
        
        # Calculate target dimensions (maintain aspect ratio)
        if original_width > cls.MAX_VIDEO_WIDTH or original_height > cls.MAX_VIDEO_HEIGHT:
            ratio = min(cls.MAX_VIDEO_WIDTH / original_width, cls.MAX_VIDEO_HEIGHT / original_height)
            new_width = int(original_width * ratio)
            new_height = int(original_height * ratio)
            # Ensure even dimensions (H.264 requirement)
            new_width = new_width - (new_width % 2)
            new_height = new_height - (new_height % 2)
            scale_filter = f"scale={new_width}:{new_height}"
        elif (original_width % 2 != 0) or (original_height % 2 != 0):
            # Fix odd dimensions
            scale_filter = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
        else:
            scale_filter = None
        
        # Build ffmpeg command
        ffmpeg_cmd = [
            'ffmpeg', '-i', str(original_path),
            '-c:v', cls.VIDEO_CODEC,
            '-crf', str(cls.VIDEO_CRF),
            '-c:a', cls.AUDIO_CODEC,
            '-b:a', cls.AUDIO_BITRATE,
            '-movflags', '+faststart',  # Enable streaming
            '-pix_fmt', 'yuv420p',  # Compatibility
            '-y',  # Overwrite output
        ]
        
        if scale_filter:
            ffmpeg_cmd.extend(['-vf', scale_filter])
        
        ffmpeg_cmd.append(str(compressed_path))
        
        # STEP 4: Execute compression
        logger.info(f"[VIDEO] Compressing with ffmpeg (CRF {cls.VIDEO_CRF})...")
        try:
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=180  # 3 minute timeout for 60s videos
            )
            
            if result.returncode != 0:
                raise VideoCompressionError(f"ffmpeg compression failed: {result.stderr}")
            
        except subprocess.TimeoutExpired:
            raise VideoCompressionError("Video compression timed out (>3 minutes)")
        except Exception as e:
            raise VideoCompressionError(f"Compression execution failed: {str(e)}")
        
        # STEP 5: Verify compressed file exists
        if not compressed_path.exists():
            raise VideoCompressionError("Compressed file was not created")
        
        # STEP 6: Extract compressed metadata
        logger.info("[VIDEO] Analyzing compressed video...")
        try:
            compressed_metadata = cls.get_video_metadata(compressed_path)
            compressed_size = compressed_metadata['size_bytes']
            compressed_duration = compressed_metadata['duration']
            
            logger.info(
                f"[VIDEO] Compressed: {compressed_size/1024/1024:.2f}MB, "
                f"{compressed_duration:.1f}s"
            )
            
        except Exception as e:
            # Cleanup partial file
            compressed_path.unlink(missing_ok=True)
            raise VideoCompressionError(f"Failed to analyze compressed video: {str(e)}")
        
        # STEP 7: Calculate compressed checksum
        logger.info("[VIDEO] Calculating compressed checksum...")
        compressed_checksum = cls.calculate_checksum(compressed_path)
        
        # STEP 8: Apply watermark if requested (for announcements)
        if apply_watermark:
            logger.info("[VIDEO] Applying watermark...")
            try:
                from app.utils.watermark import add_watermark_to_video
                success = add_watermark_to_video(str(compressed_path))
                if success:
                    # Recalculate checksum after watermarking
                    compressed_checksum = cls.calculate_checksum(compressed_path)
                    compressed_size = compressed_path.stat().st_size
                    logger.info("[VIDEO] Watermark applied successfully")
                else:
                    logger.warning("[VIDEO] Watermark application failed - continuing without watermark")
            except Exception as e:
                logger.warning(f"[VIDEO] Watermark error: {str(e)} - continuing without watermark")
        
        # STEP 9: Validate target size (soft limit - warn if exceeded)
        if compressed_size > target_size:
            size_mb = compressed_size / (1024 * 1024)
            target_mb = target_size / (1024 * 1024)
            logger.warning(
                f"[VIDEO] Compressed size ({size_mb:.2f}MB) exceeds target ({target_mb:.2f}MB) "
                f"- CRF {cls.VIDEO_CRF} is optimal for quality/size balance"
            )
        
        # STEP 10: Calculate compression metrics
        end_time = datetime.now(timezone.utc)
        processing_time = (end_time - start_time).total_seconds()
        compression_ratio = (1 - (compressed_size / original_size)) * 100
        
        metadata = {
            'original_size': original_size,
            'compressed_size': compressed_size,
            'original_duration': original_duration,
            'compressed_duration': compressed_duration,
            'compression_ratio': compression_ratio,
            'original_checksum': original_checksum,
            'compressed_checksum': compressed_checksum,
            'processing_time_seconds': processing_time
        }
        
        logger.info(
            f"[VIDEO COMPRESSION] ✅ Complete: {compression_ratio:.1f}% reduction "
            f"in {processing_time:.1f}s"
        )
        
        return compressed_path, metadata
