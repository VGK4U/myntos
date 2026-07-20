#!/usr/bin/env python3
"""
Object Storage Reconciliation Script
One-time task to verify and recover media files from local storage to Object Storage.

Performs two-phase reconciliation:
1. Database-driven: Scans media tables, verifies Object Storage, uploads missing from local
2. Filesystem-driven: Scans local storage, uploads any files not in Object Storage

Usage: python -m scripts.reconcile_object_storage

Jan 23, 2026: Initial implementation
"""

import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.services.object_storage import storage_service

DATABASE_URL = os.environ.get("DATABASE_URL")
LOCAL_STORAGE_ROOT = Path("/home/runner/workspace/frontend/storage")

MEDIA_TABLES = [
    {
        "name": "feedback_media",
        "table": "feedback_media",
        "path_column": "file_path",
        "id_column": "id",
        "filter": "file_path IS NOT NULL AND file_path != 'pending'"
    },
    {
        "name": "staff_task_attachments",
        "table": "staff_task_attachments",
        "path_column": "file_path",
        "id_column": "id",
        "filter": "file_path IS NOT NULL AND is_deleted = false"
    },
    {
        "name": "staff_journeys (photo)",
        "table": "staff_journeys",
        "path_column": "photo_path",
        "id_column": "id",
        "filter": "photo_path IS NOT NULL"
    },
    {
        "name": "staff_reimbursement_claim_items",
        "table": "staff_reimbursement_claim_items",
        "path_column": "bill_path",
        "id_column": "id",
        "filter": "bill_path IS NOT NULL"
    },
    {
        "name": "rd_property_media",
        "table": "rd_property_media",
        "path_column": "file_path",
        "id_column": "id",
        "filter": "file_path IS NOT NULL"
    },
    {
        "name": "staff_attendance_evidence",
        "table": "staff_attendance_evidence",
        "path_column": "photo_path",
        "id_column": "id",
        "filter": "photo_path IS NOT NULL"
    },
    {
        "name": "kyc_document",
        "table": "kyc_document",
        "path_column": "file_path",
        "id_column": "id",
        "filter": "file_path IS NOT NULL AND file_path != 'pending'"
    },
    {
        "name": "stock_item_images (original)",
        "table": "stock_item_images",
        "path_column": "original_path",
        "id_column": "id",
        "filter": "original_path IS NOT NULL"
    },
]

MEDIA_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov', '.avi', '.pdf', '.doc', '.docx'}


def normalize_storage_path(db_path: str) -> str:
    """
    Normalize database path to Object Storage key.
    Strips prefixes like 'frontend/storage/', '/storage/', etc.
    """
    if not db_path:
        return ""
    
    path = db_path.strip()
    
    prefixes_to_strip = [
        "frontend/storage/",
        "/frontend/storage/",
        "/storage/",
        "storage/",
    ]
    
    for prefix in prefixes_to_strip:
        if path.startswith(prefix):
            path = path[len(prefix):]
            break
    
    if path.startswith("/"):
        path = path[1:]
    
    return path


def check_object_storage(storage_key: str) -> bool:
    """Check if file exists in Object Storage."""
    try:
        data = storage_service.download_file(storage_key)
        return data is not None and len(data) > 0
    except Exception:
        return False


def check_local_storage(storage_key: str) -> tuple[bool, Path | None]:
    """Check if file exists in local storage."""
    local_path = LOCAL_STORAGE_ROOT / storage_key
    if local_path.exists() and local_path.is_file():
        return True, local_path
    return False, None


def upload_to_object_storage(storage_key: str, local_path: Path) -> bool:
    """Upload file from local storage to Object Storage."""
    try:
        with open(local_path, "rb") as f:
            file_content = f.read()
        
        if len(file_content) == 0:
            return False
        
        success = storage_service.upload_file(storage_key, file_content)
        return success
    except Exception as e:
        print(f"    [ERROR] Upload failed for {storage_key}: {e}")
        return False


