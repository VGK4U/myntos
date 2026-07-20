/**
 * Staff KRA Templates Page
 * DC Protocol: DC_MOBILE_KRA_TEMPLATES_001
 * View and manage KRA templates with full CRUD support
 * Enhanced Jan 2026: Full web parity with Create, Edit, Assign, Deactivate
 */

import { apiService } from '../services/api.service';
import { authService } from '../services/auth.service';
import { PageHeader } from '../components/PageHeader';

interface KRATemplate {
  id: number;
  kra_code: string;
  title: string;
  description: string;
  applicable_to_role: string;
  applicable_to_designation: string;
  frequency: string;
  frequency_config?: any;
  estimated_time_minutes: number;
  is_mandatory: boolean;
  approval_status: string;
  status: string;
  created_at: string;
  updated_at: string;
  assigned_count: number;
  assigned_employee_names: string[];
}

interface Employee {
  id: number;
  emp_code: string;
  full_name: string;
  department_name?: string;
  designation?: string;
}

const FREQUENCY_OPTIONS = [
  { value: 'daily', label: 'Daily' },
  { value: 'every_n_days', label: 'Every N Days' },
  { value: 'selected_days', label: 'Selected Days' },
  { value: 'every_15_days', label: 'Every 15 Days' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'custom', label: 'Custom' },
  { value: 'adhoc', label: 'Ad-hoc' }
];

export class StaffKRATemplatesPage {
  private container: HTMLElement;
  private templates: KRATemplate[] = [];
  private loading: boolean = true;
  private filterRole: string = '';
  private roles: string[] = [];
  private expandedTemplate: number | null = null;
  
  private canAddKRA: boolean = false;
  private canAssign: boolean = false;
  private canEdit: boolean = false;
  
