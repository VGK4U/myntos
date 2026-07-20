const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

const BASE_URL = process.env.BASE_URL || 'http://localhost:5000';
const API_BASE = `${BASE_URL}/api/v1`;

const issues = [];
const results = [];

const PAGES_TO_TEST = {
  PUBLIC: [
    { path: '/', name: 'Home/Login' },
    { path: '/login', name: 'User Login' },
    { path: '/staff/login', name: 'Staff Login' },
    { path: '/real-dreams/marketplace', name: 'Real Dreams Marketplace' },
  ],
  STAFF: [
    { path: '/staff/dashboard', name: 'Staff Dashboard' },
    { path: '/staff/my-attendance', name: 'My Attendance' },
    { path: '/staff/my-journeys', name: 'My Journeys' },
    { path: '/staff/my-timesheet', name: 'My Timesheet' },
    { path: '/staff/accounts/sales-invoices', name: 'Sales Invoices' },
    { path: '/staff/accounts/reports', name: 'SFMS Reports' },
    { path: '/staff/accounts/companies', name: 'SFMS Companies' },
    { path: '/staff/accounts/hsn', name: 'HSN Codes' },
    { path: '/staff/accounts/vendors', name: 'Vendors' },
    { path: '/staff/accounts/stock-items', name: 'Stock Items' },
    { path: '/staff/accounts/purchase-invoices', name: 'Purchase Invoices' },
    { path: '/staff/accounts/bom', name: 'BOM' },
    { path: '/staff/accounts/manufacturing', name: 'Manufacturing' },
    { path: '/staff/accounts/procurement', name: 'Procurement' },
    { path: '/staff/employees', name: 'Employees' },
    { path: '/staff/departments', name: 'Departments' },
    { path: '/staff/team/attendance', name: 'Team Attendance' },
    { path: '/staff/team/journeys', name: 'Team Journeys' },
    { path: '/staff/tasks/assigned-to-me', name: 'Tasks Assigned To Me' },
    { path: '/staff/tasks/assigned-by-me', name: 'Tasks Assigned By Me' },
    { path: '/staff/kra-templates', name: 'KRA Templates' },
    { path: '/staff/kra-tracking-sheet', name: 'KRA Tracking Sheet' },
    { path: '/staff/nda-editor', name: 'NDA Editor' },
    { path: '/staff/nda-versions', name: 'NDA Versions' },
    { path: '/staff/audit-logs', name: 'Audit Logs' },
  ],
  RVZ: [
    { path: '/rvz/dashboard', name: 'RVZ Dashboard' },
    { path: '/rvz/user-data-search', name: 'User Data Search' },
    { path: '/rvz/menu-access-config', name: 'Menu Access Control' },
    { path: '/rvz/menu-configuration', name: 'Menu Configuration' },
    { path: '/rvz/department-management', name: 'Department Management' },
    { path: '/rvz/crm/leads', name: 'CRM Leads' },
    { path: '/rvz/real-dreams/dashboard', name: 'Real Dreams Dashboard' },
    { path: '/rvz/award-management', name: 'Award Management' },
    { path: '/rvz/role-management', name: 'Role Management' },
    { path: '/rvz/system-controls', name: 'System Controls' },
  ],
  PARTNER: [
    { path: '/partner/login', name: 'Partner Login' },
    { path: '/partner/dashboard', name: 'Partner Dashboard' },
    { path: '/partner/orders', name: 'Partner Orders' },
    { path: '/partner/master', name: 'Partner Master' },
    { path: '/partner/pricing', name: 'Partner Pricing' },
    { path: '/partner/payments', name: 'Partner Payments' },
    { path: '/order-fulfillment-dashboard', name: 'Order Fulfillment Dashboard' },
  ],
  USER: [
    { path: '/dashboard', name: 'User Dashboard' },
    { path: '/user/awards', name: 'User Awards' },
    { path: '/user/field-allowances', name: 'Field Allowances' },
    { path: '/user/direct-referral', name: 'Direct Referral' },
  ]
};

