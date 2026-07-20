"""
Sandbox Testing Environment Schemas
Pydantic models for API validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SandboxConfigurationBase(BaseModel):
    is_enabled: bool = False
    view_mode_enabled: bool = True
    edit_mode_enabled: bool = True
    activation_start: Optional[datetime] = None
    activation_end: Optional[datetime] = None
    activation_hours_start: Optional[int] = Field(None, ge=0, le=23)
    activation_hours_end: Optional[int] = Field(None, ge=0, le=23)
    auto_reset_enabled: bool = False
    auto_reset_frequency: Optional[str] = 'DAILY'
    auto_reset_time: Optional[str] = '00:00'
    allowed_staff_types: List[str] = ['VGK4U']
    allowed_mnr_types: List[str] = ['RVZ ID', 'VGK ID', 'Admin', 'Super Admin', 'Finance Admin', 'USER']
    allowed_partner_types: List[str] = ['DISTRIBUTOR', 'DEALER', 'VENDOR', 'REAL_DREAM_PARTNER']


class SandboxConfigurationUpdate(SandboxConfigurationBase):
    pass


class SandboxConfigurationResponse(SandboxConfigurationBase):
    id: int
    last_sync_at: Optional[datetime] = None
    last_sync_by_code: Optional[str] = None
    last_sync_by_name: Optional[str] = None
    last_sync_tables_count: int = 0
    last_sync_rows_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SandboxSyncRequest(BaseModel):
    sync_type: str = Field(default='FULL', description='FULL or INCREMENTAL')
    tables_to_sync: Optional[List[str]] = None


class SandboxSyncLogResponse(BaseModel):
    id: int
    sync_type: str
    status: str
    tables_synced: int
    rows_synced: int
    duration_seconds: int
    error_message: Optional[str] = None
    triggered_by_code: Optional[str] = None
    triggered_by_name: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SandboxTestAccountBase(BaseModel):
    account_type: str = Field(..., description='STAFF, MNR, or PARTNER')
    account_role: str
    login_id: str
    display_name: str
    is_active: bool = True
    activation_start: Optional[datetime] = None
    activation_end: Optional[datetime] = None


class SandboxTestAccountCreate(SandboxTestAccountBase):
    password: str = Field(..., min_length=8)


class SandboxTestAccountUpdate(BaseModel):
    display_name: Optional[str] = None
    is_active: Optional[bool] = None
    activation_start: Optional[datetime] = None
    activation_end: Optional[datetime] = None


class SandboxTestAccountPasswordChange(BaseModel):
    new_password: str = Field(..., min_length=8)


class SandboxTestAccountResponse(SandboxTestAccountBase):
    id: int
    last_login_at: Optional[datetime] = None
    login_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SandboxBulkActivation(BaseModel):
    account_ids: List[int]
    is_active: bool
    activation_start: Optional[datetime] = None
    activation_end: Optional[datetime] = None


class SandboxStatusResponse(BaseModel):
    is_enabled: bool
    is_currently_active: bool
    view_mode_enabled: bool
    edit_mode_enabled: bool
    activation_start: Optional[datetime] = None
    activation_end: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    total_test_accounts: int
    active_test_accounts: int
