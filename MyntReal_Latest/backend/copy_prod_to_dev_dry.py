"""
Dry-run companion for copy_prod_to_dev.py
Prints what would be synced without touching the dev database.
"""
import os
import sys
import psycopg2
from copy_prod_to_dev import PROD_DB_URL, SKIP_TABLES, get_all_tables

DEV_DB_URL = os.environ.get("DATABASE_URL")

if not DEV_DB_URL:
    print("ERROR: DATABASE_URL is not set.")
    sys.exit(1)

SKIP = set(SKIP_TABLES)

prod_conn = psycopg2.connect(PROD_DB_URL)
dev_conn  = psycopg2.connect(DEV_DB_URL)

prod_tables = set(get_all_tables(prod_conn))
dev_tables  = set(get_all_tables(dev_conn))
common      = sorted((prod_tables & dev_tables) - SKIP)
prod_only   = sorted(prod_tables - dev_tables - SKIP)
dev_only    = sorted(dev_tables - prod_tables - SKIP)

print(f"\nWould copy {len(common)} tables.\n")

if prod_only:
    print(f"Prod-only (would skip — not in dev): {', '.join(prod_only)}\n")
if dev_only:
    print(f"Dev-only  (not touched):              {', '.join(dev_only)}\n")

total_rows = 0
for t in common:
    with prod_conn.cursor() as c:
        c.execute(f'SELECT COUNT(*) FROM "{t}"')
        rows = c.fetchone()[0]
    total_rows += rows
    if rows > 0:
        print(f"  {t}: {rows} rows")

print(f"\nTotal rows to copy: {total_rows}")

prod_conn.close()
dev_conn.close()
