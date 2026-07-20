/**
 * DC_UNIVERSAL_FILTER_001: Universal Filter Component for Staff Pages
 * Mynt Real LLP - All Rights Reserved
 * 
 * Created: Dec 07, 2025
 * Updated: Dec 07, 2025 - WCAG 2.1 AA Accessibility Compliance
 * DC Protocol: Write-Verify-Validate
 * 
 * Features:
 * - Company dropdown (for SFMS/Accounts pages)
 * - Staff Type dropdown (MN_STAFF, MN_EMPLOYEE, FREELANCER, MYNT_REAL)
 * - Employee autocomplete search (type-ahead)
 * - Department dropdown
 * - Persistent filter state (localStorage)
 * - Callback on filter change
 * 
 * Accessibility (WCAG 2.1 AA):
 * - ARIA labels on all form controls
 * - role="listbox" and role="option" for autocomplete dropdown
 * - aria-expanded, aria-haspopup, aria-controls for combobox pattern
 * - aria-activedescendant for current selection tracking
 * - Full keyboard navigation (Arrow Up/Down, Enter, Escape)
 * - Visible focus indicators meeting 3:1 contrast ratio
 */

(function() {
    'use strict';

    const STORAGE_KEY_PREFIX = 'dc_universal_filter_';
    const API_BASE = '/api/v1/staff/tasks/analytics';
    
    const STAFF_TYPES = [
        { value: '', label: 'All Staff Types' },
        { value: 'MN_STAFF', label: 'MN Staff' },
        { value: 'MN_EMPLOYEE', label: 'MN Employee' },
        { value: 'FREELANCER', label: 'Freelancer' },
        { value: 'MYNT_REAL', label: 'Myntreal' }
    ];

    class UniversalFilter {
        constructor(containerId, options = {}) {
            this.options = {
                showCompany: options.showCompany !== false,
                showStaffType: options.showStaffType !== false,
                showDepartment: options.showDepartment !== false,
                showEmployee: options.showEmployee !== false,
                showSearch: options.showSearch !== false,
                pageKey: options.pageKey || window.location.pathname,
                onFilterChange: options.onFilterChange || (() => {}),
                companyLabel: options.companyLabel || 'All Companies',
                departmentLabel: options.departmentLabel || 'All Departments',
                employeeLabel: options.employeeLabel || 'Search Employee...',
                searchLabel: options.searchLabel || 'Search...',
                autoLoad: options.autoLoad !== false
            };

            this.state = {
                companies: [],
                departments: [],
                selectedCompany: '',
                selectedStaffType: '',
                selectedDepartment: '',
                selectedEmployee: null,
                searchText: ''
            };

            this.debounceTimer = null;
            this.focusedOptionIndex = -1;
            this.isReady = false;
            this.initFailed = false;
            
            this.container = document.getElementById(containerId);
            if (!this.container) {
                console.error(`[DC_UNIVERSAL_FILTER] Container not found: ${containerId}`);
                this.initFailed = true;
                this.isReady = false;
                this.readyPromise = Promise.resolve(false);
                return;
            }
            
            this.readyPromise = this.init();
        }

        async init() {
            try {
                this.loadState();
                this.render();
                if (this.options.autoLoad) {
                    await this.loadFilterOptions();
                }
                this.attachEventListeners();
                this.isReady = true;
                this.initFailed = false;
                return true;
            } catch (error) {
                console.error('[DC_UNIVERSAL_FILTER] Init failed:', error);
                this.initFailed = true;
                this.isReady = false;
                return false;
            }
        }
        
        async waitForReady() {
            return this.readyPromise;
        }

        getStorageKey() {
            return `${STORAGE_KEY_PREFIX}${this.options.pageKey}`;
        }

        loadState() {
            try {
                const saved = localStorage.getItem(this.getStorageKey());
                if (saved) {
                    const parsed = JSON.parse(saved);
                    this.state.selectedCompany = parsed.selectedCompany || '';
                    this.state.selectedStaffType = parsed.selectedStaffType || '';
                    this.state.selectedDepartment = parsed.selectedDepartment || '';
                    this.state.selectedEmployee = parsed.selectedEmployee || null;
                }
            } catch (e) {
                console.warn('[DC_UNIVERSAL_FILTER] Failed to load state:', e);
            }
        }

        saveState() {
            try {
                localStorage.setItem(this.getStorageKey(), JSON.stringify({
                    selectedCompany: this.state.selectedCompany,
                    selectedStaffType: this.state.selectedStaffType,
                    selectedDepartment: this.state.selectedDepartment,
                    selectedEmployee: this.state.selectedEmployee
                }));
            } catch (e) {
                console.warn('[DC_UNIVERSAL_FILTER] Failed to save state:', e);
            }
        }

        render() {
            const filterStyles = `
                <style>
                    .dc-universal-filter {
                        display: flex;
                        flex-wrap: wrap;
                        gap: 12px;
                        align-items: center;
                        padding: 12px 0;
                    }
                    .dc-filter-group {
                        display: flex;
                        flex-direction: column;
                        gap: 4px;
                    }
                    .dc-filter-label {
                        font-size: 11px;
                        font-weight: 600;
                        color: #6b7280;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }
                    .dc-filter-select, .dc-filter-input {
                        padding: 8px 12px;
                        border: 1px solid #d1d5db;
                        border-radius: 6px;
                        font-size: 14px;
                        min-width: 150px;
                        background: white;
                        color: #374151;
                    }
                    .dc-filter-select:focus, .dc-filter-input:focus {
                        outline: none;
                        border-color: #4f46e5;
                        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
                    }
                    .dc-employee-autocomplete {
                        position: relative;
                    }
                    .dc-employee-input {
                        min-width: 200px;
                    }
                    .dc-employee-dropdown {
                        position: absolute;
                        top: 100%;
                        left: 0;
                        right: 0;
                        background: white;
                        border: 1px solid #d1d5db;
                        border-radius: 6px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                        max-height: 250px;
                        overflow-y: auto;
                        z-index: 1000;
                        display: none;
                    }
                    .dc-employee-dropdown.show {
                        display: block;
                    }
                    .dc-employee-option {
                        padding: 10px 12px;
                        cursor: pointer;
                        border-bottom: 1px solid #f3f4f6;
                    }
                    .dc-employee-option:last-child {
                        border-bottom: none;
                    }
                    .dc-employee-option:hover {
                        background: #f3f4f6;
                    }
                    .dc-employee-option.selected {
                        background: #eef2ff;
                    }
                    .dc-employee-name {
                        font-weight: 600;
                        color: #1f2937;
                    }
                    .dc-employee-code {
                        font-size: 12px;
                        color: #6b7280;
                    }
                    .dc-employee-dept {
                        font-size: 11px;
                        color: #9ca3af;
                    }
                    .dc-filter-clear {
                        padding: 8px 16px;
                        background: #f3f4f6;
                        border: 1px solid #d1d5db;
                        border-radius: 6px;
                        font-size: 13px;
                        color: #6b7280;
                        cursor: pointer;
                        transition: all 0.2s;
                    }
                    .dc-filter-clear:hover {
                        background: #e5e7eb;
                        color: #374151;
                    }
                    .dc-selected-employee {
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        padding: 6px 10px;
                        background: #eef2ff;
                        border: 1px solid #c7d2fe;
                        border-radius: 6px;
                        font-size: 13px;
                    }
                    .dc-selected-employee-name {
                        color: #4338ca;
                        font-weight: 500;
                    }
                    .dc-selected-employee-clear {
                        color: #6366f1;
                        cursor: pointer;
                        font-size: 16px;
                        background: none;
                        border: none;
                        padding: 0 4px;
                        line-height: 1;
                    }
                    .dc-selected-employee-clear:hover {
                        color: #4338ca;
                    }
                    .dc-selected-employee-clear:focus {
                        outline: 2px solid #4f46e5;
                        outline-offset: 2px;
                        border-radius: 2px;
                    }
                    .dc-employee-option.focused {
                        background: #dbeafe;
                        outline: 2px solid #3b82f6;
                        outline-offset: -2px;
                    }
                    .sr-only {
                        position: absolute;
                        width: 1px;
                        height: 1px;
                        padding: 0;
                        margin: -1px;
                        overflow: hidden;
                        clip: rect(0, 0, 0, 0);
                        white-space: nowrap;
                        border: 0;
                    }
                    @media (max-width: 768px) {
                        .dc-universal-filter {
                            flex-direction: column;
                            align-items: stretch;
                        }
                        .dc-filter-select, .dc-filter-input {
                            width: 100%;
                        }
                    }
                </style>
            `;

            let html = filterStyles + '<div class="dc-universal-filter">';

            if (this.options.showCompany) {
                html += `
                    <div class="dc-filter-group">
                        <label id="dcFilterCompanyLabel" class="dc-filter-label" for="dcFilterCompany">Company</label>
                        <select id="dcFilterCompany" class="dc-filter-select" 
                                aria-labelledby="dcFilterCompanyLabel"
                                aria-describedby="dcFilterCompanyDesc">
                            <option value="">${this.options.companyLabel}</option>
                        </select>
                        <span id="dcFilterCompanyDesc" class="sr-only">Select a company to filter results</span>
                    </div>
                `;
            }

            if (this.options.showStaffType) {
                html += `
                    <div class="dc-filter-group">
                        <label id="dcFilterStaffTypeLabel" class="dc-filter-label" for="dcFilterStaffType">Staff Type</label>
                        <select id="dcFilterStaffType" class="dc-filter-select"
                                aria-labelledby="dcFilterStaffTypeLabel"
                                aria-describedby="dcFilterStaffTypeDesc">
                            ${STAFF_TYPES.map(st => `<option value="${st.value}">${st.label}</option>`).join('')}
                        </select>
                        <span id="dcFilterStaffTypeDesc" class="sr-only">Select staff type to filter employees</span>
                    </div>
                `;
            }

            if (this.options.showDepartment) {
                html += `
                    <div class="dc-filter-group">
                        <label id="dcFilterDepartmentLabel" class="dc-filter-label" for="dcFilterDepartment">Department</label>
                        <select id="dcFilterDepartment" class="dc-filter-select"
                                aria-labelledby="dcFilterDepartmentLabel"
                                aria-describedby="dcFilterDepartmentDesc">
                            <option value="">${this.options.departmentLabel}</option>
                        </select>
                        <span id="dcFilterDepartmentDesc" class="sr-only">Select department to filter results</span>
                    </div>
                `;
            }

            if (this.options.showEmployee) {
                html += `
                    <div class="dc-filter-group">
                        <label id="dcFilterEmployeeLabel" class="dc-filter-label" for="dcFilterEmployee">Employee</label>
                        <div class="dc-employee-autocomplete">
                            <div id="dcSelectedEmployee" style="display: none;" role="status" aria-live="polite"></div>
                            <input type="text" id="dcFilterEmployee" class="dc-filter-input dc-employee-input" 
                                   placeholder="${this.options.employeeLabel}" autocomplete="off"
                                   role="combobox"
                                   aria-labelledby="dcFilterEmployeeLabel"
                                   aria-describedby="dcFilterEmployeeDesc"
                                   aria-expanded="false"
                                   aria-haspopup="listbox"
                                   aria-controls="dcEmployeeDropdown"
                                   aria-autocomplete="list">
                            <div id="dcEmployeeDropdown" class="dc-employee-dropdown" 
                                 role="listbox"
                                 aria-label="Employee search results"></div>
                            <span id="dcFilterEmployeeDesc" class="sr-only">Type to search for employees. Use arrow keys to navigate results, Enter to select, Escape to close.</span>
                        </div>
                    </div>
                `;
            }

            if (this.options.showSearch) {
                html += `
                    <div class="dc-filter-group">
                        <label id="dcFilterSearchLabel" class="dc-filter-label" for="dcFilterSearch">Search</label>
                        <input type="text" id="dcFilterSearch" class="dc-filter-input" 
                               placeholder="${this.options.searchLabel}"
                               aria-labelledby="dcFilterSearchLabel"
                               aria-describedby="dcFilterSearchDesc">
                        <span id="dcFilterSearchDesc" class="sr-only">Type to search and filter results</span>
                    </div>
                `;
            }

            html += `
                <div class="dc-filter-group" style="align-self: flex-end;">
                    <button id="dcFilterClear" class="dc-filter-clear" 
                            type="button"
                            aria-label="Clear all filters">
                        <i class="fas fa-times" aria-hidden="true"></i> Clear Filters
                    </button>
                </div>
            `;

            html += '</div>';
            this.container.innerHTML = html;
        }

        async loadFilterOptions() {
            const token = localStorage.getItem('staff_token');
            if (!token) {
                console.warn('[DC_UNIVERSAL_FILTER] No auth token found - component will work with static options only');
                this.populateDropdowns();
                return;
            }

            try {
                const response = await fetch(`${API_BASE}/filter-options`, {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    console.warn(`[DC_UNIVERSAL_FILTER] HTTP ${response.status} - falling back to static options`);
                    this.populateDropdowns();
                    return;
                }

                const data = await response.json();
                
                if (data.success) {
                    this.state.companies = data.companies || [];
                    this.state.departments = data.departments || [];
                    this.populateDropdowns();
                } else {
                    console.warn('[DC_UNIVERSAL_FILTER] API returned success=false - using static options');
                    this.populateDropdowns();
                }
            } catch (error) {
                console.warn('[DC_UNIVERSAL_FILTER] Network error loading options:', error.message);
                this.populateDropdowns();
            }
        }

        populateDropdowns() {
            if (this.options.showCompany) {
                const companySelect = document.getElementById('dcFilterCompany');
                if (companySelect) {
                    const currentValue = companySelect.value;
                    companySelect.innerHTML = `<option value="">${this.options.companyLabel}</option>`;
                    this.state.companies.forEach(company => {
                        const option = document.createElement('option');
                        option.value = company.id;
                        option.textContent = `${company.company_name} (${company.company_code})`;
                        companySelect.appendChild(option);
                    });
                    companySelect.value = this.state.selectedCompany || currentValue;
                }
            }

            if (this.options.showDepartment) {
                const deptSelect = document.getElementById('dcFilterDepartment');
                if (deptSelect) {
                    const currentValue = deptSelect.value;
                    deptSelect.innerHTML = `<option value="">${this.options.departmentLabel}</option>`;
                    this.state.departments.forEach(dept => {
                        const option = document.createElement('option');
                        option.value = dept.id;
                        option.textContent = dept.name;
                        deptSelect.appendChild(option);
                    });
                    deptSelect.value = this.state.selectedDepartment || currentValue;
                }
            }

            if (this.options.showStaffType) {
                const staffTypeSelect = document.getElementById('dcFilterStaffType');
                if (staffTypeSelect && this.state.selectedStaffType) {
                    staffTypeSelect.value = this.state.selectedStaffType;
                }
            }

            if (this.options.showEmployee && this.state.selectedEmployee) {
                this.showSelectedEmployee(this.state.selectedEmployee);
            }
        }

        attachEventListeners() {
            if (this.options.showCompany) {
                const companySelect = document.getElementById('dcFilterCompany');
                if (companySelect) {
                    companySelect.addEventListener('change', (e) => {
                        this.state.selectedCompany = e.target.value;
                        this.saveState();
                        this.triggerFilterChange();
                    });
                }
            }

            if (this.options.showStaffType) {
                const staffTypeSelect = document.getElementById('dcFilterStaffType');
                if (staffTypeSelect) {
                    staffTypeSelect.addEventListener('change', (e) => {
                        this.state.selectedStaffType = e.target.value;
                        this.saveState();
                        this.triggerFilterChange();
                    });
                }
            }

            if (this.options.showDepartment) {
                const deptSelect = document.getElementById('dcFilterDepartment');
                if (deptSelect) {
                    deptSelect.addEventListener('change', (e) => {
                        this.state.selectedDepartment = e.target.value;
                        this.saveState();
                        this.triggerFilterChange();
                    });
                }
            }

            if (this.options.showEmployee) {
                const employeeInput = document.getElementById('dcFilterEmployee');
                const dropdown = document.getElementById('dcEmployeeDropdown');
                
                if (employeeInput) {
                    employeeInput.addEventListener('input', (e) => {
                        clearTimeout(this.debounceTimer);
                        this.focusedOptionIndex = -1;
                        this.debounceTimer = setTimeout(() => {
                            this.searchEmployees(e.target.value);
                        }, 300);
                    });

                    employeeInput.addEventListener('focus', () => {
                        if (employeeInput.value.length >= 1) {
                            this.searchEmployees(employeeInput.value);
                        }
                    });

                    employeeInput.addEventListener('keydown', (e) => {
                        const isOpen = dropdown && dropdown.classList.contains('show');
                        const options = dropdown ? dropdown.querySelectorAll('.dc-employee-option[data-id]') : [];
                        
                        if (e.key === 'ArrowDown') {
                            e.preventDefault();
                            if (!isOpen && employeeInput.value.length >= 1) {
                                this.searchEmployees(employeeInput.value);
                            } else if (options.length > 0) {
                                this.focusedOptionIndex = Math.min(this.focusedOptionIndex + 1, options.length - 1);
                                this.updateFocusedOption(options);
                            }
                        } else if (e.key === 'ArrowUp') {
                            e.preventDefault();
                            if (options.length > 0) {
                                this.focusedOptionIndex = Math.max(this.focusedOptionIndex - 1, 0);
                                this.updateFocusedOption(options);
                            }
                        } else if (e.key === 'Enter') {
                            e.preventDefault();
                            if (isOpen && this.focusedOptionIndex >= 0 && options[this.focusedOptionIndex]) {
                                const option = options[this.focusedOptionIndex];
                                const employee = {
                                    id: parseInt(option.dataset.id),
                                    emp_code: option.dataset.code,
                                    full_name: option.dataset.name
                                };
                                this.selectEmployee(employee);
                            }
                        } else if (e.key === 'Escape') {
                            e.preventDefault();
                            if (dropdown) {
                                dropdown.classList.remove('show');
                            }
                            employeeInput.setAttribute('aria-expanded', 'false');
                            employeeInput.removeAttribute('aria-activedescendant');
                            this.focusedOptionIndex = -1;
                        }
                    });

                    document.addEventListener('click', (e) => {
                        if (!e.target.closest('.dc-employee-autocomplete')) {
                            if (dropdown) {
                                dropdown.classList.remove('show');
                            }
                            if (employeeInput) {
                                employeeInput.setAttribute('aria-expanded', 'false');
                                employeeInput.removeAttribute('aria-activedescendant');
                            }
                            this.focusedOptionIndex = -1;
                        }
                    });
                }
            }

            if (this.options.showSearch) {
                const searchInput = document.getElementById('dcFilterSearch');
                if (searchInput) {
                    searchInput.addEventListener('input', (e) => {
                        clearTimeout(this.debounceTimer);
                        this.debounceTimer = setTimeout(() => {
                            this.state.searchText = e.target.value;
                            this.triggerFilterChange();
                        }, 300);
                    });
                }
            }

            const clearBtn = document.getElementById('dcFilterClear');
            if (clearBtn) {
                clearBtn.addEventListener('click', () => {
                    this.clearFilters();
                });
            }
        }

        async searchEmployees(query) {
            const dropdown = document.getElementById('dcEmployeeDropdown');
            const input = document.getElementById('dcFilterEmployee');
            if (!dropdown) return;

            if (!query || query.length < 1) {
                dropdown.classList.remove('show');
                if (input) {
                    input.setAttribute('aria-expanded', 'false');
                    input.removeAttribute('aria-activedescendant');
                }
                this.focusedOptionIndex = -1;
                return;
            }

            const token = localStorage.getItem('staff_token');
            if (!token) return;

            try {
                let url = `${API_BASE}/employees-for-filter?search=${encodeURIComponent(query)}&limit=10`;
                
                if (this.state.selectedDepartment) {
                    url += `&department_id=${this.state.selectedDepartment}`;
                }
                if (this.state.selectedStaffType) {
                    url += `&staff_type=${this.state.selectedStaffType}`;
                }

                const response = await fetch(url, {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) throw new Error(`HTTP ${response.status}`);

                const data = await response.json();
                
                if (data.success && data.employees) {
                    this.renderEmployeeDropdown(data.employees);
                }
            } catch (error) {
                console.error('[DC_UNIVERSAL_FILTER] Employee search failed:', error);
            }
        }

        renderEmployeeDropdown(employees) {
            const dropdown = document.getElementById('dcEmployeeDropdown');
            const input = document.getElementById('dcFilterEmployee');
            if (!dropdown) return;

            this.focusedOptionIndex = -1;

            if (employees.length === 0) {
                dropdown.innerHTML = '<div class="dc-employee-option" role="option" aria-disabled="true" style="color: #9ca3af;">No employees found</div>';
            } else {
                dropdown.innerHTML = employees.map((emp, index) => `
                    <div class="dc-employee-option" 
                         id="dcEmployeeOption${index}"
                         role="option"
                         aria-selected="false"
                         tabindex="-1"
                         data-id="${emp.id}" 
                         data-code="${emp.emp_code}" 
                         data-name="${emp.full_name}">
                        <div class="dc-employee-name">${emp.full_name}</div>
                        <div class="dc-employee-code">${emp.emp_code}</div>
                        <div class="dc-employee-dept">${emp.department_name || 'N/A'}</div>
                    </div>
                `).join('');
            }

            dropdown.classList.add('show');
            if (input) {
                input.setAttribute('aria-expanded', 'true');
            }

            dropdown.querySelectorAll('.dc-employee-option[data-id]').forEach(option => {
                option.addEventListener('click', () => {
                    const employee = {
                        id: parseInt(option.dataset.id),
                        emp_code: option.dataset.code,
                        full_name: option.dataset.name
                    };
                    this.selectEmployee(employee);
                });
            });
        }

        updateFocusedOption(options) {
            const input = document.getElementById('dcFilterEmployee');
            options.forEach((opt, index) => {
                opt.classList.remove('focused');
                opt.setAttribute('aria-selected', 'false');
            });
            
            if (this.focusedOptionIndex >= 0 && options[this.focusedOptionIndex]) {
                const focused = options[this.focusedOptionIndex];
                focused.classList.add('focused');
                focused.setAttribute('aria-selected', 'true');
                focused.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
                
                if (input) {
                    input.setAttribute('aria-activedescendant', focused.id);
                }
            } else if (input) {
                input.removeAttribute('aria-activedescendant');
            }
        }

        selectEmployee(employee) {
            this.state.selectedEmployee = employee;
            this.saveState();
            this.showSelectedEmployee(employee);
            
            const dropdown = document.getElementById('dcEmployeeDropdown');
            const input = document.getElementById('dcFilterEmployee');
            if (dropdown) dropdown.classList.remove('show');
            if (input) {
                input.value = '';
                input.setAttribute('aria-expanded', 'false');
                input.removeAttribute('aria-activedescendant');
            }
            this.focusedOptionIndex = -1;
            
            this.triggerFilterChange();
        }

        showSelectedEmployee(employee) {
            const container = document.getElementById('dcSelectedEmployee');
            const input = document.getElementById('dcFilterEmployee');
            
            if (container && employee) {
                container.innerHTML = `
                    <div class="dc-selected-employee">
                        <span class="dc-selected-employee-name">${employee.full_name} (${employee.emp_code})</span>
                        <button type="button" 
                                class="dc-selected-employee-clear" 
                                aria-label="Clear selected employee ${employee.full_name}"
                                title="Clear selected employee">&times;</button>
                    </div>
                `;
                container.style.display = 'block';
                if (input) input.style.display = 'none';

                const clearBtn = container.querySelector('.dc-selected-employee-clear');
                clearBtn.addEventListener('click', () => {
                    this.clearEmployee();
                });
                clearBtn.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        this.clearEmployee();
                    }
                });
            }
        }

        clearEmployee() {
            this.state.selectedEmployee = null;
            this.saveState();
            this.focusedOptionIndex = -1;
            
            const container = document.getElementById('dcSelectedEmployee');
            const input = document.getElementById('dcFilterEmployee');
            const dropdown = document.getElementById('dcEmployeeDropdown');
            
            if (container) {
                container.style.display = 'none';
                container.innerHTML = '';
            }
            if (input) {
                input.style.display = 'block';
                input.setAttribute('aria-expanded', 'false');
                input.removeAttribute('aria-activedescendant');
            }
            if (dropdown) {
                dropdown.classList.remove('show');
            }
            
            this.triggerFilterChange();
        }

        clearFilters() {
            this.state.selectedCompany = '';
            this.state.selectedStaffType = '';
            this.state.selectedDepartment = '';
            this.state.selectedEmployee = null;
            this.state.searchText = '';

            if (this.options.showCompany) {
                const el = document.getElementById('dcFilterCompany');
                if (el) el.value = '';
            }
            if (this.options.showStaffType) {
                const el = document.getElementById('dcFilterStaffType');
                if (el) el.value = '';
            }
            if (this.options.showDepartment) {
                const el = document.getElementById('dcFilterDepartment');
                if (el) el.value = '';
            }
            if (this.options.showEmployee) {
                this.clearEmployee();
            }
            if (this.options.showSearch) {
                const el = document.getElementById('dcFilterSearch');
                if (el) el.value = '';
            }

            this.saveState();
            this.triggerFilterChange();
        }

        triggerFilterChange() {
            const filters = this.getFilters();
            this.options.onFilterChange(filters);
        }

        getFilters() {
            return {
                company_id: this.state.selectedCompany || null,
                staff_type: this.state.selectedStaffType || null,
                department_id: this.state.selectedDepartment || null,
                employee_id: this.state.selectedEmployee?.id || null,
                employee: this.state.selectedEmployee || null,
                search: this.state.searchText || null
            };
        }

        setFilter(key, value) {
            switch(key) {
                case 'company_id':
                    this.state.selectedCompany = value || '';
                    const companyEl = document.getElementById('dcFilterCompany');
                    if (companyEl) companyEl.value = value || '';
                    break;
                case 'staff_type':
                    this.state.selectedStaffType = value || '';
                    const staffTypeEl = document.getElementById('dcFilterStaffType');
                    if (staffTypeEl) staffTypeEl.value = value || '';
                    break;
                case 'department_id':
                    this.state.selectedDepartment = value || '';
                    const deptEl = document.getElementById('dcFilterDepartment');
                    if (deptEl) deptEl.value = value || '';
                    break;
            }
            this.saveState();
        }
    }

    window.DCUniversalFilter = UniversalFilter;
    console.log('[DC_UNIVERSAL_FILTER] Component loaded - DC Protocol v1.0.0');
})();
