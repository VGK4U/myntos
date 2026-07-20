/**
 * Staff KYC Approvals Page
 * DC Protocol: DC_MOBILE_KYC_APPROVALS_001
 * View and approve/reject KYC submissions
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface KYCSubmission {
  id: number;
  employee_id: number;
  employee_name: string;
  emp_code: string;
  department: string;
  document_type: string;
  document_number: string;
  document_url?: string;
  status: string;
  submitted_date: string;
  remarks?: string;
}

export class StaffKYCApprovalsPage {
  private container: HTMLElement;
  private submissions: KYCSubmission[] = [];
  private loading: boolean = true;
  private filterStatus: string = 'pending';
  private selectedItem: KYCSubmission | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadSubmissions();
  }

  private async loadSubmissions(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      const response = await apiService.get<any>(`/staff/kyc/pending?status=${this.filterStatus}`);
      console.log('[StaffKYCApprovalsPage] API response:', response);

      if (response.success && response.data) {
        this.submissions = response.data.submissions || response.data || [];
      }
    } catch (error) {
      console.error('[StaffKYCApprovalsPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'KYC Approvals', showBack: true })}
        
        <div class="filter-tabs">
          <button class="filter-tab ${this.filterStatus === 'pending' ? 'active' : ''}" data-status="pending">
            Pending
          </button>
          <button class="filter-tab ${this.filterStatus === 'approved' ? 'active' : ''}" data-status="approved">
            Approved
          </button>
          <button class="filter-tab ${this.filterStatus === 'rejected' ? 'active' : ''}" data-status="rejected">
            Rejected
          </button>
        </div>

        <div class="stats-row">
          <div class="stat-card mini pending">
            <span class="stat-value" id="pendingCount">0</span>
            <span class="stat-label">Pending</span>
          </div>
          <div class="stat-card mini success">
            <span class="stat-value" id="approvedCount">0</span>
            <span class="stat-label">Approved</span>
          </div>
          <div class="stat-card mini danger">
            <span class="stat-value" id="rejectedCount">0</span>
            <span class="stat-label">Rejected</span>
          </div>
        </div>

        <div class="list-container" id="submissionsList">
          <div class="loading-state">Loading submissions...</div>
        </div>
      </div>

      <!-- Approval Modal -->
      <div class="modal-overlay" id="approvalModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>KYC Review</h4>
            <button class="modal-close" id="closeModal">&times;</button>
          </div>
          <div class="modal-body" id="modalBody">
          </div>
          <div class="modal-footer" id="modalFooter">
          </div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    this.container.querySelectorAll('.filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.filterStatus = (tab as HTMLElement).dataset.status || 'pending';
        this.container.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.loadSubmissions();
      });
    });

    document.getElementById('closeModal')?.addEventListener('click', () => this.hideModal());
  }

  private updateList(): void {
    const listContainer = document.getElementById('submissionsList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading submissions...</div>';
      return;
    }

    const pending = this.submissions.filter(s => s.status === 'pending').length;
    const approved = this.submissions.filter(s => s.status === 'approved').length;
    const rejected = this.submissions.filter(s => s.status === 'rejected').length;

    const pendingEl = document.getElementById('pendingCount');
    const approvedEl = document.getElementById('approvedCount');
    const rejectedEl = document.getElementById('rejectedCount');
    if (pendingEl) pendingEl.textContent = pending.toString();
    if (approvedEl) approvedEl.textContent = approved.toString();
    if (rejectedEl) rejectedEl.textContent = rejected.toString();

    if (this.submissions.length === 0) {
      listContainer.innerHTML = `<div class="empty-state">No ${this.filterStatus} KYC submissions</div>`;
      return;
    }

    listContainer.innerHTML = this.submissions.map(sub => `
      <div class="list-card approval-card" data-id="${sub.id}">
        <div class="approval-header">
          <div class="approval-employee">
            <div class="employee-name">${sub.employee_name}</div>
            <div class="employee-code">${sub.emp_code} • ${sub.department || 'N/A'}</div>
          </div>
          <span class="status-badge ${sub.status}">${sub.status}</span>
        </div>
        <div class="approval-details">
          <div class="detail-row">
            <span class="detail-label">Document Type</span>
            <span class="detail-value">${sub.document_type}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Document Number</span>
            <span class="detail-value">${sub.document_number}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Submitted</span>
            <span class="detail-value">${this.formatDate(sub.submitted_date)}</span>
          </div>
        </div>
        ${this.filterStatus === 'pending' ? `
          <div class="approval-actions">
            <button class="btn btn-success btn-sm approve-btn" data-id="${sub.id}">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              Approve
            </button>
            <button class="btn btn-danger btn-sm reject-btn" data-id="${sub.id}">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
              Reject
            </button>
          </div>
        ` : ''}
      </div>
    `).join('');

    this.container.querySelectorAll('.approve-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = parseInt((btn as HTMLElement).dataset.id || '0');
        this.showApprovalModal(id, 'approve');
      });
    });

    this.container.querySelectorAll('.reject-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = parseInt((btn as HTMLElement).dataset.id || '0');
        this.showApprovalModal(id, 'reject');
      });
    });
  }

  private showApprovalModal(id: number, action: 'approve' | 'reject'): void {
    this.selectedItem = this.submissions.find(s => s.id === id) || null;
    if (!this.selectedItem) return;

    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');
    const modal = document.getElementById('approvalModal');

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="modal-info">
          <p><strong>Employee:</strong> ${this.selectedItem.employee_name}</p>
          <p><strong>Document:</strong> ${this.selectedItem.document_type}</p>
          <p><strong>Number:</strong> ${this.selectedItem.document_number}</p>
        </div>
        <div class="form-group">
          <label>Remarks ${action === 'reject' ? '(Required)' : '(Optional)'}</label>
          <textarea id="approvalRemarks" class="form-textarea" rows="3" placeholder="Enter remarks..."></textarea>
        </div>
      `;
    }

    if (modalFooter) {
      modalFooter.innerHTML = `
        <button class="btn btn-secondary" id="cancelAction">Cancel</button>
        <button class="btn ${action === 'approve' ? 'btn-success' : 'btn-danger'}" id="confirmAction">
          ${action === 'approve' ? 'Approve' : 'Reject'}
        </button>
      `;

      document.getElementById('cancelAction')?.addEventListener('click', () => this.hideModal());
      document.getElementById('confirmAction')?.addEventListener('click', () => this.processAction(action));
    }

    if (modal) modal.style.display = 'flex';
  }

  private async processAction(action: 'approve' | 'reject'): Promise<void> {
    if (!this.selectedItem) return;

    const remarks = (document.getElementById('approvalRemarks') as HTMLTextAreaElement)?.value || '';

    if (action === 'reject' && !remarks.trim()) {
      alert('Remarks are required for rejection');
      return;
    }

    try {
      const response = await apiService.post(`/staff/kyc/${this.selectedItem.id}/${action}`, {
        remarks
      });

      if (response.success) {
        alert(`KYC ${action === 'approve' ? 'approved' : 'rejected'} successfully`);
        this.hideModal();
        this.loadSubmissions();
      } else {
        alert(response.error || `Failed to ${action} KYC`);
      }
    } catch (error: any) {
      alert(error.message || `Failed to ${action} KYC`);
    }
  }

  private hideModal(): void {
    const modal = document.getElementById('approvalModal');
    if (modal) modal.style.display = 'none';
    this.selectedItem = null;
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  }
}
