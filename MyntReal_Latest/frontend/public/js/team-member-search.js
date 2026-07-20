/**
 * Team Member Search Component
 * DC Protocol (Feb 2026): Search-and-select for team member filtering
 * Replaces dropdown with searchable input across all team pages
 * 
 * Usage:
 *   const search = new TeamMemberSearch({
 *     containerId: 'teamMemberSearchContainer',
 *     onSelect: (member) => { console.log('Selected:', member); },
 *     onClear: () => { console.log('Cleared'); },
 *     placeholder: 'Search team member...',
 *     showSelf: true,
 *     compactMode: true
 *   });
 *   
 *   // Load data from /my-downline response:
 *   search.setMembers(selfData, downlineArray);
 */

class TeamMemberSearch {
    constructor(options) {
        this.containerId = options.containerId;
        this.onSelect = options.onSelect || (() => {});
        this.onClear = options.onClear || (() => {});
        this.placeholder = options.placeholder || 'Search team member by name...';
        this.showSelf = options.showSelf !== false;
        this.compactMode = options.compactMode !== false;
        this.selectedValue = null;
        this.selectedMember = null;
        this.allMembers = [];
        this.selfMember = null;
        this.searchTimeout = null;
        this.isOpen = false;
        this.highlightIndex = -1;
        this.filteredResults = [];

        this.init();
    }

