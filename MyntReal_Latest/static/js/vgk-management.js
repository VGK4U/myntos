/**
 * VGK Management System JavaScript
 * Handles role management and menu configuration functionality
 */

// Global variables
let selectedModule = null;
let currentInterface = 'user';
let draggedItem = null;

// Initialize the VGK system when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the first tab if on menu configuration page
    if (document.getElementById('user-interface-tab')) {
        selectInterfaceTab('user');
        
        // Setup tab click event handlers for proper tab switching
        setupTabEventHandlers();
    }
    
    // Initialize role management features
    if (document.getElementById('roles-table')) {
        initializeTableSorting();
    }
    
    // Setup drag and drop for menu items
    setupDragAndDrop();
    
    // Setup visibility toggle handlers
    setupVisibilityToggles();
});

/**
 * Setup event handlers for tab switching
 */
function setupTabEventHandlers() {
    // Add click handlers for interface tabs
    const tabButtons = ['user-interface-tab', 'admin-interface-tab', 'super-admin-interface-tab'];
    
    tabButtons.forEach(tabId => {
        const tabButton = document.getElementById(tabId);
        if (tabButton) {
            tabButton.addEventListener('click', function() {
                const interfaceType = tabId.replace('-interface-tab', '');
                selectInterfaceTab(interfaceType);
            });
        }
    });
}

// ===== ENHANCED UX FUNCTIONS =====

/**
 * Filter modules based on search input
 * @param {string} interfaceType - Type of interface (user, admin, super-admin)
 */
function filterModules(interfaceType) {
    const searchInput = document.getElementById(`${interfaceType}-module-search`);
    const modulesList = document.getElementById(`${interfaceType}-modules-list`);
    const emptyState = document.getElementById(`${interfaceType}-modules-empty`);
    
    if (!searchInput || !modulesList) return;
    
    const searchTerm = searchInput.value.toLowerCase().trim();
    const moduleItems = modulesList.querySelectorAll('.module-item');
    let visibleCount = 0;
    
    moduleItems.forEach(item => {
        const moduleName = item.querySelector('.module-name')?.textContent.toLowerCase() || '';
        const moduleDesc = item.querySelector('.module-description')?.textContent.toLowerCase() || '';
        
        if (searchTerm === '' || moduleName.includes(searchTerm) || moduleDesc.includes(searchTerm)) {
            item.style.display = '';
            visibleCount++;
        } else {
            item.style.display = 'none';
        }
    });
    
    // Show/hide empty state
    if (emptyState) {
        if (visibleCount === 0 && searchTerm !== '') {
            emptyState.classList.remove('d-none');
            modulesList.classList.add('d-none');
        } else {
            emptyState.classList.add('d-none');
            modulesList.classList.remove('d-none');
        }
    }
}

/**
 * Clear module search filter
 * @param {string} interfaceType - Type of interface (user, admin, super-admin)
 */
function clearModuleSearch(interfaceType) {
    const searchInput = document.getElementById(`${interfaceType}-module-search`);
    const modulesList = document.getElementById(`${interfaceType}-modules-list`);
    const emptyState = document.getElementById(`${interfaceType}-modules-empty`);
    
    if (searchInput) {
        searchInput.value = '';
    }
    
    if (modulesList) {
        const moduleItems = modulesList.querySelectorAll('.module-item');
        moduleItems.forEach(item => {
            item.style.display = '';
        });
        modulesList.classList.remove('d-none');
    }
    
    if (emptyState) {
        emptyState.classList.add('d-none');
    }
}

/**
 * Show loading state for modules
 * @param {string} interfaceType - Type of interface (user, admin, super-admin)
 */
function showModulesLoading(interfaceType) {
    const loader = document.getElementById(`${interfaceType}-modules-loader`);
    const skeleton = document.querySelector(`#${interfaceType}-modules-list .loading-skeleton`);
    
    if (loader) loader.classList.remove('d-none');
    if (skeleton) skeleton.classList.remove('d-none');
}

