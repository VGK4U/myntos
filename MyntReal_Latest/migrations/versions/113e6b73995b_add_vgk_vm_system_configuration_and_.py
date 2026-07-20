"""add_vgk_vm_system_configuration_and_user_fields

Revision ID: 113e6b73995b
Revises: b4dc7f54d670
Create Date: 2025-09-19 16:22:22.683379

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '113e6b73995b'
down_revision = 'b4dc7f54d670'
branch_labels = None
depends_on = None


def upgrade():
    # Add VGK VM System Configuration fields to AppSettings
    with op.batch_alter_table('app_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('coupon_popup_enabled', sa.Boolean(), nullable=False, server_default='true'))
        batch_op.add_column(sa.Column('popup_config_updated_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('popup_config_updated_by', sa.String(length=12), nullable=True))
        
        # Add foreign key constraint for popup_config_updated_by
        batch_op.create_foreign_key(
            'fk_app_settings_popup_config_updated_by',
            'user',
            ['popup_config_updated_by'],
            ['id']
        )
    
    # Note: User model fields user_level and activation_sequence already exist in the model
    # but they were added without migration. Since they are nullable, we don't need to
    # modify the existing table structure, just ensure the model matches the database.
    
    # If the user table doesn't have these columns, add them
    try:
        # Check if columns exist by attempting to add them
        with op.batch_alter_table('user', schema=None) as batch_op:
            # Only add if they don't exist (will be handled by try/catch)
            batch_op.add_column(sa.Column('user_level', sa.String(length=50), nullable=True))
            batch_op.add_column(sa.Column('activation_sequence', sa.Integer(), nullable=True))
    except Exception:
        # Columns already exist, which is expected
        pass


def downgrade():
    # Remove VGK VM System Configuration fields from AppSettings
    with op.batch_alter_table('app_settings', schema=None) as batch_op:
        # Drop foreign key constraint first
        batch_op.drop_constraint('fk_app_settings_popup_config_updated_by', type_='foreignkey')
        
        batch_op.drop_column('popup_config_updated_by')
        batch_op.drop_column('popup_config_updated_at') 
        batch_op.drop_column('coupon_popup_enabled')
    
    # Remove User model fields (only if they exist)
    try:
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.drop_column('activation_sequence')
            batch_op.drop_column('user_level')
    except Exception:
        # Columns may not exist in some environments
        pass
