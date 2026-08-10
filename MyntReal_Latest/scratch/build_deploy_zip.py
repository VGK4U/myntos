import os
import sys
import zipfile
import hashlib
import tempfile
from pathlib import Path

SOURCE_DIR = Path("/Users/viswanathkari/Documents/Mynt OS/MyntReal_Latest").resolve()
OUTPUT_ZIP = Path("/Users/viswanathkari/Documents/Mynt OS/MyntReal_AWS_Deploy_Full.zip").resolve()

# Free up disk space by removing any old temporary zips
OLD_ZIPS = [
    Path("/Users/viswanathkari/Documents/Mynt OS/MyntReal_AWS_Deploy_Slim.zip"),
    Path("/Users/viswanathkari/Documents/Mynt OS/MyntReal_Production_Release_20260809.zip"),
]

for old_z in OLD_ZIPS:
    if old_z.exists():
        try:
            old_z.unlink()
            print(f"🗑️ Cleaned up old build artifact: {old_z.name}")
        except Exception as e:
            print(f"Failed to remove {old_z}: {e}")

# Aligning exclusions strictly with .dockerignore and production deployment standards
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
    ".canvas"
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
    
    if rel_path.suffix.lower() == ".zip":
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

    # Verification: Extract and inspect
    print("\n🔍 Extracting and verifying ZIP contents...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        with zipfile.ZipFile(OUTPUT_ZIP, 'r') as zf_extract:
            zf_extract.extractall(tmp_path)
            extracted_files = set(zf_extract.namelist())
            
        required_storage_files = [
            "backend/app/services/s3_storage.py",
            "backend/app/services/object_storage.py",
            "backend/app/services/universal_upload_service.py"
        ]
        
        for req_f in required_storage_files:
            if req_f in extracted_files:
                print(f"  ✅ Required file present: {req_f}")
            else:
                print(f"  ❌ CRITICAL ERROR: Missing file {req_f}")
                sys.exit(1)
                
        # Test imports from extracted ZIP context
        sys.path.insert(0, str(tmp_path / "backend"))
        os.environ["DATABASE_URL"] = "sqlite:///./mlm_app.db"
        
        try:
            from app.services.s3_storage import s3_storage_service
            print("  ✅ S3_STORAGE_IMPORT_OK (Extracted Context)")
            from app.services.universal_upload_service import UniversalUploadService
            print("  ✅ UNIVERSAL_UPLOAD_IMPORT_OK (Extracted Context)")
            from app.services.object_storage import ObjectStorageService
            print("  ✅ OBJECT_STORAGE_IMPORT_OK (Extracted Context)")
            from app.main import app
            print("  ✅ APP_IMPORT_OK (Extracted Context)")
        except Exception as e:
            print(f"  ❌ Import error in extracted context: {e}")
            sys.exit(1)

if __name__ == "__main__":
    build_zip()
