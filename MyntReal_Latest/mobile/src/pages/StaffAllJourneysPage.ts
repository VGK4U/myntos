/**
 * Staff All Journeys Page
 * DC Protocol: DC_MOBILE_ALL_JOURNEYS_001
 * View all employee journeys (admin view)
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface Journey {
  id: number;
  employee_id: number;
  employee_name: string;
  emp_code: string;
  department: string;
  company_name: string;
  start_time: string;
  end_time: string;
  start_location: string;
  end_location: string;
  transport_mode: string;
  purpose: string;
  distance_km: number;
  duration_minutes: number;
  status: string;
  reimbursement_amount?: number;
}

export class StaffAllJourneysPage {
  private container: HTMLElement;
  private journeys: Journey[] = [];
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
    await this.loadJourneys();
  }

  private async loadJourneys(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      const year = this.currentMonth.getFullYear();
      const month = this.currentMonth.getMonth() + 1;
      const startDate = `${year}-${String(month).padStart(2, '0')}-01`;
      const lastDay = new Date(year, month, 0).getDate();
      const endDate = `${year}-${String(month).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;
      let endpoint = `/staff/journeys/all?start_date=${startDate}&end_date=${endDate}`;
      if (this.filterDepartment) endpoint += `&department=${this.filterDepartment}`;
      if (this.filterStatus) endpoint += `&status=${this.filterStatus}`;

      const response = await apiService.get<any>(endpoint);
      console.log('[StaffAllJourneysPage] API response:', response);

      if (response.success && response.data) {
        this.journeys = response.data.journeys || response.data || [];
        this.departments = [...new Set(this.journeys.map(j => j.department).filter(Boolean))];
      }
    } catch (error) {
      console.error('[StaffAllJourneysPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    const monthName = this.currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'All Journeys', showBack: true })}
        
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
            <option value="">All Depts</option>
          </select>
          <select id="statusFilter" class="filter-select">
            <option value="">All Status</option>
            <option value="completed">Completed</option>
            <option value="in_progress">In Progress</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        <div class="stats-row">
          <div class="stat-card mini">
            <span class="stat-value" id="totalCount">0</span>
            <span class="stat-label">Journeys</span>
          </div>
          <div class="stat-card mini">
            <span class="stat-value" id="totalKm">0</span>
            <span class="stat-label">Total KM</span>
          </div>
          <div class="stat-card mini">
            <span class="stat-value" id="totalReimb">0</span>
            <span class="stat-label">Reimbursement</span>
          </div>
        </div>

        <div class="list-container" id="journeysList">
          <div class="loading-state">Loading journeys...</div>
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
      this.loadJourneys();
    });

    document.getElementById('nextMonth')?.addEventListener('click', () => {
      this.currentMonth.setMonth(this.currentMonth.getMonth() + 1);
      this.render();
      this.loadJourneys();
    });

    document.getElementById('deptFilter')?.addEventListener('change', (e) => {
      this.filterDepartment = (e.target as HTMLSelectElement).value;
      this.loadJourneys();
    });

    document.getElementById('statusFilter')?.addEventListener('change', (e) => {
      this.filterStatus = (e.target as HTMLSelectElement).value;
      this.loadJourneys();
    });
  }

  private updateList(): void {
    const listContainer = document.getElementById('journeysList');
    const deptFilter = document.getElementById('deptFilter') as HTMLSelectElement;
    
    if (deptFilter && this.departments.length > 0) {
      deptFilter.innerHTML = `
        <option value="">All Depts</option>
        ${this.departments.map(d => `<option value="${d}">${d}</option>`).join('')}
      `;
    }

    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading journeys...</div>';
      return;
    }

    const totalEl = document.getElementById('totalCount');
    const totalKmEl = document.getElementById('totalKm');
    const totalReimbEl = document.getElementById('totalReimb');
    if (totalEl) totalEl.textContent = this.journeys.length.toString();
    if (totalKmEl) totalKmEl.textContent = this.journeys.reduce((sum, j) => sum + (j.distance_km || 0), 0).toFixed(1);
    if (totalReimbEl) totalReimbEl.textContent = '₹' + this.journeys.reduce((sum, j) => sum + (j.reimbursement_amount || 0), 0).toFixed(0);

    if (this.journeys.length === 0) {
      listContainer.innerHTML = '<div class="empty-state">No journeys found</div>';
      return;
    }

    listContainer.innerHTML = this.journeys.map(j => `
      <div class="list-card journey-card">
        <div class="journey-header">
          <div class="employee-info-row">
            <div class="employee-avatar-sm">${this.getInitials(j.employee_name)}</div>
            <div class="employee-details">
              <div class="employee-name">${j.employee_name}</div>
              <div class="employee-meta">${j.emp_code} • ${j.department || 'N/A'}</div>
            </div>
          </div>
          <span class="status-badge ${j.status}">${j.status}</span>
        </div>

        <div class="journey-route">
          <div class="route-point start">
            <span class="route-dot"></span>
            <span class="route-text">${j.start_location || 'Start'}</span>
            <span class="route-time">${this.formatTime(j.start_time)}</span>
          </div>
          <div class="route-line"></div>
          <div class="route-point end">
            <span class="route-dot"></span>
            <span class="route-text">${j.end_location || 'End'}</span>
            <span class="route-time">${j.end_time ? this.formatTime(j.end_time) : '--:--'}</span>
          </div>
        </div>

        <div class="journey-meta">
          <span class="meta-badge">${j.transport_mode}</span>
          <span class="meta-badge">${j.purpose}</span>
          <span class="meta-badge">${j.company_name}</span>
        </div>

        <div class="journey-stats">
          <div class="stat-item">
            <span class="stat-val">${j.distance_km?.toFixed(1) || 0} km</span>
            <span class="stat-lbl">Distance</span>
          </div>
          <div class="stat-item">
            <span class="stat-val">${j.duration_minutes || 0} min</span>
            <span class="stat-lbl">Duration</span>
          </div>
          ${j.reimbursement_amount ? `
            <div class="stat-item">
              <span class="stat-val">₹${j.reimbursement_amount}</span>
              <span class="stat-lbl">Reimb</span>
            </div>
          ` : ''}
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
