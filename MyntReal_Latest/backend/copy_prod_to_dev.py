"""
Production to Development Database Copy - Using pg_dump approach
Drops all FK constraints, copies data, then recreates them.
Uses psycopg2 COPY for JSONB/array compatibility.

Tables that exist only in prod are skipped cleanly (no error).
FK constraints that reference prod-only tables are skipped with a warning.
FK constraints with orphaned-row violations are recreated as NOT VALID
(constraint exists but pre-existing rows are not validated).
"""
import os
import sys
import psycopg2
from io import BytesIO
import time

PROD_DB_URL = "postgresql://neondb_owner:npg_tnS3mrd1KFgk@ep-dry-lab-ad9prs0y.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
DEV_DB_URL = os.environ.get("DATABASE_URL")

SKIP_TABLES = ['alembic_version', 'apscheduler_jobs']


def get_all_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        return [row[0] for row in cur.fetchall()]


def get_fk_constraints(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT tc.constraint_name, tc.table_name,
                   pg_get_constraintdef(pgc.oid) AS constraint_def
            FROM information_schema.table_constraints tc
            JOIN pg_constraint pgc ON pgc.conname = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
            ORDER BY tc.table_name;
        """)
        return cur.fetchall()


def _parse_referenced_table(constraint_def):
    """Extract the referenced table name from a constraint definition string.
    e.g. 'FOREIGN KEY (ev_model_id) REFERENCES ev_model(id)' -> 'ev_model'
    """
    import re
    m = re.search(r'REFERENCES\s+"?(\w+)"?\s*\(', constraint_def, re.IGNORECASE)
    return m.group(1) if m else None


def main():
    print("=" * 60)
    print("PRODUCTION → DEVELOPMENT DATABASE COPY")
    print("Using COPY protocol for full compatibility")
    print("=" * 60)

    if not DEV_DB_URL:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    start_time = time.time()

    prod_conn = psycopg2.connect(PROD_DB_URL)
    print("Connected to production")

    dev_conn = psycopg2.connect(DEV_DB_URL)
    print("Connected to development")

    prod_tables = set(get_all_tables(prod_conn))
    dev_tables = set(get_all_tables(dev_conn))
    common_tables = sorted(prod_tables & dev_tables)
    tables_to_copy = [t for t in common_tables if t not in SKIP_TABLES]

    prod_only = sorted(prod_tables - dev_tables - set(SKIP_TABLES))
    dev_only = sorted(dev_tables - prod_tables - set(SKIP_TABLES))

    print(f"\nTables to copy:         {len(tables_to_copy)}")
    if prod_only:
        print(f"Prod-only (skipped):    {len(prod_only)}")
        for t in prod_only:
            print(f"  SKIP (prod-only): {t}")
    if dev_only:
        print(f"Dev-only (not touched): {len(dev_only)}")
        for t in dev_only:
            print(f"  SKIP (dev-only):  {t}")

    print("\nStep 1: Saving and dropping all FK constraints...")
    fk_constraints = get_fk_constraints(dev_conn)
    print(f"  Found {len(fk_constraints)} FK constraints")

    with dev_conn.cursor() as cur:
        for constraint_name, table_name, _ in fk_constraints:
            try:
                cur.execute(f'ALTER TABLE "{table_name}" DROP CONSTRAINT IF EXISTS "{constraint_name}"')
            except Exception as e:
                dev_conn.rollback()
                print(f"  Warning: Could not drop {constraint_name}: {str(e)[:60]}")
        dev_conn.commit()
    print("  FK constraints dropped")

    print("\nStep 2: Disabling triggers...")
    with dev_conn.cursor() as cur:
        for table in tables_to_copy:
            try:
                cur.execute(f'ALTER TABLE "{table}" DISABLE TRIGGER ALL')
            except Exception:
                dev_conn.rollback()
        dev_conn.commit()

    print("\nStep 3: Truncating all dev tables...")
    with dev_conn.cursor() as cur:
        for table in tables_to_copy:
            try:
                cur.execute(f'TRUNCATE TABLE "{table}" CASCADE')
            except Exception:
                dev_conn.rollback()
                try:
                    cur.execute(f'DELETE FROM "{table}"')
                    dev_conn.commit()
                except Exception:
                    dev_conn.rollback()
        dev_conn.commit()
    print("  Tables truncated")

    print(f"\nStep 4: Copying data using COPY protocol...")
    total_rows = 0
    errors = []
    copied = 0

    for i, table in enumerate(tables_to_copy, 1):
        try:
            with prod_conn.cursor() as prod_cur:
                prod_cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                count = prod_cur.fetchone()[0]

            if count == 0:
                continue

            buf = BytesIO()
            with prod_conn.cursor() as prod_cur:
                copy_sql = f'COPY "{table}" TO STDOUT'
                prod_cur.copy_expert(copy_sql, buf)

            buf.seek(0)

            with dev_conn.cursor() as dev_cur:
                copy_sql = f'COPY "{table}" FROM STDIN'
                dev_cur.copy_expert(copy_sql, buf)
            dev_conn.commit()

            total_rows += count
            copied += 1
            print(f"  [{i}/{len(tables_to_copy)}] {table}: {count} rows")

        except Exception as e:
            dev_conn.rollback()
            error_msg = str(e).split('\n')[0][:100]
            errors.append((table, error_msg))
            if i <= 20 or 'ERROR' in error_msg.upper():
                print(f"  [{i}/{len(tables_to_copy)}] {table}: ERROR - {error_msg}")

    print(f"\nStep 5: Re-enabling triggers...")
    with dev_conn.cursor() as cur:
        for table in tables_to_copy:
            try:
                cur.execute(f'ALTER TABLE "{table}" ENABLE TRIGGER ALL')
            except Exception:
                dev_conn.rollback()
        dev_conn.commit()

    print(f"\nStep 6: Recreating FK constraints...")
    recreated = 0
    skipped_no_ref_table = 0
    fk_not_valid = 0
    fk_errors = []

    with dev_conn.cursor() as cur:
        for constraint_name, table_name, constraint_def in fk_constraints:
            ref_table = _parse_referenced_table(constraint_def)

            # Skip FKs that reference a table which exists only in prod (not in dev)
            if ref_table and ref_table not in dev_tables:
                print(f"  SKIP FK {constraint_name} on {table_name}: "
                      f"referenced table '{ref_table}' is prod-only")
                skipped_no_ref_table += 1
                continue

            # Attempt 1: full FK recreation (validates existing rows)
            try:
                cur.execute(
                    f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{constraint_name}" {constraint_def}'
                )
                dev_conn.commit()
                recreated += 1
                continue
            except Exception as e:
                dev_conn.rollback()
                err_str = str(e).split('\n')[0][:120]

            # Attempt 2: NOT VALID — creates the constraint without checking pre-existing rows.
            # This handles orphaned rows (e.g. veh_color_* → ev_model after data reload)
            # while still enforcing the constraint on new inserts/updates.
            not_valid_def = constraint_def.rstrip() + " NOT VALID"
            try:
                cur.execute(
                    f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{constraint_name}" {not_valid_def}'
                )
                dev_conn.commit()
                fk_not_valid += 1
                print(f"  NOT VALID: {constraint_name} on {table_name} "
                      f"(orphaned rows — constraint created without full validation)")
                continue
            except Exception as e2:
                dev_conn.rollback()
                err_str2 = str(e2).split('\n')[0][:120]
                fk_errors.append((table_name, constraint_name, err_str, err_str2))

    total_fk = len(fk_constraints) - skipped_no_ref_table
    print(f"  Recreated {recreated}/{total_fk} FK constraints fully valid")
    if fk_not_valid:
        print(f"  {fk_not_valid} FK constraints recreated as NOT VALID (orphaned rows present)")
    if skipped_no_ref_table:
        print(f"  {skipped_no_ref_table} FK constraints skipped (referenced table is prod-only)")
    if fk_errors:
        print(f"  {len(fk_errors)} FK constraints could not be recreated:")
        for tn, cn, e1, e2 in fk_errors[:10]:
            print(f"    - {cn} on {tn}: {e1}")

    print(f"\nStep 7: Resetting sequences...")
    with dev_conn.cursor() as cur:
        cur.execute("""
            SELECT c.relname AS seq_name, t.relname AS table_name, a.attname AS col_name
            FROM pg_class c
            JOIN pg_depend d ON d.objid = c.oid
            JOIN pg_class t ON d.refobjid = t.oid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
            WHERE c.relkind = 'S' AND t.relkind = 'r';
        """)
        seqs = cur.fetchall()
        for seq_name, table_name, col_name in seqs:
            try:
                cur.execute(f'SELECT COALESCE(MAX("{col_name}"), 0) + 1 FROM "{table_name}"')
                max_val = cur.fetchone()[0]
                cur.execute(f"SELECT setval('{seq_name}', {max_val}, false)")
                dev_conn.commit()
            except Exception:
                dev_conn.rollback()
    print(f"  Sequences reset")

    try:
        with dev_conn.cursor() as cur:
            cur.execute("SELECT refresh_wallet_materialized_views()")
            dev_conn.commit()
            print("Materialized views refreshed")
    except Exception:
        dev_conn.rollback()
        print("Could not refresh materialized views (function may not exist)")

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"COMPLETE: {total_rows} rows copied from {copied} tables in {elapsed:.1f}s")
    if prod_only:
        print(f"Skipped (prod-only):  {', '.join(prod_only)}")
    if errors:
        print(f"\n{len(errors)} tables had copy errors:")
        for t, e in errors[:20]:
            print(f"  - {t}: {e}")
        if len(errors) > 20:
            print(f"  ... and {len(errors)-20} more")

    prod_conn.close()
    dev_conn.close()
    print("\nDone!")


if __name__ == '__main__':
    main()
