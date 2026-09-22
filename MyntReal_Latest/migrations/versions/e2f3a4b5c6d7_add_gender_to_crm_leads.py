"""Add nullable gender column to crm_leads

Revision ID: e2f3a4b5c6d7
Revises: c9d0e1f2a3b4
Create Date: 2026-09-21 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2f3a4b5c6d7'
down_revision = 'c9d0e1f2a3b4'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Set safe migration timeouts
    op.execute(sa.text("SET lock_timeout = '5s';"))
    op.execute(sa.text("SET statement_timeout = '30s';"))

    # 2. Add nullable gender column to crm_leads if not exists
    bind = op.get_bind()
    has_col = bind.execute(sa.text(
        "SELECT 1 FROM information_schema.columns WHERE table_name='crm_leads' AND column_name='gender'"
    )).scalar()
    if not has_col:
        op.add_column('crm_leads', sa.Column('gender', sa.String(length=20), nullable=True))


def downgrade():
    # 1. Set safe migration timeouts
    op.execute(sa.text("SET lock_timeout = '5s';"))
    op.execute(sa.text("SET statement_timeout = '30s';"))

    # 2. Drop gender column from crm_leads
    op.drop_column('crm_leads', 'gender')