/**
 * Hide loading state for modules
 * @param {string} interfaceType - Type of interface (user, admin, super-admin)
 */
function hideModulesLoading(interfaceType) {
    const loader = document.getElementById(`${interfaceType}-modules-loader`);
    const skeleton = document.querySelector(`#${interfaceType}-modules-list .loading-skeleton`);
    
    if (loader) loader.classList.add('d-none');
    if (skeleton) skeleton.classList.add('d-none');
}

/**
 * Show save indicator with animation
 * @param {string} interfaceType - Type of interface (user, admin, super-admin)
 * @param {string} message - Optional custom message
 */
function showSaveIndicator(interfaceType, message = 'Saved') {
    const indicator = document.getElementById(`${interfaceType}-save-indicator`);
    
    if (indicator) {
        const badge = indicator.querySelector('.badge');
        if (badge) {
            badge.innerHTML = `<i class="bi bi-check-circle"></i> ${message}`;
        }
        
        indicator.classList.remove('d-none');
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            indicator.classList.add('d-none');
        }, 3000);
    }
}

/**
 * Enhanced module selection with better visual feedback
 * @param {string} interfaceType - Type of interface 
 * @param {string} moduleKey - Module identifier
 * @param {HTMLElement} element - Clicked module element
 */
function selectModuleEnhanced(interfaceType, moduleKey, element) {
    // Remove selection from all modules
    const modulesList = document.getElementById(`${interfaceType}-modules-list`);
    if (modulesList) {
        modulesList.querySelectorAll('.module-item').forEach(item => {
            item.classList.remove('selected');
        });
    }
    
    // Add selection to clicked module
    if (element) {
        element.classList.add('selected');
    }
    
    // Update global state
    selectedModule = moduleKey;
    currentInterface = interfaceType;
    
    // Load module details
    loadModuleDetails(interfaceType, moduleKey);
}

/**
 * Enhanced module visibility toggle with save feedback
 * @param {string} moduleKey - Module identifier
 * @param {string} interfaceType - Type of interface
 * @param {boolean} isVisible - New visibility state
 */
function toggleModuleVisibilityEnhanced(moduleKey, interfaceType, isVisible) {
    const payload = {
        module_key: moduleKey,
        interface_type: interfaceType,
        is_visible: isVisible
    };
    
    fetch('/api/vgk/toggle-module-visibility', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show save indicator
            showSaveIndicator(interfaceType, isVisible ? 'Module Activated' : 'Module Deactivated');
            
            // Update the visual state in the module list
            const moduleElement = document.querySelector(`[data-module-key="${moduleKey}"]`);
            if (moduleElement) {
                const badge = moduleElement.querySelector('.badge');
                if (badge) {
                    badge.className = isVisible ? 'badge bg-success ms-2' : 'badge bg-secondary ms-2';
                    badge.textContent = isVisible ? 'Active' : 'Inactive';
                }
            }
        } else {
            showNotification('error', `Failed to update module visibility: ${data.error}`);
            // Revert toggle state
            const toggle = document.querySelector(`[data-module-key="${moduleKey}"] input[type="checkbox"]`);
            if (toggle) {
                toggle.checked = !isVisible;
            }
        }
    })
    .catch(error => {
        console.error('Error toggling module visibility:', error);
        showNotification('error', 'Network error while updating module visibility');
        // Revert toggle state
        const toggle = document.querySelector(`[data-module-key="${moduleKey}"] input[type="checkbox"]`);
        if (toggle) {
            toggle.checked = !isVisible;
        }
    });
}

// ===== ROLE MANAGEMENT FUNCTIONS =====

/**
 * Filter roles table based on search and filter inputs
 */
