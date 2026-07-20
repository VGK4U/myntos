/**
 * Progress Dashboard Page
 * DC Protocol: DC_MOBILE_PROGRESS_001
 * Staff progress summary matching web version exactly
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { API_ENDPOINTS } from '../constants/api-endpoints';

interface DayPlannerData {
  planned: number;
  done: number;
  pending: number;
  overdue: number;
  percent_done: number;
  total: number;
  met: number;
  missed: number;
}

interface EmployeeInfo {
  id: number;
  full_name: string;
  emp_code: string;
  role: string;
  department: string;
  designation?: string;
  level?: string;
}

interface DownlineOption {
  id: number;
  full_name: string;
  emp_code: string;
}

interface ProgressData {
  employee: EmployeeInfo;
  day_planner?: {
    daily: { tasks: DayPlannerData; kra: DayPlannerData };
    mtd: { tasks: DayPlannerData; kra: DayPlannerData };
    rolling_30: { tasks: DayPlannerData; kra: DayPlannerData };
  };
  tasks?: { summary: any; activities?: any[] };
  kra?: { summary: any; items?: any[] };
  attendance?: { summary: any };
  travel?: { summary: any };
  leads?: { summary: any };
  service_tickets?: { summary: any };
  overall?: any;
}

interface DayProgressEntry {
  employee_id?: number;
  full_name: string;
  emp_code: string;
  is_on_leave?: boolean;
  leave_display?: string;
  clock_in: string;
  clock_in_time?: string;
  day_planner: string;
  day_planner_detail?: string;
  planner_overall?: number;
  planner_overall_pending?: number;
  planner_overall_planned?: number;
  kra_status: string;
  kra_detail?: string;
  kra_total?: number;
  kra_completed?: number;
  kra_delayed_completed?: number;
  kra_pending_or_skipped?: number;
  day_closure: string;
  day_closure_detail?: string;
  closure_planned?: number;
  closure_closed?: number;
  closure_left?: number;
  closure_worked?: number;
  timesheet: string;
  timesheet_detail?: string;
  ts_total_time_updated?: string;
  ts_total_time_approved?: string;
  ts_entry_count?: number;
  ts_approved_count?: number;
  clock_out: string;
  clock_out_time?: string;
  hr_attendance: string;
  hr_approval?: string;
  employee_name?: string;
  leave_type?: string;
  dept_type?: string;
  dept_kpi?: Record<string, any>;
}

interface DayProgressData {
  self: DayProgressEntry;
  team: DayProgressEntry[];
  team_on_leave: DayProgressEntry[];
  has_team: boolean;
}

export class ProgressPage {
  private container: HTMLElement;
  private progressData: ProgressData | null = null;
  private dateRangeData: ProgressData | null = null;
  private dayProgressData: DayProgressData | null = null;
  private downlineOptions: DownlineOption[] = [];
  private loading: boolean = true;
  private loadingDateRange: boolean = false;
  private loadingDayProgress: boolean = false;
  private selectedDate: string = new Date().toISOString().split('T')[0];
  private selectedEmployeeId: number | null = null;
  private canViewTeam: boolean = false;
  private activeTab: 'today' | 'date-range' | 'day-progress' = 'today';
  private dateRangeFrom: string = '';
  private dateRangeTo: string = '';
  private pendingTimers: ReturnType<typeof setTimeout>[] = [];
  private teamDpSortField: string | null = null;
  private teamDpSortDir: 'asc' | 'desc' = 'asc';

  private readonly STATUS_ORDER: Record<string, number> = { done: 0, completed: 0, incomplete: 1, na: 2, pending: 3 };
  private statusRank(val: string): number { return this.STATUS_ORDER[val] !== undefined ? this.STATUS_ORDER[val] : 2; }
  private getSortValue(p: DayProgressEntry, field: string): string | number {
    if (field === 'name') return (p.full_name || '').toLowerCase();
    if (field === 'clock_in') return this.statusRank(p.clock_in);
    if (field === 'day_planner') return this.statusRank(p.day_planner);
    if (field === 'kra_status') return this.statusRank(p.kra_status);
    if (field === 'day_closure') return this.statusRank(p.day_closure);
    if (field === 'timesheet') return this.statusRank(p.timesheet);
    if (field === 'clock_out') return this.statusRank(p.clock_out);
    if (field === 'hr_attendance') return this.statusRank(p.hr_approval || 'na');
    return 0;
  }

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadProgress();
  }

  private async loadProgress(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const params = new URLSearchParams();
      params.append('date', this.selectedDate);
      if (this.selectedEmployeeId) {
        params.append('employee_id', this.selectedEmployeeId.toString());
      }

      const url = `${API_ENDPOINTS.PROGRESS.SUMMARY}?${params.toString()}`;
      console.log('[ProgressPage] Fetching:', url);
      const response = await apiService.get<any>(url);
      console.log('[ProgressPage] API response:', response);

      if (response.success && response.data) {
        this.progressData = response.data;
        this.canViewTeam = response.data.permissions?.can_view_team || false;
        this.downlineOptions = response.data.downline_options || [];
      }
    } catch (error) {
      console.error('[ProgressPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    const today = new Date();
    const monthStart = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
    if (!this.dateRangeFrom) this.dateRangeFrom = monthStart;
    if (!this.dateRangeTo) this.dateRangeTo = this.selectedDate;

    this.container.innerHTML = `
      <div class="page-container progress-page">
        ${PageHeader.render({ title: 'Progress Dashboard', showBack: true })}
        
        <!-- Filters Section -->
        <div class="progress-filters">
          <div class="filter-row">
            <div class="filter-group" id="teamMemberSection" style="display: none;">
              <label>Team Member</label>
              <select id="teamMemberFilter" class="form-select">
                <option value="">My Progress</option>
              </select>
            </div>
            <div class="filter-group">
              <label>Date</label>
              <input type="date" id="dateFilter" class="form-input" value="${this.selectedDate}">
            </div>
          </div>
          <div class="filter-actions">
            <button class="btn btn-primary btn-sm" id="refreshBtn">
              <span class="btn-icon">🔄</span> Refresh
            </button>
            <button class="btn btn-secondary btn-sm" id="exportBtn">
              <span class="btn-icon">📄</span> Export PDF
            </button>
          </div>
        </div>
        
        <!-- Tabs -->
        <div class="progress-tabs">
          <button class="progress-tab ${this.activeTab === 'today' ? 'active' : ''}" data-tab="today">
            📋 Progress
          </button>
          <button class="progress-tab ${this.activeTab === 'day-progress' ? 'active' : ''}" data-tab="day-progress">
            👥 Day Progress
          </button>
          <button class="progress-tab ${this.activeTab === 'date-range' ? 'active' : ''}" data-tab="date-range">
            📅 Date Range
          </button>
        </div>

        <div id="pageContent">
          <div class="loading-state">Loading progress data...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'Progress Dashboard', showBack: true });
    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    document.getElementById('dateFilter')?.addEventListener('change', (e) => {
      this.selectedDate = (e.target as HTMLInputElement).value;
      this.loadProgress();
    });

    document.getElementById('teamMemberFilter')?.addEventListener('change', (e) => {
      const value = (e.target as HTMLSelectElement).value;
      this.selectedEmployeeId = value ? parseInt(value) : null;
      this.loadProgress();
    });

    document.getElementById('refreshBtn')?.addEventListener('click', () => {
      this.loadProgress();
    });

    document.getElementById('exportBtn')?.addEventListener('click', () => {
      this.showToast('Export PDF coming soon');
    });

    document.querySelectorAll('.progress-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const tabId = (tab as HTMLElement).dataset.tab as 'today' | 'date-range' | 'day-progress';
        this.activeTab = tabId;
        document.querySelectorAll('.progress-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        if (tabId === 'day-progress' && !this.dayProgressData) {
          this.loadDayProgress();
        } else {
          this.updateContent();
        }
      });
    });
  }

  private showToast(message: string): void {
    const toast = document.createElement('div');
    toast.className = 'toast-message';
    toast.textContent = message;
    document.body.appendChild(toast);
    const t = setTimeout(() => toast.remove(), 3000);
    this.pendingTimers.push(t);
  }

  private async loadDateRangeReport(): Promise<void> {
    if (!this.dateRangeFrom || !this.dateRangeTo) return;

    this.loadingDateRange = true;
    this.updateContent();

    try {
      const params = new URLSearchParams();
      params.append('date_from', this.dateRangeFrom);
      params.append('date_to', this.dateRangeTo);
      if (this.selectedEmployeeId) {
        params.append('employee_id', this.selectedEmployeeId.toString());
      }

      const url = `${API_ENDPOINTS.PROGRESS.SUMMARY}?${params.toString()}`;
      const response = await apiService.get<any>(url);

      if (response.success && response.data) {
        this.dateRangeData = response.data;
      }
    } catch (error) {
      console.error('[ProgressPage] Failed to load date range:', error);
    }

    this.loadingDateRange = false;
    this.updateContent();
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading progress data...</div>';
      return;
    }

    // Show/hide team member filter based on permissions
    const teamSection = document.getElementById('teamMemberSection');
    if (teamSection) {
      teamSection.style.display = this.canViewTeam && this.downlineOptions.length > 0 ? 'block' : 'none';
    }

    // Update team member dropdown
    const teamFilter = document.getElementById('teamMemberFilter') as HTMLSelectElement;
    if (teamFilter && this.canViewTeam && this.downlineOptions.length > 0) {
      teamFilter.innerHTML = '<option value="">My Progress</option>' +
        this.downlineOptions.map(emp => 
          `<option value="${emp.id}" ${this.selectedEmployeeId === emp.id ? 'selected' : ''}>${emp.full_name} (${emp.emp_code})</option>`
        ).join('');
    }

    if (this.activeTab === 'day-progress') {
      content.innerHTML = this.renderDayProgress();
      this.attachDayProgressListeners();
      return;
    }

    if (!this.progressData) {
      content.innerHTML = '<div class="empty-state">No progress data available</div>';
      return;
    }

    const emp = this.progressData.employee;
    
    const dayPlanner = this.progressData.day_planner || this.buildDayPlannerFromLegacy();

    content.innerHTML = `
      <div class="employee-banner">
        <div class="employee-avatar-circle">${this.getInitials(emp.full_name)}</div>
        <div class="employee-details">
          <span class="emp-code">${emp.emp_code}</span>
          <span class="separator">|</span>
          <span class="emp-level">${emp.level || emp.designation || emp.role || 'Staff'}</span>
          <span class="separator">|</span>
          <span class="emp-dept">${emp.department || 'Management'}</span>
        </div>
      </div>

      <div class="day-planner-section">
        <h3 class="section-header">📋 Day Planner Summary</h3>
        
        <div class="planner-period">
          <div class="period-badge daily">📌 Daily</div>
          <div class="planner-grid">
            ${this.renderPlannerColumns(dayPlanner.daily.tasks, false)}
          </div>
          <div class="planner-grid">
            ${this.renderPlannerColumns(dayPlanner.daily.kra, true)}
          </div>
        </div>

        ${this.renderAttendanceCard()}
        ${this.renderDayPlannerCard()}
        ${this.renderDayClosureCard()}
        ${this.renderTimesheetCard()}
        ${this.renderDeptKpiCard()}

        <div class="planner-period">
          <div class="period-badge mtd">📅 Month to Date (MTD)</div>
          <div class="planner-grid">
            ${this.renderPlannerColumns(dayPlanner.mtd.tasks, false)}
          </div>
          <div class="planner-grid">
            ${this.renderPlannerColumns(dayPlanner.mtd.kra, true)}
          </div>
        </div>

        <div class="planner-period">
          <div class="period-badge rolling">🔄 Rolling 30 Days</div>
          <div class="planner-grid">
            ${this.renderPlannerColumns(dayPlanner.rolling_30.tasks, false)}
          </div>
          <div class="planner-grid">
            ${this.renderPlannerColumns(dayPlanner.rolling_30.kra, true)}
          </div>
        </div>
      </div>

      ${this.activeTab === 'date-range' ? this.renderDateRangeReport() : ''}
    `;

    // Attach date range event listeners if on that tab
    if (this.activeTab === 'date-range') {
      document.getElementById('rangeFrom')?.addEventListener('change', (e) => {
        this.dateRangeFrom = (e.target as HTMLInputElement).value;
      });

      document.getElementById('rangeTo')?.addEventListener('change', (e) => {
        this.dateRangeTo = (e.target as HTMLInputElement).value;
      });

      document.getElementById('generateReportBtn')?.addEventListener('click', () => {
        this.loadDateRangeReport();
      });
    }
  }

  private buildDayPlannerFromLegacy(): any {
    const tasks = this.progressData?.tasks?.summary || { planned: 0, completed: 0, pending: 0, overdue: 0 };
    const kra = this.progressData?.kra?.summary || { total_instances: 0, submitted: 0, pending: 0, avg_score: 0 };
    const overall = this.progressData?.overall;
    
    const createData = (t: any, isKra: boolean): DayPlannerData => ({
      planned: isKra ? (t.total_instances || t.total || 0) : (t.planned || 0),
      done: isKra ? (t.submitted || t.met || 0) : (t.completed || t.done || 0),
      pending: t.pending || 0,
      overdue: isKra ? (t.missed || 0) : (t.overdue || 0),
      percent_done: 0,
      total: isKra ? (t.total_instances || t.total || 0) : (t.planned || 0),
      met: isKra ? (t.submitted || t.met || 0) : (t.completed || t.done || 0),
      missed: isKra ? (t.missed || 0) : (t.overdue || 0)
    });

    const mtdTasks = overall?.mtd?.tasks || tasks;
    const mtdKra = overall?.mtd?.kra || kra;
    const rollingTasks = overall?.rolling_30?.tasks || tasks;
    const rollingKra = overall?.rolling_30?.kra || kra;

    return {
      daily: {
        tasks: createData(tasks, false),
        kra: createData(kra, true)
      },
      mtd: {
        tasks: createData(mtdTasks, false),
        kra: createData(mtdKra, true)
      },
      rolling_30: {
        tasks: createData(rollingTasks, false),
        kra: createData(rollingKra, true)
      }
    };
  }

  private getStatusBadge(status: string): string {
    const map: Record<string, { cls: string; icon: string; label: string }> = {
      'done': { cls: 'badge-success', icon: '✅', label: 'Done' },
      'completed': { cls: 'badge-success', icon: '✅', label: 'Completed' },
      'pending': { cls: 'badge-warning', icon: '⏳', label: 'Pending' },
      'na': { cls: 'badge-muted', icon: '➖', label: 'N/A' },
    };
    const s = map[status] || map['na'];
    return `<span class="progress-badge ${s.cls}">${s.icon} ${s.label}</span>`;
  }

  private renderDayPlannerCard(): string {
    const dp = (this.progressData as any)?.day_progress;
    if (!dp) return '';
    const pOverall = dp.planner_overall || 0;
    const pPending = dp.planner_overall_pending || 0;
    const pPlanned = dp.planner_overall_planned || 0;
    if (pOverall === 0 && pPlanned === 0 && dp.day_planner === 'na') return '';
    return `
      <div class="progress-detail-card">
        <div class="detail-card-header">
          <span class="detail-card-title">📋 Day Planning</span>
          ${this.getStatusBadge(dp.day_planner)}
        </div>
        <div class="detail-card-metrics">
          <div class="metric-col">
            <div class="metric-value" style="color:#6b7280;">${pOverall}</div>
            <div class="metric-label">Overall</div>
          </div>
          <div class="metric-divider">/</div>
          <div class="metric-col">
            <div class="metric-value" style="color:#f59e0b;">${pPending}</div>
            <div class="metric-label">Pending</div>
          </div>
          <div class="metric-divider">/</div>
          <div class="metric-col">
            <div class="metric-value" style="color:#16a34a;">${pPlanned}</div>
            <div class="metric-label">Planned</div>
          </div>
        </div>
      </div>
    `;
  }

  private renderDayClosureCard(): string {
    const dp = (this.progressData as any)?.day_progress;
    if (!dp) return '';
    const cPlanned = dp.closure_planned || 0;
    const cClosed = dp.closure_closed || 0;
    const cLeft = dp.closure_left || 0;
    const cWorked = dp.closure_worked || 0;
    if (cPlanned === 0 && dp.day_closure === 'na') return '';
    return `
      <div class="progress-detail-card">
        <div class="detail-card-header">
          <span class="detail-card-title">🔒 Day End / Closure</span>
          ${this.getStatusBadge(dp.day_closure)}
        </div>
        <div class="detail-card-metrics">
          <div class="metric-col">
            <div class="metric-value" style="color:#6b7280;">${cPlanned}</div>
            <div class="metric-label">Planned</div>
          </div>
          <div class="metric-divider">/</div>
          <div class="metric-col">
            <div class="metric-value" style="color:#16a34a;">${cClosed}</div>
            <div class="metric-label">Closed</div>
          </div>
          <div class="metric-divider">/</div>
          <div class="metric-col">
            <div class="metric-value" style="color:#dc2626;">${cLeft}</div>
            <div class="metric-label">Left</div>
          </div>
          <div class="metric-divider">/</div>
          <div class="metric-col">
            <div class="metric-value" style="color:#3b82f6;">${cWorked}</div>
            <div class="metric-label">Worked</div>
          </div>
        </div>
      </div>
    `;
  }

  private renderPlannerColumns(data: DayPlannerData, isKra: boolean): string {
    const total = (data.done || 0) + (data.pending || 0) + (data.overdue || 0);
    const percentDone = total > 0 ? Math.round(((data.done || 0) / total) * 100) : 0;

    return `
      <div class="planner-col planned">
        <div class="col-icon">📊</div>
        <div class="col-value">${isKra ? (data.total || 0) : (data.planned || 0)}</div>
        <div class="col-label">${isKra ? 'TOTAL' : 'PLANNED'}</div>
      </div>
      <div class="planner-col done">
        <div class="col-icon">✅</div>
        <div class="col-value">${isKra ? (data.met || data.done || 0) : (data.done || 0)}</div>
        <div class="col-label">${isKra ? 'MET' : 'DONE'}</div>
      </div>
      <div class="planner-col pending">
        <div class="col-icon">⏳</div>
        <div class="col-value">${data.pending || 0}</div>
        <div class="col-label">PENDING</div>
      </div>
      <div class="planner-col overdue">
        <div class="col-icon">❌</div>
        <div class="col-value">${isKra ? (data.missed || 0) : (data.overdue || 0)}</div>
        <div class="col-label">${isKra ? 'MISSED' : 'OVERDUE'}</div>
      </div>
      <div class="planner-col percent ${percentDone >= 100 ? 'complete' : percentDone > 0 ? 'partial' : 'zero'}">
        <div class="col-icon">📈</div>
        <div class="col-value">${percentDone}%</div>
        <div class="col-label">% DONE</div>
      </div>
    `;
  }

  private renderDateRangeReport(): string {
    if (this.loadingDateRange) {
      return `
        <div class="date-range-section">
          <h3 class="section-header">📊 Date Range Report</h3>
          <div class="loading-state">Loading report...</div>
        </div>
      `;
    }

    const reportContent = this.dateRangeData ? this.renderDateRangeContent() : `
      <div class="report-placeholder">
        <div class="placeholder-icon">📋</div>
        <p>Select date range and click Generate Report</p>
      </div>
    `;

    return `
      <div class="date-range-section">
        <h3 class="section-header">📊 Date Range Report</h3>
        <div class="date-range-filters">
          <div class="filter-group">
            <label>From Date</label>
            <input type="date" class="form-input" id="rangeFrom" value="${this.dateRangeFrom}">
          </div>
          <div class="filter-group">
            <label>To Date</label>
            <input type="date" class="form-input" id="rangeTo" value="${this.dateRangeTo}">
          </div>
        </div>
        <button class="btn btn-primary btn-block" id="generateReportBtn">Generate Report</button>
        ${reportContent}
      </div>
    `;
  }

  private renderDateRangeContent(): string {
    if (!this.dateRangeData) return '';

    const dayPlanner = this.dateRangeData.day_planner || this.buildDayPlannerFromData(this.dateRangeData);
    
    return `
      <div class="date-range-results">
        <div class="planner-period">
          <div class="period-badge mtd">📅 Selected Period</div>
          <div class="planner-grid">
            ${this.renderPlannerColumns(dayPlanner.mtd.tasks, false)}
          </div>
          <div class="planner-grid">
            ${this.renderPlannerColumns(dayPlanner.mtd.kra, true)}
          </div>
        </div>
      </div>
    `;
  }

  private buildDayPlannerFromData(data: ProgressData): any {
    const tasks = data.tasks?.summary || { planned: 0, completed: 0, pending: 0, overdue: 0 };
    const kra = data.kra?.summary || { total_instances: 0, submitted: 0, pending: 0, avg_score: 0 };
    const overall = data.overall;
    
    const createData = (t: any, isKra: boolean): DayPlannerData => ({
      planned: isKra ? (t.total_instances || t.total || 0) : (t.planned || 0),
      done: isKra ? (t.submitted || t.met || 0) : (t.completed || t.done || 0),
      pending: t.pending || 0,
      overdue: isKra ? (t.missed || 0) : (t.overdue || 0),
      percent_done: 0,
      total: isKra ? (t.total_instances || t.total || 0) : (t.planned || 0),
      met: isKra ? (t.submitted || t.met || 0) : (t.completed || t.done || 0),
      missed: isKra ? (t.missed || 0) : (t.overdue || 0)
    });

    const mtdTasks = overall?.mtd?.tasks || tasks;
    const mtdKra = overall?.mtd?.kra || kra;

    return {
      daily: { tasks: createData(tasks, false), kra: createData(kra, true) },
      mtd: { tasks: createData(mtdTasks, false), kra: createData(mtdKra, true) },
      rolling_30: { tasks: createData(tasks, false), kra: createData(kra, true) }
    };
  }

  private getInitials(name: string): string {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .substring(0, 2)
      .toUpperCase();
  }

  private async loadDayProgress(): Promise<void> {
    this.loadingDayProgress = true;
    this.updateContent();

    try {
      const url = `${API_ENDPOINTS.DAY_PLANNER.DAY_PROGRESS}?plan_date=${this.selectedDate}`;
      const response = await apiService.get<any>(url);
      if (response.success && response.data) {
        this.dayProgressData = response.data;
      }
    } catch (error) {
      console.error('[ProgressPage] Failed to load day progress:', error);
    }

    this.loadingDayProgress = false;
    this.updateContent();
  }

  private attachDayProgressListeners(): void {
    document.getElementById('dpDatePicker')?.addEventListener('change', (e) => {
      this.selectedDate = (e.target as HTMLInputElement).value;
      this.dayProgressData = null;
      this.loadDayProgress();
    });

    document.getElementById('dpTodayQuick')?.addEventListener('click', () => {
      this.selectedDate = new Date().toISOString().split('T')[0];
      const picker = document.getElementById('dpDatePicker') as HTMLInputElement;
      if (picker) picker.value = this.selectedDate;
      this.dayProgressData = null;
      this.loadDayProgress();
    });

    document.getElementById('dpRefreshBtn')?.addEventListener('click', () => {
      this.dayProgressData = null;
      this.loadDayProgress();
    });

    document.getElementById('dpTeamGrid')?.addEventListener('click', (e) => {
      const col = (e.target as HTMLElement).closest('[data-sort]') as HTMLElement | null;
      if (!col) return;
      const field = col.dataset['sort']!;
      if (this.teamDpSortField === field) {
        this.teamDpSortDir = this.teamDpSortDir === 'asc' ? 'desc' : 'asc';
      } else {
        this.teamDpSortField = field;
        this.teamDpSortDir = 'asc';
      }
      this.updateContent();
      setTimeout(() => this.attachDayProgressListeners(), 0);
    });
  }

  private renderDayProgress(): string {
    if (this.loadingDayProgress) {
      return '<div class="loading-state">Loading day progress...</div>';
    }
    if (!this.dayProgressData) {
      return '<div class="empty-state">No day progress data available</div>';
    }

    const dp = this.dayProgressData;
    const selfHtml = dp.self
      ? (dp.self.is_on_leave ? this.renderLeaveRow(dp.self) : this.renderProgressRow(dp.self, true))
      : '';

    let sortedTeam = (dp.team || []).slice();
    if (this.teamDpSortField) {
      const field = this.teamDpSortField;
      const dir = this.teamDpSortDir;
      sortedTeam.sort((a, b) => {
        const av = this.getSortValue(a, field);
        const bv = this.getSortValue(b, field);
        if (av < bv) return dir === 'asc' ? -1 : 1;
        if (av > bv) return dir === 'asc' ? 1 : -1;
        return 0;
      });
    }
    const teamRows = sortedTeam.map(m => this.renderProgressRow(m, false)).join('');
    const onLeave = dp.team_on_leave || [];

    const si = (f: string) => {
      if (this.teamDpSortField !== f) return '<span style="opacity:0.4;font-size:9px;">⇅</span>';
      return `<span style="color:#818cf8;font-size:9px;">${this.teamDpSortDir === 'asc' ? '↑' : '↓'}</span>`;
    };

    const myGridHeader = `
      <div class="dp-grid-header">
        <span class="dp-gh">Name</span>
        <span class="dp-gh">Clock In</span>
        <span class="dp-gh">Planner</span>
        <span class="dp-gh">KRA</span>
        <span class="dp-gh">Closure</span>
        <span class="dp-gh">Timesheet</span>
        <span class="dp-gh">Clock Out</span>
        <span class="dp-gh">HR Att.</span>
      </div>`;
    const teamGridHeader = `
      <div class="dp-grid-header">
        <span class="dp-gh dp-sort-col" data-sort="name" style="cursor:pointer;">Name ${si('name')}</span>
        <span class="dp-gh dp-sort-col" data-sort="clock_in" style="cursor:pointer;">Clock In ${si('clock_in')}</span>
        <span class="dp-gh dp-sort-col" data-sort="day_planner" style="cursor:pointer;">Planner ${si('day_planner')}</span>
        <span class="dp-gh dp-sort-col" data-sort="kra_status" style="cursor:pointer;">KRA ${si('kra_status')}</span>
        <span class="dp-gh dp-sort-col" data-sort="day_closure" style="cursor:pointer;">Closure ${si('day_closure')}</span>
        <span class="dp-gh dp-sort-col" data-sort="timesheet" style="cursor:pointer;">Timesheet ${si('timesheet')}</span>
        <span class="dp-gh dp-sort-col" data-sort="clock_out" style="cursor:pointer;">Clock Out ${si('clock_out')}</span>
        <span class="dp-gh dp-sort-col" data-sort="hr_attendance" style="cursor:pointer;">HR Att. ${si('hr_attendance')}</span>
      </div>`;

    return `
      <div class="day-progress-section">
        <div class="dp-date-row">
          <input type="date" class="dp-date-picker" id="dpDatePicker" value="${this.selectedDate}">
          <button class="dp-today-quick" id="dpTodayQuick">Today</button>
          <button class="dp-refresh-btn" id="dpRefreshBtn">🔄</button>
        </div>
        <h3 class="section-header">👤 My Progress</h3>
        <div class="dp-grid-scroll">
          ${myGridHeader}
          ${selfHtml}
        </div>

        ${dp.has_team && (dp.team || []).length > 0 ? `
          <h3 class="section-header" style="margin-top:16px;">👥 Team Progress (${dp.team.length})</h3>
          <div class="dp-grid-scroll" id="dpTeamGrid">
            ${teamGridHeader}
            ${teamRows}
          </div>
        ` : (!dp.has_team ? '' : `
          <h3 class="section-header" style="margin-top:16px;">👥 Team Progress</h3>
          <div class="dp-grid-scroll">
            <div class="empty-state" style="padding:16px;">All team members are on leave</div>
          </div>
        `)}

        ${onLeave.length > 0 ? `
          <h3 class="section-header" style="margin-top:16px;">🏠 On Leave (${onLeave.length})</h3>
          <div class="dp-leave-list">
            ${onLeave.map(m => `
              <div class="dp-leave-card">
                <span class="dp-leave-name">${this.escapeHtml(m.full_name || m.employee_name || '')}</span>
                <span class="dp-leave-code">${m.emp_code}</span>
                <span class="dp-leave-type">${this.getLeaveLabel(m)}</span>
              </div>
            `).join('')}
          </div>
        ` : ''}
      </div>
    `;
  }

  private renderLeaveRow(entry: DayProgressEntry): string {
    const name = entry.full_name || entry.employee_name || '';
    const leaveLabel = entry.leave_display || 'On Leave';
    let cls = 'dp-leave-info';
    if (leaveLabel.includes('Sick')) cls = 'dp-leave-sick';
    else if (leaveLabel.includes('Casual')) cls = 'dp-leave-casual';
    else if (leaveLabel.includes('Unpaid')) cls = 'dp-leave-unpaid';
    else if (leaveLabel.includes('Holiday') || leaveLabel.includes('Weekend')) cls = 'dp-leave-holiday';

    return `
      <div class="dp-grid-row dp-grid-self dp-grid-leave">
        <span class="dp-gc dp-gc-name">
          <strong>${this.escapeHtml(name.split(' ')[0])}</strong>
          <small>${entry.emp_code}</small>
        </span>
        <span class="dp-gc dp-gc-leave-span" style="grid-column: span 7; text-align: center;">
          <span class="dp-leave-badge ${cls}">📅 ${this.escapeHtml(leaveLabel)}</span>
        </span>
      </div>
    `;
  }

  private renderProgressRow(entry: DayProgressEntry, isSelf: boolean): string {
    const name = entry.full_name || entry.employee_name || '';
    return `
      <div class="dp-grid-row ${isSelf ? 'dp-grid-self' : ''}">
        <span class="dp-gc dp-gc-name">
          <strong>${this.escapeHtml(name.split(' ')[0])}</strong>
          <small>${entry.emp_code}</small>
        </span>
        <span class="dp-gc">${this.progressBadge(entry.clock_in, entry.clock_in_time)}</span>
        <span class="dp-gc">${this.progressBadge(entry.day_planner, entry.day_planner_detail)}${this.plannerDetail(entry)}</span>
        <span class="dp-gc">${this.progressBadge(entry.kra_status, entry.kra_detail)}${this.kraDetail(entry)}</span>
        <span class="dp-gc">${this.progressBadge(entry.day_closure, entry.day_closure_detail)}${this.closureDetail(entry)}</span>
        <span class="dp-gc">${this.progressBadge(entry.timesheet, entry.timesheet_detail)}${this.timesheetDetail(entry)}</span>
        <span class="dp-gc">${this.progressBadge(entry.clock_out, entry.clock_out_time)}</span>
        <span class="dp-gc">${this.hrBadge(entry.hr_attendance, entry.hr_approval)}</span>
      </div>
      ${isSelf ? this.deptKpiDetail(entry) : ''}
    `;
  }

  private progressBadge(status: string, detail?: string): string {
    const s = (status || 'na').toLowerCase();
    let cls = 'dp-pb-na';
    let icon = '➖';
    if (s === 'done' || s === 'completed' || s === 'present') { cls = 'dp-pb-done'; icon = '✅'; }
    else if (s === 'incomplete' || s === 'partial') { cls = 'dp-pb-warn'; icon = '⚠️'; }
    else if (s === 'pending' || s === 'absent') { cls = 'dp-pb-pending'; icon = '❌'; }
    return `<span class="dp-pb ${cls}">${icon}</span>${detail ? `<small class="dp-pb-detail">${detail}</small>` : ''}`;
  }

  private hrBadge(status: string, approval?: string): string {
    const hrVal = (status || 'na').toLowerCase();
    const hrApproval = (approval || 'na').toLowerCase();

    if (hrVal === 'na' || hrApproval === 'na') {
      return '<span class="dp-hr-badge dp-hr-na">N/A</span>';
    }
    if (hrApproval === 'pending') {
      return '<span class="dp-hr-badge dp-hr-pending">⏳ Pending</span>';
    }
    if (hrApproval === 'rejected') {
      return '<span class="dp-hr-badge dp-hr-absent">❌ Rejected</span>';
    }
    if (hrApproval === 'on_hold') {
      return '<span class="dp-hr-badge dp-hr-half">⏸️ On Hold</span>';
    }

    if (hrVal === 'present') return '<span class="dp-hr-badge dp-hr-present">Present</span>';
    if (hrVal === 'half_day') return '<span class="dp-hr-badge dp-hr-half">Half Day</span>';
    if (hrVal === 'absent') return '<span class="dp-hr-badge dp-hr-absent">Absent</span>';
    if (hrVal === 'sick_leave') return '<span class="dp-hr-badge dp-hr-leave">Sick Leave</span>';
    if (hrVal === 'casual_leave') return '<span class="dp-hr-badge dp-hr-leave">Casual Leave</span>';
    if (hrVal === 'approved_leave') return '<span class="dp-hr-badge dp-hr-leave">Approved Leave</span>';
    if (hrVal === 'unpaid_leave') return '<span class="dp-hr-badge dp-hr-na">Unpaid Leave</span>';
    if (hrVal === 'holiday' || hrVal === 'weekend') return '<span class="dp-hr-badge dp-hr-holiday">Holiday</span>';

    return `<span class="dp-hr-badge dp-hr-na">${status || 'N/A'}</span>`;
  }

  private plannerDetail(e: DayProgressEntry): string {
    if (e.day_planner === 'na') return '';
    const overall = e.planner_overall || 0;
    const pending = e.planner_overall_pending || 0;
    const planned = e.planner_overall_planned || 0;
    if (overall === 0 && planned === 0) return '';
    return `<small class="dp-detail-line"><span class="dp-d-grey">${overall}</span> / <span class="dp-d-yellow">${pending}</span> / <span class="dp-d-green">${planned}</span></small><small class="dp-detail-label">Overall / Pending / Planned</small>`;
  }

  private kraDetail(e: DayProgressEntry): string {
    if (e.kra_status === 'na') return '';
    const total = e.kra_total || 0;
    if (total === 0) return '';
    const completed = e.kra_completed || 0;
    const delayed = e.kra_delayed_completed || 0;
    const pendSkip = e.kra_pending_or_skipped || 0;
    return `<small class="dp-detail-line"><span class="dp-d-grey">${total}</span> / <span class="dp-d-green">${completed}</span> / <span class="dp-d-red">${delayed}</span> / <span class="dp-d-yellow">${pendSkip}</span></small><small class="dp-detail-label">Total / Done / Delayed / Pend</small>`;
  }

  private closureDetail(e: DayProgressEntry): string {
    if (e.day_closure === 'na') return '';
    const planned = e.closure_planned || 0;
    const closed = e.closure_closed || 0;
    const left = e.closure_left || 0;
    const worked = e.closure_worked || 0;
    if (planned === 0 && e.day_closure === 'na') return '';
    return `<small class="dp-detail-line"><span class="dp-d-grey">${planned}</span> / <span class="dp-d-green">${closed}</span> / <span class="dp-d-red">${left}</span> / <span class="dp-d-blue">${worked}</span></small><small class="dp-detail-label">Planned / Closed / Left / Worked</small>`;
  }

  private timesheetDetail(e: DayProgressEntry): string {
    if (e.timesheet === 'na') return '';
    const tsEntries = e.ts_entry_count || 0;
    if (tsEntries === 0 && e.timesheet === 'na') return '';
    const updated = e.ts_total_time_updated || '0h 0m';
    const approved = e.ts_total_time_approved || '0h 0m';
    return `<small class="dp-detail-line"><span class="dp-d-blue">${updated}</span> / <span class="dp-d-green">${approved}</span></small><small class="dp-detail-label">Logged / Approved</small>`;
  }

  private renderAttendanceCard(): string {
    const att = (this.progressData as any)?.attendance;
    if (!att?.today) return '';
    const today = att.today;
    const clockIn = today.clock_in || '—';
    const clockOut = today.clock_out || '—';
    const worked = today.worked || '—';
    const status = today.status || 'absent';
    if (clockIn === '—' && worked === '—') return '';
    const statusKey = (status === 'present' || status === 'work_from_home' || status === 'on_duty') ? 'done' : (status === 'absent' ? 'pending' : 'na');
    return `
      <div class="progress-detail-card">
        <div class="detail-card-header">
          <span class="detail-card-title">🕐 Attendance</span>
          ${this.getStatusBadge(statusKey)}
        </div>
        <div class="detail-card-metrics">
          <div class="metric-col">
            <div class="metric-value" style="color:#22d3ee; font-size:1.1rem;">${clockIn}</div>
            <div class="metric-label">Clock In</div>
          </div>
          <div class="metric-divider">/</div>
          <div class="metric-col">
            <div class="metric-value" style="color:#f87171; font-size:1.1rem;">${clockOut}</div>
            <div class="metric-label">Clock Out</div>
          </div>
          <div class="metric-divider">/</div>
          <div class="metric-col">
            <div class="metric-value" style="color:#4ade80; font-size:1.1rem;">${worked}</div>
            <div class="metric-label">Worked</div>
          </div>
        </div>
      </div>
    `;
  }

  private renderTimesheetCard(): string {
    const tsSummary = (this.progressData as any)?.timesheet?.summary;
    const dpTs = (this.progressData as any)?.day_progress;
    const mtdTs = (this.progressData as any)?.overall?.mtd?.timesheet;
    if (!tsSummary) return '';
    const totalLogged = tsSummary.total_hours || '0h 0m';
    const submitted = tsSummary.submitted_hours || '0h 0m';
    const approved = tsSummary.approved_hours || '0h 0m';
    if (totalLogged === '0h 0m' && (!dpTs?.timesheet || dpTs.timesheet === 'na')) return '';
    const tsStatus = dpTs?.timesheet || 'na';
    const mtdAvg = mtdTs?.avg_hours_per_day || null;
    const mtdSubAvg = mtdTs?.submitted_avg_per_day || null;
    const mtdAprAvg = mtdTs?.approved_avg_per_day || null;
    return `
      <div class="progress-detail-card">
        <div class="detail-card-header">
          <span class="detail-card-title">🕒 Timesheet</span>
          ${this.getStatusBadge(tsStatus)}
        </div>
        <div class="detail-card-metrics">
          <div class="metric-col">
            <div class="metric-value" style="color:#3b82f6;">${totalLogged}</div>
            <div class="metric-label">Logged</div>
          </div>
          <div class="metric-divider">/</div>
          <div class="metric-col">
            <div class="metric-value" style="color:#f59e0b;">${submitted}</div>
            <div class="metric-label">Submitted</div>
          </div>
          <div class="metric-divider">/</div>
          <div class="metric-col">
            <div class="metric-value" style="color:#16a34a;">${approved}</div>
            <div class="metric-label">Approved</div>
          </div>
        </div>
        ${mtdAvg ? `
        <div class="dept-kpi-divider"><span class="dept-kpi-period">📅 MTD Overview</span></div>
        <div class="detail-card-metrics">
          <div class="metric-col">
            <div class="metric-value" style="color:#818cf8; font-size:1rem;">${mtdAvg}</div>
            <div class="metric-label">Avg / Day</div>
          </div>
          <div class="metric-divider">/</div>
          <div class="metric-col">
            <div class="metric-value" style="color:#f59e0b; font-size:1rem;">${mtdSubAvg || '—'}</div>
            <div class="metric-label">Submitted Avg</div>
          </div>
          <div class="metric-divider">/</div>
          <div class="metric-col">
            <div class="metric-value" style="color:#6ee7b7; font-size:1rem;">${mtdAprAvg || '—'}</div>
            <div class="metric-label">Approved Avg</div>
          </div>
        </div>
        ` : ''}
      </div>
    `;
  }

  private renderDeptKpiCard(): string {
    const kpi = (this.progressData as any)?.dept_kpi;
    const dt = (this.progressData as any)?.dept_type;
    const mtdKpi = (this.progressData as any)?.overall?.mtd?.dept_kpi;
    if (!dt || dt === 'other' || !kpi) return '';

    const fmtCurrency = (v: number): string => {
      if (v >= 10000000) return `₹${(v / 10000000).toFixed(1)}Cr`;
      if (v >= 100000) return `₹${(v / 100000).toFixed(1)}L`;
      if (v >= 1000) return `₹${(v / 1000).toFixed(1)}K`;
      return `₹${Math.round(v)}`;
    };

    if (dt === 'sales') {
      const talk = (kpi['talk_time_formatted'] as string) || '0h 0m';
      const handled = kpi['leads_handled_today'] ?? 0;
      const newLeads = kpi['leads_new_today'] ?? 0;
      const won = kpi['leads_won_today'] ?? 0;
      const lost = kpi['leads_lost_today'] ?? 0;
      const dealVal = kpi['deal_value_today'] ?? 0;
      const dealRcv = kpi['deal_value_received_today'] ?? 0;
      const overdue = kpi['overdue_leads'] ?? 0;

      const mtdTalk = (mtdKpi?.['talk_time_formatted'] as string) || null;
      const mtdTalkAvg = (mtdKpi?.['talk_time_avg_formatted'] as string) || null;
      const mtdHandled = mtdKpi?.['leads_handled'] ?? null;
      const mtdNew = mtdKpi?.['leads_new'] ?? null;
      const mtdWon = mtdKpi?.['leads_won'] ?? null;
      const mtdLost = mtdKpi?.['leads_lost'] ?? null;
      const mtdDealClosed = mtdKpi?.['deal_value_closed'] ?? null;
      const mtdDealRcv = mtdKpi?.['deal_value_received'] ?? null;

      return `
        <div class="progress-detail-card dept-kpi-card" style="border-left: 4px solid #818cf8;">
          <div class="detail-card-header">
            <span class="detail-card-title">📊 Sales KPIs</span>
            <span class="dept-kpi-period">Today</span>
          </div>
          <div class="dept-kpi-grid">
            <div class="dkg-item"><div class="dkg-val" style="color:#818cf8;">${talk}</div><div class="dkg-lbl">Talk Time</div></div>
            <div class="dkg-item"><div class="dkg-val" style="color:#22d3ee;">${handled}</div><div class="dkg-lbl">Handled</div></div>
            <div class="dkg-item"><div class="dkg-val" style="color:#60a5fa;">${newLeads}</div><div class="dkg-lbl">New Leads</div></div>
            <div class="dkg-item"><div class="dkg-val" style="color:#4ade80;">${won}</div><div class="dkg-lbl">Won</div></div>
            <div class="dkg-item"><div class="dkg-val" style="color:#f87171;">${lost}</div><div class="dkg-lbl">Lost</div></div>
            <div class="dkg-item"><div class="dkg-val" style="color:#f59e0b;">${overdue}</div><div class="dkg-lbl">Overdue</div></div>
            ${dealVal > 0 ? `<div class="dkg-item"><div class="dkg-val" style="color:#a3e635;">${fmtCurrency(dealVal)}</div><div class="dkg-lbl">Value</div></div>` : ''}
            ${dealRcv > 0 ? `<div class="dkg-item"><div class="dkg-val" style="color:#34d399;">${fmtCurrency(dealRcv)}</div><div class="dkg-lbl">Received</div></div>` : ''}
          </div>
          ${mtdTalk ? `
          <div class="dept-kpi-divider"><span class="dept-kpi-period">📅 MTD</span></div>
          <div class="dept-kpi-grid">
            ${mtdTalkAvg ? `<div class="dkg-item"><div class="dkg-val" style="color:#a5b4fc;">${mtdTalkAvg}</div><div class="dkg-lbl">Talk Avg/Day</div></div>` : ''}
            ${mtdHandled !== null ? `<div class="dkg-item"><div class="dkg-val" style="color:#22d3ee;">${mtdHandled}</div><div class="dkg-lbl">Handled</div></div>` : ''}
            ${mtdNew !== null ? `<div class="dkg-item"><div class="dkg-val" style="color:#60a5fa;">${mtdNew}</div><div class="dkg-lbl">New Leads</div></div>` : ''}
            ${mtdWon !== null ? `<div class="dkg-item"><div class="dkg-val" style="color:#4ade80;">${mtdWon}</div><div class="dkg-lbl">Won</div></div>` : ''}
            ${mtdLost !== null ? `<div class="dkg-item"><div class="dkg-val" style="color:#f87171;">${mtdLost}</div><div class="dkg-lbl">Lost</div></div>` : ''}
            ${mtdDealClosed !== null && (mtdDealClosed as number) > 0 ? `<div class="dkg-item"><div class="dkg-val" style="color:#a3e635;">${fmtCurrency(mtdDealClosed as number)}</div><div class="dkg-lbl">Deal Closed</div></div>` : ''}
            ${mtdDealRcv !== null && (mtdDealRcv as number) > 0 ? `<div class="dkg-item"><div class="dkg-val" style="color:#34d399;">${fmtCurrency(mtdDealRcv as number)}</div><div class="dkg-lbl">Received</div></div>` : ''}
          </div>
          ` : ''}
        </div>
      `;
    }

    const tiles: [string, string, string][] = [];
    if (dt === 'service') {
      tiles.push(
        ['Tickets', String(kpi['tickets_handled'] ?? 0), '#38bdf8'],
        ['In TAT%', kpi['within_tat_pct'] != null ? kpi['within_tat_pct'] + '%' : '—', '#4ade80'],
        ['Abv TAT', String(kpi['above_tat_count'] ?? 0), '#f87171']
      );
    } else if (dt === 'procurement') {
      tiles.push(
        ['Rcvd', String(kpi['received_today_count'] ?? 0), '#4ade80'],
        ['Pending', String(kpi['pending_count'] ?? 0), '#fbbf24'],
        ['Abv TAT', String(kpi['above_tat_count'] ?? 0), '#f87171']
      );
    } else {
      return '';
    }

    return `
      <div class="progress-detail-card dept-kpi-card" style="border-left: 4px solid ${tiles[0][2]};">
        <div class="detail-card-header">
          <span class="detail-card-title">📊 Dept KPIs (${dt.charAt(0).toUpperCase() + dt.slice(1)})</span>
        </div>
        <div class="detail-card-metrics" style="justify-content: space-around; padding: 10px 0;">
          ${tiles.map(([l, v, c]) => `
            <div class="metric-col">
              <div class="metric-value" style="color:${c}; font-size: 1.2rem;">${v}</div>
              <div class="metric-label">${l}</div>
            </div>
          `).join('<div class="metric-divider">|</div>')}
        </div>
      </div>
    `;
  }

  private deptKpiDetail(e: DayProgressEntry, isFullCard: boolean = false): string {
    const dt = e.dept_type || 'other';
    const kpi = e.dept_kpi || {};
    if (dt === 'other' || !e.dept_kpi) return '';
    let tiles: [string, string, string][] = [];
    if (dt === 'sales') {
      tiles = [
        ['Talk', (kpi['talk_time_formatted'] as string) || '0h 0m', '#818cf8'],
        ['Leads', String(kpi['leads_handled_today'] ?? 0), '#22d3ee'],
        ['Overdue', String(kpi['overdue_leads'] ?? 0), '#f87171'],
      ];
    } else if (dt === 'service') {
      tiles = [
        ['Tickets', String(kpi['tickets_handled'] ?? 0), '#38bdf8'],
        ['In TAT%', (kpi['within_tat_pct'] != null ? kpi['within_tat_pct'] + '%' : '\u2014'), '#4ade80'],
        ['Abv TAT', String(kpi['above_tat_count'] ?? 0), '#f87171'],
      ];
    } else if (dt === 'procurement') {
      tiles = [
        ['Rcvd', String(kpi['received_today_count'] ?? 0), '#4ade80'],
        ['Pending', String(kpi['pending_count'] ?? 0), '#fbbf24'],
        ['Abv TAT', String(kpi['above_tat_count'] ?? 0), '#f87171'],
      ];
    } else {
      return '';
    }
    
    if (isFullCard) {
      return `
        <div class="progress-detail-card dept-kpi-card" style="margin-top: 12px; border-left: 4px solid ${tiles[0][2]};">
          <div class="detail-card-header">
            <span class="detail-card-title">📊 Department KPIs (${dt.charAt(0).toUpperCase() + dt.slice(1)})</span>
          </div>
          <div class="detail-card-metrics" style="justify-content: space-around; padding: 10px 0;">
            ${tiles.map(([l, v, c]) => `
              <div class="metric-col">
                <div class="metric-value" style="color:${c}; font-size: 1.2rem;">${v}</div>
                <div class="metric-label">${l}</div>
              </div>
            `).join('<div class="metric-divider">|</div>')}
          </div>
        </div>
      `;
    }
    
    return `<div style="display:flex;gap:6px;justify-content:center;padding:3px 0 1px;">${tiles.map(([l,v,c]) => `<span style="text-align:center;min-width:48px;"><small style="display:block;color:#94a3b8;font-size:8px;">${l}</small><strong style="color:${c};font-size:11px;">${v}</strong></span>`).join('')}</div>`;
  }

  private getLeaveLabel(e: DayProgressEntry): string {
    return e.leave_display || e.leave_type || e.hr_attendance || 'On Leave';
  }

  private escapeHtml(str: string): string {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  cleanup(): void {
    this.pendingTimers.forEach(t => clearTimeout(t));
    this.pendingTimers = [];
  }
}
