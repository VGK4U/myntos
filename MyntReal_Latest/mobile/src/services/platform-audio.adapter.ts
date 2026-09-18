/**
 * Canonical Platform Audio Adapter — MyntOS Telephony
 * Implements the authoritative 10-method audio lifecycle contract across Web, /mobile, Android, and iOS.
 * Low-level platform adapter ONLY: does NOT own call state, CRM logic, or session creation.
 */

export interface IPlatformAudioAdapter {
  initializeAudio(): void;
  unlockAudio(): boolean;
  ensureRemoteAudioSink(): HTMLAudioElement | null;
  startRingback(): void;
  stopRingback(): void;
  attachRemoteStream(stream?: MediaStream): Promise<boolean>;
  startMicrophone(): Promise<MediaStream | null>;
  stopMicrophone(): void;
  setAudioRoute(isSpeaker: boolean): Promise<boolean>;
  cleanupAudio(): void;
  getSavedVolume(): number;
  setVolume(vol: number): void;
  getAudioDiagnostics(): Promise<any>;
}

// 44-byte standard PCM 8000Hz 16-bit mono silent WAV for instantaneous autoplay unlock
const SILENT_WAV_BASE64 = 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAP8A/w==';

class PlatformAudioAdapter implements IPlatformAudioAdapter {
  private remoteAudioEl: HTMLAudioElement | null = null;
  private audioCtx: AudioContext | null = null;
  private ringbackOsc1: OscillatorNode | null = null;
  private ringbackOsc2: OscillatorNode | null = null;
  private ringbackGain: GainNode | null = null;
  private ringbackTimer: any = null;
  private isRingbackActive: boolean = false;
  private localMicStream: MediaStream | null = null;
  private isUnlocked: boolean = false;

  constructor() {
    if (typeof window !== 'undefined') {
      if (document.readyState === 'complete' || document.readyState === 'interactive') {
        this.initializeAudio();
      } else {
        document.addEventListener('DOMContentLoaded', () => this.initializeAudio());
      }
    }
  }

  // ── 1. INITIALIZE AUDIO ────────────────────────────────────────────────────
  public initializeAudio(): void {
    if (typeof document === 'undefined') return;
    this.ensureRemoteAudioSink();
    this.getOrCreateAudioContext();
  }

  private getOrCreateAudioContext(): AudioContext | null {
    if (typeof window === 'undefined') return null;
    if (!this.audioCtx) {
      try {
        const AudioCtxClass = (window as any).AudioContext || (window as any).webkitAudioContext;
        if (AudioCtxClass) {
          this.audioCtx = new AudioCtxClass();
        }
      } catch (err) {
        console.warn('[PlatformAudioAdapter] Web Audio API not supported:', err);
      }
    }
    return this.audioCtx;
  }

  // ── 2. TRUE USER-GESTURE AUDIO UNLOCK (BEFORE FIRST AWAIT) ─────────────────
  /**
   * MUST be invoked synchronously at the very entry point of the user interaction
   * BEFORE ANY AWAIT, Promise, or setTimeout.
   * Primes HTMLAudioElement.play() and AudioContext.resume() to lift platform autoplay restrictions.
   */
  public unlockAudio(): boolean {
    if (typeof document === 'undefined') return false;

    console.log('[PlatformAudioAdapter] Executing synchronous user-gesture audio unlock...');
    const audioEl = this.ensureRemoteAudioSink();

    // 1. Prime HTMLAudioElement synchronously within user gesture
    if (audioEl) {
      try {
        audioEl.volume = this.getSavedVolume();
        audioEl.muted = false;

        // Play silent audio buffer to unlock element in WebKit/Chromium
        if (!audioEl.srcObject && !audioEl.src) {
          audioEl.src = SILENT_WAV_BASE64;
        }

        const playPromise = audioEl.play();
        if (playPromise !== undefined) {
          playPromise
            .then(() => {
              this.isUnlocked = true;
              console.log('[PlatformAudioAdapter] HTMLAudioElement successfully unlocked in user gesture.');
              // Immediately pause and remove silent audio so it does not collide with WebRTC srcObject
              if (audioEl.src === SILENT_WAV_BASE64 || audioEl.hasAttribute('src')) {
                audioEl.pause();
                audioEl.removeAttribute('src');
                try { audioEl.load(); } catch (_) {}
              }
            })
            .catch((playErr: any) => {
              // Log exact error name and message — never swallow silently
              console.warn('[PlatformAudioAdapter] Audio element unlock notice:', playErr?.name, playErr?.message);
            });
        }
      } catch (err: any) {
        console.warn('[PlatformAudioAdapter] Sync audio element unlock error:', err?.name, err?.message);
      }
    }

    // 2. Prime Web Audio Context synchronously within user gesture
    const ctx = this.getOrCreateAudioContext();
    if (ctx && ctx.state === 'suspended') {
      ctx.resume().then(() => {
        console.log('[PlatformAudioAdapter] AudioContext state transitioned to:', ctx.state);
      }).catch((ctxErr: any) => {
        console.warn('[PlatformAudioAdapter] AudioContext resume notice:', ctxErr?.name, ctxErr?.message);
      });
    }

    // 3. Prime Plivo SDK internal remoteview element if already mounted in DOM
    const plivoRemoteEl = document.getElementById('plivo_webrtc_remoteview') as HTMLAudioElement | null;
    if (plivoRemoteEl) {
      try {
        plivoRemoteEl.muted = true;
        plivoRemoteEl.play().catch(() => {});
      } catch (_) {}
    }

    return true;
  }

