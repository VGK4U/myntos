"""
Mobile Device Session Model — MyntOS Mobile Architecture
Tracks cryptographically rotating refresh tokens, device hardware IDs, and session revocation.
Created: Sep 2026
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.models.base import Base, get_indian_time


class MobileDeviceSession(Base):
    __tablename__ = 'mobile_device_sessions'
    __table_args__ = (
        Index('ix_mds_staff_active', 'staff_id', 'is_revoked', 'expires_at'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    staff_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    device_id = Column(String(100), nullable=False, index=True)
    platform = Column(String(20), nullable=False)  # 'android' | 'ios'
    refresh_token_hash = Column(String(64), nullable=False, unique=True, index=True)  # SHA-256
    device_name = Column(String(100), nullable=True)
    app_version = Column(String(30), nullable=True)
    token_version = Column(Integer, nullable=False, default=1)
    is_revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, default=get_indian_time, nullable=False)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    staff = relationship('StaffEmployee', foreign_keys=[staff_id], backref='mobile_sessions')

    def is_valid(self, current_staff_token_version: int = 1) -> bool:
        if self.is_revoked:
            return False
        if self.token_version < (current_staff_token_version or 1):
            return False
        return self.expires_at > get_indian_time()

    def to_dict(self):
        return {
            'id': self.id,
            'staff_id': self.staff_id,
            'device_id': self.device_id,
            'platform': self.platform,
            'device_name': self.device_name,
            'app_version': self.app_version,
            'is_revoked': self.is_revoked,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
