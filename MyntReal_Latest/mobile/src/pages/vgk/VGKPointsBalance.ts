/**
 * VGK4U Points Balance — Mobile Page
 * DC Protocol: DC_MOBILE_VGK4U_PARITY_001 · DC_VGK_POINTS_VIEW_001
 *
 * Web-Mobile Parity: mirrors the VGK Dashboard Points tab.
 * Shows summary cards + paginated ledger + View bottom-sheet with income breakdown.
 * Only PAID entries (reference_type='VGK_CASH_INCOME') trigger a points debit.
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface IncomeEntry {
  entry_number: string;
  commission_amount: number;
  admin_charges: number;
  tds_amount: number;
  net_payout: number;
  payment_mode?: string;
  payment_utr?: string;
  paid_at?: string;
  kind?: string;
}

interface LedgerRow {
  id: number;
  date?: string;
  type: 'DEBIT' | 'CREDIT';
  description?: string;
  reason_code?: string;
  points_credit: number;
  points_debit: number;
  balance_after: number;
  running_balance: number;
  notes?: string;
  reference_type?: string;
  reference_id?: number;
  used_at?: string;
  income_entry?: IncomeEntry | null;
}

interface Summary {
  total_credits: number;
  total_debits: number;
  income_debits: number;
  available_balance: number;
  pending_points?: number;
}

interface PointsResponse {
  success: boolean;
  summary: Summary;
  entries?: LedgerRow[];
  total_entries?: number;
  page?: number;
  page_size?: number;
}

function esc(s: unknown): string {
  return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function fmtDate(iso?: string): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch { return iso; }
}

function fmtNum(n: number): string {
  return n.toLocaleString('en-IN');
}

function fmtMoney(n: number): string {
  return n.toLocaleString('en-IN', { minimumFractionDigits: 2 });
}

export class VGKPointsBalancePage {
  private container: HTMLElement;
  private rows: LedgerRow[] = [];
  private summary: Summary = { total_credits: 0, total_debits: 0, income_debits: 0, available_balance: 0 };
  private page = 1;
  private pageSize = 30;
  private totalEntries = 0;
  private loading = false;
  private currentFilter: 'all' | 'credit' | 'debit' = 'all';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async render(): Promise<string> {
    return `
      ${PageHeader.render({ title: 'Points Balance', showBack: true })}
      <div id="vgk-pts-root" style="padding:12px;background:#f6f9fc;min-height:100vh">
        <div id="vgk-pts-summary" style="margin-bottom:14px">
          <div style="display:flex;gap:8px">
            ${['', '', ''].map(() => `<div style="flex:1;height:70px;background:#e2e8f0;border-radius:10px;animation:shimmer 1.2s infinite"></div>`).join('')}
          </div>
        </div>
        <div id="vgk-pts-filter" style="display:flex;gap:6px;margin-bottom:12px;overflow-x:auto;padding-bottom:4px"></div>
        <div id="vgk-pts-list" style="display:flex;flex-direction:column;gap:8px">
          ${[1,2,3,4,5].map(() => `<div style="height:56px;background:#e2e8f0;border-radius:10px;animation:shimmer 1.2s infinite"></div>`).join('')}
        </div>
        <div id="vgk-pts-loadmore" style="text-align:center;margin-top:12px;display:none">
          <button id="vgk-pts-more-btn" style="background:#7c3aed;color:#fff;border:none;border-radius:8px;padding:10px 24px;font-size:13px;font-weight:700;cursor:pointer">
            Load More
          </button>
        </div>
      </div>

      <!-- View Detail Bottom Sheet -->
      <div id="vgk-pts-sheet" style="display:none;position:fixed;inset:0;z-index:9999">
        <div id="vgk-pts-overlay" style="position:absolute;inset:0;background:rgba(0,0,0,.5)"></div>
        <div id="vgk-pts-panel" style="position:absolute;bottom:0;left:0;right:0;background:#fff;border-radius:20px 20px 0 0;max-height:90vh;overflow-y:auto;padding:0 0 env(safe-area-inset-bottom,16px)">
          <div style="padding:12px 20px 0;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #f1f5f9;margin-bottom:0">
            <div style="font-size:15px;font-weight:800;color:#1e1b4b">Transaction Detail</div>
            <button id="vgk-pts-close" style="background:none;border:none;font-size:22px;color:#6b7280;cursor:pointer;padding:4px">×</button>
          </div>
          <div id="vgk-pts-sheet-body" style="padding:16px 16px 20px"></div>
        </div>
      </div>

      <style>
        @keyframes shimmer { 0%{opacity:1} 50%{opacity:.5} 100%{opacity:1} }
      </style>
    `;
  }

  async afterRender(): Promise<void> {
    await this._load(true);

    document.getElementById('vgk-pts-overlay')?.addEventListener('click', () => this._closeSheet());
    document.getElementById('vgk-pts-close')?.addEventListener('click', () => this._closeSheet());
    document.getElementById('vgk-pts-more-btn')?.addEventListener('click', () => this._loadMore());
  }

  private async _load(reset: boolean): Promise<void> {
    if (this.loading) return;
    this.loading = true;
    if (reset) { this.page = 1; this.rows = []; }

    try {
      const data = await apiService.get<PointsResponse>(
        `/vgk/dashboard/points?page=${this.page}&page_size=${this.pageSize}`
      ) as unknown as PointsResponse;
      if (!data.success) throw new Error('API error');

      this.summary = data.summary;
      this.totalEntries = data.total_entries ?? (data as any).total ?? 0;
      const newRows: LedgerRow[] = data.entries ?? (data as any).data ?? [];
      this.rows = reset ? newRows : [...this.rows, ...newRows];

      this._renderSummary();
      this._renderFilters();
      this._renderList();
      this._toggleLoadMore();
    } catch (e) {
      document.getElementById('vgk-pts-list')!.innerHTML = `
        <div style="text-align:center;padding:32px;color:#dc2626;font-size:13px">
          Failed to load points history. Please try again.
        </div>`;
    } finally {
      this.loading = false;
    }
  }

  private async _loadMore(): Promise<void> {
    this.page++;
    await this._load(false);
  }

  private _renderSummary(): void {
    const s = this.summary;
    const pendPts = s.pending_points || 0;
    const pendCard = pendPts > 0
      ? `<div style="background:#fff;border:1.5px solid #fde68a;border-radius:12px;padding:12px 10px;text-align:center">
          <div style="font-size:9px;color:#92400e;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Pending Points</div>
          <div style="font-size:15px;font-weight:800;color:#d97706">${fmtNum(pendPts)}</div>
          <div style="font-size:9px;color:#6b7280">pts · awaiting payment</div>
        </div>`
      : '';
    document.getElementById('vgk-pts-summary')!.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">
        <div style="background:#fff;border:1.5px solid #d1fae5;border-radius:12px;padding:12px 10px;text-align:center">
          <div style="font-size:9px;color:#4c1d95;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Points In Total</div>
          <div style="font-size:15px;font-weight:800;color:#7c3aed">${fmtNum(s.total_credits)}</div>
          <div style="font-size:9px;color:#7c3aed;opacity:.8">pts</div>
        </div>
        <div style="background:#fff;border:1.5px solid #fee2e2;border-radius:12px;padding:12px 10px;text-align:center">
          <div style="font-size:9px;color:#991b1b;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Points Used Total</div>
          <div style="font-size:15px;font-weight:800;color:#dc2626">${fmtNum(s.income_debits||0)}</div>
          <div style="font-size:9px;color:#dc2626;opacity:.8">pts</div>
        </div>
        <div style="background:linear-gradient(135deg,#5b21b6,#7c3aed);border-radius:12px;padding:12px 10px;text-align:center;box-shadow:0 2px 8px rgba(124,58,237,.25);grid-column:1/-1">
          <div style="font-size:9px;color:#e9d5ff;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Points Final Balance</div>
          <div style="font-size:22px;font-weight:900;color:#fff">${fmtNum(s.available_balance)}</div>
          <div style="font-size:9px;color:#c4b5fd">pts &nbsp;(1 pt = ₹1 discount)</div>
        </div>
        ${pendCard}
      </div>
      <div style="background:#faf5ff;border:1px solid #e9d5ff;border-radius:10px;padding:8px 12px;font-size:11px;color:#5b21b6;text-align:center;font-weight:600">
        <i class="fas fa-info-circle me-1"></i>1 VGK Point = ₹1 · Points debited only at payment confirmation
      </div>
    `;
  }

  private _renderFilters(): void {
    const filters: { key: 'all'|'credit'|'debit'; label: string; icon: string }[] = [
      { key: 'all',    label: 'All',     icon: 'fa-th-large' },
      { key: 'credit', label: 'Credits', icon: 'fa-arrow-up' },
      { key: 'debit',  label: 'Debits',  icon: 'fa-arrow-down' },
    ];
    const el = document.getElementById('vgk-pts-filter');
    if (!el) return;
    el.innerHTML = filters.map(f => `
      <button data-filter="${f.key}"
        style="flex-shrink:0;border:1.5px solid ${this.currentFilter===f.key?'#7c3aed':'#e2e8f0'};
               background:${this.currentFilter===f.key?'#7c3aed':'#fff'};
               color:${this.currentFilter===f.key?'#fff':'#374151'};
               border-radius:20px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;white-space:nowrap">
        <i class="fas ${f.icon} me-1"></i>${f.label}
      </button>
    `).join('');
    el.querySelectorAll('button[data-filter]').forEach(btn => {
      btn.addEventListener('click', () => {
        this.currentFilter = (btn as HTMLElement).dataset.filter as typeof this.currentFilter;
        this._renderFilters();
        this._renderList();
      });
    });
  }

  private _filtered(): LedgerRow[] {
    if (this.currentFilter === 'credit') return this.rows.filter(r => r.points_credit > 0);
    if (this.currentFilter === 'debit')  return this.rows.filter(r => r.points_debit > 0);
    return this.rows;
  }

  private _renderList(): void {
    const el = document.getElementById('vgk-pts-list');
    if (!el) return;
    const visible = this._filtered();
    if (!visible.length) {
      el.innerHTML = `<div style="text-align:center;padding:32px;color:#6b7280;font-size:13px">No entries found.</div>`;
      return;
    }
    el.innerHTML = visible.map((r, idx) => {
      const isDebit = r.points_debit > 0;
      const amt     = isDebit ? r.points_debit : r.points_credit;
      const hasView = !!r.income_entry;
      return `
        <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid ${isDebit?'#dc2626':'#059669'};
                    border-radius:10px;padding:10px 12px;display:flex;align-items:center;gap:10px">
          <div style="width:34px;height:34px;border-radius:50%;background:${isDebit?'#fee2e2':'#d1fae5'};
                      display:flex;align-items:center;justify-content:center;flex-shrink:0">
            <i class="fas ${isDebit?'fa-minus':'fa-plus'}" style="font-size:13px;color:${isDebit?'#dc2626':'#059669'}"></i>
          </div>
          <div style="flex:1;min-width:0">
            <div style="font-size:12px;font-weight:700;color:#1f2937;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
              ${esc(r.description || '—')}
            </div>
            <div style="font-size:10px;color:#6b7280;margin-top:1px">
              ${fmtDate(r.date)}
              ${r.used_at ? `· <span style="color:#7c3aed">${esc(r.used_at)}</span>` : ''}
            </div>
          </div>
          <div style="text-align:right;flex-shrink:0">
            <div style="font-size:14px;font-weight:900;color:${isDebit?'#dc2626':'#059669'}">
              ${isDebit?'−':'+'}${fmtNum(amt)}
            </div>
            <div style="font-size:10px;color:#7c3aed;font-weight:700">
              Bal: ${fmtNum(r.running_balance)}
            </div>
          </div>
          <button data-row="${idx}"
            style="background:#f5f3ff;border:1px solid #c4b5fd;color:#7c3aed;border-radius:8px;
                   padding:5px 8px;font-size:10px;font-weight:700;cursor:pointer;flex-shrink:0;
                   white-space:nowrap">
            <i class="fas fa-eye"></i> View
          </button>
        </div>
      `;
    }).join('');

    el.querySelectorAll('button[data-row]').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx = parseInt((btn as HTMLElement).dataset.row ?? '0', 10);
        this._openSheet(visible[idx]);
      });
    });
  }

  private _toggleLoadMore(): void {
    const el = document.getElementById('vgk-pts-loadmore');
    if (!el) return;
    const loaded = this.page * this.pageSize;
    el.style.display = loaded < this.totalEntries ? 'block' : 'none';
  }

  private _openSheet(r: LedgerRow): void {
    const isDebit = r.points_debit > 0;
    const amt     = isDebit ? r.points_debit : r.points_credit;
    const ie       = r.income_entry;

    // DC_VGK_POINTS_VIEW_001: Income breakdown only for PAID advance debit rows
    const incomeHtml = (isDebit && ie) ? (() => {
      const gross    = Number(ie.commission_amount ?? 0);
      const admin    = Number(ie.admin_charges ?? 0);
      const tds      = Number(ie.tds_amount ?? 0);
      const net      = Number(ie.net_payout ?? 0);
      const paidDate = ie.paid_at ? fmtDate(ie.paid_at) : '—';
      const mode     = ie.payment_mode === 'BANK' ? '🏦 Bank Transfer'
                     : ie.payment_mode === 'CASH' ? '💵 Cash'
                     : (ie.payment_mode ?? '—');
      return `
        <div style="background:#faf5ff;border:1.5px solid #e9d5ff;border-radius:10px;padding:14px;margin-bottom:12px">
          <div style="font-size:10px;font-weight:800;color:#5b21b6;text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px">
            <i class="fas fa-solar-panel me-1"></i>Solar Advance Income Breakdown
          </div>
          <div style="font-size:10px;color:#6b7280;font-weight:600;margin-bottom:2px">Entry No.</div>
          <div style="font-size:12px;font-weight:700;color:#111827;margin-bottom:10px;font-family:monospace">${esc(ie.entry_number ?? '—')}</div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">
            <div style="background:#fff;border-radius:8px;padding:8px;border:1px solid #e9d5ff">
              <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:2px">Gross Income</div>
              <div style="font-size:14px;font-weight:900;color:#111827">₹${fmtMoney(gross)}</div>
            </div>
            <div style="background:#fff;border-radius:8px;padding:8px;border:1px solid #e9d5ff">
              <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:2px">Pts Debited</div>
              <div style="font-size:14px;font-weight:900;color:#dc2626">−${fmtNum(amt)}</div>
            </div>
          </div>

          <div style="background:#fff;border-radius:8px;padding:10px;border:1px solid #e9d5ff;margin-bottom:8px">
            <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:6px">Deduction Breakup</div>
            ${[
              ['Gross Income', `₹${fmtMoney(gross)}`, '#111827'],
              ['Admin Charges (8%)', `−₹${fmtMoney(admin)}`, '#dc2626'],
              ['TDS (2%)', `−₹${fmtMoney(tds)}`, '#dc2626'],
            ].map(([label, val, color], i) => `
              <div style="display:flex;justify-content:space-between;font-size:11px;padding:3px 0;${i<2?'border-bottom:1px dashed #e9d5ff':''}">
                <span style="color:#374151">${label}</span>
                <span style="font-weight:700;color:${color}">${val}</span>
              </div>
            `).join('')}
            <div style="display:flex;justify-content:space-between;font-size:12px;padding:6px 0 0;font-weight:900">
              <span style="color:#059669">Net Paid Out</span>
              <span style="color:#059669">₹${fmtMoney(net)}</span>
            </div>
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
            <div style="background:#fff;border-radius:8px;padding:8px;border:1px solid #e9d5ff">
              <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:2px">Payment Mode</div>
              <div style="font-size:11px;font-weight:700;color:#1f2937">${esc(mode)}</div>
            </div>
            <div style="background:#fff;border-radius:8px;padding:8px;border:1px solid #e9d5ff">
              <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:2px">Paid Date</div>
              <div style="font-size:11px;font-weight:700;color:#1f2937">${esc(paidDate)}</div>
            </div>
            ${ie.payment_utr ? `
            <div style="background:#fff;border-radius:8px;padding:8px;border:1px solid #e9d5ff;grid-column:1/-1">
              <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:2px">UTR / Reference</div>
              <div style="font-size:11px;font-weight:700;color:#1f2937;font-family:monospace;word-break:break-all">${esc(ie.payment_utr)}</div>
            </div>` : ''}
          </div>
        </div>`;
    })() : '';

    document.getElementById('vgk-pts-sheet-body')!.innerHTML = `
      ${incomeHtml}
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px">
        <div style="background:#f9fafb;border-radius:8px;padding:10px">
          <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:3px">Date</div>
          <div style="font-size:13px;font-weight:700;color:#111827">${fmtDate(r.date)}</div>
        </div>
        <div style="background:#f9fafb;border-radius:8px;padding:10px">
          <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:3px">Type</div>
          <div style="font-size:12px;font-weight:700;color:${isDebit?'#dc2626':'#059669'}">${isDebit?'Points Used':'Points Credited'}</div>
        </div>
        <div style="background:#f9fafb;border-radius:8px;padding:10px">
          <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:3px">Amount</div>
          <div style="font-size:18px;font-weight:900;color:${isDebit?'#dc2626':'#059669'}">${isDebit?'−':'+'}${fmtNum(amt)} pts</div>
        </div>
        <div style="background:#f9fafb;border-radius:8px;padding:10px">
          <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:3px">Balance After</div>
          <div style="font-size:18px;font-weight:900;color:#7c3aed">${fmtNum(r.running_balance)} pts</div>
        </div>
      </div>
      <div style="margin-bottom:8px">
        <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:3px">Description</div>
        <div style="font-size:13px;color:#1f2937;font-weight:500">${esc(r.description ?? '—')}</div>
      </div>
      ${r.used_at ? `<div style="margin-bottom:8px">
        <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:3px">Used At</div>
        <div style="font-size:13px;color:#5b21b6;font-weight:600">${esc(r.used_at)}</div>
      </div>` : ''}
      ${r.notes ? `<div style="background:#f5f3ff;border-radius:8px;padding:10px;font-size:11px;color:#374151;line-height:1.6">
        <i class="fas fa-sticky-note me-1" style="color:#7c3aed"></i>${esc(r.notes)}
      </div>` : ''}
    `;

    document.getElementById('vgk-pts-sheet')!.style.display = 'block';
    document.body.style.overflow = 'hidden';
  }

  private _closeSheet(): void {
    document.getElementById('vgk-pts-sheet')!.style.display = 'none';
    document.body.style.overflow = '';
  }
}

export default VGKPointsBalancePage;
