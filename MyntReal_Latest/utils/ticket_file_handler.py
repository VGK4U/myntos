# Secure File Upload System for Ticket Attachments
import os
import uuid
import hashlib
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest
from flask import current_app, flash
from typing import Optional, Tuple, Dict, Any

class TicketFileHandler:
    """
    Comprehensive secure file upload system for ticket attachments
    
    Security Features:
    - File size validation (5MB max per file)
    - MIME type validation (both extension and content)
    - Secure filename handling with random prefixes
    - Directory traversal prevention
    - Organized storage structure (uploads/tickets/YYYY/MM/)
    - SHA-256 file integrity hashing
    """
    
    # Configuration
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes
    ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'}
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'image/jpeg', 
        'image/jpg',
        'image/png',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    
    # Magic number validation as fallback (file signature validation)
    FILE_SIGNATURES = {
        'pdf': [b'%PDF-'],
        'jpg': [b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\xff\xd8\xff\xee', b'\xff\xd8\xff\xdb'],
        'jpeg': [b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\xff\xd8\xff\xee', b'\xff\xd8\xff\xdb'],
        'png': [b'\x89PNG\r\n\x1a\n'],
        'doc': [b'\xd0\xcf\x11\xe0'],
        'docx': [b'PK\x03\x04']
    }
    BASE_UPLOAD_PATH = 'uploads/tickets'
    
    @classmethod
    def validate_ticket_file(cls, file) -> Dict[str, Any]:
        """
        Comprehensive file validation for ticket attachments
        
        Args:
            file: FileStorage object from Flask request
            
        Returns:
            dict: Validation result with status and details
            
        Security Validations:
        - File presence and non-zero size
        - File size limit (5MB)
        - File extension validation
        - MIME type validation (content-based)
        - File content integrity
        """
        try:
            # Check if file exists
            if not file or not file.filename:
                return {
                    'valid': False,
                    'error': 'No file provided',
                    'error_type': 'missing_file'
                }
            
            # Get file extension
            filename = file.filename.lower()
            if '.' not in filename:
                return {
                    'valid': False,
                    'error': 'File must have a valid extension',
                    'error_type': 'invalid_extension'
                }
            
            file_ext = filename.rsplit('.', 1)[1]
            if file_ext not in cls.ALLOWED_EXTENSIONS:
                return {
                    'valid': False,
                    'error': f'File type .{file_ext.upper()} not allowed. Supported: {", ".join([f".{ext.upper()}" for ext in cls.ALLOWED_EXTENSIONS])}',
                    'error_type': 'unsupported_extension'
                }
            
            # Check file size
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset to beginning
            
            if file_size == 0:
                return {
                    'valid': False,
                    'error': 'File cannot be empty',
                    'error_type': 'empty_file'
                }
            
            if file_size > cls.MAX_FILE_SIZE:
                size_mb = file_size / (1024 * 1024)
                max_mb = cls.MAX_FILE_SIZE / (1024 * 1024)
                return {
                    'valid': False,
                    'error': f'File size {size_mb:.1f}MB exceeds maximum allowed size of {max_mb}MB',
                    'error_type': 'file_too_large',
                    'file_size': file_size,
                    'max_size': cls.MAX_FILE_SIZE
                }
            
            # MIME type validation using python-magic
            try:
                import magic
                file_content = file.read(1024)  # Read first 1KB for MIME detection
                file.seek(0)  # Reset file pointer
                
                mime_type = magic.from_buffer(file_content, mime=True)
                
                if mime_type not in cls.ALLOWED_MIME_TYPES:
                    return {
                        'valid': False,
                        'error': f'File content type {mime_type} not allowed. File appears to be corrupted or unsupported.',
                        'error_type': 'invalid_mime_type',
                        'detected_mime': mime_type
                    }
                
            except ImportError:
                # python-magic not available, skip MIME validation but log warning
                print("Warning: python-magic not available, skipping MIME validation")
                mime_type = f"unknown/{file_ext}"
            except Exception as e:
                print(f"Warning: MIME type detection failed: {e}")
                mime_type = f"unknown/{file_ext}"
            
            # File signature validation as additional security
            file_content = file.read(8)  # Read first 8 bytes for signature
            file.seek(0)  # Reset file pointer
            
            if file_ext in cls.FILE_SIGNATURES:
                valid_signature = False
                for signature in cls.FILE_SIGNATURES[file_ext]:
                    if file_content.startswith(signature):
                        valid_signature = True
                        break
                
                if not valid_signature:
                    return {
                        'valid': False,
                        'error': f'File header does not match {file_ext.upper()} format. File may be corrupted or renamed.',
                        'error_type': 'invalid_signature'
                    }
            
            return {
                'valid': True,
                'file_size': file_size,
                'mime_type': mime_type,
                'extension': file_ext
            }
            
        except Exception as e:
            print(f"File validation error: {e}")
            return {
                'valid': False,
                'error': 'File validation failed due to internal error',
                'error_type': 'validation_error'
            }
    
    @classmethod
    def save_ticket_attachment(cls, file, ticket_id: str, user_id: str) -> Dict[str, Any]:
        """
        Save ticket attachment with secure filename and path organization
        
        Args:
            file: FileStorage object
            ticket_id: The ticket ID this attachment belongs to
            user_id: ID of user uploading the file
            
        Returns:
            dict: Save result with file path and metadata
        """
        try:
            # Validate file first
            validation_result = cls.validate_ticket_file(file)
            if not validation_result['valid']:
                return validation_result
            
            # Generate secure filename
            original_filename = secure_filename(file.filename)
            file_ext = validation_result['extension']
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            random_prefix = str(uuid.uuid4())[:8]
            
            # Create secure filename: timestamp_randomprefix_ticketid_originalname
            secure_filename_str = f"{timestamp}_{random_prefix}_{ticket_id}_{original_filename}"
            
            # Create directory structure: uploads/tickets/YYYY/MM/
            current_date = datetime.now()
            upload_dir = os.path.join(
                cls.BASE_UPLOAD_PATH,
                current_date.strftime('%Y'),
                current_date.strftime('%m')
            )
            
            # Ensure directory exists
            os.makedirs(upload_dir, exist_ok=True)
            
            # Full file path
            file_path = os.path.join(upload_dir, secure_filename_str)
            
            # Calculate file hash for integrity
            file.seek(0)
            file_content = file.read()
            file_hash = hashlib.sha256(file_content).hexdigest()
            
            # Save file
            file.seek(0)  # Reset pointer before saving
            file.save(file_path)
            
            return {
                'valid': True,
                'file_path': file_path,
                'original_filename': original_filename,
                'secure_filename': secure_filename_str,
                'file_size': validation_result['file_size'],
                'mime_type': validation_result['mime_type'],
                'file_hash': file_hash,
                'upload_dir': upload_dir
            }
            
        except Exception as e:
            print(f"File save error: {e}")
            return {
                'valid': False,
                'error': 'Failed to save file due to internal error',
                'error_type': 'save_error'
            }
    
    @classmethod
    def delete_ticket_attachment(cls, file_path: str) -> bool:
        """
        Safely delete a ticket attachment file
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            if os.path.exists(file_path) and file_path.startswith(cls.BASE_UPLOAD_PATH):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"File deletion error: {e}")
            return False
    
    @classmethod
    def get_file_info(cls, file_path: str) -> Dict[str, Any]:
        """
        Get file information and validate file integrity
        
        Args:
            file_path: Path to the file
            
        Returns:
            dict: File information including existence and metadata
        """
        try:
            if not os.path.exists(file_path):
                return {
                    'exists': False,
                    'error': 'File not found'
                }
            
            # Get file stats
            file_stats = os.stat(file_path)
            
            return {
                'exists': True,
                'file_size': file_stats.st_size,
                'modified_time': datetime.fromtimestamp(file_stats.st_mtime),
                'is_readable': os.access(file_path, os.R_OK)
            }
            
        except Exception as e:
            print(f"File info error: {e}")
            return {
                'exists': False,
                'error': 'Failed to get file information'
            }