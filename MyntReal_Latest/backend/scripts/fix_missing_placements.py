"""
Fix Missing Placement Records for Migrated Users

This script creates placement records for all users who have position_id 
and position data but are missing entries in the placement table.

Uses:
- position_id as parent_id
- position (LEFT/RIGHT) as side
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

def fix_missing_placements():
    """Create placement records for users missing them"""
    
    print("\n" + "="*60)
    print("FIXING MISSING PLACEMENT RECORDS")
    print("="*60 + "\n")
    
    # Step 1: Find all users with position_id but no placement
    query = text("""
        SELECT 
            u.id,
            u.name,
            u.referrer_id,
            u.position_id,
            u.position,
            u.registration_date
        FROM "user" u
        LEFT JOIN placement p ON u.id = p.child_id
        WHERE u.position_id IS NOT NULL 
          AND u.position_id != ''
          AND p.child_id IS NULL
          AND u.user_type = 'Member'
        ORDER BY u.registration_date
    """)
    
    users_without_placement = db.execute(query).fetchall()
    total_count = len(users_without_placement)
    
    print(f"Found {total_count} users without placement records\n")
    
    if total_count == 0:
        print("No users need fixing. All placements are complete!")
        return
    
    # Step 2: Create placement records
    created_count = 0
    error_count = 0
    errors = []
    
    for user in users_without_placement:
        user_id = user.id
        name = user.name
        position_id = user.position_id  # This is the parent
        position = user.position  # This is the side (LEFT/RIGHT)
        reg_date = user.registration_date
        
        # Validate data
        if not position_id or not position:
            error_count += 1
            errors.append(f"  ❌ {user_id} ({name}): Missing position_id or position")
            continue
        
        # Normalize side to lowercase
        side = position.lower() if position else None
        if side not in ['left', 'right']:
            error_count += 1
            errors.append(f"  ❌ {user_id} ({name}): Invalid position '{position}'")
            continue
        
        try:
            # Insert placement record
            insert_query = text("""
                INSERT INTO placement (parent_id, child_id, side, placed_at, status)
                VALUES (:parent_id, :child_id, :side, :placed_at, :status)
            """)
            
            db.execute(insert_query, {
                'parent_id': position_id,
                'child_id': user_id,
                'side': side,
                'placed_at': reg_date or datetime.now(),
                'status': 'active'
            })
            
            created_count += 1
            
            if created_count % 100 == 0:
                print(f"  ✅ Created {created_count} placement records...")
                db.commit()  # Commit in batches
        
        except Exception as e:
            error_count += 1
            errors.append(f"  ❌ {user_id} ({name}): {str(e)}")
            continue
    
    # Final commit
    db.commit()
    
    # Step 3: Summary Report
    print("\n" + "="*60)
    print("PLACEMENT FIX SUMMARY")
    print("="*60)
    print(f"✅ Successfully created: {created_count} placement records")
    print(f"❌ Errors encountered: {error_count}")
    print(f"📊 Total processed: {total_count}")
    print("="*60 + "\n")
    
    if errors:
        print("ERROR DETAILS:")
        for error in errors[:10]:  # Show first 10 errors
            print(error)
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
    
    # Step 4: Verification
    print("\nVERIFICATION:")
    verify_query = text("""
        SELECT COUNT(*) as remaining
        FROM "user" u
        LEFT JOIN placement p ON u.id = p.child_id
        WHERE u.position_id IS NOT NULL 
          AND u.position_id != ''
          AND p.child_id IS NULL
          AND u.user_type = 'Member'
    """)
    
    remaining = db.execute(verify_query).fetchone().remaining
    print(f"Users still without placement: {remaining}")
    
    if remaining == 0:
        print("✅ ALL USERS NOW HAVE PLACEMENT RECORDS!")
    else:
        print(f"⚠️  {remaining} users still need manual review")
    
    # Step 5: Test MNR1800143
    print("\n" + "="*60)
    print("TESTING MNR1800143")
    print("="*60)
    
    test_query = text("""
        SELECT 
            u.id,
            u.name,
            p.parent_id,
            p.side,
            p.placed_at
        FROM "user" u
        LEFT JOIN placement p ON u.id = p.child_id
        WHERE u.id = 'MNR1800143'
    """)
    
    result = db.execute(test_query).fetchone()
    if result and result.parent_id:
        print(f"✅ MNR1800143 placement found:")
        print(f"   - Parent: {result.parent_id}")
        print(f"   - Side: {result.side}")
        print(f"   - Placed at: {result.placed_at}")
    else:
        print(f"❌ MNR1800143 still has no placement")
    
    print("\n" + "="*60)
    print("SCRIPT COMPLETED")
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        fix_missing_placements()
    except Exception as e:
        print(f"\n❌ SCRIPT FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
