from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.models.base import Base
import datetime


class FormDraft(Base):
    __tablename__ = "form_drafts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    user_type = Column(String(20), nullable=False, default='staff')
    form_key = Column(String(200), nullable=False)
    draft_data = Column(Text, nullable=True)
    page_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    expires_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'user_type', 'form_key', name='uq_form_drafts_user_form'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'form_key': self.form_key,
            'draft_data': self.draft_data,
            'page_url': self.page_url,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }
