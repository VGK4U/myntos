"""Add games, points and rewards module

Revision ID: g1a2b3c4d5e6
Revises: f3a4b5c6d7e8
Create Date: 2026-10-17 08:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g1a2b3c4d5e6'
down_revision = 'f3a4b5c6d7e8'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add loyalty_points_balance to customer_profiles if not present
    conn = op.get_bind()
    try:
        conn.execute(sa.text("""
            ALTER TABLE customer_profiles 
            ADD COLUMN IF NOT EXISTS loyalty_points_balance NUMERIC(15, 2) DEFAULT 0.00 NOT NULL;
        """))
    except Exception:
        pass

    # 2. Create game_sessions table
    op.create_table(
        'game_sessions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('session_token', sa.String(length=64), unique=True, nullable=False, index=True),
        sa.Column('game_type', sa.String(length=32), nullable=False, index=True),
        sa.Column('account_type', sa.String(length=32), nullable=False, server_default='GUEST', index=True),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customer_profiles.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('partner_id', sa.Integer(), sa.ForeignKey('official_partners.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE', index=True),
        sa.Column('score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('best_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('lines_cleared', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('items_collected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('distance_travelled', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duration_seconds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reward_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reward_status', sa.String(length=32), nullable=False, server_default='PENDING'),
        sa.Column('claim_token', sa.String(length=64), unique=True, nullable=True, index=True),
        sa.Column('character_id', sa.String(length=32), nullable=False, server_default='volt_fox'),
        sa.Column('server_seed', sa.String(length=64), nullable=False),
        sa.Column('telemetry_summary', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_game_sess_cust_date', 'game_sessions', ['customer_id', 'created_at'])
    op.create_index('idx_game_sess_part_date', 'game_sessions', ['partner_id', 'created_at'])
    op.create_index('idx_game_sess_type_status', 'game_sessions', ['game_type', 'status'])

    # 3. Create customer_points_ledger table
    op.create_table(
        'customer_points_ledger',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customer_profiles.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('points_credit', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('points_debit', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('balance_after', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('reason_code', sa.String(length=40), nullable=False),
        sa.Column('reference_type', sa.String(length=40), nullable=True),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_cust_pts_ledger_cust_created', 'customer_points_ledger', ['customer_id', 'created_at'])

    # 4. Create game_reward_codes table
    op.create_table(
        'game_reward_codes',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('code_hash', sa.String(length=64), unique=True, nullable=False, index=True),
        sa.Column('game_session_id', sa.Integer(), sa.ForeignKey('game_sessions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('points_value', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE', index=True),
        sa.Column('claimed_by_account_type', sa.String(length=32), nullable=True),
        sa.Column('claimed_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('claimed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('idx_game_reward_status_expires', 'game_reward_codes', ['status', 'expires_at'])


def downgrade():
    op.drop_table('game_reward_codes')
    op.drop_table('customer_points_ledger')
    op.drop_table('game_sessions')
    try:
        op.drop_column('customer_profiles', 'loyalty_points_balance')
    except Exception:
        pass
