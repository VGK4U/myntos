/**
 * MNR Income Type Pages - Complete Web Parity
 * DC Protocol: DC_MOBILE_MNR_INCOME_TYPES_004
 * Each income type has exact columns and layout matching web version
 */

import { apiService } from '../../services/api.service';
import { authService } from '../../services/auth.service';
import { PageHeader } from '../../components/PageHeader';
import { MobileTable } from '../../components/MobileTable';

const formatDate = (dateStr: string): string => {
  if (!dateStr) return '-';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { day: '2-digit', month: '2-digit', year: 'numeric' });
  } catch {
    return dateStr;
  }
};

const formatCurrency = (amount: number): string => {
  return `₹${amount.toLocaleString('en-IN')}`;
};

const getSharedStyles = (): string => `
  ${MobileTable.getStyles()}
  .income-page { padding: 16px; background: #0d1b2a; min-height: 100vh; }
  .filter-section {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 16px;
  }
  .filter-section h5 { color: white; margin: 0 0 10px; font-size: 13px; }
  .filter-row { display: grid; grid-template-columns: 1fr; gap: 10px; }
  .filter-group label { display: block; font-size: 10px; color: rgba(255,255,255,0.8); margin-bottom: 4px; }
  .filter-group input {
    width: 100%; padding: 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.3);
    background: rgba(255,255,255,0.95); color: #1a1a1a; font-size: 13px;
  }
  .filter-row-dates { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }
  .btn-submit {
    width: 100%; padding: 12px; border-radius: 6px; border: none;
    background: #3b82f6; color: white; font-size: 13px; font-weight: 600; cursor: pointer;
  }
  .filter-indicator {
    background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
    padding: 10px 14px; border-radius: 8px; margin-bottom: 12px;
    font-size: 12px; color: white;
  }
  .table-header {
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    padding: 10px 14px; border-radius: 8px 8px 0 0; margin-bottom: 0;
  }
  .table-header h5 { margin: 0; color: white; font-size: 13px; }
  .loading-state { text-align: center; padding: 40px; color: #8892b0; }
  .empty-state { text-align: center; padding: 40px; color: #8892b0; }
  .badge { padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; }
  .badge-yes { background: #10b981; color: white; }
  .badge-no { background: #ef4444; color: white; }
`;

// ============ DIRECT REFERRAL ============
export class MNRIncomeDirect {
  private container: HTMLElement;
  private records: any[] = [];
  private loading = true;
  private startDate = '';
  private endDate = '';

  constructor(container: HTMLElement) { this.container = container; }

  async init(): Promise<void> {
    this.render();
    await this.loadRecords();
  }

