/**
 * Authoritative Telephony Service & Call Session Engine — MyntOS Mobile
 * Unified Plivo WebRTC client, session polling, active call state machine, and audio controls.
 * Reusable by both SoftphoneModal (in-place) and SoftphonePage (standalone).
 */

import { apiService } from './api.service';

export type CallState = 'idle' | 'initializing' | 'connecting' | 'ringing' | 'connected' | 'ended' | 'failed';
export type RegistrationState = 'UNINITIALIZED' | 'CONNECTING' | 'REGISTERED' | 'REGISTRATION_FAILED';

export interface TelephonyCallSession {
  sessionId: string | null;
  destinationPhone: string;
  contactName: string;
  leadId: number | string | null;
  state: CallState;
  durationSeconds: number;
  isMuted: boolean;
  isSpeaker: boolean;
  isHeld: boolean;
  errorMessage: string | null;
  startedAt: number | null;
  direction?: 'inbound' | 'outbound';
  isIncoming?: boolean;
}

export type TelephonyStateListener = (session: TelephonyCallSession) => void;

class TelephonyService {
  private plivoClient: any = null;
  private incomingCallObj: any = null;
  private isSdkLoaded: boolean = false;
  private registrationState: RegistrationState = 'UNINITIALIZED';
  private registrationPromise: Promise<boolean> | null = null;
  private localAudioStream: MediaStream | null = null;

  // Active Session State
  private session: TelephonyCallSession = {
    sessionId: null,
    destinationPhone: '',
    contactName: '',
    leadId: null,
    state: 'idle',
    durationSeconds: 0,
    isMuted: false,
    isSpeaker: false,
    isHeld: false,
    errorMessage: null,
    startedAt: null
  };

  private listeners: Set<TelephonyStateListener> = new Set();
  private callTimerInterval: any = null;
  private sessionPollInterval: any = null;
  private heartbeatInterval: any = null;

  constructor() {
    if (typeof window !== 'undefined') {
      // Lazy pre-warm when page is interactive
      if (document.readyState === 'complete' || document.readyState === 'interactive') {
        this.prewarm();
      } else {
        document.addEventListener('DOMContentLoaded', () => this.prewarm());
      }
    }
  }

