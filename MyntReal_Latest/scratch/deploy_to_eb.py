import os
import sys
import time
import boto3
import dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'backend', '.env')
if not os.path.exists(dotenv_path):
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
dotenv.load_dotenv(dotenv_path)
key = os.environ.get('AWS_ACCESS_KEY_ID')
secret = os.environ.get('AWS_SECRET_ACCESS_KEY')
region = os.environ.get('AWS_REGION', 'ap-south-2')

from botocore.config import Config
from boto3.s3.transfer import TransferConfig
import threading

boto_config = Config(
    connect_timeout=180,
    read_timeout=180,
    retries={'max_attempts': 10, 'mode': 'standard'}
)
session = boto3.Session(aws_access_key_id=key, aws_secret_access_key=secret, region_name=region)
s3 = session.client('s3', config=boto_config)
eb = session.client('elasticbeanstalk', config=boto_config)

APP_NAME = 'vgk4u'
ENV_NAME = 'Vgk4u-env'
S3_BUCKET = 'elasticbeanstalk-ap-south-2-251714435676'
TIMESTAMP = int(time.time() * 1000)
VERSION_LABEL = f'v2.4.42-dedup-group-dispatch-{TIMESTAMP}'
S3_KEY = f'deployments/{VERSION_LABEL}.zip'
ZIP_PATH = os.path.join(os.path.dirname(__file__), '..', 'deployment.zip')

if not os.path.exists(ZIP_PATH):
    print(f"Error: {ZIP_PATH} not found.")
    sys.exit(1)

# DC Protocol: Always synchronize database schema prior to deployment version switch
print("Running pre-deployment database schema synchronization...")
os.environ['ALLOW_PROD_DB_ACCESS'] = '1'
prod_db_url = os.environ.get('PROD_DATABASE_URL')
if prod_db_url:
    os.environ['DATABASE_URL'] = prod_db_url

try:
    backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    from scripts.run_schema_migrations import run_migrations
    run_migrations()
    print("✅ Pre-deployment database migrations successfully synchronized.")

    try:
        from alembic.config import Config as AlembicConfig
        from alembic import command
        alembic_cfg = AlembicConfig(os.path.join(os.path.dirname(__file__), '..', 'alembic.ini'))
        if prod_db_url:
            alembic_cfg.set_main_option("sqlalchemy.url", prod_db_url)
        command.upgrade(alembic_cfg, "head")
        print("✅ Alembic migrations successfully upgraded to head.")
    except Exception as alembic_err:
        print(f"ℹ️ Alembic upgrade notice (standalone runner handled schema): {alembic_err}")
except Exception as mig_err:
    print(f"❌ CRITICAL PRE-DEPLOYMENT MIGRATION FAILURE: {mig_err}")
    print("🛑 DEPLOYMENT ABORTED: Production database schema cannot be verified or migrated.")
    sys.exit(1)

total_size = os.path.getsize(ZIP_PATH)
print(f"Uploading {ZIP_PATH} ({total_size} bytes / {total_size / (1024*1024):.2f} MB) to s3://{S3_BUCKET}/{S3_KEY}...")

class ProgressCallback:
    def __init__(self, size):
        self.size = size
        self.uploaded = 0
        self.last_pct = 0
        self.last_time = time.time()
        self.lock = threading.Lock()

    def __call__(self, bytes_transferred):
        with self.lock:
            self.uploaded += bytes_transferred
            pct = int((self.uploaded / self.size) * 100)
            now = time.time()
            if pct >= self.last_pct + 10 or (now - self.last_time) >= 15 or self.uploaded >= self.size:
                print(f"[{now:.0f}] Uploaded {self.uploaded / (1024*1024):.1f}MB / {self.size / (1024*1024):.1f}MB ({pct}%)", flush=True)
                self.last_pct = pct
                self.last_time = now

t_config = TransferConfig(
    multipart_threshold=8 * 1024 * 1024,
    max_concurrency=2,
    multipart_chunksize=8 * 1024 * 1024,
    use_threads=True
)

for attempt in range(1, 4):
    try:
        progress = ProgressCallback(total_size)
        s3.upload_file(ZIP_PATH, S3_BUCKET, S3_KEY, Config=t_config, Callback=progress)
        print(f"✅ S3 upload complete: s3://{S3_BUCKET}/{S3_KEY}", flush=True)
        break
    except Exception as up_err:
        print(f"⚠️ Upload attempt {attempt} failed: {up_err}", flush=True)
        if attempt == 3:
            print("❌ Max S3 upload attempts reached. Aborting.")
            sys.exit(1)
        time.sleep(5)

print(f"Creating application version {VERSION_LABEL} in {APP_NAME}...")
eb.create_application_version(
    ApplicationName=APP_NAME,
    VersionLabel=VERSION_LABEL,
    SourceBundle={
        'S3Bucket': S3_BUCKET,
        'S3Key': S3_KEY
    },
    Description='MyntOS v2.4.42: Fix duplicate WhatsApp 2-hour report trigger & dispatch, advisory lock & in-memory idempotency deduplication'[:190],
    AutoCreateApplication=False
)
print("Application version created.")

print(f"Deploying {VERSION_LABEL} to environment {ENV_NAME}...")
eb.update_environment(
    EnvironmentName=ENV_NAME,
    VersionLabel=VERSION_LABEL
)
print("Deployment initiated.")

print("Monitoring deployment progress...")
for i in range(90):
    time.sleep(10)
    res = eb.describe_environments(EnvironmentNames=[ENV_NAME])
    env = res['Environments'][0]
    status = env['Status']
    health = env['Health']
    ver = env['VersionLabel']
    print(f"[{i*10}s] Status: {status} | Health: {health} | Version: {ver}")
    if status == 'Ready':
        if ver == VERSION_LABEL and health in ('Green', 'Yellow'):
            print(f"\n🎉 DEPLOYMENT COMPLETE! Environment is Ready and {health} on version {ver}.")
            sys.exit(0)
        elif ver == VERSION_LABEL and health == 'Red':
            print(f"\n⚠️ Deployment finished but health is Red.")
            sys.exit(1)

print("Timed out waiting for environment stabilization.")
sys.exit(1)
