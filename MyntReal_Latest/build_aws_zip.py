import os
import zipfile

def create_zip():
    source_dir = r"C:\Desktop\VGK4U\MyntReal_Latest"
    zip_path = r"C:\Desktop\VGK4U\MyntReal_Latest_Deploy.zip"
    
    # Exclude these directories to keep the zip file size manageable (~50MB)
    exclude_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'pgsql', 'pgsql16', 'test_env', 'media_backup', 'storage', 'frontend-next', '.next', '.expo', 'android', 'ios'}
    exclude_files = {'final_production_backup.dump', 'final_replit_backup.dump'}
    
    print(f"Creating zip file at {zip_path}...")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file in exclude_files:
                    continue
                # Skip previously created zips and sql dumps to prevent recursive bloat
                if file.endswith('.zip') or file.endswith('.sql'):
                    continue
                    
                file_path = os.path.join(root, file)
                # Calculate the relative path to preserve directory structure in zip
                arcname = os.path.relpath(file_path, start=source_dir)
                zipf.write(file_path, arcname)
                
    print("Deployment zip created successfully!")

if __name__ == "__main__":
    create_zip()
