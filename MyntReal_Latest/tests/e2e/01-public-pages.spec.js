const { test, expect, logIssue, logPageResult, saveIssuesReport } = require('../utils/test-base');
const { PUBLIC_PAGES } = require('../utils/page-catalog');

test.describe('Public Pages - No Authentication Required', () => {
  
  PUBLIC_PAGES.forEach(pageInfo => {
    test(`${pageInfo.name} (${pageInfo.path})`, async ({ page, pageMonitor }) => {
      console.log(`Testing: ${pageInfo.name}`);
      
      try {
        await page.goto(pageInfo.path, { timeout: 90000, waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(2000);
        
        const report = pageMonitor.getReport();
        
        if (report.consoleErrors.length > 0) {
          report.consoleErrors.forEach(err => {
            logIssue('PUBLIC', pageInfo.path, 'CONSOLE_ERROR', err);
          });
        }
        
        if (report.networkErrors.length > 0) {
          report.networkErrors.forEach(err => {
            logIssue('PUBLIC', pageInfo.path, 'NETWORK_ERROR', err);
          });
        }
        
        if (report.failedRequests.length > 0) {
          report.failedRequests.forEach(err => {
            logIssue('PUBLIC', pageInfo.path, 'FAILED_REQUEST', err);
          });
        }
        
        const hasErrors = pageMonitor.hasErrors();
        logPageResult('PUBLIC', pageInfo.path, hasErrors ? 'FAIL' : 'PASS', report);
        
        await page.screenshot({ 
          path: `tests/reports/screenshots/public_${pageInfo.name.replace(/[^a-zA-Z0-9]/g, '_')}.png`,
          fullPage: true 
        });
        
        const criticalErrors = report.consoleErrors.filter(e => 
          !e.text.includes('favicon') && 
          !e.text.includes('404') &&
          !e.text.includes('Failed to load resource')
        );
        expect(criticalErrors).toHaveLength(0);
        
      } catch (error) {
        logIssue('PUBLIC', pageInfo.path, 'TEST_ERROR', { message: error.message });
        logPageResult('PUBLIC', pageInfo.path, 'ERROR', { error: error.message });
        throw error;
      }
    });
  });
  
  test.afterAll(() => {
    saveIssuesReport();
  });
});
