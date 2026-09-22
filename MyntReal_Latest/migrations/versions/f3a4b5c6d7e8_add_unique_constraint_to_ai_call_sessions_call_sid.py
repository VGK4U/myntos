"""Add unique constraint to ai_call_sessions.call_sid

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-09-22 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a4b5c6d7e8'
down_revision = 'e2f3a4b5c6d7'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Set safe migration timeouts
    op.execute(sa.text("SET lock_timeout = '5s';"))
    op.execute(sa.text("SET statement_timeout = '30s';"))

    # 2. Defensive cleanup of any legacy duplicate call_sids (keep latest id)
    op.execute(sa.text("""
        DELETE FROM ai_call_sessions a
        USING ai_call_sessions b
        WHERE a.id < b.id
          AND a.call_sid IS NOT NULL
          AND a.call_sid = b.call_sid;
    """))

    # 3. Add unique constraint on ai_call_sessions(call_sid) if not exists
    # Using create_unique_constraint ensures PostgreSQL registers both the constraint
    # and the backing unique btree index needed by ON CONFLICT (call_sid).
    bind = op.get_bind()
    has_uq = bind.execute(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conname = 'uq_ai_call_sessions_call_sid'"
    )).scalar()
    if not has_uq:
        op.create_unique_constraint(
            'uq_ai_call_sessions_call_sid',
            'ai_call_sessions',
            ['call_sid']
        )


def downgrade():
    # 1. Set safe migration timeouts
    op.execute(sa.text("SET lock_timeout = '5s';"))
    op.execute(sa.text("SET statement_timeout = '30s';"))

    # 2. Drop unique constraint
    op.drop_constraint(
        'uq_ai_call_sessions_call_sid',
        'ai_call_sessions',
        type_='unique'
    )
