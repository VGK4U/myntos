"""
Settlement and Commission Architecture Update Script
Date: 2026-09-16
Enforces:
1. Universal Category Commission Config (Solar: Base 5.0%, Senior 1.5%, Extended 1.0%, Core 0.5%, Support 1.5%, Brand 1.0%)
2. Career Designation Ladder (Member, Channel Partner, Senior, Extended, Core)
3. Legacy Category 6 Config synchronization
4. Global Settlement of in-flight pending and draft payments to PAID via SYSTEM_DIRECT
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text

def run_settlement(db_url: str):
    print(f"[SETTLE] Connecting to database: {db_url[:45]}...")
    engine = create_engine(db_url)
    with engine.begin() as conn:
        now_dt = datetime.now()
        
        # 1. Update vgk4u_category_commission_configs
        print("[SETTLE] 1. Updating vgk4u_category_commission_configs for Solar...")
        conn.execute(text("""
            UPDATE vgk4u_category_commission_configs
            SET producer_base_pct = 5.00,
                sponsor_override_pct = 1.50,
                manager_diff_pct = 1.00,
                gm_diff_pct = 0.50,
                rm_diff_pct = 0.00,
                support_journey_pct = 0.75,
                support_end_to_end_pct = 1.50,
                max_network_pool_pct = 9.50,
                is_active = TRUE,
                updated_at = :now
            WHERE category_slug = 'solar'
        """), {'now': now_dt})

        # 2. Update vgk4u_career_designation_configs by hierarchy_order
        print("[SETTLE] 2. Updating vgk4u_career_designation_configs...")
        career_updates = [
            (0, 'MEMBER', 'Member', 0, 0, 0.00, 0.00),
            (1, 'CHANNEL_PARTNER', 'Channel Partner', 1, 0, 5.00, 0.00),
            (2, 'SENIOR', 'Senior', 1, 1, 6.50, 1.50),
            (3, 'EXTENDED', 'Extended', 1, 5, 7.50, 1.00),
            (4, 'CORE', 'Core', 1, 10, 8.00, 0.50),
        ]
        for order, code, name, req_files, req_legs, self_pct, diff_pct in career_updates:
            # Check if row with this order exists
            row = conn.execute(text("SELECT id FROM vgk4u_career_designation_configs WHERE hierarchy_order = :order"), {'order': order}).fetchone()
            if row:
                conn.execute(text("""
                    UPDATE vgk4u_career_designation_configs
                    SET designation_code = :code,
                        designation_name = :name,
                        required_own_qualifying_files = :req_files,
                        required_active_team_members = :req_legs,
                        self_earning_pct = :self_pct,
                        team_differential_pct = :diff_pct,
                        is_active = TRUE,
                        updated_at = :now
                    WHERE hierarchy_order = :order
                """), {
                    'order': order, 'code': code, 'name': name,
                    'req_files': req_files, 'req_legs': req_legs,
                    'self_pct': self_pct, 'diff_pct': diff_pct,
                    'now': now_dt
                })
            else:
                conn.execute(text("""
                    INSERT INTO vgk4u_career_designation_configs
                        (hierarchy_order, designation_code, designation_name, required_own_qualifying_files,
                         required_active_team_members, self_earning_pct, team_differential_pct, is_active, updated_at)
                    VALUES
                        (:order, :code, :name, :req_files, :req_legs, :self_pct, :diff_pct, TRUE, :now)
                """), {
                    'order': order, 'code': code, 'name': name,
                    'req_files': req_files, 'req_legs': req_legs,
                    'self_pct': self_pct, 'diff_pct': diff_pct,
                    'now': now_dt
                })

        # 3. Update legacy vgk_team_commission_config for Category 6 (Solar)
        print("[SETTLE] 3. Updating legacy vgk_team_commission_config...")
        conn.execute(text("""
            UPDATE vgk_team_commission_config
            SET level1_pct = 5.00,
                level2_pct = 1.50,
                level3_pct = 1.00,
                level4_core_pct = 0.50,
                level4_pct = 1.50,
                updated_at = :now
            WHERE category_id = 6
        """), {'now': now_dt})

        # 4. Settle in-flight cash income entries
        print("[SETTLE] 4. Settling in-flight vgk_cash_income_entries to PAID...")
        vci_res = conn.execute(text("""
            UPDATE vgk_cash_income_entries
            SET status = 'PAID',
                payment_mode = 'BANK',
                payment_utr = 'SETTLE-20260916',
                paid_at = :now,
                released_at = COALESCE(released_at, :now),
                ledger_posted = TRUE,
                updated_at = :now
            WHERE status IN ('DRAFT', 'PENDING', 'STAGE1_APPROVED', 'STAGE2_APPROVED', 'VERIFIED')
        """), {'now': now_dt})
        print(f"[SETTLE] -> Settled {vci_res.rowcount} entries in vgk_cash_income_entries.")

        # 5. Settle in-flight solar cibil advances
        print("[SETTLE] 5. Settling in-flight vgk_solar_cibil_advances to RELEASED...")
        vsca_res = conn.execute(text("""
            UPDATE vgk_solar_cibil_advances
            SET status = 'RELEASED',
                released_at = COALESCE(released_at, :now),
                updated_at = :now
            WHERE status IN ('DRAFT', 'PENDING', 'APPROVED', 'VERIFIED')
        """), {'now': now_dt})
        print(f"[SETTLE] -> Settled {vsca_res.rowcount} advances in vgk_solar_cibil_advances.")

        # 6. Settle in-flight bonanza progress claims
        print("[SETTLE] 6. Settling in-flight bonanza_progress to Paid...")
        bp_res = conn.execute(text("""
            UPDATE bonanza_progress
            SET processed_status = 'Paid',
                processed_date = CURRENT_DATE,
                updated_at = :now
            WHERE processed_status IN ('Pending', 'Draft')
        """), {'now': now_dt})
        print(f"[SETTLE] -> Settled {bp_res.rowcount} claims in bonanza_progress.")

    print("[SETTLE] ✅ Migration and settlement transaction committed successfully!")

if __name__ == '__main__':
    db_uri = os.environ.get('DATABASE_URL')
    if not db_uri:
        print("ERROR: DATABASE_URL not set!")
        sys.exit(1)
    run_settlement(db_uri)
