/**
 * MNR Comprehensive Earnings Summary Page - Web Parity
 * DC Protocol: DC_MOBILE_MNR_EARNINGS_SUMMARY_003
 * Matches web: /myntreal/points/me, /myntreal/earnings-summary, /myntreal/my-incentives, /myntreal/points/my-history
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';
import { routerService } from '../../services/router.service';

interface PointsBalance {
  current_balance: number;
  total_allocated: number;
  total_consumed: number;
}

interface EarningsSummaryData {
  total_earnings: number;
  myntreal_count: number;
  zynova_count: number;
  pending_count: number;
}

interface Incentive {
  created_at: string;
  system: string;
  category: string;
  incentive_amount?: number;
  amount?: number;
  status: string;
}

interface PointsTransaction {
  created_at: string;
  transaction_type: string;
  amount: number;
  reference_type?: string;
}

export class MNREarningsSummary {
  private container: HTMLElement;
  private points: PointsBalance = { current_balance: 0, total_allocated: 0, total_consumed: 0 };
  private summary: EarningsSummaryData = { total_earnings: 0, myntreal_count: 0, zynova_count: 0, pending_count: 0 };
  private incentives: Incentive[] = [];
  private pointsHistory: PointsTransaction[] = [];
  private loading: boolean = true;
  private activeTab: 'incentives' | 'points' = 'incentives';

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
      const [pointsRes, summaryRes, incentivesRes] = await Promise.all([
        apiService.get<any>('/myntreal/points/me'),
        apiService.get<any>('/myntreal/earnings-summary'),
        apiService.get<any>('/myntreal/my-incentives')
      ]);

      if (pointsRes.success && pointsRes.data) {
        this.points = {
          current_balance: pointsRes.data.current_balance || 0,
          total_allocated: pointsRes.data.total_allocated || 0,
          total_consumed: pointsRes.data.total_consumed || 0
        };
      }

      if (summaryRes.success && summaryRes.data) {
        this.summary = {
          total_earnings: summaryRes.data.total_earnings || 0,
          myntreal_count: summaryRes.data.myntreal_count || 0,
          zynova_count: summaryRes.data.zynova_count || 0,
          pending_count: summaryRes.data.pending_count || 0
        };
      }

      if (incentivesRes.success && incentivesRes.data) {
        const items = incentivesRes.data.data || incentivesRes.data || [];
        this.incentives = Array.isArray(items) ? items : [];
      }
    } catch (error) {
      console.error('[MNREarningsSummary] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private async loadPointsHistory(): Promise<void> {
    try {
      const res = await apiService.get<any>('/myntreal/points/my-history');
      if (res.success && res.data) {
        const items = res.data.data || res.data || [];
        this.pointsHistory = Array.isArray(items) ? items : [];
      }
    } catch (error) {
      console.error('[MNREarningsSummary] Failed to load points history:', error);
    }
    this.updateTabContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        .earnings-page {
          background: linear-gradient(135deg, #0a1929 0%, #0d2137 100%);
          min-height: 100vh;
        }
        .earnings-content { padding: 16px; }

        .points-display {
          background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
          border-radius: 12px;
          padding: 24px;
          text-align: center;
          margin-bottom: 16px;
        }
        .points-value {
          font-size: 36px;
          font-weight: 700;
          color: #92400e;
        }
        .points-label {
          color: #b45309;
          font-size: 14px;
          margin-top: 4px;
        }
        .points-breakdown {
          margin-top: 16px;
          display: flex;
          justify-content: center;
          gap: 32px;
        }
        .breakdown-item { text-align: center; }
        .breakdown-value {
          font-size: 18px;
          font-weight: 600;
          color: #92400e;
        }
        .breakdown-label {
          font-size: 11px;
          color: #b45309;
        }

        .summary-cards {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
          margin-bottom: 16px;
        }
        @media (min-width: 480px) {
          .summary-cards { grid-template-columns: repeat(4, 1fr); }
        }
        .summary-card {
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          padding: 16px;
          text-align: center;
        }
        .summary-card .card-icon {
          font-size: 20px;
          margin-bottom: 8px;
        }
        .summary-card .card-value {
          font-size: 20px;
          font-weight: 700;
          color: #ffffff;
        }
        .summary-card .card-value.green { color: #10b981; }
        .summary-card .card-value.gold { color: #f59e0b; }
        .summary-card .card-value.blue { color: #3b82f6; }
        .summary-card .card-value.purple { color: #8b5cf6; }
        .summary-card .card-label {
          font-size: 11px;
          color: #94a3b8;
          margin-top: 4px;
        }

        .tabs-container {
          margin-bottom: 16px;
        }
        .tabs-row {
          display: flex;
          background: rgba(255, 255, 255, 0.08);
          border-radius: 10px;
          padding: 4px;
          gap: 4px;
        }
        .tab-btn {
          flex: 1;
          padding: 10px 16px;
          border: none;
          border-radius: 8px;
          font-size: 13px;
          font-weight: 500;
          color: #94a3b8;
          background: transparent;
          cursor: pointer;
          transition: all 0.2s;
        }
        .tab-btn.active {
          background: rgba(255, 255, 255, 0.15);
          color: #ffffff;
          font-weight: 600;
        }

        .data-card {
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          overflow: hidden;
        }
        .data-card-header {
          padding: 14px 16px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          color: #e2e8f0;
          font-size: 14px;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .table-container {
          overflow-x: auto;
          -webkit-overflow-scrolling: touch;
        }
        .earnings-table {
          width: 100%;
          min-width: 500px;
          border-collapse: collapse;
          font-size: 13px;
        }
        .earnings-table th {
          padding: 10px 12px;
          text-align: left;
          font-weight: 600;
          color: #94a3b8;
          font-size: 11px;
          text-transform: uppercase;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          background: rgba(255, 255, 255, 0.03);
        }
        .earnings-table th.text-end { text-align: right; }
        .earnings-table th.text-center { text-align: center; }
        .earnings-table td {
          padding: 12px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
          color: #e2e8f0;
          vertical-align: middle;
        }
        .earnings-table td.text-end { text-align: right; }
        .earnings-table td.text-center { text-align: center; }
        .earnings-table tbody tr:hover {
          background: rgba(255, 255, 255, 0.03);
        }

        .system-badge {
          display: inline-block;
          padding: 3px 8px;
          border-radius: 4px;
          font-size: 10px;
          font-weight: 600;
          text-transform: uppercase;
        }
        .system-myntreal { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
        .system-zynova { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }

        .status-badge {
          display: inline-block;
          padding: 3px 10px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 500;
        }
        .status-pending { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
        .status-approved { background: rgba(16, 185, 129, 0.15); color: #34d399; }
        .status-rejected { background: rgba(239, 68, 68, 0.15); color: #f87171; }

        .amount-positive { color: #10b981; font-weight: 700; }
        .amount-credit { color: #10b981; }
        .amount-debit { color: #f87171; }

        .type-badge {
          display: inline-block;
          padding: 3px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 500;
          background: rgba(148, 163, 184, 0.15);
          color: #94a3b8;
        }

        .empty-state {
          text-align: center;
          padding: 40px 20px;
          color: #64748b;
        }
        .empty-state svg { margin-bottom: 12px; opacity: 0.5; }

        .loading-state {
          text-align: center;
          padding: 60px 20px;
          color: #8892b0;
        }

        .back-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          margin-top: 16px;
          padding: 10px 16px;
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 8px;
          color: #94a3b8;
          font-size: 13px;
          cursor: pointer;
        }
      </style>

      ${PageHeader.render({ title: '📊 Facilitation Summary', showBack: true })}
      <div class="earnings-page">
        <div class="earnings-content" id="pageContent">
          <div class="loading-state">Loading earnings data...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: '📊 Facilitation Summary', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading earnings data...</div>';
      return;
    }

    content.innerHTML = `
      <!-- Points Display -->
      <div class="points-display">
        <div class="points-value">${this.formatIndian(this.points.current_balance)}</div>
        <div class="points-label">Available MNR Points</div>
        <div class="points-breakdown">
          <div class="breakdown-item">
            <div class="breakdown-value">${this.formatIndian(this.points.total_allocated)}</div>
            <div class="breakdown-label">Total Allocated</div>
          </div>
          <div class="breakdown-item">
            <div class="breakdown-value">${this.formatIndian(this.points.total_consumed)}</div>
            <div class="breakdown-label">Used</div>
          </div>
        </div>
      </div>

      <!-- Summary Cards -->
      <div class="summary-cards">
        <div class="summary-card">
          <div class="card-icon">💰</div>
          <div class="card-value green">₹${this.formatIndian(this.summary.total_earnings)}</div>
          <div class="card-label">Total Earnings</div>
        </div>
        <div class="summary-card">
          <div class="card-icon">⭐</div>
          <div class="card-value gold">${this.summary.myntreal_count}</div>
          <div class="card-label">MyntReal Incentives</div>
        </div>
        <div class="summary-card">
          <div class="card-icon">🔗</div>
          <div class="card-value blue">${this.summary.zynova_count}</div>
          <div class="card-label">Zynova Incentives</div>
        </div>
        <div class="summary-card">
          <div class="card-icon">⏳</div>
          <div class="card-value purple">${this.summary.pending_count}</div>
          <div class="card-label">Pending Approval</div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="tabs-container">
        <div class="tabs-row">
          <button class="tab-btn ${this.activeTab === 'incentives' ? 'active' : ''}" id="tabIncentives">My Incentives</button>
          <button class="tab-btn ${this.activeTab === 'points' ? 'active' : ''}" id="tabPoints">Points History</button>
        </div>
      </div>

      <!-- Data Table -->
      <div class="data-card">
        <div class="data-card-header" id="tableTitle">
          ${this.activeTab === 'incentives' ? '📋 My Incentives' : '📜 Points History'}
        </div>
        <div id="tabContent">
          ${this.activeTab === 'incentives' ? this.renderIncentivesTable() : this.renderPointsTable()}
        </div>
      </div>

      <button class="back-btn" id="backToDashboard">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="19" y1="12" x2="5" y2="12"></line>
          <polyline points="12 19 5 12 12 5"></polyline>
        </svg>
        Back to Dashboard
      </button>
    `;

    this.attachListeners();
  }

  private renderIncentivesTable(): string {
    if (!this.incentives.length) {
      return `
        <div class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <p>No incentives yet</p>
        </div>`;
    }

    return `
      <div class="table-container">
        <table class="earnings-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>System</th>
              <th>Category</th>
              <th class="text-end">Amount</th>
              <th class="text-center">Status</th>
            </tr>
          </thead>
          <tbody>
            ${this.incentives.map(item => {
              const date = item.created_at ? new Date(item.created_at).toLocaleDateString('en-IN') : 'N/A';
              const systemClass = item.system === 'zynova' ? 'system-zynova' : 'system-myntreal';
              const systemLabel = item.system === 'zynova' ? 'Zynova' : 'MyntReal';
              const category = (item.category || '-').replace(/_/g, ' ');
              const amount = item.incentive_amount || item.amount || 0;
              const status = item.status || 'pending';
              const statusClass = status === 'approved' ? 'status-approved' : status === 'rejected' ? 'status-rejected' : 'status-pending';

              return `
                <tr>
                  <td>${date}</td>
                  <td><span class="system-badge ${systemClass}">${systemLabel}</span></td>
                  <td style="text-transform: capitalize;">${category}</td>
                  <td class="text-end amount-positive">₹${this.formatIndian(amount)}</td>
                  <td class="text-center">
                    <span class="status-badge ${statusClass}">${status.charAt(0).toUpperCase() + status.slice(1)}</span>
                  </td>
                </tr>`;
            }).join('')}
          </tbody>
        </table>
      </div>`;
  }

  private renderPointsTable(): string {
    if (!this.pointsHistory.length) {
      return `
        <div class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <p>No points transactions yet</p>
        </div>`;
    }

    return `
      <div class="table-container">
        <table class="earnings-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Type</th>
              <th class="text-end">Amount</th>
              <th>Reference</th>
            </tr>
          </thead>
          <tbody>
            ${this.pointsHistory.map(txn => {
              const date = txn.created_at ? new Date(txn.created_at).toLocaleDateString('en-IN') : 'N/A';
              const isCredit = txn.transaction_type === 'allocation' || txn.transaction_type === 'refund';
              const amountClass = isCredit ? 'amount-credit' : 'amount-debit';
              const sign = isCredit ? '+' : '-';

              return `
                <tr>
                  <td>${date}</td>
                  <td><span class="type-badge">${txn.transaction_type || '-'}</span></td>
                  <td class="text-end ${amountClass}">${sign}${this.formatIndian(txn.amount || 0)}</td>
                  <td>${txn.reference_type || '-'}</td>
                </tr>`;
            }).join('')}
          </tbody>
        </table>
      </div>`;
  }

  private updateTabContent(): void {
    const tabContent = document.getElementById('tabContent');
    const tableTitle = document.getElementById('tableTitle');
    if (!tabContent) return;

    if (this.activeTab === 'incentives') {
      if (tableTitle) tableTitle.textContent = '📋 My Incentives';
      tabContent.innerHTML = this.renderIncentivesTable();
    } else {
      if (tableTitle) tableTitle.textContent = '📜 Points History';
      tabContent.innerHTML = this.renderPointsTable();
    }
  }

  private attachListeners(): void {
    document.getElementById('tabIncentives')?.addEventListener('click', () => {
      this.activeTab = 'incentives';
      document.getElementById('tabIncentives')?.classList.add('active');
      document.getElementById('tabPoints')?.classList.remove('active');
      this.updateTabContent();
    });

    document.getElementById('tabPoints')?.addEventListener('click', () => {
      this.activeTab = 'points';
      document.getElementById('tabPoints')?.classList.add('active');
      document.getElementById('tabIncentives')?.classList.remove('active');
      if (this.pointsHistory.length === 0) {
        const tabContent = document.getElementById('tabContent');
        if (tabContent) tabContent.innerHTML = '<div class="loading-state">Loading points history...</div>';
        this.loadPointsHistory();
      } else {
        this.updateTabContent();
      }
    });

    document.getElementById('backToDashboard')?.addEventListener('click', () => {
      routerService.navigate('mnr-dashboard');
    });
  }

  private formatIndian(num: number): string {
    return (num || 0).toLocaleString('en-IN');
  }
}
