import os
import zipfile
import shutil
import stat
from pathlib import Path
import tempfile

def create_zip():
    source_dir = str(Path(__file__).resolve().parent)
    root_dir = str(Path(__file__).resolve().parent.parent)
    final_zip_path = str(Path(__file__).resolve().parent / "MyntReal_AWS_Deploy.zip")
    deploy_zip_path = str(Path(__file__).resolve().parent / "deployment.zip")
    root_final_zip_path = os.path.join(root_dir, "MyntReal_AWS_Deploy.zip")
    root_deploy_zip_path = os.path.join(root_dir, "deployment.zip")
    temp_zip_path = os.path.join(tempfile.gettempdir(), "MyntReal_AWS_Deploy_temp.zip")
    
    # Exclude non-production directory names anywhere in the tree
    exclude_dir_names = {
        '.git', 'node_modules', '__pycache__', '.pytest_cache', '.venv', 'venv', 'ENV', 'test_env',
        'pgsql', 'pgsql16', 'postgres_data', 'media_backup', 'storage',
        'frontend-next', '.next', '.expo', 'android', 'ios', 'artifacts', '.agents',
        '.canvas', '.cache', 'playwright-report', 'test-results', 'tmp_ai_audio', 'scratch',
        '.ai_uploads', '.ai_backups', 'migration_context', 'tests', 'docs', 'uploads',
        'uploaded_files', 'reports'
    }
    exclude_files = {
        'final_production_backup.dump', 'final_replit_backup.dump', '.DS_Store',
        'zivBAVqt', 'zifsiIO0', 'database_backup (1).sql', 'production_menu_sync.sql',
        'mnr-catalog.pdf', '-r', 'Secrets', 'View', 'main', 'shell', 'tools',
        'scratch_ai.py', 'fix_ts.py', 'fix_ts2.py', 'fix_ts3.py', 'test_mcp_chat.py',
        'test_endpoints.js', 'test_s3.py', 'test.html', 'test_invoice_alekhya.pdf',
        'test_invoice_out.pdf', 'test_results_menu_access_20251221_040248.json',
        'local_test.jpg', 'login_test.html', 'build_placeholders.py', 'build_zip_fix_yaml.py',
        'MNR_Staff_System_Reimplementation_Plan.docx', 'curl_out.txt', 'git_push.log',
        'git_res.txt', 'flake8_errors.txt', 'test_output.txt', 'node.log', 'uvicorn.log',
        'servers.log', 'nohup.out', 'fetch.err', 'fetch.out'
    }
    
    print(f"Creating clean production zip at {final_zip_path}...")
    
    if os.path.exists(temp_zip_path):
        os.remove(temp_zip_path)
        
    with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zipf:
        for root, dirs, files in os.walk(source_dir):
            rel_root = os.path.relpath(root, source_dir).replace(os.sep, '/')
            # Exclude root mobile Android/iOS project folders (mobile web app is built into frontend/public/mobile/)
            if rel_root == 'mobile' or rel_root.startswith('mobile/'):
                dirs[:] = []
                continue
                
            # In-place directory exclusion
            dirs[:] = [
                d for d in dirs 
                if d not in exclude_dir_names 
                and not (d == 'mobile' and rel_root == '.')
                and not (d.startswith('.') and d not in ['.platform', '.ebextensions'])
            ]
            
            for file in files:
                if file in exclude_files:
                    continue
                if file.endswith('.zip') or file.endswith('.sqlite') or file.endswith('.db') or file.endswith('.dump') or file.endswith('.sql') or file.endswith('.log') or file.endswith('.pyc'):
                    continue
                if file.startswith('.') and file not in ['.dockerignore', '.ebextensions', '.platform']:
                    continue
                    
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=source_dir).replace(os.sep, '/')
                
                # Exclude environment secrets and heavy storage
                if arcname in ['.env', 'backend/.env', 'frontend/.env']:
                    continue
                if any(ex in arcname for ex in ['backend/storage', 'media_backup', 'postgres_data', 'node_modules', '.next']):
                    continue
                    
                # Normalize line endings and permissions for shell scripts / text configs
                if arcname.endswith('.sh') or arcname in ['Procfile', 'Dockerfile', '.dockerignore'] or arcname.startswith('.ebextensions/') or arcname.startswith('.platform/'):
                    with open(file_path, 'rb') as f:
                        raw_data = f.read()
                    norm_data = raw_data.replace(b'\r\n', b'\n')
                    zinfo = zipfile.ZipInfo(arcname)
                    zinfo.compress_type = zipfile.ZIP_DEFLATED
                    zinfo.external_attr = 0o100755 << 16 if arcname.endswith('.sh') else 0o100644 << 16
                    zipf.writestr(zinfo, norm_data)
                else:
                    zipf.write(file_path, arcname)
                
    # Cleanly remove old destination files so macOS Finder assigns fresh creation/added dates
    for target in [final_zip_path, deploy_zip_path, str(Path(__file__).resolve().parent / "MyntReal_AWS_Deploy_Full.zip"), root_final_zip_path, root_deploy_zip_path]:
        if os.path.exists(target):
            try:
                os.remove(target)
            except Exception:
                pass
                
    shutil.copyfile(temp_zip_path, final_zip_path)
    shutil.copyfile(temp_zip_path, deploy_zip_path)
    shutil.copyfile(temp_zip_path, str(Path(__file__).resolve().parent / "MyntReal_AWS_Deploy_Full.zip"))
    if os.path.exists(root_dir) and os.path.isdir(root_dir):
        shutil.copyfile(temp_zip_path, root_final_zip_path)
        shutil.copyfile(temp_zip_path, root_deploy_zip_path)
    if os.path.exists(temp_zip_path):
        os.remove(temp_zip_path)
    print(f"Deployment zips updated successfully: {final_zip_path}, {root_final_zip_path}")

if __name__ == "__main__":
    create_zip()
