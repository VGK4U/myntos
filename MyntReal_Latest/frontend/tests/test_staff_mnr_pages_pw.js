/**
 * Test Staff MNR Pages Integration
 * DC Protocol (Dec 28, 2025)
 * Uses Playwright for browser testing
 */
const { chromium } = require('playwright');

const BASE_URL = 'http://127.0.0.1:5000';
const STAFF_EMPLOYEE_ID = process.env.TEST_STAFF_EMPLOYEE_ID || 'MR10001';
const STAFF_PASSWORD = process.env.TEST_STAFF_PASSWORD || 'password';

const MNR_PAGES = [
    { path: '/staff/mnr/users', title: 'All Users' },
    { path: '/staff/mnr/user-status', title: 'User Status' },
    { path: '/staff/mnr/withdrawal/approvals', title: 'Withdrawal Approvals' },
    { path: '/staff/mnr/withdrawal/history', title: 'Withdrawal History' },
    { path: '/staff/mnr/kyc-management', title: 'KYC Management' },
    { path: '/staff/mnr/bank-pending', title: 'Bank Pending' },
    { path: '/staff/mnr/bank-all', title: 'All Bank Details' },
    { path: '/staff/mnr/announcements/view', title: 'Announcements' },
    { path: '/staff/mnr/feedback/pending', title: 'Pending Announcements' },
    { path: '/staff/mnr/announcement/create', title: 'Create Announcement' },
    { path: '/staff/mnr/banners-management', title: 'Banners' },
    { path: '/staff/mnr/popups', title: 'Popups' },
    { path: '/staff/mnr/pin-review', title: 'PIN Review' },
    { path: '/staff/mnr/password-reset', title: 'Password Reset' },
    { path: '/staff/mnr/reports', title: 'Reports' },
    { path: '/staff/mnr/emergency-wallet', title: 'Emergency Wallet' },
    { path: '/staff/accounts/expense-categories', title: 'Expense Categories' },
    { path: '/staff/mnr/log-reports', title: 'Log Reports' },
    { path: '/staff/mnr/tickets-management', title: 'Tickets Management' },
    { path: '/staff/mnr/tickets-assigned', title: 'Assigned Tickets' },
];

async function main() {
    console.log('='.repeat(60));
    console.log('Staff MNR Pages Integration Test');
    console.log('='.repeat(60));

    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    const page = await context.newPage();
    
    const consoleErrors = [];
    page.on('console', msg => {
        if (msg.type() === 'error') {
            consoleErrors.push(msg.text());
        }
    });

    const results = { passed: 0, failed: 0, errors: [] };

    try {
        // Login as staff
        console.log(`\n[LOGIN] Logging in as ${STAFF_EMPLOYEE_ID}...`);
        await page.goto(`${BASE_URL}/staff/login`);
        await page.waitForLoadState('networkidle');
        
        await page.fill('#employee_id', STAFF_EMPLOYEE_ID);
        await page.fill('#password', STAFF_PASSWORD);
        await page.click('button[type="submit"]');
        
        await page.waitForTimeout(3000);
        
        const currentUrl = page.url();
        if (!currentUrl.includes('/staff/')) {
            console.log(`[LOGIN] ✗ Login failed - current URL: ${currentUrl}`);
            return;
        }
        console.log('[LOGIN] ✓ Staff login successful');

        // Test each MNR page
        for (const { path, title } of MNR_PAGES) {
            console.log(`\n[TEST] Testing: ${title} (${path})`);
            consoleErrors.length = 0;
            
            const pageErrors = [];
            
            try {
                await page.goto(`${BASE_URL}${path}`, { timeout: 15000 });
                await page.waitForLoadState('networkidle', { timeout: 10000 });
                
                const finalUrl = page.url();
                
                if (finalUrl.includes('/staff/login')) {
                    pageErrors.push('Redirected to login (auth failed)');
                }
                
                const pageContent = await page.content();
                const lowerContent = pageContent.toLowerCase();
                
                if (lowerContent.includes('coming soon')) {
                    pageErrors.push("Page shows 'Coming Soon'");
                }
                
                if (lowerContent.includes('page not found') || lowerContent.includes('404')) {
                    pageErrors.push('Page not found (404)');
                }
                
                const sidebar = await page.$('#staffSidebar');
                if (!sidebar) {
                    pageErrors.push('Staff sidebar not found');
                }
                
                const mainContent = await page.$('#mainContent');
                if (!mainContent) {
                    pageErrors.push('Main content container not found');
                }
                
                // Check for severe JS errors (ignore favicon and minor issues)
                const severeErrors = consoleErrors.filter(e => 
                    !e.toLowerCase().includes('favicon') && 
                    !e.toLowerCase().includes('manifest')
                );
                if (severeErrors.length > 0) {
                    pageErrors.push(`JS Errors: ${severeErrors.slice(0, 2).join('; ').substring(0, 100)}`);
                }
                
            } catch (e) {
                pageErrors.push(`Exception: ${e.message.substring(0, 100)}`);
            }
            
            if (pageErrors.length === 0) {
                console.log(`[TEST] ✓ ${title}: OK`);
                results.passed++;
            } else {
                console.log(`[TEST] ✗ ${title}: ${pageErrors.join('; ')}`);
                results.failed++;
                results.errors.push({ page: title, path, errors: pageErrors });
            }
        }

    } finally {
        await browser.close();
        console.log('\n[CLEANUP] Browser closed');
    }

    // Summary
    console.log('\n' + '='.repeat(60));
    console.log('TEST SUMMARY');
    console.log('='.repeat(60));
    console.log(`Passed: ${results.passed}/${MNR_PAGES.length}`);
    console.log(`Failed: ${results.failed}/${MNR_PAGES.length}`);
    
    if (results.errors.length > 0) {
        console.log('\nFailed Pages:');
        for (const err of results.errors) {
            console.log(`  - ${err.page} (${err.path})`);
            for (const e of err.errors) {
                console.log(`      ${e}`);
            }
        }
    }
    
    process.exit(results.failed > 0 ? 1 : 0);
}

main().catch(console.error);
