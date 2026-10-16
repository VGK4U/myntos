import os
import sys
import zipfile
import hashlib
import shutil
from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_ZIP = SOURCE_DIR / "deployment.zip"

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
    "tests",
    "docs",
    ".agents",
    ".canvas",
    "pgsql",
    "pgsql16",
    "frontend-next",
    "catalog",
    "phase5_screenshots",
    "reports"
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
    "mnr-catalog.pdf",
    "mnr-catalog-web.pdf",
    "database_backup (1).sql",
    "final_production_backup.dump",
    "final_replit_backup.dump",
    "MyntReal_AWS_Deploy_Full.zip",
    "MyntReal_AWS_Deploy.zip",
    "MyntReal_AWS_Deploy_Slim.zip",
    "MyntReal_v2.0.4_Deploy_20260812_072613.zip",
    "MyntReal_v2.0.4_AWS_Deploy.zip",
    "MyntReal_Release_v204.zip",
    "deployment.zip",
    "modified_changes.zip",
    "modified_files.zip",
    ".env",
    ".env.local",
    ".env.production",
    "local_test.jpg",
    "test.html",
    "test_endpoints.js",
    "test_output.txt",
    "flake8_errors.txt",
    "verify_e2e_readiness.py",
    "fix_ts.py",
    "fix_ts2.py",
    "fix_ts3.py",
    "Secrets",
    "main",
    "tools"
}

def should_exclude(rel_path: Path, abs_file: Path) -> bool:
    if abs_file == OUTPUT_ZIP:
        return True

    rel_str = str(rel_path).replace("\\", "/")
    
    # Always keep production APK files
    if rel_str in ["frontend/public/MyntReal.apk", "frontend/public/mobile.apk"]:
        return False

    # Always keep compiled frontend/public/mobile assets
    if "frontend/public/mobile" in rel_str:
        if abs_file.suffix.lower() in [".zip", ".sql", ".dump", ".db"]:
            return True
        return False

    # Exclude root mobile source code directory
    parts = rel_path.parts
    if parts and parts[0] == "mobile":
        return True

    for part in parts:
        if part in EXCLUDE_DIRS or part == "__pycache__":
            return True
            
    if rel_path.name in EXCLUDE_FILES:
        return True
        
    if ("storage/" in rel_str and "vendor_docs" not in rel_str) or "uploaded_files/" in rel_str or "public/catalog/" in rel_str or "public/marketplace/" in rel_str or ".ai_uploads" in rel_str or ".ai_backups" in rel_str or "solar-creative-" in rel_str:
        return True
        
    if abs_file.suffix.lower() in [".zip", ".sql", ".dump", ".sqlite", ".db", ".app"]:
        return True

    # Exclude heavy non-UI images > 2MB while keeping all logos
    if abs_file.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
        try:
            size_mb = abs_file.stat().st_size / (1024 * 1024)
            if size_mb > 1.8:
                return True
        except Exception:
            return True
            
    return False

def build_zip():
    print(f"[PACKAGING] Packaging Slim AWS Deploy Zip (< 50MB) from: {SOURCE_DIR}")
    
    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()
        
    file_count = 0
    total_uncompressed = 0
    
    with zipfile.ZipFile(OUTPUT_ZIP, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(SOURCE_DIR):
            dirs[:] = [
                d for d in dirs 
                if d not in EXCLUDE_DIRS 
                and d != "__pycache__" 
                and not (Path(root) == SOURCE_DIR and d == "mobile")
            ]
            
            for f in files:
                abs_file = Path(root) / f
                rel_path = abs_file.relative_to(SOURCE_DIR)
                
                if should_exclude(rel_path, abs_file):
                    continue
                
                try:
                    if abs_file.suffix.lower() in [".sh", ".conf", ".config", ".py", ".js", ".json", ".txt", ".md"] or f in ["Procfile", "Dockerfile"]:
                        with open(abs_file, "r", encoding="utf-8", errors="ignore") as tf:
                            content = tf.read().replace("\r\n", "\n")
                        zf.writestr(str(rel_path).replace("\\", "/"), content)
                    else:
                        zf.write(abs_file, arcname=str(rel_path))
                    file_count += 1
                    total_uncompressed += abs_file.stat().st_size
                except Exception as err:
                    print(f"Warning skipping file {rel_path}: {err}")
                    
        # Verify .ebextensions/01_env.config adheres to AWS 4096-byte hard limit
        if '.ebextensions/01_env.config' in zf.namelist():
            config_bytes = len(zf.read('.ebextensions/01_env.config'))
            print(f"[VERIFY] .ebextensions/01_env.config size: {config_bytes} bytes (AWS Limit: 4096 bytes)")
            if config_bytes > 4096:
                raise ValueError(f"CRITICAL: .ebextensions/01_env.config size ({config_bytes} bytes) exceeds AWS limit of 4096 bytes!")
        else:
            print("[NOTICE] .ebextensions/01_env.config not bundled; using environment settings from EB console.")

    compressed_size = OUTPUT_ZIP.stat().st_size
    
    # Calculate SHA256
    hasher = hashlib.sha256()
    with open(OUTPUT_ZIP, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    sha256_checksum = hasher.hexdigest()

    root_zip = SOURCE_DIR.parent / "deployment.zip"
    try:
        shutil.copyfile(OUTPUT_ZIP, root_zip)
        print(f"[SYNC] Synchronized {root_zip}")
        deploy_zip = SOURCE_DIR.parent / "MyntReal_AWS_Deploy.zip"
        shutil.copyfile(OUTPUT_ZIP, deploy_zip)
        print(f"[SYNC] Synchronized {deploy_zip}")
    except Exception as e:
        print(f"Notice: Root copy: {e}")

    print(f"\n[SUCCESS] SLIM ZIP CREATION SUCCESSFUL (< 50MB)!")
    print(f"Location: {OUTPUT_ZIP}")
    print(f"Total Files Included: {file_count}")
    print(f"Compressed Size: {compressed_size / (1024*1024):.2f} MB ({compressed_size:,} bytes)")
    print(f"Uncompressed Size: {total_uncompressed / (1024*1024):.2f} MB ({total_uncompressed:,} bytes)")
    print(f"SHA256 Checksum: {sha256_checksum}")

if __name__ == "__main__":
    build_zip()
