"""
AI Lead Intelligence Models (Release 1A Engine)
Stores lead feature matrices, historical outcome labels for future ML, and versioned lead score audit logs.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Index, Text
from datetime import datetime
from app.models.base import Base


class LeadFeatureMatrix(Base):
    """
    Feature matrix table for offline AI analysis & future ML training.
    Captures deterministic CRM data and AI analysis factors.
    """
    __tablename__ = 'lead_feature_matrix'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    
    vertical = Column(String(50), nullable=False, default='GENERAL', index=True)
    acquisition_source = Column(String(50), nullable=True)
    campaign_id = Column(String(50), nullable=True)
    
    lead_age_days = Column(Integer, nullable=False, default=0)
    has_phone = Column(Boolean, nullable=False, default=True)
    has_email = Column(Boolean, nullable=False, default=False)
    has_budget = Column(Boolean, nullable=False, default=False)
    
    wa_message_count = Column(Integer, nullable=False, default=0)
    wa_response_rate = Column(Float, nullable=False, default=0.0)
    
    call_count = Column(Integer, nullable=False, default=0)
    appointment_scheduled = Column(Boolean, nullable=False, default=False)
    site_visit_completed = Column(Boolean, nullable=False, default=False)
    
    raw_features = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class LeadOutcomeLabel(Base):
    """
    Outcome tracking table for future machine learning model training.
    Stores authoritative conversion results (QUALIFIED, WON, LOST, REVENUE).
    """
    __tablename__ = 'lead_outcome_labels'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    
    is_qualified = Column(Boolean, nullable=False, default=False)
    is_won = Column(Boolean, nullable=False, default=False)
    realized_cash_revenue = Column(Float, nullable=False, default=0.0)
    
    outcome_stage = Column(String(50), nullable=False, default='NEW')
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class LeadScoreHistory(Base):
    """
    Versioned Lead Score Audit Log.
    Explains exactly WHY a lead received a particular score (Deterministic Factors + AI Intent).
    """
    __tablename__ = 'lead_score_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False, index=True)
    
    score = Column(Integer, nullable=False)  # 0 to 100
    score_version = Column(String(20), nullable=False, default='v1.0_RULES_PLUS_AI')
    
    rule_score = Column(Integer, nullable=False)
    ai_intent_score = Column(Integer, nullable=False)
    ai_confidence = Column(Float, nullable=False, default=0.0)
    
    positive_factors = Column(JSON, nullable=False, default=list)
    negative_factors = Column(JSON, nullable=False, default=list)
    explanation = Column(Text, nullable=True)
    
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
