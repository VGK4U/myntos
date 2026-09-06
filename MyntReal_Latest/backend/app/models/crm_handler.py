"""
CRM Handler & Lead Routing Models — MyntOS Canonical CRM Settings
Defines Company + Department + Segment/Category -> Associated Team Routing for NEW CRM Leads.
Created: Sep 2026
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from datetime import datetime
import pytz


def get_indian_time():
    """Get current datetime in Indian Standard Time (Asia/Kolkata)"""
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)


class CRMLeadHandler(BaseModel):
    """
    Canonical CRM Handler Configuration Entity.
    Maps Company + Department + Segment/Category to an Associated Active Team.
    Determines fresh lead routing and visibility without mutating lead ownership.
    """
    __tablename__ = 'crm_lead_handlers'
    __table_args__ = (
        UniqueConstraint('company_id', 'department_id', 'category_id', name='uq_crm_lead_handler_co_dept_cat'),
        Index('ix_clh_company_category', 'company_id', 'category_id'),
        Index('ix_clh_department', 'department_id'),
        Index('ix_clh_is_active', 'is_active'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey('staff_departments.id', ondelete='CASCADE'), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey('signup_categories.id', ondelete='CASCADE'), nullable=False, index=True)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    created_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    members = relationship('CRMLeadHandlerMember', back_populates='handler', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'department_id': self.department_id,
            'category_id': self.category_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by_id': self.created_by_id,
            'members': [m.to_dict() for m in self.members] if self.members else []
        }


class CRMLeadHandlerMember(BaseModel):
    """
    Associated Active Team Members assigned to a CRM Lead Handler mapping.
    """
    __tablename__ = 'crm_lead_handler_members'
    __table_args__ = (
        UniqueConstraint('handler_id', 'employee_id', name='uq_crm_lead_handler_member'),
        Index('ix_clhm_handler_id', 'handler_id'),
        Index('ix_clhm_employee_id', 'employee_id'),
        Index('ix_clhm_is_active', 'is_active'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    handler_id = Column(Integer, ForeignKey('crm_lead_handlers.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    created_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    handler = relationship('CRMLeadHandler', back_populates='members')

    def to_dict(self):
        return {
            'id': self.id,
            'handler_id': self.handler_id,
            'employee_id': self.employee_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by_id': self.created_by_id
        }


class CRMLeadHandlerAudit(BaseModel):
    """
    Audit log tracking all changes to CRM Lead Handler configurations and team memberships.
    """
    __tablename__ = 'crm_lead_handler_audits'
    __table_args__ = (
        Index('ix_clha_handler_id', 'handler_id'),
        Index('ix_clha_action', 'action'),
        Index('ix_clha_created_at', 'created_at'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    handler_id = Column(Integer, nullable=True)
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, MEMBER_ADD, MEMBER_REMOVE, ENABLE, DISABLE, DELETE
    details = Column(Text, nullable=True)        # JSON details string
    performed_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'handler_id': self.handler_id,
            'action': self.action,
            'details': self.details,
            'performed_by_id': self.performed_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


def get_staff_handler_eligibility(db, employee_ids: list) -> list:
    """
    Returns list of (company_id, category_id) tuples for which any of the given employee(s)
    are active members of an active CRMLeadHandler.
    Used to scope fresh lead routing and Auto Dialer queue visibility.
    """
    if not employee_ids:
        return []
    try:
        rows = db.query(CRMLeadHandler.company_id, CRMLeadHandler.category_id).join(
            CRMLeadHandlerMember, CRMLeadHandlerMember.handler_id == CRMLeadHandler.id
        ).filter(
            CRMLeadHandler.is_active == True,
            CRMLeadHandlerMember.is_active == True,
            CRMLeadHandlerMember.employee_id.in_(employee_ids)
        ).distinct().all()
        return [(r[0], r[1]) for r in rows]
    except Exception as e:
        return []

