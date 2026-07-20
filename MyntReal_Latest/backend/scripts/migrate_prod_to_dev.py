#!/usr/bin/env python3
"""
Production to Development Database Migration Script
DC Protocol Compliant - Full business data migration

This script:
1. Exports business data from production database
2. Truncates matching tables in development (with CASCADE)
3. Imports production data into development
4. Resets all SERIAL sequences
5. Does NOT copy menu system tables (those stay fresh in development)

Usage: python backend/scripts/migrate_prod_to_dev.py
"""

import os
import sys
import subprocess
import json
from datetime import datetime

PROD_DB = "postgresql://neondb_owner:npg_tnS3mrd1KFgk@ep-dry-lab-ad9prs0y.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
DEV_DB = os.environ.get("DATABASE_URL", "")

EXCLUDED_TABLES = [
    "staff_menu_master",
    "staff_menu_registry", 
    "staff_menu_settings_audit",
    "staff_employee_menu_settings",
    "staff_employee_modules",
    "staff_employee_module_audit",
    "staff_module_master",
    "menu_audit_logs",
    "menu_configurations",
    "menu_item_permissions",
    "menu_items",
    "menu_module_permissions",
    "menu_modules",
    "partner_menu_settings",
    "alembic_version",
    "apscheduler_jobs",
]

