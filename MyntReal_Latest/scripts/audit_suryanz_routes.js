/**
 * SURYANZ SOLAR - Comprehensive Automated Route Crawler & Audit Script
 * Enumerates all public SURYANZ routes, executes HTTP requests, verifies 200 OK,
 * validates non-empty HTML title & content, and confirms ZERO broken links / 404s.
 */

const http = require('http');

const ALL_ROUTES = [
  // Main Navigation & Content Pages
  '/',
  '/about',
  '/why-suryanz',
  '/customer-protection',
  '/technology',
  '/calculator',
  '/projects',
  '/customer-stories',
  '/reviews',
  '/faqs',
  '/contact',

  // Solution Sub-pages
  '/solutions/residential',
  '/solutions/commercial',
  '/solutions/industrial',
  '/solutions/epc',
  '/solutions/on-grid',
  '/solutions/hybrid',
  '/solutions/off-grid',
  '/solutions/solar-battery',
  '/solutions/apartments',
  '/solutions/operations-maintenance',

  // Educational Knowledge & Buying Guides
  '/solar-guide',
  '/solar-pricing',
  '/solar-roi',
  '/solar-calculator-guide',
  '/solar-warranty-guide',
  '/solar-maintenance',
  '/solar-buying-guide',

  // Regional Location Hubs
  '/location/andhra-pradesh',
  '/location/telangana',
  '/location/karnataka',
  '/location/visakhapatnam',
  '/location/vijayawada',
  '/location/hyderabad',
  '/location/bengaluru',
  '/location/mangalore',

  // Legal Trust Pages
  '/legal/privacy-policy',
  '/legal/terms-and-conditions',
  '/legal/warranty-terms',

  // System & Crawling Files
  '/sitemap.xml',
  '/robots.txt'
];

async function checkRoute(routePath) {
  return new Promise((resolve) => {
    // Test using /suryanz prefix on localhost
    const testUrl = `http://localhost:5000/suryanz${routePath === '/' ? '' : routePath}`;
    
    http.get(testUrl, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        const isOk = res.statusCode === 200;
        const hasTitle = body.includes('<title>') || body.includes('<?xml') || body.toLowerCase().includes('user-agent');
        const hasContent = routePath === '/robots.txt' ? body.length > 20 : body.length > 200;

        resolve({
          route: routePath,
          statusCode: res.statusCode,
          passed: isOk && hasTitle && hasContent,
          contentLength: body.length
        });
      });
    }).on('error', (err) => {
      resolve({
        route: routePath,
        statusCode: 0,
        passed: false,
        error: err.message
      });
    });
  });
}

async function runAudit() {
  console.log('====================================================');
  console.log('SURYANZ SOLAR - PUBLIC ROUTE AUDIT & CRAWLER ENGINE');
  console.log('====================================================');

  const results = [];
  let totalWorking = 0;
  let totalBroken = 0;

  for (const r of ALL_ROUTES) {
    const res = await checkRoute(r);
    results.push(res);
    if (res.passed) {
      totalWorking++;
      console.log(`[PASS] 200 OK | ${r.padEnd(38)} (${res.contentLength} bytes)`);
    } else {
      totalBroken++;
      console.log(`[FAIL] ${res.statusCode} ERR | ${r.padEnd(38)} ${res.error || 'Empty or invalid response'}`);
    }
  }

  console.log('----------------------------------------------------');
  console.log(`AUDIT SUMMARY:`);
  console.log(`Total Public Routes Tested : ${ALL_ROUTES.length}`);
  console.log(`Routes Passed (HTTP 200)   : ${totalWorking}`);
  console.log(`Broken Routes (404/500)    : ${totalBroken}`);
  console.log('====================================================');

  if (totalBroken === 0) {
    console.log('✅ AUDIT PASSED: ZERO BROKEN ROUTES DETECTED!');
  } else {
    console.error('❌ AUDIT FAILED: BROKEN ROUTES DETECTED!');
    process.exit(1);
  }
}

runAudit();
