"""
DC PROTOCOL: Backfill Bonanza Contributor Snapshots
===================================================
This script backfills existing bonanza claims with contributor snapshots.
Ensures historical bonanza breakdowns remain immutable and never change.

Run with: cd backend && python scripts/backfill_bonanza_snapshots.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, and_
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.bonanza import DynamicBonanzaHistory
from app.models.user import User

def backfill_bonanza_snapshots():
    """Backfill contributor snapshots for existing bonanza claims"""
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    db = Session(engine)
    
    try:
        # Get all bonanza claims without snapshots (both direct AND matching)
        from sqlalchemy import or_
        claims = db.query(DynamicBonanzaHistory).filter(
            or_(
                and_(
                    DynamicBonanzaHistory.deduction_amount_direct > 0,
                    DynamicBonanzaHistory.direct_contributors_snapshot.is_(None)
                ),
                and_(
                    DynamicBonanzaHistory.deduction_amount_matching > 0,
                    DynamicBonanzaHistory.matching_contributors_snapshot.is_(None)
                )
            )
        ).all()
        
        print(f"Found {len(claims)} bonanza claims to backfill")
        
        for claim in claims:
            print(f"\n{'='*80}")
            print(f"Backfilling Claim ID: {claim.id}")
            print(f"User: {claim.user_id}")
            print(f"Direct Deduction: {claim.deduction_amount_direct}")
            print(f"Matching Deduction: {claim.deduction_amount_matching or 0}")
            
            # Backfill direct contributors snapshot
            if claim.deduction_amount_direct > 0 and not claim.direct_contributors_snapshot:
                print(f"\n  Processing Direct Contributors...")
                
                # Get user's direct referrals (EXACT same logic as claim endpoint)
                referrals = db.query(User).filter(
                    and_(
                        User.referrer_id == claim.user_id,
                        User.coupon_status == 'Activated'
                    )
                ).order_by(User.activation_date.asc()).all()
                
                # Take first N referrals (where N = deduction_amount_direct)
                consumed_referrals = referrals[:claim.deduction_amount_direct]
                
                # Build JSON snapshot
                direct_snapshot = [
                    {
                        'user_id': ref.id,
                        'name': ref.name,
                        'package': 'Platinum' if float(ref.package_points or 0) >= 1.0 else 'Diamond',
                        'points': float(ref.package_points or 0),
                        'activation_date': ref.activation_date.isoformat() if ref.activation_date else None
                    }
                    for ref in consumed_referrals
                ]
                
                claim.direct_contributors_snapshot = direct_snapshot
                
                print(f"  ✓ Captured {len(direct_snapshot)} direct contributors:")
                for i, contrib in enumerate(direct_snapshot, 1):
                    print(f"    {i}. {contrib['user_id']} - {contrib['name']} ({contrib['package']}, {contrib['points']} pts)")
            
            # Backfill matching contributors snapshot
            if claim.deduction_amount_matching > 0 and not claim.matching_contributors_snapshot:
                print(f"\n  Processing Matching Contributors...")
                
                # Get user object
                user = db.query(User).filter(User.id == claim.user_id).first()
                if not user:
                    print(f"  ✗ User not found, skipping matching backfill")
                    continue
                
                # Get left and right leg members (EXACT same logic as claim endpoint)
                left_leg = db.query(User).filter(
                    User.position.like(f'{user.position}L%'),
                    User.coupon_status == 'Activated'
                ).order_by(User.activation_date.asc()).all()
                
                right_leg = db.query(User).filter(
                    User.position.like(f'{user.position}R%'),
                    User.coupon_status == 'Activated'
                ).order_by(User.activation_date.asc()).all()
                
                # Build JSON snapshot
                matching_snapshot = {
                    'left_leg': [
                        {
                            'user_id': m.id,
                            'name': m.name,
                            'package': 'Platinum' if float(m.package_points or 0) >= 1.0 else 'Diamond',
                            'points': float(m.package_points or 0)
                        }
                        for m in left_leg
                    ],
                    'right_leg': [
                        {
                            'user_id': m.id,
                            'name': m.name,
                            'package': 'Platinum' if float(m.package_points or 0) >= 1.0 else 'Diamond',
                            'points': float(m.package_points or 0)
                        }
                        for m in right_leg
                    ]
                }
                
                claim.matching_contributors_snapshot = matching_snapshot
                
                print(f"  ✓ Captured matching contributors:")
                print(f"    Left Leg: {len(matching_snapshot['left_leg'])} members")
                print(f"    Right Leg: {len(matching_snapshot['right_leg'])} members")
        
        # Commit all changes
        db.commit()
        
        print(f"\n{'='*80}")
        print(f"✓ BACKFILL COMPLETE!")
        print(f"  - {len(claims)} bonanza claims updated with contributor snapshots")
        print(f"  - Historical bonanza breakdowns are now immutable (DC Protocol)")
        print(f"{'='*80}\n")
        
    except Exception as e:
        db.rollback()
        print(f"\n✗ ERROR: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    backfill_bonanza_snapshots()
