/**
 * Staff Service Reports Page
 * DC Protocol: DC_MOBILE_SERVICE_REPORTS_001
 * View service ticket reports and analytics
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface ServiceReport {
  period: string;
  total_tickets: number;
  resolved: number;
  pending: number;
  escalated: number;
  avg_resolution_time: number;
  sla_met: number;
  sla_breached: number;
  revenue: number;
}

interface CategoryBreakdown {
  category: string;
  count: number;
  percentage: number;
}

export class StaffServiceReportsPage {
  private container: HTMLElement;
  private report: ServiceReport | null = null;
  private categories: CategoryBreakdown[] = [];
  private loading: boolean = true;
  private dateRange: string = 'month';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadReport();
  }

  private async loadReport(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>(`/tickets/service/reports?range=${this.dateRange}`);
      console.log('[StaffServiceReportsPage] API response:', response);

      if (response.success && response.data) {
        this.report = response.data.report || response.data;
        this.categories = response.data.by_category || [];
      }
    } catch (error) {
      console.error('[StaffServiceReportsPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Service Reports', showBack: true })}
        
        <div class="date-filter">
          <select id="dateRange" class="filter-select full-width">
            <option value="week" ${this.dateRange === 'week' ? 'selected' : ''}>This Week</option>
            <option value="month" ${this.dateRange === 'month' ? 'selected' : ''}>This Month</option>
            <option value="quarter" ${this.dateRange === 'quarter' ? 'selected' : ''}>This Quarter</option>
            <option value="year" ${this.dateRange === 'year' ? 'selected' : ''}>This Year</option>
          </select>
        </div>

        <div class="content-area" id="contentArea">
          <div class="loading-state">Loading reports...</div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    document.getElementById('dateRange')?.addEventListener('change', (e) => {
      this.dateRange = (e.target as HTMLSelectElement).value;
      this.loadReport();
    });
  }

  private updateContent(): void {
    const contentArea = document.getElementById('contentArea');
    if (!contentArea) return;

    if (this.loading) {
      contentArea.innerHTML = '<div class="loading-state">Loading reports...</div>';
      return;
    }

    if (!this.report) {
      contentArea.innerHTML = '<div class="empty-state">No report data available</div>';
      return;
    }

    const r = this.report;
    contentArea.innerHTML = `
      <div class="report-section">
        <h4 class="section-title">Ticket Summary</h4>
        <div class="report-grid">
          <div class="report-card">
            <div class="report-value">${r.total_tickets}</div>
            <div class="report-label">Total</div>
          </div>
          <div class="report-card success">
            <div class="report-value">${r.resolved}</div>
            <div class="report-label">Resolved</div>
          </div>
          <div class="report-card pending">
            <div class="report-value">${r.pending}</div>
            <div class="report-label">Pending</div>
          </div>
          <div class="report-card danger">
            <div class="report-value">${r.escalated}</div>
            <div class="report-label">Escalated</div>
          </div>
        </div>
      </div>

      <div class="report-section">
        <h4 class="section-title">SLA Performance</h4>
        <div class="sla-stats">
          <div class="sla-item success">
            <span class="sla-value">${r.sla_met}</span>
            <span class="sla-label">SLA Met</span>
          </div>
          <div class="sla-item danger">
            <span class="sla-value">${r.sla_breached}</span>
            <span class="sla-label">SLA Breached</span>
          </div>
        </div>
        <div class="sla-percentage">
          ${r.total_tickets > 0 ? ((r.sla_met / r.total_tickets) * 100).toFixed(1) : 0}% compliance
        </div>
      </div>

      <div class="report-section">
        <h4 class="section-title">Key Metrics</h4>
        <div class="metrics-list">
          <div class="metric-row">
            <span class="metric-label">Avg Resolution Time</span>
            <span class="metric-value">${r.avg_resolution_time} hrs</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">Total Revenue</span>
            <span class="metric-value highlight">₹${r.revenue?.toLocaleString() || 0}</span>
          </div>
        </div>
      </div>

      ${this.categories.length > 0 ? `
        <div class="report-section">
          <h4 class="section-title">By Category</h4>
          <div class="category-breakdown">
            ${this.categories.map(cat => `
              <div class="category-item">
                <div class="category-info">
                  <span class="category-name">${cat.category}</span>
                  <span class="category-count">${cat.count} tickets</span>
                </div>
                <div class="category-bar">
                  <div class="category-fill" style="width: ${cat.percentage}%"></div>
                </div>
                <span class="category-pct">${cat.percentage?.toFixed(0)}%</span>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}
    `;
  }
}