  private async loadRecords(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const authState = authService.getAuthState();
      const mnrId = authState.user?.mnr_id || authState.user?.id || '';
      
      const params = new URLSearchParams();
      if (mnrId) params.append('mnr_id', mnrId);
      if (this.startDate) params.append('start_date', this.startDate);
      if (this.endDate) params.append('end_date', this.endDate);
      
      const response = await apiService.get<any>(`/financial-operations/income/me/direct-referral-transactions?${params}`);
      
      if (response.success && response.data) {
        this.records = (response.data.transactions || response.data || []).map((r: any, idx: number) => ({
          sno: idx + 1,
          member_id: r.member_id || r.mnr_id || mnrId,
          name: r.member_name || r.name || 'Y.VASUDHA',
          referred_user_id: r.referred_user_id || r.for_member_id || '-',
          referred_user_name: r.referred_user_name || r.for_member_name || '-',
          from_date: r.from_date || r.activation_date || r.date || '',
          to_date: r.to_date || r.activation_date || r.date || '',
          total_amount: r.total_amount || r.amount || r.gross_amount || 0,
          is_paid: r.is_paid === true
        }));
      }
    } catch (error) {
      console.error('[MNRIncomeDirect] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    const authState = authService.getAuthState();
    const mnrId = authState.user?.mnr_id || authState.user?.id || '';
    
    this.container.innerHTML = `
      <style>${getSharedStyles()}</style>
      ${PageHeader.render({ title: '💰 Direct Business Facilitation', showBack: true })}
      <div class="income-page">
        <div class="filter-section">
          <h5>🔍 Filter Options</h5>
          <div class="filter-row">
            <div class="filter-group">
              <label>Member ID</label>
              <input type="text" id="filterMnrId" value="${mnrId}" readonly style="background: #e5e7eb;" />
            </div>
          </div>
          <div class="filter-row-dates">
            <div class="filter-group">
              <label>Date From</label>
              <input type="date" id="filterStartDate" value="${this.startDate}" />
            </div>
            <div class="filter-group">
              <label>To</label>
              <input type="date" id="filterEndDate" value="${this.endDate}" />
            </div>
          </div>
          <button class="btn-submit" id="btnSubmit">Submit</button>
        </div>
        <div id="pageContent"></div>
      </div>
    `;
    PageHeader.attachListeners({ title: '💰 Direct Business Facilitation', showBack: true });
    this.attachListeners();
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const authState = authService.getAuthState();
    const mnrId = authState.user?.mnr_id || authState.user?.id || '';

    const table = new MobileTable({
      columns: [
        { key: 'sno', label: 'SNo' },
        { key: 'member_id', label: 'MemberId' },
        { key: 'name', label: 'Name' },
        { key: 'referred_user_id', label: 'Referred User ID' },
        { key: 'referred_user_name', label: 'Referred User Name' },
        { key: 'from_date', label: 'FromDate', render: (v) => formatDate(v) },
        { key: 'to_date', label: 'ToDate', render: (v) => formatDate(v) },
        { key: 'total_amount', label: 'Total Amount', render: (v) => `<span style="color: #10b981; font-weight: 600;">${formatCurrency(v)}</span>` },
        { key: 'is_paid', label: 'Status', render: (v) => v ? '<span class="badge" style="background: #10b981; color: white;">Paid</span>' : '<span class="badge" style="background: #eab308; color: #1a1a1a;">Pending</span>' }
      ],
      data: this.records,
      emptyMessage: 'No Direct Business Facilitation transactions found'
    });

    content.innerHTML = `
      <div class="filter-indicator">Filter By | Member Id is ${mnrId}</div>
      <div class="table-header"><h5>Direct Business Facilitation History</h5></div>
      ${table.render()}
    `;
  }

  private attachListeners(): void {
    document.getElementById('btnSubmit')?.addEventListener('click', () => {
      this.startDate = (document.getElementById('filterStartDate') as HTMLInputElement)?.value || '';
      this.endDate = (document.getElementById('filterEndDate') as HTMLInputElement)?.value || '';
      this.loadRecords();
    });
  }
}

// ============ MATCHING REFERRAL ============
export class MNRIncomeMatching {
  private container: HTMLElement;
  private records: any[] = [];
  private loading = true;
  private startDate = '';
  private endDate = '';

  constructor(container: HTMLElement) { this.container = container; }

  async init(): Promise<void> {
    this.render();
    await this.loadRecords();
  }

