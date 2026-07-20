import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';

interface Task {
  id: number;
  title: string;
  description: string;
  primary_assignee_name?: string;
  primary_assignee?: { id: number; full_name: string; emp_code: string };
  secondary_assignees_count?: number;
  priority: string;
  status: string;
  due_date: string;
  created_at: string;
  completed_at?: string;
  progress: number;
  category: string;
  attachments?: { count: number; files?: any[] };
  comments?: any[];
}

interface Summary {
  total: number;
  pending: number;
  in_progress: number;
  completed: number;
  overdue: number;
}

const DATE_FILTERS = [
  { id: 'all', label: 'All Tasks' },
  { id: '7', label: 'Last 7 Days' },
  { id: '30', label: 'Last 30 Days' },
  { id: '90', label: 'Last 90 Days' }
];

const STATUS_OPTIONS = [
  { id: '', label: 'All Status' },
  { id: 'pending', label: 'Pending' },
  { id: 'in_progress', label: 'In Progress' },
  { id: 'completed', label: 'Completed' },
  { id: 'cancelled', label: 'Cancelled' },
  { id: 'on_hold', label: 'On Hold' }
];

const PRIORITY_OPTIONS = [
  { id: '', label: 'All Priority' },
  { id: 'low', label: 'Low' },
  { id: 'medium', label: 'Medium' },
  { id: 'high', label: 'High' },
  { id: 'critical', label: 'Critical' }
];

export class TasksAssignedPage {
  private container: HTMLElement;
  private tasks: Task[] = [];
  private summary: Summary = { total: 0, pending: 0, in_progress: 0, completed: 0, overdue: 0 };
  private loading: boolean = true;
  private loadError: string | null = null;
  private expandedTaskId: number | null = null;

  private dateFilter: string = 'all';
  private statusFilter: string = '';
  private priorityFilter: string = '';
  private categoryFilter: string = '';
  private searchQuery: string = '';
  private statusCardFilter: string = '';

