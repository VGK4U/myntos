"""
DC_LIMBO_FIX: One-time migration to fix limbo leads.

PROBLEM:
Leads with handler_type='staff' but empty/NULL handler_id are invisible
to all dialer queues. The dialer queue requires handler_id == emp_code to
match leads to a staff member. These "limbo" leads appear in no one's queue.

FIX:
Convert all limbo leads to handler_type='unassigned' so they appear in the
secondary dialer pool (visible to all staff members in the same company).

Run this script if limbo leads are detected (they should not recur after
backend validation was added to create/update lead endpoints, but can also
be fixed via POST /api/v1/crm/leads/limbo/fix admin endpoint).
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/postgres')
engine = create_engine(DATABASE_URL)

def fix_limbo_leads(company_id=None):
    with engine.begin() as conn:
        # Count before
        where = "WHERE handler_type = 'staff' AND (handler_id IS NULL OR TRIM(handler_id) = '')"
        params = {}
        if company_id:
            where += " AND company_id = :company_id"
            params["company_id"] = company_id

        count_before = conn.execute(text(f"SELECT COUNT(*) FROM crm_leads {where}"), params).scalar()
        print(f"[DC_LIMBO_FIX] Found {count_before} limbo leads" + (f" in company {company_id}" if company_id else " across all companies"))

        if count_before == 0:
            print("[DC_LIMBO_FIX] No limbo leads found — nothing to fix.")
            return

        # Fix: convert to unassigned
        result = conn.execute(text(f"""
            UPDATE crm_leads
            SET handler_type = 'unassigned', handler_id = NULL
            {where}
            RETURNING id, company_id
        """), params)
        rows = result.fetchall()
        print(f"[DC_LIMBO_FIX] Fixed {len(rows)} limbo leads → handler_type='unassigned'")
        by_company = {}
        for r in rows:
            by_company[r[1]] = by_company.get(r[1], 0) + 1
        for cid, cnt in sorted(by_company.items()):
            print(f"  Company {cid}: {cnt} leads fixed")

    print("[DC_LIMBO_FIX] Done.")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Fix limbo leads (handler_type=staff, empty handler_id)")
    parser.add_argument('--company-id', type=int, default=None, help="Scope fix to specific company ID")
    args = parser.parse_args()
    fix_limbo_leads(company_id=args.company_id)
