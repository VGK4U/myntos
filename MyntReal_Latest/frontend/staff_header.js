/**
 * Staff Portal Universal Header Component
 * DC Protocol Compliant: Single source of truth for all staff page headers
 * Matches Progress page header structure exactly (light theme)
 * Created: Nov 26, 2025
 * Updated: Jan 09, 2026 - Standardized to Progress page light theme header
 */

// DC Protocol Apr 2026: Changed from `const StaffHeader` to window assignment to prevent
// "Identifier already declared" SyntaxError when this file is loaded more than once
// (server.js template injects it AND the page HTML includes it explicitly).
window.StaffHeader = window.StaffHeader || {
    headerStyles: `
        <style id="staffHeaderStyles">
            .top-header {
                height: 64px;
                background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                position: sticky;
                top: 0;
                z-index: 100;
                margin-left: 0;
            }
            
            @media (max-width: 768px) {
                .top-header {
                    margin-left: 0 !important;
                }
            }
            
            .header-left {
                display: flex;
                align-items: center;
                gap: 16px;
            }
            
            .header-logo {
                height: 36px;
                width: auto;
            }
            
            .header-divider {
                width: 1px;
                height: 32px;
                background: rgba(255,255,255,0.2);
                margin: 0 8px;
            }
            
            .btn-back {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 8px 14px;
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 6px;
                color: #ffffff;
                font-size: 13px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
                text-decoration: none;
            }
            
            .btn-back:hover {
                background: rgba(255,255,255,0.2);
                color: #ffffff;
            }
            
            .btn-back i {
                font-size: 12px;
            }
            
            .page-title {
                font-size: 18px;
                font-weight: 600;
                color: #ffffff;
                display: flex;
                align-items: center;
                gap: 8px;
                margin: 0;
            }
            
            .page-title i {
                color: #10b981;
            }
            
            .header-right {
                display: flex;
                align-items: center;
                gap: 20px;
            }
            
            .user-info-header {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 8px 16px;
                background: rgba(255,255,255,0.1);
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.15);
            }
            
            .user-info-header .user-avatar-sm {
                width: 36px;
                height: 36px;
                background: linear-gradient(135deg, #10b981, #059669);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: 600;
                font-size: 14px;
            }
            
            .user-info-details {
                display: flex;
                flex-direction: column;
            }
            
            .user-info-name {
                font-size: 14px;
                font-weight: 600;
                color: #ffffff;
            }
            
            .user-info-meta {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 12px;
                color: rgba(255,255,255,0.7);
            }
            
            .user-info-role {
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 600;
                text-transform: uppercase;
            }
            
            .role-badge-supreme { background: #dc2626; color: #ffffff; }
            .role-badge-hr { background: #7c3aed; color: #ffffff; }
            .role-badge-leadership { background: #d97706; color: #ffffff; }
            .role-badge-mn-staff { background: #10b981; color: #ffffff; }
            .role-badge-mn-employee { background: #3b82f6; color: #ffffff; }
            .role-badge-freelancer { background: #db2777; color: #ffffff; }
            .role-badge-default { background: #10b981; color: #ffffff; }
            
            .btn-logout {
                padding: 8px 16px;
                background: linear-gradient(135deg, #10b981, #059669);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 6px;
                transition: all 0.2s;
            }
            
            .btn-logout:hover {
                background: linear-gradient(135deg, #059669, #047857);
            }
            
            /* MN Staff Banner - DC Protocol */
            .staff-type-banner {
                background: linear-gradient(90deg, #10b981 0%, #059669 100%);
                color: white;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 500;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-left: 260px;
                transition: margin-left 0.3s ease;
            }
            
            body.sidebar-collapsed-mode .staff-type-banner {
                margin-left: 70px;
            }
            
            @media (max-width: 768px) {
                .staff-type-banner {
                    margin-left: 0 !important;
                }
            }
            
            .staff-type-banner i {
                font-size: 14px;
            }
            
            .mn-staff-badge,
            .mn-employee-badge,
            .freelancer-badge {
                background: rgba(255,255,255,0.2);
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            
            .mn-employee-banner {
                background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
            }
            
            .freelancer-banner {
                background: linear-gradient(90deg, #db2777 0%, #be185d 100%);
            }
            
            /* Header Menu Search - DC Protocol Jan 2026 */
            .header-search-container {
                position: relative;
                flex: 0 1 320px;
                margin: 0 20px;
            }
            
            .header-search-input {
                width: 100%;
                padding: 10px 16px 10px 40px;
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 8px;
                color: #ffffff;
                font-size: 14px;
                transition: all 0.2s ease;
            }
            
            .header-search-input:focus {
                outline: none;
                background: rgba(255,255,255,0.15);
                border-color: #10b981;
                box-shadow: 0 0 0 3px rgba(16,185,129,0.2);
            }
            
            .header-search-input::placeholder {
                color: rgba(255,255,255,0.5);
            }
            
            .header-search-icon {
                position: absolute;
                left: 14px;
                top: 50%;
                transform: translateY(-50%);
                color: rgba(255,255,255,0.5);
                font-size: 14px;
                pointer-events: none;
            }
            
            .header-search-results {
                position: absolute;
                top: calc(100% + 8px);
                left: 0;
                right: 0;
                max-height: 400px;
                overflow-y: auto;
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.15);
                z-index: 1000;
                display: none;
            }
            
            .header-search-results.show {
                display: block;
            }
            
            .search-result-item {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 12px 16px;
                cursor: pointer;
                transition: background 0.15s ease;
                border-bottom: 1px solid #f3f4f6;
            }
            
            .search-result-item:hover,
            .search-result-item.active {
                background: #f3f4f6;
            }
            
            .search-result-item:last-child {
                border-bottom: none;
            }
            
            .search-result-icon {
                width: 32px;
                height: 32px;
                background: #e0e7ff;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #6366f1;
                font-size: 14px;
            }
            
            .search-result-info {
                flex: 1;
            }
            
            .search-result-name {
                font-size: 14px;
                font-weight: 500;
                color: #1f2937;
            }
            
            .search-result-section {
                font-size: 11px;
                color: #6b7280;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .search-no-results {
                padding: 20px;
                text-align: center;
                color: #6b7280;
                font-size: 13px;
            }
            
            @media (max-width: 768px) {
                .top-header {
                    height: 60px;
                    padding: 0 16px;
                }
                .user-info-header {
                    display: none;
                }
                .header-divider {
                    display: none;
                }
                .header-logo {
                    height: 32px;
                }
                .btn-logout span {
                    display: none;
                }
                .header-search-container {
                    display: none;
                }
                .btn-back span {
                    display: none;
                }
                .main-content {
                    margin-left: 0 !important;
                    padding: 10px !important;
                }
            }
            
            @media (min-width: 769px) and (max-width: 1024px) {
                .header-search-container {
                    flex: 0 1 220px;
                }
            }
        </style>
    `,

    init: function() {
        if (!document.getElementById('staffHeaderStyles')) {
            document.head.insertAdjacentHTML('beforeend', this.headerStyles);
        }
        this.updateUserInfo();
        this.initSearch();
    },

    updateUserInfo: function() {
        const userData = JSON.parse(localStorage.getItem('staff_user') || '{}');
        const name = userData.full_name || 'Staff Member';
        const role = userData.role_name || 'Employee';
        const empId = userData.emp_code || userData.employee_code || '-';
        const staffType = userData.staff_type || 'MYNT_REAL';
        
        const isMnStaff = staffType === 'MN_STAFF' || userData.is_mn_staff;
        const isMnEmployee = staffType === 'MN_EMPLOYEE' || userData.is_mn_employee;
        const isFreelancer = staffType === 'FREELANCER' || userData.is_freelancer;
        
        const initials = name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
        
        const initialsEl = document.getElementById('headerUserInitials');
        const nameEl = document.getElementById('headerUserName');
        const empIdEl = document.getElementById('headerUserEmpId');
        const roleEl = document.getElementById('headerUserRole');
        
        if (initialsEl) initialsEl.textContent = initials;
        if (nameEl) nameEl.textContent = name;
        if (empIdEl) empIdEl.textContent = empId;
        
        if (roleEl) {
            roleEl.textContent = role;
            
            if (isFreelancer) {
                roleEl.className = 'user-info-role role-badge-freelancer';
            } else if (isMnEmployee) {
                roleEl.className = 'user-info-role role-badge-mn-employee';
            } else if (isMnStaff) {
                roleEl.className = 'user-info-role role-badge-mn-staff';
            } else if (['VGK Mentor', 'VGK4U Supreme', 'VGK4U'].includes(role)) {
                roleEl.className = 'user-info-role role-badge-supreme';
            } else if (['HR', 'HR Manager'].includes(role)) {
                roleEl.className = 'user-info-role role-badge-hr';
            } else if (['Key Leadership', 'Leadership Role', 'Manager', 'Team Leader', 'Executive Admin'].includes(role)) {
                roleEl.className = 'user-info-role role-badge-leadership';
            } else {
                roleEl.className = 'user-info-role role-badge-default';
            }
        }
        
        this.showStaffTypeBanner(staffType, empId);
    },
    
    showStaffTypeBanner: function(staffType, empId) {
        const existingBanner = document.getElementById('staffTypeBanner');
        if (existingBanner) {
            existingBanner.remove();
        }
        
        const bannerConfig = {
            'MN_STAFF': {
                icon: 'fas fa-user-tie',
                badge: 'MN STAFF',
                message: 'Welcome to the Mynt Real team!',
                badgeClass: 'mn-staff-badge',
                bannerClass: 'mn_staff-banner'
            },
            'MN_EMPLOYEE': {
                icon: 'fas fa-user-check',
                badge: 'MN EMPLOYEE',
                message: 'Welcome to the Mynt Real family!',
                badgeClass: 'mn-employee-badge',
                bannerClass: 'mn-employee-banner'
            },
            'FREELANCER': {
                icon: 'fas fa-user-cog',
                badge: 'FREELANCER',
                message: 'Welcome, valued partner!',
                badgeClass: 'freelancer-badge',
                bannerClass: 'freelancer-banner'
            }
        };
        
        if (!bannerConfig[staffType]) return;
        
        const config = bannerConfig[staffType];
        const bannerHtml = `
            <div id="staffTypeBanner" class="staff-type-banner ${config.bannerClass}">
                <i class="${config.icon}"></i>
                <span>You are logged in as</span>
                <span class="${config.badgeClass}">${config.badge}</span>
                <span>(${empId})</span>
                <span>- ${config.message}</span>
            </div>
        `;
        
        const header = document.querySelector('.top-header');
        if (header) {
            header.insertAdjacentHTML('afterend', bannerHtml);
        }
    },

    renderHeader: function(pageTitle, pageIcon = 'fas fa-file', options = {}) {
        const showBack = options.showBack !== false;
        const backUrl = options.backUrl || 'javascript:history.back()';
        const showSearch = options.showSearch !== false;
        
        return `
            <header class="top-header" id="topHeader">
                <div class="header-left">
                    <img src="/assets/logos/myntreal_logo_new.png" alt="MyntReal" class="header-logo" onerror="this.style.display='none'">
                    <div class="header-divider"></div>
                    ${showBack ? `
                    <a href="${backUrl}" class="btn-back" id="headerBackBtn">
                        <i class="fas fa-arrow-left"></i>
                        <span>Back</span>
                    </a>
                    ` : ''}
                    <h1 class="page-title">
                        <i class="${pageIcon}"></i>
                        <span id="headerPageTitle">${pageTitle}</span>
                    </h1>
                </div>
                
                ${showSearch ? `
                <div class="header-search-container" id="headerSearchContainer">
                    <i class="fas fa-search header-search-icon"></i>
                    <input type="text" class="header-search-input" id="headerSearchInput" 
                           placeholder="Search menus..." autocomplete="off">
                    <div class="header-search-results" id="headerSearchResults"></div>
                </div>
                ` : ''}
                
                <div class="header-right">
                    <div class="user-info-header" id="headerUserInfo">
                        <div class="user-avatar-sm" id="headerUserInitials">--</div>
                        <div class="user-info-details">
                            <span class="user-info-name" id="headerUserName">Loading...</span>
                            <div class="user-info-meta">
                                <span class="user-info-role role-badge-default" id="headerUserRole">-</span>
                                <span id="headerUserEmpId">-</span>
                            </div>
                        </div>
                    </div>
                    <button class="btn-logout" onclick="StaffSidebar.logout()" title="Logout">
                        <i class="fas fa-sign-out-alt"></i>
                        <span>Logout</span>
                    </button>
                </div>
            </header>
        `;
    },
    
    inject: function(pageTitle, pageIcon = 'fas fa-file', options = {}) {
        const headerHtml = this.renderHeader(pageTitle, pageIcon, options);
        
        const existingHeader = document.querySelector('.top-header');
        if (existingHeader) {
            existingHeader.outerHTML = headerHtml;
        } else {
            const mainContent = document.querySelector('.main-content');
            if (mainContent) {
                mainContent.insertAdjacentHTML('afterbegin', headerHtml);
            } else {
                const sidebar = document.getElementById('staffSidebar');
                if (sidebar) {
                    sidebar.insertAdjacentHTML('afterend', headerHtml);
                }
            }
        }
        
        this.init();
    },
    
    initSearch: function() {
        const searchInput = document.getElementById('headerSearchInput');
        const searchResults = document.getElementById('headerSearchResults');
        
        if (!searchInput || !searchResults) return;
        
        let menuItems = [];
        let selectedIndex = -1;
        
        const collectMenuItems = () => {
            menuItems = [];
            if (typeof StaffSidebar !== 'undefined' && StaffSidebar.menuConfig) {
                const sections = StaffSidebar.menuConfig.sections || [];
                sections.forEach(section => {
                    const sectionTitle = section.title || section.id || 'Other';
                    (section.items || []).forEach(item => {
                        if (item.href && item.label) {
                            menuItems.push({
                                label: item.label,
                                href: item.href,
                                icon: item.icon || 'fas fa-file',
                                section: sectionTitle
                            });
                        }
                    });
                    (section.subSections || []).forEach(sub => {
                        (sub.items || []).forEach(item => {
                            if (item.href && item.label) {
                                menuItems.push({
                                    label: item.label,
                                    href: item.href,
                                    icon: item.icon || 'fas fa-file',
                                    section: sub.title || sectionTitle
                                });
                            }
                        });
                    });
                });
            }
        };
        
        let debounceTimer;
        const performSearch = (query) => {
            if (!query || query.length < 2) {
                searchResults.classList.remove('show');
                return;
            }
            
            if (menuItems.length === 0) collectMenuItems();
            
            const q = query.toLowerCase();
            const matches = menuItems.filter(item => 
                item.label.toLowerCase().includes(q) || 
                item.section.toLowerCase().includes(q)
            ).slice(0, 10);
            
            if (matches.length === 0) {
                searchResults.innerHTML = '<div class="search-no-results"><i class="fas fa-search me-2"></i>No menus found</div>';
            } else {
                searchResults.innerHTML = matches.map((item, idx) => `
                    <div class="search-result-item ${idx === selectedIndex ? 'active' : ''}" 
                         data-href="${item.href}" data-index="${idx}">
                        <div class="search-result-icon"><i class="${item.icon}"></i></div>
                        <div class="search-result-info">
                            <div class="search-result-name">${item.label}</div>
                            <div class="search-result-section">${item.section}</div>
                        </div>
                    </div>
                `).join('');
            }
            
            searchResults.classList.add('show');
            selectedIndex = -1;
        };
        
        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => performSearch(e.target.value), 150);
        });
        
        searchInput.addEventListener('focus', () => {
            if (searchInput.value.length >= 2) {
                performSearch(searchInput.value);
            }
        });
        
        searchInput.addEventListener('keydown', (e) => {
            const items = searchResults.querySelectorAll('.search-result-item');
            
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
                items.forEach((el, i) => el.classList.toggle('active', i === selectedIndex));
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, 0);
                items.forEach((el, i) => el.classList.toggle('active', i === selectedIndex));
            } else if (e.key === 'Enter' && selectedIndex >= 0) {
                e.preventDefault();
                const href = items[selectedIndex]?.dataset.href;
                if (href) window.location.href = href;
            } else if (e.key === 'Escape') {
                searchResults.classList.remove('show');
                searchInput.blur();
            }
        });
        
        searchResults.addEventListener('click', (e) => {
            const item = e.target.closest('.search-result-item');
            if (item && item.dataset.href) {
                window.location.href = item.dataset.href;
            }
        });
        
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.header-search-container')) {
                searchResults.classList.remove('show');
            }
        });
        
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                searchInput.focus();
                searchInput.select();
            }
        });
    }
};

if (!document.getElementById('staffHeaderStyles')) {
    document.head.insertAdjacentHTML('beforeend', StaffHeader.headerStyles);
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = StaffHeader;
}
