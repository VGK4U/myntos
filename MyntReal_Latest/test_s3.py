import os
import boto3
from dotenv import load_dotenv

load_dotenv(".env")

AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
BUCKET_NAME = os.environ.get("AWS_S3_BUCKET_NAME")

print(f"Testing AWS Keys...")

try:
    sts = boto3.client('sts', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name='us-east-1')
    identity = sts.get_caller_identity()
    print(f"✅ Keys are valid! Logged in as: {identity['Arn']}")
except Exception as e:
    print(f"❌ Keys are INVALID: {e}")
    exit(1)

print(f"\nChecking Bucket Region for '{BUCKET_NAME}'...")
try:
    s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name='us-east-1')
    location = s3.get_bucket_location(Bucket=BUCKET_NAME)
    region = location.get('LocationConstraint')
    if region is None:
        region = 'us-east-1'
    print(f"✅ Bucket Region is: {region}")
except Exception as e:
    print(f"❌ Failed to get bucket region: {e}")
