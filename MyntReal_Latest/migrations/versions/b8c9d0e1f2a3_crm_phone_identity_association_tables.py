"""CRM Phone Identity Association Tables (Phase 2R-3E-I)

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-09-14 17:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b8c9d0e1f2a3'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create crm_lead_phones table (Association Layer)
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS crm_lead_phones (
            id BIGSERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            lead_id INTEGER NOT NULL,
            phone_norm VARCHAR(15) NOT NULL,
            phone_role VARCHAR(30) NOT NULL DEFAULT 'PRIMARY',
            is_primary BOOLEAN NOT NULL DEFAULT TRUE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            verification_status VARCHAR(30) NOT NULL DEFAULT 'UNVERIFIED',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            
            CONSTRAINT fk_crm_lead_phones_lead 
                FOREIGN KEY (lead_id) REFERENCES crm_leads(id) ON DELETE CASCADE,
            CONSTRAINT fk_crm_lead_phones_tenant_company 
                FOREIGN KEY (tenant_id, company_id) REFERENCES associated_companies(client_id, id) ON DELETE RESTRICT,
            CONSTRAINT fk_crm_lead_phones_tenant 
                FOREIGN KEY (tenant_id) REFERENCES platform_clients(id) ON DELETE RESTRICT,
            CONSTRAINT uq_crm_lead_phones_association 
                UNIQUE (tenant_id, company_id, lead_id, phone_norm)
        );

        CREATE INDEX IF NOT EXISTS idx_crm_lead_phones_lookup 
        ON crm_lead_phones (tenant_id, company_id, phone_norm) 
        WHERE (is_active = TRUE);

        CREATE INDEX IF NOT EXISTS idx_crm_lead_phones_lead_id 
        ON crm_lead_phones (lead_id);
    """))

    # 2. Create crm_lead_phone_provenances table (Provenance Layer)
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS crm_lead_phone_provenances (
            id BIGSERIAL PRIMARY KEY,
            phone_association_id BIGINT NOT NULL,
            tenant_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            lead_id INTEGER NOT NULL,
            source_field VARCHAR(50) NOT NULL,
            raw_value VARCHAR(100),
            source_channel VARCHAR(50) NOT NULL DEFAULT 'manual',
            source_ref TEXT,
            captured_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

            CONSTRAINT fk_crm_lead_phone_prov_assoc 
                FOREIGN KEY (phone_association_id) REFERENCES crm_lead_phones(id) ON DELETE CASCADE,
            CONSTRAINT fk_crm_lead_phone_prov_lead 
                FOREIGN KEY (lead_id) REFERENCES crm_leads(id) ON DELETE CASCADE,
            CONSTRAINT fk_crm_lead_phone_prov_company 
                FOREIGN KEY (tenant_id, company_id) REFERENCES associated_companies(client_id, id) ON DELETE RESTRICT
        );

        CREATE INDEX IF NOT EXISTS idx_crm_lead_phone_prov_assoc 
        ON crm_lead_phone_provenances (phone_association_id);

        CREATE INDEX IF NOT EXISTS idx_crm_lead_phone_prov_lead 
        ON crm_lead_phone_provenances (lead_id);
    """))


def downgrade():
    op.execute(sa.text("""
        DROP TABLE IF EXISTS crm_lead_phone_provenances CASCADE;
        DROP TABLE IF EXISTS crm_lead_phones CASCADE;
    """))
