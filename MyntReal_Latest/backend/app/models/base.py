"""
Base model classes for FastAPI SQLAlchemy models
Preserves Flask app database schema exactly
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from datetime import datetime
import pytz

# DC PROTOCOL: Import Base from core.database to ensure single source of truth
from app.core.database import Base

def get_indian_time():
    """
    Get current time in Indian timezone (IST)
    Preserves exact Flask app time handling
    """
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)

class TimestampMixin:
    """
    Mixin to add timestamp fields to models
    Preserves Flask app audit trail pattern
    """
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

class AuditMixin(TimestampMixin):
    """
    Mixin to add audit fields to models
    Preserves Flask app audit pattern with User ID references
    """
    created_by_id = Column(String(12), nullable=True)  # FK to user.id
    updated_by_id = Column(String(12), nullable=True)  # FK to user.id
    
    # Soft delete fields (used in some models)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by_id = Column(String(12), nullable=True)  # FK to user.id
    is_deleted = Column(Boolean, default=False, nullable=False)

class BaseModel(Base):
    """
    Abstract base model with common functionality
    Preserves Flask app model pattern
    """
    __abstract__ = True
    
    def to_dict(self):
        """Convert model instance to dictionary for API responses"""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
    
    def update_from_dict(self, data: dict):
        """Update model instance from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)