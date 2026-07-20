"""
Comprehensive Earnings Backfill Script for ALL Users - FIXED VED INCOME LOGIC
Creates individual transaction records based on actual referral and binary tree data
Uses PLACEMENT TREE for Ved income, not referral tree
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from decimal import Decimal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Configuration
DIRECT_REFERRAL_RATE_PLATINUM = 3000  # ₹3,000 per Platinum referral
MATCHING_RATE_PER_PAIR = 2000  # ₹2,000 per matched pair
VED_INCOME_RATE_PLATINUM = 1000  # ₹1,000 per Platinum activation under Ved
GURU_DAKSHINA_RATE = 0.02  # 2% of referral earnings

# Standard deductions
ADMIN_DEDUCTION_RATE = 0.08  # 8%
TDS_DEDUCTION_RATE = 0.02  # 2%
WITHDRAWAL_WALLET_SPLIT = 0.70  # 70%
UPGRADE_WALLET_SPLIT = 0.30  # 30%

def calculate_deductions(gross_amount):
    """Calculate standard deductions and wallet splits"""
    gross = Decimal(str(gross_amount))
    admin_ded = (gross * Decimal(str(ADMIN_DEDUCTION_RATE))).quantize(Decimal('0.01'))
    tds_ded = (gross * Decimal(str(TDS_DEDUCTION_RATE))).quantize(Decimal('0.01'))
    net = gross - admin_ded - tds_ded
    withdrawal = (net * Decimal(str(WITHDRAWAL_WALLET_SPLIT))).quantize(Decimal('0.01'))
    upgrade = net - withdrawal
    
    return {
        'admin_deduction': float(admin_ded),
        'tds_deduction': float(tds_ded),
        'net_amount': float(net),
        'withdrawal_amount': float(withdrawal),
        'upgrade_amount': float(upgrade)
    }

def process_direct_referrals(db, user_id):
    """Create individual direct referral records based on actual referrals"""
    # Get all direct referrals for this user
    referrals = db.execute(text("""
        SELECT id, name, activation_date, package_points
        FROM "user"
        WHERE referrer_id = :user_id
        AND activation_date IS NOT NULL
        ORDER BY activation_date
    """), {"user_id": user_id}).fetchall()
    
    records_created = 0
    total_amount = 0.0
    
    for referral in referrals:
        referral_id = referral.id
        referral_name = referral.name
        activation_date = referral.activation_date
        package_points = float(referral.package_points or 0)
        
        # Calculate bonus (₹3,000 for Platinum, ₹1,500 for Diamond, etc.)
        if package_points >= 1.0:  # Platinum
            bonus = DIRECT_REFERRAL_RATE_PLATINUM
        elif package_points >= 0.5:  # Diamond
            bonus = 1500
        else:
            bonus = 0  # Blue/Loyal get ₹0 initially
        
        if bonus <= 0:
            continue
        
        # Calculate deductions
        deductions = calculate_deductions(bonus)
        
        # Insert pending_income record
        db.execute(text("""
            INSERT INTO pending_income (
                user_id, income_type, gross_amount, admin_deduction, tds_deduction,
                net_amount, withdrawal_wallet_amount, upgraded_wallet_amount,
                business_date, calculation_timestamp, verification_status,
                created_at, updated_at, notes, related_user_id,
                left_points_consumed, right_points_consumed, pairs_matched
            ) VALUES (
                :user_id, 'Direct Referral', :gross, :admin_ded, :tds_ded,
                :net, :withdrawal, :upgrade,
                :business_date, :calc_timestamp, 'Completed',
                :created_at, :updated_at, :notes, :related_user_id,
                0, 0, 0
            )
        """), {
            "user_id": user_id,
            "gross": bonus,
            "admin_ded": deductions['admin_deduction'],
            "tds_ded": deductions['tds_deduction'],
            "net": deductions['net_amount'],
            "withdrawal": deductions['withdrawal_amount'],
            "upgrade": deductions['upgrade_amount'],
            "business_date": activation_date,
            "calc_timestamp": activation_date,
            "created_at": activation_date,
            "updated_at": activation_date,
            "notes": f"Direct referral bonus - {referral_name}",
            "related_user_id": referral_id
        })
        
        records_created += 1
        total_amount += bonus
    
    return records_created, total_amount

def calculate_binary_tree_points(db, user_id):
    """Calculate total points in left and right legs of binary tree"""
    result = db.execute(text("""
        WITH RECURSIVE left_tree AS (
            SELECT p.child_id, u.package_points
            FROM placement p
            JOIN "user" u ON p.child_id = u.id
            WHERE p.parent_id = :user_id AND p.side = 'left'
            
            UNION ALL
            
            SELECT p.child_id, u.package_points
            FROM placement p
            JOIN "user" u ON p.child_id = u.id
            INNER JOIN left_tree t ON p.parent_id = t.child_id
        ),
        right_tree AS (
            SELECT p.child_id, u.package_points
            FROM placement p
            JOIN "user" u ON p.child_id = u.id
            WHERE p.parent_id = :user_id AND p.side = 'right'
            
            UNION ALL
            
            SELECT p.child_id, u.package_points
            FROM placement p
            JOIN "user" u ON p.child_id = u.id
            INNER JOIN right_tree t ON p.parent_id = t.child_id
        )
        SELECT 
            (SELECT COALESCE(SUM(package_points), 0) FROM left_tree) as left_points,
            (SELECT COALESCE(SUM(package_points), 0) FROM right_tree) as right_points
    """), {"user_id": user_id}).fetchone()
    
    if result:
        return float(result.left_points or 0), float(result.right_points or 0)
    return 0.0, 0.0

def process_matching_referrals(db, user_id, user_package_points):
    """Create matching referral record based on binary tree data"""
    # Get binary tree points
    left_points, right_points = calculate_binary_tree_points(db, user_id)
    
    if left_points == 0 or right_points == 0:
        return 0, 0.0  # No matching possible
    
    # Check 1st matching rule: requires 2:1 or 1:2 ratio
    if not ((left_points >= 2.0 and right_points >= 1.0) or (left_points >= 1.0 and right_points >= 2.0)):
        return 0, 0.0  # Doesn't meet 1st matching criteria
    
    # Calculate pairs matched
    pairs_matched = min(left_points, right_points)
    points_consumed = pairs_matched  # Same value for both legs
    
    # Calculate income: pairs × user_package_points × ₹2,000
    gross_amount = pairs_matched * user_package_points * MATCHING_RATE_PER_PAIR
    
    if gross_amount <= 0:
        return 0, 0.0
    
    # Calculate deductions
    deductions = calculate_deductions(gross_amount)
    
    # Use current date as business_date for matching income
    business_date = datetime.now()
    
    # Insert pending_income record
    db.execute(text("""
        INSERT INTO pending_income (
            user_id, income_type, gross_amount, admin_deduction, tds_deduction,
            net_amount, withdrawal_wallet_amount, upgraded_wallet_amount,
            business_date, calculation_timestamp, verification_status,
            created_at, updated_at, notes,
            left_points_consumed, right_points_consumed, pairs_matched
        ) VALUES (
            :user_id, 'Matching Referral', :gross, :admin_ded, :tds_ded,
            :net, :withdrawal, :upgrade,
            :business_date, :calc_timestamp, 'Completed',
            :created_at, :updated_at, :notes,
            :left_consumed, :right_consumed, :pairs
        )
    """), {
        "user_id": user_id,
        "gross": gross_amount,
        "admin_ded": deductions['admin_deduction'],
        "tds_ded": deductions['tds_deduction'],
        "net": deductions['net_amount'],
        "withdrawal": deductions['withdrawal_amount'],
        "upgrade": deductions['upgrade_amount'],
        "business_date": business_date,
        "calc_timestamp": business_date,
        "created_at": business_date,
        "updated_at": business_date,
        "notes": f"Matching referral income - {int(pairs_matched)} pair(s) matched (Left: {left_points}, Right: {right_points})",
        "left_consumed": points_consumed,
        "right_consumed": points_consumed,
        "pairs": int(pairs_matched)
    })
    
    return 1, gross_amount

def process_ved_income(db, user_id):
    """
    Create Ved Income records using PLACEMENT TREE (FIXED LOGIC)
    
    NEW CORRECT LOGIC:
    - Find Ved members owned by this user
    - For each Ved member, get ALL activations in their binary PLACEMENT downline
    - STOP at sub-Ved members (no cascading)
    - Credit Ved income to the Ved owner
    """
    # Get Ved members owned by this user
    ved_members = db.execute(text("""
        SELECT id FROM "user"
        WHERE ved_owner_id = :user_id AND is_ved = TRUE
    """), {"user_id": user_id}).fetchall()
    
    if not ved_members:
        return 0, 0.0
    
    total_ved_income = 0.0
    records_created = 0
    
    # For each Ved member, find activations in their PLACEMENT downline
    for ved_member in ved_members:
        ved_member_id = ved_member.id
        
        # Get activations under this Ved member in PLACEMENT tree (NO CASCADING)
        activations = db.execute(text("""
            WITH RECURSIVE ved_downline AS (
                -- Start from Ved member's direct placements
                SELECT 
                    p.child_id,
                    1 as level
                FROM placement p
                WHERE p.parent_id = :ved_member_id
                
                UNION ALL
                
                -- Recursively get placements, but STOP at Ved members
                SELECT 
                    p.child_id,
                    vd.level + 1
                FROM ved_downline vd
                INNER JOIN placement p ON p.parent_id = vd.child_id
                INNER JOIN "user" child_user ON child_user.id = vd.child_id
                WHERE vd.level < 50  -- Deep enough for all trees
                  AND child_user.is_ved = FALSE  -- STOP at Ved members (NO CASCADING)
            )
            SELECT 
                u.id,
                u.name,
                u.activation_date,
                u.package_points
            FROM ved_downline vd
            INNER JOIN "user" u ON vd.child_id = u.id
            WHERE u.activation_date IS NOT NULL
              AND u.package_points >= 0.5  -- Platinum or Diamond
            ORDER BY u.activation_date
        """), {"ved_member_id": ved_member_id}).fetchall()
        
        for activation in activations:
            activation_id = activation.id
            activation_name = activation.name
            activation_date = activation.activation_date
            package_points = float(activation.package_points or 0)
            
            # Calculate Ved income
            if package_points >= 1.0:  # Platinum
                ved_income = VED_INCOME_RATE_PLATINUM
            elif package_points >= 0.5:  # Diamond
                ved_income = 500
            else:
                ved_income = 0
            
            if ved_income <= 0:
                continue
            
            # Calculate deductions
            deductions = calculate_deductions(ved_income)
            
            # Insert pending_income record
            db.execute(text("""
                INSERT INTO pending_income (
                    user_id, income_type, gross_amount, admin_deduction, tds_deduction,
                    net_amount, withdrawal_wallet_amount, upgraded_wallet_amount,
                    business_date, calculation_timestamp, verification_status,
                    created_at, updated_at, notes, related_user_id,
                    left_points_consumed, right_points_consumed, pairs_matched
                ) VALUES (
                    :user_id, 'Ved Income', :gross, :admin_ded, :tds_ded,
                    :net, :withdrawal, :upgrade,
                    :business_date, :calc_timestamp, 'Completed',
                    :created_at, :updated_at, :notes, :related_user_id,
                    0, 0, 0
                )
            """), {
                "user_id": user_id,
                "gross": ved_income,
                "admin_ded": deductions['admin_deduction'],
                "tds_ded": deductions['tds_deduction'],
                "net": deductions['net_amount'],
                "withdrawal": deductions['withdrawal_amount'],
                "upgrade": deductions['upgrade_amount'],
                "business_date": activation_date,
                "calc_timestamp": activation_date,
                "created_at": activation_date,
                "updated_at": activation_date,
                "notes": f"Ved Income - {activation_name} activated in binary tree under Ved member",
                "related_user_id": activation_id
            })
            
            records_created += 1
            total_ved_income += ved_income
    
    return records_created, total_ved_income

def process_guru_dakshina(db, user_id):
    """Create Guru Dakshina records based on direct referrals' earnings"""
    # Get all direct referrals and their earnings
    referrals_earnings = db.execute(text("""
        SELECT 
            u.id,
            u.name,
            COALESCE(SUM(pi.gross_amount), 0) as total_earnings
        FROM "user" u
        LEFT JOIN pending_income pi ON pi.user_id = u.id
        WHERE u.referrer_id = :user_id
        GROUP BY u.id, u.name
        HAVING COALESCE(SUM(pi.gross_amount), 0) > 0
    """), {"user_id": user_id}).fetchall()
    
    if not referrals_earnings:
        return 0, 0.0
    
    total_guru = 0.0
    records_created = 0
    business_date = datetime.now()
    
    for referral in referrals_earnings:
        referral_id = referral.id
        referral_name = referral.name
        referral_total_earnings = float(referral.total_earnings)
        
        # Calculate 2% Guru Dakshina
        guru_amount = referral_total_earnings * GURU_DAKSHINA_RATE
        
        if guru_amount <= 0:
            continue
        
        # Calculate deductions
        deductions = calculate_deductions(guru_amount)
        
        # Insert pending_income record
        db.execute(text("""
            INSERT INTO pending_income (
                user_id, income_type, gross_amount, admin_deduction, tds_deduction,
                net_amount, withdrawal_wallet_amount, upgraded_wallet_amount,
                business_date, calculation_timestamp, verification_status,
                created_at, updated_at, notes, related_user_id,
                left_points_consumed, right_points_consumed, pairs_matched
            ) VALUES (
                :user_id, 'Guru Dakshina', :gross, :admin_ded, :tds_ded,
                :net, :withdrawal, :upgrade,
                :business_date, :calc_timestamp, 'Completed',
                :created_at, :updated_at, :notes, :related_user_id,
                0, 0, 0
            )
        """), {
            "user_id": user_id,
            "gross": guru_amount,
            "admin_ded": deductions['admin_deduction'],
            "tds_ded": deductions['tds_deduction'],
            "net": deductions['net_amount'],
            "withdrawal": deductions['withdrawal_amount'],
            "upgrade": deductions['upgrade_amount'],
            "business_date": business_date,
            "calc_timestamp": business_date,
            "created_at": business_date,
            "updated_at": business_date,
            "notes": f"Guru Dakshina - 2% of referral earnings ({referral_name}: ₹{referral_total_earnings:,.2f})",
            "related_user_id": referral_id
        })
        
        records_created += 1
        total_guru += guru_amount
    
    return records_created, total_guru

