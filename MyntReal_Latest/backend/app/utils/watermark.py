"""
Media Watermarking Utility
DC Protocol: Automatically add MNR logo watermark to all uploaded media
Watermark positioned at top-right corner with 70% opacity
"""
from PIL import Image, ImageDraw
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)

# Watermark configuration - Use absolute path from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # Go up to project root from backend/app/utils/
LOGO_PATH = PROJECT_ROOT / "uploads" / "watermark" / "logo.png"
LOGO_WIDTH = 60  # Target logo width in pixels (reduced from 80 for optimization)
LOGO_OPACITY = 0.7  # 70% opacity
MARGIN = 10  # Margin from edges in pixels

# Image optimization settings
MAX_IMAGE_WIDTH = 1920  # Maximum width for uploaded images (Full HD)
MAX_IMAGE_HEIGHT = 1920  # Maximum height for uploaded images
JPEG_QUALITY = 85  # JPEG quality (85 is excellent quality with good compression)
PNG_COMPRESSION = 9  # PNG compression level (0-9, higher = smaller files)

# Video optimization settings
MAX_VIDEO_WIDTH = 1920  # Maximum width for uploaded videos (Full HD)
MAX_VIDEO_HEIGHT = 1920  # Maximum height for uploaded videos
VIDEO_BITRATE = "2M"  # Video bitrate (2M = 2 Mbps, excellent quality for 1080p)
VIDEO_CRF = 23  # Constant Rate Factor (18-28, lower = better quality, 23 is good balance)