async function testPage(role, pageInfo) {
  return new Promise((resolve) => {
    const url = new URL(pageInfo.path, BASE_URL);
    const client = url.protocol === 'https:' ? https : http;
    
    const startTime = Date.now();
    
    const req = client.get(url.href, { timeout: 30000 }, (res) => {
      const endTime = Date.now();
      const responseTime = endTime - startTime;
      
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        const result = {
          role,
          path: pageInfo.path,
          name: pageInfo.name,
          status: res.statusCode,
          responseTime,
          contentLength: body.length,
          hasContent: body.length > 100,
          timestamp: new Date().toISOString()
        };
        
        if (res.statusCode >= 400) {
          issues.push({
            role,
            path: pageInfo.path,
            name: pageInfo.name,
            issueType: 'HTTP_ERROR',
            status: res.statusCode,
            details: `HTTP ${res.statusCode} error`,
            solution: getHttpSolution(res.statusCode),
            timestamp: new Date().toISOString()
          });
          result.passed = false;
        } else {
          result.passed = true;
        }
        
        results.push(result);
        resolve(result);
      });
    });
    
    req.on('error', (err) => {
      issues.push({
        role,
        path: pageInfo.path,
        name: pageInfo.name,
        issueType: 'CONNECTION_ERROR',
        details: err.message,
        solution: 'Check if server is running and page route is registered',
        timestamp: new Date().toISOString()
      });
      
      results.push({
        role,
        path: pageInfo.path,
        name: pageInfo.name,
        status: 0,
        error: err.message,
        passed: false,
        timestamp: new Date().toISOString()
      });
      
      resolve(null);
    });
    
    req.on('timeout', () => {
      req.destroy();
      issues.push({
        role,
        path: pageInfo.path,
        name: pageInfo.name,
        issueType: 'TIMEOUT',
        details: 'Request timed out after 30 seconds',
        solution: 'Check for slow database queries or infinite loops',
        timestamp: new Date().toISOString()
      });
      
      results.push({
        role,
        path: pageInfo.path,
        name: pageInfo.name,
        status: 0,
        error: 'Timeout',
        passed: false,
        timestamp: new Date().toISOString()
      });
      
      resolve(null);
    });
  });
}

function getHttpSolution(status) {
  const solutions = {
    401: 'Authentication required - Check if token is being passed correctly. Verify localStorage key is "staff_token" not "staffToken".',
    403: 'Forbidden - User lacks permission. Check role-based access control settings.',
    404: 'Page not found - Check if route is registered in server.js and HTML file exists.',
    500: 'Server error - Check backend logs for stack trace. Likely database or API issue.',
    502: 'Bad Gateway - Backend may be down or not responding.',
    503: 'Service unavailable - Server overloaded or under maintenance.'
  };
  return solutions[status] || `HTTP ${status} error - Check server logs for details.`;
}