def process_user(db, user_id, user_name, earned_total, package_points):
    """Process a single user - delete old records and create new individual records"""
    logger.info(f"\n{'='*80}")
    logger.info(f"Processing {user_id} ({user_name}): ₹{earned_total:,.2f}")
    logger.info(f"{'='*80}")
    
    # Step 1: Delete ALL existing pending_income records (clean slate)
    deleted_pending = db.execute(text("""
        DELETE FROM pending_income
        WHERE user_id = :user_id
    """), {"user_id": user_id}).rowcount
    
    logger.info(f"  🗑️  Deleted {deleted_pending} old pending_income records")
    
    # Step 2: Process Direct Referrals
    direct_count, direct_amount = process_direct_referrals(db, user_id)
    logger.info(f"  💰 Direct Referral: {direct_count} records, ₹{direct_amount:,.2f}")
    
    # Step 3: Process Matching Referrals
    matching_count, matching_amount = process_matching_referrals(db, user_id, package_points)
    logger.info(f"  🤝 Matching Referral: {matching_count} records, ₹{matching_amount:,.2f}")
    
    # Step 4: Process Ved Income (FIXED LOGIC - uses placement tree)
    ved_count, ved_amount = process_ved_income(db, user_id)
    logger.info(f"  🌳 Ved Income: {ved_count} records, ₹{ved_amount:,.2f}")
    
    # Step 5: Process Guru Dakshina (must be after other incomes are created)
    guru_count, guru_amount = process_guru_dakshina(db, user_id)
    logger.info(f"  🙏 Guru Dakshina: {guru_count} records, ₹{guru_amount:,.2f}")
    
    # Summary
    total_records = direct_count + matching_count + ved_count + guru_count
    total_calculated = direct_amount + matching_amount + ved_amount + guru_amount
    
    logger.info(f"  ✅ TOTAL: {total_records} records, ₹{total_calculated:,.2f} (earned_total: ₹{earned_total:,.2f})")
    
    return {
        'user_id': user_id,
        'total_records': total_records,
        'total_amount': total_calculated,
        'direct': {'count': direct_count, 'amount': direct_amount},
        'matching': {'count': matching_count, 'amount': matching_amount},
        'ved': {'count': ved_count, 'amount': ved_amount},
        'guru': {'count': guru_count, 'amount': guru_amount}
    }

