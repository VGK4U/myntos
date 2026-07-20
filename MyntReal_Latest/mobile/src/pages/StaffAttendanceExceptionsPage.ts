/**
 * Staff Attendance Exceptions Page
 * DC Protocol: DC_MOBILE_ATTENDANCE_EXCEPTIONS_001
 * Approve/reject attendance exception requests
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface ExceptionRequest {
  id: number;
  employee_id: number;
  employee_name: string;
  emp_code: string;
  department: string;
  date: string;
  exception_type: string;
  original_clock_in?: string;
  original_clock_out?: string;
  requested_clock_in?: string;
  requested_clock_out?: string;
  reason: string;
  status: string;
  submitted_date: string;
}

export class StaffAttendanceExceptionsPage {
  private container: HTMLElement;
  private requests: ExceptionRequest[] = [];
  private loading: boolean = true;
  private filterStatus: string = '';
  private selectedRequest: ExceptionRequest | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadRequests();
  }

  private async loadRequests(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      let endpoint = '/staff/attendance-sheet/exceptions';
      if (this.filterStatus) endpoint += `?status=${this.filterStatus}`;
      const response = await apiService.get<any>(endpoint);
      console.log('[StaffAttendanceExceptionsPage] API response:', response);

      if (response.success && response.data) {
        this.requests = response.data.exceptions || response.data || [];
      }
    } catch (error) {
      console.error('[StaffAttendanceExceptionsPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Exception Approvals', showBack: true })}
        
        <div class="filter-tabs">
          <button class="filter-tab ${this.filterStatus === '' ? 'active' : ''}" data-status="">
            All
          </button>
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
        </div>

        <div class="list-container" id="requestsList">
          <div class="loading-state">Loading exceptions...</div>
        </div>
      </div>

      <!-- Approval Modal -->
      <div class="modal-overlay" id="approvalModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Exception Review</h4>
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
    this.container.querySelectorAll('.filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.filterStatus = (tab as HTMLElement).dataset.status || 'pending';
        this.container.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.loadRequests();
      });
    });

    document.getElementById('closeModal')?.addEventListener('click', () => this.hideModal());
  }

  private updateList(): void {
    const listContainer = document.getElementById('requestsList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading exceptions...</div>';
      return;
    }

    const pendingEl = document.getElementById('pendingCount');
    if (pendingEl) pendingEl.textContent = this.requests.filter(r => r.status === 'pending').length.toString();

    if (this.requests.length === 0) {
      listContainer.innerHTML = `<div class="empty-state">No ${this.filterStatus} exceptions</div>`;
      return;
    }

    listContainer.innerHTML = this.requests.map(req => `
      <div class="list-card exception-card">
        <div class="exception-header">
          <div class="employee-info-row">
            <div class="employee-avatar-sm">${this.getInitials(req.employee_name)}</div>
            <div class="employee-details">
              <div class="employee-name">${req.employee_name}</div>
              <div class="employee-meta">${req.emp_code} • ${req.department || 'N/A'}</div>
            </div>
          </div>
          <span class="status-badge ${req.status}">${req.status}</span>
        </div>

        <div class="exception-type-badge">${req.exception_type?.replace('_', ' ') || 'Exception'}</div>

        <div class="exception-details">
          <div class="detail-row">
            <span class="detail-label">Date</span>
            <span class="detail-value">${this.formatDate(req.date)}</span>
          </div>
          ${req.original_clock_in ? `
            <div class="detail-row">
              <span class="detail-label">Original In</span>
              <span class="detail-value">${req.original_clock_in}</span>
            </div>
          ` : ''}
          ${req.requested_clock_in ? `
            <div class="detail-row">
              <span class="detail-label">Requested In</span>
              <span class="detail-value highlight">${req.requested_clock_in}</span>
            </div>
          ` : ''}
          ${req.original_clock_out ? `
            <div class="detail-row">
              <span class="detail-label">Original Out</span>
              <span class="detail-value">${req.original_clock_out}</span>
            </div>
          ` : ''}
          ${req.requested_clock_out ? `
            <div class="detail-row">
              <span class="detail-label">Requested Out</span>
              <span class="detail-value highlight">${req.requested_clock_out}</span>
            </div>
          ` : ''}
        </div>

        <div class="exception-reason">
          <strong>Reason:</strong> ${req.reason}
        </div>

        <div class="exception-submitted">
          Submitted: ${this.formatDate(req.submitted_date)}
        </div>

        ${this.filterStatus === 'pending' ? `
          <div class="approval-actions">
            <button class="btn btn-success btn-sm approve-btn" data-id="${req.id}">Approve</button>
            <button class="btn btn-danger btn-sm reject-btn" data-id="${req.id}">Reject</button>
          </div>
        ` : ''}
      </div>
    `).join('');

    this.attachCardListeners();
  }

  private attachCardListeners(): void {
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
    this.selectedRequest = this.requests.find(r => r.id === id) || null;
    if (!this.selectedRequest) return;

    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');
    const modal = document.getElementById('approvalModal');

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="modal-summary">
          <p><strong>${this.selectedRequest.employee_name}</strong></p>
          <p>${this.selectedRequest.exception_type?.replace('_', ' ')} for ${this.formatDate(this.selectedRequest.date)}</p>
          <p><strong>Reason:</strong> ${this.selectedRequest.reason}</p>
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
    if (!this.selectedRequest) return;

    const remarks = (document.getElementById('approvalRemarks') as HTMLTextAreaElement)?.value || '';

    if (action === 'reject' && !remarks.trim()) {
      alert('Remarks are required for rejection');
      return;
    }

    try {
      const response = await apiService.post(`/staff/attendance-sheet/exceptions/${this.selectedRequest.id}/${action}`, {
        remarks
      });

      if (response.success) {
        alert(`Exception ${action === 'approve' ? 'approved' : 'rejected'} successfully`);
        this.hideModal();
        this.loadRequests();
      } else {
        alert(response.error || `Failed to ${action}`);
      }
    } catch (error: any) {
      alert(error.message || `Failed to ${action}`);
    }
  }

  private hideModal(): void {
    const modal = document.getElementById('approvalModal');
    if (modal) modal.style.display = 'none';
    this.selectedRequest = null;
  }

  private getInitials(name: string): string {
    return name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '??';
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
