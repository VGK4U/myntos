/**
 * Staff Attendance Reports/Dashboard Page
 * DC Protocol: DC_MOBILE_ATTENDANCE_REPORTS_001
 * Attendance analytics and reports
 * DC-EXCEPTIONS-TAB-001: Exception Approvals tab added for Key Leadership / EA / Accounts / MR10001
 * DC-TIMEREPORT-001: Time Report tab added (3rd tab) – per-employee daily punch detail
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface AttendanceStats {
  total_employees: number;
  present_today: number;
  absent_today: number;
  on_leave_today: number;
  late_today: number;
  avg_working_hours: number;
  avg_attendance_percentage: number;
}

interface DepartmentStats {
  department: string;
  total: number;
  present: number;
  absent: number;
  attendance_percentage: number;
}

interface ExceptionRecord {
  id: number;
  date: string;
  employee_name: string;
  employee_code: string;
  department: string;
  bypass_type: string;
  exception_reason: string;
  approved_hours: number;
  approver_name: string;
  approver_role: string;
  created_at: string;
  clock_in?: string;
  clock_out?: string;
  total_hours?: string;
  reconciliation_snapshot?: Record<string, any>;
}

interface TimeReportRecord {
  date: string;
  in_time: string | null;
  out_time: string | null;
  total_hours: number | null;
  submitted_hours: number | null;
  approved_hours: number | null;
  exception_hours: number | null;
  attendance_status: string | null;
  in_location: string | null;
  out_location: string | null;
  logout_type: string;
}

interface EmployeeOption {
  id: number;
  full_name: string;
  emp_code?: string;
  employee_code?: string;
}

export class StaffAttendanceReportsPage {
  private container: HTMLElement;
  private stats: AttendanceStats | null = null;
  private departmentStats: DepartmentStats[] = [];
  private loading: boolean = true;
  private dateRange: string = 'today';

  private activeTab: 'dashboard' | 'exceptions' | 'timereport' = 'dashboard';
  private excRecords: ExceptionRecord[] = [];
  private excLoading: boolean = false;
  private excLoaded: boolean = false;
  private excPage: number = 1;
  private excTotalPages: number = 1;
  private excFromDate: string = '';
  private excToDate: string = '';
  private excBypassType: string = '';
  private canSeeExceptions: boolean = false;

  // DC-TIMEREPORT-001: Time Report state
  private trRecords: TimeReportRecord[] = [];
  private trLoading: boolean = false;
  private trLoaded: boolean = false;
  private trPage: number = 1;
  private trTotalPages: number = 1;
  private trTotal: number = 0;
  private trFromDate: string = '';
  private trToDate: string = '';
  private trEmployeeId: string = '';
  private trEmployeeName: string = '';
  private trEmployees: EmployeeOption[] = [];
  private trEmpLoaded: boolean = false;
  private trEmployeeInfo: { name: string; dept: string; emp_code: string } | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    const user = this.getCurrentUser();
    this.canSeeExceptions = this.checkExceptionAccess(user);
    // Set default Time Report dates (current month)
    const today = new Date();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    this.trFromDate = `${today.getFullYear()}-${mm}-01`;
    this.trToDate   = today.toISOString().split('T')[0];
    this.render();
    await this.loadData();
  }

  private getCurrentUser(): Record<string, any> {
    try {
      return JSON.parse(localStorage.getItem('staff_user') || '{}');
    } catch { return {}; }
  }

  private checkExceptionAccess(user: Record<string, any>): boolean {
    const roleCode = (user.role_code || '').toLowerCase();
    const empCode  = (user.emp_code || user.employee_code || '').toUpperCase();
    const roleName = (user.role_name || '').toLowerCase();
    const dept     = (user.department_name || '').toLowerCase();
    if (empCode === 'MR10001') return true;
    if (['key_leadership', 'ea', 'vgk4u', 'vgk4u_supreme', 'vgk_mentor'].includes(roleCode)) return true;
    if (roleName.includes('key leadership') || roleName.includes('executive admin')) return true;
    if (dept.includes('accounts') || dept.includes('account')) return true;
    if ((user.hierarchy_level || 0) >= 80) return true;
    return false;
  }

  private async loadData(): Promise<void> {
    this.loading = true;
    this.updateDashboardContent();

    try {
      const response = await apiService.get<any>(`/staff/attendance/reports?range=${this.dateRange}`);
      if (response.success && response.data) {
        this.stats = response.data.summary || response.data;
        this.departmentStats = response.data.by_department || [];
      }
    } catch (error) {
      console.error('[StaffAttendanceReportsPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateDashboardContent();
  }

  private async loadExceptions(): Promise<void> {
    this.excLoading = true;
    this.updateExceptionsContent();

    try {
      let endpoint = `/staff/attendance-sheet/exceptions?page=${this.excPage}&per_page=20`;
      if (this.excFromDate) endpoint += `&from_date=${this.excFromDate}`;
      if (this.excToDate)   endpoint += `&to_date=${this.excToDate}`;
      if (this.excBypassType) endpoint += `&bypass_type=${this.excBypassType}`;

      const response = await apiService.get<any>(endpoint);
      if (response.success && response.data) {
        this.excRecords     = response.data.records || [];
        this.excTotalPages  = response.data.pagination?.total_pages || 1;
        this.excPage        = response.data.pagination?.page || 1;
      }
    } catch (error) {
      console.error('[StaffAttendanceReportsPage] Failed to load exceptions:', error);
    }

    this.excLoading = false;
    this.updateExceptionsContent();
  }

  // ── DC-TIMEREPORT-001: Time Report data loading ─────────────────
  private async loadTREmployees(): Promise<void> {
    if (this.trEmpLoaded) return;
    try {
      const res = await apiService.get<any>('/staff/employees?per_page=500&status=active');
      if (res.success && res.data) {
        this.trEmployees = res.data.employees || res.data.items || res.data || [];
        this.trEmpLoaded = true;
      }
    } catch (e) {
      console.error('[TR] Failed to load employees:', e);
    }
  }

  private async loadTimeReport(): Promise<void> {
    if (!this.trEmployeeId) return;
    this.trLoading = true;
    this.updateTimeReportContent();

    try {
      let endpoint = `/staff/attendance-sheet/time-report?employee_id=${this.trEmployeeId}&page=${this.trPage}&per_page=30`;
      if (this.trFromDate) endpoint += `&from_date=${this.trFromDate}`;
      if (this.trToDate)   endpoint += `&to_date=${this.trToDate}`;

      const response = await apiService.get<any>(endpoint);
      if (response.success && response.data) {
        this.trRecords      = response.data.records || [];
        this.trTotalPages   = response.data.pagination?.total_pages || 1;
        this.trTotal        = response.data.pagination?.total || this.trRecords.length;
        this.trPage         = response.data.pagination?.page || 1;
        this.trEmployeeInfo = response.data.employee
          ? { name: response.data.employee.name || '', dept: response.data.employee.department || '', emp_code: response.data.employee.emp_code || '' }
          : null;
        this.trLoaded = true;
      }
    } catch (error) {
      console.error('[StaffAttendanceReportsPage] Failed to load time report:', error);
    }

    this.trLoading = false;
    this.updateTimeReportContent();
  }

  private trExportCsv(): void {
    if (!this.trRecords.length) return;
    const empName = this.trEmployeeInfo?.name || 'Staff';
    const header  = ['Date','In Time','Out Time','Total Hours','Submitted Hours','Timesheet Approved (Approved/Submitted hrs)','Exception Hours','Attendance Status','In Location','Out Location','Logout Type'];
    const rows    = this.trRecords.map(r => [
      r.date, r.in_time || '', r.out_time || '',
      r.total_hours        != null ? r.total_hours        : '',
      r.submitted_hours    != null ? r.submitted_hours    : '',
      (r.approved_hours != null || r.submitted_hours != null)
        ? `${r.approved_hours != null ? parseFloat(String(r.approved_hours)).toFixed(2) : '-'} / ${r.submitted_hours != null ? parseFloat(String(r.submitted_hours)).toFixed(2) : '-'} hrs`
        : '',
      r.exception_hours    != null ? r.exception_hours    : '',
      r.attendance_status  || '',
      (r.in_location  || '').replace(/,/g, ';'),
      (r.out_location || '').replace(/,/g, ';'),
      r.logout_type || ''
    ]);
    const csv  = [header, ...rows].map(r => r.map(v => `"${String(v).replace(/"/g,'""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `time_report_${empName.split(' ')[0]}_${this.trFromDate || 'all'}_${this.trToDate || 'all'}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ── Render ──────────────────────────────────────────────────────
  private render(): void {
    const showGatedTabs = this.canSeeExceptions;
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Attendance Dashboard', showBack: true })}

        ${showGatedTabs ? `
        <div class="tab-bar" style="display:flex;background:#fff;border-bottom:2px solid #e5e7eb;margin-bottom:0;overflow-x:auto;">
          <button id="tabDashboard" class="tab-btn"
            style="flex:1;min-width:90px;padding:12px 8px;border:none;background:transparent;font-weight:600;font-size:13px;white-space:nowrap;cursor:pointer;">
            <i class="fas fa-chart-bar" style="margin-right:4px;"></i>Dashboard
          </button>
          <button id="tabExceptions" class="tab-btn"
            style="flex:1;min-width:90px;padding:12px 8px;border:none;background:transparent;font-weight:600;font-size:13px;white-space:nowrap;cursor:pointer;">
            <i class="fas fa-shield-alt" style="margin-right:4px;"></i>Exceptions
          </button>
          <button id="tabTimereport" class="tab-btn"
            style="flex:1;min-width:90px;padding:12px 8px;border:none;background:transparent;font-weight:600;font-size:13px;white-space:nowrap;cursor:pointer;">
            <i class="fas fa-table" style="margin-right:4px;"></i>Time Report
          </button>
        </div>
        ` : ''}

        <div id="tabDashboardContent" style="display:${this.activeTab === 'dashboard' ? 'block' : 'none'};">
          <div class="date-filter" style="padding:12px 16px;">
            <select id="dateRange" class="filter-select full-width">
              <option value="today" ${this.dateRange === 'today' ? 'selected' : ''}>Today</option>
              <option value="week" ${this.dateRange === 'week' ? 'selected' : ''}>This Week</option>
              <option value="month" ${this.dateRange === 'month' ? 'selected' : ''}>This Month</option>
              <option value="quarter" ${this.dateRange === 'quarter' ? 'selected' : ''}>This Quarter</option>
            </select>
          </div>
          <div class="content-area" id="contentArea">
            <div class="loading-state">Loading attendance data...</div>
          </div>
        </div>

        <div id="tabExceptionsContent" style="display:${this.activeTab === 'exceptions' ? 'block' : 'none'};">
          <div id="excContent">
            <div class="loading-state" style="padding:40px;text-align:center;">Loading exceptions...</div>
          </div>
        </div>

        <div id="tabTimereportContent" style="display:${this.activeTab === 'timereport' ? 'block' : 'none'};">
          <div id="trContent">
            <div style="padding:40px;text-align:center;color:#9ca3af;">
              <i class="fas fa-table" style="font-size:32px;margin-bottom:10px;display:block;"></i>
              <p style="margin:0;">Select a staff member and tap <strong>View</strong></p>
            </div>
          </div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
    if (showGatedTabs) this.updateTabStyles();
  }

  private updateTabStyles(): void {
    const tabs = ['Dashboard', 'Exceptions', 'Timereport'] as const;
    const tabIds = ['tabDashboard', 'tabExceptions', 'tabTimereport'];
    const activeColor   = '#0284c7';
    const inactiveColor = '#6b7280';
    tabIds.forEach((id, i) => {
      const el = document.getElementById(id) as HTMLButtonElement | null;
      if (!el) return;
      const tabKey = tabs[i].toLowerCase() as 'dashboard' | 'exceptions' | 'timereport';
      const isActive = this.activeTab === tabKey;
      el.style.color       = isActive ? activeColor : inactiveColor;
      el.style.borderBottom = isActive ? `2px solid ${activeColor}` : '2px solid transparent';
      el.style.marginBottom = '-2px';
    });
  }

  private attachEventListeners(): void {
    document.getElementById('dateRange')?.addEventListener('change', (e) => {
      this.dateRange = (e.target as HTMLSelectElement).value;
      this.loadData();
    });

    document.getElementById('tabDashboard')?.addEventListener('click',  () => this.switchTab('dashboard'));
    document.getElementById('tabExceptions')?.addEventListener('click', () => this.switchTab('exceptions'));
    document.getElementById('tabTimereport')?.addEventListener('click', () => this.switchTab('timereport'));
  }

  private switchTab(tab: 'dashboard' | 'exceptions' | 'timereport'): void {
    this.activeTab = tab;
    const panels: Record<string, string> = {
      dashboard:  'tabDashboardContent',
      exceptions: 'tabExceptionsContent',
      timereport: 'tabTimereportContent',
    };
    Object.entries(panels).forEach(([key, panelId]) => {
      const el = document.getElementById(panelId);
      if (el) el.style.display = key === tab ? 'block' : 'none';
    });
    this.updateTabStyles();

    if (tab === 'exceptions' && !this.excLoaded) {
      this.excLoaded = true;
      this.loadExceptions();
    }
    if (tab === 'timereport' && !this.trEmpLoaded) {
      this.loadTREmployees().then(() => this.updateTimeReportContent());
    }
  }

  private updateDashboardContent(): void {
    const contentArea = document.getElementById('contentArea');
    if (!contentArea) return;

    if (this.loading) {
      contentArea.innerHTML = '<div class="loading-state">Loading attendance data...</div>';
      return;
    }

    if (!this.stats) {
      contentArea.innerHTML = '<div class="empty-state">No data available</div>';
      return;
    }

    const s = this.stats;
    contentArea.innerHTML = `
      <div class="dashboard-section">
        <h4 class="section-title">Overview</h4>
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon total">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="9" cy="7" r="4"/>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
              </svg>
            </div>
            <div class="stat-info">
              <div class="stat-value">${s.total_employees}</div>
              <div class="stat-label">Total Employees</div>
            </div>
          </div>

          <div class="stat-card success">
            <div class="stat-icon present">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
            </div>
            <div class="stat-info">
              <div class="stat-value">${s.present_today}</div>
              <div class="stat-label">Present</div>
            </div>
          </div>

          <div class="stat-card danger">
            <div class="stat-icon absent">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
              </svg>
            </div>
            <div class="stat-info">
              <div class="stat-value">${s.absent_today}</div>
              <div class="stat-label">Absent</div>
            </div>
          </div>

          <div class="stat-card info">
            <div class="stat-icon leave">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                <line x1="16" y1="2" x2="16" y2="6"/>
                <line x1="8" y1="2" x2="8" y2="6"/>
                <line x1="3" y1="10" x2="21" y2="10"/>
              </svg>
            </div>
            <div class="stat-info">
              <div class="stat-value">${s.on_leave_today}</div>
              <div class="stat-label">On Leave</div>
            </div>
          </div>

          <div class="stat-card warning">
            <div class="stat-icon late">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
            </div>
            <div class="stat-info">
              <div class="stat-value">${s.late_today}</div>
              <div class="stat-label">Late Arrivals</div>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon hours">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
            </div>
            <div class="stat-info">
              <div class="stat-value">${s.avg_working_hours?.toFixed(1) || '0'}</div>
              <div class="stat-label">Avg Hours</div>
            </div>
          </div>
        </div>
      </div>

      <div class="dashboard-section">
        <h4 class="section-title">Attendance Rate</h4>
        <div class="progress-card">
          <div class="progress-bar">
            <div class="progress-fill" style="width: ${s.avg_attendance_percentage || 0}%"></div>
          </div>
          <div class="progress-label">${s.avg_attendance_percentage?.toFixed(1) || 0}% Average Attendance</div>
        </div>
      </div>

      ${this.departmentStats.length > 0 ? `
        <div class="dashboard-section">
          <h4 class="section-title">By Department</h4>
          <div class="department-list">
            ${this.departmentStats.map(dept => `
              <div class="department-row">
                <div class="dept-info">
                  <div class="dept-name">${dept.department}</div>
                  <div class="dept-meta">${dept.present}/${dept.total} present</div>
                </div>
                <div class="dept-percentage ${dept.attendance_percentage >= 80 ? 'good' : dept.attendance_percentage >= 60 ? 'warning' : 'poor'}">
                  ${dept.attendance_percentage?.toFixed(0)}%
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}
    `;
  }

  private updateExceptionsContent(): void {
    const excContent = document.getElementById('excContent');
    if (!excContent) return;

    if (this.excLoading) {
      excContent.innerHTML = '<div class="loading-state" style="padding:40px;text-align:center;">Loading exceptions...</div>';
      return;
    }

    excContent.innerHTML = `
      <!-- Filters -->
      <div style="padding:12px 16px;background:#f9fafb;border-bottom:1px solid #e5e7eb;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
        <input type="date" id="excFrom" value="${this.excFromDate}"
          style="flex:1;min-width:120px;padding:7px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:13px;">
        <input type="date" id="excTo" value="${this.excToDate}"
          style="flex:1;min-width:120px;padding:7px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:13px;">
        <select id="excBtype" style="flex:1;min-width:130px;padding:7px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:13px;">
          <option value="">All Types</option>
          <option value="no_timesheet" ${this.excBypassType === 'no_timesheet' ? 'selected' : ''}>No Timesheet</option>
          <option value="mismatch_override" ${this.excBypassType === 'mismatch_override' ? 'selected' : ''}>Mismatch Override</option>
          <option value="manual_adjustment" ${this.excBypassType === 'manual_adjustment' ? 'selected' : ''}>Manual Adjustment</option>
        </select>
        <button id="excApplyBtn" style="padding:7px 14px;background:#0284c7;color:#fff;border:none;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;">
          Apply
        </button>
        <button id="excClearBtn" style="padding:7px 14px;background:#f3f4f6;color:#374151;border:1px solid #d1d5db;border-radius:6px;font-size:13px;cursor:pointer;">
          Clear
        </button>
      </div>

      <!-- Records -->
      <div style="padding:16px;">
        ${this.excRecords.length === 0 ? `
          <div style="text-align:center;padding:60px 20px;color:#9ca3af;">
            <div style="font-size:40px;margin-bottom:12px;">✓</div>
            <p style="margin:0;font-weight:500;">No exception records found</p>
            <small>Exception approvals appear here when EA/VGK bypass the timesheet requirement</small>
          </div>
        ` : `
          ${this.excRecords.map(r => this.renderExcCard(r)).join('')}
          ${this.excTotalPages > 1 ? `
            <div style="display:flex;justify-content:center;gap:8px;margin-top:16px;">
              <button id="excPrevBtn" ${this.excPage <= 1 ? 'disabled' : ''}
                style="padding:8px 16px;border:1px solid #d1d5db;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;${this.excPage <= 1 ? 'opacity:0.5;' : ''}">
                ← Prev
              </button>
              <span style="padding:8px 12px;font-size:13px;color:#6b7280;">
                Page ${this.excPage} of ${this.excTotalPages}
              </span>
              <button id="excNextBtn" ${this.excPage >= this.excTotalPages ? 'disabled' : ''}
                style="padding:8px 16px;border:1px solid #d1d5db;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;${this.excPage >= this.excTotalPages ? 'opacity:0.5;' : ''}">
                Next →
              </button>
            </div>
          ` : ''}
        `}
      </div>
    `;

    this.attachExceptionListeners();
  }

  // ── DC-TIMEREPORT-001: Time Report render ───────────────────────
  private updateTimeReportContent(): void {
    const trContent = document.getElementById('trContent');
    if (!trContent) return;

    const empOptions = this.trEmployees.map(e =>
      `<option value="${e.id}" ${String(e.id) === this.trEmployeeId ? 'selected' : ''}>${this.esc(e.full_name)} (${e.emp_code || e.employee_code || ''})</option>`
    ).join('');

    const filtersHtml = `
      <div style="padding:12px 16px;background:#f9fafb;border-bottom:1px solid #e5e7eb;">
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;">
          <div style="flex:1;min-width:140px;">
            <div style="font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;margin-bottom:4px;">From</div>
            <input type="date" id="trFrom" value="${this.trFromDate}"
              style="width:100%;padding:7px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:13px;">
          </div>
          <div style="flex:1;min-width:140px;">
            <div style="font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;margin-bottom:4px;">To</div>
            <input type="date" id="trTo" value="${this.trToDate}"
              style="width:100%;padding:7px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:13px;">
          </div>
        </div>
        <div style="margin-top:8px;">
          <div style="font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;margin-bottom:4px;">Select Staff</div>
          <select id="trStaff" style="width:100%;padding:7px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:13px;">
            <option value="">— select employee —</option>
            ${empOptions}
          </select>
        </div>
        <div style="display:flex;gap:8px;margin-top:10px;">
          <button id="trViewBtn"
            style="flex:1;padding:9px;background:#0284c7;color:#fff;border:none;border-radius:6px;font-weight:600;font-size:13px;cursor:pointer;">
            <i class="fas fa-eye"></i> View
          </button>
          ${this.trRecords.length > 0 ? `
          <button id="trExportBtn"
            style="padding:9px 14px;background:#16a34a;color:#fff;border:none;border-radius:6px;font-weight:600;font-size:13px;cursor:pointer;">
            <i class="fas fa-file-excel"></i> CSV
          </button>
          ` : ''}
        </div>
      </div>
    `;

    if (this.trLoading) {
      trContent.innerHTML = filtersHtml + `
        <div style="padding:40px;text-align:center;">
          <div class="spinner-border" style="color:#0284c7;"></div>
          <p style="margin-top:10px;color:#6b7280;font-size:13px;">Loading time report…</p>
        </div>`;
      this.attachTRListeners();
      return;
    }

    let recordsHtml = '';
    if (!this.trLoaded) {
      recordsHtml = `
        <div style="padding:40px;text-align:center;color:#9ca3af;">
          <i class="fas fa-table" style="font-size:32px;margin-bottom:10px;display:block;"></i>
          <p style="margin:0;">Select a staff member and tap <strong>View</strong></p>
        </div>`;
    } else if (this.trRecords.length === 0) {
      const empName = this.trEmployeeInfo?.name || 'This employee';
      const fmtD = (iso: string) => {
        const d = new Date(iso + 'T00:00:00');
        return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
      };
      const rangeMsg = (this.trFromDate && this.trToDate)
        ? `from ${fmtD(this.trFromDate)} to ${fmtD(this.trToDate)}`
        : 'for the selected period';
      recordsHtml = `
        <div style="padding:40px 20px;text-align:center;color:#9ca3af;">
          <i class="fas fa-calendar-times" style="font-size:32px;margin-bottom:10px;display:block;color:#d1d5db;"></i>
          <p style="margin:0 0 6px;font-weight:600;color:#374151;">No attendance records found</p>
          <p style="margin:0;font-size:12px;line-height:1.6;">
            <strong>${this.esc(empName)}</strong> has no punch records ${rangeMsg}.<br>
            Try a wider date range or check if attendance was recorded.
          </p>
        </div>`;
    } else {
      const empBanner = this.trEmployeeInfo ? `
        <div style="padding:10px 16px;background:#eff6ff;border-bottom:1px solid #bfdbfe;display:flex;gap:10px;align-items:center;">
          <strong style="font-size:14px;color:#1e3a5f;">${this.esc(this.trEmployeeInfo.name)}</strong>
          <span style="font-size:12px;color:#6b7280;">${this.esc(this.trEmployeeInfo.dept)}</span>
          <span style="font-size:11px;color:#9ca3af;font-family:monospace;">${this.trEmployeeInfo.emp_code}</span>
          <span style="margin-left:auto;font-size:12px;color:#6b7280;">${this.trTotal} record${this.trTotal !== 1 ? 's' : ''}</span>
        </div>` : '';

      const cards = this.trRecords.map(r => this.renderTRCard(r)).join('');

      const pagination = this.trTotalPages > 1 ? `
        <div style="display:flex;justify-content:center;gap:8px;padding:16px;">
          <button id="trPrevBtn" ${this.trPage <= 1 ? 'disabled' : ''}
            style="padding:8px 14px;border:1px solid #d1d5db;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;${this.trPage <= 1 ? 'opacity:0.5;' : ''}">
            ← Prev
          </button>
          <span style="padding:8px 10px;font-size:13px;color:#6b7280;">
            ${this.trPage} / ${this.trTotalPages}
          </span>
          <button id="trNextBtn" ${this.trPage >= this.trTotalPages ? 'disabled' : ''}
            style="padding:8px 14px;border:1px solid #d1d5db;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;${this.trPage >= this.trTotalPages ? 'opacity:0.5;' : ''}">
            Next →
          </button>
        </div>` : '';

      recordsHtml = empBanner + `<div style="padding:12px 16px;">${cards}</div>` + pagination;
    }

    trContent.innerHTML = filtersHtml + recordsHtml;
    this.attachTRListeners();
  }

  private trStatusLabel(v: string | null): string {
    if (!v) return '—';
    const map: Record<string, [string, string, string]> = {
      present:        ['#dcfce7','#166534','Present'],
      half_day:       ['#fef9c3','#854d0e','Half Day'],
      absent:         ['#fee2e2','#991b1b','Absent'],
      sick_leave:     ['#ffedd5','#9a3412','Sick Leave'],
      approved_leave: ['#dbeafe','#1e40af','Approved Leave'],
      casual_leave:   ['#ede9fe','#5b21b6','Casual Leave'],
      unpaid_leave:   ['#f3f4f6','#374151','Unpaid Leave'],
      holiday:        ['#ccfbf1','#0f766e','Holiday'],
      weekend:        ['#f3f4f6','#6b7280','Weekend'],
    };
    const [bg, fg, label] = map[v] || ['#f3f4f6','#374151', v];
    return `<span style="background:${bg};color:${fg};padding:2px 7px;border-radius:8px;font-size:10px;font-weight:600;">${label}</span>`;
  }

  private renderTRCard(r: TimeReportRecord): string {
    const fmtDate = (iso: string) => {
      const d = new Date(iso + 'T00:00:00');
      return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    };
    const fmtHr = (v: number | null) => v != null ? parseFloat(String(v)).toFixed(2) + ' h' : '—';
    const logoutBadge = r.logout_type === 'Company'
      ? `<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">Company</span>`
      : `<span style="background:#dcfce7;color:#166534;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">Self</span>`;

    return `
      <div style="background:#fff;border-radius:10px;border:1px solid #e5e7eb;padding:13px;margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
          <strong style="font-size:14px;color:#1f2937;">${fmtDate(r.date)}</strong>
          ${logoutBadge}
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px;margin-bottom:8px;">
          <div><span style="color:#9ca3af;">In:</span> <strong>${r.in_time || '—'}</strong></div>
          <div><span style="color:#9ca3af;">Out:</span> <strong>${r.out_time || '—'}</strong></div>
          <div><span style="color:#9ca3af;">Total:</span> <strong>${fmtHr(r.total_hours)}</strong></div>
          <div><span style="color:#9ca3af;">Submitted:</span> <strong>${fmtHr(r.submitted_hours)}</strong></div>
          <div><span style="color:#9ca3af;">TS Approved:</span> <strong style="font-size:11px;">${r.approved_hours != null ? parseFloat(String(r.approved_hours)).toFixed(2) : '—'} / ${r.submitted_hours != null ? parseFloat(String(r.submitted_hours)).toFixed(2) : '—'} hrs</strong></div>
          <div><span style="color:#9ca3af;">Exception:</span> <strong>${fmtHr(r.exception_hours)}</strong></div>
          <div><span style="color:#9ca3af;">Status:</span> ${this.trStatusLabel(r.attendance_status)}</div>
        </div>
        ${r.in_location || r.out_location ? `
        <div style="background:#f9fafb;border-radius:6px;padding:7px 10px;font-size:11px;color:#374151;border:1px solid #f3f4f6;">
          ${r.in_location  ? `<div><span style="color:#9ca3af;">In Loc:</span> ${this.esc(r.in_location)}</div>`  : ''}
          ${r.out_location ? `<div style="margin-top:3px;"><span style="color:#9ca3af;">Out Loc:</span> ${this.esc(r.out_location)}</div>` : ''}
        </div>` : ''}
      </div>`;
  }

  private attachTRListeners(): void {
    document.getElementById('trViewBtn')?.addEventListener('click', () => {
      this.trFromDate   = (document.getElementById('trFrom') as HTMLInputElement)?.value || '';
      this.trToDate     = (document.getElementById('trTo') as HTMLInputElement)?.value || '';
      this.trEmployeeId = (document.getElementById('trStaff') as HTMLSelectElement)?.value || '';
      if (!this.trEmployeeId) { alert('Please select a staff member first.'); return; }
      this.trPage = 1;
      this.loadTimeReport();
    });

    document.getElementById('trExportBtn')?.addEventListener('click', () => this.trExportCsv());

    document.getElementById('trPrevBtn')?.addEventListener('click', () => {
      if (this.trPage > 1) { this.trPage--; this.loadTimeReport(); }
    });

    document.getElementById('trNextBtn')?.addEventListener('click', () => {
      if (this.trPage < this.trTotalPages) { this.trPage++; this.loadTimeReport(); }
    });
  }

  private renderExcCard(r: ExceptionRecord): string {
    const bypassLabel = r.bypass_type === 'no_timesheet' ? 'No Timesheet' :
                        r.bypass_type === 'mismatch_override' ? 'Mismatch Override' : 'Manual Adjustment';
    const bypassColor = r.bypass_type === 'no_timesheet' ? '#d97706' :
                        r.bypass_type === 'mismatch_override' ? '#dc2626' : '#2563eb';
    const bypassBg    = r.bypass_type === 'no_timesheet' ? '#fef3c7' :
                        r.bypass_type === 'mismatch_override' ? '#fee2e2' : '#dbeafe';
    const createdAt   = r.created_at ? new Date(r.created_at).toLocaleDateString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric'
    }) : 'N/A';
    const date = r.date ? new Date(r.date).toLocaleDateString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric'
    }) : 'N/A';

    return `
      <div style="background:#fff;border-radius:10px;border:1px solid #e5e7eb;padding:14px;margin-bottom:12px;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
          <div>
            <div style="font-weight:600;color:#1f2937;font-size:14px;">${this.esc(r.employee_name)}</div>
            <div style="font-size:12px;color:#6b7280;">${r.employee_code} · ${this.esc(r.department)}</div>
          </div>
          <span style="background:${bypassBg};color:${bypassColor};padding:3px 8px;border-radius:4px;font-size:11px;font-weight:600;">
            ${bypassLabel}
          </span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:13px;margin-bottom:8px;">
          <div><span style="color:#9ca3af;">Date:</span> <strong>${date}</strong></div>
          <div><span style="color:#9ca3af;">Hours:</span> <strong>${r.approved_hours} hrs</strong></div>
          <div><span style="color:#9ca3af;">Approved by:</span> <strong>${this.esc(r.approver_name)}</strong></div>
          <div><span style="color:#9ca3af;">On:</span> <strong>${createdAt}</strong></div>
        </div>
        <div style="background:#fffbeb;border-left:3px solid #f59e0b;padding:8px 10px;border-radius:4px;font-size:12px;color:#374151;">
          <strong>Reason:</strong> ${this.esc(r.exception_reason)}
        </div>
      </div>`;
  }

  private attachExceptionListeners(): void {
    document.getElementById('excApplyBtn')?.addEventListener('click', () => {
      this.excFromDate  = (document.getElementById('excFrom') as HTMLInputElement)?.value || '';
      this.excToDate    = (document.getElementById('excTo') as HTMLInputElement)?.value || '';
      this.excBypassType = (document.getElementById('excBtype') as HTMLSelectElement)?.value || '';
      this.excPage = 1;
      this.loadExceptions();
    });

    document.getElementById('excClearBtn')?.addEventListener('click', () => {
      this.excFromDate = ''; this.excToDate = ''; this.excBypassType = '';
      this.excPage = 1;
      this.loadExceptions();
    });

    document.getElementById('excPrevBtn')?.addEventListener('click', () => {
      if (this.excPage > 1) { this.excPage--; this.loadExceptions(); }
    });

    document.getElementById('excNextBtn')?.addEventListener('click', () => {
      if (this.excPage < this.excTotalPages) { this.excPage++; this.loadExceptions(); }
    });
  }

  private esc(text: string): string {
    if (!text) return '';
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
  }
}
