"""
DC-PL-DATAFIX-001: Party Ledger Contamination Repair
=====================================================
Idempotent data correction script for party_ledger.
Fixes two classes of errors:

Class A — party_name / party_id MISMATCH for VENDOR type:
  party_ledger rows where party_id points to vendor_master record X
  but party_name stores vendor Y's name. The canonical truth is
  vendor_master.vendor_name for the given party_id.

Class B — party_id = 0 for VENDOR entries that have an exact
  vendor_master.vendor_name match AND the vendor is applicable
  to that company. Setting party_id links the entry to the master
  record so party_id-based balance queries work correctly.

After each correction group the running_balance chain for every
affected (company_id, party_type, party_name, party_id) combination
is recomputed in chronological order (ORDER BY id ASC).

Safe to run repeatedly — each correction is guarded by a check.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from decimal import Decimal
from sqlalchemy import text
from app.core.database import SessionLocal


def _recompute_chain(db, company_id, party_type, party_name, party_id):
    """Recompute running_balance for a (company, type, name, id) chain, oldest→newest."""
    rows = db.execute(text("""
        SELECT id, entry_type, debit_amount, credit_amount
        FROM party_ledger
        WHERE company_id = :co AND party_type = :pt
          AND party_name = :pn AND party_id = :pid
        ORDER BY id ASC
    """), dict(co=company_id, pt=party_type, pn=party_name, pid=party_id)).fetchall()

    bal = Decimal('0')
    for r in rows:
        dr = Decimal(str(r[2] or 0))
        cr = Decimal(str(r[3] or 0))
        bal = bal + dr - cr
        db.execute(text(
            "UPDATE party_ledger SET running_balance = :b WHERE id = :id"
        ), dict(b=bal, id=r[0]))
    return len(rows), bal


def run(db):
    print("[DC-PL-DATAFIX-001] Starting party_ledger contamination repair...")
    total_fixed = 0

    # ──────────────────────────────────────────────────────────────────────
    # CLASS A: party_id > 0 but party_name ≠ vendor_master.vendor_name
    # Truth: vendor_master.vendor_name is authoritative for the given id.
    # Action: update party_ledger.party_name to match vendor_master.
    # ──────────────────────────────────────────────────────────────────────
    print("\n[A] Scanning for name/ID mismatches (VENDOR, party_id > 0)...")
    mismatches = db.execute(text("""
        SELECT pl.id, pl.company_id, pl.party_id,
               pl.party_name  AS bad_name,
               vm.vendor_name AS good_name
        FROM party_ledger pl
        JOIN vendor_master vm ON vm.id = pl.party_id
        WHERE pl.party_type = 'VENDOR'
          AND pl.party_id > 0
          AND UPPER(TRIM(pl.party_name)) != UPPER(TRIM(vm.vendor_name))
        ORDER BY pl.id
    """)).fetchall()

    # Collect affected chains BEFORE renaming so we can recompute both
    # the old (bad) chain and the new (good) chain.
    affected_chains_a = set()
    for r in mismatches:
        affected_chains_a.add((r[1], 'VENDOR', r[3], r[2]))   # old: bad_name, pid
        affected_chains_a.add((r[1], 'VENDOR', r[4], r[2]))   # new: good_name, pid

    if not mismatches:
        print("  None found.")
    for r in mismatches:
        db.execute(text(
            "UPDATE party_ledger SET party_name = :good WHERE id = :id"
        ), dict(good=r[4], id=r[0]))
        print(f"  PL#{r[0]} co={r[1]} pid={r[2]}: '{r[3]}' → '{r[4]}'")
        total_fixed += 1

    # ──────────────────────────────────────────────────────────────────────
    # CLASS B: party_id = 0 where an exact vendor_master match exists
    # AND the vendor is applicable to that company.
    # Action: set party_id = vm.id
    # ──────────────────────────────────────────────────────────────────────
    print("\n[B] Scanning for pid=0 VENDOR entries with exact master match...")
    zeros = db.execute(text("""
        SELECT pl.id, pl.company_id, pl.party_name, vm.id AS vm_id
        FROM party_ledger pl
        JOIN vendor_master vm
          ON UPPER(TRIM(vm.vendor_name)) = UPPER(TRIM(pl.party_name))
          AND vm.applicable_companies @> to_jsonb(pl.company_id)
        WHERE pl.party_type = 'VENDOR'
          AND (pl.party_id IS NULL OR pl.party_id = 0)
        ORDER BY pl.id
    """)).fetchall()

    affected_chains_b = set()
    for r in zeros:
        affected_chains_b.add((r[1], 'VENDOR', r[2].upper().strip(), 0))    # old chain
        affected_chains_b.add((r[1], 'VENDOR', r[2].upper().strip(), r[3])) # new chain

    if not zeros:
        print("  None found.")
    for r in zeros:
        db.execute(text(
            "UPDATE party_ledger SET party_id = :pid WHERE id = :id"
        ), dict(pid=r[3], id=r[0]))
        print(f"  PL#{r[0]} co={r[1]} '{r[2]}': pid=0 → pid={r[3]}")
        total_fixed += 1

    db.flush()

    # ──────────────────────────────────────────────────────────────────────
    # RECOMPUTE running_balance for all affected chains
    # We must normalise party_name to UPPER for the chain key lookup
    # because _add_party normalises to UPPER before storing.
    # ──────────────────────────────────────────────────────────────────────
    print("\n[C] Recomputing running_balance chains...")
    # After updates, fetch fresh distinct chains for affected rows
    all_affected = affected_chains_a | affected_chains_b
    recomputed = set()
    for (co, pt, pn, pid) in all_affected:
        # Normalise name (stored as UPPER in party_ledger)
        pn_up = pn.upper().strip() if pn else pn
        chain_key = (co, pt, pn_up, pid)
        if chain_key in recomputed:
            continue
        cnt, final_bal = _recompute_chain(db, co, pt, pn_up, pid)
        if cnt:
            print(f"  Chain co={co} {pt} '{pn_up}' pid={pid}: {cnt} rows, closing_bal={final_bal}")
        recomputed.add(chain_key)

    # Also recompute chains that now have good_name / new pid from the fixes
    # (they were already added to all_affected above)

    db.commit()
    print(f"\n[DC-PL-DATAFIX-001] Done. {total_fixed} rows corrected, "
          f"{len(recomputed)} balance chains recomputed.")
    return total_fixed


if __name__ == '__main__':
    db = SessionLocal()
    try:
        run(db)
    except Exception as e:
        db.rollback()
        print(f"[DC-PL-DATAFIX-001] ERROR: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()