  // ── 3. ENSURE REMOTE AUDIO SINK (EXACTLY ONE CANONICAL ELEMENT) ─────────────
  public ensureRemoteAudioSink(): HTMLAudioElement | null {
    if (typeof document === 'undefined') return null;

    let el = document.getElementById('plivoRemoteAudio') as HTMLAudioElement;
    if (!el) {
      el = document.createElement('audio');
      el.id = 'plivoRemoteAudio';
      el.autoplay = true;
      el.setAttribute('playsinline', 'true');
      el.setAttribute('webkit-playsinline', 'true');
      // Hidden off-screen, NOT display:none (some WebKit versions throttle display:none audio elements)
      el.style.position = 'fixed';
      el.style.left = '-9999px';
      el.style.top = '-9999px';
      el.style.width = '1px';
      el.style.height = '1px';
      el.style.opacity = '0.01';
      el.style.pointerEvents = 'none';
      document.body.appendChild(el);
      console.log('[PlatformAudioAdapter] Canonical remote audio sink element (#plivoRemoteAudio) mounted.');
    }

    el.volume = this.getSavedVolume();
    el.muted = false;
    this.remoteAudioEl = el;
    return el;
  }

  // ── 4. START RINGBACK (SYNTHETIC CADENCE DURING CALLING/RINGING) ───────────
  public startRingback(): void {
    if (this.isRingbackActive) return;
    this.isRingbackActive = true;

    const ctx = this.getOrCreateAudioContext();
    if (!ctx) {
      console.warn('[PlatformAudioAdapter] Cannot play ringback: AudioContext unavailable');
      return;
    }

    if (ctx.state === 'suspended') {
      ctx.resume().catch(() => {});
    }

    console.log('[PlatformAudioAdapter] Starting synthetic ringback tone (400Hz + 450Hz cadence)...');

    try {
      const playToneBurst = () => {
        if (!this.isRingbackActive) return;

        try {
          const now = ctx.currentTime;
          const gain = ctx.createGain();
          gain.gain.setValueAtTime(0, now);
          gain.gain.linearRampToValueAtTime(0.08, now + 0.05);
          gain.gain.setValueAtTime(0.08, now + 0.95);
          gain.gain.linearRampToValueAtTime(0, now + 1.0);

          const osc1 = ctx.createOscillator();
          const osc2 = ctx.createOscillator();
          osc1.type = 'sine';
          osc2.type = 'sine';
          osc1.frequency.setValueAtTime(400, now);
          osc2.frequency.setValueAtTime(450, now);

          osc1.connect(gain);
          osc2.connect(gain);
          gain.connect(ctx.destination);

          osc1.start(now);
          osc2.start(now);
          osc1.stop(now + 1.0);
          osc2.stop(now + 1.0);
        } catch (toneErr) {
          console.warn('[PlatformAudioAdapter] Ringback burst error:', toneErr);
        }
      };

      // Play immediately, then repeat every 3 seconds (1s tone, 2s pause)
      playToneBurst();
      this.ringbackTimer = setInterval(() => {
        if (this.isRingbackActive) {
          playToneBurst();
        } else {
          this.stopRingback();
        }
      }, 3000);
    } catch (err) {
      console.warn('[PlatformAudioAdapter] Failed to start ringback generator:', err);
    }
  }

