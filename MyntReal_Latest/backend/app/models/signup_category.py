"""
Signup Category Model - Configurable business categories for user registration
DC Protocol: Categories are managed by RVZ and EA roles with company_id segregation
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from datetime import datetime
import pytz


def get_indian_time():
    """Get current datetime in Indian Standard Time (Asia/Kolkata)"""
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)


class SignupCategory(BaseModel):
    """
    Signup Category model for configurable business categories during registration
    DC Protocol: company_id segregation for multi-company support
    Managed by RVZ and EA roles
    """
    __tablename__ = 'signup_categories'
    __table_args__ = (
        UniqueConstraint('company_id', 'slug', name='uq_signup_category_company_slug'),
        UniqueConstraint('company_id', 'name', name='uq_signup_category_company_name'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)
    slug = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    requires_documents = Column(Boolean, default=False, nullable=False)
    document_types = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    created_by_id = Column(String(12), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'icon': self.icon,
            'display_order': self.display_order,
            'is_active': self.is_active,
            'requires_documents': self.requires_documents,
            'document_types': self.document_types,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


DEFAULT_SIGNUP_CATEGORIES = [
    {
        'name': 'ETC Training',
        'slug': 'etc-training',
        'description': 'ETC Training Program',
        'icon': 'fas fa-graduation-cap',
        'display_order': 1
    },
    {
        'name': 'EV B2B',
        'slug': 'ev-b2b',
        'description': 'EV Business to Business',
        'icon': 'fas fa-building',
        'display_order': 2
    },
    {
        'name': 'EV B2C',
        'slug': 'ev-b2c',
        'description': 'EV Business to Consumer',
        'icon': 'fas fa-car',
        'display_order': 3
    },
    {
        'name': 'EV Spares',
        'slug': 'ev-spares',
        'description': 'EV Spare Parts',
        'icon': 'fas fa-cogs',
        'display_order': 4
    },
    {
        'name': 'Insurance',
        'slug': 'insurance',
        'description': 'Insurance Services',
        'icon': 'fas fa-shield-alt',
        'display_order': 5
    },
    {
        'name': 'Real Dreams',
        'slug': 'real-dreams',
        'description': 'Real Dreams Property',
        'icon': 'fas fa-home',
        'display_order': 6
    },
    {
        'name': 'Solar',
        'slug': 'solar',
        'description': 'Solar Energy Solutions',
        'icon': 'fas fa-solar-panel',
        'display_order': 7
    }
]
