"""Create placement table with proper constraints

Revision ID: 4ded27b36619
Revises: be12742b322d
Create Date: 2025-09-14 14:37:43.773010

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4ded27b36619'
down_revision = 'be12742b322d'
branch_labels = None
depends_on = None


def upgrade():
    # ### Create the normalized placement table ###
    op.create_table('placement',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('parent_id', sa.Integer(), nullable=False),
        sa.Column('child_id', sa.Integer(), nullable=False),
        sa.Column('side', sa.String(length=5), nullable=False),
        sa.Column('placed_at', sa.DateTime(), nullable=False),
        sa.Column('placed_by_id', sa.Integer(), nullable=True),
        sa.Column('placement_method', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(['child_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['parent_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['placed_by_id'], ['user.id'], ),
        
        # Primary key
        sa.PrimaryKeyConstraint('id'),
        
        # CRITICAL CONSTRAINTS for data integrity
        sa.UniqueConstraint('child_id', name='unique_child_placement'),  # Each user can only be placed once
        sa.UniqueConstraint('parent_id', 'side', name='unique_parent_side'),  # Each parent can only have one child per side
        
        # Check constraints for data validation
        sa.CheckConstraint("side IN ('left', 'right')", name='valid_placement_side'),
        sa.CheckConstraint("status IN ('active', 'removed')", name='valid_placement_status'),
        sa.CheckConstraint("placement_method IN ('automatic', 'user_choice', 'admin')", name='valid_placement_method'),
        sa.CheckConstraint('parent_id != child_id', name='no_self_placement'),
    )
    
    # Create indexes for performance
    op.create_index('idx_placement_parent_side', 'placement', ['parent_id', 'side'])
    op.create_index('idx_placement_child_status', 'placement', ['child_id', 'status'])


def downgrade():
    # ### Drop the placement table ###
    op.drop_index('idx_placement_child_status', table_name='placement')
    op.drop_index('idx_placement_parent_side', table_name='placement')
    op.drop_table('placement')
