import os
import boto3
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env")

BUCKET_NAME = os.environ.get("AWS_S3_BUCKET_NAME")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-2")

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

def upload_file(local_path, s3_key):
    try:
        s3_client.upload_file(local_path, BUCKET_NAME, s3_key)
        return (True, s3_key, None)
    except Exception as e:
        return (False, s3_key, str(e))

def bulk_upload(source_dir):
    print(f"Starting upload from {source_dir} to bucket {BUCKET_NAME}...")
    
    # Gather all files
    files_to_upload = []
    for root, _, files in os.walk(source_dir):
        for file in files:
            local_path = os.path.join(root, file)
            # Calculate relative path to use as S3 key
            s3_key = os.path.relpath(local_path, source_dir)
            # Convert Windows backslashes to forward slashes for S3
            s3_key = s3_key.replace('\\\\', '/')
            files_to_upload.append((local_path, s3_key))
    
    total_files = len(files_to_upload)
    print(f"Found {total_files} files to upload.")
    
    success_count = 0
    fail_count = 0
    start_time = time.time()
    
    # Use max 20 threads for faster parallel uploading
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(upload_file, local, key): key for local, key in files_to_upload}
        
        for future in as_completed(futures):
            success, key, error = future.result()
            if success:
                success_count += 1
                if success_count % 100 == 0 or success_count == total_files:
                    print(f"Progress: {success_count}/{total_files} uploaded successfully...")
            else:
                fail_count += 1
                print(f"Failed to upload {key}: {error}")

    elapsed_time = time.time() - start_time
    print(f"\\nUpload Complete!")
    print(f"Successfully uploaded: {success_count}")
    print(f"Failed uploads: {fail_count}")
    print(f"Time taken: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    SOURCE_DIR = r"C:\Desktop\VGK4U\MyntReal_Latest\media_backup"
    bulk_upload(SOURCE_DIR)
