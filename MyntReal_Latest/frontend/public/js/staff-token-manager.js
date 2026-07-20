(function() {
    'use strict';
    
    const TOKEN_REFRESH_BUFFER_MS = 5 * 60 * 1000;
    const TOKEN_CHECK_INTERVAL_MS = 60 * 1000;
    const API_BASE = '/api/v1';
    
    let refreshTimer = null;
    let isRefreshing = false;
    let refreshPromise = null;
    
    function parseJwt(token) {
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));
            return JSON.parse(jsonPayload);
        } catch (e) {
            console.error('[DC_TOKEN] Failed to parse JWT:', e);
            return null;
        }
    }
    
    function getTokenExpiry(token) {
        const payload = parseJwt(token);
        if (payload && payload.exp) {
            return payload.exp * 1000;
        }
        return null;
    }
    
    function isTokenExpiringSoon(token) {
        const expiry = getTokenExpiry(token);
        if (!expiry) return true;
        return Date.now() >= (expiry - TOKEN_REFRESH_BUFFER_MS);
    }
    
    function isTokenExpired(token) {
        const expiry = getTokenExpiry(token);
        if (!expiry) return true;
        return Date.now() >= expiry;
    }
    
    async function refreshToken() {
        if (isRefreshing) {
            return refreshPromise;
        }
        
        const token = localStorage.getItem('staff_token');
        if (!token) {
            console.warn('[DC_TOKEN] No token to refresh');
            return null;
        }
        
        isRefreshing = true;
        console.log('[DC_TOKEN] Refreshing token...');
        
        refreshPromise = fetch(`${API_BASE}/staff/auth/refresh`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        })
        .then(async response => {
            if (response.ok) {
                const data = await response.json();
                if (data.access_token) {
                    localStorage.setItem('staff_token', data.access_token);
                    document.cookie = `staff_token=${data.access_token}; path=/; max-age=86400; SameSite=Lax`;
                    console.log('[DC_TOKEN] Token refreshed successfully, expires in', data.expires_in_hours, 'hours');
                    scheduleNextRefresh(data.access_token);
                    return data.access_token;
                }
            } else {
                const error = await response.json();
                console.error('[DC_TOKEN] Refresh failed:', error.detail);
                
                if (response.status === 401 || response.status === 403) {
                    handleSessionExpired(error.detail);
                }
                return null;
            }
        })
        .catch(error => {
            console.error('[DC_TOKEN] Refresh network error:', error);
            return null;
        })
        .finally(() => {
            isRefreshing = false;
            refreshPromise = null;
        });
        
        return refreshPromise;
    }
    
    function handleSessionExpired(reason) {
        // DC Protocol: Check sandbox mode
        const sandboxMode = localStorage.getItem('sandbox_mode');
        
        // In sandbox mode, don't redirect - just log the warning
        if (sandboxMode) {
            console.warn('[DC_TOKEN] Session expired (sandbox mode - no redirect):', reason);
            return;
        }
        
        console.warn('[DC_TOKEN] Session expired:', reason);
        localStorage.removeItem('staff_token');
        localStorage.removeItem('staff_user');
        document.cookie = 'staff_token=; path=/; max-age=0';
        
        const path = window.location.pathname;
        const isStaffPage = path.includes('/staff/') && !path.includes('/staff/login');
        const isRvzPage = path.startsWith('/rvz/') || path.startsWith('/crm');
        const isAdminPage = path.includes('/admin');
        const isVgkPage = path.includes('/vgk');
        const isFinancePage = path.includes('/finance');
        
        if (isStaffPage || isRvzPage || isAdminPage || isVgkPage || isFinancePage) {
            const currentPath = window.location.pathname + window.location.search;
            console.log('[DC_TOKEN] Redirecting to login with redirect:', currentPath);
            window.location.href = '/staff/login?redirect=' + encodeURIComponent(currentPath);
        }
    }
    
    function scheduleNextRefresh(token) {
        if (refreshTimer) {
            clearTimeout(refreshTimer);
        }
        
        const expiry = getTokenExpiry(token);
        if (!expiry) return;
        
        const refreshTime = expiry - TOKEN_REFRESH_BUFFER_MS - Date.now();
        
        if (refreshTime > 0) {
            console.log('[DC_TOKEN] Next refresh scheduled in', Math.round(refreshTime / 60000), 'minutes');
            refreshTimer = setTimeout(() => {
                refreshToken();
            }, refreshTime);
        }
    }
    
    function startTokenMonitoring() {
        const token = localStorage.getItem('staff_token');
        if (!token) return;
        
        if (isTokenExpired(token)) {
            refreshToken();
        } else if (isTokenExpiringSoon(token)) {
            refreshToken();
        } else {
            scheduleNextRefresh(token);
        }
        
        setInterval(() => {
            const currentToken = localStorage.getItem('staff_token');
            if (currentToken && isTokenExpiringSoon(currentToken) && !isRefreshing) {
                refreshToken();
            }
        }, TOKEN_CHECK_INTERVAL_MS);
    }
    
    async function staffFetch(url, options = {}) {
        let token = localStorage.getItem('staff_token');
        
        if (!token) {
            console.warn('[DC_TOKEN] No token available for request');
            handleSessionExpired('No authentication token');
            throw new Error('Not authenticated');
        }
        
        if (isTokenExpired(token) || isTokenExpiringSoon(token)) {
            const newToken = await refreshToken();
            if (newToken) {
                token = newToken;
            } else {
                throw new Error('Token refresh failed');
            }
        }
        
        // DC Protocol: Auto-add Content-Type for JSON body requests
        const headers = {
            ...options.headers,
            'Authorization': `Bearer ${token}`
        };
        
        // Auto-detect JSON body and add Content-Type header if not already set
        if (options.body && typeof options.body === 'string' && !headers['Content-Type']) {
            try {
                JSON.parse(options.body);
                headers['Content-Type'] = 'application/json';
            } catch (e) {
                // Not JSON, leave Content-Type as-is
            }
        }
        
        const response = await fetch(url, { ...options, headers });
        
        if (response.status === 401) {
            const error = await response.clone().json().catch(() => ({}));
            const errorDetail = (error.detail || '').toUpperCase();
            
            const authErrors = [
                'TOKEN_EXPIRED',
                'INVALID_TOKEN',
                'TOKEN_INVALID',
                'NOT_AUTHENTICATED',
                'COULD NOT VALIDATE CREDENTIALS',
                'INVALID AUTHENTICATION CREDENTIALS',
                'SIGNATURE HAS EXPIRED',
                'TOKEN HAS EXPIRED'
            ];
            
            const isAuthError = authErrors.some(e => errorDetail.includes(e));
            
            if (errorDetail.includes('TOKEN_EXPIRED')) {
                const newToken = await refreshToken();
                if (newToken) {
                    const refreshedHeaders = {
                        ...options.headers,
                        'Authorization': `Bearer ${newToken}`
                    };
                    if (options.body && typeof options.body === 'string' && !refreshedHeaders['Content-Type']) {
                        try {
                            JSON.parse(options.body);
                            refreshedHeaders['Content-Type'] = 'application/json';
                        } catch (e) {}
                    }
                    console.log('[DC_TOKEN] Retrying request with refreshed token');
                    return fetch(url, { ...options, headers: refreshedHeaders });
                }
            }
            
            if (isAuthError) {
                handleSessionExpired(error.detail || 'Authentication failed');
            }
        }
        
        return response;
    }
    
    async function staffFetchJson(url, options = {}) {
        const defaultHeaders = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        const response = await staffFetch(url, {
            ...options,
            headers: defaultHeaders
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Request failed' }));
            
            // DC Protocol (Dec 22, 2025): Handle structured error objects
            // Backend may return detail as object for validation errors
            let errorMessage = `HTTP ${response.status}`;
            if (errorData.detail) {
                if (typeof errorData.detail === 'object') {
                    // Extract message from structured validation error
                    errorMessage = errorData.detail.message || JSON.stringify(errorData.detail);
                } else {
                    errorMessage = errorData.detail;
                }
            }
            
            const error = new Error(errorMessage);
            error.status = response.status;
            error.data = errorData;
            // DC Protocol: Attach validation error object for frontend handlers
            if (typeof errorData.detail === 'object') {
                error.validationError = errorData.detail;
            }
            throw error;
        }
        
        return response.json();
    }
    
    function getValidToken() {
        const token = localStorage.getItem('staff_token');
        if (!token) return null;
        
        if (isTokenExpired(token)) {
            return null;
        }
        
        return token;
    }
    
    function init() {
        const path = window.location.pathname;
        const isStaffPage = path.includes('/staff/') && !path.includes('/staff/login');
        const isRvzPage = path.startsWith('/rvz/') || path.startsWith('/crm');
        const isAdminPage = path.includes('/admin');
        const isVgkPage = path.includes('/vgk');
        const isFinancePage = path.includes('/finance');
        
        if (isStaffPage || isRvzPage || isAdminPage || isVgkPage || isFinancePage) {
            startTokenMonitoring();
            console.log('[DC_TOKEN] Token manager initialized for path:', path);
            
            interceptFetch();
            interceptXMLHttpRequest();
        }
    }
    
    async function ensureValidToken() {
        let token = localStorage.getItem('staff_token');
        if (!token) return null;
        
        if (isTokenExpired(token) || isTokenExpiringSoon(token)) {
            const newToken = await refreshToken();
            return newToken || null;
        }
        return token;
    }
    
    function interceptFetch() {
        const originalFetch = window.fetch;
        window.fetch = async function(url, options = {}) {
            const urlStr = typeof url === 'string' ? url : (url instanceof Request ? url.url : '');
            const isApiCall = urlStr.includes('/api/');
            const isAuthEndpoint = urlStr.includes('/auth/login') || urlStr.includes('/auth/refresh');
            
            if (isApiCall && !isAuthEndpoint) {
                const token = await ensureValidToken();
                const userData = JSON.parse(localStorage.getItem('staff_user') || '{}');
                const companyId = userData.company_id || '1';
                
                if (token) {
                    if (url instanceof Request) {
                        const newHeaders = new Headers(url.headers);
                        if (!newHeaders.has('Authorization')) {
                            newHeaders.set('Authorization', `Bearer ${token}`);
                            newHeaders.set('X-Company-ID', companyId);
                        }
                        url = new Request(url, { headers: newHeaders });
                    } else {
                        options = options || {};
                        const existingHeaders = options.headers || {};
                        
                        const hasAuthHeader = existingHeaders['Authorization'] || 
                                             existingHeaders['authorization'] ||
                                             (existingHeaders instanceof Headers && existingHeaders.has('Authorization'));
                        
                        if (!hasAuthHeader) {
                            if (existingHeaders instanceof Headers) {
                                existingHeaders.set('Authorization', `Bearer ${token}`);
                                existingHeaders.set('X-Company-ID', companyId);
                            } else {
                                options.headers = {
                                    ...existingHeaders,
                                    'Authorization': `Bearer ${token}`,
                                    'X-Company-ID': companyId
                                };
                            }
                        }
                    }
                }
            }
            
            const response = await originalFetch(url, options);
            
            if (response.status === 401 && isApiCall && !isAuthEndpoint) {
                const clonedResponse = response.clone();
                try {
                    const error = await clonedResponse.json();
                    const errorDetail = (error.detail || '').toUpperCase();
                    
                    const authErrors = [
                        'TOKEN_EXPIRED',
                        'INVALID_TOKEN',
                        'TOKEN_INVALID',
                        'NOT_AUTHENTICATED',
                        'COULD NOT VALIDATE CREDENTIALS',
                        'INVALID AUTHENTICATION CREDENTIALS',
                        'SIGNATURE HAS EXPIRED',
                        'TOKEN HAS EXPIRED'
                    ];
                    
                    const isAuthError = authErrors.some(e => errorDetail.includes(e));
                    
                    if (isAuthError) {
                        console.warn('[DC_TOKEN] Auth failure detected:', error.detail, '- attempting refresh before redirect');
                        // DC Fix (Apr 2026): Try to refresh the token before giving up and redirecting.
                        // This handles the case where the token just expired mid-session.
                        const newToken = await refreshToken().catch(() => null);
                        if (!newToken) {
                            handleSessionExpired(error.detail);
                        } else {
                            console.log('[DC_TOKEN] Token refreshed after 401 - session preserved');
                        }
                    } else {
                        console.log('[DC_TOKEN] 401 non-auth error (not clearing session):', error.detail);
                    }
                } catch {
                    console.log('[DC_TOKEN] 401 response without parseable error body');
                }
            }
            
            return response;
        };
        console.log('[DC_TOKEN] Fetch interceptor installed (WVV+DC Protocol)');
    }
    
    function interceptXMLHttpRequest() {
        const originalOpen = XMLHttpRequest.prototype.open;
        const originalSend = XMLHttpRequest.prototype.send;
        
        XMLHttpRequest.prototype.open = function(method, url, async, user, password) {
            this._dcUrl = url;
            this._dcMethod = method;
            this._dcAsync = async !== false;
            return originalOpen.apply(this, arguments);
        };
        
        XMLHttpRequest.prototype.send = function(body) {
            const xhr = this;
            const urlStr = xhr._dcUrl || '';
            const isApiCall = urlStr.includes('/api/');
            const isAuthEndpoint = urlStr.includes('/auth/login') || urlStr.includes('/auth/refresh');
            
            if (isApiCall && !isAuthEndpoint) {
                let token = localStorage.getItem('staff_token');
                const userData = JSON.parse(localStorage.getItem('staff_user') || '{}');
                const companyId = userData.company_id || '1';
                
                if (token) {
                    try {
                        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
                        xhr.setRequestHeader('X-Company-ID', companyId);
                    } catch (e) {
                        console.warn('[DC_TOKEN] XHR header already set');
                    }
                }
            }
            
            xhr.addEventListener('load', function() {
                if (xhr.status === 401 && isApiCall && !isAuthEndpoint) {
                    try {
                        const error = JSON.parse(xhr.responseText);
                        const errorDetail = (error.detail || '').toUpperCase();
                        
                        const authErrors = [
                            'TOKEN_EXPIRED', 'INVALID_TOKEN', 'TOKEN_INVALID',
                            'NOT_AUTHENTICATED', 'COULD NOT VALIDATE CREDENTIALS'
                        ];
                        
                        if (authErrors.some(e => errorDetail.includes(e))) {
                            console.warn('[DC_TOKEN] XHR Auth failure:', error.detail);
                            handleSessionExpired(error.detail);
                        }
                    } catch {}
                }
            });
            
            return originalSend.call(xhr, body);
        };
        console.log('[DC_TOKEN] XMLHttpRequest interceptor installed (for jQuery/$.ajax)');
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // DC Protocol (Dec 22, 2025): Shared file upload helper with token validation
    // Ensures valid token before XHR upload, refreshes if expired, aborts if invalid
    async function uploadFileWithProgress(url, file, onProgress, extraFields = {}) {
        // First try to get a valid (non-expired) token
        let validToken = getValidToken();
        
        if (!validToken) {
            // Token is expired - attempt refresh
            console.log('[DC_TOKEN] Token expired, attempting refresh before upload...');
            try {
                await refreshToken();
            } catch (refreshError) {
                console.error('[DC_TOKEN] Token refresh failed:', refreshError);
                throw new Error('Your session has expired. Please refresh the page and try again.');
            }
            
            // CRITICAL: Re-validate token after refresh using getValidToken()
            // This ensures we only proceed with a valid, non-expired token
            validToken = getValidToken();
            
            if (!validToken) {
                // Refresh did not produce a valid token - abort
                console.error('[DC_TOKEN] No valid token after refresh attempt');
                throw new Error('Your session has expired. Please refresh the page and try again.');
            }
            
            console.log('[DC_TOKEN] Token refreshed successfully for upload');
        }
        
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            const formData = new FormData();
            formData.append('file', file);
            
            // Add any extra fields
            for (const [key, value] of Object.entries(extraFields)) {
                formData.append(key, value);
            }
            
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable && onProgress) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    onProgress(percent, file.name);
                }
            });
            
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        resolve(JSON.parse(xhr.responseText));
                    } catch {
                        resolve({ success: true });
                    }
                } else {
                    try {
                        const error = JSON.parse(xhr.responseText);
                        reject(new Error(error.detail || `Upload failed: ${xhr.status}`));
                    } catch {
                        reject(new Error(`Upload failed: ${xhr.status}`));
                    }
                }
            });
            
            xhr.addEventListener('error', () => reject(new Error('Upload failed: Network error')));
            xhr.addEventListener('abort', () => reject(new Error('Upload cancelled')));
            
            xhr.open('POST', url);
            xhr.setRequestHeader('Authorization', `Bearer ${validToken}`);
            
            // Add company ID header
            const userData = JSON.parse(localStorage.getItem('staff_user') || '{}');
            const companyId = userData.company_id || '1';
            xhr.setRequestHeader('X-Company-ID', companyId);
            
            xhr.send(formData);
        });
    }
    
    window.StaffTokenManager = {
        refreshToken,
        staffFetch,
        staffFetchJson,
        getValidToken,
        isTokenExpired,
        isTokenExpiringSoon,
        startTokenMonitoring,
        uploadFileWithProgress
    };
    
    window.staffFetch = staffFetch;
    window.staffFetchJson = staffFetchJson;
    window.uploadFileWithProgress = uploadFileWithProgress;
    
})();
