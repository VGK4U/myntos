/**
 * Staff Service Procurement Queue Page
 * DC Protocol: DC_MOBILE_PROCUREMENT_QUEUE_001
 * Manage procurement approval queue
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface ProcurementRequest {
  id: number;
  ticket_id: number;
  ticket_number: string;
  part_name: string;
  part_code: string;
  quantity: number;
  estimated_cost: number;
  urgency: string;
  justification: string;
  requested_by: string;
  requested_date: string;
  status: string;
}

export class StaffServiceProcurementQueuePage {
  private container: HTMLElement;
  private requests: ProcurementRequest[] = [];
  private loading: boolean = true;
  private filterUrgency: string = '';
  private selectedRequest: ProcurementRequest | null = null;

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
      let endpoint = '/tickets/service/procurement-queue';
      if (this.filterUrgency) endpoint += `?urgency=${this.filterUrgency}`;

      const response = await apiService.get<any>(endpoint);
      console.log('[StaffServiceProcurementQueuePage] API response:', response);

      if (response.success && response.data) {
        this.requests = response.data.requests || response.data || [];
      }
    } catch (error) {
      console.error('[StaffServiceProcurementQueuePage] Failed to load:', error);
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Procurement Queue', showBack: true })}
        
        <div class="filter-row">
          <select id="urgencyFilter" class="filter-select full-width">
            <option value="">All Urgency</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="normal">Normal</option>
            <option value="low">Low</option>
          </select>
        </div>

        <div class="stats-row">
          <div class="stat-card mini danger">
            <span class="stat-value" id="criticalCount">0</span>
            <span class="stat-label">Critical</span>
          </div>
          <div class="stat-card mini warning">
            <span class="stat-value" id="highCount">0</span>
            <span class="stat-label">High</span>
          </div>
          <div class="stat-card mini">
            <span class="stat-value" id="totalCount">0</span>
            <span class="stat-label">Total</span>
          </div>
        </div>

        <div class="list-container" id="requestsList">
          <div class="loading-state">Loading queue...</div>
        </div>
      </div>

      <div class="modal-overlay" id="approvalModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Procurement Decision</h4>
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
    document.getElementById('urgencyFilter')?.addEventListener('change', (e) => {
      this.filterUrgency = (e.target as HTMLSelectElement).value;
      this.loadRequests();
    });

    document.getElementById('closeModal')?.addEventListener('click', () => this.hideModal());
  }

  private updateList(): void {
    const listContainer = document.getElementById('requestsList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading queue...</div>';
      return;
    }

    const criticalEl = document.getElementById('criticalCount');
    const highEl = document.getElementById('highCount');
    const totalEl = document.getElementById('totalCount');
    if (criticalEl) criticalEl.textContent = this.requests.filter(r => r.urgency === 'critical').length.toString();
    if (highEl) highEl.textContent = this.requests.filter(r => r.urgency === 'high').length.toString();
    if (totalEl) totalEl.textContent = this.requests.length.toString();

    if (this.requests.length === 0) {
      listContainer.innerHTML = '<div class="empty-state">No pending procurement requests</div>';
      return;
    }

    listContainer.innerHTML = this.requests.map(req => `
      <div class="list-card queue-card">
        <div class="queue-header">
          <div class="part-info">
            <div class="part-name">${req.part_name}</div>
            <div class="part-code">${req.part_code}</div>
          </div>
          <span class="urgency-badge ${req.urgency}">${req.urgency}</span>
        </div>

        <div class="ticket-ref">Ticket: ${req.ticket_number}</div>

        <div class="queue-details">
          <div class="detail-row">
            <span class="detail-label">Quantity</span>
            <span class="detail-value">${req.quantity}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Est. Cost</span>
            <span class="detail-value">₹${req.estimated_cost?.toFixed(2) || 0}</span>
          </div>
        </div>

        <div class="justification">${req.justification}</div>

        <div class="queue-meta">
          <span>By: ${req.requested_by}</span>
          <span>${this.formatDate(req.requested_date)}</span>
        </div>

        <div class="approval-actions">
          <button class="btn btn-success btn-sm approve-btn" data-id="${req.id}">Approve</button>
          <button class="btn btn-danger btn-sm reject-btn" data-id="${req.id}">Reject</button>
        </div>
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
    this.selectedRequest = this.requests.find(r => r.id === id) || null;
    if (!this.selectedRequest) return;

    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');
    const modal = document.getElementById('approvalModal');

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="modal-summary">
          <p><strong>${this.selectedRequest.part_name}</strong> x ${this.selectedRequest.quantity}</p>
          <p>Est. Cost: ₹${this.selectedRequest.estimated_cost}</p>
        </div>
        ${action === 'approve' ? `
          <div class="form-group">
            <label>Vendor</label>
            <input type="text" id="vendorName" class="form-input" placeholder="Enter vendor name">
          </div>
          <div class="form-group">
            <label>Approved Amount</label>
            <input type="number" id="approvedAmount" class="form-input" value="${this.selectedRequest.estimated_cost}">
          </div>
        ` : ''}
        <div class="form-group">
          <label>Notes ${action === 'reject' ? '(Required)' : ''}</label>
          <textarea id="approvalNotes" class="form-textarea" rows="3" placeholder="Enter notes..."></textarea>
        </div>
      `;
    }

    if (modalFooter) {
      modalFooter.innerHTML = `
        <button class="btn btn-secondary" id="cancelAction">Cancel</button>
        <button class="btn ${action === 'approve' ? 'btn-success' : 'btn-danger'}" id="confirmAction">${action === 'approve' ? 'Approve' : 'Reject'}</button>
      `;

      document.getElementById('cancelAction')?.addEventListener('click', () => this.hideModal());
      document.getElementById('confirmAction')?.addEventListener('click', () => this.processAction(action));
    }

    if (modal) modal.style.display = 'flex';
  }

  private async processAction(action: 'approve' | 'reject'): Promise<void> {
    if (!this.selectedRequest) return;

    const notes = (document.getElementById('approvalNotes') as HTMLTextAreaElement)?.value || '';
    if (action === 'reject' && !notes.trim()) {
      alert('Notes are required for rejection');
      return;
    }

    const payload: any = { notes };
    if (action === 'approve') {
      payload.vendor_name = (document.getElementById('vendorName') as HTMLInputElement)?.value || '';
      payload.approved_amount = parseFloat((document.getElementById('approvedAmount') as HTMLInputElement)?.value || '0');
    }

    try {
      const response = await apiService.post(`/tickets/service/procurement/${this.selectedRequest.id}/${action}`, payload);

      if (response.success) {
        alert(`Request ${action}d successfully`);
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

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
  }
}
