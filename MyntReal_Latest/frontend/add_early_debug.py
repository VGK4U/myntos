#!/usr/bin/env python3
"""
Add debug logging at the beginning of request handler
"""

# Read the file
with open('static-server.js', 'r') as f:
    content = f.read()

# Find the server creation and add logging right after URL is defined
old_code = """const server = http.createServer(async (req, res) => {
  const url = req.url;
  const urlParts = new URL(url, `http://${req.headers.host}`);"""

new_code = """const server = http.createServer(async (req, res) => {
  const url = req.url;
  const urlParts = new URL(url, `http://${req.headers.host}`);
  
  // DEBUG: Log KYC management requests
  if (url.includes('kyc')) {
    console.log('🔍 DEBUG: Request with kyc in URL:', url);
  }"""

if old_code in content:
    content = content.replace(old_code, new_code)
    print("✅ Early debug logging added!")
else:
    print("❌ Could not find server creation code")

# Write the file
with open('static-server.js', 'w') as f:
    f.write(content)

print("✅ File written!")