def main():
    logger.info("="*100)
    logger.info("COMPREHENSIVE EARNINGS BACKFILL - FIXED VED INCOME (PLACEMENT TREE)")
    logger.info("="*100)
    
    db = SessionLocal()
    
    try:
        # Get all users with earned_total > 0
        users = db.execute(text("""
            SELECT id, name, earned_total, package_points
            FROM "user"
            WHERE earned_total > 0
            ORDER BY earned_total DESC
        """)).fetchall()
        
        logger.info(f"\n📊 Found {len(users)} users with earnings to process\n")
        
        results = []
        total_users_processed = 0
        total_records_created = 0
        
        for user in users:
            user_id = user.id
            user_name = user.name
            earned_total = float(user.earned_total)
            package_points = float(user.package_points or 1.0)
            
            result = process_user(db, user_id, user_name, earned_total, package_points)
            results.append(result)
            
            total_users_processed += 1
            total_records_created += result['total_records']
            
            # Commit after each user to prevent data loss
            db.commit()
        
        # Final Summary
        logger.info("\n" + "="*100)
        logger.info("FINAL SUMMARY - VED INCOME NOW USES PLACEMENT TREE")
        logger.info("="*100)
        logger.info(f"Total Users Processed: {total_users_processed}")
        logger.info(f"Total Records Created: {total_records_created}")
        logger.info(f"  - Direct Referral: {sum(r['direct']['count'] for r in results)}")
        logger.info(f"  - Matching Referral: {sum(r['matching']['count'] for r in results)}")
        logger.info(f"  - Ved Income: {sum(r['ved']['count'] for r in results)}")
        logger.info(f"  - Guru Dakshina: {sum(r['guru']['count'] for r in results)}")
        logger.info("="*100)
        logger.info("✅ BACKFILL COMPLETE!")
        
    except Exception as e:
        logger.error(f"❌ Error during backfill: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