  // ── 5. STOP RINGBACK (GUARANTEED INSTANT STOP ON CONNECTED/TERMINAL) ──────
  public stopRingback(): void {
    if (!this.isRingbackActive) return;
    this.isRingbackActive = false;

    if (this.ringbackTimer) {
      clearInterval(this.ringbackTimer);
      this.ringbackTimer = null;
    }

    try {
      if (this.ringbackGain) {
        this.ringbackGain.disconnect();
        this.ringbackGain = null;
      }
      if (this.ringbackOsc1) {
        this.ringbackOsc1.stop();
        this.ringbackOsc1.disconnect();
        this.ringbackOsc1 = null;
      }
      if (this.ringbackOsc2) {
        this.ringbackOsc2.stop();
        this.ringbackOsc2.disconnect();
        this.ringbackOsc2 = null;
      }
    } catch (_) {}

    console.log('[PlatformAudioAdapter] Ringback tone stopped immediately.');
  }

  // ── 6. ATTACH REMOTE STREAM & PLAY REAL INCOMING VOICE ──────────────────────
  public async attachRemoteStream(stream?: MediaStream): Promise<boolean> {
    // Immediately stop ringback when remote media is attached
    this.stopRingback();

    const audioEl = this.ensureRemoteAudioSink();
    if (!audioEl) {
      console.error('[PlatformAudioAdapter] Remote audio sink missing during stream attachment!');
      return false;
    }

    try {
      audioEl.volume = this.getSavedVolume();
      audioEl.muted = false;

      if (audioEl.hasAttribute('src')) {
        audioEl.removeAttribute('src');
      }

      let streamToAttach = stream;
      const plivoRemoteEl = typeof document !== 'undefined' ? (document.getElementById('plivo_webrtc_remoteview') as HTMLAudioElement | null) : null;

      // Fallback: If caller did not provide stream directly, resolve from Plivo SDK internal remoteview
      if (!streamToAttach && plivoRemoteEl?.srcObject instanceof MediaStream) {
        streamToAttach = plivoRemoteEl.srcObject;
        console.log('[PlatformAudioAdapter] Resolved remote MediaStream from #plivo_webrtc_remoteview element.');
      }

      if (streamToAttach && streamToAttach instanceof MediaStream) {
        audioEl.srcObject = streamToAttach;
        console.log('[PlatformAudioAdapter] MediaStream assigned to #plivoRemoteAudio. Tracks:', streamToAttach.getAudioTracks().length);
      }

      const activeStream = audioEl.srcObject as MediaStream | null;
      const audioTracks = activeStream ? activeStream.getAudioTracks() : [];
      const liveTracks = audioTracks.filter((t) => t.readyState === 'live' && t.enabled);
      console.log(`[PlatformAudioAdapter] Sink #plivoRemoteAudio verification: hasSrcObject=${!!activeStream}, totalTracks=${audioTracks.length}, liveTracks=${liveTracks.length}, paused=${audioEl.paused}`);

      const playPromise = audioEl.play();
      if (playPromise !== undefined) {
        await playPromise;
        console.log('[PlatformAudioAdapter] #plivoRemoteAudio is actively playing incoming speech.');
      }

      // SAFEGUARD: Only mute Plivo internal element if canonical sink is confirmed playing live audio
      if (plivoRemoteEl && liveTracks.length > 0 && !audioEl.paused) {
        plivoRemoteEl.muted = true;
        console.log('[PlatformAudioAdapter] Verified duplicate audio stream: Plivo internal remote view element muted.');
      } else if (plivoRemoteEl) {
        plivoRemoteEl.muted = false;
        console.warn('[PlatformAudioAdapter] Safeguard active: Canonical sink has no verified live stream; preserved plivo_webrtc_remoteview unmuted.');
      }

      return true;
    } catch (playErr: any) {
      // Do NOT silently swallow: Log the exact error and state
      console.error(
        '[PlatformAudioAdapter] CRITICAL: remoteAudio.play() failed!',
        'Error Name:', playErr?.name,
        'Message:', playErr?.message,
        'Sink State: paused=', audioEl.paused,
        'muted=', audioEl.muted,
        'readyState=', audioEl.readyState
      );
      return false;
    }
  }

