"""
Dynamic Central Integration Management Framework — Database Models
Supports:
- Dynamic Integration Categories
- Dynamic Integration Definitions (schema-driven)
- Generic Multi-Tenant Connections (supports multiple accounts per tenant/provider)
- Comprehensive Audit Logging
- Zero-leakage AES-256-GCM credential encryption
Created: September 2026
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index, text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel, get_indian_time


# ─────────────────────────────────────────────────────────────────────────────
# 1. integration_categories — dynamic grouping of providers
# ─────────────────────────────────────────────────────────────────────────────
class IntegrationCategory(BaseModel):
    __tablename__ = 'integration_categories'

    id = Column(Integer, primary_key=True, index=True)
    category_code = Column(String(64), unique=True, nullable=False, index=True)
    display_name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(64), nullable=False, default='fas fa-plug')
    display_order = Column(Integer, nullable=False, default=10)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text('true'))

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    definitions = relationship("IntegrationDefinition", back_populates="category", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'category_code': self.category_code,
            'display_name': self.display_name,
            'description': self.description,
            'icon': self.icon,
            'display_order': self.display_order,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 2. integration_definitions — provider declarations and dynamic configuration schemas
# ─────────────────────────────────────────────────────────────────────────────
class IntegrationDefinition(BaseModel):
    __tablename__ = 'integration_definitions'

    id = Column(Integer, primary_key=True, index=True)
    integration_code = Column(String(64), unique=True, nullable=False, index=True)
    category_code = Column(String(64), ForeignKey('integration_categories.category_code', ondelete='CASCADE'), nullable=False, index=True)
    display_name = Column(String(128), nullable=False)
    provider_name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(64), nullable=False, default='fas fa-cube')
    auth_type = Column(String(64), nullable=False, default='api_key') # api_key, account_token, oauth2, service_account, public_url, session_scan, storage_keys

    supports_platform_connection = Column(Boolean, nullable=False, default=True, server_default=text('true'))
    supports_tenant_connection = Column(Boolean, nullable=False, default=True, server_default=text('true'))
    supports_multiple_connections = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    supports_oauth = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    supports_webhooks = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    supports_connection_test = Column(Boolean, nullable=False, default=True, server_default=text('true'))
    supports_enable_disable = Column(Boolean, nullable=False, default=True, server_default=text('true'))

    configuration_schema = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    status_rules = Column(JSONB, nullable=True, default=dict, server_default=text("'{}'::jsonb"))
    adapter_class = Column(String(128), nullable=True)
    display_order = Column(Integer, nullable=False, default=10)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text('true'))

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    category = relationship("IntegrationCategory", back_populates="definitions")
    connections = relationship("IntegrationConnection", back_populates="definition", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'integration_code': self.integration_code,
            'category_code': self.category_code,
            'display_name': self.display_name,
            'provider_name': self.provider_name,
            'description': self.description,
            'icon': self.icon,
            'auth_type': self.auth_type,
            'supports_platform_connection': self.supports_platform_connection,
            'supports_tenant_connection': self.supports_tenant_connection,
            'supports_multiple_connections': self.supports_multiple_connections,
            'supports_oauth': self.supports_oauth,
            'supports_webhooks': self.supports_webhooks,
            'supports_connection_test': self.supports_connection_test,
            'supports_enable_disable': self.supports_enable_disable,
            'configuration_schema': self.configuration_schema,
            'status_rules': self.status_rules,
            'adapter_class': self.adapter_class,
            'display_order': self.display_order,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 3. integration_connections — generic accounts/connections per tenant
# ─────────────────────────────────────────────────────────────────────────────
class IntegrationConnection(BaseModel):
    __tablename__ = 'integration_connections'
    __table_args__ = (
        Index('ix_int_conn_tenant_code', 'tenant_id', 'integration_code'),
        Index('ix_int_conn_scope_code', 'scope', 'integration_code'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('platform_clients.id', ondelete='CASCADE'), nullable=True, index=True)
    integration_code = Column(String(64), ForeignKey('integration_definitions.integration_code', ondelete='CASCADE'), nullable=False, index=True)
    connection_name = Column(String(128), nullable=False)
    scope = Column(String(32), nullable=False, default='tenant', server_default=text("'tenant'")) # 'platform' or 'tenant'
    auth_type = Column(String(64), nullable=False, default='api_key')

    # AES-256-GCM encrypted JSON payload (format: gcm:v1:<nonce>:<cipher>:<tag>)
    encrypted_credentials = Column(Text, nullable=True)

    # Non-sensitive public metadata (e.g., Phone ID, WABA ID, Sender Phone, Sheet URL, Region, Bucket Name)
    public_configuration = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))

    provider_account_id = Column(String(128), nullable=True) # Account SID / Auth ID / WABA ID / Merchant ID
    status = Column(String(32), nullable=False, default='not_configured', server_default=text("'not_configured'")) # ACTIVE, INACTIVE, NOT_CONFIGURED, PENDING, ERROR, EXPIRED, REQUIRES_REAUTH
    is_active = Column(Boolean, nullable=False, default=True, server_default=text('true'))
    is_default = Column(Boolean, nullable=False, default=False, server_default=text('false'))

    last_tested_at = Column(DateTime, nullable=True)
    last_test_result = Column(JSONB, nullable=True)

    created_by = Column(String(64), nullable=True)
    updated_by = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    definition = relationship("IntegrationDefinition", back_populates="connections")
    tenant = relationship("PlatformClient", foreign_keys=[tenant_id], primaryjoin="IntegrationConnection.tenant_id == PlatformClient.id")

    def to_dict(self, include_masked_creds: bool = True):
        res = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'tenant_name': self.tenant.client_name if self.tenant else 'Platform Default',
            'tenant_code': self.tenant.client_code if self.tenant else 'PLATFORM',
            'integration_code': self.integration_code,
            'connection_name': self.connection_name,
            'scope': self.scope,
            'auth_type': self.auth_type,
            'public_configuration': self.public_configuration or {},
            'provider_account_id': self.provider_account_id,
            'status': self.status,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'last_tested_at': self.last_tested_at.isoformat() if self.last_tested_at else None,
            'last_test_result': self.last_test_result,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_masked_creds:
            from app.services.integrations.registry import mask_connection_credentials
            res['masked_credentials'] = mask_connection_credentials(self)
        return res


# ─────────────────────────────────────────────────────────────────────────────
# 4. integration_audit_logs — comprehensive audit trail for mutations & checks
# ─────────────────────────────────────────────────────────────────────────────
class IntegrationAuditLog(BaseModel):
    __tablename__ = 'integration_audit_logs'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('platform_clients.id', ondelete='SET NULL'), nullable=True, index=True)
    integration_code = Column(String(64), nullable=False, index=True)
    connection_id = Column(Integer, nullable=True, index=True)
    action = Column(String(64), nullable=False) # 'connection_created', 'credentials_updated', 'connection_tested', etc.
    actor_emp_code = Column(String(64), nullable=False)
    actor_ip = Column(String(64), nullable=True)
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'integration_code': self.integration_code,
            'connection_id': self.connection_id,
            'action': self.action,
            'actor_emp_code': self.actor_emp_code,
            'actor_ip': self.actor_ip,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
