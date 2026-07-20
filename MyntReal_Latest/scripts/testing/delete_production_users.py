#!/usr/bin/env python3
"""
Production User Deletion Script
Deletes 49 test users from PRODUCTION database safely
"""
import os
import sys

# Get production database URL from environment
prod_db_url = os.getenv('DATABASE_URL')  # This should be your PRODUCTION database URL

if not prod_db_url:
    print("❌ ERROR: DATABASE_URL not found!")
    print("Please set your PRODUCTION database URL in Replit Secrets as DATABASE_URL")
    sys.exit(1)

print(f"🔗 Connecting to Production Database...")
print(f"   URL: {prod_db_url[:30]}...")

# Import after we know we have the URL
try:
    from sqlalchemy import create_engine, text
    engine = create_engine(prod_db_url)
except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)

# Users to delete
USERS_TO_DELETE = [
    'BEV182335987', 'BEV182356628',
    'BEV1800897', 'BEV1800898', 'BEV1800899', 'BEV1800900', 'BEV1800901',
    'BEV1800902', 'BEV1800903', 'BEV1800904', 'BEV1800905', 'BEV1800906',
    'BEV1800907', 'BEV1800908', 'BEV1800909', 'BEV1800910', 'BEV1800911',
    'BEV1800912', 'BEV1800913', 'BEV1800914', 'BEV1800915', 'BEV1800916',
    'BEV1800917', 'BEV1800918', 'BEV1800919', 'BEV1800920', 'BEV1800921',
    'BEV1800922', 'BEV1800923', 'BEV1800924', 'BEV1800925', 'BEV1800926',
    'BEV1800927', 'BEV1800928', 'BEV1800929', 'BEV1800930', 'BEV1800931',
    'BEV1800932', 'BEV1800933', 'BEV1800934', 'BEV1800935', 'BEV1800936',
    'BEV1800937', 'BEV1800938', 'BEV1800939', 'BEV1800940', 'BEV1800941',
    'BEV1800942', 'BEV1800943'
]

user_ids_str = "'" + "','".join(USERS_TO_DELETE) + "'"

print("\n" + "="*70)
print(f"🗑️  PRODUCTION USER DELETION - {len(USERS_TO_DELETE)} Users")
print("="*70)

# Check if users exist first
print("\n📋 Checking if users exist in Production...")
with engine.connect() as conn:
    result = conn.execute(text(f'SELECT id, name FROM "user" WHERE id IN ({user_ids_str})'))
    existing_users = result.fetchall()
    
    if not existing_users:
        print("✅ Users already deleted! Nothing to do.")
        sys.exit(0)
    
    print(f"   Found {len(existing_users)} users to delete")
    for user in existing_users[:5]:
        print(f"   - {user[0]}: {user[1]}")
    if len(existing_users) > 5:
        print(f"   ... and {len(existing_users) - 5} more")

# Confirm deletion
print("\n⚠️  WARNING: This will DELETE these users from PRODUCTION!")
confirm = input("Type 'DELETE' to confirm: ")

if confirm != 'DELETE':
    print("❌ Deletion cancelled.")
    sys.exit(0)

print("\n🔄 Starting deletion process...")

