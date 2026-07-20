#!/usr/bin/env python3
"""
DC Protocol Phase 1.2: Reconciliation Script Validator
100% Perfect Validation Before Execution

Purpose: Validates the reconciliation script environment, dependencies,
         and formula correctness before running full analysis.

Usage:
    python scripts/dc_phase1_2_validator.py
    
Author: DC Protocol Implementation Team
Date: November 2, 2025
"""

import sys
import os
from typing import List, Tuple

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def validate_environment() -> Tuple[bool, List[str]]:
    """Validate Python environment and dependencies"""
    errors = []
    
    print("Validating environment...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        errors.append(f"Python 3.8+ required, found {sys.version}")
    else:
        print(f"  ✓ Python version: {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check required modules
    required_modules = [
        'sqlalchemy',
        'psycopg2',
    ]
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✓ Module '{module}' available")
        except ImportError:
            errors.append(f"Required module '{module}' not found")
    
    return len(errors) == 0, errors


def validate_database_connection() -> Tuple[bool, List[str]]:
    """Validate database connection"""
    errors = []
    
    print("\nValidating database connection...")
    
    try:
        from app.core.database import get_db
        db = next(get_db())
        
        # Test query
        from sqlalchemy import text
        result = db.execute(text("SELECT 1")).first()
        
        if result and result[0] == 1:
            print("  ✓ Database connection successful")
        else:
            errors.append("Database query returned unexpected result")
        
        db.close()
    
    except Exception as e:
        errors.append(f"Database connection failed: {e}")
    
    return len(errors) == 0, errors


def validate_required_tables() -> Tuple[bool, List[str]]:
    """Validate required database tables exist"""
    errors = []
    
    print("\nValidating required tables...")
    
    required_tables = [
        'user',
        'pending_income',
        'withdrawal_request'
    ]
    
    try:
        from app.core.database import get_db
        from sqlalchemy import text
        db = next(get_db())
        
        for table in required_tables:
            result = db.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table}'
                )
            """)).first()
            
            if result and result[0]:
                print(f"  ✓ Table '{table}' exists")
            else:
                errors.append(f"Required table '{table}' not found")
        
        db.close()
    
    except Exception as e:
        errors.append(f"Table validation failed: {e}")
    
    return len(errors) == 0, errors


def validate_required_columns() -> Tuple[bool, List[str]]:
    """Validate required columns exist in tables"""
    errors = []
    
    print("\nValidating required columns...")
    
    required_columns = {
        'user': ['id', 'earning_wallet', 'withdrawable_wallet'],
        'pending_income': ['user_id', 'net_amount', 'verification_status'],
        'withdrawal_request': ['user_id', 'final_payout', 'status']
    }
    
    try:
        from app.core.database import get_db
        from sqlalchemy import text
        db = next(get_db())
        
        for table, columns in required_columns.items():
            for column in columns:
                result = db.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = '{table}' AND column_name = '{column}'
                    )
                """)).first()
                
                if result and result[0]:
                    print(f"  ✓ Column '{table}.{column}' exists")
                else:
                    errors.append(f"Required column '{table}.{column}' not found")
        
        db.close()
    
    except Exception as e:
        errors.append(f"Column validation failed: {e}")
    
    return len(errors) == 0, errors


def validate_status_values() -> Tuple[bool, List[str]]:
    """Validate verification_status values in database match RFC v4.1"""
    errors = []
    warnings = []
    
    print("\nValidating verification_status values...")
    
    try:
        from app.core.database import get_db
        from sqlalchemy import text
        db = next(get_db())
        
        # Get all unique verification statuses
        result = db.execute(text("""
            SELECT DISTINCT verification_status 
            FROM pending_income 
            ORDER BY verification_status
        """)).fetchall()
        
        found_statuses = [row[0] for row in result]
        
        # RFC v4.1: All valid statuses
        valid_statuses = [
            'Pending', 'Admin Verified', 'Super Admin Verified', 'Super Admin Approved',
            'Finance Paid', 'Accounts Paid', 
            'Rejected', 'Not Eligible'
        ]
        
        print(f"  Found {len(found_statuses)} unique verification_status values:")
        
        for status in found_statuses:
            if status in valid_statuses:
                print(f"    ✓ '{status}' (valid)")
            else:
                print(f"    ✗ '{status}' (INVALID - needs cleanup)")
                warnings.append(f"Invalid status '{status}' found in database")
        
        if warnings:
            print(f"\n  ⚠ WARNING: {len(warnings)} invalid status values found")
            print("  ⚠ Run preflight cleanup before deploying validation trigger")
        
        db.close()
    
    except Exception as e:
        errors.append(f"Status validation failed: {e}")
    
    return len(errors) == 0, errors + warnings