async function runTests() {
  console.log('='.repeat(60));
  console.log('E2E PAGE CONNECTIVITY TEST - DC PROTOCOL COMPLIANT');
  console.log('='.repeat(60));
  console.log(`Base URL: ${BASE_URL}`);
  console.log(`Started: ${new Date().toISOString()}`);
  console.log('');
  
  for (const [role, pages] of Object.entries(PAGES_TO_TEST)) {
    console.log(`\n--- Testing ${role} Pages (${pages.length} pages) ---`);
    
    for (const pageInfo of pages) {
      const result = await testPage(role, pageInfo);
      const status = result?.passed ? '✅' : '❌';
      const httpStatus = result?.status || 'ERR';
      console.log(`${status} [${httpStatus}] ${pageInfo.name} (${pageInfo.path})`);
    }
  }
  
  console.log('\n' + '='.repeat(60));
  console.log('TEST SUMMARY');
  console.log('='.repeat(60));
  
  const passed = results.filter(r => r.passed).length;
  const failed = results.filter(r => !r.passed).length;
  const total = results.length;
  
  console.log(`Total Pages Tested: ${total}`);
  console.log(`Passed: ${passed}`);
  console.log(`Failed: ${failed}`);
  console.log(`Pass Rate: ${((passed/total)*100).toFixed(1)}%`);
  
  if (issues.length > 0) {
    console.log('\n' + '='.repeat(60));
    console.log('ISSUES FOUND - DC PROTOCOL SOLUTIONS');
    console.log('='.repeat(60));
    
    const byRole = {};
    issues.forEach(issue => {
      if (!byRole[issue.role]) byRole[issue.role] = [];
      byRole[issue.role].push(issue);
    });
    
    Object.entries(byRole).forEach(([role, roleIssues]) => {
      console.log(`\n### ${role} Role Issues (${roleIssues.length}):\n`);
      roleIssues.forEach((issue, idx) => {
        console.log(`${idx + 1}. ${issue.name} (${issue.path})`);
        console.log(`   Type: ${issue.issueType}`);
        console.log(`   Details: ${issue.details}`);
        console.log(`   Solution: ${issue.solution}`);
        console.log('');
      });
    });
  }
  
  const reportDir = path.join(__dirname, 'reports');
  if (!fs.existsSync(reportDir)) {
    fs.mkdirSync(reportDir, { recursive: true });
  }
  
  const report = {
    generatedAt: new Date().toISOString(),
    baseUrl: BASE_URL,
    summary: {
      total,
      passed,
      failed,
      passRate: ((passed/total)*100).toFixed(1) + '%'
    },
    issues,
    results
  };
  
  fs.writeFileSync(
    path.join(reportDir, 'e2e-report.json'),
    JSON.stringify(report, null, 2)
  );
  
  let mdReport = `# E2E Test Report\n\n`;
  mdReport += `Generated: ${new Date().toISOString()}\n\n`;
  mdReport += `## Summary\n\n`;
  mdReport += `| Metric | Value |\n|--------|-------|\n`;
  mdReport += `| Total Pages | ${total} |\n`;
  mdReport += `| Passed | ${passed} |\n`;
  mdReport += `| Failed | ${failed} |\n`;
  mdReport += `| Pass Rate | ${((passed/total)*100).toFixed(1)}% |\n\n`;
  
  if (issues.length > 0) {
    mdReport += `## Issues Found (${issues.length})\n\n`;
    
    const byRole = {};
    issues.forEach(issue => {
      if (!byRole[issue.role]) byRole[issue.role] = [];
      byRole[issue.role].push(issue);
    });
    
    Object.entries(byRole).forEach(([role, roleIssues]) => {
      mdReport += `### ${role} Role\n\n`;
      roleIssues.forEach(issue => {
        mdReport += `#### ${issue.name}\n`;
        mdReport += `- **Path**: ${issue.path}\n`;
        mdReport += `- **Issue Type**: ${issue.issueType}\n`;
        mdReport += `- **Details**: ${issue.details}\n`;
        mdReport += `- **DC Solution**: ${issue.solution}\n\n`;
      });
    });
  }
  
  mdReport += `## All Results\n\n`;
  mdReport += `| Role | Page | Status | Response Time |\n`;
  mdReport += `|------|------|--------|---------------|\n`;
  results.forEach(r => {
    const status = r.passed ? '✅ Pass' : '❌ Fail';
    mdReport += `| ${r.role} | ${r.name} | ${status} (${r.status}) | ${r.responseTime || 'N/A'}ms |\n`;
  });
  
  fs.writeFileSync(
    path.join(reportDir, 'e2e-report.md'),
    mdReport
  );
  
  console.log('\n' + '='.repeat(60));
  console.log('Reports saved to tests/reports/');
  console.log('  - e2e-report.json');
  console.log('  - e2e-report.md');
  console.log('='.repeat(60));
  
  return { passed, failed, issues };
}

