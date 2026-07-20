#!/usr/bin/env python3
"""
Migration Script: Move local storage files to Object Storage
DC Protocol Jan 2026

This script migrates existing attendance photos (and other files) 
from local filesystem to Replit Object Storage for production persistence.

Usage:
    python backend/scripts/migrate_local_to_object_storage.py

Features:
- Scans frontend/storage/ for all files
- Uploads each file to Object Storage
- Verifies upload success
- Reports migration statistics
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.services.object_storage import storage_service


def migrate_files(source_dir: str, dry_run: bool = False):
    """Migrate all files from source directory to Object Storage"""
    
    storage_root = project_root / "frontend" / "storage"
    source_path = storage_root / source_dir if source_dir else storage_root
    
    if not source_path.exists():
        print(f"❌ Source directory not found: {source_path}")
        return {"migrated": 0, "failed": 0, "skipped": 0}
    
    stats = {"migrated": 0, "failed": 0, "skipped": 0, "already_exists": 0}
    
    for root, dirs, files in os.walk(source_path):
        for filename in files:
            if filename.startswith('.'):
                continue
                
            file_path = Path(root) / filename
            relative_path = str(file_path.relative_to(storage_root))
            
            if storage_service.file_exists(relative_path):
                print(f"⏭️  Already in Object Storage: {relative_path}")
                stats["already_exists"] += 1
                continue
            
            if dry_run:
                print(f"🔍 Would migrate: {relative_path}")
                stats["migrated"] += 1
                continue
            
            try:
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                
                success = storage_service.upload_file(relative_path, file_data)
                
                if success:
                    print(f"✅ Migrated: {relative_path}")
                    stats["migrated"] += 1
                else:
                    print(f"❌ Failed: {relative_path}")
                    stats["failed"] += 1
                    
            except Exception as e:
                print(f"❌ Error migrating {relative_path}: {e}")
                stats["failed"] += 1
    
    return stats


def main():
    print("=" * 60)
    print("Local Storage to Object Storage Migration")
    print("DC Protocol Jan 2026")
    print("=" * 60)
    print()
    
    directories = [
        "attendance_evidence",
        "journey_photos",
        "expense_bills",
        "kyc_documents",
        "profile_photos",
        "reimbursement_bills",
        "payment_proofs",
        "feedback_media",
        "task_attachments"
    ]
    
    total_stats = {"migrated": 0, "failed": 0, "skipped": 0, "already_exists": 0}
    
    for directory in directories:
        print(f"\n📁 Processing: {directory}")
        print("-" * 40)
        
        stats = migrate_files(directory, dry_run=False)
        
        for key in total_stats:
            total_stats[key] += stats.get(key, 0)
    
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print(f"✅ Migrated: {total_stats['migrated']}")
    print(f"⏭️  Already existed: {total_stats['already_exists']}")
    print(f"❌ Failed: {total_stats['failed']}")
    print()


if __name__ == "__main__":
    main()
