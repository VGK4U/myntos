"""
Automation Models
Persistent Relational Data Model for WhatsApp Automation Execution, Dispatch Tracking, and Target Configuration.
Architecture:
Automation Job -> AutomationExecution -> AutomationDispatch -> Queue/MessageLog -> Provider
"""

from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from app.models.base import Base

JSONType = JSONB().with_variant(JSON(), "sqlite")


class AutomationExecution(Base):
    """
    Authoritative record for an execution run of an automation job.
    Tracks scheduled, manual, and event-driven automation instances.
    """
    __tablename__ = "automation_execution"

    id = Column(String(64), primary_key=True)
    job_id = Column(String(100), nullable=False, index=True)
    job_name = Column(String(200), nullable=False)
    trigger_type = Column(String(50), nullable=False, default="SCHEDULED")
    triggered_by = Column(String(100), nullable=False, default="System Cron")
    triggered_by_staff_id = Column(Integer, ForeignKey("staff_employees.id"), nullable=True)
    company_id = Column(Integer, nullable=False, default=1)

    status = Column(String(30), nullable=False, default="PENDING", index=True)
    target_summary = Column(String(500), nullable=True)

    total_targets = Column(Integer, nullable=False, default=0)
    sent_count = Column(Integer, nullable=False, default=0)
    uncertain_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    skipped_count = Column(Integer, nullable=False, default=0)

    started_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    error_message = Column(Text, nullable=True)
    is_legacy = Column(Boolean, nullable=False, default=False, index=True)
    execution_metadata = Column(JSONType, nullable=True)

    dispatches = relationship("AutomationDispatch", back_populates="execution", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_ae_job_started", "job_id", "started_at"),
    )

    @property
    def dispatched_count(self) -> int:
        return self.total_targets or 0

    @property
    def metadata_json(self) -> dict:
        return self.execution_metadata or {}

    def __repr__(self):
        exec_id = self.__dict__.get('id', 'new')
        job = self.__dict__.get('job_id', '')
        st = self.__dict__.get('status', '')
        return f"<AutomationExecution {exec_id} job={job} status={st}>"


class AutomationDispatch(Base):
    """
    Granular record of an individual dispatch to a specific recipient within an execution.
    Links deterministically to MessageLog (1:1/Meta API) or whatsapp_bot_queue (Group/Baileys).
    """
    __tablename__ = "automation_dispatch"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    execution_id = Column(String(64), ForeignKey("automation_execution.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(100), nullable=False, index=True)

    recipient_type = Column(String(50), nullable=False)
    recipient_identifier = Column(String(255), nullable=False, index=True)
    recipient_name = Column(String(200), nullable=True)

    target_entity_type = Column(String(50), nullable=True)
    target_entity_id = Column(Integer, nullable=True)

    # Deterministic delivery linking (indexed)
    queue_id = Column(BigInteger, nullable=True, index=True)
    message_log_id = Column(Integer, nullable=True, index=True)

    provider = Column(String(50), nullable=False, default="META_WHATSAPP")
    provider_message_id = Column(String(500), nullable=True, index=True)

    status = Column(String(30), nullable=False, default="PENDING", index=True)

    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)

    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    payload_snapshot = Column(JSONType, nullable=True)

    execution = relationship("AutomationExecution", back_populates="dispatches")

    __table_args__ = (
        Index("idx_ad_job_recipient", "job_id", "recipient_identifier"),
    )

    @property
    def is_legacy(self) -> bool:
        if self.execution:
            return bool(self.execution.is_legacy)
        return False

    @property
    def created_at(self):
        return self.sent_at or self.delivered_at or self.failed_at


    def __repr__(self):
        did = self.__dict__.get('id', 'new')
        ident = self.__dict__.get('recipient_identifier', '')
        st = self.__dict__.get('status', '')
        return f"<AutomationDispatch {did} to={ident} status={st}>"


class AutomationTargetConfig(Base):
    """
    Persistent relational configuration of recipients per automation job.
    Replaces static/untyped wa_job_targets.json with tenant-isolated, audited records.
    """
    __tablename__ = "automation_target_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), nullable=False, index=True)
    company_id = Column(Integer, nullable=False, default=1, index=True)

    target_type = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    identifier = Column(String(255), nullable=False)
    target_role = Column(String(50), nullable=True, default="PRIMARY")
    is_active = Column(Boolean, nullable=False, default=True)

    created_by_staff_id = Column(Integer, ForeignKey("staff_employees.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_atc_job_active", "job_id", "is_active"),
    )

    @property
    def recipient_name(self) -> str:
        return self.name

    @recipient_name.setter
    def recipient_name(self, val: str):
        self.name = val

    @property
    def recipient_identifier(self) -> str:
        return self.identifier

    @recipient_identifier.setter
    def recipient_identifier(self, val: str):
        self.identifier = val

    @property
    def recipient_type(self) -> str:
        return self.target_type

    @recipient_type.setter
    def recipient_type(self, val: str):
        self.target_type = val

    def __getitem__(self, key: str):
        if key in ("recipient_name", "name"):
            return self.name
        if key in ("recipient_identifier", "identifier"):
            return self.identifier
        if key in ("recipient_type", "target_type", "type"):
            return self.target_type
        if key == "id":
            return self.id
        if key == "target_role":
            return getattr(self, "target_role", "PRIMARY") or "PRIMARY"
        if key == "is_active":
            return self.is_active
        if key == "job_id":
            return self.job_id
        if key == "company_id":
            return self.company_id
        return getattr(self, key)

    def get(self, key: str, default=None):
        try:
            val = self[key]
            return default if val is None else val
        except (KeyError, AttributeError):
            return default

    def __repr__(self):
        tid = self.__dict__.get('id', 'new')
        ident = self.__dict__.get('identifier', '')
        return f"<AutomationTargetConfig {tid} {ident}>"
