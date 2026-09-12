/**
 * Mobile Softphone Page
 * DC Protocol: DC_MOBILE_SOFTPHONE_PARITY_001
 * Full Web -> Mobile functional parity with Web Softphone Center (/staff/softphone):
 * - 6 Authoritative Scopes: Dialer (Keypad + 20 Recent Calls + 6 KPIs), My Calls, New Calls, Team Calls, Contacts & Leads, Overall Calls (Leadership/Admin)
 * - Live Today's Telephony Metrics: Total Calls, Answered, Missed by Staff, Unanswered, Talk Time, Connection Rate
 * - Customer Timeline Bottom Sheet: /calls/{phone}/customer-history with CRM lead details and interaction timeline
 * - Missed Call Action Taken Bottom Sheet: /calls/{sessionId}/action-taken note recording
 * - Authoritative Contacts Contract: /telephony/my-contacts with All, Assigned Leads, Synced Contacts
 * - In-Call DTMF Keypad with direct telephonyService.sendDTMF(digit)
 * - Call Flow Studio link for Admin/Leadership users
 */

import { apiService } from '../services/api.service';
import { telephonyService } from '../services/telephony.service';
import { authService } from '../services/auth.service';
import { routerService } from '../services/router.service';
import { PageHeader } from '../components/PageHeader';

export type SoftphoneScope = 'dialer' | 'my' | 'new_calls' | 'team' | 'contacts' | 'overall';
export type ContactSourceType = 'all' | 'leads' | 'vgk' | 'mnr' | 'synced_contacts';
export type DatePreset = 'TODAY' | 'YESTERDAY' | '3DAYS' | '7DAYS' | 'CUSTOM';

interface TelephonyMetrics {
  total: number;
  answered: number;
  missed: number;
  unanswered: number;
  talkTimeFormatted: string;
  connRate: string;
}

interface CallItem {
  id: string | number;
  call_session_id?: string;
  customer_name?: string;
  customer_phone?: string;
  customer_phone_masked?: string;
  raw_caller_number?: string;
  direction?: 'inbound' | 'outbound' | string;
  computed_type?: string;
  type_label?: string;
  status?: string;
  duration_seconds?: number;
  duration_formatted?: string;
  started_at?: string;
  answered_at?: string;
  created_at?: string;
  operator_name?: string;
  operator_emp_code?: string;
  operator_id?: number;
  has_recording?: boolean;
  recording_url?: string;
  contact_source?: string;
  action_taken?: boolean;
  action_by?: string;
  action_at?: string;
  action_notes?: string;
  source?: string;
  channel?: string;
  channel_label?: string;
  lead_scope?: string;
  lead_scope_label?: string;
  is_performance_call?: boolean;
  crm_lead_id?: string | number;
  called_did?: string;
  customer_phone_display?: string;
  raw_provider_from?: string;
  normalized_provider_from?: string;
  original_caller_number?: string;
  forwarded_from_number?: string;
  forwarded_from_display?: string;
  forwarded_from_masked?: string;
  is_forwarded?: boolean;
  caller_identity_source?: string;
  caller_identity_confidence?: string;
  parent_call_identifier?: string;
}

interface CustomerContact {
  id?: string | number;
  name: string;
  phone?: string;
  masked_phone?: string;
  raw_phone?: string;
  source_type?: string;
  badge?: string;
  subtitle?: string;
  lead_id?: string | number;
}

interface TeamMember {
  id: number;
  name: string;
  emp_code: string;
  department?: string;
  designation?: string;
}

interface CustomerTimelineData {
  customer_name?: string;
  phone_masked?: string;
  raw_phone?: string;
  total_calls?: number;
  lead?: {
    name?: string;
    status?: string;
    email?: string;
    city?: string;
    phone?: string;
  };
  history?: Array<{
    id: string | number;
    type: string;
    direction?: string;
    duration_formatted?: string;
    duration_seconds?: number;
    started_at?: string;
    created_at?: string;
    operator_name?: string;
    called_did?: string;
    has_recording?: boolean;
    recording_url?: string;
    call_session_id?: string;
    status?: string;
    computed_type?: string;
    ivr_selections?: Array<{ label?: string; digit?: string; time?: string }>;
    latest_selection?: string;
  }>;
}

export class SoftphonePage {
  private container: HTMLElement;
  private dialNumber: string = '';
  private selectedContactName: string = '';
  private selectedLeadId: number | string | null = null;
  private agentStatus: 'available' | 'busy' | 'break' = 'available';
  private activeScope: SoftphoneScope = 'dialer';

  // Live Top Metrics (Today)
  private todayMetrics: TelephonyMetrics = {
    total: 0,
    answered: 0,
    missed: 0,
    unanswered: 0,
    talkTimeFormatted: '00m 00s',
    connRate: '0%'
  };
  private isLoadingMetrics: boolean = false;

  // Dialer Scope - Recent 20 Calls
  private recent20Calls: CallItem[] = [];
  private isLoadingRecent20: boolean = false;
  private recentSearchQuery: string = '';

  // Call History Scope State (my, new_calls, team, overall)
  private scopeCalls: CallItem[] = [];
  private isLoadingScopeCalls: boolean = false;
  private scopeTotalCount: number = 0;
  private scopeCurrentPage: number = 1;
  private scopePageSize: number = 25;
  private scopeFilterSearch: string = '';
  private scopeFilterType: string = '';
  private scopeFilterChannel: string = '';
  private scopeFilterLeadScope: string = '';
  private scopeFilterTeamMember: string = '';
  private scopeFilterSort: string = 'newest';
  private scopeDatePreset: DatePreset = '7DAYS';
  private customStartDate: string = '';
  private customEndDate: string = '';
  private scopeMetrics = {
    total: 0,
    answered: 0,
    missed: 0,
    unanswered: 0,
    talkTimeFormatted: '00m 00s'
  };

  // Contacts Tab State
  private contactsList: CustomerContact[] = [];
  private contactsTotal: number = 0;
  private contactsPage: number = 1;
  private contactsPageSize: number = 30;
  private contactsSourceType: ContactSourceType = 'all';
  private contactsSearchQuery: string = '';
  private isLoadingContacts: boolean = false;
  private contactsDebounceTimer: any = null;

  // Team & RBAC State
  private teamMembers: TeamMember[] = [];
  private canViewOverall: boolean = false;

  // In-App Call Engine
  private isInCall: boolean = false;
  private callStatusText: string = 'Calling...';
  private isMuted: boolean = false;
  private isSpeaker: boolean = false;
  private isHold: boolean = false;
  private showInCallDTMF: boolean = false;
  private callDuration: number = 0;
  private activeCallSessionId: string | null = null;
  private isCallConnected: boolean = false;

  // Audio Player State
  private currentAudio: HTMLAudioElement | null = null;
  private playingAudioKey: string | null = null;

  // Return route (for automatic return to CRM page after call)
  private returnUrl: string | null = null;
  private telephonyUnsub: (() => void) | null = null;

  // Bottom Sheet Drawer State
  private activeBottomSheet: 'customer_history' | 'action_taken' | 'quick_staff_verify' | null = null;
  private customerHistoryData: CustomerTimelineData | null = null;
  private customerHistoryLoading: boolean = false;
  private actionModalSessionId: string = '';
  private actionModalCustomerName: string = '';
  private actionModalPhone: string = '';
  private actionModalNotes: string = '';
  private isSubmittingAction: boolean = false;

  // Quick Staff Verification State (Option A: Direct WhatsApp Call Link)
  private quickStaffLeadPreview: any = null;
  private quickStaffEmpCode: string = '';
  private quickStaffPersistence: 'always' | 'one_time' = 'always';
  private quickStaffError: string = '';
  private isVerifyingStaff: boolean = false;
  private pendingAutoDialAfterVerify: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(params?: any): Promise<void> {
    let shouldAutoStart = false;
    let autoDialNum = '';
    let autoDialName = '';

    const hash = window.location.hash || '';
    const queryIndex = hash.indexOf('?');
    const hashParams = queryIndex !== -1 ? new URLSearchParams(hash.substring(queryIndex)) : new URLSearchParams();
    const searchParams = (typeof window !== 'undefined' && window.location.search) ? new URLSearchParams(window.location.search) : new URLSearchParams();

    const dial = params?.dial || hashParams.get('dial') || searchParams.get('dial');
    const name = params?.name || hashParams.get('name') || searchParams.get('name');
    const leadId = params?.lead_id || params?.leadId || hashParams.get('lead_id') || hashParams.get('leadId') || searchParams.get('lead_id') || searchParams.get('leadId');
    const returnParam = params?.return || hashParams.get('return') || searchParams.get('return');
    const scopeParam = (params?.scope || hashParams.get('scope') || searchParams.get('scope')) as SoftphoneScope;
    const autoStart = params?.auto_dial === '1' || params?.auto_dial === 'true' || params?.auto_start === 'true' || params?.autostart === 'true' ||
      hashParams.get('auto_dial') === '1' || hashParams.get('auto_dial') === 'true' || hashParams.get('auto_start') === 'true' || hashParams.get('autostart') === 'true' ||
      searchParams.get('auto_dial') === '1' || searchParams.get('auto_dial') === 'true' || searchParams.get('auto_start') === 'true' || searchParams.get('autostart') === 'true';

    if (returnParam) this.returnUrl = returnParam;
    if (scopeParam) this.activeScope = scopeParam;
    if (leadId) this.selectedLeadId = leadId;

    const isAuth = authService.getAuthState().isLoggedIn;

    if (dial) {
      this.dialNumber = dial;
      autoDialNum = dial;
      if (name) {
        this.selectedContactName = name;
        autoDialName = name;
      }
      this.activeScope = 'dialer';
      if (autoStart) shouldAutoStart = true;
    }

    // If authenticated and leadId is provided without dial number, fetch verified lead detail
    if (leadId && !dial && isAuth) {
      try {
        const res = await apiService.get<any>(`/telephony/plivo/lead-call-detail/${leadId}`);
        const payload = res?.data || res;
        if (payload && (payload.success || payload.lead)) {
          const leadData = payload.lead || payload;
          const targetPhone = leadData.phone || '';
          const targetName = leadData.name || 'Contact Lead';
          const cleanDigits = String(targetPhone).replace(/\D/g, '').slice(-10);
          if (cleanDigits) {
            this.dialNumber = cleanDigits;
            this.selectedContactName = targetName;
            autoDialNum = cleanDigits;
            autoDialName = targetName;
            this.activeScope = 'dialer';
            if (autoStart) shouldAutoStart = true;
          }
        }
      } catch (err) {
        console.warn('[SoftphonePage] Could not load lead call details:', err);
      }
    }

    this.render();

    // If not authenticated and leadId is present: trigger Quick Staff Verification
    if (!isAuth && leadId) {
      this.openQuickStaffVerificationSheet(leadId, autoStart);
    }

    // Initial background data loads (authenticated staff only)
    if (isAuth) {
      this.loadTodayMetrics();
      if (this.activeScope === 'dialer') {
        this.loadRecent20Calls();
      } else if (this.activeScope === 'contacts') {
        this.loadContacts(1);
      } else {
        this.loadScopeCalls(1);
        if (this.activeScope === 'team' || this.activeScope === 'overall') {
          this.loadTeamMembers();
        }
      }

      await telephonyService.initPlivoWebRTC();
    }

    // Subscribe to telephony service
    if (!this.telephonyUnsub) {
      this.telephonyUnsub = telephonyService.subscribe((session) => {
        this.handleTelephonyStateChange(session);
      });
    }

    if (shouldAutoStart && autoDialNum && isAuth) {
      setTimeout(() => {
        this.startCall(autoDialNum, autoDialName);
      }, 400);
    }
  }

  private handleTelephonyStateChange(session: any): void {
    const wasInCall = this.isInCall;
    this.isInCall = session.state !== 'idle' && session.state !== 'ended' && session.state !== 'failed';
    this.isCallConnected = session.state === 'connected';
    this.callDuration = session.durationSeconds;
    this.isMuted = session.isMuted;
    this.isSpeaker = session.isSpeaker;
    this.isHold = session.isHeld;
    this.activeCallSessionId = session.sessionId;

    if (session.state === 'ringing' && session.isIncoming) {
      this.selectedContactName = session.contactName || 'Incoming Inquiry';
      this.dialNumber = session.destinationPhone || '';
      this.callStatusText = 'Incoming Call...';
    } else if (session.state === 'connecting') {
      this.callStatusText = 'Connecting...';
    } else if (session.state === 'ringing') {
      this.callStatusText = 'Ringing...';
    } else if (session.state === 'connected') {
      this.callStatusText = 'Connected / In Call';
    } else if (session.state === 'ended') {
      this.callStatusText = 'Call ended';
      this.showInCallDTMF = false;
      // Immediate refresh for UI responsiveness
      this.loadTodayMetrics();
      if (this.activeScope === 'dialer') this.loadRecent20Calls();
      else if (this.activeScope !== 'contacts') this.loadScopeCalls(this.scopeCurrentPage);

      // HISTORY/RECORDING RECONCILIATION ONLY: Non-authoritative fallback to fetch eventual recording URL and carrier duration
      setTimeout(() => {
        this.loadTodayMetrics();
        if (this.activeScope === 'dialer') this.loadRecent20Calls();
        else if (this.activeScope !== 'contacts') this.loadScopeCalls(this.scopeCurrentPage);
      }, 1800);
    } else if (session.state === 'failed') {
      this.callStatusText = session.errorMessage || 'Call failed';
      this.showInCallDTMF = false;
    }

    if (this.isInCall !== wasInCall || session.state === 'ended' || session.state === 'failed') {
      this.render();
    } else if (this.isInCall) {
      const timerEl = document.getElementById('softphoneCallTimer');
      if (timerEl && this.isCallConnected) {
        const mins = Math.floor(this.callDuration / 60).toString().padStart(2, '0');
        const secs = (this.callDuration % 60).toString().padStart(2, '0');
        timerEl.textContent = `${mins}:${secs}`;
      }
      const statusEl = document.getElementById('softphoneCallStatusText');
      if (statusEl) {
        statusEl.textContent = this.callStatusText;
        statusEl.style.color = this.isCallConnected ? '#22c55e' : '#38bdf8';
      }
    }
  }