  private categories: Array<{id: number; name: string}> = [];
  private pendingTimers: ReturnType<typeof setTimeout>[] = [];

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadCategories();
    await this.loadTasks();
  }

  private async loadCategories(): Promise<void> {
    try {
      const response = await apiService.get<any>('/staff/tasks/categories');
      if (response.success && response.data) {
        this.categories = response.data.categories || response.data || [];
        this.updateCategoryFilter();
      }
    } catch (error) {
      console.error('[TasksAssigned] Failed to load categories:', error);
    }
  }

  private updateCategoryFilter(): void {
    const select = document.getElementById('categoryFilter') as HTMLSelectElement;
    if (select) {
      select.innerHTML = `<option value="">All Categories</option>` +
        this.categories.map(c => `<option value="${c.name}">${c.name}</option>`).join('');
    }
  }

  private async loadTasks(): Promise<void> {
    this.loading = true;
    this.loadError = null;
    this.updateTaskList();

    try {
      const params = new URLSearchParams();
      if (this.dateFilter !== 'all') {
        const days = parseInt(this.dateFilter);
        const dateFrom = new Date();
        dateFrom.setDate(dateFrom.getDate() - days);
        params.append('start_date', dateFrom.toISOString().split('T')[0]);
      }
      if (this.statusFilter) params.append('status', this.statusFilter);
      if (this.priorityFilter) params.append('priority', this.priorityFilter);
      if (this.categoryFilter) params.append('category', this.categoryFilter);

      const response = await apiService.get<any>(`/staff/tasks/assigned-by-me?${params.toString()}`);

      if (response.success !== false && response.data) {
        this.tasks = response.data.tasks || [];
        this.summary = response.data.summary || this.calculateSummary();
        this.loadError = null;
      } else {
        this.tasks = [];
        this.loadError = response.error || 'Failed to load tasks. Please try again.';
      }
    } catch (error: any) {
      console.error('[TasksAssigned] Failed to load:', error);
      this.tasks = [];
      this.loadError = error?.message || 'Network error. Please check your connection and try again.';
    }

    this.loading = false;
    this.updateStats();
    this.updateTaskList();
  }

  private calculateSummary(): Summary {
    const today = new Date().toISOString().split('T')[0];
    return {
      total: this.tasks.length,
      pending: this.tasks.filter(t => t.status === 'pending').length,
      in_progress: this.tasks.filter(t => t.status === 'in_progress').length,
      completed: this.tasks.filter(t => t.status === 'completed').length,
      overdue: this.tasks.filter(t => t.due_date && t.due_date < today && t.status !== 'completed').length
    };
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container tasks-page">
        ${PageHeader.render({ title: 'Assigned By Me', showBack: true })}
        
        <div class="create-task-bar">
          <button id="createTaskBtn" class="btn btn-primary"><i class="fas fa-plus"></i> Create New Task</button>
        </div>
        
        <div class="stats-scroll">
          <div class="stat-card ${this.statusCardFilter === '' ? 'active' : ''}" data-status="">
            <div class="stat-icon total"><i class="fas fa-tasks"></i></div>
            <div class="stat-value" id="statTotal">0</div>
            <div class="stat-label">Total</div>
          </div>
          <div class="stat-card ${this.statusCardFilter === 'pending' ? 'active' : ''}" data-status="pending">
            <div class="stat-icon pending"><i class="fas fa-clock"></i></div>
            <div class="stat-value" id="statPending">0</div>
            <div class="stat-label">Pending</div>
          </div>
          <div class="stat-card ${this.statusCardFilter === 'in_progress' ? 'active' : ''}" data-status="in_progress">
            <div class="stat-icon in-progress"><i class="fas fa-spinner"></i></div>
            <div class="stat-value" id="statInProgress">0</div>
            <div class="stat-label">In Progress</div>
          </div>
          <div class="stat-card ${this.statusCardFilter === 'completed' ? 'active' : ''}" data-status="completed">
            <div class="stat-icon completed"><i class="fas fa-check-circle"></i></div>
            <div class="stat-value" id="statCompleted">0</div>
            <div class="stat-label">Completed</div>
          </div>
          <div class="stat-card ${this.statusCardFilter === 'overdue' ? 'active' : ''}" data-status="overdue">
            <div class="stat-icon overdue"><i class="fas fa-exclamation-triangle"></i></div>
            <div class="stat-value" id="statOverdue">0</div>
            <div class="stat-label">Overdue</div>
          </div>
        </div>

        <div class="filters-section card">
          <div class="filter-row">
            <div class="filter-item">
              <label>Date Range</label>
              <select id="dateFilter" class="form-select">
                ${DATE_FILTERS.map(d => `<option value="${d.id}" ${this.dateFilter === d.id ? 'selected' : ''}>${d.label}</option>`).join('')}
              </select>
            </div>
            <div class="filter-item">
              <label>Status</label>
              <select id="statusFilter" class="form-select">
                ${STATUS_OPTIONS.map(s => `<option value="${s.id}" ${this.statusFilter === s.id ? 'selected' : ''}>${s.label}</option>`).join('')}
              </select>
            </div>
          </div>
          <div class="filter-row">
            <div class="filter-item">
              <label>Priority</label>
              <select id="priorityFilter" class="form-select">
                ${PRIORITY_OPTIONS.map(p => `<option value="${p.id}" ${this.priorityFilter === p.id ? 'selected' : ''}>${p.label}</option>`).join('')}
              </select>
            </div>
            <div class="filter-item">
              <label>Category</label>
              <select id="categoryFilter" class="form-select"><option value="">All Categories</option></select>
            </div>
          </div>
          <div class="filter-row">
            <div class="filter-item full-width">
              <label>Search</label>
              <input type="text" id="searchInput" class="form-input" placeholder="Search tasks..." value="${this.searchQuery}">
            </div>
          </div>
          <div class="filter-actions">
            <button id="applyFiltersBtn" class="btn btn-primary">Apply</button>
            <button id="resetFiltersBtn" class="btn btn-secondary">Reset</button>
          </div>
        </div>

        <div class="tasks-list" id="tasksList"><div class="loading-state">Loading tasks...</div></div>
      </div>

      ${this.getStyles()}
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private getStyles(): string {
    return `<style>
      .tasks-page { padding-bottom: 80px; }
      .create-task-bar { padding: 12px 16px; }
      .create-task-bar .btn { width: 100%; display: flex; align-items: center; justify-content: center; gap: 8px; }
      .stats-scroll { display: flex; gap: 12px; overflow-x: auto; padding: 0 16px 16px; -webkit-overflow-scrolling: touch; }
      .stats-scroll::-webkit-scrollbar { display: none; }
      .stat-card { min-width: 90px; background: rgba(255,255,255,0.1); border-radius: 12px; padding: 12px; text-align: center; cursor: pointer; border: 2px solid transparent; }
      .stat-card.active { border-color: #4f46e5; background: rgba(79,70,229,0.2); }
      .stat-icon { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; margin: 0 auto 6px; font-size: 14px; }
      .stat-icon.total { background: #e0e7ff; color: #4338ca; }
      .stat-icon.pending { background: #fef3c7; color: #d97706; }
      .stat-icon.in-progress { background: #dbeafe; color: #2563eb; }
      .stat-icon.completed { background: #d1fae5; color: #059669; }
      .stat-icon.overdue { background: #fee2e2; color: #dc2626; }
      .stat-value { font-size: 18px; font-weight: 700; color: #fff; }
      .stat-label { font-size: 10px; color: rgba(255,255,255,0.7); }
      .filters-section { margin: 0 16px 16px; padding: 16px; background: rgba(255,255,255,0.05); border-radius: 12px; }
      .filter-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
      .filter-item.full-width { grid-column: 1 / -1; }
      .filter-item label { display: block; font-size: 11px; color: rgba(255,255,255,0.6); margin-bottom: 4px; text-transform: uppercase; }
      .form-select, .form-input { width: 100%; padding: 10px 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: #fff; font-size: 14px; }
      .form-select option { background: #1e293b; color: #fff; }
      .filter-actions { display: flex; gap: 12px; margin-top: 8px; }
      .btn { flex: 1; padding: 12px; border-radius: 8px; font-weight: 600; border: none; cursor: pointer; }
      .btn-primary { background: #4f46e5; color: #fff; }
      .btn-secondary { background: rgba(255,255,255,0.1); color: #fff; }
      .btn-success { background: #059669; color: #fff; }
      .btn-danger { background: #dc2626; color: #fff; }
      .tasks-list { padding: 0 16px; }
      .task-card-container { margin-bottom: 12px; }
      .task-card { background: rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; cursor: pointer; transition: all 0.2s; }
      .task-card:hover { background: rgba(255,255,255,0.12); }
      .task-card.expanded { border-radius: 12px 12px 0 0; background: rgba(79,70,229,0.2); border: 1px solid #4f46e5; border-bottom: none; }
      .task-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
      .task-title { font-weight: 700; color: #fff; font-size: 16px; flex: 1; }
      .task-id { font-size: 12px; color: #94a3b8; }
      .expand-icon { color: rgba(255,255,255,0.5); transition: transform 0.3s; }
      .expand-icon.rotated { transform: rotate(180deg); }
      .task-meta { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
      .badge { padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 600; }
      .badge-pending { background: #fef3c7; color: #92400e; }
      .badge-in_progress { background: #dbeafe; color: #1e40af; }
      .badge-completed { background: #dcfce7; color: #166534; }
      .badge-cancelled { background: #f3f4f6; color: #6b7280; }
      .badge-on_hold { background: #fce7f3; color: #9d174d; }
      .badge-low { background: #d1fae5; color: #065f46; }
      .badge-medium { background: #fef3c7; color: #92400e; }
      .badge-high { background: #fee2e2; color: #991b1b; }
      .badge-critical { background: #dc2626; color: white; }
      .badge-category { background: #e0e7ff; color: #4338ca; }
      .task-summary { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
      .task-summary-item { display: flex; flex-direction: column; }
      .task-summary-label { font-size: 11px; color: rgba(255,255,255,0.7); text-transform: uppercase; }
      .task-summary-value { font-size: 14px; color: #fff; font-weight: 500; }
      .progress-bar { height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden; margin-top: 12px; }
      .progress-fill { height: 100%; background: linear-gradient(90deg, #4f46e5, #8b5cf6); transition: width 0.3s; }
      .due-date { font-size: 14px; }
      .due-date.overdue { color: #dc2626; font-weight: 600; }
      .due-date.today { color: #d97706; font-weight: 600; }
      .due-date.upcoming { color: #059669; }
      .loading-state, .empty-state { text-align: center; padding: 40px; color: rgba(255,255,255,0.5); }
      .task-inline-detail { display: none; background: rgba(30,41,59,0.98); border: 1px solid #4f46e5; border-top: none; border-radius: 0 0 12px 12px; padding: 16px; animation: slideDown 0.3s ease; }
      .task-inline-detail.show { display: block; }
      @keyframes slideDown { from { opacity: 0; } to { opacity: 1; } }
      .detail-section { margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.1); }
      .detail-section:last-child { border-bottom: none; margin-bottom: 0; }
      .detail-section-title { font-size: 13px; font-weight: 600; color: #fff; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
      .detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
      .detail-item { display: flex; flex-direction: column; }
      .detail-label { font-size: 11px; color: rgba(255,255,255,0.5); text-transform: uppercase; margin-bottom: 4px; }
      .detail-value { font-size: 14px; color: #fff; }
      .detail-description { font-size: 14px; color: rgba(255,255,255,0.8); line-height: 1.5; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px; }
      .progress-control { padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px; }
      .progress-label { display: flex; justify-content: space-between; margin-bottom: 8px; color: rgba(255,255,255,0.7); font-size: 13px; }
      .progress-slider { width: 100%; height: 8px; border-radius: 4px; background: #e5e7eb; appearance: none; cursor: pointer; }
      .progress-slider::-webkit-slider-thumb { appearance: none; width: 20px; height: 20px; border-radius: 50%; background: #4f46e5; cursor: pointer; }
      .status-control { margin-top: 12px; }
      .status-control label { display: block; color: rgba(255,255,255,0.7); font-size: 12px; margin-bottom: 6px; }
      .attachment-list { display: flex; flex-direction: column; gap: 8px; }
      .attachment-item { display: flex; align-items: center; justify-content: space-between; background: rgba(255,255,255,0.05); border-radius: 8px; padding: 10px 12px; }
      .attachment-info { display: flex; align-items: center; gap: 10px; flex: 1; }
      .attachment-icon { width: 32px; height: 32px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 14px; background: #dbeafe; color: #2563eb; }
      .attachment-name { font-size: 13px; color: #fff; }
      .attachment-btn { padding: 6px 10px; font-size: 12px; background: #4f46e5; color: #fff; border: none; border-radius: 6px; cursor: pointer; }
      .upload-area { margin-top: 12px; padding: 16px; border: 2px dashed rgba(255,255,255,0.2); border-radius: 8px; text-align: center; cursor: pointer; color: rgba(255,255,255,0.6); }
      .upload-area:hover { border-color: #4f46e5; color: #4f46e5; }
      .upload-area input { display: none; }
      .comment-list { display: flex; flex-direction: column; gap: 8px; max-height: 200px; overflow-y: auto; }
      .comment-item { background: rgba(255,255,255,0.05); border-radius: 8px; padding: 12px; }
      .comment-header { display: flex; justify-content: space-between; margin-bottom: 6px; }
      .comment-author { font-weight: 600; color: #fff; font-size: 13px; }
      .comment-time { color: rgba(255,255,255,0.5); font-size: 11px; }
      .comment-text { color: rgba(255,255,255,0.8); font-size: 13px; }
      .add-comment { margin-top: 12px; }
      .add-comment textarea { width: 100%; padding: 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: #fff; font-size: 14px; resize: vertical; min-height: 60px; }
      .add-comment .btn { margin-top: 8px; width: 100%; }
      .inline-footer { display: flex; gap: 8px; margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.1); }
      .inline-footer .btn { flex: 1; }
      .form-group { margin-bottom: 16px; }
      .form-group label { display: block; color: rgba(255,255,255,0.8); font-size: 13px; margin-bottom: 6px; }
      .form-group .required { color: #dc2626; }
      .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

    </style>`;
  }

  private updateStats(): void {
    const setVal = (id: string, val: number) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val.toString();
    };
    setVal('statTotal', this.summary.total);
    setVal('statPending', this.summary.pending);
    setVal('statInProgress', this.summary.in_progress);
    setVal('statCompleted', this.summary.completed);
    setVal('statOverdue', this.summary.overdue);
  }

  private updateTaskList(): void {
    const container = document.getElementById('tasksList');
    if (!container) return;

    if (this.loading) {
      container.innerHTML = '<div class="loading-state"><i class="fas fa-spinner fa-spin"></i> Loading tasks...</div>';
      return;
    }

    if (this.loadError) {
      container.innerHTML = `
        <div class="error-state" style="text-align:center;padding:40px 20px;">
          <i class="fas fa-exclamation-triangle" style="font-size:36px;color:#f59e0b;margin-bottom:12px;"></i>
          <p style="color:#fff;margin:0 0 8px;font-weight:500;">Unable to Load Tasks</p>
          <p style="color:rgba(255,255,255,0.5);font-size:13px;margin:0 0 16px;">${this.loadError}</p>
          <button id="retryLoadBtn" style="background:#6366f1;color:#fff;border:none;padding:10px 24px;border-radius:8px;font-size:14px;cursor:pointer;">Retry</button>
        </div>`;
      document.getElementById('retryLoadBtn')?.addEventListener('click', () => this.loadTasks());
      return;
    }

    let filteredTasks = [...this.tasks];
    
    if (this.statusCardFilter === 'overdue') {
      const today = new Date().toISOString().split('T')[0];
      filteredTasks = filteredTasks.filter(t => t.due_date && t.due_date < today && t.status !== 'completed');
    } else if (this.statusCardFilter) {
      filteredTasks = filteredTasks.filter(t => t.status === this.statusCardFilter);
    }
    
    if (this.searchQuery) {
      const query = this.searchQuery.toLowerCase();
      filteredTasks = filteredTasks.filter(t =>
        t.title?.toLowerCase().includes(query) ||
        t.description?.toLowerCase().includes(query) ||
        t.id?.toString().includes(query) ||
        t.primary_assignee_name?.toLowerCase().includes(query)
      );
    }

    if (filteredTasks.length === 0) {
      container.innerHTML = '<div class="empty-state"><i class="fas fa-inbox"></i><p>No tasks found</p></div>';
      return;
    }

    container.innerHTML = filteredTasks.map(task => this.renderTaskCard(task)).join('');
    this.attachTaskCardListeners();
  }

  private renderTaskCard(task: Task): string {
    const dueDateClass = this.getDueDateClass(task.due_date, task.status);
    const assignedTo = task.primary_assignee_name || task.primary_assignee?.full_name || 'N/A';
    const secondaryCount = task.secondary_assignees_count || (task as any).secondary_assignees?.length || 0;
    const assignedToDisplay = secondaryCount > 0 ? `${assignedTo} +${secondaryCount}` : assignedTo;
    const attachmentCount = (task as any).attachment_count || task.attachments?.count || (Array.isArray(task.attachments) ? task.attachments.length : 0);
    const isExpanded = this.expandedTaskId === task.id;

    return `
      <div class="task-card-container" data-task-id="${task.id}">
        <div class="task-card ${isExpanded ? 'expanded' : ''}" data-task-id="${task.id}">
          <div class="task-header">
            <div>
              <div class="task-title">${this.escapeHtml(task.title)}</div>
              <div class="task-id">#${task.id}</div>
            </div>
            <i class="fas fa-chevron-down expand-icon ${isExpanded ? 'rotated' : ''}"></i>
          </div>
          <div class="task-meta">
            <span class="badge badge-${task.status}">${this.formatStatus(task.status)}</span>
            <span class="badge badge-${task.priority}">${this.capitalize(task.priority || 'medium')}</span>
            ${task.category ? `<span class="badge badge-category">${task.category}</span>` : ''}
            ${attachmentCount > 0 ? `<span class="badge" style="background:#e0e7ff;color:#4338ca;"><i class="fas fa-paperclip"></i> ${attachmentCount}</span>` : ''}
          </div>
          <div class="task-summary">
            <div class="task-summary-item">
              <span class="task-summary-label">Assigned To</span>
              <span class="task-summary-value">${assignedToDisplay}</span>
            </div>
            <div class="task-summary-item">
              <span class="task-summary-label">Due Date</span>
              <span class="task-summary-value due-date ${dueDateClass}">${this.formatDate(task.due_date)}</span>
            </div>
            <div class="task-summary-item">
              <span class="task-summary-label">Assigned Date</span>
              <span class="task-summary-value">${this.formatDate(task.created_at)}</span>
            </div>
            <div class="task-summary-item">
              <span class="task-summary-label">Progress</span>
              <span class="task-summary-value">${task.progress || 0}%</span>
            </div>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" style="width: ${task.progress || 0}%"></div>
          </div>
        </div>
        
        <div class="task-inline-detail ${isExpanded ? 'show' : ''}" id="detail-${task.id}">
          <div class="detail-section">
            <div class="detail-section-title"><i class="fas fa-info-circle"></i> Task Details</div>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="detail-label">Created</span>
                <span class="detail-value">${this.formatDate(task.created_at)}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Progress</span>
                <span class="detail-value">${task.progress || 0}%</span>
              </div>
            </div>
            ${task.description ? `<div style="margin-top: 12px;"><span class="detail-label">Description</span><div class="detail-description">${this.escapeHtml(task.description)}</div></div>` : ''}
          </div>
          
          <div class="detail-section">
            <div class="detail-section-title"><i class="fas fa-edit"></i> Edit Task</div>
            <div class="status-control">
              <label>Status</label>
              <select id="statusSelect-${task.id}" class="form-select">
                ${STATUS_OPTIONS.filter(s => s.id).map(s => `<option value="${s.id}" ${task.status === s.id ? 'selected' : ''}>${s.label}</option>`).join('')}
              </select>
            </div>
            <div class="status-control">
              <label>Priority</label>
              <select id="prioritySelect-${task.id}" class="form-select">
                ${PRIORITY_OPTIONS.filter(p => p.id).map(p => `<option value="${p.id}" ${task.priority === p.id ? 'selected' : ''}>${p.label}</option>`).join('')}
              </select>
            </div>
          </div>
          
          <div class="detail-section">
            <div class="detail-section-title"><i class="fas fa-paperclip"></i> Attachments</div>
            <div class="attachment-list" id="attachments-${task.id}"><p style="color: rgba(255,255,255,0.5); text-align: center; font-size: 13px;">Loading...</p></div>
            <div class="upload-area" onclick="document.getElementById('fileInput-${task.id}').click()">
              <input type="file" id="fileInput-${task.id}" data-task-id="${task.id}">
              <i class="fas fa-cloud-upload-alt"></i> Upload File (Max 5MB)
            </div>
          </div>
          
          <div class="detail-section">
            <div class="detail-section-title"><i class="fas fa-comments"></i> Comments</div>
            <div class="comment-list" id="comments-${task.id}"><p style="color: rgba(255,255,255,0.5); text-align: center; font-size: 13px;">Loading...</p></div>
            <div class="add-comment">
              <textarea id="commentInput-${task.id}" placeholder="Add a comment..."></textarea>
              <button class="btn btn-primary" data-action="comment" data-id="${task.id}"><i class="fas fa-paper-plane"></i> Add Comment</button>
            </div>
          </div>
          
          <div class="inline-footer">
            <button class="btn btn-secondary" data-action="collapse" data-id="${task.id}">Close</button>
            <button class="btn btn-primary" data-action="save" data-id="${task.id}">Save Changes</button>
            <button class="btn" data-action="wa" data-id="${task.id}" data-title="${this.escapeHtml(task.title)}" data-due="${task.due_date || ''}" data-status="${task.status || ''}" data-phone="${(task as any).contact_phone || ''}" style="background:#25D366;color:#fff;border:none;padding:8px 14px;border-radius:6px;font-size:13px;cursor:pointer;">💬 WA</button>
          </div>
        </div>
      </div>
    `;
  }

  private sendWaForTask(title: string, due: string, status: string, phone: string): void {
    const msg = `📋 *Task Update*\n\nTask: ${title}\nDue: ${due || 'N/A'}\nStatus: ${status.replace(/_/g,' ')}\n\nPlease review and take action.`;
    let ph = (phone || '').replace(/\D/g, '');
    if (!ph || ph.length < 10) {
      ph = (window.prompt('WhatsApp number (e.g. 919876543210):', '91') || '').replace(/\D/g, '');
    }
    if (!ph || ph.length < 10) return;
    window.open('https://wa.me/' + ph + '?text=' + encodeURIComponent(msg), '_blank');
  }

  private attachEventListeners(): void {
    document.getElementById('createTaskBtn')?.addEventListener('click', () => routerService.navigate('task-create'));
    
    document.querySelectorAll('.stat-card').forEach(card => {
      card.addEventListener('click', () => {
        const status = card.getAttribute('data-status') || '';
        this.statusCardFilter = status;
        document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        this.expandedTaskId = null;
        this.updateTaskList();
      });
    });

    document.getElementById('dateFilter')?.addEventListener('change', (e) => { this.dateFilter = (e.target as HTMLSelectElement).value; });
    document.getElementById('statusFilter')?.addEventListener('change', (e) => { this.statusFilter = (e.target as HTMLSelectElement).value; });
    document.getElementById('priorityFilter')?.addEventListener('change', (e) => { this.priorityFilter = (e.target as HTMLSelectElement).value; });
    document.getElementById('categoryFilter')?.addEventListener('change', (e) => { this.categoryFilter = (e.target as HTMLSelectElement).value; });
    document.getElementById('searchInput')?.addEventListener('input', (e) => { this.searchQuery = (e.target as HTMLInputElement).value; });

    document.getElementById('applyFiltersBtn')?.addEventListener('click', () => { this.expandedTaskId = null; this.loadTasks(); });
    document.getElementById('resetFiltersBtn')?.addEventListener('click', () => {
      this.dateFilter = 'all'; this.statusFilter = ''; this.priorityFilter = ''; this.categoryFilter = ''; this.searchQuery = ''; this.statusCardFilter = ''; this.expandedTaskId = null;
      this.render(); this.updateCategoryFilter(); this.loadTasks();
    });
  }

  private attachTaskCardListeners(): void {
    document.querySelectorAll('.task-card').forEach(card => {
      card.addEventListener('click', async (e) => {
        const target = e.target as HTMLElement;
        if (target.closest('select') || target.closest('input') || target.closest('button') || target.closest('textarea')) return;
        const taskId = parseInt(card.getAttribute('data-task-id') || '0');
        await this.toggleTaskDetail(taskId);
      });
    });

    document.querySelectorAll('[data-action]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const action = btn.getAttribute('data-action');
        const taskId = parseInt(btn.getAttribute('data-id') || '0');
        switch (action) {
          case 'save': await this.saveTaskChanges(taskId); break;
          case 'collapse': this.collapseTask(taskId); break;
          case 'comment': await this.addComment(taskId); break;
          case 'wa': {
            const title = btn.getAttribute('data-title') || '';
            const due = btn.getAttribute('data-due') || '';
            const status = btn.getAttribute('data-status') || '';
            const phone = btn.getAttribute('data-phone') || '';
            this.sendWaForTask(title, due, status, phone);
            break;
          }
        }
      });
    });

    document.querySelectorAll('input[type="file"]').forEach(input => {
      input.addEventListener('change', (e) => {
        const taskId = parseInt((e.target as HTMLInputElement).getAttribute('data-task-id') || '0');
        this.uploadAttachment(taskId, e);
      });
    });
  }

  private async toggleTaskDetail(taskId: number): Promise<void> {
    if (this.expandedTaskId === taskId) {
      this.collapseTask(taskId);
    } else {
      if (this.expandedTaskId) this.collapseTask(this.expandedTaskId);
      this.expandedTaskId = taskId;
      this.updateTaskList();
      await this.loadTaskDetails(taskId);
    }
  }

  private collapseTask(taskId: number): void {
    this.expandedTaskId = null;
    this.updateTaskList();
  }

  private async loadTaskDetails(taskId: number): Promise<void> {
    try {
      const response = await apiService.get<any>(`/staff/tasks/${taskId}?include_attachments=true&include_comments=true`);
      if (response.success !== false && response.data) {
        const task = response.data.task || response.data;
        this.renderAttachments(taskId, task.attachments?.files || []);
        this.renderComments(taskId, task.comments || []);
      }
    } catch (error) {
      console.error('[TasksAssigned] Failed to load task details:', error);
    }
  }

  private renderAttachments(taskId: number, attachments: any[]): void {
    const container = document.getElementById(`attachments-${taskId}`);
    if (!container) return;
    if (attachments.length === 0) {
      container.innerHTML = '<p style="color: rgba(255,255,255,0.5); text-align: center; font-size: 13px;">No attachments</p>';
      return;
    }
    container.innerHTML = attachments.map(att => `
      <div class="attachment-item">
        <div class="attachment-info">
          <div class="attachment-icon"><i class="fas fa-file"></i></div>
          <span class="attachment-name">${att.filename || att.file_name || 'File'}</span>
        </div>
        <button class="attachment-btn" onclick="window.open('/api/v1/staff/tasks/attachments/${att.id}/download', '_blank')"><i class="fas fa-download"></i></button>
      </div>
    `).join('');
  }

  private renderComments(taskId: number, comments: any[]): void {
    const container = document.getElementById(`comments-${taskId}`);
    if (!container) return;
    if (comments.length === 0) {
      container.innerHTML = '<p style="color: rgba(255,255,255,0.5); text-align: center; font-size: 13px;">No comments yet</p>';
      return;
    }
    container.innerHTML = comments.map(comment => `
      <div class="comment-item">
        <div class="comment-header">
          <span class="comment-author">${comment.author_name || 'Unknown'}</span>
          <span class="comment-time">${this.formatDateTime(comment.created_at)}</span>
        </div>
        <div class="comment-text">${this.escapeHtml(comment.content || comment.text || '')}</div>
      </div>
    `).join('');
  }

  private async saveTaskChanges(taskId: number): Promise<void> {
    const statusSelect = document.getElementById(`statusSelect-${taskId}`) as HTMLSelectElement;
    const prioritySelect = document.getElementById(`prioritySelect-${taskId}`) as HTMLSelectElement;
    try {
      const response = await apiService.put<any>(`/staff/tasks/${taskId}`, { status: statusSelect?.value, priority: prioritySelect?.value });
      if (response.success !== false) { alert('Task updated successfully!'); await this.loadTasks(); }
      else { alert('Failed to update task'); }
    } catch (error) { alert('Error updating task'); }
  }

  private async addComment(taskId: number): Promise<void> {
    const textarea = document.getElementById(`commentInput-${taskId}`) as HTMLTextAreaElement;
    const content = textarea?.value?.trim();
    if (!content) { alert('Please enter a comment'); return; }
    try {
      const formData = new FormData();
      formData.append('content', content);
      const response = await apiService.postFormData<any>(`/staff/tasks/${taskId}/comments`, formData);
      if (response.success !== false) { textarea.value = ''; await this.loadTaskDetails(taskId); }
    } catch (error) { alert('Error adding comment'); }
  }

  private async uploadAttachment(taskId: number, e: Event): Promise<void> {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { alert('File size exceeds 5MB limit'); return; }
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch(`/api/v1/staff/tasks/${taskId}/attachments`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('staff_token')}` },
        body: formData
      });
      if (response.ok) { alert('File uploaded successfully!'); input.value = ''; await this.loadTaskDetails(taskId); }
      else { alert('Failed to upload file'); }
    } catch (error) { alert('Error uploading file'); }
  }

  private getDueDateClass(dueDate: string, status: string): string {
    if (!dueDate || status === 'completed') return '';
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const due = new Date(dueDate); due.setHours(0, 0, 0, 0);
    if (due < today) return 'overdue';
    if (due.getTime() === today.getTime()) return 'today';
    return 'upcoming';
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  private formatDateTime(dateStr: string): string {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  }

  private formatStatus(status: string): string {
    const statusMap: Record<string, string> = { 'pending': 'Pending', 'in_progress': 'In Progress', 'completed': 'Completed', 'cancelled': 'Cancelled', 'on_hold': 'On Hold' };
    return statusMap[status] || status;
  }

  private capitalize(str: string): string { return str.charAt(0).toUpperCase() + str.slice(1); }

  private escapeHtml(str: string): string {
    if (!str) return '';
    return str.replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m] || m);
  }

  cleanup(): void {
    this.pendingTimers.forEach(t => clearTimeout(t));
    this.pendingTimers = [];
  }
}
