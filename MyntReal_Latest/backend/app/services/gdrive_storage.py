"""
Google Drive Storage Service
Handles structured multi-tenant folder organization and file sync on Google Drive.
Structure: Root (1MLZfmVRe7vSinRcjsbNHeOPtVi18WZ_p) -> Segment -> Company -> Lead/Customer -> Document.pdf
"""
import os
import io
import re
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Default root folder provided by user
DEFAULT_DRIVE_FOLDER_ID = "1MLZfmVRe7vSinRcjsbNHeOPtVi18WZ_p"

class GoogleDriveStorageService:
    def __init__(self):
        self.root_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", DEFAULT_DRIVE_FOLDER_ID)
        self.service = None
        self._folder_cache: Dict[str, str] = {}
        self._init_drive_client()

    def _init_drive_client(self):
        """Initialize Google Drive API client using Service Account or OAuth credentials"""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            creds_path = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON")
            if not creds_path:
                # Check backend directory or root directory for default json
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                possible_paths = [
                    os.path.join(base_dir, "google-service-account.json"),
                    os.path.join(base_dir, "..", "google-service-account.json"),
                    os.path.join(base_dir, "gdrive-credentials.json"),
                ]
                for p in possible_paths:
                    if os.path.exists(p):
                        creds_path = p
                        break

            if creds_path and os.path.exists(creds_path):
                scopes = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']
                creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
                self.service = build('drive', 'v3', credentials=creds)
                logger.info(f"✅ Google Drive API initialized with Service Account from {creds_path}")
            else:
                # Check if API Key or ADC credentials can be used
                logger.info("ℹ️ Google Drive Service Account JSON not found; Google Drive client operating in local mirror fallback mode.")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize Google Drive API client: {e}")
            self.service = None

    def _sanitize_name(self, name: str) -> str:
        """Sanitize folder and file names for Google Drive compatibility"""
        if not name:
            return "Uncategorized"
        cleaned = re.sub(r'[^\w\s\-\.\(\)]', '_', str(name)).strip()
        return cleaned or "Uncategorized"

    def get_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """Find or create a subfolder inside a given parent folder ID"""
        if not self.service:
            return None
        
        parent_id = parent_id or self.root_folder_id
        cache_key = f"{parent_id}/{folder_name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]

        safe_name = self._sanitize_name(folder_name)
        try:
            # Query existing folder
            query = f"name = '{safe_name}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            res = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            files = res.get('files', [])
            if files:
                folder_id = files[0]['id']
                self._folder_cache[cache_key] = folder_id
                return folder_id

            # Create new subfolder
            folder_metadata = {
                'name': safe_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            self._folder_cache[cache_key] = folder_id
            logger.info(f"📁 Created Google Drive folder: '{safe_name}' (ID: {folder_id}) under parent {parent_id}")
            return folder_id
        except Exception as e:
            logger.error(f"❌ Error getting/creating Google Drive folder '{safe_name}': {e}")
            return None

    def resolve_target_folder(
        self, 
        segment: str = "Solar_Docs", 
        company_name: Optional[str] = None, 
        lead_id: Optional[Any] = None, 
        customer_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Creates & resolves the 3-tier folder structure:
        Root (1MLZfm...) -> Segment (e.g. Solar_Docs) -> Company -> Lead_ID_CustomerName
        """
        if not self.service:
            return None

        # 1. Segment level folder
        segment_folder_id = self.get_or_create_folder(segment, self.root_folder_id)
        if not segment_folder_id:
            return self.root_folder_id

        # 2. Company level folder
        company_label = company_name or "General_Company"
        company_folder_id = self.get_or_create_folder(company_label, segment_folder_id)
        if not company_folder_id:
            return segment_folder_id

        # 3. Lead / Customer level folder
        if lead_id or customer_name:
            lead_str = f"Lead_{lead_id}" if lead_id else ""
            cust_str = self._sanitize_name(customer_name) if customer_name else ""
            folder_label = f"{lead_str}_{cust_str}".strip('_') or "Customer_Docs"
            customer_folder_id = self.get_or_create_folder(folder_label, company_folder_id)
            return customer_folder_id or company_folder_id

        return company_folder_id

    def upload_file(
        self, 
        file_bytes: bytes, 
        filename: str, 
        segment: str = "Solar_Docs", 
        company_name: Optional[str] = None, 
        lead_id: Optional[Any] = None, 
        customer_name: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Uploads file bytes to Google Drive with structured folder metadata.
        Returns dict with webViewLink, webContentLink, and file_id.
        """
        if not self.service:
            return {"success": False, "reason": "No Google Drive service account configured", "file_id": None}

        try:
            from googleapiclient.http import MediaIoBaseUpload

            target_folder_id = self.resolve_target_folder(
                segment=segment, 
                company_name=company_name, 
                lead_id=lead_id, 
                customer_name=customer_name
            ) or self.root_folder_id

            safe_filename = self._sanitize_name(filename)
            if not content_type:
                if safe_filename.lower().endswith('.pdf'):
                    content_type = 'application/pdf'
                elif safe_filename.lower().endswith(('.jpg', '.jpeg')):
                    content_type = 'image/jpeg'
                elif safe_filename.lower().endswith('.png'):
                    content_type = 'image/png'
                else:
                    content_type = 'application/octet-stream'

            file_metadata = {
                'name': safe_filename,
                'parents': [target_folder_id]
            }

            media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=content_type, resumable=True)
            gfile = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, webContentLink'
            ).execute()

            logger.info(f"✅ Uploaded file '{safe_filename}' to Google Drive (ID: {gfile.get('id')})")
            return {
                "success": True,
                "file_id": gfile.get("id"),
                "webViewLink": gfile.get("webViewLink"),
                "webContentLink": gfile.get("webContentLink"),
                "filename": gfile.get("name")
            }
        except Exception as e:
            logger.error(f"❌ Failed to upload '{filename}' to Google Drive: {e}")
            return {"success": False, "reason": str(e), "file_id": None}

# Global Singleton Instance
gdrive_storage_service = GoogleDriveStorageService()
