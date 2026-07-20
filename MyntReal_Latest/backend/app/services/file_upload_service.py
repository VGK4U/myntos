"""
File Upload Service for Profile & KYC Documents
Handles file validation, storage, and size/format checks
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException
from datetime import datetime
import uuid

class FileUploadService:
    """Service for handling file uploads with validation"""
    
    # File size limits (in bytes)
    PROFILE_PHOTO_MAX_SIZE = 500 * 1024  # 500 KB
    KYC_DOCUMENT_MAX_SIZE = 1024 * 1024  # 1 MB
    
    # Allowed formats
    IMAGE_FORMATS = {'jpg', 'jpeg', 'png'}
    DOCUMENT_FORMATS = {'jpg', 'jpeg', 'png', 'pdf'}
    
    # Upload directories
    BASE_UPLOAD_DIR = Path("uploaded_files")
    PROFILE_PHOTO_DIR = BASE_UPLOAD_DIR / "profile_photos"
    KYC_DOCUMENTS_DIR = BASE_UPLOAD_DIR / "kyc_documents"
    
    def __init__(self):
        """Initialize upload directories"""
        self.PROFILE_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
        self.KYC_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    
    def validate_file_size(self, file: UploadFile, max_size: int, file_type: str) -> None:
        """Validate file size"""
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
        Save profile photo with validation
        Max size: 500 KB, Formats: JPG, PNG
        """
        # Validate size
        self.validate_file_size(file, self.PROFILE_PHOTO_MAX_SIZE, "Profile photo")
        
        # Validate format
        ext = self.validate_file_format(file.filename, self.IMAGE_FORMATS)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{user_id}_{timestamp}.{ext}"
        file_path = self.PROFILE_PHOTO_DIR / unique_filename
        
        # Save file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        return {
            "file_path": str(file_path),
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
        Save KYC document with validation
        Max size: 1 MB, Formats: JPG, PNG, PDF
        """
        # Validate size
        self.validate_file_size(file, self.KYC_DOCUMENT_MAX_SIZE, "KYC document")
        
        # Validate format
        ext = self.validate_file_format(file.filename, self.DOCUMENT_FORMATS)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{user_id}_{document_type}_{timestamp}.{ext}"
        file_path = self.KYC_DOCUMENTS_DIR / unique_filename
        
        # Save file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        return {
            "file_path": str(file_path),
            "file_name": unique_filename,
            "file_size": file_size,
            "file_format": ext
        }
    
    def delete_file(self, file_path: str) -> bool:
        """Delete a file if it exists"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False