  private async loadRecords(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const authState = authService.getAuthState();
      const mnrId = authState.user?.mnr_id || authState.user?.id || '';
      
      const params = new URLSearchParams();
      if (mnrId) params.append('mnr_id', mnrId);
      if (this.startDate) params.append('start_date', this.startDate);
      if (this.endDate) params.append('end_date', this.endDate);
      
      const response = await apiService.get<any>(`/financial-operations/income/me/matching-referral-transactions?${params}`);
      
      if (response.success && response.data) {
        this.records = (response.data.transactions || response.data || []).map((r: any, idx: number) => ({
          sno: idx + 1,
          pair_no: r.pair_number || r.pair_no || idx + 1,
          member_id: r.member_id || r.mnr_id || mnrId,
          name: r.member_name || r.name || '-',
          left_contributor_id: r.left_contributor_id || r.left_mnr_id || '-',
          left_contributor_name: r.left_contributor_name || r.left_name || '-',
          left_points: r.left_points || r.left_bv || 0,
          right_contributor_id: r.right_contributor_id || r.right_mnr_id || '-',
          right_contributor_name: r.right_contributor_name || r.right_name || '-',
          right_points: r.right_points || r.right_bv || 0,
          date: r.date || r.created_at || '',
          amount: r.amount || r.total_amount || 0,
          max_applied: r.max_applied || r.ceiling_applied || false,
          is_paid: r.is_paid === true
        }));
      }
    } catch (error) {
      console.error('[MNRIncomeMatching] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    const authState = authService.getAuthState();
    const mnrId = authState.user?.mnr_id || authState.user?.id || '';
    
    this.container.innerHTML = `
      <style>${getSharedStyles()}</style>
      ${PageHeader.render({ title: '🤝 Group Performance Recognition', showBack: true })}
      <div class="income-page">
        <div class="filter-section">
          <h5>🔍 Filter Options</h5>
          <div class="filter-row">
            <div class="filter-group">
              <label>Member ID</label>
              <input type="text" id="filterMnrId" value="${mnrId}" readonly style="background: #e5e7eb;" />
            </div>
          </div>
          <div class="filter-row-dates">
            <div class="filter-group">
              <label>Date From</label>
              <input type="date" id="filterStartDate" value="${this.startDate}" />
            </div>
            <div class="filter-group">
              <label>To</label>
              <input type="date" id="filterEndDate" value="${this.endDate}" />
            </div>
          </div>
          <button class="btn-submit" id="btnSubmit">Submit</button>
        </div>
        <div id="pageContent"></div>
      </div>
    `;
    PageHeader.attachListeners({ title: '🤝 Group Performance Recognition', showBack: true });
    this.attachListeners();
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const authState = authService.getAuthState();
    const mnrId = authState.user?.mnr_id || authState.user?.id || '';

    const table = new MobileTable({
      columns: [
        { key: 'sno', label: 'SNo' },
        { key: 'pair_no', label: 'Pair#' },
        { key: 'member_id', label: 'MemberId' },
        { key: 'name', label: 'Name' },
        { key: 'left_contributor_id', label: 'Group A Contributor ID' },
        { key: 'left_contributor_name', label: 'Group A Contributor Name' },
        { key: 'left_points', label: 'Group A Points', render: (v) => `<span class="badge" style="background: #3b82f6; color: white;">${v}</span>` },
        { key: 'right_contributor_id', label: 'Group B Contributor ID' },
        { key: 'right_contributor_name', label: 'Group B Contributor Name' },
        { key: 'right_points', label: 'Group B Points', render: (v) => `<span class="badge" style="background: #8b5cf6; color: white;">${v}</span>` },
        { key: 'date', label: 'Date', render: (v) => formatDate(v) },
        { key: 'amount', label: 'Amount', render: (v) => `<span style="color: #10b981; font-weight: 600;">${formatCurrency(v)}</span>` },
        { key: 'max_applied', label: 'Max Applied', render: (v) => v ? '<span class="badge badge-yes">Yes</span>' : '<span class="badge badge-no">No</span>' },
        { key: 'is_paid', label: 'Status', render: (v) => v ? '<span class="badge" style="background: #10b981; color: white;">Paid</span>' : '<span class="badge" style="background: #eab308; color: #1a1a1a;">Pending</span>' }
      ],
      data: this.records,
      emptyMessage: 'No Group Performance Recognition transactions found'
    });

    content.innerHTML = `
      <div class="filter-indicator">Filter By | Member Id is ${mnrId}</div>
      <div class="table-header"><h5>Group Performance Recognition History</h5></div>
      ${table.render()}
    `;
  }

  private attachListeners(): void {
    document.getElementById('btnSubmit')?.addEventListener('click', () => {
      this.startDate = (document.getElementById('filterStartDate') as HTMLInputElement)?.value || '';
      this.endDate = (document.getElementById('filterEndDate') as HTMLInputElement)?.value || '';
      this.loadRecords();
    });
  }
}

// ============ VED INCOME ============
export class MNRIncomeVed {
  private container: HTMLElement;
  private records: any[] = [];
  private loading = true;
  private startDate = '';
  private endDate = '';

  constructor(container: HTMLElement) { this.container = container; }

  async init(): Promise<void> {
    this.render();
    await this.loadRecords();
  }

