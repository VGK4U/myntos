/**
 * Service Revenue Page - Enhanced Version
 * DC Protocol: DC_MOBILE_SERVICE_REVENUE_001
 * View and manage service center revenue/billing with full web parity
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';

interface BillingRecord {
  id: number;
  ticket_id: number;
  ticket_number: string;
  customer_name: string;
  customer_mobile?: string;
  vehicle_number: string;
  status: string;
  labor_charges: number;
  spares_total: number;
  total_amount: number;
  discount?: number;
  created_at: string;
  confirmed_at?: string;
  partner_id?: number;
  partner_name?: string;
  items?: BillingItem[];
}

interface BillingItem {
  id: number;
  description: string;
  item_type: string;
  quantity: number;
  unit_price: number;
  amount: number;
}

interface RevenueStats {
  totalRevenue: number;
  totalBills: number;
  pendingAmount: number;
  confirmedAmount: number;
  draftCount: number;
  confirmedCount: number;
}

export class ServiceRevenuePage {
  private container: HTMLElement;
  private billings: BillingRecord[] = [];
  private filteredBillings: BillingRecord[] = [];
  private loading: boolean = true;
  private filterStatus: string = 'all';
  private searchQuery: string = '';
  private selectedBilling: BillingRecord | null = null;
  private stats: RevenueStats = { totalRevenue: 0, totalBills: 0, pendingAmount: 0, confirmedAmount: 0, draftCount: 0, confirmedCount: 0 };
  private pendingTimers: ReturnType<typeof setTimeout>[] = [];

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadBillings();
  }

  private async loadBillings(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      const response = await apiService.get<any>('/tickets/service/reports/my-revenue');
      if (response.success && response.data) {
        this.billings = Array.isArray(response.data) ? response.data : (response.data.billings || []);
        this.calculateStats();
      }
    } catch (error) {
      console.error('[ServiceRevenuePage] Failed to load:', error);
    }

    this.loading = false;
    this.applyFilters();
    this.renderStats();
  }

  private calculateStats(): void {
    this.stats = {
      totalRevenue: this.billings.reduce((sum, b) => sum + (b.total_amount || 0), 0),
      totalBills: this.billings.length,
      pendingAmount: this.billings.filter(b => b.status?.toLowerCase() === 'draft' || b.status?.toLowerCase() === 'pending')
        .reduce((sum, b) => sum + (b.total_amount || 0), 0),
      confirmedAmount: this.billings.filter(b => b.status?.toLowerCase() === 'confirmed' || b.status?.toLowerCase() === 'paid')
        .reduce((sum, b) => sum + (b.total_amount || 0), 0),
      draftCount: this.billings.filter(b => b.status?.toLowerCase() === 'draft' || b.status?.toLowerCase() === 'pending').length,
      confirmedCount: this.billings.filter(b => b.status?.toLowerCase() === 'confirmed' || b.status?.toLowerCase() === 'paid').length
    };
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container service-revenue-page">
        ${PageHeader.render({ title: 'Billing & Revenue', showBack: true })}
        
        <!-- Revenue Summary Cards -->
        <div class="revenue-summary-grid">
          <div class="revenue-card total">
            <span class="revenue-icon">💰</span>
            <div class="revenue-content">
              <span class="revenue-value" id="totalRevenue">${this.formatCurrency(this.stats.totalRevenue)}</span>
              <span class="revenue-label">Total Revenue</span>
            </div>
          </div>
          <div class="revenue-card pending">
            <span class="revenue-icon">⏳</span>
            <div class="revenue-content">
              <span class="revenue-value" id="pendingAmount">${this.formatCurrency(this.stats.pendingAmount)}</span>
              <span class="revenue-label">Pending</span>
            </div>
          </div>
        </div>

        <!-- Stats Row -->
        <div class="stats-row-compact">
          <div class="stat-pill">
            <span class="pill-value">${this.stats.totalBills}</span>
            <span class="pill-label">Total Bills</span>
          </div>
          <div class="stat-pill draft">
            <span class="pill-value">${this.stats.draftCount}</span>
            <span class="pill-label">Draft</span>
          </div>
          <div class="stat-pill confirmed">
            <span class="pill-value">${this.stats.confirmedCount}</span>
            <span class="pill-label">Confirmed</span>
          </div>
        </div>

        <!-- Search -->
        <div class="search-filter-section">
          <div class="search-bar">
            <input type="text" id="searchInput" class="search-input" placeholder="Search by ticket#, customer, vehicle..." value="${this.searchQuery}">
          </div>
        </div>

        <!-- Filter Tabs -->
        <div class="filter-tabs scrollable" id="filterTabs">
          <button class="filter-tab ${this.filterStatus === 'all' ? 'active' : ''}" data-status="all">
            All <span class="tab-count">${this.stats.totalBills}</span>
          </button>
          <button class="filter-tab ${this.filterStatus === 'draft' ? 'active' : ''}" data-status="draft">
            Draft <span class="tab-count">${this.stats.draftCount}</span>
          </button>
          <button class="filter-tab ${this.filterStatus === 'confirmed' ? 'active' : ''}" data-status="confirmed">
            Confirmed <span class="tab-count">${this.stats.confirmedCount}</span>
          </button>
        </div>

        <!-- List -->
        <div class="list-container" id="billingsList">
          <div class="loading-state"><div class="spinner"></div>Loading billings...</div>
        </div>
      </div>

      <!-- Detail Modal -->
      <div class="modal-overlay" id="billingModal" style="display: none;">
        <div class="modal-content modal-lg">
          <div class="modal-header">
            <h4 id="billingModalTitle">Billing Details</h4>
            <button class="modal-close" id="closeBillingModal">&times;</button>
          </div>
          <div class="modal-body" id="billingModalBody"></div>
          <div class="modal-footer" id="billingModalFooter"></div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachListeners();
  }

  private renderStats(): void {
    const totalEl = document.getElementById('totalRevenue');
    const pendingEl = document.getElementById('pendingAmount');
    if (totalEl) totalEl.textContent = this.formatCurrency(this.stats.totalRevenue);
    if (pendingEl) pendingEl.textContent = this.formatCurrency(this.stats.pendingAmount);
    this.updateTabCounts();
  }

  private updateTabCounts(): void {
    const tabs = document.getElementById('filterTabs');
    if (!tabs) return;

    const counts: Record<string, number> = {
      all: this.stats.totalBills,
      draft: this.stats.draftCount,
      confirmed: this.stats.confirmedCount
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

    document.getElementById('closeBillingModal')?.addEventListener('click', () => this.hideModal());
  }

  private applyFilters(): void {
    this.filteredBillings = this.billings.filter(bill => {
      const billStatus = bill.status?.toLowerCase();
      const matchesStatus = this.filterStatus === 'all' || 
        billStatus === this.filterStatus ||
        (this.filterStatus === 'draft' && (billStatus === 'draft' || billStatus === 'pending')) ||
        (this.filterStatus === 'confirmed' && (billStatus === 'confirmed' || billStatus === 'paid'));

      const matchesSearch = !this.searchQuery ||
        bill.ticket_number?.toLowerCase().includes(this.searchQuery) ||
        bill.customer_name?.toLowerCase().includes(this.searchQuery) ||
        bill.vehicle_number?.toLowerCase().includes(this.searchQuery) ||
        bill.partner_name?.toLowerCase().includes(this.searchQuery);

      return matchesStatus && matchesSearch;
    });
    this.updateList();
  }

  private updateList(): void {
    const listContainer = document.getElementById('billingsList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state"><div class="spinner"></div>Loading billings...</div>';
      return;
    }

    if (this.filteredBillings.length === 0) {
      listContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📄</div>
          <h4>No Billings Found</h4>
          <p>No ${this.filterStatus === 'all' ? '' : this.filterStatus} billings match your search</p>
        </div>
      `;
      return;
    }

    listContainer.innerHTML = this.filteredBillings.map(bill => this.renderBillingCard(bill)).join('');
    this.attachCardListeners();
  }

  private renderBillingCard(bill: BillingRecord): string {
    const statusClass = this.getStatusClass(bill.status);
    const createdDate = new Date(bill.created_at).toLocaleDateString('en-IN', { 
      day: '2-digit', month: 'short', year: '2-digit'
    });

    return `
      <div class="list-card billing-card" data-id="${bill.id}">
        <div class="billing-header-row">
          <div class="billing-id-section">
            <span class="ticket-number">${bill.ticket_number || `#${bill.ticket_id}`}</span>
            <span class="billing-date">${createdDate}</span>
          </div>
          <span class="status-badge ${statusClass}">${bill.status}</span>
        </div>
        
        <div class="billing-customer-row">
          <span class="customer-name">${bill.customer_name || 'Unknown'}</span>
          <span class="vehicle-tag">${bill.vehicle_number || 'N/A'}</span>
        </div>

        ${bill.partner_name ? `
        <div class="billing-partner-row">
          <span class="partner-tag">🏢 ${bill.partner_name}</span>
        </div>
        ` : ''}

        <div class="billing-amounts-grid">
          <div class="amount-item">
            <span class="amount-label">Labor</span>
            <span class="amount-value">₹${(bill.labor_charges || 0).toLocaleString()}</span>
          </div>
          <div class="amount-item">
            <span class="amount-label">Spares</span>
            <span class="amount-value">₹${(bill.spares_total || 0).toLocaleString()}</span>
          </div>
          <div class="amount-item total">
            <span class="amount-label">Total</span>
            <span class="amount-value">₹${(bill.total_amount || 0).toLocaleString()}</span>
          </div>
        </div>
      </div>
    `;
  }

  private getStatusClass(status: string | undefined): string {
    const s = (status || 'draft').toLowerCase();
    const map: Record<string, string> = {
      'draft': 'draft',
      'pending': 'draft',
      'confirmed': 'confirmed',
      'paid': 'paid'
    };
    return map[s] || 'draft';
  }

  private attachCardListeners(): void {
    this.container.querySelectorAll('.billing-card').forEach(card => {
      card.addEventListener('click', () => {
        const id = parseInt((card as HTMLElement).dataset.id || '0');
        this.showBillingDetails(id);
      });
    });
  }

  private async showBillingDetails(id: number): Promise<void> {
    this.selectedBilling = this.billings.find(b => b.id === id) || null;
    if (!this.selectedBilling) return;

    const bill = this.selectedBilling;
    const modalBody = document.getElementById('billingModalBody');
    const modalFooter = document.getElementById('billingModalFooter');
    const modalTitle = document.getElementById('billingModalTitle');
    const modal = document.getElementById('billingModal');

    if (modalTitle) {
      modalTitle.textContent = `Bill: ${bill.ticket_number || `#${bill.ticket_id}`}`;
    }

    if (modalBody) {
      modalBody.innerHTML = '<div class="loading-state">Loading details...</div>';
    }
    if (modal) modal.style.display = 'flex';

    try {
      const response = await apiService.get<any>(`/tickets/service/${bill.ticket_id}/billing`);
      const fullBilling = response.success && response.data ? response.data : bill;

      if (modalBody) {
        modalBody.innerHTML = `
          <div class="billing-detail-tabs">
            <button class="detail-tab active" data-tab="details">Details</button>
            <button class="detail-tab" data-tab="items">Items</button>
          </div>

          <div id="billingTabContent">
            ${this.renderDetailsTab(fullBilling)}
          </div>
        `;

        modalBody.querySelectorAll('.detail-tab').forEach(tab => {
          tab.addEventListener('click', () => {
            modalBody.querySelectorAll('.detail-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const tabName = (tab as HTMLElement).dataset.tab;
            const tabContent = document.getElementById('billingTabContent');
            if (tabContent) {
              if (tabName === 'details') tabContent.innerHTML = this.renderDetailsTab(fullBilling);
              else if (tabName === 'items') tabContent.innerHTML = this.renderItemsTab(fullBilling);
            }
          });
        });
      }

      if (modalFooter) {
        const status = bill.status?.toLowerCase();
        let buttons = '<button class="btn btn-secondary" id="closeBillingDetails">Close</button>';

        if (status === 'draft' || status === 'pending') {
          buttons += '<button class="btn btn-info" id="autoPopulateBill">Auto Populate</button>';
          buttons += '<button class="btn btn-success" id="confirmBilling">Confirm & Send</button>';
        } else if (status === 'confirmed') {
          buttons += '<button class="btn btn-primary" id="downloadPdf">Download PDF</button>';
          buttons += '<button class="btn btn-success" id="markPaid">Mark Paid</button>';
        } else if (status === 'paid') {
          buttons += '<button class="btn btn-primary" id="downloadPdf">Download PDF</button>';
        }

        modalFooter.innerHTML = buttons;
        this.attachModalListeners(fullBilling);
      }
    } catch (error) {
      if (modalBody) {
        modalBody.innerHTML = '<div class="error-state">Failed to load billing details</div>';
      }
    }
  }

  private renderDetailsTab(bill: BillingRecord): string {
    return `
      <div class="billing-detail-section">
        <div class="detail-grid">
          <div class="detail-item">
            <span class="detail-label">Status</span>
            <span class="status-badge ${this.getStatusClass(bill.status)}">${bill.status}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Created</span>
            <span class="detail-value">${new Date(bill.created_at).toLocaleDateString('en-IN')}</span>
          </div>
        </div>
      </div>

      <div class="billing-detail-section">
        <h5>Customer</h5>
        <div class="customer-info-box">
          <p class="customer-name-large">${bill.customer_name}</p>
          ${bill.customer_mobile ? `<a href="tel:${bill.customer_mobile}" class="phone-link">📞 ${bill.customer_mobile}</a>` : ''}
          <p class="vehicle-info">${bill.vehicle_number}</p>
        </div>
      </div>

      ${bill.partner_name ? `
      <div class="billing-detail-section">
        <h5>Partner</h5>
        <p class="partner-info">${bill.partner_name}</p>
      </div>
      ` : ''}

      <div class="billing-detail-section">
        <h5>Charges Summary</h5>
        <div class="charges-breakdown">
          <div class="charge-row">
            <span>Labor Charges</span>
            <span>₹${(bill.labor_charges || 0).toLocaleString()}</span>
          </div>
          <div class="charge-row">
            <span>Spares Total</span>
            <span>₹${(bill.spares_total || 0).toLocaleString()}</span>
          </div>
          ${bill.discount ? `
          <div class="charge-row discount">
            <span>Discount</span>
            <span>-₹${bill.discount.toLocaleString()}</span>
          </div>
          ` : ''}
          <div class="charge-row grand-total">
            <span>Grand Total</span>
            <span>₹${(bill.total_amount || 0).toLocaleString()}</span>
          </div>
        </div>
      </div>

      ${bill.confirmed_at ? `
      <div class="billing-detail-section">
        <h5>Confirmation</h5>
        <p class="confirmed-date">Confirmed on ${new Date(bill.confirmed_at).toLocaleString('en-IN')}</p>
      </div>
      ` : ''}
    `;
  }

  private renderItemsTab(bill: BillingRecord): string {
    const items = bill.items || [];
    
    if (items.length === 0) {
      return `
        <div class="empty-mini">
          <p>No items added to this bill</p>
          ${bill.status?.toLowerCase() === 'draft' ? '<p class="hint">Use "Auto Populate" to add items automatically</p>' : ''}
        </div>
      `;
    }

    return `
      <div class="billing-items-list">
        ${items.map(item => `
          <div class="billing-item-card">
            <div class="item-header">
              <span class="item-name">${item.description}</span>
              <span class="item-type-badge">${item.item_type}</span>
            </div>
            <div class="item-details">
              <span class="item-qty">${item.quantity} × ₹${item.unit_price?.toLocaleString()}</span>
              <span class="item-amount">₹${item.amount?.toLocaleString()}</span>
            </div>
          </div>
        `).join('')}
      </div>

      <div class="items-total">
        <span>Total</span>
        <span>₹${items.reduce((sum, i) => sum + (i.amount || 0), 0).toLocaleString()}</span>
      </div>
    `;
  }

  private attachModalListeners(bill: BillingRecord): void {
    document.getElementById('closeBillingDetails')?.addEventListener('click', () => this.hideModal());
    document.getElementById('autoPopulateBill')?.addEventListener('click', () => this.autoPopulateBill(bill.ticket_id));
    document.getElementById('confirmBilling')?.addEventListener('click', () => this.confirmBilling());
    document.getElementById('downloadPdf')?.addEventListener('click', () => this.downloadPdf());
    document.getElementById('markPaid')?.addEventListener('click', () => this.markAsPaid());
  }

  private async autoPopulateBill(ticketId: number): Promise<void> {
    try {
      const response = await apiService.post(`/tickets/service/${ticketId}/billing/auto-populate`, {});
      if (response.success) {
        this.showToast('Bill auto-populated with spares and labor');
        await this.loadBillings();
        this.showBillingDetails(this.selectedBilling!.id);
      } else {
        this.showToast(response.error || 'Failed to auto-populate', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to auto-populate', 'error');
    }
  }

  private async confirmBilling(): Promise<void> {
    if (!this.selectedBilling) return;

    try {
      const response = await apiService.post(`/tickets/service/billing/${this.selectedBilling.id}/confirm`, {});
      if (response.success) {
        this.showToast('Billing confirmed');
        this.hideModal();
        await this.loadBillings();
      } else {
        this.showToast(response.error || 'Failed to confirm billing', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to confirm billing', 'error');
    }
  }

  private async downloadPdf(): Promise<void> {
    if (!this.selectedBilling) return;

    try {
      window.open(`/api/v1/tickets/service/billing/${this.selectedBilling.id}/pdf`, '_blank');
      this.showToast('Opening PDF...');
    } catch (error: any) {
      this.showToast(error.message || 'Failed to download PDF', 'error');
    }
  }

  private async markAsPaid(): Promise<void> {
    if (!this.selectedBilling) return;

    try {
      const response = await apiService.post(`/tickets/service/billing/${this.selectedBilling.id}/mark-paid`, {});
      if (response.success) {
        this.showToast('Marked as paid');
        this.hideModal();
        await this.loadBillings();
      } else {
        this.showToast(response.error || 'Failed to update', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to update', 'error');
    }
  }

  private hideModal(): void {
    const modal = document.getElementById('billingModal');
    if (modal) modal.style.display = 'none';
    this.selectedBilling = null;
  }

  private formatCurrency(amount: number): string {
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
    if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
    return `₹${amount.toLocaleString()}`;
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
