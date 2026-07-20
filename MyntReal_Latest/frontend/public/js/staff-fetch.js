(function() {
    'use strict';
    
    const STORAGE_KEYS = {
        TOKEN: 'staff_token',
        USER: 'staff_user',
        COMPANY_ID: 'staff_company_id'
    };
    
    function getToken() {
        return localStorage.getItem(STORAGE_KEYS.TOKEN);
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
                
                const authErrorKeywords = [
                    'token', 'expired', 'invalid', 'unauthorized', 
                    'not authenticated', 'session', 'credentials',
                    'could not validate', 'jwt', 'bearer'
                ];
                
                const isAuthError = authErrorKeywords.some(keyword => 
                    errorDetail.toLowerCase().includes(keyword)
                );
                
                if (isAuthError) {
                    handleAuthFailure(response.status, errorDetail);
                    throw new Error('AUTH_EXPIRED');
                }
                
                console.warn('[DC-FETCH] Non-auth 401/403:', errorDetail);
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