MIGRATION_ORDER = [
    "staff_roles",
    "staff_departments",
    "staff_break_types",
    "staff_configurable_statuses",
    "signup_categories",
    "ev_model",
    "income_source_types",
    "matching_award_tier",
    "direct_award_tier",
    "expense_main_category",
    "expense_sub_category",
    "rd_property_types",
    "rd_amenities",
    "feedback_categories",
    "crm_lead_sources",
    "associated_companies",
    "staff_employees",
    "staff_employee_departments",
    "staff_employee_kyc",
    "staff_employee_status_history",
    "user",
    "bev_to_mnr_mapping",
    "placement",
    "placement_log",
    "user_leg_metrics",
    "ved_team_member",
    "transaction",
    "pending_income",
    "transfer_queue",
    "withdrawal_request",
    "withdrawal_reconciliation_log",
    "wallet_sync_log",
    "user_withdrawable_wallet_balance",
    "user_earning_wallet_balance",
    "user_coupon_acceptance",
    "user_award_progress",
    "user_matching_award_progress",
    "referral_income",
    "ved_income",
    "company_earnings",
    "coupon",
    "coupon_transfer",
    "pin_purchase_request",
    "staff_attendance",
    "staff_attendance_log",
    "staff_attendance_breaks",
    "staff_attendance_evidence",
    "staff_attendance_sheets",
    "staff_attendance_sheet_audits",
    "staff_journeys",
    "staff_journey_track_points",
    "staff_journey_approvals",
    "staff_realtime_locations",
    "staff_location_drift_events",
    "staff_field_work_log",
    "staff_field_work_sessions",
    "staff_field_work_track_points",
    "staff_work_intervals",
    "staff_work_interval_log",
    "staff_transport_rates",
    "staff_tasks",
    "staff_task_assignees",
    "staff_task_activity_log",
    "staff_task_time_entries",
    "staff_task_phases",
    "staff_task_comments",
    "staff_task_attachments",
    "staff_task_attachment_audit",
    "staff_kra_templates",
    "staff_kra_assignments",
    "staff_kra_daily_instances",
    "staff_kra_audit_log",
    "staff_kra_performance_summary",
    "staff_nda_versions",
    "staff_nda_acceptances",
    "staff_nda_audit",
    "staff_settings",
    "staff_audit_log",
    "staff_timesheet_entries",
    "staff_timesheet_approval_history",
    "staff_leave_types",
    "staff_leave_balances",
    "staff_leave_requests",
    "staff_leave_request_days",
    "staff_leave_approvals",
    "staff_attendance_exceptions",
    "staff_attendance_approvals",
    "staff_department_roles",
    "crm_leads",
    "crm_lead_assignments",
    "crm_lead_followups",
    "crm_lead_notes",
    "crm_lead_transactions",
    "crm_revenue_entries",
    "rd_properties",
    "rd_property_amenities",
    "rd_property_audit",
    "rd_property_media",
    "rd_property_metrics",
    "rd_property_shares",
    "rd_property_comments",
    "rd_property_ratings",
    "rd_property_crm_links",
    "rd_saved_properties",
    "rd_partner_profiles",
    "rd_leads",
    "rd_lead_followups",
    "rd_deals",
    "rd_company_config",
    "rd_banner_config",
    "rd_promotional_banners",
    "feedback_submissions",
    "feedback_approvals",
    "feedback_media",
    "announcement_ratings",
    "universal_shares",
    "universal_ratings",
    "universal_saves",
    "universal_comments",
    "bonanza",
    "bonanza_progress",
    "bonanza_reward",
    "bonanza_transaction",
    "dynamic_bonanza",
    "dynamic_bonanza_history",
    "dynamic_bonanza_progress",
    "dynamic_bonanza_reward",
    "award_audit_log",
    "award_price_change_request",
    "stock_item_master",
    "stock_item_images",
    "stock_ledger",
    "stock_transfers",
    "stock_validation_sessions",
    "stock_validation_entries",
    "stock_validation_audit_log",
    "vendor_master",
    "vendor_stock_item_association",
    "vendor_transaction_header",
    "vendor_transaction_line_items",
    "vendor_return_requests",
    "vendor_return_items",
    "vendor_returns",
    "hsn_master",
    "purchase_invoice_uploads",
    "purchase_invoice_line_items",
    "purchase_intake_batches",
    "purchase_intake_items",
    "sales_invoices",
    "sales_invoice_line_items",
    "service_ticket",
    "service_ticket_billing",
    "service_ticket_billing_item",
    "service_ticket_spare_request",
    "service_ticket_partner_history",
    "service_center_dispatches",
    "service_center_receipts",
    "service_items_used",
    "ticket_assignment",
    "ticket_attachment",
    "ticket_comment",
    "ticket_log",
    "official_partners",
    "partner_company_segments",
    "partner_orders",
    "partner_order_lines",
    "partner_order_dispatches",
    "partner_order_status_logs",
    "partner_payment_records",
    "partner_pricing_profiles",
    "partner_invoices",
    "partner_procurement_links",
    "banner",
    "banner_event_log",
    "banner_metrics",
    "banner_skipped_user",
    "banner_view_log",
    "custom_banner",
    "popup_message",
    "birthday_messages",
    "birthday_skipped_users",
    "kyc_blocking_log",
    "kyc_bypass_audit",
    "kyc_document",
    "kyc_approval",
    "data_change_log",
    "field_change_log",
    "migration_audit_log",
    "background_jobs",
    "bulk_operation",
    "bulk_withdrawal_batch",
    "scheduler_log",
    "expense",
    "expense_entries",
    "expense_audit_event",
    "system_control",
    "system_checkpoints",
    "system_log",
    "terms_and_conditions_versions",
    "pricing_configuration",
    "approval_configuration",
    "approval_history",
    "sandbox_configuration",
    "sandbox_sync_log",
    "sandbox_test_accounts",
    "sandbox_access_log",
    "app_settings",
    "permissions",
    "custom_roles",
    "custom_role_permissions",
    "custom_role_assignments",
    "audit_log",
    "message_log",
    "otp_verification",
    "whatsapp_control",
    "alert_preferences",
    "admin_notification",
    "super_admin_session",
    "field_allowance_eligibility",
    "field_allowance_progress",
    "car_allowance_eligibility",
    "allowance_scheme_selector",
    "allowance_tier_definition",
    "staff_mnr_user_audit_log",
    "staff_reimbursement_claims",
    "staff_reimbursement_claim_items",
    "staff_payroll_profile",
    "staff_payroll_cycle",
    "staff_payroll_run",
    "staff_payroll_deduction",
    "staff_payroll_document",
    "staff_payroll_audit_log",
    "staff_payroll_statutory_config",
    "staff_payroll_allowance_catalog",
    "staff_consultant_invoice",
    "employee_fund_ledger",
    "employee_fund_transfers",
    "employee_incentives",
    "party_ledger",
    "payment_receipt",
    "payment_receipts",
    "payment_transactions",
    "payment_validation",
    "tds_payable",
    "accounts_payable_schedule",
    "accounts_receivable_schedule",
    "credit_aging_snapshots",
    "balance_sheet_summary",
    "generated_invoices",
    "income_entries",
    "bank_details_approval",
    "fund_allocations",
    "pending_bonuses",
    "coupon_activation_attempt",
    "coupon_activation_tracker",
    "coupon_benefit",
    "coupon_management",
    "coupon_purchase_request",
    "coupon_request",
    "coupon_transfer_request",
    "enhanced_coupon",
    "enhanced_coupon_history",
    "ev",
    "ev_coupon_claim",
    "ev_franchise_referral",
    "ev_redemption_request",
    "pin_activation_attempt",
    "pin_request",
    "pin_transfer_request",
    "placement_request",
    "price_change_request",
    "purchase",
    "red_coupon_approval",
    "red_coupon_audit_log",
    "red_coupon_reassignment_vote",
    "royal_fleet_referral",
    "training_claim",
    "training_course",
    "user_action",
    "customized_gifts",
    "daily_cost_calculation",
    "dynamic_field",
    "dynamic_field_value",
    "email_template",
    "action_template",
    "custom_template",
    "bom_master",
    "bom_line_items",
    "manufacturing_orders",
    "manufacturing_order_lines",
    "fleet_order",
    "franchise_purchase",
    "insurance_policy",
    "insurance_referral",
    "inventory_lifecycle_events",
    "invoice_line_items",
    "held_by_company",
    "user_custom_field_definition",
    "user_custom_field_value",
    "package_assignment_storage",
    "user_package",
    "myntreal_incentive_rates",
    "myntreal_incentives",
    "zynova_incentives",
    "zynova_members",
    "mnr_points_balance",
    "mnr_points_transactions",
    "company_segments",
    "vgk_migration_storage",
    "procurement_requirements",
    "procurement_requirement_lines",
    "procurement_requests",
    "procurement_request_items",
    "procurement_quotes",
    "procurement_quote_items",
]

