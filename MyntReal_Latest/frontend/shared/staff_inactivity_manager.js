/**
 * Mynt Real LLP Staff Portal - Inactivity Manager Module
 * DC Protocol Compliant: Auto-logout after 15 minutes of inactivity
 * Created: Dec 04, 2025
 * 
 * FEATURES:
 * - Tracks user activity (mouse, keyboard, touch, scroll, API calls)
 * - Warning modal at 13 minutes (2 mins before logout)
 * - Form data preservation before auto-logout
 * - DC Protocol audit logging
 * - Graceful logout without interrupting ongoing operations
 * 
 * INTEGRATION:
 * - Works with StaffSidebar.logout() for consistent logout behavior
 * - Resets timer on successful API responses
 * - Preserves active journey tracking (GPS heartbeats reset timer)
 */

const StaffInactivityManager = {
    // Configuration
    config: {
        inactivityTimeout: 15 * 60 * 1000,  // 15 minutes in milliseconds
        warningTime: 13 * 60 * 1000,        // Show warning at 13 minutes
        checkInterval: 10 * 1000,           // Check every 10 seconds
        countdownInterval: 1000,            // Update countdown every second
        storageKey: 'staff_last_activity',
        auditStorageKey: 'staff_inactivity_audit'
    },

    // State
    state: {
        lastActivity: null,
        inactivityTimer: null,
        warningTimer: null,
        countdownTimer: null,
        warningShown: false,
        isInitialized: false,
        isPaused: false,
        remainingSeconds: 120
    },

    /**
     * Initialize the inactivity manager
     * Call this on page load after authentication check
     */
    init: function() {
        // Only initialize once and only if user is logged in
        if (this.state.isInitialized) return;
        
        const token = localStorage.getItem('staff_token');
        if (!token) {
            console.log('[DC-INACTIVITY] No staff token found, skipping initialization');
            return;
        }

        console.log('[DC-INACTIVITY] Initializing inactivity manager - 15 min timeout');
        
        // Set initial activity time
        this.updateActivity();
        
        // Bind event listeners for user activity
        this.bindActivityListeners();
        
        // Intercept fetch to reset on API calls
        this.interceptFetch();
        
        // Listen for cross-tab activity sync
        this.bindStorageListener();
        
        // Start the inactivity check timer
        this.startTimer();
        
        // Create warning modal
        this.createWarningModal();
        
        this.state.isInitialized = true;
        
        // Log initialization
        this.logAudit('INIT', 'Inactivity manager initialized');
    },

    /**
     * Update last activity timestamp
     */
    updateActivity: function() {
        if (this.state.isPaused) return;
        
        this.state.lastActivity = Date.now();
        localStorage.setItem(this.config.storageKey, this.state.lastActivity.toString());
        
        // If warning was shown, hide it and reset
        if (this.state.warningShown) {
            this.hideWarning();
            this.logAudit('ACTIVITY_RESUMED', 'User resumed activity after warning');
        }
    },

    /**
     * Bind activity event listeners
     */
    bindActivityListeners: function() {
        const activityEvents = [
            'mousedown', 'mousemove', 'keydown', 'keypress',
            'touchstart', 'touchmove', 'scroll', 'click', 'focus'
        ];
        
        // Throttle activity updates to avoid excessive calls
        let throttleTimer = null;
        const throttledUpdate = () => {
            if (throttleTimer) return;
            throttleTimer = setTimeout(() => {
                this.updateActivity();
                throttleTimer = null;
            }, 1000); // Max one update per second
        };
        
        activityEvents.forEach(event => {
            document.addEventListener(event, throttledUpdate, { passive: true });
        });
        
        // Also listen for visibility change (user returns to tab)
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                this.checkInactivity();
            }
        });
        
        console.log('[DC-INACTIVITY] Activity listeners bound');
    },

    /**
     * Intercept fetch to reset timer on successful API calls
     */
    interceptFetch: function() {
        const originalFetch = window.fetch;
        const self = this;
        
        window.fetch = function(...args) {
            return originalFetch.apply(this, args).then(response => {
                // Reset activity on any successful API response
                if (response.ok) {
                    self.updateActivity();
                }
                return response;
            });
        };
        
        console.log('[DC-INACTIVITY] Fetch interceptor installed');
    },

    /**
     * Listen for cross-tab activity sync via localStorage
     */
    bindStorageListener: function() {
        const self = this;
        
        window.addEventListener('storage', function(event) {
            // Check if the activity timestamp was updated in another tab
            if (event.key === self.config.storageKey && event.newValue) {
                const newActivityTime = parseInt(event.newValue);
                if (newActivityTime > (self.state.lastActivity || 0)) {
                    // Another tab had activity, update local state
                    self.state.lastActivity = newActivityTime;
                    
                    // If warning was showing, hide it since user is active in another tab
                    if (self.state.warningShown) {
                        self.hideWarning();
                        console.log('[DC-INACTIVITY] Activity detected in another tab, warning dismissed');
                    }
                }
            }
            
            // If staff_token is removed (logout in another tab), logout this tab too
            if (event.key === 'staff_token' && !event.newValue) {
                console.log('[DC-INACTIVITY] Logout detected in another tab, syncing logout');
                self.cleanup();
                const _tabRedirect = window.location.pathname + window.location.search;
                window.location.href = '/staff/login?redirect=' + encodeURIComponent(_tabRedirect);
            }
        });
        
        console.log('[DC-INACTIVITY] Cross-tab storage listener bound');
    },

    /**
     * Start the inactivity check timer
     */
    startTimer: function() {
        // Clear any existing timer
        if (this.state.inactivityTimer) {
            clearInterval(this.state.inactivityTimer);
        }
        
        // Check inactivity periodically
        this.state.inactivityTimer = setInterval(() => {
            this.checkInactivity();
        }, this.config.checkInterval);
    },

    /**
     * Check if user has been inactive
     * CRITICAL: Always reads from localStorage for cross-tab sync
     */
    checkInactivity: function() {
        if (this.state.isPaused) return;
        
        // Safety check: if token was removed, cleanup and stop
        const token = localStorage.getItem('staff_token');
        if (!token) {
            console.log('[DC-INACTIVITY] Token removed, cleaning up manager');
            this.cleanup();
            return;
        }
        
        const now = Date.now();
        
        // ALWAYS read from localStorage for cross-tab synchronization
        // This ensures activity from other tabs is respected
        const storedActivity = parseInt(localStorage.getItem(this.config.storageKey));
        const lastActivity = storedActivity || this.state.lastActivity || now;
        
        // Sync local state with storage
        if (storedActivity && storedActivity > (this.state.lastActivity || 0)) {
            this.state.lastActivity = storedActivity;
        }
        
        const inactiveTime = now - lastActivity;
        
        // Check if we should show warning (at 13 minutes)
        if (inactiveTime >= this.config.warningTime && !this.state.warningShown) {
            this.showWarning();
        } else if (inactiveTime < this.config.warningTime && this.state.warningShown) {
            // Activity happened (possibly in another tab), hide warning
            this.hideWarning();
        }
        
        // Check if we should logout (at 15 minutes)
        if (inactiveTime >= this.config.inactivityTimeout) {
            this.performAutoLogout();
        }
    },

    /**
     * Show warning modal with countdown
     */
    showWarning: function() {
        if (this.state.warningShown) return;
        
        this.state.warningShown = true;
        this.state.remainingSeconds = 120; // 2 minutes
        
        // Show the modal
        const modal = document.getElementById('inactivityWarningModal');
        if (modal) {
            modal.style.display = 'flex';
            this.updateCountdownDisplay();
            
            // Start countdown timer
            this.state.countdownTimer = setInterval(() => {
                this.state.remainingSeconds--;
                this.updateCountdownDisplay();
                
                if (this.state.remainingSeconds <= 0) {
                    clearInterval(this.state.countdownTimer);
                }
            }, this.config.countdownInterval);
        }
        
        this.logAudit('WARNING_SHOWN', 'Inactivity warning displayed - 2 minutes remaining');
        console.log('[DC-INACTIVITY] Warning modal shown');
    },

    /**
     * Hide warning modal
     */
    hideWarning: function() {
        this.state.warningShown = false;
        
        if (this.state.countdownTimer) {
            clearInterval(this.state.countdownTimer);
            this.state.countdownTimer = null;
        }
        
        const modal = document.getElementById('inactivityWarningModal');
        if (modal) {
            modal.style.display = 'none';
        }
    },

    /**
     * Update countdown display
     */
    updateCountdownDisplay: function() {
        const countdownEl = document.getElementById('inactivityCountdown');
        if (countdownEl) {
            const minutes = Math.floor(this.state.remainingSeconds / 60);
            const seconds = this.state.remainingSeconds % 60;
            countdownEl.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }
    },

    /**
     * User clicked "Stay Logged In"
     */
    stayLoggedIn: function() {
        this.updateActivity();
        this.hideWarning();
        this.logAudit('SESSION_EXTENDED', 'User clicked Stay Logged In');
        console.log('[DC-INACTIVITY] Session extended by user');
    },

    /**
     * User clicked "Logout Now"
     */
    logoutNow: function() {
        this.hideWarning();
        this.logAudit('MANUAL_LOGOUT', 'User clicked Logout Now from warning modal');
        this.performLogout('USER_REQUESTED');
    },

    /**
     * Perform auto-logout due to inactivity
     */
    performAutoLogout: function() {
        this.hideWarning();
        
        // Preserve form data before logout
        this.preserveFormData();
        
        // Log the auto-logout
        this.logAudit('AUTO_LOGOUT', 'Session expired due to 15 minutes of inactivity');
        
        console.log('[DC-INACTIVITY] Auto-logout triggered after 15 minutes of inactivity');
        
        this.performLogout('INACTIVITY_TIMEOUT');
    },

    /**
     * Perform the actual logout
     * SAFETY: Only logout if there's actually a token (prevents redirect loops)
     */
    performLogout: function(reason) {
        // CRITICAL: Check for token before logout to prevent redirect loops
        const token = localStorage.getItem('staff_token');
        if (!token) {
            console.log('[DC-INACTIVITY] No token found, skipping logout to prevent loop');
            this.cleanup();
            return;
        }
        
        // Stop all timers
        this.cleanup();
        
        // Store logout reason for login page to show message
        sessionStorage.setItem('staff_logout_reason', reason);
        
        // Preserve current page so user returns here after re-login
        const _redirectPath = window.location.pathname + window.location.search;
        // Clear tokens and sidebar state manually (StaffSidebar.logout() doesn't pass redirect)
        localStorage.removeItem('staff_token');
        localStorage.removeItem('staff_user');
        localStorage.removeItem(this.config.storageKey);
        Object.keys(localStorage).forEach(function(key) {
            if (key.startsWith('staff_sidebar_state_')) {
                localStorage.removeItem(key);
            }
        });
        window.location.href = '/staff/login?redirect=' + encodeURIComponent(_redirectPath);
    },

    /**
     * Preserve form data before logout
     * DC Protocol: Complete form data preservation including all input types
     */
    preserveFormData: function() {
        const forms = document.querySelectorAll('form');
        const preservedData = {};
        
        forms.forEach((form, index) => {
            const formData = {};
            
            // Generate unique form identifier
            let formId = form.id || form.getAttribute('data-form-id');
            
            // If no id, assign a temporary one based on form position and page path
            if (!formId) {
                formId = `auto_form_${window.location.pathname.replace(/\//g, '_')}_${index}`;
                // Assign the id to the form for restoration matching
                form.setAttribute('data-inactivity-form-id', formId);
            }
            
            // Handle text inputs, textareas
            form.querySelectorAll('input[type="text"], input[type="email"], input[type="tel"], input[type="number"], input[type="date"], input[type="time"], input[type="datetime-local"], textarea').forEach(input => {
                if (input.name && input.value && input.type !== 'password') {
                    formData[input.name] = {
                        type: input.type || 'text',
                        value: input.value
                    };
                }
            });
            
            // Handle checkboxes
            form.querySelectorAll('input[type="checkbox"]').forEach(input => {
                if (input.name) {
                    if (!formData[input.name]) {
                        formData[input.name] = { type: 'checkbox', values: [] };
                    }
                    if (input.checked) {
                        formData[input.name].values.push(input.value || 'on');
                    }
                }
            });
            
            // Handle radio buttons
            form.querySelectorAll('input[type="radio"]:checked').forEach(input => {
                if (input.name) {
                    formData[input.name] = {
                        type: 'radio',
                        value: input.value
                    };
                }
            });
            
            // Handle select (single and multi-select)
            form.querySelectorAll('select').forEach(select => {
                if (select.name) {
                    if (select.multiple) {
                        const selectedValues = Array.from(select.selectedOptions).map(opt => opt.value);
                        if (selectedValues.length > 0) {
                            formData[select.name] = {
                                type: 'select-multiple',
                                values: selectedValues
                            };
                        }
                    } else if (select.value) {
                        formData[select.name] = {
                            type: 'select-one',
                            value: select.value
                        };
                    }
                }
            });
            
            if (Object.keys(formData).length > 0) {
                preservedData[formId] = {
                    action: form.action || window.location.pathname,
                    method: form.method || 'POST',
                    fields: formData
                };
            }
        });
        
        if (Object.keys(preservedData).length > 0) {
            sessionStorage.setItem('staff_preserved_forms', JSON.stringify(preservedData));
            sessionStorage.setItem('staff_preserved_forms_page', window.location.pathname);
            this.logAudit('FORM_PRESERVED', `Preserved ${Object.keys(preservedData).length} form(s) before logout`);
            console.log('[DC-INACTIVITY] Form data preserved:', preservedData);
        }
    },

    /**
     * Restore preserved form data after login
     * Call this on page load if there's preserved data
     */
    restoreFormData: function() {
        const preservedPage = sessionStorage.getItem('staff_preserved_forms_page');
        if (preservedPage !== window.location.pathname) {
            // Not on the same page, clear preserved data
            sessionStorage.removeItem('staff_preserved_forms');
            sessionStorage.removeItem('staff_preserved_forms_page');
            return;
        }
        
        const preserved = sessionStorage.getItem('staff_preserved_forms');
        if (!preserved) return;
        
        try {
            const data = JSON.parse(preserved);
            
            Object.entries(data).forEach(([formId, formData]) => {
                // Try multiple selectors to find the form
                let form = document.getElementById(formId) || 
                           document.querySelector(`form[data-form-id="${formId}"]`) ||
                           document.querySelector(`form[data-inactivity-form-id="${formId}"]`);
                
                // For auto-generated IDs, try matching by index on current page
                if (!form && formId.startsWith('auto_form_')) {
                    const match = formId.match(/_(\d+)$/);
                    if (match) {
                        const index = parseInt(match[1]);
                        const forms = document.querySelectorAll('form');
                        if (forms[index]) {
                            form = forms[index];
                        }
                    }
                }
                
                if (!form) return;
                
                Object.entries(formData.fields).forEach(([fieldName, fieldData]) => {
                    if (fieldData.type === 'checkbox') {
                        fieldData.values.forEach(val => {
                            const checkbox = form.querySelector(`input[type="checkbox"][name="${fieldName}"][value="${val}"]`);
                            if (checkbox) checkbox.checked = true;
                        });
                    } else if (fieldData.type === 'radio') {
                        const radio = form.querySelector(`input[type="radio"][name="${fieldName}"][value="${fieldData.value}"]`);
                        if (radio) radio.checked = true;
                    } else if (fieldData.type === 'select-multiple') {
                        const select = form.querySelector(`select[name="${fieldName}"]`);
                        if (select) {
                            Array.from(select.options).forEach(opt => {
                                opt.selected = fieldData.values.includes(opt.value);
                            });
                        }
                    } else {
                        const input = form.querySelector(`[name="${fieldName}"]`);
                        if (input) input.value = fieldData.value;
                    }
                });
            });
            
            // Clear preserved data after restore
            sessionStorage.removeItem('staff_preserved_forms');
            sessionStorage.removeItem('staff_preserved_forms_page');
            
            this.logAudit('FORM_RESTORED', 'Preserved form data restored successfully');
            console.log('[DC-INACTIVITY] Form data restored');
        } catch (e) {
            console.error('[DC-INACTIVITY] Error restoring form data:', e);
        }
    },

    /**
     * Log audit entry (DC Protocol compliance)
     */
    logAudit: function(action, details) {
        const auditEntry = {
            timestamp: new Date().toISOString(),
            action: action,
            details: details,
            page: window.location.pathname
        };
        
        // Get existing audit log
        let auditLog = [];
        try {
            const stored = sessionStorage.getItem(this.config.auditStorageKey);
            if (stored) {
                auditLog = JSON.parse(stored);
            }
        } catch (e) {
            auditLog = [];
        }
        
        // Add new entry (keep last 50 entries)
        auditLog.push(auditEntry);
        if (auditLog.length > 50) {
            auditLog = auditLog.slice(-50);
        }
        
        sessionStorage.setItem(this.config.auditStorageKey, JSON.stringify(auditLog));
        
        // Also log to console with DC prefix
        console.log(`[DC-INACTIVITY-AUDIT] ${action}: ${details}`);
    },

    /**
     * Pause inactivity tracking (e.g., during active journey)
     */
    pause: function() {
        this.state.isPaused = true;
        this.logAudit('TRACKING_PAUSED', 'Inactivity tracking paused');
    },

    /**
     * Resume inactivity tracking
     */
    resume: function() {
        this.state.isPaused = false;
        this.updateActivity();
        this.logAudit('TRACKING_RESUMED', 'Inactivity tracking resumed');
    },

    /**
     * Cleanup timers and listeners
     */
    cleanup: function() {
        if (this.state.inactivityTimer) {
            clearInterval(this.state.inactivityTimer);
        }
        if (this.state.countdownTimer) {
            clearInterval(this.state.countdownTimer);
        }
        this.state.isInitialized = false;
    },

    /**
     * Create warning modal HTML
     */
    createWarningModal: function() {
        // Don't create if already exists
        if (document.getElementById('inactivityWarningModal')) return;
        
        const modalHTML = `
            <div id="inactivityWarningModal" style="
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.6);
                z-index: 99999;
                justify-content: center;
                align-items: center;
                backdrop-filter: blur(4px);
            ">
                <div style="
                    background: white;
                    border-radius: 16px;
                    padding: 32px;
                    max-width: 420px;
                    width: 90%;
                    text-align: center;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                    animation: modalSlideIn 0.3s ease-out;
                ">
                    <div style="
                        width: 64px;
                        height: 64px;
                        background: linear-gradient(135deg, #f59e0b, #d97706);
                        border-radius: 50%;
                        margin: 0 auto 20px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    ">
                        <i class="fas fa-clock" style="font-size: 28px; color: white;"></i>
                    </div>
                    
                    <h3 style="
                        margin: 0 0 12px;
                        color: #1f2937;
                        font-size: 20px;
                        font-weight: 600;
                    ">Session Expiring Soon</h3>
                    
                    <p style="
                        margin: 0 0 24px;
                        color: #6b7280;
                        font-size: 14px;
                        line-height: 1.5;
                    ">
                        Your session will expire in <strong id="inactivityCountdown" style="color: #dc2626; font-size: 18px;">2:00</strong> due to inactivity.
                    </p>
                    
                    <div style="display: flex; gap: 12px; justify-content: center;">
                        <button onclick="StaffInactivityManager.stayLoggedIn()" style="
                            flex: 1;
                            padding: 12px 24px;
                            background: linear-gradient(135deg, #10b981, #059669);
                            color: white;
                            border: none;
                            border-radius: 8px;
                            font-size: 14px;
                            font-weight: 600;
                            cursor: pointer;
                            transition: all 0.2s;
                        " onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
                            <i class="fas fa-check me-2"></i>Stay Logged In
                        </button>
                        
                        <button onclick="StaffInactivityManager.logoutNow()" style="
                            padding: 12px 24px;
                            background: white;
                            color: #dc2626;
                            border: 2px solid #dc2626;
                            border-radius: 8px;
                            font-size: 14px;
                            font-weight: 600;
                            cursor: pointer;
                            transition: all 0.2s;
                        " onmouseover="this.style.background='#fef2f2'" onmouseout="this.style.background='white'">
                            <i class="fas fa-sign-out-alt me-2"></i>Logout
                        </button>
                    </div>
                </div>
            </div>
            
            <style>
                @keyframes modalSlideIn {
                    from {
                        opacity: 0;
                        transform: scale(0.9) translateY(-20px);
                    }
                    to {
                        opacity: 1;
                        transform: scale(1) translateY(0);
                    }
                }
            </style>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    },

    /**
     * Get time until logout (for display purposes)
     */
    getTimeUntilLogout: function() {
        const now = Date.now();
        const lastActivity = this.state.lastActivity || parseInt(localStorage.getItem(this.config.storageKey)) || now;
        const remaining = this.config.inactivityTimeout - (now - lastActivity);
        return Math.max(0, Math.floor(remaining / 1000));
    }
};

// Auto-initialize when DOM is ready (only on staff pages, not login page)
document.addEventListener('DOMContentLoaded', function() {
    // Don't initialize on login page
    if (window.location.pathname.includes('/staff/login')) {
        console.log('[DC-INACTIVITY] Login page detected, skipping initialization');
        return;
    }
    
    // Delay initialization to allow page auth checks to run first
    // This prevents race conditions with page-level redirects
    setTimeout(() => {
        // Double-check token still exists (page may have redirected)
        const token = localStorage.getItem('staff_token');
        if (!token) {
            console.log('[DC-INACTIVITY] No token after DOM load, skipping initialization');
            return;
        }
        
        // Verify we're still on a staff page (not redirected to login)
        if (window.location.pathname.includes('/staff/login')) {
            console.log('[DC-INACTIVITY] Redirected to login, skipping initialization');
            return;
        }
        
        StaffInactivityManager.init();
    }, 500);
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StaffInactivityManager;
}
