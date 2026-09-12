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
        """Initialize S3 client using environment variables with robust production fallback"""
        try:
            self.bucket_name = (
                os.environ.get("AWS_S3_BUCKET_NAME") or 
                os.environ.get("S3_BUCKET_NAME") or 
                "myntreal-media-vault"
            )
            if self.bucket_name == "None" or not self.bucket_name:
                self.bucket_name = "myntreal-media-vault"
            
            from botocore.config import Config
            region = os.environ.get("AWS_REGION", "ap-south-2")
            aws_key = os.environ.get("AWS_ACCESS_KEY_ID")
            aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
            
            from botocore.client import Config
            s3_config = Config(
                region_name=region,
                signature_version='s3v4',
                s3={'addressing_style': 'virtual'}
            )
            client_kwargs = {
                "region_name": region,
                "config": s3_config,
                "endpoint_url": f"https://s3.{region}.amazonaws.com"
            }
            if aws_key and aws_secret and aws_key != "None" and aws_secret != "None":
                client_kwargs["aws_access_key_id"] = aws_key
                client_kwargs["aws_secret_access_key"] = aws_secret
            
            self.s3_client = boto3.client('s3', **client_kwargs)
            logger.info(f"✅ AWS S3 client initialized for bucket: {self.bucket_name} in {region} with regional s3v4 endpoint")
        except Exception as e:
            logger.error(f"❌ Failed to initialize S3 Storage: {e}")
            raise
    
    def resolve_storage_key(self, raw_path: str) -> Optional[str]:
        """
        DC Protocol: Universal S3 key resolver.
        Resolves file keys across prefixes (private/, public/, uploads/, solar_docs/, etc.), 
        Windows legacy backslashes, and un-prefixed database paths.
        """
        if not self.bucket_name:
            return None
        if not raw_path or not isinstance(raw_path, str):
            return None
            
        p = raw_path.strip().lstrip('/').replace('\\', '/')
        while p.startswith('storage/'):
            p = p[len('storage/'):]
        while p.startswith('uploads/'):
            p = p[len('uploads/'):]
        if not p:
            return None

        candidates = []
        def _add(k: str):
            if k and k not in candidates:
                candidates.append(k)
            bk = k.replace('/', '\\')
            if bk and bk not in candidates:
                candidates.append(bk)

        _add(p)
        filename = p.split('/')[-1]

        if p.startswith('private/'):
            unpref = p[len('private/'):]
            _add(unpref)
            _add(f"public/{unpref}")
        elif p.startswith('public/'):
            unpref = p[len('public/'):]
            _add(unpref)
            _add(f"private/{unpref}")
        else:
            _add(f"private/{p}")
            _add(f"public/{p}")
        
        _add(f"uploads/{p}")

        # Document category prefixes for bare filenames or alternate directory conventions
        for cat in [
            "solar_docs", "kyc_documents", "invoices", "quotations", 
            "receipts", "documents", "crm_documents", "ev_docs", 
            "insurance_docs", "bank_docs", "staff_docs", "media", "announcements",
            "wa_media", "wa_media/meta", "wa_media/scanned"
        ]:
            _add(f"{cat}/{filename}")
            _add(f"private/{cat}/{filename}")
            _add(f"public/{cat}/{filename}")

        for cand in candidates:
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=cand)
                return cand
            except Exception:
                continue
        return None

    def upload_file(self, file_path: str, file_data: bytes, content_type: Optional[str] = None) -> bool:
        """Upload file to S3 bucket"""
        if not self.bucket_name:
            return False
        try:
            # ENFORCE FORWARD SLASHES FOR ALL NEW UPLOADS
            # This prevents Windows-style backslashes from polluting S3 keys
            # and guarantees cross-platform consistency (Linux/Windows).
            s3_key = file_path.replace('\\', '/').lstrip('/')
            
            put_kwargs = {
                "Bucket": self.bucket_name,
                "Key": s3_key,
                "Body": file_data
            }
            if content_type:
                put_kwargs["ContentType"] = content_type

            self.s3_client.put_object(**put_kwargs)
            logger.info(f"✅ Uploaded to S3: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"❌ S3 Upload failed for {file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ S3 Upload failed (unexpected error) for {file_path}: {e}")
            return False
    
    def download_file(self, file_path: str) -> Optional[bytes]:
        """Download file from S3 bucket with intelligent candidate resolution"""
        if not self.bucket_name:
            return None
        try:
            resolved_key = self.resolve_storage_key(file_path)
            target_key = resolved_key or file_path.replace('\\', '/').lstrip('/')
            
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=target_key
            )
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"⚠️ File not found in S3: {file_path}")
            elif e.response.get('Error', {}).get('Code') in ('InvalidAccessKeyId', 'SignatureDoesNotMatch', 'AccessDenied', 'NoCredentialsError'):
                logger.warning(f"⚠️ S3 Download skipped for {file_path} (AWS credentials not configured/valid in dev)")
            else:
                logger.error(f"❌ S3 Download failed for {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ S3 Download failed (unexpected error) for {file_path}: {e}")
            return None
    
    def file_exists(self, file_path: str) -> bool:
        """Check if file exists in S3 bucket using candidate resolution"""
        if not self.bucket_name:
            return False
        return self.resolve_storage_key(file_path) is not None
            
    def delete_file(self, file_path: str) -> bool:
        """Delete file from S3 bucket"""
        if not self.bucket_name:
            return False
        try:
            resolved_key = self.resolve_storage_key(file_path) or file_path.replace('\\', '/').lstrip('/')
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=resolved_key
            )
            logger.info(f"🗑️ Deleted from S3: {resolved_key}")
            return True
        except ClientError as e:
            logger.error(f"❌ S3 Delete failed for {file_path}: {e}")
            return False
            
    def list_files(self, prefix: str = "") -> list:
        """List files with optional prefix filter from S3"""
        if not self.bucket_name:
            return []
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
            
    def generate_presigned_url(self, file_path: str, expiration: int = 900) -> Optional[str]:
        """
        Generate presigned URL for private asset access (default: 15 minutes / 900 seconds)
        DC Protocol: Secure private S3 object access
        """
        if not self.bucket_name:
            return None
        try:
            s3_key = file_path.lstrip('/')
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"❌ Failed to generate presigned URL for {file_path}: {e}")
            return None

    def get_public_url(self, file_path: str) -> str:
        """
        Get public S3 URL for public assets (catalogs, branding, APK downloads)
        """
        s3_key = file_path.lstrip('/')
        region = os.environ.get("AWS_REGION", "ap-south-2")
        return f"https://{self.bucket_name}.s3.{region}.amazonaws.com/{s3_key}"

    def get_file_url(self, file_path: str, is_public: bool = False, expiration: int = 900) -> str:
        """
        Get URL for accessing a file: resolves key and returns S3 presigned URL for private, S3 direct URL for public
        """
        if not file_path:
            return ""
        resolved_key = self.resolve_storage_key(file_path) or file_path.lstrip('/')
        if is_public or resolved_key.startswith("public/") or resolved_key.startswith("public\\"):
            return self.get_public_url(resolved_key)
        elif self.bucket_name:
            presigned = self.generate_presigned_url(resolved_key, expiration=expiration)
            if presigned:
                return presigned
        return f"/storage/{resolved_key}"

# Global instance
s3_storage_service = S3StorageService()
