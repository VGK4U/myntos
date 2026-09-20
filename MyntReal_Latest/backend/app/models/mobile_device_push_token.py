"""
Mobile Device Push Token Model — MyntOS Mobile Telephony Architecture
Tracks FCM tokens (Android) and Apple PushKit VoIP tokens (iOS) for screen-off incoming calls.
Created: Sep 2026
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base, get_indian_time


class MobileDevicePushToken(Base):
    __tablename__ = 'mobile_device_push_tokens'
    __table_args__ = (
        UniqueConstraint('staff_id', 'device_id', 'token_type', name='uq_staff_device_token_type'),
        Index('ix_mdpt_staff_active', 'staff_id', 'is_active'),
        Index('ix_mdpt_company_staff', 'company_id', 'staff_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    device_id = Column(String(100), nullable=False, index=True)
    platform = Column(String(20), nullable=False)  # 'android' | 'ios'
    push_token = Column(Text, nullable=False)
    token_type = Column(String(30), nullable=False, default='fcm_data')  # 'fcm_data' | 'apns_voip'
    app_version = Column(String(30), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    staff = relationship('StaffEmployee', foreign_keys=[staff_id], backref='push_tokens')

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'staff_id': self.staff_id,
            'device_id': self.device_id,
            'platform': self.platform,
            'token_type': self.token_type,
            'app_version': self.app_version,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
