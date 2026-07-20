const http = require('http');

// Simulate authenticated request to banner oversight page
const options = {
  hostname: 'localhost',
  port: 5000,
  path: '/rvz/banner-oversight',
  method: 'GET',
  headers: {
    'Cookie': 'sessionToken=test_token_12345'
  }
};

const req = http.request(options, (res) => {
  let data = '';
  
  res.on('data', (chunk) => {
    data += chunk;
  });
  
  res.on('end', () => {
    console.log('✅ Response Status:', res.statusCode);
    console.log('✅ Response Headers:', JSON.stringify(res.headers, null, 2));
    
    // Check for JavaScript errors in the HTML
    if (data.includes('SyntaxError')) {
      console.log('❌ FOUND SYNTAX ERROR IN PAGE');
      const lines = data.split('\n');
      lines.forEach((line, idx) => {
        if (line.includes('SyntaxError') || line.includes('const sessionToken')) {
          console.log(`Line ${idx}: ${line}`);
        }
      });
    }
    
    // Check if script contains our expected code
    if (data.includes('🚀 Banner Oversight - NEW PAGE LOADED')) {
      console.log('✅ Found page initialization code');
    } else {
      console.log('❌ Page initialization code NOT found');
    }
    
    if (data.includes('const sessionToken')) {
      console.log('✅ Found sessionToken declaration');
    } else {
      console.log('❌ sessionToken declaration NOT found');
    }
    
    if (data.includes('loadBanners()')) {
      console.log('✅ Found loadBanners() call');
    } else {
      console.log('❌ loadBanners() call NOT found');
    }
    
    // Check for template literal issues
    if (data.includes('${BUILD_ID}') || data.includes('${sessionToken}')) {
      console.log('❌ UNRESOLVED TEMPLATE LITERALS FOUND - will cause errors');
    } else {
      console.log('✅ No unresolved template literals');
    }
  });
});

req.on('error', (e) => {
  console.error('❌ Request failed:', e.message);
});

req.end();
