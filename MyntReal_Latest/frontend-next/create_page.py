import os

FILE_PATH = r"C:\Desktop\VGK4U\MyntReal_Latest\frontend-next\app\staff\employees\page.tsx"
os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)

CONTENT = """\"\"\"
Placeholder for Next.js page
\"\"\"
"""
with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(CONTENT)
print("File created")
