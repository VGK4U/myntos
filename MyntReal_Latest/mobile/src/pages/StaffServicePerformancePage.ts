/**
 * Staff Service Performance Page
 * DC Protocol: DC_MOBILE_SERVICE_PERFORMANCE_001
 * View service ticket performance metrics
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface PerformanceMetrics {
  total_tickets: number;
  resolved_tickets: number;
  pending_tickets: number;
  avg_resolution_time: number;
  sla_compliance: number;
  customer_satisfaction: number;
  first_response_time: number;
}

interface TechnicianPerformance {
  employee_id: number;
  employee_name: string;
  emp_code: string;
  tickets_resolved: number;
  avg_resolution_time: number;
  sla_compliance: number;
  rating: number;
}

export class StaffServicePerformancePage {
  private container: HTMLElement;
  private metrics: PerformanceMetrics | null = null;
  private technicians: TechnicianPerformance[] = [];
  private loading: boolean = true;
  private dateRange: string = 'month';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadData();
  }

  private async loadData(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>(`/tickets/service/reports?range=${this.dateRange}`);
      console.log('[StaffServicePerformancePage] API response:', response);

      if (response.success && response.data) {
        this.metrics = response.data.metrics || response.data;
        this.technicians = response.data.technicians || [];
      }
    } catch (error) {
      console.error('[StaffServicePerformancePage] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Service Performance', showBack: true })}
        
        <div class="date-filter">
          <select id="dateRange" class="filter-select full-width">
            <option value="week" ${this.dateRange === 'week' ? 'selected' : ''}>This Week</option>
            <option value="month" ${this.dateRange === 'month' ? 'selected' : ''}>This Month</option>
            <option value="quarter" ${this.dateRange === 'quarter' ? 'selected' : ''}>This Quarter</option>
          </select>
        </div>

        <div class="content-area" id="contentArea">
          <div class="loading-state">Loading performance data...</div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    document.getElementById('dateRange')?.addEventListener('change', (e) => {
      this.dateRange = (e.target as HTMLSelectElement).value;
      this.loadData();
    });
  }

  private updateContent(): void {
    const contentArea = document.getElementById('contentArea');
    if (!contentArea) return;

    if (this.loading) {
      contentArea.innerHTML = '<div class="loading-state">Loading performance data...</div>';
      return;
    }

    if (!this.metrics) {
      contentArea.innerHTML = '<div class="empty-state">No performance data available</div>';
      return;
    }

    const m = this.metrics;
    contentArea.innerHTML = `
      <div class="metrics-section">
        <h4 class="section-title">Overview</h4>
        <div class="performance-grid">
          <div class="perf-card">
            <div class="perf-value">${m.total_tickets}</div>
            <div class="perf-label">Total Tickets</div>
          </div>
          <div class="perf-card success">
            <div class="perf-value">${m.resolved_tickets}</div>
            <div class="perf-label">Resolved</div>
          </div>
          <div class="perf-card pending">
            <div class="perf-value">${m.pending_tickets}</div>
            <div class="perf-label">Pending</div>
          </div>
        </div>
      </div>

      <div class="metrics-section">
        <h4 class="section-title">Key Metrics</h4>
        <div class="metrics-list">
          <div class="metric-row">
            <span class="metric-label">Avg Resolution Time</span>
            <span class="metric-value">${m.avg_resolution_time} hrs</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">First Response Time</span>
            <span class="metric-value">${m.first_response_time} mins</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">SLA Compliance</span>
            <span class="metric-value ${m.sla_compliance >= 90 ? 'good' : m.sla_compliance >= 70 ? 'warning' : 'poor'}">${m.sla_compliance}%</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">Customer Satisfaction</span>
            <span class="metric-value">${m.customer_satisfaction}/5 ⭐</span>
          </div>
        </div>
      </div>

      ${this.technicians.length > 0 ? `
        <div class="metrics-section">
          <h4 class="section-title">Technician Performance</h4>
          <div class="technician-list">
            ${this.technicians.map(tech => `
              <div class="list-card technician-card">
                <div class="tech-header">
                  <div class="tech-info">
                    <div class="tech-name">${tech.employee_name}</div>
                    <div class="tech-code">${tech.emp_code}</div>
                  </div>
                  <div class="tech-rating">${tech.rating?.toFixed(1) || 'N/A'} ⭐</div>
                </div>
                <div class="tech-stats">
                  <div class="stat-item">
                    <span class="stat-val">${tech.tickets_resolved}</span>
                    <span class="stat-lbl">Resolved</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-val">${tech.avg_resolution_time}h</span>
                    <span class="stat-lbl">Avg Time</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-val">${tech.sla_compliance}%</span>
                    <span class="stat-lbl">SLA</span>
                  </div>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}
    `;
  }
}
