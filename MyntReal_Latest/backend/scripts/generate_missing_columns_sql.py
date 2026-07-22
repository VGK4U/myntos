import sys
import os

# Add backend to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.schema import CreateColumn
from sqlalchemy.dialects import postgresql
from app.core.database import Base
import pkgutil
import importlib
import app.models

# Dynamically import all models
for _, module_name, _ in pkgutil.iter_modules(app.models.__path__):
    importlib.import_module(f"app.models.{module_name}")

missing_columns = [
    ("coupon_activation_tracker", "deadline_extended"),
    ("coupon_activation_tracker", "extension_count"),
    ("coupon_activation_tracker", "activation_completed_at"),
    ("coupon_activation_tracker", "red_coupon_triggered"),
    ("coupon_activation_tracker", "lockout_applied"),
    ("coupon_activation_tracker", "grace_period_granted"),
    ("coupon_activation_tracker", "grace_period_expires"),
    ("coupon_activation_tracker", "appeal_submitted"),
    ("coupon_activation_tracker", "appeal_approved"),
    ("coupon_activation_tracker", "admin_notes"),
    ("coupon_activation_tracker", "processed_by_id"),
    ("tds_payable", "business_date"),
    ("marketplace_spares", "stock_item_id"),
    ("ved_income", "base_amount"),
    ("ved_income", "ceiling_applied_amount"),
    ("ved_income", "excess_amount"),
    ("ved_income", "business_date"),
    ("ved_income", "calculation_timestamp"),
    ("ved_income", "ved_relationship_level"),
    ("ved_income", "income_percentage"),
    ("custom_roles", "can_view_users"),
    ("custom_roles", "can_edit_users"),
    ("custom_roles", "can_manage_finances"),
    ("custom_roles", "can_approve_kyc"),
    ("custom_roles", "can_manage_bonanza"),
    ("custom_roles", "can_system_control"),
    ("custom_roles", "created_by"),
    ("custom_roles", "updated_by"),
    ("invoice_line_items", "hsn_id"),
    ("allowance_scheme_selector", "selection_date"),
    ("allowance_scheme_selector", "effective_from_date"),
    ("allowance_scheme_selector", "scheme_change_count"),
    ("allowance_scheme_selector", "last_change_date"),
    ("allowance_scheme_selector", "qualified_for_standard"),
    ("allowance_scheme_selector", "qualified_for_car"),
    ("allowance_scheme_selector", "qualification_verified"),
    ("allowance_scheme_selector", "is_locked"),
    ("allowance_scheme_selector", "lock_expiry_date"),
    ("allowance_scheme_selector", "lock_reason"),
    ("allowance_scheme_selector", "admin_override"),
    ("allowance_scheme_selector", "override_reason"),
    ("allowance_scheme_selector", "override_by_id"),
    ("allowance_scheme_selector", "override_date"),
    ("allowance_scheme_selector", "deactivation_reason"),
    ("allowance_scheme_selector", "deactivated_by_id"),
    ("daily_cost_calculation", "business_date"),
    ("daily_cost_calculation", "direct_referral_total"),
    ("daily_cost_calculation", "matching_referral_total"),
    ("daily_cost_calculation", "ved_income_total"),
    ("daily_cost_calculation", "guru_dakshina_total"),
    ("daily_cost_calculation", "admin_deduction_total"),
    ("daily_cost_calculation", "tds_total"),
    ("daily_cost_calculation", "company_earnings_total"),
    ("daily_cost_calculation", "gross_payout"),
    ("daily_cost_calculation", "net_payout"),
    ("daily_cost_calculation", "total_users_paid"),
    ("daily_cost_calculation", "calculation_completed_at"),
    ("daily_cost_calculation", "created_at"),
    ("daily_cost_calculation", "notes"),
    ("ev_model", "variant_name"),
    ("ev_model", "specifications"),
    ("ev_model", "approval_status"),
    ("ev_model", "created_by_user_id"),
    ("ev_model", "approved_by_user_id"),
    ("ev_model", "approved_at"),
    ("ev_model", "rejection_reason"),
    ("ev_model", "created_at"),
    ("ev_model", "updated_at")
]

print("-- Migration script to add missing columns generated automatically")
print("BEGIN;")
for table_name, col_name in missing_columns:
    table = Base.metadata.tables.get(table_name)
    if table is None:
        print(f"-- WARNING: Table {table_name} not found in models!")
        continue
    
    col = table.columns.get(col_name)
    if col is None:
        print(f"-- WARNING: Column {col_name} not found in table {table_name}!")
        continue
    
    # Generate the column type string for Postgres
    col_type = col.type.compile(dialect=postgresql.dialect())
    
    # Handle constraints
    nullable = "NULL" if col.nullable else "NOT NULL"
    default = ""
    if col.server_default is not None:
        default = f" DEFAULT {col.server_default.arg}"
    
    print(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_name} {col_type}{default};")

print("COMMIT;")
