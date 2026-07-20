const { test: base, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');
const { getCredentials, validateCredentials, getLoginType, getAllRoles, getRoleDescription } = require('./test-credentials');

const issuesLog = [];
const pageResults = [];

const test = base.extend({
  pageMonitor: async ({ page }, use) => {
    const consoleErrors = [];
    const networkErrors = [];
    const failedRequests = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push({
          text: msg.text(),
          location: msg.location(),
          timestamp: new Date().toISOString()
        });
      }
    });
    
    page.on('pageerror', error => {
      consoleErrors.push({
        text: error.message,
        stack: error.stack,
        timestamp: new Date().toISOString()
      });
    });
    
    page.on('requestfailed', request => {
      failedRequests.push({
        url: request.url(),
        method: request.method(),
        error: request.failure()?.errorText || 'Unknown error',
        timestamp: new Date().toISOString()
      });
    });
    
    page.on('response', response => {
      const status = response.status();
      if (status >= 400) {
        networkErrors.push({
          url: response.url(),
          status: status,
          statusText: response.statusText(),
          timestamp: new Date().toISOString()
        });
      }
    });
    
    const monitor = {
      getConsoleErrors: () => consoleErrors,
      getNetworkErrors: () => networkErrors,
      getFailedRequests: () => failedRequests,
      hasErrors: () => consoleErrors.length > 0 || networkErrors.length > 0 || failedRequests.length > 0,
      hasCriticalErrors: () => {
        return consoleErrors.some(e => e.text?.includes('TypeError') || e.text?.includes('ReferenceError')) ||
               networkErrors.some(e => e.status === 500 || e.status === 401 || e.status === 403);
      },
      clearErrors: () => {
        consoleErrors.length = 0;
        networkErrors.length = 0;
        failedRequests.length = 0;
      },
      getReport: () => ({
        consoleErrors: [...consoleErrors],
        networkErrors: [...networkErrors],
        failedRequests: [...failedRequests]
      })
    };
    
    await use(monitor);
  },
});

async function loginAsRole(page, role) {
  const creds = getCredentials(role);
  const loginType = getLoginType(role);
  
  if (loginType === 'staff') {
    await page.goto('/staff/login', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);
    await page.fill('input[name="employee_id"], #employee_id, input[placeholder*="Employee"]', creds.employeeId);
    await page.fill('input[name="password"], #password, input[type="password"]', creds.password);
    await page.click('button[type="submit"], .btn-login, button:has-text("Login"), button:has-text("Sign In")');
    await page.waitForTimeout(2000);
  } else if (loginType === 'user') {
    await page.goto('/login', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);
    await page.fill('input[name="mnr_id"], #mnr_id, input[placeholder*="MNR"]', creds.mnrId);
    await page.fill('input[name="password"], #password, input[type="password"]', creds.password);
    await page.click('button[type="submit"]');
    await page.waitForTimeout(2000);
  }
  
  return creds;
}

async function loginAsStaff(page, employeeId, password) {
  const creds = employeeId && password ? { employeeId, password } : getCredentials('staff');
  await page.goto('/staff/login', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1000);
  await page.fill('input[name="employee_id"], #employee_id, input[placeholder*="Employee"]', creds.employeeId);
  await page.fill('input[name="password"], #password, input[type="password"]', creds.password);
  await page.click('button[type="submit"], .btn-login, button:has-text("Login"), button:has-text("Sign In")');
  await page.waitForTimeout(2000);
}

async function loginAsRVZ(page, employeeId, password) {
  const creds = employeeId && password ? { employeeId, password } : getCredentials('rvz');
  await page.goto('/staff/login', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1000);
  await page.fill('input[name="employee_id"], #employee_id, input[placeholder*="Employee"]', creds.employeeId);
  await page.fill('input[name="password"], #password, input[type="password"]', creds.password);
  await page.click('button[type="submit"], .btn-login, button:has-text("Login"), button:has-text("Sign In")');
  await page.waitForTimeout(2000);
}

async function loginAsUser(page, mnrId, password) {
  const creds = mnrId && password ? { mnrId, password } : getCredentials('user');
  await page.goto('/login', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1000);
  await page.fill('input[name="mnr_id"], #mnr_id, input[placeholder*="MNR"]', creds.mnrId);
  await page.fill('input[name="password"], #password, input[type="password"]', creds.password);
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);
}

