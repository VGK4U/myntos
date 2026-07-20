"""
Job Handlers for Background Processing
Central registry for all async job types
"""

from .image_compression_handler import process_image_compression_job

__all__ = [
    'process_image_compression_job'
]