function filterRolesTable() {
    const searchInput = document.getElementById('roles-search');
    const statusFilter = document.getElementById('status-filter');
    const baseRoleFilter = document.getElementById('base-role-filter');
    const table = document.getElementById('roles-table');
    
    if (!table) return;
    
    const searchTerm = searchInput ? searchInput.value.toLowerCase().trim() : '';
    const statusValue = statusFilter ? statusFilter.value : '';
    const baseRoleValue = baseRoleFilter ? baseRoleFilter.value : '';
    
    const rows = table.querySelectorAll('tbody tr');
    let visibleCount = 0;
    
    rows.forEach(row => {
        const roleName = row.cells[0]?.textContent.toLowerCase() || '';
        const baseRole = row.cells[1]?.textContent.toLowerCase() || '';
        const permissions = row.cells[3]?.textContent.toLowerCase() || '';
        const users = row.cells[4]?.textContent.toLowerCase() || '';
        const status = row.cells[6]?.textContent.toLowerCase().trim() || '';
        
        // Search filter
        const matchesSearch = searchTerm === '' || 
            roleName.includes(searchTerm) || 
            permissions.includes(searchTerm) || 
            users.includes(searchTerm);
        
        // Status filter
        const matchesStatus = statusValue === '' || status === statusValue;
        
        // Base role filter (normalize values)
        const normalizedBaseRole = baseRole.replace(/\s+/g, '_').toLowerCase();
        const matchesBaseRole = baseRoleValue === '' || normalizedBaseRole.includes(baseRoleValue.toLowerCase());
        
        if (matchesSearch && matchesStatus && matchesBaseRole) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
    
    // Show empty state if no results
    showRolesEmptyState(visibleCount === 0 && searchTerm !== '');
}

/**
 * Clear roles search and filters
 */
function clearRolesSearch() {
    const searchInput = document.getElementById('roles-search');
    const statusFilter = document.getElementById('status-filter');
    const baseRoleFilter = document.getElementById('base-role-filter');
    
    if (searchInput) searchInput.value = '';
    if (statusFilter) statusFilter.value = '';
    if (baseRoleFilter) baseRoleFilter.value = '';
    
    filterRolesTable();
}

/**
 * Refresh roles table
 */
function refreshRolesTable() {
    const loader = document.getElementById('roles-table-loader');
    if (loader) loader.classList.remove('d-none');
    
    setTimeout(() => {
        location.reload();
    }, 500);
}

/**
 * Show/hide empty state for roles table
 */
function showRolesEmptyState(show) {
    let emptyState = document.querySelector('.roles-table-empty');
    const tableBody = document.querySelector('#roles-table tbody');
    
    if (!emptyState && show && tableBody) {
        emptyState = document.createElement('div');
        emptyState.className = 'roles-table-empty';
        emptyState.innerHTML = `
            <i class="bi bi-search fs-3 d-block mb-2"></i>
            <p class="mb-0">No roles found matching your criteria</p>
        `;
        tableBody.parentNode.appendChild(emptyState);
    }
    
    if (emptyState) {
        emptyState.style.display = show ? 'block' : 'none';
    }
}

/**
 * Initialize table sorting
 */
function initializeTableSorting() {
    const sortableHeaders = document.querySelectorAll('.sortable-table th.sortable');
    
    sortableHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const sortKey = this.dataset.sort;
            const table = this.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            // Determine sort direction
            const isAsc = this.classList.contains('sorted-asc');
            const isDesc = this.classList.contains('sorted-desc');
            let sortDirection = 'asc';
            
            if (isAsc) sortDirection = 'desc';
            else if (isDesc) sortDirection = 'asc';
            
            // Clear all sort classes
            sortableHeaders.forEach(h => {
                h.classList.remove('sorted-asc', 'sorted-desc');
            });
            
            // Add sort class to current header
            this.classList.add(sortDirection === 'asc' ? 'sorted-asc' : 'sorted-desc');
            
            // Sort rows
            rows.sort((a, b) => {
                const aValue = getSortValue(a, sortKey);
                const bValue = getSortValue(b, sortKey);
                
                if (sortDirection === 'asc') {
                    return aValue > bValue ? 1 : -1;
                } else {
                    return aValue < bValue ? 1 : -1;
                }
            });
            
            // Reorder rows in DOM
            rows.forEach(row => tbody.appendChild(row));
        });
    });
}

