import os
import sys
import zipfile
import shutil
import hashlib
from pathlib import Path

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
        'check_imports.py', '.antigravity_deploy_lock'
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

                if file in exclude_files:
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

                if file.endswith(('.zip', '.sqlite', '.db', '.dump', '.log', '.pyc')):
                    continue
                if file.endswith('.sql') and 'backend/migrations' not in rel_str:
                    continue

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

        # Dynamically inject environment variables into .ebextensions/01_env.config
        env_path = source_dir / 'backend' / '.env'
        if not env_path.exists():
            env_path = source_dir / '.env'

        if env_path.exists():
            env_config_lines = ["option_settings:", "  aws:elasticbeanstalk:application:environment:"]
            with open(env_path, 'r', encoding='utf-8') as env_file:
                for line in env_file:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip().strip('\'"')
                        if k != "SECRET_KEY":  # Secret key set in EB console directly
                            env_config_lines.append(f"    {k}: \"{v}\"")

            env_config_content = '\n'.join(env_config_lines) + '\n'
            zf.writestr('.ebextensions/01_env.config', env_config_content)
            print(f"[SUCCESS] Injected environment variables into .ebextensions/01_env.config")

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
