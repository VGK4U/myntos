/**
 * Staff Leave Approvals Page
 * DC Protocol: DC_MOBILE_LEAVE_APPROVALS_001
 * Manager/HR leave approval workflow with full data display
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface LeaveRequest {
  id: number;
  employee_id: number;
  employee_name: string;
  emp_code: string;
  department: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  days: number;
  reason: string;
  status: string;
  applied_date: string;
  manager_approved?: boolean;
  manager_remarks?: string;
  hr_approved?: boolean;
  hr_remarks?: string;
  contact_number?: string;
  attachment_url?: string;
}

const LEAVE_TYPE_COLORS: Record<string, string> = {
  casual: '#10b981',
  sick: '#ef4444',
  privilege: '#3b82f6',
  unpaid: '#6b7280',
  maternity: '#ec4899',
  paternity: '#8b5cf6'
};

export class StaffLeaveApprovalsPage {
  private container: HTMLElement;
  private requests: LeaveRequest[] = [];
  private loading: boolean = true;
  private approvalType: 'manager' | 'hr' = 'manager';
  private filterStatus: string = 'pending';
  private filterLeaveType: string = '';
  private selectedRequest: LeaveRequest | null = null;

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
      // DC Protocol: Match web's endpoint exactly
      const endpoint = this.approvalType === 'manager' 
        ? '/staff/leaves/pending-approvals/manager'
        : '/staff/leaves/pending-approvals/hr';
      
      const response = await apiService.get<any>(endpoint);
      console.log('[StaffLeaveApprovalsPage] API response:', response);

      if (response.success && response.data) {
        this.requests = response.data.requests || response.data || [];
      }
    } catch (error) {
      console.error('[StaffLeaveApprovalsPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Leave Approvals', showBack: true })}
        
        <div class="approval-type-tabs">
          <button class="type-tab ${this.approvalType === 'manager' ? 'active' : ''}" data-type="manager">
            Manager Queue
          </button>
          <button class="type-tab ${this.approvalType === 'hr' ? 'active' : ''}" data-type="hr">
            HR Queue
          </button>
        </div>

        <div class="filter-row">
          <select id="leaveTypeFilter" class="filter-select">
            <option value="">All Types</option>
            <option value="casual">Casual</option>
            <option value="sick">Sick</option>
            <option value="privilege">Privilege</option>
            <option value="unpaid">Unpaid</option>
            <option value="maternity">Maternity</option>
            <option value="paternity">Paternity</option>
          </select>
        </div>

        <div class="stats-row">
          <div class="stat-card mini pending">
            <span class="stat-value" id="pendingCount">0</span>
            <span class="stat-label">Pending</span>
          </div>
          <div class="stat-card mini">
            <span class="stat-value" id="totalDays">0</span>
            <span class="stat-label">Total Days</span>
          </div>
        </div>

        <div class="list-container" id="requestsList">
          <div class="loading-state">Loading requests...</div>
        </div>
      </div>

      <!-- Approval Modal -->
      <div class="modal-overlay" id="approvalModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Leave Request Details</h4>
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
    this.container.querySelectorAll('.type-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.approvalType = (tab as HTMLElement).dataset.type as 'manager' | 'hr';
        this.container.querySelectorAll('.type-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.loadRequests();
      });
    });

    document.getElementById('leaveTypeFilter')?.addEventListener('change', (e) => {
      this.filterLeaveType = (e.target as HTMLSelectElement).value;
      this.updateList();
    });

    document.getElementById('closeModal')?.addEventListener('click', () => this.hideModal());
  }

  private updateList(): void {
    const listContainer = document.getElementById('requestsList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading requests...</div>';
      return;
    }

    let filtered = this.requests;
    if (this.filterLeaveType) {
      filtered = filtered.filter(r => r.leave_type === this.filterLeaveType);
    }

    const pendingEl = document.getElementById('pendingCount');
    const totalDaysEl = document.getElementById('totalDays');
    if (pendingEl) pendingEl.textContent = filtered.length.toString();
    if (totalDaysEl) totalDaysEl.textContent = filtered.reduce((sum, r) => sum + (r.days || 0), 0).toString();

    if (filtered.length === 0) {
      listContainer.innerHTML = '<div class="empty-state">No pending leave requests</div>';
      return;
    }

    listContainer.innerHTML = filtered.map(req => `
      <div class="list-card leave-approval-card" data-id="${req.id}">
        <div class="leave-header">
          <div class="leave-type-badge" style="background: ${LEAVE_TYPE_COLORS[req.leave_type] || '#6b7280'}">
            ${req.leave_type?.toUpperCase() || 'LEAVE'}
          </div>
          <span class="leave-days">${req.days} day${req.days !== 1 ? 's' : ''}</span>
        </div>
        
        <div class="employee-info-row">
          <div class="employee-avatar-sm">${this.getInitials(req.employee_name)}</div>
          <div class="employee-details">
            <div class="employee-name">${req.employee_name}</div>
            <div class="employee-meta">${req.emp_code} • ${req.department || 'N/A'}</div>
          </div>
        </div>

        <div class="leave-dates">
          <div class="date-range">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
              <line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/>
              <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
            <span>${this.formatDate(req.start_date)} - ${this.formatDate(req.end_date)}</span>
          </div>
        </div>

        <div class="leave-reason">
          <strong>Reason:</strong> ${req.reason || 'Not specified'}
        </div>

        ${req.contact_number ? `
          <div class="leave-contact">
            <strong>Contact:</strong> ${req.contact_number}
          </div>
        ` : ''}

        ${req.manager_remarks ? `
          <div class="manager-remarks">
            <strong>Manager Remarks:</strong> ${req.manager_remarks}
          </div>
        ` : ''}

        <div class="leave-applied">
          Applied: ${this.formatDate(req.applied_date)}
        </div>

        <div class="approval-actions">
          <button class="btn btn-success btn-sm approve-btn" data-id="${req.id}">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            Approve
          </button>
          <button class="btn btn-danger btn-sm reject-btn" data-id="${req.id}">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
            Reject
          </button>
          <button class="btn btn-secondary btn-sm view-btn" data-id="${req.id}">
            View
          </button>
        </div>
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

    this.container.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = parseInt((btn as HTMLElement).dataset.id || '0');
        this.showDetailsModal(id);
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
          <p><strong>${this.selectedRequest.employee_name}</strong> (${this.selectedRequest.emp_code})</p>
          <p>${this.selectedRequest.leave_type?.toUpperCase()} Leave: ${this.selectedRequest.days} day(s)</p>
          <p>${this.formatDate(this.selectedRequest.start_date)} - ${this.formatDate(this.selectedRequest.end_date)}</p>
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
          Confirm ${action === 'approve' ? 'Approval' : 'Rejection'}
        </button>
      `;

      document.getElementById('cancelAction')?.addEventListener('click', () => this.hideModal());
      document.getElementById('confirmAction')?.addEventListener('click', () => this.processAction(action));
    }

    if (modal) modal.style.display = 'flex';
  }

  private showDetailsModal(id: number): void {
    const request = this.requests.find(r => r.id === id);
    if (!request) return;

    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');
    const modal = document.getElementById('approvalModal');

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="detail-section">
          <h5>Employee Information</h5>
          <div class="detail-grid">
            <div class="detail-item"><span>Name</span><strong>${request.employee_name}</strong></div>
            <div class="detail-item"><span>Emp Code</span><strong>${request.emp_code}</strong></div>
            <div class="detail-item"><span>Department</span><strong>${request.department || 'N/A'}</strong></div>
          </div>
        </div>
        <div class="detail-section">
          <h5>Leave Details</h5>
          <div class="detail-grid">
            <div class="detail-item"><span>Type</span><strong>${request.leave_type}</strong></div>
            <div class="detail-item"><span>Days</span><strong>${request.days}</strong></div>
            <div class="detail-item"><span>From</span><strong>${this.formatDate(request.start_date)}</strong></div>
            <div class="detail-item"><span>To</span><strong>${this.formatDate(request.end_date)}</strong></div>
            <div class="detail-item"><span>Applied</span><strong>${this.formatDate(request.applied_date)}</strong></div>
            ${request.contact_number ? `<div class="detail-item"><span>Contact</span><strong>${request.contact_number}</strong></div>` : ''}
          </div>
        </div>
        <div class="detail-section">
          <h5>Reason</h5>
          <p>${request.reason || 'Not specified'}</p>
        </div>
        ${request.attachment_url ? `
          <div class="detail-section">
            <h5>Attachment</h5>
            <a href="${request.attachment_url}" target="_blank" class="btn btn-link">View Attachment</a>
          </div>
        ` : ''}
      `;
    }

    if (modalFooter) {
      modalFooter.innerHTML = `<button class="btn btn-secondary" id="closeDetails">Close</button>`;
      document.getElementById('closeDetails')?.addEventListener('click', () => this.hideModal());
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
      // DC Protocol: Match web/backend endpoint exactly
      const endpoint = this.approvalType === 'manager'
        ? `/staff/leaves/approve/manager/${this.selectedRequest.id}`
        : `/staff/leaves/approve/hr/${this.selectedRequest.id}`;

      const response = await apiService.post(endpoint, {
        action,
        remarks
      });

      if (response.success) {
        alert(`Leave request ${action === 'approve' ? 'approved' : 'rejected'} successfully`);
        this.hideModal();
        this.loadRequests();
      } else {
        alert(response.error || `Failed to ${action} leave request`);
      }
    } catch (error: any) {
      alert(error.message || `Failed to ${action} leave request`);
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
