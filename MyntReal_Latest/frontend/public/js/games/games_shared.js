/**
 * Shared Gaming Architecture & UI State Engine (DC Protocol Oct 2026)
 * Handles session tokens, API communication, score HUD, pause/resume,
 * mobile touch controls, and reward claim dialogs.
 */

class GameFramework {
  constructor(options) {
    this.containerId = options.containerId || 'game-container';
    this.canvasId = options.canvasId || 'game-canvas';
    this.gameType = options.gameType || 'SNAKE';
    this.theme = options.theme || 'myntreal'; // 'myntreal' or 'vgk4u'
    this.onStateChange = options.onStateChange || null;

    this.container = document.getElementById(this.containerId);
    this.canvas = document.getElementById(this.canvasId);
    this.ctx = this.canvas ? this.canvas.getContext('2d') : null;

    this.state = 'READY'; // READY, PLAYING, PAUSED, GAME_OVER, SUBMITTING, REWARD_RESULT, ERROR
    this.sessionToken = null;
    this.serverSeed = null;
    this.selectedCharacter = 'volt_fox';

    this.score = 0;
    this.bestScore = 0;
    this.level = 1;
    this.linesCleared = 0;
    this.itemsCollected = 0;
    this.distanceTravelled = 0;
    this.elapsedSeconds = 0;
    this.timerInterval = null;

    this.activeGameEngine = null;
    this.telemetryMilestones = [];
    this.touchControlsActive = false;

    this._initStorage();
    this._initKeyboardTrap();
    this._initVisibilityListener();
  }

  _initStorage() {
    try {
      const key = `myntreal_best_${this.gameType.toLowerCase()}`;
      const saved = localStorage.getItem(key);
      if (saved) this.bestScore = parseInt(saved, 10) || 0;
    } catch (e) {}
  }

  _saveLocalBest() {
    if (this.score > this.bestScore) {
      this.bestScore = this.score;
      try {
        const key = `myntreal_best_${this.gameType.toLowerCase()}`;
        localStorage.setItem(key, String(this.bestScore));
      } catch (e) {}
    }
  }