def add_watermark_to_image(image_path: str) -> bool:
    """
    Add MNR logo watermark to image at top-right corner
    DC Protocol: Optimize image size while preserving quality, then add watermark
    
    Optimizations applied:
    - Resize oversized images to max 1920px (Full HD)
    - JPEG compression at quality=85 (excellent quality, 40-60% smaller)
    - PNG optimization with compression level 9
    
    Args:
        image_path: Path to the image file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not LOGO_PATH.exists():
            logger.error(f"Logo file not found: {LOGO_PATH}")
            return False
        
        # DC Protocol: Capture original format and mode BEFORE any conversions
        original_image = Image.open(image_path)
        original_mode = original_image.mode
        original_format = original_image.format or 'PNG'  # Default to PNG if format unknown
        
        # Optimization: Resize oversized images while maintaining aspect ratio
        if original_image.width > MAX_IMAGE_WIDTH or original_image.height > MAX_IMAGE_HEIGHT:
            # Calculate new dimensions maintaining aspect ratio
            ratio = min(MAX_IMAGE_WIDTH / original_image.width, MAX_IMAGE_HEIGHT / original_image.height)
            new_width = int(original_image.width * ratio)
            new_height = int(original_image.height * ratio)
            original_image = original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"📐 Resized image to {new_width}x{new_height} for optimization")
        
        # Open logo
        logo = Image.open(LOGO_PATH).convert("RGBA")
        
        # Calculate logo dimensions maintaining aspect ratio
        aspect_ratio = logo.height / logo.width
        logo_height = int(LOGO_WIDTH * aspect_ratio)
        logo_resized = logo.resize((LOGO_WIDTH, logo_height), Image.Resampling.LANCZOS)
        
        # Apply opacity to logo
        logo_with_opacity = Image.new("RGBA", logo_resized.size)
        for x in range(logo_resized.width):
            for y in range(logo_resized.height):
                r, g, b, a = logo_resized.getpixel((x, y))
                logo_with_opacity.putpixel((x, y), (r, g, b, int(a * LOGO_OPACITY)))
        
        # Convert image to RGBA for compositing
        if original_image.mode != 'RGBA':
            working_image = original_image.convert('RGBA')
        else:
            working_image = original_image
        
        # Calculate position (top-right corner)
        position = (working_image.width - LOGO_WIDTH - MARGIN, MARGIN)
        
        # Create overlay
        overlay = Image.new('RGBA', working_image.size, (255, 255, 255, 0))
        overlay.paste(logo_with_opacity, position, logo_with_opacity)
        
        # Composite
        watermarked = Image.alpha_composite(working_image, overlay)
        
        # DC Protocol: Convert back to original mode and optimize file size
        if original_mode == 'RGB':
            watermarked = watermarked.convert('RGB')
            # Save as JPEG with optimized quality (85 = excellent quality, 40-60% smaller)
            watermarked.save(image_path, format='JPEG', quality=JPEG_QUALITY, optimize=True)
        elif original_mode == 'RGBA':
            # Keep RGBA for PNG with transparency and maximum compression
            watermarked.save(image_path, format='PNG', optimize=True, compress_level=PNG_COMPRESSION)
        elif original_mode in ('P', 'L', 'LA'):
            # Palette or grayscale - convert to RGB for watermark, save as optimized PNG
            watermarked = watermarked.convert('RGB')
            watermarked.save(image_path, format='PNG', optimize=True, compress_level=PNG_COMPRESSION)
        else:
            # Unknown mode - save as optimized PNG to be safe
            watermarked.save(image_path, format='PNG', optimize=True, compress_level=PNG_COMPRESSION)
        
        logger.info(f"✅ Watermark added to image: {image_path} (original mode: {original_mode}, format: {original_format})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to add watermark to {image_path}: {str(e)}")
        return False


def optimize_video(video_path: str) -> bool:
    """
    Optimize video by resizing to max 1920px and compressing
    Uses ffmpeg to reduce file size while maintaining quality
    
    Optimizations applied:
    - Resize to max 1920px width/height (maintains aspect ratio)
    - H.264 codec with CRF 23 (excellent quality, ~50-70% smaller)
    - 2Mbps bitrate cap for consistent quality
    
    Args:
        video_path: Path to the video file
        
    Returns:
        True if successful, False otherwise
    """
    import subprocess
    import shutil
    
    try:
        # Check if ffmpeg is available
        if not shutil.which('ffmpeg'):
            logger.warning("ffmpeg not found - skipping video optimization")
            return True
        
        # Get video dimensions using ffprobe
        probe_cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=p=0',
            video_path
        ]
        
        result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            logger.warning(f"Could not probe video dimensions: {video_path}")
            return True
        
        width, height = map(int, result.stdout.strip().split(','))
        logger.info(f"📹 Original video: {width}x{height}")
        
        # Check if resize needed
        needs_resize = width > MAX_VIDEO_WIDTH or height > MAX_VIDEO_HEIGHT
        
        # CRITICAL: libx264 requires even dimensions - always ensure this
        has_odd_dimensions = (width % 2 != 0) or (height % 2 != 0)
        
        # Calculate new dimensions if resize or odd dimensions
        if needs_resize:
            ratio = min(MAX_VIDEO_WIDTH / width, MAX_VIDEO_HEIGHT / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            # Ensure even dimensions (required for H.264)
            new_width = new_width - (new_width % 2)
            new_height = new_height - (new_height % 2)
            scale_filter = f"scale={new_width}:{new_height}"
            logger.info(f"📐 Resizing video to {new_width}x{new_height}")
        elif has_odd_dimensions:
            # Use ffmpeg formula to ensure even dimensions without resizing
            # trunc(iw/2)*2:trunc(ih/2)*2 rounds down to nearest even number
            scale_filter = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
            logger.info(f"📐 Normalizing odd dimensions to even (H.264 requirement)")
        else:
            scale_filter = None
            logger.info("📹 Video dimensions acceptable, compressing only")
        
        # Create temporary output file
        temp_output = str(Path(video_path).with_suffix('.tmp.mp4'))
        
        # Build ffmpeg command for optimization
        ffmpeg_cmd = [
            'ffmpeg', '-i', video_path,
            '-c:v', 'libx264',  # H.264 codec
            '-crf', str(VIDEO_CRF),  # Quality factor
            '-b:v', VIDEO_BITRATE,  # Max bitrate
            '-c:a', 'aac',  # Audio codec
            '-b:a', '128k',  # Audio bitrate
            '-movflags', '+faststart',  # Enable streaming
            '-y',  # Overwrite output
        ]
        
        # Add scale filter if needed (always use if present)
        if scale_filter:
            ffmpeg_cmd.extend(['-vf', scale_filter])
        
        # Add fallback pixel format to ensure compatibility
        ffmpeg_cmd.extend(['-pix_fmt', 'yuv420p'])
        
        ffmpeg_cmd.append(temp_output)
        
        # Run ffmpeg
        logger.info(f"🎬 Optimizing video with ffmpeg...")
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            logger.error(f"ffmpeg failed: {result.stderr}")
            # Clean up temp file if exists
            if os.path.exists(temp_output):
                os.remove(temp_output)
            return False
        
        # Replace original with optimized version
        original_size = os.path.getsize(video_path)
        optimized_size = os.path.getsize(temp_output)
        reduction = ((original_size - optimized_size) / original_size) * 100
        
        os.replace(temp_output, video_path)
        
        logger.info(f"✅ Video optimized: {original_size/1024/1024:.1f}MB → {optimized_size/1024/1024:.1f}MB ({reduction:.1f}% reduction)")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error(f"Video optimization timeout: {video_path}")
        return False
    except Exception as e:
        logger.error(f"Video optimization failed: {str(e)}")
        return False


def add_watermark_to_video(video_path: str) -> bool:
    """
    Optimize video (resize + compress) - watermarking videos requires complex ffmpeg filters
    For now, we optimize file size without adding visible watermark
    
    Args:
        video_path: Path to the video file
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"📹 Processing video: {video_path}")
    return optimize_video(video_path)