  private showCreateForm: boolean = false;
  private nextKRACode: string = 'KRA-001';
  private employees: Employee[] = [];
  private selectedEmployees: number[] = [];
  private editingTemplate: KRATemplate | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    await this.checkPermissions();
    this.render();
    await this.loadTemplates();
  }
  
  private async checkPermissions(): Promise<void> {
    try {
      const authState = await authService.getAuthState();
      if (authState?.user) {
        const user = authState.user;
        const hierarchyLevel = user.role?.hierarchy_level || user.hierarchy_level || 0;
        const roleCode = user.role?.role_code || user.role_code || '';
        
        console.log('[StaffKRATemplatesPage] Permission check - hierarchy:', hierarchyLevel, 'roleCode:', roleCode);
        
        this.canAddKRA = hierarchyLevel >= 100 || roleCode === 'hr' || roleCode === 'ea';
        this.canAssign = hierarchyLevel >= 100 || roleCode === 'hr' || roleCode === 'ea';
        this.canEdit = hierarchyLevel >= 100 || roleCode === 'hr' || roleCode === 'ea';
        
        console.log('[StaffKRATemplatesPage] Permissions - canAdd:', this.canAddKRA, 'canAssign:', this.canAssign, 'canEdit:', this.canEdit);
      }
    } catch (e) {
      console.error('[StaffKRATemplatesPage] Failed to check permissions:', e);
    }
  }
  
  private async fetchNextKRACode(): Promise<void> {
    try {
      const response = await apiService.get<any>('/staff/kra/next-code');
      const data = response.data || response;
      if (data?.kra_code) {
        this.nextKRACode = data.kra_code;
      }
    } catch (error) {
      console.error('[StaffKRATemplatesPage] Failed to fetch next code:', error);
    }
  }

  private async loadEmployees(): Promise<void> {
    try {
      const response = await apiService.get<any>('/staff/employees?limit=100&status=active');
      if (response.success !== false && response.data?.employees) {
        this.employees = response.data.employees;
      }
    } catch (error) {
      console.error('[StaffKRATemplatesPage] Failed to load employees:', error);
    }
  }

  private async loadTemplates(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      let endpoint = '/staff/kra/templates';
      if (this.filterRole) endpoint += `?search=${encodeURIComponent(this.filterRole)}`;

      const response = await apiService.get<any>(endpoint);
      console.log('[StaffKRATemplatesPage] API response:', response);

      const data = response.data as any;
      if (response.success !== false && data) {
        if (data.templates) {
          this.templates = data.templates;
        } else if (Array.isArray(data)) {
          this.templates = data;
        } else {
          this.templates = [];
        }
        this.roles = [...new Set(this.templates.map(t => t.applicable_to_role).filter(Boolean))];
        console.log('[StaffKRATemplatesPage] Loaded templates:', this.templates.length);
      } else {
        this.templates = [];
      }
    } catch (error) {
      console.error('[StaffKRATemplatesPage] Failed to load:', error);
      this.templates = [];
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container kra-templates-page">
        ${PageHeader.render({ title: 'KRA Templates', showBack: true })}
        
        ${this.canAddKRA ? `
          <div class="action-bar">
            <button class="btn btn-primary btn-block" id="addKRABtn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
              Add KRA Template
            </button>
          </div>
        ` : ''}
        
        <div class="filter-row">
          <select id="roleFilter" class="filter-select full-width">
            <option value="">All Roles</option>
          </select>
        </div>

        <div class="list-container" id="templatesList">
          <div class="loading-state">Loading templates...</div>
        </div>
      </div>
      
      <!-- Create KRA Template Modal -->
      <div class="modal-overlay" id="createKRAModal" style="display: none;">
        <div class="modal-content modal-lg">
          <div class="modal-header">
            <h4 id="modalTitle">Create KRA Template</h4>
            <button class="modal-close" id="closeCreateModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>KRA Code <span class="required">*</span></label>
              <input type="text" id="kraCode" class="form-input" placeholder="KRA-001" readonly>
              <small class="form-hint">Auto-generated code</small>
            </div>
            
            <div class="form-group">
              <label>Title <span class="required">*</span></label>
              <input type="text" id="kraTitle" class="form-input" placeholder="Enter KRA title" maxlength="256">
            </div>
            
            <div class="form-group">
              <label>Description</label>
              <textarea id="kraDescription" class="form-textarea" rows="3" placeholder="Enter KRA description"></textarea>
            </div>
            
            <div class="form-row">
              <div class="form-group half">
                <label>Applicable to Role</label>
                <input type="text" id="kraRole" class="form-input" placeholder="e.g., All, Sales">
              </div>
              <div class="form-group half">
                <label>Applicable to Designation</label>
                <input type="text" id="kraDesignation" class="form-input" placeholder="e.g., All, Manager">
              </div>
            </div>
            
            <div class="form-row">
              <div class="form-group half">
                <label>Frequency <span class="required">*</span></label>
                <select id="kraFrequency" class="form-input">
                  ${FREQUENCY_OPTIONS.map(f => `<option value="${f.value}">${f.label}</option>`).join('')}
                </select>
              </div>
              <div class="form-group half">
                <label>Est. Time (mins)</label>
                <input type="number" id="kraEstTime" class="form-input" placeholder="30" min="1" max="480">
              </div>
            </div>
            
            <div class="form-group">
              <label class="checkbox-label">
                <input type="checkbox" id="kraMandatory" checked>
                <span>Mandatory KRA</span>
              </label>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelCreateBtn">Cancel</button>
            <button class="btn btn-primary" id="submitCreateBtn">Create Template</button>
          </div>
        </div>
      </div>
      
      <!-- Assign Staff Modal -->
      <div class="modal-overlay" id="assignModal" style="display: none;">
        <div class="modal-content modal-lg">
          <div class="modal-header">
            <h4 id="assignModalTitle">Assign Staff</h4>
            <button class="modal-close" id="closeAssignModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Effective From <span class="required">*</span></label>
              <input type="date" id="effectiveFrom" class="form-input">
            </div>
            <div class="form-group">
              <label>Effective Until (Optional)</label>
              <input type="date" id="effectiveUntil" class="form-input">
            </div>
            
            <div class="form-group">
              <label>Search Employees</label>
              <input type="text" id="employeeSearch" class="form-input" placeholder="Search by name or code...">
            </div>
            
            <div class="employee-list" id="employeeList">
              <div class="loading-state">Loading employees...</div>
            </div>
            
            <div class="selected-count" id="selectedCount">0 employees selected</div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelAssignBtn">Cancel</button>
            <button class="btn btn-primary" id="submitAssignBtn">Assign KRA</button>
          </div>
        </div>
      </div>
      
      <style>
        .kra-templates-page { padding-bottom: 100px; }
        .action-bar { padding: 12px 16px; }
        .filter-row { padding: 0 16px 12px; }
        .filter-select { width: 100%; padding: 10px 12px; border-radius: 8px; background: var(--card-bg, #1a2234); border: 1px solid var(--border-color, #2d3748); color: var(--text-primary, #fff); }
        .list-container { padding: 0 16px; }
        
        .template-card { background: var(--card-bg, #1a2234); border-radius: 12px; margin-bottom: 12px; overflow: hidden; }
        .template-header { padding: 16px; display: flex; justify-content: space-between; align-items: flex-start; cursor: pointer; }
        .template-info { flex: 1; }
        .template-name { font-weight: 600; font-size: 15px; color: var(--text-primary, #fff); margin-bottom: 4px; }
        .template-meta { font-size: 12px; color: var(--text-secondary, #a0aec0); }
        .template-toggle { display: flex; align-items: center; gap: 8px; }
        .toggle-icon { transition: transform 0.2s; color: var(--text-secondary, #a0aec0); }
        .toggle-icon.expanded { transform: rotate(180deg); }
        
        .template-summary { padding: 0 16px 12px; display: flex; flex-wrap: wrap; gap: 8px; }
        .summary-item { font-size: 12px; padding: 4px 10px; background: var(--bg-secondary, #0d1421); border-radius: 6px; color: var(--text-secondary, #a0aec0); }
        .summary-item.mandatory { background: rgba(239, 68, 68, 0.15); color: #f87171; }
        
        .status-badge { padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
        .status-badge.active { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
        .status-badge.inactive { background: rgba(239, 68, 68, 0.15); color: #f87171; }
        
        .template-details { padding: 0 16px 16px; }
        .template-details.collapsed { display: none; }
        .template-details.expanded { display: block; }
        .template-detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }
        .detail-item { font-size: 13px; color: var(--text-secondary, #a0aec0); }
        .detail-item strong { color: var(--text-primary, #fff); }
        
        .assigned-employees { font-size: 13px; color: var(--text-secondary, #a0aec0); margin-bottom: 12px; }
        
        .template-actions { display: flex; gap: 8px; flex-wrap: wrap; padding-top: 12px; border-top: 1px solid var(--border-color, #2d3748); }
        .btn-sm { padding: 8px 14px; font-size: 12px; border-radius: 6px; display: inline-flex; align-items: center; gap: 6px; }
        .btn-assign { background: #6366f1; color: white; }
        .btn-edit { background: #fbbf24; color: #1a1a1a; }
        .btn-deactivate { background: rgba(239, 68, 68, 0.15); color: #f87171; }
        .btn-reactivate { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
        
        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); display: flex; justify-content: center; align-items: flex-start; padding: 20px; z-index: 1000; overflow-y: auto; }
        .modal-content { background: var(--card-bg, #1a2234); border-radius: 12px; width: 100%; max-width: 500px; margin-top: 40px; }
        .modal-header { padding: 16px; border-bottom: 1px solid var(--border-color, #2d3748); display: flex; justify-content: space-between; align-items: center; }
        .modal-header h4 { margin: 0; color: var(--text-primary, #fff); font-size: 16px; }
        .modal-close { background: none; border: none; color: var(--text-secondary, #a0aec0); font-size: 24px; cursor: pointer; }
        .modal-body { padding: 16px; max-height: 60vh; overflow-y: auto; }
        .modal-footer { padding: 16px; border-top: 1px solid var(--border-color, #2d3748); display: flex; gap: 12px; justify-content: flex-end; }
        
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; margin-bottom: 6px; font-size: 13px; font-weight: 500; color: var(--text-primary, #fff); }
        .form-group.half { flex: 1; }
        .form-row { display: flex; gap: 12px; }
        .form-input, .form-textarea { width: 100%; padding: 10px 12px; border-radius: 8px; background: var(--bg-secondary, #0d1421); border: 1px solid var(--border-color, #2d3748); color: var(--text-primary, #fff); font-size: 14px; }
        .form-hint { font-size: 11px; color: var(--text-secondary, #a0aec0); margin-top: 4px; }
        .required { color: #f87171; }
        .checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; }
        .checkbox-label input { width: 18px; height: 18px; }
        
        .employee-list { max-height: 250px; overflow-y: auto; border: 1px solid var(--border-color, #2d3748); border-radius: 8px; }
        .employee-item { padding: 12px; display: flex; align-items: center; gap: 12px; border-bottom: 1px solid var(--border-color, #2d3748); cursor: pointer; }
        .employee-item:last-child { border-bottom: none; }
        .employee-item.selected { background: rgba(99, 102, 241, 0.1); }
        .employee-checkbox { width: 20px; height: 20px; }
        .employee-info { flex: 1; }
        .employee-name { font-size: 14px; color: var(--text-primary, #fff); }
        .employee-meta { font-size: 12px; color: var(--text-secondary, #a0aec0); }
        .selected-count { margin-top: 12px; font-size: 13px; color: var(--text-secondary, #a0aec0); text-align: right; }
      </style>
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    document.getElementById('roleFilter')?.addEventListener('change', (e) => {
      this.filterRole = (e.target as HTMLSelectElement).value;
      this.loadTemplates();
    });
    
    document.getElementById('addKRABtn')?.addEventListener('click', () => {
      this.editingTemplate = null;
      this.showCreateModal();
    });
    
    document.getElementById('closeCreateModal')?.addEventListener('click', () => this.hideCreateModal());
    document.getElementById('cancelCreateBtn')?.addEventListener('click', () => this.hideCreateModal());
    document.getElementById('submitCreateBtn')?.addEventListener('click', () => this.submitTemplate());
    
    document.getElementById('closeAssignModal')?.addEventListener('click', () => this.hideAssignModal());
    document.getElementById('cancelAssignBtn')?.addEventListener('click', () => this.hideAssignModal());
    document.getElementById('submitAssignBtn')?.addEventListener('click', () => this.submitAssignment());
    
    document.getElementById('employeeSearch')?.addEventListener('input', (e) => {
      this.filterEmployeeList((e.target as HTMLInputElement).value);
    });
  }
  
  private async showCreateModal(): Promise<void> {
    const modalTitle = document.getElementById('modalTitle');
    const submitBtn = document.getElementById('submitCreateBtn');
    const codeInput = document.getElementById('kraCode') as HTMLInputElement;
    
    if (this.editingTemplate) {
      if (modalTitle) modalTitle.textContent = 'Edit KRA Template';
      if (submitBtn) submitBtn.textContent = 'Update Template';
      if (codeInput) {
        codeInput.value = this.editingTemplate.kra_code;
      }
      
      (document.getElementById('kraTitle') as HTMLInputElement).value = this.editingTemplate.title || '';
      (document.getElementById('kraDescription') as HTMLTextAreaElement).value = this.editingTemplate.description || '';
      (document.getElementById('kraRole') as HTMLInputElement).value = this.editingTemplate.applicable_to_role || '';
      (document.getElementById('kraDesignation') as HTMLInputElement).value = this.editingTemplate.applicable_to_designation || '';
      (document.getElementById('kraFrequency') as HTMLSelectElement).value = this.editingTemplate.frequency || 'daily';
      (document.getElementById('kraEstTime') as HTMLInputElement).value = this.editingTemplate.estimated_time_minutes?.toString() || '';
      (document.getElementById('kraMandatory') as HTMLInputElement).checked = this.editingTemplate.is_mandatory !== false;
    } else {
      if (modalTitle) modalTitle.textContent = 'Create KRA Template';
      if (submitBtn) submitBtn.textContent = 'Create Template';
      await this.fetchNextKRACode();
      if (codeInput) codeInput.value = this.nextKRACode;
      
      (document.getElementById('kraTitle') as HTMLInputElement).value = '';
      (document.getElementById('kraDescription') as HTMLTextAreaElement).value = '';
      (document.getElementById('kraRole') as HTMLInputElement).value = '';
      (document.getElementById('kraDesignation') as HTMLInputElement).value = '';
      (document.getElementById('kraFrequency') as HTMLSelectElement).value = 'daily';
      (document.getElementById('kraEstTime') as HTMLInputElement).value = '';
      (document.getElementById('kraMandatory') as HTMLInputElement).checked = true;
    }
    
    const modal = document.getElementById('createKRAModal');
    if (modal) modal.style.display = 'flex';
  }
  
  private hideCreateModal(): void {
    const modal = document.getElementById('createKRAModal');
    if (modal) modal.style.display = 'none';
    this.editingTemplate = null;
  }
  
  private async submitTemplate(): Promise<void> {
    const kraCode = (document.getElementById('kraCode') as HTMLInputElement).value;
    const title = (document.getElementById('kraTitle') as HTMLInputElement).value.trim();
    const description = (document.getElementById('kraDescription') as HTMLTextAreaElement).value.trim();
    const role = (document.getElementById('kraRole') as HTMLInputElement).value.trim() || null;
    const designation = (document.getElementById('kraDesignation') as HTMLInputElement).value.trim() || null;
    const frequency = (document.getElementById('kraFrequency') as HTMLSelectElement).value;
    const estTime = parseInt((document.getElementById('kraEstTime') as HTMLInputElement).value) || null;
    const isMandatory = (document.getElementById('kraMandatory') as HTMLInputElement).checked;
    
    if (!title || title.length < 3) {
      alert('Title is required and must be at least 3 characters');
      return;
    }
    
    const submitBtn = document.getElementById('submitCreateBtn') as HTMLButtonElement;
    const originalText = submitBtn?.textContent || '';
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = this.editingTemplate ? 'Updating...' : 'Creating...';
    }
    
    try {
      const payload = {
        kra_code: kraCode,
        title: title,
        description: description || null,
        applicable_to_role: role,
        applicable_to_designation: designation,
        frequency: frequency,
        estimated_time_minutes: estTime,
        is_mandatory: isMandatory
      };
      
      let response;
      if (this.editingTemplate) {
        response = await apiService.put(`/staff/kra/templates/${this.editingTemplate.id}`, payload);
      } else {
        response = await apiService.post('/staff/kra/templates', payload);
      }
      
      if (response.success !== false) {
        alert(this.editingTemplate ? 'KRA Template updated successfully!' : 'KRA Template created successfully!');
        this.hideCreateModal();
        await this.loadTemplates();
      } else {
        alert(response.error || 'Failed to save template');
      }
    } catch (error: any) {
      console.error('[StaffKRATemplatesPage] Save failed:', error);
      alert(error.message || 'Failed to save template');
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
      }
    }
  }
  
  private async showAssignModal(template: KRATemplate): Promise<void> {
    const modalTitle = document.getElementById('assignModalTitle');
    if (modalTitle) modalTitle.textContent = `Assign: ${template.title}`;
    
    this.selectedEmployees = [];
    (document.getElementById('effectiveFrom') as HTMLInputElement).value = new Date().toISOString().split('T')[0];
    (document.getElementById('effectiveUntil') as HTMLInputElement).value = '';
    (document.getElementById('employeeSearch') as HTMLInputElement).value = '';
    
    const modal = document.getElementById('assignModal');
    if (modal) modal.style.display = 'flex';
    modal?.setAttribute('data-template-id', template.id.toString());
    
    await this.loadEmployees();
    this.renderEmployeeList();
  }
  
  private hideAssignModal(): void {
    const modal = document.getElementById('assignModal');
    if (modal) modal.style.display = 'none';
    this.selectedEmployees = [];
  }
  
  private renderEmployeeList(): void {
    const container = document.getElementById('employeeList');
    if (!container) return;
    
    if (this.employees.length === 0) {
      container.innerHTML = '<div class="empty-state" style="padding: 20px; text-align: center; color: #a0aec0;">No employees found</div>';
      return;
    }
    
    container.innerHTML = this.employees.map(emp => `
      <div class="employee-item ${this.selectedEmployees.includes(emp.id) ? 'selected' : ''}" data-emp-id="${emp.id}">
        <input type="checkbox" class="employee-checkbox" ${this.selectedEmployees.includes(emp.id) ? 'checked' : ''}>
        <div class="employee-info">
          <div class="employee-name">${emp.full_name}</div>
          <div class="employee-meta">${emp.emp_code} ${emp.department_name ? '• ' + emp.department_name : ''}</div>
        </div>
      </div>
    `).join('');
    
    container.querySelectorAll('.employee-item').forEach(item => {
      item.addEventListener('click', () => {
        const empId = parseInt((item as HTMLElement).dataset.empId || '0');
        this.toggleEmployee(empId);
      });
    });
    
    this.updateSelectedCount();
  }
  
  private toggleEmployee(empId: number): void {
    const idx = this.selectedEmployees.indexOf(empId);
    if (idx >= 0) {
      this.selectedEmployees.splice(idx, 1);
    } else {
      this.selectedEmployees.push(empId);
    }
    this.renderEmployeeList();
  }
  
  private filterEmployeeList(search: string): void {
    const container = document.getElementById('employeeList');
    if (!container) return;
    
    const searchLower = search.toLowerCase();
    const filtered = this.employees.filter(emp => 
      emp.full_name.toLowerCase().includes(searchLower) || 
      emp.emp_code.toLowerCase().includes(searchLower)
    );
    
    container.innerHTML = filtered.map(emp => `
      <div class="employee-item ${this.selectedEmployees.includes(emp.id) ? 'selected' : ''}" data-emp-id="${emp.id}">
        <input type="checkbox" class="employee-checkbox" ${this.selectedEmployees.includes(emp.id) ? 'checked' : ''}>
        <div class="employee-info">
          <div class="employee-name">${emp.full_name}</div>
          <div class="employee-meta">${emp.emp_code} ${emp.department_name ? '• ' + emp.department_name : ''}</div>
        </div>
      </div>
    `).join('');
    
    container.querySelectorAll('.employee-item').forEach(item => {
      item.addEventListener('click', () => {
        const empId = parseInt((item as HTMLElement).dataset.empId || '0');
        this.toggleEmployee(empId);
      });
    });
  }
  
  private updateSelectedCount(): void {
    const countEl = document.getElementById('selectedCount');
    if (countEl) {
      countEl.textContent = `${this.selectedEmployees.length} employee${this.selectedEmployees.length !== 1 ? 's' : ''} selected`;
    }
  }
  
  private async submitAssignment(): Promise<void> {
    const modal = document.getElementById('assignModal');
    const templateId = parseInt(modal?.getAttribute('data-template-id') || '0');
    const effectiveFrom = (document.getElementById('effectiveFrom') as HTMLInputElement).value;
    const effectiveUntil = (document.getElementById('effectiveUntil') as HTMLInputElement).value || null;
    
    if (!effectiveFrom) {
      alert('Effective From date is required');
      return;
    }
    
    if (this.selectedEmployees.length === 0) {
      alert('Please select at least one employee');
      return;
    }
    
    const submitBtn = document.getElementById('submitAssignBtn') as HTMLButtonElement;
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Assigning...';
    }
    
    try {
      const selectedEmps = this.employees.filter(e => this.selectedEmployees.includes(e.id));
      const empCodes = selectedEmps.map(e => e.emp_code);
      
      const response = await apiService.post(`/staff/kra/templates/${templateId}/assign`, {
        employee_ids: empCodes,
        effective_from: effectiveFrom,
        effective_until: effectiveUntil
      });
      
      if (response.success !== false) {
        alert('KRA assigned successfully!');
        this.hideAssignModal();
        await this.loadTemplates();
      } else {
        alert(response.error || 'Failed to assign KRA');
      }
    } catch (error: any) {
      console.error('[StaffKRATemplatesPage] Assign failed:', error);
      alert(error.message || 'Failed to assign KRA');
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Assign KRA';
      }
    }
  }
  
  private async toggleTemplateStatus(templateId: number, activate: boolean): Promise<void> {
    const action = activate ? 'reactivate' : 'deactivate';
    const confirmMsg = activate ? 'Are you sure you want to reactivate this template?' : 'Are you sure you want to deactivate this template?';
    
    if (!confirm(confirmMsg)) return;
    
    try {
      const endpoint = activate 
        ? `/staff/kra/templates/${templateId}/reactivate`
        : `/staff/kra/templates/${templateId}`;
      
      const response = activate
        ? await apiService.post(endpoint, {})
        : await apiService.delete(endpoint);
      
      if (response.success !== false) {
        alert(`Template ${activate ? 'reactivated' : 'deactivated'} successfully!`);
        await this.loadTemplates();
      } else {
        alert(response.error || `Failed to ${action} template`);
      }
    } catch (error: any) {
      console.error(`[StaffKRATemplatesPage] ${action} failed:`, error);
      alert(error.message || `Failed to ${action} template`);
    }
  }

  private updateList(): void {
    const listContainer = document.getElementById('templatesList');
    const roleFilter = document.getElementById('roleFilter') as HTMLSelectElement;
    
    if (roleFilter && this.roles.length > 0) {
      roleFilter.innerHTML = `
        <option value="">All Roles</option>
        ${this.roles.map(r => `<option value="${r}">${r}</option>`).join('')}
      `;
    }

    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading templates...</div>';
      return;
    }

    if (this.templates.length === 0) {
      listContainer.innerHTML = '<div class="empty-state">No KRA templates found</div>';
      return;
    }

    listContainer.innerHTML = this.templates.map(template => {
      const isActive = template.status !== 'inactive';
      const isExpanded = this.expandedTemplate === template.id;
      
      return `
        <div class="list-card template-card" data-id="${template.id}">
          <div class="template-header" data-toggle="${template.id}">
            <div class="template-info">
              <div class="template-name">${template.title || template.kra_code || 'Untitled'}</div>
              <div class="template-meta">${template.applicable_to_role || 'All'} • ${template.applicable_to_designation || 'All'}</div>
            </div>
            <div class="template-toggle">
              <span class="status-badge ${isActive ? 'active' : 'inactive'}">${isActive ? 'ACTIVE' : 'INACTIVE'}</span>
              <svg class="toggle-icon ${isExpanded ? 'expanded' : ''}" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
            </div>
          </div>
          
          <div class="template-summary">
            <span class="summary-item">${template.frequency || 'daily'}</span>
            <span class="summary-item">${template.assigned_count || 0} assigned</span>
            ${template.is_mandatory ? '<span class="summary-item mandatory">Mandatory</span>' : ''}
          </div>

          <div class="template-details ${isExpanded ? 'expanded' : 'collapsed'}">
            ${template.description ? `<p style="margin-bottom: 12px; font-size: 13px; color: var(--text-secondary, #a0aec0);">${template.description}</p>` : ''}
            
            <div class="template-detail-grid">
              <div class="detail-item"><strong>Code:</strong> ${template.kra_code || '-'}</div>
              <div class="detail-item"><strong>Frequency:</strong> ${template.frequency || 'Daily'}</div>
              <div class="detail-item"><strong>Est. Time:</strong> ${template.estimated_time_minutes || 0} min</div>
              <div class="detail-item"><strong>Approval:</strong> ${template.approval_status || 'pending'}</div>
            </div>
            
            ${template.assigned_employee_names?.length > 0 ? `
              <div class="assigned-employees">
                <strong>Assigned to:</strong> ${template.assigned_employee_names.slice(0, 3).join(', ')}
                ${template.assigned_employee_names.length > 3 ? ` +${template.assigned_employee_names.length - 3} more` : ''}
              </div>
            ` : ''}
            
            ${(this.canAssign || this.canEdit) ? `
              <div class="template-actions">
                ${this.canAssign && isActive ? `
                  <button class="btn btn-sm btn-assign" data-action="assign" data-id="${template.id}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>
                    </svg>
                    Assign
                  </button>
                ` : ''}
                ${this.canEdit ? `
                  <button class="btn btn-sm btn-edit" data-action="edit" data-id="${template.id}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                    Edit
                  </button>
                ` : ''}
                ${this.canEdit ? `
                  ${isActive ? `
                    <button class="btn btn-sm btn-deactivate" data-action="deactivate" data-id="${template.id}">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>
                      </svg>
                      Deactivate
                    </button>
                  ` : `
                    <button class="btn btn-sm btn-reactivate" data-action="reactivate" data-id="${template.id}">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polygon points="5 3 19 12 5 21 5 3"/>
                      </svg>
                      Reactivate
                    </button>
                  `}
                ` : ''}
              </div>
            ` : ''}
          </div>
        </div>
      `;
    }).join('');

    this.container.querySelectorAll('[data-toggle]').forEach(el => {
      el.addEventListener('click', (e) => {
        if ((e.target as HTMLElement).closest('[data-action]')) return;
        const id = parseInt((el as HTMLElement).dataset.toggle || '0');
        this.expandedTemplate = this.expandedTemplate === id ? null : id;
        this.updateList();
      });
    });
    
    this.container.querySelectorAll('[data-action]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const action = (btn as HTMLElement).dataset.action;
        const id = parseInt((btn as HTMLElement).dataset.id || '0');
        const template = this.templates.find(t => t.id === id);
        
        if (!template) return;
        
        if (action === 'assign') {
          this.showAssignModal(template);
        } else if (action === 'edit') {
          this.editingTemplate = template;
          this.showCreateModal();
        } else if (action === 'deactivate') {
          this.toggleTemplateStatus(id, false);
        } else if (action === 'reactivate') {
          this.toggleTemplateStatus(id, true);
        }
      });
    });
  }
}
