/**
 * Service Reports Page
 * DC Protocol: DC_MOBILE_SERVICE_REPORTS_001
 * View service center reports and analytics
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface ReportData {
  period: string;
  total_tickets: number;
  resolved: number;
  pending: number;
  avg_tat_hours: number;
  total_revenue: number;
  spares_cost: number;
  labor_revenue: number;
}

interface PartnerRevenue {
  partner_id: number;
  partner_name: string;
  total_tickets: number;
  revenue: number;
  spares_revenue: number;
  labor_revenue: number;
}

export class ServiceReportsPage {
  private container: HTMLElement;
  private reportData: ReportData | null = null;
  private partnerRevenue: PartnerRevenue[] = [];
  private loading: boolean = true;
  private period: string = 'month';
  private reportType: string = 'summary';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadReports();
  }

  private async loadReports(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      if (this.reportType === 'revenue') {
        const response = await apiService.get<any>(`/tickets/service/reports/revenue-by-partner?period=${this.period}`);
        if (response.success && response.data) {
          this.partnerRevenue = response.data.partners || response.data || [];
        }
      } else {
        const response = await apiService.get<any>(`/tickets/service/dashboard-stats?period=${this.period}`);
        if (response.success && response.data) {
          this.reportData = response.data;
        }
      }
    } catch (error) {
      console.error('[ServiceReportsPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Service Reports', showBack: true })}
        
        <div class="report-type-tabs">
          <button class="report-tab ${this.reportType === 'summary' ? 'active' : ''}" data-type="summary">Summary</button>
          <button class="report-tab ${this.reportType === 'revenue' ? 'active' : ''}" data-type="revenue">Revenue</button>
        </div>

        <div class="period-selector">
          <button class="period-btn ${this.period === 'week' ? 'active' : ''}" data-period="week">Week</button>
          <button class="period-btn ${this.period === 'month' ? 'active' : ''}" data-period="month">Month</button>
          <button class="period-btn ${this.period === 'quarter' ? 'active' : ''}" data-period="quarter">Quarter</button>
          <button class="period-btn ${this.period === 'year' ? 'active' : ''}" data-period="year">Year</button>
        </div>

        <div id="reportsContent">
          <div class="loading-state">Loading reports...</div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachListeners();
  }

  private attachListeners(): void {
    this.container.querySelectorAll('.report-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.reportType = (tab as HTMLElement).dataset.type || 'summary';
        this.container.querySelectorAll('.report-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.loadReports();
      });
    });

    this.container.querySelectorAll('.period-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.period = (btn as HTMLElement).dataset.period || 'month';
        this.container.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.loadReports();
      });
    });
  }

  private updateContent(): void {
    const content = document.getElementById('reportsContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading reports...</div>';
      return;
    }

    if (this.reportType === 'revenue') {
      content.innerHTML = this.renderRevenueReport();
    } else {
      content.innerHTML = this.renderSummaryReport();
    }
  }

  private renderSummaryReport(): string {
    const data = this.reportData;
    if (!data) return '<div class="empty-state">No data available</div>';

    return `
      <div class="section-card">
        <h4>Ticket Summary</h4>
        <div class="stats-grid-2x2">
          <div class="stat-item">
            <span class="stat-value">${data.total_tickets || 0}</span>
            <span class="stat-label">Total Tickets</span>
          </div>
          <div class="stat-item success">
            <span class="stat-value">${data.resolved || 0}</span>
            <span class="stat-label">Resolved</span>
          </div>
          <div class="stat-item warning">
            <span class="stat-value">${data.pending || 0}</span>
            <span class="stat-label">Pending</span>
          </div>
          <div class="stat-item info">
            <span class="stat-value">${data.avg_tat_hours?.toFixed(1) || 0}h</span>
            <span class="stat-label">Avg TAT</span>
          </div>
        </div>
      </div>

      <div class="section-card">
        <h4>Revenue Breakdown</h4>
        <div class="revenue-summary">
          <div class="revenue-item total">
            <span class="revenue-label">Total Revenue</span>
            <span class="revenue-value">₹${(data.total_revenue || 0).toLocaleString()}</span>
          </div>
          <div class="revenue-item">
            <span class="revenue-label">Labor Revenue</span>
            <span class="revenue-value">₹${(data.labor_revenue || 0).toLocaleString()}</span>
          </div>
          <div class="revenue-item">
            <span class="revenue-label">Spares Cost</span>
            <span class="revenue-value">₹${(data.spares_cost || 0).toLocaleString()}</span>
          </div>
        </div>
      </div>
    `;
  }

  private renderRevenueReport(): string {
    if (this.partnerRevenue.length === 0) {
      return '<div class="empty-state">No revenue data available</div>';
    }

    const totalRevenue = this.partnerRevenue.reduce((sum, p) => sum + (p.revenue || 0), 0);

    return `
      <div class="section-card">
        <h4>Total Revenue: ₹${totalRevenue.toLocaleString()}</h4>
      </div>

      <div class="section-card">
        <h4>Revenue by Partner</h4>
        <div class="partner-revenue-list">
          ${this.partnerRevenue.map(partner => this.renderPartnerRevenue(partner)).join('')}
        </div>
      </div>
    `;
  }

  private renderPartnerRevenue(partner: PartnerRevenue): string {
    return `
      <div class="partner-revenue-row">
        <div class="partner-info">
          <span class="partner-name">${partner.partner_name}</span>
          <span class="ticket-count">${partner.total_tickets} tickets</span>
        </div>
        <div class="partner-revenue">
          <span class="total-revenue">₹${(partner.revenue || 0).toLocaleString()}</span>
          <div class="revenue-breakdown">
            <span>Labor: ₹${(partner.labor_revenue || 0).toLocaleString()}</span>
            <span>Spares: ₹${(partner.spares_revenue || 0).toLocaleString()}</span>
          </div>
        </div>
      </div>
    `;
  }
}
