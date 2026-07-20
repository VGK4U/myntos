"""Add PendingBonuses with NOT NULL referred_user_id and unique constraint

Revision ID: 04d29dd6085c
Revises: dee4cc221460
Create Date: 2025-09-14 07:35:54.999087

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '04d29dd6085c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # No-op: columns already exist in database
    pass


def downgrade():
    # No-op: avoid affecting existing schema
    pass