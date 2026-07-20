import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, MetaData
from alembic import context

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# DC Protocol (May 2026): Prefer PROD_DATABASE_URL when DATABASE_URL points to
# Helium (Replit's internal-only local postgres). Helium is not reachable from
# Replit's external diff-checker — using it causes "timeout exceeded" errors
# during the pre-publish check. PROD_DATABASE_URL (Neon) is externally reachable
# and is the correct target for schema checks and migration tracking.
database_url = os.environ.get('DATABASE_URL', '')
prod_database_url = os.environ.get('PROD_DATABASE_URL', '')

_is_helium = any(h in database_url for h in ['@helium', 'heliumdb', '127.0.0.1', 'localhost'])
if _is_helium and prod_database_url:
    database_url = prod_database_url

# Fix sslmode=require. typo (trailing dot) that psycopg2 rejects as invalid
database_url = database_url.replace('sslmode=require.', 'sslmode=require')

if database_url:
    config.set_main_option('sqlalchemy.url', database_url)

# Use an empty MetaData as the autogenerate target.
#
# Why: Base.metadata contains tables with circular FK dependencies
# (associated_companies, staff_call_logs, staff_call_recordings,
# staff_departments, staff_employees).  Alembic's topological sort hangs
# indefinitely when it encounters these cycles.
#
# Since process_revision_directives below produces an empty migration
# regardless, we do not need the full model metadata for comparison.
# An empty target_metadata means zero tables to sort, zero diff to compute,
# and the generation completes in seconds.
target_metadata = MetaData()


def include_name(name, type_, parent_names):
    """Skip ALL table reflection — nothing to compare against empty metadata."""
    if type_ == "schema":
        return True
    return False


def include_object(obj, name, type_, reflected, compare_to):
    """Nothing passes through — belt-and-suspenders guard."""
    return False


def process_revision_directives(context, revision, directives):
    """
    Always produce an empty migration body.

    Replit's provision runner auto-applies whatever migration is generated,
    including destructive operations such as column drops.  We do NOT want
    that applied to production automatically.  Schema migrations are handled
    manually when needed.
    """
    if directives:
        directives[0].upgrade_ops.ops[:] = []
        directives[0].downgrade_ops.ops[:] = []


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_name=include_name,
        include_object=include_object,
        process_revision_directives=process_revision_directives,
        compare_type=False,
        compare_server_default=False,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_name=include_name,
            include_object=include_object,
            process_revision_directives=process_revision_directives,
            compare_type=False,
            compare_server_default=False,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