def scan_local_storage() -> list[dict]:
    """Scan local storage directory and return all media files."""
    files = []
    
    if not LOCAL_STORAGE_ROOT.exists():
        return files
    
    for file_path in LOCAL_STORAGE_ROOT.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in MEDIA_EXTENSIONS:
            relative_path = file_path.relative_to(LOCAL_STORAGE_ROOT)
            files.append({
                "local_path": file_path,
                "storage_key": str(relative_path),
                "size": file_path.stat().st_size
            })
    
    return files


def run_reconciliation():
    """Main reconciliation logic."""
    print("=" * 80)
    print("OBJECT STORAGE RECONCILIATION REPORT")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print("=" * 80)
    
    if not DATABASE_URL:
        print("[FATAL] DATABASE_URL not set")
        return
    
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    total_db_records = 0
    db_already_present = 0
    db_recovered = 0
    db_failures = 0
    
    detailed_failures = []
    detailed_recoveries = []
    
    print("\n" + "=" * 80)
    print("PHASE 1: DATABASE-DRIVEN RECONCILIATION")
    print("=" * 80)
    
    for table_config in MEDIA_TABLES:
        table_name = table_config["name"]
        table = table_config["table"]
        path_column = table_config["path_column"]
        id_column = table_config["id_column"]
        filter_clause = table_config["filter"]
        
        print(f"\n--- Scanning: {table_name} ---")
        
        try:
            result = session.execute(text(f"SELECT 1 FROM information_schema.tables WHERE table_name = '{table}'"))
            if not result.fetchone():
                print(f"    [SKIP] Table does not exist")
                continue
        except Exception as e:
            print(f"    [ERROR] Table check failed: {e}")
            continue
        
        try:
            query = f"SELECT {id_column}, {path_column} FROM {table} WHERE {filter_clause}"
            result = session.execute(text(query))
            rows = result.fetchall()
        except Exception as e:
            print(f"    [ERROR] Query failed: {e}")
            continue
        
        table_total = len(rows)
        table_present = 0
        table_recovered = 0
        table_failed = 0
        
        for row in rows:
            record_id = row[0]
            db_path = row[1]
            
            if not db_path or db_path == "pending":
                continue
            
            total_db_records += 1
            storage_key = normalize_storage_path(db_path)
            
            if not storage_key:
                continue
            
            if check_object_storage(storage_key):
                table_present += 1
                db_already_present += 1
            else:
                exists_local, local_path = check_local_storage(storage_key)
                
                if exists_local and local_path:
                    success = upload_to_object_storage(storage_key, local_path)
                    if success:
                        table_recovered += 1
                        db_recovered += 1
                        detailed_recoveries.append({
                            "source": "database",
                            "table": table_name,
                            "record_id": record_id,
                            "storage_key": storage_key
                        })
                        print(f"    [RECOVERED] {storage_key}")
                    else:
                        table_failed += 1
                        db_failures += 1
                        detailed_failures.append({
                            "source": "database",
                            "table": table_name,
                            "record_id": record_id,
                            "storage_key": storage_key,
                            "reason": "Upload to Object Storage failed"
                        })
                else:
                    table_failed += 1
                    db_failures += 1
                    detailed_failures.append({
                        "source": "database",
                        "table": table_name,
                        "record_id": record_id,
                        "storage_key": storage_key,
                        "reason": "Missing in both locations"
                    })
                    print(f"    [MISSING] {storage_key} (record {record_id})")
        
        print(f"    Records: {table_total} | Present: {table_present} | Recovered: {table_recovered} | Failed: {table_failed}")
    
    session.close()
    
    print("\n" + "=" * 80)
    print("PHASE 2: FILESYSTEM-DRIVEN RECONCILIATION")
    print("=" * 80)
    
    local_files = scan_local_storage()
    print(f"\nFound {len(local_files)} media files in local storage")
    
    fs_already_present = 0
    fs_uploaded = 0
    fs_failed = 0
    
    categories = {}
    for file_info in local_files:
        category = file_info["storage_key"].split("/")[0] if "/" in file_info["storage_key"] else "root"
        if category not in categories:
            categories[category] = {"total": 0, "present": 0, "uploaded": 0, "failed": 0}
        categories[category]["total"] += 1
    
    for file_info in local_files:
        storage_key = file_info["storage_key"]
        local_path = file_info["local_path"]
        category = storage_key.split("/")[0] if "/" in storage_key else "root"
        
        if check_object_storage(storage_key):
            fs_already_present += 1
            categories[category]["present"] += 1
        else:
            success = upload_to_object_storage(storage_key, local_path)
            if success:
                fs_uploaded += 1
                categories[category]["uploaded"] += 1
                detailed_recoveries.append({
                    "source": "filesystem",
                    "table": "N/A",
                    "record_id": "N/A",
                    "storage_key": storage_key
                })
                print(f"    [UPLOADED] {storage_key}")
            else:
                fs_failed += 1
                categories[category]["failed"] += 1
                detailed_failures.append({
                    "source": "filesystem",
                    "table": "N/A",
                    "record_id": "N/A",
                    "storage_key": storage_key,
                    "reason": "Upload failed"
                })
    
    print("\n--- Filesystem Scan by Category ---")
    for cat, stats in sorted(categories.items()):
        print(f"    {cat}: Total={stats['total']} | In ObjectStorage={stats['present']} | Uploaded={stats['uploaded']} | Failed={stats['failed']}")
    
    print()
    print("=" * 80)
    print("RECONCILIATION SUMMARY")
    print("=" * 80)
    print()
    print("PHASE 1 - Database-Driven:")
    print(f"  Total records scanned:              {total_db_records:>6}")
    print(f"  Files already in Object Storage:   {db_already_present:>6}")
    print(f"  Files recovered from local:        {db_recovered:>6}")
    print(f"  Hard failures (missing):           {db_failures:>6}")
    print()
    print("PHASE 2 - Filesystem-Driven:")
    print(f"  Total local files scanned:         {len(local_files):>6}")
    print(f"  Files already in Object Storage:   {fs_already_present:>6}")
    print(f"  Files uploaded to Object Storage:  {fs_uploaded:>6}")
    print(f"  Upload failures:                   {fs_failed:>6}")
    print()
    print("TOTALS:")
    print(f"  Total files now in Object Storage: {db_already_present + db_recovered + fs_already_present + fs_uploaded:>6}")
    print(f"  Total recovered/uploaded:          {db_recovered + fs_uploaded:>6}")
    print(f"  Total hard failures:               {db_failures + fs_failed:>6}")
    print("=" * 80)
    
    if detailed_recoveries:
        print()
        print(f"RECOVERED/UPLOADED FILES ({len(detailed_recoveries)} total):")
        for item in detailed_recoveries[:20]:
            print(f"  - [{item['source']}] {item['storage_key']}")
        if len(detailed_recoveries) > 20:
            print(f"  ... and {len(detailed_recoveries) - 20} more")
    
    if detailed_failures:
        print()
        print(f"HARD FAILURES ({len(detailed_failures)} total):")
        for item in detailed_failures:
            print(f"  - [{item['source']}:{item.get('table', 'N/A')}] {item['storage_key']}")
            print(f"    Reason: {item['reason']}")
    
    print()
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print("=" * 80)
    
    return {
        "phase1": {
            "total_records": total_db_records,
            "already_present": db_already_present,
            "recovered": db_recovered,
            "failures": db_failures
        },
        "phase2": {
            "total_files": len(local_files),
            "already_present": fs_already_present,
            "uploaded": fs_uploaded,
            "failures": fs_failed
        },
        "detailed_failures": detailed_failures,
        "detailed_recoveries": detailed_recoveries
    }


if __name__ == "__main__":
    run_reconciliation()
