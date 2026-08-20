"""
File Upload Service for Profile & KYC Documents
Handles file validation, storage, and size/format checks
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException
from datetime import datetime
import uuid
from app.services.s3_storage import s3_storage_service

class FileUploadService:
    """Service for handling file uploads with validation and AWS S3 storage"""
    
    # File size limits (in bytes)
    PROFILE_PHOTO_MAX_SIZE = 500 * 1024  # 500 KB
    KYC_DOCUMENT_MAX_SIZE = 1024 * 1024  # 1 MB
    
    # Allowed formats
    IMAGE_FORMATS = {'jpg', 'jpeg', 'png'}
    DOCUMENT_FORMATS = {'jpg', 'jpeg', 'png', 'pdf'}
    
    def __init__(self):
        """Initialize upload service"""
        pass
    
    def validate_file_size(self, file: UploadFile, max_size: int, file_type: str) -> int:
        """Validate file size and return it"""
        # Read file to check size
        file.file.seek(0, 2)  # Move to end of file
        file_size = file.file.tell()  # Get current position (file size)
        file.file.seek(0)  # Reset to beginning
        
        if file_size > max_size:
            max_size_kb = max_size / 1024
            raise HTTPException(
                status_code=400,
                detail=f"{file_type} exceeds maximum size of {max_size_kb:.0f} KB"
            )
        return file_size
    
    def validate_file_format(self, filename: str, allowed_formats: set) -> str:
        """Validate and return file extension"""
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        
        if ext not in allowed_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file format. Allowed: {', '.join(allowed_formats).upper()}"
            )
        
        return ext
    
    async def save_profile_photo(
        self,
        file: UploadFile,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Save profile photo to AWS S3
        Max size: 500 KB, Formats: JPG, PNG
        """
        # Validate size
        file_size = self.validate_file_size(file, self.PROFILE_PHOTO_MAX_SIZE, "Profile photo")
        
        # Validate format
        ext = self.validate_file_format(file.filename, self.IMAGE_FORMATS)
        
        # Generate unique filename and S3 key
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{user_id}_{timestamp}.{ext}"
        s3_key = f"profile_photos/{unique_filename}"
        
        # Read file into memory and upload to S3
        try:
            file_data = file.file.read()
            success = s3_storage_service.upload_file(s3_key, file_data)
            if not success:
                raise Exception("AWS S3 upload rejected")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file to S3: {str(e)}")
        finally:
            file.file.seek(0)
        
        return {
            "file_path": s3_key,
            "file_name": unique_filename,
            "file_size": file_size,
            "file_format": ext
        }
    
    async def save_kyc_document(
        self,
        file: UploadFile,
        user_id: str,
        document_type: str
    ) -> Dict[str, Any]:
        """
        Save KYC document to AWS S3
        Max size: 1 MB, Formats: JPG, PNG, PDF
        """
        # Validate size
        file_size = self.validate_file_size(file, self.KYC_DOCUMENT_MAX_SIZE, "KYC document")
        
        # Validate format
        ext = self.validate_file_format(file.filename, self.DOCUMENT_FORMATS)
        
        # Generate unique filename and S3 key
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{user_id}_{document_type}_{timestamp}.{ext}"
        s3_key = f"kyc_documents/{unique_filename}"
        
        # Read file into memory and upload to S3
        try:
            file_data = file.file.read()
            success = s3_storage_service.upload_file(s3_key, file_data)
            if not success:
                raise Exception("AWS S3 upload rejected")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file to S3: {str(e)}")
        finally:
            file.file.seek(0)
        
        return {
            "file_path": s3_key,
            "file_name": unique_filename,
            "file_size": file_size,
            "file_format": ext
        }
    
    def delete_file(self, file_path: str) -> bool:
        """Delete a file from AWS S3"""
        try:
            # First check if the file_path is actually a local path (legacy fallback)
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            
            # Otherwise, delete from S3
            return s3_storage_service.delete_file(file_path)
        except Exception:
            return False
