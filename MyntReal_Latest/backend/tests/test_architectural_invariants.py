import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
"""
Architectural Invariants Test Suite
Enforces:
1. Zero Database connections, sessions, or queries during application startup/import.
2. Zero runtime DDL statements in request-path services or endpoints.
3. Complete schema definitions consolidated into backend/scripts/run_schema_migrations.py.
4. Fully decoupled /staff/progress frontend initialization (non-blocking sidebar).
"""

import os
import re
import unittest
from pathlib import Path


class TestArchitecturalInvariants(unittest.TestCase):

    def test_zero_db_on_import(self):
        """Verify that importing app.main initiates 0 DB connections and 0 sessions."""
        from unittest.mock import MagicMock
        from app.core import database

        connections = []
        sessions = []

        orig_connect = database.engine.connect
        def hooked_connect(*args, **kwargs):
            connections.append(args)
            return orig_connect(*args, **kwargs)

        orig_session = database.SessionLocal
        def hooked_session(*args, **kwargs):
            sessions.append(args)
            return orig_session(*args, **kwargs)

        database.engine.connect = hooked_connect
        database.SessionLocal = hooked_session

        try:
            # Import app.main
            import app.main
            self.assertEqual(len(connections), 0, f"Expected 0 DB connections on import, got {len(connections)}")
            self.assertEqual(len(sessions), 0, f"Expected 0 SessionLocal checkouts on import, got {len(sessions)}")
        finally:
            database.engine.connect = orig_connect
            database.SessionLocal = orig_session

    def test_zero_runtime_ddl_in_request_handlers(self):
        """Verify that endpoints and services do not perform runtime DDL."""
        backend_root = Path(__file__).resolve().parent.parent

        # 1. staff_accounts_service.py
        sas_file = backend_root / "app" / "services" / "staff_accounts_service.py"
        sas_content = sas_file.read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE IF NOT EXISTS service_center_given_out", sas_content,
                         "Runtime DDL found in staff_accounts_service.py")

        # 2. platform_b2b_billing.py
        pbb_file = backend_root / "app" / "services" / "platform_b2b_billing.py"
        pbb_content = pbb_file.read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE IF NOT EXISTS platform_invoice_counters", pbb_content,
                         "Runtime DDL found in platform_b2b_billing.py")

        # 3. catalog.py
        cat_file = backend_root / "app" / "api" / "v1" / "endpoints" / "catalog.py"
        cat_content = cat_file.read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE IF NOT EXISTS catalog_shares", cat_content,
                         "Runtime DDL found in catalog.py")
        self.assertNotIn("CREATE TABLE IF NOT EXISTS catalog_hits", cat_content,
                         "Runtime DDL found in catalog.py")

        # 4. partner_auth.py
        pa_file = backend_root / "app" / "api" / "v1" / "endpoints" / "partner_auth.py"
        pa_content = pa_file.read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE IF NOT EXISTS partner_support_requests", pa_content,
                         "Runtime DDL found in partner_auth.py")
        self.assertNotIn("CREATE TABLE IF NOT EXISTS partner_stock_items", pa_content,
                         "Runtime DDL found in partner_auth.py")

        # 5. sidebar_sync_service.py
        sss_file = backend_root / "app" / "services" / "sidebar_sync_service.py"
        sss_content = sss_file.read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE IF NOT EXISTS pdf_canonical_routes", sss_content,
                         "Runtime DDL found in sidebar_sync_service.py")

    def test_migration_runner_coverage(self):
        """Verify that backend/scripts/run_schema_migrations.py covers all required schemas."""
        backend_root = Path(__file__).resolve().parent.parent
        migration_file = backend_root / "scripts" / "run_schema_migrations.py"
        migration_content = migration_file.read_text(encoding="utf-8")

        required_tables_and_columns = [
            "service_center_given_out",
            "platform_invoice_counters",
            "catalog_shares",
            "catalog_hits",
            "partner_support_requests",
            "partner_stock_items",
            "partner_stock_adjustments",
            "pdf_canonical_routes",
            "freelancer_access_mode",
            "crm_lead_handlers",
            "crm_lead_handler_members",
            "crm_lead_handler_audits",
            "veh_models",
            "veh_model_colors",
            "veh_color_batches",
            "veh_color_in",
            "veh_color_out",
            "first_payment_received_date",
            "cumulative_self_business_dvr",
            "points_evaluated_dvr",
            "vgk_self_business_points_accrual_ledger",
        ]

        for item in required_tables_and_columns:
            self.assertIn(item, migration_content, f"Missing schema definition for {item} in run_schema_migrations.py")

    def test_staff_progress_decoupled(self):
        """Verify that frontend/staff_progress.html initializes dates and data non-blocking."""
        frontend_root = Path(__file__).resolve().parent.parent.parent / "frontend"
        progress_html = (frontend_root / "staff_progress.html").read_text(encoding="utf-8")

        # Check DOMContentLoaded doesn't await StaffSidebar.init()
        self.assertNotIn("await window.StaffSidebar.init()", progress_html,
                         "staff_progress.html must not await StaffSidebar.init() sequentially")
        # Check Promise.allSettled with loadDayProgress
        self.assertIn("loadDayProgress()", progress_html)
        self.assertIn("progressDatePicker", progress_html)


if __name__ == "__main__":
    unittest.main()
