/**
 * Mynt Real LLP Staff Portal - Unified Sidebar Module
 * DC Protocol Compliant: Role-based menu with consistent styling
 * Created: Nov 26, 2025
 * Updated: Nov 26, 2025 - Added collapsible group functionality (MNR pattern)
 * Updated: Dec 11, 2025 - Zero-Default Access Policy (explicit grants required)
 * 
 * ZERO-DEFAULT ACCESS POLICY:
 * - New employees have NO menu access by default
 * - Menu items are only shown if explicitly granted via StaffEmployeeMenuSettings
 * - EA/VGK administrators must grant access via Menu Access Control page
 * 
 * FUTURE DEVELOPMENT STANDARD:
 * All new sidebar sections MUST follow the collapsible group structure:
 * - Use .sidebar-group container
 * - Use .sidebar-group-toggle for clickable headers
 * - Use .sidebar-group-items for menu items container
 * - State persistence via localStorage key: staff_sidebar_state_{role_name}
 */

// DC_THEME_001: Inline ThemeManager for Staff Portal (Jan 2026)
// Ensures theme toggle works without requiring separate script load
// DC Protocol Apr 2026: Changed from `const ThemeManager` to window assignment to prevent
// "Identifier already declared" SyntaxError when this file is loaded more than once
// (e.g. injected by server template AND included explicitly in the page HTML).
window.ThemeManager = window.ThemeManager || {
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

// DC Protocol (Jan 22, 2026): Load MENU_MASTER - the authoritative source of all menus
let MENU_MASTER_DATA = null;

// DC-SIDEBAR-RACE-FIX-001 (Jun 2026): Promise that resolves when menu-master.js is ready.
// Previously this was fire-and-forget, causing StaffSidebar.init() to call getMenuForRole()
// before MENU_MASTER was defined → only hardcoded pinned items rendered, dynamic sections blank.
let _menuMasterReady = (function loadMenuMaster() {
    return new Promise(function(resolve) {
        // Already loaded synchronously (e.g. inline script) — no wait needed
        if (typeof MENU_MASTER !== "undefined") {
            MENU_MASTER_DATA = MENU_MASTER;
            console.log("[DC-SIDEBAR] MENU_MASTER already available:", MENU_MASTER_DATA.length, "sections");
            return resolve();
        }
        var script = document.createElement("script");
        script.src = "/public/js/menu-master.js?v=" + Date.now();
        script.onload = function() {
            if (typeof MENU_MASTER !== "undefined") {
                MENU_MASTER_DATA = MENU_MASTER;
                console.log("[DC-SIDEBAR] MENU_MASTER loaded:", MENU_MASTER_DATA.length, "sections");
            } else {
                console.warn("[DC-SIDEBAR] menu-master.js loaded but MENU_MASTER not defined");
            }
            resolve();
        };
        script.onerror = function() {
            console.warn("[DC-SIDEBAR] Failed to load menu-master.js — sidebar dynamic sections will be empty");
            resolve(); // unblock init() so we still render pinned items
        };
        // Safety timeout: don't block init() forever if script hangs
        setTimeout(resolve, 6000);
        document.head.appendChild(script);
    });
})();


const StaffSidebar = {
    // Allowed menus from /my-menus API (Zero-Default Access Policy)
    allowedMenuPaths: null,  // Set of allowed route_path values
    allowedMenuCodes: null,  // DC Protocol (Jan 22, 2026): Set of allowed menu_code values
    SUPREME_STAFF_TYPES: ["VGK4U_SUPREME", "RVZ_SUPREME", "VGK4U", "VGK4U Supreme", "VGK4U_EA"],
    zeroAccessMessage: null, // Message to show when no access granted
    // DC Protocol (Jan 12, 2026): REMOVED ALL HARDCODED MENU CONFIG
    // Sidebar is now 100% API-driven from /staff/menu-settings/registry
    // Database sidebar_section_order is the SINGLE SOURCE OF TRUTH for section ordering
    // Expected 19 sections: PROGRESS, STAFF DASHBOARD, ACCOUNTS, BUSINESS PARTNERS, 
    // CONFIGURATION, CRM & LEADS, JOURNEY TRACKING, KRA MANAGEMENT, LOCATION TRACKING,
    // TASK MANAGEMENT, ATTENDANCE, TIMESHEET, SERVICE TICKETS, REIMBURSEMENT, 
    // NDA MANAGEMENT, ZYNOVA, MNR, MNR USER SIDEBAR
    menuConfig: {},  // Legacy - kept empty for backward compatibility, not used


    // Current page path
    currentPath: window.location.pathname,

    // User data cache
    userData: null,

    // Initialize sidebar
    init: async function(containerId = 'staffSidebar') {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error('Sidebar container not found:', containerId);
            return;
        }

        // Get user data from localStorage or API
        await this.loadUserData();
        
        if (this.userData) {
            const u = this.userData;
            if (u.staff_type === 'FREELANCER' && u.freelancer_access_mode === 'only_leads') {
                const allowedPaths = ['/staff/dashboard', '/staff/mnr-leads-master', '/staff/mnr-leads', '/staff/login'];
                const currentPath = window.location.pathname;
                const isAllowed = allowedPaths.some(p => currentPath === p || currentPath.startsWith(p + '/') || currentPath.startsWith(p + '?'));
                if (!isAllowed) {
                    console.warn('[DC-REDIRECT] Restricted freelancer accessed unauthorized page:', currentPath, 'redirecting to dashboard');
                    window.location.href = '/staff/dashboard';
                    return;
                }
            }
        }
        
        if (!this.userData) {
            if (this.authError === 'NO_TOKEN' || this.authError === 'AUTH_FAILED') {
                const currentPath = window.location.pathname + window.location.search;
                window.location.href = '/staff/login?redirect=' + encodeURIComponent(currentPath);
            } else {
                console.warn('[DC-SIDEBAR] User data not available, but not an auth error - continuing');
            }
            return;
        }

        // DC Protocol (Dec 28, 2025): Update header user info immediately after user data loads
        this.updateHeaderUserInfo();

        // Zero-Default Access Policy: Load allowed menus after user data
        await this.loadAllowedMenus();

        // DC_TRAINING_GATE_001: Hard-lock sidebar to Training Videos if training incomplete
        await this.applyTrainingGate();

        // DC-SIDEBAR-RACE-FIX-001: Ensure MENU_MASTER is fully loaded before rendering
        // Without this await, getMenuForRole() sees MENU_MASTER as undefined and returns
        // empty dynamic sections — only the hardcoded pinned items (Progress, Task Planner…)
        // appear in the sidebar, making it look broken/incomplete.
        if (typeof _menuMasterReady !== 'undefined') await _menuMasterReady;

        // Create mobile toggle button and backdrop
        this.createMobileToggle();
        this.createBackdrop();

        // Render sidebar
        container.innerHTML = this.renderSidebar();
        
        // Restore sidebar visibility state (desktop collapsed)
        this.restoreSidebarState();
        
        // Bind group toggle handlers
        this.bindGroupToggles();
        
        // Restore saved section states
        this.restoreSectionStates();
        
        // Auto-expand section containing active page
        this.autoExpandActiveSection();
        
        // Highlight current page
        this.highlightCurrentPage();
        
        // Close sidebar on nav item click (mobile)
        this.bindMobileNavClose();
    },
    
    // DC_TRAINING_GATE_001: Check if employee must complete training before accessing menus.
    // Replaces allowedMenuPaths with only the training page if gated.
    // Fail-open: any network/parse error keeps the full menu — never breaks access.
    applyTrainingGate: async function() {
        try {
            if (!this.allowedMenuPaths || this.allowedMenuPaths === '*') return;
            const token = localStorage.getItem('staff_token');
            if (!token) return;
            const resp = await fetch('/api/v1/staff/accounts/training/status', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!resp.ok) return;
            const ts = await resp.json();
            if (ts && ts.is_gated) {
                this.allowedMenuPaths  = new Set(['/staff/training-videos']);
                this.allowedMenuCodes  = new Set(['TRAINING_VIDEOS']);
                this.trainingGateActive = true;
                console.log('[DC_TRAINING_GATE_001] Gate active — menu locked to Training Videos only');
            }
        } catch (_) {
            // Fail-open: if API is down or slow, menus load normally
            console.warn('[DC_TRAINING_GATE_001] Gate check failed — menus loading normally (fail-open)');
        }
    },

    // Close sidebar when clicking nav items on mobile
    bindMobileNavClose: function() {
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', () => {
                if (window.innerWidth < 768) {
                    this.closeSidebar();
                }
            });
        });
    },

    // DC Protocol (Dec 29, 2025): Dynamic menu configuration loaded from registry API
    // This replaces hard-coded menuConfig with database-driven menu structure
    dynamicMenuConfig: null,
    
    // Load dynamic menu structure from registry API
    // DC Protocol: Single source of truth for sidebar menu structure
    loadDynamicMenuConfig: async function() {
        try {
            const apiUrl = '/api/v1/staff/menu-settings/registry?audience=staff&include_sections=true';
            
            // Try to fetch from registry API
            let data = null;
            if (typeof staffFetchJson === 'function') {
                data = await staffFetchJson(apiUrl);
            } else {
                const token = localStorage.getItem('staff_token');
                if (token) {
                    const response = await fetch(apiUrl, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    if (response.ok) {
                        data = await response.json();
                    }
                }
            }
            
            if (data && data.success && data.sections && data.sections.length > 0) {
                // Transform registry sections to menuConfig format
                // DC Protocol (Jan 2026): Include subSections for nested menus like ZYNOVA
                const dynamicSections = data.sections.map(section => {
                    const sectionObj = {
                        id: section.id,
                        title: section.title,
                        order: section.order || 999,  // DC Protocol (Jan 12, 2026): Include order from database
                        menu_type: section.menu_type || 'STAFF',
                        items: (section.items || []).map(item => ({
                            icon: item.icon || 'fas fa-circle',
                            label: item.label,
                            href: item.href,
                            menu_code: item.menu_code,
                            parent_section: item.parent_section  // DC Protocol (Jan 10, 2026): Include for MNR USER nesting
                        }))
                    };
                    
                    // Include subSections if present (for ZYNOVA with Real Dreams submenu)
                    if (section.subSections && section.subSections.length > 0) {
                        sectionObj.subSections = section.subSections.map(sub => ({
                            id: sub.id,
                            title: sub.title,
                            icon: sub.icon || 'fas fa-folder',
                            items: (sub.items || []).map(item => ({
                                icon: item.icon || 'fas fa-circle',
                                label: item.label,
                                href: item.href,
                                menu_code: item.menu_code
                            }))
                        }));
                    }
                    
                    return sectionObj;
                });
                
                console.log('[DC-SIDEBAR-REGISTRY] Dynamic menu loaded:', data.total_menus, 'menus in', data.total_sections, 'sections');
                
                // DC Protocol (Jan 8, 2026): Store flat menu list for MNR User Sidebar filtering
                const filteredMenus = data.menus || [];
                
                // DC Protocol (Jan 12, 2026): FULLY DATABASE-DRIVEN NESTING
                // REMOVED all hardcoded nesting logic for STAFF MENUS, ACCOUNTS, ZYNOVA
                // Backend now handles all nesting via is_submenu and parent_section database fields
                // The API returns properly nested subSections directly - no frontend manipulation needed
                console.log('[DC-SIDEBAR-REGISTRY] Using database-driven nesting (no frontend transformation)');
                
                // DC Protocol (Jan 11, 2026): SIMPLIFIED MNR HANDLING
                // Trust the backend's pre-nested structure - only remove legacy/duplicate sections
                // The API already returns MNR with proper subSections
                
                // List of legacy sections to remove (not valid parent sections)
                const legacySectionsToRemove = [
                    'staff-mnr', 'MNR MANAGEMENT', 'staff_mnr_announcements', 'STAFF MNR ANNOUNCEMENTS', 
                    'staff_mnr_kyc_bank', 'STAFF MNR KYC BANK', 'WORKING_MNR', 'WORKING MNR',
                    'USER PORTAL', 'user-portal', 'USER_PORTAL',
                    'USER TEAM', 'user-team', 'USER_TEAM',
                    'USER EARNINGS', 'user-earnings', 'USER_EARNINGS',
                    'NEW REQUIRED', 'new-required', 'NEW_REQUIRED',
                    'NEW NOT REQUIRED', 'new-not-required', 'NEW_NOT_REQUIRED',
                    'SUPER ADMIN', 'superadmin', 'SUPERADMIN', 'super-admin',
                    'RVZ INCOME', 'rvz-income', 'RVZ_INCOME',
                    'WORKING', 'WORKING_STAFF', 'WORKING STAFF',
                    'earnings-admin', 'EARNINGS ADMIN', 'members-admin', 'MEMBERS ADMIN',
                    'admin-functions', 'ADMIN FUNCTIONS', 'withdrawal-admin', 'WITHDRAWAL ADMIN',
                    'rvz-earnings', 'RVZ EARNINGS',
                    'FINANCE', 'finance', 'FINANCIAL MANAGEMENT',
                    'RVZ ADMIN', 'rvz-admin', 'RVZ_ADMIN',
                    'ADMIN', 'admin', 'ADMIN EARNINGS', 'admin-earnings', 'ADMIN_EARNINGS',
                    'ADMIN MEMBERS', 'admin-members', 'ADMIN_MEMBERS'
                ];
                
                // Remove legacy sections
                for (let i = dynamicSections.length - 1; i >= 0; i--) {
                    const section = dynamicSections[i];
                    const sId = (section.id || '').toLowerCase();
                    const sTitle = section.title || '';
                    
                    if (legacySectionsToRemove.includes(section.id) || 
                        legacySectionsToRemove.includes(sTitle) ||
                        legacySectionsToRemove.includes(sId)) {
                        dynamicSections.splice(i, 1);
                        console.log('[DC-SIDEBAR-REGISTRY] Removed legacy section:', section.id || sTitle);
                    }
                }
                
                // Find MNR and log its structure (for debugging)
                const mnr = dynamicSections.find(s => 
                    s.id === 'mnr' || s.id === 'mnr' || 
                    s.title === 'MNR' || s.title === 'MNR'
                );
                if (mnr) {
                    console.log('[DC-SIDEBAR-REGISTRY] MNR found with', 
                        mnr.items?.length || 0, 'direct items,', 
                        mnr.subSections?.length || 0, 'subSections');
                }
                
                console.log('[DC-SIDEBAR-REGISTRY] Simplified processing complete');
                
                // DC Protocol (Jan 12, 2026): FULLY DATABASE-DRIVEN ORDERING
                // REMOVED hardcoded sectionOrderMap - database sidebar_section_order is single source of truth
                // API returns sections pre-sorted by sidebar_section_order from database
                
                dynamicSections.sort((a, b) => {
                    // Use order from API response (comes from database sidebar_section_order)
                    const aOrder = a.order || 999;
                    const bOrder = b.order || 999;
                    if (aOrder !== bOrder) return aOrder - bOrder;
                    // Alphabetical for same order
                    return (a.title || '').localeCompare(b.title || '');
                });
                
                console.log('[DC-SIDEBAR-REGISTRY] Sections sorted by database order:', dynamicSections.map(s => `${s.title}(${s.order})`).slice(0, 15));
                
                // Store as dynamic menu config for VGK4U Supreme role
                this.dynamicMenuConfig = {
                    sections: dynamicSections
                };
                
                return true;
            }
            
            console.log('[DC-SIDEBAR-REGISTRY] No dynamic menu available, using static config');
            return false;
        } catch (error) {
            console.warn('[DC-SIDEBAR-REGISTRY] Error loading dynamic menu, falling back to static:', error.message);
            return false;
        }
    },

    // Load allowed menus from /my-menus API (Zero-Default Access Policy)
    // DC Protocol: Staff menu access is employee-centric (unified across ALL companies)
    loadAllowedMenus: async function() {
        try {
            // DC Protocol (Dec 29, 2025): Try to load dynamic menu config first
            await this.loadDynamicMenuConfig();
            
            // DC Protocol: Only VGK4U (Supreme) has default full access
            // All other staff types (EA, RVZ, MYNT_REAL, etc.) follow Access Matrix control
            const staffType = this.userData?.staff_type || '';
            
            // DC Protocol (Jan 2, 2026): Explicit allowlist for VGK4U variants (prevents RBAC escalation)
            const vgk4uVariants = ['VGK4U', 'VGK4U Supreme'];
            if (staffType && vgk4uVariants.includes(staffType)) {
                console.log('[DC-SIDEBAR] Supreme bypass: Full menu access for', staffType);
                this.allowedMenuPaths = '*';  // VGK4U variants are supreme, always full access
                return;
            }
            
            // DC Protocol: Use unified=true to load ALL permissions across companies
            // This ensures staff see menus regardless of which company they're working with
            const apiUrl = '/api/v1/staff/menu-settings/my-menus?unified=true';
            
            // WVV Protocol: Use staffFetchJson for authenticated API call
            if (typeof staffFetchJson === 'function') {
                const data = await staffFetchJson(apiUrl);
                
                if (data.success) {
                    if (data.total_menus === 0) {
                        // Zero-access: No menus granted
                        this.allowedMenuPaths = new Set();
                        this.zeroAccessMessage = data.message || 'No menu access granted. Contact your administrator (EA/VGK) to request access.';
                        console.log('[DC-SIDEBAR] Zero-access policy: No menus granted');
                    } else {
                        // Build set of allowed route paths (unified across companies)
                        this.allowedMenuPaths = new Set(data.menus.map(m => m.route_path).filter(p => p));
                        this.allowedMenuCodes = new Set(data.menus.map(m => m.menu_code).filter(c => c));
                        this.menuRoutesForVGK = data.menus.filter(m => m.route_path && m.label).map(m => ({ label: m.label, route: m.route_path }));
                        console.log('[DC-SIDEBAR] Unified menus loaded:', this.allowedMenuPaths.size, '(unified_mode:', data.unified_mode, ')');
                        console.log('[DC-SIDEBAR] Debug: First 10 allowed paths:', Array.from(this.allowedMenuPaths).slice(0, 10));
                    }
                } else {
                    console.error('[DC-SIDEBAR] Failed to load allowed menus:', data);
                    this.allowedMenuPaths = new Set();
                    this.zeroAccessMessage = 'Error loading menu access. Please refresh the page.';
                }
            } else {
                // Fallback if staffFetchJson not available
                const token = localStorage.getItem('staff_token');
                if (!token) {
                    this.allowedMenuPaths = new Set();
                    this.zeroAccessMessage = 'Authentication required.';
                    return;
                }
                
                const response = await fetch(apiUrl, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.total_menus === 0) {
                        this.allowedMenuPaths = new Set();
                        this.zeroAccessMessage = data.message || 'No menu access granted.';
                    } else {
                        this.allowedMenuPaths = new Set(data.menus.map(m => m.route_path).filter(p => p));
                        this.allowedMenuCodes = new Set(data.menus.map(m => m.menu_code).filter(c => c));
                        this.menuRoutesForVGK = data.menus.filter(m => m.route_path && m.label).map(m => ({ label: m.label, route: m.route_path }));
                    }
                } else {
                    this.allowedMenuPaths = new Set();
                    this.zeroAccessMessage = 'Error loading menu access.';
                }
            }
        } catch (error) {
            // SECURITY FIX (Dec 31, 2025): Never grant full access on error
            // DC Protocol: Fail-secure - show zero-access on error, not full access
            console.error('[DC-SIDEBAR] Error loading allowed menus:', error);
            this.allowedMenuPaths = new Set();
            this.zeroAccessMessage = 'Network error loading menu access. Please refresh the page.';
            
            // Log sandbox mode for debugging but don't grant access
            const sandboxMode = localStorage.getItem('sandbox_mode');
            if (sandboxMode) {
                console.warn('[SANDBOX] loadAllowedMenus error in sandbox mode - still enforcing zero-access for security');
            }
        }
    },

    // Load user data
    loadUserData: async function() {
        try {
            const cachedData = localStorage.getItem('staff_user');
            if (cachedData) {
                const parsed = JSON.parse(cachedData);
                if (parsed && parsed.freelancer_access_mode !== undefined && parsed.staff_type !== 'FREELANCER') {
                    this.userData = parsed;
                    return;
                }
            }

            const token = localStorage.getItem('staff_token');
            if (!token) {
                this.authError = 'NO_TOKEN';
                return;
            }

            if (typeof staffFetchJson === 'function') {
                const data = await staffFetchJson('/api/v1/staff/auth/me');
                this.userData = data.employee || data;
                localStorage.setItem('staff_user', JSON.stringify(this.userData));
            } else {
                const response = await fetch('/api/v1/staff/auth/me', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (response.ok) {
                    const data = await response.json();
                    this.userData = data.employee || data;
                    localStorage.setItem('staff_user', JSON.stringify(this.userData));
                } else if (response.status === 401 || response.status === 403) {
                    console.warn('[DC-SIDEBAR] Auth failure:', response.status);
                    // DC Protocol: In sandbox mode, use placeholder data instead of redirecting
                    const sandboxMode = localStorage.getItem('sandbox_mode');
                    if (sandboxMode) {
                        console.log('[SANDBOX] Staff auth returned 401 - using placeholder data');
                        this.userData = {
                            role_name: 'VGK4U',
                            staff_type: 'VGK4U',
                            employee_name: 'Test Staff',
                            employee_id: 'TESTVGK001',
                            company_id: 1
                        };
                        return;
                    }
                    this.authError = 'AUTH_FAILED';
                    // WVV Protocol: Clear tokens and redirect to login with proper redirect param
                    localStorage.removeItem('staff_token');
                    localStorage.removeItem('staff_user');
                    const currentPath = window.location.pathname + window.location.search;
                    window.location.href = '/staff/login?redirect=' + encodeURIComponent(currentPath);
                } else {
                    console.warn('[DC-SIDEBAR] API error (non-auth):', response.status);
                }
            }
        } catch (error) {
            // WVV Protocol: Auth errors from staffFetchJson mean handleSessionExpired was already called
            // Just set authError - the redirect is already initiated by token-manager
            // DC Protocol: In sandbox mode, suppress auth errors and use placeholder data
            const sandboxMode = localStorage.getItem('sandbox_mode');
            if (sandboxMode) {
                console.log('[SANDBOX] Staff loadUserData error - using placeholder data');
                this.userData = {
                    role_name: 'VGK4U',
                    staff_type: 'VGK4U',
                    employee_name: 'Test Staff',
                    employee_id: 'TESTVGK001',
                    company_id: 1
                };
                return;
            }
            if (error.message === 'Not authenticated' || error.message === 'Token refresh failed') {
                this.authError = 'AUTH_FAILED';
                return;
            }
            console.error('[DC-SIDEBAR] Network error loading user data:', error);
        }
    },

    // DC Protocol (Dec 28, 2025): Update header user info elements
    // This ensures all staff pages show the logged-in user's name and role in the header
    updateHeaderUserInfo: function() {
        if (!this.userData) return;
        
        const name = this.userData.full_name || this.userData.employee_name || this.userData.name || 'Staff Member';
        const role = this.userData.role_name || 'Employee';
        const empId = this.userData.emp_code || this.userData.employee_code || this.userData.employee_id || '';
        const staffType = this.userData.staff_type || '';
        
        // Generate initials from name
        const initials = name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2) || '--';
        
        // Update header elements if they exist
        const initialsEl = document.getElementById('headerUserInitials');
        const nameEl = document.getElementById('headerUserName');
        const roleEl = document.getElementById('headerUserRole');
        const empIdEl = document.getElementById('headerUserEmpId');
        
        if (initialsEl) initialsEl.textContent = initials;
        if (nameEl) nameEl.textContent = name;
        if (empIdEl) empIdEl.textContent = empId;
        
        if (roleEl) {
            roleEl.textContent = role;
            
            // Apply role-specific badge styling
            const isVGK4U = staffType === 'VGK4U' || role.includes('Supreme') || role.includes('VGK4U');
            const isFreelancer = staffType === 'FREELANCER' || this.userData.is_freelancer;
            const isMnEmployee = staffType === 'MN_EMPLOYEE' || this.userData.is_mn_employee;
            const isMnStaff = staffType === 'MN_STAFF' || this.userData.is_mn_staff;
            
            if (isVGK4U) {
                roleEl.className = 'user-info-role role-badge-supreme';
            } else if (isFreelancer) {
                roleEl.className = 'user-info-role role-badge-freelancer';
            } else if (isMnEmployee) {
                roleEl.className = 'user-info-role role-badge-mn-employee';
            } else if (isMnStaff) {
                roleEl.className = 'user-info-role role-badge-mn-staff';
            } else if (role.includes('HR')) {
                roleEl.className = 'user-info-role role-badge-hr';
            } else if (role.includes('Leadership') || role.includes('Leader') || role.includes('Manager')) {
                roleEl.className = 'user-info-role role-badge-leadership';
            } else {
                roleEl.className = 'user-info-role role-badge-default';
            }
        }
        
        console.log('[DC-SIDEBAR] Header updated:', name, '(' + role + ')');
        
        // DC Protocol Jan 2026: Initialize header search if StaffHeader is available
        if (typeof StaffHeader !== 'undefined' && StaffHeader.initSearch) {
            setTimeout(() => StaffHeader.initSearch(), 100);
        }
    },

    // DC Protocol (Dec 31, 2025): Unified Header Component
    // Creates a consistent purple "Mynt Real" header for ALL pages (staff/admin/rvz)
    // This replaces the separate headers in admin.js and rvz.js templates
    renderUnifiedHeader: function(pageTitle = '', pageIcon = 'fas fa-home') {
        if (!this.userData) return '';
        
        const name = this.userData.full_name || this.userData.employee_name || this.userData.name || 'Staff Member';
        const role = this.userData.role_name || 'Employee';
        const empId = this.userData.emp_code || this.userData.employee_code || this.userData.employee_id || '';
        const staffType = this.userData.staff_type || '';
        
        // Generate initials
        const initials = name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2) || '--';
        
        // Role badge class
        let roleClass = 'role-badge-default';
        const isVGK4U = staffType === 'VGK4U' || role.includes('Supreme') || role.includes('VGK4U');
        if (isVGK4U) roleClass = 'role-badge-supreme';
        else if (role.includes('HR')) roleClass = 'role-badge-hr';
        else if (role.includes('Leadership') || role.includes('Leader') || role.includes('Manager')) roleClass = 'role-badge-leadership';
        
        return `
            <div class="unified-header">
                <div class="header-left">
                    <button class="header-hamburger" onclick="StaffSidebar.toggleSidebar()" aria-label="Toggle Menu">
                        <i class="fas fa-bars"></i>
                    </button>
                    <a href="/staff/dashboard" class="header-brand">
                        <img src="/assets/logos/myntreal_logo_new.png" alt="Mynt Real" class="header-logo-img" onerror="this.style.display='none'">
                        <span class="header-brand-text">Mynt Real</span>
                    </a>
                    ${pageTitle ? `<div class="header-page-title"><i class="${pageIcon}"></i> ${this.escapeHtml(pageTitle)}</div>` : ''}
                </div>
                <div class="header-right">
                    <div class="header-user-info">
                        <div class="header-user-avatar" id="headerUserInitials">${initials}</div>
                        <div class="header-user-details">
                            <span class="header-user-role ${roleClass}" id="headerUserRole">${this.escapeHtml(role)}</span>
                            <span class="header-user-empid" id="headerUserEmpId">${this.escapeHtml(empId)}</span>
                        </div>
                    </div>
                    <button class="header-icon-btn" onclick="StaffSidebar.toggleNotifications()" aria-label="Notifications">
                        <i class="fas fa-bell"></i>
                        <span class="notification-badge" id="notificationBadge" style="display:none">0</span>
                    </button>
                    <a href="/staff/settings" class="header-icon-btn" aria-label="Settings">
                        <i class="fas fa-cog"></i>
                    </a>
                    <button class="header-icon-btn header-logout-btn" onclick="StaffSidebar.logout()" aria-label="Logout">
                        <i class="fas fa-sign-out-alt"></i>
                    </button>
                </div>
            </div>
        `;
    },

    // Toggle notifications dropdown (placeholder for future implementation)
    toggleNotifications: function() {
        console.log('[DC-SIDEBAR] Notifications toggle - to be implemented');
    },

    // Logout function
    logout: function() {
        localStorage.removeItem('staff_token');
        localStorage.removeItem('staff_user');
        localStorage.removeItem('staff_sidebar_collapsed');
        window.location.href = '/staff/login';
    },

    // Inject unified header into page
    injectUnifiedHeader: function(containerId = 'unifiedHeader', pageTitle = '', pageIcon = 'fas fa-home') {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = this.renderUnifiedHeader(pageTitle, pageIcon);
            console.log('[DC-SIDEBAR] Unified header injected');
        }
    },

    // Get menu for current role (filtered by Zero-Default Access Policy)
    // DC Protocol (Jan 12, 2026): FULLY DYNAMIC SIDEBAR - uses API response directly
    // No more hardcoded menuConfig fallback - database is single source of truth
    // DC Protocol (Jan 22, 2026): MENU_MASTER is the authoritative source of truth
    // Renders sidebar strictly from MENU_MASTER structure, filtered by Menu Access Control
    getMenuForRole: function() {
        const staffType = this.userData?.staff_type || '';
        
        // Use MENU_MASTER as the source of truth
        const menuMaster = (typeof MENU_MASTER !== 'undefined') ? MENU_MASTER : MENU_MASTER_DATA;
        
        if (!menuMaster || menuMaster.length === 0) {
            return { sections: [], zeroAccess: false };
        }
        
        // Check if user is Supreme (bypass all access control)
        const supremeTypes = this.SUPREME_STAFF_TYPES || ['VGK4U_SUPREME', 'RVZ_SUPREME', 'VGK4U', 'VGK4U Supreme', 'VGK4U_EA'];
        const isSupreme = this.allowedMenuPaths === '*' || 
                         (staffType && supremeTypes.some(s => staffType.toUpperCase().includes(s.toUpperCase())));
        
        if (isSupreme) {
            // VGK4U_SUPREME / RVZ_SUPREME: Render ALL sections & items from MENU_MASTER
            console.log('[DC-SIDEBAR] Supreme bypass: Rendering all', menuMaster.length, 'sections');
            return { sections: this.transformMenuMasterToSidebar(menuMaster, null) };
        }
        
        // For other roles: Check if they have any access
        const hasMenuCodes = this.allowedMenuCodes && this.allowedMenuCodes instanceof Set && this.allowedMenuCodes.size > 0;
        const hasMenuPaths = this.allowedMenuPaths && this.allowedMenuPaths instanceof Set && this.allowedMenuPaths.size > 0;
        
        if (!hasMenuCodes && !hasMenuPaths) {
            return {
                sections: [],
                zeroAccess: true,
                message: this.zeroAccessMessage || 'No menu access granted. Contact your administrator (EA/VGK) to request access.'
            };
        }
        
        // Filter MENU_MASTER by allowed menu_codes
        const filteredSections = this.transformMenuMasterToSidebar(menuMaster, this.allowedMenuCodes);
        
        console.log('[DC-SIDEBAR] Filtered menu:', filteredSections.length, 'sections for', staffType);
        return { sections: filteredSections };
    },
    
    // DC Protocol (Jan 22, 2026): Transform MENU_MASTER to sidebar format
    // FIX: Use route_path for filtering to resolve menu_code format mismatch
    // allowedMenuPaths contains route_paths from /my-menus API (e.g., "/staff/my-attendance")
    // MENU_MASTER item.route contains matching route paths
    transformMenuMasterToSidebar: function(menuMaster, allowedMenuCodes) {
        const sections = [];
        
        // DC Protocol: Use allowedMenuPaths (route-based) for reliable filtering
        // This fixes menu_code format mismatch: MENU_MASTER uses UPPERCASE, database uses lowercase
        const allowedPaths = this.allowedMenuPaths;
        const hasRouteAccess = allowedPaths && allowedPaths instanceof Set && allowedPaths.size > 0;
        
        for (const section of menuMaster) {
            const sectionItems = [];
            const sectionSubSections = [];
            
            // Process regular items
            if (section.items) {
                for (const item of section.items) {
                    // DC Protocol: Match by route_path (reliable) instead of menu_code (format mismatch)
                    const shouldInclude = !hasRouteAccess || (allowedPaths && allowedPaths.has(item.route));
                    if (shouldInclude) {
                        sectionItems.push({
                            icon: item.icon || 'fas fa-circle',
                            label: item.label,
                            href: item.route,
                            menu_code: item.menu_code
                        });
                    }
                }
            }
            
            // Process subSections (for ACCOUNTS, ZYNOVA, MNR, MNR USER SIDEBAR)
            if (section.subSections) {
                for (const subSection of section.subSections) {
                    const subItems = [];
                    
                    for (const item of subSection.items || []) {
                        // DC Protocol: Match by route_path for subSection items too
                        const shouldInclude = !hasRouteAccess || (allowedPaths && allowedPaths.has(item.route));
                        if (shouldInclude) {
                            subItems.push({
                                icon: item.icon || 'fas fa-circle',
                                label: item.label,
                                href: item.route,
                                menu_code: item.menu_code
                            });
                        }
                    }
                    
                    if (subItems.length > 0) {
                        sectionSubSections.push({
                            id: subSection.sub_section_code,
                            title: subSection.sub_section_label,
                            items: subItems
                        });
                    }
                }
            }
            
            // Only include section if it has visible items
            const hasItems = sectionItems.length > 0 || sectionSubSections.length > 0;
            if (hasItems) {
                sections.push({
                    id: section.section_code.toLowerCase().replace(/_/g, '-'),
                    title: section.section_label,
                    order: section.order,
                    items: sectionItems,
                    subSections: sectionSubSections
                });
            }
        }
        
        // Sort by order to maintain PDF sequence
        sections.sort((a, b) => (a.order || 999) - (b.order || 999));
        
        return sections;
    },


    // Get localStorage key for section state (role-specific)
    getStorageKey: function() {
        const roleName = this.userData?.role_name || 'Employee';
        const safeRoleName = roleName.replace(/\s+/g, '_').toLowerCase();
        return `staff_sidebar_state_${safeRoleName}`;
    },

    // Generate unique section ID with role prefix for DC compliance
    generateSectionId: function(sectionBaseId) {
        const roleName = this.userData?.role_name || 'Employee';
        const safeRoleName = roleName.replace(/\s+/g, '_').toLowerCase();
        return `${safeRoleName}_${sectionBaseId}`;
    },

    // Toggle sidebar visibility (mobile)
    toggleSidebar: function() {
        const sidebar = document.getElementById('staffSidebar');
        const backdrop = document.getElementById('sidebarBackdrop');
        const body = document.body;
        
        if (sidebar) {
            const isOpen = sidebar.classList.contains('sidebar-open');
            if (isOpen) {
                sidebar.classList.remove('sidebar-open');
                backdrop?.classList.remove('active');
                body.classList.remove('sidebar-active');
            } else {
                sidebar.classList.add('sidebar-open');
                backdrop?.classList.add('active');
                body.classList.add('sidebar-active');
            }
            // Save mobile sidebar state
            localStorage.setItem('staff_sidebar_mobile_open', !isOpen);
        }
    },

    // Close sidebar (mobile)
    closeSidebar: function() {
        const sidebar = document.getElementById('staffSidebar');
        const backdrop = document.getElementById('sidebarBackdrop');
        const body = document.body;
        
        sidebar?.classList.remove('sidebar-open');
        backdrop?.classList.remove('active');
        body.classList.remove('sidebar-active');
        localStorage.setItem('staff_sidebar_mobile_open', 'false');
    },

    // Toggle desktop collapsed state
    toggleDesktopCollapse: function() {
        const sidebar = document.getElementById('staffSidebar');
        const mainContent = document.querySelector('.main-content');
        const body = document.body;
        
        if (sidebar) {
            const isCollapsed = sidebar.classList.contains('sidebar-collapsed');
            if (isCollapsed) {
                sidebar.classList.remove('sidebar-collapsed');
                body.classList.remove('sidebar-collapsed-mode');
            } else {
                sidebar.classList.add('sidebar-collapsed');
                body.classList.add('sidebar-collapsed-mode');
            }
            // Save desktop collapse state
            localStorage.setItem('staff_sidebar_collapsed', !isCollapsed);
        }
    },

    // Restore sidebar states
    restoreSidebarState: function() {
        const sidebar = document.getElementById('staffSidebar');
        if (!sidebar) return;
        
        // Desktop: restore collapsed state
        const isCollapsed = localStorage.getItem('staff_sidebar_collapsed') === 'true';
        if (isCollapsed && window.innerWidth >= 768) {
            sidebar.classList.add('sidebar-collapsed');
            document.body.classList.add('sidebar-collapsed-mode');
        }
    },

    // Create mobile hamburger button
    createMobileToggle: function() {
        // Only create if it doesn't exist
        if (document.getElementById('sidebarMobileToggle')) return;
        
        const toggleBtn = document.createElement('button');
        toggleBtn.id = 'sidebarMobileToggle';
        toggleBtn.className = 'sidebar-mobile-toggle';
        toggleBtn.setAttribute('aria-label', 'Toggle Menu');
        toggleBtn.innerHTML = '<i class="fas fa-bars"></i>';
        toggleBtn.onclick = () => this.toggleSidebar();
        
        document.body.appendChild(toggleBtn);
    },

    // Create backdrop overlay
    createBackdrop: function() {
        // Only create if it doesn't exist
        if (document.getElementById('sidebarBackdrop')) return;
        
        const backdrop = document.createElement('div');
        backdrop.id = 'sidebarBackdrop';
        backdrop.className = 'sidebar-backdrop';
        backdrop.onclick = () => this.closeSidebar();
        
        document.body.appendChild(backdrop);
    },

    // Render sidebar HTML with collapsible groups
    renderSidebar: function() {
        const menu = this.getMenuForRole();
        const userName = this.userData?.full_name || 'Staff Member';
        const roleName = this.userData?.role_name || 'Employee';
        const roleClass = this.getRoleClass(roleName);

        let html = `
            <div class="sidebar-header">
                <div class="sidebar-header-row">
                    <button class="sidebar-close-btn" onclick="StaffSidebar.closeSidebar()" aria-label="Close Menu">
                        <i class="fas fa-times"></i>
                    </button>
                    <button class="sidebar-collapse-btn" onclick="StaffSidebar.toggleDesktopCollapse()" aria-label="Collapse Sidebar">
                        <i class="fas fa-chevron-left"></i>
                    </button>
                </div>
                <div class="sidebar-tagline">STAFF PORTAL</div>
            </div>
            
            <nav class="sidebar-nav">
        `;

        // Zero-Default Access Policy: Show message when no menus granted
        if (menu.zeroAccess) {
            html += `
                <div class="sidebar-zero-access">
                    <div class="zero-access-icon">
                        <i class="fas fa-lock"></i>
                    </div>
                    <div class="zero-access-message">
                        ${this.escapeHtml(menu.message)}
                    </div>
                    <div class="zero-access-help">
                        <small>Contact EA/VGK team for access</small>
                    </div>
                </div>
            `;
            html += '</nav>';
            return html;
        }

        const isProgressActive  = this.currentPath === '/staff/progress';
        const isOverviewActive  = this.currentPath.startsWith('/staff/overview');
        const isDayPlannerActive = this.currentPath === '/staff/tasks/day-planner';
        const isTimesheetActive = this.currentPath === '/staff/timesheet' || this.currentPath === '/staff/my-timesheet';
        const isKraStatusActive = this.currentPath === '/staff/kra-status';

        // Overview link: key leadership roles only (DC Protocol: exact match)
        // Check role_code, role object sub-field, role_name, and staff_type for maximum compatibility
        const _ovUd = this.userData || {};
        const _ovRc = (_ovUd.role_code || _ovUd.role?.role_code || '').toString().toLowerCase().trim();
        const _ovRn = (_ovUd.role_name  || _ovUd.role?.role_name  || '').toString().toUpperCase().trim();
        const _ovSt = (_ovUd.staff_type || '').toString().toUpperCase().trim();
        const _showOverview = (
            ['vgk4u','vgk4u_supreme','key_leadership','ea','executive_admin'].includes(_ovRc) ||
            _ovRc.includes('vgk') ||
            ['VGK4U','VGK4U SUPREME','VGK MENTOR','KEY LEADERSHIP','EA','EXECUTIVE ADMIN'].includes(_ovRn) ||
            _ovRn.includes('VGK') ||
            ['VGK4U','VGK4U SUPREME'].includes(_ovSt)
        );

        const isRestrictedFreelancer = this.userData?.staff_type === 'FREELANCER' && this.userData?.freelancer_access_mode === 'only_leads';

        if (!isRestrictedFreelancer) {
            html += `
                <a href="/staff/progress" class="nav-item pinned-top-link ${isProgressActive ? 'active' : ''}">
                    <i class="fas fa-chart-line"></i>
                    <span>Progress</span>
                </a>
                ${_showOverview ? `
                <a href="/staff/overview" class="nav-item pinned-top-link ${isOverviewActive ? 'active' : ''}">
                    <i class="fas fa-table-cells"></i>
                    <span>Overview</span>
                </a>` : ''}
                <a href="/staff/tasks/day-planner" class="nav-item pinned-top-link ${isDayPlannerActive ? 'active' : ''}">
                    <i class="fas fa-calendar-day"></i>
                    <span>Task Planner</span>
                </a>
                <a href="/staff/kra-status" class="nav-item pinned-top-link ${isKraStatusActive ? 'active' : ''}">
                    <i class="fas fa-chart-bar"></i>
                    <span>KRA Status</span>
                </a>
                <a href="/staff/timesheet" class="nav-item pinned-top-link ${isTimesheetActive ? 'active' : ''}">
                    <i class="fas fa-clock"></i>
                    <span>Time Sheet</span>
                </a>
            `;
        }

        for (const section of menu.sections) {
            if (section.id === 'progress' || section.title === 'PROGRESS') {
                continue;
            }
            
            const baseSectionId = section.id || section.title.toLowerCase().replace(/\s+/g, '-');
            const uniqueSectionId = this.generateSectionId(baseSectionId);
            
            html += `
                <div class="sidebar-group collapsed" data-section-id="${uniqueSectionId}">
                    <button class="sidebar-group-toggle" aria-expanded="false">
                        <span class="sidebar-group-title">${section.title}</span>
                        <i class="fas fa-chevron-down sidebar-group-caret"></i>
                    </button>
                    <div class="sidebar-group-items">
            `;
            
            // DC Protocol (Jan 12, 2026): Unified rendering - all sections use subSections from API
            // Removed special MNR USER handling - now uses same structure as ACCOUNTS, ZYNOVA, MNR
            const sectionItems = section.items || [];
            for (const item of sectionItems) {
                const isActive = this.currentPath === item.href || 
                               (item.href !== '/staff/dashboard' && this.currentPath.startsWith(item.href));
                const activeClass = isActive ? 'active' : '';
                
                html += `
                    <a href="${item.href}" class="nav-item ${activeClass}">
                        <i class="${item.icon}"></i>
                        <span>${item.label}</span>
                    </a>
                `;
            }
            
            // Render nested sub-sections (DC Protocol: Nested collapsible groups)
            if (section.subSections && section.subSections.length > 0) {
                console.log('[DC-RENDER] Rendering', section.subSections.length, 'subSections for', section.title);
                for (const subSection of section.subSections) {
                    const baseSubSectionId = subSection.id || subSection.title.toLowerCase().replace(/\s+/g, '-');
                    const uniqueSubSectionId = this.generateSectionId(baseSubSectionId);
                    const subIcon = subSection.icon || 'fas fa-folder';
                    
                    html += `
                        <div class="sidebar-sub-group collapsed" data-section-id="${uniqueSubSectionId}">
                            <button class="sidebar-sub-group-toggle" aria-expanded="false">
                                <i class="${subIcon} sub-group-icon"></i>
                                <span class="sidebar-sub-group-title">${subSection.title}</span>
                                <i class="fas fa-chevron-right sidebar-sub-group-caret"></i>
                            </button>
                            <div class="sidebar-sub-group-items">
                    `;
                    
                    // DC Protocol (Jan 11, 2026): Null-safe sub-item rendering
                    const subItems = subSection.items || [];
                    for (const subItem of subItems) {
                        const isSubActive = this.currentPath === subItem.href || 
                                          (subItem.href !== '/staff/dashboard' && this.currentPath.startsWith(subItem.href));
                        const subActiveClass = isSubActive ? 'active' : '';
                        
                        html += `
                            <a href="${subItem.href}" class="nav-item sub-nav-item ${subActiveClass}">
                                <i class="${subItem.icon}"></i>
                                <span>${subItem.label}</span>
                            </a>
                        `;
                    }
                    
                    html += `
                            </div>
                        </div>
                    `;
                }
            }
            
            // DC Protocol (Jan 9, 2026): Render standalone items (items without parent grouping)
            if (section.standaloneItems && section.standaloneItems.length > 0) {
                for (const item of section.standaloneItems) {
                    const isActive = this.currentPath === item.href || 
                                   (item.href !== '/staff/dashboard' && this.currentPath.startsWith(item.href));
                    const activeClass = isActive ? 'active' : '';
                    
                    html += `
                        <a href="${item.href}" class="nav-item ${activeClass}">
                            <i class="${item.icon || 'fas fa-circle'}"></i>
                            <span>${item.label}</span>
                        </a>
                    `;
                }
            }
            
            html += `
                    </div>
                </div>
            `;
        }

        html += `
            </nav>
            
            <div class="sidebar-footer">
                <div class="settings-section">
                    <a href="#" class="nav-item settings-item" onclick="ThemeManager.toggle(); return false;">
                        <i class="${ThemeManager.getCurrentTheme() === 'dark' ? 'fas fa-moon' : 'fas fa-sun'} theme-toggle-icon"></i>
                        <span class="theme-toggle-text">${ThemeManager.getCurrentTheme() === 'dark' ? 'Dark Mode' : 'Light Mode'}</span>
                    </a>
                    <a href="/staff/change-password" class="nav-item settings-item">
                        <i class="fas fa-key"></i>
                        <span>Change Password</span>
                    </a>
                </div>
                <a href="#" class="nav-item logout-btn" onclick="StaffSidebar.logout(); return false;">
                    <i class="fas fa-sign-out-alt"></i>
                    <span>Logout</span>
                </a>
            </div>
        `;

        return html;
    },

    // DC Protocol (Jan 10, 2026): Render MNR USER items with nested collapsible structure
    // Matches the regular MNR user portal sidebar experience
    renderMnrUserItems: function(items) {
        console.log('[DC-MNR-USER-RENDER] Called with', items?.length || 0, 'items');
        if (!items || items.length === 0) return '';
        
        // DC Protocol (Jan 10, 2026): Exclude legacy/consolidated menu items
        const excludedMenuCodes = [
            'staff_mnr_user_profile',
            'staff_mnr_user_create',
            'staff_mnr_user_create_member',
            'staff_mnr_user_popups',
            'staff_mnr_user_members_all',
            'staff_mnr_user_members_direct',
            'staff_mnr_user_members_picture',
            'staff_mnr_user_members_ved',
            'staff_mnr_user_mnr_direct',
            'staff_mnr_user_direct',
            'staff_mnr_user_mnr_matching',
            'staff_mnr_user_matching',
            'staff_mnr_user_ved',
            'staff_mnr_user_mnr_ved',
            'staff_mnr_user_guru',
            'staff_mnr_user_mnr_guru',
            'staff_mnr_user_withdrawals',
            'staff_mnr_user_mnr_withdrawals',
            'staff_mnr_user_points',
            'staff_mnr_user_mnr_points',
            'staff_mnr_user_benefits',
            'staff_mnr_user_mnr_benefits',
            'staff_mnr_user_wallet',
            'staff_mnr_user_mnr_wallet',
            // DC Protocol (Jan 10, 2026): MyntReal submenu items - consolidated into main menu item
            'staff_mnr_user_myntreal',
            'staff_mnr_user_myntreal_leads',
            'staff_mnr_user_myntreal_franchise',
            'staff_mnr_user_myntreal_properties',
            'staff_mnr_user_myntreal_earnings',
            // DC Protocol (Jan 10, 2026): Coupon Modules submenu items - consolidated into single menu item
            'staff_mnr_user_coupons',
            'staff_mnr_user_coupons_red',
            'staff_mnr_user_coupons_green',
            'staff_mnr_user_coupons_transfer',
            'staff_mnr_user_coupons_ev_discount',
            'staff_mnr_user_coupons_history',
            'staff_mnr_user_red_coupons',
            'staff_mnr_user_green_coupons',
            'staff_mnr_user_transfer_coupons',
            'staff_mnr_user_ev_discount_coupons',
            'staff_mnr_user_coupon_history',
            // DC Protocol (Jan 10, 2026): Awards & Bonanza submenu items - consolidated into single menu item
            'staff_mnr_user_awards',
            'staff_mnr_user_awards_bonanza',
            'staff_mnr_user_bonanza_status',
            'staff_mnr_user_bonanza',
            // DC Protocol (Jan 10, 2026): Announcements submenu items - consolidated into single menu item
            'staff_mnr_user_announcements',
            'staff_mnr_user_announcements_create',
            'staff_mnr_user_announcements_pending',
            'staff_mnr_user_create_announcement',
            'staff_mnr_user_pending_approvals'
        ];
        
        // Filter out excluded items
        items = items.filter(item => !excludedMenuCodes.includes(item.menu_code));
        
        // Debug: Log first few items to check parent_section
        items.slice(0, 5).forEach((item, i) => {
            console.log(`[DC-MNR-USER-RENDER] Item ${i}: menu_code=${item.menu_code}, parent_section=${item.parent_section || 'NONE'}, label=${item.label}`);
        });
        
        // Define parent menu codes and their display properties
        // DC Protocol (Jan 10, 2026): Removed all collapsible menus - consolidated into single menu items
        const parentMenuDefs = {
            'staff_mnr_user_vgk4u': { title: 'VGK4U', icon: 'fas fa-building', order: 5 }
            // DC Protocol (Jan 10, 2026): Removed staff_mnr_user_coupons, staff_mnr_user_awards, staff_mnr_user_announcements - consolidated
        };
        
        // Separate items into parents, children, and standalone
        const childrenByParent = {};
        const parentItems = [];
        const standaloneItems = [];
        
        items.forEach(item => {
            const menuCode = item.menu_code || '';
            const parentSection = item.parent_section || '';
            
            if (parentSection && parentMenuDefs[parentSection]) {
                // This is a child item
                if (!childrenByParent[parentSection]) {
                    childrenByParent[parentSection] = [];
                }
                childrenByParent[parentSection].push(item);
            } else if (parentMenuDefs[menuCode]) {
                // This is a parent item (menu_code matches a parent def)
                parentItems.push({ ...item, parentCode: menuCode });
            } else {
                // Standalone item
                standaloneItems.push(item);
            }
        });
        
        console.log('[DC-MNR-USER-RENDER] Categorized:', parentItems.length, 'parents,', Object.keys(childrenByParent).length, 'groups,', standaloneItems.length, 'standalone');
        Object.keys(childrenByParent).forEach(key => {
            console.log(`[DC-MNR-USER-RENDER] Children of ${key}:`, childrenByParent[key].length);
        });
        
        let html = '';
        
        // Render standalone items first (Member Dashboard, Create Member, etc.)
        standaloneItems.forEach(item => {
            const isActive = this.currentPath === item.href || 
                           (item.href !== '/staff/dashboard' && this.currentPath.startsWith(item.href));
            const activeClass = isActive ? 'active' : '';
            html += `
                <a href="${item.href}" class="nav-item ${activeClass}">
                    <i class="${item.icon || 'fas fa-circle'}"></i>
                    <span>${item.label}</span>
                </a>
            `;
        });
        
        // DC Protocol (Jan 10, 2026): Inject static "MNR User MyntReal" menu item after standalone items
        const myntRealActive = this.currentPath.includes('/staff/mnr-user/myntreal') ? 'active' : '';
        html += `
            <a href="/staff/mnr-user/myntreal/properties" class="nav-item ${myntRealActive}">
                <i class="fas fa-gem"></i>
                <span>MNR — Myntreal</span>
            </a>
        `;
        
        // DC Protocol (Jan 10, 2026): Inject static "MNR User Coupons" menu item
        const couponsActive = this.currentPath.includes('/staff/mnr-user/coupons') ? 'active' : '';
        html += `
            <a href="/staff/mnr-user/coupons" class="nav-item ${couponsActive}">
                <i class="fas fa-ticket-alt"></i>
                <span>MNR — Coupons</span>
            </a>
        `;
        
        // DC Protocol (Jan 10, 2026): Inject static "MNR User Awards" menu item
        const awardsActive = this.currentPath.includes('/staff/mnr-user/awards') ? 'active' : '';
        html += `
            <a href="/staff/mnr-user/awards" class="nav-item ${awardsActive}">
                <i class="fas fa-trophy"></i>
                <span>MNR — Awards</span>
            </a>
        `;
        
        // DC Protocol (Jan 10, 2026): Inject static "MNR User Allowances" menu item
        const allowancesActive = this.currentPath.includes('/staff/mnr-user/allowances') ? 'active' : '';
        html += `
            <a href="/staff/mnr-user/allowances" class="nav-item ${allowancesActive}">
                <i class="fas fa-hand-holding-usd"></i>
                <span>MNR — Allowances</span>
            </a>
        `;
        
        // Sort parent items by order
        parentItems.sort((a, b) => {
            const aOrder = parentMenuDefs[a.parentCode]?.order || 99;
            const bOrder = parentMenuDefs[b.parentCode]?.order || 99;
            return aOrder - bOrder;
        });
        
        // Render collapsible parent groups with children
        parentItems.forEach(parent => {
            const parentCode = parent.parentCode;
            const parentDef = parentMenuDefs[parentCode];
            const children = childrenByParent[parentCode] || [];
            
            if (children.length === 0) {
                // Parent without children - render as standalone
                const isActive = this.currentPath === parent.href || 
                               (parent.href !== '/staff/dashboard' && this.currentPath.startsWith(parent.href));
                const activeClass = isActive ? 'active' : '';
                html += `
                    <a href="${parent.href}" class="nav-item ${activeClass}">
                        <i class="${parent.icon || parentDef.icon}"></i>
                        <span>${parent.label}</span>
                    </a>
                `;
            } else {
                // Parent with children - render as collapsible group
                const groupId = `mnr-user-${parentCode}`;
                html += `
                    <div class="sidebar-sub-group collapsed" data-section-id="${groupId}">
                        <button class="sidebar-sub-group-toggle" aria-expanded="false">
                            <i class="${parentDef.icon} sub-group-icon"></i>
                            <span class="sidebar-sub-group-title">${parentDef.title}</span>
                            <i class="fas fa-chevron-right sidebar-sub-group-caret"></i>
                        </button>
                        <div class="sidebar-sub-group-items">
                `;
                
                // Render child items
                children.forEach(child => {
                    const isActive = this.currentPath === child.href || 
                                   (child.href !== '/staff/dashboard' && this.currentPath.startsWith(child.href));
                    const activeClass = isActive ? 'active' : '';
                    html += `
                        <a href="${child.href}" class="nav-item sub-nav-item ${activeClass}">
                            <i class="${child.icon || 'fas fa-circle'}"></i>
                            <span>${child.label}</span>
                        </a>
                    `;
                });
                
                html += `
                        </div>
                    </div>
                `;
            }
        });
        
        return html;
    },

    // Bind click handlers to group toggles
    bindGroupToggles: function() {
        // Main group toggles
        const toggleButtons = document.querySelectorAll('.sidebar-group-toggle');
        toggleButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const group = button.closest('.sidebar-group');
                if (group) {
                    this.toggleSection(group);
                }
            });
        });
        
        // Sub-group toggles (DC Protocol: Nested menu support)
        const subToggleButtons = document.querySelectorAll('.sidebar-sub-group-toggle');
        subToggleButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const subGroup = button.closest('.sidebar-sub-group');
                if (subGroup) {
                    this.toggleSubSection(subGroup);
                }
            });
        });
    },
    
    // Toggle a sub-section's collapsed state
    toggleSubSection: function(subGroupElement) {
        const isCollapsed = subGroupElement.classList.contains('collapsed');
        const toggle = subGroupElement.querySelector('.sidebar-sub-group-toggle');
        
        if (isCollapsed) {
            subGroupElement.classList.remove('collapsed');
            toggle?.setAttribute('aria-expanded', 'true');
        } else {
            subGroupElement.classList.add('collapsed');
            toggle?.setAttribute('aria-expanded', 'false');
        }
        
        // Save state to localStorage
        this.saveSectionStates();
    },

    // Toggle a section's collapsed state
    toggleSection: function(groupElement) {
        const isCollapsed = groupElement.classList.contains('collapsed');
        const toggle = groupElement.querySelector('.sidebar-group-toggle');
        
        if (isCollapsed) {
            groupElement.classList.remove('collapsed');
            toggle?.setAttribute('aria-expanded', 'true');
        } else {
            groupElement.classList.add('collapsed');
            toggle?.setAttribute('aria-expanded', 'false');
        }
        
        // Save state to localStorage
        this.saveSectionStates();
    },

    // Save all section states to localStorage
    saveSectionStates: function() {
        const states = {};
        
        // Save main group states
        const groups = document.querySelectorAll('.sidebar-group');
        groups.forEach(group => {
            const sectionId = group.dataset.sectionId;
            if (sectionId) {
                states[sectionId] = !group.classList.contains('collapsed');
            }
        });
        
        // Save sub-group states (DC Protocol: Nested menu support)
        const subGroups = document.querySelectorAll('.sidebar-sub-group');
        subGroups.forEach(subGroup => {
            const sectionId = subGroup.dataset.sectionId;
            if (sectionId) {
                states[sectionId] = !subGroup.classList.contains('collapsed');
            }
        });
        
        try {
            localStorage.setItem(this.getStorageKey(), JSON.stringify(states));
        } catch (e) {
            console.warn('Could not save sidebar state:', e);
        }
    },

    // Restore section states from localStorage
    // DC Protocol: Default is COLLAPSED, only expand sections that were saved as open
    restoreSectionStates: function() {
        try {
            const savedStates = localStorage.getItem(this.getStorageKey());
            if (!savedStates) return; // No saved state = keep default collapsed
            
            const states = JSON.parse(savedStates);
            
            // Restore main group states
            const groups = document.querySelectorAll('.sidebar-group');
            groups.forEach(group => {
                const sectionId = group.dataset.sectionId;
                if (sectionId && states.hasOwnProperty(sectionId)) {
                    const isExpanded = states[sectionId];
                    const toggle = group.querySelector('.sidebar-group-toggle');
                    
                    if (isExpanded) {
                        group.classList.remove('collapsed');
                        toggle?.setAttribute('aria-expanded', 'true');
                    }
                }
            });
            
            // Restore sub-group states (DC Protocol: Nested menu support)
            const subGroups = document.querySelectorAll('.sidebar-sub-group');
            subGroups.forEach(subGroup => {
                const sectionId = subGroup.dataset.sectionId;
                if (sectionId && states.hasOwnProperty(sectionId)) {
                    const isExpanded = states[sectionId];
                    const toggle = subGroup.querySelector('.sidebar-sub-group-toggle');
                    
                    if (isExpanded) {
                        subGroup.classList.remove('collapsed');
                        toggle?.setAttribute('aria-expanded', 'true');
                    }
                }
            });
        } catch (e) {
            console.warn('Could not restore sidebar state:', e);
        }
    },

    // Auto-expand section containing the active page (runs after state restore)
    // This forces expansion even if saved state was collapsed, ensuring active link is always visible
    autoExpandActiveSection: function() {
        const activeItem = document.querySelector('.sidebar-nav .nav-item.active');
        if (activeItem) {
            // Check if active item is in a sub-group
            const parentSubGroup = activeItem.closest('.sidebar-sub-group');
            if (parentSubGroup) {
                const wasCollapsed = parentSubGroup.classList.contains('collapsed');
                if (wasCollapsed) {
                    parentSubGroup.classList.remove('collapsed');
                    const toggle = parentSubGroup.querySelector('.sidebar-sub-group-toggle');
                    toggle?.setAttribute('aria-expanded', 'true');
                }
            }
            
            // Also expand the parent main group
            const parentGroup = activeItem.closest('.sidebar-group');
            if (parentGroup) {
                const wasCollapsed = parentGroup.classList.contains('collapsed');
                
                if (wasCollapsed) {
                    parentGroup.classList.remove('collapsed');
                    const toggle = parentGroup.querySelector('.sidebar-group-toggle');
                    toggle?.setAttribute('aria-expanded', 'true');
                }
                
                // Persist the updated open state immediately
                this.saveSectionStates();
            }

            // Scroll the active item into view within the sidebar nav
            setTimeout(() => {
                try {
                    activeItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
                } catch(e) {
                    activeItem.scrollIntoView(false);
                }
            }, 150);
        }
    },

    // Get role badge class
    getRoleClass: function(roleName) {
        const classes = {
            // New hierarchy-based roles
            'VGK Mentor': 'role-vgk4u',
            'VGK4U Supreme': 'role-vgk4u',
            'Key Leadership': 'role-key-leadership',
            'Leadership Role': 'role-leadership',
            'HR': 'role-hr',
            'Team Leader': 'role-team-leader',
            'Manager': 'role-manager',
            'Senior Executive': 'role-senior-exec',
            'Junior Executive': 'role-junior-exec',
            // Legacy roles
            'VGK Mentor': 'role-vgk4u',
            'VGK4U Supreme Admin': 'role-vgk4u',
            'HR Manager': 'role-hr',
            'Supervisor': 'role-supervisor',
            'Accounts': 'role-accounts',
            'Employee': 'role-employee'
        };
        return classes[roleName] || 'role-employee';
    },

    // Highlight current page
    highlightCurrentPage: function() {
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            if (item.getAttribute('href') === this.currentPath) {
                item.classList.add('active');
            }
        });
    },

    // Logout function
    logout: function() {
        localStorage.removeItem('staff_token');
        localStorage.removeItem('staff_user');
        // Clear all sidebar state keys for all roles
        Object.keys(localStorage).forEach(key => {
            if (key.startsWith('staff_sidebar_state_')) {
                localStorage.removeItem(key);
            }
        });
        window.location.href = '/staff/login';
    },

    // Escape HTML to prevent XSS
    escapeHtml: function(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

/**
 * Back Button Component
 * Adds a universal back button to page headers
 */
const StaffBackButton = {
    init: function(containerId = 'backButtonContainer') {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = `
            <button class="btn-back" onclick="StaffBackButton.goBack()">
                <i class="fas fa-arrow-left"></i>
                <span>Back</span>
            </button>
        `;
    },

    goBack: function() {
        if (window.history.length > 1) {
            window.history.back();
        } else {
            window.location.href = '/staff/dashboard';
        }
    }
};

// Sidebar CSS Styles (injected into page)
const StaffSidebarStyles = `
<style id="staffSidebarStyles">
/* Sidebar Container */
/* DC Protocol: Fixed height enables .sidebar-nav overflow-y scroll */
#staffSidebar {
    width: 260px;
    height: 100vh;
    min-height: 100vh;
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    color: #fff;
    display: flex;
    flex-direction: column;
    position: fixed;
    left: 0;
    top: 0;
    z-index: 1000;
    box-shadow: 4px 0 15px rgba(0,0,0,0.1);
    transition: all 0.3s ease;
}

/* Mobile Hamburger Toggle Button */
.sidebar-mobile-toggle {
    display: none;
    position: fixed;
    top: 12px;
    left: 12px;
    z-index: 1100;
    width: 44px;
    height: 44px;
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    border: none;
    border-radius: 8px;
    color: #fff;
    font-size: 20px;
    cursor: pointer;
    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    transition: all 0.2s ease;
}

.sidebar-mobile-toggle:hover {
    background: #16213e;
    transform: scale(1.05);
}

/* Backdrop Overlay */
.sidebar-backdrop {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 999;
    opacity: 0;
    transition: opacity 0.3s ease;
}

.sidebar-backdrop.active {
    opacity: 1;
}

/* ========================================
   DC Protocol (Dec 31, 2025): Unified Header Component
   Purple gradient header for ALL pages (staff/admin/rvz)
   ======================================== */
.unified-header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 64px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
    z-index: 1000;
    box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
}

.unified-header .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
}

.unified-header .header-hamburger {
    display: none;
    width: 40px;
    height: 40px;
    background: rgba(255,255,255,0.15);
    border: none;
    border-radius: 8px;
    color: white;
    font-size: 18px;
    cursor: pointer;
    transition: all 0.2s;
}

.unified-header .header-hamburger:hover {
    background: rgba(255,255,255,0.25);
}

.unified-header .header-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    text-decoration: none;
    color: white;
}

.unified-header .header-logo-img {
    height: 36px;
    width: auto;
}

.unified-header .header-brand-text {
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

.unified-header .header-page-title {
    display: flex;
    align-items: center;
    gap: 8px;
    padding-left: 16px;
    margin-left: 16px;
    border-left: 1px solid rgba(255,255,255,0.3);
    color: rgba(255,255,255,0.9);
    font-size: 15px;
    font-weight: 500;
}

.unified-header .header-right {
    display: flex;
    align-items: center;
    gap: 12px;
}

.unified-header .header-user-info {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 14px 6px 8px;
    background: rgba(255,255,255,0.15);
    border-radius: 30px;
}

.unified-header .header-user-avatar {
    width: 36px;
    height: 36px;
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 700;
    font-size: 14px;
}

.unified-header .header-user-details {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.unified-header .header-user-role {
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    text-transform: uppercase;
}

.unified-header .header-user-role.role-badge-supreme {
    background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
    color: white;
}

.unified-header .header-user-role.role-badge-hr {
    background: #8b5cf6;
    color: white;
}

.unified-header .header-user-role.role-badge-leadership {
    background: #f59e0b;
    color: white;
}

.unified-header .header-user-role.role-badge-default {
    background: rgba(255,255,255,0.2);
    color: white;
}

.unified-header .header-user-empid {
    font-size: 11px;
    color: rgba(255,255,255,0.8);
    font-weight: 500;
}

.unified-header .header-icon-btn {
    width: 38px;
    height: 38px;
    background: rgba(255,255,255,0.15);
    border: none;
    border-radius: 50%;
    color: white;
    font-size: 16px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    text-decoration: none;
    position: relative;
    transition: all 0.2s;
}

.unified-header .header-icon-btn:hover {
    background: rgba(255,255,255,0.25);
    transform: translateY(-2px);
}

.unified-header .header-logout-btn:hover {
    background: rgba(239, 68, 68, 0.8);
}

.unified-header .notification-badge {
    position: absolute;
    top: 2px;
    right: 2px;
    min-width: 16px;
    height: 16px;
    background: #ef4444;
    border-radius: 8px;
    font-size: 10px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 4px;
}

/* Body adjustment for unified header */
body.has-unified-header {
    padding-top: 64px;
}

body.has-unified-header #staffSidebar {
    top: 64px;
    height: calc(100vh - 64px);
}

body.has-unified-header .main-content {
    margin-top: 0;
}

/* Mobile responsive for unified header */
@media (max-width: 768px) {
    .unified-header {
        padding: 0 12px;
    }
    
    .unified-header .header-hamburger {
        display: flex;
    }
    
    .unified-header .header-page-title {
        display: none;
    }
    
    .unified-header .header-user-details {
        display: none;
    }
    
    .unified-header .header-icon-btn {
        width: 34px;
        height: 34px;
        font-size: 14px;
    }
}

/* Sidebar Header Row with Buttons */
.sidebar-header-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 12px;
}

/* Close Button (Mobile Only) */
.sidebar-close-btn {
    display: none;
    width: 36px;
    height: 36px;
    background: rgba(255,255,255,0.1);
    border: none;
    border-radius: 8px;
    color: #fff;
    font-size: 16px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.sidebar-close-btn:hover {
    background: rgba(255,255,255,0.2);
}

/* Collapse Button (Desktop Only) */
.sidebar-collapse-btn {
    width: 36px;
    height: 36px;
    background: rgba(255,255,255,0.1);
    border: none;
    border-radius: 8px;
    color: #fff;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s ease;
    margin-left: auto;
}

.sidebar-collapse-btn:hover {
    background: rgba(255,255,255,0.2);
}

/* Desktop Collapsed State */
#staffSidebar.sidebar-collapsed {
    width: 70px;
}

#staffSidebar.sidebar-collapsed .sidebar-brand,
#staffSidebar.sidebar-collapsed .sidebar-tagline,
#staffSidebar.sidebar-collapsed .user-info,
#staffSidebar.sidebar-collapsed .sidebar-group-title,
#staffSidebar.sidebar-collapsed .sidebar-group-caret,
#staffSidebar.sidebar-collapsed .nav-item span {
    display: none;
}

#staffSidebar.sidebar-collapsed .sidebar-header-row {
    justify-content: center;
}

#staffSidebar.sidebar-collapsed .sidebar-collapse-btn i {
    transform: rotate(180deg);
}

#staffSidebar.sidebar-collapsed .sidebar-user {
    justify-content: center;
    padding: 15px 10px;
}

#staffSidebar.sidebar-collapsed .user-avatar i {
    font-size: 28px;
}

#staffSidebar.sidebar-collapsed .nav-item {
    justify-content: center;
    padding: 14px 10px;
}

#staffSidebar.sidebar-collapsed .nav-item i {
    font-size: 18px;
    width: auto;
}

#staffSidebar.sidebar-collapsed .sidebar-group-toggle {
    justify-content: center;
    padding: 8px;
}

/* Main content adjustment for collapsed sidebar */
body.sidebar-collapsed-mode .main-content {
    margin-left: 70px !important;
}

/* Sidebar Header */
.sidebar-header {
    padding: 16px 15px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    background: rgba(255,255,255,0.03);
}

.sidebar-brand {
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255,255,255,0.95);
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 8px;
}

.sidebar-logo {
    max-width: 140px;
    height: auto;
}

.sidebar-tagline {
    text-align: center;
    font-size: 11px;
    color: rgba(255,255,255,0.5);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-top: 8px;
}

/* User Section */
.sidebar-user {
    padding: 20px 15px;
    display: flex;
    align-items: center;
    gap: 12px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}

.user-avatar i {
    font-size: 40px;
    color: #6366f1;
}

.user-info {
    display: flex;
    flex-direction: column;
}

.user-name {
    font-size: 14px;
    font-weight: 600;
    color: #fff;
}

.user-role {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 4px;
    margin-top: 4px;
    display: inline-block;
    width: fit-content;
}

.role-vgk4u { background: #dc2626; color: #fff; }
.role-key-leadership { background: #ea580c; color: #fff; }
.role-leadership { background: #0891b2; color: #fff; }
.role-hr { background: #7c3aed; color: #fff; }
.role-team-leader { background: #2563eb; color: #fff; }
.role-manager { background: #059669; color: #fff; }
.role-senior-exec { background: #4f46e5; color: #fff; }
.role-junior-exec { background: #6b7280; color: #fff; }
.role-supervisor { background: #2563eb; color: #fff; }
.role-accounts { background: #059669; color: #fff; }
.role-employee { background: #6b7280; color: #fff; }

/* Navigation */
/* DC_SCROLLBAR_VIS_002 (Dec 07, 2025): Always-visible high-contrast scrollbar */
/* min-height:0 required for flex child to respect overflow-y scroll */
.sidebar-nav {
    flex: 1;
    min-height: 0;
    padding: 15px 0;
    overflow-y: scroll !important;
    overflow-x: hidden;
    scrollbar-gutter: stable;
    position: relative;
}

/* DC_SCROLLBAR_VIS_002: ALWAYS VISIBLE Scrollbar Track */
/* Visual indicator bar on right edge - always visible regardless of content */
.sidebar-nav::after {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 8px;
    height: 100%;
    background: linear-gradient(180deg, #1E3A5F 0%, #0F172A 50%, #1E3A5F 100%);
    pointer-events: none;
    z-index: 1;
    border-radius: 4px;
}

/* DC_SCROLLBAR_VIS_002: High-Contrast Scrollbar for Webkit (Chrome, Safari, Edge) */
.sidebar-nav::-webkit-scrollbar {
    width: 8px;
    display: block !important;
    background: #0F172A;
}

.sidebar-nav::-webkit-scrollbar-track {
    background: #0F172A;
    border-radius: 4px;
    box-shadow: inset 0 0 0 1px #1E3A5F;
}

.sidebar-nav::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #60A5FA 0%, #3B82F6 100%);
    border-radius: 4px;
    border: 1px solid #1E3A5F;
    min-height: 40px;
}

.sidebar-nav::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, #93C5FD 0%, #60A5FA 100%);
}

/* Firefox scrollbar - High contrast, always visible */
.sidebar-nav {
    scrollbar-width: auto;
    scrollbar-color: #60A5FA #0F172A;
}

/* Zero-Default Access Policy - Empty Menu State */
.sidebar-zero-access {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
    text-align: center;
    color: rgba(255,255,255,0.7);
}

.zero-access-icon {
    font-size: 48px;
    color: rgba(255,255,255,0.3);
    margin-bottom: 20px;
}

.zero-access-message {
    font-size: 14px;
    line-height: 1.5;
    color: rgba(255,255,255,0.6);
    margin-bottom: 15px;
    padding: 0 10px;
}

.zero-access-help {
    font-size: 11px;
    color: rgba(255,255,255,0.4);
}

.zero-access-help small {
    display: block;
}

/* Collapsible Sidebar Groups - MNR Pattern */
.sidebar-group {
    margin-bottom: 5px;
}

.sidebar-group-toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: 10px 20px;
    background: transparent;
    border: none;
    cursor: pointer;
    transition: all 0.2s ease;
}

.sidebar-group-toggle:hover {
    background: rgba(255,255,255,0.05);
}

.sidebar-group-title {
    font-size: 11px;
    font-weight: 600;
    color: rgba(255,255,255,0.5);
    text-transform: uppercase;
    letter-spacing: 1px;
}

.sidebar-group-caret {
    font-size: 10px;
    color: rgba(255,255,255,0.4);
    transition: transform 0.3s ease;
}

/* Collapsed state - caret rotates */
.sidebar-group.collapsed .sidebar-group-caret {
    transform: rotate(-90deg);
}

/* Group items container */
.sidebar-group-items {
    max-height: 600px;
    overflow-y: auto;
    transition: max-height 0.3s ease-out, opacity 0.3s ease;
    opacity: 1;
}

/* Collapsed state - hide items */
.sidebar-group.collapsed .sidebar-group-items {
    max-height: 0;
    opacity: 0;
}

/* DC Protocol: Nested Sub-Group Styles */
.sidebar-sub-group {
    margin: 4px 8px;
    border-radius: 8px;
    background: rgba(255,255,255,0.03);
    overflow: hidden;
}

.sidebar-sub-group-toggle {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    background: transparent;
    color: rgba(255,255,255,0.8);
    font-size: 12px;
    font-weight: 500;
    text-align: left;
    border: none;
    cursor: pointer;
    transition: all 0.2s ease;
}

.sidebar-sub-group-toggle:hover {
    background: rgba(255,255,255,0.08);
}

.sub-group-icon {
    font-size: 14px;
    color: #6366f1;
    width: 16px;
}

.sidebar-sub-group-title {
    flex: 1;
    font-size: 12px;
    color: rgba(255,255,255,0.85);
}

.sidebar-sub-group-caret {
    font-size: 10px;
    color: rgba(255,255,255,0.4);
    transition: transform 0.3s ease;
}

/* Sub-group expanded state - rotate caret */
.sidebar-sub-group:not(.collapsed) .sidebar-sub-group-caret {
    transform: rotate(90deg);
}

/* Sub-group items container */
.sidebar-sub-group-items {
    max-height: 400px;
    overflow-y: auto;
    transition: max-height 0.3s ease-out, opacity 0.3s ease;
    opacity: 1;
    background: rgba(0,0,0,0.15);
    border-radius: 0 0 8px 8px;
}

/* Sub-group collapsed state - hide items */
.sidebar-sub-group.collapsed .sidebar-sub-group-items {
    max-height: 0;
    opacity: 0;
}

/* Sub-nav items styling */
.sub-nav-item {
    padding: 10px 16px 10px 32px !important;
    font-size: 13px !important;
}

.sub-nav-item i {
    font-size: 13px !important;
    width: 18px !important;
}

.nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 20px;
    color: rgba(255,255,255,0.7);
    text-decoration: none;
    transition: all 0.2s ease;
    border-left: 3px solid transparent;
}

.nav-item:hover {
    background: rgba(255,255,255,0.1);
    color: #fff;
}

.nav-item.active {
    background: rgba(99, 102, 241, 0.2);
    color: #fff;
    border-left-color: #6366f1;
}

.nav-item i {
    width: 20px;
    text-align: center;
    font-size: 16px;
}

.nav-item span {
    font-size: 14px;
}

/* Footer */
.sidebar-footer {
    padding: 15px;
    border-top: 1px solid rgba(255,255,255,0.1);
}

.logout-btn {
    color: #ef4444 !important;
}

.logout-btn:hover {
    background: rgba(239, 68, 68, 0.2) !important;
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
    padding: 10px 15px;
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
    margin-right: 10px;
    font-size: 14px;
}

.settings-item span {
    font-size: 13px;
}

/* DC_SCROLLBAR_VIS_005: Force always-visible scrollbar in Chrome/Safari/Edge */
/* Chrome overlay scrollbar mode hides scrollbars - this forces them visible */
html {
    overflow-y: scroll !important;
    overflow-x: hidden;
}

/* Main Content Offset */
.main-content {
    margin-left: 260px !important;
    min-height: 100vh;
    background: #f3f4f6;
}

/* DC_SCROLLBAR_VIS_006: Custom scrollbar for Webkit browsers - ALWAYS VISIBLE */
::-webkit-scrollbar {
    width: 14px !important;
    height: 14px !important;
    background-color: #f1f1f1 !important;
}

::-webkit-scrollbar-track {
    background: #f1f1f1 !important;
    border-left: 1px solid #e0e0e0;
}

::-webkit-scrollbar-thumb {
    background: #888 !important;
    border-radius: 7px !important;
    border: 3px solid #f1f1f1 !important;
    min-height: 40px !important;
}

::-webkit-scrollbar-thumb:hover {
    background: #555 !important;
}

::-webkit-scrollbar-corner {
    background: #f1f1f1;
}

/* Firefox scrollbar - always visible */
* {
    scrollbar-width: auto !important;
    scrollbar-color: #888 #f1f1f1 !important;
}

/* Back Button */
.btn-back {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    color: #374151;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.btn-back:hover {
    background: #f3f4f6;
    border-color: #d1d5db;
}

.btn-back i {
    font-size: 12px;
}

/* Page Header with Back Button */
.page-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 24px;
}

.page-header h1 {
    margin: 0;
    font-size: 24px;
    color: #1f2937;
}

/* Responsive - Mobile View */
@media (max-width: 767px) {
    /* Show mobile hamburger toggle */
    .sidebar-mobile-toggle {
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    /* Show backdrop on mobile */
    .sidebar-backdrop {
        display: block;
        pointer-events: none;
    }
    
    .sidebar-backdrop.active {
        pointer-events: auto;
    }
    
    /* Sidebar off-canvas by default on mobile */
    #staffSidebar {
        width: 280px;
        height: 100vh;
        position: fixed;
        left: 0;
        top: 0;
        transform: translateX(-100%);
        transition: transform 0.3s ease;
    }
    
    /* Sidebar open state on mobile */
    #staffSidebar.sidebar-open {
        transform: translateX(0);
    }
    
    /* DC Protocol: Mobile Logo Section Optimization (~40-50px savings) */
    .sidebar-header {
        padding: 10px 12px;
    }
    
    .sidebar-brand {
        padding: 8px 12px;
        margin-bottom: 0;
    }
    
    .sidebar-logo {
        max-width: 100px;
    }
    
    .sidebar-tagline {
        display: none;
    }
    
    .sidebar-user {
        padding: 12px;
        gap: 10px;
    }
    
    .user-avatar i {
        font-size: 32px;
    }
    
    .user-name {
        font-size: 13px;
    }
    
    .user-role {
        font-size: 10px;
        padding: 2px 6px;
    }
    
    /* Show close button on mobile */
    .sidebar-close-btn {
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    /* Hide desktop collapse button on mobile */
    .sidebar-collapse-btn {
        display: none;
    }
    
    /* Main content full width on mobile */
    .main-content {
        margin-left: 0 !important;
        padding-top: 60px;
    }
    
    /* Keep groups functional on mobile */
    .sidebar-group-items {
        max-height: 500px;
        overflow-y: auto;
    }
    
    .sidebar-group.collapsed .sidebar-group-items {
        max-height: 0;
    }
    
    /* Prevent body scroll when sidebar is open */
    body.sidebar-active {
        overflow: hidden;
    }
}

/* Tablet and Desktop - Hide mobile toggle */
@media (min-width: 768px) {
    .sidebar-mobile-toggle {
        display: none !important;
    }
    
    .sidebar-backdrop {
        display: none !important;
    }
    
    .sidebar-close-btn {
        display: none !important;
    }
}
</style>
`;

// Auto-inject styles when script loads
if (!document.getElementById('staffSidebarStyles')) {
    document.head.insertAdjacentHTML('beforeend', StaffSidebarStyles);
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { StaffSidebar, StaffBackButton };
}

// ─── VGK Assistant Integration (DC_VGK_001) ───────────────────────────────
(function _vgkBoot() {
  function loadVGK() {
    if (!document.getElementById('vgk-script')) {
      const s = document.createElement('script');
      s.id = 'vgk-script'; s.src = '/vgk_assistant.js';
      document.head.appendChild(s);
    }
  }
  function syncCodes(sidebar) {
    if (sidebar && sidebar.allowedMenuCodes && sidebar.allowedMenuCodes.size > 0) {
      window.__VGK_ALLOWED_MENU_CODES__ = Array.from(sidebar.allowedMenuCodes);
      window.__VGK_COMPANY_ID__ = window.__activeCompanyId__ || null;
      window.__VGK_MENU_ROUTES__ = sidebar.menuRoutesForVGK || [];
    }
  }
  function init() {
    loadVGK();
    let n = 0;
    const iv = setInterval(() => {
      const sb = window.StaffSidebar;
      if (sb && sb.allowedMenuCodes && sb.allowedMenuCodes.size > 0) {
        syncCodes(sb);
        clearInterval(iv);
      } else if (++n > 50) clearInterval(iv);
    }, 100);
  }
  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', init); }
  else { init(); }
})();