  private async loadRecords(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const authState = authService.getAuthState();
      const mnrId = authState.user?.mnr_id || authState.user?.id || '';
      
      const params = new URLSearchParams();
      if (mnrId) params.append('mnr_id', mnrId);
      if (this.startDate) params.append('start_date', this.startDate);
      if (this.endDate) params.append('end_date', this.endDate);
      
      const response = await apiService.get<any>(`/financial-operations/income/me/ved-income-transactions?${params}`);
      
      if (response.success && response.data) {
        this.records = (response.data.transactions || response.data || []).map((r: any, idx: number) => ({
          sno: idx + 1,
          for_member_id: r.for_member_id || r.from_mnr_id || '-',
          for_member_name: r.for_member_name || r.from_name || '-',
          from_date: r.from_date || r.date || '',
          to_date: r.to_date || r.date || '',
          total_amount: r.total_amount || r.amount || 0,
          max_applied: r.max_applied || r.ceiling_applied || false,
          is_paid: r.is_paid === true
        }));
      }
    } catch (error) {
      console.error('[MNRIncomeVed] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    const authState = authService.getAuthState();
    const mnrId = authState.user?.mnr_id || authState.user?.id || '';
    
    this.container.innerHTML = `
      <style>${getSharedStyles()}</style>
      ${PageHeader.render({ title: '👑 VED Leadership Recognition', showBack: true })}
      <div class="income-page">
        <div class="filter-section">
          <h5>🔍 Filter Options</h5>
          <div class="filter-row">
            <div class="filter-group">
              <label>Member ID</label>
              <input type="text" id="filterMnrId" value="${mnrId}" readonly style="background: #e5e7eb;" />
            </div>
          </div>
          <div class="filter-row-dates">
            <div class="filter-group">
              <label>Date From</label>
              <input type="date" id="filterStartDate" value="${this.startDate}" />
            </div>
            <div class="filter-group">
              <label>To</label>
              <input type="date" id="filterEndDate" value="${this.endDate}" />
            </div>
          </div>
          <button class="btn-submit" id="btnSubmit">Submit</button>
        </div>
        <div id="pageContent"></div>
      </div>
    `;
    PageHeader.attachListeners({ title: '👑 VED Leadership Recognition', showBack: true });
    this.attachListeners();
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const authState = authService.getAuthState();
    const mnrId = authState.user?.mnr_id || authState.user?.id || '';

    const table = new MobileTable({
      columns: [
        { key: 'sno', label: 'SNo' },
        { key: 'for_member_id', label: 'For Member ID' },
        { key: 'for_member_name', label: 'For Member Name' },
        { key: 'from_date', label: 'FromDate', render: (v) => formatDate(v) },
        { key: 'to_date', label: 'ToDate', render: (v) => formatDate(v) },
        { key: 'total_amount', label: 'Total Amount', render: (v) => `<span style="color: #10b981; font-weight: 600;">${formatCurrency(v)}</span>` },
        { key: 'max_applied', label: 'Max Applied', render: (v) => v ? '<span class="badge badge-yes">Yes</span>' : '<span class="badge badge-no">No</span>' },
        { key: 'is_paid', label: 'Status', render: (v) => v ? '<span class="badge" style="background: #10b981; color: white;">Paid</span>' : '<span class="badge" style="background: #eab308; color: #1a1a1a;">Pending</span>' }
      ],
      data: this.records,
      emptyMessage: 'No Ved income transactions found'
    });

    content.innerHTML = `
      <div class="filter-indicator">Filter By | Member Id is ${mnrId}</div>
      <div class="table-header"><h5>VED Leadership Recognition History</h5></div>
      ${table.render()}
    `;
  }

  private attachListeners(): void {
    document.getElementById('btnSubmit')?.addEventListener('click', () => {
      this.startDate = (document.getElementById('filterStartDate') as HTMLInputElement)?.value || '';
      this.endDate = (document.getElementById('filterEndDate') as HTMLInputElement)?.value || '';
      this.loadRecords();
    });
  }
}

// ============ GURU DAKSHINA ============
export class MNRIncomeGuru {
  private container: HTMLElement;
  private records: any[] = [];
  private loading = true;
  private startDate = '';
  private endDate = '';

  constructor(container: HTMLElement) { this.container = container; }

  async init(): Promise<void> {
    this.render();
    await this.loadRecords();
  }