  public subscribe(listener: TelephonyStateListener): () => void {
    this.listeners.add(listener);
    listener(this.getSession());
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notify(): void {
    const current = this.getSession();
    this.listeners.forEach((fn) => {
      try {
        fn(current);
      } catch (err) {
        console.warn('[TelephonyService] Listener error:', err);
      }
    });
  }

  public getSession(): TelephonyCallSession {
    return { ...this.session };
  }

  public getRegistrationState(): RegistrationState {
    return this.registrationState;
  }

  public isCallActive(): boolean {
    return this.session.state !== 'idle' && this.session.state !== 'ended' && this.session.state !== 'failed';
  }

  private async prewarm(): Promise<void> {
    this.ensureAudioElement();
  }

  private ensureAudioElement(): void {
    if (typeof document === 'undefined') return;
    let audioEl = document.getElementById('plivoRemoteAudio') as HTMLAudioElement;
    if (!audioEl) {
      audioEl = document.createElement('audio');
      audioEl.id = 'plivoRemoteAudio';
      audioEl.autoplay = true;
      audioEl.setAttribute('playsinline', 'true');
      audioEl.style.display = 'none';
      document.body.appendChild(audioEl);
    }
    audioEl.volume = 1.0;
    audioEl.muted = false;
  }

  private registrationResolve: ((val: boolean) => void) | null = null;
  private registrationReject: ((err: any) => void) | null = null;

  public async initPlivoWebRTC(): Promise<boolean> {
    if (this.registrationState === 'REGISTERED' && this.plivoClient) {
      return true;
    }
    if (this.registrationPromise) {
      return this.registrationPromise;
    }

    this.registrationState = 'CONNECTING';
    this.registrationPromise = new Promise<boolean>(async (resolve, reject) => {
      this.registrationResolve = resolve;
      this.registrationReject = reject;

      const timeout = setTimeout(() => {
        if (this.registrationState !== 'REGISTERED') {
          console.warn('[TelephonyService] Plivo login timeout after 12s');
          this.registrationState = 'REGISTRATION_FAILED';
          if (this.registrationResolve) {
            this.registrationResolve(false);
            this.registrationResolve = null;
          }
          this.registrationPromise = null;
        }
      }, 12000);

      try {
        this.ensureAudioElement();

        const isSecureOrLocal =
          typeof window !== 'undefined' &&
          (window.isSecureContext ||
            window.location.hostname === 'localhost' ||
            window.location.hostname === '127.0.0.1');
        const hasMedia =
          typeof navigator !== 'undefined' &&
          !!navigator.mediaDevices &&
          typeof navigator.mediaDevices.getUserMedia === 'function';

        if (!isSecureOrLocal && !hasMedia) {
          console.warn('[TelephonyService] Insecure context: WebRTC requires HTTPS or localhost');
          clearTimeout(timeout);
          this.registrationState = 'REGISTRATION_FAILED';
          if (this.registrationResolve) {
            this.registrationResolve(false);
            this.registrationResolve = null;
          }
          this.registrationPromise = null;
          return;
        }

        // Pre-warm local microphone tracks to initialize hardware AEC and verify permissions
        if (hasMedia) {
          try {
            const testStream = await navigator.mediaDevices.getUserMedia({
              audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
            });
            testStream.getTracks().forEach((t) => t.stop());
            console.log('[TelephonyService] Microphone AEC initialized and ready');
          } catch (micErr) {
            console.warn('[TelephonyService] Mic pre-warm notice:', micErr);
          }
        }

        // Load Plivo SDK if not present
        if (typeof (window as any).Plivo === 'undefined') {
          const sdkLoaded = await new Promise<boolean>((res) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.plivo.com/sdk/browser/v2/plivo.min.js';
            script.async = true;
            script.onload = () => res(true);
            script.onerror = () => {
              console.warn('[TelephonyService] Plivo CDN unreachable');
              res(false);
            };
            document.head.appendChild(script);
          });

          if (!sdkLoaded) {
            clearTimeout(timeout);
            this.registrationState = 'REGISTRATION_FAILED';
            if (this.registrationResolve) {
              this.registrationResolve(false);
              this.registrationResolve = null;
            }
            this.registrationPromise = null;
            return;
          }
        }

        if (typeof (window as any).Plivo !== 'undefined') {
          const PlivoConstructor = (window as any).Plivo;
          const audioConstraints = {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            channelCount: 1,
            sampleRate: 48000
          };

          if (!this.plivoClient) {
            if (typeof PlivoConstructor === 'function') {
              const sdk = new PlivoConstructor({
                allowMultipleIncomingCalls: true,
                enableDscp: true,
                audioConstraints: audioConstraints,
                audioElementOption: {
                  remoteAudioId: 'plivoRemoteAudio'
                }
              });
              this.plivoClient = sdk.client || sdk;
            } else if (PlivoConstructor.Client) {
              this.plivoClient = new PlivoConstructor.Client({
                audioConstraints: audioConstraints
              });
            }

            if (this.plivoClient) {
              this.bindClientEvents();
            }
          }

          // Fetch JWT Token
          const tokenResp = await apiService.get<any>('/telephony/plivo/browser/token');
          const payload = tokenResp?.data || tokenResp;
          const accessToken = payload?.access_token || tokenResp?.access_token;

          if (accessToken && this.plivoClient) {
            if (typeof this.plivoClient.loginWithAccessToken === 'function') {
              this.plivoClient.loginWithAccessToken(accessToken);
            } else if (typeof this.plivoClient.login === 'function') {
              this.plivoClient.login(accessToken);
            }
          } else {
            console.warn('[TelephonyService] No access token returned from backend.');
            clearTimeout(timeout);
            this.registrationState = 'REGISTRATION_FAILED';
            if (this.registrationResolve) {
              this.registrationResolve(false);
              this.registrationResolve = null;
            }
            this.registrationPromise = null;
          }
        } else {
          clearTimeout(timeout);
          this.registrationState = 'REGISTRATION_FAILED';
          if (this.registrationResolve) {
            this.registrationResolve(false);
            this.registrationResolve = null;
          }
          this.registrationPromise = null;
        }
      } catch (err) {
        console.warn('[TelephonyService] WebRTC initialization error:', err);
        clearTimeout(timeout);
        this.registrationState = 'REGISTRATION_FAILED';
        if (this.registrationResolve) {
          this.registrationResolve(false);
          this.registrationResolve = null;
        }
        this.registrationPromise = null;
      }
    });

    return this.registrationPromise;
  }

