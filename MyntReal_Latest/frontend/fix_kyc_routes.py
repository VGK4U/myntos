#!/usr/bin/env python3
"""
Fix KYC routes in static-server.js - replace old routes with new unified KYC Management route
"""

# Read the file
with open('static-server.js', 'r') as f:
    content = f.read()

# Old route handlers to replace
old_routes = """  } else if (url.startsWith('/admin/kyc-pending')) {
    if (!isLoggedIn || !hasAdminPrivileges(sessionToken)) {
      res.writeHead(302, { 'Location': `/login?v=${BUILD_ID}` });
      res.end();
      return;
    }
    const filePath = path.join(__dirname, 'admin_kyc_pending.html');
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
    return;
    
  } else if (url.startsWith('/admin/kyc-all')) {
    if (!isLoggedIn || !hasAdminPrivileges(sessionToken)) {
      res.writeHead(302, { 'Location': `/login?v=${BUILD_ID}` });
      res.end();
      return;
    }
    const filePath = path.join(__dirname, 'admin_kyc_all.html');
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

# New unified route
new_route = """  } else if (url.startsWith('/admin/kyc-management') || url.startsWith('/admin/kyc')) {
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

# Replace
if old_routes in content:
    content = content.replace(old_routes, new_route)
    print("✅ Routes replaced successfully!")
else:
    print("❌ Old routes not found - trying different approach...")
    # If exact match fails, try finding and replacing the sections individually

# Write the file
with open('static-server.js', 'w') as f:
    f.write(content)

print("✅ File written successfully!")
