/**
 * CRM Assignee Search Component
 * DC Protocol: Universal search for Tele Caller, Field Staff, and Vendor
 * Version: 1.0.0 - December 2025
 * 
 * Usage:
 *   const search = new CRMAssigneeSearch({
 *     containerId: 'telecallerSearchContainer',
 *     assigneeType: 'telecaller', // 'telecaller', 'field_staff', or 'vendor'
 *     onSelect: (assignee) => { console.log('Selected:', assignee); },
 *     placeholder: 'Search tele caller...',
 *     required: false
 *   });
 */

class CRMAssigneeSearch {
    constructor(options) {
        this.containerId = options.containerId;
        this.assigneeType = options.assigneeType || 'telecaller';
        this.onSelect = options.onSelect || (() => {});
        this.onClear = options.onClear || (() => {});
        this.placeholder = options.placeholder || this.getDefaultPlaceholder();
        this.required = options.required || false;
        this.label = options.label || this.getDefaultLabel();
        this.selectedValue = null;
        this.searchTimeout = null;
        this.isOpen = false;
        
        this.init();
    }
    
    getDefaultPlaceholder() {
        const placeholders = {
            'telecaller': 'Search tele caller by name, code, or phone...',
            'field_staff': 'Search field staff by name, code, or phone...',
            'vendor': 'Search vendor by name or code...',
            'partner': 'Search partner by name or code...'
        };
        return placeholders[this.assigneeType] || 'Search...';
    }
    
    getDefaultLabel() {
        const labels = {
            'telecaller': 'Tele Caller',
            'field_staff': 'Field Staff',
            'vendor': 'Vendor',
            'partner': 'Partner'
        };
        return labels[this.assigneeType] || 'Assignee';
    }
    
    getIcon() {
        const icons = {
            'telecaller': 'fa-headset',
            'field_staff': 'fa-user-tie',
            'vendor': 'fa-building',
            'partner': 'fa-handshake'
        };
        return icons[this.assigneeType] || 'fa-user';
    }
    
    init() {
        const container = document.getElementById(this.containerId);
        if (!container) {
            console.error(`[CRM-Search] Container not found: ${this.containerId}`);
            return;
        }
        
        container.innerHTML = this.render();
        this.bindEvents();
        console.log(`[CRM-Search] Initialized ${this.assigneeType} search in #${this.containerId}`);
    }
    
    render() {
        const uniqueId = `crm_search_${this.assigneeType}_${Date.now()}`;
        this.inputId = uniqueId + '_input';
        this.dropdownId = uniqueId + '_dropdown';
        this.selectedId = uniqueId + '_selected';
        this.hiddenId = uniqueId + '_hidden';
        
        return `
            <div class="crm-assignee-search" data-type="${this.assigneeType}">
                <label class="form-label">
                    <i class="fas ${this.getIcon()} me-1"></i>${this.label}
                    ${this.required ? '<span class="text-danger">*</span>' : ''}
                </label>
                
                <div class="crm-search-wrapper position-relative">
                    <!-- Selected Value Display -->
                    <div id="${this.selectedId}" class="crm-selected-value d-none">
                        <div class="d-flex align-items-center justify-content-between p-2 border rounded bg-light">
                            <div class="selected-info">
                                <i class="fas ${this.getIcon()} text-primary me-2"></i>
                                <span class="selected-name fw-medium"></span>
                                <small class="text-muted ms-2 selected-code"></small>
                            </div>
                            <button type="button" class="btn btn-sm btn-outline-danger crm-clear-btn" title="Clear selection">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                    
                    <!-- Search Input -->
                    <div id="${this.inputId}_wrapper" class="crm-search-input-wrapper">
                        <div class="input-group">
                            <span class="input-group-text bg-white">
                                <i class="fas fa-search text-muted"></i>
                            </span>
                            <input type="text" 
                                   id="${this.inputId}" 
                                   class="form-control crm-search-input" 
                                   placeholder="${this.placeholder}"
                                   autocomplete="off"
                                   ${this.required ? 'required' : ''}>
                            <span class="input-group-text bg-white crm-loading d-none">
                                <i class="fas fa-spinner fa-spin text-primary"></i>
                            </span>
                        </div>
                        
                        <!-- Dropdown Results -->
                        <div id="${this.dropdownId}" class="crm-search-dropdown position-absolute w-100 bg-white border rounded shadow-sm d-none" style="z-index: 1050; max-height: 300px; overflow-y: auto; top: 100%;">
                        </div>
                    </div>
                    
                    <!-- Hidden Input for Form Submission -->
                    <input type="hidden" id="${this.hiddenId}" name="${this.assigneeType}_id" value="">
                </div>
                
                <!-- Validation Message -->
                <div class="crm-validation-msg invalid-feedback"></div>
            </div>
        `;
    }
    
