(function() {
  'use strict';
  
  const DC_AUTH_VERSION = '1.0.1';
  const MAX_RETRY_ATTEMPTS = 1;
  
  function getAuthEndpoint() {
    const path = window.location.pathname;
    const staffPaths = ['/staff/', '/staff-', '/rvz/', '/vgk/', '/vgk-', '/admin/', '/finance/', '/superadmin/'];
    const partnerPaths = ['/partner/', '/partner-', '/real-dreams/', '/real-dreams-'];
    
    if (staffPaths.some(p => path.startsWith(p))) {
      return '/api/v1/auth/me-hybrid?role=staff';
    }
    if (partnerPaths.some(p => path.startsWith(p))) {
      return '/api/v1/auth/me-hybrid?role=partner';
    }
    return '/api/v1/auth/me-hybrid?role=mnr';
  }
  
  let cachedUser = null;
  let authPromise = null;
  let isInitialized = false;
  let lastError = null;
  
  function getLoginRedirectUrl() {
    const path = window.location.pathname;
    if (path.startsWith('/staff/') || path.startsWith('/staff-')) {
      return '/staff/login';
    }
    if (path.startsWith('/partner/') || path.startsWith('/partner-')) {
      return '/partner/login';
    }
    return '/login';
  }
  
  function redirectToLogin(reason) {
    console.log('[DCAuth] Redirecting to login:', reason);
    const loginUrl = getLoginRedirectUrl();
    if (window.location.pathname !== loginUrl) {
      window.location.href = loginUrl + '?expired=1&reason=' + encodeURIComponent(reason);
    }
  }
  
  async function fetchUserProfile(retryCount = 0) {
    try {
      const headers = {
        'Content-Type': 'application/json'
      };
      
      if (window.sessionToken) {
        headers['Authorization'] = 'Bearer ' + window.sessionToken;
      }
      
      const response = await fetch(getAuthEndpoint(), {
        method: 'GET',
        credentials: 'include',
        headers: headers
      });
      
      if (response.status === 401) {
        if (retryCount < MAX_RETRY_ATTEMPTS) {
          console.log('[DCAuth] 401 received, retrying once...');
          await new Promise(r => setTimeout(r, 500));
          return fetchUserProfile(retryCount + 1);
        }
        
        lastError = { status: 401, message: 'Authentication failed' };
        console.warn('[DCAuth] Authentication failed after retries');
        return null;
      }
      
      if (!response.ok) {
        lastError = { status: response.status, message: 'Server error' };
        console.warn('[DCAuth] Server error:', response.status);
        return null;
      }
      
      const data = await response.json();
      
      const user = data.data || data.employee || data;
      
      if (user && (user.id || user.emp_code)) {
        lastError = null;
        return user;
      }
      
      lastError = { status: 200, message: 'Invalid user data' };
      return null;
      
    } catch (err) {
      console.error('[DCAuth] Network error:', err);
      lastError = { status: 0, message: err.message };
      return null;
    }
  }
  
  async function initialize() {
    if (authPromise) {
      return authPromise;
    }
    
    authPromise = new Promise(async (resolve) => {
      const user = await fetchUserProfile();
      
      if (user) {
        cachedUser = user;
        isInitialized = true;
        console.log('[DCAuth] Initialized for:', user.id || user.emp_code);
      } else {
        isInitialized = true;
      }
      
      resolve(cachedUser);
    });
    
    return authPromise;
  }
  
  function getCurrentUser() {
    if (!authPromise) {
      return initialize();
    }
    return authPromise;
  }
  
  function getCachedUser() {
    return cachedUser;
  }
  
  function isAuthenticated() {
    return cachedUser !== null;
  }
  
  function getLastError() {
    return lastError;
  }
  
  function requireAuth(options = {}) {
    return getCurrentUser().then(user => {
      if (!user) {
        if (options.silent) {
          return null;
        }
        if (options.redirect !== false) {
          redirectToLogin(lastError?.message || 'Session expired');
        }
        return null;
      }
      return user;
    });
  }
  
  function clearCache() {
    cachedUser = null;
    authPromise = null;
    isInitialized = false;
    lastError = null;
  }
  
  function getUserRole() {
    if (!cachedUser) return null;
    
    if (cachedUser.emp_code) {
      return 'staff';
    }
    
    if (cachedUser.partner_type) {
      return 'partner';
    }
    
    const authLevel = cachedUser.authorization_level || cachedUser.user_type || 'Member';
    return authLevel;
  }
  
  function hasRole(roles) {
    const userRole = getUserRole();
    if (!userRole) return false;
    
    if (typeof roles === 'string') {
      return userRole === roles;
    }
    
    if (Array.isArray(roles)) {
      return roles.includes(userRole);
    }
    
    return false;
  }
  
  window.DCAuth = {
    version: DC_AUTH_VERSION,
    initialize: initialize,
    getCurrentUser: getCurrentUser,
    getCachedUser: getCachedUser,
    isAuthenticated: isAuthenticated,
    getLastError: getLastError,
    requireAuth: requireAuth,
    clearCache: clearCache,
    getUserRole: getUserRole,
    hasRole: hasRole,
    redirectToLogin: redirectToLogin
  };
  
  console.log('[DCAuth] Auth state manager v' + DC_AUTH_VERSION + ' loaded');
  
})();