/**
 * Get sort value from table row
 */
function getSortValue(row, sortKey) {
    const cellIndex = {
        'role_name': 0,
        'base_role': 1,
        'role_level': 2,
        'permission_count': 3,
        'active_users': 4,
        'created_at': 5,
        'is_active': 6
    };
    
    const cell = row.cells[cellIndex[sortKey]];
    if (!cell) return '';
    
    const text = cell.textContent.trim();
    
    // Handle numeric values
    if (sortKey === 'permission_count' || sortKey === 'active_users' || sortKey === 'role_level') {
        const match = text.match(/\d+/);
        return match ? parseInt(match[0]) : 0;
    }
    
    // Handle dates
    if (sortKey === 'created_at') {
        return new Date(text);
    }
    
    return text.toLowerCase();
}

// Table sorting is initialized in main DOMContentLoaded handler above

// ===== MENU CONFIGURATION FUNCTIONS =====

/**
 * Initialize the menu system with default modules and items
 */
function initializeMenus() {
    if (confirm('This will initialize the menu system with default modules and items. Continue?')) {
        showLoading('Initializing menu system...');
        
        fetch('/api/vgk/initialize-menus', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            
            if (data.success) {
                showNotification('success', `Menu system initialized successfully! ${data.modules} modules, ${data.permissions} permissions, ${data.items} items created.`);
                // Refresh the current interface
                loadModulesForInterface(currentInterface);
            } else {
                showNotification('error', `Initialization failed: ${data.error}`);
            }
        })
        .catch(error => {
            hideLoading();
            showNotification('error', `Error initializing menus: ${error.message}`);
        });
    }
}

/**
 * Export menu configuration as JSON
 */
function exportConfiguration() {
    window.open('/api/vgk/export-menu-config', '_blank');
}

/**
 * Switch between interface tabs
 */
function selectInterfaceTab(interfaceType) {
    currentInterface = interfaceType;
    
    // Update active tab (scoped to interface tabs only)
    document.querySelectorAll('#interfaceTabs .nav-link').forEach(tab => {
        tab.classList.remove('active');
    });
    document.getElementById(`${interfaceType}-interface-tab`).classList.add('active');
    
    // Update active tab pane (scoped to interface tab content only)
    document.querySelectorAll('#interfaceTabContent .tab-pane').forEach(pane => {
        pane.classList.remove('show', 'active');
    });
    document.getElementById(`${interfaceType}-interface`).classList.add('show', 'active');
    
    // Load modules for this interface
    loadModulesForInterface(interfaceType);
    
    // Clear module details
    clearModuleDetails(interfaceType);
}

/**
 * Load modules for a specific interface
 */
function loadModulesForInterface(interfaceType) {
    const modulesList = document.getElementById(`${interfaceType}-modules-list`);
    
    if (!modulesList) return;
    
    // Show enhanced loading state
    showModulesLoading(interfaceType);
    
    // Clear search when loading new interface
    clearModuleSearch(interfaceType);
    
    fetch(`/api/vgk/modules/${interfaceType}`)
        .then(response => response.json())
        .then(data => {
            if (data.modules) {
                displayModules(data.modules, interfaceType);
            } else {
                modulesList.innerHTML = '<div class="text-center p-3 text-muted">No modules available for this interface</div>';
            }
        })
        .catch(error => {
            modulesList.innerHTML = '<div class="text-center p-3 text-danger"><i class="bi bi-exclamation-triangle"></i> Error loading modules</div>';
            console.error('Error loading modules:', error);
        })
        .finally(() => {
            // Always hide loading state regardless of success or failure
            hideModulesLoading(interfaceType);
        });
}

