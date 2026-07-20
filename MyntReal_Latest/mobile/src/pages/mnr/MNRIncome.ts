/**
 * MNR Income Page - Web Table Parity
 * DC Protocol: DC_MOBILE_MNR_INCOME_002
 * Exact web table: Type, From User, Amount, Date, Status
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';
import { MobileTable } from '../../components/MobileTable';

interface IncomeRecord {
  id: number;
  type: string;
  amount: number;
  from_user: string;
  date: string;
  status: string;
}

interface IncomeSummary {
  direct_referral: number;
  matching_referral: number;
  ved_income: number;
  guru_dakshina: number;
  total: number;
}

export class MNRIncome {
  private container: HTMLElement;
  private records: IncomeRecord[] = [];
  private summary: IncomeSummary | null = null;
  private loading: boolean = true;
  private activeTab: string = 'all';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadIncome();
  }

  private async loadIncome(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const summaryRes = await apiService.get<any>('/users/earnings-summary');
      if (summaryRes.success && summaryRes.data) {
        const d = summaryRes.data;
        this.summary = {
          direct_referral: d.direct_referral_total || d.direct_referral || 0,
          matching_referral: d.matching_referral_total || d.matching_referral || 0,
          ved_income: d.ved_income_total || d.ved_income || 0,
          guru_dakshina: d.guru_dakshina_total || d.guru_dakshina || 0,
          total: d.total_gross_earnings || d.total || 
            (d.direct_referral_total || 0) + (d.matching_referral_total || 0) + 
            (d.ved_income_total || 0) + (d.guru_dakshina_total || 0)
        };
      }
      
      const endpoints: Record<string, string> = {
        'direct': '/financial-operations/income/me/direct-referral-transactions',
        'matching': '/financial-operations/income/me/matching-referral-transactions',
        'ved': '/financial-operations/income/me/ved-income-transactions',
        'guru': '/financial-operations/income/me/guru-dakshina-transactions'
      };

      if (this.activeTab === 'all') {
        const [directRes, matchingRes, vedRes, guruRes] = await Promise.all([
          apiService.get<any>(endpoints['direct']),
          apiService.get<any>(endpoints['matching']),
          apiService.get<any>(endpoints['ved']),
          apiService.get<any>(endpoints['guru'])
        ]);
        
        const allRecords: IncomeRecord[] = [];
        if (directRes.success && directRes.data) {
          const records = directRes.data.transactions || directRes.data.records || [];
          records.forEach((r: any) => allRecords.push(this.normalizeRecord(r, 'Direct Business Facilitation')));
        }
        if (matchingRes.success && matchingRes.data) {
          const records = matchingRes.data.transactions || matchingRes.data.records || [];
          records.forEach((r: any) => allRecords.push(this.normalizeRecord(r, 'Group Performance Recognition')));
        }
        if (vedRes.success && vedRes.data) {
          const records = vedRes.data.transactions || vedRes.data.records || [];
          records.forEach((r: any) => allRecords.push(this.normalizeRecord(r, 'VED Leadership Recognition')));
        }
        if (guruRes.success && guruRes.data) {
          const records = guruRes.data.transactions || guruRes.data.records || [];
          records.forEach((r: any) => allRecords.push(this.normalizeRecord(r, 'Mentorship Contribution Benefit')));
        }
        
        this.records = allRecords.sort((a, b) => 
          new Date(b.date).getTime() - new Date(a.date).getTime()
        );
      } else {
        const endpoint = endpoints[this.activeTab];
        if (endpoint) {
          const res = await apiService.get<any>(endpoint);
          if (res.success && res.data) {
            const records = res.data.transactions || res.data.records || [];
            this.records = records.map((r: any) => this.normalizeRecord(r, this.getTypeLabel(this.activeTab)));
          }
        }
      }
    } catch (error) {
      console.error('[MNRIncome] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        ${MobileTable.getStyles()}
        .mnr-income-page { padding: 16px; }
        .income-summary {
          display: grid;
          grid-template-columns: 1fr;
          gap: 12px;
          margin-bottom: 16px;
        }
        .total-card {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          border-radius: 12px;
          padding: 20px;
          text-align: center;
          color: white;
        }
        .total-card .label { font-size: 12px; opacity: 0.9; margin-bottom: 4px; }
        .total-card .value { font-size: 32px; font-weight: 700; }
        .income-breakdown {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 8px;
        }
        .income-type-card {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 8px;
          padding: 12px;
          text-align: center;
        }
        .income-type-card .label { font-size: 11px; color: #8892b0; text-transform: uppercase; }
        .income-type-card .value { font-size: 16px; font-weight: 600; color: #e6f1ff; }
        .tab-bar {
          display: flex;
          gap: 8px;
          margin-bottom: 16px;
          overflow-x: auto;
          padding-bottom: 8px;
        }
        .tab-btn {
          padding: 8px 16px;
          background: rgba(22, 33, 62, 0.8);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 20px;
          color: #8892b0;
          font-size: 13px;
          white-space: nowrap;
          cursor: pointer;
        }
        .tab-btn.active {
          background: #64d2ff;
          border-color: #64d2ff;
          color: #0d1b2a;
          font-weight: 600;
        }
        .section-title {
          font-size: 16px;
          font-weight: 600;
          color: #e6f1ff;
          margin: 20px 0 12px;
        }
      </style>
      ${PageHeader.render({ title: 'Income', showBack: true })}
      <div class="mnr-income-page">
        <div id="summarySection"></div>
        
        <h3 class="section-title">Transactions</h3>
        <div class="tab-bar" id="tabBar">
          <button class="tab-btn ${this.activeTab === 'all' ? 'active' : ''}" data-tab="all">All</button>
          <button class="tab-btn ${this.activeTab === 'direct' ? 'active' : ''}" data-tab="direct">Direct</button>
          <button class="tab-btn ${this.activeTab === 'matching' ? 'active' : ''}" data-tab="matching">Matching</button>
          <button class="tab-btn ${this.activeTab === 'ved' ? 'active' : ''}" data-tab="ved">Ved</button>
          <button class="tab-btn ${this.activeTab === 'guru' ? 'active' : ''}" data-tab="guru">Guru</button>
        </div>
        
        <div id="pageContent"></div>
      </div>
    `;
    this.attachListeners();
  }

  private attachListeners(): void {
    PageHeader.attachListeners({ title: 'Income', showBack: true });
    
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.activeTab = btn.getAttribute('data-tab') || 'all';
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.loadIncome();
      });
    });
  }

  private updateContent(): void {
    const summarySection = document.getElementById('summarySection');
    if (summarySection && this.summary) {
      summarySection.innerHTML = `
        <div class="income-summary">
          <div class="total-card">
            <div class="label">Total Earnings</div>
            <div class="value">₹${this.summary.total.toLocaleString()}</div>
          </div>
          <div class="income-breakdown">
            <div class="income-type-card">
              <div class="label">Direct Business Facilitation</div>
              <div class="value">₹${this.summary.direct_referral.toLocaleString()}</div>
            </div>
            <div class="income-type-card">
              <div class="label">Group Performance Recognition</div>
              <div class="value">₹${this.summary.matching_referral.toLocaleString()}</div>
            </div>
            <div class="income-type-card">
              <div class="label">VED Leadership Recognition</div>
              <div class="value">₹${this.summary.ved_income.toLocaleString()}</div>
            </div>
            <div class="income-type-card">
              <div class="label">Mentorship Contribution Benefit</div>
              <div class="value">₹${this.summary.guru_dakshina.toLocaleString()}</div>
            </div>
          </div>
        </div>
      `;
    }

    const content = document.getElementById('pageContent');
    if (!content) return;

    const table = new MobileTable({
      columns: [
        { key: 'type', label: 'Type', render: (v) => this.getTypeBadge(v) },
        { key: 'from_user', label: 'From User' },
        { key: 'amount', label: 'Amount', render: (v) => `<span style="color: #10b981; font-weight: 600;">+₹${v.toLocaleString()}</span>` },
        { key: 'date', label: 'Date', render: (v) => this.formatDate(v) },
        { key: 'status', label: 'Status', render: (v) => this.getStatusBadge(v) }
      ],
      data: this.records,
      loading: this.loading,
      emptyMessage: 'No income transactions yet'
    });

    content.innerHTML = `
      <div class="table-summary-bar">
        <span>Total <span class="count">${this.records.length}</span> transactions</span>
      </div>
      ${table.render()}
    `;
  }

  private getTypeBadge(type: string): string {
    const colors: Record<string, string> = {
      'Direct Business Facilitation': 'badge-info',
      'Group Performance Recognition': 'badge-primary',
      'VED Leadership Recognition': 'badge-warning',
      'Mentorship Contribution Benefit': 'badge-platinum'
    };
    return `<span class="badge ${colors[type] || 'badge-secondary'}">${type}</span>`;
  }

  private getStatusBadge(status: string): string {
    const s = status.toLowerCase();
    if (s === 'completed' || s === 'approved') return '<span class="badge badge-success">Completed</span>';
    if (s === 'staff validated' || s === 'staff_validated') return '<span class="badge badge-info">Staff Validated</span>';
    if (s === 'cleared') return '<span class="badge badge-info">Cleared</span>';
    if (s === 'pending') return '<span class="badge badge-warning">Pending Validation</span>';
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

  private normalizeRecord(r: any, type: string): IncomeRecord {
    return {
      id: r.id || 0,
      type: type,
      amount: r.total_amount || r.net_amount || r.amount || 0,
      from_user: r.referred_user_name || r.for_member_name || r.from_member || r.name || 'System',
      date: r.from_date || r.date || r.created_at || '',
      status: r.verification_status || r.status || 'Completed'
    };
  }

  private getTypeLabel(tab: string): string {
    const labels: Record<string, string> = {
      'direct': 'Direct Business Facilitation',
      'matching': 'Group Performance Recognition',
      'ved': 'VED Leadership Recognition',
      'guru': 'Mentorship Contribution Benefit'
    };
    return labels[tab] || tab;
  }
}