def process_media_watermark(file_path: str, file_type: str) -> bool:
    """
    Process media file and add watermark based on type
    
    Args:
        file_path: Path to the media file
        file_type: MIME type (e.g., 'image/jpeg', 'video/mp4')
        
    Returns:
        True if successful or skipped, False on error
    """
    if file_type.startswith('image/'):
        return add_watermark_to_image(file_path)
    elif file_type.startswith('video/'):
        return add_watermark_to_video(file_path)
    else:
        logger.warning(f"Unknown file type for watermarking: {file_type}")
        return True  # Don't fail for unknown types


# ===== Object Storage Support (Bytes-based processing) =====

def process_image_bytes(image_bytes: bytes, content_type: str) -> bytes:
    """
    Process image bytes: optimize and add watermark
    For Object Storage uploads
    
    Args:
        image_bytes: Raw image bytes
        content_type: MIME type (e.g., 'image/jpeg', 'image/png')
        
    Returns:
        Processed image bytes
    """
    import io
    
    try:
        if not LOGO_PATH.exists():
            logger.warning(f"Logo file not found: {LOGO_PATH} - returning original image")
            return image_bytes
        
        # Load image from bytes
        original_image = Image.open(io.BytesIO(image_bytes))
        original_mode = original_image.mode
        original_format = original_image.format or 'PNG'
        
        # Optimize: Resize oversized images
        if original_image.width > MAX_IMAGE_WIDTH or original_image.height > MAX_IMAGE_HEIGHT:
            ratio = min(MAX_IMAGE_WIDTH / original_image.width, MAX_IMAGE_HEIGHT / original_image.height)
            new_width = int(original_image.width * ratio)
            new_height = int(original_image.height * ratio)
            original_image = original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"📐 Resized image to {new_width}x{new_height}")
        
        # Load and prepare logo
        logo = Image.open(LOGO_PATH).convert("RGBA")
        aspect_ratio = logo.height / logo.width
        logo_height = int(LOGO_WIDTH * aspect_ratio)
        logo_resized = logo.resize((LOGO_WIDTH, logo_height), Image.Resampling.LANCZOS)
        
        # Apply opacity
        logo_with_opacity = Image.new("RGBA", logo_resized.size)
        for x in range(logo_resized.width):
            for y in range(logo_resized.height):
                r, g, b, a = logo_resized.getpixel((x, y))
                logo_with_opacity.putpixel((x, y), (r, g, b, int(a * LOGO_OPACITY)))
        
        # Convert to RGBA for compositing
        working_image = original_image.convert('RGBA') if original_image.mode != 'RGBA' else original_image
        
        # Calculate position (top-right corner)
        position = (working_image.width - LOGO_WIDTH - MARGIN, MARGIN)
        
        # Create overlay and composite
        overlay = Image.new('RGBA', working_image.size, (255, 255, 255, 0))
        overlay.paste(logo_with_opacity, position, logo_with_opacity)
        watermarked = Image.alpha_composite(working_image, overlay)
        
        # Convert back to original mode and save to bytes
        output = io.BytesIO()
        if original_mode == 'RGB':
            watermarked = watermarked.convert('RGB')
            watermarked.save(output, format='JPEG', quality=JPEG_QUALITY, optimize=True)
        elif original_mode == 'RGBA':
            watermarked.save(output, format='PNG', optimize=True, compress_level=PNG_COMPRESSION)
        elif original_mode in ('P', 'L', 'LA'):
            watermarked = watermarked.convert('RGB')
            watermarked.save(output, format='PNG', optimize=True, compress_level=PNG_COMPRESSION)
        else:
            watermarked.save(output, format='PNG', optimize=True, compress_level=PNG_COMPRESSION)
        
        logger.info(f"✅ Image processed with watermark (mode: {original_mode})")
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"❌ Failed to process image bytes: {str(e)}")
        return image_bytes  # Return original on error


