// API Proxy Utility
// Handles proxying requests to backend FastAPI server

const http = require('http');
const https = require('https');

// DC Protocol: Backend URL Configuration
// For VM deployments (single container), use internal localhost
// For autoscale deployments (separate containers), use public URL
const isDeployment = Boolean(process.env.REPLIT_DEPLOYMENT || process.env.REPLIT_DEPLOYMENT_ID);

// DC Protocol: Check if this is autoscale (separate containers) or VM (same container)
// In autoscale, BACKEND_URL must be set to the public backend URL
// In VM, localhost works because both services share the container
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

console.log(`🔌 [DC-PROXY] Environment: ${isDeployment ? 'PRODUCTION' : 'DEVELOPMENT'}`);
console.log(`🔌 [DC-PROXY] Backend URL: ${BACKEND_URL}`);
console.log(`🔌 [DC-PROXY] REPLIT_DEPLOYMENT: ${process.env.REPLIT_DEPLOYMENT}`);
console.log(`🔌 [DC-PROXY] REPLIT_DEPLOYMENT_ID: ${process.env.REPLIT_DEPLOYMENT_ID}`);

// DC Protocol: Retry with exponential backoff for cold start resilience
function proxyWithRetry(req, res, url, attempt = 1, maxAttempts = 3) {
  const backendUrl = `${BACKEND_URL}${url}`;
  const parsedUrl = new URL(backendUrl);
  const requestId = `${Date.now()}-${Math.random()}`;
  
  // Clone headers but sanitize the host (production can have comma-separated domains)
  const safeHeaders = { ...req.headers };
  delete safeHeaders.host;
  
  const options = {
    protocol: parsedUrl.protocol,
    hostname: parsedUrl.hostname,
    port: parsedUrl.port || (parsedUrl.protocol === 'https:' ? 443 : 80),
    path: parsedUrl.pathname + parsedUrl.search,
    method: req.method,
    headers: {
      ...safeHeaders,
      host: parsedUrl.host
    },
    timeout: 30000
  };
  
  const client = parsedUrl.protocol === 'https:' ? https : http;
  
  const proxyReq = client.request(options, (backendRes) => {
    console.log(`[DC-PROXY-${requestId}] ✅ Connected to ${parsedUrl.hostname}:${parsedUrl.port || 8000}`);
    res.writeHead(backendRes.statusCode, backendRes.headers);
    backendRes.pipe(res);
  });
  
  proxyReq.on('error', (error) => {
    console.log(`[DC-PROXY-${requestId}] ⚠️ Host ${parsedUrl.hostname}:${parsedUrl.port || 8000} failed: ${error.message}`);
    
    if (attempt < maxAttempts) {
      const delay = Math.pow(2, attempt - 1) * 100; // 100ms, 200ms, 400ms
      console.log(`[DC-PROXY-${requestId}] Retry ${attempt}/${maxAttempts - 1} after ${delay}ms`);
      setTimeout(() => proxyWithRetry(req, res, url, attempt + 1, maxAttempts), delay);
    } else {
      console.log(`[DC-PROXY-${requestId}] ❌ Connection failed: ${error.message}`);
      res.writeHead(502, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        error: 'Bad Gateway',
        message: 'Backend not responding after retries',
        detail: isDeployment ? 'Please wait and try again' : error.message
      }));
    }
  });
  
  proxyReq.on('timeout', () => {
    proxyReq.destroy();
    if (attempt < maxAttempts) {
      console.log(`[DC-PROXY-${requestId}] Timeout, retrying...`);
      setTimeout(() => proxyWithRetry(req, res, url, attempt + 1, maxAttempts), 200);
    } else {
      res.writeHead(504, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Gateway Timeout', message: 'Backend request timed out' }));
    }
  });

  if (req.body) {
    proxyReq.write(typeof req.body === 'string' ? req.body : JSON.stringify(req.body));
  }
  req.pipe(proxyReq);
}

// Proxy request to backend (wrapper for backward compatibility)
function proxyToBackend(req, res, url) {
  proxyWithRetry(req, res, url, 1, 3);
}

module.exports = { proxyToBackend, BACKEND_URL };
