#!/usr/bin/env python3
"""
Test Data Seeding Script
Creates comprehensive test data for end-to-end testing
"""

import sys
import os
import json
from datetime import datetime
import requests
from random import randint

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

class TestDataGenerator:
    """Generate test data for end-to-end testing"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.test_users = []
        self.test_data = {
            "users": [],
            "coupons": [],
            "bonanzas": [],
            "timestamp": datetime.now().isoformat()
        }
        
    def log(self, message, level="INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def create_test_sponsor(self):
        """Create a sponsor user for testing"""
        self.log("Creating test sponsor user...")
        
        test_sponsor = {
            "bev_id": f"BEVTEST{randint(100000, 999999)}",
            "first_name": "Test",
            "last_name": "Sponsor",
            "mobile_number": f"9{randint(100000000, 999999999)}",
            "password": "test123",
            "email": f"testsponsor{randint(1000, 9999)}@test.com",
            "user_type": "USER",
            "status": "Active"
        }
        
        self.test_data["users"].append(test_sponsor)
        self.log(f"✓ Created test sponsor: {test_sponsor['bev_id']}")
        return test_sponsor
    
    def create_test_users(self, count=5):
        """Create multiple test users"""
        self.log(f"Creating {count} test users...")
        
        sponsor = self.create_test_sponsor()
        
        for i in range(count):
            user = {
                "bev_id": f"BEVTEST{randint(100000, 999999)}",
                "first_name": f"TestUser{i+1}",
                "last_name": "System",
                "mobile_number": f"9{randint(100000000, 999999999)}",
                "password": "test123",
                "email": f"testuser{i+1}_{randint(1000, 9999)}@test.com",
                "sponsor_id": sponsor["bev_id"],
                "position": "LEFT" if i % 2 == 0 else "RIGHT",
                "user_type": "USER",
                "status": "Pending"
            }
            self.test_data["users"].append(user)
            self.log(f"✓ Created test user {i+1}/{count}: {user['bev_id']}")
        
        return self.test_data["users"]
    
    def create_test_bonanza(self):
        """Create a test bonanza"""
        self.log("Creating test bonanza...")
        
        bonanza = {
            "name": f"Test Bonanza {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "description": "Automated test bonanza - will be deleted after testing",
            "target_type": "referral_count",
            "target_value": 5,
            "reward_type": "cash",
            "reward_value": 1000,
            "start_date": datetime.now().date().isoformat(),
            "end_date": "2025-12-31",
            "status": "Active"
        }
        
        self.test_data["bonanzas"].append(bonanza)
        self.log(f"✓ Created test bonanza: {bonanza['name']}")
        return bonanza
    
    def save_test_manifest(self):
        """Save test data manifest for cleanup"""
        manifest_path = "tests/fixtures/test_manifest.json"
        
        with open(manifest_path, 'w') as f:
            json.dump(self.test_data, f, indent=2)
        
        self.log(f"✓ Saved test manifest to {manifest_path}")
        return manifest_path
    
    def run(self):
        """Execute test data creation"""
        try:
            self.log("=" * 60)
            self.log("STARTING TEST DATA GENERATION")
            self.log("=" * 60)
            
            # Create test users
            users = self.create_test_users(count=5)
            
            # Create test bonanza
            bonanza = self.create_test_bonanza()
            
            # Save manifest
            manifest = self.save_test_manifest()
            
            self.log("=" * 60)
            self.log("TEST DATA GENERATION COMPLETE")
            self.log(f"Total Users Created: {len(self.test_data['users'])}")
            self.log(f"Total Bonanzas Created: {len(self.test_data['bonanzas'])}")
            self.log(f"Manifest saved to: {manifest}")
            self.log("=" * 60)
            
            return True
            
        except Exception as e:
            self.log(f"ERROR: {str(e)}", level="ERROR")
            return False

if __name__ == "__main__":
    generator = TestDataGenerator()
    success = generator.run()
    sys.exit(0 if success else 1)
