"""Add hidden price ranges to Bonanza model

Revision ID: bac33708126a
Revises: 72c8859d2903
Create Date: 2025-09-16 14:26:57.685261

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bac33708126a'
down_revision = '72c8859d2903'
branch_labels = None
depends_on = None


def upgrade():
    # Add hidden price range fields to Bonanza model
    with op.batch_alter_table('bonanza', schema=None) as batch_op:
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
            'fk_bonanza_price_created_by_user_id', 'user', ['price_created_by'], ['id']
        )
        batch_op.create_foreign_key(
            'fk_bonanza_price_updated_by_user_id', 'user', ['price_last_updated_by'], ['id']
        )
    
    # Add check constraints for price validation - using raw SQL for better compatibility
    op.execute("""
        UPDATE bonanza SET 
            price_range_from = 0.00,
            price_range_to = 0.00,
            actual_price = 0.00
        WHERE price_range_from IS NULL
    """)
    
    # Make price fields required after setting defaults
    with op.batch_alter_table('bonanza', schema=None) as batch_op:
        batch_op.alter_column('price_range_from', nullable=False, server_default='0.00')
        batch_op.alter_column('price_range_to', nullable=False, server_default='0.00')
        batch_op.alter_column('actual_price', nullable=False, server_default='0.00')
    
    # Add check constraints for data validation
    op.execute("""
        ALTER TABLE bonanza ADD CONSTRAINT chk_bonanza_price_range_from_positive 
        CHECK (price_range_from >= 0)
    """)
    op.execute("""
        ALTER TABLE bonanza ADD CONSTRAINT chk_bonanza_price_range_to_positive 
        CHECK (price_range_to >= 0)
    """)
    op.execute("""
        ALTER TABLE bonanza ADD CONSTRAINT chk_bonanza_price_range_valid 
        CHECK (price_range_to >= price_range_from)
    """)
    
    # Create index for better performance on price queries
    op.create_index('idx_bonanza_price_hidden_actual', 'bonanza', ['is_price_hidden', 'actual_price'])
    op.create_index('idx_bonanza_price_audit', 'bonanza', ['price_created_by', 'price_last_updated_at'])


def downgrade():
    # Remove indexes first
    op.drop_index('idx_bonanza_price_audit', table_name='bonanza')
    op.drop_index('idx_bonanza_price_hidden_actual', table_name='bonanza')
    
    # Drop check constraints
    op.execute("ALTER TABLE bonanza DROP CONSTRAINT IF EXISTS chk_bonanza_price_range_valid")
    op.execute("ALTER TABLE bonanza DROP CONSTRAINT IF EXISTS chk_bonanza_price_range_to_positive")
    op.execute("ALTER TABLE bonanza DROP CONSTRAINT IF EXISTS chk_bonanza_price_range_from_positive")
    
    # Remove columns with foreign key constraints
    with op.batch_alter_table('bonanza', schema=None) as batch_op:
        # Drop foreign key constraints first
        batch_op.drop_constraint('fk_bonanza_price_updated_by_user_id', type_='foreignkey')
        batch_op.drop_constraint('fk_bonanza_price_created_by_user_id', type_='foreignkey')
        
        # Drop columns
        batch_op.drop_column('price_last_updated_at')
        batch_op.drop_column('price_last_updated_by')
        batch_op.drop_column('price_created_by')
        batch_op.drop_column('is_price_hidden')
        batch_op.drop_column('actual_price')
        batch_op.drop_column('price_range_to')
        batch_op.drop_column('price_range_from')
