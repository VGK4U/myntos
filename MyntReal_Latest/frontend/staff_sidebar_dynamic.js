/**
 * Mynt Real LLP Staff Portal - Dynamic Sidebar Module
 * DC Protocol Compliant: API-driven menu rendering with cascade selection
 * Created: Jan 12, 2026
 * 
 * FEATURE FLAG: USE_DYNAMIC_SIDEBAR
 * Set to true to enable API-driven sidebar, false for static fallback
 * 
 * CASCADE SELECTION LOGIC:
 * - Parent section grants cascade to all children
 * - Individual menu grants remain isolated (no sibling expansion)
 * - VGK Supreme (MR10001) has full access bypass
 */

const USE_DYNAMIC_SIDEBAR = true;  // Feature flag for safe rollback

const StaffSidebarDynamic = {
    sidebarTree: null,
    allowedPaths: null,
    employeeId: null,
    roleName: null,
    isLoading: false,
    hasError: false,
    errorMessage: null,

    init: async function(containerId = 'sidebar-menu') {
        console.log('[DC-SIDEBAR-DYNAMIC] Initializing dynamic sidebar');
        
        if (!USE_DYNAMIC_SIDEBAR) {
            console.log('[DC-SIDEBAR-DYNAMIC] Feature flag disabled, using static sidebar');
            return this.fallbackToStatic(containerId);
        }

        this.isLoading = true;
        
        try {
            const response = await this.fetchMyMenus();
            
            if (response && response.sidebar_tree) {
                this.sidebarTree = response.sidebar_tree;
                this.allowedPaths = new Set(response.allowed_paths || []);
                this.roleName = response.role_name || 'Unknown';
                
                console.log(`[DC-SIDEBAR-DYNAMIC] Loaded ${this.sidebarTree.length} sections for ${this.roleName}`);
                
                this.render(containerId);
            } else {
                throw new Error('Invalid response from /my-menus API');
            }
        } catch (error) {
            console.error('[DC-SIDEBAR-DYNAMIC] Error loading menus:', error);
            this.hasError = true;
            this.errorMessage = error.message;
            return this.fallbackToStatic(containerId);
        } finally {
            this.isLoading = false;
        }
    },

    fetchMyMenus: async function() {
        const token = localStorage.getItem('sessionToken') || localStorage.getItem('token');
        
        if (!token) {
            throw new Error('No authentication token found');
        }

        const response = await fetch('/api/v1/staff/my-menus', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status} ${response.statusText}`);
        }

        return await response.json();
    },

    fallbackToStatic: function(containerId) {
        console.log('[DC-SIDEBAR-DYNAMIC] Falling back to static sidebar');
        
        if (typeof StaffSidebar !== 'undefined' && StaffSidebar.init) {
            StaffSidebar.init(containerId);
        } else {
            console.error('[DC-SIDEBAR-DYNAMIC] Static sidebar not available');
        }
    },

    render: function(containerId) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`[DC-SIDEBAR-DYNAMIC] Container not found: ${containerId}`);
            return;
        }

        container.innerHTML = this.buildSidebarHTML();
        this.attachEventListeners();
        this.restoreState();
        console.log('[DC-SIDEBAR-DYNAMIC] Sidebar rendered successfully');
    },

    buildSidebarHTML: function() {
        if (!this.sidebarTree || this.sidebarTree.length === 0) {
            return `
                <div class="sidebar-no-access">
                    <i class="fas fa-lock"></i>
                    <p>No menu access granted</p>
                    <small>Contact your administrator</small>
                </div>
            `;
        }

        let html = '<ul class="sidebar-menu">';
        
        for (const section of this.sidebarTree) {
            html += this.buildSectionHTML(section);
        }
        
        html += '</ul>';
        return html;
    },

    buildSectionHTML: function(section) {
        const sectionId = section.id || section.section_id || 'section';
        const hasItems = section.items && section.items.length > 0;
        const hasSubSections = section.subSections && section.subSections.length > 0;
        
        if (!hasItems && !hasSubSections) {
            return '';
        }

        let html = `
            <li class="sidebar-group" data-section="${sectionId}">
                <div class="sidebar-group-toggle" data-section="${sectionId}">
                    <i class="${section.icon || 'fas fa-folder'}"></i>
                    <span>${section.title || section.name || 'Section'}</span>
                    <i class="fas fa-chevron-down toggle-icon"></i>
                </div>
                <ul class="sidebar-group-items">
        `;

        if (hasSubSections) {
            for (const subSection of section.subSections) {
                html += this.buildSubSectionHTML(subSection, sectionId);
            }
        }

        if (hasItems) {
            for (const item of section.items) {
                html += this.buildMenuItemHTML(item);
            }
        }

        html += '</ul></li>';
        return html;
    },

    buildSubSectionHTML: function(subSection, parentId) {
        const subId = `${parentId}-${subSection.id || 'sub'}`;
        const hasItems = subSection.items && subSection.items.length > 0;
        
        if (!hasItems) {
            return '';
        }

        let html = `
            <li class="sidebar-subsection" data-subsection="${subId}">
                <div class="sidebar-subsection-toggle" data-subsection="${subId}">
                    <i class="${subSection.icon || 'fas fa-folder-open'}"></i>
                    <span>${subSection.title || subSection.name || 'Subsection'}</span>
                    <i class="fas fa-chevron-down toggle-icon"></i>
                </div>
                <ul class="sidebar-subsection-items">
        `;

        for (const item of subSection.items) {
            html += this.buildMenuItemHTML(item);
        }

        html += '</ul></li>';
        return html;
    },

    buildMenuItemHTML: function(item) {
        const isActive = window.location.pathname === item.href;
        const activeClass = isActive ? 'active' : '';
        
        return `
            <li class="sidebar-item ${activeClass}">
                <a href="${item.href || '#'}" title="${item.label || item.name || 'Menu Item'}">
                    <i class="${item.icon || 'fas fa-circle'}"></i>
                    <span>${item.label || item.name || 'Menu Item'}</span>
                </a>
            </li>
        `;
    },

    attachEventListeners: function() {
        document.querySelectorAll('.sidebar-group-toggle').forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                const section = e.currentTarget.dataset.section;
                this.toggleSection(section);
            });
        });

        document.querySelectorAll('.sidebar-subsection-toggle').forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                e.stopPropagation();
                const subsection = e.currentTarget.dataset.subsection;
                this.toggleSubSection(subsection);
            });
        });
    },

    toggleSection: function(sectionId) {
        const group = document.querySelector(`.sidebar-group[data-section="${sectionId}"]`);
        if (group) {
            group.classList.toggle('collapsed');
            this.saveState();
        }
    },

    toggleSubSection: function(subsectionId) {
        const subsection = document.querySelector(`.sidebar-subsection[data-subsection="${subsectionId}"]`);
        if (subsection) {
            subsection.classList.toggle('collapsed');
            this.saveState();
        }
    },

    saveState: function() {
        const state = {};
        document.querySelectorAll('.sidebar-group.collapsed').forEach(el => {
            state[el.dataset.section] = 'collapsed';
        });
        document.querySelectorAll('.sidebar-subsection.collapsed').forEach(el => {
            state[el.dataset.subsection] = 'collapsed';
        });
        localStorage.setItem('staff_sidebar_dynamic_state', JSON.stringify(state));
    },

    restoreState: function() {
        try {
            const stateStr = localStorage.getItem('staff_sidebar_dynamic_state');
            if (!stateStr) return;
            
            const state = JSON.parse(stateStr);
            
            for (const [key, value] of Object.entries(state)) {
                if (value === 'collapsed') {
                    const section = document.querySelector(`.sidebar-group[data-section="${key}"]`);
                    const subsection = document.querySelector(`.sidebar-subsection[data-subsection="${key}"]`);
                    
                    if (section) section.classList.add('collapsed');
                    if (subsection) subsection.classList.add('collapsed');
                }
            }
        } catch (e) {
            console.warn('[DC-SIDEBAR-DYNAMIC] Failed to restore sidebar state:', e);
        }
    },

    isPathAllowed: function(path) {
        if (!this.allowedPaths) return false;
        return this.allowedPaths.has(path);
    },

    getCurrentSectionId: function() {
        const path = window.location.pathname;
        const activeItem = document.querySelector(`.sidebar-item.active`);
        if (activeItem) {
            const group = activeItem.closest('.sidebar-group');
            return group ? group.dataset.section : null;
        }
        return null;
    }
};

const DynamicSidebarStyles = `
<style>
.sidebar-no-access {
    padding: 2rem;
    text-align: center;
    color: var(--text-muted, #6c757d);
}
.sidebar-no-access i {
    font-size: 2rem;
    margin-bottom: 1rem;
}
.sidebar-menu {
    list-style: none;
    padding: 0;
    margin: 0;
}
.sidebar-group {
    margin-bottom: 0.25rem;
}
.sidebar-group-toggle,
.sidebar-subsection-toggle {
    display: flex;
    align-items: center;
    padding: 0.75rem 1rem;
    cursor: pointer;
    transition: background-color 0.2s;
    color: var(--text-primary, #fff);
    background: var(--sidebar-section-bg, #1a1a2e);
    border-left: 3px solid transparent;
}
.sidebar-group-toggle:hover,
.sidebar-subsection-toggle:hover {
    background: var(--sidebar-hover-bg, #16213e);
}
.sidebar-group-toggle i:first-child,
.sidebar-subsection-toggle i:first-child {
    margin-right: 0.75rem;
    width: 20px;
    text-align: center;
}
.sidebar-group-toggle span,
.sidebar-subsection-toggle span {
    flex: 1;
    font-weight: 500;
}
.toggle-icon {
    transition: transform 0.2s;
}
.collapsed .toggle-icon {
    transform: rotate(-90deg);
}
.sidebar-group-items,
.sidebar-subsection-items {
    list-style: none;
    padding: 0;
    margin: 0;
    overflow: hidden;
    transition: max-height 0.3s ease;
}
.collapsed .sidebar-group-items,
.collapsed .sidebar-subsection-items {
    display: none;
}
.sidebar-subsection {
    margin-left: 0.5rem;
}
.sidebar-subsection-toggle {
    padding-left: 1.5rem;
    background: var(--sidebar-subsection-bg, #0f0f1a);
}
.sidebar-item {
    list-style: none;
}
.sidebar-item a {
    display: flex;
    align-items: center;
    padding: 0.5rem 1rem 0.5rem 2rem;
    color: var(--text-secondary, #b0b0b0);
    text-decoration: none;
    transition: all 0.2s;
    border-left: 3px solid transparent;
}
.sidebar-item a:hover {
    background: var(--sidebar-item-hover, #1a1a2e);
    color: var(--text-primary, #fff);
    border-left-color: var(--accent-color, #0d6efd);
}
.sidebar-item.active a {
    background: var(--sidebar-item-active, #0d6efd1a);
    color: var(--accent-color, #0d6efd);
    border-left-color: var(--accent-color, #0d6efd);
}
.sidebar-item a i {
    margin-right: 0.75rem;
    width: 16px;
    text-align: center;
}
</style>
`;

document.head.insertAdjacentHTML('beforeend', DynamicSidebarStyles);

window.StaffSidebarDynamic = StaffSidebarDynamic;
window.USE_DYNAMIC_SIDEBAR = USE_DYNAMIC_SIDEBAR;
