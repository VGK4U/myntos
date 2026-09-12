/**
 * Authoritative Telephony Service & Canonical Call Session Engine — MyntOS Mobile
 * Unified Plivo WebRTC client, session polling, active call state machine, and audio controls.
 * Implements the Canonical Telephony Audio Architecture with low-level Platform Audio Adapter.
 * Reusable across SoftphonePage, SoftphoneModal, and AutoDialerPage.
 */

import { apiService } from './api.service';
import { platformAudioAdapter, IPlatformAudioAdapter } from './platform-audio.adapter';

export type CallState = 'idle' | 'initializing' | 'connecting' | 'ringing' | 'connected' | 'ended' | 'failed';
export type RegistrationState = 'UNINITIALIZED' | 'CONNECTING' | 'REGISTERED' | 'REGISTRATION_FAILED';
export type RecordingState = 'NONE' | 'PROCESSING' | 'AVAILABLE' | 'FAILED';

export interface TelephonyCallSession {
  sessionId: string | null;
  destinationPhone: string;
  contactName: string;
  leadId: number | string | null;
  state: CallState;
  recordingState: RecordingState;
  recordingUrl: string | null;
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
  private audioAdapter: IPlatformAudioAdapter = platformAudioAdapter;

  // Mic Boost & Audio Enhancement State
  private boostedMicTrack: MediaStreamTrack | null = null;
  private micBoostCtx: AudioContext | null = null;
  private isMicBoostApplied: boolean = false;
  private _isDialInProgress: boolean = false;

