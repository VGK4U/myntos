/**
 * Procedural Web Audio API Synthesizer (DC Protocol Oct 2026)
 * 100% royalty-free, programmatic sound effect & background music generator.
 * Zero external audio file dependencies. Handles browser autoplay restrictions gracefully.
 */

class GameAudioSynthesizer {
  constructor() {
    this.ctx = null;
    this.musicGain = null;
    this.sfxGain = null;
    this.masterGain = null;

    this.isMuted = false;
    this.isMusicEnabled = true;
    this.isSfxEnabled = true;
    this.volume = 0.7;

    this.isPlayingMusic = false;
    this.musicInterval = null;
    this.melodyStep = 0;

    this._loadSettings();
  }

  _loadSettings() {
    try {
      const saved = localStorage.getItem('myntreal_games_audio_settings');
      if (saved) {
        const parsed = JSON.parse(saved);
        this.isMuted = Boolean(parsed.isMuted);
        this.isMusicEnabled = parsed.isMusicEnabled !== undefined ? Boolean(parsed.isMusicEnabled) : true;
        this.isSfxEnabled = parsed.isSfxEnabled !== undefined ? Boolean(parsed.isSfxEnabled) : true;
        this.volume = parsed.volume !== undefined ? parseFloat(parsed.volume) : 0.7;
      }
    } catch (e) {
      console.warn('[Audio] Failed to load audio preferences:', e);
    }
  }

  _saveSettings() {
    try {
      localStorage.setItem('myntreal_games_audio_settings', JSON.stringify({
        isMuted: this.isMuted,
        isMusicEnabled: this.isMusicEnabled,
        isSfxEnabled: this.isSfxEnabled,
        volume: this.volume
      }));
    } catch (e) {}
  }

  _initContext() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
        this.masterGain = this.ctx.createGain();
        this.masterGain.gain.setValueAtTime(this.isMuted ? 0 : this.volume, this.ctx.currentTime);
        this.masterGain.connect(this.ctx.destination);

        this.sfxGain = this.ctx.createGain();
        this.sfxGain.gain.setValueAtTime(this.isSfxEnabled ? 1 : 0, this.ctx.currentTime);
        this.sfxGain.connect(this.masterGain);

