"""
MYNT OS — V25 Canonical Location Ingestion Idempotency & Performance Indexes Migration
Phase 6 Step 2: Creates composite UNIQUE partial indexes for DB-level atomic idempotency
and composite indexes for out-of-order and live-tracking queries.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from app.core.database import SessionLocal
from sqlalchemy import text

def run_v25_migration():
    db = SessionLocal()
    try:
        print("[MIGRATION-V25] Applying location idempotency and performance indexes...")

        # 1. Uniqueness on staff_journey_track_points (journey_id, client_observation_id)
        db.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_journey_track_points_client_obs 
            ON staff_journey_track_points (journey_id, client_observation_id) 
            WHERE client_observation_id IS NOT NULL;
        """))

        # 2. Chronological index for journey out-of-order distance recalculation
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_journey_track_points_journey_time 
            ON staff_journey_track_points (journey_id, timestamp ASC, id ASC);
        """))

        # 3. Uniqueness on staff_realtime_locations (employee_id, client_observation_id)
        db.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_realtime_loc_emp_client_obs 
            ON staff_realtime_locations (employee_id, client_observation_id) 
            WHERE client_observation_id IS NOT NULL;
        """))

        # 4. Composite index on (employee_id, captured_at DESC) for sub-millisecond latest location lookups
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_staff_realtime_emp_captured 
            ON staff_realtime_locations (employee_id, captured_at DESC);
        """))

        # 5. Index on captured_at DESC for global temporal queries
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_staff_realtime_captured 
            ON staff_realtime_locations (captured_at DESC);
        """))

        # 6. Index on attendance_id for shift-scoped queries
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_staff_realtime_attendance 
            ON staff_realtime_locations (attendance_id);
        """))

        db.commit()
        print("[MIGRATION-V25] Successfully applied canonical location indexes and unique constraints.")
    except Exception as e:
        db.rollback()
        print(f"[MIGRATION-V25] Error applying indexes: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    run_v25_migration()
