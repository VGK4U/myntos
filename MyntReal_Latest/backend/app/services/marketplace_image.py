"""
MNR E-Com Lite — ImageProvider Abstraction Layer
Phase 2: URL column active. Supports:
  - Direct image URLs (any CDN)
  - Google Drive file sharing links  → converted to direct-view URL
  - Google Drive folder links        → all images fetched via Drive API (GOOGLE_API_KEY)
  - Comma-separated multiple URLs    → multiple images per product

MIGRATION NOTE: Zero schema change — image_data JSONB accepts all formats.
"""

import os
import re
import logging
import urllib.request
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')

# ── URL pattern helpers ────────────────────────────────────────────────────────

_FILE_PATTERNS = [
    # https://drive.google.com/file/d/FILE_ID/view
    re.compile(r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)'),
    # https://drive.google.com/open?id=FILE_ID
    re.compile(r'drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)'),
    # https://drive.google.com/uc?id=FILE_ID
    re.compile(r'drive\.google\.com/uc\?(?:export=\w+&)?id=([a-zA-Z0-9_-]+)'),
]

_FOLDER_PATTERN = re.compile(r'drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)')


def _direct_url(file_id: str) -> str:
    """Convert a Drive file ID to a browser-renderable thumbnail URL (w800).
    Uses thumbnail endpoint which reliably serves images without auth,
    unlike uc?export=view which returns HTML for unauthenticated requests."""
    return f'https://drive.google.com/thumbnail?id={file_id}&sz=w800'


def _thumb_url(file_id: str) -> str:
    """Thumbnail URL for faster load in card grid (w400)."""
    return f'https://drive.google.com/thumbnail?id={file_id}&sz=w400'


def _extract_file_id(url: str):
    """Return file_id if url is a Drive file link, else None."""
    for pat in _FILE_PATTERNS:
        m = pat.search(url)
        if m:
            return m.group(1)
    return None


def _extract_folder_id(url: str):
    """Return folder_id if url is a Drive folder link, else None."""
    m = _FOLDER_PATTERN.search(url)
    return m.group(1) if m else None


def _fetch_folder_images(folder_id: str) -> List[Dict[str, Any]]:
    """
    Call Drive API v3 to list all image files in a folder.
    Returns list of image dicts sorted by name.
    Requires GOOGLE_API_KEY with Drive API enabled.
    """
    if not GOOGLE_API_KEY:
        logger.warning('[MARKETPLACE-IMG] GOOGLE_API_KEY not set — cannot expand folder')
        return []
    try:
        query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
        api_url = (
            f'https://www.googleapis.com/drive/v3/files'
            f'?q={urllib.request.quote(query)}'
            f'&fields=files(id,name)'
            f'&orderBy=name'
            f'&pageSize=20'
            f'&key={GOOGLE_API_KEY}'
        )
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        files = data.get('files', [])
        result = [{'url': _direct_url(f['id']), 'thumb': _thumb_url(f['id'])} for f in files]
        logger.info(f'[MARKETPLACE-IMG] Folder {folder_id}: {len(result)} image(s) found')
        return result
    except Exception as e:
        logger.warning(f'[MARKETPLACE-IMG] Drive folder fetch error ({folder_id}): {e}')
        return []


def _resolve_url(raw_url: str) -> Dict[str, Any]:
    """
    Resolve any URL to an image dict.
    - Drive folder  → fetch all files (returns first, caller handles multi)
    - Drive file    → convert to direct URL
    - Any other URL → use as-is
    """
    url = raw_url.strip()

    folder_id = _extract_folder_id(url)
    if folder_id:
        # Signal caller to expand folder (return special marker)
        return {'__folder__': folder_id}

    file_id = _extract_file_id(url)
    if file_id:
        return {'url': _direct_url(file_id), 'thumb': _thumb_url(file_id)}

    # Direct URL — use as-is
    return {'url': url, 'thumb': url}


# ── Abstract base ──────────────────────────────────────────────────────────────

class ImageProvider(ABC):
    @abstractmethod
    def get_images(self, row: List[str], col_index: int) -> List[Dict[str, Any]]:
        """Return list of image dicts: [{"url": "...", "thumb": "..."}]"""
        pass


# ── Phase 1 (legacy, unused) ───────────────────────────────────────────────────

class SheetEmbeddedImageProvider(ImageProvider):
    """Phase 1: embedded cell images — not accessible via API key. Returns empty."""
    def get_images(self, row: List[str], col_index: int) -> List[Dict[str, Any]]:
        return []


# ── Phase 2 (active) ──────────────────────────────────────────────────────────

class UrlImageProvider(ImageProvider):
    """
    Phase 2 (active): reads Image_URL column from sheet.
    Accepts:
      - Single URL (Drive file, Drive folder, or any direct URL)
      - Comma-separated list of URLs (mix of types allowed)
    Drive folder links are expanded via Drive API to include all images.
    """

    def get_images(self, row: List[str], col_index: int) -> List[Dict[str, Any]]:
        if col_index < 0 or col_index >= len(row):
            return []
        raw = row[col_index].strip()
        if not raw:
            return []

        images: List[Dict[str, Any]] = []
        parts = [u.strip() for u in raw.split(',') if u.strip()]

        for part in parts:
            resolved = _resolve_url(part)
            if '__folder__' in resolved:
                # Expand Drive folder — may return multiple images
                folder_imgs = _fetch_folder_images(resolved['__folder__'])
                images.extend(folder_imgs)
            else:
                images.append(resolved)

        return images


# ── Factory ────────────────────────────────────────────────────────────────────

def get_image_provider() -> ImageProvider:
    """Phase 2 active — URL column in sheet."""
    return UrlImageProvider()
