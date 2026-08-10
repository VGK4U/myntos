import os
import sys
import zipfile
import hashlib
import tempfile
from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_ZIP = SOURCE_DIR / "MyntReal_AWS_Deploy_Full.zip"

EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    "test_env",
    "postgres_data",
    ".next",
    ".pytest_cache",
    "__pycache__",
    "test-results",
    "playwright-report",
    ".replit_integration_files",
    "artifacts",
    "scratch",
    "media_backup",
    "mobile",
    "tests",
    "docs",
    ".agents",
    ".canvas",
    "pgsql",
    "pgsql16"
}

EXCLUDE_FILES = {
    ".DS_Store",
    "mlm_app.db",
    "nohup.out",
    "git_push.log",
    "git_res.txt",
    "servers.log",
    "node.log",
    "uvicorn.log",
    "MyntReal_AWS_Deploy_Full.zip",
    "MyntReal_AWS_Deploy.zip",
    "MyntReal_AWS_Deploy_Slim.zip",
    "deployment.zip",
    "modified_changes.zip",
    "modified_files.zip"
}

def should_exclude(rel_path: Path) -> bool:
    parts = rel_path.parts
    for part in parts:
        if part in EXCLUDE_DIRS or part == "__pycache__":
            return True
    
    if rel_path.name in EXCLUDE_FILES:
        return True
    
    if rel_path.suffix.lower() in [".zip", ".sql", ".dump"]:
        return True
        
    return False

def build_zip():
    print(f"📦 Packaging AWS Deploy Zip from: {SOURCE_DIR}")
    
    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()
        
    file_count = 0
    total_uncompressed = 0
    
    with zipfile.ZipFile(OUTPUT_ZIP, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(SOURCE_DIR):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and d != "__pycache__"]
            
            for f in files:
                abs_file = Path(root) / f
                rel_path = abs_file.relative_to(SOURCE_DIR)
                
                if should_exclude(rel_path):
                    continue
                
                try:
                    zf.write(abs_file, arcname=str(rel_path))
                    file_count += 1
                    total_uncompressed += abs_file.stat().st_size
                except Exception as err:
                    print(f"Warning skipping file {rel_path}: {err}")
                    
        # Dynamically inject the .env variables securely into the zip without writing to disk
        env_path = SOURCE_DIR / '.env'
        if not env_path.exists():
            env_path = SOURCE_DIR / 'backend' / '.env'
            
        if env_path.exists():
            env_config_lines = ["option_settings:", "  aws:elasticbeanstalk:application:environment:"]
            with open(env_path, 'r', encoding='utf-8') as env_file:
                for line in env_file:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, val = line.split('=', 1)
                        # Remove surrounding quotes if present
                        val = val.strip().strip('\'"')
                        env_config_lines.append(f"    {key.strip()}: \"{val}\"")
            
            env_config_content = '\n'.join(env_config_lines) + '\n'
            zf.writestr('.ebextensions/01_env.config', env_config_content)
            print(f"✅ Successfully injected secure environment variables from {env_path.name} into the ZIP as .ebextensions/01_env.config")

    compressed_size = OUTPUT_ZIP.stat().st_size
    
    # Calculate SHA256
    hasher = hashlib.sha256()
    with open(OUTPUT_ZIP, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    sha256_checksum = hasher.hexdigest()

    print(f"\n✅ ZIP CREATION SUCCESSFUL!")
    print(f"📍 Location: {OUTPUT_ZIP}")
    print(f"📊 Total Files Included: {file_count}")
    print(f"📦 Compressed Size: {compressed_size / (1024*1024):.2f} MB ({compressed_size:,} bytes)")
    print(f"📂 Uncompressed Size: {total_uncompressed / (1024*1024):.2f} MB ({total_uncompressed:,} bytes)")
    print(f"🔑 SHA256 Checksum: {sha256_checksum}")

if __name__ == "__main__":
    build_zip()
