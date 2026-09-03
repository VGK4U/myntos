import os
import zipfile
import shutil
from pathlib import Path

def create_zip():
    source_dir = str(Path(__file__).resolve().parent)
    final_zip_path = str(Path(__file__).resolve().parent / "MyntReal_AWS_Deploy.zip")
    temp_zip_path = "/tmp/MyntReal_AWS_Deploy_temp.zip"
    
    # Exclude non-production directory names anywhere in the tree
    exclude_dir_names = {
        '.git', 'node_modules', '__pycache__', '.pytest_cache', '.venv', 'venv', 'ENV', 'test_env',
        'pgsql', 'pgsql16', 'postgres_data', 'media_backup', 'storage',
        'frontend-next', '.next', '.expo', 'android', 'ios', 'artifacts', '.agents',
        '.canvas', '.cache', 'playwright-report', 'test-results', 'tmp_ai_audio', 'scratch',
        '.ai_uploads', '.ai_backups', 'migration_context', 'tests', 'docs'
    }
    exclude_files = {
        'final_production_backup.dump', 'final_replit_backup.dump', '.DS_Store',
        'zivBAVqt', 'zifsiIO0', 'database_backup (1).sql', 'production_menu_sync.sql',
        'mnr-catalog.pdf'
    }
    
    print(f"Creating clean production zip at {final_zip_path}...")
    
    if os.path.exists(temp_zip_path):
        os.remove(temp_zip_path)
        
    with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zipf:
        for root, dirs, files in os.walk(source_dir):
            rel_root = os.path.relpath(root, source_dir).replace(os.sep, '/')
            # Exclude root mobile Android project
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
                if file.endswith('.zip') or file.endswith('.sqlite') or file.endswith('.db') or file.endswith('.dump') or file.endswith('.sql'):
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
                    
                zipf.write(file_path, arcname)
                
    shutil.move(temp_zip_path, final_zip_path)
    print("Deployment zip created successfully!")

if __name__ == "__main__":
    create_zip()
