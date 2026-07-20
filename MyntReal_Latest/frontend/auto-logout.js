// Global logout function - called by logout buttons in sidebar/header
// DC Protocol: All logouts redirect to main landing page (/)
window.logout = function() {
    // Clear local storage for all user types
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('authToken');
    localStorage.removeItem('sessionToken');
    localStorage.removeItem('staff_token');
    localStorage.removeItem('staff_user');
    localStorage.removeItem('partner_token');
    localStorage.removeItem('partner_info');
    
    // DC Protocol: All roles redirect to main landing page
    const mainPage = '/';
    
    // Call API logout then redirect to main page
    fetch('/api/v1/auth/logout', {
        method: 'POST',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json'
        }
    }).then(response => {
        window.location.href = mainPage;
    }).catch(error => {
        window.location.href = mainPage;
    });
};

(function() {
    const INACTIVITY_TIMEOUT = 10 * 60 * 1000;
    const CHECK_INTERVAL = 60 * 1000;
    
    let lastActivityTime = Date.now();
    let checkIntervalId = null;
    let warningShown = false;
    
    function updateActivity() {
        lastActivityTime = Date.now();
        warningShown = false;
    }
    
    function checkInactivity() {
        const now = Date.now();
        const inactiveTime = now - lastActivityTime;
        
        if (inactiveTime >= INACTIVITY_TIMEOUT) {
            performLogout();
        } else if (inactiveTime >= (INACTIVITY_TIMEOUT - 60000) && !warningShown) {
            showWarning();
            warningShown = true;
        }
    }
    
    function showWarning() {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: 'Session Expiring',
                text: 'Your session will expire in 1 minute due to inactivity. Move your mouse or click to stay logged in.',
                icon: 'warning',
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 5000,
                timerProgressBar: true
            });
        }
    }
    
    function performLogout() {
        if (checkIntervalId) {
            clearInterval(checkIntervalId);
        }
        
        // Clear all tokens on auto-logout
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        localStorage.removeItem('authToken');
        localStorage.removeItem('sessionToken');
        localStorage.removeItem('staff_token');
        localStorage.removeItem('staff_user');
        localStorage.removeItem('partner_token');
        localStorage.removeItem('partner_info');
        
        // DC Protocol: All logouts redirect to main landing page
        fetch('/api/v1/auth/logout', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(response => {
            window.location.href = '/?timeout=1';
        }).catch(error => {
            window.location.href = '/?timeout=1';
        });
    }
    
    function initAutoLogout() {
        const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
        
        activityEvents.forEach(event => {
            document.addEventListener(event, updateActivity, true);
        });
        
        checkIntervalId = setInterval(checkInactivity, CHECK_INTERVAL);
        
        updateActivity();
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAutoLogout);
    } else {
        initAutoLogout();
    }
    
    window.addEventListener('beforeunload', function() {
        if (checkIntervalId) {
            clearInterval(checkIntervalId);
        }
    });
})();