  private async loadRecords(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const authState = authService.getAuthState();
      const mnrId = authState.user?.mnr_id || authState.user?.id || '';
      
      const params = new URLSearchParams();
      if (mnrId) params.append('mnr_id', mnrId);
      if (this.startDate) params.append('start_date', this.startDate);
      if (this.endDate) params.append('end_date', this.endDate);
      
      const response = await apiService.get<any>(`/financial-operations/income/me/guru-dakshina-transactions?${params}`);
      
      if (response.success && response.data) {
        this.records = (response.data.transactions || response.data || []).map((r: any, idx: number) => ({
          sno: idx + 1,
          member_id: r.member_id || r.mnr_id || mnrId,
          name: r.member_name || r.name || '-',
          for_member_id: r.for_member_id || r.from_mnr_id || '-',
          for_name: r.for_member_name || r.from_name || '-',
          from_date: r.from_date || r.date || '',
          to_date: r.to_date || r.date || '',
          total_amount: r.total_amount || r.amount || 0,
          is_paid: r.is_paid === true
        }));
      }
    } catch (error) {
      console.error('[MNRIncomeGuru] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    const authState = authService.getAuthState();
    const mnrId = authState.user?.mnr_id || authState.user?.id || '';
    
    this.container.innerHTML = `
      <style>${getSharedStyles()}</style>
      ${PageHeader.render({ title: '🙏 Mentorship Contribution Benefit', showBack: true })}
      <div class="income-page">
        <div class="filter-section">
          <h5>🔍 Filter Options</h5>
          <div class="filter-row">
            <div class="filter-group">
              <label>Member ID</label>
              <input type="text" id="filterMnrId" value="${mnrId}" readonly style="background: #e5e7eb;" />
            </div>
          </div>
          <div class="filter-row-dates">
            <div class="filter-group">
              <label>Date From</label>
              <input type="date" id="filterStartDate" value="${this.startDate}" />
            </div>
            <div class="filter-group">
              <label>To</label>
              <input type="date" id="filterEndDate" value="${this.endDate}" />
            </div>
          </div>
          <button class="btn-submit" id="btnSubmit">Submit</button>
        </div>
        <div id="pageContent"></div>
      </div>
    `;
    PageHeader.attachListeners({ title: '🙏 Mentorship Contribution Benefit', showBack: true });
    this.attachListeners();
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const authState = authService.getAuthState();
    const mnrId = authState.user?.mnr_id || authState.user?.id || '';

    const table = new MobileTable({
      columns: [
        { key: 'sno', label: 'SNo' },
        { key: 'member_id', label: 'MemberId' },
        { key: 'name', label: 'Name' },
        { key: 'for_member_id', label: 'ForMemberId' },
        { key: 'for_name', label: 'ForName' },
        { key: 'from_date', label: 'FromDate', render: (v) => formatDate(v) },
        { key: 'to_date', label: 'ToDate', render: (v) => formatDate(v) },
        { key: 'total_amount', label: 'Total Amount', render: (v) => `<span style="color: #10b981; font-weight: 600;">${formatCurrency(v)}</span>` },
        { key: 'is_paid', label: 'Status', render: (v) => v ? '<span class="badge" style="background: #10b981; color: white;">Paid</span>' : '<span class="badge" style="background: #eab308; color: #1a1a1a;">Pending</span>' }
      ],
      data: this.records,
      emptyMessage: 'No Mentorship Contribution Benefit transactions found'
    });

    content.innerHTML = `
      <div class="filter-indicator">Filter By | Member Id is ${mnrId}</div>
      <div class="table-header"><h5>Mentorship Contribution Benefit History</h5></div>
      ${table.render()}
    `;
  }

  private attachListeners(): void {
    document.getElementById('btnSubmit')?.addEventListener('click', () => {
      this.startDate = (document.getElementById('filterStartDate') as HTMLInputElement)?.value || '';
      this.endDate = (document.getElementById('filterEndDate') as HTMLInputElement)?.value || '';
      this.loadRecords();
    });
  }
}

// ============ FIELD ALLOWANCE - Two Cards Layout ============
export class MNRIncomeField {
  private container: HTMLElement;
  private standardAllowance: any = null;
  private carAllowance: any = null;
  private currentActive: string | null = null;
  private paymentHistory: any[] = [];
  private loading = true;

  constructor(container: HTMLElement) { this.container = container; }

  async init(): Promise<void> {
    this.render();
    await this.loadData();
  }

