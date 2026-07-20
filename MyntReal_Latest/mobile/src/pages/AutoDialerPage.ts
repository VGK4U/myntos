/**
 * Auto Dialer Page
 * DC Protocol: DC_DIALER_PAGE_001
 * Prioritized CRM call queue with session controls, after-call popup with full lead edit.
 * Supports Staff and MNR portals. Web sync via polling. Native call-end auto-detection.
 */

import { dialerService, QueueItem, CallOutcome } from '../services/dialer.service';
import { apiService } from '../services/api.service';
import { authService } from '../services/auth.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';
import { vgkBannerService } from '../services/vgk-banner.service';

const LEAD_STATUSES = [
  { value: 'new', label: 'New' },
  { value: 'contacted', label: 'Contacted' },
  { value: 'interested', label: 'Interested' },
  { value: 'qualified', label: 'Qualified' },
  { value: 'proposal', label: 'Proposal Sent' },
  { value: 'loan_process', label: 'Loan Process' },
  { value: 'on_hold', label: 'On Hold' },
  { value: 'won', label: 'Won' },
  { value: 'lost', label: 'Lost' },
  { value: 'do_not_call', label: '🚫 Do Not Call' },
];

const PRIORITY_LABELS: Record<string, string> = {
  overdue: '🔴 Overdue',
  due_today: '🟡 Due Today',
  new: '🟠 New Lead',
  second_contact: '🔵 2nd Contact',
  upcoming: '⚪ Upcoming',
};

const OUTCOME_COLORS: Record<string, string> = {
  answered: '#059669',
  no_answer: '#d97706',
  busy: '#7c3aed',
  callback: '#0ea5e9',
  skip: '#6b7280',
};

/**
 * DC_LAST_CONTACT_FMT: Format the "last interacted" display for the dialer.
 * Shows days elapsed PLUS the actual date and time of last contact.
 * e.g. "Today · 15 Mar at 2:30 PM" or "3 days ago · 12 Mar at 10:15 AM"
 */
function _fmtLastContact(
  lastContactDate: string | null,
  lastContactDays: number | null,
  short = false
): string {
  if (lastContactDays === null || lastContactDate === null) return 'Never contacted';
  const dt = new Date(lastContactDate);
  const timeStr = dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
  const dateStr = dt.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
  const daysLabel = lastContactDays === 0 ? 'Today' : `${lastContactDays}d ago`;
  if (short) return `${daysLabel} · ${dateStr} ${timeStr}`;
  return `Last contact: ${daysLabel} · ${dateStr} at ${timeStr}`;
}

export class AutoDialerPage {
  private container: HTMLElement;
  private queueStats = { total: 0, overdue: 0, due_today: 0, new_leads: 0, second_contact: 0 };
  private queueLoadError = false;
  private queueLoadErrorMsg = '';
  private sessionActive = false;
  private sessionPaused = false;
  private sessionId: number | null = null;
  private popupOpen = false;
  private currentLead: QueueItem | null = null;
  private popupLeadData: any = null;
  private callStartTime: number = 0;
  private webSyncMode = false;
  private searchQuery = '';
  private searchResults: any[] = [];
  private searchLoading = false;
  private searchTimer: any = null;
  // DC_CAT_PRIORITY: Category priority state
  private catPriorityIds: number[] = [];
  private availableCategories: { id: number; name: string }[] = [];
  private showCatPanel = false;
  // DC_CAT_DEFER: Categories whose leads have been pushed to end of queue ("save for later")
  private deferredCategoryIds: Set<number> = new Set();
  // DC_RECENT: Recent call history panel
  private recentCalls: any[] = [];
  private recentCallsLoading = false;
  private recentCallsLoaded = false;
  // DC_MISSED_CB: MyOperator missed callbacks panel
  private missedCallbacks: any[] = [];
  private missedCallbacksLoaded = false;
  // DC_MYOP_001: Call method tracking — 'myoperator' | 'normal'. Persists via session.myoperator_attempts.
  private myoperatorAttemptsThisSession: number = 0;
  private callMethod: string = 'myoperator';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this._injectStyles();
    this._renderSkeleton();

