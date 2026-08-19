import os

for root, _, files in os.walk('frontend-next/app/staff/mnr-user'):
    for file in files:
        if file.endswith('.tsx'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content.replace('{Title}', '"Data"').replace('{Title.toLowerCase()}', '"data"').replace('Title.toLowerCase()', '"data"').replace('{Title ', '{"Data" ')
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)

try:
    superadmin_path = 'frontend-next/app/superadmin/dashboard/page.tsx'
    with open(superadmin_path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace('<Trophy', '<Activity')
    with open(superadmin_path, 'w', encoding='utf-8') as f:
        f.write(content)
except Exception: pass
