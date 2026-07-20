const { test, expect, loginAsRole, verifyNoUnexpectedRedirect, logIssue, logPageResult, saveIssuesReport, getCredentials, getRoleDescription } = require('../utils/test-base');
const { RVZ_PAGES } = require('../utils/page-catalog');

const ROLE = 'rvz';
const ROLE_DESCRIPTION = getRoleDescription(ROLE);

test.describe(`${ROLE_DESCRIPTION} - All RVZ Pages E2E Test`, () => {
  test.setTimeout(120000);
  
  test.beforeAll(async () => {
    console.log(`=== Starting ${ROLE_DESCRIPTION} E2E Tests ===`);
    console.log(`Testing ${RVZ_PAGES.length} RVZ admin pages`);
    console.log(`Role: ${ROLE} (${ROLE_DESCRIPTION})`);
  });
  
  test('RVZ Login Test', async ({ page, pageMonitor }) => {
    await page.goto('/staff/login');
    await page.waitForLoadState('networkidle');
    
    const report = pageMonitor.getReport();
    logPageResult('RVZ', '/staff/login', report.consoleErrors.length === 0 ? 'PASS' : 'FAIL', report);
    
    await page.screenshot({ 
      path: 'tests/reports/screenshots/rvz_login.png',
      fullPage: true 
    });
  });
  
  RVZ_PAGES.forEach(pageInfo => {
    test(`${pageInfo.name} (${pageInfo.path})`, async ({ page, pageMonitor }) => {
      console.log(`Testing RVZ Page: ${pageInfo.name}`);
      
      try {
        await loginAsRole(page, ROLE);
        
        pageMonitor.clearErrors();
        
        const targetPath = pageInfo.path;
        await page.goto(targetPath, { timeout: 30000, waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(2000);
        
        const redirectCheck = verifyNoUnexpectedRedirect(page, targetPath);
        
        if (!redirectCheck.success) {
          if (redirectCheck.isLoginRedirect) {
            logIssue('RVZ', pageInfo.path, 'AUTH_REDIRECT_TO_LOGIN', { 
              message: 'Page redirected to login - server-side auth issue or route ordering problem',
              expectedPath: targetPath,
              actualUrl: redirectCheck.actualUrl,
              severity: 'CRITICAL'
            });
            logPageResult('RVZ', pageInfo.path, 'AUTH_FAIL', { 
              redirectedTo: redirectCheck.actualUrl, 
              type: 'login_redirect' 
            });
            expect(redirectCheck.isLoginRedirect, `Expected ${targetPath} but got redirected to login`).toBe(false);
            return;
          }
          
          if (redirectCheck.isDashboardRedirect) {
            logIssue('RVZ', pageInfo.path, 'AUTH_REDIRECT_TO_DASHBOARD', { 
              message: 'Page redirected to dashboard instead of target - possible route ordering issue in server.js',
              expectedPath: targetPath,
              actualUrl: redirectCheck.actualUrl,
              severity: 'HIGH'
            });
            logPageResult('RVZ', pageInfo.path, 'REDIRECT_FAIL', { 
              redirectedTo: redirectCheck.actualUrl, 
              type: 'dashboard_redirect' 
            });
            expect(redirectCheck.isDashboardRedirect, `Expected ${targetPath} but got redirected to dashboard`).toBe(false);
            return;
          }
        }
        
        const report = pageMonitor.getReport();
        
        if (report.consoleErrors.length > 0) {
          report.consoleErrors.forEach(err => {
            const severity = err.text?.includes('TypeError') || err.text?.includes('ReferenceError') ? 'HIGH' : 'MEDIUM';
            logIssue('RVZ', pageInfo.path, 'CONSOLE_ERROR', { ...err, severity });
          });
        }
        
        if (report.networkErrors.length > 0) {
          report.networkErrors.forEach(err => {
            if (err.status === 401 || err.status === 403) {
              logIssue('RVZ', pageInfo.path, 'AUTH_ERROR', { ...err, severity: 'HIGH' });
            } else if (err.status === 500) {
              logIssue('RVZ', pageInfo.path, 'SERVER_ERROR', { ...err, severity: 'CRITICAL' });
            } else if (err.status === 404 && !err.url.includes('.png') && !err.url.includes('.jpg') && !err.url.includes('.ico')) {
              logIssue('RVZ', pageInfo.path, 'NOT_FOUND', { ...err, severity: 'MEDIUM' });
            }
          });
        }
        
        if (report.failedRequests.length > 0) {
          report.failedRequests.forEach(err => {
            logIssue('RVZ', pageInfo.path, 'FAILED_REQUEST', { ...err, severity: 'MEDIUM' });
          });
        }
        
        const buttons = await page.$$('button:visible');
        const tabs = await page.$$('[role="tab"]:visible, .nav-link:visible, .tab-link:visible');
        const filters = await page.$$('select:visible, input[type="search"]:visible, .filter-input:visible');
        const tables = await page.$$('table:visible, .data-table:visible');
        
        const interactiveElements = {
          buttons: buttons.length,
          tabs: tabs.length,
          filters: filters.length,
          tables: tables.length
        };
        
        const hasCriticalErrors = pageMonitor.hasCriticalErrors();
        const hasErrors = pageMonitor.hasErrors();
        
        logPageResult('RVZ', pageInfo.path, hasCriticalErrors ? 'FAIL' : (hasErrors ? 'WARN' : 'PASS'), {
          ...report,
          interactiveElements,
          finalUrl: page.url()
        });
        
        await page.screenshot({ 
          path: `tests/reports/screenshots/rvz_${pageInfo.name.replace(/[^a-zA-Z0-9]/g, '_')}.png`,
          fullPage: true 
        });
        
      } catch (error) {
        logIssue('RVZ', pageInfo.path, 'TEST_ERROR', { message: error.message, stack: error.stack, severity: 'CRITICAL' });
        logPageResult('RVZ', pageInfo.path, 'ERROR', { error: error.message });
        throw error;
      }
    });
  });
  
  test.afterAll(() => {
    saveIssuesReport();
    console.log(`=== ${ROLE_DESCRIPTION} E2E Tests Complete ===`);
  });
});
