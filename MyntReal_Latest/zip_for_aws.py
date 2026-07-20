import os
import zipfile
import pathspec

def main():
    root_dir = os.path.abspath('.')
    zip_name = 'MyntReal_AWS_Deploy.zip'
    
    if os.path.exists(zip_name):
        os.remove(zip_name)
    
    # Read .dockerignore
    ignore_patterns = []
    if os.path.exists('.dockerignore'):
        with open('.dockerignore', 'r') as f:
            ignore_patterns = f.read().splitlines()
    
    # Add zip file itself to ignore
    ignore_patterns.append(zip_name)
    ignore_patterns.append('zip_for_aws.py')
    
    spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, ignore_patterns)
    
    print(f"Creating {zip_name}...")
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(root_dir):
            # Prune directories
            dirs[:] = [d for d in dirs if not spec.match_file(os.path.relpath(os.path.join(root, d), root_dir))]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, root_dir)
                if not spec.match_file(rel_path):
                    zipf.write(file_path, rel_path)
                    
        # Dynamically inject the .env variables securely into the zip without writing to disk
        if os.path.exists('.env'):
            env_config_lines = ["option_settings:", "  aws:elasticbeanstalk:application:environment:"]
            with open('.env', 'r', encoding='utf-8') as env_file:
                for line in env_file:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, val = line.split('=', 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        env_config_lines.append(f'    {key}: "{val}"')
            
            env_config_content = '\n'.join(env_config_lines) + '\n'
            zipf.writestr('.ebextensions/01_env.config', env_config_content)
            print("Successfully injected secure environment variables into the ZIP.")

    print(f"Successfully created {zip_name} (Size: {os.path.getsize(zip_name) / (1024*1024):.2f} MB)")

if __name__ == '__main__':
    # Ensure pathspec is installed
    try:
        import pathspec
    except ImportError:
        import subprocess
        subprocess.check_call(['python', '-m', 'pip', 'install', 'pathspec'])
        import pathspec
    main()
