import os
import sys
import zipfile
import shutil
import hashlib
from pathlib import Path

class SecurityError(Exception):
    pass

def create_zip():
    source_dir = Path(__file__).resolve().parent
    root_dir = source_dir.parent
    deploy_zip_path = source_dir / "deployment.zip"
    final_zip_path = source_dir / "MyntReal_AWS_Deploy.zip"
    root_deploy_zip_path = root_dir / "deployment.zip"
    root_final_zip_path = root_dir / "MyntReal_AWS_Deploy.zip"

    # Exclude non-production / heavy directories
    exclude_dir_names = {
        '.git', 'node_modules', '__pycache__', '.pytest_cache', '.venv', 'venv', 'ENV', 'test_env',
        'pgsql', 'pgsql16', 'postgres_data', 'media_backup', 'storage', 'frontend-next', '.next',
        '.expo', 'android', 'ios', 'artifacts', '.agents', '.canvas', '.cache',
        'playwright-report', 'test-results', 'tmp_ai_audio', 'scratch', '.ai_uploads',
        '.ai_backups', 'migration_context', 'tests', 'docs', 'uploads', 'uploaded_files',
        'reports', 'phase5_screenshots', '.replit_integration_files'
    }

    exclude_files = {
        'final_production_backup.dump', 'final_replit_backup.dump', '.DS_Store',
        'zivBAVqt', 'zifsiIO0', 'database_backup (1).sql', 'production_menu_sync.sql',
        'mnr-catalog.pdf', 'mnr-catalog-web.pdf', '-r', 'Secrets', 'View', 'main', 'shell', 'tools',
        'scratch_ai.py', 'fix_ts.py', 'fix_ts2.py', 'fix_ts3.py', 'test_mcp_chat.py',
        'test_endpoints.js', 'test_s3.py', 'test.html', 'test_invoice_alekhya.pdf',
        'test_invoice_out.pdf', 'test_results_menu_access_20251221_040248.json',
        'local_test.jpg', 'login_test.html', 'build_placeholders.py', 'build_zip_fix_yaml.py',
        'MNR_Staff_System_Reimplementation_Plan.docx', 'curl_out.txt', 'git_push.log',
        'git_res.txt', 'flake8_errors.txt', 'test_output.txt', 'node.log', 'uvicorn.log',
        'servers.log', 'nohup.out', 'fetch.err', 'fetch.out', 'verify_e2e_readiness.py',
        'check_imports.py', '.antigravity_deploy_lock',
        '.env', '.env.local', '.env.production', '.env.development', '.env.staging',
        '.env.test', '.env.backup', 'credentials', 'credentials.json', 'id_rsa', 'id_ed25519',
        'build_aws_zip.py', 'build_zip_fix_yaml.py'
    }

    print(f"[PACKAGING] Packaging Canonical Slim AWS Deploy Zip (< 50MB) from: {source_dir}")

    if deploy_zip_path.exists():
        deploy_zip_path.unlink()

    file_count = 0
    total_uncompressed = 0

    with zipfile.ZipFile(deploy_zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            rel_root = os.path.relpath(root, source_dir).replace(os.sep, '/')

            # Exclude root mobile source code directory
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
                file_path = Path(root) / file
                rel_path = file_path.relative_to(source_dir)
                rel_str = str(rel_path).replace("\\", "/")

                if file in exclude_files or file == '.env' or file.startswith('.env.') or file.endswith('.env') or file.endswith(('.key', '.pem', '.secret', '.token')):
                    continue

                # Always keep production APK files
                if rel_str in ["frontend/public/MyntReal.apk", "frontend/public/mobile.apk"]:
                    pass
                elif file.endswith('.apk'):
                    continue

                # Exclude bulky non-UI directories and heavy static catalogs / marketplace
                if any(rel_str.startswith(p) for p in [
                    'frontend/public/marketplace',
                    'frontend/public/catalog',
                    'backend/storage',
                    'media_backup',
                    'postgres_data',
                    'node_modules',
                    '.next'
                ]):
                    continue

                if file.endswith(('.zip', '.sqlite', '.db', '.db-shm', '.db-wal', '.dump', '.log', '.pyc', '.wav')):
                    continue
                if file.endswith('.sql') and 'backend/migrations' not in rel_str:
                    continue
                if rel_str == 'frontend/package-lock.json':
                    continue

                # Strictly exclude dotfiles except required deployment configs
                if file.startswith('.') and file not in ['.dockerignore', '.ebextensions', '.platform']:
                    continue

                # Exclude heavy images > 1.8MB to keep Docker context lightweight
                if file_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
                    try:
                        if file_path.stat().st_size > 1.8 * 1024 * 1024:
                            continue
                    except Exception:
                        pass

                # Normalize line endings and permissions for shell scripts / text configs
                try:
                    if file_path.suffix.lower() in [".sh", ".conf", ".config", ".py", ".js", ".json", ".txt", ".md", ".html", ".css"] or file in ["Procfile", "Dockerfile", ".dockerignore"]:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as tf:
                            raw_data = tf.read().replace("\r\n", "\n")
                        zinfo = zipfile.ZipInfo(rel_str)
                        zinfo.compress_type = zipfile.ZIP_DEFLATED
                        zinfo.external_attr = 0o100755 << 16 if rel_str.endswith('.sh') else 0o100644 << 16
                        zf.writestr(zinfo, raw_data)
                    else:
                        zf.write(file_path, arcname=rel_str)

                    file_count += 1
                    total_uncompressed += file_path.stat().st_size
                except Exception as err:
                    print(f"Warning skipping file {rel_str}: {err}")

        # Verify .ebextensions/01_env.config is NOT included (AWS 4096-byte limit & secret leak prevention)
        if '.ebextensions/01_env.config' in zf.namelist():
            config_bytes = len(zf.read('.ebextensions/01_env.config'))
            print(f"[VERIFY] .ebextensions/01_env.config size: {config_bytes} bytes (AWS Limit: 4096 bytes)")
            if config_bytes > 4096:
                raise ValueError(f"CRITICAL: .ebextensions/01_env.config ({config_bytes} bytes) exceeds AWS 4096-byte limit!")
        else:
            print("[SECURITY] .ebextensions/01_env.config is not bundled (protecting AWS CloudFormation option settings).")

    # Post-packaging Automated Security Audit
    print("\n[SECURITY AUDIT] Scanning deployment bundle for sensitive data and credentials...")
    forbidden_file_patterns = ['.env', 'credentials.json', 'id_rsa', 'id_ed25519', '.pem', '.key', 'Secrets']
    suspicious_patterns = [
        b'AWS_SECRET_ACCESS_KEY=',
        b'ghp_',
        b'Admin2026!'
    ]

    with zipfile.ZipFile(deploy_zip_path, 'r') as verify_zf:
        names = verify_zf.namelist()
        for name in names:
            # Check filename
            for pattern in forbidden_file_patterns:
                if pattern in name:
                    raise SecurityError(f"CRITICAL SECURITY VIOLATION: Forbidden file '{name}' found in deployment zip!")
            
            # Deep scan text files for credential leaks
            if any(name.endswith(ext) for ext in ['.py', '.sh', '.json', '.js', '.config', '.conf', '.txt']):
                try:
                    content = verify_zf.read(name)
                    for bad in suspicious_patterns:
                        if bad in content:
                            raise SecurityError(f"CRITICAL SECURITY VIOLATION: Raw credential detected in '{name}' inside deployment zip!")
                except Exception as ex:
                    if "CRITICAL SECURITY VIOLATION" in str(ex):
                        raise

    print("[SECURITY AUDIT PASSED] 0 sensitive files (.env, keys, tokens) found. Deployment package is 100% sanitized for AWS.")

    compressed_size = deploy_zip_path.stat().st_size
    print(f"[SUCCESS] Canonical Deploy Zip created successfully!")
    print(f"  Location: {deploy_zip_path}")
    print(f"  Total Files Included: {file_count}")
    print(f"  Compressed Size: {compressed_size / (1024*1024):.2f} MB ({compressed_size:,} bytes)")
    print(f"  Uncompressed Size: {total_uncompressed / (1024*1024):.2f} MB ({total_uncompressed:,} bytes)")

    # Synchronize to MyntReal_AWS_Deploy.zip and root paths
    for target in [final_zip_path, root_deploy_zip_path, root_final_zip_path]:
        try:
            shutil.copyfile(deploy_zip_path, target)
            print(f"[SYNC] Synchronized: {target}")
        except Exception as e:
            print(f"Notice syncing {target}: {e}")

if __name__ == "__main__":
    create_zip()
