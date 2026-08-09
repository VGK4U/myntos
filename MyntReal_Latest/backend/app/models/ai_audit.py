"""
AI Action Audit & Cost Control Models (Release 1A Engine)
Provides audit logs for every AI recommendation/action and token/cost telemetry per company/vertical.
"""

from sqlalchemy import Column, Integer, String, Text, Float, JSON, DateTime, ForeignKey, Index, Boolean
from datetime import datetime
from app.models.base import Base


class AIActionLog(Base):
    """
    AI Action Audit Log.
    Tracks every AI recommendation, prompt version, confidence score, decision, and human override.
    """
    __tablename__ = 'ai_action_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False, index=True)
    
    vertical = Column(String(50), nullable=False, default='GENERAL', index=True)
    channel = Column(String(30), nullable=False, default='WHATSAPP')  # WHATSAPP, VOICE, CRM, SYSTEM
    action_type = Column(String(50), nullable=False, index=True)      # SEND_WHATSAPP, START_AI_CALL, ASSIGN_HUMAN, etc.
    
    model_name = Column(String(100), nullable=False, default='mock_llm_v1')
    prompt_version = Column(String(50), nullable=False, default='v1.0')
    confidence_score = Column(Float, nullable=False, default=0.0)
    
    ai_recommendation = Column(JSON, nullable=True)
    final_action_taken = Column(String(50), nullable=False)
    human_override = Column(Boolean, nullable=False, default=False)
    
    correlation_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AIUsageLog(Base):
    """
    AI Token & Cost Control Log.
    Tracks input tokens, output tokens, latency, and estimated cost per lead/vertical.
    """
    __tablename__ = 'ai_usage_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=True, index=True)
    
    provider_name = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    task_name = Column(String(50), nullable=False)
    
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    estimated_cost_usd = Column(Float, nullable=False, default=0.000000)
    latency_ms = Column(Integer, nullable=False, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
