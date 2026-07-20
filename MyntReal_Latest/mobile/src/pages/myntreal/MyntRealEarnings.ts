/**
 * MyntReal Earnings Page
 * DC Protocol: DC_MOBILE_MYNTREAL_EARN_001
 * View MyntReal incentive earnings
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface EarningRecord {
  id: number;
  type: string;
  property_title: string;
  amount: number;
  status: string;
  created_at: string;
}

interface EarningSummary {
  total_earnings: number;
  pending_amount: number;
  approved_amount: number;
  disbursed_amount: number;
  properties_count: number;
}

export class MyntRealEarnings {
  private container: HTMLElement;
  private earnings: EarningRecord[] = [];
  private summary: EarningSummary | null = null;
  private loading: boolean = true;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadEarnings();
  }

  private async loadEarnings(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>('/myntreal/my-zynova-incentives');
      if (response.success && response.data) {
        this.earnings = response.data.earnings || [];
        this.summary = response.data.summary || null;
      }
    } catch (error) {
      console.error('[MyntRealEarnings] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container myntreal-page">
        ${PageHeader.render({ title: 'MyntReal Earnings', showBack: true })}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'MyntReal Earnings', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const s = this.summary || {
      total_earnings: 0,
      pending_amount: 0,
      approved_amount: 0,
      disbursed_amount: 0,
      properties_count: 0
    };

    content.innerHTML = `
      <div class="myntreal-banner card">
        <div class="banner-icon">💰</div>
        <h2>MyntReal Earnings</h2>
        <p>Your property referral income</p>
      </div>

      <div class="earnings-summary card">
        <div class="total-section">
          <span class="total-label">Total Earnings</span>
          <span class="total-value">₹${s.total_earnings.toLocaleString()}</span>
        </div>
        <div class="summary-grid">
          <div class="summary-item pending">
            <span class="item-value">₹${s.pending_amount.toLocaleString()}</span>
            <span class="item-label">Pending</span>
          </div>
          <div class="summary-item approved">
            <span class="item-value">₹${s.approved_amount.toLocaleString()}</span>
            <span class="item-label">Approved</span>
          </div>
          <div class="summary-item disbursed">
            <span class="item-value">₹${s.disbursed_amount.toLocaleString()}</span>
            <span class="item-label">Paid</span>
          </div>
          <div class="summary-item properties">
            <span class="item-value">${s.properties_count}</span>
            <span class="item-label">Properties</span>
          </div>
        </div>
      </div>

      <h3 class="section-title">Recent Transactions</h3>
      <div class="earnings-list">
        ${this.earnings.length === 0 ? 
          '<div class="empty-state">No earnings yet. Start referring properties!</div>' :
          this.earnings.map(e => `
            <div class="earning-card card">
              <div class="earning-icon">🏠</div>
              <div class="earning-info">
                <h4>${e.property_title || 'Property Referral'}</h4>
                <p class="earning-type">${e.type}</p>
                <span class="earning-date">${this.formatDate(e.created_at)}</span>
              </div>
              <div class="earning-amount-section">
                <span class="earning-amount">₹${e.amount.toLocaleString()}</span>
                <span class="earning-status ${e.status.toLowerCase()}">${e.status}</span>
              </div>
            </div>
          `).join('')
        }
      </div>
    `;
  }

  private formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
  }
}
