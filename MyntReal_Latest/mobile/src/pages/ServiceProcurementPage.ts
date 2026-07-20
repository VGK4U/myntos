/**
 * Service Procurement Page - Enhanced Version
 * DC Protocol: DC_MOBILE_SERVICE_PROCUREMENT_001
 * Manage spare parts procurement with full web parity
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';

interface SpareRequest {
  id: number;
  ticket_id: number;
  ticket_number: string;
  spare_name: string;
  part_number?: string;
  quantity: number;
  status: string;
  requested_by: string;
  requested_at: string;
  acknowledged_at?: string;
  released_at?: string;
  unit_price?: number;
  total_price?: number;
  notes?: string;
  partner_name?: string;
  customer_name?: string;
  vehicle_number?: string;
}

interface StockItem {
  id: number;
  item_name: string;
  item_code: string;
  current_stock: number;
  unit_price: number;
  hsn_code?: string;
}

interface ProcurementStats {
  total: number;
  pending: number;
  acknowledged: number;
  released: number;
  totalValue: number;
}

export class ServiceProcurementPage {
  private container: HTMLElement;
  private requests: SpareRequest[] = [];
  private filteredRequests: SpareRequest[] = [];
  private loading: boolean = true;
  private filterStatus: string = 'all';
  private searchQuery: string = '';
  private selectedRequest: SpareRequest | null = null;
  private stats: ProcurementStats = { total: 0, pending: 0, acknowledged: 0, released: 0, totalValue: 0 };
  private pendingTimers: ReturnType<typeof setTimeout>[] = [];

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
      const response = await apiService.get<any>('/tickets/service/procurement-queue');
      if (response.success && response.data) {
        this.requests = Array.isArray(response.data) ? response.data : (response.data.spares || []);
        this.calculateStats();
      }
    } catch (error) {
      console.error('[ServiceProcurementPage] Failed to load:', error);
    }

    this.loading = false;
    this.applyFilters();
    this.renderStats();
  }

  private calculateStats(): void {
    this.stats = {
      total: this.requests.length,
      pending: this.requests.filter(r => r.status?.toLowerCase() === 'pending').length,
      acknowledged: this.requests.filter(r => r.status?.toLowerCase() === 'acknowledged').length,
      released: this.requests.filter(r => r.status?.toLowerCase() === 'released').length,
      totalValue: this.requests.reduce((sum, r) => sum + (r.total_price || 0), 0)
    };
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container service-procurement-page">
        ${PageHeader.render({ title: 'Spare Parts', showBack: true })}
        
        <!-- Stats Grid -->
        <div class="stats-grid-compact" id="procurementStats">
          ${this.renderStatsCards()}
        </div>

        <!-- Search -->
        <div class="search-filter-section">
          <div class="search-bar">
            <input type="text" id="searchInput" class="search-input" placeholder="Search by part name, ticket#..." value="${this.searchQuery}">
          </div>
        </div>

        <!-- Filter Tabs -->
        <div class="filter-tabs scrollable" id="filterTabs">
          <button class="filter-tab ${this.filterStatus === 'all' ? 'active' : ''}" data-status="all">
            All <span class="tab-count">${this.stats.total}</span>
          </button>
          <button class="filter-tab ${this.filterStatus === 'pending' ? 'active' : ''}" data-status="pending">
            Pending <span class="tab-count">${this.stats.pending}</span>
          </button>
          <button class="filter-tab ${this.filterStatus === 'acknowledged' ? 'active' : ''}" data-status="acknowledged">
            Acknowledged <span class="tab-count">${this.stats.acknowledged}</span>
          </button>
          <button class="filter-tab ${this.filterStatus === 'released' ? 'active' : ''}" data-status="released">
            Released <span class="tab-count">${this.stats.released}</span>
          </button>
        </div>

        <!-- List -->
        <div class="list-container" id="requestsList">
          <div class="loading-state"><div class="spinner"></div>Loading requests...</div>
        </div>
      </div>

      <!-- Detail Modal -->
      <div class="modal-overlay" id="spareModal" style="display: none;">
        <div class="modal-content modal-lg">
          <div class="modal-header">
            <h4 id="spareModalTitle">Spare Request</h4>
            <button class="modal-close" id="closeSpareModal">&times;</button>
          </div>
          <div class="modal-body" id="spareModalBody"></div>
          <div class="modal-footer" id="spareModalFooter"></div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachListeners();
  }

  private renderStatsCards(): string {
    return `
      <div class="stat-mini pending">
        <span class="stat-icon">⏳</span>
        <span class="stat-value">${this.stats.pending}</span>
        <span class="stat-label">Pending</span>
      </div>
      <div class="stat-mini acknowledged">
        <span class="stat-icon">✓</span>
        <span class="stat-value">${this.stats.acknowledged}</span>
        <span class="stat-label">Ack'd</span>
      </div>
      <div class="stat-mini completed">
        <span class="stat-icon">📦</span>
        <span class="stat-value">${this.stats.released}</span>
        <span class="stat-label">Released</span>
      </div>
      <div class="stat-mini in-progress">
        <span class="stat-icon">💰</span>
        <span class="stat-value">${this.formatCurrency(this.stats.totalValue)}</span>
        <span class="stat-label">Value</span>
      </div>
    `;
  }

  private renderStats(): void {
    const statsEl = document.getElementById('procurementStats');
    if (statsEl) {
      statsEl.innerHTML = this.renderStatsCards();
    }
    this.updateTabCounts();
  }

  private updateTabCounts(): void {
    const tabs = document.getElementById('filterTabs');
    if (!tabs) return;

    const counts: Record<string, number> = {
      all: this.stats.total,
      pending: this.stats.pending,
      acknowledged: this.stats.acknowledged,
      released: this.stats.released
    };

    tabs.querySelectorAll('.filter-tab').forEach(tab => {
      const status = (tab as HTMLElement).dataset.status || 'all';
      const countEl = tab.querySelector('.tab-count');
      if (countEl) countEl.textContent = String(counts[status] || 0);
    });
  }

  private attachListeners(): void {
    this.container.querySelectorAll('.filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.filterStatus = (tab as HTMLElement).dataset.status || 'all';
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

    document.getElementById('closeSpareModal')?.addEventListener('click', () => this.hideModal());
  }

  private applyFilters(): void {
    this.filteredRequests = this.requests.filter(req => {
      const matchesStatus = this.filterStatus === 'all' || req.status?.toLowerCase() === this.filterStatus;
      const matchesSearch = !this.searchQuery ||
        req.spare_name?.toLowerCase().includes(this.searchQuery) ||
        req.part_number?.toLowerCase().includes(this.searchQuery) ||
        req.ticket_number?.toLowerCase().includes(this.searchQuery) ||
        req.customer_name?.toLowerCase().includes(this.searchQuery);
      return matchesStatus && matchesSearch;
    });
    this.updateList();
  }

  private updateList(): void {
    const listContainer = document.getElementById('requestsList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state"><div class="spinner"></div>Loading requests...</div>';
      return;
    }

    if (this.filteredRequests.length === 0) {
      listContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📦</div>
          <h4>No Spare Requests</h4>
          <p>No ${this.filterStatus === 'all' ? '' : this.filterStatus} spare requests found</p>
        </div>
      `;
      return;
    }

    listContainer.innerHTML = this.filteredRequests.map(req => this.renderRequestCard(req)).join('');
    this.attachCardListeners();
  }

  private renderRequestCard(req: SpareRequest): string {
    const statusClass = this.getStatusClass(req.status);
    const requestDate = new Date(req.requested_at).toLocaleDateString('en-IN', { 
      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
    });

    return `
      <div class="list-card spare-request-card ${statusClass}" data-id="${req.id}">
        <div class="spare-header-row">
          <div class="spare-name-section">
            <span class="spare-name">${req.spare_name}</span>
            ${req.part_number ? `<span class="part-number">${req.part_number}</span>` : ''}
          </div>
          <span class="status-badge spare-status ${statusClass}">${this.getStatusLabel(req.status)}</span>
          ${(req as any).is_warranty ? '<span style="background:#e0f2fe;color:#0369a1;font-size:10px;padding:1px 7px;border-radius:10px;font-weight:700;margin-left:4px;">🛡 Warranty</span>' : ''}
        </div>
        
        <div class="spare-ticket-row">
          <span class="ticket-ref">🎫 ${req.ticket_number || `#${req.ticket_id}`}</span>
          <span class="spare-qty">Qty: ${req.quantity}</span>
        </div>

        ${req.customer_name ? `
        <div class="spare-customer-row">
          <span class="customer-info">${req.customer_name}</span>
          ${req.vehicle_number ? `<span class="vehicle-info">${req.vehicle_number}</span>` : ''}
        </div>
        ` : ''}

        <div class="spare-footer-row">
          <span class="request-date">${requestDate}</span>
          ${req.total_price ? `<span class="spare-price">₹${req.total_price.toLocaleString()}</span>` : 
            '<span class="price-pending">Price pending</span>'}
        </div>
      </div>
    `;
  }

  private getStatusClass(status: string | undefined): string {
    const s = (status || 'pending').toLowerCase();
    const map: Record<string, string> = {
      'pending':            'status-pending',
      'acknowledged':       'status-acknowledged',
      'payment_received':   'status-received',
      'waiting_for_spares': 'status-ordered',
      'dispatched':         'status-released',
      'priced':             'status-ordered',
      'ordered':            'status-ordered',
      'received':           'status-received',
      'released':           'status-released',
      'cancelled':          'status-cancelled',
    };
    return map[s] || 'status-pending';
  }

  private getStatusLabel(status: string | undefined): string {
    const s = (status || 'pending').toLowerCase();
    const map: Record<string, string> = {
      'pending':            'Pending',
      'acknowledged':       'Acknowledged',
      'payment_received':   'Payment Received',
      'waiting_for_spares': 'Waiting for Spares',
      'dispatched':         'Dispatched',
      'priced':             'Priced',
      'ordered':            'Ordered',
      'received':           'Received',
      'released':           'Released',
      'cancelled':          'Cancelled',
    };
    return map[s] || status || 'Unknown';
  }

  private attachCardListeners(): void {
    this.container.querySelectorAll('.spare-request-card').forEach(card => {
      card.addEventListener('click', () => {
        const id = parseInt((card as HTMLElement).dataset.id || '0');
        this.showRequestDetails(id);
      });
    });
  }

  private showRequestDetails(id: number): void {
    this.selectedRequest = this.requests.find(r => r.id === id) || null;
    if (!this.selectedRequest) return;

    const req = this.selectedRequest;
    const modalBody = document.getElementById('spareModalBody');
    const modalFooter = document.getElementById('spareModalFooter');
    const modalTitle = document.getElementById('spareModalTitle');
    const modal = document.getElementById('spareModal');

    if (modalTitle) {
      modalTitle.textContent = req.spare_name;
    }

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="spare-detail-section">
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">Status</span>
              <span class="status-badge ${this.getStatusClass(req.status)}">${req.status}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Quantity</span>
              <span class="detail-value">${req.quantity}</span>
            </div>
          </div>
        </div>

        ${req.part_number ? `
        <div class="spare-detail-section">
          <div class="detail-item">
            <span class="detail-label">Part Number</span>
            <span class="detail-value">${req.part_number}</span>
          </div>
        </div>
        ` : ''}

        <div class="spare-detail-section">
          <h5>Ticket Details</h5>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">Ticket</span>
              <span class="detail-value link" id="goToTicket">${req.ticket_number || `#${req.ticket_id}`}</span>
            </div>
            ${req.customer_name ? `
            <div class="detail-item">
              <span class="detail-label">Customer</span>
              <span class="detail-value">${req.customer_name}</span>
            </div>
            ` : ''}
          </div>
          ${req.vehicle_number ? `
          <div class="detail-item">
            <span class="detail-label">Vehicle</span>
            <span class="detail-value">${req.vehicle_number}</span>
          </div>
          ` : ''}
        </div>

        <div class="spare-detail-section">
          <h5>Pricing</h5>
          ${req.unit_price ? `
          <div class="pricing-summary">
            <div class="pricing-row">
              <span>Unit Price</span>
              <span>₹${req.unit_price.toLocaleString()}</span>
            </div>
            <div class="pricing-row">
              <span>Quantity</span>
              <span>${req.quantity}</span>
            </div>
            <div class="pricing-row total">
              <span>Total</span>
              <span>₹${(req.total_price || 0).toLocaleString()}</span>
            </div>
          </div>
          ` : '<div class="empty-mini">Pricing not yet set</div>'}
        </div>

        ${req.notes ? `
        <div class="spare-detail-section">
          <h5>Notes</h5>
          <div class="notes-box">${req.notes}</div>
        </div>
        ` : ''}

        <div class="spare-detail-section">
          <h5>Timeline</h5>
          <div class="mini-timeline">
            <div class="mini-timeline-item completed">
              <span class="timeline-dot"></span>
              <span class="timeline-label">Requested</span>
              <span class="timeline-date">${new Date(req.requested_at).toLocaleString('en-IN')}</span>
            </div>
            ${req.acknowledged_at ? `
            <div class="mini-timeline-item completed">
              <span class="timeline-dot"></span>
              <span class="timeline-label">Acknowledged</span>
              <span class="timeline-date">${new Date(req.acknowledged_at).toLocaleString('en-IN')}</span>
            </div>
            ` : ''}
            ${req.released_at ? `
            <div class="mini-timeline-item completed">
              <span class="timeline-dot"></span>
              <span class="timeline-label">Released</span>
              <span class="timeline-date">${new Date(req.released_at).toLocaleString('en-IN')}</span>
            </div>
            ` : ''}
          </div>
        </div>
      `;

      document.getElementById('goToTicket')?.addEventListener('click', () => {
        this.hideModal();
        routerService.navigate('staff-service-queue', { ticketId: String(req.ticket_id) });
      });
    }

    if (modalFooter) {
      const status = req.status?.toLowerCase();
      let buttons = '<button class="btn btn-secondary" id="closeSpareDetails">Close</button>';

      if (status === 'pending') {
        buttons += '<button class="btn btn-primary" id="acknowledgeSpare">Acknowledge</button>';
      } else if (status === 'acknowledged') {
        buttons += '<button class="btn btn-info" id="autoPopulate">Auto Populate</button>';
        buttons += '<button class="btn btn-warning" id="setPricing">Set Price</button>';
        buttons += '<button class="btn btn-success" id="releaseSpare">Release</button>';
      } else if (status === 'priced') {
        buttons += '<button class="btn btn-success" id="releaseSpare">Release</button>';
      }

      modalFooter.innerHTML = buttons;
      this.attachModalListeners();
    }

    if (modal) modal.style.display = 'flex';
  }

  private attachModalListeners(): void {
    document.getElementById('closeSpareDetails')?.addEventListener('click', () => this.hideModal());
    document.getElementById('acknowledgeSpare')?.addEventListener('click', () => this.acknowledgeSpare());
    document.getElementById('autoPopulate')?.addEventListener('click', () => this.autoPopulatePricing());
    document.getElementById('setPricing')?.addEventListener('click', () => this.showPricingModal());
    document.getElementById('releaseSpare')?.addEventListener('click', () => this.releaseSpare());
  }

  private async acknowledgeSpare(): Promise<void> {
    if (!this.selectedRequest) return;

    try {
      const response = await apiService.post(`/tickets/service/spares/${this.selectedRequest.id}/acknowledge`, {});
      if (response.success) {
        this.showToast('Spare request acknowledged');
        this.hideModal();
        await this.loadRequests();
      } else {
        this.showToast(response.error || 'Failed to acknowledge', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to acknowledge', 'error');
    }
  }

  private async autoPopulatePricing(): Promise<void> {
    if (!this.selectedRequest) return;

    try {
      const response = await apiService.post(`/tickets/service/spares/${this.selectedRequest.id}/auto-populate-pricing`, {});
      if (response.success) {
        this.showToast('Pricing auto-populated from stock');
        this.hideModal();
        await this.loadRequests();
      } else {
        this.showToast(response.error || 'No matching stock item found', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to auto-populate', 'error');
    }
  }

  private showPricingModal(): void {
    const modalBody = document.getElementById('spareModalBody');
    const modalFooter = document.getElementById('spareModalFooter');

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="form-section">
          <h5>Set Pricing</h5>
          
          <div class="form-group">
            <label>Search Stock Items</label>
            <input type="text" id="stockSearch" class="form-input" placeholder="Search by name or code...">
            <div id="stockResults" class="stock-results"></div>
          </div>

          <div class="form-group">
            <label>Unit Price (₹) *</label>
            <input type="number" id="unitPrice" class="form-input" placeholder="0.00" step="0.01" 
              value="${this.selectedRequest?.unit_price || ''}">
          </div>
          
          <div class="form-row">
            <div class="form-group flex-1">
              <label>Quantity</label>
              <input type="number" id="pricingQty" class="form-input" value="${this.selectedRequest?.quantity || 1}" readonly>
            </div>
            <div class="form-group flex-1">
              <label>Total</label>
              <input type="text" id="totalPriceDisplay" class="form-input" readonly value="₹0">
            </div>
          </div>
        </div>
      `;

      const unitPriceInput = document.getElementById('unitPrice') as HTMLInputElement;
      const stockSearch = document.getElementById('stockSearch') as HTMLInputElement;
      
      unitPriceInput?.addEventListener('input', () => this.updateTotalPrice());
      stockSearch?.addEventListener('input', () => this.searchStockItems(stockSearch.value));
      
      this.updateTotalPrice();
    }

    if (modalFooter) {
      modalFooter.innerHTML = `
        <button class="btn btn-secondary" id="cancelPricing">Cancel</button>
        <button class="btn btn-primary" id="savePricing">Save</button>
      `;

      document.getElementById('cancelPricing')?.addEventListener('click', () => {
        this.showRequestDetails(this.selectedRequest!.id);
      });
      document.getElementById('savePricing')?.addEventListener('click', () => this.savePricing());
    }
  }

  private updateTotalPrice(): void {
    const unitPrice = parseFloat((document.getElementById('unitPrice') as HTMLInputElement)?.value) || 0;
    const qty = this.selectedRequest?.quantity || 1;
    const total = unitPrice * qty;
    const display = document.getElementById('totalPriceDisplay') as HTMLInputElement;
    if (display) display.value = `₹${total.toLocaleString()}`;
  }

  private async searchStockItems(query: string): Promise<void> {
    const resultsEl = document.getElementById('stockResults');
    if (!resultsEl || query.length < 2) {
      if (resultsEl) resultsEl.innerHTML = '';
      return;
    }

    try {
      const response = await apiService.get<any>(`/tickets/service/stock-items/search?q=${encodeURIComponent(query)}`);
      if (response.success && response.data) {
        const items: StockItem[] = response.data.items || response.data || [];
        if (items.length === 0) {
          resultsEl.innerHTML = '<div class="stock-empty">No items found</div>';
        } else {
          resultsEl.innerHTML = items.slice(0, 5).map(item => `
            <div class="stock-item" data-price="${item.unit_price}">
              <span class="stock-name">${item.item_name}</span>
              <span class="stock-code">${item.item_code}</span>
              <span class="stock-price">₹${item.unit_price?.toLocaleString()}</span>
            </div>
          `).join('');

          resultsEl.querySelectorAll('.stock-item').forEach(el => {
            el.addEventListener('click', () => {
              const price = (el as HTMLElement).dataset.price || '0';
              (document.getElementById('unitPrice') as HTMLInputElement).value = price;
              this.updateTotalPrice();
              resultsEl.innerHTML = '';
            });
          });
        }
      }
    } catch (error) {
      console.error('Stock search failed:', error);
    }
  }

  private async savePricing(): Promise<void> {
    if (!this.selectedRequest) return;

    const unitPrice = parseFloat((document.getElementById('unitPrice') as HTMLInputElement)?.value);

    if (!unitPrice || unitPrice <= 0) {
      this.showToast('Please enter a valid price', 'error');
      return;
    }

    try {
      const response = await apiService.put(`/tickets/service/spares/${this.selectedRequest.id}/pricing`, {
        unit_price: unitPrice
      });

      if (response.success) {
        this.showToast('Pricing updated');
        this.hideModal();
        await this.loadRequests();
      } else {
        this.showToast(response.error || 'Failed to update pricing', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to update pricing', 'error');
    }
  }

  private async releaseSpare(): Promise<void> {
    if (!this.selectedRequest) return;

    if (!this.selectedRequest.unit_price) {
      this.showToast('Please set pricing before releasing', 'error');
      return;
    }

    try {
      const response = await apiService.post(`/tickets/service/spares/${this.selectedRequest.id}/release`, {});
      if (response.success) {
        this.showToast('Spare released to service');
        this.hideModal();
        await this.loadRequests();
      } else {
        this.showToast(response.error || 'Failed to release spare', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to release spare', 'error');
    }
  }

  private hideModal(): void {
    const modal = document.getElementById('spareModal');
    if (modal) modal.style.display = 'none';
    this.selectedRequest = null;
  }

  private formatCurrency(amount: number): string {
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
    if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
    return `₹${amount}`;
  }

  private showToast(message: string, type: 'success' | 'error' = 'success'): void {
    const existing = document.querySelector('.toast-notification');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    const t1 = setTimeout(() => toast.classList.add('show'), 10);
    const t2 = setTimeout(() => {
      toast.classList.remove('show');
      const t3 = setTimeout(() => toast.remove(), 300);
      this.pendingTimers.push(t3);
    }, 3000);
    this.pendingTimers.push(t1, t2);
  }

  cleanup(): void {
    this.pendingTimers.forEach(t => clearTimeout(t));
    this.pendingTimers = [];
  }
}
