// Helper function for serving HTML pages with auth checks
function serveHtmlPage(res, fileName, sessionToken, requiresAuth = true, rolesAllowed = null) {
  const filePath = path.join(__dirname, fileName);
  fs.readFile(filePath, 'utf8', (err, data) => {
    if (err) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      res.end('Error loading page');
      return;
    }
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(data);
  });
}
