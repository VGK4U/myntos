const { test, expect, loginAsUser, logIssue, logPageResult, saveIssuesReport, getCredentials } = require('../utils/test-base');
const { USER_PAGES } = require('../utils/page-catalog');

const USER_CREDENTIALS = getCredentials('user');

test.describe('User Role - All User Pages E2E Test', () => {
  
  test.beforeAll(async () => {
    console.log('=== Starting User Role E2E Tests ===');
    console.log(`Testing ${USER_PAGES.length} user pages`);
  });
  
  USER_PAGES.forEach(pageInfo => {
    test(`${pageInfo.name} (${pageInfo.path})`, async ({ page, pageMonitor }) => {
      console.log(`Testing User Page: ${pageInfo.name}`);
      
      try {
        await loginAsUser(page, USER_CREDENTIALS.mnrId, USER_CREDENTIALS.password);
        
        pageMonitor.clearErrors();
        
        await page.goto(pageInfo.path, { timeout: 30000, waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(1500);
        
        const currentUrl = page.url();
        if (currentUrl.includes('/login') && pageInfo.requiresAuth) {
          logIssue('USER', pageInfo.path, 'AUTH_REDIRECT', { 
            message: 'Page redirected to login',
            expectedPath: pageInfo.path,
            actualUrl: currentUrl
          });
          logPageResult('USER', pageInfo.path, 'AUTH_FAIL', { redirectedTo: currentUrl });
          return;
        }
        
        const report = pageMonitor.getReport();
        
        if (report.consoleErrors.length > 0) {
          report.consoleErrors.forEach(err => {
            logIssue('USER', pageInfo.path, 'CONSOLE_ERROR', err);
          });
        }
        
        if (report.networkErrors.length > 0) {
          report.networkErrors.forEach(err => {
            logIssue('USER', pageInfo.path, 'NETWORK_ERROR', err);
          });
        }
        
        if (report.failedRequests.length > 0) {
          report.failedRequests.forEach(err => {
            logIssue('USER', pageInfo.path, 'FAILED_REQUEST', err);
          });
        }
        
        const hasErrors = pageMonitor.hasErrors();
        logPageResult('USER', pageInfo.path, hasErrors ? 'FAIL' : 'PASS', report);
        
        await page.screenshot({ 
          path: `tests/reports/screenshots/user_${pageInfo.name.replace(/[^a-zA-Z0-9]/g, '_')}.png`,
          fullPage: true 
        });
        
      } catch (error) {
        logIssue('USER', pageInfo.path, 'TEST_ERROR', { message: error.message });
        logPageResult('USER', pageInfo.path, 'ERROR', { error: error.message });
      }
    });
  });
  
  test.afterAll(() => {
    saveIssuesReport();
    console.log('=== User Role E2E Tests Complete ===');
  });
});
