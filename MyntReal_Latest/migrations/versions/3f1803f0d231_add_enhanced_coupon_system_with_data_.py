"""add_enhanced_coupon_system_with_data_migration

Revision ID: 3f1803f0d231
Revises: 7330c5c0757d
Create Date: 2025-09-18 08:52:08.635314

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3f1803f0d231'
down_revision = '7330c5c0757d'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create Enhanced Coupon System Tables
    
    This migration creates:
    1. enhanced_coupon table - main coupon system
    2. enhanced_coupon_history table - audit trail
    3. ev_purchase_coupon table - backward compatibility alias
    
    Since no existing EVPurchaseCoupon data exists in the database,
    this is a fresh table creation rather than data migration.
    """
    from alembic import op
    import sqlalchemy as sa
    
    # Create enhanced_coupon table
    op.create_table(
        'enhanced_coupon',
        sa.Column('coupon_id', sa.Integer, primary_key=True, autoincrement=True),
        
        # REQUIRED FIELDS
        sa.Column('coupon_code', sa.String(20), nullable=False, unique=True),
        sa.Column('coupon_value', sa.Integer, nullable=False),
        sa.Column('issue_date', sa.DateTime, default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        
        # Calculated expiry dates (stored for performance)
        sa.Column('ev_expiry_date', sa.DateTime, nullable=True),
        sa.Column('training_expiry_date', sa.DateTime, nullable=True),
        
        # Status tracking
        sa.Column('status', sa.String(20), default='issued', nullable=False),
        
        # User assignment
        sa.Column('user_id', sa.String(12), sa.ForeignKey('user.id'), nullable=False),
        
        # NEW REQUIRED FIELDS for enhanced functionality
        sa.Column('admin_claim_status', sa.String(20), default='pending', nullable=False),
        sa.Column('redemption_type', sa.String(20), nullable=True),
        sa.Column('redeemed_amount', sa.Float, default=0.0, nullable=False),
        
        # Additional tracking fields
        sa.Column('redemption_date', sa.DateTime, nullable=True),
        sa.Column('approval_date', sa.DateTime, nullable=True),
        sa.Column('approved_by', sa.String(12), sa.ForeignKey('user.id'), nullable=True),
        
        # Business logic fields
        sa.Column('training_course_fee', sa.Float, nullable=True),
        sa.Column('ev_model_redeemed', sa.String(50), nullable=True),
        
        # Migration and audit fields
        sa.Column('created_by', sa.String(12), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('updated_at', sa.DateTime, default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        
        # Legacy compatibility fields
        sa.Column('legacy_coupon_id', sa.Integer, nullable=True),
        sa.Column('legacy_status', sa.String(20), nullable=True),
        
        # Database constraints
        sa.CheckConstraint("status IN ('issued', 'redeemed_ev', 'redeemed_training', 'expired')", name='valid_enhanced_coupon_status'),
        sa.CheckConstraint("admin_claim_status IN ('pending', 'approved', 'rejected')", name='valid_admin_claim_status'),
        sa.CheckConstraint("redemption_type IN ('ev', 'training') OR redemption_type IS NULL", name='valid_redemption_type'),
        sa.CheckConstraint("coupon_value > 0", name='positive_enhanced_coupon_value'),
        sa.CheckConstraint("redeemed_amount >= 0", name='non_negative_redeemed_amount'),
        sa.CheckConstraint("coupon_value IN (15000, 7500)", name='valid_coupon_values'),
    )
    
    # Create enhanced_coupon_history table
    op.create_table(
        'enhanced_coupon_history',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        
        # Associated enhanced coupon
        sa.Column('coupon_id', sa.Integer, sa.ForeignKey('enhanced_coupon.coupon_id'), nullable=False),
        
        # Action tracking
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('timestamp', sa.DateTime, default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('performed_by', sa.String(12), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        
        # State tracking
        sa.Column('old_status', sa.String(20), nullable=True),
        sa.Column('new_status', sa.String(20), nullable=True),
        sa.Column('old_admin_claim_status', sa.String(20), nullable=True),
        sa.Column('new_admin_claim_status', sa.String(20), nullable=True),
        
        # Redemption tracking
        sa.Column('redemption_type', sa.String(20), nullable=True),
        sa.Column('redemption_amount', sa.Float, nullable=True),
        sa.Column('course_fee', sa.Float, nullable=True),
        sa.Column('benefit_amount', sa.Float, nullable=True),
        
        # Context fields
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(255), nullable=True),
        sa.Column('additional_data', sa.JSON, nullable=True),
        
        # Database constraints
        sa.CheckConstraint("action IN ('issued', 'redeemed', 'approved', 'rejected', 'expired', 'updated', 'created')", name='valid_coupon_history_action'),
    )
    
    # Create backward compatibility table (ev_purchase_coupon) as a view-like alias
    # This ensures existing foreign keys work without code changes
    op.create_table(
        'ev_purchase_coupon',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        
        # Map to enhanced_coupon fields for compatibility
        sa.Column('coupon_id', sa.Integer, sa.ForeignKey('enhanced_coupon.coupon_id'), nullable=False, unique=True),
        sa.Column('coupon_pin', sa.String(20), nullable=False, unique=True),  # Maps to coupon_code
        sa.Column('coupon_value', sa.Integer, nullable=False),
        sa.Column('status', sa.String(20), default='Generated', nullable=False),  # Legacy status mapping
        sa.Column('generated_date', sa.DateTime, default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('user_id', sa.String(12), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('tagged_date', sa.DateTime, nullable=True),
        sa.Column('activated_date', sa.DateTime, nullable=True),
        sa.Column('used_date', sa.DateTime, nullable=True),
        sa.Column('expiry_date', sa.DateTime, nullable=True),
        
        # Admin tracking
        sa.Column('created_by', sa.String(12), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('tagged_by', sa.String(12), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        
        # Additional compatibility fields
        sa.Column('pin_id', sa.Integer, nullable=True),
        sa.Column('amount_paid', sa.Integer, nullable=True),
        sa.Column('payment_screenshot', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    
    # Create indexes for performance
    op.create_index('idx_enhanced_coupon_user_id', 'enhanced_coupon', ['user_id'])
    op.create_index('idx_enhanced_coupon_status', 'enhanced_coupon', ['status'])
    op.create_index('idx_enhanced_coupon_code', 'enhanced_coupon', ['coupon_code'])
    op.create_index('idx_enhanced_coupon_issue_date', 'enhanced_coupon', ['issue_date'])
    op.create_index('idx_enhanced_coupon_history_coupon_id', 'enhanced_coupon_history', ['coupon_id'])
    op.create_index('idx_enhanced_coupon_history_timestamp', 'enhanced_coupon_history', ['timestamp'])
    op.create_index('idx_ev_purchase_coupon_user_id', 'ev_purchase_coupon', ['user_id'])
    op.create_index('idx_ev_purchase_coupon_coupon_id', 'ev_purchase_coupon', ['coupon_id'])
    
    print("✅ Enhanced Coupon System tables created successfully")
    print("📊 Tables created: enhanced_coupon, enhanced_coupon_history, ev_purchase_coupon (compatibility)")
    print("🔗 Foreign key relationships established")
    print("📈 Performance indexes created")


def downgrade():
    """
    Remove Enhanced Coupon System Tables
    
    DANGER: This will permanently delete all enhanced coupon data!
    Only use this in development or with proper backup procedures.
    """
    from alembic import op
    
    # Drop indexes first
    op.drop_index('idx_ev_purchase_coupon_coupon_id', table_name='ev_purchase_coupon')
    op.drop_index('idx_ev_purchase_coupon_user_id', table_name='ev_purchase_coupon')
    op.drop_index('idx_enhanced_coupon_history_timestamp', table_name='enhanced_coupon_history')
    op.drop_index('idx_enhanced_coupon_history_coupon_id', table_name='enhanced_coupon_history')
    op.drop_index('idx_enhanced_coupon_issue_date', table_name='enhanced_coupon')
    op.drop_index('idx_enhanced_coupon_code', table_name='enhanced_coupon')
    op.drop_index('idx_enhanced_coupon_status', table_name='enhanced_coupon')
    op.drop_index('idx_enhanced_coupon_user_id', table_name='enhanced_coupon')
    
    # Drop tables in reverse order (child tables first)
    op.drop_table('ev_purchase_coupon')  # Compatibility table
    op.drop_table('enhanced_coupon_history')  # History table
    op.drop_table('enhanced_coupon')  # Main table
    
    print("⚠️  Enhanced Coupon System tables removed")
    print("💥 All coupon data has been permanently deleted")
