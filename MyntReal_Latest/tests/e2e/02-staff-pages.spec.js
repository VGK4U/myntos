const { test, expect, loginAsStaff, logIssue, logPageResult, saveIssuesReport, getCredentials } = require('../utils/test-base');
const { STAFF_PAGES } = require('../utils/page-catalog');

const STAFF_CREDENTIALS = getCredentials('staff');

test.describe('Staff Role - All Staff Pages E2E Test', () => {
  
  test.beforeAll(async ({ browser }) => {
    console.log('=== Starting Staff Role E2E Tests ===');
    console.log(`Testing ${STAFF_PAGES.length} staff pages`);
  });
  
  test('Staff Login Test', async ({ page, pageMonitor }) => {
    await page.goto('/staff/login');
    await page.waitForLoadState('networkidle');
    
    const report = pageMonitor.getReport();
    logPageResult('STAFF', '/staff/login', report.consoleErrors.length === 0 ? 'PASS' : 'FAIL', report);
    
    await page.screenshot({ 
      path: 'tests/reports/screenshots/staff_login.png',
      fullPage: true 
    });
  });
  
  STAFF_PAGES.forEach(pageInfo => {
    test(`${pageInfo.name} (${pageInfo.path})`, async ({ page, pageMonitor }) => {
      console.log(`Testing Staff Page: ${pageInfo.name}`);
      
      try {
        await loginAsStaff(page, STAFF_CREDENTIALS.employeeId, STAFF_CREDENTIALS.password);
        
        pageMonitor.clearErrors();
        
        await page.goto(pageInfo.path, { timeout: 30000, waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(1500);
        
        const currentUrl = page.url();
        if (currentUrl.includes('/login')) {
          logIssue('STAFF', pageInfo.path, 'AUTH_REDIRECT', { 
            message: 'Page redirected to login - possible auth issue',
            expectedPath: pageInfo.path,
            actualUrl: currentUrl
          });
          logPageResult('STAFF', pageInfo.path, 'AUTH_FAIL', { redirectedTo: currentUrl });
          return;
        }
        
        const report = pageMonitor.getReport();
        
        if (report.consoleErrors.length > 0) {
          report.consoleErrors.forEach(err => {
            logIssue('STAFF', pageInfo.path, 'CONSOLE_ERROR', err);
          });
        }
        
        if (report.networkErrors.length > 0) {
          report.networkErrors.forEach(err => {
            if (err.status === 401 || err.status === 403) {
              logIssue('STAFF', pageInfo.path, 'AUTH_ERROR', err);
            } else {
              logIssue('STAFF', pageInfo.path, 'NETWORK_ERROR', err);
            }
          });
        }
        
        if (report.failedRequests.length > 0) {
          report.failedRequests.forEach(err => {
            logIssue('STAFF', pageInfo.path, 'FAILED_REQUEST', err);
          });
        }
        
        const buttons = await page.$$('button:visible');
        const tabs = await page.$$('[role="tab"]:visible, .nav-link:visible, .tab-link:visible');
        const filters = await page.$$('select:visible, input[type="search"]:visible, .filter-input:visible');
        
        const interactiveElements = {
          buttons: buttons.length,
          tabs: tabs.length,
          filters: filters.length
        };
        
        const hasErrors = pageMonitor.hasErrors();
        logPageResult('STAFF', pageInfo.path, hasErrors ? 'FAIL' : 'PASS', {
          ...report,
          interactiveElements
        });
        
        await page.screenshot({ 
          path: `tests/reports/screenshots/staff_${pageInfo.name.replace(/[^a-zA-Z0-9]/g, '_')}.png`,
          fullPage: true 
        });
        
      } catch (error) {
        logIssue('STAFF', pageInfo.path, 'TEST_ERROR', { message: error.message, stack: error.stack });
        logPageResult('STAFF', pageInfo.path, 'ERROR', { error: error.message });
      }
    });
  });
  
  test.afterAll(() => {
    saveIssuesReport();
    console.log('=== Staff Role E2E Tests Complete ===');
  });
});
