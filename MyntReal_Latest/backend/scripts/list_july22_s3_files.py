import os
import sys
import boto3
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

def list_recent_s3_files():
    project_root = Path(__file__).parent.parent.parent
    load_dotenv(project_root / ".env")

    bucket_name = os.environ.get("AWS_S3_BUCKET_NAME")
    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    region = os.environ.get("AWS_REGION")
    
    if not bucket_name:
        print("ERROR: AWS_S3_BUCKET_NAME is not set in .env")
        return
        
    s3_client = boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )
        
    print(f"Connected to bucket: {bucket_name}")
    print("Scanning for files uploaded on July 22, 2026...\n")
    
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name)
    
    target_date_str = "2026-07-22"
    matched_files = []
    
    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                # The LastModified is a timezone-aware datetime object
                last_modified = obj['LastModified']
                
                # Convert to YYYY-MM-DD for easy comparison
                # Using UTC date, which is fine since the migration script ran at 01:35 UTC (which is 07:05 IST on July 22)
                date_str = last_modified.strftime("%Y-%m-%d")
                
                if date_str == target_date_str:
                    matched_files.append(obj['Key'])
    
    # Sort files alphabetically for nice output
    matched_files.sort()
    
    print(f"=== FOUND {len(matched_files)} FILES UPLOADED ON JULY 22 ===")
    for f in matched_files:
        print(f)

if __name__ == "__main__":
    list_recent_s3_files()