/**
 * Display modules in the sidebar
 */
function displayModules(modules, interfaceType) {
    const modulesList = document.getElementById(`${interfaceType}-modules-list`);
    
    // Preserve skeleton by generating content with skeleton intact
    const modulesHTML = modules.map(module => `
        <div class="module-item d-flex justify-content-between align-items-center" 
             data-module-id="${module.id}" 
             data-module-key="${module.module_key || module.id}"
             onclick="selectModuleEnhanced('${interfaceType}', '${module.module_key || module.id}', this)">
            <div class="flex-grow-1">
                <div class="module-name fw-semibold">${module.module_name}</div>
                <div class="module-description text-muted small">${module.description || 'Module functionality'}</div>
                <div class="module-stats small text-secondary mt-1">
                    <i class="bi bi-list-ul"></i> ${module.items_count || 0} items
                    ${module.is_visible ? '<span class="badge bg-success ms-2">Active</span>' : '<span class="badge bg-secondary ms-2">Inactive</span>'}
                </div>
            </div>
            <div class="d-flex align-items-center">
                <div class="form-check form-switch me-2">
                    <input class="form-check-input" type="checkbox" 
                           ${module.is_visible ? 'checked' : ''} 
                           onclick="event.stopPropagation()"
                           onchange="toggleModuleVisibilityEnhanced('${module.module_key || module.id}', '${interfaceType}', this.checked)">
                </div>
                <i class="bi bi-chevron-right text-muted"></i>
            </div>
        </div>
    `).join('');
    
    // Update innerHTML while preserving skeleton structure
    modulesList.innerHTML = `
        <div class="loading-skeleton d-none">
            <div class="skeleton-item"></div>
            <div class="skeleton-item"></div>
            <div class="skeleton-item"></div>
        </div>
        ${modulesHTML}
    `;
}

/**
 * Select a module and load its items
 */