  _initKeyboardTrap() {
    window.addEventListener('keydown', (e) => {
      // Prevent browser scroll on arrow keys and space when game is active or canvas focused
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space'].includes(e.code)) {
        if (this.state === 'PLAYING' || this.state === 'PAUSED') {
          e.preventDefault();
        }
      }
      if (e.code === 'KeyP' || e.code === 'Escape') {
        if (this.state === 'PLAYING') this.pauseGame();
        else if (this.state === 'PAUSED') this.resumeGame();
      }
    }, { passive: false });
  }

  _initVisibilityListener() {
    document.addEventListener('visibilitychange', () => {
      if (document.hidden && this.state === 'PLAYING') {
        this.pauseGame();
      }
    });
  }

  setGameEngine(engine) {
    this.activeGameEngine = engine;
  }

  setCharacter(charId) {
    if (window.RUNNER_CHARACTERS && window.RUNNER_CHARACTERS[charId]) {
      this.selectedCharacter = charId;
      if (this.activeGameEngine && typeof this.activeGameEngine.setCharacter === 'function') {
        this.activeGameEngine.setCharacter(charId);
      }
    }
  }

  // ── LIFECYCLE CONTROLS ──
  async startGame() {
    this.score = 0;
    this.level = 1;
    this.linesCleared = 0;
    this.itemsCollected = 0;
    this.distanceTravelled = 0;
    this.elapsedSeconds = 0;
    this.telemetryMilestones = [];

    this._updateScoreHUD();
    this._showLoading("Initializing Secure Session...");

    try {
      // Call backend to create verified game session
      const resp = await fetch('/api/v1/games/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this._getAuthToken()}`
        },
        body: JSON.stringify({
          game_type: this.gameType,
          character_id: this.selectedCharacter
        })
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to start game session');
      }

      const data = await resp.json();
      this.sessionToken = data.session_token;
      this.serverSeed = data.server_seed;

      this.state = 'PLAYING';
      this._hideAllOverlays();
      this._startTimer();

      if (window.gameAudio) {
        window.gameAudio.startMusic();
      }

      if (this.activeGameEngine && typeof this.activeGameEngine.start === 'function') {
        this.activeGameEngine.start();
      }

      if (this.onStateChange) this.onStateChange(this.state);
    } catch (err) {
      console.warn('[GameFramework] Fallback to local session on error:', err.message);
      // Fallback local session allows gameplay if offline/network fails
      this.sessionToken = `local_${Date.now()}`;
      this.state = 'PLAYING';
      this._hideAllOverlays();
      this._startTimer();
      if (window.gameAudio) window.gameAudio.startMusic();
      if (this.activeGameEngine && typeof this.activeGameEngine.start === 'function') {
        this.activeGameEngine.start();
      }
      if (this.onStateChange) this.onStateChange(this.state);
    }
  }

  pauseGame() {
    if (this.state !== 'PLAYING') return;
    this.state = 'PAUSED';
    this._stopTimer();

    if (window.gameAudio) {
      window.gameAudio.pauseAll();
    }

    if (this.activeGameEngine && typeof this.activeGameEngine.pause === 'function') {
      this.activeGameEngine.pause();
    }

    this._showPauseOverlay();
    if (this.onStateChange) this.onStateChange(this.state);
  }

  resumeGame() {
    if (this.state !== 'PAUSED') return;
    this.state = 'PLAYING';
    this._hideAllOverlays();
    this._startTimer();

    if (window.gameAudio) {
      window.gameAudio.resumeAll();
    }

    if (this.activeGameEngine && typeof this.activeGameEngine.resume === 'function') {
      this.activeGameEngine.resume();
    }

    if (this.onStateChange) this.onStateChange(this.state);
  }

  restartGame() {
    this._stopTimer();
    if (this.activeGameEngine && typeof this.activeGameEngine.reset === 'function') {
      this.activeGameEngine.reset();
    }
    this.startGame();
  }

  async gameOver(finalStats = {}) {
    if (this.state === 'GAME_OVER') return;
    this.state = 'GAME_OVER';
    this._stopTimer();

    if (window.gameAudio) {
      window.gameAudio.playGameOver();
      window.gameAudio.stopMusic();
    }

    this.score = finalStats.score !== undefined ? finalStats.score : this.score;
    this.linesCleared = finalStats.linesCleared !== undefined ? finalStats.linesCleared : this.linesCleared;
    this.itemsCollected = finalStats.itemsCollected !== undefined ? finalStats.itemsCollected : this.itemsCollected;
    this.distanceTravelled = finalStats.distanceTravelled !== undefined ? finalStats.distanceTravelled : this.distanceTravelled;
    this.level = finalStats.level !== undefined ? finalStats.level : this.level;

    const isNewPersonalBest = this.score > this.bestScore;
    this._saveLocalBest();
    this._updateScoreHUD();

    this._showSubmittingOverlay();

    // Submit results to server
    try {
      const resp = await fetch('/api/v1/games/complete', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this._getAuthToken()}`
        },
        body: JSON.stringify({
          session_token: this.sessionToken,
          score: this.score,
          level: this.level,
          lines_cleared: this.linesCleared,
          items_collected: this.itemsCollected,
          distance_travelled: this.distanceTravelled,
          duration_seconds: this.elapsedSeconds,
          telemetry_summary: {
            milestones: this.telemetryMilestones
          }
        })
      });

      const data = await resp.json();
      this._showGameOverOverlay(data, isNewPersonalBest);
    } catch (e) {
      console.warn('[GameFramework] Server submission error:', e);
      this._showGameOverOverlay({
        success: true,
        score: this.score,
        reward_points: 0,
        reward_status: 'OFFLINE',
        message: 'Game complete! (Offline score recorded locally)'
      }, isNewPersonalBest);
    }

    if (this.onStateChange) this.onStateChange(this.state);
  }

  // ── METRIC REPORTING FROM ENGINES ──
  addScore(points) {
    this.score += points;
    this._saveLocalBest();
    this._updateScoreHUD();
  }

  setItems(count) {
    this.itemsCollected = count;
    this._updateScoreHUD();
  }

  setLines(count) {
    this.linesCleared = count;
    this._updateScoreHUD();
  }

  setDistance(meters) {
    this.distanceTravelled = meters;
    this._updateScoreHUD();
  }

  setLevel(lvl) {
    this.level = lvl;
    this._updateScoreHUD();
  }

  recordMilestone(value) {
    this.telemetryMilestones.push({
      time: this.elapsedSeconds,
      value: value,
      score: this.score
    });
  }

  // ── TIMERS & HUD ──
  _startTimer() {
    this._stopTimer();
    this.timerInterval = setInterval(() => {
      this.elapsedSeconds++;
      this._updateTimerDisplay();
    }, 1000);
  }

  _stopTimer() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  _updateTimerDisplay() {
    const el = document.getElementById('hud-time');
    if (!el) return;
    const m = String(Math.floor(this.elapsedSeconds / 60)).padStart(2, '0');
    const s = String(this.elapsedSeconds % 60).padStart(2, '0');
    el.textContent = `${m}:${s}`;
  }

  _updateScoreHUD() {
    const currEl = document.getElementById('hud-current-score');
    if (currEl) currEl.textContent = this.score.toLocaleString();

    const bestEl = document.getElementById('hud-best-score');
    if (bestEl) bestEl.textContent = this.bestScore.toLocaleString();

    const lvlEl = document.getElementById('hud-level');
    if (lvlEl) lvlEl.textContent = `Lvl ${this.level}`;

    const progBar = document.getElementById('hud-progress-bar');
    const progLabel = document.getElementById('hud-progress-label');

    if (this.gameType === 'SNAKE') {
      const step = 10;
      const progress = (this.itemsCollected % step) / step * 100;
      if (progBar) progBar.style.width = `${progress}%`;
      if (progLabel) progLabel.textContent = `${this.itemsCollected} Food Eaten`;
    } else if (this.gameType === 'BLOCK_DROP') {
      const step = 4;
      const progress = (this.linesCleared % step) / step * 100;
      if (progBar) progBar.style.width = `${progress}%`;
      if (progLabel) progLabel.textContent = `${this.linesCleared} Lines Cleared`;
    } else if (this.gameType === 'ENDLESS_RUNNER') {
      const step = 250;
      const progress = (this.distanceTravelled % step) / step * 100;
      if (progBar) progBar.style.width = `${progress}%`;
      if (progLabel) progLabel.textContent = `${this.distanceTravelled}m Distance`;
    }
  }

  // ── OVERLAYS & UI ──
  _hideAllOverlays() {
    const overlays = document.querySelectorAll('.game-ui-overlay');
    overlays.forEach(el => el.classList.add('d-none'));
  }

  _showLoading(text) {
    this._hideAllOverlays();
    const el = document.getElementById('overlay-loading');
    if (el) {
      el.classList.remove('d-none');
      const textEl = el.querySelector('.loading-text');
      if (textEl) textEl.textContent = text;
    }
  }

  _showPauseOverlay() {
    this._hideAllOverlays();
    const el = document.getElementById('overlay-paused');
    if (el) el.classList.remove('d-none');
  }

  _showSubmittingOverlay() {
    this._hideAllOverlays();
    const el = document.getElementById('overlay-submitting');
    if (el) el.classList.remove('d-none');
  }

  _showGameOverOverlay(data, isNewBest) {
    this._hideAllOverlays();
    const el = document.getElementById('overlay-gameover');
    if (!el) return;

    el.classList.remove('d-none');
    const scoreVal = el.querySelector('#go-final-score');
    if (scoreVal) scoreVal.textContent = this.score.toLocaleString();

    const bestVal = el.querySelector('#go-best-score');
    if (bestVal) bestVal.textContent = this.bestScore.toLocaleString();

    const newBestBadge = el.querySelector('#go-new-best-badge');
    if (newBestBadge) {
      newBestBadge.style.display = isNewBest ? 'inline-block' : 'none';
    }

    const rewardCard = el.querySelector('#go-reward-card');
    const rewardMsg = el.querySelector('#go-reward-msg');
    const rewardCodeWrap = el.querySelector('#go-reward-code-wrap');
    const rewardCodeVal = el.querySelector('#go-reward-code');

    if (data.reward_points > 0 && rewardCard) {
      rewardCard.classList.remove('d-none');
      if (rewardMsg) rewardMsg.textContent = data.message;
      if (data.requires_claim && data.claim_code && rewardCodeWrap) {
        rewardCodeWrap.classList.remove('d-none');
        if (rewardCodeVal) rewardCodeVal.textContent = data.claim_code;
      } else if (rewardCodeWrap) {
        rewardCodeWrap.classList.add('d-none');
      }
    } else if (rewardCard) {
      rewardCard.classList.add('d-none');
    }
  }

  _getAuthToken() {
    try {
      return localStorage.getItem('customer_token') ||
             localStorage.getItem('staff_token') ||
             sessionStorage.getItem('customer_token') ||
             sessionStorage.getItem('staff_token') || '';
    } catch (e) {
      return '';
    }
  }
}
