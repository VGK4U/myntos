/**
 * DC_PARTNER_AUTH_001: Partner Sidebar Component (Dec 2025)
 * Zero-Default Access Policy - Shows only explicitly granted menus
 */

// DC_THEME_001: Inline ThemeManager for Partner Portal (Jan 2026)
// Ensures theme toggle works without requiring separate script load
const ThemeManager = window.ThemeManager || {
  getCurrentTheme: function() {
    return localStorage.getItem('mnr_theme_preference') || 'dark';
  },
  setTheme: function(theme) {
    localStorage.setItem('mnr_theme_preference', theme);
    document.body.classList.remove('dark-theme', 'light-theme');
    document.body.classList.add(theme + '-theme');
  },
  toggle: function() {
    const current = this.getCurrentTheme();
    this.setTheme(current === 'dark' ? 'light' : 'dark');
    const icon = document.querySelector('.theme-toggle-icon');
    const text = document.querySelector('.theme-toggle-text');
    if (icon) icon.className = 'fas fa-' + (this.getCurrentTheme() === 'dark' ? 'moon' : 'sun') + ' theme-toggle-icon';
    if (text) text.textContent = this.getCurrentTheme() === 'dark' ? 'Dark Mode' : 'Light Mode';
  },
  init: function() {
    this.setTheme(this.getCurrentTheme());
  }
};
window.ThemeManager = ThemeManager;
ThemeManager.init();