function selectModule(moduleId, interfaceType) {
    selectedModule = moduleId;
    
    // Update visual selection
    document.querySelectorAll(`#${interfaceType}-modules-list .module-item`).forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-module-id="${moduleId}"]`).classList.add('active');
    
    // Load module items
    loadModuleItems(moduleId, interfaceType);
}

/**
 * Load items for a specific module
 */
function loadModuleItems(moduleId, interfaceType) {
    const detailsContainer = document.getElementById(`${interfaceType}-module-details`);
    
    detailsContainer.innerHTML = '<div class="text-center p-3"><i class="bi bi-arrow-repeat spin"></i> Loading items...</div>';
    
    fetch(`/api/vgk/module/${moduleId}/items?interface=${interfaceType}`)
        .then(response => response.json())
        .then(data => {
            if (data.items) {
                displayModuleItems(data, interfaceType);
            } else {
                detailsContainer.innerHTML = '<div class="text-center p-3 text-danger">Error loading items</div>';
            }
        })
        .catch(error => {
            detailsContainer.innerHTML = '<div class="text-center p-3 text-danger">Error loading items</div>';
            console.error('Error loading module items:', error);
        });
}

/**
 * Display module items with drag-and-drop support
 */
function displayModuleItems(data, interfaceType) {
    const detailsContainer = document.getElementById(`${interfaceType}-module-details`);
    
    const itemsHTML = data.items.map(item => `
        <div class="menu-item list-group-item" data-item-id="${item.id}" draggable="true">
            <div class="d-flex justify-content-between align-items-center">
                <div class="d-flex align-items-center">
                    <i class="bi bi-grip-vertical me-2 text-muted drag-handle"></i>
                    <i class="bi ${item.item_icon} me-2"></i>
                    <div>
                        <strong>${item.item_name}</strong>
                        <br>
                        <small class="text-muted">${item.route_endpoint}</small>
                    </div>
                </div>
                <div class="d-flex align-items-center">
                    <div class="form-check form-switch me-2">
                        <input class="form-check-input" type="checkbox" 
                               ${item.is_visible ? 'checked' : ''} 
                               onchange="toggleItemVisibility(${item.id}, '${interfaceType}', this.checked)">
                    </div>
                    <div class="btn-group btn-group-sm">
                        <button type="button" class="btn btn-outline-secondary" onclick="editMenuItem(${item.id})">
                            <i class="bi bi-pencil"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
    
    detailsContainer.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h6>${data.module.module_name}</h6>
            <button type="button" class="btn btn-sm btn-outline-primary" onclick="addMenuItem(${selectedModule})">
                <i class="bi bi-plus"></i> Add Item
            </button>
        </div>
        <div class="list-group sortable-list" id="menu-items-list">
            ${itemsHTML}
        </div>
    `;
    
    // Re-setup drag and drop for new items
    setupDragAndDrop();
}

/**
 * Toggle module visibility
 */
function toggleModuleVisibility(moduleId, interfaceType, visible) {
    fetch(`/api/vgk/module/${moduleId}/visibility`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
            interface: interfaceType,
            visible: visible
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('success', `Module visibility updated for ${interfaceType} interface`);
        } else {
            showNotification('error', `Error updating visibility: ${data.error}`);
            // Revert the toggle
            event.target.checked = !visible;
        }
    })
    .catch(error => {
        showNotification('error', `Error updating visibility: ${error.message}`);
        event.target.checked = !visible;
    });
}

/**
 * Toggle menu item visibility
 */
function toggleItemVisibility(itemId, interfaceType, visible) {
    fetch(`/api/vgk/item/${itemId}/visibility`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
            interface: interfaceType,
            visible: visible
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('success', `Item visibility updated for ${interfaceType} interface`);
        } else {
            showNotification('error', `Error updating visibility: ${data.error}`);
            event.target.checked = !visible;
        }
    })
    .catch(error => {
        showNotification('error', `Error updating visibility: ${error.message}`);
        event.target.checked = !visible;
    });
}

/**
 * Clear module details display
 */
function clearModuleDetails(interfaceType) {
    const detailsContainer = document.getElementById(`${interfaceType}-module-details`);
    if (detailsContainer) {
        detailsContainer.innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="bi bi-cursor fs-1 d-block mb-2"></i>
                Select a module from the left to configure its menu items
            </div>
        `;
    }
}

/**
 * Add new menu item
 */
function addMenuItem(moduleId) {
    // This would open a modal or form to add a new menu item
    showNotification('info', 'Add menu item functionality will be implemented in the next phase');
}

/**
 * Edit menu item
 */
function editMenuItem(itemId) {
    // This would open a modal or form to edit the menu item
    showNotification('info', 'Edit menu item functionality will be implemented in the next phase');
}

// ===== ROLE MANAGEMENT FUNCTIONS =====

/**
 * Edit a custom role
 */
function editRole(roleId) {
    showNotification('info', 'Edit role functionality will be implemented in the next phase');
}

/**
 * View role permissions
 */
function viewPermissions(roleId) {
    showNotification('info', 'View permissions functionality will be implemented in the next phase');
}

/**
 * Manage users assigned to a role
 */
function manageUsers(roleId) {
    showNotification('info', 'Manage users functionality will be implemented in the next phase');
}

/**
 * Deactivate a role
 */
function deactivateRole(roleId) {
    if (confirm('Are you sure you want to deactivate this role? Users with this role will lose associated permissions.')) {
        showNotification('info', 'Deactivate role functionality will be implemented in the next phase');
    }
}

/**
 * Activate a role
 */
function activateRole(roleId) {
    showNotification('info', 'Activate role functionality will be implemented in the next phase');
}

// ===== DRAG AND DROP FUNCTIONALITY =====

/**
 * Setup drag and drop for menu items
 */
