/**
 * DC-PARTNER-SPARE-001: Partner Spare Orders Mobile Page
 * Browse spare parts catalog and submit/view purchase requests.
 * Mirrors partner_spare_orders.html functionality.
 */
import { apiService } from '../../services/api.service';

interface SpareItem {
  item_id: number;
  item_code: string;
  item_name: string;
  unit_of_measure: string;
  hsn_code?: string;
  purchase_rate: number;
  current_stock: number;
  in_stock: boolean;
}

interface CartEntry {
  item: SpareItem;
  qty: number;
}

interface SpareRequest {
  id: number;
  request_number: string;
  status: string;
  notes?: string;
  created_at: string;
  line_count: number;
  lines?: Array<{ item_code: string; item_name: string; quantity: number; unit_of_measure: string }>;
}

function statusChip(status: string): string {
  const map: Record<string, [string, string]> = {
    SUBMITTED:    ['#451a03', '#f59e0b'],
    ACKNOWLEDGED: ['#1e3a5f', '#60a5fa'],
    FULFILLED:    ['#064e3b', '#10b981'],
    CANCELLED:    ['#1f2937', '#9ca3af'],
  };
  const [bg, color] = map[status] || ['#1f2937', '#9ca3af'];
  return `<span style="background:${bg};color:${color};padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700">${status}</span>`;
}

