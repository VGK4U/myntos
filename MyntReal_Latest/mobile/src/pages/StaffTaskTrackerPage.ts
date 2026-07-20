/**
 * Staff Task Dashboard Page - Enhanced with Web Parity
 * DC Protocol: DC_MOBILE_TASK_TRACKER_001
 * Tab 1: My Tasks (self data with subtask counts)
 * Tab 2: Team (view any team member's task data)
 * Tab 3: Department-wise team performance
 * Tab 4: Employee-wise team performance
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';

interface DepartmentStats {
  department_id: number;
  department_name: string;
  total: number;
  completed: number;
  in_progress: number;
  pending: number;
  overdue: number;
  completion_rate: number;
}

interface EmployeeStats {
  employee_id: number;
  employee_name: string;
  employee_code: string;
  department: string;
  total: number;
  total_assigned?: number;
  as_primary?: number;
  as_secondary?: number;
  completed: number;
  pending: number;
  overdue: number;
  completion_rate: number;
}

interface TaskStats {
  total: number;
  pending: number;
  in_progress: number;
  completed: number;
  overdue: number;
}

interface SubtaskSummary {
  total: number;
  completed: number;
  in_progress: number;
  pending: number;
  cancelled: number;
  overdue: number;
  completion_rate: number;
}

interface SelfSummary {
  total: number;
  new_tasks_assigned: number;
  completed: number;
  in_progress: number;
  pending: number;
  overdue: number;
  completion_rate: number;
}

interface TeamEmployee {
  id: number;
  emp_code: string;
  full_name: string;
}

export class StaffTaskTrackerPage {
  private container: HTMLElement;
  private departmentStats: DepartmentStats[] = [];
  private employeeStats: EmployeeStats[] = [];
  private stats: TaskStats = { total: 0, pending: 0, in_progress: 0, completed: 0, overdue: 0 };
  private loading: boolean = true;
  private activeTab: 'myTasks' | 'team' | 'department' | 'employee' = 'myTasks';
  private dateFrom: string = '';
  private dateTo: string = '';
  private searchQuery: string = '';
  private assignedByMe: SelfSummary | null = null;
  private assignedByMeSubtasks: SubtaskSummary | null = null;
  private assignedToMe: SelfSummary | null = null;
  private assignedToMeSubtasks: SubtaskSummary | null = null;
  private teamEmployees: TeamEmployee[] = [];
  private teamEmployeesLoaded: boolean = false;
  private selectedTeamMemberId: string = '';
  private teamMemberName: string = '';
  private teamAssignedBy: SelfSummary | null = null;
  private teamAssignedBySubtasks: SubtaskSummary | null = null;
  private teamAssignedTo: SelfSummary | null = null;
  private teamAssignedToSubtasks: SubtaskSummary | null = null;
  private teamLoading: boolean = false;
  private statusFilter: string = 'all';
  private priorityFilter: string = 'all';
  private categoryFilter: string = 'all';

  private dateRangeMode: string = '30';

  constructor(container: HTMLElement) {
    this.container = container;
    const now = new Date();
    this.dateTo = now.toISOString().split('T')[0];
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    this.dateFrom = thirtyDaysAgo.toISOString().split('T')[0];
  }

  async init(): Promise<void> {
    this.render();
    await this.loadData();
  }

  private buildQueryParams(): string {
    const params = new URLSearchParams();
    if (this.dateRangeMode !== 'overall') {
      if (this.dateFrom) params.append('start_date', this.dateFrom);
      if (this.dateTo) params.append('end_date', this.dateTo);
    }
    if (this.statusFilter && this.statusFilter !== 'all') params.append('status', this.statusFilter);
    if (this.priorityFilter && this.priorityFilter !== 'all') params.append('priority', this.priorityFilter);
    if (this.categoryFilter && this.categoryFilter !== 'all') params.append('category', this.categoryFilter);
    return params.toString();
  }

  private async loadData(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const qp = this.buildQueryParams();
      const summaryDays = this.dateRangeMode === 'overall' ? 365 : 
        (this.dateFrom && this.dateTo 
          ? Math.min(365, Math.ceil((new Date(this.dateTo).getTime() - new Date(this.dateFrom).getTime()) / (1000 * 60 * 60 * 24)))
          : 30);

      const [deptResponse, empResponse, summaryResponse, myAssignedRes, myReceivedRes] = await Promise.all([
        apiService.get<any>(`/staff/tasks/analytics/department-summary?${qp}`),
        apiService.get<any>(`/staff/tasks/analytics/by-employee`),
        apiService.get<any>(`/staff/tasks/analytics/summary?days=${summaryDays}`),
        apiService.get<any>(`/staff/tasks/analytics/my-assigned-summary?${qp}`),
        apiService.get<any>(`/staff/tasks/analytics/my-summary?${qp}`)
      ]);

      if (deptResponse.success !== false && deptResponse.data) {
        const data = deptResponse.data as any;
        this.departmentStats = data.departments || data.department_summary || [];
        if (data.summary) {
          this.stats = {
            total: data.summary.total || 0,
            pending: data.summary.pending || 0,
            in_progress: data.summary.in_progress || 0,
            completed: data.summary.completed || 0,
            overdue: data.summary.overdue || 0
          };
        }
      }

      if (empResponse.success !== false && empResponse.data) {
        const data = empResponse.data as any;
        const rawEmployees = data.employees || data.employee_stats || [];
        this.employeeStats = rawEmployees.map((emp: any) => ({
          ...emp,
          total: emp.total ?? emp.total_assigned ?? ((emp.as_primary || 0) + (emp.as_secondary || 0)),
          overdue: emp.overdue ?? 0,
          completion_rate: emp.completion_rate ?? (emp.total_assigned > 0 ? Math.min(100, Math.round((emp.completed / emp.total_assigned) * 100)) : 0)
        }));
      }

      if (summaryResponse.success !== false && summaryResponse.data) {
        const data = summaryResponse.data as any;
        if (data.status_breakdown) {
          this.stats = {
            total: data.total_tasks || this.stats.total,
            pending: data.status_breakdown.pending || this.stats.pending,
            in_progress: data.status_breakdown.in_progress || this.stats.in_progress,
            completed: data.status_breakdown.completed || this.stats.completed,
            overdue: data.overdue_count || this.stats.overdue
          };
        }
      }

      if (myAssignedRes.success !== false && myAssignedRes.data) {
        const data = myAssignedRes.data as any;
        if (data.summary) {
          this.assignedByMe = data.summary;
          this.assignedByMeSubtasks = data.subtask_summary || null;
        }
      }

      if (myReceivedRes.success !== false && myReceivedRes.data) {
        const data = myReceivedRes.data as any;
        if (data.summary) {
          const sb = data.summary.status_breakdown || [];
          this.assignedToMe = {
            total: data.summary.total || 0,
            new_tasks_assigned: data.summary.new_tasks_assigned || 0,
            completed: sb.find((x: any) => x.status === 'completed')?.count || 0,
            in_progress: sb.find((x: any) => x.status === 'in_progress')?.count || 0,
            pending: sb.find((x: any) => x.status === 'pending')?.count || 0,
            overdue: data.summary.overdue || 0,
            completion_rate: data.summary.completion_rate || 0
          };
          this.assignedToMeSubtasks = data.subtask_summary || null;
        }
      }

    } catch (error) {
      console.error('[StaffTaskTrackerPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private async loadTeamEmployees(): Promise<void> {
    if (this.teamEmployeesLoaded) return;
    try {
      const response = await apiService.get<any>('/staff/employees?status=active');
      if (response.success !== false && response.data) {
        const data = response.data as any;
        const emps = data.employees || data || [];
        this.teamEmployees = emps.map((e: any) => ({
          id: e.id,
          emp_code: e.emp_code,
          full_name: e.full_name
        }));
        this.teamEmployeesLoaded = true;
      }
    } catch (error) {
      console.error('[StaffTaskTrackerPage] Failed to load team employees:', error);
    }
  }

  private async loadTeamMemberData(): Promise<void> {
    if (!this.selectedTeamMemberId) return;
    this.teamLoading = true;
    this.teamAssignedBy = null;
    this.teamAssignedBySubtasks = null;
    this.teamAssignedTo = null;
    this.teamAssignedToSubtasks = null;
    this.updateContent();

    try {
      const qp = this.buildQueryParams();
      const response = await apiService.get<any>(`/staff/tasks/analytics/team-member-summary?employee_id=${this.selectedTeamMemberId}&${qp}`);
      if (response.success !== false && response.data) {
        const data = response.data as any;
        this.teamMemberName = `${data.employee.emp_code} - ${data.employee.full_name}`;
        
        const ab = data.assigned_by;
        if (ab && ab.success && ab.summary) {
          this.teamAssignedBy = ab.summary;
          this.teamAssignedBySubtasks = ab.subtask_summary || null;
        }
        
        const at = data.assigned_to;
        if (at && at.success && at.summary) {
          const sb = at.summary.status_breakdown || [];
          this.teamAssignedTo = {
            total: at.summary.total || 0,
            new_tasks_assigned: at.summary.new_tasks_assigned || 0,
            completed: sb.find((x: any) => x.status === 'completed')?.count || 0,
            in_progress: sb.find((x: any) => x.status === 'in_progress')?.count || 0,
            pending: sb.find((x: any) => x.status === 'pending')?.count || 0,
            overdue: at.summary.overdue || 0,
            completion_rate: at.summary.completion_rate || 0
          };
          this.teamAssignedToSubtasks = at.subtask_summary || null;
        }
      }
    } catch (error) {
      console.error('[StaffTaskTrackerPage] Failed to load team member:', error);
    }

    this.teamLoading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Task Dashboard', showBack: true })}
        
        <div class="date-filter-row">
          <div class="date-input-group">
            <label>Date Range</label>
            <select id="dateRangeMode" class="form-input">
              <option value="overall" ${this.dateRangeMode === 'overall' ? 'selected' : ''}>Overall</option>
              <option value="7" ${this.dateRangeMode === '7' ? 'selected' : ''}>Last 7 Days</option>
              <option value="30" ${this.dateRangeMode === '30' ? 'selected' : ''}>Last 30 Days</option>
              <option value="90" ${this.dateRangeMode === '90' ? 'selected' : ''}>Last 90 Days</option>
              <option value="custom" ${this.dateRangeMode === 'custom' ? 'selected' : ''}>Custom</option>
            </select>
          </div>
          <div class="date-input-group" id="customFromGroup" style="display:${this.dateRangeMode === 'custom' ? 'flex' : 'none'};">
            <label>From</label>
            <input type="date" id="dateFrom" class="form-input" value="${this.dateFrom}">
          </div>
          <div class="date-input-group" id="customToGroup" style="display:${this.dateRangeMode === 'custom' ? 'flex' : 'none'};">
            <label>To</label>
            <input type="date" id="dateTo" class="form-input" value="${this.dateTo}">
          </div>
          <button class="btn btn-sm btn-primary" id="applyDateFilter">Apply</button>
        </div>

        <div class="filter-row-extra">
          <select id="statusFilter" class="form-input filter-select">
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <select id="priorityFilter" class="form-input filter-select">
            <option value="all">All Priority</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <select id="categoryFilter" class="form-input filter-select">
            <option value="all">All Category</option>
            <option value="general">General</option>
            <option value="development">Development</option>
            <option value="design">Design</option>
            <option value="testing">Testing</option>
            <option value="documentation">Documentation</option>
            <option value="maintenance">Maintenance</option>
            <option value="support">Support</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div class="tabs-nav">
          <button class="tab-btn ${this.activeTab === 'myTasks' ? 'active' : ''}" data-tab="myTasks">My Tasks</button>
          <button class="tab-btn ${this.activeTab === 'team' ? 'active' : ''}" data-tab="team">Team</button>
          <button class="tab-btn ${this.activeTab === 'department' ? 'active' : ''}" data-tab="department">Department</button>
          <button class="tab-btn ${this.activeTab === 'employee' ? 'active' : ''}" data-tab="employee">Employee</button>
        </div>
        
        <div class="quick-actions-row">
          <button class="btn btn-outline btn-sm" id="viewTasksBtn">View All Tasks</button>
          <button class="btn btn-outline btn-sm" id="viewAssignedBtn">Assigned By Me</button>
          <button class="btn btn-outline btn-sm" id="viewReceivedBtn">Assigned To Me</button>
        </div>

        <div class="content-area" id="contentArea">
          <div class="loading-state">Loading analytics...</div>
        </div>

        <button class="fab-btn" id="createTaskBtn">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </button>
      </div>

      <style>
        .filter-row-extra { display: flex; gap: 8px; padding: 0 16px 8px 16px; }
        .filter-select { flex: 1; font-size: 13px; padding: 6px 8px; }
        .team-member-select { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; margin-bottom: 12px; background: white; }
        .team-member-label { font-size: 13px; font-weight: 600; color: #555; margin-bottom: 4px; }
        .team-member-name { font-size: 15px; font-weight: 600; color: #333; margin-bottom: 8px; }
        .empty-team-state { text-align: center; padding: 32px 16px; color: #888; }
        .empty-team-state .icon { font-size: 32px; margin-bottom: 8px; }
      </style>
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    this.container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const tab = btn.getAttribute('data-tab') as any;
        this.activeTab = tab;
        this.container.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        if (tab === 'team' && !this.teamEmployeesLoaded) {
          await this.loadTeamEmployees();
        }
        this.updateContent();
      });
    });

    document.getElementById('dateRangeMode')?.addEventListener('change', (e) => {
      this.dateRangeMode = (e.target as HTMLSelectElement).value;
      const customFrom = document.getElementById('customFromGroup') as HTMLElement;
      const customTo = document.getElementById('customToGroup') as HTMLElement;
      if (this.dateRangeMode === 'custom') {
        if (customFrom) customFrom.style.display = 'flex';
        if (customTo) customTo.style.display = 'flex';
      } else {
        if (customFrom) customFrom.style.display = 'none';
        if (customTo) customTo.style.display = 'none';
        if (this.dateRangeMode !== 'overall') {
          const now = new Date();
          this.dateTo = now.toISOString().split('T')[0];
          const daysBack = parseInt(this.dateRangeMode) || 30;
          const fromDate = new Date(now.getTime() - daysBack * 24 * 60 * 60 * 1000);
          this.dateFrom = fromDate.toISOString().split('T')[0];
        }
        this.applyAllFilters();
      }
    });

    document.getElementById('applyDateFilter')?.addEventListener('click', () => {
      const fromInput = document.getElementById('dateFrom') as HTMLInputElement;
      const toInput = document.getElementById('dateTo') as HTMLInputElement;
      if (fromInput) this.dateFrom = fromInput.value;
      if (toInput) this.dateTo = toInput.value;
      this.applyAllFilters();
    });

    document.getElementById('statusFilter')?.addEventListener('change', (e) => {
      this.statusFilter = (e.target as HTMLSelectElement).value;
      this.applyAllFilters();
    });

    document.getElementById('priorityFilter')?.addEventListener('change', (e) => {
      this.priorityFilter = (e.target as HTMLSelectElement).value;
      this.applyAllFilters();
    });

    document.getElementById('categoryFilter')?.addEventListener('change', (e) => {
      this.categoryFilter = (e.target as HTMLSelectElement).value;
      this.applyAllFilters();
    });

    document.getElementById('createTaskBtn')?.addEventListener('click', () => {
      routerService.navigate('task-create');
    });

    document.getElementById('viewTasksBtn')?.addEventListener('click', () => {
      routerService.navigate('tasks');
    });

    document.getElementById('viewAssignedBtn')?.addEventListener('click', () => {
      routerService.navigate('tasks-assigned');
    });

    document.getElementById('viewReceivedBtn')?.addEventListener('click', () => {
      routerService.navigate('tasks-received');
    });
  }

  private async applyAllFilters(): Promise<void> {
    await this.loadData();
    if (this.activeTab === 'team' && this.selectedTeamMemberId) {
      await this.loadTeamMemberData();
    }
  }

  private updateContent(): void {
    const contentArea = document.getElementById('contentArea');
    if (!contentArea) return;

    if (this.loading) {
      contentArea.innerHTML = '<div class="loading-state">Loading analytics...</div>';
      return;
    }

    contentArea.innerHTML = `
      <div class="stats-grid-compact">
        <div class="stat-mini">
          <span class="stat-value">${this.stats.total}</span>
          <span class="stat-label">Total</span>
        </div>
        <div class="stat-mini completed">
          <span class="stat-value">${this.stats.completed}</span>
          <span class="stat-label">Completed</span>
        </div>
        <div class="stat-mini pending">
          <span class="stat-value">${this.stats.pending}</span>
          <span class="stat-label">Pending</span>
        </div>
        <div class="stat-mini danger">
          <span class="stat-value">${this.stats.overdue}</span>
          <span class="stat-label">Overdue</span>
        </div>
      </div>

      ${this.activeTab === 'myTasks' ? this.renderMyTasksView() : 
        this.activeTab === 'team' ? this.renderTeamView() :
        this.activeTab === 'department' ? this.renderDepartmentView() : this.renderEmployeeView()}
    `;

    this.attachCardListeners();
  }

  private renderSelfSection(label: string, icon: string, bgClass: string, summary: SelfSummary | null, subtasks: SubtaskSummary | null): string {
    if (!summary) {
      return `
        <div class="section-header"><h4>${icon} ${label}</h4></div>
        <div class="empty-state">No data available</div>
      `;
    }

    return `
      <div class="section-header"><h4>${icon} ${label}</h4></div>
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Tot</th>
              <th>Done</th>
              <th>Prog</th>
              <th>Pend</th>
              <th>OD</th>
              <th>%</th>
            </tr>
          </thead>
          <tbody>
            <tr class="${bgClass}">
              <td class="cell-name"><strong>Tasks</strong></td>
              <td><strong>${summary.total}</strong></td>
              <td class="cell-completed">${summary.completed}</td>
              <td class="cell-progress">${summary.in_progress}</td>
              <td class="cell-pending">${summary.pending}</td>
              <td class="cell-overdue">${summary.overdue}</td>
              <td class="cell-rate">${summary.completion_rate}%</td>
            </tr>
            <tr>
              <td class="cell-name cell-subtext">Sub Tasks</td>
              <td><strong>${subtasks?.total || 0}</strong></td>
              <td class="cell-completed">${subtasks?.completed || 0}</td>
              <td class="cell-progress">${subtasks?.in_progress || 0}</td>
              <td class="cell-pending">${subtasks?.pending || 0}</td>
              <td class="cell-overdue">${subtasks?.overdue || 0}</td>
              <td class="cell-rate">${subtasks?.completion_rate || 0}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    `;
  }

  private renderMyTasksView(): string {
    return `
      ${this.renderSelfSection('Assigned By Me', '📤', 'row-assigned-by', this.assignedByMe, this.assignedByMeSubtasks)}
      <div style="height: 16px;"></div>
      ${this.renderSelfSection('Assigned To Me', '📥', 'row-assigned-to', this.assignedToMe, this.assignedToMeSubtasks)}
    `;
  }

  private renderTeamView(): string {
    const employeeOptions = this.teamEmployees.map(e => 
      `<option value="${e.id}" ${this.selectedTeamMemberId === String(e.id) ? 'selected' : ''}>${e.emp_code} - ${e.full_name}</option>`
    ).join('');

    let content = '';
    if (this.teamLoading) {
      content = '<div class="loading-state">Loading team member data...</div>';
    } else if (!this.selectedTeamMemberId) {
      content = `
        <div class="empty-team-state">
          <div class="icon">👥</div>
          <div>Select a team member above to view their task summary</div>
        </div>
      `;
    } else if (this.teamAssignedBy || this.teamAssignedTo) {
      content = `
        <div class="team-member-name">👤 ${this.teamMemberName}</div>
        ${this.renderSelfSection('Assigned By Them', '📤', 'row-assigned-by', this.teamAssignedBy, this.teamAssignedBySubtasks)}
        <div style="height: 16px;"></div>
        ${this.renderSelfSection('Assigned To Them', '📥', 'row-assigned-to', this.teamAssignedTo, this.teamAssignedToSubtasks)}
      `;
    } else {
      content = `
        <div class="team-member-name">👤 ${this.teamMemberName}</div>
        <div class="empty-team-state">No task data found for this employee</div>
      `;
    }

    return `
      <div class="team-member-label">Select Team Member</div>
      <select id="teamMemberSelect" class="team-member-select">
        <option value="">-- Select an employee --</option>
        ${employeeOptions}
      </select>
      ${content}
    `;
  }

  private renderDepartmentView(): string {
    if (this.departmentStats.length === 0) {
      return '<div class="empty-state">No department data available</div>';
    }

    return `
      <div class="section-header">
        <h4>Team Performance (Department-wise)</h4>
      </div>
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Dept</th>
              <th>Tot</th>
              <th>Done</th>
              <th>Prog</th>
              <th>Pend</th>
              <th>OD</th>
              <th>%</th>
            </tr>
          </thead>
          <tbody>
            ${this.departmentStats.map(dept => {
              const rate = dept.completion_rate || Math.round((dept.completed / (dept.total || 1)) * 100);
              return `
                <tr data-dept-id="${dept.department_id}">
                  <td class="cell-name">${dept.department_name}</td>
                  <td>${dept.total}</td>
                  <td class="cell-completed">${dept.completed}</td>
                  <td class="cell-progress">${dept.in_progress || 0}</td>
                  <td class="cell-pending">${dept.pending}</td>
                  <td class="cell-overdue">${dept.overdue}</td>
                  <td class="cell-rate">${rate}%</td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  private renderEmployeeView(): string {
    let employees = this.employeeStats;
    
    if (this.searchQuery) {
      employees = employees.filter(e => 
        e.employee_name?.toLowerCase().includes(this.searchQuery) ||
        e.employee_code?.toLowerCase().includes(this.searchQuery)
      );
    }

    return `
      <div class="section-header">
        <h4>Team Performance (Employee-wise)</h4>
      </div>
      <div class="search-bar">
        <input type="text" id="employeeSearch" class="search-input" placeholder="Search employees..." value="${this.searchQuery}">
      </div>
      ${employees.length === 0 ? '<div class="empty-state">No employee data available</div>' : `
        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th>Employee</th>
                <th>Dept</th>
                <th>Tot</th>
                <th>Done</th>
                <th>Pend</th>
                <th>OD</th>
                <th>%</th>
              </tr>
            </thead>
            <tbody>
              ${employees.map(emp => {
                const rate = Math.min(100, emp.completion_rate || Math.round((emp.completed / (emp.total || 1)) * 100));
                return `
                  <tr data-emp-id="${emp.employee_id}">
                    <td class="cell-name">
                      <div>${emp.employee_name}</div>
                      <div class="cell-subtext">${emp.employee_code}</div>
                    </td>
                    <td class="cell-dept">${emp.department || '-'}</td>
                    <td>${emp.total}</td>
                    <td class="cell-completed">${emp.completed}</td>
                    <td class="cell-pending">${emp.pending}</td>
                    <td class="cell-overdue">${emp.overdue}</td>
                    <td class="cell-rate">${rate}%</td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      `}
    `;
  }

  private attachCardListeners(): void {
    const searchInput = document.getElementById('employeeSearch') as HTMLInputElement;
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = (e.target as HTMLInputElement).value.toLowerCase();
        this.updateContent();
      });
    }

    const teamSelect = document.getElementById('teamMemberSelect') as HTMLSelectElement;
    if (teamSelect) {
      teamSelect.addEventListener('change', async () => {
        this.selectedTeamMemberId = teamSelect.value;
        if (this.selectedTeamMemberId) {
          await this.loadTeamMemberData();
        } else {
          this.teamAssignedBy = null;
          this.teamAssignedTo = null;
          this.updateContent();
        }
      });
    }
  }
}