    // DC_INIT_GUARD: Wrap the entire init body so ANY unexpected error (network, 403, 500, etc.)
    // transitions the page out of the skeleton into a recoverable error state instead of freezing.
    try {
      // Check if existing session
      const existingSession = await dialerService.checkExistingSession();
      if (existingSession) {
        this.sessionId = existingSession.id;
        if (existingSession.status === 'active') {
          this.sessionActive = true;
        } else if (existingSession.status === 'paused') {
          this.sessionPaused = true;
        }
        // DC_MYOP_001: Restore MyOperator attempt count so Normal Call lock is correct after page reload
        this.myoperatorAttemptsThisSession = (existingSession as any).myoperator_attempts ?? 0;
      }

      // Fetch queue and category preferences
      await this._loadQueue();
      await this._loadPreferences();

      // Detect web sync mode (browser, not native)
      const { APP_CONFIG } = await import('../config/app.config');
      this.webSyncMode = !APP_CONFIG.isNativeApp();

      // Register popup callback
      dialerService.onPopup((leadId) => this._openPopup(leadId));
    } catch (err: any) {
      // DC_INIT_GUARD: Any unhandled throw lands here — set error state so _render() shows retry
      if (!this.queueLoadError) {
        this.queueLoadError = true;
        this.queueLoadErrorMsg = (err?.message || 'Failed to initialize dialer.') + ' Tap Reload to retry.';
      }
      console.error('[DC_DIALER] init() unexpected error:', err);
    } finally {
      // DC_INIT_GUARD: ALWAYS call _render() — page must never stay on the skeleton indefinitely
      this._render();
      // Load missed callbacks + recent calls in background after first render
      void this._loadMissedCallbacks().then(() => this._render());
      void this._loadRecentCalls();
    }
  }

  cleanup(): void {
    dialerService.stopCallPoll();
    dialerService.stopAppListener();
    dialerService.stopSyncPoll();
  }

  // ── Data Loading ─────────────────────────────────────────────────────────────

  private async _loadQueue(): Promise<void> {
    // DC_DIALER_P1: Catch fetch errors — do not silently return empty queue
    try {
      this.queueLoadError = false;
      this.queueLoadErrorMsg = '';
      const data = await dialerService.fetchQueue();
      this.queueStats = {
        total: data.total || 0,
        overdue: data.overdue || 0,
        due_today: data.due_today || 0,
        new_leads: data.new_leads || 0,
        second_contact: data.second_contact || 0,
      };
      this.currentLead = dialerService.getCurrentLead();
    } catch (err: any) {
      this.queueLoadError = true;
      this.queueLoadErrorMsg = err?.message || 'Failed to load queue. Tap Reload to retry.';
    }
  }

  private async _loadPreferences(): Promise<void> {
    // DC_CAT_PRIORITY: Load telecaller's saved category priority from backend.
    try {
      const res = await apiService.get<any>('/crm/dialer/preferences');
      const body = res?.data;
      if (res?.success && body) {
        this.catPriorityIds = (body.category_priority || []).map(Number);
        this.availableCategories = body.available_categories || [];
      }
    } catch {
      // Non-fatal
    }
  }

  private async _loadMissedCallbacks(): Promise<void> {
    // DC_MISSED_CB: Load pending missed operator calls for callback panel.
    try {
      const res = await apiService.get<any>('/crm/dialer/missed-callbacks');
      const body = res?.data;
      if (res?.success && body) {
        this.missedCallbacks = body.data || [];
      }
    } catch {
      this.missedCallbacks = [];
    } finally {
      this.missedCallbacksLoaded = true;
    }
  }

  // ── Session Controls ─────────────────────────────────────────────────────────

  private async _startSession(): Promise<void> {
    // DC_DIALER_P1: Distinguish between "queue failed to load" vs "queue genuinely empty"
    if (this.queueLoadError) {
      alert(this.queueLoadErrorMsg || 'Queue failed to load. Tap Reload to retry.');
      return;
    }
    const queue = dialerService.getQueue();
    if (queue.length === 0) {
      alert('No leads in queue. Your queue is empty.');
      return;
    }
    const session = await dialerService.startSession(dialerService.getQueueLeadIds());
    if (session) {
      this.sessionId = session.id;
      this.sessionActive = true;
      this.sessionPaused = false;
      this.myoperatorAttemptsThisSession = 0; // DC_MYOP_001: fresh session starts at 0
      this.currentLead = dialerService.getCurrentLead();
      this._render();
    }
  }

  private async _pauseSession(): Promise<void> {
    await dialerService.pauseSession(dialerService.getQueueLeadIds());
    this.sessionActive = false;
    this.sessionPaused = true;
    this._render();
  }

  private async _resumeSession(): Promise<void> {
    const data = await dialerService.resumeSession();
    if (data) {
      this.sessionId = data.session.id;
      this.sessionActive = true;
      this.sessionPaused = false;
      // DC_MYOP_001: Restore MyOperator attempt count from resumed session
      this.myoperatorAttemptsThisSession = (data.session as any).myoperator_attempts ?? this.myoperatorAttemptsThisSession;
      this.currentLead = dialerService.getCurrentLead();
      this._render();
    }
  }

  private async _closeSession(): Promise<void> {
    if (!confirm('Close this dialer session? Progress will be saved but the session ends.')) return;
    await dialerService.closeSession();
    this.sessionActive = false;
    this.sessionPaused = false;
    this.sessionId = null;
    this.currentLead = null;
    await this._loadQueue();
    this._render();
  }

  // ── Dial ─────────────────────────────────────────────────────────────────────

  // DC_MYOP_001: Entry point — shows method picker before dialling
  private _dial(phone: string, lead: QueueItem): void {
    this._showCallMethodModal(phone, lead);
  }

  // DC_MYOP_001 / DC_MYOP_CTC: The actual dial — called after method is chosen in the modal.
  // MyOperator: uses Click-to-Call API (server-side bridge). Normal: uses tel: URI.
  private async _executeDial(phone: string, lead: QueueItem, method: string): Promise<void> {
    this.callMethod = method;
    if (method === 'myoperator') this.myoperatorAttemptsThisSession++;
    this.callStartTime = Date.now();
    this.currentLead = lead;

    if (method === 'myoperator') {
      // DC_MYOP_CTC: Backend-initiated Click-to-Call via MyOperator API.
      // Agent's personal phone will ring from +918065184781; app stays in foreground.
      this._showCallingScreen(lead, phone, method);
      // DC_WEB_SYNC: await notifyCallActive so web dialer sees call before dial starts
      await dialerService.notifyCallActive(lead.lead_id);
      try {
        const result = await dialerService.clickToCall(phone, lead.lead_id, this.sessionId);
        if (result.call_id) {
          dialerService.startClickToCallPoll(result.call_id, () => {
            this._removeCallingScreen();
            this._openPopup(lead.lead_id);
          });
        }
      } catch (err: any) {
        this._removeCallingScreen();
        void dialerService.clearCallActive();
        this._showClickToCallError(String(err?.message || 'Click-to-Call failed'), phone, lead);
      }
    } else {
      // Normal call — DC_WEB_SYNC: await notifyCallActive before dialing
      await dialerService.notifyCallActive(lead.lead_id);
      this._showCallingScreen(lead, phone, method);
      dialerService.dial(phone);
    }
  }

  private _showClickToCallError(message: string, phone: string, lead: QueueItem): void {
    document.getElementById('dc-ctc-error')?.remove();
    const div = document.createElement('div');
    div.id = 'dc-ctc-error';
    div.style.cssText = 'position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.7);padding:24px;';
    div.innerHTML = `
      <div style="background:#fff;border-radius:16px;padding:24px;max-width:340px;width:100%;text-align:center;">
        <div style="font-size:32px;margin-bottom:12px;">⚠️</div>
        <div style="font-weight:700;font-size:16px;margin-bottom:8px;color:#dc2626;">MyOperator Call Failed</div>
        <div style="font-size:14px;color:#555;margin-bottom:20px;line-height:1.5;">${message}</div>
        <button id="dc-ctc-fallback" style="width:100%;padding:12px;background:#0ea5e9;color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;margin-bottom:10px;">
          📱 Use Normal Call Instead
        </button>
        <button id="dc-ctc-dismiss" style="width:100%;padding:10px;background:none;border:1px solid #ddd;border-radius:10px;font-size:14px;cursor:pointer;color:#666;">
          Cancel
        </button>
      </div>`;
    document.body.appendChild(div);
    document.getElementById('dc-ctc-fallback')?.addEventListener('click', () => {
      div.remove();
      void this._executeDial(phone, lead, 'normal');
    });
    document.getElementById('dc-ctc-dismiss')?.addEventListener('click', () => div.remove());
  }

  // DC_MYOP_001: Call method chooser modal
  private _showCallMethodModal(phone: string, lead: QueueItem): void {
    document.getElementById('dc-method-modal')?.remove();
    const normalLocked = this.myoperatorAttemptsThisSession === 0;

    const modal = document.createElement('div');
    modal.id = 'dc-method-modal';
    modal.innerHTML = `
      <div class="dc-method-backdrop">
        <div class="dc-method-sheet">
          <div class="dc-method-handle"></div>
          <div class="dc-method-lead">${lead.name || 'Lead'}</div>
          <div class="dc-method-phone">${phone}</div>
          <p class="dc-method-title">How do you want to call?</p>

          <button id="dc-method-myop" class="dc-method-btn dc-method-btn--myop">
            <span class="dc-method-icon">📞</span>
            <span class="dc-method-label">
              <b>Call via MyOperator</b>
              <small>Recommended · Call recorded · Your phone rings automatically</small>
            </span>
          </button>

          <button id="dc-method-normal" class="dc-method-btn dc-method-btn--normal${normalLocked ? ' dc-method-btn--locked' : ''}">
            <span class="dc-method-icon">${normalLocked ? '🔒' : '📱'}</span>
            <span class="dc-method-label">
              <b>Normal Call</b>
              <small>${normalLocked ? 'Make at least 1 MyOperator call first this session' : 'Device dialer — no recording'}</small>
            </span>
          </button>

          <button id="dc-method-cancel" class="dc-method-cancel">Cancel</button>
        </div>
      </div>`;
    document.body.appendChild(modal);

    document.getElementById('dc-method-myop')?.addEventListener('click', () => {
      modal.remove();
      void this._executeDial(phone, lead, 'myoperator');
    });

    document.getElementById('dc-method-normal')?.addEventListener('click', () => {
      if (normalLocked) {
        const hint = modal.querySelector('.dc-method-btn--locked small');
        if (hint) {
          hint.textContent = '⚠️ You must make at least 1 MyOperator call first this session';
          (hint as HTMLElement).style.color = '#ef4444';
        }
        return;
      }
      modal.remove();
      void this._executeDial(phone, lead, 'normal');
    });

    document.getElementById('dc-method-cancel')?.addEventListener('click', () => {
      modal.remove();
    });
  }

  private _showCallingScreen(lead: QueueItem | any, phone: string, method: string = 'normal'): void {
    document.getElementById('dc-calling-screen')?.remove();
    const initial = (lead.name || 'L').charAt(0).toUpperCase();
    const isMyOp = method === 'myoperator';
    const statusText = isMyOp
      ? 'Connecting via MyOperator…'
      : 'Calling via your phone app…';
    const hintText = isMyOp
      ? 'Your phone will ring shortly from <b>+918065184781</b>.<br>Answer it — the customer will be bridged automatically.<br>Tap "Call Ended" below when done.'
      : 'Come back to this app after the call<br>and the outcome form will open automatically.';
    const screen = document.createElement('div');
    screen.id = 'dc-calling-screen';
    screen.innerHTML = `
      <div class="dc-calling-overlay">
        <div class="dc-calling-inner">
          <div class="dc-calling-avatar">${initial}</div>
          <div class="dc-calling-name">${lead.name || 'Unknown Lead'}</div>
          <div class="dc-calling-phone">${phone}</div>
          ${isMyOp ? '<div class="dc-method-badge">📞 MyOperator</div>' : ''}
          <div class="dc-calling-status">
            <span class="dc-calling-dot"></span>
            <span class="dc-calling-dot"></span>
            <span class="dc-calling-dot"></span>
            ${statusText}
          </div>
          <p class="dc-calling-hint">${hintText}</p>
          <button id="dc-call-ended-btn" class="dc-call-ended-btn">
            📵 Call Ended — Log Outcome
          </button>
          <button id="dc-calling-cancel-btn" class="dc-calling-cancel-btn">Cancel</button>
        </div>
      </div>`;
    document.body.appendChild(screen);
    document.getElementById('dc-call-ended-btn')?.addEventListener('click', () => {
      this._removeCallingScreen();
      this._openPopup(lead.lead_id);
    });
    document.getElementById('dc-calling-cancel-btn')?.addEventListener('click', () => {
      this._removeCallingScreen();
      void dialerService.clearCallActive();
    });
  }

  private _removeCallingScreen(): void {
    document.getElementById('dc-calling-screen')?.remove();
    document.getElementById('dc-manual-done-btn')?.remove();
  }

  // ── After-Call Popup ─────────────────────────────────────────────────────────

  private async _openPopup(leadId: number): Promise<void> {
    if (this.popupOpen) return;
    this.popupOpen = true;
    this._removeCallingScreen();
    // Clear active call so web desktop knows this call has ended
    void dialerService.clearCallActive();

    // DC_SESSION_GUARD: If sessionId is null when the popup opens (e.g. after page reload),
    // attempt to recover the active session from the server before proceeding.
    if (!this.sessionId) {
      try {
        const recovered = await dialerService.checkExistingSession();
        if (recovered) {
          this.sessionId = recovered.id;
          console.warn('[DC_DIALER] _openPopup: recovered sessionId', this.sessionId);
        } else {
          console.warn('[DC_DIALER] _openPopup: no session to recover — popup will open without a session');
        }
      } catch (err) {
        console.error('[DC_DIALER] _openPopup: session recovery failed', err);
      }
    }

    // Fetch full lead data for edit form
    let lead = dialerService.getQueue().find(q => q.lead_id === leadId) || null;
    let fullLead: any = lead;
    try {
      const companyId = lead?.company_id || this.currentLead?.company_id || '';
      const res = await apiService.get(`/crm/leads/${leadId}?company_id=${companyId}`);
      if (res.success && res.data) fullLead = { ...lead, ...res.data };
    } catch (_) { /* use queue data */ }

    // DC_SOURCE_CAT_FIX: Fetch categories for the dropdown in Update Lead form
    let categories: Array<{id: number; name: string}> = [];
    try {
      const catRes = await apiService.get('/crm/signup/categories');
      if (catRes.success && Array.isArray(catRes.data)) {
        categories = catRes.data.map((c: any) => ({ id: c.id, name: c.name }));
      }
    } catch (_) { /* dropdown remains empty */ }

    this.popupLeadData = fullLead;
    const durationSec = Math.round((Date.now() - this.callStartTime) / 1000);

    const overlay = document.createElement('div');
    overlay.id = 'dc-dialer-popup';
    overlay.innerHTML = this._popupHTML(fullLead, durationSec, categories);
    document.body.appendChild(overlay);
    this._attachPopupListeners(overlay, leadId, durationSec);

    // DC Protocol N001: lazy-load VGK banner (non-blocking, 200ms after popup renders)
    const vgkCid = fullLead?.company_id;
    if (vgkCid) {
      setTimeout(() => vgkBannerService.load(leadId, vgkCid, 'dc-vgk-banner'), 200);
    }
  }

  private _popupHTML(lead: any, durationSec: number, categories: Array<{id: number; name: string}> = []): string {
    const durationStr = durationSec > 5
      ? `${Math.floor(durationSec / 60)}m ${durationSec % 60}s`
      : 'Just dialed';
    const defaultMinutes = Math.max(1, Math.round(durationSec / 60));
    const now = new Date();
    // DC_FOLLOWUP_IST: Use local time (IST) for datetime-local input.
    // toISOString() returns UTC which is 5.5h behind IST — causes stored follow-up to be wrong.
    const tomorrowLocal = new Date(now.getTime() + 24 * 60 * 60 * 1000);
    const _pad = (n: number) => n.toString().padStart(2, '0');
    const defaultFollowup = `${tomorrowLocal.getFullYear()}-${_pad(tomorrowLocal.getMonth()+1)}-${_pad(tomorrowLocal.getDate())}T${_pad(tomorrowLocal.getHours())}:${_pad(tomorrowLocal.getMinutes())}`;
    const statusOptions = LEAD_STATUSES.map(s =>
      `<option value="${s.value}" ${lead?.status === s.value ? 'selected' : ''}>${s.label}</option>`
    ).join('');
    const priorityOptions = ['normal', 'medium', 'high'].map(p =>
      `<option value="${p}" ${lead?.priority === p ? 'selected' : ''}>${p.charAt(0).toUpperCase() + p.slice(1)}</option>`
    ).join('');

    // DC_SOURCE_CAT_FIX: Build category dropdown options
    const categoryOptions = [
      `<option value="">— No change —</option>`,
      ...categories.map(c =>
        `<option value="${c.id}" ${lead?.category_id === c.id ? 'selected' : ''}>${c.name}</option>`
      )
    ].join('');

    const activityChips = [
      { act: 'Client Call', icon: '📞' },
      { act: 'Team Meeting', icon: '👥' },
      { act: 'Feedback Meeting', icon: '💬' },
      { act: 'Training', icon: '🎓' },
      { act: 'Report Preparation', icon: '📄' },
      { act: 'Travel / Field Visit', icon: '🚗' },
      { act: 'Internal Review', icon: '🔍' },
      { act: 'Admin / Documentation', icon: '📁' },
    ].map(c => `<button class="dc-act-chip" data-act="${c.act}">${c.icon} ${c.act.split(' ')[0]}</button>`).join('');

    return `
    <div class="dc-popup-overlay">
      <div class="dc-popup-sheet">
        <div class="dc-popup-header">
          <div class="dc-popup-lead-info">
            <div class="dc-popup-name">${lead?.name || 'Unknown Lead'}</div>
            <div class="dc-popup-meta">
              ${lead?.phone || ''} ${lead?.city ? '· ' + lead.city : ''} · ${durationStr}
            </div>
          </div>
          <div class="dc-popup-priority-badge ${lead?.queue_priority || ''}">
            ${PRIORITY_LABELS[lead?.queue_priority || ''] || ''}
          </div>
        </div>

        <div class="dc-popup-scroll">
          <!-- QUICK DIAL: Search and dial any lead/contact directly from the popup -->
          <div class="dc-popup-qd-section">
            <div class="dc-popup-qd-input-row">
              <span class="dc-popup-qd-icon">🔍</span>
              <input id="dc-popup-qd-input" class="dc-popup-qd-input" type="text"
                placeholder="Dial another lead or contact…" autocomplete="off">
              <button class="dc-popup-qd-clear" id="dc-popup-qd-clear" style="display:none;">✕</button>
            </div>
            <div id="dc-popup-qd-results"></div>
          </div>

          <!-- DC Protocol N001: VGK Member Status Banner (lazy-loaded, non-blocking) -->
          <div class="dc-popup-section" style="padding-top:0;padding-bottom:0">
            <div id="dc-vgk-banner"></div>
          </div>

          <!-- OUTCOME -->
          <div class="dc-popup-section">
            <div class="dc-popup-section-title">Call Outcome</div>
            <div class="dc-outcome-btns">
              <button class="dc-outcome-btn" data-outcome="answered">✅ Answered</button>
              <button class="dc-outcome-btn" data-outcome="no_answer">📵 No Answer</button>
              <button class="dc-outcome-btn" data-outcome="busy">📳 Busy</button>
              <button class="dc-outcome-btn" data-outcome="callback">🔁 Callback</button>
            </div>
          </div>

          <!-- LEAD EDIT — COMPLETE FORM -->
          <div class="dc-popup-section">
            <div class="dc-popup-section-title">📋 Update Lead</div>

            <!-- ─── Status & Timeline ─────────────────────────── -->
            <div class="dc-form-group-label">Status & Timeline</div>
            <div class="dc-form-row-inline">
              <div class="dc-form-col">
                <label>Status</label>
                <select id="dc-edit-status">${statusOptions}</select>
              </div>
              <div class="dc-form-col">
                <label>Priority</label>
                <select id="dc-edit-priority">${priorityOptions}</select>
              </div>
            </div>
            <div class="dc-form-row">
              <label>Next Follow-up</label>
              <input type="datetime-local" id="dc-edit-followup" value="${defaultFollowup}">
            </div>
            <div class="dc-form-row">
              <label>Expected Close Date</label>
              <input type="date" id="dc-edit-close-date" value="${lead?.expected_close_date ? String(lead.expected_close_date).slice(0, 10) : ''}">
            </div>
            <div class="dc-form-row" id="dc-lost-reason-row" style="${lead?.status === 'lost' ? '' : 'display:none'}">
              <label>Lost Reason</label>
              <textarea id="dc-edit-lost-reason" rows="2" placeholder="Why was this lead lost?">${lead?.lost_reason || ''}</textarea>
            </div>

            <!-- ─── Call Note ──────────────────────────────────── -->
            <div class="dc-form-group-label">Call Note</div>
            <div class="dc-form-row">
              <label>Note for this call</label>
              <textarea id="dc-edit-note" rows="3" placeholder="What happened on this call — next steps, objections, promises...">${lead?.recent_comments || ''}</textarea>
            </div>

            <!-- ─── Contact Details ───────────────────────────── -->
            <div class="dc-form-group-label">Contact Details</div>
            <div class="dc-form-row">
              <label>Full Name</label>
              <input type="text" id="dc-edit-name" value="${lead?.name || ''}" placeholder="Lead name">
            </div>
            <div class="dc-form-row">
              <label>Email</label>
              <input type="email" id="dc-edit-email" value="${lead?.email || ''}" placeholder="email@example.com">
            </div>
            <div class="dc-form-row">
              <label>Primary Phone</label>
              <div class="dc-phone-row">
                <input type="tel" id="dc-edit-phone" value="${lead?.phone || ''}" placeholder="Primary number">
                <label class="dc-wa-toggle"><input type="checkbox" id="dc-edit-phone-wa" ${lead?.phone_primary_whatsapp ? 'checked' : ''}><span>WhatsApp</span></label>
              </div>
            </div>
            <div class="dc-form-row">
              <label>Alternate Phone</label>
              <div class="dc-phone-row">
                <input type="tel" id="dc-edit-alt-phone" value="${lead?.alternate_phone || ''}" placeholder="Alt. number">
                <label class="dc-wa-toggle"><input type="checkbox" id="dc-edit-alt-phone-wa" ${lead?.phone_secondary_whatsapp ? 'checked' : ''}><span>WhatsApp</span></label>
              </div>
            </div>

            <!-- ─── Lead Classification ───────────────────────── -->
            <div class="dc-form-group-label">Lead Classification</div>
            <div class="dc-form-row">
              <label>Category</label>
              <select id="dc-edit-category">${categoryOptions}</select>
            </div>
            <div class="dc-form-row">
              <label>Source</label>
              <input type="text" id="dc-edit-source" value="${lead?.source || ''}" placeholder="e.g. Google, Walk-in, Referral">
            </div>
            <div class="dc-form-row">
              <label>Source Details</label>
              <input type="text" id="dc-edit-source-details" value="${lead?.source_details || ''}" placeholder="Campaign name, referrer, medium...">
            </div>
            <div class="dc-form-row">
              <label>Tags</label>
              <input type="text" id="dc-edit-tags" value="${lead?.tags || ''}" placeholder="Comma-separated tags">
            </div>

            <!-- ─── Requirements ──────────────────────────────── -->
            <div class="dc-form-group-label">Requirements</div>
            <div class="dc-form-row">
              <label>Description</label>
              <textarea id="dc-edit-desc" rows="2" placeholder="Lead overview / context...">${lead?.description || ''}</textarea>
            </div>
            <div class="dc-form-row">
              <label>Requirements</label>
              <textarea id="dc-edit-requirements" rows="2" placeholder="What does the lead specifically need?">${lead?.requirements || ''}</textarea>
            </div>
            <div class="dc-form-row">
              <label>Looking For</label>
              <input type="text" id="dc-edit-looking-for" value="${lead?.looking_for || ''}" placeholder="e.g. 3BHK flat, 5kW solar, agri loan...">
            </div>

            <!-- ─── Budget & Location ─────────────────────────── -->
            <div class="dc-form-group-label">Budget & Location</div>
            <div class="dc-form-row-inline">
              <div class="dc-form-col">
                <label>Budget Min (₹ Lakhs)</label>
                <input type="number" id="dc-edit-budget-min" step="0.5" min="0" value="${lead?.budget_min ? (lead.budget_min / 100000).toFixed(2) : ''}" placeholder="0.00">
              </div>
              <div class="dc-form-col">
                <label>Budget Max (₹ Lakhs)</label>
                <input type="number" id="dc-edit-budget-max" step="0.5" min="0" value="${lead?.budget_max ? (lead.budget_max / 100000).toFixed(2) : ''}" placeholder="0.00">
              </div>
            </div>
            <div class="dc-form-row-inline">
              <div class="dc-form-col">
                <label>Area / Locality</label>
                <input type="text" id="dc-edit-area" value="${lead?.area || ''}" placeholder="Locality">
              </div>
              <div class="dc-form-col">
                <label>City</label>
                <input type="text" id="dc-edit-city" value="${lead?.city || ''}" placeholder="City">
              </div>
            </div>
            <div class="dc-form-row-inline">
              <div class="dc-form-col">
                <label>State</label>
                <input type="text" id="dc-edit-state" value="${lead?.state || ''}" placeholder="State">
              </div>
              <div class="dc-form-col">
                <label>Pincode</label>
                <input type="text" id="dc-edit-pincode" value="${lead?.pincode || ''}" placeholder="6-digit" maxlength="6">
              </div>
            </div>
            <div class="dc-form-row">
              <label>Full Address</label>
              <textarea id="dc-edit-address" rows="2" placeholder="Door no, street, landmark...">${lead?.address || ''}</textarea>
            </div>
          </div>

          <!-- ACTIVITY LOG (TIMESHEET) -->
          <div class="dc-popup-section">
            <div class="dc-popup-section-title">📊 Activity Log <span style="font-size:10px;font-weight:400;opacity:0.6;">(auto-syncs to timesheet)</span></div>
            <div class="dc-act-chips" id="dc-act-chips">${activityChips}</div>
            <div id="dc-act-time-row" style="display:none;margin-top:10px;align-items:center;gap:8px;">
              <span style="font-size:12px;color:#6b7280;">Time (min):</span>
              <input type="number" id="dc-act-minutes" min="1" max="480" value="${defaultMinutes}" style="width:64px;padding:6px 8px;border:1px solid #e5e7eb;border-radius:8px;font-size:14px;text-align:center;">
              <span id="dc-act-clear" style="font-size:12px;color:#ef4444;cursor:pointer;margin-left:4px;">✕ Clear</span>
            </div>
          </div>

          <!-- EXTENSION BUTTON (visible once outcome is picked) -->
          <div class="dc-popup-section" id="dc-extend-section" style="padding-bottom:12px;display:none;">
            <button id="dc-extend-btn" class="dc-hold-btn">⏱ +1 Min Extension <span id="dc-extend-left">(2 left)</span></button>
          </div>

          <!-- LEAD INFO -->
          <div class="dc-popup-section dc-popup-lead-details">
            <div class="dc-popup-section-title">Lead Details</div>
            <div class="dc-detail-grid">
              ${lead?.source ? `<div class="dc-detail-item"><span>Source</span><b>${lead.source}</b></div>` : ''}
              ${(lead?.category_name || lead?.category_id) ? `<div class="dc-detail-item"><span>Category</span><b>${lead.category_name || '#' + lead.category_id}</b></div>` : ''}
              ${lead?.area ? `<div class="dc-detail-item"><span>Area</span><b>${lead.area}</b></div>` : ''}
              ${lead?.budget_min ? `<div class="dc-detail-item"><span>Budget</span><b>₹${(lead.budget_min/100000).toFixed(1)}L – ₹${((lead.budget_max||lead.budget_min)/100000).toFixed(1)}L</b></div>` : ''}
              ${lead?.last_contact_days !== null
                ? `<div class="dc-detail-item dc-detail-item--wide"><span>Last Contact</span><b>${_fmtLastContact(lead.last_contact_date, lead.last_contact_days)}</b></div>`
                : ''}
            </div>
            ${lead?.description ? `<div class="dc-detail-desc">${lead.description}</div>` : ''}
            ${lead?.requirements ? `<div class="dc-detail-desc"><b>Needs:</b> ${lead.requirements}</div>` : ''}
          </div>

          <!-- DNC -->
          <div class="dc-popup-section">
            <label class="dc-dnc-label">
              <input type="checkbox" id="dc-edit-dnc">
              <span>🚫 Do Not Call — remove from all future dialer sessions</span>
            </label>
          </div>
        </div>

        <!-- ACTIONS -->
        <div class="dc-popup-actions">
          <div id="dc-countdown-row" style="display:none;width:100%;text-align:center;font-size:12px;color:#9ca3af;margin-bottom:6px;">
            Auto-saving in <b id="dc-countdown-sec">1:00</b>
            <div id="dc-countdown-bar-wrap" style="width:100%;height:3px;background:#f3f4f6;border-radius:2px;margin-top:4px;overflow:hidden;">
              <div id="dc-countdown-bar" style="height:3px;background:#059669;width:100%;transition:width 1s linear;"></div>
            </div>
          </div>
          <div id="dc-popup-footer-error" style="display:none;width:100%;padding:8px 12px;margin-bottom:6px;background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;color:#dc2626;font-size:13px;font-weight:600;text-align:center;"></div>
          <button class="dc-popup-skip-btn" id="dc-popup-skip">Skip → End of Queue</button>
          <button class="dc-popup-save-btn" id="dc-popup-save">Save &amp; Next →</button>
        </div>
      </div>
    </div>`;
  }

  private _attachPopupListeners(overlay: HTMLElement, leadId: number, durationSec: number): void {
    let selectedOutcome: CallOutcome | null = null;
    let selectedActivity: string | null = null;
    let extensionsLeft = 2;
    let countdownSec = 60;
    let countdownTimer: ReturnType<typeof setInterval> | null = null;
    const COUNTDOWN_TOTAL = 60;

    // ── Popup Quick Dial ─────────────────────────────────────────────────────
    // DC_POPUP_QD: Search for any lead/contact and dial directly from after-call popup
    const qdInput = overlay.querySelector('#dc-popup-qd-input') as HTMLInputElement | null;
    const qdResults = overlay.querySelector('#dc-popup-qd-results') as HTMLElement | null;
    const qdClear = overlay.querySelector('#dc-popup-qd-clear') as HTMLButtonElement | null;
    let qdTimer: ReturnType<typeof setTimeout> | null = null;

    const _qdRenderResults = (results: any[]) => {
      if (!qdResults) return;
      if (results.length === 0) {
        qdResults.innerHTML = '<div class="dc-popup-qd-empty">No results found</div>';
        return;
      }
      qdResults.innerHTML = results.slice(0, 6).map(r => {
        const isContact = r.source === 'contact';
        const badge = isContact ? '📱' : '🎯';
        const alt = r.alternate_phone && r.alternate_phone !== r.phone;
        return `
          <div class="dc-popup-qd-item">
            <div class="dc-popup-qd-info">
              <div class="dc-popup-qd-name">${badge} ${r.name}</div>
              <div class="dc-popup-qd-meta">${r.phone || '—'}${r.city ? ' · ' + r.city : ''}${r.dialed_today ? ' · ✅ Called' : ''}</div>
            </div>
            <div class="dc-popup-qd-btns">
              ${r.phone ? `<button class="dc-popup-qd-dial" data-qd-phone="${r.phone}" title="${r.phone}">📞</button>` : ''}
              ${alt ? `<button class="dc-popup-qd-dial alt" data-qd-phone="${r.alternate_phone}" title="${r.alternate_phone}">📱</button>` : ''}
            </div>
          </div>`;
      }).join('');
      qdResults.querySelectorAll('[data-qd-phone]').forEach(btn => {
        btn.addEventListener('click', () => {
          const phone = (btn as HTMLElement).dataset.qdPhone!;
          dialerService.dial(phone);
          if (qdInput) { qdInput.value = ''; }
          if (qdResults) { qdResults.innerHTML = ''; }
          if (qdClear) { qdClear.style.display = 'none'; }
        });
      });
    };

    if (qdInput) {
      qdInput.addEventListener('input', () => {
        const q = qdInput.value.trim();
        if (qdClear) qdClear.style.display = q ? 'flex' : 'none';
        if (qdTimer) clearTimeout(qdTimer);
        if (q.length < 2) { if (qdResults) qdResults.innerHTML = ''; return; }
        if (qdResults) qdResults.innerHTML = '<div class="dc-popup-qd-empty">Searching…</div>';
        qdTimer = setTimeout(async () => {
          try {
            const res = await apiService.get<any>(`/crm/dialer/search?q=${encodeURIComponent(q)}`);
            const list: any[] = res.data?.results || res.results || [];
            _qdRenderResults(list);
          } catch { if (qdResults) qdResults.innerHTML = ''; }
        }, 300);
      });
    }
    if (qdClear) {
      qdClear.addEventListener('click', () => {
        if (qdInput) qdInput.value = '';
        if (qdResults) qdResults.innerHTML = '';
        qdClear.style.display = 'none';
      });
    }

    // ── Outcome buttons ──────────────────────────────────────────────────────
    overlay.querySelectorAll('.dc-outcome-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        overlay.querySelectorAll('.dc-outcome-btn').forEach(b => {
          b.classList.remove('selected');
          (b as HTMLElement).style.cssText = '';
        });
        btn.classList.add('selected');
        selectedOutcome = btn.getAttribute('data-outcome') as CallOutcome;
        const color = OUTCOME_COLORS[selectedOutcome] || '#0ea5e9';
        (btn as HTMLElement).style.background = color;
        (btn as HTMLElement).style.color = 'white';
        (btn as HTMLElement).style.borderColor = color;
        _startCountdown();
      });
    });

    // ── Auto-countdown ───────────────────────────────────────────────────────
    const _fmtCountdown = (sec: number) => {
      const m = Math.floor(sec / 60);
      const s = sec % 60;
      return `${m}:${String(s).padStart(2, '0')}`;
    };
    const _startCountdown = () => {
      if (countdownTimer) clearInterval(countdownTimer);
      countdownSec = COUNTDOWN_TOTAL;
      const row = document.getElementById('dc-countdown-row');
      const secEl = document.getElementById('dc-countdown-sec');
      const bar = document.getElementById('dc-countdown-bar');
      const extSection = document.getElementById('dc-extend-section');
      if (row) row.style.display = 'block';
      if (extSection) extSection.style.display = 'block';
      if (secEl) secEl.textContent = _fmtCountdown(countdownSec);
      countdownTimer = setInterval(() => {
        countdownSec--;
        if (secEl) secEl.textContent = _fmtCountdown(countdownSec);
        if (bar) bar.style.width = `${(countdownSec / COUNTDOWN_TOTAL) * 100}%`;
        if (countdownSec <= 0) {
          clearInterval(countdownTimer!);
          countdownTimer = null;
          document.getElementById('dc-popup-save')?.click();
        }
      }, 1000);
    };

    const _pauseCountdown = () => {
      if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; }
      const row = document.getElementById('dc-countdown-row');
      if (row) row.style.display = 'none';
    };

    // Reset countdown on any user interaction inside the popup
    overlay.addEventListener('pointerdown', () => {
      if (selectedOutcome) {
        _startCountdown();
      }
    });

    // ── Activity chips ───────────────────────────────────────────────────────
    overlay.querySelectorAll('.dc-act-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const act = (chip as HTMLElement).dataset.act!;
        if (selectedActivity === act) {
          selectedActivity = null;
          chip.classList.remove('selected');
          const timeRow = document.getElementById('dc-act-time-row');
          if (timeRow) timeRow.style.display = 'none';
        } else {
          overlay.querySelectorAll('.dc-act-chip').forEach(c => c.classList.remove('selected'));
          chip.classList.add('selected');
          selectedActivity = act;
          const timeRow = document.getElementById('dc-act-time-row');
          if (timeRow) timeRow.style.display = 'flex';
        }
      });
    });

    document.getElementById('dc-act-clear')?.addEventListener('click', () => {
      selectedActivity = null;
      overlay.querySelectorAll('.dc-act-chip').forEach(c => c.classList.remove('selected'));
      const timeRow = document.getElementById('dc-act-time-row');
      if (timeRow) timeRow.style.display = 'none';
    });

    // ── Extension button (max 2 × +60s) ─────────────────────────────────────
    document.getElementById('dc-extend-btn')?.addEventListener('click', () => {
      if (extensionsLeft <= 0) return;
      extensionsLeft--;
      // Add 60 seconds to whatever is remaining
      countdownSec += 60;
      // Update progress bar base so it doesn't jump to full
      const bar = document.getElementById('dc-countdown-bar');
      if (bar) bar.style.width = `${Math.min(100, (countdownSec / COUNTDOWN_TOTAL) * 100)}%`;
      // Update extension button label
      const extBtn = document.getElementById('dc-extend-btn') as HTMLButtonElement;
      const extLeft = document.getElementById('dc-extend-left');
      if (extensionsLeft === 0) {
        extBtn.disabled = true;
        extBtn.style.opacity = '0.4';
        extBtn.style.cursor = 'not-allowed';
        if (extLeft) extLeft.textContent = '(max reached)';
      } else {
        if (extLeft) extLeft.textContent = `(${extensionsLeft} left)`;
      }
    });

    // ── DNC ──────────────────────────────────────────────────────────────────
    document.getElementById('dc-edit-dnc')?.addEventListener('change', (e) => {
      const checked = (e.target as HTMLInputElement).checked;
      const statusSel = document.getElementById('dc-edit-status') as HTMLSelectElement;
      if (checked && statusSel) statusSel.value = 'do_not_call';
    });

    // ── Status → show Lost Reason field when status is "lost" ────────────────
    document.getElementById('dc-edit-status')?.addEventListener('change', (e) => {
      const v = (e.target as HTMLSelectElement).value;
      const lostRow = document.getElementById('dc-lost-reason-row');
      if (lostRow) lostRow.style.display = v === 'lost' ? '' : 'none';
    });

    // ── Skip ─────────────────────────────────────────────────────────────────
    document.getElementById('dc-popup-skip')?.addEventListener('click', async () => {
      _pauseCountdown();

      // DC_SESSION_GUARD: Attempt session recovery if sessionId is missing
      if (!this.sessionId) {
        console.warn('[DC_DIALER] skip: sessionId is null — attempting recovery');
        try {
          const recovered = await dialerService.checkExistingSession();
          if (recovered) {
            this.sessionId = recovered.id;
            console.warn('[DC_DIALER] skip: recovered sessionId', this.sessionId);
          }
        } catch (err) {
          console.error('[DC_DIALER] skip: session recovery error', err);
        }
      }

      if (!this.sessionId) {
        // No session recoverable — skip locally so the user can still move forward
        console.warn('[DC_DIALER] skip: no session — skipping locally without logging');
        dialerService.skipToEnd(leadId);
        this._closePopup(overlay);
        this.currentLead = dialerService.getCurrentLead();
        this._render();
        if (this.currentLead?.phone) this._maybeActivityThenDial(this.currentLead);
        return;
      }

      // DC_RESUME_FIX: skipToEnd already repositions the pointer to the next lead.
      // Do NOT call advanceQueue() after — that was double-skipping one lead for every person.
      dialerService.skipToEnd(leadId);
      await dialerService.logAttempt({
        session_id: this.sessionId,
        lead_id: leadId,
        call_outcome: 'skip',
        current_index: dialerService.getCurrentIndex(),
        // DC_RESUME_FIX: Send updated queue order so the server knows Ram moved to the end
        queue_lead_ids: dialerService.getQueueLeadIds(),
      });
      this._closePopup(overlay);
      this.currentLead = dialerService.getCurrentLead();
      this._render();
      if (this.currentLead?.phone) this._maybeActivityThenDial(this.currentLead);
    });

    // ── Save & Next ──────────────────────────────────────────────────────────
    document.getElementById('dc-popup-save')?.addEventListener('click', async () => {
      _pauseCountdown();

      // DC_SESSION_GUARD: Attempt session recovery if sessionId is missing
      if (!this.sessionId) {
        console.warn('[DC_DIALER] save: sessionId is null — attempting recovery');
        try {
          const recovered = await dialerService.checkExistingSession();
          if (recovered) {
            this.sessionId = recovered.id;
            console.warn('[DC_DIALER] save: recovered sessionId', this.sessionId);
          }
        } catch (err) {
          console.error('[DC_DIALER] save: session recovery error', err);
        }
      }

      if (!this.sessionId) {
        // Session unrecoverable — show error and close popup gracefully
        const footerErr = document.getElementById('dc-popup-footer-error');
        if (footerErr) {
          footerErr.innerHTML = 'Session expired — your data could not be saved.<br><button id="dc-popup-close-expired" style="margin-top:8px;padding:6px 18px;background:#dc2626;color:white;border:none;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;">Close</button>';
          footerErr.style.display = 'block';
          document.getElementById('dc-popup-close-expired')?.addEventListener('click', () => this._closePopup(overlay));
        }
        const saveBtn = document.getElementById('dc-popup-save') as HTMLButtonElement | null;
        if (saveBtn) {
          saveBtn.disabled = true;
          saveBtn.textContent = 'Session Lost';
        }
        const skipBtn = document.getElementById('dc-popup-skip') as HTMLButtonElement | null;
        if (skipBtn) {
          skipBtn.disabled = true;
        }
        return;
      }

      // ── Read all form fields ─────────────────────────────────────────────────
      const g = (id: string) => document.getElementById(id);
      const val = (id: string) => (g(id) as HTMLInputElement)?.value?.trim() || '';
      const sel = (id: string) => (g(id) as HTMLSelectElement)?.value || '';
      const txt = (id: string) => (g(id) as HTMLTextAreaElement)?.value?.trim() || '';
      const chk = (id: string) => !!(g(id) as HTMLInputElement)?.checked;

      const status   = sel('dc-edit-status');
      const priority = sel('dc-edit-priority');
      const followup = val('dc-edit-followup');
      const note     = txt('dc-edit-note');
      const dnc      = chk('dc-edit-dnc');
      const actMinutesRaw = val('dc-act-minutes');
      const activityMinutes = selectedActivity && actMinutesRaw ? parseInt(actMinutesRaw) : undefined;

      // Lead PUT payload — all field values from the comprehensive form
      const catRaw = sel('dc-edit-category');
      const budgetMinRaw = val('dc-edit-budget-min');
      const budgetMaxRaw = val('dc-edit-budget-max');
      const leadPutPayload: Record<string, any> = {
        name:                      val('dc-edit-name')            || undefined,
        email:                     val('dc-edit-email')           || undefined,
        phone:                     val('dc-edit-phone')           || undefined,
        phone_primary_whatsapp:    chk('dc-edit-phone-wa'),
        alternate_phone:           val('dc-edit-alt-phone')       || undefined,
        phone_secondary_whatsapp:  chk('dc-edit-alt-phone-wa'),
        status,
        priority,
        category_id:               catRaw ? parseInt(catRaw)      : undefined,
        source:                    val('dc-edit-source')          || undefined,
        source_details:            val('dc-edit-source-details')  || undefined,
        tags:                      val('dc-edit-tags')            || undefined,
        description:               txt('dc-edit-desc')            || undefined,
        requirements:              txt('dc-edit-requirements')    || undefined,
        looking_for:               val('dc-edit-looking-for')     || undefined,
        budget_min:                budgetMinRaw ? parseFloat(budgetMinRaw) * 100000 : undefined,
        budget_max:                budgetMaxRaw ? parseFloat(budgetMaxRaw) * 100000 : undefined,
        area:                      val('dc-edit-area')            || undefined,
        city:                      val('dc-edit-city')            || undefined,
        state:                     val('dc-edit-state')           || undefined,
        pincode:                   val('dc-edit-pincode')         || undefined,
        address:                   txt('dc-edit-address')         || undefined,
        next_followup_date:        followup                       || undefined,
        expected_close_date:       val('dc-edit-close-date')      || undefined,
        lost_reason:               txt('dc-edit-lost-reason')     || undefined,
        recent_comments:           note                           || undefined,
      };
      // Strip undefined keys so backend only updates what was touched
      Object.keys(leadPutPayload).forEach(k => {
        if (leadPutPayload[k] === undefined) delete leadPutPayload[k];
      });

      const saveBtn = document.getElementById('dc-popup-save') as HTMLButtonElement;
      saveBtn.disabled = true;
      saveBtn.textContent = 'Saving...';

      // Fire both calls in parallel: full lead PUT + call outcome logAttempt
      const companyId = this.popupLeadData?.company_id || '';
      await Promise.all([
        apiService.put(`/crm/leads/${leadId}?company_id=${companyId}`, leadPutPayload).catch(() => null),
        dialerService.logAttempt({
          session_id: this.sessionId,
          lead_id: leadId,
          call_outcome: selectedOutcome || 'answered',
          call_method: this.callMethod,
          duration_seconds: durationSec,
          note,
          next_followup_date: followup || undefined,
          new_status: status,
          new_priority: priority,
          do_not_call: dnc,
          // DC_RESUME_FIX: Send the POST-advance index so server knows this lead is done.
          // Without +1, server stores index 0 (Ram's position); on resume it shows Ram again.
          current_index: dialerService.getCurrentIndex() + 1,
          activity_type: selectedActivity || undefined,
          activity_minutes: activityMinutes,
        }),
      ]);

      this._closePopup(overlay);
      const hasNext = dialerService.advanceQueue();
      this.currentLead = dialerService.getCurrentLead();

      if (!hasNext) {
        this._showQueueComplete();
      } else {
        this._render();
        if (this.currentLead?.phone) this._maybeActivityThenDial(this.currentLead);
      }
    });
  }

  private _closePopup(overlay: HTMLElement): void {
    overlay.remove();
    this.popupOpen = false;
    this.callStartTime = 0;
  }

  /**
   * DC_ACTIVITY_MODE: After a call is logged, show a 10-sec prompt asking if the employee
   * needs activity time before the next call. If YES, ask how long, then count down.
   * If NO or timer expires, proceed directly to the next-dial countdown.
   * Activity time is tracked as paused_secs in the existing session (pause + resume).
   */
  private _maybeActivityThenDial(lead: QueueItem): void {
    document.getElementById('dc-activity-prompt')?.remove();

    let promptSec = 10;
    let promptTimer: ReturnType<typeof setInterval> | null = null;

    const overlay = document.createElement('div');
    overlay.id = 'dc-activity-prompt';
    overlay.style.cssText = [
      'position:fixed', 'inset:0', 'background:rgba(0,0,0,0.45)',
      'display:flex', 'align-items:center', 'justify-content:center',
      'z-index:9100',
    ].join(';');

    const dismiss = (goActivity: boolean) => {
      if (promptTimer) { clearInterval(promptTimer); promptTimer = null; }
      overlay.remove();
      if (goActivity) {
        this._showActivityTimePicker(lead);
      } else {
        this._startNextDialCountdown(lead);
      }
    };

    const renderPrompt = () => {
      const pct = (promptSec / 10) * 100;
      overlay.innerHTML = `
        <div style="background:#fff;border-radius:20px;padding:28px 28px 24px;text-align:center;width:290px;box-shadow:0 8px 32px rgba(0,0,0,0.18);">
          <div style="font-size:26px;margin-bottom:4px;">🟡</div>
          <div style="font-size:16px;font-weight:700;color:#1f2937;margin-bottom:4px;">Need activity time?</div>
          <div style="font-size:13px;color:#6b7280;margin-bottom:18px;">Update notes or complete a task before the next call</div>
          <div style="width:100%;height:4px;background:#f3f4f6;border-radius:2px;margin-bottom:16px;overflow:hidden;">
            <div style="height:4px;background:#f59e0b;border-radius:2px;width:${pct}%;transition:width 1s linear;"></div>
          </div>
          <div style="display:flex;gap:10px;">
            <button id="dc-act-yes" style="flex:1;padding:12px 0;background:#f59e0b;color:#fff;border:none;border-radius:12px;font-size:14px;font-weight:700;cursor:pointer;">
              ⏸ Activity Mode
            </button>
            <button id="dc-act-no" style="flex:1;padding:12px 0;background:#f3f4f6;color:#6b7280;border:none;border-radius:12px;font-size:14px;font-weight:600;cursor:pointer;">
              Dial Next (${promptSec}s)
            </button>
          </div>
        </div>`;
      document.getElementById('dc-act-yes')?.addEventListener('click', () => dismiss(true));
      document.getElementById('dc-act-no')?.addEventListener('click', () => dismiss(false));
    };

    renderPrompt();
    document.body.appendChild(overlay);

    promptTimer = setInterval(() => {
      promptSec--;
      if (promptSec <= 0) {
        dismiss(false);
      } else {
        renderPrompt();
      }
    }, 1000);
  }

  /**
   * DC_ACTIVITY_TIME_PICKER: Ask how much activity time is needed, then start countdown.
   */
  private _showActivityTimePicker(lead: QueueItem): void {
    document.getElementById('dc-activity-picker')?.remove();

    const overlay = document.createElement('div');
    overlay.id = 'dc-activity-picker';
    overlay.style.cssText = [
      'position:fixed', 'inset:0', 'background:rgba(0,0,0,0.45)',
      'display:flex', 'align-items:center', 'justify-content:center',
      'z-index:9100',
    ].join(';');

    overlay.innerHTML = `
      <div style="background:#fff;border-radius:20px;padding:28px;text-align:center;width:290px;box-shadow:0 8px 32px rgba(0,0,0,0.18);">
        <div style="font-size:26px;margin-bottom:6px;">⏱</div>
        <div style="font-size:16px;font-weight:700;color:#1f2937;margin-bottom:4px;">How long do you need?</div>
        <div style="font-size:13px;color:#6b7280;margin-bottom:18px;">Activity time will be paused from session</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;">
          <button class="dc-act-time-btn" data-min="1" style="padding:14px 0;border:2px solid #e5e7eb;border-radius:12px;background:#fff;font-size:15px;font-weight:700;color:#1f2937;cursor:pointer;">1 min</button>
          <button class="dc-act-time-btn" data-min="2" style="padding:14px 0;border:2px solid #e5e7eb;border-radius:12px;background:#fff;font-size:15px;font-weight:700;color:#1f2937;cursor:pointer;">2 min</button>
          <button class="dc-act-time-btn" data-min="5" style="padding:14px 0;border:2px solid #e5e7eb;border-radius:12px;background:#fff;font-size:15px;font-weight:700;color:#1f2937;cursor:pointer;">5 min</button>
          <button class="dc-act-time-btn" data-min="custom" style="padding:14px 0;border:2px solid #e5e7eb;border-radius:12px;background:#fff;font-size:15px;font-weight:700;color:#6b7280;cursor:pointer;">Custom</button>
        </div>
        <div id="dc-act-custom-row" style="display:none;margin-bottom:14px;">
          <input id="dc-act-custom-min" type="number" min="1" max="60" placeholder="Minutes (1–60)"
            style="width:100%;padding:12px;border:1.5px solid #d1d5db;border-radius:10px;font-size:15px;text-align:center;box-sizing:border-box;"/>
        </div>
        <button id="dc-act-start" style="width:100%;padding:13px;background:#f59e0b;color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:700;cursor:pointer;opacity:.5;" disabled>
          Start Activity Timer
        </button>
        <button id="dc-act-cancel" style="width:100%;padding:10px;margin-top:8px;border:none;background:transparent;font-size:13px;color:#9ca3af;cursor:pointer;">
          Cancel — Dial Next Instead
        </button>
      </div>`;

    document.body.appendChild(overlay);

    let selectedMin: number | null = null;

    const startBtn = document.getElementById('dc-act-start') as HTMLButtonElement;
    const customRow = document.getElementById('dc-act-custom-row')!;
    const customInput = document.getElementById('dc-act-custom-min') as HTMLInputElement;

    const enableStart = (min: number | null) => {
      selectedMin = min;
      startBtn.disabled = !min || min < 1;
      startBtn.style.opacity = (!min || min < 1) ? '.5' : '1';
    };

    overlay.querySelectorAll<HTMLButtonElement>('.dc-act-time-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        overlay.querySelectorAll<HTMLButtonElement>('.dc-act-time-btn').forEach(b => {
          b.style.borderColor = '#e5e7eb'; b.style.background = '#fff'; b.style.color = '#1f2937';
        });
        btn.style.borderColor = '#f59e0b'; btn.style.background = '#fffbeb'; btn.style.color = '#92400e';
        if (btn.dataset.min === 'custom') {
          customRow.style.display = 'block';
          customInput.focus();
          enableStart(null);
        } else {
          customRow.style.display = 'none';
          enableStart(parseInt(btn.dataset.min!));
        }
      });
    });

    customInput.addEventListener('input', () => {
      const v = parseInt(customInput.value);
      enableStart(v >= 1 && v <= 60 ? v : null);
    });

    document.getElementById('dc-act-cancel')?.addEventListener('click', () => {
      overlay.remove();
      this._startNextDialCountdown(lead);
    });

    startBtn.addEventListener('click', () => {
      if (!selectedMin) return;
      overlay.remove();
      this._runActivityCountdown(lead, selectedMin);
    });
  }

  /**
   * DC_ACTIVITY_COUNTDOWN: Run the activity timer, pause the session for tracking,
   * and resume + start next dial when done.
   */
  private _runActivityCountdown(lead: QueueItem, minutes: number): void {
    document.getElementById('dc-activity-running')?.remove();

    void dialerService.pauseSession(dialerService.getQueueLeadIds());

    let remainingSec = minutes * 60;
    let actTimer: ReturnType<typeof setInterval> | null = null;

    // DC_ACT_BANNER: Compact sticky header bar — does NOT block the page.
    // Agent can still scroll the queue, check missed callbacks, etc. while activity runs.
    const overlay = document.createElement('div');
    overlay.id = 'dc-activity-running';
    overlay.style.cssText = 'position:fixed;top:56px;left:0;right:0;z-index:9100;background:#fffbeb;border-bottom:3px solid #f59e0b;padding:10px 16px;display:flex;align-items:center;gap:12px;box-shadow:0 4px 16px rgba(245,158,11,0.15);';

    const fmtTime = (s: number) => {
      const m = Math.floor(s / 60);
      const sec = s % 60;
      return `${m}:${sec.toString().padStart(2, '0')}`;
    };

    const finish = () => {
      if (actTimer) { clearInterval(actTimer); actTimer = null; }
      overlay.remove();
      void dialerService.resumeSession().then(() => {
        this.sessionActive = true;
        this.sessionPaused = false;
        this._render();
        this._startNextDialCountdown(lead);
      });
    };

    const renderActivity = () => {
      const total = minutes * 60;
      const pct = Math.max(0, (remainingSec / total) * 100);
      overlay.innerHTML = `
        <div style="font-size:11px;font-weight:800;color:#d97706;white-space:nowrap;letter-spacing:.5px;">🟡 ACTIVITY</div>
        <div style="font-size:26px;font-weight:800;color:#1f2937;font-variant-numeric:tabular-nums;white-space:nowrap;line-height:1;">${fmtTime(remainingSec)}</div>
        <div style="flex:1;height:6px;background:#fef3c7;border-radius:3px;overflow:hidden;min-width:40px;">
          <div style="height:6px;background:#f59e0b;border-radius:3px;width:${pct}%;transition:width 1s linear;"></div>
        </div>
        <div style="font-size:11px;color:#92400e;white-space:nowrap;flex-shrink:0;">Complete activity</div>
        <button id="dc-act-done" style="background:#059669;color:#fff;border:none;border-radius:10px;padding:8px 16px;font-size:13px;font-weight:700;cursor:pointer;white-space:nowrap;flex-shrink:0;">✓ Done — Dial Next</button>`;
      document.getElementById('dc-act-done')?.addEventListener('click', finish);
    };

    renderActivity();
    document.body.appendChild(overlay);

    actTimer = setInterval(() => {
      remainingSec--;
      if (remainingSec <= 0) {
        finish();
      } else {
        renderActivity();
      }
    }, 1000);
  }

  /**
   * DC_AUTO_DIAL: Show a 5-4-3-2-1 countdown overlay, then auto-dial the next lead.
   * Staff can cancel at any point during the countdown.
   */
  private _startNextDialCountdown(lead: QueueItem): void {
    document.getElementById('dc-next-dial-countdown')?.remove();
    let count = 5;

    const overlay = document.createElement('div');
    overlay.id = 'dc-next-dial-countdown';
    overlay.style.cssText = [
      'position:fixed', 'inset:0', 'background:rgba(0,0,0,0.55)',
      'display:flex', 'align-items:center', 'justify-content:center',
      'z-index:9000',
    ].join(';');

    const render = () => {
      overlay.innerHTML = `
        <div style="background:#fff;border-radius:20px;padding:32px 40px;text-align:center;min-width:260px;box-shadow:0 8px 32px rgba(0,0,0,0.18);">
          <div style="font-size:72px;font-weight:800;color:#059669;line-height:1;font-variant-numeric:tabular-nums;">${count}</div>
          <div style="font-size:14px;color:#9ca3af;margin-top:6px;letter-spacing:.5px;">DIALING NEXT IN…</div>
          <div style="font-size:16px;font-weight:700;color:#1f2937;margin-top:10px;">${lead.name}</div>
          <div style="font-size:13px;color:#6b7280;margin-top:2px;">${lead.phone}</div>
          <button id="dc-next-dial-cancel" style="margin-top:20px;width:100%;padding:12px;border:1px solid #e5e7eb;border-radius:12px;background:#f9fafb;font-size:14px;color:#6b7280;cursor:pointer;font-weight:600;">
            ✕ Cancel — I'll dial manually
          </button>
        </div>`;
      document.getElementById('dc-next-dial-cancel')?.addEventListener('click', () => {
        clearInterval(timer);
        overlay.remove();
      });
    };

    render();
    document.body.appendChild(overlay);

    const timer = setInterval(() => {
      count--;
      if (count <= 0) {
        clearInterval(timer);
        overlay.remove();
        this._dial(lead.phone, lead);
      } else {
        render();
      }
    }, 1000);
  }

  private _showQueueComplete(): void {
    this.container.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:60vh;gap:16px;padding:24px;text-align:center;">
        <div style="font-size:48px;">🎉</div>
        <h2 style="color:#1f2937;font-size:22px;font-weight:700;">Queue Complete!</h2>
        <p style="color:#6b7280;font-size:15px;">You've gone through all leads in this session.</p>
        <button onclick="location.reload()" style="background:#0ea5e9;color:white;border:none;border-radius:12px;padding:14px 28px;font-size:15px;font-weight:600;cursor:pointer;">
          Start New Session
        </button>
      </div>`;
  }

  // ── Render ────────────────────────────────────────────────────────────────────

  private _renderSkeleton(): void {
    this.container.innerHTML = `
      ${PageHeader.render({ title: 'Auto Dialer', showBack: true })}
      <div style="padding:20px;color:#6b7280;text-align:center;">Loading dialer...</div>`;
    PageHeader.attachListeners({ title: 'Auto Dialer', showBack: true });
  }

  private _render(): void {
    const queue = dialerService.getQueue();
    const idx = dialerService.getCurrentIndex();
    const lead = this.currentLead;
    const remaining = queue.length - idx;

    this.container.innerHTML = `
      ${PageHeader.render({ title: 'Auto Dialer', showBack: true })}
      <div class="dc-dialer-wrap">
        ${this._renderBanner()}
        ${this.queueLoadError ? this._renderQueueErrorBanner() : ''}
        ${this._renderQueueBadges()}
        ${this.showCatPanel ? this._renderCatPriorityPanel() : ''}
        ${this._renderMissedCallbacks()}
        ${this._renderSearchBar()}
        ${this.sessionPaused ? this._renderPausedBanner(remaining) : ''}
        ${(this.sessionActive || this.sessionPaused) && lead ? this._renderLeadCard(lead) : ''}
        ${(this.sessionActive || this.sessionPaused) ? this._renderQueueList(queue, idx) : ''}
        ${!this.sessionActive && !this.sessionPaused ? this._renderIdleState() : ''}
      </div>`;

    PageHeader.attachListeners({ title: 'Auto Dialer', showBack: true });
    this._attachMainListeners();
    this._attachSearchListeners();
    this._attachNmcListeners();
    this._attachQueueItemListeners();
    this._attachCatPriorityListeners();
    this._attachDeferListeners();
    this._attachMissedCallbackListeners();
  }

  private _renderBanner(): string {
    const statusColor = this.sessionActive ? '#059669' : this.sessionPaused ? '#d97706' : '#6b7280';
    const statusText = this.sessionActive ? '🟢 Session Active' : this.sessionPaused ? '⏸ Paused' : '⚪ No Session';
    return `
      <div class="dc-banner">
        <div class="dc-banner-left">
          <div class="dc-banner-title">Auto Dialer</div>
          <div class="dc-banner-status" style="color:${statusColor}">${statusText}</div>
        </div>
        <div class="dc-session-controls">
          ${this.sessionActive ? `
            <button class="dc-ctrl-btn pause" id="dc-pause-btn">⏸ Pause</button>
            <button class="dc-ctrl-btn close" id="dc-close-btn">✖ Close</button>
          ` : this.sessionPaused ? `
            <button class="dc-ctrl-btn resume" id="dc-resume-btn">▶ Resume</button>
            <button class="dc-ctrl-btn close" id="dc-close-btn">✖ Close</button>
          ` : `
            <button class="dc-ctrl-btn start" id="dc-start-btn">▶ Start Session</button>
          `}
        </div>
      </div>`;
  }

  private _renderMissedCallbacks(): string {
    // DC_MISSED_CB: Show pending missed operator calls at top of dialer.
    // Self-missed first, then unassigned, then other-agent missed.
    if (!this.missedCallbacksLoaded) return '';
    const items = this.missedCallbacks;
    if (!items.length) return '';

    const selfItems = items.filter(c => c.priority_type === 'self');
    const unassigned = items.filter(c => c.priority_type === 'unassigned');
    const total = items.length;

    const fmtTime = (iso: string) => {
      if (!iso) return '—';
      const d = new Date(iso);
      return d.toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: true });
    };

    const rows = items.slice(0, 10).map(c => {
      const tag = c.priority_type === 'self'
        ? `<span style="background:#fee2e2;color:#b91c1c;font-size:10px;font-weight:700;padding:1px 6px;border-radius:10px;margin-left:4px;">YOUR MISS</span>`
        : c.priority_type === 'unassigned'
          ? `<span style="background:#fef3c7;color:#92400e;font-size:10px;font-weight:700;padding:1px 6px;border-radius:10px;margin-left:4px;">UNASSIGNED</span>`
          : `<span style="background:#f3f4f6;color:#6b7280;font-size:10px;padding:1px 6px;border-radius:10px;margin-left:4px;">OTHER</span>`;
      const dept = c.operator_name ? `<span style="color:#6b7280;font-size:11px;"> · ${c.operator_name}</span>` : '';
      return `
        <div class="dc-mcb-row" data-call-id="${c.call_id}">
          <div class="dc-mcb-info">
            <div style="display:flex;align-items:center;flex-wrap:wrap;gap:2px;">
              <span style="font-weight:700;font-size:14px;letter-spacing:0.5px;">${c.caller_number}</span>
              ${tag}${dept}
            </div>
            <div style="font-size:11px;color:#9ca3af;margin-top:2px;">${fmtTime(c.started_at)}</div>
          </div>
          <div style="display:flex;gap:6px;flex-shrink:0;">
            <button class="dc-mcb-call-btn" data-mcb-call="${c.call_id}" data-mcb-phone="${c.caller_number}">
              📞 Callback
            </button>
            <button class="dc-mcb-done-btn" data-mcb-done="${c.call_id}" title="Mark as handled">✓</button>
          </div>
        </div>`;
    }).join('');

    const selfCount = selfItems.length;
    const unassignedCount = unassigned.length;
    const summary = [
      selfCount ? `<span style="color:#dc2626;font-weight:700;">${selfCount} yours</span>` : '',
      unassignedCount ? `<span style="color:#d97706;font-weight:700;">${unassignedCount} unassigned</span>` : '',
    ].filter(Boolean).join(' · ');

    return `
      <div class="dc-mcb-panel">
        <div class="dc-mcb-header">
          <span>📵 Missed Callbacks <span style="background:#ef4444;color:white;font-size:11px;font-weight:700;padding:1px 7px;border-radius:10px;margin-left:4px;">${total}</span></span>
          <span style="font-size:12px;font-weight:400;color:#6b7280;">${summary}</span>
        </div>
        <div class="dc-mcb-list">${rows}</div>
        ${total > 10 ? `<div style="text-align:center;font-size:11px;color:#9ca3af;padding:4px 0;">+ ${total - 10} more — open Operator Calls Dashboard to see all</div>` : ''}
      </div>`;
  }

  private _renderQueueErrorBanner(): string {
    // DC_DIALER_P1: Visible error banner with actionable Reload button
    return `
      <div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:10px;margin:12px 16px 0;padding:12px 14px;display:flex;align-items:center;justify-content:space-between;gap:10px;">
        <div style="font-size:13px;color:#b91c1c;flex:1;">⚠️ ${this.queueLoadErrorMsg || 'Queue failed to load.'}</div>
        <button id="dc-reload-queue-btn" style="background:#ef4444;color:white;border:none;border-radius:8px;padding:6px 14px;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap;">Reload</button>
      </div>`;
  }

  private _renderQueueBadges(): string {
    const s = this.queueStats;
    const hasPriority = this.catPriorityIds.length > 0;
    const btnLabel = this.showCatPanel ? '✕ Close' : `🎯 Category${hasPriority ? ` (${this.catPriorityIds.length})` : ''}`;
    const btnStyle = this.showCatPanel
      ? 'background:#e5e7eb;color:#374151;'
      : hasPriority
        ? 'background:#dbeafe;color:#1d4ed8;border:1px solid #bfdbfe;'
        : 'background:#f3f4f6;color:#6b7280;';
    return `
      <div class="dc-queue-badges">
        <div class="dc-badge red"><span>${s.overdue}</span>Overdue</div>
        <div class="dc-badge yellow"><span>${s.due_today}</span>Due Today</div>
        <div class="dc-badge orange"><span>${s.new_leads}</span>New</div>
        <div class="dc-badge blue"><span>${s.second_contact}</span>2nd Call</div>
        <div class="dc-badge grey"><span>${s.total}</span>Total</div>
        <button id="dc-cat-priority-toggle" style="margin-left:auto;border:1px solid #e5e7eb;border-radius:16px;padding:4px 12px;font-size:12px;font-weight:600;cursor:pointer;${btnStyle}">${btnLabel}</button>
      </div>`;
  }

  // DC_CAT_DEFER: Move all remaining leads of a category to end of queue ("save for later")
  private _deferCategory(catId: number, catName: string): void {
    const q = dialerService.getQueue();
    const idx = dialerService.getCurrentIndex();
    const toDefer: any[] = [];
    let i = idx + 1;
    while (i < q.length) {
      if (q[i].category_id === catId) {
        toDefer.push(...q.splice(i, 1));
      } else {
        i++;
      }
    }
    q.push(...toDefer);
    this.deferredCategoryIds.add(catId);
    console.log(`[DC_DEFER] Moved ${toDefer.length} leads from "${catName}" to end of queue`, { catId });
    this._render();
  }

  private _renderCatPriorityPanel(): string {
    // DC_CAT_PRIORITY: Inline panel for selecting preferred categories
    const prioritisedCats = this.catPriorityIds
      .map(id => this.availableCategories.find(c => c.id === id))
      .filter((c): c is { id: number; name: string } => !!c);
    const unprioritisedCats = this.availableCategories.filter(c => !this.catPriorityIds.includes(c.id));

    const priorityRows = prioritisedCats.length
      ? prioritisedCats.map((cat, i) => `
          <div class="dc-cppanel-row" data-cat-id="${cat.id}">
            <span class="dc-cppanel-rank">${i + 1}</span>
            <span class="dc-cppanel-name">${cat.name}</span>
            <div class="dc-cppanel-actions">
              ${i > 0 ? `<button class="dc-cppanel-btn up" data-cp-up="${cat.id}" title="Move up">↑</button>` : '<span class="dc-cppanel-btn-ph"></span>'}
              ${i < prioritisedCats.length - 1 ? `<button class="dc-cppanel-btn dn" data-cp-dn="${cat.id}" title="Move down">↓</button>` : '<span class="dc-cppanel-btn-ph"></span>'}
              <button class="dc-cppanel-btn rm" data-cp-rm="${cat.id}" title="Remove">✕</button>
            </div>
          </div>`).join('')
      : `<div style="color:#9ca3af;font-size:13px;padding:8px 0;">No categories selected — all categories shown equally.</div>`;

    const addRows = unprioritisedCats.length
      ? unprioritisedCats.map(cat => {
          const hasPriority = prioritisedCats.length > 0;
          const ordinal = (n: number) => {
            const s = ['th', 'st', 'nd', 'rd'];
            const v = n % 100;
            return n + (s[(v - 20) % 10] || s[v] || s[0]);
          };
          const posOptions = hasPriority
            ? Array.from({ length: prioritisedCats.length + 1 }, (_, i) =>
                `<option value="${i}">${ordinal(i + 1)} position</option>`
              ).join('')
            : '';
          return `
          <div class="dc-cppanel-add-row" data-cp-add-row="${cat.id}">
            <span class="dc-cppanel-name" style="color:#6b7280;">${cat.name}</span>
            ${hasPriority
              ? `<select class="dc-cppanel-pos-select" data-cp-pos-select="${cat.id}" style="font-size:12px;border:1px solid #d1d5db;border-radius:6px;padding:3px 6px;color:#374151;background:#fff;margin-right:4px;">${posOptions}</select>
                 <button class="dc-cppanel-btn add" data-cp-add="${cat.id}">+ Add</button>`
              : `<button class="dc-cppanel-btn add" data-cp-add="${cat.id}">+ Add</button>`
            }
          </div>`;
        }).join('')
      : '';

    return `
      <div class="dc-cppanel" id="dc-cat-priority-panel">
        <div class="dc-cppanel-header">
          <span>🎯 Category Priority</span>
          <span style="font-size:12px;color:#6b7280;font-weight:400;">Preferred categories appear first in queue</span>
        </div>
        <div class="dc-cppanel-section-label">PRIORITY ORDER</div>
        <div id="dc-cppanel-priority-list">${priorityRows}</div>
        ${unprioritisedCats.length ? `<div class="dc-cppanel-section-label" style="margin-top:12px;">ALSO AVAILABLE</div>
        <div id="dc-cppanel-add-list">${addRows}</div>` : ''}
        <div class="dc-cppanel-footer">
          <button id="dc-cppanel-clear" style="background:none;border:1px solid #d1d5db;border-radius:8px;padding:8px 16px;font-size:13px;color:#6b7280;cursor:pointer;">Clear All</button>
          <button id="dc-cppanel-save" style="background:#1d4ed8;color:white;border:none;border-radius:8px;padding:8px 20px;font-size:13px;font-weight:600;cursor:pointer;">Save & Reload Queue</button>
        </div>
      </div>`;
  }

  private _renderLeadCard(lead: QueueItem): string {
    const priorityClass = lead.queue_priority || 'upcoming';
    const lastContact = _fmtLastContact(lead.last_contact_date, lead.last_contact_days);
    const queueIdx = dialerService.getCurrentIndex();
    const total = dialerService.getQueue().length;
    // DC_CURRENT_NMC: Show "Not my segment" on the active card only for unassigned leads.
    // Assigned leads are specifically allocated to this agent — they cannot NMC those.
    const isUnassigned = lead.slot_type === 'unassigned';

    return `
      <div class="dc-lead-card ${priorityClass}">
        <div class="dc-lead-card-top">
          <div class="dc-priority-tag">${PRIORITY_LABELS[lead.queue_priority] || ''}</div>
          <div class="dc-queue-pos">${queueIdx + 1} / ${total}</div>
        </div>
        <div class="dc-lead-name">${lead.name}</div>
        <div class="dc-lead-meta">
          ${lead.city ? `📍 ${lead.city}` : ''} 
          ${lead.source ? `· ${lead.source}` : ''}
          ${lead.status ? `· <span class="dc-status-chip">${lead.status}</span>` : ''}
        </div>
        <div class="dc-last-contact">${lastContact}</div>
        ${lead.description ? `<div class="dc-lead-desc">${lead.description.slice(0, 100)}${lead.description.length > 100 ? '...' : ''}</div>` : ''}
        <div class="dc-dial-row">
          ${lead.phone ? `
            <button class="dc-dial-btn" data-phone="${lead.phone}" data-lead="${lead.lead_id}">
              📞 ${lead.phone}
            </button>` : '<span style="color:#ef4444">No phone number</span>'}
          ${lead.alternate_phone ? `
            <button class="dc-dial-btn alt" data-phone="${lead.alternate_phone}" data-lead="${lead.lead_id}">
              📱 Alt: ${lead.alternate_phone}
            </button>` : ''}
        </div>
        ${isUnassigned ? `
          <div class="dc-current-nmc-row">
            <button class="dc-current-nmc-btn" data-nmc-id="${lead.lead_id}" title="Skip this lead — not your segment">
              ✕ Not my segment
            </button>
          </div>` : ''}
        ${lead.category_id && lead.category_name && !this.deferredCategoryIds.has(lead.category_id) ? `
          <div class="dc-defer-current-row">
            <button class="dc-defer-current-btn" data-defer-cat-id="${lead.category_id}" data-defer-cat-name="${lead.category_name}" title="Move all remaining ${lead.category_name} leads to end of queue">
              ⏬ Save all <strong>${lead.category_name}</strong> calls for later
            </button>
          </div>` : ''}
        ${this.webSyncMode ? `<div class="dc-web-note">💻 Web mode: tap "Call Ended" button after call</div>` : ''}
      </div>`;
  }

  private _renderQueueList(queue: QueueItem[], currentIdx: number): string {
    const upcoming = queue.slice(currentIdx + 1, currentIdx + 8);
    if (!upcoming.length) return '';

    // DC_CAT_DEFER: Group upcoming items by category — show defer button per category group.
    // Items with no category are shown under a generic group (no defer button).
    type CatGroup = { catId: number | null; catName: string | null; items: { item: QueueItem; absIdx: number }[] };
    const groups: CatGroup[] = [];
    const groupIndex = new Map<number | null, CatGroup>();
    upcoming.forEach((item, i) => {
      const catId: number | null = item.category_id ?? null;
      if (!groupIndex.has(catId)) {
        const g: CatGroup = { catId, catName: item.category_name || null, items: [] };
        groups.push(g);
        groupIndex.set(catId, g);
      }
      groupIndex.get(catId)!.items.push({ item, absIdx: currentIdx + i + 2 });
    });

    const rows = groups.map(g => {
      const isDeferred = g.catId !== null && this.deferredCategoryIds.has(g.catId);
      const catHeaderHtml = g.catName
        ? `<div class="dc-qcat-header${isDeferred ? ' deferred' : ''}">
            <span class="dc-qcat-label">${g.catName}</span>
            ${isDeferred
              ? `<span class="dc-qcat-deferred-tag">⏬ Saved for later</span>`
              : `<button class="dc-qcat-defer-btn" data-defer-cat-id="${g.catId}" data-defer-cat-name="${g.catName}">⏬ Save for Later</button>`}
          </div>`
        : '';

      const itemRows = g.items.map(({ item, absIdx }) => {
        const isUnassigned = item.slot_type === 'unassigned';
        const lastDial = item.last_contact_days !== null
          ? `<span class="dc-queue-last-dial">· ${_fmtLastContact(item.last_contact_date, item.last_contact_days, true)}</span>`
          : '';
        const nmcBtn = isUnassigned
          ? `<button class="dc-nmc-btn" data-nmc-id="${item.lead_id}" title="Hide this lead — not your category">✕ Not my category</button>`
          : '';
        return `
          <div class="dc-queue-item${isDeferred ? ' dc-queue-item-deferred' : ''}" data-item-lead="${item.lead_id}" style="cursor:pointer;">
            <div class="dc-queue-item-num">${absIdx}</div>
            <div class="dc-queue-item-info">
              <div class="dc-queue-item-name">${item.name}${isUnassigned ? ' <span class="dc-unassigned-badge">Unassigned</span>' : ''}</div>
              <div class="dc-queue-item-meta">${item.phone || 'No phone'}${lastDial} · <span class="dc-prio-${item.queue_priority}">${PRIORITY_LABELS[item.queue_priority] || ''}</span></div>
              ${nmcBtn}
            </div>
            <div class="dc-queue-item-chevron">›</div>
          </div>`;
      }).join('');

      return catHeaderHtml + itemRows;
    }).join('');

    return `
      <div class="dc-queue-list">
        <div class="dc-queue-list-title">Up Next (${queue.length - currentIdx - 1} remaining)</div>
        ${rows}
      </div>`;
  }

  private _attachNmcListeners(): void {
    // DC_CURRENT_NMC: "Not my segment" on the active (current) lead card.
    // Permanently excludes this unassigned lead and immediately advances to the next one.
    const currentNmcBtn = document.querySelector('.dc-current-nmc-btn') as HTMLButtonElement | null;
    if (currentNmcBtn) {
      currentNmcBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const leadId = parseInt(currentNmcBtn.dataset.nmcId || '0');
        if (!leadId || !this.sessionId) return;

        currentNmcBtn.disabled = true;
        currentNmcBtn.textContent = 'Removing…';
        try {
          await dialerService.logAttempt({
            session_id: this.sessionId,
            lead_id: leadId,
            call_outcome: 'not_my_category' as any,
            duration_seconds: 0,
            current_index: dialerService.getCurrentIndex(),
          });
          dialerService.removeFromQueue(leadId);
          this.currentLead = dialerService.getCurrentLead();
          this._render();
          if (this.currentLead?.phone) this._maybeActivityThenDial(this.currentLead);
        } catch (_) {
          currentNmcBtn.disabled = false;
          currentNmcBtn.textContent = '✕ Not my segment';
        }
      });
    }

    // NMC on upcoming queue items (existing behaviour — hides the item in the list)
    document.querySelectorAll('.dc-nmc-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const leadId = parseInt((btn as HTMLElement).dataset.nmcId || '0');
        if (!leadId || !this.sessionId) return;

        // Immediately hide from UI — remove the card
        const card = (btn as HTMLElement).closest('[data-item-lead]') as HTMLElement;
        if (card) {
          card.style.opacity = '0.4';
          card.style.pointerEvents = 'none';
          const label = card.querySelector('.dc-queue-item-name');
          if (label) label.innerHTML += ' <span style="color:#ef4444;font-size:10px;">Dismissed</span>';
        }

        // Log the NMC outcome so it is permanently excluded from future queues
        try {
          await dialerService.logAttempt({
            session_id: this.sessionId,
            lead_id: leadId,
            call_outcome: 'not_my_category' as any,
            duration_seconds: 0,
            current_index: dialerService.getCurrentIndex(),
          });
          // Remove from the in-memory queue so it doesn't become the active lead
          dialerService.removeFromQueue(leadId);
          if (card) card.remove();
        } catch (_) {
          if (card) { card.style.opacity = ''; card.style.pointerEvents = ''; }
        }
      });
    });
  }

  private _attachQueueItemListeners(): void {
    // DC_QUEUE_DETAIL: Tapping a queue row opens the lead detail bottom-sheet.
    // NMC button clicks are excluded via stopPropagation on their own listener.
    document.querySelectorAll('.dc-queue-item[data-item-lead]').forEach(row => {
      row.addEventListener('click', async (e) => {
        // Don't open sheet if a button inside the row was tapped
        if ((e.target as HTMLElement).closest('button')) return;
        const leadId = parseInt((row as HTMLElement).dataset.itemLead || '0');
        if (!leadId) return;
        await this._openLeadDetailSheet(leadId);
      });
    });
  }

  private async _openLeadDetailSheet(leadId: number): Promise<void> {
    // Show loading sheet immediately
    const sheetId = 'dc-lead-detail-sheet';
    const existingSheet = document.getElementById(sheetId);
    if (existingSheet) existingSheet.remove();

    const sheet = document.createElement('div');
    sheet.id = sheetId;
    sheet.innerHTML = `
      <div class="dc-lds-backdrop"></div>
      <div class="dc-lds-panel">
        <div class="dc-lds-handle"></div>
        <div class="dc-lds-body dc-lds-loading">
          <div class="dc-lds-spinner">⏳ Loading…</div>
        </div>
      </div>`;
    document.body.appendChild(sheet);

    // Dismiss on backdrop tap
    sheet.querySelector('.dc-lds-backdrop')?.addEventListener('click', () => sheet.remove());

    try {
      const resp = await apiService.get<{
        success: boolean;
        lead: {
          id: number; name: string; phone: string | null; alternate_phone: string | null;
          status: string; priority: string; category_name: string | null;
          city: string | null; area: string | null; budget_min: number | null; budget_max: number | null;
          last_contact_date: string | null; next_followup_date: string | null; handler_type: string;
        };
        attempts: { outcome: string; note: string; dialed_at: string | null; duration_seconds: number }[];
        notes: { note: string; created_at: string | null }[];
      }>(`/crm/dialer/lead/${leadId}/detail`);
      const data = resp.data ?? (resp as any);

      const lead = data.lead;
      const attempts = data.attempts || [];
      const notes = data.notes || [];

      const statusLabel = lead.status.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase());
      const budgetStr = lead.budget_min || lead.budget_max
        ? `₹${(lead.budget_min || 0).toLocaleString('en-IN')}–₹${(lead.budget_max || 0).toLocaleString('en-IN')}`
        : null;
      const nfdStr = lead.next_followup_date
        ? new Date(lead.next_followup_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
        : null;

      const attemptsHtml = attempts.length === 0
        ? `<div class="dc-lds-empty">No calls logged yet</div>`
        : attempts.map((a: any) => {
            const color = OUTCOME_COLORS[a.outcome] || '#6b7280';
            const dateStr = a.dialed_at
              ? new Date(a.dialed_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) + ' · ' +
                new Date(a.dialed_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })
              : '—';
            return `<div class="dc-lds-attempt">
              <span class="dc-lds-outcome-pill" style="background:${color}20;color:${color};">${a.outcome.replace(/_/g,' ')}</span>
              <span class="dc-lds-attempt-date">${dateStr}</span>
              ${a.note ? `<div class="dc-lds-attempt-note">${a.note}</div>` : ''}
            </div>`;
          }).join('');

      const notesHtml = notes.length === 0
        ? `<div class="dc-lds-empty">No notes</div>`
        : notes.map((n: any) => {
            const dateStr = n.created_at
              ? new Date(n.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
              : '';
            return `<div class="dc-lds-note"><span class="dc-lds-note-date">${dateStr}</span>${n.note}</div>`;
          }).join('');

      sheet.querySelector('.dc-lds-body')!.innerHTML = `
        <div class="dc-lds-header">
          <div class="dc-lds-name">${lead.name}</div>
          <div class="dc-lds-badges">
            <span class="dc-lds-status-badge">${statusLabel}</span>
            ${lead.handler_type === 'unassigned' ? '<span class="dc-unassigned-badge">Unassigned</span>' : ''}
          </div>
          <button class="dc-lds-close-btn">✕</button>
        </div>
        <div class="dc-lds-scroll">
          <div class="dc-lds-row">📞 ${lead.phone || '—'}${lead.alternate_phone && lead.alternate_phone !== lead.phone ? ' · ' + lead.alternate_phone : ''}</div>
          ${lead.category_name ? `<div class="dc-lds-row">🏷 ${lead.category_name}</div>` : ''}
          ${lead.city || lead.area ? `<div class="dc-lds-row">📍 ${[lead.area, lead.city].filter(Boolean).join(', ')}</div>` : ''}
          ${budgetStr ? `<div class="dc-lds-row">💰 ${budgetStr}</div>` : ''}
          ${nfdStr ? `<div class="dc-lds-row">📅 Follow-up: <strong>${nfdStr}</strong></div>` : ''}

          <div class="dc-lds-section-title">Call History</div>
          ${attemptsHtml}

          <div class="dc-lds-section-title">Notes</div>
          ${notesHtml}
        </div>`;

      sheet.querySelector('.dc-lds-close-btn')?.addEventListener('click', () => sheet.remove());
    } catch (err) {
      sheet.querySelector('.dc-lds-body')!.innerHTML = `
        <div class="dc-lds-header">
          <div class="dc-lds-name">Lead #${leadId}</div>
          <button class="dc-lds-close-btn">✕</button>
        </div>
        <div class="dc-lds-scroll"><div class="dc-lds-empty">Failed to load lead details. Please try again.</div></div>`;
      sheet.querySelector('.dc-lds-close-btn')?.addEventListener('click', () => sheet.remove());
    }
  }

  private _attachDeferListeners(): void {
    // DC_CAT_DEFER: Wire "Save for Later" buttons — both on current lead card and queue list headers.
    const wire = (selector: string) => {
      this.container.querySelectorAll(selector).forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const el = btn as HTMLElement;
          const catId = parseInt(el.dataset.deferCatId || '0');
          const catName = el.dataset.deferCatName || 'this category';
          if (!catId) return;
          this._deferCategory(catId, catName);
        });
      });
    };
    wire('.dc-defer-current-btn');
    wire('.dc-qcat-defer-btn');
  }

  // DC_MCB_HANDLE: Wire "Done" and "Callback" buttons in the Missed Callbacks panel.
  private _attachMissedCallbackListeners(): void {
    // ── ✓ Done button: marks missed call as disposed and removes the row immediately ──
    this.container.querySelectorAll<HTMLButtonElement>('[data-mcb-done]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const callId = btn.dataset.mcbDone || '';
        if (!callId) return;
        // Optimistic removal from local array and DOM
        this.missedCallbacks = this.missedCallbacks.filter(c => c.call_id !== callId);
        const row = btn.closest('[data-call-id]') as HTMLElement | null;
        if (row) {
          row.style.opacity = '0.4';
          row.style.pointerEvents = 'none';
        }
        // If panel is now empty, re-render so it disappears
        if (!this.missedCallbacks.length) {
          this._render();
          return;
        }
        // Update count badge without full re-render
        const badge = this.container.querySelector('.dc-mcb-panel .dc-mcb-header span span') as HTMLElement | null;
        if (badge) badge.textContent = String(this.missedCallbacks.length);
        // Persist to backend
        try {
          await apiService.patch(`/operator-calls/${callId}/missed-status`, { missed_status: 'disposed' });
        } catch (err) {
          console.warn('[DC_MCB] Failed to mark disposed:', err);
        }
        // Remove row from DOM
        row?.remove();
      });
    });

    // ── Callback button: Click-to-Call via MyOperator instead of tel: ──
    this.container.querySelectorAll<HTMLButtonElement>('[data-mcb-call]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const phone = btn.dataset.mcbPhone || '';
        const callId = btn.dataset.mcbCall || '';
        if (!phone) return;
        // Find an associated lead ID if available
        const cb = this.missedCallbacks.find(c => c.call_id === callId);
        const leadId = cb?.crm_lead_id ?? null;
        btn.disabled = true;
        btn.textContent = '⏳ Calling…';
        try {
          const result = await dialerService.clickToCall(phone, leadId, this.sessionId);
          btn.textContent = '📞 Ringing…';
          if (result.call_id) {
            dialerService.startClickToCallPoll(result.call_id, () => {
              btn.textContent = '📞 Callback';
              btn.disabled = false;
            });
          } else {
            btn.textContent = '📞 Callback';
            btn.disabled = false;
          }
        } catch (err: any) {
          // Fallback to normal tel: if CTC fails
          btn.textContent = '📞 Callback';
          btn.disabled = false;
          const a = document.createElement('a');
          a.href = `tel:${phone}`;
          a.click();
        }
      });
    });
  }

  private _buildSearchResultsHtml(): string {
    if (this.searchLoading) return `<div class="dc-srch-loading">Searching…</div>`;
    if (this.searchResults.length > 0) {
      return this.searchResults.map(r => {
        const hasAlt = r.alternate_phone && r.alternate_phone !== r.phone;
        const loc = [r.area, r.city].filter(Boolean).join(', ');
        const isContact = r.source === 'contact';
        const sourceBadge = isContact
          ? `<span class="dc-srch-src-badge contact">📱 Contact</span>`
          : `<span class="dc-srch-src-badge lead">🎯 Lead</span>`;
        const calledBadge = r.dialed_today
          ? `<span class="dc-srch-called-badge">✅ Called</span>`
          : '';
        const dialAttr = (isContact && !r.lead_id)
          ? `data-direct-phone="${r.phone}"`
          : `data-override-phone="${r.phone}" data-override-id="${r.lead_id}" data-override-name="${r.name}"`;
        const altDialAttr = (isContact && !r.lead_id)
          ? `data-direct-phone="${r.alternate_phone}"`
          : `data-override-phone="${r.alternate_phone}" data-override-id="${r.lead_id}" data-override-name="${r.name}"`;
        return `
          <div class="dc-srch-item" style="${r.dialed_today ? 'opacity:0.72;' : ''}">
            <div class="dc-srch-info">
              <div class="dc-srch-name-row"><span class="dc-srch-name">${r.name}</span>${sourceBadge}${calledBadge}</div>
              <div class="dc-srch-meta">${r.phone || '—'}${loc ? ' · ' + loc : ''}</div>
            </div>
            <div class="dc-srch-btns">
              ${r.phone ? `<button class="dc-srch-dial" ${dialAttr}>📞</button>` : ''}
              ${hasAlt ? `<button class="dc-srch-dial alt" ${altDialAttr}>📱</button>` : ''}
            </div>
          </div>`;
      }).join('');
    }
    if (this.searchQuery.length >= 2) {
      const digitsOnly = this.searchQuery.replace(/\D/g, '');
      if (digitsOnly.length >= 6) {
        return `
          <div class="dc-srch-direct-wrap">
            <div class="dc-srch-nr-text">Not found in CRM leads</div>
            <button class="dc-srch-direct-btn" data-direct-phone="${digitsOnly}" data-direct-name="Direct Dial">
              📞 Call ${this.searchQuery.replace(/</g,'&lt;')} directly
            </button>
          </div>`;
      }
      return `<div class="dc-srch-loading">No results</div>`;
    }
    // Query is empty — show recent calls panel
    return this._buildRecentCallsHtml();
  }

  private _buildRecentCallsHtml(): string {
    const localHistory = this._getLocalDialHistory();
    const combined: any[] = [...this.recentCalls];
    const seenPhones = new Set(combined.map(c => c.phone));
    for (const lh of localHistory) {
      if (!seenPhones.has(lh.phone)) { combined.push(lh); seenPhones.add(lh.phone); }
    }

    const viewAllBtn = `<button id="dc-view-all-hist" style="background:none;border:none;font-size:11px;font-weight:700;color:#0ea5e9;cursor:pointer;padding:0 14px 0 0;">View All</button>`;
    const header = `<div class="dc-recent-header" style="display:flex;align-items:center;justify-content:space-between;">🕐 Recent Calls${viewAllBtn}</div>`;

    if (this.recentCallsLoading) {
      return `${header}<div class="dc-srch-loading">Loading…</div>`;
    }
    if (combined.length === 0) {
      return `${header}<div class="dc-srch-loading">No recent calls yet</div>`;
    }

    const callTypeIcon = (c: any): string => {
      const t = (c.call_type || '').toUpperCase();
      if (t === 'INCOMING') return '📲';
      if (t === 'MISSED')   return '📵';
      if (t === 'REJECTED') return '🚫';
      const o = c.call_outcome || '';
      if (o === 'answered') return '✅';
      if (o === 'no_answer') return '📵';
      if (o === 'busy') return '🔴';
      return '📞';
    };
    const callTypeColor = (c: any): string => {
      const t = (c.call_type || '').toUpperCase();
      if (t === 'INCOMING') return '#059669';
      if (t === 'MISSED')   return '#dc2626';
      if (t === 'REJECTED') return '#7c3aed';
      return '#0ea5e9';
    };

    const rows = combined.slice(0, 12).map(c => {
      const src = c.source || '';
      const badge = src === 'direct'
        ? `<span class="dc-srch-src-badge contact">Device</span>`
        : src === 'native'
        ? `<span class="dc-srch-src-badge contact" style="background:#dcfce7;color:#166534">Native</span>`
        : `<span class="dc-srch-src-badge lead">CRM</span>`;
      const dialAttr = c.lead_id
        ? `data-override-phone="${c.phone}" data-override-id="${c.lead_id}" data-override-name="${(c.name||'').replace(/"/g,'&quot;')}"`
        : `data-direct-phone="${c.phone}" data-direct-name="${(c.name||'').replace(/"/g,'&quot;')}"`;
      const icon = callTypeIcon(c);
      const iconColor = callTypeColor(c);
      const displayName = (c.name || c.phone || '').replace(/</g,'&lt;');
      return `
        <div class="dc-srch-item">
          <div class="dc-srch-info">
            <div class="dc-srch-name-row">
              <span class="dc-srch-name"><span style="color:${iconColor}">${icon}</span> ${displayName}</span>${badge}
            </div>
            <div class="dc-srch-meta">${c.phone || '—'}</div>
          </div>
          <div class="dc-srch-btns">
            <button class="dc-srch-dial" ${dialAttr}>📞</button>
          </div>
        </div>`;
    }).join('');
    return `${header}${rows}`;
  }

  private _renderSearchBar(): string {
    const resultsHtml = this._buildSearchResultsHtml();
    const hasContactsApi = typeof (navigator as any).contacts !== 'undefined';
    return `
      <div class="dc-search-bar-wrap">
        <div class="dc-srch-label">⚡ Quick Dial Override</div>
        <div class="dc-srch-input-row">
          <input id="dc-srch-input" class="dc-srch-input" type="text"
            placeholder="Name or phone number…"
            value="${this.searchQuery.replace(/"/g, '&quot;')}" autocomplete="off">
          ${hasContactsApi ? `<button class="dc-srch-contacts-btn" id="dc-srch-contacts-btn" title="Pick from contacts">📱</button>` : ''}
          ${this.searchQuery ? `<button class="dc-srch-clear" id="dc-srch-clear">✕</button>` : ''}
        </div>
        ${resultsHtml ? `<div class="dc-srch-results">${resultsHtml}</div>` : ''}
      </div>`;
  }

  private _attachSearchListeners(): void {
    const inp = document.getElementById('dc-srch-input') as HTMLInputElement | null;
    if (!inp) return;
    inp.addEventListener('input', () => {
      this.searchQuery = inp.value.trim();
      clearTimeout(this.searchTimer);
      if (this.searchQuery.length < 2) {
        this.searchResults = [];
        this.searchLoading = false;
        this._renderSearchOnly();
        return;
      }
      this.searchLoading = true;
      this._renderSearchOnly();
      this.searchTimer = setTimeout(() => this._runSearch(this.searchQuery), 300);
    });
    // Contact Picker API button
    const contactBtn = document.getElementById('dc-srch-contacts-btn');
    if (contactBtn) {
      contactBtn.addEventListener('click', async () => {
        try {
          const contacts = await (navigator as any).contacts.select(['name', 'tel'], { multiple: false });
          if (contacts && contacts.length > 0) {
            const c = contacts[0];
            const rawPhone = (c.tel?.[0] || '').replace(/\D/g, '');
            const phone = rawPhone.replace(/^0+/, '').replace(/^91(\d{10})$/, '$1');
            const name = c.name?.[0] || 'Contact';
            if (phone.length >= 6) {
              this._saveToLocalDialHistory(phone, name);
              dialerService.dial(phone);
              this.searchQuery = '';
              this.searchResults = [];
              this._renderSearchOnly();
            }
          }
        } catch (_) { /* user cancelled or API unavailable */ }
      });
    }
  }

  // DC_SRCH_SURGICAL: Update only the results area and clear button — never replace the
  // <input> element. Replacing it destroys focus and dismisses the mobile keyboard.
  private _renderSearchOnly(): void {
    const wrap = document.querySelector('.dc-search-bar-wrap');
    if (!wrap) return;

    // ── Clear button: inject or remove without touching the input ─────────────
    const inputRow = wrap.querySelector('.dc-srch-input-row');
    if (inputRow) {
      const existingClear = inputRow.querySelector<HTMLButtonElement>('#dc-srch-clear');
      if (this.searchQuery && !existingClear) {
        const btn = document.createElement('button');
        btn.className = 'dc-srch-clear';
        btn.id = 'dc-srch-clear';
        btn.textContent = '✕';
        btn.addEventListener('click', () => {
          this.searchQuery = '';
          this.searchResults = [];
          this.searchLoading = false;
          clearTimeout(this.searchTimer);
          const inp = document.getElementById('dc-srch-input') as HTMLInputElement | null;
          if (inp) { inp.value = ''; inp.focus(); }
          this._renderSearchOnly();
        });
        inputRow.appendChild(btn);
      } else if (!this.searchQuery && existingClear) {
        existingClear.remove();
      }
    }

    // ── Results section: inject / update / remove ─────────────────────────────
    const resultsHtml = this._buildSearchResultsHtml();
    const existingResults = wrap.querySelector('.dc-srch-results');
    if (resultsHtml) {
      if (existingResults) {
        existingResults.innerHTML = resultsHtml;
      } else {
        const div = document.createElement('div');
        div.className = 'dc-srch-results';
        div.innerHTML = resultsHtml;
        wrap.appendChild(div);
      }
    } else if (existingResults) {
      existingResults.remove();
    }

    // ── Re-attach click listeners on newly rendered result buttons ────────────
    this._attachSearchResultListeners();
  }

  private _attachSearchResultListeners(): void {
    document.querySelectorAll('[data-override-phone]').forEach(btn => {
      btn.addEventListener('click', () => {
        const phone = (btn as HTMLElement).dataset.overridePhone!;
        const idStr = (btn as HTMLElement).dataset.overrideId;
        const id = idStr && idStr !== 'null' ? parseInt(idStr) : null;
        const name = (btn as HTMLElement).dataset.overrideName!;
        if (id) {
          this._overrideDial(phone, id, name);
        } else {
          dialerService.dial(phone);
          this.searchQuery = '';
          this.searchResults = [];
          this._renderSearchOnly();
        }
      });
    });
    document.querySelectorAll('[data-direct-phone]').forEach(btn => {
      btn.addEventListener('click', () => {
        const phone = (btn as HTMLElement).dataset.directPhone!;
        const name = (btn as HTMLElement).dataset.directName || 'Direct Dial';
        this._saveToLocalDialHistory(phone, name);
        dialerService.dial(phone);
        this.searchQuery = '';
        this.searchResults = [];
        this._renderSearchOnly();
      });
    });
    const viewAllBtn = document.getElementById('dc-view-all-hist');
    if (viewAllBtn) {
      viewAllBtn.addEventListener('click', () => routerService.navigate('call-history'));
    }
  }

  // ── DC_RECENT: Recent calls helpers ─────────────────────────────────────────

  private async _loadRecentCalls(): Promise<void> {
    if (this.recentCallsLoaded) return;
    this.recentCallsLoading = true;
    this._updateRecentPanel();
    try {
      const res = await apiService.get<any>('/crm/dialer/recent-calls?limit=15');
      this.recentCalls = res.data?.results || res.results || [];
      this.recentCallsLoaded = true;
    } catch (_) {
      this.recentCalls = [];
      this.recentCallsLoaded = true;
    } finally {
      this.recentCallsLoading = false;
      this._updateRecentPanel();
    }
  }

  private _updateRecentPanel(): void {
    // Only update the results div if search bar is visible and query is empty
    if (this.searchQuery) return;
    const wrap = document.querySelector('.dc-search-bar-wrap');
    if (!wrap) return;
    const resultsHtml = this._buildRecentCallsHtml();
    const existingResults = wrap.querySelector('.dc-srch-results');
    if (resultsHtml) {
      if (existingResults) {
        existingResults.innerHTML = resultsHtml;
      } else {
        const div = document.createElement('div');
        div.className = 'dc-srch-results';
        div.innerHTML = resultsHtml;
        wrap.appendChild(div);
      }
      this._attachSearchResultListeners();
    }
  }

  private _getLocalDialHistory(): any[] {
    try {
      return JSON.parse(localStorage.getItem('dc_dial_history') || '[]');
    } catch { return []; }
  }

  private _saveToLocalDialHistory(phone: string, name = 'Direct Dial'): void {
    try {
      const history = this._getLocalDialHistory();
      const entry = { phone, name, source: 'direct', call_outcome: '', dialed_at: new Date().toISOString() };
      const filtered = history.filter((h: any) => h.phone !== phone);
      filtered.unshift(entry);
      localStorage.setItem('dc_dial_history', JSON.stringify(filtered.slice(0, 20)));
      // Invalidate so panel refreshes next time
      this.recentCallsLoaded = false;
      this.recentCalls = [];
      void this._loadRecentCalls();
    } catch (_) {}
  }

  private async _runSearch(q: string): Promise<void> {
    try {
      const res = await apiService.get<any>(`/crm/dialer/search?q=${encodeURIComponent(q)}`);
      if (q !== this.searchQuery) return;
      // Backend returns {success, results:[...]} — apiService wraps body as res.data
      this.searchResults = res.data?.results || res.results || [];
    } catch (_) {
      this.searchResults = [];
    } finally {
      if (q === this.searchQuery) {
        this.searchLoading = false;
        this._renderSearchOnly();
      }
    }
  }

  private async _overrideDial(phone: string, leadId: number, name: string): Promise<void> {
    this.searchQuery = '';
    this.searchResults = [];
    this.callStartTime = Date.now();
    let lead: any = { lead_id: leadId, name, phone, queue_priority: 'upcoming' };
    try {
      const queueLead = dialerService.getQueue().find(q => q.lead_id === leadId);
      const companyId = queueLead?.company_id || this.currentLead?.company_id || '';
      const res = await apiService.get(`/crm/leads/${leadId}?company_id=${companyId}`);
      if (res.success && res.data) lead = { ...lead, ...res.data, lead_id: leadId };
    } catch (_) {}
    this.currentLead = lead as QueueItem;
    void dialerService.notifyCallActive(leadId);
    this._showCallingScreen(lead, phone);
    dialerService.dial(phone);
    this._render();
  }

  private _renderIdleState(): string {
    return `
      <div class="dc-idle-state">
        <div style="font-size:48px;margin-bottom:12px;">📞</div>
        <h3>Ready to Dial</h3>
        <p>${this.queueStats.total} leads in your queue · ${this.queueStats.overdue} overdue</p>
        <button class="dc-ctrl-btn start large" id="dc-start-btn-idle">▶ Start Dialing Session</button>
      </div>`;
  }

  private _renderPausedBanner(remaining: number): string {
    // DC_PAUSE_BANNER: Compact inline notice — does NOT hide the queue/lead card.
    // Resume is also available in the top banner controls (dc-resume-btn).
    return `
      <div style="background:#fff7ed;border:1.5px solid #fed7aa;border-radius:10px;margin:4px 16px 0;padding:10px 14px;display:flex;align-items:center;justify-content:space-between;gap:10px;">
        <div>
          <div style="font-size:13px;font-weight:700;color:#d97706;">⏸ Session Paused</div>
          <div style="font-size:11px;color:#92400e;margin-top:2px;">${remaining} leads remaining in queue · Tap Resume to continue dialing</div>
        </div>
        <button id="dc-resume-btn-idle" style="background:#d97706;color:white;border:none;border-radius:8px;padding:7px 16px;font-size:13px;font-weight:700;cursor:pointer;white-space:nowrap;flex-shrink:0;">▶ Resume</button>
      </div>`;
  }

  private _attachMainListeners(): void {
    document.getElementById('dc-start-btn')?.addEventListener('click', () => this._startSession());
    document.getElementById('dc-start-btn-idle')?.addEventListener('click', () => this._startSession());
    document.getElementById('dc-reload-queue-btn')?.addEventListener('click', async () => {
      await this._loadQueue();
      this._render();
    });
    document.getElementById('dc-pause-btn')?.addEventListener('click', () => this._pauseSession());
    document.getElementById('dc-resume-btn')?.addEventListener('click', () => this._resumeSession());
    document.getElementById('dc-resume-btn-idle')?.addEventListener('click', () => this._resumeSession());
    document.getElementById('dc-close-btn')?.addEventListener('click', () => this._closeSession());

    this.container.querySelectorAll('.dc-dial-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const phone = btn.getAttribute('data-phone') || '';
        const lead = dialerService.getCurrentLead();
        if (phone && lead) this._dial(phone, lead);
      });
    });
  }

  private _attachCatPriorityListeners(): void {
    // DC_CAT_PRIORITY: Toggle panel open/close
    document.getElementById('dc-cat-priority-toggle')?.addEventListener('click', () => {
      this.showCatPanel = !this.showCatPanel;
      this._render();
    });

    // Move category up in priority list
    this.container.querySelectorAll('[data-cp-up]').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = Number((btn as HTMLElement).dataset.cpUp);
        const idx = this.catPriorityIds.indexOf(id);
        if (idx > 0) {
          [this.catPriorityIds[idx - 1], this.catPriorityIds[idx]] = [this.catPriorityIds[idx], this.catPriorityIds[idx - 1]];
          this._render();
        }
      });
    });

    // Move category down in priority list
    this.container.querySelectorAll('[data-cp-dn]').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = Number((btn as HTMLElement).dataset.cpDn);
        const idx = this.catPriorityIds.indexOf(id);
        if (idx >= 0 && idx < this.catPriorityIds.length - 1) {
          [this.catPriorityIds[idx], this.catPriorityIds[idx + 1]] = [this.catPriorityIds[idx + 1], this.catPriorityIds[idx]];
          this._render();
        }
      });
    });

    // Remove category from priority list
    this.container.querySelectorAll('[data-cp-rm]').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = Number((btn as HTMLElement).dataset.cpRm);
        this.catPriorityIds = this.catPriorityIds.filter(x => x !== id);
        this._render();
      });
    });

    // Add category to priority list at chosen position (or end if no priority list yet)
    this.container.querySelectorAll('[data-cp-add]').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = Number((btn as HTMLElement).dataset.cpAdd);
        if (!this.catPriorityIds.includes(id)) {
          const row = (btn as HTMLElement).closest('[data-cp-add-row]') as HTMLElement | null;
          const posSelect = row?.querySelector(`[data-cp-pos-select="${id}"]`) as HTMLSelectElement | null;
          if (posSelect) {
            const insertAt = Number(posSelect.value);
            const updated = [...this.catPriorityIds];
            updated.splice(insertAt, 0, id);
            this.catPriorityIds = updated;
          } else {
            this.catPriorityIds = [...this.catPriorityIds, id];
          }
          this._render();
        }
      });
    });

    // Clear all priorities
    document.getElementById('dc-cppanel-clear')?.addEventListener('click', () => {
      this.catPriorityIds = [];
      this._render();
    });

    // Save and reload queue
    const saveBtn = document.getElementById('dc-cppanel-save') as HTMLButtonElement | null;
    if (saveBtn) {
      saveBtn.addEventListener('click', async () => {
        saveBtn.disabled = true;
        saveBtn.textContent = 'Saving…';
        try {
          await apiService.put('/crm/dialer/preferences', { category_priority: this.catPriorityIds });
          this.showCatPanel = false;
          await this._loadQueue();
          this._render();
        } catch {
          saveBtn.textContent = 'Save failed — retry';
          saveBtn.disabled = false;
        }
      });
    }
  }

  // ── Styles ────────────────────────────────────────────────────────────────────

  private _injectStyles(): void {
    if (document.getElementById('dc-dialer-styles')) return;
    const style = document.createElement('style');
    style.id = 'dc-dialer-styles';
    style.textContent = `
      .dc-dialer-wrap { padding: 0 0 80px; background: #f3f4f6; min-height: 100%; }

      /* Banner */
      .dc-banner { background: linear-gradient(135deg, #1e3a5f 0%, #0ea5e9 100%); padding: 16px; display: flex; justify-content: space-between; align-items: center; color: white; }
      .dc-banner-title { font-size: 18px; font-weight: 700; }
      .dc-banner-status { font-size: 12px; margin-top: 2px; opacity: 0.9; }
      .dc-session-controls { display: flex; gap: 8px; }
      .dc-ctrl-btn { border: none; border-radius: 20px; padding: 8px 16px; font-size: 13px; font-weight: 600; cursor: pointer; }
      .dc-ctrl-btn.start, .dc-ctrl-btn.resume { background: #059669; color: white; }
      .dc-ctrl-btn.pause { background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.4); }
      .dc-ctrl-btn.close { background: rgba(239,68,68,0.2); color: #fca5a5; border: 1px solid rgba(239,68,68,0.3); }
      .dc-ctrl-btn.large { padding: 14px 32px; font-size: 15px; border-radius: 30px; margin-top: 16px; }

      /* Missed Callbacks Panel */
      .dc-mcb-panel { margin: 12px 16px 0; background: white; border-radius: 12px; border: 1.5px solid #fca5a5; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
      .dc-mcb-header { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: #fff7f7; border-bottom: 1px solid #fecaca; font-size: 13px; font-weight: 700; color: #b91c1c; }
      .dc-mcb-list { padding: 4px 0; }
      .dc-mcb-row { display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; border-bottom: 1px solid #f3f4f6; gap: 10px; }
      .dc-mcb-row:last-child { border-bottom: none; }
      .dc-mcb-info { flex: 1; min-width: 0; }
      .dc-mcb-call-btn { display: inline-flex; align-items: center; gap: 4px; background: #059669; color: white; border-radius: 20px; padding: 7px 14px; font-size: 12px; font-weight: 700; text-decoration: none; white-space: nowrap; flex-shrink: 0; border: none; cursor: pointer; }
      .dc-mcb-call-btn:hover { background: #047857; }
      .dc-mcb-call-btn:disabled { background: #6b7280; cursor: not-allowed; }
      .dc-mcb-done-btn { display: inline-flex; align-items: center; justify-content: center; background: #f0fdf4; color: #15803d; border: 1.5px solid #86efac; border-radius: 50%; width: 32px; height: 32px; font-size: 15px; font-weight: 700; cursor: pointer; flex-shrink: 0; transition: background 0.15s; }
      .dc-mcb-done-btn:hover { background: #dcfce7; border-color: #4ade80; }

      /* Badges */
      .dc-queue-badges { display: flex; gap: 8px; padding: 12px 16px; overflow-x: auto; }
      .dc-badge { display: flex; flex-direction: column; align-items: center; background: white; border-radius: 10px; padding: 8px 12px; min-width: 60px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
      .dc-badge span { font-size: 20px; font-weight: 700; }
      .dc-badge { font-size: 10px; color: #6b7280; }
      .dc-badge.red { border-top: 3px solid #ef4444; }
      .dc-badge.red span { color: #ef4444; }
      .dc-badge.yellow { border-top: 3px solid #d97706; }
      .dc-badge.yellow span { color: #d97706; }
      .dc-badge.orange { border-top: 3px solid #f97316; }
      .dc-badge.orange span { color: #f97316; }
      .dc-badge.blue { border-top: 3px solid #0ea5e9; }
      .dc-badge.blue span { color: #0ea5e9; }
      .dc-badge.grey { border-top: 3px solid #6b7280; }
      .dc-badge.grey span { color: #6b7280; }

      /* DC_CAT_PRIORITY: Category Priority Panel */
      .dc-cppanel { margin: 0 16px 12px; background: white; border-radius: 14px; padding: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); border: 1px solid #e5e7eb; }
      .dc-cppanel-header { display: flex; flex-direction: column; gap: 2px; margin-bottom: 12px; font-size: 14px; font-weight: 700; color: #111827; }
      .dc-cppanel-section-label { font-size: 10px; font-weight: 700; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }
      .dc-cppanel-row { display: flex; align-items: center; gap: 8px; padding: 7px 0; border-bottom: 1px solid #f3f4f6; }
      .dc-cppanel-row:last-child { border-bottom: none; }
      .dc-cppanel-add-row { display: flex; align-items: center; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f3f4f6; }
      .dc-cppanel-add-row:last-child { border-bottom: none; }
      .dc-cppanel-rank { width: 22px; height: 22px; border-radius: 50%; background: #dbeafe; color: #1d4ed8; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
      .dc-cppanel-name { flex: 1; font-size: 13px; font-weight: 600; color: #1f2937; }
      .dc-cppanel-actions { display: flex; gap: 4px; flex-shrink: 0; }
      .dc-cppanel-btn { border: 1px solid #e5e7eb; background: #f9fafb; border-radius: 6px; padding: 4px 8px; font-size: 12px; font-weight: 600; cursor: pointer; color: #374151; }
      .dc-cppanel-btn.up, .dc-cppanel-btn.dn { color: #1d4ed8; border-color: #bfdbfe; background: #eff6ff; }
      .dc-cppanel-btn.rm { color: #dc2626; border-color: #fca5a5; background: #fff1f2; }
      .dc-cppanel-btn.add { color: #059669; border-color: #6ee7b7; background: #f0fdf4; }
      .dc-cppanel-btn-ph { width: 30px; display: inline-block; }
      .dc-cppanel-footer { display: flex; gap: 8px; justify-content: flex-end; margin-top: 14px; padding-top: 12px; border-top: 1px solid #f3f4f6; }

      /* Lead Card */
      .dc-lead-card { margin: 0 16px 16px; background: white; border-radius: 16px; padding: 18px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); }
      .dc-lead-card.overdue { border-left: 4px solid #ef4444; }
      .dc-lead-card.due_today { border-left: 4px solid #d97706; }
      .dc-lead-card.new { border-left: 4px solid #f97316; }
      .dc-lead-card.second_contact { border-left: 4px solid #0ea5e9; }
      .dc-lead-card.upcoming { border-left: 4px solid #6b7280; }
      .dc-lead-card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
      .dc-priority-tag { font-size: 11px; font-weight: 700; background: #f3f4f6; padding: 3px 8px; border-radius: 6px; }
      .dc-queue-pos { font-size: 11px; color: #9ca3af; }
      .dc-lead-name { font-size: 20px; font-weight: 700; color: #111827; margin-bottom: 4px; }
      .dc-lead-meta { font-size: 12px; color: #6b7280; margin-bottom: 4px; }
      .dc-status-chip { background: #dbeafe; color: #1d4ed8; padding: 1px 6px; border-radius: 4px; font-size: 11px; }
      .dc-last-contact { font-size: 11px; color: #9ca3af; margin-bottom: 8px; }
      .dc-lead-desc { font-size: 13px; color: #374151; background: #f9fafb; border-radius: 8px; padding: 8px; margin-bottom: 12px; }
      .dc-dial-row { display: flex; flex-direction: column; gap: 8px; }
      .dc-dial-btn { background: #059669; color: white; border: none; border-radius: 30px; padding: 14px 20px; font-size: 15px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 8px; justify-content: center; }
      .dc-dial-btn.alt { background: #0ea5e9; }
      .dc-web-note { font-size: 11px; color: #9ca3af; text-align: center; margin-top: 8px; }

      /* Queue List */
      .dc-queue-list { margin: 0 16px 16px; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
      .dc-queue-list-title { padding: 12px 16px; font-size: 12px; font-weight: 700; color: #6b7280; text-transform: uppercase; background: #f9fafb; border-bottom: 1px solid #f3f4f6; }
      .dc-queue-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-bottom: 1px solid #f3f4f6; }
      .dc-queue-item:last-child { border-bottom: none; }
      .dc-queue-item:active { background: #f9fafb; }
      .dc-queue-item-num { width: 24px; height: 24px; border-radius: 50%; background: #f3f4f6; color: #6b7280; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
      .dc-queue-item-chevron { color: #d1d5db; font-size: 22px; font-weight: 300; flex-shrink: 0; line-height: 1; margin-left: auto; }
      .dc-queue-item-name { font-size: 13px; font-weight: 600; color: #1f2937; }
      .dc-queue-item-meta { font-size: 11px; color: #9ca3af; margin-top: 2px; }
      .dc-prio-overdue { color: #ef4444; }
      .dc-prio-due_today { color: #d97706; }
      .dc-prio-new { color: #f97316; }
      .dc-prio-second_contact { color: #0ea5e9; }

      /* Unassigned lead extras in queue list */
      .dc-unassigned-badge { font-size: 9px; font-weight: 700; background: #fef3c7; color: #92400e; border-radius: 4px; padding: 1px 5px; vertical-align: middle; margin-left: 4px; text-transform: uppercase; letter-spacing: 0.4px; }
      .dc-queue-cat-tag { display: inline-block; font-size: 10px; font-weight: 600; background: #ede9fe; color: #6d28d9; border-radius: 4px; padding: 1px 6px; margin-left: 4px; }
      .dc-queue-last-dial { color: #6b7280; }
      .dc-nmc-btn { display: inline-block; margin-top: 5px; font-size: 11px; font-weight: 600; color: #ef4444; background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; padding: 3px 9px; cursor: pointer; line-height: 1.4; }
      .dc-nmc-btn:active { background: #fee2e2; }
      .dc-current-nmc-row { margin-top: 10px; border-top: 1px solid #f3f4f6; padding-top: 10px; }
      .dc-current-nmc-btn { display: inline-flex; align-items: center; gap: 5px; font-size: 13px; font-weight: 600; color: #ef4444; background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 7px 16px; cursor: pointer; line-height: 1.4; }
      .dc-current-nmc-btn:active { background: #fee2e2; }
      .dc-current-nmc-btn:disabled { opacity: 0.5; cursor: not-allowed; }

      /* DC_CAT_DEFER: Save category for later */
      .dc-defer-current-row { margin-top: 8px; border-top: 1px solid #f3f4f6; padding-top: 8px; }
      .dc-defer-current-btn { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600; color: #6366f1; background: #eef2ff; border: 1px solid #c7d2fe; border-radius: 8px; padding: 6px 14px; cursor: pointer; line-height: 1.4; width: 100%; justify-content: center; }
      .dc-defer-current-btn:active { background: #e0e7ff; }
      .dc-qcat-header { display: flex; align-items: center; justify-content: space-between; padding: 7px 16px; background: #f5f3ff; border-bottom: 1px solid #e9e5ff; border-top: 1px solid #e9e5ff; }
      .dc-qcat-header.deferred { background: #f9fafb; }
      .dc-qcat-label { font-size: 11px; font-weight: 700; color: #6d28d9; text-transform: uppercase; letter-spacing: 0.04em; }
      .dc-qcat-header.deferred .dc-qcat-label { color: #9ca3af; }
      .dc-qcat-defer-btn { font-size: 11px; font-weight: 600; color: #6366f1; background: #eef2ff; border: 1px solid #c7d2fe; border-radius: 6px; padding: 3px 9px; cursor: pointer; }
      .dc-qcat-defer-btn:active { background: #e0e7ff; }
      .dc-qcat-deferred-tag { font-size: 11px; color: #9ca3af; font-style: italic; }
      .dc-queue-item-deferred { opacity: 0.55; }
      .dc-queue-item-info { flex: 1; min-width: 0; }

      /* Popup form optional label hint */
      .dc-field-optional { font-size: 9px; font-weight: 400; color: #9ca3af; text-transform: none; }

      /* Complete lead edit form — groups, inline cols, phone rows */
      .dc-form-group-label { font-size: 10px; font-weight: 800; color: #6366f1; text-transform: uppercase; letter-spacing: 0.7px; margin: 14px 0 6px; padding-bottom: 4px; border-bottom: 1px solid #ede9fe; }
      .dc-form-row-inline { display: flex; gap: 10px; }
      .dc-form-col { flex: 1; min-width: 0; }
      .dc-form-col label { display: block; font-size: 10px; font-weight: 600; color: #6b7280; text-transform: uppercase; margin-bottom: 3px; }
      .dc-form-col select, .dc-form-col input { width: 100%; padding: 8px 10px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 13px; color: #1f2937; background: white; box-sizing: border-box; }
      .dc-phone-row { display: flex; gap: 8px; align-items: center; }
      .dc-phone-row input { flex: 1; min-width: 0; }
      .dc-wa-toggle { display: flex; align-items: center; gap: 4px; white-space: nowrap; font-size: 12px; font-weight: 600; color: #059669; cursor: pointer; }
      .dc-wa-toggle input { width: auto; margin: 0; accent-color: #059669; }

      /* Idle / Paused */
      .dc-idle-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px 24px; text-align: center; }
      .dc-idle-state h3 { font-size: 20px; font-weight: 700; color: #1f2937; margin-bottom: 8px; }
      .dc-idle-state p { font-size: 14px; color: #6b7280; }

      /* Popup */
      .dc-popup-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 9999; display: flex; align-items: flex-end; }
      .dc-popup-sheet { background: white; border-radius: 24px 24px 0 0; width: 100%; max-height: 92vh; display: flex; flex-direction: column; }
      .dc-popup-header { padding: 20px 20px 16px; border-bottom: 1px solid #f3f4f6; display: flex; justify-content: space-between; align-items: flex-start; flex-shrink: 0; }
      .dc-popup-name { font-size: 18px; font-weight: 700; color: #111827; }
      .dc-popup-meta { font-size: 12px; color: #6b7280; margin-top: 2px; }
      .dc-popup-priority-badge { font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 20px; background: #f3f4f6; white-space: nowrap; }
      .dc-popup-scroll { overflow-y: auto; flex: 1; padding: 0 20px; }
      .dc-popup-section { padding: 16px 0; border-bottom: 1px solid #f9fafb; }
      .dc-popup-section:last-child { border-bottom: none; }
      .dc-popup-section-title { font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase; margin-bottom: 10px; }
      /* DC_POPUP_QD: Quick Dial search bar inside after-call popup */
      .dc-popup-qd-section { padding: 12px 0 10px; border-bottom: 2px solid #f0f0f0; }
      .dc-popup-qd-input-row { display: flex; align-items: center; gap: 8px; background: #f9fafb; border: 1.5px solid #e5e7eb; border-radius: 10px; padding: 8px 12px; }
      .dc-popup-qd-icon { font-size: 16px; flex-shrink: 0; opacity: 0.6; }
      .dc-popup-qd-input { flex: 1; border: none; background: transparent; font-size: 14px; color: #111827; outline: none; min-width: 0; }
      .dc-popup-qd-input::placeholder { color: #9ca3af; }
      .dc-popup-qd-clear { background: none; border: none; cursor: pointer; color: #9ca3af; font-size: 15px; padding: 0; line-height: 1; flex-shrink: 0; align-items: center; justify-content: center; }
      .dc-popup-qd-empty { font-size: 12px; color: #9ca3af; padding: 8px 4px; }
      .dc-popup-qd-item { display: flex; align-items: center; justify-content: space-between; padding: 8px 4px; border-bottom: 1px solid #f3f4f6; gap: 8px; }
      .dc-popup-qd-item:last-child { border-bottom: none; }
      .dc-popup-qd-info { flex: 1; min-width: 0; }
      .dc-popup-qd-name { font-size: 13px; font-weight: 600; color: #111827; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .dc-popup-qd-meta { font-size: 11px; color: #6b7280; margin-top: 1px; }
      .dc-popup-qd-btns { display: flex; gap: 6px; flex-shrink: 0; }
      .dc-popup-qd-dial { background: #059669; color: white; border: none; border-radius: 20px; padding: 6px 14px; font-size: 15px; cursor: pointer; }
      .dc-popup-qd-dial.alt { background: #0ea5e9; }
      .dc-outcome-btns { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
      .dc-outcome-btn { padding: 10px; border: 2px solid #e5e7eb; border-radius: 10px; background: white; font-size: 13px; font-weight: 600; cursor: pointer; color: #374151; }
      .dc-outcome-btn.selected { border-color: #059669; color: #059669; }
      .dc-form-row { margin-bottom: 10px; }
      .dc-form-row label { display: block; font-size: 11px; font-weight: 600; color: #6b7280; text-transform: uppercase; margin-bottom: 4px; }
      .dc-form-row select, .dc-form-row input, .dc-form-row textarea { width: 100%; padding: 8px 10px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 14px; color: #1f2937; background: white; }
      .dc-form-row textarea { resize: none; }
      .dc-detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
      .dc-detail-item { background: #f9fafb; border-radius: 8px; padding: 8px 10px; }
      .dc-detail-item--wide { grid-column: 1 / -1; }
      .dc-detail-item span { display: block; font-size: 10px; color: #9ca3af; text-transform: uppercase; }
      .dc-detail-item b { font-size: 13px; color: #1f2937; }
      .dc-detail-desc { margin-top: 8px; font-size: 13px; color: #374151; background: #f9fafb; padding: 8px; border-radius: 8px; }
      .dc-dnc-label { display: flex; align-items: center; gap: 10px; cursor: pointer; font-size: 13px; color: #ef4444; }
      .dc-dnc-label input { width: 18px; height: 18px; flex-shrink: 0; }
      .dc-popup-actions { padding: 12px 20px 24px; display: flex; flex-wrap: wrap; gap: 10px; flex-shrink: 0; border-top: 1px solid #f3f4f6; }
      .dc-popup-skip-btn { flex: 1; padding: 13px; border: 1px solid #e5e7eb; border-radius: 12px; background: white; font-size: 13px; font-weight: 600; color: #6b7280; cursor: pointer; }
      .dc-popup-save-btn { flex: 2; padding: 13px; border: none; border-radius: 12px; background: #059669; color: white; font-size: 14px; font-weight: 700; cursor: pointer; }
      .dc-popup-save-btn:disabled { opacity: 0.6; }
      /* Activity Chips */
      .dc-act-chips { display: flex; flex-wrap: wrap; gap: 7px; }
      .dc-act-chip { padding: 6px 12px; border: 1.5px solid #e5e7eb; border-radius: 20px; background: white; font-size: 12px; font-weight: 600; cursor: pointer; color: #374151; transition: all .15s; }
      .dc-act-chip.selected { border-color: #7c3aed; background: #ede9fe; color: #7c3aed; }
      /* Hold button */
      .dc-hold-btn { width: 100%; padding: 10px 16px; border: 1.5px dashed #d97706; border-radius: 10px; background: #fffbeb; color: #92400e; font-size: 13px; font-weight: 600; cursor: pointer; text-align: center; transition: all .2s; }
      .dc-hold-btn.active { border-color: #059669; background: #d1fae5; color: #065f46; border-style: solid; }

      /* Quick Dial Search */
      .dc-search-bar-wrap { margin: 0 16px 12px; background: white; border-radius: 14px; padding: 12px 14px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); border: 1px solid #e5e7eb; }
      .dc-srch-label { font-size: 10px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 8px; }
      .dc-srch-input-row { position: relative; display: flex; align-items: center; gap: 6px; }
      .dc-srch-input { flex: 1; border: 1.5px solid #d1d5db; border-radius: 10px; padding: 9px 12px; font-size: 14px; outline: none; }
      .dc-srch-input:focus { border-color: #0ea5e9; }
      .dc-srch-clear { background: none; border: none; color: #9ca3af; font-size: 16px; cursor: pointer; padding: 4px 6px; }
      .dc-srch-results { margin-top: 8px; border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden; max-height: 240px; overflow-y: auto; }
      .dc-srch-item { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-bottom: 1px solid #f3f4f6; gap: 8px; }
      .dc-srch-item:last-child { border-bottom: none; }
      .dc-srch-info { flex: 1; min-width: 0; }
      .dc-srch-name-row { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }
      .dc-srch-name { font-size: 13px; font-weight: 700; color: #1f2937; }
      .dc-srch-src-badge { font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 8px; white-space: nowrap; flex-shrink: 0; }
      .dc-srch-src-badge.lead { background: #eff6ff; color: #1d4ed8; }
      .dc-srch-src-badge.contact { background: #f0f9ff; color: #0369a1; }
      .dc-srch-called-badge { background: #d1fae5; color: #065f46; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 8px; white-space: nowrap; flex-shrink: 0; }
      .dc-srch-meta { font-size: 11px; color: #6b7280; margin-top: 1px; }
      .dc-srch-btns { display: flex; gap: 6px; flex-shrink: 0; }
      .dc-srch-dial { background: #059669; color: white; border: none; border-radius: 20px; padding: 6px 12px; font-size: 14px; cursor: pointer; }
      .dc-srch-dial.alt { background: #0ea5e9; }
      .dc-srch-loading { padding: 10px 14px; font-size: 12px; color: #9ca3af; text-align: center; }
      .dc-srch-contacts-btn { background: #eff6ff; border: 1.5px solid #bfdbfe; border-radius: 10px; color: #1d4ed8; font-size: 18px; padding: 6px 10px; cursor: pointer; flex-shrink: 0; }
      .dc-srch-direct-wrap { padding: 10px 14px; text-align: center; }
      .dc-srch-nr-text { font-size: 11px; color: #9ca3af; margin-bottom: 8px; }
      .dc-srch-direct-btn { background: #059669; color: white; border: none; border-radius: 24px; padding: 10px 20px; font-size: 14px; font-weight: 700; cursor: pointer; width: 100%; }
      .dc-srch-direct-btn:active { background: #047857; }
      .dc-recent-header { font-size: 10px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: .5px; padding: 8px 14px 4px; border-bottom: 1px solid #f3f4f6; }

      /* ── Call Method Modal (DC_MYOP_001) ──────────────────────────────────── */
      #dc-method-modal { position: fixed; inset: 0; z-index: 10500; }
      .dc-method-backdrop { position: absolute; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: flex-end; justify-content: center; }
      .dc-method-sheet { background: white; border-radius: 24px 24px 0 0; width: 100%; max-width: 480px; padding: 12px 20px 36px; }
      .dc-method-handle { width: 36px; height: 4px; background: #e5e7eb; border-radius: 2px; margin: 0 auto 16px; }
      .dc-method-lead { font-size: 18px; font-weight: 800; color: #1f2937; text-align: center; }
      .dc-method-phone { font-size: 14px; color: #6b7280; text-align: center; margin-bottom: 18px; letter-spacing: 0.5px; }
      .dc-method-title { font-size: 13px; font-weight: 700; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }
      .dc-method-btn { width: 100%; display: flex; align-items: center; gap: 14px; padding: 16px 18px; border-radius: 16px; border: 2px solid #e5e7eb; background: white; cursor: pointer; text-align: left; margin-bottom: 12px; transition: border-color .15s, background .15s; }
      .dc-method-btn--myop { border-color: #7c3aed; background: #faf5ff; }
      .dc-method-btn--myop:active { background: #f3e8ff; }
      .dc-method-btn--normal:not(.dc-method-btn--locked):active { background: #f9fafb; }
      .dc-method-btn--locked { opacity: 0.55; cursor: not-allowed; }
      .dc-method-icon { font-size: 24px; flex-shrink: 0; }
      .dc-method-label { display: flex; flex-direction: column; gap: 2px; }
      .dc-method-label b { font-size: 15px; font-weight: 700; color: #1f2937; }
      .dc-method-label small { font-size: 12px; color: #6b7280; font-weight: 400; }
      .dc-method-btn--myop .dc-method-label b { color: #7c3aed; }
      .dc-method-cancel { width: 100%; background: none; border: none; color: #9ca3af; font-size: 14px; padding: 10px; cursor: pointer; margin-top: 4px; }
      .dc-method-badge { background: rgba(124,58,237,0.18); color: #7c3aed; font-size: 12px; font-weight: 700; border-radius: 20px; padding: 4px 14px; margin-bottom: 10px; display: inline-block; }

      /* ── Calling Screen ───────────────────────────────────────────────────── */
      #dc-calling-screen { position: fixed; inset: 0; z-index: 10000; }
      .dc-calling-overlay { position: absolute; inset: 0; background: linear-gradient(160deg, #0f2942 0%, #0c4a6e 60%, #0369a1 100%); display: flex; align-items: center; justify-content: center; }
      .dc-calling-inner { display: flex; flex-direction: column; align-items: center; padding: 40px 32px; text-align: center; }
      .dc-calling-avatar { width: 96px; height: 96px; border-radius: 50%; background: rgba(255,255,255,0.15); border: 3px solid rgba(255,255,255,0.3); display: flex; align-items: center; justify-content: center; font-size: 40px; font-weight: 800; color: white; margin-bottom: 20px; box-shadow: 0 0 0 0 rgba(255,255,255,0.4); animation: dc-avatar-pulse 2s infinite; }
      @keyframes dc-avatar-pulse { 0% { box-shadow: 0 0 0 0 rgba(255,255,255,0.35); } 70% { box-shadow: 0 0 0 20px rgba(255,255,255,0); } 100% { box-shadow: 0 0 0 0 rgba(255,255,255,0); } }
      .dc-calling-name { font-size: 26px; font-weight: 800; color: white; margin-bottom: 6px; }
      .dc-calling-phone { font-size: 15px; color: rgba(255,255,255,0.7); margin-bottom: 24px; letter-spacing: 0.5px; }
      .dc-calling-status { display: flex; align-items: center; gap: 6px; color: rgba(255,255,255,0.85); font-size: 14px; font-weight: 600; margin-bottom: 16px; }
      .dc-calling-dot { width: 7px; height: 7px; border-radius: 50%; background: #6ee7b7; display: inline-block; animation: dc-dot-bounce 1.2s infinite ease-in-out; }
      .dc-calling-dot:nth-child(2) { animation-delay: 0.2s; }
      .dc-calling-dot:nth-child(3) { animation-delay: 0.4s; }
      @keyframes dc-dot-bounce { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; } 40% { transform: scale(1); opacity: 1; } }
      .dc-calling-hint { font-size: 13px; color: rgba(255,255,255,0.55); margin-bottom: 36px; line-height: 1.6; }
      .dc-call-ended-btn { background: #059669; color: white; border: none; border-radius: 50px; padding: 18px 36px; font-size: 17px; font-weight: 700; cursor: pointer; box-shadow: 0 6px 24px rgba(5,150,105,0.45); transition: transform .15s, box-shadow .15s; width: 100%; max-width: 320px; margin-bottom: 14px; }
      .dc-call-ended-btn:active { transform: scale(0.97); box-shadow: 0 3px 12px rgba(5,150,105,0.3); }
      .dc-calling-cancel-btn { background: transparent; color: rgba(255,255,255,0.45); border: 1px solid rgba(255,255,255,0.2); border-radius: 30px; padding: 10px 28px; font-size: 13px; font-weight: 600; cursor: pointer; transition: color .15s; }
      .dc-calling-cancel-btn:active { color: rgba(255,255,255,0.8); }

      /* ── Lead Detail Bottom-Sheet ────────────────────────────────────────────── */
      #dc-lead-detail-sheet { position: fixed; inset: 0; z-index: 20000; display: flex; flex-direction: column; justify-content: flex-end; }
      .dc-lds-backdrop { position: absolute; inset: 0; background: rgba(0,0,0,0.45); }
      .dc-lds-panel { position: relative; background: white; border-radius: 20px 20px 0 0; max-height: 85vh; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 -4px 24px rgba(0,0,0,0.18); }
      .dc-lds-handle { width: 40px; height: 4px; background: #e5e7eb; border-radius: 2px; margin: 10px auto 0; flex-shrink: 0; }
      .dc-lds-body { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
      .dc-lds-loading { align-items: center; justify-content: center; }
      .dc-lds-spinner { font-size: 16px; color: #9ca3af; padding: 40px; }
      .dc-lds-header { display: flex; align-items: flex-start; gap: 10px; padding: 16px 16px 12px; border-bottom: 1px solid #f3f4f6; flex-shrink: 0; }
      .dc-lds-name { flex: 1; font-size: 17px; font-weight: 800; color: #1f2937; line-height: 1.3; }
      .dc-lds-badges { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 4px; }
      .dc-lds-status-badge { font-size: 11px; font-weight: 700; background: #eff6ff; color: #1d4ed8; border-radius: 6px; padding: 2px 8px; }
      .dc-lds-close-btn { background: #f3f4f6; border: none; border-radius: 50%; width: 30px; height: 30px; font-size: 14px; cursor: pointer; flex-shrink: 0; display: flex; align-items: center; justify-content: center; color: #6b7280; }
      .dc-lds-scroll { flex: 1; overflow-y: auto; padding: 12px 16px 24px; }
      .dc-lds-row { font-size: 13px; color: #374151; padding: 6px 0; border-bottom: 1px solid #f9fafb; }
      .dc-lds-section-title { font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin: 16px 0 8px; }
      .dc-lds-attempt { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; padding: 8px 0; border-bottom: 1px solid #f9fafb; }
      .dc-lds-outcome-pill { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 12px; text-transform: capitalize; }
      .dc-lds-attempt-date { font-size: 11px; color: #9ca3af; }
      .dc-lds-attempt-note { width: 100%; font-size: 12px; color: #6b7280; padding-top: 2px; font-style: italic; }
      .dc-lds-note { font-size: 13px; color: #374151; padding: 8px 0; border-bottom: 1px solid #f9fafb; }
      .dc-lds-note-date { font-size: 11px; color: #9ca3af; margin-right: 6px; }
      .dc-lds-empty { font-size: 12px; color: #9ca3af; padding: 8px 0; }
    `;
    document.head.appendChild(style);
  }
}
