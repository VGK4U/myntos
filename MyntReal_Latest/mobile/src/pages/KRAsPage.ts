/**
 * KRAs Page - My KRAs with INLINE EXPANSION
 * DC Protocol: DC_MOBILE_KRAS_003
 * View, score, and submit KRAs for review - Full web parity
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface KRAInstance {
  id: number;
  instance_date: string;
  completion_status: string;
  completion_percentage?: number;
  self_rating: number | null;
  self_remarks: string | null;
  staff_notes: string | null;
  manager_rating: number | null;
  manager_remarks: string | null;
  manager_review_status: string | null;
  time_spent_minutes: number | null;
  submitted_at: string | null;
  completed_at: string | null;
  is_late?: boolean;
  is_delayed?: boolean;
  target_time?: string;
  template_id?: number;
  kra_code?: string;
  title?: string;
  description?: string;
  frequency?: string;
  kra_template?: {
    id: number;
    kra_code: string;
    title: string;
    description: string;
    weightage: number;
    target_value: number;
    unit: string;
    frequency: string;
  };
}

interface KRAStats {
  total: number;
  pending_submission: number;
  awaiting_review: number;
  approved: number;
  rejected: number;
}

const RATING_LABELS = ['Poor', 'Below Average', 'Average', 'Good', 'Excellent'];

const STATUS_TABS = [
  { id: 'pending', label: 'Pending' },
  { id: 'submitted', label: 'Submitted' },
  { id: 'approved', label: 'Approved' },
  { id: 'rejected', label: 'Rejected' },
  { id: '', label: 'All' }
];

export class KRAsPage {
  private container: HTMLElement;
  private kras: KRAInstance[] = [];
  private stats: KRAStats = { total: 0, pending_submission: 0, awaiting_review: 0, approved: 0, rejected: 0 };
  private loading: boolean = true;
  private filter: string = 'pending';
  private expandedKRAId: number | null = null;
  private dateFrom: string = '';
  private dateTo: string = '';

  constructor(container: HTMLElement) {
    this.container = container;
    const now = new Date();
    this.dateFrom = now.toISOString().split('T')[0];
    const twoDaysLater = new Date(now.getTime() + 2 * 24 * 60 * 60 * 1000);
    this.dateTo = twoDaysLater.toISOString().split('T')[0];
  }

  async init(): Promise<void> {
    this.render();
    await this.loadKRAs();
  }

  private async loadKRAs(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const params = new URLSearchParams();
      if (this.dateFrom) params.append('date_from', this.dateFrom);
      if (this.dateTo) params.append('date_to', this.dateTo);
      if (this.filter) params.append('status', this.filter);
      params.append('_t', Date.now().toString());
      
      const response = await apiService.get<any>(`/staff/kra/my-kras?${params.toString()}`);
      const data = response.data as any;
      
      if (response.success !== false && data) {
        this.kras = data.kras || data.instances || (Array.isArray(data) ? data : []);
        if (data.stats) {
          this.stats = data.stats;
        }
      } else {
        this.kras = [];
      }
    } catch (error) {
      console.error('[KRAsPage] Failed to load:', error);
      this.kras = [];
    }

    this.loading = false;
    this.updateStats();
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container kras-page">
        ${PageHeader.render({ title: 'My KRAs', showBack: true })}
        
        <div class="stats-scroll">
          <div class="stat-card" data-filter="">
            <div class="stat-icon total"><i class="fas fa-list"></i></div>
            <div class="stat-value" id="statTotal">0</div>
            <div class="stat-label">Total</div>
          </div>
          <div class="stat-card" data-filter="pending">
            <div class="stat-icon pending"><i class="fas fa-clock"></i></div>
            <div class="stat-value" id="statPending">0</div>
            <div class="stat-label">Pending</div>
          </div>
          <div class="stat-card" data-filter="submitted">
            <div class="stat-icon submitted"><i class="fas fa-paper-plane"></i></div>
            <div class="stat-value" id="statSubmitted">0</div>
            <div class="stat-label">Submitted</div>
          </div>
          <div class="stat-card" data-filter="approved">
            <div class="stat-icon approved"><i class="fas fa-check-circle"></i></div>
            <div class="stat-value" id="statApproved">0</div>
            <div class="stat-label">Approved</div>
          </div>
        </div>
        
        <div class="filters-card">
          <div class="date-filter-row">
            <div class="date-input-group">
              <label>From</label>
              <input type="date" id="dateFrom" class="form-input" value="${this.dateFrom}">
            </div>
            <div class="date-input-group">
              <label>To</label>
              <input type="date" id="dateTo" class="form-input" value="${this.dateTo}">
            </div>
            <button class="btn btn-sm btn-primary" id="applyDateFilter">Apply</button>
          </div>
          
          <div class="filter-tabs scrollable">
            ${STATUS_TABS.map(t => `<button class="filter-tab ${this.filter === t.id ? 'active' : ''}" data-filter="${t.id}">${t.label}</button>`).join('')}
          </div>
        </div>

        <div class="list-container" id="krasList">
          <div class="loading-state">Loading...</div>
        </div>
      </div>

      ${this.getStyles()}
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private getStyles(): string {
    return `<style>
      .kras-page { padding-bottom: 80px; }
      .stats-scroll { display: flex; gap: 12px; overflow-x: auto; padding: 0 16px 16px; -webkit-overflow-scrolling: touch; }
      .stats-scroll::-webkit-scrollbar { display: none; }
      .stat-card { min-width: 80px; background: rgba(255,255,255,0.1); border-radius: 12px; padding: 12px; text-align: center; cursor: pointer; border: 2px solid transparent; }
      .stat-card.active { border-color: #4f46e5; background: rgba(79,70,229,0.2); }
      .stat-icon { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; margin: 0 auto 6px; font-size: 14px; }
      .stat-icon.total { background: #e0e7ff; color: #4338ca; }
      .stat-icon.pending { background: #fef3c7; color: #d97706; }
      .stat-icon.submitted { background: #dbeafe; color: #2563eb; }
      .stat-icon.approved { background: #d1fae5; color: #059669; }
      .stat-value { font-size: 18px; font-weight: 700; color: #fff; }
      .stat-label { font-size: 10px; color: rgba(255,255,255,0.7); }
      .filters-card { margin: 0 16px 16px; padding: 16px; background: rgba(255,255,255,0.05); border-radius: 12px; }
      .date-filter-row { display: flex; gap: 12px; align-items: flex-end; margin-bottom: 12px; }
      .date-input-group { flex: 1; }
      .date-input-group label { display: block; font-size: 11px; color: rgba(255,255,255,0.6); margin-bottom: 4px; text-transform: uppercase; }
      .form-input, .form-textarea { width: 100%; padding: 10px 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: #fff; font-size: 14px; }
      .form-textarea { resize: vertical; min-height: 80px; }
      .btn { padding: 10px 16px; border-radius: 8px; font-weight: 600; border: none; cursor: pointer; }
      .btn-sm { padding: 8px 12px; font-size: 13px; }
      .btn-primary { background: #4f46e5; color: #fff; }
      .btn-secondary { background: rgba(255,255,255,0.1); color: #fff; }
      .btn-success { background: #059669; color: #fff; }
      .filter-tabs { display: flex; gap: 8px; overflow-x: auto; -webkit-overflow-scrolling: touch; }
      .filter-tabs::-webkit-scrollbar { display: none; }
      .filter-tab { padding: 8px 16px; background: rgba(255,255,255,0.1); border: none; border-radius: 20px; color: rgba(255,255,255,0.7); font-size: 13px; white-space: nowrap; cursor: pointer; }
      .filter-tab.active { background: #4f46e5; color: #fff; }
      .list-container { padding: 0 16px; }
      .kra-card-container { margin-bottom: 12px; }
      .kra-card { background: rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; cursor: pointer; transition: all 0.2s; }
      .kra-card:hover { background: rgba(255,255,255,0.12); }
      .kra-card.expanded { border-radius: 12px 12px 0 0; background: rgba(79,70,229,0.2); border: 1px solid #4f46e5; border-bottom: none; }
      .kra-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
      .kra-code { font-size: 11px; color: #a78bfa; font-weight: 600; }
      .expand-icon { color: rgba(255,255,255,0.5); transition: transform 0.3s; }
      .expand-icon.rotated { transform: rotate(180deg); }
      .status-badge { padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }
      .status-badge.pending { background: #fef3c7; color: #92400e; }
      .status-badge.submitted { background: #dbeafe; color: #1e40af; }
      .status-badge.approved { background: #d1fae5; color: #065f46; }
      .status-badge.rejected { background: #fee2e2; color: #991b1b; }
      .kra-title { font-size: 15px; font-weight: 600; color: #fff; margin-bottom: 6px; }
      .kra-description { font-size: 13px; color: rgba(255,255,255,0.7); margin-bottom: 8px; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
      .kra-meta { display: flex; gap: 16px; font-size: 12px; color: rgba(255,255,255,0.6); }
      .self-rating { margin-top: 8px; display: flex; align-items: center; gap: 8px; }
      .rating-stars { color: #fbbf24; font-size: 14px; }
      .rating-value { font-size: 12px; color: rgba(255,255,255,0.7); }
      .kra-inline-detail { display: none; background: rgba(30,41,59,0.98); border: 1px solid #4f46e5; border-top: none; border-radius: 0 0 12px 12px; padding: 16px; }
      .kra-inline-detail.show { display: block; }
      .detail-section { margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.1); }
      .detail-section:last-child { border-bottom: none; margin-bottom: 0; }
      .detail-section-title { font-size: 13px; font-weight: 600; color: #fff; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
      .detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
      .detail-item { display: flex; flex-direction: column; }
      .detail-label { font-size: 11px; color: rgba(255,255,255,0.5); text-transform: uppercase; margin-bottom: 4px; }
      .detail-value { font-size: 14px; color: #fff; }
      .detail-description { padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px; color: rgba(255,255,255,0.8); font-size: 14px; line-height: 1.5; }
      .star-rating-input { display: flex; gap: 8px; margin-bottom: 8px; }
      .star-btn { width: 44px; height: 44px; border-radius: 8px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: rgba(255,255,255,0.3); font-size: 20px; cursor: pointer; transition: all 0.2s; }
      .star-btn.selected { background: #fbbf24; color: #fff; border-color: #fbbf24; }
      .star-btn:hover { background: rgba(251,191,36,0.3); color: #fbbf24; }
      .rating-label-text { font-size: 13px; color: rgba(255,255,255,0.7); }
      .form-group { margin-bottom: 16px; }
      .form-group label { display: block; color: rgba(255,255,255,0.7); font-size: 13px; margin-bottom: 8px; }
      .form-group .required { color: #ef4444; }
      .form-select { width: 100%; padding: 10px 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: #fff; font-size: 14px; -webkit-appearance: none; appearance: none; background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3e%3cpath fill='none' stroke='%23ffffff' stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M2 5l6 6 6-6'/%3e%3c/svg%3e"); background-repeat: no-repeat; background-position: right 12px center; background-size: 12px; }
      .form-select option { background: #1e293b; color: #fff; }
      .pending-review-banner { text-align: center; padding: 12px; background: rgba(59,130,246,0.15); border: 1px solid rgba(59,130,246,0.3); border-radius: 8px; color: #93c5fd; font-size: 13px; }
      .pending-review-banner i { margin-right: 8px; }
      .inline-footer { display: flex; gap: 8px; margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.1); }
      .inline-footer .btn { flex: 1; }
      .manager-review-section { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); border-radius: 8px; padding: 12px; }
      .manager-review-section h6 { color: #10b981; margin: 0 0 8px 0; font-size: 13px; }
      .loading-state, .empty-state { text-align: center; padding: 40px; color: rgba(255,255,255,0.5); }
    </style>`;
  }

  private updateStats(): void {
    const setVal = (id: string, val: number) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val.toString();
    };
    setVal('statTotal', this.stats.total || this.kras.length);
    setVal('statPending', this.stats.pending_submission || this.kras.filter(k => k.completion_status === 'pending').length);
    setVal('statSubmitted', this.stats.awaiting_review || this.kras.filter(k => k.completion_status === 'completed').length);
    setVal('statApproved', this.stats.approved || this.kras.filter(k => k.manager_review_status === 'approved').length);
  }

  private updateContent(): void {
    const container = document.getElementById('krasList');
    if (!container) return;

    if (this.loading) {
      container.innerHTML = '<div class="loading-state"><i class="fas fa-spinner fa-spin"></i> Loading KRAs...</div>';
      return;
    }

    if (this.kras.length === 0) {
      container.innerHTML = `<div class="empty-state"><i class="fas fa-clipboard-list"></i><p>No KRAs found${this.filter ? ` with status "${this.filter}"` : ''}</p></div>`;
      return;
    }

    const sorted = [...this.kras].sort((a, b) => a.instance_date < b.instance_date ? -1 : a.instance_date > b.instance_date ? 1 : 0);
    container.innerHTML = sorted.map(kra => this.renderKRACard(kra)).join('');
    this.attachCardListeners();
  }

  private renderKRACard(kra: KRAInstance): string {
    const kraCode = kra.kra_code || kra.kra_template?.kra_code || '';
    const title = kra.title || kra.kra_template?.title || 'Untitled KRA';
    const description = kra.description || kra.kra_template?.description || '';
    const frequency = kra.frequency || kra.kra_template?.frequency || 'Daily';
    const isExpanded = this.expandedKRAId === kra.id;
    const isSubmitted = !!kra.submitted_at;
    const canUpdate = !isSubmitted;
    const canSubmit = !isSubmitted && kra.completion_status !== 'pending';
    const isPendingReview = isSubmitted && kra.manager_review_status === 'pending_review';
    const notes = kra.self_remarks || kra.staff_notes || '';

    return `
      <div class="kra-card-container" data-kra-id="${kra.id}">
        <div class="kra-card ${isExpanded ? 'expanded' : ''}" data-kra-id="${kra.id}">
          <div class="kra-header">
            <div>
              <span class="kra-code">${kraCode}</span>
              <span class="status-badge ${this.getStatusClass(kra.completion_status)}">${this.getStatusLabel(kra.completion_status)}</span>
              ${isPendingReview ? '<span class="status-badge submitted" style="margin-left:4px;">Under Review</span>' : ''}
              ${kra.manager_review_status === 'approved' ? '<span class="status-badge approved" style="margin-left:4px;">Approved</span>' : ''}
              ${kra.manager_review_status === 'rejected' ? '<span class="status-badge rejected" style="margin-left:4px;">Rejected</span>' : ''}
            </div>
            <i class="fas fa-chevron-down expand-icon ${isExpanded ? 'rotated' : ''}"></i>
          </div>
          <div class="kra-title">${this.escapeHtml(title)}</div>
          ${description ? `<div class="kra-description">${this.escapeHtml(description)}</div>` : ''}
          <div class="kra-meta">
            <span><i class="fas fa-sync-alt"></i> ${frequency}</span>
            <span><i class="fas fa-calendar"></i> ${this.formatDate(kra.instance_date)}</span>
            ${kra.time_spent_minutes ? `<span><i class="fas fa-clock"></i> ${kra.time_spent_minutes} mins</span>` : ''}
          </div>
          ${kra.self_rating ? `
            <div class="self-rating">
              <span class="rating-stars">${'★'.repeat(kra.self_rating)}${'☆'.repeat(5 - kra.self_rating)}</span>
              <span class="rating-value">${kra.self_rating}/5</span>
            </div>
          ` : ''}
        </div>
        
        <div class="kra-inline-detail ${isExpanded ? 'show' : ''}" id="detail-${kra.id}">
          <div class="detail-section">
            <div class="detail-section-title"><i class="fas fa-info-circle"></i> KRA Details</div>
            <div class="detail-grid">
              <div class="detail-item"><span class="detail-label">Code</span><span class="detail-value">${kraCode}</span></div>
              <div class="detail-item"><span class="detail-label">Frequency</span><span class="detail-value">${frequency}</span></div>
              <div class="detail-item"><span class="detail-label">Date</span><span class="detail-value">${this.formatDate(kra.instance_date)}</span></div>
              <div class="detail-item"><span class="detail-label">Status</span><span class="detail-value">${this.getStatusLabel(kra.completion_status)}</span></div>
              ${kra.completion_percentage !== undefined && kra.completion_percentage !== null ? `<div class="detail-item"><span class="detail-label">Completion</span><span class="detail-value">${kra.completion_percentage}%</span></div>` : ''}
              ${kra.time_spent_minutes ? `<div class="detail-item"><span class="detail-label">Time Spent</span><span class="detail-value">${kra.time_spent_minutes} mins</span></div>` : ''}
            </div>
            ${description ? `<div style="margin-top: 12px;"><span class="detail-label">Description</span><div class="detail-description">${this.escapeHtml(description)}</div></div>` : ''}
            ${notes ? `<div style="margin-top: 12px;"><span class="detail-label">Staff Notes</span><div class="detail-description">${this.escapeHtml(notes)}</div></div>` : ''}
          </div>
          
          ${kra.self_rating ? `
            <div class="detail-section">
              <div class="detail-section-title"><i class="fas fa-user"></i> Your Submission</div>
              <div class="detail-grid">
                <div class="detail-item"><span class="detail-label">Self Rating</span><span class="detail-value" style="color: #fbbf24;">${'★'.repeat(kra.self_rating)}${'☆'.repeat(5 - kra.self_rating)} (${kra.self_rating}/5)</span></div>
                ${kra.time_spent_minutes ? `<div class="detail-item"><span class="detail-label">Time Spent</span><span class="detail-value">${kra.time_spent_minutes} minutes</span></div>` : ''}
              </div>
              ${kra.self_remarks ? `<div style="margin-top: 12px;"><span class="detail-label">Your Remarks</span><div class="detail-description">${this.escapeHtml(kra.self_remarks)}</div></div>` : ''}
            </div>
          ` : ''}
          
          ${kra.manager_rating ? `
            <div class="detail-section">
              <div class="manager-review-section">
                <h6><i class="fas fa-user-tie"></i> Manager Review</h6>
                <div class="detail-grid">
                  <div class="detail-item"><span class="detail-label">Manager Rating</span><span class="detail-value" style="color: #fbbf24;">${'★'.repeat(kra.manager_rating)}${'☆'.repeat(5 - kra.manager_rating)} (${kra.manager_rating}/5)</span></div>
                </div>
                ${kra.manager_remarks ? `<div style="margin-top: 8px;"><span class="detail-label">Manager Remarks</span><div class="detail-description">${this.escapeHtml(kra.manager_remarks)}</div></div>` : ''}
              </div>
            </div>
          ` : ''}
          
          ${canUpdate ? `
            <div class="detail-section">
              <div class="detail-section-title"><i class="fas fa-edit"></i> Update Status</div>
              <div class="form-group">
                <label>Status <span class="required">*</span></label>
                <select id="updateStatus-${kra.id}" class="form-select">
                  <option value="pending" ${kra.completion_status === 'pending' ? 'selected' : ''}>Pending</option>
                  <option value="in_progress" ${kra.completion_status === 'in_progress' ? 'selected' : ''}>In Progress</option>
                  <option value="completed" ${kra.completion_status === 'completed' ? 'selected' : ''}>Completed</option>
                  <option value="partial" ${kra.completion_status === 'partial' ? 'selected' : ''}>Partial</option>
                  <option value="skipped" ${kra.completion_status === 'skipped' ? 'selected' : ''}>Skipped</option>
                  <option value="na" ${kra.completion_status === 'na' ? 'selected' : ''}>NA / Exempted</option>
                </select>
              </div>
              <div class="form-group">
                <label>Completion %</label>
                <input type="number" id="updatePercentage-${kra.id}" class="form-input" min="0" max="100" value="${kra.completion_percentage ?? (kra.completion_status === 'completed' ? 100 : 0)}">
              </div>
              <div class="form-group">
                <label>Time Spent (minutes)</label>
                <input type="number" id="updateTimeSpent-${kra.id}" class="form-input" min="0" max="1440" value="${kra.time_spent_minutes || 0}">
              </div>
              <div class="form-group">
                <label>Staff Notes</label>
                <textarea id="updateNotes-${kra.id}" class="form-textarea" maxlength="1000" placeholder="Add notes about your progress">${this.escapeHtml(notes)}</textarea>
              </div>
              <button class="btn btn-primary" data-action="update" data-id="${kra.id}" style="width: 100%;">
                <i class="fas fa-save"></i> Save Update
              </button>
            </div>
          ` : ''}

          ${canSubmit ? `
            <div class="detail-section">
              <div class="detail-section-title"><i class="fas fa-paper-plane"></i> Submit for Manager Review</div>
              <div class="form-group">
                <label>Self Rating (1-5) <span class="required">*</span></label>
                <div class="star-rating-input" id="starRating-${kra.id}">
                  ${[1,2,3,4,5].map(n => `<button class="star-btn" data-value="${n}">★</button>`).join('')}
                </div>
                <input type="hidden" id="rating-${kra.id}" value="0">
                <div class="rating-label-text" id="ratingLabel-${kra.id}">Select a rating</div>
              </div>
              <div class="form-group">
                <label>Self Remarks</label>
                <textarea id="remarks-${kra.id}" class="form-textarea" maxlength="1000" placeholder="Add remarks about your work"></textarea>
              </div>
              <div class="form-group">
                <label>Time Spent (minutes)</label>
                <input type="number" id="submitTimeSpent-${kra.id}" class="form-input" min="0" max="1440" value="${kra.time_spent_minutes || 0}">
              </div>
            </div>
          ` : ''}

          ${isPendingReview ? `
            <div class="detail-section">
              <div class="pending-review-banner">
                <i class="fas fa-hourglass-half"></i> Submitted &amp; awaiting manager review
              </div>
            </div>
          ` : ''}
          
          <div class="inline-footer">
            <button class="btn btn-secondary" data-action="collapse" data-id="${kra.id}">Close</button>
            ${canSubmit ? `<button class="btn btn-success" data-action="submit" data-id="${kra.id}"><i class="fas fa-paper-plane"></i> Submit</button>` : ''}
            <button class="btn" data-action="wa-kra" data-id="${kra.id}" data-title="${this.escapeHtml(title)}" data-date="${kra.instance_date || ''}" data-status="${kra.completion_status || 'pending'}" style="background:#25D366;color:#fff;border:none;padding:8px 14px;border-radius:6px;font-size:13px;cursor:pointer;">💬 WA</button>
          </div>
        </div>
      </div>
    `;
  }

  private sendWaForKra(title: string, date: string, status: string): void {
    const msg = `📊 *KRA Update*\n\nKRA: ${title}\nDate: ${date || 'N/A'}\nStatus: ${status.replace(/_/g,' ')}\n\nPlease review and take action.`;
    const ph = (window.prompt('WhatsApp number (e.g. 919876543210):', '91') || '').replace(/\D/g, '');
    if (!ph || ph.length < 10) return;
    window.open('https://wa.me/' + ph + '?text=' + encodeURIComponent(msg), '_blank');
  }

  private attachEventListeners(): void {
    document.getElementById('applyDateFilter')?.addEventListener('click', () => {
      const fromInput = document.getElementById('dateFrom') as HTMLInputElement;
      const toInput = document.getElementById('dateTo') as HTMLInputElement;
      if (fromInput) this.dateFrom = fromInput.value;
      if (toInput) this.dateTo = toInput.value;
      this.expandedKRAId = null;
      this.loadKRAs();
    });

    this.container.querySelectorAll('.filter-tab').forEach(btn => {
      btn.addEventListener('click', () => {
        this.filter = btn.getAttribute('data-filter') || '';
        this.container.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.expandedKRAId = null;
        this.loadKRAs();
      });
    });

    this.container.querySelectorAll('.stat-card').forEach(card => {
      card.addEventListener('click', () => {
        const filter = card.getAttribute('data-filter') || '';
        this.filter = filter;
        this.container.querySelectorAll('.filter-tab').forEach(t => t.classList.toggle('active', t.getAttribute('data-filter') === filter));
        this.container.querySelectorAll('.stat-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        this.expandedKRAId = null;
        this.loadKRAs();
      });
    });
  }

  private attachCardListeners(): void {
    document.querySelectorAll('.kra-card').forEach(card => {
      card.addEventListener('click', (e) => {
        const target = e.target as HTMLElement;
        if (target.closest('select') || target.closest('input') || target.closest('button') || target.closest('textarea')) return;
        const kraId = parseInt(card.getAttribute('data-kra-id') || '0');
        this.toggleDetail(kraId);
      });
    });

    document.querySelectorAll('[data-action]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const action = btn.getAttribute('data-action');
        const kraId = parseInt(btn.getAttribute('data-id') || '0');
        switch (action) {
          case 'update': await this.updateKRA(kraId); break;
          case 'submit': await this.submitKRA(kraId); break;
          case 'collapse': this.collapseDetail(); break;
          case 'wa-kra': {
            const title = btn.getAttribute('data-title') || '';
            const date = btn.getAttribute('data-date') || '';
            const status = btn.getAttribute('data-status') || '';
            this.sendWaForKra(title, date, status);
            break;
          }
        }
      });
    });

    document.querySelectorAll('.star-rating-input').forEach(container => {
      const kraId = container.id.replace('starRating-', '');
      container.querySelectorAll('.star-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const value = parseInt((btn as HTMLElement).dataset.value || '0');
          const hiddenInput = document.getElementById(`rating-${kraId}`) as HTMLInputElement;
          const labelEl = document.getElementById(`ratingLabel-${kraId}`);
          if (hiddenInput) hiddenInput.value = value.toString();
          if (labelEl) labelEl.textContent = `${value}/5 - ${RATING_LABELS[value - 1]}`;
          container.querySelectorAll('.star-btn').forEach((b, i) => {
            b.classList.toggle('selected', i < value);
          });
        });
      });
    });
  }

  private toggleDetail(kraId: number): void {
    if (this.expandedKRAId === kraId) {
      this.collapseDetail();
    } else {
      this.expandedKRAId = kraId;
      this.updateContent();
    }
  }

  private collapseDetail(): void {
    this.expandedKRAId = null;
    this.updateContent();
  }

  private async updateKRA(kraId: number): Promise<void> {
    const status = (document.getElementById(`updateStatus-${kraId}`) as HTMLSelectElement)?.value;
    const percentage = parseInt((document.getElementById(`updatePercentage-${kraId}`) as HTMLInputElement)?.value || '0');
    const timeSpent = parseInt((document.getElementById(`updateTimeSpent-${kraId}`) as HTMLInputElement)?.value || '0');
    const notes = (document.getElementById(`updateNotes-${kraId}`) as HTMLTextAreaElement)?.value?.trim() || null;

    if (!status) {
      alert('Please select a status');
      return;
    }

    try {
      const response = await apiService.put(`/staff/kra/instances/${kraId}`, {
        completion_status: status,
        completion_percentage: percentage,
        time_spent_minutes: timeSpent,
        time_source: 'manual',
        staff_notes: notes
      });

      if (response.success) {
        alert('KRA updated successfully');
        await this.loadKRAs();
      } else {
        alert((response as any).error || 'Failed to update KRA');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to update KRA');
    }
  }

  private async submitKRA(kraId: number): Promise<void> {
    const rating = parseInt((document.getElementById(`rating-${kraId}`) as HTMLInputElement)?.value || '0');
    const timeSpent = parseInt((document.getElementById(`submitTimeSpent-${kraId}`) as HTMLInputElement)?.value || '0');
    const remarks = (document.getElementById(`remarks-${kraId}`) as HTMLTextAreaElement)?.value?.trim() || '';

    if (!rating || rating < 1 || rating > 5) {
      alert('Please select a self rating (1-5 stars)');
      return;
    }

    try {
      const response = await apiService.post(`/staff/kra/my-kras/${kraId}/submit`, {
        self_rating: rating,
        self_remarks: remarks,
        time_spent_minutes: timeSpent
      });

      if (response.success) {
        alert('KRA submitted for manager review!');
        this.expandedKRAId = null;
        await this.loadKRAs();
      } else {
        alert((response as any).error || 'Failed to submit KRA');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to submit KRA');
    }
  }

  private getStatusClass(status: string): string {
    switch (status?.toLowerCase()) {
      case 'pending': return 'pending';
      case 'in_progress': return 'submitted';
      case 'completed': return 'approved';
      case 'partial': return 'pending';
      case 'skipped': return 'rejected';
      case 'na': return 'rejected';
      case 'approved': return 'approved';
      case 'rejected': return 'rejected';
      default: return 'pending';
    }
  }

  private getStatusLabel(status: string): string {
    switch (status?.toLowerCase()) {
      case 'pending': return 'Pending';
      case 'in_progress': return 'In Progress';
      case 'completed': return 'Completed';
      case 'partial': return 'Partial';
      case 'skipped': return 'Skipped';
      case 'na': return 'NA / Exempted';
      case 'approved': return 'Approved';
      case 'rejected': return 'Rejected';
      default: return status || 'Pending';
    }
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'Not set';
    return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  private escapeHtml(str: string): string {
    if (!str) return '';
    return str.replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m] || m);
  }
}
