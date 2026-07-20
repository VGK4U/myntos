/**
 * Staff Team Activities Page
 * DC Protocol: DC_MOBILE_TEAM_ACTIVITIES_002
 * Full web parity - View and manage all team tasks with filters and edit functionality
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface Task {
  id: number;
  title: string;
  description: string;
  status: string;
  priority: string;
  category: string;
  due_date: string;
  assigned_date: string;
  created_at: string;
  progress: number;
  primary_assignee_name: string;
  primary_assignee?: { full_name: string; emp_code: string };
  secondary_assignees_count: number;
  creator_name: string;
  creator_code: string;
  assigned_by?: { full_name: string; emp_code: string };
  viewer_role: string;
  attachments?: { count: number };
}

interface Summary {
  total: number;
  pending: number;
  in_progress: number;
  completed: number;
  overdue: number;
}

interface Department {
  id: number;
  name: string;
}

interface Category {
  id: number;
  name: string;
}

interface Employee {
  id: number;
  full_name: string;
  emp_code: string;
}

const DATE_RANGES = [
  { id: '7', label: 'Last 7 Days' },
  { id: '30', label: 'Last 30 Days' },
  { id: '90', label: 'Last 90 Days' },
  { id: 'all', label: 'All Time' }
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

export class StaffTeamActivitiesPage {
  private container: HTMLElement;
  private tasks: Task[] = [];
  private summary: Summary = { total: 0, pending: 0, in_progress: 0, completed: 0, overdue: 0 };
  private loading: boolean = true;
  private expandedTaskId: number | null = null;
  
  // Filters
  private dateRange: string = '30';
  private statusFilter: string = '';
  private priorityFilter: string = '';
  private categoryFilter: string = '';
  private departmentFilter: string = '';
  private employeeFilter: string = '';
  private searchQuery: string = '';
  private statusCardFilter: string = '';
  
  // Filter options
  private departments: Department[] = [];
  private categories: Category[] = [];
  private employees: Employee[] = [];
  private isVGKOrEA: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadFilterOptions();
    await this.loadTasks();
  }

  private async loadFilterOptions(): Promise<void> {
    try {
      const [deptRes, catRes, profileRes] = await Promise.all([
        apiService.get<any>('/staff/departments'),
        apiService.get<any>('/staff/tasks/categories'),
        apiService.get<any>('/staff/auth/me')
      ]);
      
      if (deptRes.success && deptRes.data) {
        this.departments = deptRes.data.departments || deptRes.data || [];
      }
      if (catRes.success && catRes.data) {
        this.categories = catRes.data.categories || catRes.data || [];
      }
      
      // DC Protocol: Load downline employees for all users with team access
      await this.loadDownlineEmployees();
      
      this.updateFiltersUI();
    } catch (error) {
      console.error('[StaffTeamActivities] Failed to load filter options:', error);
    }
  }
  
  private async loadDownlineEmployees(): Promise<void> {
    try {
      // DC Protocol: Fetch user's team members (direct reports for managers, all for admins)
      const response = await apiService.get<any>('/staff/employees/team');
      if (response.success && response.data) {
        const team = response.data.employees || response.data || [];
        this.employees = team
          .map((e: any) => ({
            id: e.id,
            full_name: e.full_name || e.name,
            emp_code: e.emp_code
          }))
          .sort((a: Employee, b: Employee) => a.full_name.localeCompare(b.full_name));
        
        // Show employee filter if user has team members
        this.isVGKOrEA = this.employees.length > 0;
      }
    } catch (error) {
      console.error('[StaffTeamActivities] Failed to load team employees:', error);
    }
  }

  private async loadTasks(): Promise<void> {
    this.loading = true;
    this.updateTaskList();

    try {
      const params = new URLSearchParams();
      
      // Date range filter
      if (this.dateRange !== 'all') {
        const days = parseInt(this.dateRange);
        const dateFrom = new Date();
        dateFrom.setDate(dateFrom.getDate() - days);
        params.append('start_date', dateFrom.toISOString().split('T')[0]);
      }
      
      if (this.departmentFilter) params.append('department_id', this.departmentFilter);
      if (this.statusFilter) params.append('status', this.statusFilter);
      if (this.priorityFilter) params.append('priority', this.priorityFilter);
      if (this.categoryFilter) params.append('category', this.categoryFilter);
      if (this.employeeFilter) params.append('employee_id', this.employeeFilter);

      const response = await apiService.get<any>(`/staff/tasks/team-activity?${params.toString()}`);

      if (response.success !== false && response.data) {
        this.tasks = response.data.tasks || [];
        this.summary = response.data.summary || { total: 0, pending: 0, in_progress: 0, completed: 0, overdue: 0 };
      } else {
        this.tasks = [];
      }
    } catch (error) {
      console.error('[StaffTeamActivities] Failed to load:', error);
      this.tasks = [];
    }

    this.loading = false;
    this.updateStats();
    this.updateTaskList();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container team-activities-page">
        ${PageHeader.render({ title: 'Team Activities', showBack: true })}
        
        <!-- Stats Cards -->
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

        <!-- Filters Section -->
        <div class="filters-section card">
          <div class="filter-row">
            <div class="filter-item">
              <label>Date Range</label>
              <select id="dateRangeFilter" class="form-select">
                ${DATE_RANGES.map(d => 
                  `<option value="${d.id}" ${this.dateRange === d.id ? 'selected' : ''}>${d.label}</option>`
                ).join('')}
              </select>
            </div>
            <div class="filter-item">
              <label>Department</label>
              <select id="departmentFilter" class="form-select">
                <option value="">All Departments</option>
              </select>
            </div>
          </div>
          <div class="filter-row">
            <div class="filter-item">
              <label>Status</label>
              <select id="statusFilter" class="form-select">
                ${STATUS_OPTIONS.map(s => 
                  `<option value="${s.id}" ${this.statusFilter === s.id ? 'selected' : ''}>${s.label}</option>`
                ).join('')}
              </select>
            </div>
            <div class="filter-item">
              <label>Priority</label>
              <select id="priorityFilter" class="form-select">
                ${PRIORITY_OPTIONS.map(p => 
                  `<option value="${p.id}" ${this.priorityFilter === p.id ? 'selected' : ''}>${p.label}</option>`
                ).join('')}
              </select>
            </div>
          </div>
          <div class="filter-row">
            <div class="filter-item">
              <label>Category</label>
              <select id="categoryFilter" class="form-select">
                <option value="">All Categories</option>
              </select>
            </div>
            <div class="filter-item" id="employeeFilterContainer" style="display: none;">
              <label>Team Member</label>
              <select id="employeeFilter" class="form-select">
                <option value="">All Team Members</option>
              </select>
            </div>
          </div>
          <div class="filter-row">
            <div class="filter-item" style="grid-column: span 2;">
              <label>Search</label>
              <input type="text" id="searchInput" class="form-input" placeholder="Search tasks..." value="${this.searchQuery}">
            </div>
          </div>
          <div class="filter-actions">
            <button id="applyFiltersBtn" class="btn btn-primary">Apply Filters</button>
            <button id="resetFiltersBtn" class="btn btn-secondary">Reset</button>
          </div>
        </div>

        <!-- Tasks List -->
        <div class="tasks-list" id="tasksList">
          <div class="loading-state">Loading tasks...</div>
        </div>
      </div>

      <!-- Task Detail Modal -->
      <div class="modal-overlay" id="taskModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h3>Task Details</h3>
            <button class="modal-close" id="closeModalBtn">&times;</button>
          </div>
          <div class="modal-body" id="taskModalBody"></div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="closeTaskBtn">Close</button>
            <button class="btn btn-primary" id="saveTaskBtn">Save Progress</button>
          </div>
        </div>
      </div>

      <style>
        .team-activities-page { padding-bottom: 80px; }
        
        .stats-scroll {
          display: flex;
          gap: 12px;
          overflow-x: auto;
          padding: 16px;
          -webkit-overflow-scrolling: touch;
        }
        .stats-scroll::-webkit-scrollbar { display: none; }
        
        .stat-card {
          min-width: 100px;
          background: rgba(255,255,255,0.1);
          border-radius: 12px;
          padding: 12px;
          text-align: center;
          cursor: pointer;
          transition: all 0.2s;
          border: 2px solid transparent;
        }
        .stat-card.active { border-color: #4f46e5; background: rgba(79,70,229,0.2); }
        .stat-card:hover { transform: translateY(-2px); }
        
        .stat-icon {
          width: 40px;
          height: 40px;
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 8px;
          font-size: 16px;
        }
        .stat-icon.total { background: #e0e7ff; color: #4338ca; }
        .stat-icon.pending { background: #fef3c7; color: #d97706; }
        .stat-icon.in-progress { background: #dbeafe; color: #2563eb; }
        .stat-icon.completed { background: #d1fae5; color: #059669; }
        .stat-icon.overdue { background: #fee2e2; color: #dc2626; }
        
        .stat-value { font-size: 20px; font-weight: 700; color: #fff; }
        .stat-label { font-size: 11px; color: rgba(255,255,255,0.7); }
        
        .filters-section {
          margin: 0 16px 16px;
          padding: 16px;
          background: rgba(255,255,255,0.05);
          border-radius: 12px;
        }
        .filter-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          margin-bottom: 12px;
        }
        .filter-item label {
          display: block;
          font-size: 11px;
          color: rgba(255,255,255,0.6);
          margin-bottom: 4px;
          text-transform: uppercase;
        }
        .form-select, .form-input {
          width: 100%;
          padding: 10px 12px;
          background: rgba(255,255,255,0.1);
          border: 1px solid rgba(255,255,255,0.2);
          border-radius: 8px;
          color: #fff;
          font-size: 14px;
        }
        .form-select option { background: #1e293b; color: #fff; }
        
        .filter-actions {
          display: flex;
          gap: 12px;
          margin-top: 16px;
        }
        .btn {
          flex: 1;
          padding: 12px;
          border-radius: 8px;
          font-weight: 600;
          border: none;
          cursor: pointer;
        }
        .btn-primary { background: #4f46e5; color: #fff; }
        .btn-secondary { background: rgba(255,255,255,0.1); color: #fff; }
        
        .tasks-list { padding: 0 16px; }
        
        .task-card-container { margin-bottom: 12px; }
        .task-card {
          background: rgba(255,255,255,0.08);
          border-radius: 12px;
          padding: 16px;
          cursor: pointer;
          transition: all 0.2s;
        }
        .task-card:hover { background: rgba(255,255,255,0.12); }
        .task-card.expanded { border-radius: 12px 12px 0 0; background: rgba(79,70,229,0.2); border: 1px solid #4f46e5; border-bottom: none; }
        .expand-icon { color: rgba(255,255,255,0.5); transition: transform 0.3s; }
        .expand-icon.rotated { transform: rotate(180deg); }
        .task-inline-detail { display: none; background: rgba(30,41,59,0.98); border: 1px solid #4f46e5; border-top: none; border-radius: 0 0 12px 12px; padding: 16px; }
        .task-inline-detail.show { display: block; }
        .detail-section { margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .detail-section:last-child { border-bottom: none; margin-bottom: 0; }
        .detail-section-title { font-size: 13px; font-weight: 600; color: #fff; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
        .detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .detail-item { display: flex; flex-direction: column; }
        .detail-label { font-size: 11px; color: rgba(255,255,255,0.5); text-transform: uppercase; margin-bottom: 4px; }
        .detail-value { font-size: 14px; color: #fff; }
        .inline-footer { display: flex; gap: 8px; margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.1); }
        .inline-footer .btn { flex: 1; }
        
        .task-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 8px;
        }
        .task-title {
          font-weight: 600;
          color: #fff;
          font-size: 15px;
          flex: 1;
        }
        .task-id { font-size: 11px; color: rgba(255,255,255,0.5); }
        
        .task-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-bottom: 8px;
        }
        
        .badge {
          padding: 4px 8px;
          border-radius: 6px;
          font-size: 11px;
          font-weight: 500;
        }
        .badge-pending { background: #fef3c7; color: #92400e; }
        .badge-in_progress { background: #dbeafe; color: #1e40af; }
        .badge-completed { background: #dcfce7; color: #166534; }
        .badge-cancelled { background: #f3f4f6; color: #6b7280; }
        .badge-on_hold { background: #fce7f3; color: #9d174d; }
        .badge-low { background: #d1fae5; color: #065f46; }
        .badge-medium { background: #fef3c7; color: #92400e; }
        .badge-high { background: #fee2e2; color: #991b1b; }
        .badge-critical { background: #dc2626; color: white; }
        .badge-role { background: #4f46e5; color: white; }
        
        .task-details {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
          font-size: 12px;
          color: rgba(255,255,255,0.7);
        }
        .task-detail-item { display: flex; flex-direction: column; }
        .task-detail-label { font-size: 10px; color: rgba(255,255,255,0.5); text-transform: uppercase; }
        
        .progress-bar {
          height: 6px;
          background: rgba(255,255,255,0.1);
          border-radius: 3px;
          overflow: hidden;
          margin-top: 12px;
        }
        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #4f46e5, #8b5cf6);
          transition: width 0.3s;
        }
        
        .due-date.overdue { color: #dc2626; font-weight: 600; }
        .due-date.today { color: #d97706; font-weight: 600; }
        .due-date.upcoming { color: #059669; }
        
        .loading-state, .empty-state {
          text-align: center;
          padding: 40px;
          color: rgba(255,255,255,0.5);
        }
        
        /* Modal Styles */
        .modal-overlay {
          position: fixed;
          top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0,0,0,0.8);
          z-index: 1000;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
        }
        .modal-content {
          background: #1e293b;
          border-radius: 16px;
          width: 100%;
          max-width: 500px;
          max-height: 80vh;
          overflow-y: auto;
        }
        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 20px;
          border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .modal-header h3 { margin: 0; color: #fff; font-size: 18px; }
        .modal-close {
          background: none;
          border: none;
          color: #fff;
          font-size: 24px;
          cursor: pointer;
        }
        .modal-body { padding: 20px; }
        .modal-footer {
          display: flex;
          gap: 12px;
          padding: 16px 20px;
          border-top: 1px solid rgba(255,255,255,0.1);
        }
        
        .detail-row {
          display: flex;
          justify-content: space-between;
          padding: 12px 0;
          border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .detail-row:last-child { border-bottom: none; }
        .detail-label { color: rgba(255,255,255,0.6); font-size: 13px; }
        .detail-value { color: #fff; font-size: 14px; font-weight: 500; }
        
        .progress-input-group {
          margin-top: 16px;
          padding: 16px;
          background: rgba(255,255,255,0.05);
          border-radius: 8px;
        }
        .progress-input-group label { display: block; margin-bottom: 8px; color: rgba(255,255,255,0.7); }
        .progress-input-group input {
          width: 100%;
          padding: 10px;
          background: rgba(255,255,255,0.1);
          border: 1px solid rgba(255,255,255,0.2);
          border-radius: 6px;
          color: #fff;
        }
        
        .task-actions {
          display: flex;
          gap: 8px;
          margin-top: 16px;
        }
        .task-actions .btn { flex: 1; }
        .btn-success { background: #059669; color: #fff; }
        .btn-warning { background: #d97706; color: #fff; }
      </style>
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private updateFiltersUI(): void {
    const deptSelect = document.getElementById('departmentFilter') as HTMLSelectElement;
    if (deptSelect) {
      deptSelect.innerHTML = `<option value="">All Departments</option>` +
        this.departments.map(d => 
          `<option value="${d.id}" ${this.departmentFilter === d.id.toString() ? 'selected' : ''}>${d.name}</option>`
        ).join('');
    }
    
    const catSelect = document.getElementById('categoryFilter') as HTMLSelectElement;
    if (catSelect) {
      catSelect.innerHTML = `<option value="">All Categories</option>` +
        this.categories.map(c => 
          `<option value="${c.name}" ${this.categoryFilter === c.name ? 'selected' : ''}>${c.name}</option>`
        ).join('');
    }
    
    // DC Protocol: Team member filter for all users with downline access
    const empContainer = document.getElementById('employeeFilterContainer');
    const empSelect = document.getElementById('employeeFilter') as HTMLSelectElement;
    if (empContainer && empSelect && this.isVGKOrEA && this.employees.length > 0) {
      empContainer.style.display = 'block';
      empSelect.innerHTML = `<option value="">All Team Members</option>` +
        this.employees.map(e => 
          `<option value="${e.id}" ${this.employeeFilter === e.id.toString() ? 'selected' : ''}>${e.full_name} (${e.emp_code})</option>`
        ).join('');
    }
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

    let filteredTasks = [...this.tasks];
    
    // Apply status card filter
    if (this.statusCardFilter === 'overdue') {
      const today = new Date().toISOString().split('T')[0];
      filteredTasks = filteredTasks.filter(t => t.due_date && t.due_date < today && t.status !== 'completed');
    } else if (this.statusCardFilter) {
      filteredTasks = filteredTasks.filter(t => t.status === this.statusCardFilter);
    }
    
    // Apply search filter
    if (this.searchQuery) {
      const query = this.searchQuery.toLowerCase();
      filteredTasks = filteredTasks.filter(t =>
        t.title?.toLowerCase().includes(query) ||
        t.description?.toLowerCase().includes(query) ||
        t.id?.toString().includes(query) ||
        t.primary_assignee_name?.toLowerCase().includes(query) ||
        t.creator_name?.toLowerCase().includes(query)
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
    const roleLabels: Record<string, string> = {
      'primary': 'Primary',
      'secondary': 'Secondary', 
      'creator': 'Creator',
      'viewer': 'Viewer'
    };
    const roleLabel = roleLabels[task.viewer_role] || 'Viewer';
    
    const assignedTo = task.primary_assignee_name || task.primary_assignee?.full_name || 'N/A';
    const secondaryCount = task.secondary_assignees_count || 0;
    const assignedToDisplay = secondaryCount > 0 ? `${assignedTo} +${secondaryCount}` : assignedTo;
    const createdBy = task.assigned_by?.full_name || task.creator_name || 'Unknown';
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
            <span class="badge badge-role">${roleLabel}</span>
          </div>
          <div class="task-details">
            <div class="task-detail-item">
              <span class="task-detail-label">Assigned To</span>
              <span>${assignedToDisplay}</span>
            </div>
            <div class="task-detail-item">
              <span class="task-detail-label">Created By</span>
              <span>${createdBy}</span>
            </div>
            <div class="task-detail-item">
              <span class="task-detail-label">Due Date</span>
              <span class="due-date ${dueDateClass}">${this.formatDate(task.due_date)}</span>
            </div>
            <div class="task-detail-item">
              <span class="task-detail-label">Assigned</span>
              <span>${this.formatDate(task.assigned_date || task.created_at)}</span>
            </div>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" style="width: ${task.progress || 0}%"></div>
          </div>
        </div>
        
        <!-- INLINE DETAIL -->
        <div class="task-inline-detail ${isExpanded ? 'show' : ''}" id="detail-${task.id}">
          <div class="detail-section">
            <div class="detail-section-title"><i class="fas fa-info-circle"></i> Task Details</div>
            <div class="detail-grid">
              <div class="detail-item"><span class="detail-label">Category</span><span class="detail-value">${task.category || '-'}</span></div>
              <div class="detail-item"><span class="detail-label">Progress</span><span class="detail-value">${task.progress || 0}%</span></div>
            </div>
            ${task.description ? `<div style="margin-top: 12px;"><span class="detail-label">Description</span><div style="margin-top: 8px; color: rgba(255,255,255,0.8); font-size: 14px; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px;">${this.escapeHtml(task.description)}</div></div>` : ''}
          </div>
          
          <div class="detail-section">
            <div class="detail-section-title"><i class="fas fa-edit"></i> Update Task</div>
            <div style="margin-bottom: 12px;">
              <label style="display: block; color: rgba(255,255,255,0.7); font-size: 12px; margin-bottom: 6px;">Status</label>
              <select id="statusSelect-${task.id}" class="form-select">
                ${STATUS_OPTIONS.filter(s => s.id).map(s => `<option value="${s.id}" ${task.status === s.id ? 'selected' : ''}>${s.label}</option>`).join('')}
              </select>
            </div>
            <div style="margin-bottom: 12px;">
              <label style="display: block; color: rgba(255,255,255,0.7); font-size: 12px; margin-bottom: 6px;">Priority</label>
              <select id="prioritySelect-${task.id}" class="form-select">
                ${PRIORITY_OPTIONS.filter(p => p.id).map(p => `<option value="${p.id}" ${task.priority === p.id ? 'selected' : ''}>${p.label}</option>`).join('')}
              </select>
            </div>
          </div>
          
          <div class="inline-footer">
            <button class="btn btn-secondary" data-action="collapse" data-id="${task.id}">Close</button>
            <button class="btn btn-primary" data-action="save" data-id="${task.id}">Save Changes</button>
          </div>
        </div>
      </div>
    `;
  }

  private attachEventListeners(): void {
    // Stat cards filter
    document.querySelectorAll('.stat-card').forEach(card => {
      card.addEventListener('click', () => {
        const status = card.getAttribute('data-status') || '';
        this.statusCardFilter = status;
        document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        this.updateTaskList();
      });
    });

    // Filter dropdowns
    document.getElementById('dateRangeFilter')?.addEventListener('change', (e) => {
      this.dateRange = (e.target as HTMLSelectElement).value;
    });
    document.getElementById('departmentFilter')?.addEventListener('change', (e) => {
      this.departmentFilter = (e.target as HTMLSelectElement).value;
    });
    document.getElementById('statusFilter')?.addEventListener('change', (e) => {
      this.statusFilter = (e.target as HTMLSelectElement).value;
    });
    document.getElementById('priorityFilter')?.addEventListener('change', (e) => {
      this.priorityFilter = (e.target as HTMLSelectElement).value;
    });
    document.getElementById('categoryFilter')?.addEventListener('change', (e) => {
      this.categoryFilter = (e.target as HTMLSelectElement).value;
    });
    document.getElementById('employeeFilter')?.addEventListener('change', (e) => {
      this.employeeFilter = (e.target as HTMLSelectElement).value;
    });
    document.getElementById('searchInput')?.addEventListener('input', (e) => {
      this.searchQuery = (e.target as HTMLInputElement).value;
    });

    // Apply & Reset buttons
    document.getElementById('applyFiltersBtn')?.addEventListener('click', () => {
      this.loadTasks();
    });
    document.getElementById('resetFiltersBtn')?.addEventListener('click', () => {
      this.dateRange = '30';
      this.statusFilter = '';
      this.priorityFilter = '';
      this.categoryFilter = '';
      this.departmentFilter = '';
      this.employeeFilter = '';
      this.searchQuery = '';
      this.statusCardFilter = '';
      this.render();
      this.updateFiltersUI();
      this.loadTasks();
    });
  }

  private attachTaskCardListeners(): void {
    document.querySelectorAll('.task-card').forEach(card => {
      card.addEventListener('click', (e) => {
        const target = e.target as HTMLElement;
        if (target.closest('select') || target.closest('input') || target.closest('button') || target.closest('textarea')) return;
        const taskId = parseInt(card.getAttribute('data-task-id') || '0');
        this.toggleTaskDetail(taskId);
      });
    });

    document.querySelectorAll('[data-action]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const action = btn.getAttribute('data-action');
        const taskId = parseInt(btn.getAttribute('data-id') || '0');
        switch (action) {
          case 'save': await this.saveTaskInline(taskId); break;
          case 'collapse': this.collapseTask(); break;
        }
      });
    });
  }

  private toggleTaskDetail(taskId: number): void {
    if (this.expandedTaskId === taskId) {
      this.collapseTask();
    } else {
      this.expandedTaskId = taskId;
      this.updateTaskList();
    }
  }

  private collapseTask(): void {
    this.expandedTaskId = null;
    this.updateTaskList();
  }

  private async saveTaskInline(taskId: number): Promise<void> {
    const statusSelect = document.getElementById(`statusSelect-${taskId}`) as HTMLSelectElement;
    const prioritySelect = document.getElementById(`prioritySelect-${taskId}`) as HTMLSelectElement;
    try {
      const response = await apiService.put<any>(`/staff/tasks/${taskId}`, { status: statusSelect?.value, priority: prioritySelect?.value });
      if (response.success !== false) { alert('Task updated successfully!'); await this.loadTasks(); }
      else { alert('Failed to update task'); }
    } catch (error) { alert('Error updating task'); }
  }

  private getDueDateClass(dueDate: string, status: string): string {
    if (!dueDate || status === 'completed') return '';
    
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const due = new Date(dueDate);
    due.setHours(0, 0, 0, 0);
    
    if (due < today) return 'overdue';
    if (due.getTime() === today.getTime()) return 'today';
    return 'upcoming';
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  private formatStatus(status: string): string {
    const statusMap: Record<string, string> = {
      'pending': 'Pending',
      'in_progress': 'In Progress',
      'completed': 'Completed',
      'cancelled': 'Cancelled',
      'on_hold': 'On Hold'
    };
    return statusMap[status] || status;
  }

  private capitalize(str: string): string {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  private escapeHtml(str: string): string {
    if (!str) return '';
    return str.replace(/[&<>"']/g, (m) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[m] || m);
  }
}