  private async loadData(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const [statusRes, historyRes] = await Promise.all([
        apiService.get<any>('/users/field-allowances-status'),
        apiService.get<any>('/users/field-allowances')
      ]);

      if (statusRes.success && statusRes.data) {
        const std = statusRes.data.standard_allowance || {};
        const car = statusRes.data.car_allowance || {};
        this.currentActive = statusRes.data.current_active || null;

        this.standardAllowance = {
          status: std.status?.overall_status || 'Not Started',
          total_paid: std.status?.total_paid || 0,
          months_completed: std.status?.months_completed || 0,
          months_remaining: std.status?.months_remaining || 18,
          opportunity_missed: std.status?.opportunity_missed || false,
          initial_eligibility: {
            required: std.initial_requirements?.direct_referrals?.required || 7,
            current: std.initial_requirements?.direct_referrals?.current || 0,
            remaining: std.initial_requirements?.direct_referrals?.remaining || 7,
            progress_percentage: std.initial_requirements?.direct_referrals?.progress_percentage || 0,
            is_frozen: std.initial_requirements?.direct_referrals?.is_frozen || false,
            deadline: std.target_dates?.initial_eligibility_deadline || null
          },
          monthly_requirement: {
            required: std.monthly_requirements?.matching_pairs?.required || 20,
            current: std.monthly_requirements?.matching_pairs?.current || 0,
            progress_percentage: std.monthly_requirements?.matching_pairs?.progress_percentage || 0,
            months_completed: std.status?.months_completed || 0
          },
          target_dates: std.target_dates || {}
        };

        this.carAllowance = {
          status: car.status?.overall_status || 'Not Eligible',
          total_paid: car.status?.total_paid || 0,
          months_completed: car.status?.months_completed || 0,
          months_remaining: car.status?.months_remaining || 72,
          opportunity_missed: car.status?.opportunity_missed || false,
          initial_eligibility: {
            required: car.initial_requirements?.matching_points?.required || 250,
            current: car.initial_requirements?.matching_points?.current || 0,
            remaining: car.initial_requirements?.matching_points?.remaining || 250,
            progress_percentage: car.initial_requirements?.matching_points?.progress_percentage || 0,
            is_frozen: car.initial_requirements?.matching_points?.is_frozen || false,
            qualification_status: car.initial_requirements?.matching_points?.qualification_status || null,
            deadline: car.target_dates?.initial_eligibility_deadline || null
          },
          monthly_requirement: {
            required: car.monthly_requirements?.matching_pairs?.required || 40,
            current: car.monthly_requirements?.matching_pairs?.current || 0,
            progress_percentage: car.monthly_requirements?.matching_pairs?.progress_percentage || 0,
            months_completed: car.status?.months_completed || 0
          },
          target_dates: car.target_dates || {}
        };
      }

      if (historyRes.success && historyRes.data) {
        const allowances = historyRes.data.allowances || historyRes.data.payment_history || [];
        this.paymentHistory = allowances.map((a: any) => ({
          date: a.date || a.timestamp || '',
          type: a.type || a.description || 'Field Allowance',
          amount: a.amount || 0,
          status: a.status || 'Completed'
        }));
      }
    } catch (error) {
      console.error('[MNRIncomeField] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        ${MobileTable.getStyles()}
        .field-page { padding: 16px; background: #0d1b2a; min-height: 100vh; }
        .about-section {
          background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
          border-radius: 12px; padding: 14px; margin-bottom: 16px; color: #451a03;
        }
        .about-section p { margin: 0; font-size: 12px; line-height: 1.5; }
        .allowance-cards { display: flex; flex-direction: column; gap: 16px; margin-bottom: 16px; }
        .allowance-card {
          border-radius: 12px; overflow: hidden;
          background: rgba(22, 33, 62, 0.9); border: 1px solid rgba(255,255,255,0.1);
        }
        .card-header { padding: 14px; color: white; }
        .card-header.standard { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
        .card-header.car { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); }
        .card-header h4 { margin: 0 0 4px; font-size: 15px; }
        .card-header p { margin: 0; font-size: 11px; opacity: 0.9; }
        .card-body { padding: 14px; }
        .status-row { display: flex; justify-content: space-between; margin-bottom: 12px; }
        .status-item { text-align: center; }
        .status-item .label { font-size: 10px; color: #8892b0; margin-bottom: 4px; }
        .status-item .value { font-size: 14px; font-weight: 600; color: #e6f1ff; }
        .status-badge { padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; }
        .badge-not-started { background: #6b7280; color: white; }
        .badge-not-eligible { background: #ef4444; color: white; }
        .badge-active { background: #10b981; color: white; }
        .eligibility-section { margin-bottom: 12px; }
        .eligibility-section h5 { font-size: 12px; color: #8892b0; margin: 0 0 8px; }
        .progress-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
        .progress-label { font-size: 11px; color: #e6f1ff; flex: 1; }
        .progress-bar { flex: 2; height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #3b82f6, #8b5cf6); border-radius: 4px; }
        .progress-value { font-size: 11px; color: #64d2ff; font-weight: 600; min-width: 50px; text-align: right; }
        .deadline-row { display: flex; justify-content: space-between; font-size: 11px; color: #8892b0; margin-top: 6px; }
        .history-section { margin-top: 16px; }
        .history-header {
          background: linear-gradient(135deg, #374151 0%, #1f2937 100%);
          padding: 12px; border-radius: 8px 8px 0 0;
        }
        .history-header h5 { margin: 0; color: white; font-size: 13px; }
        .loading-state { text-align: center; padding: 40px; color: #8892b0; }
      </style>
      ${PageHeader.render({ title: '🚗 Field Activity Support', showBack: true })}
      <div class="field-page" id="pageContent">
        <div class="loading-state">Loading...</div>
      </div>
    `;
    PageHeader.attachListeners({ title: '🚗 Field Activity Support', showBack: true });
  }

  private formatDeadline(dateStr: string | null): string {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch { return '-'; }
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const std = this.standardAllowance;
    const car = this.carAllowance;
    const stdPct = std?.initial_eligibility?.progress_percentage || 0;
    const carPct = car?.initial_eligibility?.progress_percentage || 0;
    const stdMonthlyPct = std?.monthly_requirement?.progress_percentage || 0;
    const carMonthlyPct = car?.monthly_requirement?.progress_percentage || 0;

    const activeAlert = this.currentActive ? `
      <div style="background: linear-gradient(135deg, #10b981, #059669); border-radius: 10px; padding: 12px; margin-bottom: 16px; color: white; font-size: 13px;">
        <strong>Active Allowance:</strong> ${this.currentActive === 'car' ? 'Car Allowance (₹25,000/month)' : 'Standard Field Allowance (₹10,000/month)'}
      </div>` : '';

    const stdMissedAlert = std?.opportunity_missed ? `
      <div style="background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3); border-radius: 6px; padding: 8px; margin-top: 8px; font-size: 11px; color: #fca5a5;">
        <strong>Missed Opportunity!</strong> Deadline passed.
      </div>` : '';

    const carMissedAlert = car?.opportunity_missed ? `
      <div style="background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3); border-radius: 6px; padding: 8px; margin-top: 8px; font-size: 11px; color: #fca5a5;">
        <strong>Missed Opportunity!</strong> Deadline passed.
      </div>` : '';

    const carQualAlert = (car?.initial_eligibility?.qualification_status && !car.initial_eligibility.qualification_status.qualified && !car.opportunity_missed) ? `
      <div style="background: rgba(251,191,36,0.15); border: 1px solid rgba(251,191,36,0.3); border-radius: 6px; padding: 8px; margin-top: 8px; font-size: 11px; color: #fde68a;">
        <strong>Qualification Required:</strong> ${car.initial_eligibility.qualification_status.message || ''}
      </div>` : '';

    content.innerHTML = `
      <div class="about-section">
        <p><strong>About Field Allowances:</strong> Performance-based fixed monthly payments for active MNR members. Two tiers available: Standard (₹10,000/month x 18 months) and Car Allowance (₹25,000/month x 72 months).</p>
      </div>

      ${activeAlert}

      <div class="allowance-cards">
        <div class="allowance-card">
          <div class="card-header standard">
            <h4>Standard Field Allowance</h4>
            <p>₹10,000/month x 18 months</p>
          </div>
          <div class="card-body">
            <div class="status-row">
              <div class="status-item">
                <div class="label">Status</div>
                <div class="value"><span class="status-badge ${std?.status === 'Active' ? 'badge-active' : std?.opportunity_missed ? 'badge-not-eligible' : 'badge-not-started'}">${std?.status || 'Not Started'}</span></div>
              </div>
              <div class="status-item">
                <div class="label">Total Paid</div>
                <div class="value" style="color: #10b981;">₹${(std?.total_paid || 0).toLocaleString('en-IN')}</div>
              </div>
            </div>
            
            <div class="eligibility-section">
              <h5>Initial Eligibility:</h5>
              <div class="progress-row">
                <div class="progress-label">7 Direct Business Facilitations (45 days)</div>
                <div class="progress-bar"><div class="progress-fill" style="width: ${stdPct}%; background: ${stdPct >= 100 ? '#10b981' : 'linear-gradient(90deg, #3b82f6, #8b5cf6)'};"></div></div>
                <div class="progress-value">${std?.initial_eligibility?.current || 0}/${std?.initial_eligibility?.required || 7}</div>
              </div>
              <div class="deadline-row">
                <span>Remaining: ${std?.initial_eligibility?.remaining ?? 7}</span>
                <span>Deadline: ${this.formatDeadline(std?.initial_eligibility?.deadline)}</span>
              </div>
              ${stdMissedAlert}
            </div>

            <div class="eligibility-section">
              <h5>Monthly Requirement:</h5>
              <div class="progress-row">
                <div class="progress-label">20 Matching Pairs/month</div>
                <div class="progress-bar"><div class="progress-fill" style="width: ${stdMonthlyPct}%;"></div></div>
                <div class="progress-value">${std?.monthly_requirement?.current || 0}/${std?.monthly_requirement?.required || 20}</div>
              </div>
              <div class="deadline-row">
                <span>Months: ${std?.monthly_requirement?.months_completed || 0}/18</span>
                <span>Next: ${this.formatDeadline(std?.target_dates?.next_payment_date)}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="allowance-card">
          <div class="card-header car">
            <h4>Car Allowance (Premium)</h4>
            <p>₹25,000/month x 72 months</p>
          </div>
          <div class="card-body">
            <div class="status-row">
              <div class="status-item">
                <div class="label">Status</div>
                <div class="value"><span class="status-badge ${car?.status === 'Active' ? 'badge-active' : car?.opportunity_missed ? 'badge-not-eligible' : 'badge-not-eligible'}">${car?.status || 'Not Eligible'}</span></div>
              </div>
              <div class="status-item">
                <div class="label">Total Paid</div>
                <div class="value" style="color: #10b981;">₹${(car?.total_paid || 0).toLocaleString('en-IN')}</div>
              </div>
            </div>
            
            <div class="eligibility-section">
              <h5>Initial Eligibility:</h5>
              <div class="progress-row">
                <div class="progress-label">250 Matching Points (90 days)</div>
                <div class="progress-bar"><div class="progress-fill" style="width: ${carPct}%; background: ${carPct >= 100 ? '#10b981' : 'linear-gradient(90deg, #f59e0b, #ef4444)'};"></div></div>
                <div class="progress-value">${car?.initial_eligibility?.current || 0}/${car?.initial_eligibility?.required || 250}</div>
              </div>
              <div class="deadline-row">
                <span>Remaining: ${car?.initial_eligibility?.remaining ?? 250}</span>
                <span>Deadline: ${this.formatDeadline(car?.initial_eligibility?.deadline)}</span>
              </div>
              ${carMissedAlert}
              ${carQualAlert}
            </div>

            <div class="eligibility-section">
              <h5>Monthly Requirement:</h5>
              <div class="progress-row">
                <div class="progress-label">40 Matching Pairs/month</div>
                <div class="progress-bar"><div class="progress-fill" style="width: ${carMonthlyPct}%;"></div></div>
                <div class="progress-value">${car?.monthly_requirement?.current || 0}/${car?.monthly_requirement?.required || 40}</div>
              </div>
              <div class="deadline-row">
                <span>Months: ${car?.monthly_requirement?.months_completed || 0}/72</span>
                <span>Next: ${this.formatDeadline(car?.target_dates?.next_payment_date)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="history-section">
        <div class="history-header"><h5>Payment History</h5></div>
        ${this.paymentHistory.length > 0 ? this.renderHistoryTable() : '<div class="empty-state" style="background: rgba(22,33,62,0.8); padding: 20px; text-align: center; color: #8892b0; border-radius: 0 0 8px 8px;">No payment history yet</div>'}
      </div>
    `;
  }

  private renderHistoryTable(): string {
    const table = new MobileTable({
      columns: [
        { key: 'date', label: 'Date', render: (v) => formatDate(v) },
        { key: 'type', label: 'Type' },
        { key: 'amount', label: 'Amount', render: (v) => `₹${v.toLocaleString()}` },
        { key: 'status', label: 'Status' }
      ],
      data: this.paymentHistory,
      emptyMessage: 'No payments found'
    });
    return table.render();
  }
}
