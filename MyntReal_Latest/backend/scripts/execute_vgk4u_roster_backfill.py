#!/usr/bin/env python3
"""
VGK4U Roster Backfill Execution Script (Phase 3B)
=================================================
Safely updates the six approved cache columns on official_partners for the 286 VGK_TEAM partners:
  - vgk4u_current_designation
  - vgk4u_personal_prod_qualification
  - vgk4u_own_qualifying_files
  - vgk4u_active_team_count
  - is_apex_node
  - vgk4u_designation_updated_at

Non-negotiable invariants:
  - Single atomic database transaction with rollback on any failure.
  - Zero modifications to legacy columns (current_position, parent_partner_id, etc.).
  - Zero modifications to financial tables (vgk_cash_income_entries, vgk_solar_cibil_advances).
  - SHA-256 cryptographic verification before and after write.
  - Full before/after snapshot comparison.
"""

import os
import sys
import json
import hashlib
from datetime import datetime
from decimal import Decimal

# Dynamic project root resolution (NO hardcoded absolute paths)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.database import SessionLocal
from sqlalchemy import text
from app.services.vgk4u_career_service import (
    VGK4UCareerService,
    DESIGNATION_MEMBER,
    DESIGNATION_CHANNEL_PARTNER,
    DESIGNATION_MANAGER,
    DESIGNATION_GENERAL_MANAGER,
    DESIGNATION_REGIONAL_MANAGER,
    DESIGNATION_APEX_NODE,
    PROD_QUAL_NONE,
    PROD_QUAL_BASE,
    PROD_QUAL_GM,
    PROD_QUAL_RM,
)


def compute_financial_hashes(db):
    """Compute SHA-256 hashes of financial ledgers."""
    cash_rows = db.execute(text('''
        SELECT id, partner_id, source_lead_id, kind, level, commission_amount, net_payout, status, created_at 
        FROM vgk_cash_income_entries ORDER BY id
    ''')).fetchall()
    cash_str = ''.join(f'{r[0]}:{r[1]}:{r[2]}:{r[3]}:{r[4]}:{r[5]}:{r[6]}:{r[7]}:{r[8]}' for r in cash_rows)
    cash_hash = hashlib.sha256(cash_str.encode()).hexdigest()

    adv_rows = db.execute(text('''
        SELECT id, partner_id, lead_id, kind, level, advance_amount, status, created_at 
        FROM vgk_solar_cibil_advances ORDER BY id
    ''')).fetchall()
    adv_str = ''.join(f'{r[0]}:{r[1]}:{r[2]}:{r[3]}:{r[4]}:{r[5]}:{r[6]}:{r[7]}' for r in adv_rows)
    adv_hash = hashlib.sha256(adv_str.encode()).hexdigest()

    cash_totals = db.execute(text('''
        SELECT COUNT(*) as count, SUM(commission_amount) as gross, SUM(net_payout) as net
        FROM vgk_cash_income_entries
    ''')).fetchone()

    adv_totals = db.execute(text('''
        SELECT COUNT(*) as count, SUM(advance_amount) as total
        FROM vgk_solar_cibil_advances
    ''')).fetchone()

    return {
        'cash_hash': cash_hash,
        'cash_rows': len(cash_rows),
        'cash_gross': cash_totals.gross,
        'cash_net': cash_totals.net,
        'adv_hash': adv_hash,
        'adv_rows': len(adv_rows),
        'adv_total': adv_totals.total,
    }


