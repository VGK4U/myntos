"""
Meta Ads Management Center Models (Phase 2J Integration Layer)
Additive database schema for Meta sync runs, action approval requests, audit logs, budget alerts,
insights snapshots, and multilingual creative QA results.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class MetaSyncRunModel(Base):
    __tablename__ = "meta_sync_runs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, default=1, index=True)
    sync_type = Column(String(50), default="FULL_SYNC")  # FULL_SYNC, CAMPAIGN_SYNC, INSIGHTS_SYNC
    status = Column(String(50), default="SYNC_SUCCESS")  # SYNC_SUCCESS, SYNC_FAILED
    items_synced_count = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), server_default=func.now())


class MetaActionRequestModel(Base):
    __tablename__ = "meta_action_requests"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, default=1, index=True)
    requested_by = Column(String(100), nullable=False)  # User ID e.g. MR10001
    action_type = Column(String(50), nullable=False)    # CREATE_CAMPAIGN, PAUSE_CAMPAIGN, ACTIVATE_CAMPAIGN, EDIT_BUDGET
    target_object_type = Column(String(50), nullable=False)  # CAMPAIGN, ADSET, AD, CREATIVE
    target_object_id = Column(String(100))
    current_value = Column(JSON)
    proposed_value = Column(JSON)
    reason = Column(Text)
    risk_level = Column(String(20), default="MEDIUM")   # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(50), default="PENDING_APPROVAL") # PENDING_APPROVAL, APPROVED, REJECTED, EXECUTED, EXECUTION_FAILED
    approved_by = Column(String(100))
    approval_date = Column(DateTime(timezone=True))
    execution_result = Column(JSON)
    graph_api_trace_id = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MetaAuditLogModel(Base):
    __tablename__ = "meta_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, default=1, index=True)
    user_id = Column(String(100), nullable=False)
    user_role = Column(String(50), default="SUPREME_ADMIN")
    action = Column(String(100), nullable=False)
    target_object = Column(String(100))
    before_value = Column(JSON)
    after_value = Column(JSON)
    result_status = Column(String(50), default="SUCCESS")
    graph_api_trace_id = Column(String(100))
    error_details = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MetaAlertModel(Base):
    __tablename__ = "meta_alerts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, default=1, index=True)
    alert_type = Column(String(100), nullable=False)   # BUDGET_80_PERCENT, SPEND_SPIKE, CPL_SPIKE, CONNECTION_HEALTH
    severity = Column(String(20), default="WARNING")   # INFO, WARNING, CRITICAL
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MetaInsightsSnapshotModel(Base):
    __tablename__ = "meta_insights_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, default=1, index=True)
    account_id = Column(String(50), default="560062103113819")
    spend_today = Column(Float, default=0.0)
    spend_mtd = Column(Float, default=0.0)
    impressions = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    ctr = Column(Float, default=0.0)
    cpc = Column(Float, default=0.0)
    cpm = Column(Float, default=0.0)
    leads_count = Column(Integer, default=0)
    cpl = Column(Float, default=0.0)
    realized_revenue = Column(Float, default=0.0)
    roas = Column(Float, default=0.0)
    data_availability = Column(String(50), default="REAL_DATA") # REAL_DATA, NO_DATA_AVAILABLE
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CreativeQAResultModel(Base):
    __tablename__ = "creative_qa_results"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, default=1, index=True)
    generation_id = Column(Integer, ForeignKey("creative_generations.id"))
    language = Column(String(20), default="en") # en, te, hi
    source_text = Column(Text, nullable=False)
    rendered_ocr_text = Column(Text)
    mismatch_percentage = Column(Float, default=0.0)
    spelling_status = Column(String(50), default="PASSED") # PASSED, FAILED
    brand_safety_status = Column(String(50), default="PASSED") # PASSED, FAILED
    qa_decision = Column(String(50), default="QA_PASSED") # QA_PASSED, QA_FAILED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
