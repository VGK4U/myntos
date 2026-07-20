/**
 * Staff Attendance Computation Page
 * DC Protocol: DC_MOBILE_ATTENDANCE_COMPUTATION_001
 * View computed attendance with working hours calculation
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface ComputedAttendance {
  employee_id: number;
  employee_name: string;
  emp_code: string;
  department: string;
  month: string;
  total_days: number;
  working_days: number;
  present_days: number;
  absent_days: number;
  leave_days: number;
  half_days: number;
  late_days: number;
  total_hours: number;
  overtime_hours: number;
  attendance_percentage: number;
  computed_at: string;
}

export class StaffAttendanceComputationPage {
  private container: HTMLElement;
  private computations: ComputedAttendance[] = [];
  private loading: boolean = true;
  private currentMonth: Date = new Date();
  private filterDepartment: string = '';
  private departments: string[] = [];

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadComputations();
  }

  private async loadComputations(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      const year = this.currentMonth.getFullYear();
      const month = this.currentMonth.getMonth() + 1;
      const monthYear = `${year}-${String(month).padStart(2, '0')}`;
      let endpoint = `/staff/timesheet/computation?month=${monthYear}`;
      if (this.filterDepartment) endpoint += `&department=${this.filterDepartment}`;

      const response = await apiService.get<any>(endpoint);
      console.log('[StaffAttendanceComputationPage] API response:', response);

      if (response.success && response.data) {
        this.computations = response.data.computations || response.data || [];
        this.departments = [...new Set(this.computations.map(c => c.department).filter(Boolean))];
      }
    } catch (error) {
      console.error('[StaffAttendanceComputationPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    const monthName = this.currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Attendance Computation', showBack: true })}
        
        <div class="month-selector">
          <button class="month-nav" id="prevMonth">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>
          <span class="month-label">${monthName}</span>
          <button class="month-nav" id="nextMonth">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
        </div>

        <div class="filter-row">
          <select id="deptFilter" class="filter-select full-width">
            <option value="">All Departments</option>
          </select>
        </div>

        <div class="list-container" id="computationsList">
          <div class="loading-state">Loading computations...</div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    document.getElementById('prevMonth')?.addEventListener('click', () => {
      this.currentMonth.setMonth(this.currentMonth.getMonth() - 1);
      this.render();
      this.loadComputations();
    });

    document.getElementById('nextMonth')?.addEventListener('click', () => {
      this.currentMonth.setMonth(this.currentMonth.getMonth() + 1);
      this.render();
      this.loadComputations();
    });

    document.getElementById('deptFilter')?.addEventListener('change', (e) => {
      this.filterDepartment = (e.target as HTMLSelectElement).value;
      this.loadComputations();
    });
  }

  private updateList(): void {
    const listContainer = document.getElementById('computationsList');
    const deptFilter = document.getElementById('deptFilter') as HTMLSelectElement;
    
    if (deptFilter && this.departments.length > 0) {
      deptFilter.innerHTML = `
        <option value="">All Departments</option>
        ${this.departments.map(d => `<option value="${d}">${d}</option>`).join('')}
      `;
    }

    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading computations...</div>';
      return;
    }

    if (this.computations.length === 0) {
      listContainer.innerHTML = '<div class="empty-state">No computation data available</div>';
      return;
    }

    listContainer.innerHTML = this.computations.map(comp => `
      <div class="list-card computation-card">
        <div class="computation-header">
          <div class="employee-info-row">
            <div class="employee-avatar-sm">${this.getInitials(comp.employee_name)}</div>
            <div class="employee-details">
              <div class="employee-name">${comp.employee_name}</div>
              <div class="employee-meta">${comp.emp_code} • ${comp.department || 'N/A'}</div>
            </div>
          </div>
          <div class="attendance-percentage ${comp.attendance_percentage >= 90 ? 'excellent' : comp.attendance_percentage >= 75 ? 'good' : 'poor'}">
            ${comp.attendance_percentage?.toFixed(0) || 0}%
          </div>
        </div>

        <div class="computation-grid">
          <div class="comp-item">
            <span class="comp-value">${comp.working_days}</span>
            <span class="comp-label">Working Days</span>
          </div>
          <div class="comp-item success">
            <span class="comp-value">${comp.present_days}</span>
            <span class="comp-label">Present</span>
          </div>
          <div class="comp-item danger">
            <span class="comp-value">${comp.absent_days}</span>
            <span class="comp-label">Absent</span>
          </div>
          <div class="comp-item info">
            <span class="comp-value">${comp.leave_days}</span>
            <span class="comp-label">Leave</span>
          </div>
          <div class="comp-item warning">
            <span class="comp-value">${comp.half_days}</span>
            <span class="comp-label">Half Days</span>
          </div>
          <div class="comp-item">
            <span class="comp-value">${comp.late_days}</span>
            <span class="comp-label">Late</span>
          </div>
        </div>

        <div class="computation-hours">
          <div class="hours-item">
            <span class="hours-label">Total Hours</span>
            <span class="hours-value">${comp.total_hours?.toFixed(1) || 0} hrs</span>
          </div>
          <div class="hours-item">
            <span class="hours-label">Overtime</span>
            <span class="hours-value highlight">${comp.overtime_hours?.toFixed(1) || 0} hrs</span>
          </div>
        </div>

        ${comp.computed_at ? `
          <div class="computation-timestamp">
            Last computed: ${this.formatDateTime(comp.computed_at)}
          </div>
        ` : ''}
      </div>
    `).join('');
  }

  private getInitials(name: string): string {
    return name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '??';
  }

  private formatDateTime(dateStr: string): string {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
