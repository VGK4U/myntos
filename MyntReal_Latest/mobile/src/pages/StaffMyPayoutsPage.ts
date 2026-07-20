/**
 * Staff My Performance Payouts Page — Mobile Parity
 * DC Protocol: DC_MOBILE_STAFF_PERF_PAYOUTS_001
 * Web parity: /staff/my-lead-incentives → Performance Payouts tab
 * Endpoint: GET /api/v1/staff/incentive-payouts/my-summary?year=YYYY
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface PerfPayout {
  month: number;
  year: number;
  total_incentive: number;
  payout_status: string;
  due_date: string | null;
  cleared_at: string | null;
  company_name: string;
}

interface PayoutSummary {
  total: number;
  pending: number;
  cleared: number;
}

const MONTH_NAMES = ['', 'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'];

function fmt(n: number): string {
  return '₹' + Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function statusBadge(s: string): string {
  if (s === 'cleared')   return '<span style="background:#d1fae5;color:#065f46;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600">Cleared</span>';
  if (s === 'in_progress') return '<span style="background:#dbeafe;color:#1e40af;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600">In Progress</span>';
  return '<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600">Pending</span>';
}

export class StaffMyPayoutsPage {
  private container: HTMLElement;
  private data: PerfPayout[] = [];
  private summary: PayoutSummary = { total: 0, pending: 0, cleared: 0 };
  private loading: boolean = true;
  private year: number = new Date().getFullYear();

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadPayouts();
  }

  private async loadPayouts(): Promise<void> {
    this.loading = true;
    this.updateContent();
    try {
      const res = await apiService.get<any>(`/staff/incentive-payouts/my-summary?year=${this.year}`);
      if (res.success) {
        this.data    = res.data    || [];
        this.summary = res.summary || { total: 0, pending: 0, cleared: 0 };
      }
    } catch (err) {
      console.error('[StaffMyPayouts] Load failed:', err);
    }
    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    const curYear = new Date().getFullYear();
    const yearOpts = [curYear, curYear - 1, curYear - 2]
      .map(y => `<option value="${y}"${y === this.year ? ' selected' : ''}>${y}</option>`)
      .join('');

    this.container.innerHTML = `
      <div class="page-container" style="background:#f3f4f6;min-height:100vh;padding-bottom:80px">
        ${PageHeader.render({ title: 'Performance Payouts', showBack: true })}
        <div style="padding:16px">
          <!-- Year filter -->
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">
            <label style="font-size:13px;color:#6b7280;font-weight:600">Year</label>
            <select id="payout-year-sel" style="border:1px solid #d1d5db;border-radius:8px;padding:6px 10px;font-size:13px;background:white">
              ${yearOpts}
            </select>
            <button id="payout-load-btn" style="padding:6px 14px;background:#6366f1;color:white;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer">
              Load
            </button>
          </div>
          <!-- Summary cards -->
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px" id="payout-summary">
            <div style="background:linear-gradient(135deg,#667eea,#764ba2);border-radius:12px;padding:14px;text-align:center;color:white">
              <div style="font-size:10px;opacity:0.85;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px">Total</div>
              <div id="payout-total" style="font-size:1.1rem;font-weight:700">₹0</div>
            </div>
            <div style="background:linear-gradient(135deg,#f7971e,#ffd200);border-radius:12px;padding:14px;text-align:center;color:white">
              <div style="font-size:10px;opacity:0.85;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px">Pending</div>
              <div id="payout-pending" style="font-size:1.1rem;font-weight:700">₹0</div>
            </div>
            <div style="background:linear-gradient(135deg,#11998e,#38ef7d);border-radius:12px;padding:14px;text-align:center;color:white">
              <div style="font-size:10px;opacity:0.85;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px">Cleared</div>
              <div id="payout-cleared" style="font-size:1.1rem;font-weight:700">₹0</div>
            </div>
          </div>
          <!-- Payout list -->
          <div id="payout-list"></div>
        </div>
      </div>`;

    document.getElementById('payout-year-sel')?.addEventListener('change', (e) => {
      this.year = parseInt((e.target as HTMLSelectElement).value);
    });
    document.getElementById('payout-load-btn')?.addEventListener('click', () => {
      this.loadPayouts();
    });
    PageHeader.attachBackHandler();
  }

  private updateContent(): void {
    const listEl = document.getElementById('payout-list');
    if (!listEl) return;

    document.getElementById('payout-total')!.textContent   = fmt(this.summary.total);
    document.getElementById('payout-pending')!.textContent = fmt(this.summary.pending);
    document.getElementById('payout-cleared')!.textContent = fmt(this.summary.cleared);

    if (this.loading) {
      listEl.innerHTML = `<div style="text-align:center;padding:40px;color:#6b7280">
        <div class="loading-spinner" style="width:32px;height:32px;border:3px solid #e5e7eb;border-top-color:#6366f1;border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto 12px"></div>
        Loading payouts…
      </div>`;
      return;
    }

    if (!this.data.length) {
      listEl.innerHTML = `<div style="text-align:center;padding:48px 20px;color:#9ca3af">
        <div style="font-size:2.5rem;margin-bottom:12px">📭</div>
        <div style="font-weight:600">No performance payouts for ${this.year}</div>
        <div style="font-size:12px;margin-top:6px">Payouts are created by HR/Accounts after monthly calculation</div>
      </div>`;
      return;
    }

    listEl.innerHTML = this.data.map(p => {
      const dateLabel = p.cleared_at
        ? 'Cleared: ' + new Date(p.cleared_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
        : (p.due_date ? 'Due: ' + new Date(p.due_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—');
      return `
        <div style="background:white;border-radius:12px;padding:16px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08)">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
            <div>
              <div style="font-weight:700;font-size:15px;color:#1f2937">${MONTH_NAMES[p.month]} ${p.year}</div>
              <div style="font-size:11px;color:#9ca3af;margin-top:2px">${p.company_name}</div>
            </div>
            <div style="text-align:right">
              <div style="font-size:18px;font-weight:700;color:#1f2937">${fmt(p.total_incentive)}</div>
              <div style="margin-top:4px">${statusBadge(p.payout_status)}</div>
            </div>
          </div>
          <div style="font-size:11px;color:#6b7280;border-top:1px solid #f3f4f6;padding-top:8px">${dateLabel}</div>
        </div>`;
    }).join('');
  }
}
