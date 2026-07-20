/**
 * DC_PARTNER_AUTH_001: Partner Token Manager (Dec 2025)
 * Centralized authentication handling for partner portal
 * - Manages partner_token in localStorage
 * - Intercepts fetch/XHR calls to inject Authorization header
 * - Handles token expiry and redirect to login
 */
;(function(window) {
    'use strict';
    
    const PARTNER_TOKEN_KEY = 'partner_token';
    const PARTNER_INFO_KEY = 'partner_info';
    const LOGIN_URL = '/partner/login';
    
    // DC Protocol: Check if in sandbox mode
    function isSandboxMode() {
        return !!localStorage.getItem('sandbox_mode');
    }
    
    function getSandboxMode() {
        return localStorage.getItem('sandbox_mode') || 'view';
    }
    
    // Partner Token Manager
    window.PartnerTokenManager = {
        // Get current token
        getToken: function() {
            return localStorage.getItem(PARTNER_TOKEN_KEY);
        },
        
        // Set token
        setToken: function(token) {
            localStorage.setItem(PARTNER_TOKEN_KEY, token);
        },
        
        // Clear token
        clearToken: function() {
            localStorage.removeItem(PARTNER_TOKEN_KEY);
            localStorage.removeItem(PARTNER_INFO_KEY);
        },
        
        // Get partner info
        getPartnerInfo: function() {
            try {
                const info = localStorage.getItem(PARTNER_INFO_KEY);
                return info ? JSON.parse(info) : null;
            } catch (e) {
                return null;
            }
        },
        
        // Set partner info
        setPartnerInfo: function(info) {
            localStorage.setItem(PARTNER_INFO_KEY, JSON.stringify(info));
        },
        
        // Check if logged in
        isLoggedIn: function() {
            return !!this.getToken();
        },
        
        // Redirect to login (sandbox-aware)
        redirectToLogin: function() {
            // DC Protocol: In sandbox mode, redirect to sandbox login
            if (isSandboxMode()) {
                const mode = getSandboxMode();
                this.clearToken();
                localStorage.removeItem('sandbox_mode');
                window.location.href = '/test/' + mode + '/partner/login';
                return;
            }
            this.clearToken();
            window.location.href = LOGIN_URL;
        },
        
        // Check if in sandbox mode
        isSandbox: function() {
            return isSandboxMode();
        },
        
        // Handle auth error
        handleAuthError: function(errorDetail) {
            const authErrors = ['TOKEN_EXPIRED', 'INVALID_TOKEN', 'Missing or invalid authorization header'];
            if (authErrors.some(e => errorDetail && errorDetail.includes(e))) {
                this.redirectToLogin();
                return true;
            }
            return false;
        },
        
        // Get company ID from partner info
        getCompanyId: function() {
            const info = this.getPartnerInfo();
            return info ? info.primary_company_id : null;
        }
    };
    
    // Partner Fetch Helper
    window.partnerFetch = async function(url, options = {}) {
        const token = PartnerTokenManager.getToken();
        
        if (!token) {
            PartnerTokenManager.redirectToLogin();
            throw new Error('No partner token');
        }
        
        // Merge headers
        const headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token,
            ...options.headers
        };
        
        // Add company ID if available
        const companyId = PartnerTokenManager.getCompanyId();
        if (companyId) {
            headers['X-Company-ID'] = String(companyId);
        }
        
        const response = await fetch(url, {
            ...options,
            headers
        });
        
        // Handle 401/403 errors (sandbox-aware)
        if (response.status === 401 || response.status === 403) {
            // DC Protocol: In sandbox mode, don't redirect - return response for graceful handling
            if (isSandboxMode()) {
                console.warn('[SANDBOX] API returned ' + response.status + ' - sandbox tokens not valid for production APIs');
                return response;
            }
            try {
                const errorData = await response.clone().json();
                if (PartnerTokenManager.handleAuthError(errorData.detail)) {
                    throw new Error('Authentication required');
                }
            } catch (e) {
                if (response.status === 401) {
                    PartnerTokenManager.redirectToLogin();
                    throw new Error('Authentication required');
                }
            }
        }
        
        return response;
    };
    
    // Partner Fetch JSON Helper
    window.partnerFetchJson = async function(url, options = {}) {
        const response = await partnerFetch(url, options);
        return response.json();
    };
    
    // Global fetch interceptor for partner pages
    if (window.location.pathname.startsWith('/partner/')) {
        const originalFetch = window.fetch;
        
        window.fetch = function(url, options = {}) {
            // Only intercept API calls
            if (typeof url === 'string' && url.includes('/api/')) {
                const token = PartnerTokenManager.getToken();
                if (token) {
                    options.headers = options.headers || {};
                    if (!options.headers['Authorization']) {
                        options.headers['Authorization'] = 'Bearer ' + token;
                    }
                    
                    const companyId = PartnerTokenManager.getCompanyId();
                    if (companyId && !options.headers['X-Company-ID']) {
                        options.headers['X-Company-ID'] = String(companyId);
                    }
                }
            }
            
            return originalFetch.call(window, url, options).then(response => {
                // Handle auth errors globally
                if (response.status === 401) {
                    response.clone().json().then(data => {
                        PartnerTokenManager.handleAuthError(data.detail);
                    }).catch(() => {});
                }
                return response;
            });
        };
        
        console.log('[DC] Partner Token Manager initialized - fetch interceptor active');
    }
    
})(window);
