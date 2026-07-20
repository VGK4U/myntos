#!/usr/bin/env python3
"""
MNR TEST USER MANAGEMENT SYSTEM
Creates and manages test users for Selenium testing with automatic cleanup
"""

import sys
import os
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.app.db.session import SessionLocal
from backend.app.models.user import User
from backend.app.core.security import get_password_hash
from sqlalchemy import text

# Test User Configuration
TEST_PARENT_USER_ID = "MNR1900000"
TEST_USER_ID_PREFIX = "MNR19"  # All test users start with MNR19XXXXX
TEST_USER_PASSWORD = "TestPass123!"

# Color codes for console output
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{'='*80}")
    print(f"{CYAN}{text:^80}{RESET}")
    print(f"{'='*80}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_info(text):
    print(f"{BLUE}► {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")


class TestUserManager:
    def __init__(self):
        self.db = SessionLocal()
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()
    
    def ensure_test_parent_exists(self):
        """Ensure the test parent user exists"""
        print_info(f"Checking test parent user: {TEST_PARENT_USER_ID}")
        
        parent = self.db.query(User).filter(User.user_id == TEST_PARENT_USER_ID).first()
        
        if not parent:
            print_warning(f"Test parent user {TEST_PARENT_USER_ID} does not exist. Creating...")
            
            parent = User(
                user_id=TEST_PARENT_USER_ID,
                name="Test Parent User",
                email="testparent@mnr.test",
                mobile="9000000000",
                password=get_password_hash(TEST_USER_PASSWORD),
                user_type="Standard",
                package_id=1,
                sponsor_id=None,
                placement_id=None,
                position="L"
            )
            
            self.db.add(parent)
            self.db.commit()
            self.db.refresh(parent)
            
            print_success(f"Created test parent user: {TEST_PARENT_USER_ID}")
        else:
            print_success(f"Test parent user exists: {parent.name}")
        
        return parent
    
    def create_test_user(self, name, email, mobile, package_id=1, user_type="Standard"):
        """Create a single test user under the test parent"""
        
        # Ensure parent exists
        parent = self.ensure_test_parent_exists()
        
        # Generate unique user ID
        timestamp = datetime.now().strftime("%H%M%S")
        user_id = f"{TEST_USER_ID_PREFIX}{timestamp}"
        
        # Check if user exists
        existing = self.db.query(User).filter(User.user_id == user_id).first()
        if existing:
            print_warning(f"User {user_id} already exists. Skipping...")
            return existing
        
        # Create test user
        test_user = User(
            user_id=user_id,
            name=name,
            email=email,
            mobile=mobile,
            password=get_password_hash(TEST_USER_PASSWORD),
            user_type=user_type,
            package_id=package_id,
            sponsor_id=TEST_PARENT_USER_ID,
            placement_id=TEST_PARENT_USER_ID,
            position="L"
        )
        
        self.db.add(test_user)
        self.db.commit()
        self.db.refresh(test_user)
        
        print_success(f"Created test user: {user_id} - {name}")
        print_info(f"  Email: {email}")
        print_info(f"  Mobile: {mobile}")
        print_info(f"  Package: {package_id}")
        print_info(f"  Type: {user_type}")
        
        return test_user
    
    def create_bulk_test_users(self, count=10):
        """Create multiple test users for testing"""
        print_info(f"Creating {count} test users...")
        
        created_users = []
        
        for i in range(1, count + 1):
            timestamp = datetime.now().strftime("%H%M%S") + str(i).zfill(2)
            
            user = self.create_test_user(
                name=f"Test User {i}",
                email=f"testuser{timestamp}@mnr.test",
                mobile=f"90{timestamp[:8]}",
                package_id=(i % 4) + 1,  # Rotate through packages 1-4
                user_type="Standard"
            )
            
            created_users.append(user)
        
        print_success(f"Successfully created {len(created_users)} test users")
        return created_users
    
    def list_test_users(self):
        """List all test users"""
        print_info("Listing all test users...")
        
        test_users = self.db.query(User).filter(
            User.user_id.like(f'{TEST_USER_ID_PREFIX}%')
        ).all()
        
        if not test_users:
            print_warning("No test users found")
            return []
        
        print_success(f"Found {len(test_users)} test users:")
        
        for user in test_users:
            print(f"  • {user.user_id} - {user.name} ({user.user_type})")
        
        return test_users
    
    def cleanup_test_users(self):
        """Delete all test users and their related data"""
        print_header("CLEANING UP TEST USERS")
        
        # Find all test users
        test_users = self.db.query(User).filter(
            User.user_id.like(f'{TEST_USER_ID_PREFIX}%')
        ).all()
        
        if not test_users:
            print_warning("No test users to clean up")
            return 0
        
        user_ids = [u.user_id for u in test_users]
        print_info(f"Found {len(user_ids)} test users to delete")
        
        # Delete related records in order
        tables_to_clean = [
            'user_income',
            'user_earnings',
            'withdrawal_requests',
            'awards_tracking',
            'bonanza_tracking',
            'ev_coupon_benefits',
            'user_wallets',
            'bank_accounts',
            'kyc_documents',
            'announcements',
            'announcement_ratings',
            'training_course_claims',
            'ev_vehicle_claims'
        ]
        
        total_deleted = 0
        
        for table in tables_to_clean:
            try:
                result = self.db.execute(
                    text(f"DELETE FROM {table} WHERE user_id LIKE :prefix"),
                    {"prefix": f"{TEST_USER_ID_PREFIX}%"}
                )
                deleted = result.rowcount
                if deleted > 0:
                    print_info(f"  Deleted {deleted} records from {table}")
                    total_deleted += deleted
            except Exception as e:
                print_warning(f"  Could not clean {table}: {str(e)}")
        
        # Delete users last
        for user in test_users:
            try:
                self.db.delete(user)
                print_success(f"  Deleted user: {user.user_id} - {user.name}")
            except Exception as e:
                print_error(f"  Failed to delete {user.user_id}: {str(e)}")
        
        self.db.commit()
        
        print_success(f"\n✅ Cleanup complete! Deleted {len(test_users)} users and {total_deleted} related records")
        
        return len(test_users)
    
    def get_test_credentials(self):
        """Return test credentials for Selenium tests"""
        return {
            'parent': {
                'user_id': TEST_PARENT_USER_ID,
                'password': TEST_USER_PASSWORD
            },
            'test_password': TEST_USER_PASSWORD
        }


def main():
    """Main CLI interface"""
    print_header("MNR TEST USER MANAGER")
    
    if len(sys.argv) < 2:
        print_info("Usage:")
        print("  python test_user_manager.py create <count>    - Create test users")
        print("  python test_user_manager.py list              - List all test users")
        print("  python test_user_manager.py cleanup           - Delete all test users")
        print("  python test_user_manager.py ensure-parent     - Ensure parent exists")
        return
    
    command = sys.argv[1].lower()
    
    with TestUserManager() as manager:
        if command == "create":
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            manager.create_bulk_test_users(count)
            
        elif command == "list":
            manager.list_test_users()
            
        elif command == "cleanup":
            confirm = input(f"{YELLOW}⚠️  This will delete ALL test users (MNR19XXXXX). Continue? (yes/no): {RESET}")
            if confirm.lower() == 'yes':
                manager.cleanup_test_users()
            else:
                print_info("Cleanup cancelled")
                
        elif command == "ensure-parent":
            manager.ensure_test_parent_exists()
            
        else:
            print_error(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
