"""Add unique constraint to Transaction table for deduplication

Revision ID: ccc9dc170018
Revises: 04d29dd6085c
Create Date: 2025-09-14 07:40:14.530664

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ccc9dc170018'
down_revision = '04d29dd6085c'
branch_labels = None
depends_on = None


def upgrade():
    # Add unique constraint to Transaction table for deduplication using batch mode for SQLite
    with op.batch_alter_table('transaction', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_txn_event', ['referrer_id', 'referred_user_id', 'transaction_type'])


def downgrade():
    # Remove unique constraint from Transaction table using batch mode for SQLite
    with op.batch_alter_table('transaction', schema=None) as batch_op:
        batch_op.drop_constraint('uq_txn_event', type_='unique')
