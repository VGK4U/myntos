/**
 * Call History Page
 * DC Protocol: DC_CALLHIST_001
 * Shows full call log: INCOMING, OUTGOING, MISSED, REJECTED from native call log
 * plus CRM Auto Dialer history. Filterable by type, paginated, tap-to-dial.
 */

import { apiService } from '../services/api.service';
import { dialerService } from '../services/dialer.service';
import { PageHeader } from '../components/PageHeader';

const TYPE_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
  INCOMING:  { icon: '📲', color: '#059669', label: 'Incoming' },
  OUTGOING:  { icon: '📞', color: '#0ea5e9', label: 'Outgoing' },
  MISSED:    { icon: '📵', color: '#dc2626', label: 'Missed' },
  REJECTED:  { icon: '🚫', color: '#7c3aed', label: 'Rejected' },
  DIALER:    { icon: '🎯', color: '#d97706', label: 'CRM Dialer' },
};

function fmtDuration(secs: number): string {
  if (!secs) return '';
  if (secs < 60) return `${secs}s`;
  return `${Math.floor(secs / 60)}m ${secs % 60}s`;
}

function fmtTime(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - d.getTime()) / 86400000);
  const timeStr = d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
  if (diffDays === 0) return `Today ${timeStr}`;
  if (diffDays === 1) return `Yesterday ${timeStr}`;
  if (diffDays < 7) return `${diffDays}d ago · ${timeStr}`;
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) + ` · ${timeStr}`;
}

