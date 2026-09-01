(function() {
    'use strict';
    
    const STORAGE_KEYS = {
        TOKEN: 'staff_token',
        USER: 'staff_user',
        COMPANY_ID: 'staff_company_id'
    };
    
    function isValidJwt(tok) {
        if (!tok || typeof tok !== 'string') return false;
        const parts = tok.split('.');
        return parts.length === 3 && parts[0].length > 5 && parts[1].length > 5;
    }

    function getToken() {
        // Multi-storage JWT token lookup with fallback hierarchy
        let tok = localStorage.getItem(STORAGE_KEYS.TOKEN) ||
                  localStorage.getItem('access_token') ||
                  localStorage.getItem('token') ||
                  sessionStorage.getItem(STORAGE_KEYS.TOKEN) ||
                  sessionStorage.getItem('access_token') ||
                  sessionStorage.getItem('token');
        
        // Defensive cookie fallback for staff_token / access_token / token if storage is transiently empty
        if (!tok || tok === 'null' || tok === 'undefined' || tok === '[object Object]' || tok.trim() === '') {
            const cookies = document.cookie.split(';').map(c => c.trim());
            const cookieMatch = cookies.find(c => c.startsWith('staff_token=') || c.startsWith('access_token=') || c.startsWith('token='));
            if (cookieMatch) {
                tok = cookieMatch.split('=')[1];
                if (tok) {
                    try { tok = decodeURIComponent(tok); } catch(e) {}
                }
            }
        }
        
        if (tok) {
            tok = tok.trim();
            while (tok.toLowerCase().startsWith('bearer ')) {
                tok = tok.slice(7).trim();
            }
            tok = tok.replace(/^["']|["']$/g, '').trim();
        }
        
        // Validation: Must be a valid 3-part JWT string
        if (tok && isValidJwt(tok)) {
            // Self-heal localStorage if it was quote-wrapped or dirty
            try {
                if (localStorage.getItem(STORAGE_KEYS.TOKEN) !== tok) {
                    localStorage.setItem(STORAGE_KEYS.TOKEN, tok);
                }
            } catch(e) {}
            return tok;
        }
        
        // If token exists but is corrupted (not valid JWT), clear it
        if (tok) {
            console.warn('[DC-FETCH] Corrupted non-JWT token detected in storage. Auto-clearing...');
            clearSession();
        }
        return null;
    }
    
    function getCompanyId() {
        const user = JSON.parse(localStorage.getItem(STORAGE_KEYS.USER) || '{}');
        return user.company_id || localStorage.getItem(STORAGE_KEYS.COMPANY_ID) || '1';
    }
    
    function clearSession() {
        localStorage.removeItem(STORAGE_KEYS.TOKEN);
        localStorage.removeItem(STORAGE_KEYS.USER);
    }
    
    function redirectToLogin() {
        const rawUser = localStorage.getItem('staff_user');
        let isSaaSTenant = false;
        if (rawUser) {
            try {
                const u = JSON.parse(rawUser);
                if (u.staff_type === 'TENANT_ADMIN' || u.staff_type === 'SAAS_CLIENT' || (u.base_company_id && u.base_company_id !== 4 && u.base_company_id !== 88 && u.base_company_id !== 1)) {
                    isSaaSTenant = true;
                }
            } catch (_) {}
        }
        const currentPath = window.location.pathname + window.location.search;
        console.log('[DC-FETCH] Redirecting to login with redirect:', currentPath);
        if (isSaaSTenant) {
            window.location.href = '/saas/login?redirect=' + encodeURIComponent(currentPath);
        } else {
            window.location.href = '/staff/login?redirect=' + encodeURIComponent(currentPath);
        }
    }
    
    function handleAuthFailure(status, errorDetail) {
        console.warn('[DC-FETCH] Auth failure detected:', status, errorDetail);
        clearSession();
        redirectToLogin();
    }
    
    let isRefreshingToken = false;
    let refreshPromise = null;
    
    async function silentRefreshToken() {
        if (isRefreshingToken) return refreshPromise;
        const currentTok = getToken();
        if (!currentTok) return null;
        
        isRefreshingToken = true;
        console.log('[DC-FETCH] Attempting transparent token refresh...');
        
        refreshPromise = (async () => {
            try {
                const res = await fetch('/api/v1/staff/auth/refresh', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${currentTok}`,
                        'Content-Type': 'application/json'
                    }
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.access_token) {
                        localStorage.setItem(STORAGE_KEYS.TOKEN, data.access_token);
                        document.cookie = `staff_token=${data.access_token}; path=/; max-age=86400; SameSite=Lax`;
                        console.log('[DC-FETCH] Transparent token refresh successful!');
                        return data.access_token;
                    }
                } else {
                    console.warn('[DC-FETCH] Token refresh endpoint returned status:', res.status);
                }
            } catch (e) {
                console.warn('[DC-FETCH] Transparent token refresh failed:', e);
            } finally {
                isRefreshingToken = false;
                refreshPromise = null;
            }
            return null;
        })();
        
        return refreshPromise;
    }
    
    // Proactive background refresh every 5 minutes if token exp <= 10 mins
    function checkAndProactivelyRefreshToken() {
        const token = getToken();
        if (!token) return;
        try {
            const parts = token.split('.');
            if (parts.length === 3) {
                const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
                if (payload.exp) {
                    const timeUntilExpMs = (payload.exp * 1000) - Date.now();
                    // If token expires in less than 10 minutes, refresh proactively
                    if (timeUntilExpMs > 0 && timeUntilExpMs <= (10 * 60 * 1000)) {
                        console.log('[DC-FETCH] Proactive token refresh triggered (expires in', Math.round(timeUntilExpMs / 1000), 's)');
                        silentRefreshToken();
                    }
                }
            }
        } catch(e) {}
    }
    
    // Run proactive check every 5 minutes
    setInterval(checkAndProactivelyRefreshToken, 5 * 60 * 1000);
    setTimeout(checkAndProactivelyRefreshToken, 3000);

    async function staffFetch(url, options = {}) {
        let token = getToken();
        const companyId = getCompanyId();
        
        if (!token) {
            console.warn('[DC-FETCH] No token available');
            redirectToLogin();
            throw new Error('NO_TOKEN');
        }
        
        const defaultHeaders = {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'X-Company-ID': companyId
        };
        
        const mergedHeaders = { ...defaultHeaders, ...options.headers };
        
        if (options.body instanceof FormData) {
            delete mergedHeaders['Content-Type'];
        }
        
        const fetchOptions = {
            ...options,
            headers: mergedHeaders
        };
        
        try {
            let response = await fetch(url, fetchOptions);
            
            if (response.status === 401) {
                let errorDetail = 'Authentication failed';
                try {
                    const errorData = await response.clone().json();
                    errorDetail = errorData.detail || errorData.message || errorDetail;
                } catch (e) {}
                
                // DC Protocol: NDA_PENDING must NEVER trigger auth failure or token removal
                if (errorDetail === 'NDA_PENDING') {
                    return response;
                }
                
                // Do NOT immediately log out! Attempt transparent silent refresh first!
                console.log('[DC-FETCH] HTTP 401 received. Attempting transparent token refresh for:', url);
                const newToken = await silentRefreshToken();
                if (newToken) {
                    // Refresh succeeded! Retry original request with fresh token
                    fetchOptions.headers['Authorization'] = `Bearer ${newToken}`;
                    console.log('[DC-FETCH] Retrying original request with refreshed token...');
                    const retryResponse = await fetch(url, fetchOptions);
                    if (retryResponse.ok || retryResponse.status !== 401) {
                        return retryResponse;
                    }
                }
                
                // If refresh failed or retry still returns 401, check if session is truly dead
                handleAuthFailure(response.status, errorDetail);
                throw new Error('AUTH_EXPIRED');
            }
            
            return response;
        } catch (error) {
            if (error.message === 'AUTH_EXPIRED' || error.message === 'NO_TOKEN') {
                throw error;
            }
            
            console.error('[DC-FETCH] Network error:', error);
            throw error;
        }
    }
    
    async function staffFetchJson(url, options = {}) {
        const response = await staffFetch(url, options);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Request failed' }));
            // WVV Protocol: Preserve structured error data for validation errors
            // If detail is an object (validation error), throw it directly so frontend can access type, message, resolution_url, etc.
            const detail = errorData.detail;
            if (response.status === 403 && (errorData.module_unsubscribed || (typeof detail === 'string' && detail.includes('not activated')))) {
                // Dispatch friendly module spotlight event
                window.dispatchEvent(new CustomEvent('mnr:module_unsubscribed', {
                    detail: {
                        module_code: errorData.module_code || 'PREMIUM_MODULE',
                        module_name: errorData.module_name || 'Advanced Module',
                        message: errorData.message || detail
                    }
                }));
            }
            if (detail && typeof detail === 'object' && detail.type) {
                // Structured validation error - throw the object itself
                const error = new Error(detail.message || 'Validation error');
                error.validationError = detail;  // Preserve full structure
                error.type = detail.type;
                error.severity = detail.severity;
                error.resolution = detail.resolution;
                error.resolution_url = detail.resolution_url;
                throw error;
            }
            // Standard string error
            throw new Error(typeof detail === 'string' ? detail : `Request failed with status ${response.status}`);
        }
        return response.json();
    }
    
    function getAuthHeaders() {
        const token = getToken();
        const companyId = getCompanyId();
        return {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'X-Company-ID': companyId
        };
    }
    
    function buildApiUrl(endpoint, params = {}) {
        const companyId = getCompanyId();
        const urlParams = new URLSearchParams({ company_id: companyId, ...params });
        const separator = endpoint.includes('?') ? '&' : '?';
        return `${endpoint}${separator}${urlParams.toString()}`;
    }
    
    window.StaffFetch = {
        fetch: staffFetch,
        fetchJson: staffFetchJson,
        getToken: getToken,
        getCompanyId: getCompanyId,
        getAuthHeaders: getAuthHeaders,
        buildApiUrl: buildApiUrl,
        clearSession: clearSession,
        redirectToLogin: redirectToLogin
    };
    
    // DC_FIX: Only set window.staffFetch if NOT already defined by staff-token-manager.js
    // This prevents overwriting the better version with global interceptors
    // Silent operation - no console logs for normal behavior
    if (typeof window.staffFetch !== 'function') {
        window.staffFetch = staffFetch;
    }
    
    if (typeof window.staffFetchJson !== 'function') {
        window.staffFetchJson = staffFetchJson;
    }
})();
