import os
import zipfile

from pathlib import Path

source_dir = str(Path(__file__).resolve().parent)
output_zip = str(Path(__file__).resolve().parent / 'MyntReal_AWS_Deploy.zip')
old_zip = str(Path(__file__).resolve().parent / 'deployment.zip')
env_file_path = str(Path(__file__).resolve().parent / 'backend' / '.env')

# Minimal exclusions to ensure we don't accidentally remove anything the user needs.
exclusions = [
    '.git', '.agents', 'artifacts', 'node_modules', '__pycache__', 
    '.pytest_cache', 'venv', 'ENV', 'test_env', 'media_backup',
    '.canvas', '.next', '.cache', 'playwright-report', 'test-results',
    'pgsql', 'pgsql16', 'postgres_data', 'mobile', 'tests', 'docs'
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

# 2. Extract old .ebextensions/01_env.config as plain text
eb_content = None
with zipfile.ZipFile(old_zip, 'r') as z_old:
    if '.ebextensions/01_env.config' in z_old.namelist():
        eb_content = z_old.read('.ebextensions/01_env.config').decode('utf-8')

if eb_content:
    # 3. Inject missing keys manually by appending lines (preserving quotes)
    keys_to_inject = ['GEMINI_API_KEY', 'META_APP_ID', 'META_AD_ACCOUNT_ID', 'META_APP_SECRET', 'META_SYSTEM_USER_TOKEN']
    
    # Ensure the file ends with a newline before appending
    if not eb_content.endswith('\n'):
        eb_content += '\n'
        
    for key in keys_to_inject:
        if key in local_env:
            val = local_env[key]
            # Crucial: Use double quotes to prevent AWS YAML parser from crashing on special characters
            eb_content += f'    {key}: "{val}"\n'
            print(f'Injected {key} into ebextensions config.')
            
    new_eb_content = eb_content
else:
    print('WARNING: Could not load old .ebextensions config!')
    new_eb_content = None

print(f'Building {output_zip} (Fixing YAML formatting issues)...')

# 4. Build final zip
with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if d not in exclusions]
        
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, source_dir).replace(os.sep, '/')
            
            # Skip massive files that shouldn't be in the zip (zips, dumps, dbs)
            if file.endswith('.zip') or file.endswith('.sqlite') or file.endswith('.db') or file.endswith('.dump') or file == 'database_backup (1).sql':
                continue
                
            if rel_path in env_files_to_exclude or file == '.env':
                continue
                
            if rel_path in scripts_to_fix:
                with open(file_path, 'rb') as f:
                    content = f.read()
                content = content.replace(b'\r\n', b'\n')
                z.writestr(rel_path, content)
            else:
                z.write(file_path, rel_path)
                
    # 5. Add updated .ebextensions config
    if new_eb_content:
        z.writestr('.ebextensions/01_env.config', new_eb_content.encode('utf-8'))
        print('Added updated .ebextensions/01_env.config to zip.')

print('Final zip created successfully!')
