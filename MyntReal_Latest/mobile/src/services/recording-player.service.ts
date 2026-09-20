/**
 * Recording Player Service — MyntOS Mobile
 * Unified service for loud call recording playback across all mobile pages:
 * - Directs native iOS/Android audio session to loud loudspeaker via AudioRouting.setMediaPlaybackMode
 * - Amplifies quiet telephony recordings via Web Audio API GainNode (up to 250% boost)
 * - Provides an interactive floating playback bar with scrubber, volume boost control, and 10s skip
 * - Fully SSR and WKWebView safe (auth blob streaming, zero CORS/origin issues)
 */

import { APP_CONFIG } from '../config/app.config';
import { apiService } from './api.service';

export interface PlaybackOptions {
  key: string;
  rawUrl: string;
  title?: string;
  subtitle?: string;
}

export interface PlaybackState {
  isPlaying: boolean;
  key: string | null;
  currentTime: number;
  duration: number;
  gain: number;
  isLoading: boolean;
}

export type PlaybackListener = (state: PlaybackState) => void;

class RecordingPlayerService {
  private currentKey: string | null = null;
  private currentRawUrl: string | null = null;
  private currentBlobUrl: string | null = null;
  private currentTitle: string = 'Call Recording';
  private currentSubtitle: string = '';

  private audioEl: HTMLAudioElement | null = null;
  private audioCtx: AudioContext | null = null;
  private gainNode: GainNode | null = null;
  private sourceNode: MediaElementAudioSourceNode | null = null;

  private isPlaying: boolean = false;
  private isLoading: boolean = false;
  private currentTime: number = 0;
  private duration: number = 0;
  private currentGainPercent: number = 150; // Default 150% volume boost for loud playback

  private containerEl: HTMLElement | null = null;
  private listeners: Set<PlaybackListener> = new Set();

  constructor() {
    // Restore user preferred volume boost level (defaults to 150%)
    if (typeof window !== 'undefined') {
      try {
        const savedGain = localStorage.getItem('myntos_rec_volume_boost');
        if (savedGain) {
          const parsed = parseInt(savedGain, 10);
          if (!isNaN(parsed) && parsed >= 0 && parsed <= 250) {
            this.currentGainPercent = parsed;
          }
        }
      } catch (_) {}
    }
  }

  // ── 1. PUBLIC API ─────────────────────────────────────────────────────────

  public getCurrentKey(): string | null {
    return this.currentKey;
  }

  public getIsPlaying(): boolean {
    return this.isPlaying;
  }

  public subscribe(listener: PlaybackListener): () => void {
    this.listeners.add(listener);
    // Send immediate initial state
    listener(this.getState());
    return () => {
      this.listeners.delete(listener);
    };
  }

  public getState(): PlaybackState {
    return {
      isPlaying: this.isPlaying,
      key: this.currentKey,
      currentTime: this.currentTime,
      duration: this.duration,
      gain: this.currentGainPercent,
      isLoading: this.isLoading
    };
  }

  private notifyListeners(): void {
    const state = this.getState();
    this.listeners.forEach(fn => {
      try {
        fn(state);
      } catch (err) {
        console.warn('[RecordingPlayer] Listener error:', err);
      }
    });
  }

