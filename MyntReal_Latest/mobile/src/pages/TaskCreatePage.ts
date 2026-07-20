import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';
import { authService } from '../services/auth.service';

interface Employee {
  id: number;
  emp_code: string;
  full_name: string;
  department?: string;
  designation?: string;
}

interface Phase {
  phase_number: number;
  phase_title: string;
  phase_description: string;
  phase_assignee_id: number;
  target_date: string;
}

const PRIORITIES = [
  { id: 'low', name: 'Low' },
  { id: 'medium', name: 'Medium' },
  { id: 'high', name: 'High' },
  { id: 'critical', name: 'Critical' }
];

const CATEGORIES = [
  { id: 'general', name: 'General' },
  { id: 'development', name: 'Development' },
  { id: 'support', name: 'Support' },
  { id: 'admin', name: 'Admin' },
  { id: 'meeting', name: 'Meeting' },
  { id: 'review', name: 'Review' },
  { id: 'documentation', name: 'Documentation' },
  { id: 'other', name: 'Other' }
];

export class TaskCreatePage {
  private container: HTMLElement;
  private employees: Employee[] = [];
  private filteredEmployees: Employee[] = [];
  private selectedSecondary: Employee[] = [];
  private phases: Phase[] = [];
  private phasesEnabled: boolean = false;
  private attachmentFiles: File[] = [];
  private searchQuery: string = '';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadEmployees();
  }

  private async loadEmployees(): Promise<void> {
    try {
      const response = await apiService.get<any>('/staff/tasks/assignable-employees?limit=500');
      const data = response.data as any;
      if (response.success !== false && data) {
        const employeesArray = data.employees || (Array.isArray(data) ? data : []);
        this.employees = employeesArray.map((e: any) => ({
          id: e.id,
          emp_code: e.employee_code || e.emp_code,
          full_name: e.full_name,
          department: e.department,
          designation: e.designation
        }));
        this.filteredEmployees = [...this.employees];
      }
    } catch (error) {
      console.error('[TaskCreatePage] Failed to load employees:', error);
    }
    this.updateEmployeeSelect();
  }

  private render(): void {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const y = tomorrow.getFullYear();
    const m = String(tomorrow.getMonth() + 1).padStart(2, '0');
    const d = String(tomorrow.getDate()).padStart(2, '0');
    const defaultDueDate = `${y}-${m}-${d}T09:00`;

    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Create New Task', showBack: true })}
        
        <div class="form-container">
          <div class="form-section">
            <h4 class="section-title">Task Details</h4>
            
            <div class="form-group">
              <label>Task Title <span class="required">*</span></label>
              <input type="text" id="taskTitle" class="form-input" placeholder="Enter task title" maxlength="200">
              <div class="char-counter"><span id="titleCharCount">0</span>/200</div>
            </div>
            
            <div class="form-group">
              <label>Description</label>
              <textarea id="taskDescription" class="form-textarea" rows="4" placeholder="Detailed task description..." maxlength="2000"></textarea>
              <div class="char-counter"><span id="descCharCount">0</span>/2000</div>
            </div>

            <div class="form-row">
              <div class="form-group half">
                <label>Priority <span class="required">*</span></label>
                <select id="taskPriority" class="form-select">
                  ${PRIORITIES.map(p => `<option value="${p.id}" ${p.id === 'medium' ? 'selected' : ''}>${p.name}</option>`).join('')}
                </select>
              </div>
              <div class="form-group half">
                <label>Category <span class="required">*</span></label>
                <select id="taskCategory" class="form-select">
                  ${CATEGORIES.map(c => `<option value="${c.id}">${c.name}</option>`).join('')}
                </select>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group half">
                <label>Due Date <span class="required">*</span></label>
                <input type="datetime-local" id="taskDueDate" class="form-input" value="${defaultDueDate}">
              </div>
              <div class="form-group half">
                <label>Estimated Hours</label>
                <input type="number" id="taskEstimatedHours" class="form-input" min="0.5" max="999" step="0.5" placeholder="e.g., 4">
              </div>
            </div>
          </div>

          <div class="form-section">
            <h4 class="section-title">Assignment</h4>
            
            <div class="form-group">
              <label>Primary Assignee <span class="required">*</span></label>
              <select id="taskPrimaryAssignee" class="form-select">
                <option value="">Self (Assign to myself)</option>
              </select>
            </div>

            <div class="form-group">
              <label>Secondary Assignees (max 2)</label>
              <div class="secondary-assignees-section">
                <div class="search-input-wrap">
                  <input type="text" id="secondarySearch" class="form-input" placeholder="Search employee by name or ID...">
                </div>
                <div class="employee-search-results" id="employeeSearchResults" style="display: none;"></div>
                <div class="selected-secondary" id="selectedSecondary">
                  <span class="no-selection">No secondary assignees selected</span>
                </div>
              </div>
            </div>
          </div>

          <div class="form-section">
            <h4 class="section-title">Additional Details</h4>

            <div class="form-group">
              <label>Tags (comma separated)</label>
              <input type="text" id="taskTags" class="form-input" placeholder="e.g., urgent, frontend, bug-fix">
            </div>
            
            <div class="form-group">
              <div class="toggle-row" id="phasesToggle">
                <span class="toggle-label">Multi-Stage Task (Add Phases)</span>
                <div class="toggle-switch ${this.phasesEnabled ? 'active' : ''}">
                  <div class="toggle-knob"></div>
                </div>
              </div>
            </div>

            <div id="phasesSection" style="display: ${this.phasesEnabled ? 'block' : 'none'};">
              <div id="phasesList"></div>
              <button class="btn btn-outline" id="addPhaseBtn" type="button">+ Add Phase</button>
            </div>

            <div class="form-group">
              <label>Attachments (Optional)</label>
              <div class="file-hint">Max 2 files. Images up to 5MB (JPEG, PNG, GIF). Documents (PDF, DOC, XLS, PPT, TXT)</div>
              <div class="upload-area" id="uploadArea">
                <input type="file" id="fileInput" multiple accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt" style="display:none;">
                <i class="fas fa-cloud-upload-alt"></i> Tap to select files
              </div>
              <div id="filePreview" class="file-preview-list"></div>
            </div>
          </div>

          <div class="form-actions">
            <button class="btn btn-secondary btn-lg" id="cancelBtn">Cancel</button>
            <button class="btn btn-primary btn-lg" id="createTaskBtn">+ Create Task</button>
          </div>
        </div>
      </div>

      ${this.getStyles()}
    `;

    this.attachListeners();
  }

  private getStyles(): string {
    return `<style>
      .page-container { padding-bottom: 100px; }
      .form-container { padding: 0 16px; }
      .form-section { background: rgba(255,255,255,0.06); border-radius: 12px; padding: 16px; margin-bottom: 16px; }
      .section-title { color: #fff; font-size: 16px; font-weight: 700; margin: 0 0 16px; }
      .form-group { margin-bottom: 16px; }
      .form-group label { display: block; color: rgba(255,255,255,0.85); font-size: 14px; font-weight: 600; margin-bottom: 6px; }
      .required { color: #ef4444; }
      .form-input, .form-textarea, .form-select { width: 100%; padding: 12px 14px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: #fff; font-size: 15px; box-sizing: border-box; }
      .form-input:focus, .form-textarea:focus, .form-select:focus { border-color: #6366f1; outline: none; background: rgba(255,255,255,0.15); }
      .form-select option { background: #1e293b; color: #fff; }
      .form-textarea { resize: vertical; min-height: 80px; font-family: inherit; }
      .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
      .form-group.half { margin-bottom: 16px; }
      .char-counter { text-align: right; font-size: 12px; color: rgba(255,255,255,0.4); margin-top: 4px; }
      .search-input-wrap { position: relative; }
      .employee-search-results { max-height: 200px; overflow-y: auto; background: #1e293b; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; margin-top: 4px; z-index: 10; position: relative; }
      .employee-result { padding: 12px 14px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.08); display: flex; flex-direction: column; gap: 2px; }
      .employee-result:hover { background: rgba(99,102,241,0.2); }
      .employee-result:last-child { border-bottom: none; }
      .emp-name { color: #fff; font-size: 14px; font-weight: 600; }
      .emp-details { color: rgba(255,255,255,0.5); font-size: 12px; }
      .no-results { padding: 12px 14px; color: rgba(255,255,255,0.5); font-size: 13px; text-align: center; }
      .selected-secondary { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
      .no-selection { color: rgba(255,255,255,0.4); font-size: 13px; }
      .selected-emp-chip { display: inline-flex; align-items: center; gap: 8px; background: #4f46e5; color: #fff; padding: 6px 12px; border-radius: 20px; font-size: 13px; font-weight: 500; }
      .remove-chip { background: none; border: none; color: rgba(255,255,255,0.7); font-size: 18px; cursor: pointer; padding: 0 2px; line-height: 1; }
      .toggle-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 0; cursor: pointer; }
      .toggle-label { color: rgba(255,255,255,0.85); font-size: 14px; font-weight: 500; }
      .toggle-switch { width: 44px; height: 24px; background: rgba(255,255,255,0.2); border-radius: 12px; position: relative; transition: background 0.2s; }
      .toggle-switch.active { background: #4f46e5; }
      .toggle-knob { width: 20px; height: 20px; background: #fff; border-radius: 50%; position: absolute; top: 2px; left: 2px; transition: transform 0.2s; }
      .toggle-switch.active .toggle-knob { transform: translateX(20px); }
      .phase-card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.15); border-radius: 10px; padding: 14px; margin-bottom: 12px; position: relative; }
      .phase-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
      .phase-number { color: #8b5cf6; font-weight: 700; font-size: 14px; }
      .phase-remove { background: none; border: none; color: #ef4444; font-size: 16px; cursor: pointer; padding: 4px 8px; }
      .phase-card .form-input, .phase-card .form-select { font-size: 14px; padding: 10px 12px; margin-bottom: 8px; }
      .phase-card .form-group { margin-bottom: 8px; }
      .phase-card label { font-size: 12px; color: rgba(255,255,255,0.6); margin-bottom: 4px; }
      .btn-outline { width: 100%; padding: 12px; background: transparent; border: 2px dashed rgba(255,255,255,0.3); border-radius: 8px; color: rgba(255,255,255,0.7); font-size: 14px; font-weight: 600; cursor: pointer; margin-top: 8px; }
      .btn-outline:hover { border-color: #6366f1; color: #6366f1; }
      .file-hint { font-size: 12px; color: rgba(255,255,255,0.5); margin-bottom: 8px; line-height: 1.4; }
      .upload-area { padding: 20px; border: 2px dashed rgba(255,255,255,0.25); border-radius: 10px; text-align: center; cursor: pointer; color: rgba(255,255,255,0.6); font-size: 14px; transition: all 0.2s; }
      .upload-area:hover { border-color: #6366f1; color: #6366f1; }
      .upload-area i { font-size: 20px; margin-right: 8px; }
      .file-preview-list { margin-top: 8px; }
      .file-preview-item { display: flex; align-items: center; justify-content: space-between; background: rgba(255,255,255,0.05); border-radius: 8px; padding: 10px 12px; margin-bottom: 6px; }
      .file-preview-name { color: #fff; font-size: 13px; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .file-preview-size { color: rgba(255,255,255,0.5); font-size: 12px; margin: 0 12px; }
      .file-preview-remove { background: none; border: none; color: #ef4444; font-size: 16px; cursor: pointer; padding: 2px 6px; }
      .form-actions { display: flex; gap: 12px; padding: 16px 0; }
      .btn { flex: 1; padding: 14px; border-radius: 10px; font-weight: 700; border: none; cursor: pointer; font-size: 15px; text-align: center; }
      .btn-primary { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #fff; }
      .btn-secondary { background: rgba(255,255,255,0.1); color: #fff; }
      .btn-lg { padding: 16px; font-size: 16px; }
      .btn:disabled { opacity: 0.5; cursor: not-allowed; }

    </style>`;
  }

  private attachListeners(): void {
    PageHeader.attachListeners({ title: 'Create New Task', showBack: true });

    document.getElementById('cancelBtn')?.addEventListener('click', () => routerService.goBack());
    document.getElementById('createTaskBtn')?.addEventListener('click', () => this.createTask());

    const titleInput = document.getElementById('taskTitle') as HTMLInputElement;
    titleInput?.addEventListener('input', () => {
      const counter = document.getElementById('titleCharCount');
      if (counter) counter.textContent = String(titleInput.value.length);
    });

    const descInput = document.getElementById('taskDescription') as HTMLTextAreaElement;
    descInput?.addEventListener('input', () => {
      const counter = document.getElementById('descCharCount');
      if (counter) counter.textContent = String(descInput.value.length);
    });

    const searchInput = document.getElementById('secondarySearch') as HTMLInputElement;
    if (searchInput) {
      searchInput.addEventListener('focus', () => this.showSearchResults());
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = (e.target as HTMLInputElement).value.toLowerCase();
        this.filterEmployees();
        this.showSearchResults();
      });
    }

    document.addEventListener('click', (e) => {
      const target = e.target as HTMLElement;
      if (!target.closest('.secondary-assignees-section')) {
        this.hideSearchResults();
      }
    });

    document.getElementById('phasesToggle')?.addEventListener('click', () => {
      this.phasesEnabled = !this.phasesEnabled;
      const toggle = document.querySelector('.toggle-switch');
      const section = document.getElementById('phasesSection');
      if (toggle) toggle.classList.toggle('active', this.phasesEnabled);
      if (section) section.style.display = this.phasesEnabled ? 'block' : 'none';
      if (this.phasesEnabled && this.phases.length === 0) {
        this.addPhase();
      }
    });

    document.getElementById('addPhaseBtn')?.addEventListener('click', () => this.addPhase());

    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput') as HTMLInputElement;
    uploadArea?.addEventListener('click', () => fileInput?.click());
    fileInput?.addEventListener('change', () => this.handleFileSelect(fileInput));
  }

  private updateEmployeeSelect(): void {
    const select = document.getElementById('taskPrimaryAssignee') as HTMLSelectElement;
    if (!select) return;
    select.innerHTML = `
      <option value="">Self (Assign to myself)</option>
      ${this.employees.map(e => `<option value="${e.id}">${e.full_name} (${e.emp_code})</option>`).join('')}
    `;
  }

  private filterEmployees(): void {
    if (!this.searchQuery) {
      this.filteredEmployees = [...this.employees];
    } else {
      this.filteredEmployees = this.employees.filter(e =>
        e.full_name.toLowerCase().includes(this.searchQuery) ||
        e.emp_code.toLowerCase().includes(this.searchQuery) ||
        (e.department || '').toLowerCase().includes(this.searchQuery)
      );
    }
    const selectedIds = this.selectedSecondary.map(s => s.id);
    this.filteredEmployees = this.filteredEmployees.filter(e => !selectedIds.includes(e.id));
  }

  private showSearchResults(): void {
    const resultsContainer = document.getElementById('employeeSearchResults');
    if (!resultsContainer) return;
    this.filterEmployees();
    if (this.filteredEmployees.length === 0) {
      resultsContainer.innerHTML = '<div class="no-results">No matching employees</div>';
    } else {
      resultsContainer.innerHTML = this.filteredEmployees.slice(0, 10).map(e => `
        <div class="employee-result" data-id="${e.id}">
          <span class="emp-name">${e.full_name}</span>
          <span class="emp-details">${e.emp_code} ${e.department ? `\u2022 ${e.department}` : ''}</span>
        </div>
      `).join('');
      resultsContainer.querySelectorAll('.employee-result').forEach(item => {
        item.addEventListener('click', () => {
          const empId = parseInt((item as HTMLElement).dataset.id || '0');
          const emp = this.employees.find(e => e.id === empId);
          if (emp) this.addSecondaryAssignee(emp);
        });
      });
    }
    resultsContainer.style.display = 'block';
  }

  private hideSearchResults(): void {
    const resultsContainer = document.getElementById('employeeSearchResults');
    if (resultsContainer) resultsContainer.style.display = 'none';
  }

  private addSecondaryAssignee(emp: Employee): void {
    if (this.selectedSecondary.length >= 2) {
      alert('Maximum 2 secondary assignees allowed');
      return;
    }
    if (!this.selectedSecondary.find(s => s.id === emp.id)) {
      this.selectedSecondary.push(emp);
      this.updateSelectedSecondary();
    }
    const searchInput = document.getElementById('secondarySearch') as HTMLInputElement;
    if (searchInput) searchInput.value = '';
    this.searchQuery = '';
    this.hideSearchResults();
  }

  private removeSecondaryAssignee(empId: number): void {
    this.selectedSecondary = this.selectedSecondary.filter(s => s.id !== empId);
    this.updateSelectedSecondary();
  }

  private updateSelectedSecondary(): void {
    const container = document.getElementById('selectedSecondary');
    if (!container) return;
    if (this.selectedSecondary.length === 0) {
      container.innerHTML = '<span class="no-selection">No secondary assignees selected</span>';
    } else {
      container.innerHTML = this.selectedSecondary.map(emp => `
        <div class="selected-emp-chip">
          <span>${emp.full_name} (${emp.emp_code})</span>
          <button class="remove-chip" data-id="${emp.id}">&times;</button>
        </div>
      `).join('');
      container.querySelectorAll('.remove-chip').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const id = parseInt((btn as HTMLElement).dataset.id || '0');
          this.removeSecondaryAssignee(id);
        });
      });
    }
  }

  private addPhase(): void {
    if (this.phases.length >= 10) {
      alert('Maximum 10 phases allowed');
      return;
    }
    const phaseNum = this.phases.length + 1;
    this.phases.push({
      phase_number: phaseNum,
      phase_title: '',
      phase_description: '',
      phase_assignee_id: 0,
      target_date: ''
    });
    this.renderPhases();
  }

  private removePhase(index: number): void {
    this.phases.splice(index, 1);
    this.phases.forEach((p, i) => { p.phase_number = i + 1; });
    this.renderPhases();
  }

  private renderPhases(): void {
    const container = document.getElementById('phasesList');
    if (!container) return;
    container.innerHTML = this.phases.map((phase, index) => `
      <div class="phase-card" data-index="${index}">
        <div class="phase-header">
          <span class="phase-number">Phase ${phase.phase_number}</span>
          <button class="phase-remove" data-phase-index="${index}">&times;</button>
        </div>
        <div class="form-group">
          <label>Phase Title <span class="required">*</span></label>
          <input type="text" class="form-input phase-title" data-index="${index}" value="${this.escapeAttr(phase.phase_title)}" placeholder="Phase title" maxlength="256">
        </div>
        <div class="form-group">
          <label>Description</label>
          <input type="text" class="form-input phase-desc" data-index="${index}" value="${this.escapeAttr(phase.phase_description)}" placeholder="Phase description">
        </div>
        <div class="form-group">
          <label>Assignee <span class="required">*</span></label>
          <select class="form-select phase-assignee" data-index="${index}">
            <option value="">Select assignee</option>
            ${this.employees.map(e => `<option value="${e.id}" ${phase.phase_assignee_id === e.id ? 'selected' : ''}>${e.full_name} (${e.emp_code})</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label>Target Date</label>
          <input type="date" class="form-input phase-date" data-index="${index}" value="${phase.target_date}">
        </div>
      </div>
    `).join('');

    container.querySelectorAll('.phase-remove').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const idx = parseInt((btn as HTMLElement).dataset.phaseIndex || '0');
        this.removePhase(idx);
      });
    });

    container.querySelectorAll('.phase-title').forEach(input => {
      input.addEventListener('input', (e) => {
        const idx = parseInt((e.target as HTMLElement).dataset.index || '0');
        this.phases[idx].phase_title = (e.target as HTMLInputElement).value;
      });
    });

    container.querySelectorAll('.phase-desc').forEach(input => {
      input.addEventListener('input', (e) => {
        const idx = parseInt((e.target as HTMLElement).dataset.index || '0');
        this.phases[idx].phase_description = (e.target as HTMLInputElement).value;
      });
    });

    container.querySelectorAll('.phase-assignee').forEach(select => {
      select.addEventListener('change', (e) => {
        const idx = parseInt((e.target as HTMLElement).dataset.index || '0');
        this.phases[idx].phase_assignee_id = parseInt((e.target as HTMLSelectElement).value || '0');
      });
    });

    container.querySelectorAll('.phase-date').forEach(input => {
      input.addEventListener('change', (e) => {
        const idx = parseInt((e.target as HTMLElement).dataset.index || '0');
        this.phases[idx].target_date = (e.target as HTMLInputElement).value;
      });
    });
  }

  private handleFileSelect(input: HTMLInputElement): void {
    const files = input.files;
    if (!files) return;
    for (let i = 0; i < files.length; i++) {
      if (this.attachmentFiles.length >= 2) {
        alert('Maximum 2 files allowed');
        break;
      }
      if (files[i].size > 5 * 1024 * 1024) {
        alert(`${files[i].name} exceeds 5MB limit`);
        continue;
      }
      this.attachmentFiles.push(files[i]);
    }
    input.value = '';
    this.renderFilePreview();
  }

  private removeFile(index: number): void {
    this.attachmentFiles.splice(index, 1);
    this.renderFilePreview();
  }

  private renderFilePreview(): void {
    const container = document.getElementById('filePreview');
    if (!container) return;
    if (this.attachmentFiles.length === 0) {
      container.innerHTML = '';
      return;
    }
    container.innerHTML = this.attachmentFiles.map((file, index) => `
      <div class="file-preview-item">
        <span class="file-preview-name">${this.escapeHtml(file.name)}</span>
        <span class="file-preview-size">${(file.size / 1024).toFixed(0)} KB</span>
        <button class="file-preview-remove" data-file-index="${index}">&times;</button>
      </div>
    `).join('');
    container.querySelectorAll('.file-preview-remove').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const idx = parseInt((btn as HTMLElement).dataset.fileIndex || '0');
        this.removeFile(idx);
      });
    });
  }

  private async createTask(): Promise<void> {
    const title = (document.getElementById('taskTitle') as HTMLInputElement)?.value?.trim();
    const description = (document.getElementById('taskDescription') as HTMLTextAreaElement)?.value?.trim();
    const priority = (document.getElementById('taskPriority') as HTMLSelectElement)?.value;
    const category = (document.getElementById('taskCategory') as HTMLSelectElement)?.value;
    const primaryAssigneeId = (document.getElementById('taskPrimaryAssignee') as HTMLSelectElement)?.value;
    const dueDate = (document.getElementById('taskDueDate') as HTMLInputElement)?.value;
    const estimatedHours = (document.getElementById('taskEstimatedHours') as HTMLInputElement)?.value;
    const tagsRaw = (document.getElementById('taskTags') as HTMLInputElement)?.value?.trim();

    if (!title || title.length < 3) {
      alert('Please enter a task title (minimum 3 characters)');
      return;
    }
    if (!dueDate) {
      alert('Please select a due date');
      return;
    }

    if (this.phasesEnabled && this.phases.length > 0) {
      for (const phase of this.phases) {
        if (!phase.phase_title || phase.phase_title.length < 3) {
          alert(`Phase ${phase.phase_number}: Title is required (min 3 characters)`);
          return;
        }
        if (!phase.phase_assignee_id) {
          alert(`Phase ${phase.phase_number}: Please select an assignee`);
          return;
        }
      }
    }

    const btn = document.getElementById('createTaskBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Creating...'; }

    try {
      let resolvedAssigneeId: number;
      if (primaryAssigneeId) {
        resolvedAssigneeId = parseInt(primaryAssigneeId);
      } else {
        const currentUser = authService.getAuthState().user;
        if (!currentUser?.id) {
          alert('Unable to determine your employee ID. Please log in again.');
          return;
        }
        resolvedAssigneeId = currentUser.id;
      }

      const payload: any = {
        title,
        description: description || '',
        priority: priority || 'medium',
        category: category || 'general',
        due_date: dueDate,
        primary_assignee_id: resolvedAssigneeId
      };

      if (this.selectedSecondary.length > 0) {
        payload.secondary_assignee_ids = this.selectedSecondary.map(s => s.id);
      }

      if (estimatedHours) {
        payload.estimated_hours = parseFloat(estimatedHours);
      }

      if (tagsRaw) {
        payload.tags = tagsRaw.split(',').map((t: string) => t.trim()).filter((t: string) => t.length > 0);
      }

      if (this.phasesEnabled && this.phases.length > 0) {
        payload.phases = this.phases.map(p => ({
          phase_number: p.phase_number,
          phase_title: p.phase_title,
          phase_description: p.phase_description || null,
          phase_assignee_id: p.phase_assignee_id,
          target_date: p.target_date || null
        }));
      }

      console.log('[TaskCreatePage] Creating task with payload:', payload);
      const response = await apiService.post('/staff/tasks', payload);

      if (response.success) {
        const taskId = (response.data as any)?.task?.id || (response.data as any)?.id;

        if (taskId && this.attachmentFiles.length > 0) {
          for (const file of this.attachmentFiles) {
            try {
              const formData = new FormData();
              formData.append('file', file);
              await fetch(`/api/v1/staff/tasks/${taskId}/attachments`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('staff_token')}` },
                body: formData
              });
            } catch (err) {
              console.error('[TaskCreatePage] Attachment upload failed:', err);
            }
          }
        }

        alert('Task created successfully!');
        routerService.navigate('tasks');
      } else {
        alert((response as any).error || 'Failed to create task');
      }
    } catch (error: any) {
      console.error('[TaskCreatePage] Create error:', error);
      alert(error.message || 'Failed to create task');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = '+ Create Task'; }
    }
  }

  private escapeHtml(str: string): string {
    if (!str) return '';
    return str.replace(/[&<>"']/g, (m) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[m] || m);
  }

  private escapeAttr(str: string): string {
    if (!str) return '';
    return str.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
}