;(function() {
    'use strict';
    
    // Partner sidebar menu structure (default structure, filtered by access)
    // IDs MUST match staff_menu_master.id for partner audience_scope
    // Uses path-based matching to handle company-specific ID variations (637-877 range)
    // DC_PARTNER_MENUS_001 (Apr 2026): hrefs use /partner/ prefix matching server.js routes
    // IDs kept for legacy matching; path-based matching is the primary mechanism
    const PARTNER_MENU_STRUCTURE = [
        { icon: 'fas fa-tachometer-alt',      label: 'Dashboard',         href: '/partner/dashboard'      },
        { icon: 'fas fa-walking',             label: 'Walk-ins',          href: '/partner/walkins'        },
        { icon: 'fas fa-users',               label: 'My Leads',          href: '/partner/my-leads'       },
        { icon: 'fas fa-store',               label: 'Marketplace',       href: '/partner/marketplace'    },
        { icon: 'fas fa-shopping-cart',       label: 'My Orders',         href: '/partner/orders'         },
        { icon: 'fas fa-file-invoice',        label: 'My Purchases',      href: '/partner/purchases'      },
        { icon: 'fas fa-file-invoice-dollar', label: 'Sales',             href: '/partner/sales/invoices' },
        { icon: 'fas fa-wrench',              label: 'Service',           href: '/partner/service'        },
        { icon: 'fas fa-boxes',               label: 'My Stock',          href: '/partner/stock'          },
        { icon: 'fas fa-money-check-alt',     label: 'My Payments',       href: '/partner/payments'       },
        { icon: 'fas fa-box-open',            label: 'Product Catalog',   href: '/partner/pricing'        },
        { icon: 'fas fa-chart-bar',           label: 'Revenue Dashboard', href: '/partner/revenue'        },
        { icon: 'fas fa-coins',               label: 'Reference Bonus',   href: '/partner/commissions'    },
        { icon: 'fas fa-id-card',             label: 'KYC &amp; Documents',  href: '/partner/kyc-documents'  },
        { icon: 'fas fa-tools',               label: 'Spare Orders',      href: '/partner/spare-orders'   },
        { icon: 'fas fa-headset',             label: 'Support',           href: '/partner/support'        },
        { icon: 'fas fa-home',                label: 'Real Dreams',       href: '/partner/real-dreams/dashboard'    },
        { icon: 'fas fa-building',            label: 'My Properties',     href: '/partner/real-dreams/properties'  },
        { icon: 'fas fa-coins',               label: 'Commissions',       href: '/partner/real-dreams/commissions' },
    ];
    
    // Allowed menus from API (Zero-Default Access Policy)
    let allowedMenus = [];
    
    /**
     * Load allowed menus from API based on Zero-Default Access Policy
     */
    async function loadAllowedMenus() {
        try {
            const token = localStorage.getItem('partner_token');
            if (!token) {
                console.log('[DC] Partner not authenticated - no menus loaded');
                return [];
            }
            
            const partnerInfo = JSON.parse(localStorage.getItem('partner_info') || '{}');
            const companyId = partnerInfo.primary_company_id;
            
            const headers = {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            };
            
            if (companyId) {
                headers['X-Company-ID'] = String(companyId);
            }
            
            const response = await fetch('/api/v1/partner/auth/my-menus', { headers });
            
            if (!response.ok) {
                if (response.status === 401) {
                    // DC Protocol: Check sandbox mode - don't redirect in sandbox
                    const sandboxMode = localStorage.getItem('sandbox_mode');
                    if (sandboxMode) {
                        console.log('[DC] Partner API 401 (sandbox mode - using default menus)');
                        // Return all menus for sandbox testing
                        return [{ id: 'sandbox', route_path: '*' }];
                    }
                    console.log('[DC] Partner token expired - redirecting to login');
                    localStorage.removeItem('partner_token');
                    localStorage.removeItem('partner_info');
                    window.location.href = '/partner/login';
                    return [];
                }
                throw new Error('Failed to load menus');
            }
            
            const data = await response.json();
            allowedMenus = data.menus || [];
            console.log('[DC] Partner menus loaded:', allowedMenus.length, 'items');
            return allowedMenus;
        } catch (error) {
            console.error('[DC] Error loading partner menus:', error);
            return [];
        }
    }
    
    /**
     * Check if a menu is accessible (uses BOTH ID and path matching for cross-company support)
     * Different companies may have different menu IDs for the same route_path
     */
    function isMenuAccessible(menuItem) {
        // First try exact ID match
        if (allowedMenus.some(m => m.id === menuItem.id)) return true;
        
        // Path-based matching for cross-company support
        // Normalize paths to handle /partner-portal/ vs /partner/ differences
        const normalizePath = (path) => {
            if (!path) return '';
            return path.toLowerCase()
                .replace('/partner-portal/', '/partner/')
                .replace(/\/$/, ''); // Remove trailing slash
        };
        
        const normalizedHref = normalizePath(menuItem.href);
        
        return allowedMenus.some(m => {
            const normalizedMenuPath = normalizePath(m.route_path || '');
            return normalizedMenuPath === normalizedHref;
        });
    }
    
    // DC_PARTNER_STATUS_001: Status display configuration
    const PARTNER_STATUS_BLOCKS = {
        'inactive':  { icon: 'fa-ban',                color: '#ef4444', title: 'Account Inactive',   msg: 'This account has been deactivated. Contact your administrator.' },
        'pause':     { icon: 'fa-pause-circle',       color: '#f59e0b', title: 'Account Paused',     msg: 'Your account is temporarily paused. Contact support to reactivate.' },
        'expired':   { icon: 'fa-calendar-times',     color: '#f97316', title: 'Account Expired',    msg: 'Your partnership has expired. Please renew your agreement to continue.' },
        'suspended': { icon: 'fa-exclamation-circle', color: '#ef4444', title: 'Account Suspended',  msg: 'Your account has been suspended. Contact support for assistance.' },
        'locked':    { icon: 'fa-lock',               color: '#6b7280', title: 'Account Locked',     msg: 'Account locked after multiple failed attempts. Contact support.' },
    };

    /**
     * Create the partner sidebar HTML
     */
    function createPartnerSidebar() {
        const partnerInfo = JSON.parse(localStorage.getItem('partner_info') || '{}');
        const partnerName = partnerInfo.partner_name || 'Partner';
        const partnerCode = partnerInfo.partner_code || '';
        const category = partnerInfo.category || 'PARTNER';
        const loginStatus = partnerInfo.login_status || 'active';
        const staffRole = partnerInfo.staff_role || null; // [DC-ROLE-001]

        // Create menu HTML
        let menuHtml = '';

        // DC_PARTNER_STATUS_001: Non-active partners see a status-specific message instead of menus
        if (loginStatus !== 'active') {
            const sb = PARTNER_STATUS_BLOCKS[loginStatus] || { icon: 'fa-lock', color: '#6b7280', title: 'Access Restricted', msg: 'Contact your administrator to request access.' };
            menuHtml = `
                <li class="nav-item">
                    <div class="px-3 py-4 text-center">
                        <i class="fas ${sb.icon} fa-2x mb-3 d-block" style="color:${sb.color}"></i>
                        <p style="color:#fff;font-weight:600;margin-bottom:6px">${sb.title}</p>
                        <small style="color:rgba(255,255,255,0.65);font-size:12px;line-height:1.5">${sb.msg}</small>
                    </div>
                </li>
            `;
        } else {
            // Filter menus based on Zero-Default Access Policy (uses ID + path matching)
            const accessibleMenus = PARTNER_MENU_STRUCTURE.filter(menu => isMenuAccessible(menu));

            if (accessibleMenus.length === 0) {
                // Active but no menus configured yet
                menuHtml = `
                    <li class="nav-item">
                        <div class="px-3 py-4 text-center">
                            <i class="fas fa-lock fa-2x mb-3 d-block" style="color:#9ca3af"></i>
                            <p style="color:rgba(255,255,255,0.7);margin-bottom:6px">No menu access granted</p>
                            <small style="color:rgba(255,255,255,0.5);font-size:12px">Please contact your administrator to request access.</small>
                        </div>
                    </li>
                `;
            } else {
                accessibleMenus.forEach(menu => {
                    const isActive = window.location.pathname === menu.href;
                    menuHtml += `
                        <li class="nav-item">
                            <a class="nav-link ${isActive ? 'active' : ''}" href="${menu.href}">
                                <i class="${menu.icon} me-2"></i>
                                <span>${menu.label}</span>
                            </a>
                        </li>
                    `;
                });
            }
        }
        
        const sidebarHtml = `
            <div class="partner-sidebar" id="partnerSidebar">
                <div class="sidebar-header">
                    <div class="partner-logo">
                        <img src="/assets/logos/myntreal_logo_horizontal.png" alt="Myntreal" class="sidebar-logo" onerror="this.src='/assets/logos/myntreal_logo_new.png'">
                    </div>
                    <div class="partner-info mt-3">
                        <div class="partner-avatar">
                            <i class="fas fa-user-tie"></i>
                        </div>
                        <div class="partner-details">
                            <h6 class="partner-name mb-0">${partnerName}</h6>
                            <small class="partner-code" style="color:rgba(255,255,255,0.65);font-size:11px;">${partnerCode}</small>
                            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:4px;">
                                <span class="badge bg-purple">${category}</span>
                                ${staffRole ? `<span style="background:${staffRole==='sales'?'#1d4ed8':'#059669'};color:#fff;font-size:10px;padding:2px 7px;border-radius:10px;font-weight:700;">${staffRole==='sales'?'Sales Staff':'Service Staff'}</span>` : ''}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- DC Protocol (Apr 2026): VGK Portal cross-auth — below DEALER badge, above nav -->
                <div style="padding:10px 16px 6px;">
                    <a href="#" id="vgkPortalSidebarBtn" onclick="partnerSwitchToVGK(); return false;" style="display:flex;align-items:center;gap:10px;padding:9px 14px;border-radius:8px;background:linear-gradient(135deg,#f59e0b,#d97706);border:none;text-decoration:none;transition:opacity .2s;box-shadow:0 2px 8px rgba(0,0,0,.25);">
                        <i class="fas fa-exchange-alt" style="color:#fff;font-size:13px;width:16px;text-align:center;"></i>
                        <span style="color:#fff;font-size:13px;font-weight:700;letter-spacing:.3px;">VGK4U Portal</span>
                    </a>
                </div>
                
                <nav class="sidebar-nav">
                    <ul class="nav flex-column">
                        ${menuHtml}
                    </ul>
                </nav>
                
                <div class="sidebar-footer">
                    <div class="settings-section">
                        <a href="/partner/change-password" class="nav-item settings-item">
                            <i class="fas fa-key"></i>
                            <span>Change Password</span>
                        </a>
                    </div>
                    <button class="btn btn-outline-light btn-sm w-100" onclick="partnerLogout()">
                        <i class="fas fa-sign-out-alt me-2"></i>Logout
                    </button>
                </div>
            </div>
        `;
        
        return sidebarHtml;
    }
    
    /**
     * Inject sidebar styles
     */
    function injectSidebarStyles() {
        if (document.getElementById('partnerSidebarStyles')) return;
        
        const styles = document.createElement('style');
        styles.id = 'partnerSidebarStyles';
        styles.textContent = `
            .partner-sidebar {
                position: fixed;
                left: 0;
                top: 0;
                width: 260px;
                height: 100vh;
                background: linear-gradient(180deg, #0f2044 0%, #0a1628 100%);
                color: white;
                display: flex;
                flex-direction: column;
                z-index: 1000;
                box-shadow: 2px 0 12px rgba(0,0,0,0.35);
            }
            
            .sidebar-header {
                padding: 20px;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }
            
            .sidebar-logo {
                max-width: 150px;
                height: auto;
            }
            
            .partner-info {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .partner-avatar {
                width: 45px;
                height: 45px;
                background: rgba(255,255,255,0.2);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.2rem;
            }
            
            .partner-details {
                display: flex;
                flex-direction: column;
            }
            
            .partner-name {
                font-weight: 700;
                font-size: 0.88rem;
                color: #fff;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                max-width: 155px;
            }
            
            .badge.bg-purple {
                background: rgba(255,255,255,0.2);
                font-size: 0.65rem;
                padding: 3px 8px;
            }
            
            .sidebar-nav {
                flex: 1;
                overflow-y: auto;
                padding: 15px 0;
            }
            
            .sidebar-nav .nav-link {
                color: rgba(255,255,255,0.8);
                padding: 12px 20px;
                display: flex;
                align-items: center;
                transition: all 0.2s;
                border-left: 3px solid transparent;
            }
            
            .sidebar-nav .nav-link:hover {
                background: rgba(255,255,255,0.1);
                color: white;
            }
            
            .sidebar-nav .nav-link.active {
                background: rgba(59,130,246,0.18);
                color: white;
                border-left-color: #3b82f6;
            }
            
            .sidebar-nav .nav-link i {
                width: 20px;
                text-align: center;
            }
            
            .sidebar-footer {
                padding: 15px 20px;
                border-top: 1px solid rgba(255,255,255,0.1);
            }
            
            /* DC_THEME_001: Settings section styles */
            .settings-section {
                margin-bottom: 10px;
                padding-bottom: 10px;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }
            
            .settings-item {
                display: flex;
                align-items: center;
                padding: 8px 12px;
                color: rgba(255,255,255,0.8);
                text-decoration: none;
                transition: all 0.2s ease;
                border-radius: 6px;
                margin-bottom: 4px;
            }
            
            .settings-item:hover {
                background: rgba(255,255,255,0.1);
                color: #fff;
            }
            
            .settings-item i {
                width: 20px;
                text-align: center;
                margin-right: 8px;
                font-size: 14px;
            }
            
            .settings-item span {
                font-size: 13px;
            }
            
            .partner-main-content {
                margin-left: 260px;
                min-height: 100vh;
                background: transparent;
            }
            
            @media (max-width: 768px) {
                .partner-sidebar {
                    transform: translateX(-100%);
                    transition: transform 0.3s;
                }
                
                .partner-sidebar.show,
                .partner-sidebar.mobile-open {
                    transform: translateX(0);
                }
                
                .partner-main-content {
                    margin-left: 0;
                }
            }

            /* Backdrop overlay — closes sidebar on tap-outside */
            #partnerSidebarOverlay {
                display: none;
                position: fixed;
                inset: 0;
                background: rgba(0,0,0,0.45);
                z-index: 999;
                -webkit-tap-highlight-color: transparent;
            }
            #partnerSidebarOverlay.active { display: block; }
        `;
        document.head.appendChild(styles);
    }
    
    /**
     * DC Protocol (Apr 2026): Check if this partner has a linked VGK account.
     * Shows #vgkPortalSidebarBtn if linked, otherwise keeps it hidden.
     */
    async function _checkAndShowVgkBtn(partnerCode) {
        try {
            if (!partnerCode) return;
            const resp = await fetch('/api/v1/promo/cross-auth/check-vgk-link?partner_code=' + encodeURIComponent(partnerCode));
            if (resp.ok) {
                const data = await resp.json();
                if (data.linked) {
                    const btn = document.getElementById('vgkPortalSidebarBtn');
                    if (btn) btn.style.display = 'flex';
                }
            }
        } catch(e) {}
    }

    /**
     * DC Protocol (Apr 2026): Cross-auth — switch from Partner portal to VGK4U portal.
     * Calls generate-partner-to-vgk, then redirects to /vgk/login?ct=...
     */
    window.partnerSwitchToVGK = async function() {
        const btn = document.getElementById('vgkPortalSidebarBtn');
        const origHtml = btn ? btn.innerHTML : '';
        if (btn) { btn.style.pointerEvents = 'none'; btn.innerHTML = '<i class="fas fa-spinner fa-spin" style="color:#fff"></i><span style="color:#fff;font-weight:700;margin-left:8px">Opening…</span>'; }
        try {
            const tok = localStorage.getItem('partner_token');
            if (!tok) { alert('Session expired. Please log in again.'); window.location.href = '/partner/login'; return; }
            const resp = await fetch('/api/v1/promo/cross-auth/generate-partner-to-vgk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + tok }
            });
            const data = await resp.json();
            if (resp.ok && data.success) {
                // Redirect — VGK login page redeems the cross-auth token automatically
                window.location.href = '/vgk/login?ct=' + encodeURIComponent(data.cross_token);
            } else if (resp.status === 400) {
                alert(data.detail || 'Mobile number not set on your profile. Please update your profile before accessing VGK4U.');
                if (btn) { btn.style.pointerEvents = ''; btn.innerHTML = origHtml; }
            } else {
                alert(data.detail || 'Could not open VGK4U Portal. Please try again.');
                if (btn) { btn.style.pointerEvents = ''; btn.innerHTML = origHtml; }
            }
        } catch(e) {
            alert('Network error. Please try again.');
            if (btn) { btn.style.pointerEvents = ''; btn.innerHTML = origHtml; }
        }
    };

    /**
     * Partner logout function
     */
    window.partnerLogout = function() {
        const sandboxMode = localStorage.getItem('sandbox_mode');
        localStorage.removeItem('partner_token');
        localStorage.removeItem('partner_info');
        if (sandboxMode) {
            localStorage.removeItem('sandbox_mode');
            window.location.href = '/test/' + sandboxMode + '/partner/login';
        } else {
            window.location.href = '/partner/login';
        }
    };
    
    /**
     * Initialize partner sidebar
     * DC_PARTNER_STATUS_001: Only load menus for active partners
     */
    // DC Protocol: load universal inactivity manager if not already present
    function _loadDCInactivity() {
        if (window.DCInactivityManager) {
            window.DCInactivityManager.init({
                tokenKey:      'partner_token',
                tokenStorage:  'localStorage',
                loginUrl:      '/partner/login',
                portalName:    'Partner Portal',
                accentColor:   '#0f766e',
                companionKeys: ['partner_info'],
            });
            return;
        }
        const s = document.createElement('script');
        s.src = '/shared/dc_universal_inactivity.js';
        s.onload = function () {
            window.DCInactivityManager.init({
                tokenKey:      'partner_token',
                tokenStorage:  'localStorage',
                loginUrl:      '/partner/login',
                portalName:    'Partner Portal',
                accentColor:   '#0f766e',
                companionKeys: ['partner_info'],
            });
        };
        document.head.appendChild(s);
    }

    let _sidebarInitialized = false;
    window.initPartnerSidebar = async function(containerId) {
        if (_sidebarInitialized) return;
        _sidebarInitialized = true;
        injectSidebarStyles();

        // DC_PARTNER_STATUS_001: Only call menus API for active partners
        const _pInfo = JSON.parse(localStorage.getItem('partner_info') || '{}');
        const _pStatus = _pInfo.login_status || 'active';
        if (_pStatus === 'active') {
            await loadAllowedMenus();
        }

        // Create and inject sidebar
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = createPartnerSidebar();
        } else {
            // Insert at beginning of body
            document.body.insertAdjacentHTML('afterbegin', createPartnerSidebar());
        }

        // Inject backdrop overlay for mobile sidebar close-on-tap-outside
        if (!document.getElementById('partnerSidebarOverlay')) {
            const overlay = document.createElement('div');
            overlay.id = 'partnerSidebarOverlay';
            overlay.addEventListener('click', function() { closeMobileSidebar(); });
            overlay.addEventListener('touchstart', function(e) { e.preventDefault(); closeMobileSidebar(); }, { passive: false });
            document.body.appendChild(overlay);
        }

        // DC Protocol (Apr 2026): Check if this partner has a linked VGK account and show button if so
        const _pCode = _pInfo.partner_code || _pInfo.code || '';
        _checkAndShowVgkBtn(_pCode);

        // DC Protocol: Start universal 15-min inactivity manager
        _loadDCInactivity();

        console.log('[DC] Partner sidebar initialized — status:', _pStatus);
    };

    function closeMobileSidebar() {
        const sidebar = document.getElementById('partnerSidebar');
        const overlay = document.getElementById('partnerSidebarOverlay');
        if (sidebar) { sidebar.classList.remove('show'); sidebar.classList.remove('mobile-open'); }
        if (overlay) overlay.classList.remove('active');
    }

    // Global toggleMobileMenu — works for ALL partner pages regardless of local definition
    // Pages with local toggleMobileMenu that use wrong class will continue to work because
    // both 'show' and 'mobile-open' are now CSS-aliased; this global is a safety fallback.
    if (!window.toggleMobileMenu) {
        window.toggleMobileMenu = function() {
            const sidebar = document.getElementById('partnerSidebar');
            const overlay = document.getElementById('partnerSidebarOverlay');
            if (!sidebar) return;
            const isOpen = sidebar.classList.contains('show') || sidebar.classList.contains('mobile-open');
            if (isOpen) {
                sidebar.classList.remove('show', 'mobile-open');
                if (overlay) overlay.classList.remove('active');
            } else {
                sidebar.classList.add('show');
                if (overlay) overlay.classList.add('active');
            }
        };
    }
    
    // Auto-initialize if on partner page
    if (window.location.pathname.startsWith('/partner/') && !window.location.pathname.includes('/partner/login')) {
        document.addEventListener('DOMContentLoaded', function() {
            // Check if logged in
            const token = localStorage.getItem('partner_token');
            if (!token) {
                // DC Protocol: Check sandbox mode
                const sandboxMode = localStorage.getItem('sandbox_mode');
                if (sandboxMode) {
                    window.location.href = '/test/' + sandboxMode + '/partner/login';
                } else {
                    window.location.href = '/partner/login';
                }
                return;
            }
            
            initPartnerSidebar();
        });
    }
    
    console.log('[DC] Partner Sidebar component loaded - Zero-Default Access Policy');
})();

// ─── VGK Assistant Integration (DC_VGK_001 - Partner Portal) ─────────────
(function _vgkPartnerBoot() {
  function init() {
    if (!document.getElementById('vgk-script')) {
      const s = document.createElement('script');
      s.id = 'vgk-script'; s.src = '/vgk_assistant.js';
      document.head.appendChild(s);
    }
  }
  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', init); }
  else { init(); }
})();