  public maskPhone(p: string): string {
    if (!p || p === '—' || p === '-' || p === 'null') return '—';
    const s = String(p).trim();
    if (s.includes('@g.us') || s.includes('@broadcast') || s.includes('@lid')) return s;
    const digits = s.replace(/\D/g, '');
    if (digits.length < 6) return s;
    const clean10 = digits.slice(-10);
    return `+91 ${clean10.slice(0, 2)}••••${clean10.slice(-4)}`;
  }

  private bindClientEvents(): void {
    if (!this.plivoClient) return;

    this.plivoClient.on('onLogin', (data: any) => {
      console.log('[TelephonyService] Plivo WebRTC registered:', data);
      this.registrationState = 'REGISTERED';
      if (this.registrationResolve) {
        this.registrationResolve(true);
        this.registrationResolve = null;
      }
      this.registrationPromise = null;
    });

    this.plivoClient.on('onLogout', () => {
      this.registrationState = 'UNINITIALIZED';
      this.registrationPromise = null;
    });

    this.plivoClient.on('onLoginFailed', (reason: any) => {
      console.warn('[TelephonyService] Plivo WebRTC login failed:', reason);
      this.registrationState = 'REGISTRATION_FAILED';
      if (this.registrationResolve) {
        this.registrationResolve(false);
        this.registrationResolve = null;
      }
      this.registrationPromise = null;
    });

    this.plivoClient.on('onIncomingCall', (callerName: any, extraHeaders: any, callInfo: any) => {
      console.log('[TelephonyService] Inbound call received:', callerName, callInfo);
      this.incomingCallObj = callInfo;
      const callerPhone = callerName || callInfo?.src || '';
      const leadName = extraHeaders?.['X-PH-Lead-Name'] || 'Incoming Inquiry';
      const maskedPhone = this.maskPhone(callerPhone);

      this.session = {
        sessionId: extraHeaders?.['X-PH-Call-Session-ID'] || callInfo?.callUUID || `vcs_in_${Date.now()}`,
        destinationPhone: maskedPhone,
        contactName: leadName,
        leadId: extraHeaders?.['X-PH-Lead-ID'] || null,
        state: 'ringing',
        durationSeconds: 0,
        isMuted: false,
        isSpeaker: false,
        isHeld: false,
        errorMessage: null,
        startedAt: null,
        direction: 'inbound',
        isIncoming: true
      };
      this.notify();
    });

    this.plivoClient.on('onIncomingCallCanceled', () => {
      console.log('[TelephonyService] Inbound call canceled / missed');
      this.incomingCallObj = null;
      this.handleCallEnd('Call missed / canceled');
    });

    this.plivoClient.on('onCallAnswered', (callInfo: any) => {
      console.log('[TelephonyService] Call connected / answered:', callInfo);
      this.session.state = 'connected';
      this.session.startedAt = Date.now();
      const remoteAudio = document.getElementById('plivoRemoteAudio') as HTMLAudioElement;
      if (remoteAudio) {
        remoteAudio.volume = 1.0;
        remoteAudio.muted = false;
        if (typeof remoteAudio.play === 'function') {
          remoteAudio.play().catch(() => {});
        }
      }
      this.applyAudioRouting(this.session.isSpeaker);
      this.startTimer();
      this.startHeartbeat();
      this.notify();
    });

    this.plivoClient.on('onMediaConnected', () => {
      console.log('[TelephonyService] Media stream established');
      const remoteAudio = document.getElementById('plivoRemoteAudio') as HTMLAudioElement;
      if (remoteAudio) {
        remoteAudio.volume = 1.0;
        remoteAudio.muted = false;
        if (typeof remoteAudio.play === 'function') {
          remoteAudio.play().catch(() => {});
        }
      }
      this.applyAudioRouting(this.session.isSpeaker);
    });

    this.plivoClient.on('onCallTerminated', () => {
      console.log('[TelephonyService] Call terminated');
      this.handleCallEnd('Call ended');
    });

    this.plivoClient.on('onCallFailed', (reason: any) => {
      console.warn('[TelephonyService] Call failed:', reason);
      this.handleCallEnd(typeof reason === 'string' ? reason : 'Call failed');
    });
  }

