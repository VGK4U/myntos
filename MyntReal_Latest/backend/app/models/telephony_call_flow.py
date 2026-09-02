"""
Telephony Call Flow Models — MyntOS Native Call Flow Designer & Execution Engine
Multi-tenant, normalized schema for IVR menus, business hours, ring groups, versioned DAG flows, and execution logs.
Created: Sep 2026
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index, BigInteger, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.models.base import BaseModel, get_indian_time


class TelephonyCallFlow(BaseModel):
    """
    Master Call Flow entity.
    Scoped per tenant company_id. Manages current draft and active published version pointers.
    """
    __tablename__ = 'telephony_call_flows'
    __table_args__ = (
        Index('ix_tcf_company_status', 'company_id', 'status'),
        Index('ix_tcf_did_number', 'did_number'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    did_number = Column(String(50), nullable=True, index=True)  # Associated Plivo Inbound DID e.g. +918031728899
    status = Column(String(30), default='draft', nullable=False)  # draft | published | archived
    current_published_version_id = Column(Integer, nullable=True)
    created_by_staff_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    versions = relationship("TelephonyCallFlowVersion", back_populates="flow", cascade="all, delete-orphan", foreign_keys="[TelephonyCallFlowVersion.flow_id]")

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'description': self.description,
            'did_number': self.did_number,
            'status': self.status,
            'current_published_version_id': self.current_published_version_id,
            'created_by_staff_id': self.created_by_staff_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class TelephonyCallFlowVersion(BaseModel):
    """
    Immutable Call Flow Version snapshot.
    Stores complete versioned DAG graph (nodes, edges, config) for instant rollback and live routing.
    """
    __tablename__ = 'telephony_call_flow_versions'
    __table_args__ = (
        UniqueConstraint('flow_id', 'version_number', name='uq_tcf_version_num'),
        Index('ix_tcfv_flow_status', 'flow_id', 'status'),
        Index('ix_tcfv_company', 'company_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    flow_id = Column(Integer, ForeignKey('telephony_call_flows.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = Column(Integer, nullable=False, index=True)
    version_number = Column(Integer, nullable=False, default=1)
    status = Column(String(30), default='draft', nullable=False)  # draft | published | archived | superseded
    flow_data = Column(JSON, nullable=False, default=dict)  # Full JSON DAG graph containing nodes and edges
    published_at = Column(DateTime, nullable=True)
    published_by_staff_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    flow = relationship("TelephonyCallFlow", back_populates="versions", foreign_keys=[flow_id])
    nodes = relationship("TelephonyFlowNode", back_populates="version", cascade="all, delete-orphan")
    edges = relationship("TelephonyFlowEdge", back_populates="version", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'flow_id': self.flow_id,
            'company_id': self.company_id,
            'version_number': self.version_number,
            'status': self.status,
            'flow_data': self.flow_data or {},
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'published_by_staff_id': self.published_by_staff_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class TelephonyFlowNode(BaseModel):
    """
    Normalized node entity belonging to a specific flow version.
    Supports node types: trigger_did, time_router, caller_lookup, speak_prompt, play_audio,
    ivr_menu, dial_user, dial_ring_group, dial_queue, voicemail, forward_pstn, hangup.
    """
    __tablename__ = 'telephony_flow_nodes'
    __table_args__ = (
        Index('ix_tfn_version_key', 'flow_version_id', 'node_key'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    flow_version_id = Column(Integer, ForeignKey('telephony_call_flow_versions.id', ondelete='CASCADE'), nullable=False, index=True)
    node_key = Column(String(64), nullable=False)  # Unique identifier within flow e.g. "node_ivr_1"
    node_type = Column(String(50), nullable=False)
    name = Column(String(150), nullable=False)
    config = Column(JSON, nullable=False, default=dict)
    position_x = Column(Integer, nullable=True, default=100)
    position_y = Column(Integer, nullable=True, default=100)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    version = relationship("TelephonyCallFlowVersion", back_populates="nodes")

    def to_dict(self):
        return {
            'id': self.id,
            'flow_version_id': self.flow_version_id,
            'node_key': self.node_key,
            'node_type': self.node_type,
            'name': self.name,
            'config': self.config or {},
            'position_x': self.position_x,
            'position_y': self.position_y,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class TelephonyFlowEdge(BaseModel):
    """
    Normalized transition edge between nodes in a flow version.
    Condition examples: 'always', 'open', 'closed', 'holiday', 'digit_1', 'no_answer', 'timeout', 'invalid'.
    """
    __tablename__ = 'telephony_flow_edges'
    __table_args__ = (
        Index('ix_tfe_version', 'flow_version_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    flow_version_id = Column(Integer, ForeignKey('telephony_call_flow_versions.id', ondelete='CASCADE'), nullable=False, index=True)
    source_node_key = Column(String(64), nullable=False)
    target_node_key = Column(String(64), nullable=False)
    condition = Column(String(100), nullable=False, default='always')
    priority = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    version = relationship("TelephonyCallFlowVersion", back_populates="edges")

    def to_dict(self):
        return {
            'id': self.id,
            'flow_version_id': self.flow_version_id,
            'source_node_key': self.source_node_key,
            'target_node_key': self.target_node_key,
            'condition': self.condition,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class TelephonyRingGroup(BaseModel):
    """
    Department or Team Ring Group for distributing inbound calls.
    Strategies: 'simultaneous' | 'sequential' | 'round_robin'
    """
    __tablename__ = 'telephony_ring_groups'
    __table_args__ = (
        Index('ix_trg_company', 'company_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    strategy = Column(String(30), nullable=False, default='simultaneous')
    timeout_seconds = Column(Integer, nullable=False, default=25)
    fallback_action = Column(String(50), nullable=False, default='voicemail')  # voicemail | hangup | forward
    fallback_config = Column(JSON, nullable=True, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    members = relationship("TelephonyRingGroupMember", back_populates="ring_group", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'strategy': self.strategy,
            'timeout_seconds': self.timeout_seconds,
            'fallback_action': self.fallback_action,
            'fallback_config': self.fallback_config or {},
            'is_active': self.is_active,
            'members_count': len(self.members) if self.members else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class TelephonyRingGroupMember(BaseModel):
    """
    Staff member enrolled in a Ring Group with ordering and priority.
    """
    __tablename__ = 'telephony_ring_group_members'
    __table_args__ = (
        UniqueConstraint('ring_group_id', 'staff_id', name='uq_trg_member'),
        Index('ix_trgm_group', 'ring_group_id'),
        Index('ix_trgm_staff', 'staff_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    ring_group_id = Column(Integer, ForeignKey('telephony_ring_groups.id', ondelete='CASCADE'), nullable=False, index=True)
    staff_id = Column(Integer, nullable=False, index=True)
    priority_order = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    ring_group = relationship("TelephonyRingGroup", back_populates="members")
    staff = relationship("StaffEmployee", foreign_keys=[staff_id], primaryjoin="TelephonyRingGroupMember.staff_id == StaffEmployee.id", uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'ring_group_id': self.ring_group_id,
            'staff_id': self.staff_id,
            'staff_name': self.staff.full_name if self.staff else None,
            'staff_emp_code': self.staff.emp_code if self.staff else None,
            'staff_phone': self.staff.phone if self.staff else None,
            'priority_order': self.priority_order,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class TelephonyBusinessHours(BaseModel):
    """
    Weekly business hours schedule for tenant call routing.
    """
    __tablename__ = 'telephony_business_hours'
    __table_args__ = (
        Index('ix_tbh_company', 'company_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False, default='Standard Business Hours')
    timezone = Column(String(50), nullable=False, default='Asia/Kolkata')
    # Schedule format: {"mon": {"open": "09:30", "close": "18:30", "enabled": true}, ...}
    schedule_data = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'timezone': self.timezone,
            'schedule_data': self.schedule_data or {},
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class TelephonyHoliday(BaseModel):
    """
    Tenant holiday calendar for after-hours routing.
    """
    __tablename__ = 'telephony_holidays'
    __table_args__ = (
        UniqueConstraint('company_id', 'holiday_date', name='uq_th_company_date'),
        Index('ix_th_company_date', 'company_id', 'holiday_date'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, nullable=False, index=True)
    holiday_date = Column(String(10), nullable=False)  # Format: YYYY-MM-DD
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'holiday_date': self.holiday_date,
            'name': self.name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class TelephonyPlivoEndpoint(BaseModel):
    """
    Mapping model linking MyntOS staff employees to genuine Plivo SIP endpoints.
    Eliminates hardcoded or fabricated SIP URIs.
    """
    __tablename__ = 'telephony_plivo_endpoints'
    __table_args__ = (
        UniqueConstraint('company_id', 'staff_id', name='uq_tpe_company_staff'),
        Index('ix_tpe_company_staff', 'company_id', 'staff_id'),
        Index('ix_tpe_username', 'plivo_username'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, nullable=False, index=True)
    staff_id = Column(Integer, nullable=False, index=True)
    plivo_endpoint_id = Column(String(128), nullable=True)  # Plivo Endpoint UUID
    plivo_username = Column(String(128), nullable=False)    # e.g. agent_c1_s101
    plivo_alias = Column(String(128), nullable=True)
    plivo_password_hash = Column(String(255), nullable=True)
    is_registered = Column(Boolean, nullable=False, default=False)
    last_registered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    staff = relationship("StaffEmployee", foreign_keys=[staff_id], primaryjoin="TelephonyPlivoEndpoint.staff_id == StaffEmployee.id", uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'staff_id': self.staff_id,
            'staff_name': self.staff.full_name if self.staff else None,
            'staff_emp_code': self.staff.emp_code if self.staff else None,
            'plivo_endpoint_id': self.plivo_endpoint_id,
            'plivo_username': self.plivo_username,
            'plivo_sip_uri': f"sip:{self.plivo_username}@phone.plivo.com",
            'plivo_alias': self.plivo_alias,
            'is_registered': self.is_registered,
            'last_registered_at': self.last_registered_at.isoformat() if self.last_registered_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class TelephonyFlowExecutionLog(BaseModel):
    """
    Step-by-step traversal history and telemetry for inbound call sessions.
    """
    __tablename__ = 'telephony_flow_execution_logs'
    __table_args__ = (
        Index('ix_tfel_session', 'call_session_id'),
        Index('ix_tfel_company_flow', 'company_id', 'flow_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_session_id = Column(String(64), nullable=False, index=True)
    company_id = Column(Integer, nullable=False, index=True)
    flow_id = Column(Integer, nullable=False)
    flow_version_id = Column(Integer, nullable=False)
    caller_phone = Column(String(30), nullable=False)
    did_number = Column(String(50), nullable=True)
    current_node_key = Column(String(64), nullable=False)
    traversed_nodes = Column(JSON, nullable=False, default=list)  # List of visited node summaries
    collected_digits = Column(String(20), nullable=True)
    selected_destination = Column(String(150), nullable=True)
    connected_staff_id = Column(Integer, nullable=True)
    final_outcome = Column(String(50), nullable=True)  # answered | voicemail | missed | abandoned | hangup | error
    duration_seconds = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'call_session_id': self.call_session_id,
            'company_id': self.company_id,
            'flow_id': self.flow_id,
            'flow_version_id': self.flow_version_id,
            'caller_phone': self.caller_phone,
            'did_number': self.did_number,
            'current_node_key': self.current_node_key,
            'traversed_nodes': self.traversed_nodes or [],
            'collected_digits': self.collected_digits,
            'selected_destination': self.selected_destination,
            'connected_staff_id': self.connected_staff_id,
            'final_outcome': self.final_outcome,
            'duration_seconds': self.duration_seconds,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
