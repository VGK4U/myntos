/**
 * Auto Dialer Service
 * DC Protocol: DC_DIALER_SERVICE_001
 * Manages dialer session state, queue, call-end detection (Android), and sync polling.
 */

import { Preferences } from '@capacitor/preferences';
import { apiService } from './api.service';
import { APP_CONFIG } from '../config/app.config';

const SESSION_KEY = 'dialer_session';
const QUEUE_KEY = 'dialer_queue';
const INDEX_KEY = 'dialer_index';
const POLL_INTERVAL_MS = 5000;
const CALL_LOG_POLL_MS = 3000;
const CALL_LOG_POLL_RETRIES = 6; // DC_DIALER_FIX3: 6 × 3s = 18s max wait (reduced from 60s)

export type CallOutcome = 'answered' | 'no_answer' | 'busy' | 'callback' | 'skip';
export type QueuePriority = 'overdue' | 'due_today' | 'new' | 'second_contact' | 'upcoming';

export interface QueueItem {
  lead_id: number;
  name: string;
  phone: string;
  alternate_phone: string;
  phone_primary_whatsapp: boolean;
  phone_secondary_whatsapp: boolean;
  status: string;
  priority: string;
  category_id: number | null;
  category_name: string | null;
  company_id: number;
  source: string;
  description: string;
  requirements: string;
  looking_for: string;
  recent_comments: string;
  city: string;
  area: string;
  budget_min: number | null;
  budget_max: number | null;
  next_followup_date: string | null;
  last_contact_date: string | null;
  last_contact_days: number | null;
  queue_priority: QueuePriority;
  slot_type: 'assigned' | 'unassigned';
}

export interface DialerSession {
  id: number;
  status: 'active' | 'paused' | 'closed';
  current_index: number;
  started_at: string;
  queue_data: string;
}

export interface AttemptResult {
  session_id: number;
  lead_id: number;
  call_outcome: CallOutcome;
  call_method?: string;
  duration_seconds?: number;
  note?: string;
  next_followup_date?: string;
  new_status?: string;
  new_priority?: string;
  new_source?: string;
  new_category_id?: number;
  do_not_call?: boolean;
  current_index?: number;
  queue_lead_ids?: number[];
  activity_type?: string;
  activity_minutes?: number;
  lead_update_minutes?: number;
}

export interface QueueStats {
  total: number;
  overdue: number;
  due_today: number;
  new_leads: number;
  second_contact: number;
  queue: QueueItem[];
}

type PopupCallback = (leadId: number, attemptId?: number) => void;

class DialerService {
  private session: DialerSession | null = null;
  private queue: QueueItem[] = [];
  private currentIndex: number = 0;
  private isDialing: boolean = false;
  private callPollTimer: ReturnType<typeof setInterval> | null = null;
  private syncPollTimer: ReturnType<typeof setInterval> | null = null;
  private ctcPollTimer: ReturnType<typeof setInterval> | null = null;
  private onPopupCallback: PopupCallback | null = null;
  private lastDialedAt: number = 0;
  private lastAttemptId: number | null = null;
  private _appStateHandle: { remove: () => void } | null = null;
  // DC_RESUME_FIX: Anchor resume to a lead ID, not a position. Set by checkExistingSession,
  // consumed and cleared by fetchQueue so the index lands on the correct lead after re-sort.
  private _pendingCurrentLeadId: number | null = null;

  // ── Queue Fetch ──────────────────────────────────────────────────────────────

