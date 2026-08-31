import os
import sys
import zipfile
import hashlib
import shutil
from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parent
TEMP_ZIP = Path("/tmp/MyntReal_AWS_Deploy.zip")
OUTPUT_ZIP = SOURCE_DIR / "MyntReal_AWS_Deploy.zip"
FULL_ZIP = SOURCE_DIR / "MyntReal_AWS_Deploy_Full.zip"
ALIAS_ZIP = SOURCE_DIR / "deployment.zip"

EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    "ENV",
    "test_env",
    "postgres_data",
    ".next",
    ".cache",
    ".pytest_cache",
    "__pycache__",
    "test-results",
    "playwright-report",
    ".replit_integration_files",
    "artifacts",
    "scratch",
    "storage",
    "uploaded_files",
    "uploads",
    "media_backup",
    "mobile",
    "tests",
    "docs",
    ".agents",
    ".canvas",
    "pgsql",
    "pgsql16",
    "frontend-next",
    "catalog"
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
    "bot.log",
    "mobile.app",
    "mobile.apk",
    "mnr-catalog.pdf",
    "mnr-catalog-web.pdf",
    "database_backup (1).sql",
    "final_production_backup.dump",
    "final_replit_backup.dump"
}

def should_exclude(rel_path: Path, abs_file: Path) -> bool:
    rel_str = str(rel_path).replace("\\", "/")
    is_compiled_mobile_asset = rel_str.startswith("frontend/public/mobile")
    
    parts = rel_path.parts
    for part in parts:
        if part == "mobile" and is_compiled_mobile_asset:
            continue
        if part in EXCLUDE_DIRS or part == "__pycache__":
            return True
            
    if rel_path.name in EXCLUDE_FILES or abs_file.name.endswith(".zip"):
        return True
        
    if "storage/" in rel_str or "uploaded_files/" in rel_str or "uploads/" in rel_str or "postgres_data/" in rel_str:
        return True
        
    if abs_file.suffix.lower() in [".zip", ".sql", ".dump", ".sqlite", ".db"]:
        return True

    if abs_file.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf"]:
        size_mb = abs_file.stat().st_size / (1024 * 1024)
        if size_mb > 0.2 and abs_file.name != "MyntReal.apk":
            return True
            
    return False

def build_zip():
    print(f"📦 Packaging DEFAULT Slim AWS Deploy Zip (< 50MB) from: {SOURCE_DIR}")
    
    if TEMP_ZIP.exists():
        TEMP_ZIP.unlink()
    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()
        
    file_count = 0
    total_uncompressed = 0
    
    with zipfile.ZipFile(TEMP_ZIP, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(SOURCE_DIR):
            dirs[:] = [
                d for d in dirs
                if (d not in EXCLUDE_DIRS or (d == "mobile" and Path(root).name == "public"))
                and d != "__pycache__"
            ]
            
            for f in files:
                abs_file = Path(root) / f
                rel_path = abs_file.relative_to(SOURCE_DIR)
                
                if should_exclude(rel_path, abs_file) or str(rel_path) == "Procfile":
                    continue
                
                try:
                    if abs_file.suffix.lower() in [".sh", ".env", ".config"] or abs_file.name in ["Dockerfile", "Procfile"]:
                        content = abs_file.read_bytes().replace(b"\r\n", b"\n")
                        zf.writestr(str(rel_path), content)
                    else:
                        zf.write(abs_file, arcname=str(rel_path))
                    file_count += 1
                    total_uncompressed += abs_file.stat().st_size
                except Exception as err:
                    print(f"Warning skipping file {rel_path}: {err}")
                    
        # 1. Inject root Procfile for AWS Elastic Beanstalk
        procfile_content = "web: gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.app.main:app\n"
        zf.writestr('Procfile', procfile_content)
        print("✅ Injected root Procfile (gunicorn + uvicorn) into ZIP")

        # 2. Inject root requirements.txt for AWS Elastic Beanstalk
        backend_req = SOURCE_DIR / 'backend' / 'requirements.txt'
        if backend_req.exists():
            zf.write(backend_req, arcname='requirements.txt')
            print("✅ Injected root requirements.txt into ZIP")

        # 3. Inject Nginx configuration (.platform/nginx/conf.d/proxy.conf) for 50MB body size
        nginx_conf = "client_max_body_size 50M;\nproxy_connect_timeout 300;\nproxy_send_timeout 300;\nproxy_read_timeout 300;\nsend_timeout 300;\n"
        zf.writestr('.platform/nginx/conf.d/proxy.conf', nginx_conf)
        print("✅ Injected .platform/nginx/conf.d/proxy.conf into ZIP")

        # 4. Dynamically inject .env variables securely into .ebextensions/01_env.config
        env_path = SOURCE_DIR / 'backend' / '.env'
        if not env_path.exists():
            env_path = SOURCE_DIR / '.env'
            
        if env_path.exists():
            env_config_lines = ["option_settings:", "  aws:elasticbeanstalk:application:environment:"]
            with open(env_path, 'r', encoding='utf-8') as env_file:
                for line in env_file:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, val = line.split('=', 1)
                        key = key.strip()
                        val = val.strip().strip('\'"')
                        # Escape internal backslashes and double quotes for YAML
                        val_escaped = val.replace('\\', '\\\\').replace('"', '\\"')
                        env_config_lines.append(f'    {key}: "{val_escaped}"')
            
            env_config_content = '\n'.join(env_config_lines) + '\n'
            zf.writestr('.ebextensions/01_env.config', env_config_content)
            print(f"✅ Successfully injected secure environment variables from {env_path.name} into ZIP as .ebextensions/01_env.config")

    # Sync output to all zip target filenames
    shutil.copyfile(TEMP_ZIP, OUTPUT_ZIP)
    shutil.copyfile(TEMP_ZIP, ALIAS_ZIP)
    shutil.copyfile(TEMP_ZIP, FULL_ZIP)

    compressed_size = OUTPUT_ZIP.stat().st_size
    
    # Calculate SHA256
    hasher = hashlib.sha256()
    with open(OUTPUT_ZIP, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    sha256_checksum = hasher.hexdigest()

    print(f"\n✅ AWS ELASTIC BEANSTALK DEPLOYMENT ZIP CREATION SUCCESSFUL!")
    print(f"📍 Primary Location: {OUTPUT_ZIP}")
    print(f"📍 Full Zip Alias:   {FULL_ZIP}")
    print(f"📍 Deployment Alias: {ALIAS_ZIP}")
    print(f"📊 Total Files Included: {file_count}")
    print(f"📦 Compressed Size: {compressed_size / (1024*1024):.2f} MB ({compressed_size:,} bytes)")
    print(f"📂 Uncompressed Size: {total_uncompressed / (1024*1024):.2f} MB ({total_uncompressed:,} bytes)")
    print(f"🔑 SHA256 Checksum: {sha256_checksum}")

if __name__ == "__main__":
    build_zip()
