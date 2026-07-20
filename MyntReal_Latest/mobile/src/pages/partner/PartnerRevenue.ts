/**
 * Partner Revenue Dashboard Page
 * DC Protocol: DC_MOBILE_PARTNER_REVENUE_001
 * View revenue analytics
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface RevenueData {
  total_revenue: number;
  this_month: number;
  last_month: number;
  growth_percentage: number;
  pending_payments: number;
  received_payments: number;
  monthly_breakdown: { month: string; amount: number }[];
}

export class PartnerRevenue {
  private container: HTMLElement;
  private data: RevenueData | null = null;
  private loading: boolean = true;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadRevenue();
  }

  private async loadRevenue(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<RevenueData>('/partner/revenue-dashboard');
      if (response.success && response.data) {
        this.data = response.data;
      }
    } catch (error) {
      console.error('[PartnerRevenue] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Revenue Dashboard', showBack: true })}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'Revenue Dashboard', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const d = this.data || { 
      total_revenue: 0, 
      this_month: 0, 
      last_month: 0, 
      growth_percentage: 0,
      pending_payments: 0,
      received_payments: 0,
      monthly_breakdown: []
    };

    const growthColor = d.growth_percentage >= 0 ? 'var(--success)' : 'var(--danger)';
    const growthIcon = d.growth_percentage >= 0 ? '↑' : '↓';

    content.innerHTML = `
      <div class="revenue-overview card">
        <div class="total-revenue">
          <span class="label">Total Revenue</span>
          <span class="amount">₹${d.total_revenue.toLocaleString()}</span>
        </div>
        <div class="growth-indicator" style="color: ${growthColor}">
          ${growthIcon} ${Math.abs(d.growth_percentage)}% vs last month
        </div>
      </div>

      <div class="stats-grid">
        <div class="card stat-card">
          <p class="stat-value">₹${d.this_month.toLocaleString()}</p>
          <p class="stat-label">This Month</p>
        </div>
        <div class="card stat-card">
          <p class="stat-value">₹${d.last_month.toLocaleString()}</p>
          <p class="stat-label">Last Month</p>
        </div>
        <div class="card stat-card success">
          <p class="stat-value">₹${d.received_payments.toLocaleString()}</p>
          <p class="stat-label">Received</p>
        </div>
        <div class="card stat-card warning">
          <p class="stat-value">₹${d.pending_payments.toLocaleString()}</p>
          <p class="stat-label">Pending</p>
        </div>
      </div>

      <div class="monthly-breakdown card">
        <h3 class="card-title">Monthly Breakdown</h3>
        <div class="breakdown-list">
          ${d.monthly_breakdown.length === 0 ? '<p class="empty-text">No data available</p>' :
            d.monthly_breakdown.map(item => `
              <div class="breakdown-item">
                <span class="month">${item.month}</span>
                <span class="amount">₹${item.amount.toLocaleString()}</span>
              </div>
            `).join('')
          }
        </div>
      </div>
    `;
  }
}