async function loginAsPartner(page, mnrId, password) {
  const creds = mnrId && password ? { mnrId, password } : getCredentials('partner');
  await page.goto('/login', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1000);
  await page.fill('input[name="mnr_id"], #mnr_id, input[placeholder*="MNR"]', creds.mnrId);
  await page.fill('input[name="password"], #password, input[type="password"]', creds.password);
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);
}

function verifyNoUnexpectedRedirect(page, expectedPath) {
  const currentUrl = page.url();
  const currentPath = new URL(currentUrl).pathname;
  
  const isLoginRedirect = currentPath.includes('/login') || currentPath.includes('/staff/login');
  const isDashboardRedirect = (currentPath === '/dashboard' || currentPath === '/staff/dashboard' || currentPath === '/rvz/dashboard') && !expectedPath.includes('/dashboard');
  
  return {
    success: !isLoginRedirect && !isDashboardRedirect,
    isLoginRedirect,
    isDashboardRedirect,
    expectedPath,
    actualPath: currentPath,
    actualUrl: currentUrl
  };
}

function logIssue(role, page, issueType, details) {
  issuesLog.push({
    role,
    page,
    issueType,
    details,
    timestamp: new Date().toISOString()
  });
}

function logPageResult(role, pagePath, status, errors) {
  pageResults.push({
    role,
    pagePath,
    status,
    errors,
    timestamp: new Date().toISOString()
  });
}

function saveIssuesReport() {
  const reportPath = path.join(__dirname, '../reports/issues-report.json');
  fs.writeFileSync(reportPath, JSON.stringify({
    generatedAt: new Date().toISOString(),
    totalIssues: issuesLog.length,
    totalPages: pageResults.length,
    issues: issuesLog,
    pageResults: pageResults
  }, null, 2));
  
  const summaryPath = path.join(__dirname, '../reports/issues-summary.md');
  let summary = `# E2E Test Issues Report\n\n`;
  summary += `Generated: ${new Date().toISOString()}\n\n`;
  summary += `## Summary\n`;
  summary += `- Total Pages Tested: ${pageResults.length}\n`;
  summary += `- Total Issues Found: ${issuesLog.length}\n`;
  summary += `- Pages with Errors: ${pageResults.filter(p => p.status === 'FAIL').length}\n`;
  summary += `- Pages Passed: ${pageResults.filter(p => p.status === 'PASS').length}\n`;
  summary += `- Auth Failures: ${pageResults.filter(p => p.status === 'AUTH_FAIL' || p.status === 'REDIRECT_FAIL').length}\n\n`;
  
  const byRole = {};
  issuesLog.forEach(issue => {
    if (!byRole[issue.role]) byRole[issue.role] = [];
    byRole[issue.role].push(issue);
  });
  
  Object.keys(byRole).forEach(role => {
    summary += `## ${role} Role Issues (${getRoleDescription(role) || role})\n\n`;
    byRole[role].forEach(issue => {
      summary += `### ${issue.page}\n`;
      summary += `- **Type**: ${issue.issueType}\n`;
      summary += `- **Severity**: ${issue.details?.severity || 'MEDIUM'}\n`;
      summary += `- **Details**: ${JSON.stringify(issue.details)}\n\n`;
    });
  });
  
  fs.writeFileSync(summaryPath, summary);
  
  console.log(`\n=== Test Report Generated ===`);
  console.log(`Issues Report: ${reportPath}`);
  console.log(`Summary: ${summaryPath}`);
  console.log(`Total Issues: ${issuesLog.length}`);
  console.log(`Auth Failures: ${pageResults.filter(p => p.status === 'AUTH_FAIL' || p.status === 'REDIRECT_FAIL').length}`);
}

module.exports = {
  test,
  expect,
  loginAsRole,
  loginAsStaff,
  loginAsRVZ,
  loginAsUser,
  loginAsPartner,
  verifyNoUnexpectedRedirect,
  logIssue,
  logPageResult,
  saveIssuesReport,
  issuesLog,
  pageResults,
  getCredentials,
  validateCredentials,
  getAllRoles,
  getRoleDescription
};
