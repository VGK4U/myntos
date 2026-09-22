"""CRM Phone Composite Referential Integrity (Phase 2R-3E-II)

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-09-14 20:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c9d0e1f2a3b4'
down_revision = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Set safe migration timeouts
    op.execute(sa.text("SET lock_timeout = '5s';"))
    op.execute(sa.text("SET statement_timeout = '30s';"))

    bind = op.get_bind()

    # 2. Supporting composite UNIQUE on crm_leads(tenant_id, company_id, id)
    has_uq1 = bind.execute(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conname = 'uq_crm_leads_tenant_company_id'"
    )).scalar()
    if not has_uq1:
        op.create_unique_constraint(
            'uq_crm_leads_tenant_company_id',
            'crm_leads',
            ['tenant_id', 'company_id', 'id']
        )

    # 3. Supporting composite UNIQUE on crm_lead_phones(id, tenant_id, company_id, lead_id)
    has_uq2 = bind.execute(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conname = 'uq_crm_lead_phones_composite_id'"
    )).scalar()
    if not has_uq2:
        op.create_unique_constraint(
            'uq_crm_lead_phones_composite_id',
            'crm_lead_phones',
            ['id', 'tenant_id', 'company_id', 'lead_id']
        )

    # 4. Replace unary fk_crm_lead_phones_lead with composite (tenant_id, company_id, lead_id)
    has_unary_fk1 = bind.execute(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conname = 'fk_crm_lead_phones_lead'"
    )).scalar()
    if has_unary_fk1:
        op.drop_constraint('fk_crm_lead_phones_lead', 'crm_lead_phones', type_='foreignkey')

    has_comp_fk1 = bind.execute(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conname = 'fk_crm_lead_phones_composite_lead'"
    )).scalar()
    if not has_comp_fk1:
        op.create_foreign_key(
            'fk_crm_lead_phones_composite_lead',
            'crm_lead_phones',
            'crm_leads',
            ['tenant_id', 'company_id', 'lead_id'],
            ['tenant_id', 'company_id', 'id'],
            ondelete='CASCADE',
            onupdate='RESTRICT'
        )

    # 5. Replace unary fk_crm_lead_phone_prov_assoc with composite (phone_association_id, tenant_id, company_id, lead_id)
    has_unary_fk2 = bind.execute(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conname = 'fk_crm_lead_phone_prov_assoc'"
    )).scalar()
    if has_unary_fk2:
        op.drop_constraint('fk_crm_lead_phone_prov_assoc', 'crm_lead_phone_provenances', type_='foreignkey')

    has_comp_fk2 = bind.execute(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conname = 'fk_crm_lead_phone_prov_composite_assoc'"
    )).scalar()
    if not has_comp_fk2:
        op.create_foreign_key(
            'fk_crm_lead_phone_prov_composite_assoc',
            'crm_lead_phone_provenances',
            'crm_lead_phones',
            ['phone_association_id', 'tenant_id', 'company_id', 'lead_id'],
            ['id', 'tenant_id', 'company_id', 'lead_id'],
            ondelete='CASCADE',
            onupdate='RESTRICT'
        )


def downgrade():
    # 1. Set safe migration timeouts
    op.execute(sa.text("SET lock_timeout = '5s';"))
    op.execute(sa.text("SET statement_timeout = '30s';"))

    # 2. Downgrade provenance composite FK back to unary
    op.drop_constraint('fk_crm_lead_phone_prov_composite_assoc', 'crm_lead_phone_provenances', type_='foreignkey')
    op.create_foreign_key(
        'fk_crm_lead_phone_prov_assoc',
        'crm_lead_phone_provenances',
        'crm_lead_phones',
        ['phone_association_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # 3. Downgrade phone association composite FK back to unary
    op.drop_constraint('fk_crm_lead_phones_composite_lead', 'crm_lead_phones', type_='foreignkey')
    op.create_foreign_key(
        'fk_crm_lead_phones_lead',
        'crm_lead_phones',
        'crm_leads',
        ['lead_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # 4. Drop supporting composite UNIQUE on crm_lead_phones
    op.drop_constraint('uq_crm_lead_phones_composite_id', 'crm_lead_phones', type_='unique')

    # 5. Drop supporting composite UNIQUE on crm_leads
    op.drop_constraint('uq_crm_leads_tenant_company_id', 'crm_leads', type_='unique')