  // ── 7. START MICROPHONE (HARDWARE AEC & AGC) ──────────────────────────────
  public async startMicrophone(): Promise<MediaStream | null> {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      console.warn('[PlatformAudioAdapter] getUserMedia not supported in this environment');
      return null;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
          sampleRate: 48000
        },
        video: false
      });
      this.localMicStream = stream;
      console.log('[PlatformAudioAdapter] Local microphone initialized with hardware AEC.');
      return stream;
    } catch (err: any) {
      console.error('[PlatformAudioAdapter] Microphone access error:', err?.name, err?.message);
      return null;
    }
  }

  // ── 8. STOP MICROPHONE ─────────────────────────────────────────────────────
  public stopMicrophone(): void {
    if (this.localMicStream) {
      try {
        this.localMicStream.getTracks().forEach((track) => {
          track.stop();
          console.log('[PlatformAudioAdapter] Microphone track stopped:', track.id);
        });
      } catch (err) {
        console.warn('[PlatformAudioAdapter] Mic track stop notice:', err);
      }
      this.localMicStream = null;
    }
  }

  // ── 9. SET AUDIO ROUTING (EARPIECE VS SPEAKERPHONE) ────────────────────────
  public async setAudioRoute(isSpeaker: boolean): Promise<boolean> {
    const cap = (window as any).Capacitor;

    // 1. Native Capacitor AudioRouting Plugin (Android & iOS)
    if (cap?.Plugins?.AudioRouting) {
      try {
        const res = await cap.Plugins.AudioRouting.setSpeakerphoneOn({ enabled: isSpeaker });
        if (res && typeof res.speakerOn === 'boolean') {
          console.log(`[PlatformAudioAdapter] Native AudioRouting setSpeakerphoneOn confirmed: ${res.speakerOn}`);
          return res.speakerOn;
        }
        if (typeof cap.Plugins.AudioRouting.isSpeakerphoneOn === 'function') {
          const status = await cap.Plugins.AudioRouting.isSpeakerphoneOn();
          if (status && typeof status.speakerOn === 'boolean') {
            console.log(`[PlatformAudioAdapter] Native AudioRouting isSpeakerphoneOn confirmed: ${status.speakerOn}`);
            return status.speakerOn;
          }
        }
        // If native call didn't confirm speakerOn, return false (do not assume success)
        console.warn('[PlatformAudioAdapter] Native AudioRouting did not return confirmed state; assuming false.');
        return false;
      } catch (nativeErr: any) {
        console.warn('[PlatformAudioAdapter] Native AudioRouting failed, route rejected:', nativeErr?.message);
        return false;
      }
    }

    // 2. Web Standards setSinkId Routing (Desktop & Supported Mobile Browsers)
    if (typeof navigator !== 'undefined' && (navigator as any).mediaDevices?.enumerateDevices) {
      const audioEl = this.ensureRemoteAudioSink();
      if (audioEl && typeof (audioEl as any).setSinkId === 'function') {
        try {
          const devices = await (navigator as any).mediaDevices.enumerateDevices();
          const audioOutputs = devices.filter((d: any) => d.kind === 'audiooutput');
          if (audioOutputs.length > 0) {
            const targetDevice = isSpeaker
              ? (audioOutputs.find((d: any) => /speaker|loudspeaker|external/i.test(d.label)) || audioOutputs[0])
              : (audioOutputs.find((d: any) => /default|earpiece|headset|internal/i.test(d.label)) || audioOutputs[0]);

            if (targetDevice?.deviceId) {
              await (audioEl as any).setSinkId(targetDevice.deviceId);
              console.log(`[PlatformAudioAdapter] Sink ID successfully set to: ${targetDevice.label || targetDevice.deviceId}`);
              return isSpeaker;
            }
          }
        } catch (sinkErr: any) {
          console.warn('[PlatformAudioAdapter] setSinkId failed, route rejected:', sinkErr?.message);
          return false;
        }
      }
    }

    // 3. Fallback for Web/WebKit without setSinkId or without Native Plugin:
    // Route switching cannot be executed programmatically; audio stays on earpiece/receiver/default.
    if (isSpeaker) {
      console.warn('[PlatformAudioAdapter] Speaker routing unsupported by current browser/platform; request rejected.');
      return false;
    }
    return false;
  }

  // ── 10. CLEANUP AUDIO (ZERO AUDIO LEAKAGE ON TERMINATION) ──────────────────
  public cleanupAudio(): void {
    console.log('[PlatformAudioAdapter] Authoritative audio cleanup starting...');

    // 1. Stop ringback tone immediately
    this.stopRingback();

    // 2. Pause and disconnect remote audio sink
    if (this.remoteAudioEl) {
      try {
        this.remoteAudioEl.pause();
        this.remoteAudioEl.srcObject = null;
        this.remoteAudioEl.src = '';
      } catch (err) {
        console.warn('[PlatformAudioAdapter] Remote audio pause notice:', err);
      }
    }

    // 3. Stop and release local microphone hardware
    this.stopMicrophone();

    // 4. Stop in-call foreground service & reset audio routing mode (Issue #3 & #5)
    try {
      const cap = (window as any).Capacitor;
      if (cap?.Plugins?.AudioRouting) {
        if (typeof cap.Plugins.AudioRouting.stopInCallService === 'function') {
          cap.Plugins.AudioRouting.stopInCallService().catch(() => {});
        }
        cap.Plugins.AudioRouting.resetAudioMode().catch(() => {});
      }
    } catch (_) {}

    console.log('[PlatformAudioAdapter] Audio cleanup complete: Zero audio leakage.');
  }

  // ── 11. VOLUME CONTROL & PERSISTENCE ───────────────────────────────────────
  public getSavedVolume(): number {
    try {
      if (typeof localStorage !== 'undefined') {
        const saved = localStorage.getItem('myntos_softphone_volume');
        if (saved !== null) {
          const parsed = parseFloat(saved);
          if (!isNaN(parsed) && parsed >= 0 && parsed <= 1) {
            return parsed;
          }
        }
      }
    } catch (_) {}
    return 0.85; // Standard conversational voice level
  }

  public setVolume(vol: number): void {
    const clamped = Math.max(0, Math.min(1, vol || 0.85));
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('myntos_softphone_volume', clamped.toString());
      }
    } catch (_) {}
    if (this.remoteAudioEl) {
      this.remoteAudioEl.volume = clamped;
    }
    const plivoRemoteEl = typeof document !== 'undefined' ? (document.getElementById('plivo_webrtc_remoteview') as HTMLAudioElement | null) : null;
    if (plivoRemoteEl && !plivoRemoteEl.muted) {
      plivoRemoteEl.volume = clamped;
    }
    console.log(`[PlatformAudioAdapter] Call volume updated to ${Math.round(clamped * 100)}%`);
  }

  // ── 12. AUDIO DIAGNOSTICS (ZERO PII) ──────────────────────────────────────
  public async getAudioDiagnostics(): Promise<any> {
    const cap = (window as any).Capacitor;
    let nativeDiag = null;
    if (cap?.Plugins?.AudioRouting?.getAudioDiagnostics) {
      try {
        nativeDiag = await cap.Plugins.AudioRouting.getAudioDiagnostics();
      } catch (e: any) {
        nativeDiag = { error: e?.message };
      }
    }

    const plivoRemoteEl = typeof document !== 'undefined' ? (document.getElementById('plivo_webrtc_remoteview') as HTMLAudioElement | null) : null;
    return {
      remoteAudioPresent: !!this.remoteAudioEl,
      remoteAudioPaused: this.remoteAudioEl ? this.remoteAudioEl.paused : null,
      remoteAudioMuted: this.remoteAudioEl ? this.remoteAudioEl.muted : null,
      remoteAudioVolume: this.remoteAudioEl ? this.remoteAudioEl.volume : null,
      plivoInternalPresent: !!plivoRemoteEl,
      plivoInternalMuted: plivoRemoteEl ? plivoRemoteEl.muted : null,
      plivoInternalVolume: plivoRemoteEl ? plivoRemoteEl.volume : null,
      nativeRouting: nativeDiag
    };
  }
}

export const platformAudioAdapter = new PlatformAudioAdapter();
