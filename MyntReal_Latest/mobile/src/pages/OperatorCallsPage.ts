/**
 * Operator Calls Dashboard Page (Mobile)
 * DC Protocol: DC_OPERATOR_CALLS_001
 * Full-featured: Active/Answered/Missed tabs, Call Detail view, Caller History,
 * Click-to-Dial, Follow Up creation, Convert to Lead, Lead info, Add Note,
 * Bulk match, Manual sync.
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface OperatorCall {
  id: number;
  call_id: string;
  caller_number: string;
  called_number: string;
  operator_name: string;
  operator_number: string;
  call_type: string;
  status: string;
  started_at: string | null;
  answered_at: string | null;
  ended_at: string | null;
  duration_seconds: number;
  recording_url: string | null;
  crm_lead_id: number | null;
  followup_created: boolean;
  followup_id: number | null;
  lead_matched: boolean;
  lead_name?: string;
  lead_status?: string;
  lead_source?: string;
}

const STATUS_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  ringing: { bg: '#fef3c7', color: '#d97706', label: 'Ringing' },
  active:  { bg: '#d1fae5', color: '#059669', label: 'Active' },
  answered:{ bg: '#d1fae5', color: '#059669', label: 'Answered' },
  missed:  { bg: '#fee2e2', color: '#dc2626', label: 'Missed' },
  ended:   { bg: '#f3f4f6', color: '#6b7280', label: 'Ended' },
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

function esc(s: string): string {
  return (s || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

export class OperatorCallsPage {
  private container: HTMLElement;
  private activeTab: 'active' | 'answered' | 'missed' = 'active';
  private calls: OperatorCall[] = [];
  private stats = { active: 0, answered: 0, missed: 0 };
  private page = 1;
  private hasMore = true;
  private loading = false;
  private autoRefresh: ReturnType<typeof setInterval> | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this._injectStyles();
    this._render();
    PageHeader.attachListeners({ title: 'Operator Calls', showBack: true });
    await this._load(true);
    this._startAutoRefresh();
  }

  cleanup(): void {
    if (this.autoRefresh) { clearInterval(this.autoRefresh); this.autoRefresh = null; }
    document.querySelectorAll('.opc-modal-overlay').forEach(el => el.remove());
  }

  private _startAutoRefresh(): void {
    this.autoRefresh = setInterval(async () => {
      if (this.activeTab === 'active' && !this.loading) await this._load(true);
    }, 15000);
  }

  private async _load(reset = false): Promise<void> {
    if (this.loading) return;
    if (reset) { this.page = 1; this.calls = []; this.hasMore = true; }
    if (!this.hasMore) return;
    this.loading = true;
    this._renderContent();

    try {
      const statusParam = this.activeTab === 'active' ? 'active' : this.activeTab;
      const res = await apiService.get<any>(`/operator-calls/?status=${statusParam}&page=${this.page}&per_page=20`);
      const data = (res as any).data || res;

      if (data?.stats) { this.stats = data.stats; this._updateStats(); }
      const batch: OperatorCall[] = data?.data || [];
      this.calls = reset ? batch : [...this.calls, ...batch];
      const pagination = data?.pagination;
      this.hasMore = pagination ? this.page < pagination.pages : batch.length >= 20;
      if (this.hasMore) this.page++;
    } catch (_) {}
    this.loading = false;
    this._renderContent();
  }

  private _render(): void {
    this.container.innerHTML = `
      ${PageHeader.render({ title: 'Operator Calls', showBack: true })}
      <div class="opcalls-wrap">
        <div class="opcalls-stats">
          <div class="opcalls-stat-card purple"><div class="opc-val" id="opc-active">0</div><div class="opc-lbl">Active</div></div>
          <div class="opcalls-stat-card green"><div class="opc-val" id="opc-answered">0</div><div class="opc-lbl">Answered</div></div>
          <div class="opcalls-stat-card red"><div class="opc-val" id="opc-missed">0</div><div class="opc-lbl">Missed</div></div>
        </div>
        <div class="opcalls-tabs">
          <button class="opc-tab active" data-tab="active"><span class="opc-pulse"></span> Active</button>
          <button class="opc-tab" data-tab="answered">Answered</button>
          <button class="opc-tab" data-tab="missed">Missed</button>
        </div>
        <div class="opc-action-bar">
          <button class="opc-action-btn" id="opc-sync-btn">Sync Now</button>
          <button class="opc-action-btn" id="opc-match-btn">Bulk Match</button>
        </div>
        <div id="opcalls-content"></div>
        <div id="opcalls-loadmore" style="display:none;padding:12px;text-align:center;">
          <button class="opc-loadmore-btn" id="opc-load-btn">Load More</button>
        </div>
      </div>`;

    this._attachTabListeners();
    this._attachActionListeners();
  }

  private _attachTabListeners(): void {
    this.container.querySelectorAll('.opc-tab').forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = (btn as HTMLElement).dataset.tab as 'active' | 'answered' | 'missed';
        this.activeTab = tab;
        this.container.querySelectorAll('.opc-tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this._load(true);
      });
    });
    this.container.querySelector('#opc-load-btn')?.addEventListener('click', () => this._load(false));
  }

  private _attachActionListeners(): void {
    this.container.querySelector('#opc-sync-btn')?.addEventListener('click', async () => {
      const btn = this.container.querySelector('#opc-sync-btn') as HTMLButtonElement;
      btn.textContent = 'Syncing...'; btn.disabled = true;
      try {
        const res = await apiService.post<any>('/operator-calls/sync', {});
        const d = (res as any).data || res;
        alert(`Sync: ${d?.result?.synced || 0} calls synced`);
        this._load(true);
      } catch (_) { alert('Sync failed'); }
      btn.textContent = 'Sync Now'; btn.disabled = false;
    });

    this.container.querySelector('#opc-match-btn')?.addEventListener('click', async () => {
      const btn = this.container.querySelector('#opc-match-btn') as HTMLButtonElement;
      btn.textContent = 'Matching...'; btn.disabled = true;
      try {
        const res = await apiService.post<any>('/operator-calls/bulk-match', {});
        const d = (res as any).data || res;
        alert(`${d?.matched || 0} calls matched to leads`);
        this._load(true);
      } catch (_) { alert('Match failed'); }
      btn.textContent = 'Bulk Match'; btn.disabled = false;
    });
  }

  private _updateStats(): void {
    const el = (id: string) => this.container.querySelector(`#${id}`);
    const a = el('opc-active'); const ans = el('opc-answered'); const m = el('opc-missed');
    if (a) a.textContent = String(this.stats.active || 0);
    if (ans) ans.textContent = String(this.stats.answered || 0);
    if (m) m.textContent = String(this.stats.missed || 0);
  }

  private _renderContent(): void {
    const content = this.container.querySelector('#opcalls-content') as HTMLElement;
    const loadmore = this.container.querySelector('#opcalls-loadmore') as HTMLElement;
    if (!content) return;

    if (this.loading && this.calls.length === 0) {
      content.innerHTML = `<div class="opc-loading"><div class="opc-spinner"></div> Loading calls...</div>`;
      return;
    }
    if (!this.loading && this.calls.length === 0) {
      content.innerHTML = `<div class="opc-empty"><div style="font-size:36px;opacity:0.3;">📵</div><div>No ${this.activeTab} calls found</div></div>`;
      if (loadmore) loadmore.style.display = 'none';
      return;
    }

    content.innerHTML = this.calls.map(c => this._renderCard(c)).join('');
    if (loadmore) loadmore.style.display = this.hasMore ? 'block' : 'none';
    this._attachCardActions();
  }

  private _renderCard(c: OperatorCall): string {
    const s = STATUS_STYLE[c.status] || STATUS_STYLE.ended;
    const isActive = ['ringing', 'active'].includes(c.status);
    const duration = fmtDuration(c.duration_seconds);
    const time = fmtTime(c.started_at || (c as any).created_at || null);
    const cid = esc(c.call_id);
    const cphone = esc(c.caller_number || '');

    let leadHtml = '';
    if (c.crm_lead_id) {
      leadHtml = `<div class="opc-lead-tag">${c.lead_name || `Lead #${c.crm_lead_id}`}</div>`;
    }

    return `<div class="opc-card" data-callid="${cid}">
      <div class="opc-card-header">
        <div style="display:flex;align-items:center;gap:6px;">
          ${isActive ? '<span class="opc-pulse-dot"></span>' : ''}
          <span class="opc-badge" style="background:${s.bg};color:${s.color};">${s.label}</span>
          <span style="font-size:11px;color:#9ca3af;text-transform:uppercase;">${c.call_type || 'inbound'}</span>
        </div>
        <div style="font-size:12px;color:#9ca3af;">${time}</div>
      </div>
      <div class="opc-card-body" data-action="detail" data-callid="${cid}">
        <div class="opc-phone">${c.caller_number || '—'}</div>
        ${c.called_number ? `<div class="opc-phone-small">→ ${c.called_number}</div>` : ''}
        ${c.operator_name ? `<div style="font-size:12px;color:#6b7280;margin-top:2px;">Operator: ${c.operator_name}</div>` : ''}
        ${duration ? `<div style="font-size:12px;color:#6b7280;margin-top:2px;">⏱ ${duration}</div>` : ''}
        ${leadHtml}
      </div>
      <div class="opc-card-actions">
        <a href="tel:${c.caller_number}" class="opc-btn opc-btn-dial">📞 Dial</a>
        <button class="opc-btn opc-btn-detail" data-action="detail" data-callid="${cid}">👁 Details</button>
        <button class="opc-btn opc-btn-history" data-action="history" data-phone="${cphone}">📋 History</button>
        ${c.status === 'missed' || !c.crm_lead_id ? `<button class="opc-btn opc-btn-followup" data-action="followup" data-callid="${cid}" data-phone="${cphone}">📅 Follow Up</button>` : ''}
        ${!c.crm_lead_id ? `<button class="opc-btn opc-btn-lead" data-action="lead" data-callid="${cid}" data-phone="${cphone}">👤 Lead</button>` : ''}
        ${c.recording_url ? `<a href="${c.recording_url}" target="_blank" class="opc-btn opc-btn-record">🎙️ Rec</a>` : ''}
      </div>
    </div>`;
  }

  private _attachCardActions(): void {
    this.container.querySelectorAll('[data-action]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const el = btn as HTMLElement;
        const action = el.dataset.action;
        const callId = el.dataset.callid || '';
        const phone = el.dataset.phone || '';

        if (action === 'detail') this._showDetailModal(callId);
        else if (action === 'history') this._showHistoryModal(phone);
        else if (action === 'followup') this._showFollowupModal(callId, phone);
        else if (action === 'lead') this._showLeadModal(callId, phone);
      });
    });
  }

  // ── Detail Modal ──────────────────────────────────────────────────────────

  private async _showDetailModal(callId: string): Promise<void> {
    const overlay = this._createOverlay();
    overlay.innerHTML = `<div class="opc-modal"><div class="opc-loading"><div class="opc-spinner"></div> Loading...</div></div>`;
    document.body.appendChild(overlay);

    try {
      const res = await apiService.get<any>(`/operator-calls/${callId}/detail`);
      const data = (res as any).data || res;
      if (!data?.success && !data?.data) { overlay.querySelector('.opc-modal')!.innerHTML = '<p style="color:red;padding:16px;">Failed to load.</p>'; return; }
      const c = data.data || data;
      const s = STATUS_STYLE[c.status] || STATUS_STYLE.ended;

      let html = `<h3>📞 Call Details</h3>`;
      html += `<div class="opc-detail-grid">
        <div><span class="opc-detail-label">Status</span><span class="opc-badge" style="background:${s.bg};color:${s.color};">${s.label}</span></div>
        <div><span class="opc-detail-label">Type</span><span>${(c.call_type||'inbound').toUpperCase()}</span></div>
        <div><span class="opc-detail-label">Caller</span><a href="tel:${c.caller_number}" style="color:#059669;font-weight:600;">${c.caller_number||'—'}</a></div>
        <div><span class="opc-detail-label">Called</span><span>${c.called_number||'—'}</span></div>
        <div><span class="opc-detail-label">Operator</span><span>${c.operator_name||'—'}</span></div>
        <div><span class="opc-detail-label">Duration</span><span>${fmtDuration(c.duration_seconds)}</span></div>
        <div><span class="opc-detail-label">Started</span><span>${fmtTime(c.started_at)}</span></div>
        <div><span class="opc-detail-label">Ended</span><span>${fmtTime(c.ended_at)}</span></div>
      </div>`;

      if (c.recording_url) {
        html += `<div style="margin:10px 0;display:flex;align-items:center;gap:8px;"><span class="opc-detail-label" style="margin:0;">Recording</span>
          <a href="${c.recording_url}" target="_blank" rel="noopener" class="opc-btn opc-btn-record" style="font-size:12px;padding:5px 12px;">🎙️ Open Recording</a></div>`;
      }

      html += `<div class="opc-detail-actions">
        <a href="tel:${c.caller_number}" class="opc-btn opc-btn-dial">📞 Dial</a>
        <button class="opc-btn opc-btn-history" id="dtl-hist-btn">📋 History (${c.caller_total_calls || 1})</button>`;
      if (!c.crm_lead_id) {
        html += `<button class="opc-btn opc-btn-lead" id="dtl-lead-btn">👤 Convert Lead</button>`;
        if (c.potential_lead) {
          html += `<button class="opc-btn opc-btn-match" id="dtl-match-btn">🔗 Link ${c.potential_lead.name}</button>`;
        }
      }
      html += `</div>`;

      if (c.caller_stats) {
        const cs = c.caller_stats;
        html += `<div style="margin-top:12px;"><span class="opc-detail-label">CALLER STATISTICS</span>
          <div class="opc-detail-grid">
            <div><span class="opc-detail-label">Total</span><span style="font-weight:700;">${cs.total_calls}</span></div>
            <div><span class="opc-detail-label">Answered</span><span style="color:#059669;font-weight:700;">${cs.answered}</span></div>
            <div><span class="opc-detail-label">Missed</span><span style="color:#dc2626;font-weight:700;">${cs.missed}</span></div>
            <div><span class="opc-detail-label">Talk Time</span><span style="font-weight:700;">${fmtDuration(cs.total_duration)}</span></div>
          </div></div>`;
      }

      if (c.lead) {
        const l = c.lead;
        html += `<div class="opc-lead-panel">
          <div class="opc-lead-panel-title">Linked CRM Lead #${l.id}</div>
          <div class="opc-lead-row"><span>Name</span><span style="font-weight:600;">${l.name||'—'}</span></div>
          <div class="opc-lead-row"><span>Phone</span><span>${l.phone||'—'}</span></div>
          <div class="opc-lead-row"><span>Status</span><span>${l.status||'—'}</span></div>
          <div class="opc-lead-row"><span>Source</span><span>${l.source||'—'}</span></div>`;
        if (l.followups?.length) {
          html += `<div class="opc-detail-label" style="margin-top:8px;">Follow-ups</div>`;
          l.followups.slice(0,3).forEach((fu: any) => {
            html += `<div class="opc-fu-item"><span>${fu.subject||'Follow-up'} · ${fmtTime(fu.scheduled_date)}</span><span style="font-weight:600;color:${fu.status==='completed'?'#059669':'#f59e0b'};">${fu.status}</span></div>`;
          });
        }
        if (l.notes?.length) {
          html += `<div class="opc-detail-label" style="margin-top:8px;">Notes</div>`;
          l.notes.slice(0,3).forEach((n: any) => {
            html += `<div class="opc-note-item">${n.note}<div style="font-size:10px;color:#9ca3af;margin-top:2px;">${fmtTime(n.created_at)}</div></div>`;
          });
        }
        html += `<div style="margin-top:8px;display:flex;gap:6px;">
          <button class="opc-btn opc-btn-followup" id="dtl-fu-btn">📅 Follow Up</button>
          <button class="opc-btn opc-btn-note" id="dtl-note-btn">📝 Add Note</button>
        </div></div>`;
      } else if (c.potential_lead) {
        const pl = c.potential_lead;
        html += `<div class="opc-lead-panel" style="background:#fef3c7;border-color:#fde68a;">
          <div class="opc-lead-panel-title" style="color:#b45309;">⚠️ Potential Match</div>
          <div class="opc-lead-row"><span>Name</span><span style="font-weight:600;">${pl.name||'—'}</span></div>
          <div class="opc-lead-row"><span>Phone</span><span>${pl.phone||'—'}</span></div>
        </div>`;
      }

      if (c.caller_history?.length) {
        html += `<div style="margin-top:12px;"><span class="opc-detail-label">PREVIOUS CALLS (${c.caller_history.length})</span>
          <div class="opc-history-list">`;
        c.caller_history.slice(0,10).forEach((h: any) => {
          const hs = STATUS_STYLE[h.status] || STATUS_STYLE.ended;
          html += `<div class="opc-history-item">
            <span class="opc-badge" style="background:${hs.bg};color:${hs.color};font-size:10px;">${hs.label}</span>
            <span>${fmtDuration(h.duration_seconds)} · ${fmtTime(h.started_at||h.created_at)}</span>
          </div>`;
        });
        html += `</div></div>`;
      }

      html += `<button class="opc-btn-close" id="dtl-close">Close</button>`;

      const modal = overlay.querySelector('.opc-modal')!;
      modal.innerHTML = html;

      modal.querySelector('#dtl-close')?.addEventListener('click', () => overlay.remove());
      modal.querySelector('#dtl-hist-btn')?.addEventListener('click', () => { overlay.remove(); this._showHistoryModal(c.caller_number); });
      modal.querySelector('#dtl-lead-btn')?.addEventListener('click', () => { overlay.remove(); this._showLeadModal(c.call_id, c.caller_number); });
      modal.querySelector('#dtl-match-btn')?.addEventListener('click', async () => {
        try {
          await apiService.post<any>(`/operator-calls/${c.call_id}/match-lead`, {});
          alert('Lead linked!'); overlay.remove(); this._load(true);
        } catch (_) { alert('Match failed'); }
      });
      modal.querySelector('#dtl-fu-btn')?.addEventListener('click', () => { overlay.remove(); this._showFollowupModal(c.call_id, c.caller_number); });
      modal.querySelector('#dtl-note-btn')?.addEventListener('click', () => { overlay.remove(); this._showNoteModal(c.call_id); });

    } catch (_) {
      overlay.querySelector('.opc-modal')!.innerHTML = '<p style="color:red;padding:16px;">Error loading details.</p><button class="opc-btn-close" onclick="this.closest(\'.opc-modal-overlay\').remove()">Close</button>';
    }
  }

  // ── Caller History Modal ──────────────────────────────────────────────────

  private async _showHistoryModal(phone: string): Promise<void> {
    if (!phone) return;
    const overlay = this._createOverlay();
    overlay.innerHTML = `<div class="opc-modal"><div class="opc-loading"><div class="opc-spinner"></div> Loading history...</div></div>`;
    document.body.appendChild(overlay);

    try {
      const res = await apiService.get<any>(`/operator-calls/caller-history/${encodeURIComponent(phone)}`);
      const data = (res as any).data || res;
      if (!data?.success && !data?.data) { overlay.querySelector('.opc-modal')!.innerHTML = '<p style="color:red;padding:16px;">Failed.</p>'; return; }

      let html = `<h3>📋 Call History — ${phone}</h3>`;
      html += `<a href="tel:${phone}" class="opc-btn opc-btn-dial" style="margin-bottom:10px;display:inline-flex;">📞 Dial ${phone}</a>`;

      if (data.lead) {
        const l = data.lead;
        html += `<div class="opc-lead-panel">
          <div class="opc-lead-panel-title">CRM Lead #${l.id}</div>
          <div class="opc-lead-row"><span>Name</span><span style="font-weight:600;">${l.name||'—'}</span></div>
          <div class="opc-lead-row"><span>Status</span><span>${l.status||'—'}</span></div>
          <div class="opc-lead-row"><span>Source</span><span>${l.source||'—'}</span></div>
        </div>`;
      }

      const s = data.stats || {};
      html += `<div class="opc-detail-grid">
        <div><span class="opc-detail-label">Total</span><span style="font-weight:700;">${s.total||0}</span></div>
        <div><span class="opc-detail-label">Answered</span><span style="color:#059669;font-weight:700;">${s.answered||0}</span></div>
        <div><span class="opc-detail-label">Missed</span><span style="color:#dc2626;font-weight:700;">${s.missed||0}</span></div>
        <div><span class="opc-detail-label">Talk Time</span><span style="font-weight:700;">${fmtDuration(s.total_duration)}</span></div>
      </div>`;

      const calls = data.data || [];
      if (calls.length) {
        html += `<div class="opc-history-list" style="max-height:50vh;">`;
        calls.forEach((c: any) => {
          const hs = STATUS_STYLE[c.status] || STATUS_STYLE.ended;
          html += `<div class="opc-history-item" data-action="detail" data-callid="${esc(c.call_id)}">
            <div style="display:flex;align-items:center;gap:6px;">
              <span class="opc-badge" style="background:${hs.bg};color:${hs.color};font-size:10px;">${hs.label}</span>
              <span style="font-size:11px;color:#9ca3af;">${(c.call_type||'inbound').toUpperCase()}</span>
              ${c.operator_name ? `<span style="font-size:11px;color:#6b7280;">${c.operator_name}</span>` : ''}
            </div>
            <div style="font-size:12px;color:#6b7280;">${fmtDuration(c.duration_seconds)} · ${fmtTime(c.started_at||c.created_at)}</div>
          </div>`;
        });
        html += `</div>`;
      } else {
        html += `<p style="color:#9ca3af;text-align:center;margin-top:20px;">No calls found.</p>`;
      }

      html += `<button class="opc-btn-close" id="hist-close">Close</button>`;

      const modal = overlay.querySelector('.opc-modal')!;
      modal.innerHTML = html;
      modal.querySelector('#hist-close')?.addEventListener('click', () => overlay.remove());
      modal.querySelectorAll('[data-action="detail"]').forEach(el => {
        el.addEventListener('click', () => { overlay.remove(); this._showDetailModal((el as HTMLElement).dataset.callid || ''); });
      });

    } catch (_) {
      overlay.querySelector('.opc-modal')!.innerHTML = '<p style="color:red;padding:16px;">Error.</p><button class="opc-btn-close" onclick="this.closest(\'.opc-modal-overlay\').remove()">Close</button>';
    }
  }

  // ── Follow-up Modal ───────────────────────────────────────────────────────

  private _showFollowupModal(callId: string, phone: string): void {
    const overlay = this._createOverlay();
    const now = new Date(); now.setHours(now.getHours() + 2);
    const defaultDate = now.toISOString().slice(0, 16);

    overlay.innerHTML = `<div class="opc-modal">
      <h3>📅 Create Follow-Up</h3>
      <label class="opc-detail-label">Caller</label>
      <input type="text" class="opc-input" value="${phone}" readonly>
      <label class="opc-detail-label">Subject</label>
      <input type="text" class="opc-input" id="fu-subject-m" value="Follow up on missed call from ${phone}">
      <label class="opc-detail-label">Scheduled Date</label>
      <input type="datetime-local" class="opc-input" id="fu-date-m" value="${defaultDate}">
      <label class="opc-detail-label">Notes</label>
      <textarea class="opc-input" id="fu-notes-m" rows="3" placeholder="Add notes..."></textarea>
      <div class="opc-modal-actions">
        <button class="opc-btn-cancel" id="fu-cancel-m">Cancel</button>
        <button class="opc-btn-submit" id="fu-submit-m">Create</button>
      </div>
    </div>`;

    document.body.appendChild(overlay);
    overlay.querySelector('#fu-cancel-m')?.addEventListener('click', () => overlay.remove());
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
    overlay.querySelector('#fu-submit-m')?.addEventListener('click', async () => {
      const body = {
        subject: (overlay.querySelector('#fu-subject-m') as HTMLInputElement)?.value,
        scheduled_date: (overlay.querySelector('#fu-date-m') as HTMLInputElement)?.value,
        notes: (overlay.querySelector('#fu-notes-m') as HTMLTextAreaElement)?.value,
      };
      try {
        await apiService.post<any>(`/operator-calls/${callId}/create-followup`, body);
        overlay.remove(); alert('Follow-up created!'); this._load(true);
      } catch (_) { alert('Failed.'); }
    });
  }

  // ── Lead Modal ────────────────────────────────────────────────────────────

  private _showLeadModal(callId: string, phone: string): void {
    const overlay = this._createOverlay();
    overlay.innerHTML = `<div class="opc-modal">
      <h3>👤 Convert to Lead</h3>
      <label class="opc-detail-label">Caller</label>
      <input type="text" class="opc-input" value="${phone}" readonly>
      <label class="opc-detail-label">Contact Name</label>
      <input type="text" class="opc-input" id="lead-name-m" placeholder="Enter name...">
      <div class="opc-modal-actions">
        <button class="opc-btn-cancel" id="lead-cancel-m">Cancel</button>
        <button class="opc-btn-submit" id="lead-submit-m">Create Lead</button>
      </div>
    </div>`;

    document.body.appendChild(overlay);
    overlay.querySelector('#lead-cancel-m')?.addEventListener('click', () => overlay.remove());
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
    overlay.querySelector('#lead-submit-m')?.addEventListener('click', async () => {
      const name = (overlay.querySelector('#lead-name-m') as HTMLInputElement)?.value;
      try {
        const res = await apiService.post<any>(`/operator-calls/${callId}/convert-lead`, { name: name || undefined });
        const d = (res as any).data || res;
        overlay.remove(); alert(`Lead created! ID: ${d?.lead_id}`); this._load(true);
      } catch (_) { alert('Failed.'); }
    });
  }

  // ── Note Modal ────────────────────────────────────────────────────────────

  private _showNoteModal(callId: string): void {
    const overlay = this._createOverlay();
    overlay.innerHTML = `<div class="opc-modal">
      <h3>📝 Add Note</h3>
      <label class="opc-detail-label">Note</label>
      <textarea class="opc-input" id="note-text-m" rows="4" placeholder="Enter note..."></textarea>
      <div class="opc-modal-actions">
        <button class="opc-btn-cancel" id="note-cancel-m">Cancel</button>
        <button class="opc-btn-submit" id="note-submit-m">Save</button>
      </div>
    </div>`;

    document.body.appendChild(overlay);
    overlay.querySelector('#note-cancel-m')?.addEventListener('click', () => overlay.remove());
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
    overlay.querySelector('#note-submit-m')?.addEventListener('click', async () => {
      const note = (overlay.querySelector('#note-text-m') as HTMLTextAreaElement)?.value?.trim();
      if (!note) { alert('Note is required.'); return; }
      try {
        await apiService.post<any>(`/operator-calls/${callId}/add-note`, { note });
        overlay.remove(); alert('Note added!');
      } catch (_) { alert('Failed.'); }
    });
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  private _createOverlay(): HTMLDivElement {
    const overlay = document.createElement('div');
    overlay.className = 'opc-modal-overlay';
    return overlay;
  }

  private _injectStyles(): void {
    if (document.getElementById('opcalls-styles')) return;
    const style = document.createElement('style');
    style.id = 'opcalls-styles';
    style.textContent = `
      .opcalls-wrap { padding: 12px; padding-bottom: 80px; }

      .opcalls-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 14px; }
      .opcalls-stat-card { background: white; border-radius: 10px; padding: 12px 8px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
      .opcalls-stat-card.purple { border-top: 3px solid #7c3aed; }
      .opcalls-stat-card.green { border-top: 3px solid #059669; }
      .opcalls-stat-card.red { border-top: 3px solid #dc2626; }
      .opc-val { font-size: 22px; font-weight: 700; color: #1f2937; }
      .opc-lbl { font-size: 10px; color: #9ca3af; text-transform: uppercase; font-weight: 600; }

      .opcalls-tabs { display: flex; background: white; border-radius: 10px; padding: 5px; gap: 4px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
      .opc-tab { flex: 1; padding: 8px 4px; border: none; background: transparent; border-radius: 7px; font-size: 13px; font-weight: 600; color: #6b7280; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 4px; }
      .opc-tab.active { background: #7c3aed; color: white; }

      .opc-action-bar { display: flex; gap: 8px; margin-bottom: 14px; }
      .opc-action-btn { flex: 1; padding: 8px; border: 1px solid #e5e7eb; border-radius: 8px; background: white; font-size: 12px; font-weight: 600; color: #374151; cursor: pointer; }

      .opc-pulse { display: inline-block; width: 7px; height: 7px; background: currentColor; border-radius: 50%; animation: opcPulse 1.5s infinite; }
      .opc-pulse-dot { display: inline-block; width: 8px; height: 8px; background: #059669; border-radius: 50%; animation: opcPulse 1.5s infinite; }
      @keyframes opcPulse { 0% { box-shadow: 0 0 0 0 rgba(124,58,237,0.5); } 70% { box-shadow: 0 0 0 6px rgba(124,58,237,0); } 100% { box-shadow: 0 0 0 0 rgba(124,58,237,0); } }

      .opc-card { background: white; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); overflow: hidden; }
      .opc-card-header { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; border-bottom: 1px solid #f3f4f6; }
      .opc-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
      .opc-card-body { padding: 10px 14px; cursor: pointer; }
      .opc-phone { font-size: 16px; font-weight: 600; color: #1f2937; font-family: monospace; }
      .opc-phone-small { font-size: 12px; color: #6b7280; font-family: monospace; }
      .opc-lead-tag { display: inline-block; margin-top: 4px; padding: 2px 8px; background: #f5f3ff; color: #7c3aed; border-radius: 6px; font-size: 11px; font-weight: 600; }
      .opc-card-actions { display: flex; gap: 6px; flex-wrap: wrap; padding: 10px 14px; border-top: 1px solid #f3f4f6; background: #fafafa; }

      .opc-btn { padding: 6px 12px; border-radius: 7px; font-size: 12px; font-weight: 600; border: 1px solid; cursor: pointer; white-space: nowrap; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; background: white; color: #374151; border-color: #e5e7eb; }
      .opc-btn-dial { border-color: #059669; color: #047857; background: #d1fae5; }
      .opc-btn-detail { border-color: #6b7280; color: #374151; background: #f9fafb; }
      .opc-btn-history { border-color: #8b5cf6; color: #6d28d9; background: #ede9fe; }
      .opc-btn-followup { border-color: #f59e0b; color: #b45309; background: #fffbeb; }
      .opc-btn-lead { border-color: #7c3aed; color: #5b21b6; background: #f5f3ff; }
      .opc-btn-record { border-color: #0ea5e9; color: #0284c7; background: #f0f9ff; }
      .opc-btn-match { border-color: #7c3aed; color: #5b21b6; background: #f5f3ff; }
      .opc-btn-note { border-color: #f59e0b; color: #b45309; background: #fffbeb; }

      .opc-loading { text-align: center; padding: 40px; color: #9ca3af; }
      .opc-spinner { display: inline-block; width: 24px; height: 24px; border: 3px solid #e5e7eb; border-top-color: #7c3aed; border-radius: 50%; animation: opcSpin 0.8s linear infinite; margin-right: 8px; }
      @keyframes opcSpin { to { transform: rotate(360deg); } }
      .opc-empty { text-align: center; padding: 40px 20px; color: #9ca3af; }
      .opc-loadmore-btn { padding: 10px 24px; border-radius: 8px; border: 1px solid #7c3aed; background: white; color: #7c3aed; font-size: 13px; font-weight: 600; cursor: pointer; }

      .opc-modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.55); z-index: 1000; display: flex; align-items: flex-end; justify-content: center; }
      .opc-modal { background: white; border-radius: 16px 16px 0 0; padding: 20px; width: 100%; max-height: 92vh; overflow-y: auto; }
      .opc-modal h3 { font-size: 17px; font-weight: 700; margin-bottom: 14px; color: #1f2937; }

      .opc-detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 10px 0; }
      .opc-detail-grid > div { display: flex; flex-direction: column; gap: 2px; }
      .opc-detail-label { font-size: 10px; font-weight: 600; color: #9ca3af; text-transform: uppercase; display: block; margin-top: 6px; }
      .opc-detail-actions { display: flex; gap: 6px; flex-wrap: wrap; margin: 10px 0; }

      .opc-lead-panel { background: #f5f3ff; border-radius: 10px; padding: 12px; margin: 10px 0; border: 1px solid #ede9fe; }
      .opc-lead-panel-title { font-size: 13px; font-weight: 700; color: #5b21b6; margin-bottom: 6px; }
      .opc-lead-row { display: flex; justify-content: space-between; font-size: 12px; padding: 2px 0; }
      .opc-fu-item { display: flex; justify-content: space-between; align-items: center; background: #f0f9ff; border-radius: 6px; padding: 6px 8px; margin: 3px 0; font-size: 11px; }
      .opc-note-item { background: #fffbeb; border-radius: 6px; padding: 6px 8px; margin: 3px 0; font-size: 12px; }

      .opc-history-list { max-height: 250px; overflow-y: auto; margin: 8px 0; }
      .opc-history-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; border-bottom: 1px solid #f3f4f6; cursor: pointer; }
      .opc-history-item:active { background: #faf5ff; }

      .opc-input { width: 100%; padding: 9px 12px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 14px; margin-top: 4px; }
      .opc-modal-actions { display: flex; gap: 10px; margin-top: 16px; }
      .opc-btn-cancel { flex: 1; padding: 11px; border: 1px solid #e5e7eb; border-radius: 8px; background: white; color: #374151; font-size: 14px; cursor: pointer; }
      .opc-btn-submit { flex: 2; padding: 11px; border: none; border-radius: 8px; background: #7c3aed; color: white; font-size: 14px; font-weight: 600; cursor: pointer; }
      .opc-btn-close { width: 100%; padding: 12px; border: none; border-radius: 8px; background: #f3f4f6; color: #374151; font-size: 14px; font-weight: 600; cursor: pointer; margin-top: 12px; }
    `;
    document.head.appendChild(style);
  }
}
