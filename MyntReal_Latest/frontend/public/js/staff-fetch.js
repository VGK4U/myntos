(function() {
    'use strict';
    
    const STORAGE_KEYS = {
        TOKEN: 'staff_token',
        USER: 'staff_user',
        COMPANY_ID: 'staff_company_id'
    };
    
    function getToken() {
        // Sole staff authority: localStorage.staff_token
        let tok = localStorage.getItem(STORAGE_KEYS.TOKEN);
        
        // Defensive cookie fallback for staff_token ONLY if localStorage is transiently empty
        if (!tok || tok === 'null' || tok === 'undefined' || tok === '[object Object]' || tok.trim() === '') {
            const cookieMatch = document.cookie.split(';').map(c => c.trim()).find(c => c.startsWith('staff_token='));
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
        
        // STRICT ENFORCEMENT: Never return legacy keys (authToken, token, access_token).
        // Never return 'null', 'undefined', or empty string.
        if (tok && tok !== 'null' && tok !== 'undefined' && tok !== '[object Object]' && tok.trim() !== '') {
            // Self-heal localStorage if it was quote-wrapped or dirty
            try {
                if (localStorage.getItem(STORAGE_KEYS.TOKEN) !== tok) {
                    localStorage.setItem(STORAGE_KEYS.TOKEN, tok);
                }
            } catch(e) {}
            return tok;
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
        const currentPath = window.location.pathname + window.location.search;
        console.log('[DC-FETCH] Redirecting to login with redirect:', currentPath);
        window.location.href = '/staff/login?redirect=' + encodeURIComponent(currentPath);
    }
    
    function handleAuthFailure(status, errorDetail) {
        console.warn('[DC-FETCH] Auth failure detected:', status, errorDetail);
        clearSession();
        redirectToLogin();
    }
    
    async function staffFetch(url, options = {}) {
        const token = getToken();
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
            const response = await fetch(url, fetchOptions);
            
            if (response.status === 401 || response.status === 403) {
                let errorDetail = 'Authentication failed';
                try {
                    const errorData = await response.clone().json();
                    errorDetail = errorData.detail || errorData.message || errorDetail;
                } catch (e) {}
                
                // DC Protocol: NDA_PENDING must NEVER trigger auth failure or token removal
                if (errorDetail === 'NDA_PENDING') {
                    return response;
                }
                
                const authErrorKeywords = [
                    'token_expired', 'token expired', 'session expired',
                    'could not validate credentials', 'invalid token'
                ];
                
                const isExplicitAuthExpiry = authErrorKeywords.some(keyword => 
                    errorDetail.toLowerCase().includes(keyword)
                );
                
                // Check if token is locally expired before nuking session
                const activeToken = getToken();
                let isLocallyExpired = false;
                if (activeToken) {
                    try {
                        const parts = activeToken.split('.');
                        if (parts.length === 3) {
                            const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
                            if (payload.exp && Date.now() >= payload.exp * 1000) {
                                isLocallyExpired = true;
                            }
                        }
                    } catch (e) {}
                } else {
                    isLocallyExpired = true;
                }

                if (isExplicitAuthExpiry || (response.status === 401 && isLocallyExpired)) {
                    handleAuthFailure(response.status, errorDetail);
                    throw new Error('AUTH_EXPIRED');
                }
                
                console.warn('[DC-FETCH] Non-fatal 401/403 response (session preserved):', errorDetail);
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
