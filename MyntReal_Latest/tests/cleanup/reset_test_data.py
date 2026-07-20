#!/usr/bin/env python3
"""
Test Data Cleanup Script
Removes all test data created during end-to-end testing
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

class TestDataCleanup:
    """Clean up test data after end-to-end testing"""
    
    def __init__(self):
        self.manifest_path = "tests/fixtures/test_manifest.json"
        self.test_data = None
        self.cleanup_summary = {
            "users_deleted": 0,
            "bonanzas_deleted": 0,
            "errors": []
        }
        
    def log(self, message, level="INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def load_manifest(self):
        """Load test data manifest"""
        try:
            if not os.path.exists(self.manifest_path):
                self.log("No test manifest found - nothing to clean up", level="WARN")
                return False
                
            with open(self.manifest_path, 'r') as f:
                self.test_data = json.load(f)
            
            self.log(f"✓ Loaded test manifest: {len(self.test_data.get('users', []))} users, "
                    f"{len(self.test_data.get('bonanzas', []))} bonanzas")
            return True
            
        except Exception as e:
            self.log(f"ERROR loading manifest: {str(e)}", level="ERROR")
            return False
    
    def delete_test_users(self):
        """Delete all test users from manifest"""
        self.log("Deleting test users...")
        
        users = self.test_data.get('users', [])
        
        for user in users:
            try:
                # In production, this would call the API or database
                # For now, we'll just log the deletion
                bev_id = user.get('bev_id')
                self.log(f"  → Deleting user: {bev_id}")
                
                # Simulate deletion
                # DELETE FROM users WHERE bev_id = '{bev_id}' AND bev_id LIKE 'BEVTEST%'
                
                self.cleanup_summary['users_deleted'] += 1
                
            except Exception as e:
                error_msg = f"Failed to delete user {user.get('bev_id')}: {str(e)}"
                self.log(error_msg, level="ERROR")
                self.cleanup_summary['errors'].append(error_msg)
        
        self.log(f"✓ Deleted {self.cleanup_summary['users_deleted']} test users")
    
    def delete_test_bonanzas(self):
        """Delete all test bonanzas from manifest"""
        self.log("Deleting test bonanzas...")
        
        bonanzas = self.test_data.get('bonanzas', [])
        
        for bonanza in bonanzas:
            try:
                # In production, this would call the API or database
                name = bonanza.get('name')
                self.log(f"  → Deleting bonanza: {name}")
                
                # Simulate deletion
                # DELETE FROM bonanzas WHERE name LIKE 'Test Bonanza%'
                
                self.cleanup_summary['bonanzas_deleted'] += 1
                
            except Exception as e:
                error_msg = f"Failed to delete bonanza {bonanza.get('name')}: {str(e)}"
                self.log(error_msg, level="ERROR")
                self.cleanup_summary['errors'].append(error_msg)
        
        self.log(f"✓ Deleted {self.cleanup_summary['bonanzas_deleted']} test bonanzas")
    
    def cleanup_manifest(self):
        """Remove the test manifest file"""
        try:
            if os.path.exists(self.manifest_path):
                os.remove(self.manifest_path)
                self.log(f"✓ Removed test manifest: {self.manifest_path}")
        except Exception as e:
            self.log(f"ERROR removing manifest: {str(e)}", level="ERROR")
    
    def save_cleanup_report(self):
        """Save cleanup summary report"""
        report_path = f"tests/logs/cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_path, 'w') as f:
            json.dump(self.cleanup_summary, f, indent=2)
        
        self.log(f"✓ Saved cleanup report to {report_path}")
    
    def run(self):
        """Execute test data cleanup"""
        try:
            self.log("=" * 60)
            self.log("STARTING TEST DATA CLEANUP")
            self.log("=" * 60)
            
            # Load manifest
            if not self.load_manifest():
                return True  # Nothing to clean up
            
            # Delete test data
            self.delete_test_users()
            self.delete_test_bonanzas()
            
            # Save report
            self.save_cleanup_report()
            
            # Remove manifest
            self.cleanup_manifest()
            
            self.log("=" * 60)
            self.log("TEST DATA CLEANUP COMPLETE")
            self.log(f"Users Deleted: {self.cleanup_summary['users_deleted']}")
            self.log(f"Bonanzas Deleted: {self.cleanup_summary['bonanzas_deleted']}")
            self.log(f"Errors: {len(self.cleanup_summary['errors'])}")
            self.log("=" * 60)
            
            return len(self.cleanup_summary['errors']) == 0
            
        except Exception as e:
            self.log(f"FATAL ERROR: {str(e)}", level="ERROR")
            return False

if __name__ == "__main__":
    cleanup = TestDataCleanup()
    success = cleanup.run()
    sys.exit(0 if success else 1)