def execute_roster_backfill():
    db = SessionLocal()
    print("=" * 80)
    print("VGK4U PHASE 3B: EXECUTING ROSTER CACHE BACKFILL")
    print("=" * 80)

    # 1. PRE-WRITE CHECKS & SNAPSHOT
    print("\n[STEP 1] Pre-Write Checks & Baseline Verification...")
    target_count = db.execute(text("SELECT COUNT(*) FROM official_partners WHERE category = 'VGK_TEAM'")).scalar()
    print(f"-> Official Partners (VGK_TEAM) Count: {target_count}")
    if target_count != 286:
        print(f"ABORT: Target row count {target_count} != 286!")
        db.close()
        sys.exit(1)

    # Capture BEFORE snapshot of all columns
    raw_before = db.execute(text("SELECT * FROM official_partners WHERE category = 'VGK_TEAM' ORDER BY id ASC")).fetchall()
    before_snapshot = {r.id: dict(r._mapping) for r in raw_before}
    print(f"-> Captured BEFORE snapshot for {len(before_snapshot)} partners.")

    # Capture baseline financial hashes
    baseline_fin = compute_financial_hashes(db)
    print(f"-> Baseline Cash Hash : {baseline_fin['cash_hash']} ({baseline_fin['cash_rows']} rows, gross ₹{baseline_fin['cash_gross']})")
    print(f"-> Baseline Adv Hash  : {baseline_fin['adv_hash']} ({baseline_fin['adv_rows']} rows, total ₹{baseline_fin['adv_total']})")

    # Verify baseline against established constants
    BASELINE_CASH_HASH = '4ab74b1bf3583ad22c291c974d3bb99ee8a4e6ff0860cb84d6713199e11aae35'
    BASELINE_ADV_HASH  = '5b1322cc5587bd5994e2b4f1947afab94d17019b05bcee753805a7163db37f8b'
    if baseline_fin['cash_hash'] != BASELINE_CASH_HASH:
        print(f"ABORT: Cash income hash mismatch before write! {baseline_fin['cash_hash']} != {BASELINE_CASH_HASH}")
        db.close()
        sys.exit(1)
    if baseline_fin['adv_hash'] != BASELINE_ADV_HASH:
        print(f"ABORT: Solar advance hash mismatch before write! {baseline_fin['adv_hash']} != {BASELINE_ADV_HASH}")
        db.close()
        sys.exit(1)
    print("-> Financial baseline verification PASSED.")

    # 2. EVALUATE SOURCE OF TRUTH VIA CAREER SERVICE
    print("\n[STEP 2] Calculating Authoritative Status via VGK4UCareerService...")
    status_map = VGK4UCareerService.get_bulk_partner_career_status(db)
    if len(status_map) != 286:
        print(f"ABORT: Status map count {len(status_map)} != 286!")
        db.close()
        sys.exit(1)

    career_counts = {}
    prod_counts = {}
    for pid, s in status_map.items():
        cd = s['career_designation']
        pq = s['personal_prod_qualification']
        career_counts[cd] = career_counts.get(cd, 0) + 1
        prod_counts[pq] = prod_counts.get(pq, 0) + 1

    print(f"-> Career Counts Calculated : {career_counts}")
    print(f"-> Prod Qual Calculated    : {prod_counts}")

    # Validate exact expected counts before starting write transaction
    EXPECTED_CAREER = {
        DESIGNATION_MEMBER: 273,
        DESIGNATION_CHANNEL_PARTNER: 8,
        DESIGNATION_MANAGER: 4,
        DESIGNATION_APEX_NODE: 1,
    }
    EXPECTED_PROD = {
        PROD_QUAL_NONE: 273,
        PROD_QUAL_BASE: 12,
        None: 1,
    }

    if career_counts != EXPECTED_CAREER:
        print(f"ABORT: Career counts mismatch! {career_counts} != {EXPECTED_CAREER}")
        db.close()
        sys.exit(1)
    if prod_counts != EXPECTED_PROD:
        print(f"ABORT: Prod counts mismatch! {prod_counts} != {EXPECTED_PROD}")
        db.close()
        sys.exit(1)
    print("-> Pre-execution count validation PASSED.")

    # 3. EXECUTE TRANSACTIONAL UPDATE
    print("\n[STEP 3] Executing Atomic Transactional UPDATE...")
    tx_start = datetime.now()
    updated_count = 0
    now_dt = datetime.now()

    try:
        # Explicit UPDATE parameter by parameter
        update_stmt = text("""
            UPDATE official_partners
            SET 
                vgk4u_current_designation          = :desig,
                vgk4u_personal_prod_qualification  = :qual,
                vgk4u_own_qualifying_files         = :files,
                vgk4u_active_team_count            = :legs,
                is_apex_node                       = :apex,
                vgk4u_designation_updated_at       = :updated_at
            WHERE id = :pid AND category = 'VGK_TEAM'
        """)

        for pid, s in status_map.items():
            res = db.execute(update_stmt, {
                'pid': pid,
                'desig': s['career_designation'],
                'qual': s['personal_prod_qualification'],
                'files': s['own_qualifying_files'],
                'legs': s['active_team_legs'],
                'apex': s['is_apex_node'],
                'updated_at': now_dt,
            })
            updated_count += res.rowcount

        print(f"-> Rows updated in session: {updated_count}")
        if updated_count != 286:
            raise RuntimeError(f"Expected 286 rows updated, but got {updated_count}! Rolling back.")

        # In-transaction validation
        in_tx_desig = db.execute(text("""
            SELECT vgk4u_current_designation, COUNT(*) 
            FROM official_partners WHERE category = 'VGK_TEAM' 
            GROUP BY vgk4u_current_designation
        """)).fetchall()
        in_tx_map = dict(in_tx_desig)
        print(f"-> In-Transaction Career Distribution: {in_tx_map}")

        if in_tx_map.get(DESIGNATION_MEMBER) != 273 or \
           in_tx_map.get(DESIGNATION_CHANNEL_PARTNER) != 8 or \
           in_tx_map.get(DESIGNATION_MANAGER) != 4 or \
           in_tx_map.get(DESIGNATION_APEX_NODE) != 1:
            raise RuntimeError(f"In-transaction career distribution mismatch: {in_tx_map}! Rolling back.")

        # Commit transaction
        db.commit()
        tx_end = datetime.now()
        print(f"-> TRANSACTION COMMITTED SUCCESSFULLY at {tx_end.isoformat()} (Duration: {(tx_end - tx_start).total_seconds():.3f}s)")

    except Exception as e:
        db.rollback()
        print(f"FATAL ERROR DURING UPDATE: {e}")
        print("TRANSACTION ROLLED BACK. ZERO DATA MUTATIONS PERSISTED.")
        db.close()
        sys.exit(1)

    # 4. POST-WRITE VALIDATION
    print("\n[STEP 4] Executing Comprehensive Post-Write Validation...")
    raw_after = db.execute(text("SELECT * FROM official_partners WHERE category = 'VGK_TEAM' ORDER BY id ASC")).fetchall()
    after_snapshot = {r.id: dict(r._mapping) for r in raw_after}

    # A. Exactly 286 VGK_TEAM partners exist
    print(f"A. Total VGK_TEAM partners: {len(after_snapshot)} (Expected: 286)")
    assert len(after_snapshot) == 286

    # B. Career distribution
    career_dist = dict(db.execute(text("""
        SELECT vgk4u_current_designation, COUNT(*) 
        FROM official_partners WHERE category = 'VGK_TEAM' 
        GROUP BY vgk4u_current_designation
    """)).fetchall())
    print(f"B. Career Distribution: {career_dist}")
    assert career_dist.get(DESIGNATION_MEMBER) == 273
    assert career_dist.get(DESIGNATION_CHANNEL_PARTNER) == 8
    assert career_dist.get(DESIGNATION_MANAGER) == 4
    assert career_dist.get(DESIGNATION_APEX_NODE) == 1
    assert career_dist.get(DESIGNATION_GENERAL_MANAGER, 0) == 0
    assert career_dist.get(DESIGNATION_REGIONAL_MANAGER, 0) == 0

    # C. Personal production distribution
    prod_dist = dict(db.execute(text("""
        SELECT vgk4u_personal_prod_qualification, COUNT(*) 
        FROM official_partners WHERE category = 'VGK_TEAM' 
        GROUP BY vgk4u_personal_prod_qualification
    """)).fetchall())
    print(f"C. Production Qualification Distribution: {prod_dist}")
    assert prod_dist.get(PROD_QUAL_NONE) == 273
    assert prod_dist.get(PROD_QUAL_BASE) == 12
    assert prod_dist.get(None) == 1
    assert prod_dist.get(PROD_QUAL_RM, 0) == 0
    assert prod_dist.get(PROD_QUAL_GM, 0) == 0

    # D. Exactly one is_apex_node = TRUE
    apex_count = db.execute(text("SELECT COUNT(*) FROM official_partners WHERE category = 'VGK_TEAM' AND is_apex_node = TRUE")).scalar()
    print(f"D. Apex Node count: {apex_count} (Expected: 1)")
    assert apex_count == 1

    # E. Partner 31 verification
    p31 = after_snapshot[31]
    print(f"E. Partner 31 ({p31['partner_code']}, {p31['partner_name']}): desig={p31['vgk4u_current_designation']}, qual={p31['vgk4u_personal_prod_qualification']}, legs={p31['vgk4u_active_team_count']}, is_apex={p31['is_apex_node']}")
    assert p31['vgk4u_current_designation'] == DESIGNATION_APEX_NODE
    assert p31['vgk4u_personal_prod_qualification'] is None
    assert p31['vgk4u_active_team_count'] == 7
    assert p31['is_apex_node'] is True

    # F. Partner 122 (Bandi Gangaraju) verification
    p122 = after_snapshot[122]
    print(f"F. Partner 122 ({p122['partner_code']}, {p122['partner_name']}): desig={p122['vgk4u_current_designation']}, qual={p122['vgk4u_personal_prod_qualification']}, files={p122['vgk4u_own_qualifying_files']}, legs={p122['vgk4u_active_team_count']}")
    assert p122['vgk4u_current_designation'] == DESIGNATION_CHANNEL_PARTNER
    assert p122['vgk4u_personal_prod_qualification'] == PROD_QUAL_BASE
    assert p122['vgk4u_own_qualifying_files'] == 4
    assert p122['vgk4u_active_team_count'] == 0

    # G. Partner 77 (Kalla Nookunaidu) verification
    p77 = after_snapshot[77]
    print(f"G. Partner 77 ({p77['partner_code']}, {p77['partner_name']}): desig={p77['vgk4u_current_designation']}, qual={p77['vgk4u_personal_prod_qualification']}, files={p77['vgk4u_own_qualifying_files']}, legs={p77['vgk4u_active_team_count']}")
    assert p77['vgk4u_current_designation'] == DESIGNATION_MANAGER
    assert p77['vgk4u_personal_prod_qualification'] == PROD_QUAL_BASE
    assert p77['vgk4u_own_qualifying_files'] == 1
    assert p77['vgk4u_active_team_count'] == 1

    # H. Partner 97 (Velagas Enterprises) verification
    p97 = after_snapshot[97]
    print(f"H. Partner 97 ({p97['partner_code']}, {p97['partner_name']}): desig={p97['vgk4u_current_designation']}, qual={p97['vgk4u_personal_prod_qualification']}, files={p97['vgk4u_own_qualifying_files']}, legs={p97['vgk4u_active_team_count']}")
    assert p97['vgk4u_current_designation'] == DESIGNATION_MANAGER
    assert p97['vgk4u_personal_prod_qualification'] == PROD_QUAL_BASE
    assert p97['vgk4u_own_qualifying_files'] == 1
    assert p97['vgk4u_active_team_count'] == 2

    # I. Partner 134 (Rohith Tangi) verification
    p134 = after_snapshot[134]
    print(f"I. Partner 134 ({p134['partner_code']}, {p134['partner_name']}): desig={p134['vgk4u_current_designation']}, qual={p134['vgk4u_personal_prod_qualification']}, files={p134['vgk4u_own_qualifying_files']}, legs={p134['vgk4u_active_team_count']}")
    assert p134['vgk4u_current_designation'] == DESIGNATION_MEMBER
    assert p134['vgk4u_personal_prod_qualification'] == PROD_QUAL_NONE
    assert p134['vgk4u_own_qualifying_files'] == 0
    assert p134['vgk4u_active_team_count'] == 1  # 1 active leg, but Member due to 0 personal files!

    # J. Partner 249 verification (Independent verification)
    p249 = after_snapshot[249]
    print(f"J. Partner 249 ({p249['partner_code']}, {p249['partner_name']}): desig={p249['vgk4u_current_designation']}, qual={p249['vgk4u_personal_prod_qualification']}, files={p249['vgk4u_own_qualifying_files']}, legs={p249['vgk4u_active_team_count']}")
    assert p249['vgk4u_current_designation'] == DESIGNATION_MEMBER
    assert p249['vgk4u_personal_prod_qualification'] == PROD_QUAL_NONE
    assert p249['vgk4u_own_qualifying_files'] == 0
    assert p249['vgk4u_active_team_count'] == 0

    # 5. VERIFY NO LEGACY FIELD CHANGED
    print("\n[STEP 5] Comparing Legacy Columns Before vs After...")
    ALLOWED_CHANGED_COLS = {
        'vgk4u_current_designation',
        'vgk4u_personal_prod_qualification',
        'vgk4u_own_qualifying_files',
        'vgk4u_active_team_count',
        'is_apex_node',
        'vgk4u_designation_updated_at'
    }

    legacy_mutation_found = False
    for pid in before_snapshot:
        b_dict = before_snapshot[pid]
        a_dict = after_snapshot[pid]
        for col, b_val in b_dict.items():
            if col not in ALLOWED_CHANGED_COLS:
                a_val = a_dict[col]
                if b_val != a_val:
                    print(f"CRITICAL ERROR: Legacy column {col} mutated on partner {pid}! Before: {b_val} != After: {a_val}")
                    legacy_mutation_found = True

    if legacy_mutation_found:
        print("ABORT: Legacy column mutations detected!")
        sys.exit(1)
    print("-> All legacy columns across all 286 partners are 100% BYTE/VALUE IDENTICAL. PASSED.")

    # 6. POST-WRITE FINANCIAL IMMUTABILITY VERIFICATION
    print("\n[STEP 6] Post-Write Financial Immutability Verification...")
    post_fin = compute_financial_hashes(db)
    print(f"-> Post-Write Cash Hash : {post_fin['cash_hash']} ({post_fin['cash_rows']} rows, gross ₹{post_fin['cash_gross']})")
    print(f"-> Post-Write Adv Hash  : {post_fin['adv_hash']} ({post_fin['adv_rows']} rows, total ₹{post_fin['adv_total']})")

    assert post_fin['cash_hash'] == BASELINE_CASH_HASH
    assert post_fin['adv_hash'] == BASELINE_ADV_HASH
    assert post_fin['cash_rows'] == baseline_fin['cash_rows']
    assert post_fin['adv_rows'] == baseline_fin['adv_rows']
    assert post_fin['cash_gross'] == baseline_fin['cash_gross']
    assert post_fin['cash_net'] == baseline_fin['cash_net']
    assert post_fin['adv_total'] == baseline_fin['adv_total']
    print("-> Post-write financial immutability verification PASSED (100% EXACT MATCH).")

    db.close()

    print("\n" + "=" * 80)
    print("PHASE 3B BACKFILL COMPLETE — 286 VGK_TEAM PARTNERS RECONCILED")
    print("=" * 80)


if __name__ == '__main__':
    execute_roster_backfill()
