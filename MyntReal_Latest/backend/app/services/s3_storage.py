import io
import os
from typing import Optional
import boto3
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

class S3StorageService:
    """Service for handling file uploads/downloads with AWS S3"""
    
    def __init__(self):
        """Initialize S3 client using environment variables"""
        try:
            self.bucket_name = os.environ.get("AWS_S3_BUCKET_NAME")
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
                region_name=os.environ.get("AWS_REGION", "ap-south-2")
            )
            if not self.bucket_name:
                logger.error("❌ AWS_S3_BUCKET_NAME not found in environment variables")
            else:
                logger.info("✅ AWS S3 client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize S3 Storage: {e}")
            raise
    
    def upload_file(self, file_path: str, file_data: bytes) -> bool:
        """Upload file to S3 bucket"""
        try:
            # ENFORCE FORWARD SLASHES FOR ALL NEW UPLOADS
            # This prevents Windows-style backslashes from polluting S3 keys
            # and guarantees cross-platform consistency (Linux/Windows).
            s3_key = file_path.replace('\\', '/')
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_data
            )
            logger.info(f"✅ Uploaded to S3: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"❌ S3 Upload failed for {file_path}: {e}")
            return False
    
    def download_file(self, file_path: str) -> Optional[bytes]:
        """Download file from S3 bucket"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                # Windows migration fallback: S3 keys might use backslashes instead of forward slashes
                alt_path = file_path.replace('/', '\\')
                if alt_path != file_path:
                    try:
                        response = self.s3_client.get_object(
                            Bucket=self.bucket_name,
                            Key=alt_path
                        )
                        return response['Body'].read()
                    except ClientError:
                        pass
                logger.warning(f"⚠️ File not found in S3: {file_path}")
            else:
                logger.error(f"❌ S3 Download failed for {file_path}: {e}")
            return None
    
    def file_exists(self, file_path: str) -> bool:
        """Check if file exists in S3 bucket"""
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                alt_path = file_path.replace('/', '\\')
                if alt_path != file_path:
                    try:
                        self.s3_client.head_object(
                            Bucket=self.bucket_name,
                            Key=alt_path
                        )
                        return True
                    except ClientError:
                        pass
                return False
            logger.error(f"❌ S3 Existence check failed for {file_path}: {e}")
            return False
            
    def delete_file(self, file_path: str) -> bool:
        """Delete file from S3 bucket"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            logger.info(f"🗑️ Deleted from S3: {file_path}")
            return True
        except ClientError as e:
            logger.error(f"❌ S3 Delete failed for {file_path}: {e}")
            return False
            
    def list_files(self, prefix: str = "") -> list:
        """List files with optional prefix filter from S3"""
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            
            files = []
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        files.append(obj['Key'])
            return files
        except ClientError as e:
            logger.error(f"❌ S3 List failed for prefix '{prefix}': {e}")
            return []
            
    def get_file_url(self, file_path: str) -> str:
        """Get URL for accessing a file. Still routes through our backend /storage endpoint for now."""
        file_path = file_path.lstrip('/')
        return f"/storage/{file_path}"

# Global instance
s3_storage_service = S3StorageService()
