/**
 * Staff Reimbursement Approvals Page
 * DC Protocol: DC_MOBILE_REIMBURSEMENT_APPROVALS_001
 * Approve/reject reimbursement claims
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface ReimbursementClaim {
  id: number;
  employee_id: number;
  employee_name: string;
  emp_code: string;
  department: string;
  claim_type: string;
  amount: number;
  description: string;
  receipt_url?: string;
  submitted_date: string;
  expense_date: string;
  status: string;
  level1_approved?: boolean;
  level1_remarks?: string;
  level2_approved?: boolean;
  level2_remarks?: string;
}

export class StaffReimbursementApprovalsPage {
  private container: HTMLElement;
  private claims: ReimbursementClaim[] = [];
  private loading: boolean = true;
  private filterStatus: string = 'pending';
  private approvalLevel: 'level1' | 'level2' = 'level1';
  private selectedClaim: ReimbursementClaim | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadClaims();
  }

  private async loadClaims(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      const endpoint = `/staff/reimbursements/approval-queue?level=${this.approvalLevel}&status=${this.filterStatus}`;
      const response = await apiService.get<any>(endpoint);
      console.log('[StaffReimbursementApprovalsPage] API response:', response);

      if (response.success && response.data) {
        this.claims = response.data.claims || response.data || [];
      }
    } catch (error) {
      console.error('[StaffReimbursementApprovalsPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Reimbursement Approvals', showBack: true })}
        
        <div class="approval-level-tabs">
          <button class="level-tab ${this.approvalLevel === 'level1' ? 'active' : ''}" data-level="level1">
            Level 1
          </button>
          <button class="level-tab ${this.approvalLevel === 'level2' ? 'active' : ''}" data-level="level2">
            Level 2
          </button>
        </div>

        <div class="filter-tabs">
          <button class="filter-tab ${this.filterStatus === 'pending' ? 'active' : ''}" data-status="pending">Pending</button>
          <button class="filter-tab ${this.filterStatus === 'approved' ? 'active' : ''}" data-status="approved">Approved</button>
          <button class="filter-tab ${this.filterStatus === 'rejected' ? 'active' : ''}" data-status="rejected">Rejected</button>
        </div>

        <div class="stats-row">
          <div class="stat-card mini pending">
            <span class="stat-value" id="pendingCount">0</span>
            <span class="stat-label">Pending</span>
          </div>
          <div class="stat-card mini">
            <span class="stat-value" id="totalAmount">₹0</span>
            <span class="stat-label">Total Amount</span>
          </div>
        </div>

        <div class="list-container" id="claimsList">
          <div class="loading-state">Loading claims...</div>
        </div>
      </div>

      <div class="modal-overlay" id="approvalModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Review Claim</h4>
            <button class="modal-close" id="closeModal">&times;</button>
          </div>
          <div class="modal-body" id="modalBody"></div>
          <div class="modal-footer" id="modalFooter"></div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    this.container.querySelectorAll('.level-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.approvalLevel = (tab as HTMLElement).dataset.level as 'level1' | 'level2';
        this.container.querySelectorAll('.level-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.loadClaims();
      });
    });

    this.container.querySelectorAll('.filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.filterStatus = (tab as HTMLElement).dataset.status || 'pending';
        this.container.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.loadClaims();
      });
    });

    document.getElementById('closeModal')?.addEventListener('click', () => this.hideModal());
  }

  private updateList(): void {
    const listContainer = document.getElementById('claimsList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading claims...</div>';
      return;
    }

    const pendingEl = document.getElementById('pendingCount');
    const totalAmountEl = document.getElementById('totalAmount');
    const pendingClaims = this.claims.filter(c => c.status === 'pending');
    if (pendingEl) pendingEl.textContent = pendingClaims.length.toString();
    if (totalAmountEl) totalAmountEl.textContent = '₹' + this.claims.reduce((sum, c) => sum + (c.amount || 0), 0).toFixed(0);

    if (this.claims.length === 0) {
      listContainer.innerHTML = `<div class="empty-state">No ${this.filterStatus} claims</div>`;
      return;
    }

    listContainer.innerHTML = this.claims.map(claim => `
      <div class="list-card reimbursement-card">
        <div class="claim-header">
          <div class="employee-info-row">
            <div class="employee-avatar-sm">${this.getInitials(claim.employee_name)}</div>
            <div class="employee-details">
              <div class="employee-name">${claim.employee_name}</div>
              <div class="employee-meta">${claim.emp_code} • ${claim.department || 'N/A'}</div>
            </div>
          </div>
          <span class="status-badge ${claim.status}">${claim.status}</span>
        </div>

        <div class="claim-type-amount">
          <span class="claim-type">${claim.claim_type}</span>
          <span class="claim-amount">₹${claim.amount?.toFixed(2) || 0}</span>
        </div>

        <div class="claim-description">${claim.description}</div>

        <div class="claim-dates">
          <div class="date-item">
            <span class="date-label">Expense Date</span>
            <span class="date-value">${this.formatDate(claim.expense_date)}</span>
          </div>
          <div class="date-item">
            <span class="date-label">Submitted</span>
            <span class="date-value">${this.formatDate(claim.submitted_date)}</span>
          </div>
        </div>

        ${claim.receipt_url ? `
          <a href="${claim.receipt_url}" target="_blank" class="view-receipt-link">View Receipt</a>
        ` : ''}

        ${claim.level1_remarks ? `
          <div class="approval-history">
            <strong>L1:</strong> ${claim.level1_approved ? '✓ Approved' : '✗ Rejected'} - ${claim.level1_remarks}
          </div>
        ` : ''}

        ${this.filterStatus === 'pending' ? `
          <div class="approval-actions">
            <button class="btn btn-success btn-sm approve-btn" data-id="${claim.id}">Approve</button>
            <button class="btn btn-danger btn-sm reject-btn" data-id="${claim.id}">Reject</button>
          </div>
        ` : ''}
      </div>
    `).join('');

    this.attachCardListeners();
  }

  private attachCardListeners(): void {
    this.container.querySelectorAll('.approve-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = parseInt((btn as HTMLElement).dataset.id || '0');
        this.showApprovalModal(id, 'approve');
      });
    });

    this.container.querySelectorAll('.reject-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = parseInt((btn as HTMLElement).dataset.id || '0');
        this.showApprovalModal(id, 'reject');
      });
    });
  }

  private showApprovalModal(id: number, action: 'approve' | 'reject'): void {
    this.selectedClaim = this.claims.find(c => c.id === id) || null;
    if (!this.selectedClaim) return;

    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');
    const modal = document.getElementById('approvalModal');

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="modal-summary">
          <p><strong>${this.selectedClaim.employee_name}</strong></p>
          <p>${this.selectedClaim.claim_type}: ₹${this.selectedClaim.amount}</p>
          <p>${this.selectedClaim.description}</p>
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
    if (!this.selectedClaim) return;

    const remarks = (document.getElementById('approvalRemarks') as HTMLTextAreaElement)?.value || '';

    if (action === 'reject' && !remarks.trim()) {
      alert('Remarks are required for rejection');
      return;
    }

    try {
      const endpoint = action === 'approve' 
        ? `/staff/reimbursements/claims/${this.selectedClaim.id}/${this.approvalLevel === 'level1' ? 'manager-approve' : 'finance-approve'}`
        : `/staff/reimbursements/claims/${this.selectedClaim.id}/reject`;
      const response = await apiService.post(endpoint, { remarks });

      if (response.success) {
        alert(`Claim ${action}d successfully`);
        this.hideModal();
        this.loadClaims();
      } else {
        alert(response.error || `Failed to ${action} claim`);
      }
    } catch (error: any) {
      alert(error.message || `Failed to ${action} claim`);
    }
  }

  private hideModal(): void {
    const modal = document.getElementById('approvalModal');
    if (modal) modal.style.display = 'none';
    this.selectedClaim = null;
  }

  private getInitials(name: string): string {
    return name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '??';
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  }
}
