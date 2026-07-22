import os
import boto3
from dotenv import load_dotenv

def test_s3_connection():
    # Load environment variables from .env file
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(env_path)

    bucket_name = os.environ.get("AWS_S3_BUCKET_NAME")
    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    region = os.environ.get("AWS_REGION")

    print(f"Testing connection to AWS S3 Bucket: '{bucket_name}' in region '{region}'...")
    
    try:
        # Initialize boto3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        
        # Test connection by listing up to 5 objects in the bucket
        response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
        
        if 'Contents' in response:
            print("\n[SUCCESS] Successfully connected to the S3 bucket!")
            print(f"Found {len(response['Contents'])} files (showing up to 5):")
            for obj in response['Contents']:
                print(f"  - {obj['Key']} (Size: {obj['Size']} bytes, Last Modified: {obj['LastModified']})")
        else:
            print("\n[SUCCESS] Connected to the S3 bucket successfully, but the bucket is currently empty.")
            
    except Exception as e:
        print(f"\n[ERROR] Failed to connect to S3 Bucket. Details:")
        print(str(e))

if __name__ == "__main__":
    test_s3_connection()
