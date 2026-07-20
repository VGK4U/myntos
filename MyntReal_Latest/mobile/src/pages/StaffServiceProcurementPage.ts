/**
 * Staff Service Procurement Page
 * DC Protocol: DC_MOBILE_SERVICE_PROCUREMENT_001
 * View and manage spare parts procurement
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface ProcurementItem {
  id: number;
  ticket_id: number;
  ticket_number: string;
  part_name: string;
  part_code: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  vendor_name: string;
  status: string;
  requested_date: string;
  expected_date?: string;
  received_date?: string;
  requested_by: string;
}

export class StaffServiceProcurementPage {
  private container: HTMLElement;
  private items: ProcurementItem[] = [];
  private loading: boolean = true;
  private filterStatus: string = '';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadItems();
  }

  private async loadItems(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      let endpoint = '/tickets/service/procurement-queue';
      if (this.filterStatus) endpoint += `?status=${this.filterStatus}`;

      const response = await apiService.get<any>(endpoint);
      console.log('[StaffServiceProcurementPage] API response:', response);

      if (response.success && response.data) {
        this.items = response.data.items || response.data || [];
      }
    } catch (error) {
      console.error('[StaffServiceProcurementPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Procurement', showBack: true })}
        
        <div class="filter-row">
          <select id="statusFilter" class="filter-select full-width">
            <option value="">All Status</option>
            <option value="requested">Requested</option>
            <option value="ordered">Ordered</option>
            <option value="shipped">Shipped</option>
            <option value="received">Received</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        <div class="stats-row">
          <div class="stat-card mini">
            <span class="stat-value" id="totalCount">0</span>
            <span class="stat-label">Total</span>
          </div>
          <div class="stat-card mini pending">
            <span class="stat-value" id="pendingCount">0</span>
            <span class="stat-label">Pending</span>
          </div>
          <div class="stat-card mini">
            <span class="stat-value" id="totalValue">₹0</span>
            <span class="stat-label">Value</span>
          </div>
        </div>

        <div class="list-container" id="itemsList">
          <div class="loading-state">Loading procurement items...</div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    document.getElementById('statusFilter')?.addEventListener('change', (e) => {
      this.filterStatus = (e.target as HTMLSelectElement).value;
      this.loadItems();
    });
  }

  private updateList(): void {
    const listContainer = document.getElementById('itemsList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading procurement items...</div>';
      return;
    }

    const totalEl = document.getElementById('totalCount');
    const pendingEl = document.getElementById('pendingCount');
    const valueEl = document.getElementById('totalValue');
    if (totalEl) totalEl.textContent = this.items.length.toString();
    if (pendingEl) pendingEl.textContent = this.items.filter(i => !['received', 'cancelled'].includes(i.status)).length.toString();
    if (valueEl) valueEl.textContent = '₹' + this.items.reduce((sum, i) => sum + (i.total_price || 0), 0).toFixed(0);

    if (this.items.length === 0) {
      listContainer.innerHTML = '<div class="empty-state">No procurement items found</div>';
      return;
    }

    listContainer.innerHTML = this.items.map(item => `
      <div class="list-card procurement-card">
        <div class="procurement-header">
          <div class="part-info">
            <div class="part-name">${item.part_name}</div>
            <div class="part-code">${item.part_code}</div>
          </div>
          <span class="status-badge ${item.status}">${item.status}</span>
        </div>

        <div class="ticket-ref">
          Ticket: ${item.ticket_number}
        </div>

        <div class="procurement-details">
          <div class="detail-row">
            <span class="detail-label">Quantity</span>
            <span class="detail-value">${item.quantity}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Unit Price</span>
            <span class="detail-value">₹${item.unit_price?.toFixed(2) || 0}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Total</span>
            <span class="detail-value highlight">₹${item.total_price?.toFixed(2) || 0}</span>
          </div>
        </div>

        <div class="vendor-info">
          <strong>Vendor:</strong> ${item.vendor_name}
        </div>

        <div class="procurement-dates">
          <div class="date-item">
            <span class="date-label">Requested</span>
            <span class="date-value">${this.formatDate(item.requested_date)}</span>
          </div>
          ${item.expected_date ? `
            <div class="date-item">
              <span class="date-label">Expected</span>
              <span class="date-value">${this.formatDate(item.expected_date)}</span>
            </div>
          ` : ''}
          ${item.received_date ? `
            <div class="date-item">
              <span class="date-label">Received</span>
              <span class="date-value">${this.formatDate(item.received_date)}</span>
            </div>
          ` : ''}
        </div>

        <div class="requested-by">
          By: ${item.requested_by}
        </div>
      </div>
    `).join('');
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  }
}
