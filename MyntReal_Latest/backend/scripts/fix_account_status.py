"""
Fix Account Status - Normalize all account_status values to 'Active' or 'Inactive'
Run this to fix the status mismatch issue
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import get_db, engine
from app.models.user import User

def normalize_status(status_str):
    """Normalize status to exactly 'Active' or 'Inactive'"""
    if not status_str:
        return "Inactive"
    
    status = str(status_str).upper().strip()
    
    # Map common variations to 'Active'
    if status in ["ACTIVE", "ACTIVATED", "YES", "Y", "1", "TRUE"]:
        return "Active"
    
    # Map common variations to 'Inactive'
    if status in ["INACTIVE", "DEACTIVATED", "NO", "N", "0", "FALSE", "BLOCKED", "SUSPENDED"]:
        return "Inactive"
    
    # Default: if it contains "ACTIVE", treat as Active, else Inactive
    if "ACTIVE" in status:
        return "Active"
    
    return "Inactive"

def fix_account_status():
    """Fix all user account statuses"""
    print("=" * 80)
    print("FIXING ACCOUNT STATUS - SYNC WITH COUPON STATUS")
    print("=" * 80)
    
    db = next(get_db())
    
    try:
        # Get all users
        users = db.query(User).all()
        total_users = len(users)
        
        print(f"\n📊 Found {total_users} users to check")
        
        fixed_count = 0
        status_changes = {}
        
        for user in users:
            old_status = user.account_status
            
            # RULE: If coupon is Activated, account MUST be Active
            if hasattr(user, 'coupon_status') and user.coupon_status == 'Activated':
                new_status = 'Active'
            else:
                new_status = normalize_status(old_status)
            
            if old_status != new_status:
                # Track changes
                change_key = f"{old_status} → {new_status}"
                if change_key not in status_changes:
                    status_changes[change_key] = []
                status_changes[change_key].append(user.id)
                
                # Update status
                user.account_status = new_status
                fixed_count += 1
        
        # Commit changes
        db.commit()
        
        print(f"\n✅ Status Fix Complete!")
        print(f"   Total users checked: {total_users}")
        print(f"   Users fixed: {fixed_count}")
        print(f"   No changes needed: {total_users - fixed_count}")
        
        if status_changes:
            print(f"\n📋 Status Changes Applied:")
            for change, user_ids in status_changes.items():
                print(f"   {change}: {len(user_ids)} users")
                if len(user_ids) <= 5:
                    print(f"      Example IDs: {', '.join(map(str, user_ids))}")
                else:
                    print(f"      Example IDs: {', '.join(map(str, user_ids[:5]))}...")
        
        # Show stats
        active_users = db.query(User).filter(User.account_status == 'Active').count()
        inactive_users = db.query(User).filter(User.account_status == 'Inactive').count()
        activated_coupons = db.query(User).filter(User.coupon_status == 'Activated').count()
        
        print(f"\n📊 Final Statistics:")
        print(f"   Total Users: {total_users}")
        print(f"   Active Accounts: {active_users}")
        print(f"   Inactive Accounts: {inactive_users}")
        print(f"   Activated Coupons: {activated_coupons}")
        
        print("\n" + "=" * 80)
        print("✅ ALL STATUSES SYNCHRONIZED!")
        print("   RULE: Activated Coupon = Active Account")
        print("=" * 80)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    fix_account_status()
