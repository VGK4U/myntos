import os
import zipfile
import yaml

source_dir = 'C:/Desktop/VGK4U/MyntReal_Latest'
output_zip_temp = 'C:/Desktop/VGK4U/MyntReal_Latest/temp_deploy.zip'
old_zip = 'C:/Desktop/VGK4U/MyntReal_Latest/MyntReal_AWS_Deploy.zip'
env_file_path = 'C:/Desktop/VGK4U/MyntReal_Latest/backend/.env'

# Minimal exclusions to ensure we don't accidentally remove anything the user needs.
# Excluding git, node_modules, pycache, venv, and large PGSQL local databases.
exclusions = [
    '.git', '.agents', 'artifacts', 'node_modules', '__pycache__', 
    '.pytest_cache', 'venv', 'ENV', 'test_env', 'media_backup',
    '.canvas', '.next', '.cache', 'playwright-report', 'test-results',
    'pgsql', 'pgsql16', 'postgres_data', 'mobile', 'tests', 'docs',
    'frontend-next', 'uploads', 'uploaded_files'
]

env_files_to_exclude = ['.env', 'backend/.env', 'frontend/.env']
scripts_to_fix = ['start.sh', 'build.sh', 'check_deployment.sh', 'audit_storage_structure.sh']

# 1. Read environment variables from local .env
local_env = {}
if os.path.exists(env_file_path):
    with open(env_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                local_env[key] = val

# 2. Extract and parse old .ebextensions/01_env.config
eb_yaml = None
with zipfile.ZipFile(old_zip, 'r') as z_old:
    if '.ebextensions/01_env.config' in z_old.namelist():
        eb_content = z_old.read('.ebextensions/01_env.config').decode('utf-8')
        eb_yaml = yaml.safe_load(eb_content)

if eb_yaml:
    env_section = eb_yaml.get('option_settings', {}).get('aws:elasticbeanstalk:application:environment', {})
    
    # 3. Inject missing keys
    keys_to_inject = ['GEMINI_API_KEY', 'META_APP_ID', 'META_AD_ACCOUNT_ID', 'META_APP_SECRET', 'META_SYSTEM_USER_TOKEN']
    for key in keys_to_inject:
        if key in local_env:
            env_section[key] = local_env[key]
            print(f'Injected {key} into ebextensions config.')
            
    # Explicitly inject the 4 core variables required for production hardening
    env_section['ENVIRONMENT'] = 'production'
    env_section['AWS_S3_BUCKET_NAME'] = 'myntreal-media-vault'
    env_section['AWS_REGION'] = 'ap-south-2'
    env_section['SECRET_KEY'] = 'fuBL-l737--J8d88tFMlcOE5g94Mj2L33sy0gcFLJKg'
    print('Injected ENVIRONMENT, AWS_S3_BUCKET_NAME, AWS_REGION, and SECRET_KEY explicitly.')
            
    eb_yaml['option_settings']['aws:elasticbeanstalk:application:environment'] = env_section
    new_eb_content = yaml.dump(eb_yaml, default_flow_style=False, default_style='"')
else:
    print('WARNING: Could not load old .ebextensions config!')
    new_eb_content = None

print(f'Building temporary zip (Including ALL original needed files, no over-optimizations)...')

# 4. Build final zip
with zipfile.ZipFile(output_zip_temp, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(source_dir):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in exclusions]
        
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, source_dir).replace(os.sep, '/')
            
            # Skip massive files that shouldn't be in the zip (zips, dumps, dbs)
            if file.endswith('.zip') or file.endswith('.sqlite') or file.endswith('.db') or file.endswith('.dump') or file == 'database_backup (1).sql':
                continue
                
            # Skip .env files
            if rel_path in env_files_to_exclude or file == '.env':
                continue
                
            # Read and process file
            if rel_path in scripts_to_fix:
                with open(file_path, 'rb') as f:
                    content = f.read()
                # Fix CRLF to LF
                content = content.replace(b'\r\n', b'\n')
                z.writestr(rel_path, content)
            else:
                z.write(file_path, rel_path)
                
    # 5. Add updated .ebextensions config
    if new_eb_content:
        z.writestr('.ebextensions/01_env.config', new_eb_content.encode('utf-8'))
        print('Added updated .ebextensions/01_env.config to zip.')

print('Final un-optimized (full) zip created successfully!')

# Replace the original file with the new one
import shutil

try:
    if os.path.exists(old_zip):
        os.remove(old_zip)
    os.rename(output_zip_temp, old_zip)
    print(f'Successfully updated {old_zip}')
    
    # Clean up messy old zip files as requested by the user
    messy_zips = [
        'MyntReal_AWS_Deploy_Final.zip',
        'MyntReal_AWS_Deploy_Full.zip',
        'MyntReal_AWS_Deploy_Ready.zip',
        'MyntReal_Deploy.zip'
    ]
    for messy in messy_zips:
        path = os.path.join(source_dir, messy)
        if os.path.exists(path):
            os.remove(path)
            print(f'Cleaned up old messy zip: {messy}')
            
except Exception as e:
    print(f'Error moving zip or cleaning up: {e}')
