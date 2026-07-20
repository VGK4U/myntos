/**
 * Partner Invoices Page
 * DC Protocol: DC_MOBILE_PARTNER_INVOICES_001
 * View partner invoices
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface Invoice {
  id: number;
  invoice_number: string;
  customer_name: string;
  amount: number;
  gst_amount: number;
  total_amount: number;
  status: string;
  invoice_date: string;
  due_date: string;
}

interface SfmsInvoice {
  id: number;
  invoice_number: string;
  invoice_date: string;
  grand_total: number;
  balance_due: number;
  payment_status: string;
  dispatch_status: string;
  company_name: string;
  company_code: string;
}

export class PartnerInvoices {
  private container: HTMLElement;
  private invoices: Invoice[] = [];
  private sfmsInvoices: SfmsInvoice[] = [];
  private loading: boolean = true;
  private sfmsLoading: boolean = false;
  private sfmsLoaded: boolean = false;
  private activeTab: 'invoices' | 'sfms' = 'invoices';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadInvoices();
  }

  private async loadInvoices(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<{ invoices: Invoice[] }>('/partner/invoices');
      if (response.success && response.data) {
        this.invoices = response.data.invoices || [];
      }
    } catch (error) {
      console.error('[PartnerInvoices] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private async loadSfmsInvoices(): Promise<void> {
    this.sfmsLoading = true;
    this.updateContent();
    try {
      const response = await apiService.get<{ data: SfmsInvoice[] }>('/partner/sfms-invoices?per_page=50');
      if (response.success && response.data) {
        this.sfmsInvoices = response.data.data || [];
      }
    } catch (error) {
      console.error('[PartnerInvoices] SFMS load failed:', error);
    }
    this.sfmsLoading = false;
    this.sfmsLoaded = true;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Invoices', showBack: true })}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;
    PageHeader.attachListeners({ title: 'Invoices', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const tabBar = `
      <div style="display:flex;border-bottom:2px solid rgba(255,255,255,0.1);margin-bottom:14px">
        <button id="tabInvoices" style="flex:1;padding:10px;background:none;border:none;border-bottom:3px solid ${this.activeTab==='invoices'?'#10b981':'transparent'};color:${this.activeTab==='invoices'?'#10b981':'#8892b0'};font-size:13px;font-weight:600;cursor:pointer;margin-bottom:-2px">Order Invoices</button>
        <button id="tabSfms" style="flex:1;padding:10px;background:none;border:none;border-bottom:3px solid ${this.activeTab==='sfms'?'#10b981':'transparent'};color:${this.activeTab==='sfms'?'#10b981':'#8892b0'};font-size:13px;font-weight:600;cursor:pointer;margin-bottom:-2px">Company Invoices</button>
      </div>`;

    if (this.activeTab === 'invoices') {
      const totalAmount = this.invoices.reduce((s, i) => s + i.total_amount, 0);
      const pendingAmount = this.invoices.filter(i => i.status !== 'Paid').reduce((s, i) => s + i.total_amount, 0);
      content.innerHTML = tabBar + (this.invoices.length === 0 ? '<div class="empty-state">No invoices found</div>' : `
        <div class="invoice-summary card">
          <div class="summary-row">
            <div class="summary-item"><span class="value">₹${totalAmount.toLocaleString()}</span><span class="label">Total Invoiced</span></div>
            <div class="summary-item"><span class="value">₹${pendingAmount.toLocaleString()}</span><span class="label">Pending</span></div>
          </div>
        </div>
        <div class="list-container">
          ${this.invoices.map(inv => `
            <div class="list-item card invoice-card">
              <div class="item-header">
                <span class="invoice-number">${inv.invoice_number}</span>
                <span class="status-badge ${inv.status.toLowerCase()}">${inv.status}</span>
              </div>
              <div class="invoice-details">
                <p class="customer-name">${inv.customer_name}</p>
                <div class="amount-breakdown"><span>Amount: ₹${inv.amount.toLocaleString()}</span><span>GST: ₹${inv.gst_amount.toLocaleString()}</span></div>
              </div>
              <div class="invoice-footer">
                <span class="total-amount">Total: ₹${inv.total_amount.toLocaleString()}</span>
                <span class="invoice-date">${this.formatDate(inv.invoice_date)}</span>
              </div>
            </div>`).join('')}
        </div>`);
    } else {
      if (this.sfmsLoading) {
        content.innerHTML = tabBar + '<div class="loading-state">Loading company invoices...</div>';
      } else if (this.sfmsInvoices.length === 0) {
        content.innerHTML = tabBar + '<div class="empty-state">No company invoices linked to your account.</div>';
      } else {
        content.innerHTML = tabBar + `
          <div class="list-container">
            ${this.sfmsInvoices.map(inv => `
              <div class="list-item card" style="background:rgba(22,33,62,0.9);border-radius:10px;padding:14px;margin-bottom:10px;border:1px solid rgba(255,255,255,0.08)">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                  <span style="font-weight:700;color:#64d2ff">${inv.invoice_number}</span>
                  <span style="font-size:10px;padding:2px 8px;border-radius:10px;background:rgba(16,185,129,0.15);color:#10b981">${inv.payment_status}</span>
                </div>
                <div style="font-size:12px;color:#8892b0;margin-bottom:6px">${inv.company_name || inv.company_code || '—'} · ${this.formatDate(inv.invoice_date)}</div>
                <div style="display:flex;justify-content:space-between;font-size:13px">
                  <span style="color:#e6f1ff">Total: ₹${inv.grand_total.toLocaleString()}</span>
                  <span style="color:${inv.balance_due>0?'#ef4444':'#10b981'}">Due: ₹${inv.balance_due.toLocaleString()}</span>
                </div>
                <div style="font-size:11px;color:#8892b0;margin-top:6px">${(inv.dispatch_status||'').replace(/_/g,' ')}</div>
              </div>`).join('')}
          </div>`;
      }
    }

    document.getElementById('tabInvoices')?.addEventListener('click', () => { this.activeTab = 'invoices'; this.updateContent(); });
    document.getElementById('tabSfms')?.addEventListener('click', () => {
      this.activeTab = 'sfms';
      if (!this.sfmsLoaded && !this.sfmsLoading) this.loadSfmsInvoices();
      else this.updateContent();
    });
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return '—';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  }
}