  // Active Session State
  private session: TelephonyCallSession = {
    sessionId: null,
    destinationPhone: '',
    contactName: '',
    leadId: null,
    state: 'idle',
    recordingState: 'NONE',
    recordingUrl: null,
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

  public isTerminalState(state?: CallState): boolean {
    const s = state || this.session.state;
    return s === 'ended' || s === 'failed';
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
    this.audioAdapter.initializeAudio();
  }

  /**
   * TRUE USER-GESTURE AUDIO UNLOCK (SYNCHRONOUS ENTRY POINT)
   * Must be called in the direct user click/touch handler BEFORE any await.
   */
  public prepareAudioOnUserGesture(): boolean {
    return this.audioAdapter.unlockAudio();
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
        this.audioAdapter.initializeAudio();

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

        // Pre-warm local microphone tracks with hardware AEC
        if (hasMedia) {
          try {
            const testStream = await this.audioAdapter.startMicrophone();
            if (testStream) {
              testStream.getTracks().forEach((t) => t.stop());
              console.log('[TelephonyService] Microphone AEC initialized and ready.');
            }
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
                enableNoiseReduction: true,
                audioConstraints: audioConstraints,
                audioElementOption: {
                  remoteAudioId: 'plivoRemoteAudio'
                }
              });
              this.plivoClient = sdk.client || sdk;
            } else if (PlivoConstructor.Client) {
              this.plivoClient = new PlivoConstructor.Client({
                enableNoiseReduction: true,
                audioConstraints: audioConstraints
              });
            }

            if (this.plivoClient) {
              // Attach canonical remote audio element to Plivo WebRTC client
              const audioEl = this.audioAdapter.ensureRemoteAudioSink();
              if (audioEl && typeof this.plivoClient.setAudioElement === 'function') {
                this.plivoClient.setAudioElement(audioEl);
              }
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
        recordingState: 'NONE',
        recordingUrl: null,
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

    this.plivoClient.on('onCallRinging', (callInfo: any) => {
      console.log('[TelephonyService] Call ringing on destination device:', callInfo);
      if (this.isTerminalState() || this.session.state === 'connected') return;
      this.session.state = 'ringing';
      this.audioAdapter.startRingback();
      this.notify();
    });

    this.plivoClient.on('onRinging', (callInfo: any) => {
      console.log('[TelephonyService] Call ringing on destination device:', callInfo);
      if (this.isTerminalState() || this.session.state === 'connected') return;
      this.session.state = 'ringing';
      this.audioAdapter.startRingback();
      this.notify();
    });

    this.plivoClient.on('onCallConnected', async (callInfo: any) => {
      await this.handleCallConnected('onCallConnected', callInfo);
    });

    this.plivoClient.on('onCallAnswered', async (callInfo: any) => {
      await this.handleCallConnected('onCallAnswered', callInfo);
    });

    this.plivoClient.on('onMediaConnected', async (callInfo: any) => {
      await this.handleCallConnected('onMediaConnected', callInfo);
    });

    this.plivoClient.on('onCallTerminated', () => {
      console.log('[TelephonyService] Call terminated');
      this.handleCallEnd('Call ended');
    });

    this.plivoClient.on('onCallFailed', (reason: any) => {
      console.warn('[TelephonyService] Call failed:', reason);
      this.handleCallEnd(typeof reason === 'string' ? reason : 'Call failed', true);
    });
  }

  /**
   * CANONICAL IDEMPOTENT CALL CONNECTED HANDLER
   * Authoritative convergence point for onCallConnected, onCallAnswered, onMediaConnected,
   * user manual answer, and backend session watcher.
   */
  private async handleCallConnected(sourceEvent: string, callInfo?: any): Promise<void> {
    console.log(`[TelephonyService] handleCallConnected invoked from '${sourceEvent}':`, callInfo);

    // 1. Ignore if session is already terminal
    if (this.isTerminalState()) {
      console.log(`[TelephonyService] Ignoring '${sourceEvent}': Session is already terminal (${this.session.state})`);
      return;
    }

    // 2. Stop ringback immediately upon any connected or media event
    this.audioAdapter.stopRingback();

    // 3. Resolve remote MediaStream from Plivo SDK / callInfo / PeerConnection / Plivo remoteview
    let remoteStream: MediaStream | undefined = undefined;
    if (callInfo?.stream instanceof MediaStream) {
      remoteStream = callInfo.stream;
    } else if (callInfo?.mediaStream instanceof MediaStream) {
      remoteStream = callInfo.mediaStream;
    } else if (callInfo?.remoteStream instanceof MediaStream) {
      remoteStream = callInfo.remoteStream;
    } else {
      // Trace from active Plivo WebRTC PeerConnection
      try {
        const pc =
          (typeof this.plivoClient?._getPeerConnection === 'function' ? this.plivoClient._getPeerConnection()?.pc : null) ||
          this.plivoClient?._currentSession?.session?.connection ||
          this.plivoClient?._currentSession?.session?._connection;
        if (pc) {
          if (typeof pc.getRemoteStreams === 'function') {
            const streams = pc.getRemoteStreams();
            if (streams && streams.length > 0) {
              remoteStream = streams[0];
            }
          }
          if (!remoteStream && typeof pc.getReceivers === 'function') {
            const audioTracks = pc
              .getReceivers()
              .map((r: any) => r.track)
              .filter((t: any) => t && t.kind === 'audio' && t.readyState === 'live');
            if (audioTracks.length > 0) {
              remoteStream = new MediaStream(audioTracks);
            }
          }
        }
      } catch (pcErr) {
        console.warn('[TelephonyService] Remote stream extraction notice:', pcErr);
      }

      // Check Plivo SDK internal remoteview sink (#plivo_webrtc_remoteview)
      if (!remoteStream && typeof document !== 'undefined') {
        const plivoRemoteEl = document.getElementById('plivo_webrtc_remoteview') as HTMLAudioElement | null;
        if (plivoRemoteEl?.srcObject instanceof MediaStream) {
          remoteStream = plivoRemoteEl.srcObject;
          console.log('[TelephonyService] Acquired remote MediaStream from plivo_webrtc_remoteview.');
        }
      }
    }

    // 4. Attach REAL remote MediaStream to canonical #plivoRemoteAudio sink and play
    await this.audioAdapter.attachRemoteStream(remoteStream);

    // If stream was not yet populated due to Plivo internal ontrack timeout (100ms), bridge with micro-recheck
    if (!remoteStream && typeof document !== 'undefined') {
      setTimeout(() => {
        if (!this.isTerminalState()) {
          const deferredEl = document.getElementById('plivo_webrtc_remoteview') as HTMLAudioElement | null;
          if (deferredEl?.srcObject instanceof MediaStream) {
            console.log('[TelephonyService] Deferred remote MediaStream acquired from plivo_webrtc_remoteview.');
            void this.audioAdapter.attachRemoteStream(deferredEl.srcObject);
          }
        }
      }, 150);
    }

    // 5. Apply confirmed audio routing (earpiece by default, speaker if user toggled)
    await this.audioAdapter.setAudioRoute(this.session.isSpeaker);

    // Start Android InCallService for lock-screen & background microphone retention (Issue #3)
    try {
      const cap = (window as any).Capacitor;
      if (cap?.Plugins?.AudioRouting?.startInCallService) {
        cap.Plugins.AudioRouting.startInCallService({
          title: this.session.contactName || 'Active Softphone Call',
          text: this.session.destinationPhone ? `In call with ${this.session.destinationPhone}` : 'Call in progress'
        }).catch(() => {});
      }
    } catch (_) {}

    // Apply modest mic boost (+2.5 dB / 1.33x with limiter) (Issue #1)
    void this.applyModestMicBoost();

    // 6. Transition state idempotently: ringing/connecting -> connected
    const wasAlreadyConnected = this.session.state === 'connected';
    this.session.state = 'connected';
    this.session.recordingState = 'PROCESSING';

    if (!wasAlreadyConnected) {
      // Set startedAt exactly once
      if (!this.session.startedAt) {
        this.session.startedAt = Date.now();
      }
      // Start duration timer and heartbeat exactly once
      this.startTimer();
      this.startHeartbeat();
      this.notify();
    }
  }

  public answerIncomingCall(): void {
    // MANDATE 1: TRUE USER-GESTURE AUDIO UNLOCK BEFORE ANY ASYNC OPERATION
    this.audioAdapter.unlockAudio();

    if (this.incomingCallObj && typeof this.incomingCallObj.answer === 'function') {
      try {
        this.incomingCallObj.answer();
      } catch (err) {
        console.warn('[TelephonyService] Answer error:', err);
      }
    }
    void this.handleCallConnected('user-answer-incoming');
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
    // MANDATE 1: TRUE USER-GESTURE AUDIO UNLOCK BEFORE THE FIRST AWAIT!
    // The browser media unlock (HTMLAudioElement.play() and AudioContext.resume())
    // MUST occur synchronously at the very entry point of the call stack before any await.
    this.audioAdapter.unlockAudio();

    if (this._isDialInProgress || this.isCallActive()) {
      return { success: false, error: 'A call is already in progress.' };
    }
    this._isDialInProgress = true;

    if (!destinationPhone || typeof destinationPhone !== 'string' || destinationPhone.includes('•') || destinationPhone.includes('*')) {
      this._isDialInProgress = false;
      return { success: false, error: 'Please provide a valid 10-digit phone number.' };
    }

    const digits = destinationPhone.replace(/\D/g, '');
    if (digits.length < 10) {
      this._isDialInProgress = false;
      return { success: false, error: 'Please enter a valid 10-digit phone number.' };
    }

    const cleanDest = `+91${digits.slice(-10)}`;

    this.session = {
      sessionId: null,
      destinationPhone: cleanDest,
      contactName: contactName || 'Contact Lead',
      leadId: leadId ? String(leadId) : null,
      state: 'connecting',
      recordingState: 'NONE',
      recordingUrl: null,
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
        this._isDialInProgress = false;
        this.session.state = 'failed';
        this.session.errorMessage =
          'Telephony network unavailable: Plivo registration failed. Please check your internet connection or use Direct SIM.';
        this.notify();
        setTimeout(() => {
          if (this.session.state === 'failed') {
            this.session.state = 'idle';
            this.session.errorMessage = null;
            this.notify();
          }
        }, 1500);
        return { success: false, error: this.session.errorMessage };
      }
    }

    // Ensure remote audio playback element is ready and full volume
    this.audioAdapter.ensureRemoteAudioSink();

    // Create session on backend with lead_id preserved
    try {
      const cleanLeadId =
        leadId && String(leadId).trim() !== '' && !isNaN(parseInt(String(leadId)))
          ? parseInt(String(leadId))
          : null;

      const initResp = await apiService.post<any>('/telephony/plivo/browser/call/initiate', {
        destination_phone: cleanDest,
        lead_id: cleanLeadId,
        is_webrtc: true,
        dispatch_provider_call: false
      });

      let sessData: any = null;
      if (initResp && initResp.success && initResp.data) {
        sessData = initResp.data;
      } else if (initResp && (initResp as any).call_session_id) {
        sessData = initResp;
      } else {
        throw new Error(initResp?.error || initResp?.message || initResp?.detail || 'Failed to initiate telephony session on server');
      }

      if (!sessData?.call_session_id) {
        throw new Error('Server returned invalid call session ID');
      }

      this.session.sessionId = sessData.call_session_id;
      this.session.state = 'ringing';
      this.session.isSpeaker = false;
      this.audioAdapter.setAudioRoute(false);

      // Start audible synthetic ringback during ringing phase
      this.audioAdapter.startRingback();
      this.notify();

      // Dispatch Plivo Call with session and lead headers
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
      this._isDialInProgress = false;
      this.audioAdapter.stopRingback();
      this.session.state = 'failed';
      this.session.errorMessage = err.message || 'Call placement failed';
      this.notify();
      setTimeout(() => {
        if (this.session.state === 'failed') {
          this.session.state = 'idle';
          this.session.errorMessage = null;
          this.notify();
        }
      }, 1500);
      return { success: false, error: this.session.errorMessage || undefined };
    }
  }

