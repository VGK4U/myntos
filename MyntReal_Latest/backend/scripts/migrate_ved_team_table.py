"""
Ved Team Member Table Migration Script
Creates ved_team_member table and populates with existing Ved Team data
"""

import sys
sys.path.insert(0, '/home/runner/workspace/backend')

from app.core.database import SessionLocal, engine
from app.models.base import Base
from app.models.ved_team import VedTeamMember
from app.models.user import User
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_ved_team_table():
    """Create ved_team_member table"""
    try:
        logger.info("Creating ved_team_member table...")
        Base.metadata.create_all(bind=engine, tables=[VedTeamMember.__table__])
        logger.info("✅ Table created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Error creating table: {e}")
        return False

def populate_ved_team_data(db):
    """
    Populate Ved Team data for all users with 3+ direct referrals
    
    Logic:
    1. Find all users with 3+ direct referrals
    2. Identify Ved Head (3rd direct referral)
    3. Find all users in Ved Head's placement tree (NO CASCADING)
    4. Create VedTeamMember records
    """
    logger.info("\n" + "="*70)
    logger.info("POPULATING VED TEAM DATA")
    logger.info("="*70)
    
    # Get all users
    all_users = db.query(User).all()
    total_ved_owners = 0
    total_ved_members_created = 0
    
    for user in all_users:
        # Get direct referrals ordered by registration_date.asc(), id.asc()
        direct_refs = db.query(User).filter(
            User.referrer_id == user.id
        ).order_by(User.registration_date.asc(), User.id.asc()).all()
        
        # Skip if less than 3 direct referrals
        if len(direct_refs) < 3:
            continue
        
        total_ved_owners += 1
        ved_head = direct_refs[2]  # 3rd direct referral
        
        logger.info(f"\n👤 {user.id} ({user.name})")
        logger.info(f"   Total Direct Referrals: {len(direct_refs)}")
        logger.info(f"   Ved Head (3rd): {ved_head.id} - {ved_head.name}")
        
        # Get Ved Team (placement tree under Ved Head) using recursive CTE
        ved_tree_query = text("""
            WITH RECURSIVE ved_downline AS (
                -- Base: Start from Ved Head's children
                SELECT 
                    p.child_id as user_id,
                    p.parent_id,
                    p.side,
                    u.is_ved,
                    1 as level
                FROM placement p
                INNER JOIN "user" u ON u.id = p.child_id
                WHERE p.parent_id = :ved_root_id
                
                UNION ALL
                
                -- Recursive: Stop at other Ved owners (NO CASCADING)
                SELECT 
                    p.child_id,
                    p.parent_id,
                    p.side,
                    u.is_ved,
                    vd.level + 1
                FROM ved_downline vd
                INNER JOIN placement p ON p.parent_id = vd.user_id
                INNER JOIN "user" u ON u.id = p.child_id
                WHERE vd.level < 50
                  AND vd.is_ved = FALSE  -- Stop at Ved members
            )
            SELECT user_id, parent_id, side, level
            FROM ved_downline
            ORDER BY level, user_id
        """)
        
        result = db.execute(ved_tree_query, {'ved_root_id': str(ved_head.id)})
        ved_team = result.fetchall()
        
        logger.info(f"   Ved Team Members: {len(ved_team)}")
        
        # Create VedTeamMember records
        for member in ved_team:
            ved_member = VedTeamMember(
                ved_owner_id=user.id,
                ved_head_id=ved_head.id,
                member_id=member.user_id,
                level=member.level,
                parent_id=member.parent_id,
                position=member.side.upper() if member.side else None,
                is_active=True
            )
            db.add(ved_member)
            total_ved_members_created += 1
        
        if len(ved_team) > 0:
            logger.info(f"   ✅ Created {len(ved_team)} Ved Team records")
    
    db.commit()
    
    logger.info(f"\n{'='*70}")
    logger.info(f"✅ MIGRATION COMPLETE")
    logger.info(f"   Ved Owners: {total_ved_owners}")
    logger.info(f"   Ved Team Members Created: {total_ved_members_created}")
    logger.info(f"{'='*70}\n")
    
    return total_ved_owners, total_ved_members_created

def verify_ved_team_data(db, user_id='MNR1800359'):
    """Verify Ved Team data for a test user"""
    logger.info(f"\n{'='*70}")
    logger.info(f"VERIFICATION: {user_id}")
    logger.info(f"{'='*70}")
    
    # Get Ved Team members from new table
    ved_members = db.query(VedTeamMember).filter(
        VedTeamMember.ved_owner_id == user_id,
        VedTeamMember.is_active == True
    ).all()
    
    logger.info(f"\n📊 Ved Team Members from new table: {len(ved_members)}")
    
    activated_count = 0
    for member in ved_members:
        user = db.query(User).filter(User.id == member.member_id).first()
        if user and user.activation_date:
            activated_count += 1
            logger.info(f"   ✅ {member.member_id} - Level {member.level} - {member.position}")
    
    logger.info(f"\n   Total: {len(ved_members)}")
    logger.info(f"   Activated: {activated_count}")
    
    return len(ved_members), activated_count

def main():
    """Run migration"""
    logger.info("="*70)
    logger.info("VED TEAM MEMBER TABLE MIGRATION")
    logger.info("="*70)
    
    # Step 1: Create table
    if not create_ved_team_table():
        logger.error("❌ Failed to create table. Exiting.")
        return False
    
    # Step 2: Populate data
    db = SessionLocal()
    try:
        ved_owners, members_created = populate_ved_team_data(db)
        
        # Step 3: Verify with test user
        if ved_owners > 0:
            verify_ved_team_data(db, 'MNR1800359')
        
        logger.info("\n✅ MIGRATION SUCCESSFUL!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
