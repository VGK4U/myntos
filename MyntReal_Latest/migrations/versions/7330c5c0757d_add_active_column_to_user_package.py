"""add_active_column_to_user_package

Revision ID: 7330c5c0757d
Revises: f1234567890a
Create Date: 2025-09-17 20:00:12.710284

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7330c5c0757d'
down_revision = 'f1234567890a'
branch_labels = None
depends_on = None


def upgrade():
    # Add active column to user_package table
    op.add_column('user_package', sa.Column('active', sa.Boolean(), nullable=False, server_default='true'))
    
    # Create indexes for the active column
    op.create_index('idx_user_package_user_active', 'user_package', ['user_id', 'active'])
    op.create_index('idx_user_package_type_active', 'user_package', ['package_type', 'active'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_user_package_type_active', 'user_package')
    op.drop_index('idx_user_package_user_active', 'user_package')
    
    # Drop active column
    op.drop_column('user_package', 'active')
