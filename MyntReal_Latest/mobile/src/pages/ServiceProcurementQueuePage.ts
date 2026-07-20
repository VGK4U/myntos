/**
 * Service Procurement Queue Page
 * DC Protocol: DC_MOBILE_SERVICE_PROC_QUEUE_001
 * Admin view of all procurement requests across service centers
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface ProcurementItem {
  id: number;
  ticket_id: number;
  ticket_number: string;
  spare_name: string;
  part_number?: string;
  quantity: number;
  status: string;
  partner_name: string;
  requested_by: string;
  requested_at: string;
  acknowledged_at?: string;
  released_at?: string;
  unit_price?: number;
  total_price?: number;
}

export class ServiceProcurementQueuePage {
  private container: HTMLElement;
  private items: ProcurementItem[] = [];
  private filteredItems: ProcurementItem[] = [];
  private loading: boolean = true;
  private filterStatus: string = 'pending';
  private searchQuery: string = '';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadQueue();
  }

  private async loadQueue(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      const response = await apiService.get<any>('/tickets/service/procurement-queue');
      if (response.success && response.data) {
        this.items = response.data.spares || response.data || [];
      }
    } catch (error) {
      console.error('[ServiceProcurementQueuePage] Failed to load:', error);
    }

    this.loading = false;
    this.applyFilters();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Procurement Queue', showBack: true })}
        
        <div class="search-bar">
          <input type="text" id="searchInput" class="search-input" placeholder="Search by spare name, part#, partner..." value="${this.searchQuery}">
        </div>

        <div class="filter-tabs">
          <button class="filter-tab ${this.filterStatus === 'all' ? 'active' : ''}" data-status="all">All</button>
          <button class="filter-tab ${this.filterStatus === 'pending' ? 'active' : ''}" data-status="pending">Pending</button>
          <button class="filter-tab ${this.filterStatus === 'acknowledged' ? 'active' : ''}" data-status="acknowledged">Acknowledged</button>
          <button class="filter-tab ${this.filterStatus === 'released' ? 'active' : ''}" data-status="released">Released</button>
        </div>

        <div class="summary-bar">
          <span id="summaryText">Loading...</span>
        </div>

        <div class="list-container" id="queueList">
          <div class="loading-state">Loading queue...</div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachListeners();
  }

  private attachListeners(): void {
    this.container.querySelectorAll('.filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.filterStatus = (tab as HTMLElement).dataset.status || 'pending';
        this.container.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.applyFilters();
      });
    });

    const searchInput = document.getElementById('searchInput') as HTMLInputElement;
    searchInput?.addEventListener('input', () => {
      this.searchQuery = searchInput.value.toLowerCase();
      this.applyFilters();
    });
  }

  private applyFilters(): void {
    this.filteredItems = this.items.filter(item => {
      const matchesStatus = this.filterStatus === 'all' || item.status?.toLowerCase() === this.filterStatus;
      const matchesSearch = !this.searchQuery ||
        item.spare_name?.toLowerCase().includes(this.searchQuery) ||
        item.part_number?.toLowerCase().includes(this.searchQuery) ||
        item.partner_name?.toLowerCase().includes(this.searchQuery) ||
        item.ticket_number?.toLowerCase().includes(this.searchQuery);
      return matchesStatus && matchesSearch;
    });
    this.updateList();
  }

  private updateList(): void {
    const listContainer = document.getElementById('queueList');
    const summaryEl = document.getElementById('summaryText');

    if (summaryEl) {
      const pending = this.items.filter(i => i.status?.toLowerCase() === 'pending').length;
      const totalValue = this.filteredItems.reduce((sum, i) => sum + (i.total_price || 0), 0);
      summaryEl.textContent = `${this.filteredItems.length} items | ${pending} pending | ₹${totalValue.toLocaleString()} total`;
    }

    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading queue...</div>';
      return;
    }

    if (this.filteredItems.length === 0) {
      listContainer.innerHTML = `<div class="empty-state">No ${this.filterStatus} items found</div>`;
      return;
    }

    listContainer.innerHTML = this.filteredItems.map(item => this.renderQueueItem(item)).join('');
    this.attachItemListeners();
  }

  private getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      pending: 'Pending',
      acknowledged: 'Payment Pending',
      payment_received: 'Payment Received',
      waiting_for_spares: 'Waiting for Spares',
      dispatched: 'Dispatched',
      cancelled: 'Cancelled',
      ordered: 'Ordered',
      received: 'Received',
      released: 'Released',
    };
    return labels[status?.toLowerCase()] || status || 'Unknown';
  }

  private renderQueueItem(item: ProcurementItem): string {
    const statusKey = item.status?.toLowerCase() || 'pending';
    const requestDate = new Date(item.requested_at).toLocaleDateString('en-IN', { 
      day: '2-digit', month: 'short' 
    });

    return `
      <div class="list-card procurement-item" data-id="${item.id}">
        <div class="item-header">
          <span class="spare-name">${item.spare_name}</span>
          <span class="status-badge ${statusKey}">${this.getStatusLabel(item.status)}</span>
        </div>
        <div class="item-meta">
          <span class="partner-name">${item.partner_name || 'N/A'}</span>
          <span class="ticket-ref">${item.ticket_number || `#${item.ticket_id}`}</span>
        </div>
        <div class="item-details">
          ${item.part_number ? `<span class="part-number">${item.part_number}</span>` : ''}
          <span class="quantity">Qty: ${item.quantity}</span>
          ${item.total_price ? `<span class="price">₹${item.total_price.toLocaleString()}</span>` : ''}
        </div>
        <div class="item-footer">
          <span class="request-date">Requested: ${requestDate}</span>
          ${item.released_at ? `<span class="released-date">Released: ${new Date(item.released_at).toLocaleDateString('en-IN')}</span>` : ''}
        </div>
      </div>
    `;
  }

  private attachItemListeners(): void {
    this.container.querySelectorAll('.procurement-item').forEach(item => {
      item.addEventListener('click', () => {
        const id = parseInt((item as HTMLElement).dataset.id || '0');
        const selectedItem = this.items.find(i => i.id === id);
        if (selectedItem) {
          alert(`Spare: ${selectedItem.spare_name}\nQty: ${selectedItem.quantity}\nStatus: ${selectedItem.status}\nPartner: ${selectedItem.partner_name}`);
        }
      });
    });
  }
}
