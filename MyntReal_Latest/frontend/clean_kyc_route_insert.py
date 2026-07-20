#!/usr/bin/env python3
"""
Cleanly insert KYC route by finding /admin/users and adding KYC right after
"""
import re

# Read the file
with open('static-server.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the exact /admin/users block
users_pattern = r"(  \} else if \(url\.startsWith\('/admin/users'\)\) \{.*?return;)"

# Match to find the block
match = re.search(users_pattern, content, re.DOTALL)

if match:
    users_block = match.group(1)
    
    # Create KYC block by copying and modifying
    kyc_block = users_block.replace('/admin/users', '/admin/kyc-management')
    kyc_block = kyc_block.replace('admin_users.html', 'admin_kyc_management.html')
    
    # Insert KYC block right after users block
    insertion_point = match.end()
    content = content[:insertion_point] + "\n    \n" + kyc_block + content[insertion_point:]
    
    print("✅ KYC route inserted after /admin/users!")
    
    # Write the file
    with open('static-server.js', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ File written!")
else:
    print("❌ Could not find /admin/users route")
