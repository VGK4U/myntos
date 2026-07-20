"""
Media Path Utilities
DC Protocol: Centralized media path normalization for all endpoints
Created: Jan 24, 2026

Purpose: Provide consistent media path normalization across all API endpoints
without circular import dependencies.
"""


def normalize_media_path(file_path: str) -> str:
    """
    Convert database file_path to accessible URL
    Uses Object Storage (/storage/) for new uploads
    
    DC Protocol: Handles multiple path formats for backward compatibility
    - Object Storage: feedback/12/photo_1.jpeg
    - Local Storage (new): feedback_media/36_uuid.png
    - Local Storage (broken): frontend/storage/feedback_media/36_uuid.png
    - Pending placeholder: pending
    """
    if not file_path:
        return file_path
    
    if file_path == 'pending':
        return '/storage/placeholder-pending.png'
    
    if file_path.startswith('frontend/storage/'):
        file_path = file_path[len('frontend/storage/'):]
    
    if file_path.startswith('feedback/'):
        return f"/storage/{file_path}"
    
    if file_path.startswith('feedback_media/'):
        return f"/storage/{file_path}"
    
    if file_path.startswith('/uploads/feedback/'):
        return '/storage/' + file_path[9:]
    elif file_path.startswith('uploads/feedback/'):
        return '/storage/' + file_path[8:]
    
    if file_path.startswith('/uploads/'):
        return file_path
    elif file_path.startswith('uploads/'):
        return '/' + file_path
    
    return f"/storage/{file_path}"
