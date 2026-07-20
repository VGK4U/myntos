#!/usr/bin/env python3
"""
Add debug logging to KYC management route
"""

# Read the file
with open('static-server.js', 'r') as f:
    content = f.read()

# Find and replace the KYC route with debug logging
old_route = """  } else if (url.startsWith('/admin/kyc-management')) {
    if (!isLoggedIn || !hasAdminPrivileges(sessionToken)) {"""

new_route = """  } else if (url.startsWith('/admin/kyc-management')) {
    console.log('🔍 KYC Management route HIT! URL:', url);
    if (!isLoggedIn || !hasAdminPrivileges(sessionToken)) {"""

if old_route in content:
    content = content.replace(old_route, new_route)
    print("✅ Debug logging added to KYC route!")
else:
    print("❌ KYC route not found")

# Write the file
with open('static-server.js', 'w') as f:
    f.write(content)

print("✅ File written!")
