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
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if line.startswith('/'):
                        line = line[1:]
                    ignore_patterns.append(line)
    
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
        env_path = 'backend/.env' if os.path.exists('backend/.env') else '.env'
        if os.path.exists(env_path):
            env_config_lines = ["option_settings:", "  aws:elasticbeanstalk:application:environment:"]
            with open(env_path, 'r', encoding='utf-8') as env_file:
                for line in env_file:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, val = line.split('=', 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        env_config_lines.append(f'    {key}: "{val}"')
            
            env_config_content = '\n'.join(env_config_lines) + '\n'
            zipf.writestr('.ebextensions/01_env.config', env_config_content)
            print(f"Successfully injected secure environment variables from {env_path} into the ZIP.")
        
        health_config_content = """option_settings:
  aws:elasticbeanstalk:application:
    Application Healthcheck URL: "/health"
  aws:elasticbeanstalk:environment:process:default:
    HealthCheckPath: "/health"
    MatcherHTTPCode: "200,301,302,307"
    Port: "5000"
    Protocol: "HTTP"
    HealthCheckTimeout: "5"
    HealthCheckInterval: "15"
    HealthyThresholdCount: "2"
    UnhealthyThresholdCount: "5"
"""
        zipf.writestr('.ebextensions/02_healthcheck.config', health_config_content)
        print("Successfully injected .ebextensions/02_healthcheck.config into the ZIP.")

    print(f"Successfully created {zip_name} (Size: {os.path.getsize(zip_name) / (1024*1024):.2f} MB)")

if __name__ == '__main__':
    # Ensure pathspec is installed
    try:
        import pathspec
    except ImportError:
        import subprocess, sys
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pathspec'])
        import pathspec
    main()
