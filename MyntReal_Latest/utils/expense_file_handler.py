# Secure File Upload System for Expense Bill Copies
import os
import uuid
import magic
import hashlib
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest
from flask import current_app, flash
from typing import Optional, Tuple, Dict, Any

class ExpenseFileHandler:
    """
    Comprehensive secure file upload system for expense bill copies
    
    Security Features:
    - File size validation (1MB max)
    - MIME type validation (both extension and content)
    - Secure filename handling with random prefixes
    - Directory traversal prevention
    - Organized storage structure (uploads/expenses/YYYY/MM/)
    """
    
    # Configuration
    MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB in bytes
    ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}  # WEBP removed for security
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'image/jpeg', 
        'image/jpg',
        'image/png'
        # WEBP removed for security compliance
    }
    
    # Magic number validation as fallback (file signature validation)
    FILE_SIGNATURES = {
        'pdf': [b'%PDF-'],
        'jpg': [b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\xff\xd8\xff\xee', b'\xff\xd8\xff\xdb'],
        'jpeg': [b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\xff\xd8\xff\xee', b'\xff\xd8\xff\xdb'],
        'png': [b'\x89PNG\r\n\x1a\n']
    }
    BASE_UPLOAD_PATH = 'uploads/expenses'
    
    @classmethod
    def validate_expense_file(cls, file) -> Dict[str, Any]:
        """
        Comprehensive file validation for expense bill uploads
        
        Args:
            file: FileStorage object from Flask request
            
        Returns:
            dict: Validation result with status and details
            
        Security Validations:
        - File presence and non-zero size
        - File size limit (1MB)
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
                    'error': 'File must have an extension',
                    'error_type': 'no_extension'
                }
            
            file_ext = filename.rsplit('.', 1)[1]
            
            # Validate file extension
            if file_ext not in cls.ALLOWED_EXTENSIONS:
                return {
                    'valid': False,
                    'error': f'File type .{file_ext} not allowed. Allowed: {", ".join(cls.ALLOWED_EXTENSIONS)}',
                    'error_type': 'invalid_extension'
                }
            
            # Check file size
            file.seek(0, 2)  # Seek to end to get file size
            file_size = file.tell()
            file.seek(0)  # Reset to beginning
            
            if file_size == 0:
                return {
                    'valid': False,
                    'error': 'File cannot be empty',
                    'error_type': 'empty_file'
                }
            
            if file_size > cls.MAX_FILE_SIZE:
                size_mb = cls.MAX_FILE_SIZE / (1024 * 1024)
                return {
                    'valid': False,
                    'error': f'File size ({cls._format_file_size(file_size)}) exceeds maximum allowed size ({size_mb:.1f}MB)',
                    'error_type': 'file_too_large'
                }
            
            # ENHANCED SECURITY: Comprehensive file content validation
            # Primary: python-magic MIME detection
            detected_mime = None
            magic_validation_passed = False
            
            try:
                # Read first 2KB for MIME detection (sufficient for most file types)
                file_header = file.read(2048)
                file.seek(0)  # Reset after reading
                
                # Detect MIME type from file content using python-magic
                detected_mime = magic.from_buffer(file_header, mime=True)
                
                if detected_mime not in cls.ALLOWED_MIME_TYPES:
                    return {
                        'valid': False,
                        'error': f'Invalid file type detected: {detected_mime}. File content does not match allowed types.',
                        'error_type': 'invalid_mime_type'
                    }
                
                # Additional security: Check if extension matches detected MIME type
                expected_mimes = cls._get_expected_mime_types(file_ext)
                if detected_mime not in expected_mimes:
                    return {
                        'valid': False,
                        'error': f'File extension .{file_ext} does not match detected file type {detected_mime}. Possible file spoofing attempt.',
                        'error_type': 'mime_extension_mismatch'
                    }
                
                magic_validation_passed = True
                print(f"✅ python-magic validation passed: {file_ext} -> {detected_mime}")
                    
            except Exception as e:
                print(f"⚠️  python-magic MIME detection failed: {str(e)}. Falling back to magic number validation.")
                # FALLBACK: Magic number validation (file signature validation)
                magic_validation_passed = False
                
            # CRITICAL SECURITY: If python-magic fails, use magic number validation as fallback
            if not magic_validation_passed:
                file.seek(0)  # Reset to beginning
                file_header = file.read(16)  # Read first 16 bytes for magic number detection
                file.seek(0)  # Reset after reading
                
                # Validate using magic numbers (file signatures)
                magic_number_valid = cls._validate_magic_numbers(file_header, file_ext)
                
                if not magic_number_valid:
                    return {
                        'valid': False,
                        'error': f'File signature validation failed. File does not appear to be a valid {file_ext.upper()} file. Possible file spoofing attempt.',
                        'error_type': 'invalid_file_signature'
                    }
                
                # Use fallback MIME type
                detected_mime = cls._get_mime_from_extension(file_ext)
                print(f"✅ Magic number validation passed: {file_ext} (fallback MIME: {detected_mime})")
            
            # File is valid
            return {
                'valid': True,
                'file_size': file_size,
                'file_extension': file_ext,
                'detected_mime': detected_mime,
                'human_size': cls._format_file_size(file_size)
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'File validation error: {str(e)}',
                'error_type': 'validation_exception'
            }
    
    @classmethod
    def upload_expense_bill(cls, file, expense_id: int) -> Dict[str, Any]:
        """
        Handle secure expense bill file upload
        
        Args:
            file: FileStorage object
            expense_id: ID of the expense record
            
        Returns:
            dict: Upload result with file info or error
        """
        try:
            # Validate the file first
            validation = cls.validate_expense_file(file)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': validation['error'],
                    'error_type': validation['error_type']
                }
            
            # Generate secure filename with random prefix
            original_filename = secure_filename(file.filename)
            file_ext = validation['file_extension']
            
            # Create unique filename: timestamp_uuid_expenseID_originalname
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]  # Short UUID
            safe_filename = f"{timestamp}_{unique_id}_exp{expense_id}_{original_filename}"
            
            # Create directory structure: uploads/expenses/YYYY/MM/
            upload_date = datetime.now()
            year_month_path = f"{upload_date.year}/{upload_date.month:02d}"
            full_directory = os.path.join(cls.BASE_UPLOAD_PATH, year_month_path)
            
            # Ensure directory exists
            os.makedirs(full_directory, exist_ok=True)
            
            # Full file path
            file_path = os.path.join(full_directory, safe_filename)
            
            # Save the file
            file.save(file_path)
            
            # Calculate file hash for integrity verification
            file_hash = cls._calculate_file_hash(file_path)
            
            # Return success info
            return {
                'success': True,
                'filename': safe_filename,
                'file_path': file_path,
                'relative_path': os.path.join(year_month_path, safe_filename),
                'file_size': validation['file_size'],
                'mime_type': validation['detected_mime'],
                'file_hash': file_hash,
                'human_size': validation['human_size']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}',
                'error_type': 'upload_exception'
            }
    
    @classmethod
    def finalize_expense_upload(cls, temp_file_info: Dict[str, Any], final_expense_id: int) -> Dict[str, Any]:
        """
        Finalize expense bill upload by moving temp file to final location with expense ID
        
        Args:
            temp_file_info: Result dict from upload_expense_bill() with temp filename
            final_expense_id: The real expense ID from database
            
        Returns:
            dict: Success/error info with finalized file details
        """
        try:
            if not temp_file_info or not temp_file_info.get('success'):
                return {
                    'success': False,
                    'error': 'Invalid temp file info provided',
                    'error_type': 'invalid_temp_info'
                }
            
            # Extract temp file details
            temp_file_path = temp_file_info['file_path']
            temp_relative_path = temp_file_info['relative_path']
            original_filename = temp_file_info.get('original_filename', 'unknown')
            
            if not os.path.exists(temp_file_path):
                return {
                    'success': False,
                    'error': f'Temporary file not found: {temp_file_path}',
                    'error_type': 'temp_file_missing'
                }
            
            # Parse temp filename to extract components
            temp_filename = os.path.basename(temp_file_path)
            
            # Extract timestamp and file extension from temp filename
            # Format: timestamp_uuid_tempID_originalname.ext
            parts = temp_filename.split('_')
            if len(parts) < 4:
                return {
                    'success': False,
                    'error': f'Invalid temp filename format: {temp_filename}',
                    'error_type': 'invalid_temp_format'
                }
            
            timestamp = parts[0]
            unique_id = parts[1] 
            # parts[2] is the temp ID, skip it
            # Reconstruct original name from remaining parts
            original_parts = parts[3:]  # Everything after tempID
            reconstructed_original = '_'.join(original_parts)
            
            # Create final filename with real expense ID
            final_filename = f"{timestamp}_{unique_id}_exp{final_expense_id}_{reconstructed_original}"
            
            # Get directory from temp path (preserve year/month structure)
            temp_dir = os.path.dirname(temp_file_path)
            final_file_path = os.path.join(temp_dir, final_filename)
            
            # Move file from temp location to final location
            os.rename(temp_file_path, final_file_path)
            
            # Calculate relative path for database storage
            # Extract year/month from temp_relative_path
            year_month_path = os.path.dirname(temp_relative_path)  # e.g., "2025/09"
            final_relative_path = os.path.join(year_month_path, final_filename)
            
            # Verify file integrity after move
            if not os.path.exists(final_file_path):
                return {
                    'success': False,
                    'error': 'File move operation failed - final file not found',
                    'error_type': 'move_failed'
                }
            
            print(f"✅ File finalized: {temp_file_path} → {final_file_path}")
            
            return {
                'success': True,
                'final_filename': final_filename,
                'final_file_path': final_file_path,
                'final_relative_path': final_relative_path,
                'original_temp_path': temp_file_path,
                'file_size': temp_file_info['file_size'],
                'mime_type': temp_file_info['mime_type'],
                'file_hash': temp_file_info.get('file_hash'),
                'human_size': temp_file_info['human_size']
            }
            
        except OSError as e:
            return {
                'success': False,
                'error': f'File system error during finalization: {str(e)}',
                'error_type': 'filesystem_error'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error during file finalization: {str(e)}',
                'error_type': 'finalization_exception'
            }
    
    @classmethod
    def cleanup_temp_file(cls, temp_file_info: Dict[str, Any]) -> bool:
        """
        Clean up temporary expense bill file in case of errors
        
        Args:
            temp_file_info: Result dict from upload_expense_bill()
            
        Returns:
            bool: True if cleanup successful, False if failed
        """
        try:
            if not temp_file_info or not temp_file_info.get('success'):
                print("⚠️  No temp file to cleanup or invalid temp file info")
                return True  # Nothing to cleanup is considered success
            
            temp_file_path = temp_file_info.get('file_path')
            if not temp_file_path:
                print("⚠️  No temp file path to cleanup")
                return True
            
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                print(f"🗑️  Cleaned up temp file: {temp_file_path}")
                return True
            else:
                print(f"ℹ️  Temp file already removed or never existed: {temp_file_path}")
                return True  # Already cleaned up
                
        except OSError as e:
            print(f"❌ Error cleaning up temp file: {str(e)}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error during temp file cleanup: {str(e)}")
            return False
    
    @classmethod
    def upload_expense_bill_with_temp_id(cls, file, temp_id: str) -> Dict[str, Any]:
        """
        Upload expense bill with temporary ID for two-phase atomic operations
        
        Args:
            file: FileStorage object
            temp_id: Temporary identifier for the file
            
        Returns:
            dict: Upload result with temp file info
        """
        try:
            # Validate the file first
            validation = cls.validate_expense_file(file)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': validation['error'],
                    'error_type': validation['error_type']
                }
            
            # Generate secure filename with temp ID
            original_filename = secure_filename(file.filename)
            file_ext = validation['file_extension']
            
            # Store original filename for later reconstruction
            # Create unique filename: timestamp_uuid_tempID_originalname
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]  # Short UUID
            safe_filename = f"{timestamp}_{unique_id}_{temp_id}_{original_filename}"
            
            # Create directory structure: uploads/expenses/YYYY/MM/
            upload_date = datetime.now()
            year_month_path = f"{upload_date.year}/{upload_date.month:02d}"
            full_directory = os.path.join(cls.BASE_UPLOAD_PATH, year_month_path)
            
            # Ensure directory exists
            os.makedirs(full_directory, exist_ok=True)
            
            # Full file path
            file_path = os.path.join(full_directory, safe_filename)
            
            # Save the file
            file.save(file_path)
            
            # Calculate file hash for integrity verification
            file_hash = cls._calculate_file_hash(file_path)
            
            # Return success info with temp details
            return {
                'success': True,
                'filename': safe_filename,
                'file_path': file_path,
                'relative_path': os.path.join(year_month_path, safe_filename),
                'file_size': validation['file_size'],
                'mime_type': validation['detected_mime'],
                'file_hash': file_hash,
                'human_size': validation['human_size'],
                'original_filename': original_filename,
                'temp_id': temp_id,
                'timestamp': timestamp,
                'unique_id': unique_id
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Temp upload failed: {str(e)}',
                'error_type': 'temp_upload_exception'
            }
    
    @classmethod
    def get_expense_bill_path(cls, filename: str) -> str:
        """
        Get secure file path for expense bill
        
        Args:
            filename: The stored filename (includes path structure)
            
        Returns:
            str: Full system path to the file
        """
        # Prevent directory traversal
        safe_filename = os.path.basename(filename)
        
        # If filename includes path structure, use it
        if '/' in filename:
            return os.path.join(cls.BASE_UPLOAD_PATH, filename)
        else:
            # Legacy support: search for file in directory structure
            return cls._find_file_in_structure(safe_filename)
    
    @classmethod
    def delete_expense_bill(cls, filename: str) -> bool:
        """
        Securely delete expense bill file
        
        Args:
            filename: The filename to delete
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            file_path = cls.get_expense_bill_path(filename)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
                # Try to remove empty directories (cleanup)
                dir_path = os.path.dirname(file_path)
                try:
                    os.rmdir(dir_path)  # Only removes if empty
                except OSError:
                    pass  # Directory not empty, that's fine
                
                return True
            
            return False
            
        except Exception as e:
            print(f"Error deleting file {filename}: {str(e)}")
            return False
    
    @classmethod
    def verify_file_integrity(cls, file_path: str, expected_hash: str) -> bool:
        """
        Verify file integrity using hash comparison
        
        Args:
            file_path: Path to the file
            expected_hash: Expected SHA-256 hash
            
        Returns:
            bool: True if file integrity is verified
        """
        try:
            if not os.path.exists(file_path):
                return False
                
            current_hash = cls._calculate_file_hash(file_path)
            return current_hash == expected_hash
            
        except Exception:
            return False
    
    # Private helper methods
    
    @classmethod
    def _format_file_size(cls, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    @classmethod
    def _get_expected_mime_types(cls, file_ext: str) -> set:
        """Get expected MIME types for a file extension"""
        mime_mapping = {
            'pdf': {'application/pdf'},
            'jpg': {'image/jpeg', 'image/jpg'},
            'jpeg': {'image/jpeg', 'image/jpg'},
            'png': {'image/png'}
            # WEBP removed for security compliance
        }
        return mime_mapping.get(file_ext.lower(), set())
    
    @classmethod
    def _get_mime_from_extension(cls, file_ext: str) -> str:
        """Fallback MIME type detection from extension"""
        mime_mapping = {
            'pdf': 'application/pdf',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg', 
            'png': 'image/png'
            # WEBP removed for security compliance
        }
        return mime_mapping.get(file_ext.lower(), 'application/octet-stream')
    
    @classmethod
    def _calculate_file_hash(cls, file_path: str) -> str:
        """Calculate SHA-256 hash of file for integrity verification"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    @classmethod
    def _validate_magic_numbers(cls, file_header: bytes, file_ext: str) -> bool:
        """
        CRITICAL SECURITY: Validate file using magic numbers (file signatures)
        This serves as a fallback when python-magic is not available
        
        Args:
            file_header: First 16 bytes of the file
            file_ext: File extension
            
        Returns:
            bool: True if file signature matches extension
        """
        try:
            file_ext = file_ext.lower()
            
            if file_ext not in cls.FILE_SIGNATURES:
                print(f"❌ Unknown file extension for magic number validation: {file_ext}")
                return False
            
            # Check if file header matches any of the expected signatures
            expected_signatures = cls.FILE_SIGNATURES[file_ext]
            
            for signature in expected_signatures:
                if file_header.startswith(signature):
                    print(f"✅ Magic number validation passed: {file_ext} (signature: {signature.hex()})")
                    return True
            
            print(f"❌ Magic number validation failed: {file_ext} header {file_header[:8].hex()} does not match expected signatures")
            return False
            
        except Exception as e:
            print(f"❌ Error during magic number validation: {str(e)}")
            return False
    
    @classmethod
    def _find_file_in_structure(cls, filename: str) -> Optional[str]:
        """Find file in directory structure (for legacy support)"""
        base_path = cls.BASE_UPLOAD_PATH
        
        if not os.path.exists(base_path):
            return None
        
        # Search in year/month subdirectories
        for root, dirs, files in os.walk(base_path):
            if filename in files:
                return os.path.join(root, filename)
        
        return None


# Role-based file access control
class ExpenseFileAccess:
    """
    Role-based access control for expense bill downloads
    """
    
    @classmethod
    def user_can_download_expense_bill(cls, user, expense) -> Tuple[bool, str]:
        """
        Check if user can download expense bill
        
        Args:
            user: Current user object
            expense: Expense object
            
        Returns:
            tuple: (can_download: bool, reason: str)
        """
        if not user or not user.is_authenticated:
            return False, "Authentication required"
        
        # Super Admin can download all bills
        if user.user_type == 'Super Admin':
            return True, "Super Admin access"
        
        # Finance Admin can download bills they created
        if user.user_type == 'Finance Admin' and expense.created_by_id == user.id:
            return True, "Created by current Finance Admin"
        
        # All other roles denied
        return False, f"Access denied for {user.user_type}"
    
    @classmethod
    def get_download_permissions_summary(cls, user) -> Dict[str, Any]:
        """
        Get summary of download permissions for user
        
        Args:
            user: User object
            
        Returns:
            dict: Permission summary
        """
        if not user or not user.is_authenticated:
            return {
                'can_download_any': False,
                'role': 'Unauthenticated',
                'permissions': []
            }
        
        if user.user_type == 'Super Admin':
            return {
                'can_download_any': True,
                'role': 'Super Admin',
                'permissions': ['Download all expense bills', 'Full access to all records']
            }
        
        if user.user_type == 'Finance Admin':
            return {
                'can_download_any': True,
                'role': 'Finance Admin',
                'permissions': ['Download bills for expenses they created']
            }
        
        return {
            'can_download_any': False,
            'role': user.user_type,
            'permissions': ['No expense bill download access']
        }