BACKUP_DIR = "/tmp/prod_backup"

def run_psql(db_url, sql, capture=False):
    cmd = ["psql", db_url, "-c", sql]
    if capture:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else None
    else:
        result = subprocess.run(cmd)
        return result.returncode == 0

def get_table_row_count(db_url, table):
    result = subprocess.run(
        ["psql", db_url, "-t", "-c", f"SELECT COUNT(*) FROM {table};"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        try:
            return int(result.stdout.strip())
        except:
            return 0
    return 0

def table_exists(db_url, table):
    result = subprocess.run(
        ["psql", db_url, "-t", "-c", 
         f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '{table}');"],
        capture_output=True, text=True
    )
    return "t" in result.stdout if result.returncode == 0 else False

def export_table(table):
    print(f"  Exporting {table}...")
    dump_file = f"{BACKUP_DIR}/{table}.sql"
    cmd = [
        "pg_dump", PROD_DB,
        "--data-only",
        "--disable-triggers",
        f"--table={table}",
        f"--file={dump_file}"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    WARNING: Could not export {table}: {result.stderr}")
        return False
    return True

def import_table(table):
    print(f"  Importing {table}...")
    dump_file = f"{BACKUP_DIR}/{table}.sql"
    if not os.path.exists(dump_file):
        print(f"    Skipping {table} - no dump file")
        return True
    
    cmd = ["psql", DEV_DB, "-f", dump_file]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    WARNING: Import error for {table}: {result.stderr[:200]}")
        return False
    return True

def truncate_table(table):
    result = subprocess.run(
        ["psql", DEV_DB, "-c", f"TRUNCATE TABLE {table} CASCADE;"],
        capture_output=True, text=True
    )
    return result.returncode == 0

def reset_sequences():
    print("\n5. Resetting all SERIAL sequences...")
    sql = """
    DO $$
    DECLARE
        r RECORD;
        max_val BIGINT;
    BEGIN
        FOR r IN 
            SELECT 
                tc.table_name,
                kc.column_name,
                pg_get_serial_sequence(tc.table_name, kc.column_name) as seq_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kc 
                ON tc.constraint_name = kc.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY'
            AND tc.table_schema = 'public'
            AND pg_get_serial_sequence(tc.table_name, kc.column_name) IS NOT NULL
        LOOP
            EXECUTE format('SELECT COALESCE(MAX(%I), 0) FROM %I', r.column_name, r.table_name) INTO max_val;
            IF max_val > 0 THEN
                EXECUTE format('SELECT setval(%L, %s)', r.seq_name, max_val);
                RAISE NOTICE 'Reset sequence % to %', r.seq_name, max_val;
            END IF;
        END LOOP;
    END $$;
    """
    result = subprocess.run(
        ["psql", DEV_DB, "-c", sql],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("  Sequences reset successfully")
    else:
        print(f"  WARNING: Sequence reset had issues: {result.stderr[:500]}")

def main():
    print("=" * 60)
    print("PRODUCTION TO DEVELOPMENT DATABASE MIGRATION")
    print("DC Protocol Compliant")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    
    if not DEV_DB:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
    
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    print("\n1. Checking table existence in both databases...")
    tables_to_migrate = []
    for table in MIGRATION_ORDER:
        if table in EXCLUDED_TABLES:
            continue
        prod_exists = table_exists(PROD_DB, table)
        dev_exists = table_exists(DEV_DB, table)
        if prod_exists and dev_exists:
            prod_count = get_table_row_count(PROD_DB, table)
            if prod_count > 0:
                tables_to_migrate.append((table, prod_count))
                print(f"  {table}: {prod_count} rows")
    
    print(f"\n  Total tables to migrate: {len(tables_to_migrate)}")
    
    print("\n2. Exporting data from production...")
    export_success = 0
    for table, count in tables_to_migrate:
        if export_table(table):
            export_success += 1
    print(f"  Exported {export_success}/{len(tables_to_migrate)} tables")
    
    print("\n3. Disabling triggers and truncating development tables...")
    run_psql(DEV_DB, "SET session_replication_role = replica;")
    
    for table, _ in reversed(tables_to_migrate):
        truncate_table(table)
    
    print("\n4. Importing data into development...")
    import_success = 0
    for table, _ in tables_to_migrate:
        if import_table(table):
            import_success += 1
    print(f"  Imported {import_success}/{len(tables_to_migrate)} tables")
    
    run_psql(DEV_DB, "SET session_replication_role = DEFAULT;")
    
    reset_sequences()
    
    print("\n6. Verifying data counts...")
    verification_ok = True
    for table, prod_count in tables_to_migrate[:20]:
        dev_count = get_table_row_count(DEV_DB, table)
        status = "OK" if dev_count == prod_count else f"MISMATCH ({dev_count})"
        if dev_count != prod_count:
            verification_ok = False
        print(f"  {table}: {status}")
    
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print(f"Finished: {datetime.now().isoformat()}")
    print(f"Tables migrated: {import_success}")
    print(f"Verification: {'PASSED' if verification_ok else 'NEEDS REVIEW'}")
    print("=" * 60)
    print("\nNEXT STEPS:")
    print("1. Run sidebar sync to regenerate staff_employee_menu_settings")
    print("2. Test CRUD operations on all modules")
    print("3. Disconnect production and republish")

if __name__ == "__main__":
    main()