    init() {
        const container = document.getElementById(this.containerId);
        if (!container) {
            console.error(`[TeamSearch] Container not found: ${this.containerId}`);
            return;
        }

        const uniqueId = `tms_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
        this.inputId = uniqueId + '_input';
        this.dropdownId = uniqueId + '_dropdown';
        this.selectedId = uniqueId + '_selected';
        this.wrapperId = uniqueId + '_wrapper';

        container.innerHTML = this.render();
        this.bindEvents();
    }

    render() {
        if (this.compactMode) {
            return `
                <div class="tms-wrapper position-relative" id="${this.wrapperId}" style="min-width: 220px;">
                    <div id="${this.selectedId}" class="tms-selected d-none">
                        <div class="d-flex align-items-center gap-1">
                            <div class="form-control form-control-sm d-flex align-items-center justify-content-between" style="background: rgba(255,255,255,0.95); cursor: default; padding: 0.2rem 0.5rem;">
                                <span class="tms-selected-name text-truncate" style="font-size: 13px; max-width: 170px;"></span>
                                <button type="button" class="btn btn-link btn-sm p-0 ms-1 tms-clear-btn text-danger" title="Clear" style="font-size: 12px; line-height: 1;">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                    <div id="${this.inputId}_wrap" class="tms-input-wrap">
                        <div class="position-relative">
                            <input type="text"
                                   id="${this.inputId}"
                                   class="form-control form-control-sm"
                                   placeholder="${this.placeholder}"
                                   autocomplete="off"
                                   style="background: rgba(255,255,255,0.95); padding-right: 28px;">
                            <i class="fas fa-search position-absolute text-muted" style="right: 8px; top: 50%; transform: translateY(-50%); font-size: 12px; pointer-events: none;"></i>
                        </div>
                    </div>
                    <div id="${this.dropdownId}" class="tms-dropdown position-absolute w-100 bg-white border rounded shadow-sm d-none" style="z-index: 1050; max-height: 280px; overflow-y: auto; top: 100%; margin-top: 2px; color: #333;">
                    </div>
                </div>
            `;
        }

        return `
            <div class="tms-wrapper position-relative" id="${this.wrapperId}" style="min-width: 250px;">
                <div id="${this.selectedId}" class="tms-selected d-none mb-1">
                    <div class="d-flex align-items-center justify-content-between p-2 border rounded bg-light">
                        <div>
                            <i class="fas fa-user text-primary me-2"></i>
                            <span class="tms-selected-name fw-medium"></span>
                        </div>
                        <button type="button" class="btn btn-sm btn-outline-danger tms-clear-btn" title="Clear">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
                <div id="${this.inputId}_wrap" class="tms-input-wrap">
                    <div class="input-group">
                        <span class="input-group-text bg-white"><i class="fas fa-search text-muted"></i></span>
                        <input type="text"
                               id="${this.inputId}"
                               class="form-control"
                               placeholder="${this.placeholder}"
                               autocomplete="off">
                    </div>
                </div>
                <div id="${this.dropdownId}" class="tms-dropdown position-absolute w-100 bg-white border rounded shadow-sm d-none" style="z-index: 1050; max-height: 300px; overflow-y: auto; top: 100%; margin-top: 2px; color: #333;">
                </div>
            </div>
        `;
    }

    bindEvents() {
        const input = document.getElementById(this.inputId);
        const clearBtn = document.querySelector(`#${this.wrapperId} .tms-clear-btn`);

        if (!input) return;

        input.addEventListener('input', (e) => this.handleSearch(e.target.value));
        input.addEventListener('focus', () => {
            this.showAllResults();
            this.showDropdown();
        });
        input.addEventListener('keydown', (e) => this.handleKeydown(e));

        if (clearBtn) {
            clearBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.clearSelection();
            });
        }

        document.addEventListener('click', (e) => {
            if (!e.target.closest(`#${this.wrapperId}`)) {
                this.hideDropdown();
            }
        });
    }

    setMembers(selfData, downlineArray) {
        this.selfMember = selfData;
        this.allMembers = [];

        if (this.showSelf && selfData) {
            this.allMembers.push({
                id: selfData.id,
                name: selfData.name || selfData.full_name || selfData.emp_code,
                emp_code: selfData.emp_code,
                designation: selfData.designation || '',
                level: selfData.level || null,
                is_self: true,
                is_resigned: false,
                composite_id: selfData.composite_id || null
            });
        }

        if (downlineArray && downlineArray.length > 0) {
            downlineArray.forEach(member => {
                this.allMembers.push({
                    id: member.id,
                    name: member.name || member.full_name || member.emp_code,
                    emp_code: member.emp_code,
                    designation: member.designation || '',
                    level: member.level || null,
                    is_self: false,
                    is_resigned: member.is_resigned || false,
                    composite_id: member.composite_id || null
                });
            });
        }
    }

    handleSearch(query) {
        clearTimeout(this.searchTimeout);

        this.searchTimeout = setTimeout(() => {
            const q = (query || '').toLowerCase().trim();
            if (!q) {
                this.showAllResults();
            } else {
                this.filteredResults = this.allMembers.filter(m =>
                    (m.name && m.name.toLowerCase().includes(q)) ||
                    (m.emp_code && m.emp_code.toLowerCase().includes(q)) ||
                    (m.designation && m.designation.toLowerCase().includes(q))
                );
                this.renderResults(this.filteredResults);
            }
            this.showDropdown();
        }, 150);
    }

    showAllResults() {
        this.filteredResults = [...this.allMembers];
        this.renderResults(this.filteredResults);
    }

    renderResults(results) {
        const dropdown = document.getElementById(this.dropdownId);
        if (!dropdown) return;

        this.highlightIndex = -1;

        if (!results || results.length === 0) {
            dropdown.innerHTML = `
                <div class="p-3 text-center text-muted" style="font-size: 13px;">
                    <i class="fas fa-search me-1"></i> No team members found
                </div>
            `;
            return;
        }

        const allOption = `
            <div class="tms-item p-2 border-bottom" data-value="" style="cursor: pointer; font-size: 13px;">
                <div class="d-flex align-items-center">
                    <i class="fas fa-users text-muted me-2" style="font-size: 12px;"></i>
                    <span class="fw-medium">All Team Members</span>
                </div>
            </div>
        `;

        const items = results.map((member, idx) => {
            const selfBadge = member.is_self ? '<span class="badge bg-primary ms-1" style="font-size: 10px;">Me</span>' : '';
            const resignedBadge = member.is_resigned ? '<span class="badge bg-danger ms-1" style="font-size: 10px;">Resigned</span>' : '';
            const levelInfo = member.level ? `<span class="text-muted ms-1" style="font-size: 11px;">L${member.level}</span>` : '';
            const value = member.composite_id || member.id;

            return `
                <div class="tms-item p-2 ${idx < results.length - 1 ? 'border-bottom' : ''}" data-value="${value}" data-index="${idx}" style="cursor: pointer; font-size: 13px;">
                    <div class="d-flex align-items-center justify-content-between">
                        <div class="text-truncate">
                            <i class="fas fa-user text-muted me-1" style="font-size: 11px;"></i>
                            <span class="fw-medium">${this.escapeHtml(member.name)}</span>
                            ${selfBadge}${resignedBadge}${levelInfo}
                        </div>
                        <small class="text-muted ms-2 flex-shrink-0">${this.escapeHtml(member.emp_code)}</small>
                    </div>
                    ${member.designation ? `<div class="text-muted ms-3" style="font-size: 11px;">${this.escapeHtml(member.designation)}</div>` : ''}
                </div>
            `;
        }).join('');

        dropdown.innerHTML = allOption + items;

        dropdown.querySelectorAll('.tms-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const value = item.dataset.value;
                if (!value) {
                    this.clearSelection();
                } else {
                    const member = this.allMembers.find(m => String(m.composite_id || m.id) === String(value));
                    if (member) {
                        this.selectMember(member);
                    }
                }
            });
            item.addEventListener('mouseenter', () => {
                dropdown.querySelectorAll('.tms-item').forEach(i => i.classList.remove('tms-highlight'));
                item.classList.add('tms-highlight');
            });
        });
    }

    selectMember(member) {
        this.selectedValue = member.composite_id || member.id;
        this.selectedMember = member;

        const selectedDiv = document.getElementById(this.selectedId);
        const inputWrap = document.getElementById(this.inputId + '_wrap');
        const nameSpan = selectedDiv?.querySelector('.tms-selected-name');

        if (nameSpan) {
            const selfLabel = member.is_self ? ' (Me)' : '';
            const resignedLabel = member.is_resigned ? ' (Resigned)' : '';
            nameSpan.textContent = `${member.name} (${member.emp_code})${selfLabel}${resignedLabel}`;
            nameSpan.title = `${member.name} (${member.emp_code})`;
        }

        if (selectedDiv) selectedDiv.classList.remove('d-none');
        if (inputWrap) inputWrap.classList.add('d-none');

        this.hideDropdown();
        this.onSelect(member);
    }

    clearSelection() {
        this.selectedValue = null;
        this.selectedMember = null;

        const selectedDiv = document.getElementById(this.selectedId);
        const inputWrap = document.getElementById(this.inputId + '_wrap');
        const input = document.getElementById(this.inputId);

        if (selectedDiv) selectedDiv.classList.add('d-none');
        if (inputWrap) inputWrap.classList.remove('d-none');
        if (input) input.value = '';

        this.hideDropdown();
        this.onClear();
    }

    getValue() {
        return this.selectedValue || '';
    }

    getSelectedMember() {
        return this.selectedMember;
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
            this.highlightIndex = -1;
        }
    }

    handleKeydown(e) {
        const items = document.querySelectorAll(`#${this.dropdownId} .tms-item`);
        if (!items.length) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.highlightIndex = Math.min(this.highlightIndex + 1, items.length - 1);
            this.updateHighlight(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.highlightIndex = Math.max(this.highlightIndex - 1, 0);
            this.updateHighlight(items);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (this.highlightIndex >= 0 && items[this.highlightIndex]) {
                items[this.highlightIndex].click();
            }
        } else if (e.key === 'Escape') {
            this.hideDropdown();
        }
    }

    updateHighlight(items) {
        items.forEach(i => i.classList.remove('tms-highlight'));
        if (this.highlightIndex >= 0 && items[this.highlightIndex]) {
            items[this.highlightIndex].classList.add('tms-highlight');
            items[this.highlightIndex].scrollIntoView({ block: 'nearest' });
        }
    }

    setDisabled(disabled) {
        const input = document.getElementById(this.inputId);
        if (input) input.disabled = disabled;
        if (disabled) {
            this.clearSelection();
        }
    }

    reset(silent = false) {
        if (silent) {
            this.selectedValue = null;
            this.selectedMember = null;
            const selectedDiv = document.getElementById(this.selectedId);
            const inputWrap = document.getElementById(this.inputId + '_wrap');
            const input = document.getElementById(this.inputId);
            if (selectedDiv) selectedDiv.classList.add('d-none');
            if (inputWrap) inputWrap.classList.remove('d-none');
            if (input) input.value = '';
            this.hideDropdown();
        } else {
            this.clearSelection();
        }
        this.allMembers = [];
        this.selfMember = null;
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

if (!document.getElementById('tms-styles')) {
    const style = document.createElement('style');
    style.id = 'tms-styles';
    style.textContent = `
        .tms-item:hover, .tms-item.tms-highlight {
            background-color: #f0f4ff !important;
        }
        .tms-dropdown {
            scrollbar-width: thin;
        }
        .tms-dropdown::-webkit-scrollbar {
            width: 6px;
        }
        .tms-dropdown::-webkit-scrollbar-thumb {
            background: #ccc;
            border-radius: 3px;
        }
        .tms-selected-name {
            display: inline-block;
        }
    `;
    document.head.appendChild(style);
}