  public answerIncomingCall(): void {
    if (this.incomingCallObj && typeof this.incomingCallObj.answer === 'function') {
      try {
        this.incomingCallObj.answer();
      } catch (err) {
        console.warn('[TelephonyService] Answer error:', err);
      }
    }
    this.session.state = 'connected';
    this.session.startedAt = Date.now();
    this.applyAudioRouting(this.session.isSpeaker);
    this.startTimer();
    this.startHeartbeat();
    this.notify();
  }

  public rejectIncomingCall(): void {
    if (this.incomingCallObj && typeof this.incomingCallObj.reject === 'function') {
      try {
        this.incomingCallObj.reject();
      } catch (err) {
        console.warn('[TelephonyService] Reject error:', err);
      }
    }
    this.incomingCallObj = null;
    this.handleCallEnd('Call rejected');
  }

  public async startCall(
    destinationPhone: string,
    contactName: string = 'Contact Lead',
    leadId: number | string | null = null
  ): Promise<{ success: boolean; sessionId?: string; error?: string }> {
    if (this.isCallActive()) {
      return { success: false, error: 'A call is already in progress.' };
    }

    const cleanDest = destinationPhone.startsWith('+')
      ? destinationPhone
      : `+91${destinationPhone.replace(/\D/g, '').slice(-10)}`;

    this.session = {
      sessionId: null,
      destinationPhone: cleanDest,
      contactName: contactName || 'Contact Lead',
      leadId: leadId ? String(leadId) : null,
      state: 'connecting',
      durationSeconds: 0,
      isMuted: false,
      isSpeaker: false,
      isHeld: false,
      errorMessage: null,
      startedAt: null
    };
    this.notify();

    // Ensure registration
    if (this.registrationState !== 'REGISTERED') {
      const ready = await this.initPlivoWebRTC();
      if (!ready || this.getRegistrationState() !== 'REGISTERED' || !this.plivoClient || typeof this.plivoClient.call !== 'function') {
        this.session.state = 'failed';
        this.session.errorMessage =
          'Telephony network unavailable: Plivo registration failed. Please check your internet connection or use Direct SIM.';
        this.notify();
        return { success: false, error: this.session.errorMessage };
      }
    }

    // Ensure remote audio playback element is ready and full volume
    this.ensureAudioElement();

    // Create session on backend
    try {
      const cleanLeadId =
        leadId && String(leadId).trim() !== '' && !isNaN(parseInt(String(leadId)))
          ? parseInt(String(leadId))
          : null;

      const initResp = await apiService.post<any>('/telephony/plivo/browser/call/initiate', {
        destination_phone: cleanDest,
        lead_id: cleanLeadId
      });

      let sessData: any = null;
      if (initResp && initResp.success && initResp.data) {
        sessData = initResp.data;
      } else if (initResp && (initResp as any).call_session_id) {
        sessData = initResp;
      } else {
        sessData = { call_session_id: 'vcs_mob_' + Date.now() };
      }

      this.session.sessionId = sessData.call_session_id || 'vcs_mob_' + Date.now();
      this.session.state = 'ringing';
      this.session.isSpeaker = false;
      this.applyAudioRouting(false);
      this.notify();

      // Dispatch Plivo Call
      const extraHeaders = {
        'X-PH-Call-Session-ID': this.session.sessionId,
        'X-PH-Lead-ID': String(leadId || '')
      };

      this.plivoClient.call(cleanDest, extraHeaders);

      // Start Session Polling
      if (this.session.sessionId) {
        this.startSessionStatusPolling(this.session.sessionId);
      }

      return { success: true, sessionId: this.session.sessionId || undefined };
    } catch (err: any) {
      console.error('[TelephonyService] Outbound dial error:', err);
      this.session.state = 'failed';
      this.session.errorMessage = err.message || 'Call placement failed';
      this.notify();
      return { success: false, error: this.session.errorMessage || undefined };
    }
  }

