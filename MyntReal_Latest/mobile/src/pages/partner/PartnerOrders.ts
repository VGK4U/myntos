/**
 * Partner Orders Page
 * DC Protocol: DC_MOBILE_PARTNER_ORDERS_001
 * DC-PARTNER-PENDING-002: Pending Delivery tab added for web/mobile parity
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface Order {
  id: number;
  order_number: string;
  customer_name: string;
  product: string;
  quantity: number;
  amount: number;
  status: string;
  order_date: string;
}

interface PendingItem {
  item_description: string;
  item_code: string;
  unit_of_measure: string;
  invoiced_qty: number;
  dispatched_qty: number;
  remaining_qty: number;
}

interface PendingInvoice {
  invoice_id: number;
  invoice_number: string;
  invoice_date: string | null;
  dispatch_status: string;
  company_name: string | null;
  company_code: string | null;
  items: PendingItem[];
}

export class PartnerOrders {
  private container: HTMLElement;
  private orders: Order[] = [];
  private pendingInvoices: PendingInvoice[] = [];
  private loading: boolean = true;
  private pendingLoading: boolean = false;
  private pendingLoaded: boolean = false;
  private filter: 'all' | 'pending' | 'completed' = 'all';
  private activeTab: 'orders' | 'pending' = 'orders';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadOrders();
  }

  private async loadOrders(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<{ orders: Order[] }>('/partner/orders');
      if (response.success && response.data) {
        this.orders = response.data.orders || [];
      }
    } catch (error) {
      console.error('[PartnerOrders] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private async loadPendingDelivery(): Promise<void> {
    this.pendingLoading = true;
    this.updateContent();
    try {
      const response = await apiService.get<{ success: boolean; invoices: PendingInvoice[]; total_invoices: number }>('/partner/pending-dispatch');
      if (response.success && response.data) {
        this.pendingInvoices = response.data.invoices || [];
      }
    } catch (error) {
      console.error('[PartnerOrders] Pending delivery load failed:', error);
    }
    this.pendingLoading = false;
    this.pendingLoaded = true;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'My Orders', showBack: true })}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;
    PageHeader.attachListeners({ title: 'My Orders', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    const tabBar = `
      <div style="display:flex;border-bottom:2px solid rgba(255,255,255,0.1);margin-bottom:14px">
        <button id="tabOrders" style="flex:1;padding:10px;background:none;border:none;border-bottom:3px solid ${this.activeTab==='orders'?'#10b981':'transparent'};color:${this.activeTab==='orders'?'#10b981':'#8892b0'};font-size:13px;font-weight:600;cursor:pointer;margin-bottom:-2px"><i class="fas fa-file-alt" style="margin-right:4px"></i>My Orders</button>
        <button id="tabPending" style="flex:1;padding:10px;background:none;border:none;border-bottom:3px solid ${this.activeTab==='pending'?'#10b981':'transparent'};color:${this.activeTab==='pending'?'#10b981':'#8892b0'};font-size:13px;font-weight:600;cursor:pointer;margin-bottom:-2px"><i class="fas fa-truck" style="margin-right:4px"></i>Pending Delivery</button>
      </div>`;

    if (this.activeTab === 'orders') {
      if (this.loading) {
        content.innerHTML = tabBar + '<div class="loading-state">Loading orders...</div>';
      } else {
        const filterRow = `
          <div style="display:flex;gap:8px;margin-bottom:12px;padding:0 2px">
            ${(['all','pending','completed'] as const).map(f => `
              <button data-filter="${f}" style="flex:1;padding:6px 4px;border-radius:8px;border:1px solid ${this.filter===f?'#10b981':'rgba(255,255,255,0.12)'};background:${this.filter===f?'rgba(16,185,129,0.15)':'transparent'};color:${this.filter===f?'#10b981':'#8892b0'};font-size:12px;font-weight:600;cursor:pointer;text-transform:capitalize">${f}</button>`).join('')}
          </div>`;

        let filteredOrders = this.orders;
        if (this.filter === 'pending') {
          filteredOrders = this.orders.filter(o => o.status.toLowerCase() !== 'completed');
        } else if (this.filter === 'completed') {
          filteredOrders = this.orders.filter(o => o.status.toLowerCase() === 'completed');
        }

        const ordersHtml = filteredOrders.length === 0
          ? '<div class="empty-state">No orders found</div>'
          : `<div class="list-container">${filteredOrders.map(order => `
              <div class="list-item card order-card">
                <div class="item-header">
                  <span class="order-number">${order.order_number}</span>
                  <span class="status-badge ${order.status.toLowerCase()}">${order.status}</span>
                </div>
                <div class="order-details">
                  <h4 class="customer-name">${order.customer_name}</h4>
                  <p class="product-info">${order.product} x ${order.quantity}</p>
                </div>
                <div class="order-footer">
                  <span class="order-amount">₹${order.amount.toLocaleString()}</span>
                  <span class="order-date">${this.formatDate(order.order_date)}</span>
                </div>
              </div>`).join('')}
            </div>`;

        content.innerHTML = tabBar + filterRow + ordersHtml;

        content.querySelectorAll('[data-filter]').forEach(btn => {
          btn.addEventListener('click', () => {
            this.filter = btn.getAttribute('data-filter') as any;
            this.updateContent();
          });
        });
      }
    } else {
      if (this.pendingLoading) {
        content.innerHTML = tabBar + '<div class="loading-state">Loading pending deliveries...</div>';
      } else if (this.pendingInvoices.length === 0) {
        content.innerHTML = tabBar + `
          <div class="empty-state">
            <div style="font-size:2rem;margin-bottom:12px">🚚</div>
            <strong>No Pending Deliveries</strong>
            <p style="margin-top:8px;font-size:13px;color:#8892b0">All dispatches are up to date.</p>
          </div>`;
      } else {
        const cards = this.pendingInvoices.map(inv => `
          <div style="background:rgba(22,33,62,0.9);border-radius:10px;padding:14px;margin-bottom:12px;border:1px solid rgba(255,255,255,0.08)">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:6px">
              <span style="font-weight:700;color:#64d2ff">${inv.invoice_number}</span>
              <span style="font-size:10px;padding:2px 8px;border-radius:10px;background:rgba(245,158,11,0.15);color:#f59e0b">${(inv.dispatch_status||'').replace(/_/g,' ')}</span>
            </div>
            <div style="font-size:11px;color:#8892b0;margin-bottom:10px">${inv.company_code||inv.company_name||'—'}${inv.invoice_date?' · '+this.formatDate(inv.invoice_date):''}</div>
            <table style="width:100%;border-collapse:collapse;font-size:11px">
              <thead>
                <tr style="color:#6b7280;text-transform:uppercase">
                  <th style="padding:4px 6px;text-align:left;font-weight:600;border-bottom:1px solid rgba(255,255,255,0.08)">Item</th>
                  <th style="padding:4px 6px;text-align:right;font-weight:600;border-bottom:1px solid rgba(255,255,255,0.08)">Invoiced</th>
                  <th style="padding:4px 6px;text-align:right;font-weight:600;border-bottom:1px solid rgba(255,255,255,0.08)">Done</th>
                  <th style="padding:4px 6px;text-align:right;color:#ef4444;font-weight:600;border-bottom:1px solid rgba(255,255,255,0.08)">Pending</th>
                </tr>
              </thead>
              <tbody>
                ${inv.items.map(it => `
                  <tr>
                    <td style="padding:5px 6px;color:#e6f1ff;border-bottom:1px solid rgba(255,255,255,0.04)">${it.item_description}<br><small style="color:#8892b0">${it.item_code||''} ${it.unit_of_measure||''}</small></td>
                    <td style="padding:5px 6px;text-align:right;color:#8892b0;border-bottom:1px solid rgba(255,255,255,0.04)">${it.invoiced_qty}</td>
                    <td style="padding:5px 6px;text-align:right;color:#10b981;border-bottom:1px solid rgba(255,255,255,0.04)">${it.dispatched_qty}</td>
                    <td style="padding:5px 6px;text-align:right;font-weight:700;color:#ef4444;border-bottom:1px solid rgba(255,255,255,0.04)">${it.remaining_qty}</td>
                  </tr>`).join('')}
              </tbody>
            </table>
          </div>`).join('');

        content.innerHTML = tabBar + `
          <div style="margin-bottom:10px;font-size:12px;color:#8892b0">${this.pendingInvoices.length} invoice${this.pendingInvoices.length===1?'':'s'} with pending items</div>
          ${cards}`;
      }
    }

    content.querySelector('#tabOrders')?.addEventListener('click', () => {
      this.activeTab = 'orders';
      this.updateContent();
    });
    content.querySelector('#tabPending')?.addEventListener('click', () => {
      this.activeTab = 'pending';
      if (!this.pendingLoaded && !this.pendingLoading) this.loadPendingDelivery();
      else this.updateContent();
    });
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return '—';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  }
}