  /**
   * Main Play / Toggle Entry Point
   */
  public async play(options: PlaybackOptions): Promise<void> {
    const { key, rawUrl, title, subtitle } = options;

    // If clicking same recording that is already playing, toggle pause
    if (this.currentKey === key && this.audioEl) {
      if (this.isPlaying) {
        this.pause();
      } else {
        await this.resume();
      }
      return;
    }

    // Stop and cleanup previous track
    this.stopPlaybackInternal(false);

    this.currentKey = key;
    this.currentRawUrl = rawUrl;
    this.currentTitle = title || 'Call Recording';
    this.currentSubtitle = subtitle || '';
    this.isLoading = true;
    this.currentTime = 0;
    this.duration = 0;
    this.notifyListeners();
    this.renderFloatingPlayer();

    // 1. Force native audio session into loud media playback mode (Loudspeaker)
    await this.enforceMediaPlaybackMode();

    // 2. Fetch authenticated audio blob
    try {
      const token = await apiService.getToken() ||
        localStorage.getItem('auth_token') ||
        localStorage.getItem('staff_token') ||
        localStorage.getItem('token') || '';

      const baseServerUrl = APP_CONFIG.BASE_SERVER_URL;
      let fullUrl = rawUrl;
      if (!fullUrl.startsWith('http://') && !fullUrl.startsWith('https://')) {
        fullUrl = fullUrl.startsWith('/') ? `${baseServerUrl}${fullUrl}` : `${baseServerUrl}/${fullUrl}`;
      }
      const audioUrl = token && !fullUrl.includes('token=')
        ? (fullUrl.includes('?') ? `${fullUrl}&token=${token}` : `${fullUrl}?token=${token}`)
        : fullUrl;

      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const resp = await fetch(audioUrl, { headers });
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }

      const blob = await resp.blob();
      this.currentBlobUrl = URL.createObjectURL(blob);
      await this.startAudioWithBlob(this.currentBlobUrl);
    } catch (err) {
      console.warn('[RecordingPlayer] Blob fetch failed, falling back to direct stream:', err);
      // Fallback: Direct Audio element playback
      try {
        const token = await apiService.getToken() || localStorage.getItem('auth_token') || '';
        let directUrl = rawUrl;
        if (!directUrl.startsWith('http://') && !directUrl.startsWith('https://')) {
          directUrl = directUrl.startsWith('/') ? `${APP_CONFIG.BASE_SERVER_URL}${directUrl}` : `${APP_CONFIG.BASE_SERVER_URL}/${directUrl}`;
        }
        if (token && !directUrl.includes('token=')) {
          directUrl = directUrl.includes('?') ? `${directUrl}&token=${token}` : `${directUrl}?token=${token}`;
        }
        await this.startAudioWithUrl(directUrl);
      } catch (fallbackErr) {
        console.error('[RecordingPlayer] Direct playback failed:', fallbackErr);
        alert('Unable to play recording. Stream unavailable or expired.');
        this.stop();
      }
    }
  }

  public async resume(): Promise<void> {
    if (!this.audioEl) return;
    await this.enforceMediaPlaybackMode();
    try {
      if (this.audioCtx && this.audioCtx.state === 'suspended') {
        await this.audioCtx.resume();
      }
      await this.audioEl.play();
      this.isPlaying = true;
      this.notifyListeners();
      this.updatePlayerUI();
    } catch (e) {
      console.warn('[RecordingPlayer] Resume failed:', e);
    }
  }

  public pause(): void {
    if (this.audioEl && !this.audioEl.paused) {
      this.audioEl.pause();
    }
    this.isPlaying = false;
    this.notifyListeners();
    this.updatePlayerUI();
  }

  public togglePlayPause(): void {
    if (this.isPlaying) {
      this.pause();
    } else {
      this.resume();
    }
  }

  public seek(seconds: number): void {
    if (this.audioEl && !isNaN(seconds)) {
      this.audioEl.currentTime = Math.max(0, Math.min(seconds, this.duration || seconds));
      this.currentTime = this.audioEl.currentTime;
      this.updatePlayerUI();
    }
  }

  public skip(seconds: number): void {
    if (this.audioEl) {
      this.seek(this.audioEl.currentTime + seconds);
    }
  }

  public setVolumeBoost(percent: number): void {
    this.currentGainPercent = Math.max(0, Math.min(percent, 250));
    try {
      localStorage.setItem('myntos_rec_volume_boost', String(this.currentGainPercent));
    } catch (_) {}

    const gainValue = this.currentGainPercent / 100;

    // 1. Web Audio GainNode boost
    if (this.gainNode && this.audioCtx) {
      try {
        this.gainNode.gain.setValueAtTime(gainValue, this.audioCtx.currentTime);
      } catch (_) {
        this.gainNode.gain.value = gainValue;
      }
    }

    // 2. HTMLAudioElement volume
    if (this.audioEl) {
      this.audioEl.volume = Math.min(1.0, Math.max(0.0, gainValue));
    }

    this.updatePlayerUI();
  }

  public stop(): void {
    this.stopPlaybackInternal(true);
  }

  // ── 2. INTERNAL AUDIO PIPELINE ────────────────────────────────────────────

  private async enforceMediaPlaybackMode(): Promise<void> {
    try {
      const cap = (window as any).Capacitor;
      if (cap?.Plugins?.AudioRouting?.setMediaPlaybackMode) {
        await cap.Plugins.AudioRouting.setMediaPlaybackMode();
      } else if (cap?.Plugins?.AudioRouting?.resetAudioMode) {
        await cap.Plugins.AudioRouting.resetAudioMode();
      }
    } catch (e) {
      console.warn('[RecordingPlayer] AudioRouting mode error:', e);
    }
  }

  private initAudioElement(): HTMLAudioElement {
    if (this.audioEl) {
      return this.audioEl;
    }

    const audio = new Audio();
    audio.volume = 1.0;
    this.audioEl = audio;

    // Attach Web Audio API gain pipeline once
    try {
      const AudioCtxClass = (window as any).AudioContext || (window as any).webkitAudioContext;
      if (AudioCtxClass) {
        const ctx: AudioContext = new AudioCtxClass();
        this.audioCtx = ctx;
        this.sourceNode = ctx.createMediaElementSource(audio);
        this.gainNode = ctx.createGain();
        const initialGain = this.currentGainPercent / 100;
        this.gainNode.gain.setValueAtTime(initialGain, ctx.currentTime);
        this.sourceNode.connect(this.gainNode);
        this.gainNode.connect(ctx.destination);
      }
    } catch (ctxErr) {
      console.warn('[RecordingPlayer] Web Audio API gain routing fallback notice:', ctxErr);
    }

    // Set up standard lifecycle events
    audio.addEventListener('loadedmetadata', () => {
      this.duration = audio.duration || 0;
      this.isLoading = false;
      this.notifyListeners();
      this.updatePlayerUI();
    });

    audio.addEventListener('timeupdate', () => {
      this.currentTime = audio.currentTime;
      this.updatePlayerUI();
    });

    audio.addEventListener('ended', () => {
      this.isPlaying = false;
      this.currentTime = 0;
      this.notifyListeners();
      this.updatePlayerUI();
    });

    audio.addEventListener('error', (e) => {
      console.warn('[RecordingPlayer] Audio playback error:', e);
      this.isLoading = false;
      this.isPlaying = false;
      this.notifyListeners();
      this.updatePlayerUI();
    });

    return audio;
  }

  private async startAudioWithBlob(blobUrl: string): Promise<void> {
    const audio = this.initAudioElement();
    audio.src = blobUrl;
    audio.load();

    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      await this.audioCtx.resume().catch(() => {});
    }

    // Apply current gain level
    const gainValue = this.currentGainPercent / 100;
    if (this.gainNode && this.audioCtx) {
      this.gainNode.gain.setValueAtTime(gainValue, this.audioCtx.currentTime);
    }
    audio.volume = Math.min(1.0, Math.max(0.0, gainValue));

    await audio.play();
    this.isPlaying = true;
    this.isLoading = false;
    this.notifyListeners();
    this.updatePlayerUI();
  }

  private async startAudioWithUrl(directUrl: string): Promise<void> {
    const audio = this.initAudioElement();
    audio.src = directUrl;
    audio.load();

    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      await this.audioCtx.resume().catch(() => {});
    }

    const gainValue = this.currentGainPercent / 100;
    if (this.gainNode && this.audioCtx) {
      this.gainNode.gain.setValueAtTime(gainValue, this.audioCtx.currentTime);
    }
    audio.volume = Math.min(1.0, Math.max(0.0, gainValue));

    await audio.play();
    this.isPlaying = true;
    this.isLoading = false;
    this.notifyListeners();
    this.updatePlayerUI();
  }

  private stopPlaybackInternal(removeUI: boolean): void {
    if (this.audioEl) {
      this.audioEl.pause();
      this.audioEl.currentTime = 0;
    }
    if (this.currentBlobUrl) {
      URL.revokeObjectURL(this.currentBlobUrl);
      this.currentBlobUrl = null;
    }
    this.isPlaying = false;
    this.isLoading = false;
    this.currentTime = 0;
    this.duration = 0;
    this.currentKey = null;

    if (removeUI && this.containerEl) {
      this.containerEl.remove();
      this.containerEl = null;
    }

    this.notifyListeners();
  }

  // ── 3. FLOATING PLAYER UI ──────────────────────────────────────────────────

  private formatTime(secs: number): string {
    if (isNaN(secs) || secs < 0) return '0:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }

  private renderFloatingPlayer(): void {
    if (typeof document === 'undefined') return;

    let container = document.getElementById('vgkMobileRecordingPlayer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'vgkMobileRecordingPlayer';
      document.body.appendChild(container);
    }
    this.containerEl = container;

    container.setAttribute('style', `
      position: fixed;
      bottom: calc(14px + env(safe-area-inset-bottom, 0px));
      left: 12px;
      right: 12px;
      z-index: 99999;
      background: rgba(15, 23, 42, 0.95);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1.5px solid rgba(56, 189, 248, 0.4);
      border-radius: 18px;
      padding: 12px 14px;
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.6), 0 0 12px rgba(56, 189, 248, 0.25);
      color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      user-select: none;
      -webkit-user-select: none;
    `);

    this.updatePlayerUI();
  }

  private updatePlayerUI(): void {
    if (!this.containerEl) return;

    const curTimeFormatted = this.formatTime(this.currentTime);
    const durFormatted = this.formatTime(this.duration);
    const isMaxBoost = this.currentGainPercent >= 200;

    // Volume badge styling
    let volIconClass = 'fa-volume-high';
    let volBadgeColor = '#38bdf8';
    if (this.currentGainPercent === 0) {
      volIconClass = 'fa-volume-xmark';
      volBadgeColor = '#ef4444';
    } else if (this.currentGainPercent < 80) {
      volIconClass = 'fa-volume-low';
      volBadgeColor = '#94a3b8';
    } else if (this.currentGainPercent > 130) {
      volIconClass = 'fa-volume-high';
      volBadgeColor = '#22c55e';
    }

    const titleHtml = `
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
        <div style="display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1;">
          <div style="width: 26px; height: 26px; border-radius: 50%; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.3); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
            <i class="fas ${volIconClass}" style="font-size: 11px; color: ${volBadgeColor};"></i>
          </div>
          <div style="min-width: 0; flex: 1;">
            <div style="font-size: 12.5px; font-weight: 700; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
              ${this.currentTitle}
            </div>
            ${this.currentSubtitle ? `
              <div style="font-size: 10px; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                ${this.currentSubtitle}
              </div>
            ` : ''}
          </div>
          <span style="font-size: 9.5px; font-weight: 700; padding: 2px 7px; border-radius: 8px; background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); flex-shrink: 0; display: inline-flex; align-items: center; gap: 3px;">
            <i class="fas fa-bullhorn" style="font-size: 8px;"></i> Stereo Loudspeaker
          </span>
        </div>
        <button id="recCloseBtn" title="Close" style="background: transparent; border: none; color: #94a3b8; font-size: 15px; cursor: pointer; padding: 4px 6px; margin-left: 8px; line-height: 1;">
          ✕
        </button>
      </div>
    `;

    const scrubberHtml = `
      <div style="margin-bottom: 8px;">
        <input 
          type="range" 
          id="recProgressBar" 
          min="0" 
          max="${this.duration > 0 ? this.duration : 100}" 
          step="0.1"
          value="${this.currentTime}" 
          style="width: 100%; height: 5px; accent-color: #38bdf8; cursor: pointer; display: block; border-radius: 4px; background: #334155; outline: none;"
        />
        <div style="display: flex; justify-content: space-between; font-size: 10.5px; color: #94a3b8; margin-top: 3px; font-weight: 600;">
          <span id="recCurrentTime">${curTimeFormatted}</span>
          <span id="recDuration">${this.isLoading ? 'Loading...' : durFormatted}</span>
        </div>
      </div>
    `;

    const controlsHtml = `
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
        <!-- Left: Playback controls -->
        <div style="display: flex; align-items: center; gap: 6px;">
          <button id="recRewindBtn" title="Rewind 10s" style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); color: #cbd5e1; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 11px;">
            -10
          </button>
          <button id="recPlayPauseBtn" title="${this.isPlaying ? 'Pause' : 'Play'}" style="background: ${this.isPlaying ? '#eab308' : 'linear-gradient(135deg, #38bdf8, #0ea5e9)'}; border: none; color: ${this.isPlaying ? '#000' : '#fff'}; width: 42px; height: 42px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 16px; box-shadow: 0 4px 12px ${this.isPlaying ? 'rgba(234, 179, 8, 0.4)' : 'rgba(14, 165, 233, 0.4)'};">
            ${this.isLoading ? '<i class="fas fa-spinner fa-spin"></i>' : `<i class="fas ${this.isPlaying ? 'fa-pause' : 'fa-play'}"></i>`}
          </button>
          <button id="recForwardBtn" title="Forward 10s" style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); color: #cbd5e1; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 11px;">
            +10
          </button>
        </div>

        <!-- Right: Loudness Volume Control Slider & Boost -->
        <div style="display: flex; align-items: center; gap: 6px; background: rgba(30, 41, 59, 0.85); padding: 4px 8px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
          <i class="fas ${volIconClass}" style="color: ${volBadgeColor}; font-size: 11px;"></i>
          <input 
            type="range" 
            id="recVolumeSlider" 
            min="0" 
            max="250" 
            step="5" 
            value="${this.currentGainPercent}" 
            title="Adjust volume boost"
            style="width: 68px; height: 4px; accent-color: ${volBadgeColor}; cursor: pointer; outline: none;"
          />
          <span id="recVolumeBadge" style="font-size: 11px; font-weight: 700; color: ${volBadgeColor}; min-width: 38px; text-align: right;">
            ${this.currentGainPercent}%
          </span>
          <button id="recMaxBoostBtn" title="Toggle Loud Boost" style="padding: 2px 6px; border-radius: 6px; background: ${isMaxBoost ? '#22c55e' : 'rgba(34,197,94,0.18)'}; border: 1px solid rgba(34,197,94,0.4); color: ${isMaxBoost ? '#000' : '#4ade80'}; font-size: 9.5px; font-weight: 800; cursor: pointer;">
            ${isMaxBoost ? 'MAX' : 'BOOST'}
          </button>
        </div>
      </div>
    `;

    this.containerEl.innerHTML = `${titleHtml}${scrubberHtml}${controlsHtml}`;
    this.attachPlayerEvents();
  }

  private attachPlayerEvents(): void {
    if (!this.containerEl) return;

    // Close button
    this.containerEl.querySelector('#recCloseBtn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.stop();
    });

    // Play/Pause button
    this.containerEl.querySelector('#recPlayPauseBtn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.togglePlayPause();
    });

    // Rewind / Forward
    this.containerEl.querySelector('#recRewindBtn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.skip(-10);
    });
    this.containerEl.querySelector('#recForwardBtn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.skip(10);
    });

    // Progress Bar Scrubber
    const progressBar = this.containerEl.querySelector('#recProgressBar') as HTMLInputElement | null;
    if (progressBar) {
      progressBar.addEventListener('input', (e) => {
        const val = parseFloat((e.target as HTMLInputElement).value);
        this.seek(val);
      });
    }

    // Volume Boost Slider
    const volumeSlider = this.containerEl.querySelector('#recVolumeSlider') as HTMLInputElement | null;
    if (volumeSlider) {
      volumeSlider.addEventListener('input', (e) => {
        const val = parseInt((e.target as HTMLInputElement).value, 10);
        this.setVolumeBoost(val);
      });
    }

    // Quick Max Boost Toggle
    this.containerEl.querySelector('#recMaxBoostBtn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      if (this.currentGainPercent >= 200) {
        this.setVolumeBoost(100);
      } else {
        this.setVolumeBoost(200);
      }
    });
  }
}

export const recordingPlayerService = new RecordingPlayerService();