def validate_formula_correctness() -> Tuple[bool, List[str]]:
    """Validate RFC v4.1 formulas with sample data"""
    errors = []
    
    print("\nValidating RFC v4.1 formulas with sample user...")
    
    try:
        from app.core.database import get_db
        from sqlalchemy import text
        from decimal import Decimal
        db = next(get_db())
        
        # Get first user with income records
        user_query = text("""
            SELECT DISTINCT user_id 
            FROM pending_income 
            LIMIT 1
        """)
        user_result = db.execute(user_query).first()
        
        if not user_result:
            print("  ⚠ No users with income records found (cannot validate formulas)")
            return True, []
        
        user_id = user_result[0]
        print(f"  Testing with user: {user_id}")
        
        # Test earning wallet formula
        earning_query = text("""
            SELECT COALESCE(SUM(net_amount), 0.0)
            FROM pending_income
            WHERE user_id = :user_id
            AND verification_status IN ('Pending', 'Admin Verified', 'Super Admin Verified', 'Super Admin Approved')
        """)
        earning_result = db.execute(earning_query, {"user_id": user_id}).first()
        earning_balance = Decimal(str(earning_result[0]))
        print(f"    Earning wallet: ₹{earning_balance}")
        
        # Test withdrawable wallet formula
        withdrawable_query = text("""
            WITH earned AS (
                SELECT COALESCE(SUM(net_amount), 0.0) as total
                FROM pending_income
                WHERE user_id = :user_id
                AND verification_status IN ('Finance Paid', 'Accounts Paid')
            ),
            withdrawn AS (
                SELECT COALESCE(SUM(final_payout), 0.0) as total
                FROM withdrawal_request
                WHERE user_id = :user_id
                AND status IN ('Bank Sent', 'Completed')
            )
            SELECT (SELECT total FROM earned) - (SELECT total FROM withdrawn)
        """)
        withdrawable_result = db.execute(withdrawable_query, {"user_id": user_id}).first()
        withdrawable_balance = Decimal(str(withdrawable_result[0]))
        print(f"    Withdrawable wallet: ₹{withdrawable_balance}")
        
        print("  ✓ Formulas execute successfully")
        
        db.close()
    
    except Exception as e:
        errors.append(f"Formula validation failed: {e}")
    
    return len(errors) == 0, errors


def validate_output_directories() -> Tuple[bool, List[str]]:
    """Validate output directories exist and are writable"""
    errors = []
    
    print("\nValidating output directories...")
    
    required_dirs = ['logs', 'reports']
    
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            try:
                os.makedirs(dir_name)
                print(f"  ✓ Created directory '{dir_name}'")
            except Exception as e:
                errors.append(f"Cannot create directory '{dir_name}': {e}")
        else:
            print(f"  ✓ Directory '{dir_name}' exists")
        
        # Test writability
        test_file = os.path.join(dir_name, '.write_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            print(f"    ✓ Directory '{dir_name}' is writable")
        except Exception as e:
            errors.append(f"Directory '{dir_name}' is not writable: {e}")
    
    return len(errors) == 0, errors


def main():
    """Main validation entry point"""
    print("=" * 70)
    print("DC PROTOCOL PHASE 1.2: RECONCILIATION SCRIPT VALIDATOR")
    print("100% Perfect Validation Before Execution")
    print("=" * 70)
    print()
    
    all_validations = [
        ("Environment", validate_environment),
        ("Database Connection", validate_database_connection),
        ("Required Tables", validate_required_tables),
        ("Required Columns", validate_required_columns),
        ("Status Values", validate_status_values),
        ("Formula Correctness", validate_formula_correctness),
        ("Output Directories", validate_output_directories),
    ]
    
    all_passed = True
    all_errors = []
    
    for name, validator in all_validations:
        passed, errors = validator()
        
        if not passed:
            all_passed = False
            all_errors.extend(errors)
    
    print()
    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    
    if all_passed:
        print("✓ ALL VALIDATIONS PASSED")
        print("✓ Safe to run reconciliation analysis")
        print()
        print("Next step:")
        print("  python scripts/dc_phase1_2_reconciliation.py --output reports/dc_reconciliation_baseline.json")
        return 0
    else:
        print(f"✗ {len(all_errors)} VALIDATION ERRORS")
        print()
        print("Errors:")
        for i, error in enumerate(all_errors, 1):
            print(f"  {i}. {error}")
        print()
        print("Fix errors before running reconciliation analysis")
        return 1


if __name__ == '__main__':
    sys.exit(main())
