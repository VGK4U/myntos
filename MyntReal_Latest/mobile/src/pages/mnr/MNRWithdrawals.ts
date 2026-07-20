/**
 * MNR Withdrawals Page - Web Parity
 * DC Protocol: DC_MOBILE_MNR_WITHDRAWALS_003
 * Exact web match: Summary cards, pending breakdown, table with filters
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';
import { MobileTable } from '../../components/MobileTable';

interface DayRow {
  business_date: string;
  gross_amount: number;
  admin_deduction: number;
  tds_deduction: number;
  gurudakshina_deduction: number;
  net_amount: number;
  statuses: Set<string>;
}

interface WithdrawalSummary {
  total_earned: number;
  completed: number;
  pending_validation: number;
  staff_validated: number;
  rejected: number;
}

export class MNRWithdrawals {
  private container: HTMLElement;
  private dayRows: DayRow[] = [];
  private summary: WithdrawalSummary = {
    total_earned: 0, completed: 0, pending_validation: 0,
    staff_validated: 0, rejected: 0
  };
  private loading: boolean = true;
  private startDate: string = '';
  private endDate: string = '';
  private statusFilter: string = '';
  private kycStatus: string = 'Approved';
  private bankStatus: string = 'Approved';
  private showKycWarning: boolean = false;
  private kycWarningMessage: string = '';

  private static readonly STAFF_WORKFLOW_CUTOFF = '2026-02-12';

  private static readonly INCOME_REBRAND_MAP: Record<string, string> = {
    'Direct Referral': 'Direct Business Facilitation',
    'Matching Referral': 'Group Performance Recognition',
    'Ved Income': 'VED Leadership Recognition',
    'Guru Dakshina': 'Mentorship Contribution Benefit'
  };

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await Promise.all([
      this.checkKYCStatus(),
      this.loadTransactions()
    ]);
  }

  private async checkKYCStatus(): Promise<void> {
    try {
      const response = await apiService.get<any>('/auth/me');
      if (response) {
        const data = response.data || response;
        const kyc = data.kyc_status || 'Pending';
        const bank = data.bank_details_status || 'Not Submitted';
        this.kycStatus = kyc;
        this.bankStatus = bank;

        if (kyc !== 'Approved' || bank !== 'Approved') {
          this.showKycWarning = true;
          if (kyc !== 'Approved' && bank !== 'Approved') {
            this.kycWarningMessage = `<strong>KYC Status:</strong> ${kyc} | <strong>Bank Status:</strong> ${bank}<br>You cannot process withdrawals until both KYC and bank details are approved.`;
          } else if (kyc !== 'Approved') {
            this.kycWarningMessage = `<strong>KYC Status:</strong> ${kyc}<br>Complete your KYC verification to enable withdrawals.`;
          } else {
            this.kycWarningMessage = `<strong>Bank Status:</strong> ${bank}<br>Submit your bank details for approval to enable withdrawals.`;
          }
        }
      }
    } catch (error) {
      console.error('[MNRWithdrawals] Error checking KYC status:', error);
    }
    this.updateContent();
  }

  private async loadTransactions(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const params = new URLSearchParams();
      if (this.startDate) params.append('start_date', this.startDate);
      if (this.endDate) params.append('end_date', this.endDate);
      if (this.statusFilter) params.append('verification_status', this.statusFilter);

      const queryStr = params.toString() ? `?${params}` : '';
      const result = await apiService.get<any>(`/withdrawals/income-transactions${queryStr}`);

      if (result && result.success && result.data) {
        const data = result.data;
        const summary = data.summary || {};

        this.summary = {
          total_earned: summary.total_earned || 0,
          completed: summary.completed || 0,
          pending_validation: summary.pending_validation || 0,
          staff_validated: summary.staff_validated || 0,
          rejected: summary.rejected || 0
        };

        const segments = data.segments || [];
        const dayMap: Record<string, DayRow> = {};

        segments.forEach((seg: any) => {
          const txns = seg.transactions || [];
          txns.forEach((t: any) => {
            const dateKey = t.business_date || 'unknown';
            if (!dayMap[dateKey]) {
              dayMap[dateKey] = {
                business_date: dateKey,
                gross_amount: 0,
                admin_deduction: 0,
                tds_deduction: 0,
                gurudakshina_deduction: 0,
                net_amount: 0,
                statuses: new Set<string>()
              };
            }
            dayMap[dateKey].gross_amount += (t.gross_amount || 0);
            dayMap[dateKey].admin_deduction += (t.admin_deduction || 0);
            dayMap[dateKey].tds_deduction += (t.tds_deduction || 0);
            dayMap[dateKey].gurudakshina_deduction += (t.gurudakshina_deduction || 0);
            dayMap[dateKey].net_amount += (t.net_amount || 0);
            if (t.verification_status) dayMap[dateKey].statuses.add(t.verification_status);
          });
        });

        this.dayRows = Object.values(dayMap).sort((a, b) => b.business_date.localeCompare(a.business_date));
      }
    } catch (error) {
      console.error('[MNRWithdrawals] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        ${MobileTable.getStyles()}
        .withdrawals-page { padding: 16px; }
        
        .page-banner {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: 12px;
          padding: 20px;
          margin-bottom: 16px;
          color: white;
        }
        .page-banner h2 { margin: 0 0 4px; font-size: 18px; }
        .page-banner p { margin: 0; font-size: 12px; opacity: 0.9; }
        
        .kyc-warning {
          background: rgba(251, 191, 36, 0.15);
          border: 1px solid rgba(251, 191, 36, 0.4);
          border-radius: 10px;
          padding: 14px;
          margin-bottom: 16px;
        }
        .kyc-warning h5 { color: #fbbf24; margin: 0 0 8px; font-size: 14px; }
        .kyc-warning .kyc-msg { color: #fcd34d; margin: 0 0 10px; font-size: 12px; line-height: 1.5; }
        .kyc-warning .btn-kyc {
          background: #fbbf24;
          color: #451a03;
          border: none;
          padding: 8px 14px;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          margin-right: 8px;
        }
        .kyc-warning .btn-bank {
          background: transparent;
          color: #fbbf24;
          border: 1px solid #fbbf24;
          padding: 8px 14px;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
        }
        
        .summary-row {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 8px;
          margin-bottom: 12px;
        }
        .summary-card {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 10px;
          padding: 14px 8px;
          text-align: center;
        }
        .summary-card.green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
        .summary-card.purple { background: linear-gradient(135deg, #8e2de2 0%, #4a00e0 100%); }
        .summary-card.pink { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .summary-card .label { font-size: 9px; color: rgba(255,255,255,0.8); text-transform: uppercase; margin-bottom: 4px; }
        .summary-card .value { font-size: 18px; font-weight: 700; color: white; }
        .summary-card .sub { font-size: 9px; color: rgba(255,255,255,0.7); margin-top: 2px; }
        
        .pending-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 8px;
          margin-bottom: 16px;
        }
        .pending-card {
          border-radius: 10px;
          padding: 12px;
          text-align: center;
        }
        .pending-card.admin { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: #451a03; }
        .pending-card.super { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .pending-card.finance { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; }
        .pending-card.rejected { background: linear-gradient(135deg, #fc5c7d 0%, #6a82fb 100%); color: white; }
        .pending-card .label { font-size: 10px; opacity: 0.9; margin-bottom: 4px; }
        .pending-card .value { font-size: 16px; font-weight: 700; }
        .pending-card .sub { font-size: 9px; opacity: 0.8; margin-top: 2px; }
        
        .lifecycle-section {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 10px;
          padding: 14px;
          margin-bottom: 16px;
        }
        .lifecycle-section h5 { color: #e6f1ff; margin: 0 0 12px; font-size: 13px; }
        .lifecycle-steps {
          display: flex;
          justify-content: space-between;
          position: relative;
        }
        .lifecycle-steps::before {
          content: '';
          position: absolute;
          top: 18px;
          left: 20px;
          right: 20px;
          height: 2px;
          background: rgba(255,255,255,0.2);
        }
        .lifecycle-step {
          text-align: center;
          position: relative;
          z-index: 1;
        }
        .lifecycle-step .icon {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 6px;
          font-size: 14px;
        }
        .lifecycle-step.green .icon { background: linear-gradient(135deg, #10b981, #059669); }
        .lifecycle-step.yellow .icon { background: linear-gradient(135deg, #fbbf24, #f59e0b); }
        .lifecycle-step.purple .icon { background: linear-gradient(135deg, #8b5cf6, #7c3aed); }
        .lifecycle-step.blue .icon { background: linear-gradient(135deg, #3b82f6, #2563eb); }
        .lifecycle-step .label { font-size: 9px; color: #8892b0; }
        
        .filters-section {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 10px;
          padding: 14px;
          margin-bottom: 16px;
        }
        .filters-section h5 { color: #e6f1ff; margin: 0 0 12px; font-size: 13px; }
        .filter-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
          margin-bottom: 10px;
        }
        .filter-group label {
          display: block;
          font-size: 10px;
          color: #8892b0;
          text-transform: uppercase;
          margin-bottom: 4px;
        }
        .filter-group input, .filter-group select {
          width: 100%;
          padding: 10px;
          border-radius: 6px;
          border: 1px solid rgba(255,255,255,0.1);
          background: rgba(13, 27, 42, 0.8);
          color: #e6f1ff;
          font-size: 13px;
        }
        .btn-apply {
          width: 48%;
          padding: 12px;
          border-radius: 6px;
          border: none;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
        }
        .btn-clear {
          width: 48%;
          padding: 12px;
          border-radius: 6px;
          border: none;
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          color: white;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
        }
        .filter-buttons {
          display: flex;
          gap: 8px;
          justify-content: space-between;
        }
        
        .section-header {
          background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
          padding: 12px 14px;
          border-radius: 8px 8px 0 0;
        }
        .section-header h5 { margin: 0; color: white; font-size: 13px; }

        .day-table {
          width: 100%;
          border-collapse: collapse;
          margin-bottom: 16px;
          background: rgba(22, 33, 62, 0.8);
          border-radius: 0 0 8px 8px;
          overflow: hidden;
        }
        .day-table thead th {
          padding: 8px 6px;
          font-size: 9px;
          color: #8892b0;
          text-transform: uppercase;
          border-bottom: 1px solid rgba(255,255,255,0.1);
          text-align: right;
        }
        .day-table thead th:first-child { text-align: left; }
        .day-table thead th:last-child { text-align: center; }
        .day-table tbody td {
          padding: 10px 6px;
          font-size: 12px;
          color: #e6f1ff;
          border-bottom: 1px solid rgba(255,255,255,0.05);
          text-align: right;
        }
        .day-table tbody td:first-child { text-align: left; font-weight: 600; }
        .day-table tbody td:last-child { text-align: center; }
        .day-table tfoot td {
          padding: 10px 6px;
          font-size: 12px;
          font-weight: 700;
          color: #e6f1ff;
          border-top: 2px solid rgba(102, 126, 234, 0.3);
          background: rgba(102, 126, 234, 0.08);
          text-align: right;
        }
        .day-table tfoot td:first-child { text-align: left; }
        .day-table tfoot td:last-child { text-align: center; }
        .text-danger { color: #ef4444 !important; }
        .text-warning-deduction { color: #f59e0b !important; }
        .text-success { color: #10b981 !important; }

        .day-summary-bar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 14px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: 8px 8px 0 0;
          color: white;
          font-size: 11px;
        }
        .day-summary-bar .badge-light {
          background: rgba(255,255,255,0.2);
          padding: 3px 8px;
          border-radius: 4px;
          font-size: 10px;
          margin-left: 6px;
        }
      </style>
      ${PageHeader.render({ title: '💸 Earnings & Payments', showBack: true })}
      <div class="withdrawals-page" id="pageContent">
        <div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">Loading...</div>
      </div>
    `;

    PageHeader.attachListeners({ title: '💸 Earnings & Payments', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">Loading withdrawals...</div>';
      return;
    }

    const totalGross = this.dayRows.reduce((s, r) => s + r.gross_amount, 0);
    const totalAdmin = this.dayRows.reduce((s, r) => s + r.admin_deduction, 0);
    const totalTds = this.dayRows.reduce((s, r) => s + r.tds_deduction, 0);
    const totalGuru = this.dayRows.reduce((s, r) => s + r.gurudakshina_deduction, 0);
    const totalNet = this.dayRows.reduce((s, r) => s + r.net_amount, 0);

    let rowsHtml = '';
    this.dayRows.forEach(r => {
      const statusArr = Array.from(r.statuses);
      const isPreCutoff = r.business_date < MNRWithdrawals.STAFF_WORKFLOW_CUTOFF;
      const displayStatuses = statusArr.map(s => {
        if (isPreCutoff && s === 'Completed') return 'Cleared';
        return s;
      });
      const statusBadge = displayStatuses.map(s => this.getStatusBadge(s)).join(' ');

      rowsHtml += `<tr>
        <td>${this.formatDate(r.business_date)}</td>
        <td>₹${r.gross_amount.toLocaleString('en-IN')}</td>
        <td class="text-danger">-₹${r.admin_deduction.toLocaleString('en-IN')}</td>
        <td class="text-danger">-₹${r.tds_deduction.toLocaleString('en-IN')}</td>
        <td class="text-warning-deduction">-₹${r.gurudakshina_deduction.toLocaleString('en-IN')}</td>
        <td class="text-success" style="font-weight:600;">₹${r.net_amount.toLocaleString('en-IN')}</td>
        <td>${statusBadge}</td>
      </tr>`;
    });

    content.innerHTML = `
      <div class="page-banner">
        <h2>💰 Earnings & Payment Tracking</h2>
        <p>Track your earnings journey from income generation to bank payment</p>
      </div>

      ${this.showKycWarning ? `
        <div class="kyc-warning">
          <h5>⚠️ KYC Verification Required</h5>
          <div class="kyc-msg">${this.kycWarningMessage}</div>
          <button class="btn-kyc">Complete KYC Now</button>
          <button class="btn-bank">Update Bank Details</button>
        </div>
      ` : ''}

      <div class="summary-row">
        <div class="summary-card green">
          <div class="label">💰 Total Income Generated</div>
          <div class="value">₹${this.summary.total_earned.toLocaleString('en-IN')}</div>
          <div class="sub">NET (After Deductions)</div>
        </div>
        <div class="summary-card pink">
          <div class="label">🏦 Paid to Bank</div>
          <div class="value">₹${this.summary.completed.toLocaleString('en-IN')}</div>
          <div class="sub">Payment Completed</div>
        </div>
      </div>

      <div class="pending-grid">
        <div class="pending-card admin">
          <div class="label">⏰ Pending Validation</div>
          <div class="value">₹${this.summary.pending_validation.toLocaleString('en-IN')}</div>
          <div class="sub">Awaiting Staff Review</div>
        </div>
        <div class="pending-card finance">
          <div class="label">✅ Staff Validated</div>
          <div class="value">₹${this.summary.staff_validated.toLocaleString('en-IN')}</div>
          <div class="sub">Awaiting Payment</div>
        </div>
        <div class="pending-card rejected">
          <div class="label">❌ Rejected</div>
          <div class="value">₹${this.summary.rejected.toLocaleString('en-IN')}</div>
          <div class="sub">Not Approved</div>
        </div>
      </div>

      <div class="lifecycle-section">
        <h5>📋 Payment Lifecycle Journey</h5>
        <p style="color: #8892b0; font-size: 11px; margin: 0 0 12px;">Your income is calculated daily, then goes through validation before payment</p>
        <div class="lifecycle-steps">
          <div class="lifecycle-step green">
            <div class="icon">💰</div>
            <div class="label">Income<br>Generated</div>
          </div>
          <div class="lifecycle-step yellow">
            <div class="icon">⏳</div>
            <div class="label">Pending<br>Validation</div>
          </div>
          <div class="lifecycle-step purple">
            <div class="icon">✅</div>
            <div class="label">Staff<br>Validated</div>
          </div>
          <div class="lifecycle-step blue">
            <div class="icon">🏦</div>
            <div class="label">Completed<br>(Paid)</div>
          </div>
        </div>
        <p style="color: #64748b; font-size: 10px; margin: 12px 0 0; background: rgba(59,130,246,0.1); padding: 8px; border-radius: 6px;">
          ℹ️ <strong>Pending Validation</strong> → <strong>Staff Validated</strong> → <strong>Completed</strong>. 
          Records before 12 Feb 2026 are shown as <strong>Cleared</strong> (auto-approved).
        </p>
      </div>

      <div class="filters-section">
        <h5>🔍 Filter Transactions</h5>
        <div class="filter-row">
          <div class="filter-group">
            <label>📅 Start Date</label>
            <input type="date" id="filterStartDate" value="${this.startDate}" />
          </div>
          <div class="filter-group">
            <label>📅 End Date</label>
            <input type="date" id="filterEndDate" value="${this.endDate}" />
          </div>
        </div>
        <div class="filter-row" style="grid-template-columns: 1fr;">
          <div class="filter-group">
            <label>🏷️ Payment Status</label>
            <select id="filterStatus">
              <option value="">All Status</option>
              <option value="Pending" ${this.statusFilter === 'Pending' ? 'selected' : ''}>⏳ Pending Validation</option>
              <option value="Staff Validated" ${this.statusFilter === 'Staff Validated' ? 'selected' : ''}>✅ Staff Validated</option>
              <option value="Completed" ${this.statusFilter === 'Completed' ? 'selected' : ''}>💰 Completed (Paid)</option>
              <option value="Rejected" ${this.statusFilter === 'Rejected' ? 'selected' : ''}>❌ Rejected</option>
            </select>
          </div>
        </div>
        <div class="filter-buttons">
          <button class="btn-apply" id="btnApplyFilters">🔍 Apply</button>
          <button class="btn-clear" id="btnClearFilters">🔄 Show All</button>
        </div>
      </div>

      ${this.dayRows.length > 0 ? `
        <div class="day-summary-bar">
          <span>📋 Day-Wise Cumulative Income</span>
          <span>
            <span class="badge-light">Gross: ₹${totalGross.toLocaleString('en-IN')}</span>
            <span class="badge-light">NET: ₹${totalNet.toLocaleString('en-IN')}</span>
          </span>
        </div>
        <table class="day-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Gross</th>
              <th>Adm 8%</th>
              <th>TDS 2%</th>
              <th>Ctb 2%</th>
              <th>NET</th>
              <th>Sts</th>
            </tr>
          </thead>
          <tbody>${rowsHtml}</tbody>
          <tfoot>
            <tr>
              <td>TOTAL (${this.dayRows.length} days)</td>
              <td>₹${totalGross.toLocaleString('en-IN')}</td>
              <td class="text-danger">-₹${totalAdmin.toLocaleString('en-IN')}</td>
              <td class="text-danger">-₹${totalTds.toLocaleString('en-IN')}</td>
              <td class="text-warning-deduction">-₹${totalGuru.toLocaleString('en-IN')}</td>
              <td class="text-success">₹${totalNet.toLocaleString('en-IN')}</td>
              <td>-</td>
            </tr>
          </tfoot>
        </table>
      ` : `
        <div style="text-align: center; padding: 40px; color: #8892b0;">
          <div style="font-size: 40px; margin-bottom: 12px;">📭</div>
          <h4 style="color: #e6f1ff; margin: 0 0 8px;">No Income Records Found</h4>
          <p style="margin: 0; font-size: 12px;">No income has been generated yet. Income is calculated daily at midnight.</p>
        </div>
      `}
    `;

    this.attachListeners();
  }

  private attachListeners(): void {
    document.getElementById('btnApplyFilters')?.addEventListener('click', () => {
      this.startDate = (document.getElementById('filterStartDate') as HTMLInputElement)?.value || '';
      this.endDate = (document.getElementById('filterEndDate') as HTMLInputElement)?.value || '';
      this.statusFilter = (document.getElementById('filterStatus') as HTMLSelectElement)?.value || '';
      this.loadTransactions();
    });

    document.getElementById('btnClearFilters')?.addEventListener('click', () => {
      this.startDate = '';
      this.endDate = '';
      this.statusFilter = '';
      this.loadTransactions();
    });
  }

  private getStatusBadge(status: string): string {
    const s = status.toLowerCase();
    if (s === 'paid' || s === 'completed') return '<span class="badge badge-success">Completed</span>';
    if (s === 'cleared') return '<span class="badge badge-info">Cleared</span>';
    if (s === 'staff validated' || s === 'staff_validated') return '<span class="badge badge-info">Staff Validated</span>';
    if (s.includes('pending') || s === 'pending') return '<span class="badge badge-warning">Pending Validation</span>';
    if (s === 'rejected') return '<span class="badge badge-danger">Rejected</span>';
    return `<span class="badge badge-secondary">${status}</span>`;
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return '-';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
      return dateStr;
    }
  }
}