  public cleanup(): void {
    if (this.telephonyUnsub) {
      this.telephonyUnsub();
      this.telephonyUnsub = null;
    }
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio = null;
    }
    if (this.contactsDebounceTimer) {
      clearTimeout(this.contactsDebounceTimer);
      this.contactsDebounceTimer = null;
    }
  }

  // ──────────────────────────── RBAC & USER UTILS ────────────────────────────

  private getCurrentUser(): any {
    try {
      const fromAuth = authService.getAuthState()?.user;
      if (fromAuth) return fromAuth;
      const staffUser = localStorage.getItem('staff_user') || sessionStorage.getItem('staff_user');
      if (staffUser) return JSON.parse(staffUser);
      const mnrState = localStorage.getItem('mnr_auth_state');
      if (mnrState) {
        const parsed = JSON.parse(mnrState);
        if (parsed.user) return parsed.user;
      }
    } catch (e) {}
    return {};
  }

  private isLeadershipUser(): boolean {
    const user = this.getCurrentUser();
    const empCode = (user.emp_code || '').toUpperCase();
    const roleCode = (user.role?.role_code || user.role_code || '').toLowerCase();
    const staffType = (user.staff_type || '').toUpperCase();
    const isSupreme = Boolean(user.is_supreme);
    return isSupreme ||
      ['vgk4u', 'vgk4u_supreme', 'key_leadership', 'ea', 'executive_admin', 'super_admin', 'admin', 'director'].includes(roleCode) ||
      ['VGK4U', 'VGK4U_SUPREME', 'KEY_LEADERSHIP', 'EA', 'DIRECTOR'].includes(staffType) ||
      ['MR10001', 'MR10018', 'MR10016', 'MR10025'].includes(empCode) ||
      Boolean(this.canViewOverall);
  }

  // ──────────────────────────── TIME & DATE UTILS ────────────────────────────

  private getISTDateString(d: Date = new Date()): string {
    return d.toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });
  }

  private parseISTDate(dateStr?: string): Date | null {
    if (!dateStr) return null;
    let str = String(dateStr).trim();
    if (!str) return null;
    if (!str.includes('+') && !str.endsWith('Z') && !str.endsWith('z')) {
      str = str + '+05:30';
    }
    const d = new Date(str);
    return isNaN(d.getTime()) ? null : d;
  }

  private formatRelativeTime(dateStr?: string): string {
    if (!dateStr) return 'Recent';
    try {
      const d = this.parseISTDate(dateStr);
      if (!d) return dateStr;
      const now = new Date();
      const dDateStr = d.toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });
      const nowDateStr = now.toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });
      const timeStr = d.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: true });

      if (dDateStr === nowDateStr) return `Today, ${timeStr}`;

      const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000);
      const yestDateStr = yesterday.toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });
      if (dDateStr === yestDateStr) return `Yesterday, ${timeStr}`;

      return d.toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short' }) + `, ${timeStr}`;
    } catch {
      return dateStr;
    }
  }

  private formatDuration(seconds: number): string {
    if (!seconds || seconds <= 0) return '00m 00s';
    const mins = Math.floor(seconds / 60);
    const rem = seconds % 60;
    return `${mins}m ${rem.toString().padStart(2, '0')}s`;
  }

  private maskPhone(p?: string): string {
    if (!p || p === '—' || p === '-' || p === 'null') return '—';
    const s = String(p).trim();
    if (s.includes('@g.us') || s.includes('@broadcast') || s.includes('@lid')) return s;
    const digits = s.replace(/\D/g, '');
    if (digits.length < 6) return s;
    const clean10 = digits.slice(-10);
    return `+91 ${clean10.slice(0, 2)}••••${clean10.slice(-4)}`;
  }

  private escapeAttr(str: string): string {
    return (str || '').replace(/"/g, '&quot;');
  }

  private escapeHtml(str: string): string {
    return (str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  private getDateRangeForPreset(preset: DatePreset): { start_date: string; end_date: string } {
    const now = new Date();
    const todayStr = this.getISTDateString(now);
    if (preset === 'TODAY') {
      return { start_date: todayStr, end_date: todayStr };
    }
    if (preset === 'YESTERDAY') {
      const yest = new Date(Date.now() - 24 * 60 * 60 * 1000);
      const yestStr = this.getISTDateString(yest);
      return { start_date: yestStr, end_date: yestStr };
    }
    if (preset === '3DAYS') {
      const past = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000);
      return { start_date: this.getISTDateString(past), end_date: todayStr };
    }
    if (preset === '7DAYS') {
      const past = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
      return { start_date: this.getISTDateString(past), end_date: todayStr };
    }
    if (preset === 'CUSTOM' && this.customStartDate) {
      return {
        start_date: this.customStartDate,
        end_date: this.customEndDate || todayStr
      };
    }
    return { start_date: todayStr, end_date: todayStr };
  }

  // ──────────────────────────── DATA FETCHERS ────────────────────────────

  private async loadTodayMetrics(): Promise<void> {
    this.isLoadingMetrics = true;
    try {
      const todayStr = this.getISTDateString();
      const res = await apiService.get<any>(`/telephony/incoming-calls?scope=my&start_date=${todayStr}&end_date=${todayStr}&page=1&page_size=100`);
      const data = (res && res.data) ? res.data : res;
      if (data && data.items) {
        const items = data.items || [];
        const totalToday = data.total_count || items.length;
        const answeredToday = items.filter((c: any) => c.computed_type === 'inbound_answered' || c.computed_type === 'outbound_answered').length;
        const missedToday = items.filter((c: any) => c.computed_type === 'missed_by_staff').length;
        const unansToday = items.filter((c: any) => c.computed_type === 'outbound_unanswered').length;
        const totalSec = items.filter((c: any) => c.computed_type === 'inbound_answered' || c.computed_type === 'outbound_answered')
                              .reduce((acc: number, c: any) => acc + (c.duration_seconds || 0), 0);
        const connRate = totalToday > 0 ? `${Math.round((answeredToday / totalToday) * 100)}%` : '0%';

        this.todayMetrics = {
          total: totalToday,
          answered: answeredToday,
          missed: missedToday,
          unanswered: unansToday,
          talkTimeFormatted: `${Math.floor(totalSec / 60)}m ${(totalSec % 60).toString().padStart(2, '0')}s`,
          connRate: connRate
        };

        if (data.current_user_can_view_overall) {
          this.canViewOverall = true;
        }
      }
    } catch (err) {
      console.warn('[SoftphonePage] Error loading today metrics:', err);
    } finally {
      this.isLoadingMetrics = false;
      this.updateMetricsDisplay();
    }
  }

  private async loadRecent20Calls(): Promise<void> {
    this.isLoadingRecent20 = true;
    this.renderRecent20List();

    try {
      const res = await apiService.get<any>(`/telephony/incoming-calls?scope=my&page=1&page_size=20&sort_by=newest`);
      const data = (res && res.data) ? res.data : res;
      const items = (data && Array.isArray(data.items)) ? data.items : ((data && Array.isArray(data.data)) ? data.data : (Array.isArray(data) ? data : []));
      this.recent20Calls = items;
      if (data && data.current_user_can_view_overall) {
        this.canViewOverall = true;
      }
    } catch (err) {
      console.warn('[SoftphonePage] Error loading recent 20 calls:', err);
      this.recent20Calls = [];
    } finally {
      this.isLoadingRecent20 = false;
      this.renderRecent20List();
    }
  }

  private async loadScopeCalls(page: number = 1): Promise<void> {
    this.scopeCurrentPage = page;
    this.isLoadingScopeCalls = true;
    this.renderScopeCallsList();

    try {
      const dateRange = this.getDateRangeForPreset(this.scopeDatePreset);
      let url = `/telephony/incoming-calls?scope=${this.activeScope}&page=${page}&page_size=${this.scopePageSize}&sort_by=${this.scopeFilterSort}`;
      if (this.scopeFilterSearch) url += `&search=${encodeURIComponent(this.scopeFilterSearch)}`;
      if (this.scopeFilterType) url += `&call_type=${encodeURIComponent(this.scopeFilterType)}`;
      if (this.scopeFilterChannel) url += `&channel=${encodeURIComponent(this.scopeFilterChannel)}`;
      if (this.scopeFilterLeadScope) url += `&lead_scope=${encodeURIComponent(this.scopeFilterLeadScope)}`;
      if (this.scopeFilterTeamMember && (this.activeScope === 'team' || this.activeScope === 'overall')) {
        url += `&staff_id=${encodeURIComponent(this.scopeFilterTeamMember)}`;
      }
      if (dateRange.start_date) url += `&start_date=${encodeURIComponent(dateRange.start_date)}`;
      if (dateRange.end_date) url += `&end_date=${encodeURIComponent(dateRange.end_date)}`;

      const res = await apiService.get<any>(url);
      const data = (res && res.data) ? res.data : res;
      if (data) {
        this.scopeCalls = data.items || [];
        this.scopeTotalCount = data.total_count || this.scopeCalls.length;
        if (data.current_user_can_view_overall) {
          this.canViewOverall = true;
        }
        const answered = this.scopeCalls.filter(c => c.computed_type === 'inbound_answered' || c.computed_type === 'outbound_answered').length;
        const missed = this.scopeCalls.filter(c => c.computed_type === 'missed_by_staff').length;
        const unans = this.scopeCalls.filter(c => c.computed_type === 'outbound_unanswered').length;
        const totalSec = this.scopeCalls.reduce((acc, c) => acc + (c.duration_seconds || 0), 0);
        this.scopeMetrics = {
          total: this.scopeTotalCount,
          answered,
          missed,
          unanswered: unans,
          talkTimeFormatted: `${Math.floor(totalSec / 60)}m ${(totalSec % 60).toString().padStart(2, '0')}s`
        };
      }
    } catch (err) {
      console.warn('[SoftphonePage] Error loading scope calls:', err);
      this.scopeCalls = [];
    } finally {
      this.isLoadingScopeCalls = false;
      this.renderScopeCallsList();
    }
  }

  private async loadContacts(page: number = 1): Promise<void> {
    this.contactsPage = page;
    this.isLoadingContacts = true;
    this.renderContactsList();

    try {
      let url = `/telephony/my-contacts?page=${page}&page_size=${this.contactsPageSize}&source_type=${this.contactsSourceType}`;
      if (this.contactsSearchQuery) {
        url += `&q=${encodeURIComponent(this.contactsSearchQuery)}`;
      }
      const res = await apiService.get<any>(url);
      const data = (res && res.data) ? res.data : res;
      if (data) {
        this.contactsList = data.contacts || [];
        this.contactsTotal = data.total || this.contactsList.length;
      }
    } catch (err) {
      console.warn('[SoftphonePage] Error loading contacts:', err);
      this.contactsList = [];
    } finally {
      this.isLoadingContacts = false;
      this.renderContactsList();
    }
  }

  private async loadTeamMembers(): Promise<void> {
    try {
      const res = await apiService.get<any>('/telephony/team-members');
      const data = (res && res.data) ? res.data : res;
      if (data && data.team_members) {
        this.teamMembers = data.team_members;
        const select = document.getElementById('scopeTeamSelect') as HTMLSelectElement;
        if (select) {
          select.innerHTML = `<option value="">All Team Members (${this.teamMembers.length})</option>` +
            this.teamMembers.map(m => `<option value="${m.id}" ${this.scopeFilterTeamMember === String(m.id) ? 'selected' : ''}>${this.escapeHtml(m.name)} (${m.emp_code})</option>`).join('');
        }
      }
    } catch (err) {
      console.warn('[SoftphonePage] Error loading team members:', err);
    }
  }

  // ──────────────────────────── DIALER & CALL ACTIONS ────────────────────────────

  private pressKey(digit: string): void {
    if (this.dialNumber.length < 15) {
      this.dialNumber += digit;
      this.selectedContactName = '';
      this.updateDialDisplay();
    }
  }

  private backspace(): void {
    if (this.dialNumber.length > 0) {
      this.dialNumber = this.dialNumber.slice(0, -1);
      this.selectedContactName = '';
      this.updateDialDisplay();
    }
  }

  private clearNumber(): void {
    this.dialNumber = '';
    this.selectedContactName = '';
    this.updateDialDisplay();
  }

  private updateDialDisplay(): void {
    const input = document.getElementById('softphoneDialInput') as HTMLInputElement;
    if (input) {
      input.value = this.dialNumber;
    }
    const nameLabel = document.getElementById('softphoneMatchedNameLabel');
    if (nameLabel) {
      if (this.selectedContactName) {
        nameLabel.textContent = `👤 ${this.selectedContactName}`;
        nameLabel.style.display = 'block';
      } else {
        nameLabel.style.display = 'none';
      }
    }
    const clearBtn = document.getElementById('softphoneClearBtn');
    if (clearBtn) {
      clearBtn.style.visibility = this.dialNumber ? 'visible' : 'hidden';
    }
    const clearAllBtn = document.getElementById('softphoneClearAllBtn');
    if (clearAllBtn) {
      clearAllBtn.style.display = this.dialNumber ? 'inline-block' : 'none';
    }
  }

  private async startCall(
    numberToDial?: string,
    contactName?: string,
    isDirectSim: boolean = false,
    leadId?: number | string | null
  ): Promise<void> {
    // MANDATE 1: TRUE USER-GESTURE AUDIO UNLOCK BEFORE ANY ASYNC OPERATION
    telephonyService.prepareAudioOnUserGesture();

    const target = (numberToDial || this.dialNumber || '').trim();
    if (!target || target.replace(/[^0-9]/g, '').length < 3) {
      alert('Please enter a valid phone number');
      return;
    }

    const cleanNumber = target.startsWith('+') ? target : `+91${target.replace(/\D/g, '').slice(-10)}`;
    this.dialNumber = target;
    if (contactName) this.selectedContactName = contactName;
    if (leadId !== undefined && leadId !== null) this.selectedLeadId = leadId;

    if (isDirectSim) {
      telephonyService.triggerDirectSimCall(cleanNumber);
      return;
    }

    const effectiveLeadId = this.selectedLeadId ?? null;
    const res = await telephonyService.startCall(cleanNumber, this.selectedContactName, effectiveLeadId);
    if (!res.success) {
      alert(res.error || 'Failed to place call');
      this.isInCall = false;
      this.render();
      return;
    }
  }

  private endCall(): void {
    this.isInCall = false;
    this.isCallConnected = false;
    this.showInCallDTMF = false;
    telephonyService.endCall();

    if (this.returnUrl) {
      const dest = this.returnUrl;
      this.returnUrl = null;
      setTimeout(() => {
        window.location.hash = dest.startsWith('#') ? dest : `#${dest}`;
      }, 600);
      return;
    }

    this.render();
  }

  private toggleMute(): void {
    this.isMuted = telephonyService.toggleMute();
    this.render();
  }

  private async toggleSpeaker(): Promise<void> {
    this.isSpeaker = await telephonyService.toggleSpeaker();
    this.render();
  }

  private toggleHold(): void {
    this.isHold = telephonyService.toggleHold();
    this.render();
  }

  private sendInCallDTMF(digit: string): void {
    telephonyService.sendDTMF(digit);
  }

  // ──────────────────────────── AUDIO PLAYER ────────────────────────────

  private toggleAudioPlayback(key: string, rawUrl: string): void {
    if (this.playingAudioKey === key && this.currentAudio) {
      if (!this.currentAudio.paused) {
        this.currentAudio.pause();
        this.playingAudioKey = null;
        this.updateAudioIcons();
        return;
      }
    }

    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio = null;
    }

    // Ensure in-communication mode is reset to media loudspeaker (Issue #5)
    try {
      const cap = (window as any).Capacitor;
      if (cap?.Plugins?.AudioRouting?.resetAudioMode) {
        cap.Plugins.AudioRouting.resetAudioMode().catch(() => {});
      }
    } catch (_) {}

    const token = localStorage.getItem('auth_token') || localStorage.getItem('staff_token') || localStorage.getItem('token') || '';
    const fullUrl = rawUrl.startsWith('http') ? rawUrl : `${window.location.origin}${rawUrl}`;
    const audioUrl = fullUrl.includes('?') ? `${fullUrl}&token=${token}` : `${fullUrl}?token=${token}`;

    this.currentAudio = new Audio(audioUrl);
    this.playingAudioKey = key;
    this.updateAudioIcons();

    this.currentAudio.play().then(() => {
      this.updateAudioIcons();
    }).catch(err => {
      console.warn('[SoftphonePage] Audio playback error:', err);
      alert('Unable to play recording. Stream unavailable or expired.');
      this.playingAudioKey = null;
      this.updateAudioIcons();
    });

    this.currentAudio.onended = () => {
      this.playingAudioKey = null;
      this.updateAudioIcons();
    };

    this.currentAudio.onerror = () => {
      this.playingAudioKey = null;
      this.updateAudioIcons();
    };
  }

  private updateAudioIcons(): void {
    document.querySelectorAll('.audio-play-trigger-btn').forEach(btn => {
      const key = btn.getAttribute('data-audio-key');
      const icon = btn.querySelector('i');
      if (icon) {
        if (key === this.playingAudioKey) {
          icon.className = 'fas fa-pause';
          (btn as HTMLElement).style.background = '#eab308';
          (btn as HTMLElement).style.color = '#000';
        } else {
          icon.className = 'fas fa-play';
          (btn as HTMLElement).style.background = 'rgba(56, 189, 248, 0.15)';
          (btn as HTMLElement).style.color = '#38bdf8';
        }
      }
    });
  }

  // ──────────────────────────── BOTTOM SHEETS ────────────────────────────

  private async openCustomerHistory(rawPhone: string, customerName: string = 'Guest Customer'): Promise<void> {
    const clean = (rawPhone || '').replace(/\D/g, '').slice(-10);
    if (!clean) return;

    this.customerHistoryLoading = true;
    this.customerHistoryData = null;
    this.activeBottomSheet = 'customer_history';
    this.renderBottomSheet();

    try {
      const res = await apiService.get<any>(`/telephony/calls/${clean}/customer-history`);
      const data = (res && res.data) ? res.data : res;
      this.customerHistoryData = data;
    } catch (err: any) {
      console.warn('[SoftphonePage] Error fetching customer timeline:', err);
    } finally {
      this.customerHistoryLoading = false;
      this.renderBottomSheet();
    }
  }

  private openActionTakenModal(sessionId: string, rawPhone: string, customerName: string = 'Customer'): void {
    this.actionModalSessionId = sessionId;
    this.actionModalPhone = (rawPhone || '').replace(/\D/g, '').slice(-10);
    this.actionModalCustomerName = customerName;
    this.actionModalNotes = '';
    this.activeBottomSheet = 'action_taken';
    this.renderBottomSheet();
  }

  private async submitActionTaken(): Promise<void> {
    if (!this.actionModalNotes.trim()) {
      alert('Please enter a brief resolution note for this missed call.');
      return;
    }
    this.isSubmittingAction = true;
    try {
      await apiService.post<any>(`/telephony/calls/${this.actionModalSessionId}/action-taken`, {
        notes: this.actionModalNotes.trim()
      });

      // Update calls list item state locally
      const foundScopeCall = this.scopeCalls.find(c => c.call_session_id === this.actionModalSessionId);
      if (foundScopeCall) {
        foundScopeCall.action_taken = true;
        foundScopeCall.action_notes = this.actionModalNotes.trim();
      }
      const foundRecent = this.recent20Calls.find(c => c.call_session_id === this.actionModalSessionId);
      if (foundRecent) {
        foundRecent.action_taken = true;
        foundRecent.action_notes = this.actionModalNotes.trim();
      }

      this.closeBottomSheet();
      if (this.activeScope === 'dialer') {
        this.renderRecent20List();
      } else {
        this.renderScopeCallsList();
      }
    } catch (err: any) {
      alert(`Failed to save action: ${err?.message || err}`);
    } finally {
      this.isSubmittingAction = false;
    }
  }

  private closeBottomSheet(): void {
    const wasQuickStaff = this.activeBottomSheet === 'quick_staff_verify';
    this.activeBottomSheet = null;
    this.customerHistoryData = null;
    this.quickStaffLeadPreview = null;
    this.renderBottomSheet();

    if (wasQuickStaff && !authService.getAuthState().isLoggedIn) {
      routerService.navigate('dashboard');
    }
  }

  // ──────────────────────────── MAIN RENDER ────────────────────────────

  private render(): void {
    const isLeadership = this.isLeadershipUser();

    this.container.innerHTML = `
      <div class="page-container softphone-page" style="padding-bottom: 90px; min-height: 100vh; background: #0f172a; color: #fff; position: relative;">
        ${PageHeader.render({ title: 'Softphone Center', showMenu: true, showBack: false })}

        <!-- Top Controls Bar: Status, Call Flow Studio (Leadership), Refresh -->
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(255,255,255,0.08); gap: 8px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <select id="softphoneStatusSelect" style="background: #1e293b; color: ${this.agentStatus === 'available' ? '#22c55e' : this.agentStatus === 'busy' ? '#ef4444' : '#eab308'}; border: 1px solid rgba(255,255,255,0.15); border-radius: 12px; padding: 4px 8px; font-size: 11.5px; font-weight: 700; outline: none; cursor: pointer;">
              <option value="available" ${this.agentStatus === 'available' ? 'selected' : ''}>🟢 Available</option>
              <option value="busy" ${this.agentStatus === 'busy' ? 'selected' : ''}>🔴 Busy</option>
              <option value="break" ${this.agentStatus === 'break' ? 'selected' : ''}>🟡 Break</option>
            </select>
            <span class="badge" style="background: rgba(34, 197, 94, 0.15); color: #22c55e; border: 1px solid rgba(34, 197, 94, 0.3); font-size: 11px; padding: 4px 8px; border-radius: 10px;">
              <i class="fas fa-circle-check" style="margin-right: 4px;"></i>Online
            </span>
          </div>

          <div style="display: flex; align-items: center; gap: 6px;">
            ${isLeadership ? `
              <a href="/staff/call-flow-studio" target="_blank" style="text-decoration: none; padding: 5px 9px; border-radius: 10px; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.3); color: #38bdf8; font-size: 11px; font-weight: 700; display: inline-flex; align-items: center; gap: 5px;">
                <i class="fas fa-diagram-project"></i> Studio
              </a>
            ` : ''}
            <button id="softphoneRefreshBtn" title="Refresh" style="width: 30px; height: 30px; border-radius: 50%; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); color: #94a3b8; cursor: pointer; display: inline-flex; align-items: center; justify-content: center;">
              <i class="fas fa-rotate"></i>
            </button>
          </div>
        </div>

        <!-- 6-Scope Horizontal Navigation Bar (Touch-Optimized, Horizontal Scroll) -->
        <div style="background: #111827; border-bottom: 1px solid rgba(255,255,255,0.08); padding: 8px 12px; overflow-x: auto; white-space: nowrap; -webkit-overflow-scrolling: touch; scrollbar-width: none;">
          <div style="display: inline-flex; gap: 6px;">
            <button class="scope-nav-btn" data-scope="dialer" style="padding: 6px 12px; border-radius: 18px; font-size: 12px; font-weight: 700; border: none; cursor: pointer; transition: all 0.15s; background: ${this.activeScope === 'dialer' ? '#3b82f6' : 'rgba(255,255,255,0.06)'}; color: ${this.activeScope === 'dialer' ? '#fff' : '#94a3b8'};">
              <i class="fas fa-keyboard" style="margin-right: 5px;"></i>Dialer
            </button>
            <button class="scope-nav-btn" data-scope="my" style="padding: 6px 12px; border-radius: 18px; font-size: 12px; font-weight: 700; border: none; cursor: pointer; transition: all 0.15s; background: ${this.activeScope === 'my' ? '#3b82f6' : 'rgba(255,255,255,0.06)'}; color: ${this.activeScope === 'my' ? '#fff' : '#94a3b8'};">
              <i class="fas fa-user" style="margin-right: 5px;"></i>My Calls
            </button>
            <button class="scope-nav-btn" data-scope="new_calls" style="padding: 6px 12px; border-radius: 18px; font-size: 12px; font-weight: 700; border: none; cursor: pointer; transition: all 0.15s; background: ${this.activeScope === 'new_calls' ? '#3b82f6' : 'rgba(255,255,255,0.06)'}; color: ${this.activeScope === 'new_calls' ? '#fff' : '#94a3b8'};">
              <i class="fas fa-sparkles" style="color: #f59e0b; margin-right: 5px;"></i>New Calls
            </button>
            <button class="scope-nav-btn" data-scope="team" style="padding: 6px 12px; border-radius: 18px; font-size: 12px; font-weight: 700; border: none; cursor: pointer; transition: all 0.15s; background: ${this.activeScope === 'team' ? '#3b82f6' : 'rgba(255,255,255,0.06)'}; color: ${this.activeScope === 'team' ? '#fff' : '#94a3b8'};">
              <i class="fas fa-users" style="margin-right: 5px;"></i>Team Calls
            </button>
            <button class="scope-nav-btn" data-scope="contacts" style="padding: 6px 12px; border-radius: 18px; font-size: 12px; font-weight: 700; border: none; cursor: pointer; transition: all 0.15s; background: ${this.activeScope === 'contacts' ? '#3b82f6' : 'rgba(255,255,255,0.06)'}; color: ${this.activeScope === 'contacts' ? '#fff' : '#94a3b8'};">
              <i class="fas fa-address-book" style="color: #38bdf8; margin-right: 5px;"></i>Contacts & Leads
            </button>
            ${isLeadership ? `
              <button class="scope-nav-btn" data-scope="overall" style="padding: 6px 12px; border-radius: 18px; font-size: 12px; font-weight: 700; border: none; cursor: pointer; transition: all 0.15s; background: ${this.activeScope === 'overall' ? '#f59e0b' : 'rgba(245, 158, 11, 0.15)'}; color: ${this.activeScope === 'overall' ? '#000' : '#f59e0b'};">
                <i class="fas fa-shield-halved" style="margin-right: 5px;"></i>Overall Calls
              </button>
            ` : ''}
          </div>
        </div>

        <!-- Scope Content -->
        ${this.isInCall ? this.renderInCallScreen() : this.renderScopeBody()}

        <!-- Bottom Sheet Container (Customer Timeline & Action Taken) -->
        <div id="softphoneBottomSheetContainer"></div>
      </div>
    `;

    this.attachListeners();
    this.renderBottomSheet();
  }

  private renderScopeBody(): string {
    if (this.activeScope === 'dialer') {
      return this.renderDialerView();
    }
    if (this.activeScope === 'contacts') {
      return this.renderContactsView();
    }
    return this.renderHistoryScopeView();
  }

  // ──────────────────────────── 1. DIALER VIEW ────────────────────────────

  private renderDialerView(): string {
    return `
      <div style="max-width: 480px; margin: 0 auto; padding: 14px 16px;">
        
        <!-- Interactive Keypad Box -->
        <div style="background: #1e293b; border-radius: 16px; padding: 14px 16px; margin-bottom: 16px; border: 1px solid rgba(255,255,255,0.08); box-shadow: 0 4px 16px rgba(0,0,0,0.3);">
          
          <div id="softphoneMatchedNameLabel" style="display: ${this.selectedContactName ? 'block' : 'none'}; font-size: 12px; font-weight: 700; color: #38bdf8; margin-bottom: 4px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">
            👤 ${this.selectedContactName}
          </div>

          <!-- Dial Input & Clear Buttons -->
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;">
            <input 
              type="tel" 
              inputmode="tel"
              id="softphoneDialInput" 
              value="${this.dialNumber}" 
              placeholder="Enter phone number..." 
              style="background: transparent; border: none; outline: none; color: #fff; font-size: 22px; font-weight: 700; width: 100%; letter-spacing: 0.5px;"
            />
            <div style="display: flex; align-items: center; gap: 8px;">
              <button id="softphoneClearAllBtn" title="Clear all" style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; font-size: 10.5px; font-weight: 700; border-radius: 10px; padding: 3px 7px; cursor: pointer; display: ${this.dialNumber ? 'inline-block' : 'none'};">
                Clear
              </button>
              <button id="softphoneClearBtn" title="Backspace" style="background: transparent; border: none; color: #94a3b8; font-size: 20px; cursor: pointer; visibility: ${this.dialNumber ? 'visible' : 'hidden'}; padding: 4px; display: flex; align-items: center; user-select: none;">
                <i class="fas fa-delete-left"></i>
              </button>
            </div>
          </div>

          <!-- 3x4 Dialpad Grid -->
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 14px;">
            ${this.renderKey('1', '&nbsp;')}
            ${this.renderKey('2', 'ABC')}
            ${this.renderKey('3', 'DEF')}

            ${this.renderKey('4', 'GHI')}
            ${this.renderKey('5', 'JKL')}
            ${this.renderKey('6', 'MNO')}

            ${this.renderKey('7', 'PQRS')}
            ${this.renderKey('8', 'TUV')}
            ${this.renderKey('9', 'WXYZ')}

            ${this.renderKey('*', '&nbsp;')}
            ${this.renderKey('0', '+')}
            ${this.renderKey('#', '&nbsp;')}
          </div>

          <!-- Dual Call Actions -->
          <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
            <button id="softphoneStartCallBtn" title="Call via Cloud Softphone" style="width: 62px; height: 62px; border-radius: 50%; background: linear-gradient(135deg, #22c55e, #16a34a); border: none; color: #fff; font-size: 24px; display: flex; align-items: center; justify-content: center; box-shadow: 0 8px 24px rgba(34, 197, 94, 0.4); cursor: pointer;">
              <i class="fas fa-phone"></i>
            </button>

            <button id="softphoneDirectSimBtn" style="padding: 5px 12px; border-radius: 16px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); color: #38bdf8; font-size: 11px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 5px;">
              <i class="fas fa-mobile-screen"></i> Direct SIM Call
            </button>
          </div>
        </div>

        <!-- Today's 6 Live KPI Metrics Chips -->
        <div style="margin-bottom: 18px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-size: 12px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">
              <i class="fas fa-chart-pie" style="margin-right: 4px; color: #38bdf8;"></i> Today's Performance
            </span>
            <span style="font-size: 10.5px; color: #64748b;">Asia/Kolkata</span>
          </div>

          <div id="softphoneTodayMetricsGrid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">
            ${this.renderMetricsCardsHtml(this.todayMetrics)}
          </div>
        </div>

        <!-- Last 20 Recent Calls Section -->
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <div style="display: flex; align-items: center; gap: 6px;">
              <span style="font-size: 13px; font-weight: 700; color: #fff;">
                <i class="fas fa-clock-rotate-left" style="color: #60a5fa; margin-right: 4px;"></i> Recent 20 Calls
              </span>
              <span id="recent20CountBadge" class="badge" style="background: rgba(59, 130, 246, 0.2); color: #60a5fa; font-size: 10px; padding: 2px 6px; border-radius: 10px;">
                ${this.recent20Calls.length}
              </span>
            </div>
          </div>

          <!-- Quick Search Filter for Recent Calls -->
          <div style="background: #1e293b; border-radius: 10px; padding: 8px 12px; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; border: 1px solid rgba(255,255,255,0.08);">
            <i class="fas fa-search" style="color: #64748b; font-size: 12px;"></i>
            <input 
              type="text" 
              id="recentCallsSearchInput" 
              value="${this.recentSearchQuery}" 
              placeholder="Filter recent 20 calls by name or phone..." 
              style="background: transparent; border: none; outline: none; color: #fff; font-size: 12px; width: 100%;"
            />
            ${this.recentSearchQuery ? `
              <button id="clearRecentSearchBtn" style="background: transparent; border: none; color: #94a3b8; font-size: 12px; cursor: pointer;">✕</button>
            ` : ''}
          </div>

          <div id="recent20CallsContainer">
            ${this.renderRecent20ListHtml()}
          </div>
        </div>
      </div>
    `;
  }

  private renderKey(digit: string, sub: string): string {
    return `
      <button 
        class="dialpad-key-btn" 
        data-digit="${digit}" 
        style="height: 56px; border-radius: 14px; background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(255,255,255,0.08); color: #fff; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; user-select: none;"
      >
        <span style="font-size: 20px; font-weight: 700; line-height: 1;">${digit}</span>
        <span style="font-size: 8.5px; font-weight: 700; color: #94a3b8; letter-spacing: 0.5px; margin-top: 2px;">${sub}</span>
      </button>
    `;
  }

  private renderMetricsCardsHtml(metrics: TelephonyMetrics): string {
    return `
      <div style="background: #1e293b; border-radius: 12px; padding: 10px 12px; border: 1px solid rgba(255,255,255,0.06); text-align: center;">
        <div id="dialer-stat-total" style="font-size: 18px; font-weight: 800; color: #fff;">${metrics.total}</div>
        <div style="font-size: 10px; font-weight: 600; color: #94a3b8; margin-top: 2px;">Total Calls</div>
      </div>
      <div style="background: #1e293b; border-radius: 12px; padding: 10px 12px; border: 1px solid rgba(34, 197, 94, 0.2); text-align: center;">
        <div id="dialer-stat-answered" style="font-size: 18px; font-weight: 800; color: #22c55e;">${metrics.answered}</div>
        <div style="font-size: 10px; font-weight: 600; color: #86efac; margin-top: 2px;">Answered</div>
      </div>
      <div style="background: #1e293b; border-radius: 12px; padding: 10px 12px; border: 1px solid rgba(239, 68, 68, 0.2); text-align: center;">
        <div id="dialer-stat-missed" style="font-size: 18px; font-weight: 800; color: #ef4444;">${metrics.missed}</div>
        <div style="font-size: 10px; font-weight: 600; color: #fca5a5; margin-top: 2px;">Missed</div>
      </div>
      <div style="background: #1e293b; border-radius: 12px; padding: 10px 12px; border: 1px solid rgba(148, 163, 184, 0.2); text-align: center;">
        <div id="dialer-stat-unanswered" style="font-size: 18px; font-weight: 800; color: #cbd5e1;">${metrics.unanswered}</div>
        <div style="font-size: 10px; font-weight: 600; color: #94a3b8; margin-top: 2px;">Unanswered</div>
      </div>
      <div style="background: #1e293b; border-radius: 12px; padding: 10px 12px; border: 1px solid rgba(192, 132, 252, 0.2); text-align: center;">
        <div id="dialer-stat-talktime" style="font-size: 14px; font-weight: 800; color: #c084fc; font-family: monospace;">${metrics.talkTimeFormatted}</div>
        <div style="font-size: 10px; font-weight: 600; color: #d8b4fe; margin-top: 2px;">Talk Time</div>
      </div>
      <div style="background: #1e293b; border-radius: 12px; padding: 10px 12px; border: 1px solid rgba(56, 189, 248, 0.2); text-align: center;">
        <div id="dialer-stat-connrate" style="font-size: 18px; font-weight: 800; color: #38bdf8;">${metrics.connRate}</div>
        <div style="font-size: 10px; font-weight: 600; color: #7dd3fc; margin-top: 2px;">Conn Rate</div>
      </div>
    `;
  }

  private updateMetricsDisplay(): void {
    const grid = document.getElementById('softphoneTodayMetricsGrid');
    if (grid) {
      grid.innerHTML = this.renderMetricsCardsHtml(this.todayMetrics);
    }
  }

  private renderRecent20List(): void {
    const container = document.getElementById('recent20CallsContainer');
    if (container) {
      container.innerHTML = this.renderRecent20ListHtml();
      this.attachCallCardListeners();
    }
    const badge = document.getElementById('recent20CountBadge');
    if (badge) badge.textContent = String(this.recent20Calls.length);
  }

  private renderRecent20ListHtml(): string {
    if (this.isLoadingRecent20) {
      return `<div style="text-align: center; padding: 30px; color: #94a3b8;"><i class="fas fa-spinner fa-spin" style="margin-right: 8px;"></i>Loading recent calls...</div>`;
    }

    let filtered = this.recent20Calls;
    if (this.recentSearchQuery) {
      const q = this.recentSearchQuery.toLowerCase();
      filtered = filtered.filter(c => 
        (c.customer_name || '').toLowerCase().includes(q) ||
        (c.customer_phone || '').includes(q) ||
        (c.customer_phone_masked || '').includes(q) ||
        (c.raw_caller_number || '').includes(q)
      );
    }

    if (filtered.length === 0) {
      return `
        <div style="text-align: center; padding: 36px 16px; color: #64748b; background: #1e293b; border-radius: 14px; border: 1px solid rgba(255,255,255,0.06);">
          <i class="fas fa-phone-slash" style="font-size: 28px; margin-bottom: 8px; color: #475569;"></i>
          <p style="font-weight: 600; font-size: 13px; margin: 0;">${this.recentSearchQuery ? 'No recent calls match filter' : 'No recent calls yet'}</p>
        </div>
      `;
    }

    return `
      <div style="display: flex; flex-direction: column; gap: 8px;">
        ${filtered.map(c => this.renderCallCardHtml(c, 'recent')).join('')}
      </div>
    `;
  }

  // ──────────────────────────── 2. CALL HISTORY SCOPES (my, new_calls, team, overall) ────────────────────────────

  private renderHistoryScopeView(): string {
    const isTeamOrOverall = this.activeScope === 'team' || this.activeScope === 'overall';

    return `
      <div style="max-width: 540px; margin: 0 auto; padding: 14px 16px;">
        
        <!-- Filter Controls Bar -->
        <div style="background: #1e293b; border-radius: 14px; padding: 12px 14px; margin-bottom: 12px; border: 1px solid rgba(255,255,255,0.08); display: flex; flex-direction: column; gap: 10px;">
          
          <!-- Search Input -->
          <div style="display: flex; align-items: center; gap: 8px; background: #0f172a; padding: 7px 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);">
            <i class="fas fa-search" style="color: #64748b; font-size: 12px;"></i>
            <input 
              type="text" 
              id="scopeSearchInput" 
              value="${this.scopeFilterSearch}" 
              placeholder="Search caller name, masked phone..." 
              style="background: transparent; border: none; outline: none; color: #fff; font-size: 12px; width: 100%;"
            />
            ${this.scopeFilterSearch ? `
              <button id="clearScopeSearchBtn" style="background: transparent; border: none; color: #94a3b8; font-size: 12px; cursor: pointer;">✕</button>
            ` : ''}
          </div>

          <!-- Date Range Presets -->
          <div style="display: flex; gap: 4px; overflow-x: auto; scrollbar-width: none;">
            ${['TODAY', 'YESTERDAY', '3DAYS', '7DAYS', 'CUSTOM'].map(p => `
              <button 
                class="date-preset-btn" 
                data-preset="${p}" 
                style="flex: 1; padding: 5px 6px; border-radius: 6px; font-size: 10.5px; font-weight: 700; border: none; cursor: pointer; white-space: nowrap; background: ${this.scopeDatePreset === p ? '#3b82f6' : 'rgba(255,255,255,0.06)'}; color: ${this.scopeDatePreset === p ? '#fff' : '#94a3b8'};"
              >
                ${p === 'TODAY' ? 'Today' : p === 'YESTERDAY' ? 'Yesterday' : p === '3DAYS' ? '3 Days' : p === '7DAYS' ? '7 Days' : 'Custom'}
              </button>
            `).join('')}
          </div>

          <!-- Custom Date Range Row -->
          ${this.scopeDatePreset === 'CUSTOM' ? `
            <div style="display: flex; gap: 8px; align-items: center; background: #0f172a; padding: 6px 8px; border-radius: 8px;">
              <input type="date" id="scopeCustomStartInput" value="${this.customStartDate}" style="flex: 1; background: #1e293b; border: 1px solid #475569; color: #fff; padding: 4px 6px; border-radius: 6px; font-size: 11px;">
              <span style="font-size: 11px; color: #94a3b8;">to</span>
              <input type="date" id="scopeCustomEndInput" value="${this.customEndDate}" style="flex: 1; background: #1e293b; border: 1px solid #475569; color: #fff; padding: 4px 6px; border-radius: 6px; font-size: 11px;">
              <button id="applyScopeCustomDateBtn" style="padding: 4px 8px; background: #3b82f6; border: none; border-radius: 6px; color: #fff; font-size: 11px; font-weight: 700; cursor: pointer;">Go</button>
            </div>
          ` : ''}

          <!-- Type Filter & Sort Row -->
          <div style="display: flex; gap: 8px;">
            <select id="scopeTypeSelect" style="flex: 1; background: #0f172a; color: #fff; border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; padding: 6px 8px; font-size: 11px; font-weight: 600; outline: none;">
              <option value="" ${this.scopeFilterType === '' ? 'selected' : ''}>All Call Types</option>
              <option value="inbound_answered" ${this.scopeFilterType === 'inbound_answered' ? 'selected' : ''}>↙️ Incoming Answered</option>
              <option value="missed_by_staff" ${this.scopeFilterType === 'missed_by_staff' ? 'selected' : ''}>🚫 Missed by Staff</option>
              <option value="outbound_answered" ${this.scopeFilterType === 'outbound_answered' ? 'selected' : ''}>↗️ Outbound Answered</option>
              <option value="outbound_unanswered" ${this.scopeFilterType === 'outbound_unanswered' ? 'selected' : ''}>⏳ Outbound Unanswered</option>
              <option value="voicemail" ${this.scopeFilterType === 'voicemail' ? 'selected' : ''}>📼 Voicemail</option>
            </select>

            <select id="scopeSortSelect" style="flex: 1; background: #0f172a; color: #fff; border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; padding: 6px 8px; font-size: 11px; font-weight: 600; outline: none;">
              <option value="newest" ${this.scopeFilterSort === 'newest' ? 'selected' : ''}>Newest First</option>
              <option value="oldest" ${this.scopeFilterSort === 'oldest' ? 'selected' : ''}>Oldest First</option>
              <option value="longest" ${this.scopeFilterSort === 'longest' ? 'selected' : ''}>Longest Duration</option>
            </select>
          </div>

          <!-- Channel & Lead Scope Filter Row -->
          <div style="display: flex; gap: 8px;">
            <select id="scopeChannelSelect" style="flex: 1; background: #0f172a; color: #fff; border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; padding: 6px 8px; font-size: 11px; font-weight: 600; outline: none;">
              <option value="" ${this.scopeFilterChannel === '' ? 'selected' : ''}>All Channels</option>
              <option value="softphone" ${this.scopeFilterChannel === 'softphone' ? 'selected' : ''}>🎧 Softphone (WebRTC)</option>
              <option value="autodialer" ${this.scopeFilterChannel === 'autodialer' ? 'selected' : ''}>🤖 Auto Dialer</option>
              <option value="device" ${this.scopeFilterChannel === 'device' ? 'selected' : ''}>📱 Local Device (Carrier)</option>
            </select>

            <select id="scopeLeadScopeSelect" style="flex: 1; background: #0f172a; color: #fff; border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; padding: 6px 8px; font-size: 11px; font-weight: 600; outline: none;">
              <option value="" ${this.scopeFilterLeadScope === '' ? 'selected' : ''}>All Calls & Leads</option>
              <option value="my_leads" ${this.scopeFilterLeadScope === 'my_leads' ? 'selected' : ''}>👤 My Leads</option>
              <option value="staff_leads" ${this.scopeFilterLeadScope === 'staff_leads' ? 'selected' : ''}>👥 Staff Leads</option>
              <option value="others" ${this.scopeFilterLeadScope === 'others' ? 'selected' : ''}>📋 Others (Non-CRM)</option>
            </select>
          </div>

          <!-- Team Member Dropdown (if team or overall) -->
          ${isTeamOrOverall ? `
            <div>
              <select id="scopeTeamSelect" style="width: 100%; background: #0f172a; color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 8px; padding: 6px 8px; font-size: 11px; font-weight: 700; outline: none;">
                <option value="">All Team Members (${this.teamMembers.length})</option>
                ${this.teamMembers.map(m => `
                  <option value="${m.id}" ${this.scopeFilterTeamMember === String(m.id) ? 'selected' : ''}>
                    ${this.escapeHtml(m.name)} (${m.emp_code})
                  </option>
                `).join('')}
              </select>
            </div>
          ` : ''}
        </div>

        <!-- Scope Dynamic Result Metrics -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 12px;">
          <div style="background: #1e293b; border-radius: 8px; padding: 6px 8px; text-align: center; border: 1px solid rgba(255,255,255,0.06);">
            <div style="font-size: 14px; font-weight: 800; color: #fff;">${this.scopeMetrics.total}</div>
            <div style="font-size: 9px; color: #94a3b8;">Total</div>
          </div>
          <div style="background: #1e293b; border-radius: 8px; padding: 6px 8px; text-align: center; border: 1px solid rgba(34, 197, 94, 0.2);">
            <div style="font-size: 14px; font-weight: 800; color: #22c55e;">${this.scopeMetrics.answered}</div>
            <div style="font-size: 9px; color: #86efac;">Answered</div>
          </div>
          <div style="background: #1e293b; border-radius: 8px; padding: 6px 8px; text-align: center; border: 1px solid rgba(239, 68, 68, 0.2);">
            <div style="font-size: 14px; font-weight: 800; color: #ef4444;">${this.scopeMetrics.missed}</div>
            <div style="font-size: 9px; color: #fca5a5;">Missed</div>
          </div>
          <div style="background: #1e293b; border-radius: 8px; padding: 6px 8px; text-align: center; border: 1px solid rgba(192, 132, 252, 0.2);">
            <div style="font-size: 12px; font-weight: 800; color: #c084fc; font-family: monospace;">${this.scopeMetrics.talkTimeFormatted}</div>
            <div style="font-size: 9px; color: #d8b4fe;">Talk Time</div>
          </div>
        </div>

        <!-- Scope Calls List Container -->
        <div id="scopeCallsListContainer">
          ${this.renderScopeCallsListHtml()}
        </div>

        <!-- Scope Pagination Controls -->
        <div id="scopePaginationContainer" style="margin-top: 14px;">
          ${this.renderPaginationHtml(this.scopeTotalCount, this.scopePageSize, this.scopeCurrentPage, 'scope')}
        </div>
      </div>
    `;
  }

  private renderScopeCallsList(): void {
    const container = document.getElementById('scopeCallsListContainer');
    if (container) {
      container.innerHTML = this.renderScopeCallsListHtml();
      this.attachCallCardListeners();
    }
    const pag = document.getElementById('scopePaginationContainer');
    if (pag) {
      pag.innerHTML = this.renderPaginationHtml(this.scopeTotalCount, this.scopePageSize, this.scopeCurrentPage, 'scope');
      this.attachPaginationListeners();
    }
  }

  private renderScopeCallsListHtml(): string {
    if (this.isLoadingScopeCalls) {
      return `<div style="text-align: center; padding: 40px; color: #94a3b8;"><i class="fas fa-spinner fa-spin" style="margin-right: 8px;"></i>Loading calls...</div>`;
    }

    if (this.scopeCalls.length === 0) {
      return `
        <div style="text-align: center; padding: 40px 16px; color: #64748b; background: #1e293b; border-radius: 14px; border: 1px solid rgba(255,255,255,0.06);">
          <i class="fas fa-phone-slash" style="font-size: 32px; margin-bottom: 10px; color: #475569;"></i>
          <p style="font-weight: 700; font-size: 14px; margin: 0 0 4px 0; color: #cbd5e1;">No call records found</p>
          <p style="font-size: 12px; margin: 0;">Try adjusting your filters or date range.</p>
        </div>
      `;
    }

    return `
      <div style="display: flex; flex-direction: column; gap: 8px;">
        ${this.scopeCalls.map(c => this.renderCallCardHtml(c, 'scope')).join('')}
      </div>
    `;
  }

  // ──────────────────────────── 3. CONTACTS & ASSIGNED LEADS VIEW ────────────────────────────

  private renderContactsView(): string {
    return `
      <div style="max-width: 500px; margin: 0 auto; padding: 14px 16px;">
        
        <!-- Search Input -->
        <div style="background: #1e293b; border-radius: 12px; padding: 8px 12px; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; border: 1px solid rgba(255,255,255,0.08);">
          <i class="fas fa-search" style="color: #64748b; font-size: 12px;"></i>
          <input 
            type="text" 
            id="contactsSearchInput" 
            value="${this.contactsSearchQuery}" 
            placeholder="Search CRM leads, VGK, MNR, contacts..." 
            style="background: transparent; border: none; outline: none; color: #fff; font-size: 12.5px; width: 100%;"
          />
          ${this.contactsSearchQuery ? `
            <button id="clearContactsSearchBtn" style="background: transparent; border: none; color: #94a3b8; font-size: 12px; cursor: pointer;">✕</button>
          ` : ''}
        </div>

        <!-- 5 Authoritative Source Pills: All, Assigned Leads, VGK Members, MNR Members, Synced Mobile Contacts -->
        <div style="display: flex; gap: 6px; margin-bottom: 12px; overflow-x: auto; padding-bottom: 4px; scrollbar-width: none; -webkit-overflow-scrolling: touch;">
          <button class="contacts-source-btn" data-source="all" style="flex-shrink: 0; padding: 6px 10px; border-radius: 8px; font-size: 11px; font-weight: 700; border: none; cursor: pointer; background: ${this.contactsSourceType === 'all' ? '#3b82f6' : 'rgba(255,255,255,0.06)'}; color: ${this.contactsSourceType === 'all' ? '#fff' : '#94a3b8'};">
            All Contacts
          </button>
          <button class="contacts-source-btn" data-source="leads" style="flex-shrink: 0; padding: 6px 10px; border-radius: 8px; font-size: 11px; font-weight: 700; border: none; cursor: pointer; background: ${this.contactsSourceType === 'leads' ? '#0284c7' : 'rgba(255,255,255,0.06)'}; color: ${this.contactsSourceType === 'leads' ? '#fff' : '#94a3b8'};">
            <i class="fas fa-user-tag" style="margin-right: 4px;"></i>Assigned Leads
          </button>
          <button class="contacts-source-btn" data-source="vgk" style="flex-shrink: 0; padding: 6px 10px; border-radius: 8px; font-size: 11px; font-weight: 700; border: none; cursor: pointer; background: ${this.contactsSourceType === 'vgk' ? '#d97706' : 'rgba(255,255,255,0.06)'}; color: ${this.contactsSourceType === 'vgk' ? '#fff' : '#94a3b8'};">
            <i class="fas fa-handshake" style="margin-right: 4px;"></i>VGK Members
          </button>
          <button class="contacts-source-btn" data-source="mnr" style="flex-shrink: 0; padding: 6px 10px; border-radius: 8px; font-size: 11px; font-weight: 700; border: none; cursor: pointer; background: ${this.contactsSourceType === 'mnr' ? '#9333ea' : 'rgba(255,255,255,0.06)'}; color: ${this.contactsSourceType === 'mnr' ? '#fff' : '#94a3b8'};">
            <i class="fas fa-star" style="margin-right: 4px;"></i>MNR Members
          </button>
          <button class="contacts-source-btn" data-source="synced_contacts" style="flex-shrink: 0; padding: 6px 10px; border-radius: 8px; font-size: 11px; font-weight: 700; border: none; cursor: pointer; background: ${this.contactsSourceType === 'synced_contacts' ? '#059669' : 'rgba(255,255,255,0.06)'}; color: ${this.contactsSourceType === 'synced_contacts' ? '#fff' : '#94a3b8'};">
            <i class="fas fa-mobile-screen" style="margin-right: 4px;"></i>Synced Contacts
          </button>
        </div>

        <!-- Contacts Count Header -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 11px; color: #94a3b8;">
          <span id="contactsCountSpan">Showing ${this.contactsList.length} of ${this.contactsTotal} contacts</span>
        </div>

        <!-- Contacts List Container -->
        <div id="contactsListContainer">
          ${this.renderContactsListHtml()}
        </div>

        <!-- Contacts Pagination -->
        <div id="contactsPaginationContainer" style="margin-top: 14px;">
          ${this.renderPaginationHtml(this.contactsTotal, this.contactsPageSize, this.contactsPage, 'contacts')}
        </div>
      </div>
    `;
  }

  private renderContactsList(): void {
    const countSpan = document.getElementById('contactsCountSpan');
    if (countSpan) {
      countSpan.textContent = `Showing ${this.contactsList.length} of ${this.contactsTotal} contacts`;
    }
    const container = document.getElementById('contactsListContainer');
    if (container) {
      container.innerHTML = this.renderContactsListHtml();
      this.attachContactCardListeners();
    }
    const pag = document.getElementById('contactsPaginationContainer');
    if (pag) {
      pag.innerHTML = this.renderPaginationHtml(this.contactsTotal, this.contactsPageSize, this.contactsPage, 'contacts');
      this.attachPaginationListeners();
    }
  }

  private renderContactsListHtml(): string {
    if (this.isLoadingContacts) {
      return `<div style="text-align: center; padding: 40px; color: #94a3b8;"><i class="fas fa-spinner fa-spin" style="margin-right: 8px;"></i>Loading contacts...</div>`;
    }

    if (this.contactsList.length === 0) {
      return `
        <div style="text-align: center; padding: 40px 16px; color: #64748b; background: #1e293b; border-radius: 14px; border: 1px solid rgba(255,255,255,0.06);">
          <i class="fas fa-address-book" style="font-size: 32px; margin-bottom: 10px; color: #475569;"></i>
          <p style="font-weight: 700; font-size: 14px; margin: 0 0 4px 0; color: #cbd5e1;">No contacts found</p>
          <p style="font-size: 12px; margin: 0;">Try adjusting your search query.</p>
        </div>
      `;
    }

    return `
      <div style="display: flex; flex-direction: column; gap: 8px;">
        ${this.contactsList.map(c => {
          const name = this.escapeHtml(c.name || 'Contact');
          const maskedPhone = this.escapeHtml(c.masked_phone || c.phone || '—');
          const cleanPhone = (c.raw_phone || c.phone || '').replace(/\D/g, '').slice(-10);
          const initial = (name.replace(/[^a-zA-Z]/g, '') || 'C').slice(0, 2).toUpperCase();
          const isLead = c.source_type === 'assigned_lead' || c.source_type === 'lead';
          const isVgk = c.source_type === 'vgk_member';
          const isMnr = c.source_type === 'mnr_member';

          let avatarBg = 'linear-gradient(135deg, #059669, #047857)'; // green default (synced)
          let badgeBg = 'rgba(34, 197, 94, 0.2)';
          let badgeColor = '#4ade80';
          let defaultBadge = 'Contact';

          if (isLead) {
            avatarBg = 'linear-gradient(135deg, #0284c7, #0369a1)';
            badgeBg = 'rgba(59, 130, 246, 0.2)';
            badgeColor = '#60a5fa';
            defaultBadge = 'Lead';
          } else if (isVgk) {
            avatarBg = 'linear-gradient(135deg, #d97706, #b45309)';
            badgeBg = 'rgba(245, 158, 11, 0.2)';
            badgeColor = '#fbbf24';
            defaultBadge = 'VGK Member';
          } else if (isMnr) {
            avatarBg = 'linear-gradient(135deg, #9333ea, #7e22ce)';
            badgeBg = 'rgba(168, 85, 247, 0.2)';
            badgeColor = '#c084fc';
            defaultBadge = 'MNR Member';
          }

          return `
            <div style="background: #1e293b; border-radius: 12px; padding: 10px 12px; border: 1px solid rgba(255,255,255,0.06); display: flex; align-items: center; justify-content: space-between;">
              <div style="display: flex; align-items: center; gap: 10px; min-width: 0;">
                <div style="width: 38px; height: 38px; border-radius: 50%; background: ${avatarBg}; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; color: #fff; flex-shrink: 0;">
                  ${initial}
                </div>
                <div style="min-width: 0;">
                  <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                    <span class="customer-history-trigger" data-phone="${cleanPhone}" data-name="${this.escapeAttr(c.name)}" style="font-weight: 700; font-size: 13px; color: #fff; cursor: pointer; text-decoration: underline; text-decoration-color: rgba(255,255,255,0.3);">
                      ${name}
                    </span>
                    <span style="font-size: 9px; font-weight: 700; padding: 1px 5px; border-radius: 4px; background: ${badgeBg}; color: ${badgeColor};">
                      ${this.escapeHtml(c.badge || defaultBadge)}
                    </span>
                  </div>
                  <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
                    <span style="font-family: monospace;">${maskedPhone}</span>
                    ${c.subtitle ? ` · <span style="color: #64748b;">${this.escapeHtml(c.subtitle)}</span>` : ''}
                  </div>
                </div>
              </div>

              <div style="display: flex; align-items: center; gap: 6px; flex-shrink: 0;">
                <button class="customer-history-trigger-btn" data-phone="${cleanPhone}" data-name="${this.escapeAttr(c.name)}" title="Customer Timeline" style="width: 32px; height: 32px; border-radius: 50%; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.3); color: #38bdf8; cursor: pointer; display: flex; align-items: center; justify-content: center;">
                  <i class="fas fa-clock-rotate-left fa-xs"></i>
                </button>
                <button class="call-action-btn" data-phone="${cleanPhone}" data-name="${this.escapeAttr(c.name)}" title="Call Now" style="width: 34px; height: 34px; border-radius: 50%; background: linear-gradient(135deg, #22c55e, #16a34a); border: none; color: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center;">
                  <i class="fas fa-phone fa-xs"></i>
                </button>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  // ──────────────────────────── SHARED CALL CARD RENDERER ────────────────────────────

  private renderCallCardHtml(c: CallItem, originContext: string): string {
    const rawCustomerNum = c.raw_caller_number || c.customer_phone || '';
    const cleanPhone = (rawCustomerNum || '').replace(/\D/g, '').slice(-10);
    const name = this.escapeHtml(c.customer_name || 'Customer Lead');
    const isUnresolved = c.caller_identity_source === 'unresolved_forwarded' || c.customer_phone_masked === 'Unknown / Not provided' || c.customer_phone_display === 'Unknown / Not provided';
    const maskedPhone = isUnresolved ? '<span style="color:#94a3b8; font-style:italic;">Unknown / Not provided</span>' : this.escapeHtml(c.customer_phone_masked || this.maskPhone(cleanPhone));
    const initial = (name.replace(/[^a-zA-Z]/g, '') || 'C').slice(0, 2).toUpperCase();

    const isForwarded = Boolean(c.is_forwarded || c.forwarded_from_number);
    const fwdMasked = c.forwarded_from_masked || c.forwarded_from_display || (c.forwarded_from_number ? this.maskPhone(c.forwarded_from_number) : '');

    // Direction Pill
    const isIncoming = (c.direction === 'inbound') || ['inbound_answered', 'missed_by_staff', 'voicemail'].includes(c.computed_type || '');
    const dirBadgeColor = isIncoming ? 'rgba(34, 197, 94, 0.2)' : 'rgba(59, 130, 246, 0.2)';
    const dirTextColor = isIncoming ? '#4ade80' : '#60a5fa';
    const dirText = isIncoming ? (isForwarded ? '↙ FWD IN' : '↙ IN') : '↗ OUT';

    // Type Badge
    let typeBadgeBg = 'rgba(148, 163, 184, 0.2)';
    let typeBadgeColor = '#cbd5e1';
    let typeText = c.type_label || (isIncoming ? 'Incoming' : 'Outgoing');

    if (c.computed_type === 'inbound_answered') {
      typeBadgeBg = 'rgba(34, 197, 94, 0.25)';
      typeBadgeColor = '#86efac';
      typeText = isForwarded ? 'Fwd Answered' : 'Incoming';
    } else if (c.computed_type === 'missed_by_staff') {
      typeBadgeBg = 'rgba(239, 68, 68, 0.25)';
      typeBadgeColor = '#fca5a5';
      typeText = isForwarded ? 'Fwd Missed' : 'Missed';
    } else if (c.computed_type === 'outbound_answered') {
      typeBadgeBg = 'rgba(59, 130, 246, 0.25)';
      typeBadgeColor = '#93c5fd';
      typeText = 'Outgoing';
    } else if (c.computed_type === 'outbound_unanswered') {
      typeBadgeBg = 'rgba(148, 163, 184, 0.2)';
      typeBadgeColor = '#94a3b8';
      typeText = 'Unanswered';
    } else if (c.computed_type === 'voicemail') {
      typeBadgeBg = 'rgba(192, 132, 252, 0.25)';
      typeBadgeColor = '#d8b4fe';
      typeText = 'Voicemail';
    }

    const durationText = c.duration_formatted || this.formatDuration(c.duration_seconds || 0);
    const timeFormatted = this.formatRelativeTime(c.started_at || c.answered_at || c.created_at);
    const audioKey = `rec_${c.id}`;
    const hasRecording = Boolean(c.recording_url || c.has_recording);
    const isVoicemail = c.computed_type === 'voicemail' || (c.status && c.status.toLowerCase().includes('voicemail'));
    const recPlayTitle = isVoicemail ? 'Listen to Voicemail' : 'Listen to Call Recording';
    const recBtnBg = isVoicemail ? 'rgba(192, 132, 252, 0.2)' : 'rgba(56, 189, 248, 0.15)';
    const recBtnBorder = isVoicemail ? '1px solid rgba(192, 132, 252, 0.4)' : '1px solid rgba(56, 189, 248, 0.3)';
    const recBtnColor = isVoicemail ? '#d8b4fe' : '#38bdf8';
    const recAudioUrl = c.recording_url || `/api/v1/telephony/calls/${c.call_session_id}/recording`;

    // Missed Call Action Taken UI
    let actionTakenHtml = '';
    if (c.computed_type === 'missed_by_staff') {
      if (c.action_taken) {
        actionTakenHtml = `
          <span style="display: inline-flex; align-items: center; gap: 3px; font-size: 9.5px; font-weight: 700; padding: 2px 6px; border-radius: 6px; background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); color: #4ade80;" title="${this.escapeAttr(c.action_notes || '')}">
            <i class="fas fa-check-double"></i> Action Taken
          </span>
        `;
      } else {
        actionTakenHtml = `
          <button class="action-taken-open-btn" data-session-id="${this.escapeAttr(c.call_session_id || String(c.id))}" data-phone="${cleanPhone}" data-name="${this.escapeAttr(name)}" style="display: inline-flex; align-items: center; gap: 3px; font-size: 9.5px; font-weight: 700; padding: 2px 6px; border-radius: 6px; background: rgba(234, 179, 8, 0.15); border: 1px solid rgba(234, 179, 8, 0.3); color: #facc15; cursor: pointer;">
            <i class="fas fa-clipboard-check"></i> Action Taken
          </button>
        `;
      }
    }

    // Channel & Lead Scope Badges
    const chanKey = c.channel || (c.source === 'device' ? 'device' : (c.source === 'dialer' ? 'autodialer' : 'softphone'));
    let chanBg = 'rgba(56, 189, 248, 0.15)';
    let chanColor = '#38bdf8';
    let chanText = '🎧 VoIP';
    if (chanKey === 'device') {
      chanBg = 'rgba(148, 163, 184, 0.15)';
      chanColor = '#cbd5e1';
      chanText = '📱 SIM';
    } else if (chanKey === 'autodialer') {
      chanBg = 'rgba(168, 85, 247, 0.15)';
      chanColor = '#c084fc';
      chanText = '🤖 Dialer';
    }

    const scopeKey = c.lead_scope || (c.crm_lead_id ? 'my_leads' : 'others');
    let scopeBg = 'rgba(148, 163, 184, 0.12)';
    let scopeColor = '#94a3b8';
    let scopeText = '📋 Non-CRM';
    if (scopeKey === 'my_leads') {
      scopeBg = 'rgba(34, 197, 94, 0.15)';
      scopeColor = '#4ade80';
      scopeText = '👤 My Lead';
    } else if (scopeKey === 'staff_leads') {
      scopeBg = 'rgba(234, 179, 8, 0.15)';
      scopeColor = '#facc15';
      scopeText = '👥 Team Lead';
    }

    return `
      <div style="background: #1e293b; border-radius: 12px; padding: 10px 12px; border: 1px solid rgba(255,255,255,0.06);">
        <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 8px;">
          
          <div style="display: flex; align-items: flex-start; gap: 10px; min-width: 0; flex: 1;">
            <div style="width: 36px; height: 36px; border-radius: 50%; background: ${isIncoming ? 'rgba(34, 197, 94, 0.15)' : 'rgba(59, 130, 246, 0.15)'}; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: ${isIncoming ? '#4ade80' : '#60a5fa'}; flex-shrink: 0; margin-top: 2px;">
              ${initial}
            </div>

            <div style="min-width: 0; flex: 1;">
              <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 2px;">
                <span class="customer-history-trigger" data-phone="${cleanPhone}" data-name="${this.escapeAttr(name)}" style="font-weight: 700; font-size: 13px; color: #fff; cursor: pointer; text-decoration: underline; text-decoration-color: rgba(255,255,255,0.3);">
                  ${name}
                </span>
                <span style="font-size: 9px; font-weight: 700; padding: 1px 5px; border-radius: 4px; background: ${dirBadgeColor}; color: ${dirTextColor}; font-family: monospace;">
                  ${dirText}
                </span>
                <span style="font-size: 9px; font-weight: 700; padding: 1px 5px; border-radius: 4px; background: ${typeBadgeBg}; color: ${typeBadgeColor};">
                  ${this.escapeHtml(typeText)}
                </span>
                <span style="font-size: 9px; font-weight: 700; padding: 1px 5px; border-radius: 4px; background: rgba(255,255,255,0.06); color: #cbd5e1; font-family: monospace;">
                  ${durationText}
                </span>
                <span style="font-size: 9px; font-weight: 700; padding: 1px 5px; border-radius: 4px; background: ${chanBg}; color: ${chanColor}; font-family: monospace;">
                  ${chanText}
                </span>
                <span style="font-size: 9px; font-weight: 700; padding: 1px 5px; border-radius: 4px; background: ${scopeBg}; color: ${scopeColor};" title="${scopeKey === 'others' ? 'Non-CRM / Personal call — excluded from staff performance metrics' : ''}">
                  ${scopeText}
                </span>
              </div>

                ${(!isUnresolved && cleanPhone && cleanPhone.length >= 6 && cleanPhone !== 'unresolved') ? `
                  <span class="call-action-btn" data-phone="${cleanPhone}" data-name="${this.escapeAttr(name)}" style="font-family: monospace; cursor: pointer; color: #60a5fa; text-decoration: underline; text-decoration-style: dashed;" title="Click to call back">${maskedPhone}</span>
                ` : `
                  <span style="font-family: monospace;">${maskedPhone}</span>
                `}
                ${isForwarded && fwdMasked ? `
                  <span style="font-size: 9.5px; padding: 1px 5px; border-radius: 4px; background: rgba(234, 179, 8, 0.15); border: 1px solid rgba(234, 179, 8, 0.3); color: #facc15; font-family: monospace;" title="Forwarded From">
                    <i class="fas fa-share fa-xs" style="margin-right: 2px;"></i>Fwd: ${this.escapeHtml(fwdMasked)}
                  </span>
                ` : ''}
                <span>·</span>
                <span>${timeFormatted}</span>
                ${c.operator_name ? `<span>· 👤 ${this.escapeHtml(c.operator_name)}</span>` : ''}
              </div>

              ${actionTakenHtml ? `<div style="margin-top: 4px;">${actionTakenHtml}</div>` : ''}
            </div>
          </div>

          <!-- Actions: Audio Recording Play + Customer Timeline + Redial Call -->
          <div style="display: flex; align-items: center; gap: 6px; flex-shrink: 0; margin-top: 2px;">
            ${hasRecording ? `
              <button class="audio-play-trigger-btn" data-audio-key="${audioKey}" data-stream-url="${this.escapeAttr(recAudioUrl)}" title="${recPlayTitle}" style="width: 32px; height: 32px; border-radius: 50%; background: ${recBtnBg}; border: ${recBtnBorder}; color: ${recBtnColor}; cursor: pointer; display: flex; align-items: center; justify-content: center;">
                <i class="fas ${this.playingAudioKey === audioKey ? 'fa-pause' : 'fa-play'} fa-xs"></i>
              </button>
            ` : ''}

            <button class="customer-history-trigger-btn" data-phone="${cleanPhone}" data-name="${this.escapeAttr(name)}" title="Customer Timeline" style="width: 32px; height: 32px; border-radius: 50%; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.3); color: #38bdf8; cursor: pointer; display: flex; align-items: center; justify-content: center;">
              <i class="fas fa-clock-rotate-left fa-xs"></i>
            </button>

            ${(!isUnresolved && cleanPhone && cleanPhone.length >= 6 && cleanPhone !== 'unresolved') ? `
              <button class="call-action-btn" data-phone="${cleanPhone}" data-name="${this.escapeAttr(name)}" title="Call Now" style="width: 34px; height: 34px; border-radius: 50%; background: linear-gradient(135deg, #22c55e, #16a34a); border: none; color: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center;">
                <i class="fas fa-phone fa-xs"></i>
              </button>
            ` : `
              <button class="call-action-btn disabled" title="Customer number not provided" style="width: 34px; height: 34px; border-radius: 50%; background: #334155; border: none; color: #64748b; cursor: not-allowed; display: flex; align-items: center; justify-content: center; opacity: 0.5;" disabled>
                <i class="fas fa-phone-slash fa-xs"></i>
              </button>
            `}
          </div>
        </div>
      </div>
    `;
  }

  // ──────────────────────────── 4. IN-CALL ACTIVE SCREEN ────────────────────────────

  private renderInCallScreen(): string {
    const mins = Math.floor(this.callDuration / 60).toString().padStart(2, '0');
    const secs = (this.callDuration % 60).toString().padStart(2, '0');
    const maskedPhone = this.maskPhone(this.dialNumber);
    const session = telephonyService.getSession();
    const isIncomingRinging = session.isIncoming && !this.isCallConnected;

    if (isIncomingRinging) {
      return `
        <div style="max-width: 380px; margin: 30px auto; padding: 20px; text-align: center;">
          <div style="width: 86px; height: 86px; border-radius: 50%; background: linear-gradient(135deg, #10b981, #059669); display: flex; align-items: center; justify-content: center; font-size: 32px; color: #fff; margin: 0 auto 16px auto; box-shadow: 0 8px 24px rgba(16, 185, 129, 0.4);">
            <i class="fas fa-phone-volume fa-shake"></i>
          </div>

          <h3 style="font-size: 20px; font-weight: 700; margin: 0 0 4px 0; color: #fff;">${this.selectedContactName || 'Incoming Caller'}</h3>
          <div style="font-size: 13px; color: #94a3b8; margin-bottom: 6px;">${maskedPhone}</div>
          <p id="softphoneCallStatusText" style="font-size: 13px; color: #38bdf8; font-weight: 600; margin: 0 0 24px 0;">Incoming Call...</p>

          <div style="display: flex; align-items: center; justify-content: center; gap: 32px; margin-top: 24px;">
            <button id="softphoneAnswerCallBtn" style="width: 66px; height: 66px; border-radius: 50%; background: linear-gradient(135deg, #10b981, #059669); border: none; color: #fff; font-size: 24px; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 8px 24px rgba(16, 185, 129, 0.4); cursor: pointer;" title="Answer Call">
              <i class="fas fa-phone"></i>
            </button>
            <button id="softphoneRejectCallBtn" style="width: 66px; height: 66px; border-radius: 50%; background: linear-gradient(135deg, #ef4444, #b91c1c); border: none; color: #fff; font-size: 24px; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 8px 24px rgba(239, 68, 68, 0.4); cursor: pointer;" title="Decline Call">
              <i class="fas fa-phone-slash"></i>
            </button>
          </div>
        </div>
      `;
    }

    return `
      <div style="max-width: 380px; margin: 20px auto; padding: 20px; text-align: center;">
        <div style="width: 86px; height: 86px; border-radius: 50%; background: linear-gradient(135deg, #3b82f6, #1d4ed8); display: flex; align-items: center; justify-content: center; font-size: 32px; color: #fff; margin: 0 auto 16px auto; box-shadow: 0 8px 24px rgba(59, 130, 246, 0.4);">
          <i class="fas fa-user"></i>
        </div>

        <h3 style="font-size: 20px; font-weight: 700; margin: 0 0 4px 0; color: #fff;">${this.selectedContactName || maskedPhone}</h3>
        ${this.selectedContactName ? `<div style="font-size: 13px; color: #94a3b8; margin-bottom: 6px;">${maskedPhone}</div>` : ''}
        <p id="softphoneCallStatusText" style="font-size: 13px; color: ${this.isCallConnected ? '#22c55e' : '#38bdf8'}; font-weight: 600; margin: 0 0 8px 0;">${this.callStatusText}</p>
        
        <div id="softphoneCallTimer" style="font-size: ${this.isCallConnected ? '26px' : '16px'}; font-weight: 700; font-family: ${this.isCallConnected ? 'monospace' : 'inherit'}; color: ${this.isCallConnected ? '#cbd5e1' : '#38bdf8'}; margin-bottom: 24px;">
          ${this.isCallConnected ? `${mins}:${secs}` : `<i class="fas fa-phone-volume fa-shake" style="margin-right: 6px;"></i> Ringing...`}
        </div>

        <!-- In-Call Control Grid: Mute, Speaker, Hold -->
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 20px;">
          <button id="callMuteBtn" style="padding: 12px; border-radius: 14px; background: ${this.isMuted ? '#ef4444' : 'rgba(255,255,255,0.08)'}; border: none; color: #fff; cursor: pointer;">
            <i class="fas fa-microphone-slash" style="font-size: 18px; margin-bottom: 4px;"></i>
            <div style="font-size: 11px; font-weight: 600;">${this.isMuted ? 'Muted' : 'Mute'}</div>
          </button>
          
          <button id="callSpeakerBtn" style="padding: 12px; border-radius: 14px; background: ${this.isSpeaker ? '#3b82f6' : 'rgba(255,255,255,0.08)'}; border: none; color: #fff; cursor: pointer;">
            <i class="fas fa-volume-high" style="font-size: 18px; margin-bottom: 4px;"></i>
            <div style="font-size: 11px; font-weight: 600;">Speaker</div>
          </button>

          <button id="callHoldBtn" style="padding: 12px; border-radius: 14px; background: ${this.isHold ? '#eab308' : 'rgba(255,255,255,0.08)'}; border: none; color: #fff; cursor: pointer;">
            <i class="fas fa-pause" style="font-size: 18px; margin-bottom: 4px;"></i>
            <div style="font-size: 11px; font-weight: 600;">${this.isHold ? 'On Hold' : 'Hold'}</div>
          </button>
        </div>

        <!-- In-Call DTMF Keypad Toggle & Drawer -->
        <div style="margin-bottom: 24px;">
          <button id="inCallDTMFToggleBtn" style="padding: 6px 14px; border-radius: 16px; background: ${this.showInCallDTMF ? '#3b82f6' : 'rgba(255,255,255,0.06)'}; border: 1px solid rgba(255,255,255,0.12); color: #fff; font-size: 11.5px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;">
            <i class="fas fa-table-cells"></i> ${this.showInCallDTMF ? 'Hide DTMF Keypad' : 'DTMF Keypad'}
          </button>

          ${this.showInCallDTMF ? `
            <div style="margin-top: 14px; background: rgba(30, 41, 59, 0.9); padding: 12px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.1);">
              <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">
                ${['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#'].map(d => `
                  <button class="in-call-dtmf-btn" data-digit="${d}" style="height: 44px; border-radius: 10px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); color: #fff; font-size: 18px; font-weight: 700; cursor: pointer;">
                    ${d}
                  </button>
                `).join('')}
              </div>
            </div>
          ` : ''}
        </div>

        <!-- Hangup Call Button -->
        <div style="display: flex; flex-direction: column; align-items: center; gap: 14px;">
          <button id="softphoneEndCallBtn" style="width: 68px; height: 68px; border-radius: 50%; background: linear-gradient(135deg, #ef4444, #b91c1c); border: none; color: #fff; font-size: 24px; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 8px 24px rgba(239, 68, 68, 0.4); cursor: pointer;">
            <i class="fas fa-phone-slash"></i>
          </button>

          <button id="softphoneDirectSimBtn" style="padding: 5px 12px; border-radius: 16px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); color: #38bdf8; font-size: 11px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 5px;">
            <i class="fas fa-mobile-screen"></i> Direct SIM Call
          </button>
        </div>
      </div>
    `;
  }

  // ──────────────────────────── 5. BOTTOM SHEETS RENDERER ────────────────────────────

  private renderBottomSheet(): void {
    const container = document.getElementById('softphoneBottomSheetContainer');
    if (!container) return;

    if (!this.activeBottomSheet) {
      container.innerHTML = '';
      return;
    }

    if (this.activeBottomSheet === 'customer_history') {
      container.innerHTML = this.renderCustomerHistorySheetHtml();
    } else if (this.activeBottomSheet === 'action_taken') {
      container.innerHTML = this.renderActionTakenSheetHtml();
    } else if (this.activeBottomSheet === 'quick_staff_verify') {
      container.innerHTML = this.renderQuickStaffVerifySheetHtml();
    }

    this.attachBottomSheetListeners();
  }

  private renderCustomerHistorySheetHtml(): string {
    const data = this.customerHistoryData;
    const custName = this.escapeHtml(data?.lead?.name || data?.customer_name || 'Customer Lead');
    const rawPhone = data?.raw_phone || '';
    const cleanPhone = rawPhone.replace(/\D/g, '').slice(-10);
    const maskedPhone = this.escapeHtml(data?.phone_masked || this.maskPhone(cleanPhone));
    const historyList = data?.history || [];

    return `
      <!-- Backdrop Overlay -->
      <div id="bottomSheetBackdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.65); z-index: 999; backdrop-filter: blur(2px);"></div>

      <!-- Slide-Up Drawer -->
      <div style="position: fixed; bottom: 0; left: 0; right: 0; max-height: 85vh; background: #0f172a; border-top-left-radius: 20px; border-top-right-radius: 20px; z-index: 1000; display: flex; flex-direction: column; box-shadow: 0 -8px 30px rgba(0,0,0,0.6); border-top: 1px solid rgba(255,255,255,0.12);">
        
        <!-- Drawer Header -->
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; border-bottom: 1px solid rgba(255,255,255,0.08);">
          <div>
            <div style="font-size: 15px; font-weight: 700; color: #fff;">
              <i class="fas fa-user-clock" style="color: #38bdf8; margin-right: 6px;"></i>${custName}
            </div>
            <div style="font-size: 11.5px; color: #94a3b8; font-family: monospace; margin-top: 2px;">
              ${maskedPhone}
            </div>
          </div>
          <button id="closeBottomSheetBtn" style="background: rgba(255,255,255,0.08); border: none; color: #cbd5e1; width: 32px; height: 32px; border-radius: 50%; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center;">
            ✕
          </button>
        </div>

        <!-- Scrollable Content -->
        <div style="padding: 16px; overflow-y: auto; flex: 1;">
          ${this.customerHistoryLoading ? `
            <div style="text-align: center; padding: 40px; color: #94a3b8;">
              <i class="fas fa-spinner fa-spin" style="margin-right: 8px;"></i>Fetching customer timeline...
            </div>
          ` : `
            <!-- Lead Details Card -->
            <div style="background: #1e293b; border-radius: 12px; padding: 12px 14px; margin-bottom: 16px; border: 1px solid rgba(255,255,255,0.06);">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 13px; font-weight: 700; color: #fff;">${custName}</span>
                <span class="badge" style="background: rgba(59, 130, 246, 0.2); color: #60a5fa; font-size: 10.5px; padding: 2px 7px; border-radius: 8px;">
                  ${this.escapeHtml(data?.lead?.status || 'Customer')}
                </span>
              </div>
              <div style="font-size: 11.5px; color: #94a3b8; display: flex; flex-direction: column; gap: 4px;">
                <div><i class="fas fa-phone" style="width: 16px; color: #64748b;"></i> <span style="font-family: monospace; color: #cbd5e1;">${maskedPhone}</span></div>
                ${data?.lead?.email ? `<div><i class="fas fa-envelope" style="width: 16px; color: #64748b;"></i> ${this.escapeHtml(data.lead.email)}</div>` : ''}
                ${data?.lead?.city ? `<div><i class="fas fa-location-dot" style="width: 16px; color: #64748b;"></i> ${this.escapeHtml(data.lead.city)}</div>` : ''}
              </div>
            </div>

            <!-- Interaction History Header & Call Now Button -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
              <span style="font-size: 13px; font-weight: 700; color: #fff;">
                <i class="fas fa-timeline" style="color: #60a5fa; margin-right: 5px;"></i> Interaction History (${data?.total_calls || historyList.length})
              </span>
              <button class="call-action-btn" data-phone="${cleanPhone}" data-name="${this.escapeAttr(custName)}" style="padding: 6px 14px; border-radius: 16px; background: linear-gradient(135deg, #22c55e, #16a34a); border: none; color: #fff; font-size: 11.5px; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; gap: 5px;">
                <i class="fas fa-phone fa-xs"></i> Call Now
              </button>
            </div>

            <!-- Timeline Items -->
            ${historyList.length === 0 ? `
              <div style="text-align: center; padding: 30px; color: #64748b;">No previous calls found.</div>
            ` : `
              <div style="display: flex; flex-direction: column; gap: 10px; border-left: 2px solid rgba(255,255,255,0.1); padding-left: 14px; margin-left: 6px;">
                ${historyList.map(h => {
                  const isIncoming = (h.direction === 'inbound') || (h.type && h.type.toLowerCase().includes('in')) || h.type === 'Missed by Staff';
                  const timeFormatted = this.formatRelativeTime(h.started_at || h.created_at);
                  const audioKey = `timeline_${h.id}`;
                  const hasRecording = Boolean(h.recording_url || h.has_recording);
                  const isVm = (h.type && h.type.toLowerCase().includes('voicemail')) || (h.computed_type === 'voicemail') || (h.status && h.status.toLowerCase().includes('voicemail'));
                  const audioUrl = h.recording_url || `/api/v1/telephony/calls/${h.call_session_id || h.id}/recording`;

                  return `
                    <div style="position: relative; background: #1e293b; border-radius: 10px; padding: 10px 12px; border: 1px solid rgba(255,255,255,0.06);">
                      <!-- Timeline Node Dot -->
                      <div style="position: absolute; left: -21px; top: 12px; width: 12px; height: 12px; border-radius: 50%; background: ${isVm ? '#c084fc' : (isIncoming ? '#22c55e' : '#3b82f6')}; border: 2px solid #0f172a;"></div>

                      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <div style="display: flex; align-items: center; gap: 6px;">
                          <span style="font-size: 9.5px; font-weight: 700; padding: 1px 5px; border-radius: 4px; background: ${isVm ? 'rgba(192, 132, 252, 0.2)' : (isIncoming ? 'rgba(34, 197, 94, 0.2)' : 'rgba(59, 130, 246, 0.2)')}; color: ${isVm ? '#d8b4fe' : (isIncoming ? '#4ade80' : '#60a5fa')}; font-family: monospace;">
                            ${isVm ? '📼 VM' : (isIncoming ? '↙ IN' : '↗ OUT')}
                          </span>
                          <span style="font-size: 11px; font-weight: 700; color: #fff;">${this.escapeHtml(h.type)}</span>
                          <span style="font-size: 10px; font-weight: 600; color: #facc15; font-family: monospace;">${this.escapeHtml(h.duration_formatted || '00m 00s')}</span>
                        </div>
                        <span style="font-size: 10.5px; color: #94a3b8;">${timeFormatted}</span>
                      </div>

                      <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
                        Handled By: <strong style="color: #cbd5e1;">${this.escapeHtml(h.operator_name || 'System')}</strong>
                        ${h.called_did ? ` · DID: <span style="color: #64748b;">${this.escapeHtml(this.maskPhone(h.called_did))}</span>` : ''}
                      </div>

                      ${h.ivr_selections && h.ivr_selections.length > 0 ? `
                        <div style="margin-top: 6px; padding: 4px 8px; background: rgba(0,0,0,0.3); border-radius: 6px; border: 1px solid rgba(234, 179, 8, 0.2); font-size: 10.5px; color: #facc15;">
                          <i class="fas fa-list-check" style="margin-right: 4px;"></i>IVR Selected: 
                          ${h.ivr_selections.map(s => `<strong>${this.escapeHtml(s.label || s.digit || '')}</strong>`).join(', ')}
                        </div>
                      ` : ''}

                      ${hasRecording ? `
                        <div style="margin-top: 6px;">
                          <button class="audio-play-trigger-btn" data-audio-key="${audioKey}" data-stream-url="${this.escapeAttr(audioUrl)}" style="padding: 4px 10px; border-radius: 12px; background: ${isVm ? 'rgba(192, 132, 252, 0.2)' : 'rgba(56, 189, 248, 0.15)'}; border: ${isVm ? '1px solid rgba(192, 132, 252, 0.4)' : '1px solid rgba(56, 189, 248, 0.3)'}; color: ${isVm ? '#d8b4fe' : '#38bdf8'}; font-size: 10.5px; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; gap: 5px;">
                            <i class="fas ${this.playingAudioKey === audioKey ? 'fa-pause' : 'fa-play'} fa-xs"></i> ${isVm ? 'Play Voicemail' : 'Play Audio'}
                          </button>
                        </div>
                      ` : ''}
                    </div>
                  `;
                }).join('')}
              </div>
            `}
          `}
        </div>
      </div>
    `;
  }

  private renderActionTakenSheetHtml(): string {
    return `
      <!-- Backdrop Overlay -->
      <div id="bottomSheetBackdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.65); z-index: 999; backdrop-filter: blur(2px);"></div>

      <!-- Slide-Up Drawer -->
      <div style="position: fixed; bottom: 0; left: 0; right: 0; background: #0f172a; border-top-left-radius: 20px; border-top-right-radius: 20px; z-index: 1000; box-shadow: 0 -8px 30px rgba(0,0,0,0.6); border-top: 1px solid rgba(255,255,255,0.12); padding: 18px;">
        
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
          <div>
            <div style="font-size: 15px; font-weight: 700; color: #fff;">
              <i class="fas fa-clipboard-check" style="color: #facc15; margin-right: 6px;"></i>Missed Call Action Taken
            </div>
            <div style="font-size: 12px; color: #94a3b8; margin-top: 2px;">
              ${this.escapeHtml(this.actionModalCustomerName)} (${this.maskPhone(this.actionModalPhone)})
            </div>
          </div>
          <button id="closeBottomSheetBtn" style="background: rgba(255,255,255,0.08); border: none; color: #cbd5e1; width: 32px; height: 32px; border-radius: 50%; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center;">
            ✕
          </button>
        </div>

        <div style="margin-bottom: 14px;">
          <label style="display: block; font-size: 11.5px; font-weight: 600; color: #94a3b8; margin-bottom: 6px;">
            Resolution Note (Describe action taken with customer):
          </label>
          <textarea 
            id="actionTakenNoteInput" 
            rows="3" 
            placeholder="e.g. Called customer back via mobile SIM, shared brochure on WhatsApp, scheduled site visit."
            style="width: 100%; background: #1e293b; border: 1px solid rgba(255,255,255,0.15); border-radius: 10px; color: #fff; padding: 10px; font-size: 12.5px; outline: none; box-sizing: border-box;"
          >${this.actionModalNotes}</textarea>
        </div>

        <button 
          id="submitActionTakenBtn" 
          style="width: 100%; padding: 12px; border-radius: 12px; background: linear-gradient(135deg, #f59e0b, #d97706); border: none; color: #000; font-size: 13.5px; font-weight: 800; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px;"
          ${this.isSubmittingAction ? 'disabled' : ''}
        >
          ${this.isSubmittingAction ? '<i class="fas fa-spinner fa-spin"></i> Saving...' : '<i class="fas fa-check"></i> Save Action Taken'}
        </button>
      </div>
    `;
  }

  // ──────────────────────────── 6. PAGINATION RENDERER ────────────────────────────

  private renderPaginationHtml(total: number, pageSize: number, currentPage: number, context: 'scope' | 'contacts'): string {
    const totalPages = Math.ceil(total / pageSize);
    if (totalPages <= 1) return '';

    const startIdx = (currentPage - 1) * pageSize + 1;
    const endIdx = Math.min(currentPage * pageSize, total);

    return `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; font-size: 11px; color: #94a3b8;">
        <span>Showing ${startIdx}–${endIdx} of ${total}</span>
        <div style="display: flex; gap: 4px;">
          <button class="pag-btn" data-context="${context}" data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled style="opacity: 0.4; cursor: not-allowed;"' : 'style="cursor: pointer;"'}>
            ‹
          </button>
          <span style="padding: 4px 8px; font-weight: 700; color: #fff;">${currentPage} / ${totalPages}</span>
          <button class="pag-btn" data-context="${context}" data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled style="opacity: 0.4; cursor: not-allowed;"' : 'style="cursor: pointer;"'}>
            ›
          </button>
        </div>
      </div>
    `;
  }

  // ──────────────────────────── EVENT LISTENERS ────────────────────────────

  private attachListeners(): void {
    // 1. Scope Navigation Bar Buttons
    this.container.querySelectorAll('.scope-nav-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const scope = (target.dataset.scope || 'dialer') as SoftphoneScope;
        this.activeScope = scope;
        this.render();

        if (scope === 'dialer') {
          this.loadRecent20Calls();
          this.loadTodayMetrics();
        } else if (scope === 'contacts') {
          this.loadContacts(1);
        } else {
          this.loadScopeCalls(1);
          if (scope === 'team' || scope === 'overall') {
            if (this.teamMembers.length === 0) this.loadTeamMembers();
          }
        }
      });
    });

    // 2. Header Agent Status select
    document.getElementById('softphoneStatusSelect')?.addEventListener('change', (e) => {
      this.agentStatus = (e.target as HTMLSelectElement).value as any;
      this.render();
    });

    // 3. Header Refresh button
    document.getElementById('softphoneRefreshBtn')?.addEventListener('click', () => {
      this.loadTodayMetrics();
      if (this.activeScope === 'dialer') this.loadRecent20Calls();
      else if (this.activeScope === 'contacts') this.loadContacts(this.contactsPage);
      else this.loadScopeCalls(this.scopeCurrentPage);
    });

    // 4. Keypad Buttons
    this.container.querySelectorAll('.dialpad-key-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const digit = (btn as HTMLElement).dataset.digit;
        if (digit) this.pressKey(digit);
      });
    });

    // 5. Dialpad Clear All & Backspace
    document.getElementById('softphoneClearAllBtn')?.addEventListener('click', () => this.clearNumber());
    document.getElementById('softphoneClearBtn')?.addEventListener('click', () => this.backspace());

    // 6. Manual dial input change
    const dialInput = document.getElementById('softphoneDialInput') as HTMLInputElement;
    dialInput?.addEventListener('input', () => {
      this.dialNumber = dialInput.value;
      this.selectedContactName = '';
      this.updateDialDisplay();
    });

    // 7. Call Initiation Buttons
    document.getElementById('softphoneStartCallBtn')?.addEventListener('click', () => this.startCall());
    document.getElementById('softphoneDirectSimBtn')?.addEventListener('click', () => this.startCall(undefined, undefined, true));

    // 8. Recent Calls Quick Search
    const recentSearchInput = document.getElementById('recentCallsSearchInput') as HTMLInputElement;
    recentSearchInput?.addEventListener('input', () => {
      this.recentSearchQuery = recentSearchInput.value;
      this.renderRecent20List();
    });
    document.getElementById('clearRecentSearchBtn')?.addEventListener('click', () => {
      this.recentSearchQuery = '';
      this.renderRecent20List();
    });

    // 9. Scope Filter Bar Events (for history scopes)
    const scopeSearch = document.getElementById('scopeSearchInput') as HTMLInputElement;
    scopeSearch?.addEventListener('input', () => {
      this.scopeFilterSearch = scopeSearch.value;
      if (this.contactsDebounceTimer) clearTimeout(this.contactsDebounceTimer);
      this.contactsDebounceTimer = setTimeout(() => {
        this.loadScopeCalls(1);
      }, 300);
    });
    document.getElementById('clearScopeSearchBtn')?.addEventListener('click', () => {
      this.scopeFilterSearch = '';
      this.loadScopeCalls(1);
    });

    this.container.querySelectorAll('.date-preset-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        this.scopeDatePreset = (target.dataset.preset || '7DAYS') as DatePreset;
        this.render();
        if (this.scopeDatePreset !== 'CUSTOM') {
          this.loadScopeCalls(1);
        }
      });
    });

    document.getElementById('applyScopeCustomDateBtn')?.addEventListener('click', () => {
      const sInput = document.getElementById('scopeCustomStartInput') as HTMLInputElement;
      const eInput = document.getElementById('scopeCustomEndInput') as HTMLInputElement;
      if (sInput) this.customStartDate = sInput.value;
      if (eInput) this.customEndDate = eInput.value;
      this.loadScopeCalls(1);
    });

    document.getElementById('scopeTypeSelect')?.addEventListener('change', (e) => {
      this.scopeFilterType = (e.target as HTMLSelectElement).value;
      this.loadScopeCalls(1);
    });

    document.getElementById('scopeSortSelect')?.addEventListener('change', (e) => {
      this.scopeFilterSort = (e.target as HTMLSelectElement).value;
      this.loadScopeCalls(1);
    });

    document.getElementById('scopeChannelSelect')?.addEventListener('change', (e) => {
      this.scopeFilterChannel = (e.target as HTMLSelectElement).value;
      this.loadScopeCalls(1);
    });

    document.getElementById('scopeLeadScopeSelect')?.addEventListener('change', (e) => {
      this.scopeFilterLeadScope = (e.target as HTMLSelectElement).value;
      this.loadScopeCalls(1);
    });

    document.getElementById('scopeTeamSelect')?.addEventListener('change', (e) => {
      this.scopeFilterTeamMember = (e.target as HTMLSelectElement).value;
      this.loadScopeCalls(1);
    });

    // 10. Contacts Tab Events
    const contactsSearch = document.getElementById('contactsSearchInput') as HTMLInputElement;
    contactsSearch?.addEventListener('input', () => {
      this.contactsSearchQuery = contactsSearch.value;
      if (this.contactsDebounceTimer) clearTimeout(this.contactsDebounceTimer);
      this.contactsDebounceTimer = setTimeout(() => {
        this.loadContacts(1);
      }, 300);
    });
    document.getElementById('clearContactsSearchBtn')?.addEventListener('click', () => {
      this.contactsSearchQuery = '';
      this.loadContacts(1);
    });

    this.container.querySelectorAll('.contacts-source-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        this.contactsSourceType = (target.dataset.source || 'all') as ContactSourceType;
        this.render();
        this.loadContacts(1);
      });
    });

    // 11. In-Call Events
    document.getElementById('softphoneAnswerCallBtn')?.addEventListener('click', () => telephonyService.answerIncomingCall());
    document.getElementById('softphoneRejectCallBtn')?.addEventListener('click', () => telephonyService.rejectIncomingCall());
    document.getElementById('softphoneEndCallBtn')?.addEventListener('click', () => this.endCall());
    document.getElementById('callMuteBtn')?.addEventListener('click', () => this.toggleMute());
    document.getElementById('callSpeakerBtn')?.addEventListener('click', () => this.toggleSpeaker());
    document.getElementById('callHoldBtn')?.addEventListener('click', () => this.toggleHold());
    document.getElementById('inCallDTMFToggleBtn')?.addEventListener('click', () => {
      this.showInCallDTMF = !this.showInCallDTMF;
      this.render();
    });

    this.container.querySelectorAll('.in-call-dtmf-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const digit = (btn as HTMLElement).dataset.digit;
        if (digit) this.sendInCallDTMF(digit);
      });
    });

    this.attachCallCardListeners();
    this.attachContactCardListeners();
    this.attachPaginationListeners();
  }

  private attachCallCardListeners(): void {
    // Redial call button
    this.container.querySelectorAll('.call-action-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const phone = (btn as HTMLElement).dataset.phone;
        const name = (btn as HTMLElement).dataset.name;
        if (phone) this.startCall(phone, name);
      });
    });

    // Customer timeline trigger button & customer name click
    this.container.querySelectorAll('.customer-history-trigger, .customer-history-trigger-btn').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = el as HTMLElement;
        const phone = target.dataset.phone || '';
        const name = target.dataset.name || 'Customer';
        if (phone) this.openCustomerHistory(phone, name);
      });
    });

    // Audio Play / Pause Trigger
    this.container.querySelectorAll('.audio-play-trigger-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = btn as HTMLElement;
        const key = target.dataset.audioKey || '';
        const streamUrl = target.dataset.streamUrl || '';
        if (key && streamUrl) {
          this.toggleAudioPlayback(key, streamUrl);
        }
      });
    });

    // Action Taken Open Modal Button
    this.container.querySelectorAll('.action-taken-open-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = btn as HTMLElement;
        const sessionId = target.dataset.sessionId || '';
        const phone = target.dataset.phone || '';
        const name = target.dataset.name || 'Customer';
        if (sessionId) {
          this.openActionTakenModal(sessionId, phone, name);
        }
      });
    });
  }

  private attachContactCardListeners(): void {
    this.attachCallCardListeners();
  }

  private attachPaginationListeners(): void {
    this.container.querySelectorAll('.pag-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const target = btn as HTMLElement;
        const context = target.dataset.context;
        const page = parseInt(target.dataset.page || '1', 10);
        if (page > 0) {
          if (context === 'contacts') {
            this.loadContacts(page);
          } else {
            this.loadScopeCalls(page);
          }
        }
      });
    });
  }

  private async openQuickStaffVerificationSheet(leadId: string, autoDial: boolean = false): Promise<void> {
    this.selectedLeadId = leadId;
    this.pendingAutoDialAfterVerify = autoDial;
    this.activeBottomSheet = 'quick_staff_verify';
    this.quickStaffEmpCode = '';
    this.quickStaffPersistence = 'always';
    this.quickStaffError = '';
    this.isVerifyingStaff = false;
    this.renderBottomSheet();

    try {
      const resp = await apiService.get<any>(`/telephony/plivo/public-lead-preview?lead_id=${leadId}`);
      const payload = resp?.data || resp;
      if (payload && (payload.success || payload.lead_id)) {
        this.quickStaffLeadPreview = payload;
        if (this.activeBottomSheet === 'quick_staff_verify') {
          this.renderBottomSheet();
        }
      }
    } catch (err) {
      console.warn('[SoftphonePage] Could not load public lead preview:', err);
    }
  }

  private renderQuickStaffVerifySheetHtml(): string {
    const preview = this.quickStaffLeadPreview;
    const custName = this.escapeHtml(preview?.name || 'Customer Lead');
    const maskedPhone = this.escapeHtml(preview?.masked_phone || '+91 ***** *****');
    const location = this.escapeHtml(preview?.location || '—');
    const service = this.escapeHtml(preview?.service || 'CRM Lead');
    const company = this.escapeHtml(preview?.company_name || 'MyntReal');

    return `
      <!-- Backdrop Overlay -->
      <div id="bottomSheetBackdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 999; backdrop-filter: blur(4px);"></div>

      <!-- Slide-Up Drawer -->
      <div style="position: fixed; bottom: 0; left: 0; right: 0; max-height: 90vh; overflow-y: auto; background: #0f172a; border-top-left-radius: 24px; border-top-right-radius: 24px; z-index: 1000; box-shadow: 0 -10px 40px rgba(0,0,0,0.8); border-top: 1px solid rgba(255,255,255,0.15); padding: 20px 18px 28px;">
        
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width: 40px; height: 40px; border-radius: 12px; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); display: flex; align-items: center; justify-content: center; color: #10b981; font-size: 18px;">
              <i class="fas fa-id-badge"></i>
            </div>
            <div>
              <div style="font-size: 16px; font-weight: 700; color: #f8fafc;">Staff Verification</div>
              <div style="font-size: 11px; color: #94a3b8; margin-top: 1px;">Enter Employee ID to connect CRM lead call</div>
            </div>
          </div>
          <button id="closeBottomSheetBtn" style="background: rgba(255,255,255,0.08); border: none; color: #94a3b8; width: 32px; height: 32px; border-radius: 50%; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center;">
            ✕
          </button>
        </div>

        <!-- Lead Preview Card -->
        <div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.95)); border: 1px solid rgba(255,255,255,0.1); border-radius: 14px; padding: 12px 14px; margin-bottom: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-size: 10px; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; color: #38bdf8;">Lead Call Details</span>
            <span id="qsvCompBadge" style="font-size: 10px; padding: 2px 8px; border-radius: 6px; background: rgba(99, 102, 241, 0.2); color: #a5b4fc; font-weight: 600;">${company}</span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div id="qsvCustomerName" style="font-size: 14px; font-weight: 700; color: #fff;">${custName}</div>
              <div id="qsvMaskedPhone" style="font-size: 12px; font-family: monospace; color: #cbd5e1; margin-top: 2px;">${maskedPhone}</div>
            </div>
            <div style="text-align: right;">
              <div id="qsvService" style="font-size: 11px; color: #facc15; font-weight: 600;">${service}</div>
              <div id="qsvLocation" style="font-size: 11px; color: #64748b; margin-top: 2px;">${location}</div>
            </div>
          </div>
        </div>

        <!-- Employee ID Input -->
        <div style="margin-bottom: 14px;">
          <label style="display: block; font-size: 11.5px; font-weight: 600; color: #cbd5e1; margin-bottom: 6px;">
            Employee Code / Staff ID:
          </label>
          <div style="position: relative;">
            <i class="fas fa-user-tag" style="position: absolute; left: 12px; top: 12px; color: #64748b; font-size: 13px;"></i>
            <input 
              type="text" 
              id="quickStaffEmpInput" 
              placeholder="e.g. MR10012 or MN10017" 
              value="${this.escapeAttr(this.quickStaffEmpCode)}"
              autocapitalize="characters"
              style="width: 100%; background: #1e293b; border: 1px solid rgba(255,255,255,0.15); border-radius: 10px; color: #fff; padding: 10px 12px 10px 34px; font-size: 13px; font-weight: 600; letter-spacing: 0.5px; outline: none; box-sizing: border-box;"
            />
          </div>
        </div>

        <!-- Device Persistence Options (One Time vs Always) -->
        <div style="margin-bottom: 16px;">
          <label style="display: block; font-size: 11.5px; font-weight: 600; color: #cbd5e1; margin-bottom: 8px;">
            Login Persistence:
          </label>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <label style="display: flex; align-items: flex-start; gap: 8px; padding: 10px; border-radius: 10px; background: ${this.quickStaffPersistence === 'always' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(30, 41, 59, 0.6)'}; border: 1px solid ${this.quickStaffPersistence === 'always' ? 'rgba(16, 185, 129, 0.4)' : 'rgba(255, 255, 255, 0.1)'}; cursor: pointer;">
              <input type="radio" name="mobileQsvPersistence" value="always" ${this.quickStaffPersistence === 'always' ? 'checked' : ''} style="margin-top: 2px; accent-color: #10b981;" />
              <div>
                <div style="font-size: 12px; font-weight: 700; color: #fff;">Always</div>
                <div style="font-size: 10px; color: #94a3b8; line-height: 1.2; margin-top: 2px;">Remember on device</div>
              </div>
            </label>
            <label style="display: flex; align-items: flex-start; gap: 8px; padding: 10px; border-radius: 10px; background: ${this.quickStaffPersistence === 'one_time' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(30, 41, 59, 0.6)'}; border: 1px solid ${this.quickStaffPersistence === 'one_time' ? 'rgba(16, 185, 129, 0.4)' : 'rgba(255, 255, 255, 0.1)'}; cursor: pointer;">
              <input type="radio" name="mobileQsvPersistence" value="one_time" ${this.quickStaffPersistence === 'one_time' ? 'checked' : ''} style="margin-top: 2px; accent-color: #10b981;" />
              <div>
                <div style="font-size: 12px; font-weight: 700; color: #fff;">One-Time</div>
                <div style="font-size: 10px; color: #94a3b8; line-height: 1.2; margin-top: 2px;">Current session only</div>
              </div>
            </label>
          </div>
        </div>

        <!-- Error Alert -->
        <div id="quickStaffErrorAlert" style="display: ${this.quickStaffError ? 'block' : 'none'}; padding: 10px 12px; border-radius: 10px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; font-size: 12px; margin-bottom: 14px;">
          <i class="fas fa-exclamation-circle" style="margin-right: 4px;"></i>${this.escapeHtml(this.quickStaffError)}
        </div>

        <!-- Action Button -->
        <button 
          id="submitQuickStaffBtn" 
          style="width: 100%; padding: 13px; border-radius: 12px; background: linear-gradient(135deg, #10b981, #059669); border: none; color: #fff; font-size: 14px; font-weight: 700; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; box-shadow: 0 4px 14px rgba(16, 185, 129, 0.4);"
          ${this.isVerifyingStaff ? 'disabled' : ''}
        >
          ${this.isVerifyingStaff ? '<i class="fas fa-spinner fa-spin"></i> Verifying & Connecting...' : '<i class="fas fa-phone-volume"></i> Verify & Connect Call Now'}
        </button>

        <!-- Footer Notice -->
        <div style="text-align: center; margin-top: 12px; font-size: 11px; color: #64748b;">
          Calls are automatically tagged with your Staff ID and recorded.
        </div>
      </div>
    `;
  }

  private async submitQuickStaffVerification(): Promise<void> {
    const empCode = (this.quickStaffEmpCode || '').trim().toUpperCase();
    if (!empCode) {
      this.quickStaffError = 'Please enter your Employee ID (e.g. MR10012 or MN10017).';
      this.renderBottomSheet();
      return;
    }

    this.isVerifyingStaff = true;
    this.quickStaffError = '';
    this.renderBottomSheet();

    try {
      const resp = await apiService.post<any>('/telephony/plivo/quick-dial/verify-staff', {
        emp_code: empCode,
        lead_id: this.selectedLeadId,
        persistence: this.quickStaffPersistence
      });

      const data = resp?.data || resp;
      if (!data || !data.success) {
        throw new Error(data?.detail || data?.error || 'Employee verification failed. Please check Employee ID.');
      }

      // 1. Store token & auth state via quickStaffLogin
      await authService.quickStaffLogin(data.access_token, data.employee, this.quickStaffPersistence);

      // 2. Pre-warm and register Plivo WebRTC singleton
      await telephonyService.initPlivoWebRTC();

      // 3. Extract lead details
      const targetPhone = data.lead?.phone || '';
      const targetName = data.lead?.name || 'Contact Lead';
      const cleanDigits = String(targetPhone).replace(/\D/g, '').slice(-10);

      this.activeBottomSheet = null;
      this.customerHistoryData = null;
      this.quickStaffLeadPreview = null;

      // 4. Update dialer state
      if (cleanDigits) {
        this.dialNumber = cleanDigits;
        this.selectedContactName = targetName;
      }
      this.activeScope = 'dialer';
      this.render();

      // 5. Background data loads
      this.loadTodayMetrics();
      this.loadRecent20Calls();

      // 6. Connect call automatically if destination phone is ready
      if (cleanDigits) {
        setTimeout(() => {
          this.startCall(cleanDigits, targetName);
        }, 500);
      }
    } catch (err: any) {
      console.error('[SoftphonePage] Quick verification error:', err);
      this.isVerifyingStaff = false;
      this.quickStaffError = err?.message || 'Verification failed. Please check Employee ID.';
      this.renderBottomSheet();
    }
  }

  private attachBottomSheetListeners(): void {
    document.getElementById('bottomSheetBackdrop')?.addEventListener('click', () => this.closeBottomSheet());
    document.getElementById('closeBottomSheetBtn')?.addEventListener('click', () => this.closeBottomSheet());

    if (this.activeBottomSheet === 'quick_staff_verify') {
      const empInput = document.getElementById('quickStaffEmpInput') as HTMLInputElement;
      if (empInput) {
        empInput.addEventListener('input', () => {
          this.quickStaffEmpCode = empInput.value;
        });
        empInput.addEventListener('keydown', (ev) => {
          if (ev.key === 'Enter') {
            ev.preventDefault();
            this.submitQuickStaffVerification();
          }
        });
        setTimeout(() => empInput.focus(), 150);
      }

      const radios = document.querySelectorAll<HTMLInputElement>('input[name="mobileQsvPersistence"]');
      radios.forEach(radio => {
        radio.addEventListener('change', () => {
          if (radio.checked) {
            this.quickStaffPersistence = radio.value as 'always' | 'one_time';
          }
        });
      });

      document.getElementById('submitQuickStaffBtn')?.addEventListener('click', () => this.submitQuickStaffVerification());
      return;
    }

    const noteInput = document.getElementById('actionTakenNoteInput') as HTMLTextAreaElement;
    noteInput?.addEventListener('input', () => {
      this.actionModalNotes = noteInput.value;
    });

    document.getElementById('submitActionTakenBtn')?.addEventListener('click', () => this.submitActionTaken());

    // Inside bottom sheet customer timeline: Audio play triggers & Call button
    const container = document.getElementById('softphoneBottomSheetContainer');
    if (container) {
      container.querySelectorAll('.audio-play-trigger-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const target = btn as HTMLElement;
          const key = target.dataset.audioKey || '';
          const streamUrl = target.dataset.streamUrl || '';
          if (key && streamUrl) {
            this.toggleAudioPlayback(key, streamUrl);
          }
        });
      });

      container.querySelectorAll('.call-action-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const phone = (btn as HTMLElement).dataset.phone;
          const name = (btn as HTMLElement).dataset.name;
          if (phone) {
            this.closeBottomSheet();
            this.startCall(phone, name);
          }
        });
      });
    }
  }
}
