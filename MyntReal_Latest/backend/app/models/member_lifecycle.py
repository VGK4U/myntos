"""
Member Lifecycle Tracker Model
DC Protocol: Tracks entire lifecycle of MNR members from registration to completion
Auto-created when a member registers; updated by staff with page access
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, get_indian_time


class MemberLifecycleTracker(Base):
    __tablename__ = 'member_lifecycle_tracker'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(20), nullable=False, unique=True, index=True)
    user_name = Column(String(200), nullable=True)
    registration_date = Column(DateTime, nullable=True)

    welcome_call_status = Column(String(20), default='PENDING', nullable=False)
    welcome_call_updated_by = Column(String(50), nullable=True)
    welcome_call_updated_at = Column(DateTime, nullable=True)
    welcome_call_notes = Column(Text, nullable=True)

    login_shared_status = Column(String(20), default='PENDING', nullable=False)
    login_shared_updated_by = Column(String(50), nullable=True)
    login_shared_updated_at = Column(DateTime, nullable=True)
    login_shared_notes = Column(Text, nullable=True)

    kyc_status = Column(String(20), default='PENDING', nullable=False)
    kyc_updated_by = Column(String(50), nullable=True)
    kyc_updated_at = Column(DateTime, nullable=True)
    kyc_notes = Column(Text, nullable=True)

    bank_details_status = Column(String(20), default='PENDING', nullable=False)
    bank_details_updated_by = Column(String(50), nullable=True)
    bank_details_updated_at = Column(DateTime, nullable=True)
    bank_details_notes = Column(Text, nullable=True)

    insurance_status = Column(String(20), default='PENDING', nullable=False)
    insurance_updated_by = Column(String(50), nullable=True)
    insurance_updated_at = Column(DateTime, nullable=True)
    insurance_notes = Column(Text, nullable=True)

    points_explained_status = Column(String(20), default='PENDING', nullable=False)
    points_explained_updated_by = Column(String(50), nullable=True)
    points_explained_updated_at = Column(DateTime, nullable=True)
    points_explained_notes = Column(Text, nullable=True)

    package_activation_status = Column(String(20), default='PENDING', nullable=False)
    package_activation_updated_by = Column(String(50), nullable=True)
    package_activation_updated_at = Column(DateTime, nullable=True)
    package_activation_notes = Column(Text, nullable=True)

    coupon_delivery_status = Column(String(20), default='PENDING', nullable=False)
    coupon_delivery_updated_by = Column(String(50), nullable=True)
    coupon_delivery_updated_at = Column(DateTime, nullable=True)
    coupon_delivery_notes = Column(Text, nullable=True)

    congrats_call_status = Column(String(20), default='PENDING', nullable=False)
    congrats_call_updated_by = Column(String(50), nullable=True)
    congrats_call_updated_at = Column(DateTime, nullable=True)
    congrats_call_notes = Column(Text, nullable=True)

    overall_progress = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)

    STAGE_FIELDS = [
        'welcome_call', 'login_shared', 'kyc', 'bank_details',
        'insurance', 'points_explained', 'package_activation',
        'coupon_delivery', 'congrats_call'
    ]

    STAGE_LABELS = {
        'welcome_call': 'Welcome Call',
        'login_shared': 'Login Details Shared',
        'kyc': 'KYC Completion',
        'bank_details': 'Bank Details',
        'insurance': 'Insurance',
        'points_explained': 'Points Usage Explained',
        'package_activation': 'Package Activation',
        'coupon_delivery': 'Coupon Delivery',
        'congrats_call': 'Award/Bonanza Congratulation Call'
    }

    def calculate_progress(self):
        total = len(self.STAGE_FIELDS)
        completed = 0
        for field in self.STAGE_FIELDS:
            status = getattr(self, f'{field}_status', 'PENDING')
            if status == 'COMPLETED':
                completed += 1
        self.overall_progress = int((completed / total) * 100) if total > 0 else 0
        return self.overall_progress

    def to_dict(self):
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'registration_date': self.registration_date.isoformat() if self.registration_date else None,
            'overall_progress': self.overall_progress,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'stages': {}
        }
        for field in self.STAGE_FIELDS:
            result['stages'][field] = {
                'label': self.STAGE_LABELS.get(field, field),
                'status': getattr(self, f'{field}_status', 'PENDING'),
                'updated_by': getattr(self, f'{field}_updated_by', None),
                'updated_at': getattr(self, f'{field}_updated_at', None),
                'notes': getattr(self, f'{field}_notes', None),
            }
            if result['stages'][field]['updated_at']:
                result['stages'][field]['updated_at'] = result['stages'][field]['updated_at'].isoformat()
        return result