  private async applyAudioRouting(speakerOn: boolean): Promise<void> {
    try {
      const cap = (window as any).Capacitor;
      if (cap?.Plugins?.AudioRouting) {
        await cap.Plugins.AudioRouting.setSpeakerphoneOn({ enabled: speakerOn });
      }
    } catch (err) {
      console.warn('[TelephonyService] Audio routing error:', err);
    }
  }

  private async resetAudioRouting(): Promise<void> {
    try {
      const cap = (window as any).Capacitor;
      if (cap?.Plugins?.AudioRouting) {
        await cap.Plugins.AudioRouting.resetAudioMode();
      }
    } catch (err) {
      console.warn('[TelephonyService] Audio reset error:', err);
    }
  }

  private startSessionStatusPolling(sessionId: string): void {
    if (this.sessionPollInterval) clearInterval(this.sessionPollInterval);

    this.sessionPollInterval = setInterval(async () => {
      if (!this.isCallActive()) {
        clearInterval(this.sessionPollInterval);
        this.sessionPollInterval = null;
        return;
      }

      try {
        const resp = await apiService.get<any>(`/telephony/plivo/calls/session-status/${sessionId}`);
        const data = resp?.data || resp;
        if (data) {
          const s = String(data.status || data.call_state || '').toLowerCase();
          if (
            (s === 'in-progress' || s === 'answered' || s === 'connected' || data.is_connected === true) &&
            this.session.state !== 'connected'
          ) {
            this.session.state = 'connected';
            this.session.startedAt = Date.now();
            this.applyAudioRouting(this.session.isSpeaker);
            this.startTimer();
            this.notify();
          } else if (
            s === 'completed' ||
            s === 'failed' ||
            s === 'hungup' ||
            s === 'busy' ||
            s === 'no-answer' ||
            s === 'rejected'
          ) {
            this.handleCallEnd(`Call finished (${s})`);
          }
        }
      } catch (_) {}
    }, 1200);
  }

  private startTimer(): void {
    if (this.callTimerInterval) clearInterval(this.callTimerInterval);
    this.session.durationSeconds = 0;
    this.callTimerInterval = setInterval(() => {
      this.session.durationSeconds++;
      this.notify();
    }, 1000);
  }