# All tables with foreign keys to user table
# Based on the CSV you provided - ALL 196 constraints
dependent_tables = [
    ('user_leg_metrics', 'user_id'),
    ('leg_metrics_cache', 'root_user_id'),
    ('leg_metrics_cache', 'user_id'),
    ('alert_preferences', 'user_id'),
    ('alert_preferences', 'last_updated_by'),
    ('allowance_scheme_selector', 'user_id'),
    ('allowance_scheme_selector', 'created_by'),
    ('audit_log', 'actor_user_id'),
    ('audit_log', 'target_user_id'),
    ('bank_details_approval', 'user_id'),
    ('bank_details_approval', 'approved_by_finance_admin'),
    ('bank_details_approval', 'approved_by_super_admin'),
    ('bank_details_approval', 'rejected_by'),
    ('bonanza_progress', 'user_id'),
    ('bonanza_progress', 'processed_by'),
    ('bonanza_reward', 'user_id'),
    ('bonanza_reward', 'processed_by'),
    ('bonanza_transaction', 'user_id'),
    ('car_allowance_eligibility', 'user_id'),
    ('company_earnings', 'user_id'),
    ('coupon', 'owner_id'),
    ('coupon_activation_attempt', 'user_id'),
    ('coupon_activation_tracker', 'user_id'),
    ('coupon_activation_tracker', 'accounts_admin_approved_by'),
    ('coupon_activation_tracker', 'super_admin_approved_by'),
    ('coupon_activation_tracker', 'reassignment_target_user_id'),
    ('coupon_benefit', 'user_id'),
    ('coupon_benefit', 'applied_by'),
    ('coupon_benefit', 'verified_by'),
    ('coupon_purchase_request', 'user_id'),
    ('coupon_purchase_request', 'finance_validated_by'),
    ('coupon_purchase_request', 'rejected_by'),
    ('coupon_purchase_request', 'superadmin_approved_by'),
    ('custom_role_assignments', 'user_id'),
    ('custom_role_assignments', 'assigned_by_id'),
    ('custom_role_assignments', 'deactivated_by_id'),
    ('dynamic_bonanza_history', 'user_id'),
    ('dynamic_bonanza_history', 'processed_by'),
    ('dynamic_bonanza_progress', 'user_id'),
    ('dynamic_field_value', 'user_id'),
    ('enhanced_coupon', 'user_id'),
    ('ev_franchise_referral', 'user_id'),
    ('ev_redemption_request', 'user_id'),
    ('field_allowance_eligibility', 'user_id'),
    ('field_allowance_progress', 'user_id'),
    ('field_allowance_progress', 'price_created_by'),
    ('field_allowance_progress', 'price_last_updated_by'),
    ('fleet_order', 'contact_person_user_id'),
    ('fleet_order', 'primary_referrer_id'),
    ('fleet_order', 'secondary_referrer_id'),
    ('franchise_purchase', 'franchisee_user_id'),
    ('held_by_company', 'user_id'),
    ('insurance_policy', 'user_id'),
    ('insurance_policy', 'referred_by_user_id'),
    ('insurance_referral', 'user_id'),
    ('kyc_approval', 'user_id'),
    ('kyc_approval', 'reviewer_id'),
    ('kyc_blocking_log', 'user_id'),
    ('kyc_bypass_audit', 'target_user_id'),
    ('kyc_bypass_audit', 'super_admin_id'),
    ('kyc_document', 'owner_id'),
    ('kyc_document', 'reviewed_by_id'),
    ('message_log', 'user_id'),
    ('otp_verification', 'user_id'),
    ('package_assignment_storage', 'user_id'),
    ('placement', 'child_id'),
    ('transaction', 'user_id'),
    ('transaction', 'referred_user_id'),
]

print("\n🧹 Deleting from dependent tables...")
total_rows_deleted = 0

with engine.begin() as conn:  # This ensures everything is in one transaction
    # Delete from all dependent tables
    for table, column in dependent_tables:
        try:
            result = conn.execute(text(f'DELETE FROM "{table}" WHERE {column} IN ({user_ids_str})'))
            if result.rowcount > 0:
                print(f"   ✅ {table}.{column}: {result.rowcount} rows deleted")
                total_rows_deleted += result.rowcount
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' not in error_msg:
                print(f"   ⚠️  {table}.{column}: {error_msg[:60]}...")
    
    # Clear user self-references
    print("\n🔗 Clearing user self-references...")
    conn.execute(text(f'UPDATE "user" SET referrer_id = NULL WHERE referrer_id IN ({user_ids_str})'))
    conn.execute(text(f'UPDATE "user" SET position_id = NULL WHERE position_id IN ({user_ids_str})'))
    
    # Finally delete the users
    print("\n👤 Deleting users...")
    result = conn.execute(text(f'DELETE FROM "user" WHERE id IN ({user_ids_str})'))
    users_deleted = result.rowcount
    
    print(f"   ✅ {users_deleted} users deleted")
    total_rows_deleted += users_deleted

print("\n" + "="*70)
print(f"✅ SUCCESS! Total rows deleted: {total_rows_deleted}")
print("="*70)

# Verify deletion
print("\n🔍 Verifying deletion...")
with engine.connect() as conn:
    result = conn.execute(text(f'SELECT id FROM "user" WHERE id IN ({user_ids_str})'))
    remaining = result.fetchall()
    
    if remaining:
        print(f"❌ ERROR: {len(remaining)} users still remain!")
        for user in remaining:
            print(f"   - {user[0]}")
    else:
        print("✅ All users successfully deleted from Production!")
        print("\n🌐 Refresh app.bevseries.com/team to confirm!")

print("\n✨ Done!")
