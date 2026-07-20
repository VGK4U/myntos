#!/usr/bin/env python3
import requests
import sys

# Login
login_url = 'http://localhost:5000/api/auth/login'
login_data = {'username': 'BEV182364369', 'password': 'vgkadmin123'}
r = requests.post(login_url, json=login_data)

if r.status_code != 200:
    print(f"Login failed: {r.status_code}")
    sys.exit(1)

token = r.json().get('access_token')

# Get bonanza page
headers = {'Cookie': f'session_token={token}'}
page = requests.get('http://localhost:5000/vgk/bonanza-management', headers=headers)

if page.status_code != 200:
    print(f"Page request failed: {page.status_code}")
    sys.exit(1)

# Analyze the page
lines = page.text.split('\n')
print(f"Total lines: {len(lines)}")

# Show lines around 565
print(f"\n📍 Lines 560-570 (error at line 565:146):")
for i in range(559, min(570, len(lines))):
    line = lines[i]
    prefix = ">>> " if i == 564 else "    "
    print(f"{prefix}Line {i+1}: {line[:200]}")
    if i == 564 and len(line) > 145:
        print(f"         Char at pos 146: '{line[145]}' (context: ...{line[140:150]}...)")
