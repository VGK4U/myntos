"""
Object Storage Service
Currently routed to AWS S3 storage service.
This file is kept for backwards compatibility with imports.
"""

from .s3_storage import S3StorageService, s3_storage_service as storage_service
from collections import namedtuple

ObjectInfo = namedtuple('ObjectInfo', ['name'])

class Client:
    """A fake Replit object storage client that actually routes to AWS S3.
    This prevents us from having to rewrite every single API file."""
    
    def __init__(self):
        self._s3 = S3StorageService()
        
    def upload_from_bytes(self, path: str, data: bytes) -> None:
        self._s3.upload_file(path, data)
        
    def download_as_bytes(self, path: str) -> bytes:
        data = self._s3.download_file(path)
        if data is None:
            raise FileNotFoundError(f"File not found: {path}")
        return data
        
    def exists(self, path: str) -> bool:
        return self._s3.file_exists(path)
        
    def delete(self, path: str, ignore_not_found: bool = True) -> None:
        self._s3.delete_file(path)
        
    def list(self, prefix: str = "") -> list:
        names = self._s3.list_files(prefix)
        return [ObjectInfo(name=n) for n in names]

ObjectStorageService = S3StorageService
