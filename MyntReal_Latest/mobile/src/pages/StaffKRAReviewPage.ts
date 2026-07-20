/**
 * Staff KRA Review Page
 * DC Protocol: DC_MOBILE_KRA_REVIEW_002
 * Review and approve employee KRA scores with INLINE EXPANSION
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface KRAReview {
  id: number;
  employee_id: number;
  employee_name: string;
  kra_title: string;
  kra_code: string;
  instance_date: string;
  completion_status: string;
  manager_review_status: string;
  self_rating: number | null;
  manager_rating: number | null;
  submitted_at: string;
  description?: string;
  metrics?: any[];
  employee_remarks?: string;
  manager_remarks?: string;
}

const STATUS_TABS = [
  { id: 'pending_review', label: 'Pending' },
  { id: 'approved', label: 'Approved' },
  { id: 'rejected', label: 'Rejected' },
  { id: '', label: 'All' }
];

export class StaffKRAReviewPage {
  private container: HTMLElement;
  private reviews: KRAReview[] = [];
  private loading: boolean = true;
  private filterStatus: string = 'pending_review';
  private dateFrom: string = '';
  private dateTo: string = '';
  private expandedReviewId: number | null = null;
  private employeeSearch: string = '';
  private selectedEmployeeId: number | null = null;
  private teamEmployees: Array<{id: number; name: string}> = [];
  private isVGKOrEA: boolean = false;
  private hasTeam: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
    const now = new Date();
    this.dateTo = now.toISOString().split('T')[0];
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    this.dateFrom = thirtyDaysAgo.toISOString().split('T')[0];
  }

  async init(): Promise<void> {
    this.render();
    await this.checkUserPermissions();
    await this.loadReviews();
  }

  private async checkUserPermissions(): Promise<void> {
    try {
      const response = await apiService.get<any>('/staff/auth/me');
      if (response.success && response.data) {
        const profile = response.data;
        // DC Protocol (Feb 2026): Check if user is VGK/EA/Key Leadership for all employee access
        this.isVGKOrEA = profile.is_vgk || profile.is_admin || profile.is_leader || 
          (profile.role && (
            profile.role.hierarchy_level >= 150 ||
            ['HR', 'Executive Assistant', 'Key Leadership', 'VGK4U', 'Supreme'].includes(profile.role.role_name) ||
            ['hr', 'ea', 'kl', 'vgk4u', 'supreme'].includes(profile.role.role_code?.toLowerCase())
          ));
        this.hasTeam = profile.has_direct_reports || profile.is_manager || profile.is_leader || this.isVGKOrEA;
        
        console.log(`[StaffKRAReview] User permissions: isVGKOrEA=${this.isVGKOrEA}, hasTeam=${this.hasTeam}`);
        
        // Load team employees for filter dropdown
        if (this.hasTeam || this.isVGKOrEA) {
          await this.loadTeamEmployees();
        }
      }
    } catch (error) {
      console.error('[StaffKRAReview] Failed to check permissions:', error);
    }
  }

  private async loadTeamEmployees(): Promise<void> {
    try {
      const scope = this.isVGKOrEA ? 'all' : 'team';
      const response = await apiService.get<any>(`/staff/employees/list?scope=${scope}&status=active`);
      if (response.success && response.data) {
        this.teamEmployees = (response.data.employees || response.data || []).map((e: any) => ({
          id: e.id,
          name: e.full_name || `${e.first_name || ''} ${e.last_name || ''}`.trim() || e.employee_id
        }));
        console.log(`[StaffKRAReview] Loaded ${this.teamEmployees.length} team employees`);
        // Update employee filter in UI
        this.updateEmployeeFilter();
      }
    } catch (error) {
      console.error('[StaffKRAReview] Failed to load team employees:', error);
    }
  }

  private updateEmployeeFilter(): void {
    const filterContainer = document.getElementById('employeeFilterContainer');
    if (filterContainer && (this.hasTeam || this.isVGKOrEA)) {
      filterContainer.innerHTML = `
        <div class="filter-row">
          <select id="employeeFilter" class="form-select">
            <option value="">All Employees</option>
            ${this.teamEmployees.map(e => `<option value="${e.id}" ${e.id === this.selectedEmployeeId ? 'selected' : ''}>${e.name}</option>`).join('')}
          </select>
        </div>
      `;
      document.getElementById('employeeFilter')?.addEventListener('change', (e) => {
        this.selectedEmployeeId = parseInt((e.target as HTMLSelectElement).value) || null;
        // DC Protocol (Feb 2026): Reload reviews when employee filter changes
        this.loadReviews();
      });
    }
  }

  private async loadReviews(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      const params = new URLSearchParams();
      if (this.filterStatus) {
        params.append('manager_review_status', this.filterStatus);
        params.append('view_mode', this.filterStatus === 'approved' ? 'performance_review' : 'pending');
      }
      if (this.dateFrom) params.append('date_from', this.dateFrom);
      if (this.dateTo) params.append('date_to', this.dateTo);
      // DC Protocol (Feb 2026): Add employee_id filter for person-wise filtering
      if (this.selectedEmployeeId) {
        params.append('employee_id', this.selectedEmployeeId.toString());
      }
      params.append('_t', Date.now().toString());
      
      const response = await apiService.get<any>(`/staff/kra/manager-review/pending?${params.toString()}`);
      const data = response.data as any;
      if (response.success !== false && data) {
        this.reviews = data.instances || data.reviews || (Array.isArray(data) ? data : []);
      } else {
        this.reviews = [];
      }
    } catch (error) {
      console.error('[StaffKRAReviewPage] Failed to load:', error);
      this.reviews = [];
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container kra-review-page">
        ${PageHeader.render({ title: 'KRA Reviews', showBack: true })}
        
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
            <button class="btn btn-sm btn-primary" id="applyFilter">Apply</button>
          </div>
          
          <!-- DC Protocol (Feb 2026): Employee filter container - populated dynamically for VGK/EA users -->
          <div id="employeeFilterContainer"></div>
          
          <div class="filter-tabs scrollable">
            ${STATUS_TABS.map(t => `<button class="filter-tab ${this.filterStatus === t.id ? 'active' : ''}" data-status="${t.id}">${t.label}</button>`).join('')}
          </div>
        </div>

        <div class="list-container" id="reviewsList">
          <div class="loading-state">Loading reviews...</div>
        </div>
      </div>

      ${this.getStyles()}
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private getStyles(): string {
    return `<style>
      .kra-review-page { padding-bottom: 80px; }
      .filters-card { margin: 0 16px 16px; padding: 16px; background: rgba(255,255,255,0.05); border-radius: 12px; }
      .date-filter-row { display: flex; gap: 12px; align-items: flex-end; margin-bottom: 12px; }
      .date-input-group { flex: 1; }
      .date-input-group label { display: block; font-size: 11px; color: rgba(255,255,255,0.6); margin-bottom: 4px; text-transform: uppercase; }
      .filter-row { margin-bottom: 12px; }
      .filter-row:last-child { margin-bottom: 0; }
      .form-input, .form-select { width: 100%; padding: 10px 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: #fff; font-size: 14px; }
      .form-select option { background: #1e293b; color: #fff; }
      .btn { padding: 10px 16px; border-radius: 8px; font-weight: 600; border: none; cursor: pointer; }
      .btn-sm { padding: 8px 12px; font-size: 13px; }
      .btn-primary { background: #4f46e5; color: #fff; }
      .btn-secondary { background: rgba(255,255,255,0.1); color: #fff; }
      .btn-success { background: #059669; color: #fff; }
      .btn-danger { background: #dc2626; color: #fff; }
      .filter-tabs { display: flex; gap: 8px; overflow-x: auto; -webkit-overflow-scrolling: touch; }
      .filter-tabs::-webkit-scrollbar { display: none; }
      .filter-tab { padding: 8px 16px; background: rgba(255,255,255,0.1); border: none; border-radius: 20px; color: rgba(255,255,255,0.7); font-size: 13px; white-space: nowrap; cursor: pointer; }
      .filter-tab.active { background: #4f46e5; color: #fff; }
      .list-container { padding: 0 16px; }
      .kra-card-container { margin-bottom: 12px; }
      .kra-card { background: rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; cursor: pointer; transition: all 0.2s; }
      .kra-card:hover { background: rgba(255,255,255,0.12); }
      .kra-card.expanded { border-radius: 12px 12px 0 0; background: rgba(79,70,229,0.2); border: 1px solid #4f46e5; border-bottom: none; }
      .kra-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
      .employee-info { display: flex; align-items: center; gap: 12px; }
      .employee-avatar { width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #6366f1, #8b5cf6); display: flex; align-items: center; justify-content: center; font-weight: 600; color: #fff; font-size: 14px; }
      .employee-name { font-weight: 600; color: #fff; font-size: 15px; }
      .employee-meta { font-size: 12px; color: rgba(255,255,255,0.6); }
      .expand-icon { color: rgba(255,255,255,0.5); transition: transform 0.3s; }
      .expand-icon.rotated { transform: rotate(180deg); }
      .status-badge { padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }
      .status-badge.pending { background: #fef3c7; color: #92400e; }
      .status-badge.approved { background: #d1fae5; color: #065f46; }
      .status-badge.rejected { background: #fee2e2; color: #991b1b; }
      .kra-title { font-size: 14px; color: #fff; margin-bottom: 12px; }
      .score-row { display: flex; gap: 16px; }
      .score-item { display: flex; flex-direction: column; }
      .score-label { font-size: 10px; color: rgba(255,255,255,0.5); text-transform: uppercase; margin-bottom: 2px; }
      .score-value { font-size: 14px; color: #fbbf24; }
      .kra-inline-detail { display: none; background: rgba(30,41,59,0.98); border: 1px solid #4f46e5; border-top: none; border-radius: 0 0 12px 12px; padding: 16px; }
      .kra-inline-detail.show { display: block; }
      .detail-section { margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.1); }
      .detail-section:last-child { border-bottom: none; margin-bottom: 0; }
      .detail-section-title { font-size: 13px; font-weight: 600; color: #fff; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
      .detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
      .detail-item { display: flex; flex-direction: column; }
      .detail-label { font-size: 11px; color: rgba(255,255,255,0.5); text-transform: uppercase; margin-bottom: 4px; }
      .detail-value { font-size: 14px; color: #fff; }
      .rating-input-group { margin-bottom: 16px; }
      .rating-input-group label { display: block; color: rgba(255,255,255,0.7); font-size: 13px; margin-bottom: 8px; }
      .star-rating { display: flex; gap: 8px; }
      .star-btn { width: 40px; height: 40px; border-radius: 8px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: rgba(255,255,255,0.5); font-size: 18px; cursor: pointer; transition: all 0.2s; }
      .star-btn.selected { background: #fbbf24; color: #fff; border-color: #fbbf24; }
      .star-btn:hover { background: rgba(251,191,36,0.3); }
      .form-textarea { width: 100%; padding: 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: #fff; font-size: 14px; resize: vertical; min-height: 80px; }
      .inline-footer { display: flex; gap: 8px; margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.1); }
      .inline-footer .btn { flex: 1; }
      .loading-state, .empty-state { text-align: center; padding: 40px; color: rgba(255,255,255,0.5); }
    </style>`;
  }

  private updateList(): void {
    const listContainer = document.getElementById('reviewsList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state"><i class="fas fa-spinner fa-spin"></i> Loading reviews...</div>';
      return;
    }

    if (this.reviews.length === 0) {
      const statusLabel = this.filterStatus === 'pending_review' ? 'pending' : this.filterStatus || 'any';
      listContainer.innerHTML = `<div class="empty-state"><i class="fas fa-clipboard-check"></i><p>No ${statusLabel} reviews found</p></div>`;
      return;
    }

    listContainer.innerHTML = this.reviews.map(review => this.renderReviewCard(review)).join('');
    this.attachCardListeners();
  }

  private renderReviewCard(review: KRAReview): string {
    const isExpanded = this.expandedReviewId === review.id;
    const isPending = review.manager_review_status === 'pending_review';

    return `
      <div class="kra-card-container" data-review-id="${review.id}">
        <div class="kra-card ${isExpanded ? 'expanded' : ''}" data-review-id="${review.id}">
          <div class="kra-header">
            <div class="employee-info">
              <div class="employee-avatar">${this.getInitials(review.employee_name)}</div>
              <div>
                <div class="employee-name">${review.employee_name}</div>
                <div class="employee-meta">${review.kra_code || ''} • ${this.formatDate(review.instance_date)}</div>
              </div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="status-badge ${this.getStatusClass(review.manager_review_status)}">${this.getStatusLabel(review.manager_review_status)}</span>
              <i class="fas fa-chevron-down expand-icon ${isExpanded ? 'rotated' : ''}"></i>
            </div>
          </div>
          <div class="kra-title">${review.kra_title || 'KRA'}</div>
          <div class="score-row">
            <div class="score-item">
              <span class="score-label">Self Rating</span>
              <span class="score-value">${review.self_rating ? '★'.repeat(review.self_rating) + ' ' + review.self_rating + '/5' : 'N/A'}</span>
            </div>
            ${review.manager_rating ? `
              <div class="score-item">
                <span class="score-label">Manager Rating</span>
                <span class="score-value">${'★'.repeat(review.manager_rating)} ${review.manager_rating}/5</span>
              </div>
            ` : ''}
          </div>
        </div>
        
        <div class="kra-inline-detail ${isExpanded ? 'show' : ''}" id="detail-${review.id}">
          <div class="detail-section">
            <div class="detail-section-title"><i class="fas fa-info-circle"></i> KRA Details</div>
            <div class="detail-grid">
              <div class="detail-item"><span class="detail-label">Submitted</span><span class="detail-value">${this.formatDate(review.submitted_at)}</span></div>
              <div class="detail-item"><span class="detail-label">Status</span><span class="detail-value">${review.completion_status || 'N/A'}</span></div>
            </div>
            ${review.employee_remarks ? `<div style="margin-top: 12px;"><span class="detail-label">Employee Remarks</span><div style="margin-top: 8px; color: rgba(255,255,255,0.8); font-size: 14px; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px;">${this.escapeHtml(review.employee_remarks)}</div></div>` : ''}
          </div>
          
          ${isPending ? `
            <div class="detail-section">
              <div class="detail-section-title"><i class="fas fa-star"></i> Manager Review</div>
              <div class="rating-input-group">
                <label>Your Rating (1-5 stars)</label>
                <div class="star-rating" id="starRating-${review.id}">
                  ${[1,2,3,4,5].map(n => `<button class="star-btn ${(review.self_rating || 3) >= n ? 'selected' : ''}" data-value="${n}">★</button>`).join('')}
                </div>
                <input type="hidden" id="managerRating-${review.id}" value="${review.self_rating || 3}">
              </div>
              <div class="rating-input-group">
                <label>Comments (optional)</label>
                <textarea id="reviewComments-${review.id}" class="form-textarea" placeholder="Enter review comments..."></textarea>
              </div>
            </div>
            <div class="inline-footer">
              <button class="btn btn-secondary" data-action="collapse" data-id="${review.id}">Close</button>
              <button class="btn btn-danger" data-action="reject" data-id="${review.id}">Reject</button>
              <button class="btn btn-success" data-action="approve" data-id="${review.id}">Approve</button>
            </div>
          ` : `
            ${review.manager_remarks ? `<div class="detail-section"><div class="detail-section-title"><i class="fas fa-comment"></i> Manager Remarks</div><div style="color: rgba(255,255,255,0.8); font-size: 14px; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px;">${this.escapeHtml(review.manager_remarks)}</div></div>` : ''}
            <div class="inline-footer">
              <button class="btn btn-secondary" data-action="collapse" data-id="${review.id}" style="flex: 1;">Close</button>
            </div>
          `}
        </div>
      </div>
    `;
  }

  private attachEventListeners(): void {
    document.getElementById('applyFilter')?.addEventListener('click', () => {
      const fromInput = document.getElementById('dateFrom') as HTMLInputElement;
      const toInput = document.getElementById('dateTo') as HTMLInputElement;
      if (fromInput) this.dateFrom = fromInput.value;
      if (toInput) this.dateTo = toInput.value;
      this.expandedReviewId = null;
      this.loadReviews();
    });
    
    this.container.querySelectorAll('.filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.filterStatus = (tab as HTMLElement).dataset.status || '';
        this.container.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.expandedReviewId = null;
        this.loadReviews();
      });
    });
  }

  private attachCardListeners(): void {
    document.querySelectorAll('.kra-card').forEach(card => {
      card.addEventListener('click', (e) => {
        const target = e.target as HTMLElement;
        if (target.closest('select') || target.closest('input') || target.closest('button') || target.closest('textarea')) return;
        const reviewId = parseInt(card.getAttribute('data-review-id') || '0');
        this.toggleDetail(reviewId);
      });
    });

    document.querySelectorAll('[data-action]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const action = btn.getAttribute('data-action');
        const reviewId = parseInt(btn.getAttribute('data-id') || '0');
        switch (action) {
          case 'approve': await this.submitReview(reviewId, 'approved'); break;
          case 'reject': await this.submitReview(reviewId, 'rejected'); break;
          case 'collapse': this.collapseDetail(); break;
        }
      });
    });

    document.querySelectorAll('.star-rating').forEach(container => {
      const reviewId = container.id.replace('starRating-', '');
      container.querySelectorAll('.star-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const value = parseInt((btn as HTMLElement).dataset.value || '3');
          const hiddenInput = document.getElementById(`managerRating-${reviewId}`) as HTMLInputElement;
          if (hiddenInput) hiddenInput.value = value.toString();
          container.querySelectorAll('.star-btn').forEach((b, i) => {
            b.classList.toggle('selected', i < value);
          });
        });
      });
    });
  }

  private toggleDetail(reviewId: number): void {
    if (this.expandedReviewId === reviewId) {
      this.collapseDetail();
    } else {
      this.expandedReviewId = reviewId;
      this.updateList();
    }
  }

  private collapseDetail(): void {
    this.expandedReviewId = null;
    this.updateList();
  }

  private async submitReview(reviewId: number, action: 'approved' | 'rejected'): Promise<void> {
    const rating = parseInt((document.getElementById(`managerRating-${reviewId}`) as HTMLInputElement)?.value || '3');
    const comments = (document.getElementById(`reviewComments-${reviewId}`) as HTMLTextAreaElement)?.value || '';

    try {
      const endpoint = action === 'approved' ? '/staff/kra/manager-review/approve' : '/staff/kra/manager-review/reject';
      const response = await apiService.post(endpoint, {
        instance_id: reviewId,
        manager_rating: rating,
        manager_remarks: comments
      });

      if (response.success) {
        alert(`KRA ${action === 'approved' ? 'approved' : 'rejected'} successfully`);
        this.expandedReviewId = null;
        this.loadReviews();
      } else {
        alert((response as any).error || 'Failed to submit review');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to submit review');
    }
  }

  private getStatusClass(status: string): string {
    switch (status) {
      case 'pending_review': return 'pending';
      case 'approved': case 'edited_by_manager': return 'approved';
      case 'rejected': return 'rejected';
      default: return 'pending';
    }
  }
  
  private getStatusLabel(status: string): string {
    switch (status) {
      case 'pending_review': return 'Pending';
      case 'approved': return 'Approved';
      case 'edited_by_manager': return 'Edited';
      case 'rejected': return 'Rejected';
      default: return status || 'Pending';
    }
  }

  private getInitials(name: string): string {
    return name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '??';
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  private escapeHtml(str: string): string {
    if (!str) return '';
    return str.replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m] || m);
  }
}