function setupDragAndDrop() {
    const sortableList = document.getElementById('menu-items-list');
    if (!sortableList) return;
    
    const items = sortableList.querySelectorAll('.menu-item');
    
    items.forEach(item => {
        item.addEventListener('dragstart', handleDragStart);
        item.addEventListener('dragover', handleDragOver);
        item.addEventListener('drop', handleDrop);
        item.addEventListener('dragend', handleDragEnd);
    });
}

/**
 * Handle drag start
 */
function handleDragStart(e) {
    draggedItem = this;
    this.style.opacity = '0.5';
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', this.outerHTML);
}

/**
 * Handle drag over
 */
function handleDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault();
    }
    e.dataTransfer.dropEffect = 'move';
    return false;
}

/**
 * Handle drop
 */
function handleDrop(e) {
    if (e.stopPropagation) {
        e.stopPropagation();
    }
    
    if (draggedItem !== this) {
        // Get the parent list
        const list = this.parentNode;
        const draggedIndex = Array.from(list.children).indexOf(draggedItem);
        const targetIndex = Array.from(list.children).indexOf(this);
        
        // Reorder items
        if (draggedIndex < targetIndex) {
            list.insertBefore(draggedItem, this.nextSibling);
        } else {
            list.insertBefore(draggedItem, this);
        }
        
        // Update order on server
        updateItemOrder();
    }
    
    return false;
}

/**
 * Handle drag end
 */
function handleDragEnd(e) {
    this.style.opacity = '1';
    draggedItem = null;
}

/**
 * Update item order on server
 */
function updateItemOrder() {
    const items = document.querySelectorAll('#menu-items-list .menu-item');
    const itemsData = Array.from(items).map((item, index) => ({
        id: item.getAttribute('data-item-id'),
        order: index + 1
    }));
    
    fetch(`/api/vgk/module/${selectedModule}/reorder`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
            interface: currentInterface,
            items: itemsData
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('success', 'Menu items reordered successfully');
        } else {
            showNotification('error', `Error reordering items: ${data.error}`);
        }
    })
    .catch(error => {
        showNotification('error', `Error reordering items: ${error.message}`);
    });
}

// ===== UTILITY FUNCTIONS =====

/**
 * Setup visibility toggle handlers
 */
function setupVisibilityToggles() {
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('visibility-toggle')) {
            const moduleId = e.target.getAttribute('data-module-id');
            const interfaceType = e.target.getAttribute('data-interface');
            const visible = e.target.checked;
            
            toggleModuleVisibility(moduleId, interfaceType, visible);
        }
    });
}

/**
 * Get CSRF token from meta tag
 */
function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}

/**
 * Show loading indicator
 */
function showLoading(message = 'Loading...') {
    // Create loading overlay if it doesn't exist
    let overlay = document.getElementById('loading-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center';
        overlay.style.backgroundColor = 'rgba(0,0,0,0.5)';
        overlay.style.zIndex = '9999';
        document.body.appendChild(overlay);
    }
    
    overlay.innerHTML = `
        <div class="bg-white p-4 rounded shadow text-center">
            <div class="spinner-border text-primary mb-2" role="status"></div>
            <div>${message}</div>
        </div>
    `;
    overlay.style.display = 'flex';
}

/**
 * Hide loading indicator
 */
function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

/**
 * Show notification
 */
function showNotification(type, message) {
    // Create notification container if it doesn't exist
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        container.className = 'position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    // Create notification
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

// Add CSS for spinning icon
const style = document.createElement('style');
style.textContent = `
.spin {
    animation: spin 1s linear infinite;
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.drag-handle {
    cursor: grab;
}

.drag-handle:active {
    cursor: grabbing;
}

.menu-item[draggable="true"]:hover {
    background-color: var(--bs-light);
}

.menu-item.dragging {
    opacity: 0.5;
}
`;
document.head.appendChild(style);