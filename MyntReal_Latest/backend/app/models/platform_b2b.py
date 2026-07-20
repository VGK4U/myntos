"""
B2B SaaS Layer — Phase 1 Foundation Models (DC Protocol, Shadow Mode)

Tables:
- platform_clients:                    Tenant master (one row per external client)
- platform_modules:                    Catalog mirroring staff_menu_registry at menu/page granularity
- platform_module_dependencies:        Module->module DAG (auto-include on assignment)
- platform_plans:                      Plan templates (Starter / Binary / Suite ...)
- platform_plan_modules:               M2M plan <-> module
- platform_subscriptions:              Per-client subscription header (currency, cycle, status, dates)
- platform_subscription_modules:       M2M subscription <-> module (the actual entitlements)
- platform_module_pricing:             Global per-module dual-currency price (INR + USD)
- platform_client_module_pricing_override:  Per-client price override (Q7/Q8)
- platform_audit_log:                  Audit trail for every B2B mutation
- b2b_shadow_log:                      Shadow-mode "would-have-blocked" decisions

Phase-1 invariant: NO enforcement runs. is_module_entitled() always returns True
behind feature flag B2B_ENFORCE (default false) and only logs decisions.

Created: May 03, 2026 (Task #39)
"""

from sqlalchemy import (
    Column, Integer, BigInteger, String, DateTime, Date, Boolean, Text,
    ForeignKey, Index, Numeric, UniqueConstraint, CheckConstraint, text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel, get_indian_time


# ─────────────────────────────────────────────────────────────────────────────
# 1. platform_clients — tenant master
# ─────────────────────────────────────────────────────────────────────────────
class PlatformClient(BaseModel):
    __tablename__ = 'platform_clients'

    id = Column(Integer, primary_key=True, index=True)
    client_code = Column(String(64), unique=True, nullable=False, index=True)
    client_name = Column(String(200), nullable=False)
    is_internal = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    status = Column(String(16), nullable=False, default='active', server_default=text("'active'"))

    contact_name = Column(String(200), nullable=True)
    contact_email = Column(String(200), nullable=True)
    contact_phone = Column(String(40), nullable=True)
    billing_currency = Column(String(8), nullable=False, default='INR', server_default=text("'INR'"))
    billing_address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Phase 3a.0 — Tally/Zoho parity: link to default issuing legal entity + GST identity
    primary_legal_entity_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='SET NULL'), nullable=True, index=True)
    gstin = Column(String(20), nullable=True)
    state_for_gst = Column(String(80), nullable=True)
    pan_number = Column(String(20), nullable=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('active','suspended','archived','trial')", name='platform_client_status_check'),
        CheckConstraint("billing_currency IN ('INR','USD')", name='platform_client_currency_check'),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. platform_modules — module catalog (mirrors staff_menu_registry granularity)
# ─────────────────────────────────────────────────────────────────────────────
class PlatformModule(BaseModel):
    __tablename__ = 'platform_modules'

    id = Column(Integer, primary_key=True, index=True)
    module_code = Column(String(128), unique=True, nullable=False, index=True)
    module_name = Column(String(200), nullable=False)
    category = Column(String(64), nullable=True, index=True)
    description = Column(Text, nullable=True)

    # Mirror back to the source menu row (nullable — some modules are abstract groupings)
    menu_code = Column(String(128), nullable=True, index=True)
    sidebar_section = Column(String(64), nullable=True)

    internal_only = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    is_active = Column(Boolean, nullable=False, default=True, server_default=text('true'))
    custom_overrides = Column(JSONB, nullable=True)

    # Phase 3a.0 — Tally/Zoho parity: HSN/SAC + unit + default GST rate
    hsn_sac_code = Column(String(20), nullable=True)
    unit_of_measure = Column(String(20), nullable=True, server_default=text("'NOS'"))
    default_tax_rate_pct = Column(Numeric(5, 2), nullable=True, server_default=text('18.00'))

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)


# ─────────────────────────────────────────────────────────────────────────────
# 3. platform_module_dependencies — DAG for auto-include on assignment
# ─────────────────────────────────────────────────────────────────────────────
class PlatformModuleDependency(BaseModel):
    __tablename__ = 'platform_module_dependencies'

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey('platform_modules.id', ondelete='CASCADE'), nullable=False, index=True)
    depends_on_module_id = Column(Integer, ForeignKey('platform_modules.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    __table_args__ = (
        UniqueConstraint('module_id', 'depends_on_module_id', name='uq_platform_module_dep'),
        CheckConstraint('module_id <> depends_on_module_id', name='ck_platform_module_dep_no_self'),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. platform_plans — plan templates (renamable per-client via subscription field)
# ─────────────────────────────────────────────────────────────────────────────
class PlatformPlan(BaseModel):
    __tablename__ = 'platform_plans'

    id = Column(Integer, primary_key=True, index=True)
    plan_code = Column(String(64), unique=True, nullable=False, index=True)
    plan_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text('true'))

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)