export class CallHistoryPage {
  private container: HTMLElement;
  private activeFilter: string = 'ALL';
  private page: number = 1;
  private perPage: number = 25;
  private entries: any[] = [];
  private loading = false;
  private hasMore = true;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this._injectStyles();
    this._render();
    PageHeader.attachListeners({ title: 'Call History', showBack: true });
    await this._load(true);
  }

  cleanup(): void {}

  private async _load(reset = false): Promise<void> {
    if (this.loading) return;
    if (reset) { this.page = 1; this.entries = []; this.hasMore = true; }
    if (!this.hasMore) return;
    this.loading = true;
    this._renderContent();
    try {
      const filter = this.activeFilter === 'ALL' ? '' : `&call_type=${this.activeFilter}`;
      const res = await apiService.get<any>(`/crm/dialer/call-history?page=${this.page}&per_page=${this.perPage}${filter}`);
      const batch: any[] = res.data?.entries || res.entries || [];
      this.entries = reset ? batch : [...this.entries, ...batch];
      this.hasMore = batch.length === this.perPage;
      if (this.hasMore) this.page++;
    } catch (_) {}
    this.loading = false;
    this._renderContent();
  }

  private _render(): void {
    this.container.innerHTML = `
      ${PageHeader.render({ title: 'Call History', showBack: true })}
      <div class="ch-wrap">
        <div class="ch-filters" id="ch-filters">${this._buildFilters()}</div>
        <div class="ch-content" id="ch-content"></div>
      </div>`;
    this._attachFilterListeners();
  }

  private _buildFilters(): string {
    const tabs = [
      { key: 'ALL', label: 'All' },
      { key: 'MISSED', label: '📵 Missed' },
      { key: 'INCOMING', label: '📲 Received' },
      { key: 'OUTGOING', label: '📞 Outgoing' },
      { key: 'REJECTED', label: '🚫 Rejected' },
      { key: 'DIALER', label: '🎯 CRM Dialer' },
    ];
    return tabs.map(t => `
      <button class="ch-tab${this.activeFilter === t.key ? ' active' : ''}" data-filter="${t.key}">${t.label}</button>
    `).join('');
  }

  private _renderContent(): void {
    const el = document.getElementById('ch-content');
    if (!el) return;

    if (this.loading && this.entries.length === 0) {
      el.innerHTML = `<div class="ch-loading">Loading call history…</div>`;
      return;
    }
    if (!this.loading && this.entries.length === 0) {
      el.innerHTML = `<div class="ch-empty">No calls found${this.activeFilter !== 'ALL' ? ` for ${TYPE_CONFIG[this.activeFilter]?.label || this.activeFilter}` : ''}</div>`;
      return;
    }

    const rows = this.entries.map(e => {
      const cfg = TYPE_CONFIG[e.call_type] || TYPE_CONFIG['OUTGOING'];
      const dur = fmtDuration(e.duration_seconds || 0);
      const displayName = e.contact_name || e.name || e.phone;
      const phone = e.phone || '';
      return `
        <div class="ch-row">
          <div class="ch-type-icon" style="color:${cfg.color}">${cfg.icon}</div>
          <div class="ch-info">
            <div class="ch-name">${displayName.replace(/</g, '&lt;')}</div>
            <div class="ch-meta">
              <span style="color:${cfg.color};font-weight:600">${cfg.label}</span>
              ${e.source === 'dialer' ? `<span class="ch-crm-badge">CRM</span>` : ''}
              ${dur ? `· ${dur}` : ''}
              · ${fmtTime(e.dialed_at)}
            </div>
            ${phone ? `<div class="ch-phone">${phone}</div>` : ''}
          </div>
          <div class="ch-actions">
            ${phone ? `<button class="ch-call-btn" data-phone="${phone}" data-name="${displayName.replace(/"/g, '&quot;')}" data-lead="${e.lead_id || ''}">📞</button>` : ''}
          </div>
        </div>`;
    }).join('');

    const loadMore = this.hasMore
      ? `<button class="ch-load-more" id="ch-load-more">${this.loading ? 'Loading…' : 'Load more'}</button>`
      : '';

    el.innerHTML = `<div class="ch-list">${rows}</div>${loadMore}`;
    this._attachRowListeners();
  }

  private _attachFilterListeners(): void {
    document.querySelectorAll('.ch-tab').forEach(btn => {
      btn.addEventListener('click', async () => {
        this.activeFilter = (btn as HTMLElement).dataset.filter || 'ALL';
        const filtersEl = document.getElementById('ch-filters');
        if (filtersEl) filtersEl.innerHTML = this._buildFilters();
        this._attachFilterListeners();
        await this._load(true);
      });
    });
  }

  private _attachRowListeners(): void {
    document.querySelectorAll('.ch-call-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const phone = (btn as HTMLElement).dataset.phone!;
        const name = (btn as HTMLElement).dataset.name || 'Contact';
        const leadIdStr = (btn as HTMLElement).dataset.lead;
        // Save to local dial history and dial
        try {
          const history = JSON.parse(localStorage.getItem('dc_dial_history') || '[]');
          const entry = { phone, name, source: 'direct', call_outcome: '', dialed_at: new Date().toISOString() };
          const filtered = history.filter((h: any) => h.phone !== phone);
          filtered.unshift(entry);
          localStorage.setItem('dc_dial_history', JSON.stringify(filtered.slice(0, 20)));
        } catch (_) {}
        dialerService.dial(phone);
      });
    });

    const loadMoreBtn = document.getElementById('ch-load-more');
    if (loadMoreBtn) {
      loadMoreBtn.addEventListener('click', () => this._load(false));
    }
  }

  private _injectStyles(): void {
    if (document.getElementById('ch-styles')) return;
    const style = document.createElement('style');
    style.id = 'ch-styles';
    style.textContent = `
      .ch-wrap { display: flex; flex-direction: column; height: calc(100vh - 56px); overflow: hidden; background: #f9fafb; }
      .ch-filters { display: flex; gap: 6px; padding: 10px 14px; overflow-x: auto; background: white; border-bottom: 1px solid #e5e7eb; flex-shrink: 0; scrollbar-width: none; }
      .ch-filters::-webkit-scrollbar { display: none; }
      .ch-tab { border: 1.5px solid #e5e7eb; background: white; border-radius: 20px; padding: 6px 12px; font-size: 12px; font-weight: 600; white-space: nowrap; cursor: pointer; color: #6b7280; flex-shrink: 0; }
      .ch-tab.active { border-color: #0ea5e9; background: #eff6ff; color: #0369a1; }
      .ch-content { flex: 1; overflow-y: auto; padding: 0 0 80px; }
      .ch-list { display: flex; flex-direction: column; }
      .ch-row { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: white; border-bottom: 1px solid #f3f4f6; }
      .ch-type-icon { font-size: 22px; flex-shrink: 0; width: 30px; text-align: center; }
      .ch-info { flex: 1; min-width: 0; }
      .ch-name { font-size: 14px; font-weight: 700; color: #1f2937; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .ch-meta { font-size: 11px; color: #6b7280; margin-top: 2px; display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
      .ch-crm-badge { background: #fef9c3; color: #92400e; font-size: 9px; font-weight: 700; padding: 1px 5px; border-radius: 6px; }
      .ch-phone { font-size: 11px; color: #9ca3af; margin-top: 1px; }
      .ch-actions { flex-shrink: 0; }
      .ch-call-btn { background: #059669; color: white; border: none; border-radius: 50%; width: 36px; height: 36px; font-size: 16px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
      .ch-call-btn:active { background: #047857; }
      .ch-loading, .ch-empty { text-align: center; padding: 40px 20px; font-size: 14px; color: #9ca3af; }
      .ch-load-more { width: calc(100% - 32px); margin: 12px 16px; padding: 12px; background: #f3f4f6; border: 1px solid #e5e7eb; border-radius: 12px; font-size: 13px; font-weight: 600; color: #374151; cursor: pointer; }
    `;
    document.head.appendChild(style);
  }
}
