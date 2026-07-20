"""
Ved Program Database Cleanup Script
====================================

CRITICAL OPERATION: Keep ONLY position 3 as Ved Head

This script ensures the Ved Program follows the correct rule:
- ONLY the 3rd direct referral becomes Ved Head
- Positions 4, 5, 6+ should NOT be Ved members
- Remove Ved status from all positions except 3

Based on Ved Program Specification (replit.md):
- Rule 1: Ved Head Creation - ONLY the 3rd direct referral becomes Ved Head
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.user import User
from sqlalchemy import func
from datetime import datetime


def analyze_ved_cleanup(db, dry_run=True):
    """
    Analyze and optionally cleanup Ved members
    
    Args:
        db: Database session
        dry_run: If True, only show what would be changed (no actual changes)
    """
    print("=" * 80)
    print("VED PROGRAM CLEANUP: Keep ONLY Position 3 as Ved Head")
    print("=" * 80)
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
    else:
        print("\n⚠️  LIVE MODE - Changes will be applied to database!")
    
    print("\n" + "=" * 80)
    
    # Get all users who have direct referrals
    users_with_refs = db.query(User.id).filter(
        User.id.in_(
            db.query(User.referrer_id).filter(User.referrer_id.isnot(None)).distinct()
        )
    ).all()
    
    total_users_checked = 0
    users_with_cleanup = 0
    total_removed = 0
    users_kept_correct = 0
    
    changes_log = []
    
    for (user_id,) in users_with_refs:
        total_users_checked += 1
        
        # Get all direct referrals in registration order
        direct_refs = db.query(User).filter(
            User.referrer_id == user_id
        ).order_by(User.registration_date.asc(), User.id.asc()).all()
        
        if len(direct_refs) < 3:
            # No Ved Head possible
            continue
        
        # Position 3 (index 2) should be Ved Head
        correct_ved_head = direct_refs[2]
        
        # Find all users marked as Ved with this owner
        current_ved_members = db.query(User).filter(
            User.ved_owner_id == user_id,
            User.is_ved == True
        ).all()
        
        # Check if cleanup needed
        needs_cleanup = False
        positions_to_remove = []
        
        for i, ref in enumerate(direct_refs, 1):
            if i == 3:
                # Position 3 - should be Ved
                if not ref.is_ved or ref.ved_owner_id != user_id:
                    needs_cleanup = True
                    changes_log.append({
                        'user_id': user_id,
                        'action': 'SET_VED',
                        'affected_user': ref.id,
                        'position': i,
                        'message': f"Set position {i} as Ved Head (was not Ved)"
                    })
            else:
                # NOT position 3 - should NOT be Ved
                if ref.is_ved and ref.ved_owner_id == user_id:
                    needs_cleanup = True
                    positions_to_remove.append((i, ref.id, ref.name))
                    changes_log.append({
                        'user_id': user_id,
                        'action': 'REMOVE_VED',
                        'affected_user': ref.id,
                        'position': i,
                        'message': f"Remove Ved status from position {i} (should only be position 3)"
                    })
        
        if needs_cleanup:
            users_with_cleanup += 1
            
            if not dry_run:
                # Apply changes
                for i, ref in enumerate(direct_refs, 1):
                    if i == 3:
                        # Ensure position 3 is Ved
                        ref.is_ved = True
                        ref.ved_owner_id = user_id
                        users_kept_correct += 1
                    else:
                        # Remove Ved status from other positions
                        if ref.is_ved and ref.ved_owner_id == user_id:
                            ref.is_ved = False
                            ref.ved_owner_id = None
                            total_removed += 1
                
                db.commit()
    
    # Print summary
    print("\n" + "=" * 80)
    print("CLEANUP SUMMARY")
    print("=" * 80)
    print(f"\nTotal users checked: {total_users_checked}")
    print(f"Users needing cleanup: {users_with_cleanup}")
    
    if dry_run:
        print(f"\nChanges that WOULD be made:")
        print(f"  - Ved members to remove: {sum(1 for c in changes_log if c['action'] == 'REMOVE_VED')}")
        print(f"  - Ved members to set: {sum(1 for c in changes_log if c['action'] == 'SET_VED')}")
    else:
        print(f"\nChanges APPLIED:")
        print(f"  - Ved members removed: {total_removed}")
        print(f"  - Ved members kept/set: {users_kept_correct}")
    
    # Show detailed changes
    if changes_log:
        print(f"\n" + "=" * 80)
        print("DETAILED CHANGES LOG")
        print("=" * 80)
        
        # Group by user
        by_user = {}
        for change in changes_log:
            if change['user_id'] not in by_user:
                by_user[change['user_id']] = []
            by_user[change['user_id']].append(change)
        
        for user_id, user_changes in list(by_user.items())[:20]:  # Show first 20 users
            print(f"\nUser: {user_id}")
            for change in user_changes:
                action_symbol = "✅" if change['action'] == 'SET_VED' else "❌"
                print(f"  {action_symbol} Position {change['position']}: {change['affected_user']} - {change['message']}")
        
        if len(by_user) > 20:
            print(f"\n... and {len(by_user) - 20} more users")
    
    print("\n" + "=" * 80)
    
    return {
        'total_users_checked': total_users_checked,
        'users_with_cleanup': users_with_cleanup,
        'total_removed': total_removed,
        'users_kept_correct': users_kept_correct,
        'changes_log': changes_log
    }


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ved Program Cleanup: Keep ONLY position 3 as Ved Head')
    parser.add_argument('--execute', action='store_true', help='Execute cleanup (default is dry-run)')
    args = parser.parse_args()
    
    dry_run = not args.execute
    
    db = SessionLocal()
    
    try:
        result = analyze_ved_cleanup(db, dry_run=dry_run)
        
        if dry_run:
            print("\n" + "=" * 80)
            print("⚠️  THIS WAS A DRY RUN - No changes were made")
            print("=" * 80)
            print("\nTo execute the cleanup, run:")
            print("  python backend/scripts/ved_cleanup_position_3_only.py --execute")
        else:
            print("\n" + "=" * 80)
            print("✅ CLEANUP COMPLETED")
            print("=" * 80)
            print(f"\nRemoved Ved status from {result['total_removed']} users")
            print(f"Kept/set {result['users_kept_correct']} users as Ved Heads (position 3)")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