  private startHeartbeat(): void {
    if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);
    this.heartbeatInterval = setInterval(async () => {
      if (this.session.state === 'connected' && this.session.sessionId) {
        try {
          await apiService.post('/telephony/plivo/browser/register', {
            is_registered: true,
            in_call: true,
            call_session_id: this.session.sessionId
          });
        } catch (_) {}
      }
    }, 15000);
  }

  private handleCallEnd(reason: string = 'Call ended'): void {
    if (this.callTimerInterval) {
      clearInterval(this.callTimerInterval);
      this.callTimerInterval = null;
    }
    if (this.sessionPollInterval) {
      clearInterval(this.sessionPollInterval);
      this.sessionPollInterval = null;
    }
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }

    if (this.localAudioStream) {
      try {
        this.localAudioStream.getTracks().forEach((t) => t.stop());
      } catch (_) {}
      this.localAudioStream = null;
    }

    const sid = this.session.sessionId;
    const durSecs = this.session.durationSeconds || 0;

    if (sid) {
      apiService.post('/telephony/plivo/browser/call/end', {
        call_session_id: sid,
        duration_seconds: durSecs
      }).catch(() => {});

      apiService.post('/telephony/plivo/browser/call-event', {
        call_session_id: sid,
        event_type: 'ended',
        duration_seconds: durSecs
      }).catch(() => {});
    }

    this.resetAudioRouting();
    this.saveRecentCall(this.session.destinationPhone, this.session.contactName, this.session.durationSeconds);

    this.session.state = 'ended';
    this.session.isSpeaker = false;
    this.notify();

    // Reset to idle after 1.5s
    setTimeout(() => {
      if (this.session.state === 'ended') {
        this.session.state = 'idle';
        this.session.sessionId = null;
        this.session.durationSeconds = 0;
        this.notify();
      }
    }, 1500);
  }

  public async endCall(): Promise<void> {
    if (this.plivoClient && typeof this.plivoClient.hangup === 'function') {
      try {
        this.plivoClient.hangup();
      } catch (_) {}
    }
    this.handleCallEnd('Call ended by user');
  }

  public toggleMute(): boolean {
    this.session.isMuted = !this.session.isMuted;
    if (this.plivoClient) {
      try {
        if (this.session.isMuted && typeof this.plivoClient.mute === 'function') {
          this.plivoClient.mute();
        } else if (!this.session.isMuted && typeof this.plivoClient.unmute === 'function') {
          this.plivoClient.unmute();
        }
      } catch (_) {}
    }
    if (this.localAudioStream) {
      this.localAudioStream.getAudioTracks().forEach((t) => (t.enabled = !this.session.isMuted));
    }
    this.notify();
    return this.session.isMuted;
  }

  public async toggleSpeaker(): Promise<boolean> {
    const nextSpeakerState = !this.session.isSpeaker;
    try {
      const cap = (window as any).Capacitor;
      if (cap?.Plugins?.AudioRouting) {
        const res = await cap.Plugins.AudioRouting.setSpeakerphoneOn({ enabled: nextSpeakerState });
        this.session.isSpeaker = (res && typeof res.speakerOn === 'boolean') ? res.speakerOn : nextSpeakerState;
      } else {
        this.session.isSpeaker = nextSpeakerState;
      }
    } catch (err) {
      console.warn('[TelephonyService] Speakerphone toggle warning:', err);
      this.session.isSpeaker = nextSpeakerState;
    }
    this.notify();
    return this.session.isSpeaker;
  }

  public toggleHold(): boolean {
    this.session.isHeld = !this.session.isHeld;
    this.notify();
    return this.session.isHeld;
  }

  public sendDTMF(digit: string): void {
    if (this.plivoClient && typeof this.plivoClient.sendDTMF === 'function') {
      try {
        this.plivoClient.sendDTMF(digit);
      } catch (err) {
        console.warn('[TelephonyService] DTMF send error:', err);
      }
    }
    this.playKeyTone();
  }

  public playKeyTone(): void {
    try {
      const AudioCtx = (window as any).AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(350, ctx.currentTime);
      gain.gain.setValueAtTime(0.04, ctx.currentTime);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.05);
    } catch (_) {}
  }

  public triggerDirectSimCall(phone: string): void {
    const cleanNumber = phone.replace(/[^+\d]/g, '');
    if (cleanNumber && typeof window !== 'undefined') {
      window.location.href = `tel:${cleanNumber}`;
    }
  }

  public async triggerMyOperatorCall(phone: string, leadId?: number | null): Promise<void> {
    const res = await apiService.post<any>('/crm/dialer/click-to-call', {
      customer_phone: phone,
      lead_id: leadId ?? null
    });
    if (!res.success) {
      throw new Error((res as any)?.error?.detail || 'MyOperator dispatch failed');
    }
  }

  private saveRecentCall(phone: string, name: string, duration: number): void {
    if (typeof localStorage === 'undefined' || !phone) return;
    try {
      const stored = localStorage.getItem('mnr_softphone_call_logs');
      const list = stored ? JSON.parse(stored) : [];
      list.unshift({
        phone_number: phone,
        contact_name: name || 'Contact Lead',
        duration_seconds: duration,
        timestamp: new Date().toISOString(),
        call_type: 'OUTGOING',
        source: 'softphone'
      });
      if (list.length > 50) list.pop();
      localStorage.setItem('mnr_softphone_call_logs', JSON.stringify(list));
    } catch (_) {}
  }
}

export const telephonyService = new TelephonyService();