export class PartnerSpareOrders {
  private container: HTMLElement;
  private cart: Map<number, CartEntry> = new Map();
  private companies: Array<{ id: number; company_name: string }> = [];
  private activeTab: 'catalog' | 'requests' = 'catalog';
  private searchTimer: ReturnType<typeof setTimeout> | null = null;
  private allItems: SpareItem[] = [];
  private requests: SpareRequest[] = [];

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadCompanies();
    await this.loadCatalog();
  }

  private render(): void {
    this.container.innerHTML = `
      <div style="display:flex;flex-direction:column;height:100%;background:#0f172a;">
        <!-- Header -->
        <div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);padding:16px 20px 14px;flex-shrink:0;">
          <div style="font-size:18px;font-weight:700;color:#fff;margin-bottom:2px;">
            🔧 Spare Parts Orders
          </div>
          <div style="font-size:12px;color:rgba(255,255,255,.7);">Request spare parts from the catalog</div>
        </div>

        <!-- Tab Pills -->
        <div style="display:flex;gap:0;background:#1e293b;border-bottom:1px solid #334155;flex-shrink:0;">
          <button id="spTabCatalog" onclick="spTab('catalog')"
            style="flex:1;padding:12px;background:#2563eb;color:#fff;border:none;font-size:13px;font-weight:700;cursor:pointer;">
            📦 Catalog
          </button>
          <button id="spTabRequests" onclick="spTab('requests')"
            style="flex:1;padding:12px;background:transparent;color:#94a3b8;border:none;font-size:13px;font-weight:600;cursor:pointer;">
            📋 My Requests
          </button>
        </div>

        <!-- Catalog Panel -->
        <div id="spCatalogPanel" style="flex:1;overflow-y:auto;padding:0 16px 16px;">
          <!-- Search -->
          <div style="position:sticky;top:0;background:#0f172a;padding:12px 0 8px;z-index:10;">
            <input id="spSearch" type="text" placeholder="Search spare parts…"
              style="width:100%;padding:10px 14px;background:#1e293b;border:1px solid #334155;border-radius:10px;color:#e2e8f0;font-size:14px;outline:none;box-sizing:border-box;"
              oninput="spSearchDebounce()">
          </div>

          <!-- Cart Bar -->
          <div id="spCartBar" style="display:none;background:#1e40af;border-radius:10px;padding:12px 14px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
            <span id="spCartCount" style="color:#fff;font-size:13px;font-weight:700;"></span>
            <button onclick="spSubmitSheet()"
              style="background:#fff;color:#1e40af;border:none;padding:8px 16px;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;">
              Submit Request
            </button>
          </div>

          <div id="spCatalogLoading" style="padding:40px;text-align:center;color:#64748b;">
            <div style="font-size:32px;margin-bottom:12px">⏳</div>
            <div style="font-size:13px">Loading catalog…</div>
          </div>
          <div id="spCatalogList"></div>
          <div id="spCatalogEmpty" style="display:none;padding:40px;text-align:center;color:#64748b;">
            <div style="font-size:40px;margin-bottom:12px">📦</div>
            <div style="font-size:14px;font-weight:600;color:#94a3b8">No spare parts found</div>
          </div>
        </div>

        <!-- Requests Panel -->
        <div id="spRequestsPanel" style="display:none;flex:1;overflow-y:auto;padding:16px;">
          <div id="spReqLoading" style="padding:40px;text-align:center;color:#64748b;">
            <div style="font-size:32px;margin-bottom:12px">⏳</div>
          </div>
          <div id="spReqList"></div>
          <div id="spReqEmpty" style="display:none;padding:40px;text-align:center;color:#64748b;">
            <div style="font-size:40px;margin-bottom:12px">📋</div>
            <div style="font-size:14px;font-weight:600;color:#94a3b8">No requests yet</div>
            <div style="font-size:12px;color:#64748b;margin-top:4px">Browse the catalog and submit a request</div>
          </div>
        </div>

        <!-- Submit Sheet (hidden) -->
        <div id="spSubmitSheet" style="display:none;position:fixed;bottom:0;left:0;right:0;background:#1e293b;border-radius:16px 16px 0 0;padding:20px;z-index:200;max-height:80vh;overflow-y:auto;box-shadow:0 -8px 32px rgba(0,0,0,.4);">
          <div style="width:40px;height:4px;background:#475569;border-radius:2px;margin:0 auto 16px;"></div>
          <div style="font-size:16px;font-weight:700;color:#e2e8f0;margin-bottom:14px;">Submit Spare Request</div>
          <div id="spSubmitItems" style="margin-bottom:14px;"></div>
          <select id="spSubmitCompany" style="width:100%;padding:12px;background:#0f172a;border:1px solid #334155;border-radius:10px;color:#e2e8f0;font-size:14px;margin-bottom:12px;box-sizing:border-box;">
            <option value="">Select Company…</option>
          </select>
          <textarea id="spSubmitNotes" placeholder="Notes (optional)…" rows="2"
            style="width:100%;padding:12px;background:#0f172a;border:1px solid #334155;border-radius:10px;color:#e2e8f0;font-size:14px;resize:none;margin-bottom:14px;box-sizing:border-box;"></textarea>
          <div style="display:flex;gap:10px;">
            <button onclick="document.getElementById('spSubmitSheet').style.display='none'"
              style="flex:1;padding:14px;background:#334155;color:#e2e8f0;border:none;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;">Cancel</button>
            <button onclick="spDoSubmit()"
              style="flex:2;padding:14px;background:#2563eb;color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;">
              Submit Request
            </button>
          </div>
        </div>
        <div id="spSubmitOverlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:199;" onclick="document.getElementById('spSubmitSheet').style.display='none';this.style.display='none';"></div>
      </div>`;

    // Attach global functions to window
    const self = this;
    (window as any).spTab       = (t: string) => self.switchTab(t as 'catalog' | 'requests');
    (window as any).spSearchDebounce = () => {
      if (self.searchTimer) clearTimeout(self.searchTimer);
      self.searchTimer = setTimeout(() => self.loadCatalog(), 350);
    };
    (window as any).spToggleCart = (itemId: number) => self.toggleCart(itemId);
    (window as any).spUpdateQty  = (itemId: number, val: string) => self.updateQty(itemId, parseFloat(val) || 1);
    (window as any).spSubmitSheet = () => self.openSubmitSheet();
    (window as any).spDoSubmit   = () => self.doSubmit();
    (window as any).spCancelReq  = (id: number) => self.cancelRequest(id);
  }

  private switchTab(tab: 'catalog' | 'requests'): void {
    this.activeTab = tab;
    const catalog  = document.getElementById('spCatalogPanel');
    const requests = document.getElementById('spRequestsPanel');
    const btnCat   = document.getElementById('spTabCatalog') as HTMLButtonElement;
    const btnReq   = document.getElementById('spTabRequests') as HTMLButtonElement;
    if (!catalog || !requests) return;

    if (tab === 'catalog') {
      catalog.style.display  = '';
      requests.style.display = 'none';
      btnCat.style.background  = '#2563eb'; btnCat.style.color = '#fff';
      btnReq.style.background  = 'transparent'; btnReq.style.color = '#94a3b8';
    } else {
      catalog.style.display  = 'none';
      requests.style.display = '';
      btnCat.style.background  = 'transparent'; btnCat.style.color = '#94a3b8';
      btnReq.style.background  = '#2563eb'; btnReq.style.color = '#fff';
      this.loadRequests();
    }
  }

  private async loadCompanies(): Promise<void> {
    try {
      const token  = localStorage.getItem('partner_token') || '';
      const base   = apiService.getBaseUrl();
      const r = await fetch(`${base}/api/v1/staff/accounts/companies`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) return;
      const d = await r.json();
      this.companies = d.companies || d.data || [];
    } catch { /* non-fatal */ }
  }

  private async loadCatalog(): Promise<void> {
    const token  = localStorage.getItem('partner_token') || '';
    const base   = apiService.getBaseUrl();
    const search = (document.getElementById('spSearch') as HTMLInputElement)?.value?.trim() || '';
    const loadEl = document.getElementById('spCatalogLoading');
    const listEl = document.getElementById('spCatalogList');
    const emptyEl = document.getElementById('spCatalogEmpty');
    if (loadEl)  loadEl.style.display  = '';
    if (listEl)  listEl.innerHTML      = '';
    if (emptyEl) emptyEl.style.display = 'none';

    try {
      let url = `${base}/api/v1/partner/auth/spare-catalog?limit=200`;
      if (search) url += `&search=${encodeURIComponent(search)}`;
      const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error('Auth error');
      const d = await r.json();
      this.allItems = d.items || [];
      if (loadEl)  loadEl.style.display  = 'none';
      if (!this.allItems.length) {
        if (emptyEl) emptyEl.style.display = '';
        return;
      }
      this.renderCatalog();
    } catch {
      if (loadEl)  loadEl.style.display  = 'none';
      if (emptyEl) emptyEl.style.display = '';
    }
  }

  private renderCatalog(): void {
    const listEl = document.getElementById('spCatalogList');
    if (!listEl) return;
    listEl.innerHTML = this.allItems.map(item => {
      const inCart  = this.cart.has(item.item_id);
      const cartEntry = this.cart.get(item.item_id);
      const stockColor = item.current_stock > 10 ? '#10b981' : item.current_stock > 0 ? '#f59e0b' : '#ef4444';
      const stockLabel = item.current_stock > 0 ? `${item.current_stock} in stock` : 'Out of stock';
      return `
        <div style="background:#1e293b;border-radius:12px;padding:14px 16px;margin-bottom:10px;border:1.5px solid ${inCart ? '#2563eb' : '#334155'};">
          <div style="font-size:10px;font-weight:700;color:#64748b;text-transform:uppercase;margin-bottom:2px;">${item.item_code}</div>
          <div style="font-size:15px;font-weight:700;color:#e2e8f0;margin-bottom:6px;line-height:1.3;">${item.item_name}</div>
          <div style="font-size:12px;margin-bottom:10px;">
            <span style="color:${stockColor};font-weight:600;">${stockLabel}</span>
            <span style="color:#64748b;margin-left:8px;">· ${item.unit_of_measure}</span>
          </div>
          ${inCart ? `
            <div style="display:flex;align-items:center;gap:10px;">
              <span style="font-size:12px;color:#60a5fa;font-weight:600;">✓ In Request</span>
              <input type="number" value="${cartEntry!.qty}" min="1"
                style="width:70px;padding:6px 10px;background:#0f172a;border:1px solid #2563eb;border-radius:8px;color:#e2e8f0;font-size:14px;text-align:center;"
                onchange="spUpdateQty(${item.item_id}, this.value)">
              <span style="font-size:12px;color:#64748b;">${item.unit_of_measure}</span>
              <button onclick="spToggleCart(${item.item_id})"
                style="margin-left:auto;background:#450a0a;color:#ef4444;border:none;padding:6px 12px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;">Remove</button>
            </div>` : `
            <button onclick="spToggleCart(${item.item_id})"
              style="width:100%;padding:10px;background:#1d4ed8;color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;">
              + Add to Request
            </button>`}
        </div>`;
    }).join('');
    this.updateCartBar();
  }

  private toggleCart(itemId: number): void {
    const item = this.allItems.find(i => i.item_id === itemId);
    if (!item) return;
    if (this.cart.has(itemId)) {
      this.cart.delete(itemId);
    } else {
      this.cart.set(itemId, { item, qty: 1 });
    }
    this.renderCatalog();
  }

  private updateQty(itemId: number, qty: number): void {
    const entry = this.cart.get(itemId);
    if (entry) { entry.qty = Math.max(1, qty); }
  }

  private updateCartBar(): void {
    const bar    = document.getElementById('spCartBar');
    const count  = document.getElementById('spCartCount');
    if (!bar || !count) return;
    const n = this.cart.size;
    if (n === 0) { bar.style.display = 'none'; return; }
    bar.style.display = 'flex';
    count.textContent = `${n} item${n > 1 ? 's' : ''} in request`;
  }

  private openSubmitSheet(): void {
    if (!this.cart.size) return;
    const sheet   = document.getElementById('spSubmitSheet');
    const overlay = document.getElementById('spSubmitOverlay');
    const items   = document.getElementById('spSubmitItems');
    const coSel   = document.getElementById('spSubmitCompany') as HTMLSelectElement;
    if (!sheet || !overlay || !items || !coSel) return;

    items.innerHTML = Array.from(this.cart.values()).map(e =>
      `<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #334155;">
        <span style="font-size:13px;color:#e2e8f0;">${e.item.item_name}</span>
        <span style="font-size:13px;font-weight:700;color:#60a5fa;">${e.qty} ${e.item.unit_of_measure}</span>
      </div>`
    ).join('');

    coSel.innerHTML = '<option value="">Select Company…</option>' +
      this.companies.map(c => `<option value="${c.id}">${c.company_name}</option>`).join('');

    sheet.style.display  = '';
    overlay.style.display = '';
  }

  private async doSubmit(): Promise<void> {
    const token  = localStorage.getItem('partner_token') || '';
    const base   = apiService.getBaseUrl();
    const coSel  = (document.getElementById('spSubmitCompany') as HTMLSelectElement)?.value;
    const notes  = (document.getElementById('spSubmitNotes') as HTMLTextAreaElement)?.value?.trim() || '';
    if (!coSel) { alert('Please select a company'); return; }

    const items = Array.from(this.cart.values()).map(e => ({
      item_id: e.item.item_id, quantity: e.qty, uom: e.item.unit_of_measure,
    }));

    try {
      const r = await fetch(`${base}/api/v1/partner/auth/spare-requests`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ items, notes, company_id: parseInt(coSel) }),
      });
      const d = await r.json();
      if (d.success) {
        document.getElementById('spSubmitSheet')!.style.display  = 'none';
        document.getElementById('spSubmitOverlay')!.style.display = 'none';
        this.cart.clear();
        alert(`✅ Request ${d.request?.request_number} submitted!`);
        this.switchTab('requests');
      } else {
        alert('Error: ' + (d.detail || d.message || 'Submission failed'));
      }
    } catch {
      alert('Network error. Please try again.');
    }
  }

  private async loadRequests(): Promise<void> {
    const token = localStorage.getItem('partner_token') || '';
    const base  = apiService.getBaseUrl();
    const loadEl = document.getElementById('spReqLoading');
    const listEl = document.getElementById('spReqList');
    const emptyEl = document.getElementById('spReqEmpty');
    if (loadEl)  loadEl.style.display  = '';
    if (listEl)  listEl.innerHTML      = '';
    if (emptyEl) emptyEl.style.display = 'none';

    try {
      const r = await fetch(`${base}/api/v1/partner/auth/spare-requests?limit=100`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const d = await r.json();
      this.requests = d.requests || [];
      if (loadEl)  loadEl.style.display  = 'none';
      if (!this.requests.length) {
        if (emptyEl) emptyEl.style.display = '';
        return;
      }
      this.renderRequests();
    } catch {
      if (loadEl)  loadEl.style.display  = 'none';
      if (emptyEl) emptyEl.style.display = '';
    }
  }

  private renderRequests(): void {
    const listEl = document.getElementById('spReqList');
    if (!listEl) return;
    listEl.innerHTML = this.requests.map(req => {
      const date = new Date(req.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
      const lineNames = (req.lines || []).slice(0, 2).map(l => l.item_name || l.item_code).join(', ');
      const more = (req.lines || []).length > 2 ? ` +${(req.lines || []).length - 2} more` : '';
      return `
        <div style="background:#1e293b;border-radius:12px;padding:14px 16px;margin-bottom:10px;border:1px solid #334155;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
            <div style="font-size:14px;font-weight:700;color:#60a5fa;">${req.request_number}</div>
            ${statusChip(req.status)}
          </div>
          <div style="font-size:12px;color:#94a3b8;margin-bottom:4px;">${lineNames}${more}</div>
          <div style="font-size:11px;color:#64748b;margin-bottom:10px;">${req.line_count} item(s) · ${date}</div>
          ${req.notes ? `<div style="font-size:12px;color:#94a3b8;margin-bottom:8px;">📝 ${req.notes}</div>` : ''}
          ${req.status === 'SUBMITTED' ? `
            <button onclick="spCancelReq(${req.id})"
              style="padding:8px 16px;background:#450a0a;color:#ef4444;border:1px solid #7f1d1d;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;">
              Cancel Request
            </button>` : ''}
        </div>`;
    }).join('');
  }

  private async cancelRequest(reqId: number): Promise<void> {
    if (!confirm('Cancel this spare parts request?')) return;
    const token = localStorage.getItem('partner_token') || '';
    const base  = apiService.getBaseUrl();
    try {
      const r = await fetch(`${base}/api/v1/partner/auth/spare-requests/${reqId}/cancel`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}` },
      });
      const d = await r.json();
      if (d.success) { alert('Request cancelled'); this.loadRequests(); }
      else alert('Error: ' + (d.detail || 'Could not cancel'));
    } catch { alert('Network error'); }
  }
}
