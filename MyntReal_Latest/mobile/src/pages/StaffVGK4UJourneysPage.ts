/**
 * Staff VGK4U Journeys Page
 * DC Protocol: DC_MOBILE_VGK4U_JOURNEYS_001
 * VGK4U specific journey management
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface VGK4UJourney {
  id: number;
  employee_name: string;
  emp_code: string;
  date: string;
  client_name: string;
  client_location: string;
  purpose: string;
  start_time: string;
  end_time: string;
  distance_km: number;
  status: string;
  verified: boolean;
  verification_notes?: string;
}

export class StaffVGK4UJourneysPage {
  private container: HTMLElement;
  private journeys: VGK4UJourney[] = [];
  private loading: boolean = true;
  private currentMonth: Date = new Date();
  private filterVerified: string = '';

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
      let endpoint = `/staff/journeys/vgk4u/dashboard?start_date=${startDate}&end_date=${endDate}`;
      if (this.filterVerified) endpoint += `&verified=${this.filterVerified}`;

      const response = await apiService.get<any>(endpoint);
      console.log('[StaffVGK4UJourneysPage] API response:', response);

      if (response.success && response.data) {
        this.journeys = response.data.journeys || response.data || [];
      }
    } catch (error) {
      console.error('[StaffVGK4UJourneysPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    const monthName = this.currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'VGK4U Journeys', showBack: true })}
        
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
          <select id="verifiedFilter" class="filter-select full-width">
            <option value="">All Journeys</option>
            <option value="true">Verified</option>
            <option value="false">Unverified</option>
          </select>
        </div>

        <div class="stats-row">
          <div class="stat-card mini">
            <span class="stat-value" id="totalCount">0</span>
            <span class="stat-label">Total</span>
          </div>
          <div class="stat-card mini success">
            <span class="stat-value" id="verifiedCount">0</span>
            <span class="stat-label">Verified</span>
          </div>
          <div class="stat-card mini pending">
            <span class="stat-value" id="unverifiedCount">0</span>
            <span class="stat-label">Unverified</span>
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

    document.getElementById('verifiedFilter')?.addEventListener('change', (e) => {
      this.filterVerified = (e.target as HTMLSelectElement).value;
      this.loadJourneys();
    });
  }

  private updateList(): void {
    const listContainer = document.getElementById('journeysList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading journeys...</div>';
      return;
    }

    const totalEl = document.getElementById('totalCount');
    const verifiedEl = document.getElementById('verifiedCount');
    const unverifiedEl = document.getElementById('unverifiedCount');
    if (totalEl) totalEl.textContent = this.journeys.length.toString();
    if (verifiedEl) verifiedEl.textContent = this.journeys.filter(j => j.verified).length.toString();
    if (unverifiedEl) unverifiedEl.textContent = this.journeys.filter(j => !j.verified).length.toString();

    if (this.journeys.length === 0) {
      listContainer.innerHTML = '<div class="empty-state">No VGK4U journeys found</div>';
      return;
    }

    listContainer.innerHTML = this.journeys.map(j => `
      <div class="list-card vgk4u-card">
        <div class="vgk4u-header">
          <div class="employee-info">
            <div class="employee-name">${j.employee_name}</div>
            <div class="employee-code">${j.emp_code}</div>
          </div>
          <span class="verified-badge ${j.verified ? 'verified' : 'unverified'}">
            ${j.verified ? '✓ Verified' : 'Unverified'}
          </span>
        </div>

        <div class="vgk4u-client">
          <strong>Client:</strong> ${j.client_name}
        </div>
        <div class="vgk4u-location">${j.client_location}</div>

        <div class="vgk4u-details">
          <div class="detail-row">
            <span class="detail-label">Date</span>
            <span class="detail-value">${this.formatDate(j.date)}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Time</span>
            <span class="detail-value">${this.formatTime(j.start_time)} - ${j.end_time ? this.formatTime(j.end_time) : 'Ongoing'}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Purpose</span>
            <span class="detail-value">${j.purpose}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Distance</span>
            <span class="detail-value">${j.distance_km?.toFixed(1) || 0} km</span>
          </div>
        </div>

        ${j.verification_notes ? `
          <div class="verification-notes">
            <strong>Notes:</strong> ${j.verification_notes}
          </div>
        ` : ''}
      </div>
    `).join('');
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  private formatTime(dateStr: string): string {
    if (!dateStr) return '--:--';
    return new Date(dateStr).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  }
}
