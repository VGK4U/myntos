"""Add comprehensive KYC management system with document versioning and approval history

Revision ID: eedc69b69c77
Revises: 4ded27b36619
Create Date: 2025-09-14 15:07:37.713248

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'eedc69b69c77'
down_revision = '4ded27b36619'
branch_labels = None
depends_on = None


def upgrade():
    # Safely drop legacy table if present
    op.execute("DROP TABLE IF EXISTS kyc__document")
    
    # Create kyc_document table with all columns and constraints
    op.create_table(
        'kyc_document',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('owner_id', sa.Integer, sa.ForeignKey('user.id'), nullable=False),
        sa.Column('document_type', sa.String(50), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='Pending'),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('file_size', sa.Integer, nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('previous_version_id', sa.Integer, sa.ForeignKey('kyc_document.id'), nullable=True),
        sa.Column('is_current_version', sa.Boolean, nullable=False, server_default=sa.text('1')),
        sa.Column('uploaded_at', sa.DateTime, nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('reviewed_by_id', sa.Integer, sa.ForeignKey('user.id'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime, nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),
        sa.Column('admin_notes', sa.Text, nullable=True),
        sa.CheckConstraint("document_type IN ('passport_photo','aadhar_front','aadhar_back','pan_card','bank_passbook')", name='valid_document_type'),
        sa.CheckConstraint("status IN ('Pending','Approved','Rejected')", name='valid_status'),
        sa.CheckConstraint('version > 0', name='positive_version'),
        sa.CheckConstraint('file_size > 0', name='positive_file_size'),
        sa.CheckConstraint("(status = 'Pending') OR (status IN ('Approved','Rejected') AND reviewed_by_id IS NOT NULL AND reviewed_at IS NOT NULL)", name='approval_integrity')
    )
    
    # Create kyc_document indexes
    op.create_index('idx_kyc_owner_type_current', 'kyc_document', ['owner_id','document_type','is_current_version'])
    op.create_index('idx_kyc_status_reviewed', 'kyc_document', ['status','reviewed_at'])
    op.create_index('idx_kyc_version_chain', 'kyc_document', ['previous_version_id'])
    op.create_index(
        'idx_kyc_unique_current', 'kyc_document', ['owner_id','document_type'], unique=True,
        sqlite_where=sa.text('is_current_version = 1'),
        postgresql_where=sa.text('is_current_version = true')
    )
    
    # Create kyc_approval table with all columns and constraints  
    op.create_table(
        'kyc_approval',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('kyc_document_id', sa.Integer, sa.ForeignKey('kyc_document.id'), nullable=False),
        sa.Column('reviewer_id', sa.Integer, sa.ForeignKey('user.id'), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('previous_status', sa.String(20), nullable=False),
        sa.Column('new_status', sa.String(20), nullable=False),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('admin_notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.CheckConstraint("action IN ('Approved','Rejected','Reviewed')", name='valid_approval_action'),
        sa.CheckConstraint("previous_status IN ('Pending','Approved','Rejected')", name='valid_previous_status'),
        sa.CheckConstraint("new_status IN ('Pending','Approved','Rejected')", name='valid_new_status')
    )
    
    # Create kyc_approval indexes
    op.create_index('idx_kyc_approval_document', 'kyc_approval', ['kyc_document_id'])
    op.create_index('idx_kyc_approval_reviewer', 'kyc_approval', ['reviewer_id'])
    op.create_index('idx_kyc_approval_created', 'kyc_approval', ['created_at'])


def downgrade():
    # Drop indexes first
    op.drop_index('idx_kyc_approval_created', table_name='kyc_approval')
    op.drop_index('idx_kyc_approval_reviewer', table_name='kyc_approval')
    op.drop_index('idx_kyc_approval_document', table_name='kyc_approval')
    
    op.drop_index('idx_kyc_unique_current', table_name='kyc_document')
    op.drop_index('idx_kyc_version_chain', table_name='kyc_document')
    op.drop_index('idx_kyc_status_reviewed', table_name='kyc_document')
    op.drop_index('idx_kyc_owner_type_current', table_name='kyc_document')
    
    # Drop tables
    op.drop_table('kyc_approval')
    op.drop_table('kyc_document')
