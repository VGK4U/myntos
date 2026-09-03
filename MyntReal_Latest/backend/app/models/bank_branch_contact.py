"""
Bank Branch Contact Model
Stores personnel contact details for bank branches (Branch Manager, Field Officer, Custom Officers)
Supports multi-tenant segregation, staff audit trail, and WebRTC softphone dialing.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from app.models.base import BaseModel
from datetime import datetime
import pytz


def get_indian_time():
    indian_tz = pytz.timezone("Asia/Kolkata")
    return datetime.now(indian_tz).replace(tzinfo=None)


class BankBranchContact(BaseModel):
    __tablename__ = "crm_bank_branch_contacts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_id = Column(Integer, nullable=True, default=4, index=True)
    bank_name = Column(String(200), nullable=False, index=True)
    branch_name = Column(String(200), nullable=False, index=True)

    # Branch Manager
    manager_name = Column(String(200), nullable=True)
    manager_phone = Column(String(50), nullable=True)
    manager_alt_phone = Column(String(50), nullable=True)

    # Field Officer
    officer_name = Column(String(200), nullable=True)
    officer_phone = Column(String(50), nullable=True)
    officer_alt_phone = Column(String(50), nullable=True)

    # Custom Field Designation / Staff
    custom_designation = Column(String(200), nullable=True)
    custom_name = Column(String(200), nullable=True)
    custom_phone = Column(String(50), nullable=True)
    custom_alt_phone = Column(String(50), nullable=True)

    # General Notes & Audit
    notes = Column(Text, nullable=True)
    updated_by_staff_id = Column(Integer, nullable=True)
    updated_by_staff_name = Column(String(200), nullable=True)

    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)

    __table_args__ = (
        Index("idx_bank_branch_key", "bank_name", "branch_name"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "bank_name": self.bank_name,
            "branch_name": self.branch_name,
            "manager_name": self.manager_name or "",
            "manager_phone": self.manager_phone or "",
            "manager_alt_phone": self.manager_alt_phone or "",
            "officer_name": self.officer_name or "",
            "officer_phone": self.officer_phone or "",
            "officer_alt_phone": self.officer_alt_phone or "",
            "custom_designation": self.custom_designation or "",
            "custom_name": self.custom_name or "",
            "custom_phone": self.custom_phone or "",
            "custom_alt_phone": self.custom_alt_phone or "",
            "notes": self.notes or "",
            "updated_by_staff_id": self.updated_by_staff_id,
            "updated_by_staff_name": self.updated_by_staff_name or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
