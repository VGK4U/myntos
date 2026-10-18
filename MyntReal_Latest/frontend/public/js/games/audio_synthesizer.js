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
    this.volume = 0.85;

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
        this.volume = parsed.volume !== undefined ? parseFloat(parsed.volume) : 0.85;
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
        this.sfxGain.gain.setValueAtTime(this.isSfxEnabled ? 0.8 : 0, this.ctx.currentTime);
        this.sfxGain.connect(this.masterGain);

        this.musicGain = this.ctx.createGain();
        this.musicGain.gain.setValueAtTime(this.isMusicEnabled ? 0.5 : 0, this.ctx.currentTime);
        this.musicGain.connect(this.masterGain);
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume().catch(() => {});
    }
  }

  /**
   * Synchronous audio unlock for mobile Safari & Chrome autoplay policies.
   * Must be called in direct response to user gesture (touch, click, key).
   */
  unlock() {
    this._initContext();
    if (this.ctx) {
      if (this.ctx.state === 'suspended') {
        this.ctx.resume().catch(() => {});
      }
      try {
        // Kickstart hardware audio pipe with a 1-sample silent buffer
        const buffer = this.ctx.createBuffer(1, 1, 22050);
        const source = this.ctx.createBufferSource();
        source.buffer = buffer;
        source.connect(this.ctx.destination);
        source.start(0);
      } catch (e) {}
    }
  }

  toggleMute() {
    this.unlock();
    this.isMuted = !this.isMuted;
    if (this.masterGain && this.ctx) {
      this.masterGain.gain.setValueAtTime(this.isMuted ? 0 : this.volume, this.ctx.currentTime);
    }
    this._saveSettings();
    return this.isMuted;
  }

  toggleMusic() {
    this.unlock();
    this.isMusicEnabled = !this.isMusicEnabled;
    if (this.musicGain && this.ctx) {
      this.musicGain.gain.setValueAtTime(this.isMusicEnabled ? 0.5 : 0, this.ctx.currentTime);
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
    this.unlock();
    this.isSfxEnabled = !this.isSfxEnabled;
    if (this.sfxGain && this.ctx) {
      this.sfxGain.gain.setValueAtTime(this.isSfxEnabled ? 0.8 : 0, this.ctx.currentTime);
    }
    this._saveSettings();
    return this.isSfxEnabled;
  }

  setVolume(val) {
    this.unlock();
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
      osc.frequency.exponentialRampToValueAtTime(880.00, now + 0.12); // A5

      gain.gain.setValueAtTime(0.35, now);
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
      osc.frequency.setValueAtTime(240, now);
      osc.frequency.exponentialRampToValueAtTime(560, now + 0.16);

      gain.gain.setValueAtTime(0.35, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.16);

      osc.connect(gain);
      gain.connect(this.sfxGain);

      osc.start(now);
      osc.stop(now + 0.16);
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

        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, start);

        gain.gain.setValueAtTime(0.28, start);
        gain.gain.exponentialRampToValueAtTime(0.001, start + 0.16);

        osc.connect(gain);
        gain.connect(this.sfxGain);

        osc.start(start);
        osc.stop(start + 0.16);
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
      osc.frequency.exponentialRampToValueAtTime(330, now + 0.06);

      gain.gain.setValueAtTime(0.22, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.06);

      osc.connect(gain);
      gain.connect(this.sfxGain);

      osc.start(now);
      osc.stop(now + 0.06);
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
      osc.frequency.setValueAtTime(160, now);
      osc.frequency.exponentialRampToValueAtTime(60, now + 0.09);

      gain.gain.setValueAtTime(0.3, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.09);

      osc.connect(gain);
      gain.connect(this.sfxGain);

      osc.start(now);
      osc.stop(now + 0.09);
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
      osc.frequency.setValueAtTime(140, now);
      osc.frequency.linearRampToValueAtTime(40, now + 0.25);

      gain.gain.setValueAtTime(0.35, now);
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

        gain.gain.setValueAtTime(0.25, start);
        gain.gain.exponentialRampToValueAtTime(0.001, start + 0.22);

        osc.connect(gain);
        gain.connect(this.sfxGain);

        osc.start(start);
        osc.stop(start + 0.22);
      });
    } catch (e) {}
  }

  // ── NEW SOUND EFFECTS: BUBBLE BLASTER & BOUNCING BALL ──
  playBubbleShoot() {
    this._initContext();
    if (this.isMuted || !this.isSfxEnabled || !this.ctx) return;

    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(320, now);
      osc.frequency.exponentialRampToValueAtTime(680, now + 0.08);

      gain.gain.setValueAtTime(0.28, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);

      osc.connect(gain);
      gain.connect(this.sfxGain);

      osc.start(now);
      osc.stop(now + 0.08);
    } catch (e) {}
  }

  playBubblePop(pitchMod = 1.0) {
    this._initContext();
    if (this.isMuted || !this.isSfxEnabled || !this.ctx) return;

    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'triangle';
      const baseFreq = 540 * pitchMod;
      osc.frequency.setValueAtTime(baseFreq, now);
      osc.frequency.exponentialRampToValueAtTime(baseFreq * 1.8, now + 0.09);

      gain.gain.setValueAtTime(0.38, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.11);

      osc.connect(gain);
      gain.connect(this.sfxGain);

      osc.start(now);
      osc.stop(now + 0.11);
    } catch (e) {}
  }

  playClusterDrop() {
    this._initContext();
    if (this.isMuted || !this.isSfxEnabled || !this.ctx) return;

    try {
      const notes = [659.25, 783.99, 987.77, 1318.51]; // E5, G5, B5, E6
      const now = this.ctx.currentTime;
      notes.forEach((freq, i) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        const start = now + (i * 0.05);

        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, start);

        gain.gain.setValueAtTime(0.25, start);
        gain.gain.exponentialRampToValueAtTime(0.001, start + 0.14);

        osc.connect(gain);
        gain.connect(this.sfxGain);

        osc.start(start);
        osc.stop(start + 0.14);
      });
    } catch (e) {}
  }

  playPaddleHit(angleOffset = 0) {
    this._initContext();
    if (this.isMuted || !this.isSfxEnabled || !this.ctx) return;

    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'triangle';
      const freq = 420 + (angleOffset * 150);
      osc.frequency.setValueAtTime(freq, now);
      osc.frequency.exponentialRampToValueAtTime(freq * 0.6, now + 0.08);

      gain.gain.setValueAtTime(0.35, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);

      osc.connect(gain);
      gain.connect(this.sfxGain);

      osc.start(now);
      osc.stop(now + 0.08);
    } catch (e) {}
  }

  playBrickBreak(combo = 1) {
    this._initContext();
    if (this.isMuted || !this.isSfxEnabled || !this.ctx) return;

    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'square';
      // Pitch goes up with combo multiplier!
      const baseFreq = Math.min(1200, 480 + (combo * 60));
      osc.frequency.setValueAtTime(baseFreq, now);
      osc.frequency.exponentialRampToValueAtTime(baseFreq * 1.5, now + 0.07);

      gain.gain.setValueAtTime(0.25, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.09);

      osc.connect(gain);
      gain.connect(this.sfxGain);

      osc.start(now);
      osc.stop(now + 0.09);
    } catch (e) {}
  }

  playPowerup() {
    this._initContext();
    if (this.isMuted || !this.isSfxEnabled || !this.ctx) return;

    try {
      const notes = [440, 554.37, 659.25, 880]; // A4, C#5, E5, A5
      const now = this.ctx.currentTime;
      notes.forEach((freq, i) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        const start = now + (i * 0.05);

        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, start);

        gain.gain.setValueAtTime(0.28, start);
        gain.gain.exponentialRampToValueAtTime(0.001, start + 0.15);

        osc.connect(gain);
        gain.connect(this.sfxGain);

        osc.start(start);
        osc.stop(start + 0.15);
      });
    } catch (e) {}
  }

  playBallBounce(highBounce = false) {
    this._initContext();
    if (this.isMuted || !this.isSfxEnabled || !this.ctx) return;

    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'sine';
      const startFreq = highBounce ? 180 : 220;
      const endFreq = highBounce ? 580 : 420;
      osc.frequency.setValueAtTime(startFreq, now);
      osc.frequency.exponentialRampToValueAtTime(endFreq, now + 0.12);

      gain.gain.setValueAtTime(0.32, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.14);

      osc.connect(gain);
      gain.connect(this.sfxGain);

      osc.start(now);
      osc.stop(now + 0.14);
    } catch (e) {}
  }

  playHoopPass() {
    this._initContext();
    if (this.isMuted || !this.isSfxEnabled || !this.ctx) return;

    try {
      const notes = [783.99, 987.77, 1318.51, 1567.98]; // G5, B5, E6, G6
      const now = this.ctx.currentTime;
      notes.forEach((freq, i) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        const start = now + (i * 0.04);

        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, start);

        gain.gain.setValueAtTime(0.24, start);
        gain.gain.exponentialRampToValueAtTime(0.001, start + 0.16);

        osc.connect(gain);
        gain.connect(this.sfxGain);

        osc.start(start);
        osc.stop(start + 0.16);
      });
    } catch (e) {}
  }

  // ── PROCEDURAL BACKGROUND MUSIC LOOP (CHIPTUNE ARCADE) ──
  startMusic() {
    if (this.isPlayingMusic) return;
    this.unlock();
    if (!this.ctx || this.isMuted || !this.isMusicEnabled) return;

    if (this.musicInterval) {
      clearInterval(this.musicInterval);
      this.musicInterval = null;
    }

    if (this.musicGain && this.ctx) {
      try {
        this.musicGain.gain.cancelScheduledValues(this.ctx.currentTime);
        this.musicGain.gain.setValueAtTime(0.5, this.ctx.currentTime);
      } catch (e) {}
    }

    this.isPlayingMusic = true;

    // Upbeat pentatonic retro arcade melody
    const leadMelody = [
      261.63, 329.63, 392.00, 523.25, 392.00, 329.63, 293.66, 349.23,
      440.00, 587.33, 440.00, 349.23, 246.94, 329.63, 392.00, 493.88,
      523.25, 587.33, 659.25, 587.33, 523.25, 440.00, 392.00, 329.63,
      293.66, 329.63, 392.00, 440.00, 392.00, 329.63, 293.66, 261.63
    ];

    // Bassline root progression
    const bassline = [
      130.81, 130.81, 130.81, 130.81, 146.83, 146.83, 146.83, 146.83,
      164.81, 164.81, 164.81, 164.81, 123.47, 123.47, 130.81, 130.81,
      130.81, 130.81, 164.81, 164.81, 174.61, 174.61, 196.00, 196.00,
      146.83, 146.83, 164.81, 164.81, 196.00, 196.00, 130.81, 130.81
    ];

    this.musicInterval = setInterval(() => {
      if (!this.isPlayingMusic || !this.isMusicEnabled || this.isMuted || !this.ctx) return;
      try {
        const step = this.melodyStep % leadMelody.length;
        const now = this.ctx.currentTime;

        // Channel 1: Lead Melody (Triangle wave with warm envelope)
        const leadFreq = leadMelody[step];
        const oscLead = this.ctx.createOscillator();
        const gainLead = this.ctx.createGain();

        oscLead.type = 'triangle';
        oscLead.frequency.setValueAtTime(leadFreq, now);

        gainLead.gain.setValueAtTime(0.20, now);
        gainLead.gain.exponentialRampToValueAtTime(0.001, now + 0.22);

        oscLead.connect(gainLead);
        gainLead.connect(this.musicGain);

        oscLead.start(now);
        oscLead.stop(now + 0.22);

        // Channel 2: Bassline (Warm Sine wave sub every 2 steps)
        if (step % 2 === 0) {
          const bassFreq = bassline[step];
          const oscBass = this.ctx.createOscillator();
          const gainBass = this.ctx.createGain();

          oscBass.type = 'sine';
          oscBass.frequency.setValueAtTime(bassFreq, now);

          gainBass.gain.setValueAtTime(0.24, now);
          gainBass.gain.exponentialRampToValueAtTime(0.001, now + 0.40);

          oscBass.connect(gainBass);
          gainBass.connect(this.musicGain);

          oscBass.start(now);
          oscBass.stop(now + 0.40);
        }

        this.melodyStep++;
      } catch (e) {}
    }, 220);
  }

  stopMusic() {
    this.isPlayingMusic = false;
    if (this.musicInterval) {
      clearInterval(this.musicInterval);
      this.musicInterval = null;
    }
    if (this.musicGain && this.ctx) {
      try {
        this.musicGain.gain.cancelScheduledValues(this.ctx.currentTime);
        this.musicGain.gain.setValueAtTime(0, this.ctx.currentTime);
      } catch (e) {}
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