  async fetchQueue(companyId?: number): Promise<QueueStats> {
    // DC_DIALER_P1: Throw on failure — caller must handle error, not receive silent empty queue
    const params = companyId ? `?company_id=${companyId}` : '';
    const res = await apiService.get<QueueStats>(`/crm/dialer/queue${params}`);
    const data = res.data as QueueStats | undefined;
    if (!res.success) {
      throw new Error('Unable to load your call queue. Check your connection and tap Reload.');
    }
    if (data?.queue) {
      this.queue = data.queue;
    }
    // DC_RESUME_FIX: If a session resume anchored to a specific lead ID, re-align currentIndex
    // to wherever that lead now sits in the freshly-sorted queue. This handles the case where
    // the queue re-prioritises after a call (e.g. next_followup_date changed) so position N
    // no longer means the same lead as when the session was saved.
    if (this._pendingCurrentLeadId !== null) {
      const idx = this.queue.findIndex(q => q.lead_id === this._pendingCurrentLeadId);
      if (idx >= 0) this.currentIndex = idx;
      this._pendingCurrentLeadId = null;
    }
    return data ?? { total: 0, overdue: 0, due_today: 0, new_leads: 0, second_contact: 0, queue: [] };
  }

  // ── Session Management ──────────────────────────────────────────────────────

  async startSession(queueLeadIds: number[], companyId?: number): Promise<DialerSession | null> {
    const res = await apiService.post<{ session: DialerSession }>('/crm/dialer/session/start', {
      queue_lead_ids: queueLeadIds,
      company_id: companyId || null,
    });
    const data = res.data as { session?: DialerSession } | undefined;
    if (res.success && data?.session) {
      this.session = data.session;
      this.currentIndex = 0;
      await this._saveLocalState();
      return this.session;
    }
    return null;
  }

  async pauseSession(queueLeadIds?: number[]): Promise<void> {
    if (!this.session) return;
    await apiService.post('/crm/dialer/session/pause', {
      session_id: this.session.id,
      current_index: this.currentIndex,
      queue_lead_ids: queueLeadIds || null,
    });
    if (this.session) this.session.status = 'paused';
    this.stopCallPoll();
    this.stopAppListener();
    this.stopSyncPoll();
    this.stopClickToCallPoll();
    await this._saveLocalState();
  }

  async resumeSession(): Promise<{ session: DialerSession; current_index: number; queue_lead_ids: number[] } | null> {
    const res = await apiService.post('/crm/dialer/session/resume', {});
    const data = res.data as { session?: DialerSession; current_index?: number; queue_lead_ids?: number[] } | undefined;
    if (res.success && data?.session) {
      this.session = data.session;
      this.currentIndex = data.current_index ?? 0;
      const leadIds: number[] = data.queue_lead_ids ?? [];
      // Restore queue items from saved IDs
      if (this.queue.length === 0 && leadIds.length > 0) {
        const fetchedIds = new Set(leadIds);
        const fullRes = await this.fetchQueue();
        this.queue = fullRes.queue.filter(q => fetchedIds.has(q.lead_id));
        // Preserve skip order
        this.queue.sort((a, b) => leadIds.indexOf(a.lead_id) - leadIds.indexOf(b.lead_id));
      }
      await this._saveLocalState();
      return { session: this.session as DialerSession, current_index: this.currentIndex, queue_lead_ids: leadIds };
    }
    return null;
  }

  async closeSession(): Promise<void> {
    if (!this.session) return;
    const sessionId = this.session.id;
    // DC_DIALER_P3: Clear local state FIRST — prevents ghost sessions even if API call fails
    this.session = null;
    this.currentIndex = 0;
    this.queue = [];
    this.isDialing = false;
    this.stopCallPoll();
    this.stopAppListener();
    this.stopSyncPoll();
    this.stopClickToCallPoll();
    await this._clearLocalState();
    // Best-effort server close — if it fails, the session auto-expires server-side after 8h
    try {
      await apiService.post('/crm/dialer/session/close', { session_id: sessionId });
    } catch (_) { /* silent — local state already cleared */ }
  }

  async checkExistingSession(): Promise<DialerSession | null> {
    const res = await apiService.get('/crm/dialer/session/current');
    const data = res.data as { session?: DialerSession; current_index?: number; queue_lead_ids?: number[] } | undefined;
    if (!res.success) {
      // DC_DIALER_P4: 401 (expired token) or 500 → clear ghost local session, start fresh
      await this._clearLocalState();
      this.session = null;
      return null;
    }
    if (data?.session) {
      this.session = data.session;
      const serverIdx = data.current_index ?? this.session?.current_index ?? 0;
      this.currentIndex = serverIdx;
      // DC_RESUME_FIX: Derive which lead should be current from the saved queue order.
      // fetchQueue() will re-align currentIndex to wherever that lead sits in the fresh queue.
      const leadIds: number[] = data.queue_lead_ids ?? [];
      if (leadIds.length > 0 && serverIdx < leadIds.length) {
        this._pendingCurrentLeadId = leadIds[serverIdx];
      }
      return this.session;
    }
    return null;
  }

