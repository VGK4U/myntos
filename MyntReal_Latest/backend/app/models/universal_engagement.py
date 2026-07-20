"""
Universal Engagement System - Ratings, Comments, and Shares
DC Protocol Compliant with Company-Wise Data Segregation

This is a polymorphic system that can be attached to any entity type:
- Announcements (feedback_submissions)
- Properties (rd_properties)
- Products (future)
- Articles (future)
- Any other entity type

Tables:
- universal_ratings: Star ratings (1-5) for any entity
- universal_comments: Threaded comments for any entity
- universal_shares: Share tracking for any entity

Created: December 08, 2025
DC Protocol: All tables have company_id for strict segregation
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Text,
    ForeignKey, CheckConstraint, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import Base, BaseModel, get_indian_time


class UniversalRating(BaseModel):
    """
    Universal Ratings System
    DC Protocol: Company-wise segregation with polymorphic entity support
    Supports: announcements, properties, products, articles, etc.
    """
    __tablename__ = 'universal_ratings'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    
    rating = Column(Integer, nullable=False)
    
    rater_type = Column(String(20), nullable=False)
    rater_id = Column(String(100), nullable=True)
    rater_name = Column(String(100), nullable=False)
    rater_email = Column(String(255), nullable=True)
    rater_phone = Column(String(20), nullable=True)
    
    is_verified = Column(Boolean, default=False, nullable=False)
    is_visible = Column(Boolean, default=True, nullable=False)
    
    deleted_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    deletion_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='universal_rating_range_check'),
        CheckConstraint(
            "rater_type IN ('staff', 'partner', 'member', 'public', 'user')",
            name='universal_rating_rater_type_check'
        ),
        CheckConstraint(
            "entity_type IN ('announcement', 'property', 'product', 'article', 'service', 'event')",
            name='universal_rating_entity_type_check'
        ),
        UniqueConstraint('company_id', 'entity_type', 'entity_id', 'rater_type', 'rater_id', 
                        name='uq_universal_rating_per_entity'),
        Index('idx_universal_rating_entity', 'company_id', 'entity_type', 'entity_id', 'is_visible'),
    )
    
    def __repr__(self):
        return f'<UniversalRating {self.entity_type}:{self.entity_id} Rating:{self.rating}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'rating': self.rating,
            'rater_type': self.rater_type,
            'rater_name': self.rater_name,
            'is_verified': self.is_verified,
            'is_visible': self.is_visible,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UniversalComment(BaseModel):
    """
    Universal Comments System with Threading
    DC Protocol: Company-wise segregation with polymorphic entity support
    Supports replies via parent_id for threaded discussions
    """
    __tablename__ = 'universal_comments'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    
    comment = Column(Text, nullable=False)
    
    parent_id = Column(Integer, ForeignKey('universal_comments.id', ondelete='CASCADE'), nullable=True, index=True)
    
    commenter_type = Column(String(20), nullable=False)
    commenter_id = Column(String(100), nullable=True)
    commenter_name = Column(String(100), nullable=False)
    commenter_email = Column(String(255), nullable=True)
    commenter_phone = Column(String(20), nullable=True)
    
    is_verified = Column(Boolean, default=False, nullable=False)
    is_visible = Column(Boolean, default=True, nullable=False)
    
    deleted_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    deletion_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "commenter_type IN ('staff', 'partner', 'member', 'public', 'user')",
            name='universal_comment_commenter_type_check'
        ),
        CheckConstraint(
            "entity_type IN ('announcement', 'property', 'product', 'article', 'service', 'event')",
            name='universal_comment_entity_type_check'
        ),
        Index('idx_universal_comment_entity', 'company_id', 'entity_type', 'entity_id', 'is_visible'),
        Index('idx_universal_comment_parent', 'parent_id'),
    )
    
    def __repr__(self):
        return f'<UniversalComment {self.entity_type}:{self.entity_id} ID:{self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'comment': self.comment,
            'parent_id': self.parent_id,
            'commenter_type': self.commenter_type,
            'commenter_name': self.commenter_name,
            'is_verified': self.is_verified,
            'is_visible': self.is_visible,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class UniversalShare(BaseModel):
    """
    Universal Share Tracking
    DC Protocol: Company-wise segregation with polymorphic entity support
    Tracks which platform was used and basic analytics
    """
    __tablename__ = 'universal_shares'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    
    platform = Column(String(30), nullable=False)
    
    sharer_type = Column(String(20), nullable=True)
    sharer_id = Column(String(100), nullable=True)
    
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "platform IN ('facebook', 'twitter', 'whatsapp', 'linkedin', 'email', 'copy_link', 'telegram', 'other')",
            name='universal_share_platform_check'
        ),
        CheckConstraint(
            "entity_type IN ('announcement', 'property', 'product', 'article', 'service', 'event')",
            name='universal_share_entity_type_check'
        ),
        Index('idx_universal_share_entity', 'company_id', 'entity_type', 'entity_id', 'platform'),
    )
    
    def __repr__(self):
        return f'<UniversalShare {self.entity_type}:{self.entity_id} Platform:{self.platform}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'platform': self.platform,
            'sharer_type': self.sharer_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UniversalSave(BaseModel):
    """
    Universal Save/Favorite/Bookmark System
    DC Protocol: Company-wise segregation with polymorphic entity support
    Users can save any entity for later viewing
    """
    __tablename__ = 'universal_saves'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    
    saver_type = Column(String(20), nullable=False)
    saver_id = Column(String(100), nullable=False)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "saver_type IN ('staff', 'partner', 'member', 'public', 'user')",
            name='universal_save_saver_type_check'
        ),
        CheckConstraint(
            "entity_type IN ('announcement', 'property', 'product', 'article', 'service', 'event')",
            name='universal_save_entity_type_check'
        ),
        UniqueConstraint('company_id', 'entity_type', 'entity_id', 'saver_type', 'saver_id', 
                        name='uq_universal_save_per_entity'),
        Index('idx_universal_save_user', 'company_id', 'saver_type', 'saver_id'),
    )
    
    def __repr__(self):
        return f'<UniversalSave {self.entity_type}:{self.entity_id} Saver:{self.saver_type}:{self.saver_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'saver_type': self.saver_type,
            'saver_id': self.saver_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