        this.musicGain = this.ctx.createGain();
        this.musicGain.gain.setValueAtTime(this.isMusicEnabled ? 0.35 : 0, this.ctx.currentTime);
        this.musicGain.connect(this.masterGain);
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume().catch(() => {});
    }
  }

  toggleMute() {
    this._initContext();
    this.isMuted = !this.isMuted;
    if (this.masterGain && this.ctx) {
      this.masterGain.gain.setValueAtTime(this.isMuted ? 0 : this.volume, this.ctx.currentTime);
    }
    this._saveSettings();
    return this.isMuted;
  }

  toggleMusic() {
    this._initContext();
    this.isMusicEnabled = !this.isMusicEnabled;
    if (this.musicGain && this.ctx) {
      this.musicGain.gain.setValueAtTime(this.isMusicEnabled ? 0.35 : 0, this.ctx.currentTime);
    }
    if (this.isMusicEnabled && !this.isPlayingMusic) {
      this.startMusic();
    } else if (!this.isMusicEnabled && this.isPlayingMusic) {
      this.stopMusic();
    }
    this._saveSettings();
    return this.isMusicEnabled;
  }

  toggleSfx() {
    this._initContext();
    this.isSfxEnabled = !this.isSfxEnabled;
    if (this.sfxGain && this.ctx) {
      this.sfxGain.gain.setValueAtTime(this.isSfxEnabled ? 1 : 0, this.ctx.currentTime);
    }
    this._saveSettings();
    return this.isSfxEnabled;
  }

  setVolume(val) {
    this._initContext();
    this.volume = Math.max(0, Math.min(1, parseFloat(val)));
    if (this.masterGain && this.ctx && !this.isMuted) {
      this.masterGain.gain.setValueAtTime(this.volume, this.ctx.currentTime);
    }
    this._saveSettings();
  }

  // ── SOUND EFFECTS ──
  playCollect() {
    this._initContext();
    if (this.isMuted || !this.isSfxEnabled || !this.ctx) return;

    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'triangle';
      osc.frequency.setValueAtTime(587.33, now); // D5
      osc.frequency.exponentialRampToValueAtTime(880.00, now + 0.1); // A5

      gain.gain.setValueAtTime(0.2, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);

      osc.connect(gain);
      gain.connect(this.sfxGain);

      osc.start(now);
      osc.stop(now + 0.15);
    } catch (e) {}
  }

  playJump() {
    this._initContext();
    if (this.isMuted || !this.isSfxEnabled || !this.ctx) return;

    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(220, now);
      osc.frequency.exponentialRampToValueAtTime(520, now + 0.18);

      gain.gain.setValueAtTime(0.25, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.18);

      osc.connect(gain);
      gain.connect(this.sfxGain);

      osc.start(now);
      osc.stop(now + 0.18);
    } catch (e) {}
  }

  playLineClear() {
    this._initContext();
    if (this.isMuted || !this.isSfxEnabled || !this.ctx) return;

    try {
      const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
      const now = this.ctx.currentTime;
      notes.forEach((freq, i) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        const start = now + (i * 0.06);

        osc.type = 'square';
        osc.frequency.setValueAtTime(freq, start);

        gain.gain.setValueAtTime(0.12, start);
        gain.gain.exponentialRampToValueAtTime(0.001, start + 0.14);

        osc.connect(gain);
        gain.connect(this.sfxGain);

        osc.start(start);
        osc.stop(start + 0.14);
      });
    } catch (e) {}
  }

  playRotate() {
    this._initContext();
    if (this.isMuted || !this.isSfxEnabled || !this.ctx) return;

    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(440, now);
      osc.frequency.exponentialRampToValueAtTime(330, now + 0.05);

      gain.gain.setValueAtTime(0.1, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);

      osc.connect(gain);
      gain.connect(this.sfxGain);

      osc.start(now);
      osc.stop(now + 0.05);
    } catch (e) {}
  }

  playDrop() {
    this._initContext();
    if (this.isMuted || !this.isSfxEnabled || !this.ctx) return;

    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'triangle';
      osc.frequency.setValueAtTime(140, now);
      osc.frequency.exponentialRampToValueAtTime(60, now + 0.08);

      gain.gain.setValueAtTime(0.2, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);

      osc.connect(gain);
      gain.connect(this.sfxGain);

      osc.start(now);
      osc.stop(now + 0.08);
    } catch (e) {}
  }

  playCollision() {
    this._initContext();
    if (this.isMuted || !this.isSfxEnabled || !this.ctx) return;

    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(120, now);
      osc.frequency.linearRampToValueAtTime(40, now + 0.25);

      gain.gain.setValueAtTime(0.3, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);

      osc.connect(gain);
      gain.connect(this.sfxGain);

      osc.start(now);
      osc.stop(now + 0.25);
    } catch (e) {}
  }

  playGameOver() {
    this._initContext();
    if (this.isMuted || !this.isSfxEnabled || !this.ctx) return;

    try {
      const notes = [440, 415.30, 392, 349.23]; // A4, Ab4, G4, F4
      const now = this.ctx.currentTime;
      notes.forEach((freq, i) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        const start = now + (i * 0.12);

        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(freq, start);

        gain.gain.setValueAtTime(0.18, start);
        gain.gain.exponentialRampToValueAtTime(0.001, start + 0.2);

        osc.connect(gain);
        gain.connect(this.sfxGain);

        osc.start(start);
        osc.stop(start + 0.2);
      });
    } catch (e) {}
  }

  // ── PROCEDURAL BACKGROUND MUSIC LOOP ──
  startMusic() {
    if (this.isPlayingMusic) return;
    this._initContext();
    if (!this.ctx || this.isMuted || !this.isMusicEnabled) return;

    this.isPlayingMusic = true;
    const melody = [
      261.63, 329.63, 392.00, 523.25, 392.00, 329.63, 293.66, 349.23,
      440.00, 587.33, 440.00, 349.23, 246.94, 329.63, 392.00, 493.88
    ];

    this.musicInterval = setInterval(() => {
      if (!this.isPlayingMusic || !this.isMusicEnabled || this.isMuted || !this.ctx) return;
      try {
        const freq = melody[this.melodyStep % melody.length];
        const now = this.ctx.currentTime;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, now);

        gain.gain.setValueAtTime(0.05, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.22);

        osc.connect(gain);
        gain.connect(this.musicGain);

        osc.start(now);
        osc.stop(now + 0.22);

        this.melodyStep++;
      } catch (e) {}
    }, 240);
  }

  stopMusic() {
    this.isPlayingMusic = false;
    if (this.musicInterval) {
      clearInterval(this.musicInterval);
      this.musicInterval = null;
    }
  }

  pauseAll() {
    this.stopMusic();
  }

  resumeAll() {
    if (this.isMusicEnabled && !this.isMuted) {
      this.startMusic();
    }
  }
}

// Global audio singleton
window.gameAudio = new GameAudioSynthesizer();
