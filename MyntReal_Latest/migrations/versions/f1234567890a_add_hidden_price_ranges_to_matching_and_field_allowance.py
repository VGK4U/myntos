"""Add hidden price ranges to MatchingAwardTier and FieldAllowanceProgress models

Revision ID: f1234567890a
Revises: bac33708126a
Create Date: 2025-09-16 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1234567890a'
down_revision = 'bac33708126a'
branch_labels = None
depends_on = None


def upgrade():
    # Add hidden price range fields to MatchingAwardTier model
    with op.batch_alter_table('matching_award_tier', schema=None) as batch_op:
        # Add price range fields
        batch_op.add_column(sa.Column('price_range_from', sa.DECIMAL(precision=12, scale=2), nullable=True))
        batch_op.add_column(sa.Column('price_range_to', sa.DECIMAL(precision=12, scale=2), nullable=True))
        batch_op.add_column(sa.Column('actual_price', sa.DECIMAL(precision=12, scale=2), nullable=True))
        
        # Add price visibility and audit fields
        batch_op.add_column(sa.Column('is_price_hidden', sa.Boolean(), nullable=False, server_default=sa.text('1')))
        batch_op.add_column(sa.Column('price_created_by', sa.String(length=12), nullable=True))
        batch_op.add_column(sa.Column('price_last_updated_by', sa.String(length=12), nullable=True))
        batch_op.add_column(sa.Column('price_last_updated_at', sa.DateTime(), nullable=True))
        
        # Add foreign key constraints for price audit fields
        batch_op.create_foreign_key(
            'fk_matching_award_price_created_by_user_id', 'user', ['price_created_by'], ['id']
        )
        batch_op.create_foreign_key(
            'fk_matching_award_price_updated_by_user_id', 'user', ['price_last_updated_by'], ['id']
        )

    # Add hidden price range fields to FieldAllowanceProgress model
    with op.batch_alter_table('field_allowance_progress', schema=None) as batch_op:
        # Add price range fields
        batch_op.add_column(sa.Column('price_range_from', sa.DECIMAL(precision=12, scale=2), nullable=True))
        batch_op.add_column(sa.Column('price_range_to', sa.DECIMAL(precision=12, scale=2), nullable=True))
        batch_op.add_column(sa.Column('actual_price', sa.DECIMAL(precision=12, scale=2), nullable=True))
        
        # Add price visibility and audit fields
        batch_op.add_column(sa.Column('is_price_hidden', sa.Boolean(), nullable=False, server_default=sa.text('1')))
        batch_op.add_column(sa.Column('price_created_by', sa.String(length=12), nullable=True))
        batch_op.add_column(sa.Column('price_last_updated_by', sa.String(length=12), nullable=True))
        batch_op.add_column(sa.Column('price_last_updated_at', sa.DateTime(), nullable=True))
        
        # Add foreign key constraints for price audit fields
        batch_op.create_foreign_key(
            'fk_field_allowance_price_created_by_user_id', 'user', ['price_created_by'], ['id']
        )
        batch_op.create_foreign_key(
            'fk_field_allowance_price_updated_by_user_id', 'user', ['price_last_updated_by'], ['id']
        )
    
    # Set default values for existing records - MatchingAwardTier
    op.execute("""
        UPDATE matching_award_tier SET 
            price_range_from = 0.00,
            price_range_to = 0.00,
            actual_price = 0.00,
            price_last_updated_at = datetime('now')
        WHERE price_range_from IS NULL
    """)
    
    # Set default values for existing records - FieldAllowanceProgress
    op.execute("""
        UPDATE field_allowance_progress SET 
            price_range_from = 0.00,
            price_range_to = 0.00,
            actual_price = 0.00,
            price_last_updated_at = datetime('now')
        WHERE price_range_from IS NULL
    """)
    
    # Make price fields required after setting defaults - MatchingAwardTier
    with op.batch_alter_table('matching_award_tier', schema=None) as batch_op:
        batch_op.alter_column('price_range_from', nullable=False, server_default='0.00')
        batch_op.alter_column('price_range_to', nullable=False, server_default='0.00')
        batch_op.alter_column('actual_price', nullable=False, server_default='0.00')
    
    # Make price fields required after setting defaults - FieldAllowanceProgress
    with op.batch_alter_table('field_allowance_progress', schema=None) as batch_op:
        batch_op.alter_column('price_range_from', nullable=False, server_default='0.00')
        batch_op.alter_column('price_range_to', nullable=False, server_default='0.00')
        batch_op.alter_column('actual_price', nullable=False, server_default='0.00')
    
    # Add check constraints for data validation - MatchingAwardTier
    op.execute("""
        ALTER TABLE matching_award_tier ADD CONSTRAINT chk_matching_award_price_range_from_positive 
        CHECK (price_range_from >= 0)
    """)
    op.execute("""
        ALTER TABLE matching_award_tier ADD CONSTRAINT chk_matching_award_price_range_to_positive 
        CHECK (price_range_to >= 0)
    """)
    op.execute("""
        ALTER TABLE matching_award_tier ADD CONSTRAINT chk_matching_award_price_range_valid 
        CHECK (price_range_to >= price_range_from)
    """)
    
    # Add check constraints for data validation - FieldAllowanceProgress
    op.execute("""
        ALTER TABLE field_allowance_progress ADD CONSTRAINT chk_field_allowance_price_range_from_positive 
        CHECK (price_range_from >= 0)
    """)
    op.execute("""
        ALTER TABLE field_allowance_progress ADD CONSTRAINT chk_field_allowance_price_range_to_positive 
        CHECK (price_range_to >= 0)
    """)
    op.execute("""
        ALTER TABLE field_allowance_progress ADD CONSTRAINT chk_field_allowance_price_range_valid 
        CHECK (price_range_to >= price_range_from)
    """)
    
    # Create indexes for better performance on price queries
    op.create_index('idx_matching_award_price_hidden_actual', 'matching_award_tier', ['is_price_hidden', 'actual_price'])
    op.create_index('idx_matching_award_price_audit', 'matching_award_tier', ['price_created_by', 'price_last_updated_at'])
    op.create_index('idx_field_allowance_price_hidden_actual', 'field_allowance_progress', ['is_price_hidden', 'actual_price'])
    op.create_index('idx_field_allowance_price_audit', 'field_allowance_progress', ['price_created_by', 'price_last_updated_at'])


def downgrade():
    # Remove indexes first
    op.drop_index('idx_field_allowance_price_audit', table_name='field_allowance_progress')
    op.drop_index('idx_field_allowance_price_hidden_actual', table_name='field_allowance_progress')
    op.drop_index('idx_matching_award_price_audit', table_name='matching_award_tier')
    op.drop_index('idx_matching_award_price_hidden_actual', table_name='matching_award_tier')
    
    # Drop check constraints - FieldAllowanceProgress
    op.execute("ALTER TABLE field_allowance_progress DROP CONSTRAINT IF EXISTS chk_field_allowance_price_range_valid")
    op.execute("ALTER TABLE field_allowance_progress DROP CONSTRAINT IF EXISTS chk_field_allowance_price_range_to_positive")
    op.execute("ALTER TABLE field_allowance_progress DROP CONSTRAINT IF EXISTS chk_field_allowance_price_range_from_positive")
    
    # Drop check constraints - MatchingAwardTier
    op.execute("ALTER TABLE matching_award_tier DROP CONSTRAINT IF EXISTS chk_matching_award_price_range_valid")
    op.execute("ALTER TABLE matching_award_tier DROP CONSTRAINT IF EXISTS chk_matching_award_price_range_to_positive")
    op.execute("ALTER TABLE matching_award_tier DROP CONSTRAINT IF EXISTS chk_matching_award_price_range_from_positive")
    
    # Remove columns with foreign key constraints - FieldAllowanceProgress
    with op.batch_alter_table('field_allowance_progress', schema=None) as batch_op:
        # Drop foreign key constraints first
        batch_op.drop_constraint('fk_field_allowance_price_updated_by_user_id', type_='foreignkey')
        batch_op.drop_constraint('fk_field_allowance_price_created_by_user_id', type_='foreignkey')
        
        # Drop columns
        batch_op.drop_column('price_last_updated_at')
        batch_op.drop_column('price_last_updated_by')
        batch_op.drop_column('price_created_by')
        batch_op.drop_column('is_price_hidden')
        batch_op.drop_column('actual_price')
        batch_op.drop_column('price_range_to')
        batch_op.drop_column('price_range_from')
    
    # Remove columns with foreign key constraints - MatchingAwardTier
    with op.batch_alter_table('matching_award_tier', schema=None) as batch_op:
        # Drop foreign key constraints first
        batch_op.drop_constraint('fk_matching_award_price_updated_by_user_id', type_='foreignkey')
        batch_op.drop_constraint('fk_matching_award_price_created_by_user_id', type_='foreignkey')
        
        # Drop columns
        batch_op.drop_column('price_last_updated_at')
        batch_op.drop_column('price_last_updated_by')
        batch_op.drop_column('price_created_by')
        batch_op.drop_column('is_price_hidden')
        batch_op.drop_column('actual_price')
        batch_op.drop_column('price_range_to')
        batch_op.drop_column('price_range_from')