  private startSessionStatusPolling(sessionId: string): void {
    if (this.sessionPollInterval) clearInterval(this.sessionPollInterval);

    this.sessionPollInterval = setInterval(async () => {
      if (!this.isCallActive() || this.isTerminalState()) {
        clearInterval(this.sessionPollInterval);
        this.sessionPollInterval = null;
        return;
      }

      try {
        const resp = await apiService.get<any>(`/telephony/plivo/calls/session-status/${sessionId}`);
        if (this.isTerminalState()) {
          clearInterval(this.sessionPollInterval);
          this.sessionPollInterval = null;
          return;
        }
        const data = resp?.data || resp;
        if (data) {
          const s = String(data.status || data.call_state || '').toLowerCase();
          if (
            (s === 'in-progress' || s === 'answered' || s === 'connected' || data.is_connected === true) &&
            !this.isTerminalState() &&
            this.session.state !== 'connected'
          ) {
            console.log('[TelephonyService] Carrier session poller detected connected call state');
            await this.handleCallConnected('session-status-polling', data);
          } else if (
            s === 'completed' ||
            s === 'failed' ||
            s === 'hungup' ||
            s === 'busy' ||
            s === 'no-answer' ||
            s === 'rejected'
          ) {
            const isFailed = (s === 'failed' || s === 'busy' || s === 'no-answer' || s === 'rejected');
            this.handleCallEnd(`Call finished (${s})`, isFailed);
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

  private handleCallEnd(reason: string = 'Call ended', isFailed: boolean = false): void {
    this._isDialInProgress = false;
    // Monotonic Terminal State Lock: Once terminal, no subsequent event or callback can modify it
    if (this.isTerminalState()) {
      console.log(`[TelephonyService] handleCallEnd ignored: already in terminal state (${this.session.state})`);
      return;
    }

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

    // Authoritative audio cleanup: stop ringback, pause sink, stop mic, reset route
    this.cleanupMicBoost();
    this.audioAdapter.cleanupAudio();

    const sid = this.session.sessionId;
    const durSecs = this.session.durationSeconds || 0;

    if (sid) {
      apiService.post('/telephony/plivo/browser/call/end', {
        call_session_id: sid,
        duration_seconds: durSecs
      }).catch(() => {});

      apiService.post('/telephony/plivo/browser/call-event', {
        call_session_id: sid,
        event_type: isFailed ? 'failed' : 'ended',
        duration_seconds: durSecs
      }).catch(() => {});
    }

    this.saveRecentCall(this.session.destinationPhone, this.session.contactName, this.session.durationSeconds);

    this.session.state = isFailed ? 'failed' : 'ended';
    if (isFailed) {
      this.session.errorMessage = reason;
    }
    this.session.isSpeaker = false;
    this.notify();

    // Reset to idle after 1.5s
    setTimeout(() => {
      if (this.session.state === 'ended' || this.session.state === 'failed') {
        this.session.state = 'idle';
        this.session.sessionId = null;
        this.session.durationSeconds = 0;
        this.session.errorMessage = null;
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
    if (this.boostedMicTrack) {
      this.boostedMicTrack.enabled = !this.session.isMuted;
    }
    this.notify();
    return this.session.isMuted;
  }

  public async toggleSpeaker(): Promise<boolean> {
    const nextSpeakerState = !this.session.isSpeaker;
    const finalSpeaker = await this.audioAdapter.setAudioRoute(nextSpeakerState);
    this.session.isSpeaker = finalSpeaker;
    this.notify();
    return this.session.isSpeaker;
  }

  public toggleHold(): boolean {
    this.session.isHeld = !this.session.isHeld;
    const audioEl = this.audioAdapter.ensureRemoteAudioSink();
    if (audioEl) {
      audioEl.muted = this.session.isHeld;
    }
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

  private async applyModestMicBoost(): Promise<void> {
    try {
      if (this.isMicBoostApplied) return;
      const pc =
        (typeof this.plivoClient?._getPeerConnection === 'function' ? this.plivoClient._getPeerConnection()?.pc : null) ||
        this.plivoClient?._currentSession?.session?.connection ||
        this.plivoClient?._currentSession?.session?._connection;

      if (!pc || typeof pc.getSenders !== 'function') return;

      const senders = pc.getSenders();
      const audioSender = senders.find((s: any) => s.track && s.track.kind === 'audio');
      if (!audioSender || !audioSender.track) return;

      const originalTrack = audioSender.track;
      if (originalTrack === this.boostedMicTrack) return;

      const AudioCtxClass = (window as any).AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtxClass) return;

      console.log('[TelephonyService] Applying modest mic boost (+2.5 dB / 1.33x with limiter)...');
      const ctx: AudioContext = new AudioCtxClass();
      this.micBoostCtx = ctx;
      if (ctx.state === 'suspended') {
        await ctx.resume();
      }
      if (ctx.state !== 'running') {
        console.warn('[TelephonyService] AudioContext is not running (state:', ctx.state, '). Skipping mic boost to preserve audio.');
        return;
      }

      const inputStream = new MediaStream([originalTrack]);
      const sourceNode = ctx.createMediaStreamSource(inputStream);

      // Gain +2.5 dB (1.33x factor)
      const gainNode = ctx.createGain();
      gainNode.gain.setValueAtTime(1.33, ctx.currentTime);

      // Dynamics limiter
      const compressor = ctx.createDynamicsCompressor();
      compressor.threshold.setValueAtTime(-14, ctx.currentTime);
      compressor.knee.setValueAtTime(6, ctx.currentTime);
      compressor.ratio.setValueAtTime(4, ctx.currentTime);
      compressor.attack.setValueAtTime(0.003, ctx.currentTime);
      compressor.release.setValueAtTime(0.05, ctx.currentTime);

      const destNode = ctx.createMediaStreamDestination();
      sourceNode.connect(gainNode);
      gainNode.connect(compressor);
      compressor.connect(destNode);

      const boostedTracks = destNode.stream.getAudioTracks();
      if (boostedTracks.length === 0) return;

      const boostedTrack = boostedTracks[0];
      this.boostedMicTrack = boostedTrack;

      await audioSender.replaceTrack(boostedTrack);
      this.isMicBoostApplied = true;
      console.log('[TelephonyService] Modest mic boost applied successfully (+2.5 dB / 1.33x).');
    } catch (err) {
      console.warn('[TelephonyService] Notice applying mic boost:', err);
    }
  }

  private cleanupMicBoost(): void {
    try {
      if (this.boostedMicTrack) {
        try { this.boostedMicTrack.stop(); } catch (_) {}
        this.boostedMicTrack = null;
      }
      if (this.micBoostCtx) {
        try { this.micBoostCtx.close(); } catch (_) {}
        this.micBoostCtx = null;
      }
      this.isMicBoostApplied = false;
      console.log('[TelephonyService] Mic boost cleaned up.');
    } catch (err) {
      console.warn('[TelephonyService] Notice cleaning up mic boost:', err);
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

if (typeof window !== 'undefined') {
  (window as any).telephonyService = telephonyService;
}
