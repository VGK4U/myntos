"""
AI Knowledge Base Models (Release 1A Engine)
Stores approved company facts across Products, Prices, Offers, Specs, FAQs, Locations, Policies, and Campaigns.
Strict rule: AI must ONLY draw business facts from approved, active knowledge base records.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from datetime import datetime
from app.models.base import Base


class AIKnowledgeCategory(Base):
    """Knowledge Categories (PRODUCTS, PRICES, OFFERS, SPECS, FAQS, LOCATIONS, POLICIES, CAMPAIGNS)."""
    __tablename__ = 'ai_knowledge_categories'
    __table_args__ = (
        UniqueConstraint('company_id', 'vertical', 'category_code', name='uq_knowledge_cat'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, index=True)
    vertical = Column(String(50), nullable=False, default='GENERAL', index=True)
    category_code = Column(String(50), nullable=False)  # PRODUCTS, PRICES, OFFERS, etc.
    display_name = Column(String(100), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AIKnowledgeItem(Base):
    """
    Approved Business Knowledge Fact.
    Must be approved by staff before LLM retrieval usage.
    """
    __tablename__ = 'ai_knowledge_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey('ai_knowledge_categories.id', ondelete='CASCADE'), nullable=False, index=True)
    
    title = Column(String(200), nullable=False)
    fact_content = Column(Text, nullable=False)
    keywords = Column(String(300), nullable=True)
    
    is_approved = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    version = Column(String(20), nullable=False, default='v1.0')
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<AIKnowledgeItem id={self.id} title={self.title} approved={self.is_approved}>'
