/**
 * Staff Service Revenue Page
 * DC Protocol: DC_MOBILE_SERVICE_REVENUE_001
 * View service revenue analytics
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface RevenueData {
  total_revenue: number;
  labor_revenue: number;
  parts_revenue: number;
  tickets_billed: number;
  avg_ticket_value: number;
  collection_rate: number;
}

interface RevenueTrend {
  period: string;
  revenue: number;
  tickets: number;
}

export class StaffServiceRevenuePage {
  private container: HTMLElement;
  private data: RevenueData | null = null;
  private trends: RevenueTrend[] = [];
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
      const response = await apiService.get<any>(`/tickets/service/reports/revenue-by-partner?range=${this.dateRange}`);
      console.log('[StaffServiceRevenuePage] API response:', response);

      if (response.success && response.data) {
        this.data = response.data.summary || response.data;
        this.trends = response.data.trends || [];
      }
    } catch (error) {
      console.error('[StaffServiceRevenuePage] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Service Revenue', showBack: true })}
        
        <div class="date-filter">
          <select id="dateRange" class="filter-select full-width">
            <option value="week" ${this.dateRange === 'week' ? 'selected' : ''}>This Week</option>
            <option value="month" ${this.dateRange === 'month' ? 'selected' : ''}>This Month</option>
            <option value="quarter" ${this.dateRange === 'quarter' ? 'selected' : ''}>This Quarter</option>
            <option value="year" ${this.dateRange === 'year' ? 'selected' : ''}>This Year</option>
          </select>
        </div>

        <div class="content-area" id="contentArea">
          <div class="loading-state">Loading revenue data...</div>
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
      contentArea.innerHTML = '<div class="loading-state">Loading revenue data...</div>';
      return;
    }

    if (!this.data) {
      contentArea.innerHTML = '<div class="empty-state">No revenue data available</div>';
      return;
    }

    const d = this.data;
    contentArea.innerHTML = `
      <div class="revenue-hero">
        <div class="hero-label">Total Revenue</div>
        <div class="hero-value">₹${d.total_revenue?.toLocaleString() || 0}</div>
      </div>

      <div class="revenue-section">
        <h4 class="section-title">Revenue Breakdown</h4>
        <div class="breakdown-list">
          <div class="breakdown-item">
            <div class="breakdown-info">
              <span class="breakdown-label">Labor Revenue</span>
              <span class="breakdown-value">₹${d.labor_revenue?.toLocaleString() || 0}</span>
            </div>
            <div class="breakdown-bar">
              <div class="breakdown-fill labor" style="width: ${d.total_revenue ? (d.labor_revenue / d.total_revenue * 100) : 0}%"></div>
            </div>
          </div>
          <div class="breakdown-item">
            <div class="breakdown-info">
              <span class="breakdown-label">Parts Revenue</span>
              <span class="breakdown-value">₹${d.parts_revenue?.toLocaleString() || 0}</span>
            </div>
            <div class="breakdown-bar">
              <div class="breakdown-fill parts" style="width: ${d.total_revenue ? (d.parts_revenue / d.total_revenue * 100) : 0}%"></div>
            </div>
          </div>
        </div>
      </div>

      <div class="revenue-section">
        <h4 class="section-title">Key Metrics</h4>
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-value">${d.tickets_billed}</div>
            <div class="metric-label">Tickets Billed</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">₹${d.avg_ticket_value?.toLocaleString() || 0}</div>
            <div class="metric-label">Avg Ticket Value</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">${d.collection_rate}%</div>
            <div class="metric-label">Collection Rate</div>
          </div>
        </div>
      </div>

      ${this.trends.length > 0 ? `
        <div class="revenue-section">
          <h4 class="section-title">Revenue Trend</h4>
          <div class="trend-list">
            ${this.trends.map(t => `
              <div class="trend-item">
                <div class="trend-period">${t.period}</div>
                <div class="trend-stats">
                  <span class="trend-revenue">₹${t.revenue?.toLocaleString()}</span>
                  <span class="trend-tickets">${t.tickets} tickets</span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}
    `;
  }
}