  // ── Queue Navigation ────────────────────────────────────────────────────────

  getCurrentLead(): QueueItem | null {
    return this.queue[this.currentIndex] ?? null;
  }

  getNextLead(): QueueItem | null {
    return this.queue[this.currentIndex + 1] ?? null;
  }

  advanceQueue(): boolean {
    if (this.currentIndex < this.queue.length - 1) {
      this.currentIndex++;
      this._saveLocalState();
      return true;
    }
    return false; // Queue complete
  }

  skipToEnd(leadId: number): void {
    const idx = this.queue.findIndex(q => q.lead_id === leadId);
    if (idx >= 0 && idx !== this.queue.length - 1) {
      const [item] = this.queue.splice(idx, 1);
      this.queue.push(item);
      // Adjust current index if needed
      if (idx < this.currentIndex) {
        this.currentIndex = Math.max(0, this.currentIndex - 1);
      }
    }
    this._saveLocalState();
  }

  /** DC_NMC_FIX: Remove a lead from the in-memory queue entirely (e.g. after "Not my category"). */
  removeFromQueue(leadId: number): void {
    const idx = this.queue.findIndex(q => q.lead_id === leadId);
    if (idx < 0) return;
    this.queue.splice(idx, 1);
    // If the removed item was before or at the current pointer, shift pointer back
    if (idx <= this.currentIndex) {
      this.currentIndex = Math.max(0, this.currentIndex - 1);
    }
    this._saveLocalState();
  }

  getQueue(): QueueItem[] { return this.queue; }
  getQueueLeadIds(): number[] { return this.queue.map(q => q.lead_id); }
  getCurrentIndex(): number { return this.currentIndex; }
  getSession(): DialerSession | null { return this.session; }
  isActive(): boolean { return this.session?.status === 'active'; }
  isPaused(): boolean { return this.session?.status === 'paused'; }

  // ── Dial + Call-End Detection ────────────────────────────────────────────────

  dial(phone: string): void {
    this.isDialing = true;
    this.lastDialedAt = Date.now();
    const cleaned = phone.replace(/[^+\d]/g, '');
    window.location.href = `tel:${cleaned}`;
    // Start polling for call end on Android
    if (APP_CONFIG.isNativeApp()) {
      this._startCallEndPoll(phone);
    }
  }

  onPopup(cb: PopupCallback): void {
    this.onPopupCallback = cb;
  }

  triggerPopupManually(leadId: number): void {
    this.isDialing = false;
    if (this.onPopupCallback) {
      this.onPopupCallback(leadId, this.lastAttemptId ?? undefined);
    }
  }