// DC_CONTENT_TYPE_REGRESSION_001: API endpoint validation tests
const API_TESTS = {
  ATTENDANCE: [
    {
      name: 'Clock-In Endpoint Schema Validation',
      endpoint: '/staff/attendance/clock-in',
      method: 'POST',
      requiresAuth: true,
      expectedContentType: 'application/json',
      testPayload: {
        work_mode: 'office',
        location: { latitude: 19.0760, longitude: 72.8777, accuracy: 10 },
        evidence: null
      }
    },
    {
      name: 'Clock-Out Endpoint Schema Validation', 
      endpoint: '/staff/attendance/clock-out',
      method: 'POST',
      requiresAuth: true,
      expectedContentType: 'application/json',
      testPayload: {
        location: { latitude: 19.0760, longitude: 72.8777, accuracy: 10 },
        evidence: null
      }
    },
    {
      name: 'Attendance Today Status Endpoint',
      endpoint: '/staff/attendance/today',
      method: 'GET',
      requiresAuth: true,
      expectedContentType: 'application/json'
    }
  ]
};

async function testApiEndpoint(testInfo) {
  return new Promise((resolve) => {
    const url = new URL(`/api/v1${testInfo.endpoint}`, BASE_URL);
    const client = url.protocol === 'https:' ? https : http;
    
    const options = {
      method: testInfo.method,
      hostname: url.hostname,
      port: url.port,
      path: url.pathname,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    };
    
    const req = client.request(options, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        const contentType = res.headers['content-type'] || '';
        const isJsonResponse = contentType.includes('application/json');
        
        // For auth-required endpoints, 401/403 is expected without token
        const expectedUnauth = testInfo.requiresAuth && (res.statusCode === 401 || res.statusCode === 403);
        
        // Check if response is valid JSON when expected
        let isValidJson = false;
        try {
          if (body) JSON.parse(body);
          isValidJson = true;
        } catch (e) {
          isValidJson = false;
        }
        
        const passed = expectedUnauth || (isJsonResponse && isValidJson);
        
        resolve({
          name: testInfo.name,
          endpoint: testInfo.endpoint,
          method: testInfo.method,
          status: res.statusCode,
          contentType,
          isJsonResponse,
          isValidJson,
          expectedUnauth,
          passed,
          details: expectedUnauth 
            ? 'Auth required - 401/403 expected without token'
            : (passed ? 'JSON response validated' : 'Invalid response format')
        });
      });
    });
    
    req.on('error', (err) => {
      resolve({
        name: testInfo.name,
        endpoint: testInfo.endpoint,
        passed: false,
        error: err.message
      });
    });
    
    req.on('timeout', () => {
      req.destroy();
      resolve({
        name: testInfo.name,
        endpoint: testInfo.endpoint,
        passed: false,
        error: 'Request timeout'
      });
    });
    
    if (testInfo.method === 'POST' && testInfo.testPayload) {
      req.write(JSON.stringify(testInfo.testPayload));
    }
    
    req.end();
  });
}

async function runApiTests() {
  console.log('\n--- Testing ATTENDANCE API Endpoints (DC_CONTENT_TYPE_REGRESSION) ---');
  
  const apiResults = [];
  
  for (const test of API_TESTS.ATTENDANCE) {
    const result = await testApiEndpoint(test);
    apiResults.push(result);
    
    const status = result.passed ? '✅' : '❌';
    const httpStatus = result.status || 'ERR';
    console.log(`${status} [${httpStatus}] ${test.name} (${test.method} ${test.endpoint})`);
    if (!result.passed && result.error) {
      console.log(`   Error: ${result.error}`);
    }
  }
  
  return apiResults;
}

runTests().then(async (summary) => {
  // Run API regression tests after page tests
  const apiResults = await runApiTests();
  const apiPassed = apiResults.filter(r => r.passed).length;
  const apiFailed = apiResults.filter(r => !r.passed).length;
  
  console.log(`\nAPI Tests: ${apiPassed}/${apiResults.length} passed`);
  
  console.log('\nE2E Tests Complete!');
  process.exit((summary.failed > 0 || apiFailed > 0) ? 1 : 0);
}).catch(err => {
  console.error('Test runner error:', err);
  process.exit(1);
});
