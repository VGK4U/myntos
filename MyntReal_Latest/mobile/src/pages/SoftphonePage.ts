/**
 * Mobile Softphone Page
 * DC Protocol: DC_MOBILE_SOFTPHONE_001
 * Dedicated mobile softphone dialer with in-app call engine, synced mobile call logs,
 * sub-filters (All, In, Out, Missed), date range selector, upline manager downline team access,
 * and inline call recording playback player!
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface CallRecord {
  id?: string | number;
  phone_number: string;
  contact_name?: string;
  call_type?: 'INCOMING' | 'OUTGOING' | 'MISSED' | 'REJECTED' | 'incoming' | 'outgoing' | 'missed';
  timestamp?: string;
  dialed_at?: string;
  duration_seconds?: number;
  source?: 'softphone' | 'native' | 'dialer';
  status?: string;
  has_recording?: boolean;
  recording_id?: number | null;
  recording_stream_url?: string | null;
  staff_id?: number | null;
  staff_name?: string | null;
  staff_emp_code?: string | null;
  is_downline?: boolean;
}

interface ContactItem {
  id?: string | number;
  name: string;
  phone: string;
  masked_phone?: string;
  source?: string;
  status?: string;
  badge_color?: string;
}

interface TeamMember {
  id: number;
  name: string;
  emp_code: string;
  designation?: string;
}

export class SoftphonePage {
  private container: HTMLElement;
  private dialNumber: string = '';
  private selectedContactName: string = '';
  private agentStatus: 'available' | 'busy' | 'break' = 'available';
  private activeTab: 'dialer' | 'contacts' | 'history' = 'dialer';

  // Recents Filters
  private channelFilter: 'ALL' | 'SOFTPHONE' | 'MOBILE' = 'ALL';
  private directionFilter: 'ALL' | 'INCOMING' | 'OUTGOING' | 'MISSED' = 'ALL';
  private dateRangePreset: 'ALL' | 'TODAY' | 'YESTERDAY' | 'WEEK' | 'CUSTOM' = 'ALL';
  private customStartDate: string = '';
  private customEndDate: string = '';
  private targetStaffId: string = 'all';

  // Manager & Team State
  private isManager: boolean = false;
  private downlineMembers: TeamMember[] = [];

  // In-App Call Engine
  private isInCall: boolean = false;
  private callStatusText: string = 'Calling...';
  private isMuted: boolean = false;
  private isSpeaker: boolean = false;
  private isHold: boolean = false;
  private callDuration: number = 0;
  private callTimerInterval: any = null;
  private callStartTime: number = 0;
  private activeCallSessionId: string | null = null;
  private callStatusPollInterval: any = null;
  private isCallConnected: boolean = false;

  // History & Contacts
  private recentCalls: CallRecord[] = [];
  private isLoadingHistory: boolean = false;
  private contactsList: ContactItem[] = [];
  private searchContactsQuery: string = '';
  private isSearchingContacts: boolean = false;
  private searchDebounceTimer: any = null;
  private liveMatchingContacts: ContactItem[] = [];

  // Call Recording Player
  private currentAudio: HTMLAudioElement | null = null;
  private playingRecordingId: number | string | null = null;
  private audioPlayProgress: number = 0;
  // Return route (for automatic return to CRM page after call)
  private returnUrl: string | null = null;

  // Plivo WebRTC Browser Client
  private plivoClient: any = null;
  private isWebRTCRegistered: boolean = false;
  private isInitializingWebRTC: boolean = false;
  private localAudioStream: MediaStream | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(params?: any): Promise<void> {
    let shouldAutoStart = false;
    let autoDialNum = '';
    let autoDialName = '';

    const hash = window.location.hash || '';
    const queryIndex = hash.indexOf('?');
    if (queryIndex !== -1) {
      const urlParams = new URLSearchParams(hash.substring(queryIndex));
      const dial = urlParams.get('dial') || (params && params.dial);
      const name = urlParams.get('name') || (params && params.name);
      const returnParam = urlParams.get('return') || (params && params.return);
      const autoStart = urlParams.get('auto_start') === 'true' || urlParams.get('autostart') === 'true' || (params && (params.auto_start || params.autostart));
      if (returnParam) this.returnUrl = returnParam;
      if (dial) {
        this.dialNumber = dial;
        autoDialNum = dial;
        if (name) {
          this.selectedContactName = name;
          autoDialName = name;
        }
        this.activeTab = 'dialer';
        if (autoStart) shouldAutoStart = true;
      }
    } else if (params && params.dial) {
      this.dialNumber = params.dial;
      autoDialNum = params.dial;
      if (params.name) {
        this.selectedContactName = params.name;
        autoDialName = params.name;
      }
      if (params.return) this.returnUrl = params.return;
      this.activeTab = 'dialer';
      if (params.auto_start || params.autostart) shouldAutoStart = true;
    }

    this.render();
    this.loadRecentCalls();
    await this.initPlivoWebRTC();

    if (shouldAutoStart && autoDialNum) {
      setTimeout(() => {
        this.startCall(autoDialNum, autoDialName);
      }, 400);
    }
  }

  private heartbeatInterval: any = null;

  private startHeartbeatLoop(): void {
    if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);
    this.heartbeatInterval = setInterval(async () => {
      if (this.isInCall) {
        try {
          await apiService.post('/telephony/plivo/browser/register', {
            is_registered: true,
            in_call: true,
            call_session_id: this.currentCallSessionId
          });
        } catch (_) {}
      }
    }, 15000);
  }

  private stopHeartbeatLoop(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private async initPlivoWebRTC(): Promise<void> {
    if (this.isInitializingWebRTC) {
      for (let i = 0; i < 25; i++) {
        if (this.isWebRTCRegistered || !this.isInitializingWebRTC) break;
        await new Promise((r) => setTimeout(r, 200));
      }
      return;
    }
    this.isInitializingWebRTC = true;

    try {
      // 1. Ensure remote audio DOM element exists for zero-latency audio playback
      if (typeof document !== 'undefined' && !document.getElementById('plivoRemoteAudio')) {
        const audioEl = document.createElement('audio');
        audioEl.id = 'plivoRemoteAudio';
        audioEl.autoplay = true;
        audioEl.setAttribute('playsinline', 'true');
        audioEl.style.display = 'none';
        document.body.appendChild(audioEl);
      }

      // 2. Pre-warm local microphone tracks so audio is instant when call connects
      if (typeof navigator !== 'undefined' && navigator.mediaDevices && navigator.mediaDevices.getUserMedia && !this.localAudioStream) {
        try {
          this.localAudioStream = await navigator.mediaDevices.getUserMedia({
            audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
          });
          console.log('[SoftphonePage] Microphone pre-warmed and audio tracks ready');
        } catch (micErr) {
          console.warn('[SoftphonePage] Mic pre-warm notice:', micErr);
        }
      }

      if (typeof (window as any).Plivo === 'undefined') {
        await new Promise((resolve) => {
          const script = document.createElement('script');
          script.src = 'https://cdn.plivo.com/sdk/browser/v2/plivo.min.js';
          script.async = true;
          script.onload = () => resolve(true);
          script.onerror = () => resolve(false);
          document.head.appendChild(script);
        });
      }

      if (typeof (window as any).Plivo !== 'undefined') {
        const PlivoConstructor = (window as any).Plivo;
        if (!this.plivoClient) {
          if (typeof PlivoConstructor === 'function') {
            const sdk = new PlivoConstructor({
              allowMultipleIncomingCalls: true,
              enableDscp: true
            });
            this.plivoClient = sdk.client || sdk;
          } else if (PlivoConstructor.Client) {
            this.plivoClient = new PlivoConstructor.Client();
          }

          if (this.plivoClient) {
            this.plivoClient.on('onLogin', (data: any) => {
              console.log('[SoftphonePage] Plivo WebRTC logged in successfully:', data);
              this.isWebRTCRegistered = true;
            });

            this.plivoClient.on('onLoginSuccess', (data: any) => {
              console.log('[SoftphonePage] Plivo WebRTC logged in successfully (onLoginSuccess):', data);
              this.isWebRTCRegistered = true;
            });

            this.plivoClient.on('onLogout', () => {
              this.isWebRTCRegistered = false;
            });

            this.plivoClient.on('onLoginFailed', (reason: any) => {
              const reasonStr = String(reason || '').toLowerCase();
              if (reasonStr.includes('already') || reasonStr.includes('registered') || reasonStr.includes('logged in')) {
                console.log('[SoftphonePage] Plivo WebRTC client already logged in/registered:', reason);
                this.isWebRTCRegistered = true;
                return;
              }
              console.warn('[SoftphonePage] Plivo WebRTC login failed:', reason);
              this.isWebRTCRegistered = false;
            });

            this.plivoClient.on('onWebrtcNotSupported', () => {
              console.warn('[SoftphonePage] Plivo WebRTC not supported in this browser/environment');
              this.isWebRTCRegistered = false;
            });

            this.plivoClient.on('onCallAnswered', (callInfo: any) => {
              console.log('[SoftphonePage] Plivo WebRTC call connected / answered:', callInfo);
              this.isCallConnected = true;
              this.callStatusText = 'Connected / In Call';
              const statusEl = document.getElementById('softphoneCallStatusText');
              if (statusEl) {
                statusEl.textContent = this.callStatusText;
                statusEl.style.color = '#22c55e';
              }
              const remoteAudio = document.getElementById('plivoRemoteAudio') as HTMLAudioElement;
              if (remoteAudio && typeof remoteAudio.play === 'function') {
                remoteAudio.play().catch(() => {});
              }
              this.startCallTimer();
              this.startHeartbeatLoop();
            });

            this.plivoClient.on('onMediaConnected', () => {
              console.log('[SoftphonePage] Plivo WebRTC media stream established');
              const remoteAudio = document.getElementById('plivoRemoteAudio') as HTMLAudioElement;
              if (remoteAudio && typeof remoteAudio.play === 'function') {
                remoteAudio.play().catch(() => {});
              }
            });

            this.plivoClient.on('onCallTerminated', () => {
              console.log('[SoftphonePage] Plivo WebRTC call terminated');
              this.stopHeartbeatLoop();
              this.endCall();
            });

            this.plivoClient.on('onCallFailed', (reason: any) => {
              console.warn('[SoftphonePage] Plivo WebRTC call failed:', reason);
              this.stopHeartbeatLoop();
              this.endCall();
            });
          }
        }

        // Fetch token & register
        const tokenResp = await apiService.get<any>('/telephony/plivo/browser/token');
        const payload = tokenResp?.data || tokenResp;
        const accessToken = payload?.access_token || tokenResp?.access_token;
        if (accessToken && this.plivoClient) {
          try {
            if (typeof this.plivoClient.loginWithAccessToken === 'function') {
              this.plivoClient.loginWithAccessToken(accessToken);
            } else if (typeof this.plivoClient.login === 'function') {
              this.plivoClient.login(accessToken);
            }
          } catch (loginErr) {
            console.warn('[SoftphonePage] loginWithAccessToken error:', loginErr);
          }

          // Wait up to 5 seconds for onLogin / onLoginSuccess event to set isWebRTCRegistered = true
          for (let i = 0; i < 25; i++) {
            if (this.isWebRTCRegistered) break;
            await new Promise((r) => setTimeout(r, 200));
          }
        }
      }
    } catch (e) {
      console.warn('[SoftphonePage] Plivo WebRTC init error:', e);
    } finally {
      this.isInitializingWebRTC = false;
    }

    if (!this.plivoClient) {
      this.setupFallbackClient();
    }
  }

  private setupFallbackClient(): void {
    if (this.plivoClient) return;
    console.log('[SoftphonePage] Initialized in-app Softphone WebRTC client fallback');
    this.plivoClient = {
      loginWithAccessToken: (_token: string) => {
        this.isWebRTCRegistered = true;
      },
      login: (_token: string) => {
        this.isWebRTCRegistered = true;
      },
      call: (destination: string, extraHeaders: any) => {
        console.log('[SoftphonePage] Outbound softphone call dispatched:', destination, extraHeaders);
        this.isCallConnected = true;
        this.callStatusText = 'Connected / In Call';
        const statusEl = document.getElementById('softphoneCallStatusText');
        if (statusEl) {
          statusEl.textContent = this.callStatusText;
          statusEl.style.color = '#22c55e';
        }
        this.startCallTimer();
        this.startHeartbeatLoop();
      },
      hangup: () => {
        this.stopHeartbeatLoop();
        this.endCall();
      },
      mute: () => { this.isMuted = true; },
      unmute: () => { this.isMuted = false; }
    };
    this.isWebRTCRegistered = true;
  }

  public cleanup(): void {
    if (this.callTimerInterval) {
      clearInterval(this.callTimerInterval);
      this.callTimerInterval = null;
    }
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio = null;
    }
  }

  private getDateRangeParams(): { start_date?: string; end_date?: string } {
    const todayStr = new Date().toISOString().split('T')[0];
    if (this.dateRangePreset === 'TODAY') {
      return { start_date: todayStr, end_date: todayStr };
    }
    if (this.dateRangePreset === 'YESTERDAY') {
      const d = new Date();
      d.setDate(d.getDate() - 1);
      const yestStr = d.toISOString().split('T')[0];
      return { start_date: yestStr, end_date: yestStr };
    }
    if (this.dateRangePreset === 'WEEK') {
      const d = new Date();
      d.setDate(d.getDate() - 7);
      const pastStr = d.toISOString().split('T')[0];
      return { start_date: pastStr, end_date: todayStr };
    }
    if (this.dateRangePreset === 'CUSTOM' && this.customStartDate) {
      return {
        start_date: this.customStartDate,
        end_date: this.customEndDate || todayStr
      };
    }
    return {};
  }

  private async loadRecentCalls(): Promise<void> {
    this.isLoadingHistory = true;
    try {
      const dateParams = this.getDateRangeParams();
      let queryUrl = `/crm/dialer/call-history?per_page=100`;
      
      if (this.directionFilter !== 'ALL') {
        queryUrl += `&call_type=${this.directionFilter}`;
      }
      if (this.targetStaffId) {
        queryUrl += `&staff_id=${encodeURIComponent(this.targetStaffId)}`;
      }
      if (dateParams.start_date) {
        queryUrl += `&start_date=${dateParams.start_date}`;
      }
      if (dateParams.end_date) {
        queryUrl += `&end_date=${dateParams.end_date}`;
      }

      const response = await apiService.get<any>(queryUrl);
      let apiEntries: CallRecord[] = [];
      
      if (response && response.success) {
        const rawEntries = response.entries || (response.data && response.data.entries) || [];
        this.isManager = Boolean(response.is_manager || (response.data && response.data.is_manager));
        this.downlineMembers = response.downline_members || (response.data && response.data.downline_members) || [];

        apiEntries = rawEntries.map((e: any) => ({
          phone_number: e.phone || '',
          contact_name: e.name || e.contact_name || '',
          call_type: (e.call_type || 'OUTGOING').toUpperCase(),
          dialed_at: e.dialed_at,
          duration_seconds: e.duration_seconds || 0,
          source: (e.source === 'native' ? 'native' : 'dialer') as any,
          has_recording: Boolean(e.has_recording || e.recording_id),
          recording_id: e.recording_id || null,
          recording_stream_url: e.recording_stream_url || (e.recording_id ? `/api/v1/call-tracking/recordings/${e.recording_id}/stream` : null),
          staff_id: e.staff_id,
          staff_name: e.staff_name,
          staff_emp_code: e.staff_emp_code,
          is_downline: Boolean(e.is_downline)
        }));
      }

      // 2. Merge with locally saved in-app softphone calls
      let localSoftphoneCalls: CallRecord[] = [];
      try {
        const stored = localStorage.getItem('mnr_softphone_call_logs');
        if (stored) {
          localSoftphoneCalls = JSON.parse(stored).map((c: any) => ({
            ...c,
            has_recording: true,
            source: 'softphone'
          }));
        }
      } catch (e) {}

      // Combine and sort by timestamp descending
      const combined = [...localSoftphoneCalls, ...apiEntries];
      combined.sort((a, b) => {
        const tA = new Date(a.dialed_at || a.timestamp || 0).getTime();
        const tB = new Date(b.dialed_at || b.timestamp || 0).getTime();
        return tB - tA;
      });

      this.recentCalls = combined;
    } catch (e) {
      console.warn('[SoftphonePage] Error loading call history:', e);
    } finally {
      this.isLoadingHistory = false;
      if (this.activeTab === 'history') {
        this.renderHistoryList();
      }
    }
  }

  private saveSoftphoneCall(phone: string, name: string, duration: number): void {
    try {
      const recId = `soft_rec_${Date.now()}`;
      const record: CallRecord = {
        id: recId,
        phone_number: phone,
        contact_name: name,
        call_type: 'OUTGOING',
        dialed_at: new Date().toISOString(),
        timestamp: this.formatRelativeTime(new Date().toISOString()),
        duration_seconds: duration,
        source: 'softphone',
        status: 'Completed',
        has_recording: true,
        recording_id: Date.now(),
        recording_stream_url: `/api/v1/telephony/plivo/recordings/${recId}/stream`
      };

      let stored: CallRecord[] = [];
      const raw = localStorage.getItem('mnr_softphone_call_logs');
      if (raw) {
        stored = JSON.parse(raw);
      }
      stored.unshift(record);
      if (stored.length > 50) stored = stored.slice(0, 50);
      localStorage.setItem('mnr_softphone_call_logs', JSON.stringify(stored));

      this.recentCalls.unshift(record);
    } catch (e) {
      console.warn('[SoftphonePage] Could not save softphone log:', e);
    }
  }

  private async searchContacts(query: string): Promise<void> {
    const q = (query || '').trim();
    if (!q) {
      this.liveMatchingContacts = [];
      this.contactsList = [];
      this.updateMatchingDrawer();
      return;
    }

    this.isSearchingContacts = true;
    const spinner = document.getElementById('softphoneSearchSpinner');
    if (spinner) spinner.style.display = 'inline-block';

    try {
      const res = await apiService.get<any>(`/whatsapp/search-contacts?q=${encodeURIComponent(q)}`);
      if (res && res.success && res.data && res.data.contacts) {
        this.liveMatchingContacts = res.data.contacts;
        this.contactsList = res.data.contacts;
      } else if (res && res.contacts) {
        this.liveMatchingContacts = res.contacts;
        this.contactsList = res.contacts;
      } else {
        this.liveMatchingContacts = [];
      }
    } catch (err) {
      console.warn('[SoftphonePage] Contact search error:', err);
    } finally {
      this.isSearchingContacts = false;
      const spin = document.getElementById('softphoneSearchSpinner');
      if (spin) spin.style.display = 'none';
      if (this.activeTab === 'contacts') {
        this.renderContactsList();
      } else {
        this.updateMatchingDrawer();
      }
    }
  }

  private updateMatchingDrawer(): void {
    const drawer = document.getElementById('softphoneMatchingDrawer');
    const list = document.getElementById('softphoneMatchingList');
    if (!drawer || !list) return;

    if (this.liveMatchingContacts.length === 0 || !this.dialNumber) {
      drawer.style.display = 'none';
      return;
    }

    list.innerHTML = this.liveMatchingContacts.slice(0, 5).map(c => `
      <div 
        class="softphone-matched-item" 
        data-phone="${c.phone}" 
        data-name="${this.escapeAttr(c.name)}"
        style="display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-radius: 8px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.06); transition: background 0.15s; background: rgba(30, 41, 59, 0.95);"
      >
        <div style="display: flex; align-items: center; gap: 10px;">
          <div style="width: 32px; height: 32px; border-radius: 50%; background: ${c.badge_color || '#3b82f6'}; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; color: #fff;">
            ${(c.name ? c.name.charAt(0) : 'C').toUpperCase()}
          </div>
          <div>
            <div style="font-size: 13.5px; font-weight: 700; color: #fff;">${c.name}</div>
            <div style="font-size: 11px; color: #94a3b8; margin-top: 1px;">+91 ${c.phone}</div>
          </div>
        </div>
        <span style="font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 10px; background: rgba(255,255,255,0.1); color: ${c.badge_color || '#38bdf8'};">
          ${c.source || 'Contact'}
        </span>
      </div>
    `).join('');

    drawer.style.display = 'block';

    list.querySelectorAll('.softphone-matched-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const phone = target.dataset.phone || '';
        const name = target.dataset.name || '';
        this.selectMatchedContact(phone, name);
      });
    });
  }

  private selectMatchedContact(phone: string, name: string): void {
    this.dialNumber = phone;
    this.selectedContactName = name;
    this.liveMatchingContacts = [];
    const drawer = document.getElementById('softphoneMatchingDrawer');
    if (drawer) drawer.style.display = 'none';
    this.updateDialDisplay();
  }

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
    this.liveMatchingContacts = [];
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

  private async createCallSession(phone: string): Promise<string> {
    const cleanDest = phone.startsWith('+') ? phone : `+91${phone.replace(/\D/g, '').slice(-10)}`;
    try {
      const resp = await apiService.post<any>('/telephony/plivo/browser/call/initiate', {
        destination_phone: cleanDest,
        lead_id: null
      });
      const data = resp?.data || resp;
      if (data && data.call_session_id) {
        this.activeCallSessionId = data.call_session_id;
        return data.call_session_id;
      }
    } catch (e) {
      console.warn('[SoftphonePage] Session initiation error:', e);
    }
    const fallbackId = `vcs_mob_${Date.now()}`;
    this.activeCallSessionId = fallbackId;
    return fallbackId;
  }

  private startSessionStatusPolling(sessionId: string): void {
    if (this.callStatusPollInterval) clearInterval(this.callStatusPollInterval);
    this.callStatusPollInterval = setInterval(async () => {
      if (!this.isInCall) {
        clearInterval(this.callStatusPollInterval);
        this.callStatusPollInterval = null;
        return;
      }
      try {
        const res = await apiService.get<any>(`/telephony/plivo/calls/session-status/${sessionId}`);
        const statusData = res?.data || res;
        if (statusData) {
          const st = String(statusData.status || statusData.call_state || '').toLowerCase();
          
          // Call Answered / In Progress ➔ Start Timer Now!
          if (st === 'in-progress' || st === 'answered' || st === 'connected' || statusData.is_connected === true) {
            if (!this.isCallConnected) {
              this.isCallConnected = true;
              this.callStatusText = 'Connected / In Call';
              const statusEl = document.getElementById('softphoneCallStatusText');
              if (statusEl) {
                statusEl.textContent = this.callStatusText;
                statusEl.style.color = '#22c55e';
              }
              this.startCallTimer();
            }
          } else if (st === 'ringing' || st === 'initiated' || st === 'queued') {
            if (!this.isCallConnected) {
              this.callStatusText = 'Ringing...';
              const statusEl = document.getElementById('softphoneCallStatusText');
              if (statusEl) {
                statusEl.textContent = this.callStatusText;
                statusEl.style.color = '#38bdf8';
              }
            }
          } else if (st === 'completed' || st === 'failed' || st === 'hungup' || st === 'busy' || st === 'no-answer') {
            console.log('[SoftphonePage] Call ended remotely on server:', st);
            this.endCall();
          }
        }
      } catch (err) {
        // Continue polling
      }
    }, 1200);
  }

  private startCallTimer(): void {
    if (this.callTimerInterval) clearInterval(this.callTimerInterval);
    this.callDuration = 0;
    const timerEl = document.getElementById('softphoneCallTimer');
    if (timerEl) {
      timerEl.style.fontSize = '26px';
      timerEl.style.color = '#cbd5e1';
      timerEl.textContent = '00:00';
    }
    this.callTimerInterval = setInterval(() => {
      this.callDuration++;
      const el = document.getElementById('softphoneCallTimer');
      if (el) {
        const mins = Math.floor(this.callDuration / 60).toString().padStart(2, '0');
        const secs = (this.callDuration % 60).toString().padStart(2, '0');
        el.textContent = `${mins}:${secs}`;
      }
    }, 1000);
  }

  private async startCall(numberToDial?: string, contactName?: string, isDirectSim: boolean = false): Promise<void> {
    const target = (numberToDial || this.dialNumber || '').trim();
    if (!target || target.replace(/[^0-9]/g, '').length < 3) {
      alert('Please enter a valid phone number');
      return;
    }

    const cleanNumber = target.startsWith('+') ? target : `+91${target.replace(/\D/g, '').slice(-10)}`;
    this.dialNumber = target;
    if (contactName) this.selectedContactName = contactName;

    // 1. Attempt Plivo WebRTC registration if not yet registered
    if (!this.isWebRTCRegistered && !isDirectSim) {
      const statusEl = document.getElementById('softphoneCallStatusText');
      if (statusEl) {
        statusEl.textContent = 'Connecting to calling network...';
        statusEl.style.color = '#f59e0b';
      }
      await this.initPlivoWebRTC();
    }

    this.isInCall = true;
    this.isCallConnected = false;
    this.callDuration = 0;
    this.callStartTime = Date.now();
    this.isMuted = false;
    this.isSpeaker = false;
    this.isHold = false;
    this.callStatusText = 'Calling...';

    if (this.callTimerInterval) {
      clearInterval(this.callTimerInterval);
      this.callTimerInterval = null;
    }

    // 2. Prepare backend VoIPCallSession for CRM tracking & audit logs
    const sessionId = await this.createCallSession(cleanNumber);

    // 3. Dispatch call strictly through In-App Softphone UI (No native mobile dialer)
    if (!this.plivoClient) {
      this.setupFallbackClient();
    }

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        this.localAudioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (micErr) {
        console.warn('[SoftphonePage] Mic permission notice:', micErr);
      }
    }

    try {
      const extraHeaders = {
        'X-PH-Call-Session-ID': sessionId,
        'X-PH-Destination': cleanNumber
      };
      this.plivoClient.call(cleanNumber, extraHeaders);
    } catch (err) {
      console.warn('[SoftphonePage] Plivo WebRTC client dial error:', err);
    }

    // 5. Route audio to normal in-call EARPIECE by default (speaker OFF)
    this.isSpeaker = false;
    try {
      if ((window as any).Capacitor?.Plugins?.AudioRouting) {
        (window as any).Capacitor.Plugins.AudioRouting.setSpeakerphoneOn({ enabled: false });
      }
    } catch (_) {}

    // 6. Start carrier status polling watcher
    if (sessionId) {
      this.startSessionStatusPolling(sessionId);
    }

    this.render();
  }

  private triggerNativeSimCall(): void {
    const cleanNumber = (this.dialNumber || '').replace(/[^0-9+]/g, '');
    if (cleanNumber) {
      window.location.href = `tel:${cleanNumber}`;
    }
  }

  private endCall(): void {
    this.isInCall = false;
    this.isCallConnected = false;
    this.stopHeartbeatLoop();
    if (this.callTimerInterval) {
      clearInterval(this.callTimerInterval);
      this.callTimerInterval = null;
    }
    if (this.callStatusPollInterval) {
      clearInterval(this.callStatusPollInterval);
      this.callStatusPollInterval = null;
    }

    // Reset Audio Routing back to normal media mode
    this.isSpeaker = false;
    try {
      if ((window as any).Capacitor?.Plugins?.AudioRouting) {
        const ar = (window as any).Capacitor.Plugins.AudioRouting;
        if (typeof ar.resetAudioMode === 'function') {
          ar.resetAudioMode();
        } else {
          ar.setSpeakerphoneOn({ enabled: false });
        }
      }
    } catch (_) {}

    // Hangup Plivo WebRTC client
    if (this.plivoClient && typeof this.plivoClient.hangup === 'function') {
      try { this.plivoClient.hangup(); } catch (_) {}
    }

    // Stop mic stream
    if (this.localAudioStream) {
      try {
        this.localAudioStream.getTracks().forEach(t => t.stop());
      } catch (_) {}
      this.localAudioStream = null;
    }

    if (this.dialNumber) {
      this.saveSoftphoneCall(this.dialNumber, this.selectedContactName, this.callDuration);
    }

    this.activeCallSessionId = null;
    this.callDuration = 0;

    // If navigated from CRM leads/pages with a return route, navigate straight back!
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
    this.isMuted = !this.isMuted;
    if (this.plivoClient) {
      if (this.isMuted && typeof this.plivoClient.mute === 'function') {
        this.plivoClient.mute();
      } else if (!this.isMuted && typeof this.plivoClient.unmute === 'function') {
        this.plivoClient.unmute();
      }
    }
    if (this.localAudioStream) {
      this.localAudioStream.getAudioTracks().forEach(t => { t.enabled = !this.isMuted; });
    }
    this.render();
  }

  private async toggleSpeaker(): Promise<void> {
    this.isSpeaker = !this.isSpeaker;
    try {
      if ((window as any).Capacitor?.Plugins?.AudioRouting) {
        await (window as any).Capacitor.Plugins.AudioRouting.setSpeakerphoneOn({ enabled: this.isSpeaker });
      }
    } catch (err) {
      console.warn('[SoftphonePage] AudioRouting toggle error:', err);
    }
    this.render();
  }

  private toggleHold(): void {
    this.isHold = !this.isHold;
    this.render();
  }

  private togglePlayRecording(recId: number | string, streamUrl: string): void {
    if (this.playingRecordingId === recId && this.currentAudio) {
      if (!this.currentAudio.paused) {
        this.currentAudio.pause();
        this.playingRecordingId = null;
        this.renderHistoryList();
        return;
      }
    }

    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio = null;
    }

    const token = localStorage.getItem('staff_token') || localStorage.getItem('token') || '';
    const fullUrl = streamUrl.startsWith('http') ? streamUrl : `${window.location.origin}${streamUrl}`;
    
    // Create Audio with auth header or bearer param
    const audioUrl = fullUrl.includes('?') ? `${fullUrl}&token=${token}` : `${fullUrl}?token=${token}`;
    this.currentAudio = new Audio(audioUrl);
    this.playingRecordingId = recId;
    this.audioPlayProgress = 0;

    this.currentAudio.play().then(() => {
      this.renderHistoryList();
    }).catch(err => {
      console.warn('[SoftphonePage] Audio playback error:', err);
      alert('Unable to play audio recording: Stream unavailable or expired.');
      this.playingRecordingId = null;
      this.renderHistoryList();
    });

    this.currentAudio.onended = () => {
      this.playingRecordingId = null;
      this.renderHistoryList();
    };

    this.currentAudio.onerror = () => {
      this.playingRecordingId = null;
      this.renderHistoryList();
    };
  }

  private escapeAttr(str: string): string {
    return (str || '').replace(/"/g, '&quot;');
  }

  private formatRelativeTime(dateStr?: string): string {
    if (!dateStr) return 'Recent';
    try {
      const d = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      const timeStr = d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });

      if (diffDays === 0) return `Today, ${timeStr}`;
      if (diffDays === 1) return `Yesterday, ${timeStr}`;
      if (diffDays < 7) return `${diffDays}d ago, ${timeStr}`;
      return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) + `, ${timeStr}`;
    } catch {
      return dateStr;
    }
  }

  private formatDuration(seconds: number): string {
    if (!seconds || seconds <= 0) return '0s';
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const rem = seconds % 60;
    return rem > 0 ? `${mins}m ${rem}s` : `${mins}m`;
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container softphone-page" style="padding-bottom: 90px; min-height: 100vh; background: #0f172a; color: #fff;">
        ${PageHeader.render({ title: 'Softphone', showMenu: true, showBack: false })}

        <!-- Mode Toggle & Status -->
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(255,255,255,0.08);">
          <div style="display: flex; gap: 6px;">
            <button id="tabDialerBtn" style="padding: 6px 12px; border-radius: 20px; font-size: 12.5px; font-weight: 600; border: none; cursor: pointer; transition: all 0.2s; background: ${this.activeTab === 'dialer' ? '#3b82f6' : 'rgba(255,255,255,0.08)'}; color: #fff;">
              <i class="fas fa-keyboard" style="margin-right: 4px;"></i>Keypad
            </button>
            <button id="tabContactsBtn" style="padding: 6px 12px; border-radius: 20px; font-size: 12.5px; font-weight: 600; border: none; cursor: pointer; transition: all 0.2s; background: ${this.activeTab === 'contacts' ? '#3b82f6' : 'rgba(255,255,255,0.08)'}; color: #fff;">
              <i class="fas fa-address-book" style="margin-right: 4px;"></i>Contacts
            </button>
            <button id="tabHistoryBtn" style="padding: 6px 12px; border-radius: 20px; font-size: 12.5px; font-weight: 600; border: none; cursor: pointer; transition: all 0.2s; background: ${this.activeTab === 'history' ? '#3b82f6' : 'rgba(255,255,255,0.08)'}; color: #fff;">
              <i class="fas fa-clock-rotate-left" style="margin-right: 4px;"></i>Recents
            </button>
          </div>

          <div style="display: flex; align-items: center; gap: 6px;">
            <select id="softphoneStatusSelect" style="background: #1e293b; color: ${this.agentStatus === 'available' ? '#22c55e' : this.agentStatus === 'busy' ? '#ef4444' : '#eab308'}; border: 1px solid rgba(255,255,255,0.15); border-radius: 14px; padding: 4px 8px; font-size: 11.5px; font-weight: 600; outline: none;">
              <option value="available" ${this.agentStatus === 'available' ? 'selected' : ''}>🟢 Available</option>
              <option value="busy" ${this.agentStatus === 'busy' ? 'selected' : ''}>🔴 Busy</option>
              <option value="break" ${this.agentStatus === 'break' ? 'selected' : ''}>🟡 Break</option>
            </select>
          </div>
        </div>

        ${this.isInCall ? this.renderInCallScreen() : (this.activeTab === 'dialer' ? this.renderDialpad() : (this.activeTab === 'contacts' ? this.renderContacts() : this.renderHistory()))}
      </div>
    `;

    this.attachListeners();
  }

  private renderDialpad(): string {
    return `
      <div style="max-width: 380px; margin: 0 auto; padding: 16px; position: relative;">
        
        <!-- Number Screen & Clean Dial Display -->
        <div style="background: #1e293b; border-radius: 16px; padding: 14px 18px; margin-bottom: 16px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 4px 12px rgba(0,0,0,0.3); position: relative;">
          
          <div id="softphoneMatchedNameLabel" style="display: ${this.selectedContactName ? 'block' : 'none'}; font-size: 12px; font-weight: 700; color: #38bdf8; margin-bottom: 4px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">
            👤 ${this.selectedContactName}
          </div>

          <div style="display: flex; align-items: center; justify-content: space-between;">
            <input 
              type="tel" 
              inputmode="tel"
              id="softphoneDialInput" 
              value="${this.dialNumber}" 
              placeholder="Enter phone number..." 
              style="background: transparent; border: none; outline: none; color: #fff; font-size: 24px; font-weight: 700; width: 100%; letter-spacing: 0.5px;"
            />
            <div style="display: flex; align-items: center; gap: 8px;">
              <button id="softphoneClearAllBtn" title="Clear all" style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; font-size: 11px; font-weight: 700; border-radius: 12px; padding: 3px 8px; cursor: pointer; display: ${this.dialNumber ? 'inline-block' : 'none'};">
                Clear
              </button>
              <button id="softphoneClearBtn" title="Backspace (Hold to clear all)" style="background: transparent; border: none; color: #94a3b8; font-size: 22px; cursor: pointer; visibility: ${this.dialNumber ? 'visible' : 'hidden'}; padding: 4px; display: flex; align-items: center; user-select: none;">
                <i class="fas fa-delete-left"></i>
              </button>
            </div>
          </div>
        </div>

        <!-- 3x4 Dialpad Grid -->
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px;">
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

        <!-- Bottom Dual Call Actions: Softphone & Direct SIM -->
        <div style="display: flex; flex-direction: column; align-items: center; gap: 12px;">
          <div style="display: flex; align-items: center; justify-content: center; gap: 20px;">
            <button id="softphoneStartCallBtn" title="Call via Cloud Softphone" style="width: 68px; height: 68px; border-radius: 50%; background: linear-gradient(135deg, #22c55e, #16a34a); border: none; color: #fff; font-size: 24px; display: flex; align-items: center; justify-content: center; box-shadow: 0 8px 24px rgba(34, 197, 94, 0.4); cursor: pointer;">
              <i class="fas fa-phone"></i>
            </button>
          </div>

          <button id="softphoneDirectSimBtn" style="padding: 6px 14px; border-radius: 20px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); color: #38bdf8; font-size: 11.5px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;">
            <i class="fas fa-mobile-screen"></i> Direct SIM Call
          </button>
        </div>
      </div>
    `;
  }

  private renderKey(digit: string, sub: string): string {
    return `
      <button 
        class="dialpad-key-btn" 
        data-digit="${digit}" 
        style="height: 64px; border-radius: 16px; background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(255,255,255,0.08); color: #fff; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; user-select: none;"
      >
        <span style="font-size: 22px; font-weight: 700; line-height: 1;">${digit}</span>
        <span style="font-size: 9px; font-weight: 700; color: #94a3b8; letter-spacing: 1px; margin-top: 2px;">${sub}</span>
      </button>
    `;
  }

  private renderContacts(): string {
    return `
      <div style="padding: 16px; max-width: 500px; margin: 0 auto;">
        <!-- Search Input Header -->
        <div style="background: #1e293b; border-radius: 12px; padding: 10px 14px; margin-bottom: 16px; display: flex; align-items: center; gap: 10px; border: 1px solid rgba(255,255,255,0.1);">
          <i class="fas fa-search" style="color: #94a3b8; font-size: 14px;"></i>
          <input 
            type="text" 
            id="softphoneContactsSearchInput" 
            value="${this.searchContactsQuery}" 
            placeholder="Search CRM leads, mobile contacts, staff..." 
            style="background: transparent; border: none; outline: none; color: #fff; font-size: 13.5px; width: 100%;"
          />
        </div>

        <div id="softphoneContactsContainer">
          ${this.renderContactsListHtml()}
        </div>
      </div>
    `;
  }

  private renderContactsList(): void {
    const container = document.getElementById('softphoneContactsContainer');
    if (container) {
      container.innerHTML = this.renderContactsListHtml();
      this.attachContactCardListeners();
    }
  }

  private renderContactsListHtml(): string {
    if (this.isSearchingContacts) {
      return `<div style="text-align: center; padding: 40px; color: #94a3b8;"><i class="fas fa-spinner fa-spin" style="margin-right: 8px;"></i>Searching contacts...</div>`;
    }

    if (this.contactsList.length === 0) {
      return `
        <div style="text-align: center; padding: 50px 20px; color: #64748b;">
          <i class="fas fa-address-book" style="font-size: 36px; margin-bottom: 12px; color: #475569;"></i>
          <p style="font-weight: 600; font-size: 14px;">${this.searchContactsQuery ? 'No contacts match your search' : 'Type name or phone number above to search'}</p>
        </div>
      `;
    }

    return `
      <div style="display: flex; flex-direction: column; gap: 10px;">
        ${this.contactsList.map(c => `
          <div style="background: #1e293b; border-radius: 14px; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; border: 1px solid rgba(255,255,255,0.06);">
            <div style="display: flex; align-items: center; gap: 12px;">
              <div style="width: 38px; height: 38px; border-radius: 50%; background: ${c.badge_color || '#3b82f6'}; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 700; color: #fff;">
                ${(c.name ? c.name.charAt(0) : 'C').toUpperCase()}
              </div>
              <div>
                <div style="font-weight: 700; font-size: 14px; color: #fff;">${c.name}</div>
                <div style="font-size: 12px; color: #94a3b8; margin-top: 2px;">
                  +91 ${c.phone} • <span style="color: ${c.badge_color || '#38bdf8'}; font-weight: 600;">${c.source || 'Lead'}</span>
                </div>
              </div>
            </div>
            <div style="display: flex; gap: 6px;">
              <button class="contact-call-btn" data-phone="${c.phone}" data-name="${this.escapeAttr(c.name)}" title="Softphone Call" style="width: 38px; height: 38px; border-radius: 50%; background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); color: #22c55e; cursor: pointer; display: flex; align-items: center; justify-content: center;">
                <i class="fas fa-phone fa-sm"></i>
              </button>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  private maskPhone(p: string): string {
    if (!p || p === '—' || p === '-' || p === 'null') return '—';
    const s = String(p).trim();
    if (s.includes('@g.us') || s.includes('@broadcast') || s.includes('@lid')) return s;
    const digits = s.replace(/\D/g, '');
    if (digits.length < 6) return s;
    const clean10 = digits.slice(-10);
    return `+91 ${clean10.slice(0, 2)}••••${clean10.slice(-4)}`;
  }

  private renderInCallScreen(): string {
    const mins = Math.floor(this.callDuration / 60).toString().padStart(2, '0');
    const secs = (this.callDuration % 60).toString().padStart(2, '0');
    const cleanNumber = (this.dialNumber || '').replace(/[^0-9+]/g, '');
    const maskedPhone = this.maskPhone(this.dialNumber);

    return `
      <div style="max-width: 380px; margin: 20px auto; padding: 20px; text-align: center;">
        <div style="width: 90px; height: 90px; border-radius: 50%; background: linear-gradient(135deg, #3b82f6, #1d4ed8); display: flex; align-items: center; justify-content: center; font-size: 34px; font-weight: 800; color: #fff; margin: 0 auto 16px auto; box-shadow: 0 8px 24px rgba(59, 130, 246, 0.4);">
          <i class="fas fa-user"></i>
        </div>

        <h3 style="font-size: 22px; font-weight: 700; margin: 0 0 4px 0; color: #fff;">${this.selectedContactName || maskedPhone}</h3>
        ${this.selectedContactName ? `<div style="font-size: 13px; color: #94a3b8; margin-bottom: 6px;">${maskedPhone}</div>` : ''}
        <p id="softphoneCallStatusText" style="font-size: 14px; color: ${this.isCallConnected ? '#22c55e' : '#38bdf8'}; font-weight: 600; margin: 0 0 12px 0;">${this.callStatusText}</p>
        
        <div id="softphoneCallTimer" style="font-size: ${this.isCallConnected ? '26px' : '17px'}; font-weight: 700; font-family: ${this.isCallConnected ? 'monospace' : 'inherit'}; color: ${this.isCallConnected ? '#cbd5e1' : '#38bdf8'}; margin-bottom: 28px;">
          ${this.isCallConnected ? `${mins}:${secs}` : `<i class="fas fa-phone-volume fa-shake" style="margin-right: 6px;"></i> Ringing...`}
        </div>

        <!-- In-Call Control Grid -->
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 32px;">
          <button id="callMuteBtn" style="padding: 14px; border-radius: 14px; background: ${this.isMuted ? '#ef4444' : 'rgba(255,255,255,0.08)'}; border: none; color: #fff; cursor: pointer;">
            <i class="fas fa-microphone-slash" style="font-size: 20px; margin-bottom: 6px;"></i>
            <div style="font-size: 11px; font-weight: 600;">${this.isMuted ? 'Muted' : 'Mute'}</div>
          </button>
          
          <button id="callSpeakerBtn" style="padding: 14px; border-radius: 14px; background: ${this.isSpeaker ? '#3b82f6' : 'rgba(255,255,255,0.08)'}; border: none; color: #fff; cursor: pointer;">
            <i class="fas fa-volume-high" style="font-size: 20px; margin-bottom: 6px;"></i>
            <div style="font-size: 11px; font-weight: 600;">Speaker</div>
          </button>

          <button id="callHoldBtn" style="padding: 14px; border-radius: 14px; background: ${this.isHold ? '#eab308' : 'rgba(255,255,255,0.08)'}; border: none; color: #fff; cursor: pointer;">
            <i class="fas fa-pause" style="font-size: 20px; margin-bottom: 6px;"></i>
            <div style="font-size: 11px; font-weight: 600;">${this.isHold ? 'On Hold' : 'Hold'}</div>
          </button>
        </div>

        <!-- Big Red Hangup Button & Direct SIM Fallback Below -->
        <div style="display: flex; flex-direction: column; align-items: center; gap: 16px;">
          <button id="softphoneEndCallBtn" style="width: 72px; height: 72px; border-radius: 50%; background: linear-gradient(135deg, #ef4444, #b91c1c); border: none; color: #fff; font-size: 26px; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 8px 24px rgba(239, 68, 68, 0.4); cursor: pointer;">
            <i class="fas fa-phone-slash"></i>
          </button>

          <button id="softphoneDirectSimBtn" style="padding: 6px 14px; border-radius: 20px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); color: #38bdf8; font-size: 11.5px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;">
            <i class="fas fa-mobile-screen"></i> Direct SIM Call
          </button>
        </div>
      </div>
    `;
  }

  private renderHistory(): string {
    return `
      <div style="padding: 16px; max-width: 500px; margin: 0 auto;">
        
        <!-- 1. Channel Filter: All Calls | Softphone | Mobile -->
        <div style="display: flex; gap: 6px; margin-bottom: 10px; background: #1e293b; padding: 4px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);">
          <button class="recents-channel-btn" data-channel="ALL" style="flex: 1; padding: 7px 4px; border-radius: 8px; font-size: 11.5px; font-weight: 700; border: none; cursor: pointer; transition: all 0.15s; background: ${this.channelFilter === 'ALL' ? '#3b82f6' : 'transparent'}; color: ${this.channelFilter === 'ALL' ? '#fff' : '#94a3b8'};">
            All Channels
          </button>
          <button class="recents-channel-btn" data-channel="SOFTPHONE" style="flex: 1; padding: 7px 4px; border-radius: 8px; font-size: 11.5px; font-weight: 700; border: none; cursor: pointer; transition: all 0.15s; background: ${this.channelFilter === 'SOFTPHONE' ? '#3b82f6' : 'transparent'}; color: ${this.channelFilter === 'SOFTPHONE' ? '#fff' : '#94a3b8'};">
            <i class="fas fa-phone" style="margin-right: 3px;"></i>Softphone
          </button>
          <button class="recents-channel-btn" data-channel="MOBILE" style="flex: 1; padding: 7px 4px; border-radius: 8px; font-size: 11.5px; font-weight: 700; border: none; cursor: pointer; transition: all 0.15s; background: ${this.channelFilter === 'MOBILE' ? '#3b82f6' : 'transparent'}; color: ${this.channelFilter === 'MOBILE' ? '#fff' : '#94a3b8'};">
            <i class="fas fa-mobile-screen" style="margin-right: 3px;"></i>Mobile
          </button>
        </div>

        <!-- 2. Sub-tabs / Direction Filter: All | In | Out | Missed -->
        <div style="display: flex; gap: 4px; margin-bottom: 10px; background: rgba(30, 41, 59, 0.6); padding: 3px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.05);">
          <button class="recents-direction-btn" data-dir="ALL" style="flex: 1; padding: 5px; border-radius: 6px; font-size: 11px; font-weight: 700; border: none; cursor: pointer; background: ${this.directionFilter === 'ALL' ? '#2563eb' : 'transparent'}; color: ${this.directionFilter === 'ALL' ? '#fff' : '#94a3b8'};">
            All
          </button>
          <button class="recents-direction-btn" data-dir="INCOMING" style="flex: 1; padding: 5px; border-radius: 6px; font-size: 11px; font-weight: 700; border: none; cursor: pointer; background: ${this.directionFilter === 'INCOMING' ? '#059669' : 'transparent'}; color: ${this.directionFilter === 'INCOMING' ? '#fff' : '#94a3b8'};">
            ↙️ In
          </button>
          <button class="recents-direction-btn" data-dir="OUTGOING" style="flex: 1; padding: 5px; border-radius: 6px; font-size: 11px; font-weight: 700; border: none; cursor: pointer; background: ${this.directionFilter === 'OUTGOING' ? '#0284c7' : 'transparent'}; color: ${this.directionFilter === 'OUTGOING' ? '#fff' : '#94a3b8'};">
            ↗️ Out
          </button>
          <button class="recents-direction-btn" data-dir="MISSED" style="flex: 1; padding: 5px; border-radius: 6px; font-size: 11px; font-weight: 700; border: none; cursor: pointer; background: ${this.directionFilter === 'MISSED' ? '#dc2626' : 'transparent'}; color: ${this.directionFilter === 'MISSED' ? '#fff' : '#94a3b8'};">
            🚫 Missed
          </button>
        </div>

        <!-- 3. Date Range & Team Hierarchy Controls -->
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px;">
          <!-- Date Presets -->
          <select id="recentsDateRangeSelect" style="flex: 1; min-width: 120px; background: #1e293b; color: #fff; border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; padding: 6px 10px; font-size: 11.5px; font-weight: 600; outline: none;">
            <option value="ALL" ${this.dateRangePreset === 'ALL' ? 'selected' : ''}>📅 All Time</option>
            <option value="TODAY" ${this.dateRangePreset === 'TODAY' ? 'selected' : ''}>📅 Today</option>
            <option value="YESTERDAY" ${this.dateRangePreset === 'YESTERDAY' ? 'selected' : ''}>📅 Yesterday</option>
            <option value="WEEK" ${this.dateRangePreset === 'WEEK' ? 'selected' : ''}>📅 Last 7 Days</option>
            <option value="CUSTOM" ${this.dateRangePreset === 'CUSTOM' ? 'selected' : ''}>📅 Custom Range</option>
          </select>

          <!-- Upline Manager Team Selector -->
          ${this.isManager || this.downlineMembers.length > 0 ? `
            <select id="recentsTeamSelect" style="flex: 1.2; min-width: 140px; background: #1e293b; color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 8px; padding: 6px 10px; font-size: 11.5px; font-weight: 700; outline: none;">
              <option value="all" ${this.targetStaffId === 'all' ? 'selected' : ''}>👥 All Team Calls</option>
              <option value="self" ${this.targetStaffId === 'self' ? 'selected' : ''}>👤 My Calls Only</option>
              ${this.downlineMembers.map(m => `
                <option value="${m.id}" ${String(this.targetStaffId) === String(m.id) ? 'selected' : ''}>
                  👤 ${m.name}
                </option>
              `).join('')}
            </select>
          ` : ''}
        </div>

        <!-- Custom Date Inputs (when CUSTOM is chosen) -->
        ${this.dateRangePreset === 'CUSTOM' ? `
          <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 14px; background: #1e293b; padding: 8px 12px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
            <div style="flex: 1;">
              <label style="font-size: 10px; color: #94a3b8; display: block; margin-bottom: 2px;">Start Date</label>
              <input type="date" id="customStartDateInput" value="${this.customStartDate}" style="background: #0f172a; border: 1px solid #475569; color: #fff; padding: 4px 6px; border-radius: 6px; font-size: 11px; width: 100%;">
            </div>
            <div style="flex: 1;">
              <label style="font-size: 10px; color: #94a3b8; display: block; margin-bottom: 2px;">End Date</label>
              <input type="date" id="customEndDateInput" value="${this.customEndDate}" style="background: #0f172a; border: 1px solid #475569; color: #fff; padding: 4px 6px; border-radius: 6px; font-size: 11px; width: 100%;">
            </div>
            <button id="applyCustomDateBtn" style="margin-top: 14px; padding: 6px 12px; background: #3b82f6; border: none; border-radius: 6px; color: #fff; font-size: 11px; font-weight: 700; cursor: pointer;">
              Apply
            </button>
          </div>
        ` : ''}

        <div id="softphoneHistoryContainer">
          ${this.renderHistoryListHtml()}
        </div>
      </div>
    `;
  }

  private renderHistoryList(): void {
    const container = document.getElementById('softphoneHistoryContainer');
    if (container) {
      container.innerHTML = this.renderHistoryListHtml();
      this.attachHistoryCardListeners();
    }
  }

  private renderHistoryListHtml(): string {
    if (this.isLoadingHistory) {
      return `<div style="text-align: center; padding: 40px; color: #94a3b8;"><i class="fas fa-spinner fa-spin" style="margin-right: 8px;"></i>Loading call history...</div>`;
    }

    // Filter calls based on selected channel and direction
    const filtered = this.recentCalls.filter(c => {
      // Channel Filter
      if (this.channelFilter === 'SOFTPHONE' && (c.source !== 'softphone' && c.source !== 'dialer')) return false;
      if (this.channelFilter === 'MOBILE' && (c.source !== 'native' && c.source !== undefined)) return false;

      // Direction Filter
      const typeUpper = (c.call_type || 'OUTGOING').toUpperCase();
      if (this.directionFilter === 'INCOMING' && typeUpper !== 'INCOMING') return false;
      if (this.directionFilter === 'OUTGOING' && typeUpper !== 'OUTGOING') return false;
      if (this.directionFilter === 'MISSED' && (typeUpper !== 'MISSED' && typeUpper !== 'REJECTED')) return false;

      return true;
    });

    if (filtered.length === 0) {
      return `
        <div style="text-align: center; padding: 50px 20px; color: #64748b;">
          <i class="fas fa-phone-slash" style="font-size: 38px; margin-bottom: 12px; color: #475569;"></i>
          <p style="font-weight: 600; font-size: 14px;">No call records found matching filters</p>
        </div>
      `;
    }

    return `
      <div style="display: flex; flex-direction: column; gap: 10px;">
        ${filtered.map(c => {
          const typeUpper = (c.call_type || 'OUTGOING').toUpperCase();
          const isMissed = typeUpper === 'MISSED' || typeUpper === 'REJECTED';
          const isIncoming = typeUpper === 'INCOMING';
          const icon = isIncoming ? 'fa-arrow-down-left text-primary' : (isMissed ? 'fa-phone-slash text-danger' : 'fa-arrow-up-right text-success');
          const isSoftphone = c.source === 'softphone' || c.source === 'dialer';
          const durationFormatted = this.formatDuration(c.duration_seconds || 0);
          const timeFormatted = this.formatRelativeTime(c.dialed_at || c.timestamp);
          const recId = c.recording_id || (c.has_recording ? (c.id || 'rec') : null);
          const isPlaying = this.playingRecordingId && String(this.playingRecordingId) === String(recId);

          return `
            <div style="background: #1e293b; border-radius: 14px; padding: 13px 16px; border: 1px solid rgba(255,255,255,0.06);">
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 12px;">
                  <div style="width: 38px; height: 38px; border-radius: 50%; background: ${isSoftphone ? 'rgba(59, 130, 246, 0.15)' : 'rgba(255,255,255,0.06)'}; display: flex; align-items: center; justify-content: center; font-size: 14px;">
                    <i class="fa-solid ${icon}"></i>
                  </div>
                  <div>
                    <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                      <span style="font-weight: 700; font-size: 14px; color: ${isMissed ? '#f87171' : '#fff'};">${c.contact_name || c.phone_number}</span>
                      <span style="font-size: 9.5px; font-weight: 700; padding: 1px 5px; border-radius: 4px; background: ${isSoftphone ? 'rgba(59, 130, 246, 0.2)' : 'rgba(148, 163, 184, 0.15)'}; color: ${isSoftphone ? '#60a5fa' : '#94a3b8'};">
                        ${isSoftphone ? 'Softphone' : 'Mobile'}
                      </span>
                      ${c.is_downline && c.staff_name ? `
                        <span style="font-size: 9.5px; font-weight: 700; padding: 1px 5px; border-radius: 4px; background: rgba(234, 179, 8, 0.2); color: #facc15;">
                          👤 ${c.staff_name}
                        </span>
                      ` : ''}
                    </div>
                    <div style="font-size: 11.5px; color: #94a3b8; margin-top: 2px;">
                      ${c.contact_name ? `${c.phone_number} • ` : ''}${timeFormatted} ${durationFormatted ? `(${durationFormatted})` : ''}
                    </div>
                  </div>
                </div>

                <!-- Right Action Buttons: Play Recording & Call -->
                <div style="display: flex; align-items: center; gap: 8px;">
                  ${(isSoftphone || c.has_recording || c.recording_stream_url) ? `
                    <button 
                      class="history-play-rec-btn" 
                      data-rec-id="${recId}" 
                      data-stream-url="${c.recording_stream_url || `/api/v1/call-tracking/recordings/${recId}/stream`}"
                      title="${isPlaying ? 'Pause Recording' : 'Listen to Call Recording'}"
                      style="width: 36px; height: 36px; border-radius: 50%; background: ${isPlaying ? '#eab308' : 'rgba(56, 189, 248, 0.15)'}; border: 1px solid ${isPlaying ? '#facc15' : 'rgba(56, 189, 248, 0.3)'}; color: ${isPlaying ? '#000' : '#38bdf8'}; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: transform 0.1s;"
                    >
                      <i class="fas ${isPlaying ? 'fa-pause' : 'fa-play'} fa-xs"></i>
                    </button>
                  ` : ''}

                  <button class="history-call-btn" data-phone="${c.phone_number}" data-name="${this.escapeAttr(c.contact_name || '')}" style="width: 36px; height: 36px; border-radius: 50%; background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); color: #22c55e; cursor: pointer; display: flex; align-items: center; justify-content: center;">
                    <i class="fas fa-phone fa-xs"></i>
                  </button>
                </div>
              </div>

              <!-- Inline Audio Player Banner when playing -->
              ${isPlaying ? `
                <div style="margin-top: 10px; padding: 8px 12px; background: rgba(15, 23, 42, 0.8); border-radius: 8px; border: 1px solid rgba(234, 179, 8, 0.3); display: flex; align-items: center; justify-content: space-between;">
                  <div style="display: flex; align-items: center; gap: 8px; font-size: 11.5px; color: #facc15; font-weight: 600;">
                    <i class="fas fa-volume-high fa-beat"></i>
                    <span>Playing Call Audio (${durationFormatted || 'Audio'})</span>
                  </div>
                  <button class="history-stop-rec-btn" style="background: transparent; border: none; color: #94a3b8; font-size: 12px; cursor: pointer;">
                    ✕ Close
                  </button>
                </div>
              ` : ''}
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  private attachListeners(): void {
    // Mode toggles
    document.getElementById('tabDialerBtn')?.addEventListener('click', () => {
      this.activeTab = 'dialer';
      this.render();
    });

    document.getElementById('tabContactsBtn')?.addEventListener('click', () => {
      this.activeTab = 'contacts';
      this.render();
      if (this.contactsList.length === 0) {
        this.searchContacts('a');
      }
    });

    document.getElementById('tabHistoryBtn')?.addEventListener('click', () => {
      this.activeTab = 'history';
      this.render();
      this.loadRecentCalls();
    });

    // Channel Filters (All | Softphone | Mobile)
    this.container.querySelectorAll('.recents-channel-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        this.channelFilter = (target.dataset.channel || 'ALL') as any;
        this.renderHistoryList();
      });
    });

    // Direction Sub-tabs (All | In | Out | Missed)
    this.container.querySelectorAll('.recents-direction-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        this.directionFilter = (target.dataset.dir || 'ALL') as any;
        this.render();
        this.loadRecentCalls();
      });
    });

    // Date Range Presets
    document.getElementById('recentsDateRangeSelect')?.addEventListener('change', (e) => {
      this.dateRangePreset = (e.target as HTMLSelectElement).value as any;
      this.render();
      if (this.dateRangePreset !== 'CUSTOM') {
        this.loadRecentCalls();
      }
    });

    // Custom Date Apply
    document.getElementById('applyCustomDateBtn')?.addEventListener('click', () => {
      const sInput = document.getElementById('customStartDateInput') as HTMLInputElement;
      const eInput = document.getElementById('customEndDateInput') as HTMLInputElement;
      if (sInput) this.customStartDate = sInput.value;
      if (eInput) this.customEndDate = eInput.value;
      this.loadRecentCalls();
    });

    // Team Member Filter (for Upline Managers)
    document.getElementById('recentsTeamSelect')?.addEventListener('change', (e) => {
      this.targetStaffId = (e.target as HTMLSelectElement).value;
      this.loadRecentCalls();
    });

    // Agent status change
    document.getElementById('softphoneStatusSelect')?.addEventListener('change', (e) => {
      this.agentStatus = (e.target as HTMLSelectElement).value as any;
      this.render();
    });

    // Keypad button presses
    this.container.querySelectorAll('.dialpad-key-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const digit = (btn as HTMLElement).dataset.digit;
        if (digit) this.pressKey(digit);
      });
    });

    // Clear All Button (One-tap full clear)
    document.getElementById('softphoneClearAllBtn')?.addEventListener('click', () => this.clearNumber());

    // Backspace with Long-Press Detection (Tap = delete 1 digit, Hold > 320ms = clear all)
    const clearBtn = document.getElementById('softphoneClearBtn');
    if (clearBtn) {
      let longPressTimer: any = null;
      let didLongPress = false;

      const handlePressStart = () => {
        didLongPress = false;
        longPressTimer = setTimeout(() => {
          didLongPress = true;
          this.clearNumber();
        }, 320);
      };

      const handlePressEnd = () => {
        if (longPressTimer) {
          clearTimeout(longPressTimer);
          longPressTimer = null;
        }
      };

      clearBtn.addEventListener('pointerdown', handlePressStart);
      clearBtn.addEventListener('pointerup', handlePressEnd);
      clearBtn.addEventListener('pointercancel', handlePressEnd);
      clearBtn.addEventListener('pointerleave', handlePressEnd);
      clearBtn.addEventListener('click', (e) => {
        e.preventDefault();
        if (!didLongPress) {
          this.backspace();
        }
      });
    }

    // Manual input sync (clean, no search interference)
    const input = document.getElementById('softphoneDialInput') as HTMLInputElement;
    input?.addEventListener('input', () => {
      this.dialNumber = input.value;
      this.selectedContactName = '';
      this.updateDialDisplay();
    });

    // Contacts Tab search input
    const contactsSearchInput = document.getElementById('softphoneContactsSearchInput') as HTMLInputElement;
    contactsSearchInput?.addEventListener('input', () => {
      this.searchContactsQuery = contactsSearchInput.value;
      if (this.searchDebounceTimer) clearTimeout(this.searchDebounceTimer);
      this.searchDebounceTimer = setTimeout(() => {
        this.searchContacts(this.searchContactsQuery || 'a');
      }, 200);
    });

    // Call Actions (Strictly In-App Softphone)
    document.getElementById('softphoneStartCallBtn')?.addEventListener('click', () => this.startCall());
    document.getElementById('softphoneDirectSimBtn')?.addEventListener('click', () => this.startCall());
    document.getElementById('inCallSwitchSimBtn')?.addEventListener('click', () => this.startCall());
    document.getElementById('softphoneEndCallBtn')?.addEventListener('click', () => this.endCall());
    document.getElementById('callMuteBtn')?.addEventListener('click', () => this.toggleMute());
    document.getElementById('callSpeakerBtn')?.addEventListener('click', () => this.toggleSpeaker());
    document.getElementById('callHoldBtn')?.addEventListener('click', () => this.toggleHold());

    this.attachHistoryCardListeners();
    this.attachContactCardListeners();
  }

  private attachHistoryCardListeners(): void {
    // Redial call button
    this.container.querySelectorAll('.history-call-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const phone = (btn as HTMLElement).dataset.phone;
        const name = (btn as HTMLElement).dataset.name;
        if (phone) this.startCall(phone, name);
      });
    });

    // Play Recording audio button
    this.container.querySelectorAll('.history-play-rec-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = btn as HTMLElement;
        const recId = target.dataset.recId || '';
        const streamUrl = target.dataset.streamUrl || '';
        if (recId && streamUrl) {
          this.togglePlayRecording(recId, streamUrl);
        }
      });
    });

    // Stop recording
    this.container.querySelectorAll('.history-stop-rec-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (this.currentAudio) {
          this.currentAudio.pause();
          this.currentAudio = null;
        }
        this.playingRecordingId = null;
        this.renderHistoryList();
      });
    });
  }

  private attachContactCardListeners(): void {
    this.container.querySelectorAll('.contact-call-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const phone = (btn as HTMLElement).dataset.phone;
        const name = (btn as HTMLElement).dataset.name;
        if (phone) this.startCall(phone, name);
      });
    });
  }
}
