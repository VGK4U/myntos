#!/usr/bin/env python3
"""
Insert KYC Management route immediately after /admin/users route
"""

# Read the file
with open('static-server.js', 'r') as f:
    content = f.read()

# Find the /admin/users route block end
marker = """  } else if (url.startsWith('/admin/users')) {
    if (!isLoggedIn || !hasAdminPrivileges(sessionToken)) {
      res.writeHead(302, { 'Location': `/login?v=${BUILD_ID}` });
      res.end();
      return;
    }
    const filePath = path.join(__dirname, 'admin_users.html');
    fs.readFile(filePath, 'utf8', (err, data) => {
      if (err) {
        res.writeHead(404);
        res.end('Page not found');
        return;
      }
      const modifiedData = data.replace(/localStorage\\.getItem\\('authToken'\\)/g, `'${escapeJSServer(sessionToken)}'`);
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(modifiedData);
    });
    return;"""

# New KYC route to insert after
new_kyc_route = """
    
  } else if (url.startsWith('/admin/kyc-management')) {
    if (!isLoggedIn || !hasAdminPrivileges(sessionToken)) {
      res.writeHead(302, { 'Location': `/login?v=${BUILD_ID}` });
      res.end();
      return;
    }
    const filePath = path.join(__dirname, 'admin_kyc_management.html');
    fs.readFile(filePath, 'utf8', (err, data) => {
      if (err) {
        res.writeHead(404);
        res.end('Page not found');
        return;
      }
      const modifiedData = data.replace(/localStorage\\.getItem\\('authToken'\\)/g, `'${escapeJSServer(sessionToken)}'`);
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(modifiedData);
    });
    return;"""

# Insert after the marker
if marker in content:
    # First, remove any existing KYC management routes
    import re
    # Remove old KYC route
    pattern = r"  \} else if \(url\.startsWith\('/admin/kyc-management'\).*?\n    return;\n"
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    pattern = r"  \} else if \(url === '/admin/kyc-management'.*?\n    return;\n"
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # Now insert after /admin/users
    content = content.replace(marker, marker + new_kyc_route)
    print("✅ KYC Management route inserted after /admin/users!")
else:
    print("❌ Marker not found")

# Write the file
with open('static-server.js', 'w') as f:
    f.write(content)

print("✅ File written!")
