#!/usr/bin/env node
/**
 * Safe patch script to inject feedback routes into server.js
 * Uses anchor points and idempotency markers to safely modify the large file
 */

const fs = require('fs');
const path = require('path');

const SERVER_FILE = path.join(__dirname, 'server.js');
const BACKUP_FILE = path.join(__dirname, 'server.js.backup');

// Markers for idempotency
const BEGIN_MARKER = '// BEGIN_FEEDBACK_ROUTES - Auto-generated, do not modify';
const END_MARKER = '// END_FEEDBACK_ROUTES';

// Define the routes to be inserted
const FEEDBACK_ROUTES = `
  ${BEGIN_MARKER}
  } else if (url.startsWith('/user/feedback/submit')) {
    // User Feedback Submission page
    if (!isLoggedIn) {
      res.writeHead(302, { 'Location': \`/login?v=\${BUILD_ID}\` });
      res.end();
      return;
    }
    const filePath = path.join(__dirname, 'user_feedback_submit.html');
    fs.readFile(filePath, 'utf8', (err, data) => {
      if (err) {
        res.writeHead(500);
        res.end('Error loading page');
        return;
      }
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(data);
    });
    return;
    
  } else if (url.startsWith('/user/my-feedback-submissions')) {
    // User's My Submissions page
    if (!isLoggedIn) {
      res.writeHead(302, { 'Location': \`/login?v=\${BUILD_ID}\` });
      res.end();
      return;
    }
    const filePath = path.join(__dirname, 'user_my_submissions.html');
    fs.readFile(filePath, 'utf8', (err, data) => {
      if (err) {
        res.writeHead(500);
        res.end('Error loading page');
        return;
      }
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(data);
    });
    return;
    
  } else if (url.startsWith('/user/announcements')) {
    // Public Announcements page
    if (!isLoggedIn) {
      res.writeHead(302, { 'Location': \`/login?v=\${BUILD_ID}\` });
      res.end();
      return;
    }
    const filePath = path.join(__dirname, 'user_announcements.html');
    fs.readFile(filePath, 'utf8', (err, data) => {
      if (err) {
        res.writeHead(500);
        res.end('Error loading page');
        return;
      }
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(data);
    });
    return;
    
  } else if (url.startsWith('/admin/feedback/pending')) {
    // Admin Feedback Approval page
    if (!isLoggedIn) {
      res.writeHead(302, { 'Location': \`/login?v=\${BUILD_ID}\` });
      res.end();
      return;
    }
    const userRole = getUserRole(sessionToken);
    if (!['Admin', 'Super Admin', 'RVZ ID', 'Finance Admin'].includes(userRole)) {
      res.writeHead(403);
      res.end('Access denied');
      return;
    }
    const filePath = path.join(__dirname, 'admin_feedback_pending.html');
    fs.readFile(filePath, 'utf8', (err, data) => {
      if (err) {
        res.writeHead(500);
        res.end('Error loading page');
        return;
      }
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(data);
    });
    return;
    
  } else if (url.startsWith('/rvz/categories')) {
    // RVZ Category Management page
    if (!isLoggedIn) {
      res.writeHead(302, { 'Location': \`/login?v=\${BUILD_ID}\` });
      res.end();
      return;
    }
    const userRole = getUserRole(sessionToken);
    if (userRole !== 'RVZ ID') {
      res.writeHead(403);
      res.end('Access denied - RVZ only');
      return;
    }
    const filePath = path.join(__dirname, 'vgk_categories.html');
    fs.readFile(filePath, 'utf8', (err, data) => {
      if (err) {
        res.writeHead(500);
        res.end('Error loading page');
        return;
      }
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(data);
    });
    return;
  }
  ${END_MARKER}
`;

// Anchor to find insertion point (in PHASE 4 section)
const ANCHOR = "  // PHASE 4: NEW FRONTEND ROUTES (Template Migration Completion)";

function main() {
  console.log('🔧 Feedback Routes Patch Script');
  console.log('================================');
  
  // Check if server.js exists
  if (!fs.existsSync(SERVER_FILE)) {
    console.error('❌ Error: server.js not found');
    process.exit(1);
  }
  
  // Read server.js
  console.log('📖 Reading server.js...');
  let content = fs.readFileSync(SERVER_FILE, 'utf8');
  
  // Check if already patched
  if (content.includes(BEGIN_MARKER)) {
    console.log('✅ Routes already patched! Skipping...');
    console.log('   (Remove markers to re-patch)');
    return;
  }
  
  // Find anchor point
  console.log('🔍 Looking for insertion anchor...');
  if (!content.includes(ANCHOR)) {
    console.error('❌ Error: Anchor point not found');
    console.error('   Looking for:', ANCHOR);
    process.exit(1);
  }
  
  // Create backup
  console.log('💾 Creating backup...');
  fs.copyFileSync(SERVER_FILE, BACKUP_FILE);
  console.log('   Backup saved:', BACKUP_FILE);
  
  // Find insertion point after the anchor comment and section markers
  const anchorIndex = content.indexOf(ANCHOR);
  
  // Skip to after the "// ======..." line and find the next } else if
  const sectionEndMarker = '  // ================================================================================';
  const sectionEndIndex = content.indexOf(sectionEndMarker, anchorIndex);
  const nextElseIndex = content.indexOf('\n', sectionEndIndex) + 1;
  
  if (nextElseIndex === -1) {
    console.error('❌ Error: Could not find safe insertion point');
    process.exit(1);
  }
  
  // Insert routes right after the section marker
  const before = content.substring(0, nextElseIndex);
  const after = content.substring(nextElseIndex);
  const patchedContent = before + FEEDBACK_ROUTES + '\n' + after;
  
  // Safety checks
  console.log('🔒 Running safety checks...');
  
  // Check brace balance
  const openBraces = (patchedContent.match(/{/g) || []).length;
  const closeBraces = (patchedContent.match(/}/g) || []).length;
  
  if (openBraces !== closeBraces) {
    console.error('❌ Error: Brace mismatch detected');
    console.error(`   Open: ${openBraces}, Close: ${closeBraces}`);
    process.exit(1);
  }
  
  console.log('   ✓ Brace balance: OK');
  console.log(`   ✓ New file size: ${patchedContent.length} chars`);
  console.log(`   ✓ Added ${FEEDBACK_ROUTES.split('\n').length} lines`);
  
  // Write patched file
  console.log('💾 Writing patched server.js...');
  fs.writeFileSync(SERVER_FILE, patchedContent, 'utf8');
  
  console.log('✅ Patch completed successfully!');
  console.log('');
  console.log('📝 Next steps:');
  console.log('   1. Restart frontend workflow');
  console.log('   2. Test new routes:');
  console.log('      - /user/feedback/submit');
  console.log('      - /user/my-feedback-submissions');
  console.log('      - /user/announcements');
  console.log('      - /admin/feedback/pending');
  console.log('      - /rvz/categories');
  console.log('');
  console.log('💡 To rollback: mv server.js.backup server.js');
}

try {
  main();
} catch (error) {
  console.error('❌ Unexpected error:', error.message);
  process.exit(1);
}
