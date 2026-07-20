"""
DC Protocol: CRM Google Sheets Lead Sync
Tables: crm_lead_sync_configs, crm_lead_sync_runs
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.models.base import BaseModel


class CRMLeadSyncConfig(BaseModel):
    """Registered Google Sheet configurations for lead import."""
    __tablename__ = 'crm_lead_sync_configs'

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(200), nullable=False)
    sheet_url       = Column(Text, nullable=False)
    is_active       = Column(Boolean, default=True, nullable=False)
    sync_9am        = Column(Boolean, default=True, nullable=False)
    sync_12pm       = Column(Boolean, default=True, nullable=False)
    sync_3pm        = Column(Boolean, default=True, nullable=False)
    sync_6pm        = Column(Boolean, default=True, nullable=False)
    daily_sync_enabled = Column(Boolean, default=True, nullable=False)
    total_imported  = Column(Integer, default=0, nullable=False)
    last_synced_at  = Column(DateTime(timezone=True), nullable=True)
    created_by      = Column(Integer, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            'id':                  self.id,
            'name':                self.name,
            'sheet_url':           self.sheet_url,
            'is_active':           self.is_active,
            'sync_9am':            self.sync_9am,
            'sync_12pm':           self.sync_12pm,
            'sync_3pm':            self.sync_3pm,
            'sync_6pm':            self.sync_6pm,
            'daily_sync_enabled':  self.daily_sync_enabled,
            'total_imported':      self.total_imported,
            'last_synced_at':      self.last_synced_at.isoformat() if self.last_synced_at else None,
            'created_at':          self.created_at.isoformat() if self.created_at else None,
        }


class CRMLeadSyncRun(BaseModel):
    """Audit log for every sync run (manual or scheduled)."""
    __tablename__ = 'crm_lead_sync_runs'

    id              = Column(Integer, primary_key=True, index=True)
    config_id       = Column(Integer, ForeignKey('crm_lead_sync_configs.id', ondelete='CASCADE'), nullable=True)
    config_name     = Column(String(200), nullable=True)
    synced_at       = Column(DateTime(timezone=True), server_default=func.now())
    slot            = Column(String(20), default='manual')     # manual / 9am / 12pm / 3pm / 6pm
    triggered_by    = Column(String(20), default='manual')     # manual / auto
    tabs_synced     = Column(Integer, default=1)
    new_leads       = Column(Integer, default=0)
    duplicate_leads = Column(Integer, default=0)
    error_count     = Column(Integer, default=0)

    def to_dict(self):
        return {
            'id':              self.id,
            'config_id':       self.config_id,
            'config_name':     self.config_name,
            'synced_at':       self.synced_at.isoformat() if self.synced_at else None,
            'slot':            self.slot,
            'triggered_by':    self.triggered_by,
            'tabs_synced':     self.tabs_synced,
            'new_leads':       self.new_leads,
            'duplicate_leads': self.duplicate_leads,
            'error_count':     self.error_count,
        }
