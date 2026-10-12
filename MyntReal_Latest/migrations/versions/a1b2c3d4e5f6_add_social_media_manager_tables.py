"""Add Social Media Manager multi-tenant tables

Revision ID: a1b2c3d4e5f6
Revises: f3a4b5c6d7e8
Create Date: 2026-10-11 17:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f3a4b5c6d7e8'
branch_labels = None
depends_on = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')


def upgrade():
    # 1. social_account_connections
    op.create_table(
        'social_account_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(length=32), nullable=False),
        sa.Column('platform_account_id', sa.String(length=128), nullable=False),
        sa.Column('account_name', sa.String(length=200), nullable=False),
        sa.Column('account_username', sa.String(length=100), nullable=True),
        sa.Column('profile_image_url', sa.Text(), nullable=True),
        sa.Column('provider_profile_id', sa.String(length=128), nullable=False),
        sa.Column('provider_account_id', sa.String(length=128), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='ACTIVE', nullable=False),
        sa.Column('capabilities', JSON_TYPE, nullable=False),
        sa.Column('access_token_encrypted', sa.Text(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['associated_companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['platform_clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'platform', 'platform_account_id', name='uq_company_social_account')
    )
    op.create_index('ix_social_account_connections_id', 'social_account_connections', ['id'])
    op.create_index('ix_soc_conn_comp_platform', 'social_account_connections', ['company_id', 'platform'])
    op.create_index('ix_soc_conn_tenant_status', 'social_account_connections', ['tenant_id', 'status'])

    # 2. social_calendar_settings
    op.create_table(
        'social_calendar_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('posting_frequency_days', sa.Integer(), server_default='2', nullable=False),
        sa.Column('preferred_time_ist', sa.String(length=10), server_default='10:30', nullable=False),
        sa.Column('timezone', sa.String(length=50), server_default='Asia/Kolkata', nullable=False),
        sa.Column('brand_voice', sa.String(length=100), server_default='Professional & Engaging', nullable=False),
        sa.Column('target_audience', sa.Text(), nullable=True),
        sa.Column('content_themes', JSON_TYPE, nullable=False),
        sa.Column('default_hashtags', JSON_TYPE, nullable=False),
        sa.Column('helpline_phone', sa.String(length=30), nullable=True),
        sa.Column('website_url', sa.String(length=255), nullable=True),
        sa.Column('enabled_platforms', JSON_TYPE, nullable=False),
        sa.Column('require_admin_approval', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('provider_profile_id', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['associated_companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['platform_clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id')
    )
    op.create_index('ix_social_calendar_settings_id', 'social_calendar_settings', ['id'])
    op.create_index('ix_soc_cal_prov_prof', 'social_calendar_settings', ['provider_profile_id'])

    # 3. social_posts
    op.create_table(
        'social_posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('campaign_name', sa.String(length=150), nullable=True),
        sa.Column('topic_theme', sa.String(length=100), nullable=False),
        sa.Column('master_caption', sa.Text(), nullable=False),
        sa.Column('master_hashtags', JSON_TYPE, nullable=False),
        sa.Column('call_to_action_url', sa.Text(), nullable=True),
        sa.Column('call_to_action_text', sa.String(length=100), nullable=True),
        sa.Column('media_urls', JSON_TYPE, nullable=False),
        sa.Column('media_type', sa.String(length=20), server_default='IMAGE', nullable=False),
        sa.Column('suggested_media_brief', sa.Text(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='DRAFT', nullable=False),
        sa.Column('created_by_staff_id', sa.Integer(), nullable=True),
        sa.Column('approved_by_staff_id', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['approved_by_staff_id'], ['staff_employees.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['company_id'], ['associated_companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_staff_id'], ['staff_employees.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['platform_clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_social_posts_id', 'social_posts', ['id'])
    op.create_index('ix_social_posts_sched_status', 'social_posts', ['status', 'scheduled_at'])
    op.create_index('ix_social_posts_comp_sched', 'social_posts', ['company_id', 'scheduled_at'])

    # 4. social_post_dispatches
    op.create_table(
        'social_post_dispatches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('connection_id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(length=32), nullable=False),
        sa.Column('tailored_caption', sa.Text(), nullable=False),
        sa.Column('tailored_media_urls', JSON_TYPE, nullable=False),
        sa.Column('dispatch_key', sa.String(length=128), nullable=False),
        sa.Column('provider_post_id', sa.String(length=128), nullable=True),
        sa.Column('published_url', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='PENDING', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['connection_id'], ['social_account_connections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['social_posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dispatch_key')
    )
    op.create_index('ix_social_post_dispatches_id', 'social_post_dispatches', ['id'])
    op.create_index('ix_soc_disp_post_plat', 'social_post_dispatches', ['post_id', 'platform'])
    op.create_index('ix_soc_disp_status', 'social_post_dispatches', ['status'])

    # 5. social_analytics_snapshots
    op.create_table(
        'social_analytics_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('dispatch_id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(length=32), nullable=False),
        sa.Column('impressions', sa.Integer(), nullable=True),
        sa.Column('reach', sa.Integer(), nullable=True),
        sa.Column('likes', sa.Integer(), nullable=True),
        sa.Column('comments', sa.Integer(), nullable=True),
        sa.Column('shares', sa.Integer(), nullable=True),
        sa.Column('clicks', sa.Integer(), nullable=True),
        sa.Column('video_views', sa.Integer(), nullable=True),
        sa.Column('engagement_rate', sa.Float(), nullable=True),
        sa.Column('data_availability', sa.String(length=32), server_default='AVAILABLE', nullable=False),
        sa.Column('raw_metrics', JSON_TYPE, nullable=False),
        sa.Column('synced_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['associated_companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['dispatch_id'], ['social_post_dispatches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['platform_clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dispatch_id')
    )
    op.create_index('ix_social_analytics_snapshots_id', 'social_analytics_snapshots', ['id'])
    op.create_index('ix_soc_ana_comp_plat', 'social_analytics_snapshots', ['company_id', 'platform'])

    # 6. social_webhook_events
    op.create_table(
        'social_webhook_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=32), server_default='zernio', nullable=False),
        sa.Column('event_id', sa.String(length=128), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('payload', JSON_TYPE, nullable=False),
        sa.Column('processed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id')
    )
    op.create_index('ix_social_webhook_events_id', 'social_webhook_events', ['id'])


def downgrade():
    op.drop_table('social_webhook_events')
    op.drop_table('social_analytics_snapshots')
    op.drop_table('social_post_dispatches')
    op.drop_table('social_posts')
    op.drop_table('social_calendar_settings')
    op.drop_table('social_account_connections')