# ─────────────────────────────────────────────────────────────────────────────
# 5. platform_plan_modules — plan <-> module M2M
# ─────────────────────────────────────────────────────────────────────────────
class PlatformPlanModule(BaseModel):
    __tablename__ = 'platform_plan_modules'

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey('platform_plans.id', ondelete='CASCADE'), nullable=False, index=True)
    module_id = Column(Integer, ForeignKey('platform_modules.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    __table_args__ = (UniqueConstraint('plan_id', 'module_id', name='uq_platform_plan_module'),)


# ─────────────────────────────────────────────────────────────────────────────
# 6. platform_subscriptions — per-client subscription header
# ─────────────────────────────────────────────────────────────────────────────
class PlatformSubscription(BaseModel):
    __tablename__ = 'platform_subscriptions'

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey('platform_clients.id', ondelete='CASCADE'), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey('platform_plans.id', ondelete='SET NULL'), nullable=True, index=True)

    # Per-Q6: same plan can be renamed per client
    display_plan_name = Column(String(200), nullable=True)

    billing_currency = Column(String(8), nullable=False, default='INR', server_default=text("'INR'"))
    billing_cycle = Column(String(16), nullable=False, default='monthly', server_default=text("'monthly'"))
    annual_free_months = Column(Integer, nullable=False, default=2, server_default=text('2'))

    is_trial = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    status = Column(String(16), nullable=False, default='active', server_default=text("'active'"))

    starts_on = Column(Date, nullable=True)
    ends_on = Column(Date, nullable=True)
    trial_ends_on = Column(Date, nullable=True)

    # Phase 3a.2 — seat = staff login count for the tenant; drives per_seat pricing
    seat_count = Column(Integer, nullable=False, default=1, server_default=text('1'))

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    __table_args__ = (
        CheckConstraint("billing_currency IN ('INR','USD')", name='platform_sub_currency_check'),
        CheckConstraint("billing_cycle IN ('monthly','annual')", name='platform_sub_cycle_check'),
        CheckConstraint("status IN ('trial','active','suspended','cancelled')", name='platform_sub_status_check'),
        CheckConstraint("seat_count >= 1", name='platform_sub_seat_count_check'),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7. platform_subscription_modules — actual entitlements
# ─────────────────────────────────────────────────────────────────────────────
class PlatformSubscriptionModule(BaseModel):
    __tablename__ = 'platform_subscription_modules'

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey('platform_subscriptions.id', ondelete='CASCADE'), nullable=False, index=True)
    module_id = Column(Integer, ForeignKey('platform_modules.id', ondelete='CASCADE'), nullable=False, index=True)
    enabled = Column(Boolean, nullable=False, default=True, server_default=text('true'))
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    __table_args__ = (UniqueConstraint('subscription_id', 'module_id', name='uq_platform_sub_module'),)


# ─────────────────────────────────────────────────────────────────────────────
# 8. platform_module_pricing — global per-module dual-currency
# ─────────────────────────────────────────────────────────────────────────────
class PlatformModulePricing(BaseModel):
    __tablename__ = 'platform_module_pricing'

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey('platform_modules.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    price_inr = Column(Numeric(14, 2), nullable=False, default=0, server_default=text('0'))
    price_usd = Column(Numeric(14, 2), nullable=False, default=0, server_default=text('0'))
    pricing_unit = Column(String(16), nullable=False, default='per_company', server_default=text("'per_company'"))
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    __table_args__ = (
        CheckConstraint("pricing_unit IN ('per_company','per_seat','flat')", name='platform_pricing_unit_check'),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 9. platform_client_module_pricing_override — per-client overrides
# ─────────────────────────────────────────────────────────────────────────────
class PlatformClientModulePricingOverride(BaseModel):
    __tablename__ = 'platform_client_module_pricing_override'

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey('platform_clients.id', ondelete='CASCADE'), nullable=False, index=True)
    module_id = Column(Integer, ForeignKey('platform_modules.id', ondelete='CASCADE'), nullable=False, index=True)
    price_inr = Column(Numeric(14, 2), nullable=True)
    price_usd = Column(Numeric(14, 2), nullable=True)
    pricing_unit = Column(String(16), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    __table_args__ = (UniqueConstraint('client_id', 'module_id', name='uq_platform_client_module_override'),)


# ─────────────────────────────────────────────────────────────────────────────
# 10. platform_audit_log — DC-style audit
# ─────────────────────────────────────────────────────────────────────────────
class PlatformAuditLog(BaseModel):
    __tablename__ = 'platform_audit_log'

    id = Column(BigInteger, primary_key=True, index=True)
    actor_staff_id = Column(Integer, nullable=True, index=True)
    client_id = Column(Integer, nullable=True, index=True)
    entity = Column(String(32), nullable=False, index=True)   # B2B-CLIENT, B2B-MODULE, B2B-PLAN, B2B-SUB, B2B-PRICE
    action = Column(String(16), nullable=False)               # CREATE, UPDATE, DELETE
    entity_id = Column(Integer, nullable=True, index=True)
    before_json = Column(JSONB, nullable=True)
    after_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False, index=True)

    __table_args__ = (
        CheckConstraint("action IN ('CREATE','UPDATE','DELETE')", name='platform_audit_action_check'),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 11. b2b_shadow_log — would-have-blocked decisions
# ─────────────────────────────────────────────────────────────────────────────
class B2BShadowLog(BaseModel):
    __tablename__ = 'b2b_shadow_log'

    id = Column(BigInteger, primary_key=True, index=True)
    client_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    user_type = Column(String(32), nullable=True)             # staff / member / partner / vendor / influencer
    module_code = Column(String(128), nullable=True, index=True)
    route = Column(String(512), nullable=True)
    decision = Column(String(16), nullable=False)             # ALLOW / WOULD_BLOCK
    reason = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False, index=True)

    __table_args__ = (
        CheckConstraint("decision IN ('ALLOW','WOULD_BLOCK')", name='b2b_shadow_decision_check'),
        Index('ix_b2b_shadow_client_module_at', 'client_id', 'module_code', 'created_at'),
    )
