#!/usr/bin/env python3
"""
Fix KYC route to be more specific and avoid conflicts
"""

# Read the file
with open('static-server.js', 'r') as f:
    content = f.read()

# Old route handler
old_route = """  } else if (url.startsWith('/admin/kyc-management') || url.startsWith('/admin/kyc')) {"""

# New more specific route
new_route = """  } else if (url === '/admin/kyc-management' || url.startsWith('/admin/kyc-management?')) {"""

# Replace
if old_route in content:
    content = content.replace(old_route, new_route)
    print("✅ Route condition updated to be more specific!")
else:
    print("❌ Old route not found")

# Write the file
with open('static-server.js', 'w') as f:
    f.write(content)

print("✅ File written successfully!")