def process_video_bytes(video_bytes: bytes, temp_filename: str) -> bytes:
    """
    Process video bytes: optimize with ffmpeg
    Requires temporary file since ffmpeg works with files
    
    Args:
        video_bytes: Raw video bytes
        temp_filename: Temporary filename hint (for extension)
        
    Returns:
        Processed video bytes
    """
    import tempfile
    import shutil
    
    try:
        # Check if ffmpeg is available
        if not shutil.which('ffmpeg'):
            logger.warning("ffmpeg not found - returning original video")
            return video_bytes
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix=Path(temp_filename).suffix, delete=False) as temp_input:
            temp_input.write(video_bytes)
            temp_input_path = temp_input.name
        
        # Optimize video
        success = optimize_video(temp_input_path)
        
        # Read back optimized video
        if success:
            with open(temp_input_path, 'rb') as f:
                optimized_bytes = f.read()
            
            # Cleanup
            os.unlink(temp_input_path)
            logger.info("✅ Video processed successfully")
            return optimized_bytes
        else:
            # Cleanup and return original
            os.unlink(temp_input_path)
            logger.warning("Video optimization failed - returning original")
            return video_bytes
            
    except Exception as e:
        logger.error(f"❌ Failed to process video bytes: {str(e)}")
        return video_bytes  # Return original on error


def process_media_bytes(file_bytes: bytes, content_type: str, filename: str) -> bytes:
    """
    Process media bytes and add watermark/optimization based on type
    For Object Storage uploads
    
    Args:
        file_bytes: Raw file bytes
        content_type: MIME type (e.g., 'image/jpeg', 'video/mp4')
        filename: Original filename (for extension hint)
        
    Returns:
        Processed file bytes
    """
    if content_type.startswith('image/'):
        return process_image_bytes(file_bytes, content_type)
    elif content_type.startswith('video/'):
        return process_video_bytes(file_bytes, filename)
    else:
        logger.warning(f"Unknown file type for processing: {content_type}")
        return file_bytes  # Return original for unknown types
