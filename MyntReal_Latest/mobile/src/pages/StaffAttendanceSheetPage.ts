/**
 * Staff Attendance Sheet Page
 * DC Protocol: DC_MOBILE_ATTENDANCE_SHEET_001
 * View attendance records with filters
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface AttendanceRecord {
  id: number;
  employee_id: number;
  employee_name: string;
  emp_code: string;
  department: string;
  date: string;
  clock_in: string;
  clock_out: string;
  working_hours: number;
  status: string;
  remarks?: string;
  approval_status: string;
}

export class StaffAttendanceSheetPage {
  private container: HTMLElement;
  private records: AttendanceRecord[] = [];
  private loading: boolean = true;
  private currentMonth: Date = new Date();
  private filterDepartment: string = '';
  private filterStatus: string = '';
  private departments: string[] = [];

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadRecords();
  }

  private async loadRecords(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      const year = this.currentMonth.getFullYear();
      const month = this.currentMonth.getMonth() + 1;
      const monthYear = `${year}-${String(month).padStart(2, '0')}`;
      let endpoint = `/staff/attendance-sheet/monthly/${monthYear}`;
      const params: string[] = [];
      if (this.filterDepartment) params.push(`department=${this.filterDepartment}`);
      if (this.filterStatus) params.push(`status=${this.filterStatus}`);
      if (params.length) endpoint += `?${params.join('&')}`;

      const response = await apiService.get<any>(endpoint);
      console.log('[StaffAttendanceSheetPage] API response:', response);

      if (response.success && response.data) {
        this.records = response.data.records || response.data || [];
        this.departments = [...new Set(this.records.map(r => r.department).filter(Boolean))];
      }
    } catch (error) {
      console.error('[StaffAttendanceSheetPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    const monthName = this.currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Attendance Records', showBack: true })}
        
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
          <select id="deptFilter" class="filter-select">
            <option value="">All Departments</option>
          </select>
          <select id="statusFilter" class="filter-select">
            <option value="">All Status</option>
            <option value="present">Present</option>
            <option value="absent">Absent</option>
            <option value="late">Late</option>
            <option value="half_day">Half Day</option>
            <option value="leave">On Leave</option>
          </select>
        </div>

        <div class="stats-row">
          <div class="stat-card mini success">
            <span class="stat-value" id="presentCount">0</span>
            <span class="stat-label">Present</span>
          </div>
          <div class="stat-card mini danger">
            <span class="stat-value" id="absentCount">0</span>
            <span class="stat-label">Absent</span>
          </div>
          <div class="stat-card mini warning">
            <span class="stat-value" id="lateCount">0</span>
            <span class="stat-label">Late</span>
          </div>
        </div>

        <div class="list-container" id="recordsList">
          <div class="loading-state">Loading records...</div>
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
      this.loadRecords();
    });

    document.getElementById('nextMonth')?.addEventListener('click', () => {
      this.currentMonth.setMonth(this.currentMonth.getMonth() + 1);
      this.render();
      this.loadRecords();
    });

    document.getElementById('deptFilter')?.addEventListener('change', (e) => {
      this.filterDepartment = (e.target as HTMLSelectElement).value;
      this.loadRecords();
    });

    document.getElementById('statusFilter')?.addEventListener('change', (e) => {
      this.filterStatus = (e.target as HTMLSelectElement).value;
      this.loadRecords();
    });
  }

  private updateList(): void {
    const listContainer = document.getElementById('recordsList');
    const deptFilter = document.getElementById('deptFilter') as HTMLSelectElement;
    
    if (deptFilter && this.departments.length > 0) {
      deptFilter.innerHTML = `
        <option value="">All Departments</option>
        ${this.departments.map(d => `<option value="${d}">${d}</option>`).join('')}
      `;
    }

    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading records...</div>';
      return;
    }

    const presentEl = document.getElementById('presentCount');
    const absentEl = document.getElementById('absentCount');
    const lateEl = document.getElementById('lateCount');
    if (presentEl) presentEl.textContent = this.records.filter(r => r.status === 'present').length.toString();
    if (absentEl) absentEl.textContent = this.records.filter(r => r.status === 'absent').length.toString();
    if (lateEl) lateEl.textContent = this.records.filter(r => r.status === 'late').length.toString();

    if (this.records.length === 0) {
      listContainer.innerHTML = '<div class="empty-state">No attendance records found</div>';
      return;
    }

    listContainer.innerHTML = this.records.map(rec => `
      <div class="list-card attendance-record-card">
        <div class="record-header">
          <div class="employee-info-row">
            <div class="employee-avatar-sm">${this.getInitials(rec.employee_name)}</div>
            <div class="employee-details">
              <div class="employee-name">${rec.employee_name}</div>
              <div class="employee-meta">${rec.emp_code} • ${rec.department || 'N/A'}</div>
            </div>
          </div>
          <span class="status-badge ${rec.status}">${rec.status}</span>
        </div>
        <div class="record-details">
          <div class="detail-row">
            <span class="detail-label">Date</span>
            <span class="detail-value">${this.formatDate(rec.date)}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Clock In</span>
            <span class="detail-value">${rec.clock_in || '--:--'}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Clock Out</span>
            <span class="detail-value">${rec.clock_out || '--:--'}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Working Hours</span>
            <span class="detail-value">${rec.working_hours?.toFixed(1) || '0'} hrs</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Approval</span>
            <span class="approval-badge ${rec.approval_status}">${rec.approval_status || 'pending'}</span>
          </div>
        </div>
        ${rec.remarks ? `<div class="record-remarks"><strong>Remarks:</strong> ${rec.remarks}</div>` : ''}
      </div>
    `).join('');
  }

  private getInitials(name: string): string {
    return name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '??';
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-IN', {
      weekday: 'short',
      day: '2-digit',
      month: 'short'
    });
  }
}
