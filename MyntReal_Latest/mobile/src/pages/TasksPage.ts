/**
 * Tasks Page - Full Workflow
 * DC Protocol: DC_MOBILE_TASKS_001
 * View Tasks + Create Task + Mark Complete
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';

interface AssignedBy {
  id: number;
  emp_code: string;
  full_name: string;
}

interface Task {
  id: number;
  title: string;
  description: string;
  priority: string;
  status: string;
  assigned_by: AssignedBy | string;
  assigned_date: string;
  due_date: string;
  start_date?: string | null;
  completed_date: string | null;
  completed_at?: string | null;
  category?: string;
  progress?: number;
  estimated_hours?: number | null;
  actual_hours?: number | null;
  completion_notes?: string | null;
  contact_phone?: string | null;
  contact_person_name?: string | null;
  phases?: TaskPhase[];
  comments?: TaskComment[];
  primary_assignee_id?: number | null;
}

interface TaskPhase {
  id: number;
  phase_number: number;
  title: string;
  description?: string;
  status: string;
  target_date?: string | null;
  completed_at?: string | null;
  assignee_name?: string;
  phase_assignee_id?: number;
  child_task_id?: number | null;
  contact_phone?: string | null;
  contact_person_name?: string | null;
  secondary_assignees?: Array<{ employee_name?: string; full_name?: string }>;
}

interface TaskComment {
  id: number;
  comment: string;
  employee_name: string;
  created_at: string;
}

interface Employee {
  id: number;
  emp_code: string;
  full_name: string;
}

const PRIORITIES = [
  { id: 'low', name: 'Low', color: '#10b981' },
  { id: 'medium', name: 'Medium', color: '#f59e0b' },
  { id: 'high', name: 'High', color: '#ef4444' },
  { id: 'urgent', name: 'Urgent', color: '#dc2626' }
];

// DC Protocol: Categories must match backend enum values exactly
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

export class TasksPage {
  private container: HTMLElement;
  private tasks: Task[] = [];
  private employees: Employee[] = [];
  private loading: boolean = true;
  private loadError: string | null = null;
  private filter: 'all' | 'pending' | 'in_progress' | 'completed' = 'all';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await Promise.all([
      this.loadTasks(),
      this.loadEmployees()
    ]);
  }

  private async loadTasks(): Promise<void> {
    this.loading = true;
    this.loadError = null;
    this.updateContent();

    try {
      const params = new URLSearchParams();
      
      if (this.filter !== 'all') {
        params.append('status', this.filter);
      }
      
      const queryString = params.toString();
      const endpoint = `/staff/tasks/assigned-to-me${queryString ? '?' + queryString : ''}`;
      
      const response = await apiService.get<any>(endpoint);
      console.log('[TasksPage] API response:', response);

      const data = response.data as any;
      if (response.success !== false && data) {
        if (data.tasks) {
          this.tasks = data.tasks;
        } else if (Array.isArray(data)) {
          this.tasks = data;
        } else {
          this.tasks = [];
        }
        this.loadError = null;
        console.log('[TasksPage] Loaded tasks:', this.tasks.length);
      } else {
        this.tasks = [];
        this.loadError = response.error || 'Failed to load tasks. Please try again.';
      }
    } catch (error: any) {
      console.error('[TasksPage] Failed to load:', error);
      this.tasks = [];
      this.loadError = error?.message || 'Network error. Please check your connection and try again.';
    }

    this.loading = false;
    this.updateContent();
  }

  private async loadEmployees(): Promise<void> {
    try {
      const response = await apiService.get<any>('/staff/tasks/assignable-employees');
      console.log('[TasksPage] Employees response:', response);
      
      // DC Protocol: Handle multiple response formats
      const data = response.data as any;
      if (response.success !== false && data) {
        const employeesArray = data.employees || (Array.isArray(data) ? data : []);
        this.employees = employeesArray.map((e: any) => ({
          id: e.id,
          emp_code: e.employee_code || e.emp_code,
          full_name: e.full_name
        }));
        console.log('[TasksPage] Loaded employees:', this.employees.length);
      } else {
        this.employees = [];
      }
    } catch (error) {
      console.error('[TasksPage] Failed to load employees:', error);
      this.employees = [];
    }
    this.updateEmployeeSelect();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'My Tasks', showBack: true })}
        
        <button class="fab-btn" id="addTaskBtn">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </button>
        
        <!-- Stats Cards - Web Parity (scoped class) -->
        <div class="tasks-stats" id="taskStats">
          <div class="stat-card">
            <div class="stat-icon blue">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 11l3 3L22 4"/>
                <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
              </svg>
            </div>
            <div class="stat-info">
              <div class="stat-value" id="statTotal">0</div>
              <div class="stat-label">Total</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon green">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
            </div>
            <div class="stat-info">
              <div class="stat-value" id="statCompleted">0</div>
              <div class="stat-label">Done</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon yellow">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
            </div>
            <div class="stat-info">
              <div class="stat-value" id="statInProgress">0</div>
              <div class="stat-label">Active</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon red">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
            </div>
            <div class="stat-info">
              <div class="stat-value" id="statOverdue">0</div>
              <div class="stat-label">Overdue</div>
            </div>
          </div>
        </div>
        
        <div class="filter-tabs">
          <button class="filter-tab ${this.filter === 'all' ? 'active' : ''}" data-filter="all">All</button>
          <button class="filter-tab ${this.filter === 'pending' ? 'active' : ''}" data-filter="pending">Pending</button>
          <button class="filter-tab ${this.filter === 'in_progress' ? 'active' : ''}" data-filter="in_progress">In Progress</button>
          <button class="filter-tab ${this.filter === 'completed' ? 'active' : ''}" data-filter="completed">Completed</button>
        </div>

        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>

      <!-- Create Task Modal -->
      <div class="modal-overlay" id="createTaskModal" style="display: none;">
        <div class="modal-content modal-lg">
          <div class="modal-header">
            <h4>Create New Task</h4>
            <button class="modal-close" id="closeCreateModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Title <span class="required">*</span></label>
              <input type="text" id="taskTitle" class="form-input" placeholder="Enter task title">
            </div>
            
            <div class="form-group">
              <label>Description</label>
              <textarea id="taskDescription" class="form-textarea" rows="3" placeholder="Task description"></textarea>
            </div>

            <div class="form-row">
              <div class="form-group half">
                <label>Priority</label>
                <select id="taskPriority" class="form-select">
                  ${PRIORITIES.map(p => `<option value="${p.id}">${p.name}</option>`).join('')}
                </select>
              </div>
              <div class="form-group half">
                <label>Category</label>
                <select id="taskCategory" class="form-select">
                  ${CATEGORIES.map(c => `<option value="${c.id}">${c.name}</option>`).join('')}
                </select>
              </div>
            </div>

            <div class="form-group">
              <label>Assign To</label>
              <select id="taskAssignee" class="form-select">
                <option value="">Self (Assign to myself)</option>
              </select>
            </div>

            <div class="form-group">
              <label>Due Date</label>
              <input type="date" id="taskDueDate" class="form-input">
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelCreateBtn">Cancel</button>
            <button class="btn btn-primary" id="confirmCreateBtn">Create Task</button>
          </div>
        </div>
      </div>

      <!-- Task Detail Modal -->
      <div class="modal-overlay" id="taskDetailModal" style="display: none;">
        <div class="modal-content modal-lg">
          <div class="modal-header">
            <h4>Task Details</h4>
            <button class="modal-close" id="closeDetailModal">&times;</button>
          </div>
          <div class="modal-body" id="taskDetailContent"></div>
          <div class="modal-footer" id="taskDetailActions"></div>
        </div>
      </div>

      <!-- Update Phase Status Modal -->
      <div class="modal-overlay action-modal" id="phaseStatusModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Update Sub-Task Status</h4>
            <button class="modal-close" id="closePhaseModal">&times;</button>
          </div>
          <div class="modal-body">
            <p class="phase-title-display" id="phaseModalTitle"></p>
            <div class="form-group">
              <label>Status <span class="required">*</span></label>
              <select id="phaseNewStatus" class="form-select">
                <option value="pending">Pending</option>
                <option value="in_progress">In Progress</option>
                <option value="on_hold">On Hold</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
            <div class="form-group" id="phaseNotesGroup" style="display: none;">
              <label>Completion Notes</label>
              <textarea id="phaseCompletionNotes" class="form-textarea" rows="2" placeholder="Add notes..."></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelPhaseBtn">Cancel</button>
            <button class="btn btn-primary" id="savePhaseBtn">Update Status</button>
          </div>
        </div>
      </div>
    `;

    this.attachListeners();
  }

  private attachListeners(): void {
    PageHeader.attachListeners({ title: 'My Tasks', showBack: true });

    // Add Task FAB button
    document.getElementById('addTaskBtn')?.addEventListener('click', () => this.showCreateModal());

    // Filter tabs - DC Protocol: reload from server (matches web behavior)
    this.container.querySelectorAll('.filter-tab').forEach(btn => {
      btn.addEventListener('click', () => {
        this.filter = btn.getAttribute('data-filter') as any;
        this.container.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.loadTasks(); // Reload from server with filter param (web parity)
      });
    });

    // Create modal controls
    document.getElementById('closeCreateModal')?.addEventListener('click', () => this.hideCreateModal());
    document.getElementById('cancelCreateBtn')?.addEventListener('click', () => this.hideCreateModal());
    document.getElementById('confirmCreateBtn')?.addEventListener('click', () => this.createTask());

    // Detail modal
    document.getElementById('closeDetailModal')?.addEventListener('click', () => this.hideDetailModal());

    // Phase status modal
    document.getElementById('closePhaseModal')?.addEventListener('click', () => { document.getElementById('phaseStatusModal')!.style.display = 'none'; });
    document.getElementById('cancelPhaseBtn')?.addEventListener('click', () => { document.getElementById('phaseStatusModal')!.style.display = 'none'; });
    document.getElementById('savePhaseBtn')?.addEventListener('click', () => this.savePhaseStatus());
    document.getElementById('phaseNewStatus')?.addEventListener('change', (e) => {
      const val = (e.target as HTMLSelectElement).value;
      document.getElementById('phaseNotesGroup')!.style.display = val === 'completed' ? 'block' : 'none';
    });
  }

  private updateEmployeeSelect(): void {
    const select = document.getElementById('taskAssignee') as HTMLSelectElement;
    if (!select) return;

    select.innerHTML = `
      <option value="">Self (Assign to myself)</option>
      ${this.employees.map(e => `<option value="${e.id}">${e.full_name} (${e.emp_code})</option>`).join('')}
    `;
  }

  private updateStats(): void {
    const total = this.tasks.length;
    const completed = this.tasks.filter(t => t.status?.toLowerCase() === 'completed').length;
    const inProgress = this.tasks.filter(t => t.status?.toLowerCase() === 'in_progress' || t.status?.toLowerCase() === 'in progress').length;
    const overdue = this.tasks.filter(t => 
      t.status?.toLowerCase() !== 'completed' && this.isOverdue(t.due_date)
    ).length;

    const statTotal = document.getElementById('statTotal');
    const statCompleted = document.getElementById('statCompleted');
    const statInProgress = document.getElementById('statInProgress');
    const statOverdue = document.getElementById('statOverdue');

    if (statTotal) statTotal.textContent = String(total);
    if (statCompleted) statCompleted.textContent = String(completed);
    if (statInProgress) statInProgress.textContent = String(inProgress);
    if (statOverdue) statOverdue.textContent = String(overdue);
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    if (this.loadError) {
      content.innerHTML = `
        <div class="error-state" style="text-align:center;padding:40px 20px;">
          <i class="fas fa-exclamation-triangle" style="font-size:36px;color:#f59e0b;margin-bottom:12px;"></i>
          <p style="color:#fff;margin:0 0 8px;font-weight:500;">Unable to Load Tasks</p>
          <p style="color:rgba(255,255,255,0.5);font-size:13px;margin:0 0 16px;">${this.loadError}</p>
          <button id="retryLoadBtn" style="background:#6366f1;color:#fff;border:none;padding:10px 24px;border-radius:8px;font-size:14px;cursor:pointer;">Retry</button>
        </div>`;
      document.getElementById('retryLoadBtn')?.addEventListener('click', () => this.loadTasks());
      return;
    }

    this.updateStats();

    let filteredTasks = this.tasks;
    if (this.filter === 'pending') {
      filteredTasks = this.tasks.filter(t => t.status?.toLowerCase() === 'pending');
    } else if (this.filter === 'in_progress') {
      filteredTasks = this.tasks.filter(t => t.status?.toLowerCase() === 'in_progress' || t.status?.toLowerCase() === 'in progress');
    } else if (this.filter === 'completed') {
      filteredTasks = this.tasks.filter(t => t.status?.toLowerCase() === 'completed');
    }

    if (filteredTasks.length === 0) {
      content.innerHTML = '<div class="empty-state">No tasks found</div>';
      return;
    }

    content.innerHTML = `
      <div class="list-container">
        ${filteredTasks.map(task => `
          <div class="list-item card task-card" data-task-id="${task.id}">
            <div class="item-header">
              <span class="priority-badge ${task.priority?.toLowerCase()}">${task.priority || 'Medium'}</span>
              <span class="status-badge ${this.getStatusClass(task.status)}">${task.status || 'Pending'}</span>
            </div>
            <h4 class="task-title">${task.title}</h4>
            <p class="task-description">${task.description || ''}</p>
            <div class="task-meta">
              <span class="assigned-by">From: ${this.getAssignedByName(task.assigned_by)}</span>
              <span class="due-date ${this.isOverdue(task.due_date) ? 'overdue' : ''}">
                Due: ${this.formatDate(task.due_date)}
              </span>
            </div>
            ${task.status?.toLowerCase() !== 'completed' ? `
              <div class="task-actions">
                <button class="btn btn-sm btn-primary mark-complete-btn" data-task-id="${task.id}">
                  Mark Complete
                </button>
                <button class="btn btn-sm btn-secondary view-task-btn" data-task-id="${task.id}">
                  View
                </button>
              </div>
            ` : `
              <div class="task-actions">
                <button class="btn btn-sm btn-secondary view-task-btn" data-task-id="${task.id}">
                  View Details
                </button>
              </div>
            `}
          </div>
        `).join('')}
      </div>
    `;

    // Attach task action listeners
    content.querySelectorAll('.mark-complete-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const taskId = btn.getAttribute('data-task-id');
        await this.markComplete(parseInt(taskId!));
      });
    });

    content.querySelectorAll('.view-task-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const taskId = btn.getAttribute('data-task-id');
        routerService.navigate('task-detail', { id: taskId! });
      });
    });
  }

  private getAssignedByName(assignedBy: AssignedBy | string | null | undefined): string {
    if (!assignedBy) return 'Admin';
    if (typeof assignedBy === 'string') return assignedBy;
    if (typeof assignedBy === 'object') {
      return assignedBy.full_name || assignedBy.emp_code || 'Admin';
    }
    return 'Admin';
  }

  private getStatusClass(status: string): string {
    const s = status?.toLowerCase().replace(' ', '-') || 'pending';
    return s;
  }

  private showCreateModal(): void {
    const modal = document.getElementById('createTaskModal');
    if (modal) modal.style.display = 'flex';
    
    // Set default due date to tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const dueDateInput = document.getElementById('taskDueDate') as HTMLInputElement;
    if (dueDateInput) {
      dueDateInput.value = tomorrow.toISOString().split('T')[0];
    }
  }

  private hideCreateModal(): void {
    const modal = document.getElementById('createTaskModal');
    if (modal) modal.style.display = 'none';
  }

  private async createTask(): Promise<void> {
    const title = (document.getElementById('taskTitle') as HTMLInputElement)?.value?.trim();
    const description = (document.getElementById('taskDescription') as HTMLTextAreaElement)?.value?.trim();
    const priority = (document.getElementById('taskPriority') as HTMLSelectElement)?.value;
    const category = (document.getElementById('taskCategory') as HTMLSelectElement)?.value;
    const assigneeId = (document.getElementById('taskAssignee') as HTMLSelectElement)?.value;
    const dueDate = (document.getElementById('taskDueDate') as HTMLInputElement)?.value;

    if (!title) {
      alert('Please enter a task title');
      return;
    }

    try {
      const payload: any = {
        title,
        description,
        priority,
        category,
        due_date: dueDate
      };

      if (assigneeId) {
        payload.primary_assignee_id = parseInt(assigneeId);
      }

      const response = await apiService.post('/staff/tasks', payload);

      if (response.success) {
        this.hideCreateModal();
        await this.loadTasks();
        alert('Task created successfully!');
      } else {
        alert(response.error || 'Failed to create task');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to create task');
    }
  }

  private currentDetailTaskId: number | null = null;

  private async showTaskDetail(taskId: number): Promise<void> {
    this.currentDetailTaskId = taskId;
    const modal = document.getElementById('taskDetailModal');
    const content = document.getElementById('taskDetailContent');
    const actions = document.getElementById('taskDetailActions');
    if (!modal || !content || !actions) return;

    content.innerHTML = '<div class="loading-state">Loading task details...</div>';
    actions.innerHTML = '';
    modal.style.display = 'flex';

    let task: Task | null = null;
    try {
      const resp = await apiService.get(`/staff/tasks/${taskId}?include_attachments=true`);
      task = (resp.data as any)?.task || resp.data as any;
    } catch (e) {
      task = this.tasks.find(t => t.id === taskId) || null;
    }
    if (!task) {
      content.innerHTML = '<p>Failed to load task details.</p>';
      return;
    }

    const canEdit = task.status !== 'completed' && task.status !== 'cancelled';
    const phases = task.phases || [];
    const comments = task.comments || [];
    const completedCount = phases.filter(p => p.status === 'completed').length;

    content.innerHTML = `
      <div class="task-detail-enhanced">
        <h4 class="task-detail-title">${task.title}</h4>
        <div class="badge-row">
          <span class="status-badge ${this.getStatusClass(task.status)}">${this.formatStatus(task.status)}</span>
          <span class="priority-badge ${task.priority?.toLowerCase()}">${task.priority}</span>
          ${task.category ? `<span class="category-badge">${task.category}</span>` : ''}
        </div>

        <div class="detail-grid">
          <div class="detail-row">
            <span class="detail-label">Assigned By</span>
            <span class="detail-value">${this.getAssignedByName(task.assigned_by)}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Due Date</span>
            <span class="detail-value ${this.isOverdue(task.due_date) && canEdit ? 'overdue' : ''}">${this.formatDate(task.due_date)}</span>
          </div>
          ${task.start_date ? `
            <div class="detail-row">
              <span class="detail-label">Start Date</span>
              <span class="detail-value">${this.formatDate(task.start_date)}</span>
            </div>
          ` : ''}
          ${task.completed_date || task.completed_at ? `
            <div class="detail-row">
              <span class="detail-label">Completed</span>
              <span class="detail-value">${this.formatDate(task.completed_date || task.completed_at || '')}</span>
            </div>
          ` : ''}
          ${task.contact_phone ? `
            <div class="detail-row">
              <span class="detail-label">Contact</span>
              <span class="detail-value"><a href="tel:${task.contact_phone}" class="contact-link">${task.contact_phone}</a>${task.contact_person_name ? ` (${task.contact_person_name})` : ''}</span>
            </div>
          ` : ''}
        </div>

        <div class="detail-description card">
          <strong>Description</strong>
          <p>${task.description || 'No description'}</p>
        </div>

        <div class="time-info-row">
          <span>Time Logged: <strong>${task.actual_hours || 0}h</strong></span>
          <span>Estimated: <strong>${task.estimated_hours || 'N/A'}h</strong></span>
        </div>

        ${canEdit ? `
          <div class="progress-section card">
            <label><strong>Progress: <span id="progressVal">${task.progress || 0}</span>%</strong></label>
            <input type="range" class="progress-slider-mobile" id="taskProgressSlider" min="0" max="100" step="5" value="${task.progress || 0}">
          </div>

          <div class="status-update-section card">
            <label><strong>Update Status</strong></label>
            <select id="taskStatusSelect" class="form-select">
              <option value="pending" ${task.status === 'pending' ? 'selected' : ''}>Pending</option>
              <option value="in_progress" ${task.status === 'in_progress' ? 'selected' : ''}>In Progress</option>
              <option value="on_hold" ${task.status === 'on_hold' ? 'selected' : ''}>On Hold</option>
              <option value="completed" ${task.status === 'completed' ? 'selected' : ''}>Completed</option>
            </select>
          </div>
        ` : ''}

        <div class="phases-section card">
          <div class="section-header-row">
            <strong>Sub-Tasks (${phases.length})${phases.length > 0 ? ` — ${completedCount}/${phases.length} done` : ''}</strong>
          </div>
          ${phases.length === 0 ? '<p class="empty-hint">No sub-tasks yet</p>' : `
            <div class="phase-timeline-mobile">
              ${phases.map((phase, idx) => `
                <div class="phase-item-mobile phase-${phase.status}">
                  <div class="phase-connector-line ${idx === phases.length - 1 ? 'last' : ''}"></div>
                  <div class="phase-dot phase-dot-${phase.status}"></div>
                  <div class="phase-content-mobile">
                    <div class="phase-header-mobile">
                      <span class="phase-title-mobile">${phase.title}</span>
                      <span class="status-badge sm ${this.getStatusClass(phase.status)}">${this.formatStatus(phase.status)}</span>
                    </div>
                    <div class="phase-meta-mobile">
                      <span>${phase.assignee_name || 'Unassigned'}</span>
                      ${phase.target_date ? `<span class="phase-target-date">Target: ${this.formatDate(phase.target_date)}</span>` : ''}
                      ${phase.completed_at ? `<span class="phase-completed-date">Done: ${this.formatDate(phase.completed_at)}</span>` : ''}
                    </div>
                    ${phase.description ? `<p class="phase-desc">${phase.description}</p>` : ''}
                    ${canEdit ? `<button class="btn btn-sm btn-outline phase-update-btn" data-task-id="${taskId}" data-phase-id="${phase.id}" data-phase-title="${phase.title}" data-phase-status="${phase.status}">Update</button>` : ''}
                  </div>
                </div>
              `).join('')}
            </div>
          `}
        </div>

        <div class="comments-section-mobile card">
          <strong>Comments (${comments.length})</strong>
          ${comments.length === 0 ? '<p class="empty-hint">No comments yet</p>' : `
            <div class="comments-list">
              ${comments.map(c => `
                <div class="comment-item-mobile">
                  <div class="comment-header">
                    <span class="comment-author">${c.employee_name || 'Unknown'}</span>
                    <span class="comment-time">${this.formatDate(c.created_at)}</span>
                  </div>
                  ${c.comment ? `<p class="comment-text">${c.comment}</p>` : ''}
                </div>
              `).join('')}
            </div>
          `}
          ${canEdit ? `
            <div class="add-comment-row">
              <textarea id="newCommentText" class="form-textarea" rows="2" placeholder="Add a comment..."></textarea>
              <button class="btn btn-sm btn-primary" id="postCommentBtn">Post</button>
            </div>
          ` : ''}
        </div>
      </div>
    `;

    if (canEdit) {
      actions.innerHTML = `
        <button class="btn btn-secondary" onclick="document.getElementById('taskDetailModal').style.display='none'">Close</button>
        <button class="btn btn-primary" id="saveProgressBtn">Save Changes</button>
      `;
      document.getElementById('taskProgressSlider')?.addEventListener('input', (e) => {
        const val = (e.target as HTMLInputElement).value;
        const display = document.getElementById('progressVal');
        if (display) display.textContent = val;
      });
      document.getElementById('saveProgressBtn')?.addEventListener('click', () => this.saveTaskProgress(taskId));
      document.getElementById('postCommentBtn')?.addEventListener('click', () => this.postComment(taskId));

      document.querySelectorAll('.phase-update-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const tId = parseInt(btn.getAttribute('data-task-id') || '0');
          const pId = parseInt(btn.getAttribute('data-phase-id') || '0');
          const pTitle = btn.getAttribute('data-phase-title') || '';
          const pStatus = btn.getAttribute('data-phase-status') || 'pending';
          this.showPhaseStatusModal(tId, pId, pTitle, pStatus);
        });
      });
    } else {
      actions.innerHTML = `
        <button class="btn btn-secondary" onclick="document.getElementById('taskDetailModal').style.display='none'">Close</button>
      `;
    }
  }

  private hideDetailModal(): void {
    const modal = document.getElementById('taskDetailModal');
    if (modal) modal.style.display = 'none';
  }

  private async markComplete(taskId: number): Promise<void> {
    try {
      const response = await apiService.put(`/staff/tasks/${taskId}`, { progress: 100, status: 'completed' });
      if (response.success !== false) {
        await this.loadTasks();
        alert('Task marked as complete!');
      } else {
        alert(response.error || 'Failed to update task');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to update task');
    }
  }

  private async saveTaskProgress(taskId: number): Promise<void> {
    const progress = parseInt((document.getElementById('taskProgressSlider') as HTMLInputElement)?.value || '0');
    const status = (document.getElementById('taskStatusSelect') as HTMLSelectElement)?.value || undefined;

    const btn = document.getElementById('saveProgressBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Saving...'; }

    try {
      const response = await apiService.put(`/staff/tasks/${taskId}`, { progress, status });
      if (response.success !== false) {
        await this.loadTasks();
        await this.showTaskDetail(taskId);
        alert('Progress updated!');
      } else {
        alert(response.error || 'Failed to update progress');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to update progress');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Save Changes'; }
    }
  }

  private async postComment(taskId: number): Promise<void> {
    const text = (document.getElementById('newCommentText') as HTMLTextAreaElement)?.value?.trim();
    if (!text) {
      alert('Please enter a comment');
      return;
    }

    const btn = document.getElementById('postCommentBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Posting...'; }

    try {
      const formData = new FormData();
      formData.append('content', text);
      const response = await apiService.postFormData(`/staff/tasks/${taskId}/comments`, formData);
      if (response.success !== false) {
        await this.showTaskDetail(taskId);
      } else {
        alert(response.error || 'Failed to post comment');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to post comment');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Post'; }
    }
  }

  private showPhaseStatusModal(taskId: number, phaseId: number, phaseTitle: string, currentStatus: string): void {
    (document.getElementById('phaseModalTitle') as HTMLElement).textContent = phaseTitle;
    (document.getElementById('phaseNewStatus') as HTMLSelectElement).value = currentStatus;
    (document.getElementById('phaseCompletionNotes') as HTMLTextAreaElement).value = '';
    document.getElementById('phaseNotesGroup')!.style.display = currentStatus === 'completed' ? 'block' : 'none';

    (document.getElementById('phaseStatusModal') as HTMLElement).setAttribute('data-task-id', String(taskId));
    (document.getElementById('phaseStatusModal') as HTMLElement).setAttribute('data-phase-id', String(phaseId));
    document.getElementById('phaseStatusModal')!.style.display = 'flex';
  }

  private async savePhaseStatus(): Promise<void> {
    const modal = document.getElementById('phaseStatusModal')!;
    const taskId = parseInt(modal.getAttribute('data-task-id') || '0');
    const phaseId = parseInt(modal.getAttribute('data-phase-id') || '0');
    const newStatus = (document.getElementById('phaseNewStatus') as HTMLSelectElement).value;
    const notes = (document.getElementById('phaseCompletionNotes') as HTMLTextAreaElement).value.trim();

    if (!taskId || !phaseId) return;

    const btn = document.getElementById('savePhaseBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Updating...'; }

    const payload: any = { phase_status: newStatus };
    if (notes) payload.completion_notes = notes;

    try {
      const response = await apiService.patch(`/staff/tasks/${taskId}/phases/${phaseId}`, payload);
      if (response.success !== false) {
        modal.style.display = 'none';
        await this.loadTasks();
        await this.showTaskDetail(taskId);
        alert('Sub-task status updated!');
      } else {
        alert(response.error || 'Failed to update sub-task');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to update sub-task');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Update Status'; }
    }
  }

  private formatStatus(status: string): string {
    if (!status) return '';
    return status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  private isOverdue(dateStr: string): boolean {
    if (!dateStr) return false;
    return new Date(dateStr) < new Date();
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'Not set';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
  }
}
