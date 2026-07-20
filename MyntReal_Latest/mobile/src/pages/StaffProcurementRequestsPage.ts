/**
 * Staff Procurement Requests Page — Mobile
 * DC Protocol: DC_MOBILE_PROC_REQUESTS_001
 * Web/Mobile Parity: mirrors staff_accounts_procurement.html "Procurement Requests" tab
 * Features: vendor column, updated timestamp, status actions, WhatsApp send
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface ProcurementRequestItem {
  id: number;
  item_id: number;
  item_code: string;
  item_name: string;
  item_category?: string;
  hsn_code?: string;
  brand?: string;
  model_compat?: string;
  colors?: string[];
  specification?: string;
  required_qty: number;
  unit_of_measure: string;
  specifications?: string;
}

interface ProcurementRequest {
  id: number;
  request_number: string;
  company_id: number;
  company_name: string;
  request_date: string;
  status: string;
  min_quotes_required: number;
  quotes_received_count: number;
  approved_vendor_id?: number;
  approved_vendor_name?: string;
  approved_vendor_phone?: string;
  notes?: string;
  return_notes?: string;
  created_at: string;
  updated_at: string;
  item_count: number;
  items?: ProcurementRequestItem[];
}

const STATUS_STYLES: Record<string, { bg: string; color: string }> = {
  DRAFT:                { bg: '#e5e7eb', color: '#374151' },
  SENT_TO_VENDORS:      { bg: '#dbeafe', color: '#1d4ed8' },
  QUOTES_RECEIVED:      { bg: '#ede9fe', color: '#6d28d9' },
  QUOTE_APPROVED:       { bg: '#dcfce7', color: '#15803d' },
  PO_CREATED:           { bg: '#d1fae5', color: '#059669' },
  COMPLETED:            { bg: '#bbf7d0', color: '#065f46' },
  CANCELLED:            { bg: '#fee2e2', color: '#dc2626' },
  RETURNED_FOR_QUALITY: { bg: '#fff7ed', color: '#c2410c' },
};

function statusBadge(status: string): string {
  const s = STATUS_STYLES[status] || { bg: '#f3f4f6', color: '#374151' };
  return `<span style="background:${s.bg};color:${s.color};padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;">${status.replace(/_/g,' ')}</span>`;
}

function fmtDate(dt?: string): string {
  if (!dt) return '—';
  return new Date(dt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

export class StaffProcurementRequestsPage {
  private container: HTMLElement;
  private requests: ProcurementRequest[] = [];
  private loading = true;
  private filterStatus = '';
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
      let url = '/accounts/procurement/requests?page=1&limit=50';
      if (this.filterStatus) url += `&status=${this.filterStatus}`;
      const resp = await apiService.get<any>(url);
      this.requests = resp.data || resp.requests || [];
    } catch (e) {
      console.error('[StaffProcurementRequestsPage] load error:', e);
      this.requests = [];
    }
    this.loading = false;
    this.updateList();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container" style="background:#f1f5f9;min-height:100vh;padding-bottom:80px;">
        ${PageHeader.render({ title: 'Procurement Requests', showBack: true })}

        <div style="padding:12px 14px 6px;">
          <select id="prStatusFilter" onchange="window._prFilterChange()" style="width:100%;padding:10px 12px;border:1px solid #d1d5db;border-radius:10px;font-size:13px;background:#fff;">
            <option value="">All Statuses</option>
            <option value="DRAFT">Draft</option>
            <option value="SENT_TO_VENDORS">Sent to Vendors</option>
            <option value="QUOTES_RECEIVED">Quotes Received</option>
            <option value="QUOTE_APPROVED">Quote Approved</option>
            <option value="PO_CREATED">PO Created</option>
            <option value="COMPLETED">Completed</option>
            <option value="CANCELLED">Cancelled</option>
            <option value="RETURNED_FOR_QUALITY">Returned for Quality</option>
          </select>
        </div>

        <div id="prList" style="padding:8px 14px;"></div>

        <!-- Detail sheet -->
        <div id="prDetailSheet" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:900;overflow-y:auto;">
          <div id="prDetailBox" style="background:#fff;margin:16px;border-radius:16px;overflow:hidden;box-shadow:0 20px 50px rgba(0,0,0,.3);">
            <div style="background:linear-gradient(135deg,#1e40af,#2563eb);padding:14px 18px;display:flex;justify-content:space-between;align-items:center;">
              <span id="prDetailTitle" style="color:#fff;font-size:14px;font-weight:700;"></span>
              <button onclick="window._prCloseDetail()" style="background:rgba(255,255,255,.2);border:none;color:#fff;width:28px;height:28px;border-radius:50%;font-size:16px;cursor:pointer;">✕</button>
            </div>
            <div id="prDetailBody" style="padding:16px;"></div>
          </div>
        </div>

        <!-- Status update sheet -->
        <div id="prStatusSheet" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:1000;align-items:flex-end;">
          <div style="background:#fff;border-radius:20px 20px 0 0;width:100%;padding:20px;box-shadow:0 -8px 30px rgba(0,0,0,.2);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
              <span style="font-size:15px;font-weight:700;color:#111827;">Update Status</span>
              <button onclick="window._prCloseStatus()" style="background:#f3f4f6;border:none;width:30px;height:30px;border-radius:50%;font-size:16px;">✕</button>
            </div>
            <input type="hidden" id="prStatusReqId">
            <select id="prStatusSelect" onchange="window._prStatusChange()" style="width:100%;padding:12px;border:1px solid #d1d5db;border-radius:10px;font-size:14px;margin-bottom:12px;">
              <option value="">— Select status —</option>
              <option value="COMPLETED">✅ Completed</option>
              <option value="CANCELLED">❌ Cancelled</option>
              <option value="RETURNED_FOR_QUALITY">↩ Returned for Quality</option>
            </select>
            <div id="prReturnSection" style="display:none;background:#fff7ed;border-radius:10px;padding:14px;margin-bottom:12px;border:1px solid #fed7aa;">
              <div style="font-size:13px;font-weight:700;color:#c2410c;margin-bottom:10px;">↩ Quality Return Details</div>
              <div style="display:flex;gap:16px;margin-bottom:10px;">
                <label style="display:flex;align-items:center;gap:6px;font-size:13px;">
                  <input type="radio" name="prReturnType" value="PARTIAL" checked style="accent-color:#c2410c;"> Partial
                </label>
                <label style="display:flex;align-items:center;gap:6px;font-size:13px;">
                  <input type="radio" name="prReturnType" value="COMPLETE" style="accent-color:#c2410c;"> Complete
                </label>
              </div>
              <textarea id="prReturnNotes" rows="3" style="width:100%;padding:10px;border:1px solid #fed7aa;border-radius:8px;font-size:13px;resize:none;" placeholder="Describe the quality issue and items returned…"></textarea>
            </div>
            <textarea id="prStatusNotes" rows="2" style="width:100%;padding:10px;border:1px solid #d1d5db;border-radius:10px;font-size:13px;resize:none;margin-bottom:14px;" placeholder="Additional notes (optional)…"></textarea>
            <button onclick="window._prSubmitStatus()" style="width:100%;padding:14px;background:#2563eb;color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:700;">Update Status</button>
          </div>
        </div>

        <!-- WhatsApp sheet -->
        <div id="prWASheet" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:1000;overflow-y:auto;">
          <div style="background:#fff;margin:20px 12px;border-radius:18px;overflow:hidden;box-shadow:0 20px 50px rgba(0,0,0,.3);">
            <div style="background:linear-gradient(135deg,#15803d,#22c55e);padding:16px 18px;display:flex;justify-content:space-between;align-items:center;">
              <span style="color:#fff;font-size:15px;font-weight:700;">WhatsApp Vendor</span>
              <button onclick="window._prCloseWA()" style="background:rgba(255,255,255,.2);border:none;color:#fff;width:28px;height:28px;border-radius:50%;font-size:16px;">✕</button>
            </div>
            <div style="padding:16px;">
              <div id="prWAVendorBox" style="background:#f0fdf4;border-radius:10px;padding:12px;margin-bottom:14px;border:1px solid #bbf7d0;"></div>
              <label style="font-size:13px;font-weight:600;color:#374151;display:block;margin-bottom:6px;">Message Preview (editable)</label>
              <textarea id="prWAMessage" rows="14" style="width:100%;padding:10px 12px;border:1px solid #d1d5db;border-radius:10px;font-size:12px;font-family:monospace;resize:vertical;"></textarea>
              <p style="font-size:11px;color:#9ca3af;margin-top:6px;">Full specs included. Edit as needed before sending.</p>
            </div>
            <div style="padding:14px 16px;border-top:1px solid #f3f4f6;display:flex;gap:10px;flex-wrap:wrap;">
              <button onclick="window._prOpenWebWA()" style="flex:1;padding:12px;background:#16a34a;color:#fff;border:none;border-radius:10px;font-size:13px;font-weight:700;">Open WhatsApp</button>
              <button onclick="window._prSendWAAPI()" style="flex:1;padding:12px;background:#2563eb;color:#fff;border:none;border-radius:10px;font-size:13px;font-weight:700;">Send via API</button>
            </div>
          </div>
        </div>
      </div>
    `;

    // Attach global handlers
    window._prFilterChange = () => {
      this.filterStatus = (document.getElementById('prStatusFilter') as HTMLSelectElement).value;
      this.loadRequests();
    };
    window._prStatusChange = () => {
      const val = (document.getElementById('prStatusSelect') as HTMLSelectElement).value;
      const sec = document.getElementById('prReturnSection')!;
      sec.style.display = val === 'RETURNED_FOR_QUALITY' ? 'block' : 'none';
    };
    window._prOpenStatus = (reqId: number) => this.openStatusSheet(reqId);
    window._prCloseStatus = () => {
      document.getElementById('prStatusSheet')!.style.display = 'none';
    };
    window._prSubmitStatus = () => this.submitStatus();
    window._prOpenDetail = (reqId: number) => this.openDetail(reqId);
    window._prCloseDetail = () => {
      document.getElementById('prDetailSheet')!.style.display = 'none';
    };
    window._prOpenWA = (reqId: number) => this.openWASheet(reqId);
    window._prCloseWA = () => {
      document.getElementById('prWASheet')!.style.display = 'none';
    };
    window._prOpenWebWA = () => this.doOpenWebWA();
    window._prSendWAAPI = () => this.doSendWAAPI();
  }

  private updateList(): void {
    const list = document.getElementById('prList');
    if (!list) return;

    if (this.loading) {
      list.innerHTML = `<div style="text-align:center;padding:40px;color:#9ca3af;"><div style="font-size:32px;margin-bottom:12px;">⏳</div>Loading procurement requests…</div>`;
      return;
    }
    if (!this.requests.length) {
      list.innerHTML = `<div style="text-align:center;padding:40px;color:#9ca3af;"><div style="font-size:40px;margin-bottom:12px;">📋</div><div style="font-weight:600;">No procurement requests</div><div style="font-size:12px;margin-top:4px;">Create a request from the web portal</div></div>`;
      return;
    }

    list.innerHTML = this.requests.map(r => {
      const quotePct = r.quotes_received_count >= r.min_quotes_required;
      return `
        <div style="background:#fff;border-radius:14px;margin-bottom:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08);">
          <div style="padding:14px 16px;border-bottom:1px solid #f3f4f6;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
              <div>
                <div style="font-size:13px;font-weight:700;color:#1e40af;font-family:monospace;">${r.request_number}</div>
                <div style="font-size:12px;color:#6b7280;margin-top:2px;">${r.company_name || '—'}</div>
              </div>
              ${statusBadge(r.status)}
            </div>
            <!-- Vendor row -->
            <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
              <span style="font-size:11px;color:#9ca3af;font-weight:600;">VENDOR</span>
              ${r.approved_vendor_name
                ? `<span style="font-size:12px;font-weight:700;color:#2563eb;">${r.approved_vendor_name}${r.approved_vendor_phone ? ' · ' + r.approved_vendor_phone : ''}</span>`
                : `<span style="font-size:12px;color:#d1d5db;">Not assigned yet</span>`}
            </div>
            <!-- Stats row -->
            <div style="margin-top:10px;display:flex;gap:12px;font-size:12px;color:#6b7280;">
              <span>📦 ${r.item_count || 0} items</span>
              <span style="color:${quotePct ? '#16a34a' : '#d97706'};font-weight:600;">💬 ${r.quotes_received_count}/${r.min_quotes_required} quotes</span>
              <span>🕐 ${fmtDate(r.updated_at || r.created_at)}</span>
            </div>
          </div>
          <!-- Actions -->
          <div style="padding:10px 14px;display:flex;gap:8px;flex-wrap:wrap;background:#fafafa;">
            <button onclick="window._prOpenDetail(${r.id})" style="flex:1;padding:9px 12px;background:#eff6ff;color:#2563eb;border:1px solid #bfdbfe;border-radius:8px;font-size:12px;font-weight:700;min-width:60px;">
              👁 View
            </button>
            <button onclick="window._prOpenStatus(${r.id})" style="flex:1;padding:9px 12px;background:#f3f4f6;color:#374151;border:1px solid #e5e7eb;border-radius:8px;font-size:12px;font-weight:700;min-width:60px;">
              ✏️ Status
            </button>
            <button onclick="window._prOpenWA(${r.id})" style="flex:1;padding:9px 12px;background:#dcfce7;color:#16a34a;border:1px solid #bbf7d0;border-radius:8px;font-size:12px;font-weight:700;min-width:60px;">
              💬 WA
            </button>
          </div>
        </div>
      `;
    }).join('');
  }

  private openStatusSheet(reqId: number): void {
    const req = this.requests.find(r => r.id === reqId);
    if (!req) return;
    this.selectedRequest = req;
    (document.getElementById('prStatusReqId') as HTMLInputElement).value = String(reqId);
    (document.getElementById('prStatusSelect') as HTMLSelectElement).value = '';
    (document.getElementById('prStatusNotes') as HTMLTextAreaElement).value = '';
    (document.getElementById('prReturnNotes') as HTMLTextAreaElement).value = '';
    document.getElementById('prReturnSection')!.style.display = 'none';
    const sheet = document.getElementById('prStatusSheet')!;
    sheet.style.display = 'flex';
  }

  private async submitStatus(): Promise<void> {
    const status = (document.getElementById('prStatusSelect') as HTMLSelectElement).value;
    const reqId = (document.getElementById('prStatusReqId') as HTMLInputElement).value;
    if (!status) { alert('Please select a status'); return; }

    const generalNotes = (document.getElementById('prStatusNotes') as HTMLTextAreaElement).value.trim();
    let finalNotes = generalNotes;

    if (status === 'RETURNED_FOR_QUALITY') {
      const rType = (document.querySelector('input[name="prReturnType"]:checked') as HTMLInputElement)?.value || 'PARTIAL';
      const rNotes = (document.getElementById('prReturnNotes') as HTMLTextAreaElement).value.trim();
      if (!rNotes) { alert('Please describe the quality return reason'); return; }
      finalNotes = `[${rType} RETURN] ${rNotes}${generalNotes ? '\n' + generalNotes : ''}`;
    }

    try {
      const resp: any = await apiService.put(`/accounts/procurement/requests/${reqId}/status`, {
        status, notes: finalNotes || undefined,
      });
      if (resp.success) {
        document.getElementById('prStatusSheet')!.style.display = 'none';
        this._showToast(`Status updated to ${status.replace(/_/g,' ')}`, '#16a34a');
        await this.loadRequests();
      } else {
        alert('Error: ' + (resp.detail || resp.message || 'Update failed'));
      }
    } catch (e: any) {
      alert('Network error: ' + e.message);
    }
  }

  private async openDetail(reqId: number): Promise<void> {
    document.getElementById('prDetailSheet')!.style.display = 'block';
    document.getElementById('prDetailTitle')!.textContent = 'Loading…';
    document.getElementById('prDetailBody')!.innerHTML = `<div style="text-align:center;padding:30px;color:#9ca3af;">⏳ Loading…</div>`;

    try {
      const resp: any = await apiService.get(`/accounts/procurement/requests/${reqId}`);
      const r: ProcurementRequest = resp.data || resp;
      document.getElementById('prDetailTitle')!.textContent = r.request_number;

      const items = r.items || [];
      document.getElementById('prDetailBody')!.innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px;font-size:13px;">
          <div><span style="color:#9ca3af;font-size:11px;font-weight:700;">COMPANY</span><br><strong>${r.company_name || '—'}</strong></div>
          <div><span style="color:#9ca3af;font-size:11px;font-weight:700;">STATUS</span><br>${statusBadge(r.status)}</div>
          <div><span style="color:#9ca3af;font-size:11px;font-weight:700;">VENDOR</span><br><strong style="color:#2563eb;">${r.approved_vendor_name || '—'}</strong>${r.approved_vendor_phone ? `<br><span style="color:#6b7280;font-size:12px;">📱 ${r.approved_vendor_phone}</span>` : ''}</div>
          <div><span style="color:#9ca3af;font-size:11px;font-weight:700;">UPDATED</span><br><span style="font-size:12px;">${fmtDate(r.updated_at)}</span></div>
          <div><span style="color:#9ca3af;font-size:11px;font-weight:700;">QUOTES</span><br><strong style="color:${r.quotes_received_count >= r.min_quotes_required ? '#16a34a' : '#d97706'};">${r.quotes_received_count}/${r.min_quotes_required}</strong></div>
          <div><span style="color:#9ca3af;font-size:11px;font-weight:700;">DATE</span><br><span style="font-size:12px;">${fmtDate(r.request_date)}</span></div>
        </div>
        ${r.notes ? `<div style="background:#f9fafb;border-radius:8px;padding:10px 12px;margin-bottom:14px;font-size:13px;"><strong>Notes:</strong> ${r.notes}</div>` : ''}
        ${r.return_notes ? `<div style="background:#fff7ed;border-radius:8px;padding:10px 12px;margin-bottom:14px;font-size:13px;border:1px solid #fed7aa;"><strong style="color:#c2410c;">↩ Return Notes:</strong> ${r.return_notes}</div>` : ''}
        <div style="font-size:13px;font-weight:700;color:#374151;margin-bottom:10px;">📦 Items Required (${items.length})</div>
        ${items.map((it, i) => `
          <div style="background:#f9fafb;border-radius:10px;padding:12px;margin-bottom:8px;border:1px solid #e5e7eb;">
            <div style="font-size:13px;font-weight:700;color:#111827;">${i + 1}. ${it.item_name || it.item_code}</div>
            <div style="font-size:11px;color:#9ca3af;margin-top:2px;font-family:monospace;">${it.item_code}</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px;font-size:12px;">
              <div><span style="color:#9ca3af;">Qty:</span> <strong>${it.required_qty} ${it.unit_of_measure}</strong></div>
              ${it.hsn_code ? `<div><span style="color:#9ca3af;">HSN:</span> <strong>${it.hsn_code}</strong></div>` : ''}
              ${it.item_category ? `<div><span style="color:#9ca3af;">Category:</span> ${it.item_category}</div>` : ''}
              ${it.brand ? `<div><span style="color:#9ca3af;">Brand:</span> <strong>${it.brand}</strong></div>` : ''}
              ${it.model_compat ? `<div style="grid-column:1/-1"><span style="color:#9ca3af;">Model/Compat:</span> ${it.model_compat}</div>` : ''}
              ${it.colors && it.colors.length ? `<div><span style="color:#9ca3af;">Colour:</span> ${it.colors.join(', ')}</div>` : ''}
            </div>
            ${it.specification ? `<div style="margin-top:8px;padding:8px 10px;background:#eff6ff;border-radius:6px;font-size:12px;color:#1e40af;border:1px solid #bfdbfe;"><span style="font-weight:700;">Spec (Master):</span> ${it.specification}</div>` : ''}
            ${it.specifications ? `<div style="margin-top:6px;padding:8px 10px;background:#fff;border-radius:6px;font-size:12px;color:#374151;border:1px solid #e5e7eb;"><span style="color:#9ca3af;font-weight:700;">Additional Notes:</span> ${it.specifications}</div>` : ''}
          </div>
        `).join('')}
      `;
    } catch (e) {
      document.getElementById('prDetailBody')!.innerHTML = `<div style="color:#dc2626;padding:16px;">Failed to load details</div>`;
    }
  }

  private _waCurrentReqId: number | null = null;

  private async openWASheet(reqId: number): Promise<void> {
    this._waCurrentReqId = reqId;
    document.getElementById('prWASheet')!.style.display = 'block';
    document.getElementById('prWAVendorBox')!.innerHTML = '⏳ Loading vendor info…';
    (document.getElementById('prWAMessage') as HTMLTextAreaElement).value = '';

    try {
      const resp: any = await apiService.get(`/accounts/procurement/requests/${reqId}`);
      const r: ProcurementRequest = resp.data || resp;
      this.selectedRequest = r;

      if (!r.approved_vendor_id) {
        document.getElementById('prWAVendorBox')!.innerHTML = `<span style="color:#92400e;font-size:13px;">⚠ No approved vendor. Approve a quote first.</span>`;
        (document.getElementById('prWAMessage') as HTMLTextAreaElement).value = '';
        return;
      }

      document.getElementById('prWAVendorBox')!.innerHTML = `
        <div style="font-size:11px;color:#16a34a;font-weight:700;text-transform:uppercase;margin-bottom:4px;">Vendor</div>
        <div style="font-size:15px;font-weight:700;color:#111827;">${r.approved_vendor_name}</div>
        ${r.approved_vendor_phone ? `<div style="font-size:12px;color:#6b7280;margin-top:2px;">📱 ${r.approved_vendor_phone}</div>` : `<div style="font-size:12px;color:#dc2626;margin-top:2px;">⚠ No phone on file</div>`}
      `;

      const items = r.items || [];
      const itemLines = items.map((it, i) => {
        let line = `${i + 1}. *${it.item_name || it.item_code}*`;
        if (it.item_code) line += ` (Code: ${it.item_code})`;
        line += `\n   Qty: ${it.required_qty} ${it.unit_of_measure}`;
        if (it.item_category) line += `\n   Category: ${it.item_category}`;
        if (it.hsn_code) line += `\n   HSN: ${it.hsn_code}`;
        if (it.brand) line += `\n   Brand: ${it.brand}`;
        if (it.model_compat) line += `\n   Model/Compatible With: ${it.model_compat}`;
        if (it.colors && it.colors.length) line += `\n   Colour: ${it.colors.join(', ')}`;
        if (it.specification) line += `\n   Specification: ${it.specification}`;
        if (it.specifications) line += `\n   Additional Notes: ${it.specifications}`;
        return line;
      }).join('\n\n');

      const today = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
      const companyName = r.company_name || 'MyntReal LLP';
      const msg = `Dear ${r.approved_vendor_name},\n\nWe have a Procurement Request from *${companyName}* and would like your best quotation.\n\nRequest Details:\n• Request No: *${r.request_number}*\n• Date: ${r.request_date || today}\n• Company: ${companyName}\n${r.notes ? '• Notes: ' + r.notes + '\n' : ''}\n*Items Required:*\n\n${itemLines || 'Please refer attached document.'}\n\nKindly share your proforma invoice with unit rate, taxes (GST), delivery terms and expected delivery date at the earliest.\n\nThank you,\n${companyName} Procurement Team`;

      (document.getElementById('prWAMessage') as HTMLTextAreaElement).value = msg;
    } catch (e) {
      document.getElementById('prWAVendorBox')!.innerHTML = `<span style="color:#dc2626;">Failed to load request details</span>`;
    }
  }

  private doOpenWebWA(): void {
    const msg = (document.getElementById('prWAMessage') as HTMLTextAreaElement).value;
    const phone = (this.selectedRequest?.approved_vendor_phone || '').replace(/\D/g, '');
    if (phone) {
      const full = phone.startsWith('91') ? phone : '91' + phone;
      window.open(`https://wa.me/${full}?text=${encodeURIComponent(msg)}`, '_blank');
    } else {
      if (navigator.clipboard) navigator.clipboard.writeText(msg).catch(() => {});
      window.open('https://web.whatsapp.com', '_blank');
      this._showToast('No phone on file — message copied, paste in WhatsApp Web', '#d97706');
    }
  }

  private async doSendWAAPI(): Promise<void> {
    if (!this._waCurrentReqId) return;
    const msg = (document.getElementById('prWAMessage') as HTMLTextAreaElement).value;
    try {
      const resp: any = await apiService.post(`/accounts/procurement/requests/${this._waCurrentReqId}/whatsapp`, { message: msg });
      if (resp.success) {
        document.getElementById('prWASheet')!.style.display = 'none';
        this._showToast('WhatsApp sent to vendor!', '#16a34a');
      } else {
        this._showToast('API not configured — opening WhatsApp Web', '#d97706');
        this.doOpenWebWA();
      }
    } catch (e) {
      this.doOpenWebWA();
    }
  }

  private _showToast(msg: string, bg: string): void {
    const t = document.createElement('div');
    t.style.cssText = `position:fixed;top:20px;right:16px;left:16px;background:${bg};color:#fff;padding:12px 16px;border-radius:12px;z-index:9999;font-weight:700;font-size:13px;text-align:center;box-shadow:0 6px 20px rgba(0,0,0,.2);`;
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 4000);
  }
}

declare global {
  interface Window {
    _prFilterChange: () => void;
    _prStatusChange: () => void;
    _prOpenStatus: (id: number) => void;
    _prCloseStatus: () => void;
    _prSubmitStatus: () => void;
    _prOpenDetail: (id: number) => void;
    _prCloseDetail: () => void;
    _prOpenWA: (id: number) => void;
    _prCloseWA: () => void;
    _prOpenWebWA: () => void;
    _prSendWAAPI: () => void;
  }
}