  private _startCallEndPoll(phone: string): void {
    this.stopCallPoll();
    this.stopAppListener();
    let retries = 0;
    const normalizedPhone = phone.replace(/[^+\d]/g, '').slice(-10);
    void normalizedPhone; // referenced for potential future use
    const dialedAt = this.lastDialedAt;

    // DC_DIALER_FIX3: Fire popup immediately when app returns to foreground after a dial
    // Handles no-answer / short calls where call-sync hasn't updated yet
    import('@capacitor/app').then(({ App }) => {
      App.addListener('appStateChange', (state) => {
        if (state.isActive && this.isDialing) {
          this.stopCallPoll();
          this.stopAppListener();
          this.isDialing = false;
          const lead = this.getCurrentLead();
          if (lead && this.onPopupCallback) {
            this.onPopupCallback(lead.lead_id, undefined);
          }
        }
      }).then(handle => {
        this._appStateHandle = handle;
      }).catch(() => { /* silent — fall back to poll timeout */ });
    }).catch(() => { /* silent */ });

    this.callPollTimer = setInterval(async () => {
      retries++;
      if (retries > CALL_LOG_POLL_RETRIES) {
        this.stopCallPoll();
        this.stopAppListener();
        // Fallback: trigger popup after timeout
        if (this.isDialing && this.onPopupCallback) {
          this.isDialing = false;
          const lead = this.getCurrentLead();
          if (lead) this.onPopupCallback(lead.lead_id, undefined);
        }
        return;
      }

      try {
        // Check call logs for the dialed number appearing after dial time
        const { value: token } = await (await import('@capacitor/preferences')).Preferences.get({ key: 'auth_token' });
        if (!token) return;
        const res = await fetch(`/api/v1/call-tracking/my-stats?range=today`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        // DC_401_POLL_STOP: On auth failure, stop poll immediately and fire popup
        // so the outcome is not lost. Avoids 401 flood in server logs.
        if (res.status === 401) {
          this.stopCallPoll();
          this.stopAppListener();
          this.isDialing = false;
          const lead = this.getCurrentLead();
          if (lead && this.onPopupCallback) {
            this.onPopupCallback(lead.lead_id, undefined);
          }
          return;
        }
        if (!res.ok) return;
        const data = await res.json() as { last_sync?: { sync_completed_at?: string } };
        // If stats show a new call after dialedAt — assume call ended
        const lastSync = data?.last_sync?.sync_completed_at;
        if (lastSync && new Date(lastSync).getTime() > dialedAt) {
          this.stopCallPoll();
          this.stopAppListener();
          this.isDialing = false;
          const lead = this.getCurrentLead();
          if (lead && this.onPopupCallback) {
            this.onPopupCallback(lead.lead_id, undefined);
          }
        }
      } catch (_) { /* silent */ }
    }, CALL_LOG_POLL_MS);
  }

  stopCallPoll(): void {
    if (this.callPollTimer) {
      clearInterval(this.callPollTimer);
      this.callPollTimer = null;
    }
  }

  stopAppListener(): void {
    if (this._appStateHandle) {
      this._appStateHandle.remove();
      this._appStateHandle = null;
    }
  }

  // ── Web Sync Polling (browser polls backend to mirror mobile dialer) ─────────

  startSyncPoll(onAttemptLogged: (attempt: Record<string, unknown>) => void): void {
    this.stopSyncPoll();
    let lastAttemptId: number | null = null;
    this.syncPollTimer = setInterval(async () => {
      try {
        const res = await apiService.get('/crm/dialer/session/current');
        const data = res.data as { session?: DialerSession; last_attempt?: { id: number } & Record<string, unknown> } | undefined;
        if (!res.success || !data?.session) return;
        const attempt = data.last_attempt;
        if (attempt && attempt.id !== lastAttemptId) {
          lastAttemptId = attempt.id;
          onAttemptLogged(attempt);
        }
      } catch (_) { /* silent */ }
    }, POLL_INTERVAL_MS);
  }

  stopSyncPoll(): void {
    if (this.syncPollTimer) {
      clearInterval(this.syncPollTimer);
      this.syncPollTimer = null;
    }
  }

  // ── Active Call Sync (web desktop mirror) ────────────────────────────────────

  async notifyCallActive(leadId: number): Promise<void> {
    try {
      await apiService.post('/crm/dialer/call/active', { lead_id: leadId });
    } catch (_) { /* non-critical — fire and forget */ }
  }

  async clearCallActive(): Promise<void> {
    try {
      await apiService.post('/crm/dialer/call/active', { lead_id: null });
    } catch (_) { /* non-critical */ }
  }

  // ── MyOperator Click-to-Call ─────────────────────────────────────────────────

  async clickToCall(customerPhone: string, leadId: number | null, sessionId?: number | null): Promise<{ success: boolean; call_id: string; agent_number: string; message?: string }> {
    const res = await apiService.post<{ success: boolean; call_id: string; agent_number: string; message?: string }>(
      '/crm/dialer/click-to-call',
      { customer_phone: customerPhone, lead_id: leadId ?? null, session_id: sessionId ?? null }
    );
    const data = res.data as { success?: boolean; call_id?: string; agent_number?: string; message?: string } | undefined;
    if (!res.success || !data?.success) {
      const detail = (res as any)?.error?.detail || data?.message || 'Click-to-Call failed. Please try again.';
      throw new Error(String(detail));
    }
    return { success: true, call_id: data.call_id ?? '', agent_number: data.agent_number ?? '', message: data.message };
  }

  startClickToCallPoll(callId: string, onEnded: () => void): void {
    this.stopClickToCallPoll();
    if (!callId) return;
    let ticks = 0;
    const MAX_TICKS = 200;
    this.ctcPollTimer = setInterval(async () => {
      ticks++;
      if (ticks > MAX_TICKS) {
        this.stopClickToCallPoll();
        onEnded();
        return;
      }
      try {
        const res = await apiService.get<{ status: string }>(`/crm/dialer/click-to-call/status/${callId}`);
        const data = res.data as { status?: string } | undefined;
        if (data?.status === 'ended' || data?.status === 'missed') {
          this.stopClickToCallPoll();
          onEnded();
        }
      } catch (_) { /* silent — non-critical poll */ }
    }, 3000);
  }

  stopClickToCallPoll(): void {
    if (this.ctcPollTimer) {
      clearInterval(this.ctcPollTimer);
      this.ctcPollTimer = null;
    }
  }

  // ── Attempt Logging ─────────────────────────────────────────────────────────

  async logAttempt(result: AttemptResult): Promise<{ success: boolean; attempt_id?: number }> {
    const res = await apiService.post<{ attempt_id?: number }>('/crm/dialer/attempt', {
      session_id: result.session_id,
      lead_id: result.lead_id,
      call_outcome: result.call_outcome,
      call_method: result.call_method ?? 'normal',
      duration_seconds: result.duration_seconds ?? 0,
      note: result.note ?? '',
      next_followup_date: result.next_followup_date ?? null,
      new_status: result.new_status ?? null,
      new_priority: result.new_priority ?? null,
      new_source: result.new_source ?? null,
      new_category_id: result.new_category_id ?? null,
      do_not_call: result.do_not_call ?? false,
      current_index: result.current_index ?? this.currentIndex,
      queue_lead_ids: result.queue_lead_ids ?? null,
      activity_type: result.activity_type ?? null,
      activity_minutes: result.activity_minutes ?? null,
      lead_update_minutes: result.lead_update_minutes ?? null,
    });
    const data = res.data as { attempt_id?: number } | undefined;
    if (res.success && data?.attempt_id) {
      this.lastAttemptId = data.attempt_id;
    }
    return { success: res.success, attempt_id: data?.attempt_id };
  }

  // ── Local State Persistence ─────────────────────────────────────────────────

  private async _saveLocalState(): Promise<void> {
    if (this.session) {
      await Preferences.set({ key: SESSION_KEY, value: JSON.stringify(this.session) });
    }
    await Preferences.set({ key: QUEUE_KEY, value: JSON.stringify(this.queue.map(q => q.lead_id)) });
    await Preferences.set({ key: INDEX_KEY, value: String(this.currentIndex) });
  }

  private async _clearLocalState(): Promise<void> {
    await Preferences.remove({ key: SESSION_KEY });
    await Preferences.remove({ key: QUEUE_KEY });
    await Preferences.remove({ key: INDEX_KEY });
  }

  async loadLocalState(): Promise<boolean> {
    try {
      const { value: sessionVal } = await Preferences.get({ key: SESSION_KEY });
      const { value: idxVal } = await Preferences.get({ key: INDEX_KEY });
      if (sessionVal) this.session = JSON.parse(sessionVal) as DialerSession;
      if (idxVal) this.currentIndex = parseInt(idxVal, 10) || 0;
      return !!sessionVal;
    } catch (_) {
      return false;
    }
  }
}

export const dialerService = new DialerService();
