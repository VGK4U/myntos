const { test, expect, loginAsStaff, logIssue, logPageResult, saveIssuesReport } = require('../utils/test-base');
const { PARTNER_PAGES } = require('../utils/page-catalog');

const PARTNER_CREDENTIALS = {
  employeeId: process.env.TEST_PARTNER_ID || 'EMP001',
  password: process.env.TEST_PARTNER_PASSWORD || 'Test@123'
};

test.describe('Partner Role - All Partner Pages E2E Test', () => {
  
  test.beforeAll(async () => {
    console.log('=== Starting Partner Role E2E Tests ===');
    console.log(`Testing ${PARTNER_PAGES.length} partner pages`);
  });
  
  PARTNER_PAGES.forEach(pageInfo => {
    test(`${pageInfo.name} (${pageInfo.path})`, async ({ page, pageMonitor }) => {
      console.log(`Testing Partner Page: ${pageInfo.name}`);
      
      try {
        await loginAsStaff(page, PARTNER_CREDENTIALS.employeeId, PARTNER_CREDENTIALS.password);
        
        pageMonitor.clearErrors();
        
        await page.goto(pageInfo.path);
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(3000);
        
        const currentUrl = page.url();
        if (currentUrl.includes('/login')) {
          logIssue('PARTNER', pageInfo.path, 'AUTH_REDIRECT', { 
            message: 'Page redirected to login',
            expectedPath: pageInfo.path,
            actualUrl: currentUrl
          });
          logPageResult('PARTNER', pageInfo.path, 'AUTH_FAIL', { redirectedTo: currentUrl });
          return;
        }
        
        const report = pageMonitor.getReport();
        
        if (report.consoleErrors.length > 0) {
          report.consoleErrors.forEach(err => {
            logIssue('PARTNER', pageInfo.path, 'CONSOLE_ERROR', err);
          });
        }
        
        if (report.networkErrors.length > 0) {
          report.networkErrors.forEach(err => {
            logIssue('PARTNER', pageInfo.path, 'NETWORK_ERROR', err);
          });
        }
        
        if (report.failedRequests.length > 0) {
          report.failedRequests.forEach(err => {
            logIssue('PARTNER', pageInfo.path, 'FAILED_REQUEST', err);
          });
        }
        
        const hasErrors = pageMonitor.hasErrors();
        logPageResult('PARTNER', pageInfo.path, hasErrors ? 'FAIL' : 'PASS', report);
        
        await page.screenshot({ 
          path: `tests/reports/screenshots/partner_${pageInfo.name.replace(/[^a-zA-Z0-9]/g, '_')}.png`,
          fullPage: true 
        });
        
      } catch (error) {
        logIssue('PARTNER', pageInfo.path, 'TEST_ERROR', { message: error.message });
        logPageResult('PARTNER', pageInfo.path, 'ERROR', { error: error.message });
      }
    });
  });
  
  test.afterAll(() => {
    saveIssuesReport();
    console.log('=== Partner Role E2E Tests Complete ===');
  });
});
