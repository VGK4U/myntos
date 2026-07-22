import os
import sys
import zipfile
import tempfile
import shutil
import boto3
from pathlib import Path
from dotenv import load_dotenv

def upload_zip_to_s3():
    project_root = Path(__file__).parent.parent.parent
    load_dotenv(project_root / ".env")
    
    zip_path = project_root / "post_july13_files.zip"
    
    if not zip_path.exists():
        print(f"[ERROR] Zip file not found at {zip_path}")
        return

    print("=" * 60)
    print("[START] EXTRACTING AND MIGRATING FILES TO AWS S3")
    print("=" * 60)

    bucket_name = os.environ.get("AWS_S3_BUCKET_NAME")
    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    region = os.environ.get("AWS_REGION")
    
    if not bucket_name:
        print("[ERROR] AWS_S3_BUCKET_NAME is not set in .env")
        return
        
    s3_client = boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )
        
    print(f"[INFO] Connected to bucket: {bucket_name}")

    # Create temporary directory for extraction
    temp_dir = tempfile.mkdtemp()
    try:
        print(f"[EXTRACT] Extracting {zip_path.name}...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        migrated = 0
        failed = 0
        skipped = 0
        
        for root, _, files in os.walk(temp_dir):
            for filename in files:
                if filename.startswith('.'):
                    continue
                    
                local_file_path = Path(root) / filename
                s3_key = str(local_file_path.relative_to(temp_dir)).replace("\\", "/")
                
                # Check if exists
                try:
                    s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                    print(f"   [SKIP] Already exists: {s3_key}")
                    skipped += 1
                    continue
                except Exception as e:
                    # Not found, proceed to upload
                    pass
                    
                try:
                    with open(local_file_path, 'rb') as f:
                        file_data = f.read()
                        
                    s3_client.put_object(
                        Bucket=bucket_name,
                        Key=s3_key,
                        Body=file_data
                    )
                    
                    size_kb = len(file_data) / 1024
                    print(f"   [UPLOAD] Success: {s3_key} ({size_kb:.1f} KB)")
                    migrated += 1
                except Exception as e:
                    print(f"   [ERROR] Failed on {s3_key}: {str(e)}")
                    failed += 1
                    
        print("=" * 60)
        print("[STATS] MIGRATION COMPLETE")
        print(f"   Successfully Uploaded: {migrated}")
        print(f"   Skipped (Already in S3): {skipped}")
        print(f"   Failed: {failed}")
        print("=" * 60)
        
    finally:
        print("[CLEANUP] Cleaning up temporary files...")
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    upload_zip_to_s3()
