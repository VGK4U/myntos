"""
Profile and KYC File Upload Handler for EV Reference Program
Handles secure file uploads with type-specific size limits
"""

import os
import secrets
import magic
from datetime import datetime
from typing import Dict, Any, Optional
from PIL import Image
from werkzeug.utils import secure_filename

class ProfileFileHandler:
    """
    Secure file upload system for profile pictures and KYC documents
    
    Security Features:
    - Type-specific file size validation
    - MIME type validation (both extension and content)
    - Magic byte verification
    - Secure filename handling with random prefixes
    - Image re-encoding for security
    """
    
    # Profile Picture Configuration (500KB max)
    PROFILE_MAX_SIZE = 500 * 1024  # 500KB in bytes
    PROFILE_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    PROFILE_ALLOWED_MIMES = {'image/png', 'image/jpeg', 'image/jpg'}
    
    # KYC Document Configuration (1MB max)  
    KYC_MAX_SIZE = 1 * 1024 * 1024  # 1MB in bytes
    KYC_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
    KYC_ALLOWED_MIMES = {
        'image/png', 'image/jpeg', 'image/jpg', 'application/pdf'
    }
    
    # File signature validation
    FILE_SIGNATURES = {
        'png': [b'\x89PNG\r\n\x1a\n'],
        'jpg': [b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\xff\xd8\xff\xee', b'\xff\xd8\xff\xdb'],
        'jpeg': [b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\xff\xd8\xff\xee', b'\xff\xd8\xff\xdb'],
        'pdf': [b'%PDF-']
    }
    
    @classmethod
    def validate_profile_picture(cls, file) -> Dict[str, Any]:
        """
        Validate profile picture upload (500KB max, PNG/JPG only)
        
        Args:
            file: FileStorage object from Flask request
            
        Returns:
            dict: Validation result with status and details
        """
        return cls._validate_file(
            file=file,
            max_size=cls.PROFILE_MAX_SIZE,
            allowed_extensions=cls.PROFILE_ALLOWED_EXTENSIONS,
            allowed_mimes=cls.PROFILE_ALLOWED_MIMES,
            file_type="profile picture"
        )
    
    @classmethod  
    def validate_kyc_document(cls, file) -> Dict[str, Any]:
        """
        Validate KYC document upload (1MB max, PNG/JPG/PDF)
        
        Args:
            file: FileStorage object from Flask request
            
        Returns:
            dict: Validation result with status and details
        """
        return cls._validate_file(
            file=file,
            max_size=cls.KYC_MAX_SIZE,
            allowed_extensions=cls.KYC_ALLOWED_EXTENSIONS,
            allowed_mimes=cls.KYC_ALLOWED_MIMES,
            file_type="KYC document"
        )
    
    @classmethod
    def _validate_file(cls, file, max_size: int, allowed_extensions: set, 
                      allowed_mimes: set, file_type: str) -> Dict[str, Any]:
        """
        Internal file validation logic
        
        Args:
            file: FileStorage object
            max_size: Maximum file size in bytes
            allowed_extensions: Set of allowed file extensions
            allowed_mimes: Set of allowed MIME types
            file_type: Description for error messages
            
        Returns:
            dict: Validation result
        """
        try:
            # Check if file exists
            if not file or not file.filename:
                return {
                    'valid': False,
                    'error': f'No {file_type} provided',
                    'error_type': 'missing_file'
                }
            
            # Get file extension
            filename = file.filename.lower()
            if '.' not in filename:
                return {
                    'valid': False,
                    'error': f'{file_type.title()} must have a file extension',
                    'error_type': 'no_extension'
                }
            
            file_ext = filename.rsplit('.', 1)[1]
            
            # Validate file extension
            if file_ext not in allowed_extensions:
                return {
                    'valid': False,
                    'error': f'{file_type.title()} type .{file_ext} not allowed. Allowed: {", ".join(allowed_extensions)}',
                    'error_type': 'invalid_extension'
                }
            
            # Check file size
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset to beginning
            
            if file_size == 0:
                return {
                    'valid': False,
                    'error': f'{file_type.title()} cannot be empty',
                    'error_type': 'empty_file'
                }
            
            if file_size > max_size:
                max_size_kb = max_size / 1024
                file_size_kb = file_size / 1024
                return {
                    'valid': False,
                    'error': f'{file_type.title()} size {file_size_kb:.1f}KB exceeds maximum {max_size_kb:.0f}KB',
                    'error_type': 'file_too_large'
                }
            
            # Validate MIME type using python-magic
            file_content = file.read(2048)
            file.seek(0)
            mime_type = magic.from_buffer(file_content, mime=True)
            
            if mime_type not in allowed_mimes:
                return {
                    'valid': False,
                    'error': f'Invalid {file_type} format. Expected: {", ".join(allowed_mimes)}, got: {mime_type}',
                    'error_type': 'invalid_mime'
                }
            
            # Validate file signature (magic bytes)
            file_header = file.read(16)
            file.seek(0)
            
            signature_valid = False
            if file_ext in cls.FILE_SIGNATURES:
                for signature in cls.FILE_SIGNATURES[file_ext]:
                    if file_header.startswith(signature):
                        signature_valid = True
                        break
            
            if not signature_valid:
                return {
                    'valid': False,
                    'error': f'Invalid {file_type} file format (signature mismatch)',
                    'error_type': 'invalid_signature'
                }
            
            # For images, validate using Pillow and get dimensions
            image_info = None
            if file_ext in ['png', 'jpg', 'jpeg']:
                try:
                    image = Image.open(file)
                    width, height = image.size
                    image_info = {
                        'width': width,
                        'height': height,
                        'dimensions': f"{width}x{height}"
                    }
                    file.seek(0)
                except Exception as e:
                    return {
                        'valid': False,
                        'error': f'Invalid image file: {str(e)}',
                        'error_type': 'invalid_image'
                    }
            
            # Return success with file info
            return {
                'valid': True,
                'file_info': {
                    'size_bytes': file_size,
                    'size_kb': round(file_size / 1024, 1),
                    'mime_type': mime_type,
                    'extension': file_ext,
                    'original_filename': file.filename,
                    'image_info': image_info
                }
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Unexpected error validating {file_type}: {str(e)}',
                'error_type': 'validation_exception'
            }
    
    @classmethod
    def save_profile_picture(cls, file, user_id: int) -> Dict[str, Any]:
        """
        Save profile picture with security processing
        
        Args:
            file: Validated FileStorage object
            user_id: User ID for directory organization
            
        Returns:
            dict: Save result with file details
        """
        try:
            # Validate first
            validation = cls.validate_profile_picture(file)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': validation['error'],
                    'error_type': validation['error_type']
                }
            
            file_info = validation['file_info']
            
            # Generate secure filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            random_id = secrets.token_hex(8)
            file_ext = file_info['extension']
            secure_name = f"profile_{timestamp}_{random_id}_{user_id}.{file_ext}"
            
            # Create upload directory
            year_month = datetime.now().strftime('%Y/%m')
            upload_dir = os.path.join('static', 'uploads', 'profiles', year_month)
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, secure_name)
            
            # Re-encode image for security (removes potential exploits)
            if file_ext in ['png', 'jpg', 'jpeg']:
                image = Image.open(file)
                # Convert to RGB if necessary
                if image.mode in ('RGBA', 'LA', 'P'):
                    image = image.convert('RGB')
                # Save with compression
                save_format = 'PNG' if file_ext == 'png' else 'JPEG'
                image.save(file_path, format=save_format, quality=85 if save_format == 'JPEG' else None)
            else:
                file.save(file_path)
            
            return {
                'success': True,
                'file_path': file_path,
                'relative_path': file_path.replace('static/', ''),
                'secure_filename': secure_name,
                'file_info': file_info
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error saving profile picture: {str(e)}',
                'error_type': 'save_exception'
            }
    
    @classmethod
    def save_kyc_document(cls, file, user_id: int, document_type: str) -> Dict[str, Any]:
        """
        Save KYC document with security processing
        
        Args:
            file: Validated FileStorage object  
            user_id: User ID for directory organization
            document_type: Type of KYC document
            
        Returns:
            dict: Save result with file details
        """
        try:
            # Validate first
            validation = cls.validate_kyc_document(file)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': validation['error'],
                    'error_type': validation['error_type']
                }
            
            file_info = validation['file_info']
            
            # Generate secure filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            random_id = secrets.token_hex(8)
            file_ext = file_info['extension']
            secure_name = f"kyc_{document_type}_{timestamp}_{random_id}.{file_ext}"
            
            # Create secure upload directory (outside static to prevent public access)
            year_month = datetime.now().strftime('%Y/%m')
            upload_dir = os.path.join('uploads', 'kyc_secure', year_month)
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, secure_name)
            
            # Handle different file types
            if file_ext in ['png', 'jpg', 'jpeg']:
                # Re-encode images for security
                image = Image.open(file)
                if image.mode in ('RGBA', 'LA', 'P'):
                    image = image.convert('RGB')
                save_format = 'PNG' if file_ext == 'png' else 'JPEG'
                image.save(file_path, format=save_format, quality=85 if save_format == 'JPEG' else None)
            else:
                # Save PDF directly (already validated)
                file.save(file_path)
            
            return {
                'success': True,
                'file_path': file_path,
                'relative_path': file_path.replace('static/', ''),
                'secure_filename': secure_name,
                'file_info': file_info,
                'document_type': document_type
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error saving KYC document: {str(e)}',
                'error_type': 'save_exception'
            }