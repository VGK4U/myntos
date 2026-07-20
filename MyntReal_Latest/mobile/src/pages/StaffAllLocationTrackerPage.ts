/**
 * Staff All Location Tracker Page
 * DC Protocol: DC_MOBILE_LOCATION_TRACKER_001
 * View historical location data for all employees
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface LocationRecord {
  id: number;
  employee_id: number;
  employee_name: string;
  emp_code: string;
  department: string;
  latitude: number;
  longitude: number;
  address: string;
  accuracy: number;
  timestamp: string;
  battery_level?: number;
  source: string;
}

export class StaffAllLocationTrackerPage {
  private container: HTMLElement;
  private records: LocationRecord[] = [];
  private loading: boolean = true;
  private selectedDate: string = new Date().toISOString().split('T')[0];
  private filterDepartment: string = '';
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
      // DC Protocol: Match web's endpoint exactly
      let endpoint = `/staff/attendance/location/team/history?date=${this.selectedDate}&limit=100`;
      if (this.filterDepartment) endpoint += `&department=${this.filterDepartment}`;

      const response = await apiService.get<any>(endpoint);
      console.log('[StaffAllLocationTrackerPage] API response:', response);

      if (response.success && response.data) {
        this.records = response.data.records || response.data || [];
        this.departments = [...new Set(this.records.map(r => r.department).filter(Boolean))];
      }
    } catch (error) {
      console.error('[StaffAllLocationTrackerPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'All Location Tracker', showBack: true })}
        
        <div class="filter-row">
          <input type="date" id="dateFilter" class="filter-input" value="${this.selectedDate}">
          <select id="deptFilter" class="filter-select">
            <option value="">All Depts</option>
          </select>
        </div>

        <div class="stats-row">
          <div class="stat-card mini">
            <span class="stat-value" id="recordCount">0</span>
            <span class="stat-label">Records</span>
          </div>
          <div class="stat-card mini">
            <span class="stat-value" id="employeeCount">0</span>
            <span class="stat-label">Employees</span>
          </div>
        </div>

        <div class="list-container" id="recordsList">
          <div class="loading-state">Loading location data...</div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    document.getElementById('dateFilter')?.addEventListener('change', (e) => {
      this.selectedDate = (e.target as HTMLInputElement).value;
      this.loadRecords();
    });

    document.getElementById('deptFilter')?.addEventListener('change', (e) => {
      this.filterDepartment = (e.target as HTMLSelectElement).value;
      this.loadRecords();
    });
  }

  private updateList(): void {
    const listContainer = document.getElementById('recordsList');
    const deptFilter = document.getElementById('deptFilter') as HTMLSelectElement;
    
    if (deptFilter && this.departments.length > 0) {
      deptFilter.innerHTML = `
        <option value="">All Depts</option>
        ${this.departments.map(d => `<option value="${d}">${d}</option>`).join('')}
      `;
    }

    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading location data...</div>';
      return;
    }

    const recordEl = document.getElementById('recordCount');
    const employeeEl = document.getElementById('employeeCount');
    const uniqueEmployees = [...new Set(this.records.map(r => r.employee_id))];
    if (recordEl) recordEl.textContent = this.records.length.toString();
    if (employeeEl) employeeEl.textContent = uniqueEmployees.length.toString();

    if (this.records.length === 0) {
      listContainer.innerHTML = '<div class="empty-state">No location records found</div>';
      return;
    }

    const groupedByEmployee = this.records.reduce((acc, rec) => {
      const key = rec.employee_id;
      if (!acc[key]) acc[key] = { employee: rec, records: [] };
      acc[key].records.push(rec);
      return acc;
    }, {} as Record<number, { employee: LocationRecord, records: LocationRecord[] }>);

    listContainer.innerHTML = Object.values(groupedByEmployee).map(group => `
      <div class="list-card location-group-card">
        <div class="location-header">
          <div class="employee-info-row">
            <div class="employee-avatar-sm">${this.getInitials(group.employee.employee_name)}</div>
            <div class="employee-details">
              <div class="employee-name">${group.employee.employee_name}</div>
              <div class="employee-meta">${group.employee.emp_code} • ${group.employee.department || 'N/A'}</div>
            </div>
          </div>
          <span class="record-count">${group.records.length} points</span>
        </div>

        <div class="location-points">
          ${group.records.slice(0, 5).map(rec => `
            <div class="location-point">
              <div class="point-time">${this.formatTime(rec.timestamp)}</div>
              <div class="point-address">${rec.address || `${rec.latitude.toFixed(4)}, ${rec.longitude.toFixed(4)}`}</div>
              <div class="point-meta">
                <span class="accuracy">±${rec.accuracy}m</span>
                ${rec.battery_level ? `<span class="battery">${rec.battery_level}%</span>` : ''}
              </div>
            </div>
          `).join('')}
          ${group.records.length > 5 ? `<div class="more-points">+${group.records.length - 5} more locations</div>` : ''}
        </div>
      </div>
    `).join('');
  }

  private getInitials(name: string): string {
    return name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '??';
  }

  private formatTime(dateStr: string): string {
    if (!dateStr) return '--:--';
    return new Date(dateStr).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  }
}
