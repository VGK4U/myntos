"""
Sandbox Testing Environment Models
DC Protocol Compliant - Company-wise data segregation
WVV Protocol Compliant - Full audit trail
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.sql import func
from app.core.database import Base


class SandboxConfiguration(Base):
    """
    Master configuration for sandbox testing environment
    Accessible only by VGK4U Supreme staff
    """
    __tablename__ = 'sandbox_configuration'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    is_enabled = Column(Boolean, default=False, nullable=False)
    view_mode_enabled = Column(Boolean, default=True, nullable=False)
    edit_mode_enabled = Column(Boolean, default=True, nullable=False)
    
    activation_start = Column(DateTime, nullable=True)
    activation_end = Column(DateTime, nullable=True)
    activation_hours_start = Column(Integer, nullable=True)
    activation_hours_end = Column(Integer, nullable=True)
    
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_by_id = Column(Integer, nullable=True)
    last_sync_by_code = Column(String(50), nullable=True)
    last_sync_by_name = Column(String(100), nullable=True)
    last_sync_tables_count = Column(Integer, default=0)
    last_sync_rows_count = Column(Integer, default=0)
    
    auto_reset_enabled = Column(Boolean, default=False, nullable=False)
    auto_reset_frequency = Column(String(20), default='DAILY', nullable=True)
    auto_reset_time = Column(String(10), default='00:00', nullable=True)
    
    allowed_staff_types = Column(JSON, default=['VGK4U'], nullable=False)
    allowed_mnr_types = Column(JSON, default=['RVZ ID', 'VGK ID', 'Admin', 'Super Admin', 'Finance Admin', 'USER'], nullable=False)
    allowed_partner_types = Column(JSON, default=['DISTRIBUTOR', 'DEALER', 'VENDOR', 'REAL_DREAM_PARTNER'], nullable=False)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by_id = Column(Integer, nullable=True)
    created_by_code = Column(String(50), nullable=True)
    updated_by_id = Column(Integer, nullable=True)
    updated_by_code = Column(String(50), nullable=True)


class SandboxSyncLog(Base):
    """
    Audit log for sandbox data synchronization
    WVV Protocol: Full audit trail
    """
    __tablename__ = 'sandbox_sync_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    sync_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    
    tables_synced = Column(Integer, default=0)
    rows_synced = Column(Integer, default=0)
    duration_seconds = Column(Integer, default=0)
    
    error_message = Column(Text, nullable=True)
    sync_details = Column(JSON, nullable=True)
    
    triggered_by_id = Column(Integer, nullable=True)
    triggered_by_code = Column(String(50), nullable=True)
    triggered_by_name = Column(String(100), nullable=True)
    
    started_at = Column(DateTime, server_default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_sandbox_sync_log_status', 'status'),
        Index('idx_sandbox_sync_log_started_at', 'started_at'),
    )


class SandboxTestAccount(Base):
    """
    Pre-configured test accounts for sandbox environment
    DC Protocol: Accounts work across all companies in testing schema
    """
    __tablename__ = 'sandbox_test_accounts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    account_type = Column(String(20), nullable=False)
    account_role = Column(String(50), nullable=False)
    login_id = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(200), nullable=False)
    
    password_hash = Column(String(255), nullable=False)
    
    is_active = Column(Boolean, default=True, nullable=False)
    activation_start = Column(DateTime, nullable=True)
    activation_end = Column(DateTime, nullable=True)
    
    last_login_at = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by_id = Column(Integer, nullable=True)
    created_by_code = Column(String(50), nullable=True)
    
    __table_args__ = (
        Index('idx_sandbox_test_accounts_type', 'account_type'),
        Index('idx_sandbox_test_accounts_role', 'account_role'),
        Index('idx_sandbox_test_accounts_active', 'is_active'),
    )


class SandboxAccessLog(Base):
    """
    Audit log for sandbox access
    WVV Protocol: Track all sandbox usage
    """
    __tablename__ = 'sandbox_access_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    access_mode = Column(String(10), nullable=False)
    account_type = Column(String(20), nullable=False)
    login_id = Column(String(100), nullable=False)
    
    page_accessed = Column(String(255), nullable=True)
    action_performed = Column(String(50), nullable=True)
    
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    accessed_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_sandbox_access_log_mode', 'access_mode'),
        Index('idx_sandbox_access_log_account', 'account_type', 'login_id'),
        Index('idx_sandbox_access_log_time', 'accessed_at'),
    )