    bindEvents() {
        const input = document.getElementById(this.inputId);
        const dropdown = document.getElementById(this.dropdownId);
        const clearBtn = document.querySelector(`#${this.selectedId} .crm-clear-btn`);
        
        if (!input) return;
        
        input.addEventListener('input', (e) => this.handleSearch(e.target.value));
        input.addEventListener('focus', () => this.showDropdown());
        input.addEventListener('keydown', (e) => this.handleKeydown(e));
        
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearSelection());
        }
        
        document.addEventListener('click', (e) => {
            if (!e.target.closest(`#${this.containerId}`)) {
                this.hideDropdown();
            }
        });
    }
    
    async handleSearch(query) {
        clearTimeout(this.searchTimeout);
        
        if (query.length < 1) {
            this.showDropdown();
            this.loadInitialResults();
            return;
        }
        
        this.showLoading(true);
        
        this.searchTimeout = setTimeout(async () => {
            try {
                const results = await this.fetchResults(query);
                this.renderResults(results);
            } catch (error) {
                console.error('[CRM-Search] Search error:', error);
                this.renderError('Failed to search. Please try again.');
            } finally {
                this.showLoading(false);
            }
        }, 300);
    }
    
    async loadInitialResults() {
        this.showLoading(true);
        try {
            const results = await this.fetchResults('');
            this.renderResults(results);
        } catch (error) {
            console.error('[CRM-Search] Initial load error:', error);
            this.renderError('Failed to load options.');
        } finally {
            this.showLoading(false);
        }
    }
    
    async fetchResults(query) {
        const companyId = this.getCompanyId();
        // Partners, telecallers, and field staff are global — company_id is not required for these types
        if (!companyId && this.assigneeType !== 'partner' && this.assigneeType !== 'telecaller' && this.assigneeType !== 'field_staff') {
            throw new Error('Company ID not available');
        }
        
        const effectiveCompanyId = companyId || 0;
        const url = `/api/v1/crm/search-assignees?company_id=${effectiveCompanyId}&assignee_type=${this.assigneeType}&q=${encodeURIComponent(query)}&limit=20`;
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        return data.data || [];
    }
    
    getCompanyId() {
        if (typeof staffGetCompanyId === 'function') {
            return staffGetCompanyId();
        }
        if (window.currentCompanyId) {
            return window.currentCompanyId;
        }
        const stored = sessionStorage.getItem('selectedCompanyId') || localStorage.getItem('selectedCompanyId');
        if (stored) return parseInt(stored);
        
        console.warn('[CRM-Search] Could not determine company_id');
        return null;
    }
    
    renderResults(results) {
        const dropdown = document.getElementById(this.dropdownId);
        if (!dropdown) return;
        
        if (results.length === 0) {
            dropdown.innerHTML = `
                <div class="p-3 text-center text-muted">
                    <i class="fas fa-search mb-2"></i>
                    <div>No ${this.label.toLowerCase()} found</div>
                </div>
            `;
            this.showDropdown();
            return;
        }
        
        dropdown.innerHTML = results.map((item, index) => `
            <div class="crm-search-item p-2 border-bottom cursor-pointer" 
                 data-index="${index}"
                 data-id="${item.id}"
                 data-name="${this.escapeHtml(item.name)}"
                 data-code="${this.escapeHtml(item.code)}"
                 data-phone="${this.escapeHtml(item.phone || '')}"
                 data-type="${item.type}"
                 data-subtype="${item.subtype}"
                 style="cursor: pointer;">
                <div class="d-flex align-items-center">
                    <div class="me-3">
                        <div class="avatar-sm bg-${this.getAvatarColor()} text-white rounded-circle d-flex align-items-center justify-content-center" style="width: 36px; height: 36px;">
                            <i class="fas ${this.getIcon()}"></i>
                        </div>
                    </div>
                    <div class="flex-grow-1">
                        <div class="fw-medium">${this.escapeHtml(item.name)}</div>
                        <div class="small text-muted">
                            <span class="badge bg-secondary me-1">${this.escapeHtml(item.code)}</span>
                            ${item.phone ? `<i class="fas fa-phone me-1"></i>${this.escapeHtml(item.phone)}` : ''}
                            ${item.department ? `<span class="ms-2"><i class="fas fa-building me-1"></i>${this.escapeHtml(item.department)}</span>` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
        
        dropdown.querySelectorAll('.crm-search-item').forEach(item => {
            item.addEventListener('click', () => this.selectItem(item));
            item.addEventListener('mouseenter', () => {
                dropdown.querySelectorAll('.crm-search-item').forEach(i => i.classList.remove('bg-light'));
                item.classList.add('bg-light');
            });
        });
        
        this.showDropdown();
    }
    
    getAvatarColor() {
        const colors = {
            'telecaller': 'info',
            'field_staff': 'success',
            'vendor': 'warning',
            'partner': 'primary'
        };
        return colors[this.assigneeType] || 'primary';
    }
    
    selectItem(itemEl) {
        const data = {
            id: parseInt(itemEl.dataset.id),
            name: itemEl.dataset.name,
            code: itemEl.dataset.code,
            phone: itemEl.dataset.phone,
            type: itemEl.dataset.type,
            subtype: itemEl.dataset.subtype
        };
        
        this.selectedValue = data;
        
        const selectedDiv = document.getElementById(this.selectedId);
        const inputWrapper = document.getElementById(this.inputId + '_wrapper');
        const hiddenInput = document.getElementById(this.hiddenId);
        
        if (selectedDiv) {
            selectedDiv.querySelector('.selected-name').textContent = data.name;
            selectedDiv.querySelector('.selected-code').textContent = `(${data.code})`;
            selectedDiv.classList.remove('d-none');
        }
        
        if (inputWrapper) {
            inputWrapper.classList.add('d-none');
        }
        
        if (hiddenInput) {
            hiddenInput.value = data.id;
        }
        
        this.hideDropdown();
        this.clearValidation();
        
        if (typeof this.onSelect === 'function') {
            this.onSelect(data);
        }
        
        console.log(`[CRM-Search] Selected ${this.assigneeType}:`, data);
    }
    
    clearSelection() {
        this.selectedValue = null;
        
        const selectedDiv = document.getElementById(this.selectedId);
        const inputWrapper = document.getElementById(this.inputId + '_wrapper');
        const hiddenInput = document.getElementById(this.hiddenId);
        const input = document.getElementById(this.inputId);
        
        if (selectedDiv) {
            selectedDiv.classList.add('d-none');
        }
        
        if (inputWrapper) {
            inputWrapper.classList.remove('d-none');
        }
        
        if (hiddenInput) {
            hiddenInput.value = '';
        }
        
        if (input) {
            input.value = '';
            input.focus();
        }
        
        if (typeof this.onClear === 'function') {
            this.onClear();
        }
        
        console.log(`[CRM-Search] Cleared ${this.assigneeType} selection`);
    }
    
    setValue(id, name, code) {
        if (!id) {
            this.clearSelection();
            return;
        }
        
        this.selectedValue = { id, name, code };
        
        const selectedDiv = document.getElementById(this.selectedId);
        const inputWrapper = document.getElementById(this.inputId + '_wrapper');
        const hiddenInput = document.getElementById(this.hiddenId);
        
        if (selectedDiv) {
            selectedDiv.querySelector('.selected-name').textContent = name;
            selectedDiv.querySelector('.selected-code').textContent = code ? `(${code})` : '';
            selectedDiv.classList.remove('d-none');
        }
        
        if (inputWrapper) {
            inputWrapper.classList.add('d-none');
        }
        
        if (hiddenInput) {
            hiddenInput.value = id;
        }
    }
    
    getValue() {
        return this.selectedValue ? this.selectedValue.id : null;
    }
    
    getSelectedData() {
        return this.selectedValue;
    }
    
    validate() {
        if (this.required && !this.selectedValue) {
            this.showValidation(`${this.label} is required`);
            return false;
        }
        this.clearValidation();
        return true;
    }
    
    showValidation(message) {
        const container = document.getElementById(this.containerId);
        const msgDiv = container?.querySelector('.crm-validation-msg');
        const wrapper = container?.querySelector('.crm-search-wrapper');
        
        if (msgDiv) {
            msgDiv.textContent = message;
            msgDiv.classList.add('d-block');
        }
        if (wrapper) {
            wrapper.classList.add('is-invalid');
        }
    }
    
    clearValidation() {
        const container = document.getElementById(this.containerId);
        const msgDiv = container?.querySelector('.crm-validation-msg');
        const wrapper = container?.querySelector('.crm-search-wrapper');
        
        if (msgDiv) {
            msgDiv.textContent = '';
            msgDiv.classList.remove('d-block');
        }
        if (wrapper) {
            wrapper.classList.remove('is-invalid');
        }
    }
    
    renderError(message) {
        const dropdown = document.getElementById(this.dropdownId);
        if (dropdown) {
            dropdown.innerHTML = `
                <div class="p-3 text-center text-danger">
                    <i class="fas fa-exclamation-circle mb-2"></i>
                    <div>${message}</div>
                </div>
            `;
            this.showDropdown();
        }
    }
    
    showDropdown() {
        const dropdown = document.getElementById(this.dropdownId);
        if (dropdown) {
            dropdown.classList.remove('d-none');
            this.isOpen = true;
        }
    }
    
    hideDropdown() {
        const dropdown = document.getElementById(this.dropdownId);
        if (dropdown) {
            dropdown.classList.add('d-none');
            this.isOpen = false;
        }
    }
    
    showLoading(show) {
        const container = document.getElementById(this.containerId);
        const loading = container?.querySelector('.crm-loading');
        if (loading) {
            loading.classList.toggle('d-none', !show);
        }
    }
    
    handleKeydown(e) {
        const dropdown = document.getElementById(this.dropdownId);
        if (!dropdown || !this.isOpen) return;
        
        const items = dropdown.querySelectorAll('.crm-search-item');
        const current = dropdown.querySelector('.crm-search-item.bg-light');
        let currentIndex = current ? Array.from(items).indexOf(current) : -1;
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            currentIndex = Math.min(currentIndex + 1, items.length - 1);
            items.forEach((item, i) => item.classList.toggle('bg-light', i === currentIndex));
            items[currentIndex]?.scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            currentIndex = Math.max(currentIndex - 1, 0);
            items.forEach((item, i) => item.classList.toggle('bg-light', i === currentIndex));
            items[currentIndex]?.scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (current) {
                this.selectItem(current);
            }
        } else if (e.key === 'Escape') {
            this.hideDropdown();
        }
    }
    
    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
    
    destroy() {
        const container = document.getElementById(this.containerId);
        if (container) {
            container.innerHTML = '';
        }
        this.selectedValue = null;
    }
    
    setDisabled(disabled) {
        const container = document.getElementById(this.containerId);
        if (!container) return;
        
        const input = document.getElementById(this.inputId);
        const clearBtn = container.querySelector('.crm-clear-btn');
        const wrapper = container.querySelector('.crm-assignee-search');
        
        if (input) {
            input.disabled = disabled;
        }
        if (clearBtn) {
            clearBtn.disabled = disabled;
        }
        if (wrapper) {
            wrapper.style.opacity = disabled ? '0.6' : '1';
            wrapper.style.pointerEvents = disabled ? 'none' : 'auto';
        }
        
        this.isDisabled = disabled;
    }
}

window.CRMAssigneeSearch = CRMAssigneeSearch;
console.log('[CRM-Search] CRMAssigneeSearch component loaded - DC Protocol v1.0.0');
