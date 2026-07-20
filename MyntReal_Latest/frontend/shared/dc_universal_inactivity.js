/**
 * DC Protocol — Universal Inactivity Manager
 * Covers: VGK4U, Partner, Promo, and any other portal
 *
 * BEHAVIOUR:
 *  - 13 min inactivity → warning modal with countdown
 *  - 15 min inactivity → auto sign-out + redirect to portal login
 *  - Tab hidden (browser switch) → inactivity clock continues from hide time (no reset)
 *  - Cross-tab sync via localStorage: logout in one tab logs out all tabs on same portal
 *
 * USAGE:
 *   <script src="/shared/dc_universal_inactivity.js"></script>
 *   <script>
 *     DCInactivityManager.init({
 *       tokenKey:     'vgk_token',        // key in localStorage or sessionStorage
 *       tokenStorage: 'localStorage',     // 'localStorage' or 'sessionStorage'
 *       loginUrl:     '/vgk/login',       // redirect here on logout
 *       portalName:   'VGK4U',            // shown in warning modal
 *       accentColor:  '#7c3aed',          // optional modal accent colour
 *       logoutFn:     null,               // optional fn() called just before token clear
 *     });
 *   </script>
 */

(function (global) {
  'use strict';

  const INACTIVITY_MS  = 15 * 60 * 1000;  // 15 minutes
  const WARNING_MS     = 13 * 60 * 1000;  // show warning at 13 minutes
  const CHECK_INTERVAL = 10 * 1000;       // poll every 10 s
  const MODAL_ID       = 'dcUniversalInactivityModal';

  const DCInactivityManager = {
    _cfg: null,
    _lastActivity: 0,
    _checkTimer: null,
    _countdownTimer: null,
    _warningShown: false,
    _initialized: false,
    _remainingSeconds: 120,

    // ── Public API ─────────────────────────────────────────────────────────────

    init: function (cfg) {
      if (this._initialized) return;

      this._cfg = Object.assign({
        tokenKey:      'token',
        tokenStorage:  'localStorage',
        loginUrl:      '/login',
        portalName:    'Portal',
        accentColor:   '#7c3aed',
        companionKeys: [],   // extra localStorage/sessionStorage keys to clear on logout
      }, cfg);

      if (!this._getToken()) {
        console.log('[DC-INACTIVITY] No token — skipping init for', this._cfg.portalName);
        return;
      }

      console.log('[DC-INACTIVITY] Initialising for portal:', this._cfg.portalName);

      this._touch();
      this._bindActivityEvents();
      this._bindVisibilityChange();
      this._bindStorageSync();
      this._createModal();

      this._checkTimer = setInterval(() => this._check(), CHECK_INTERVAL);
      this._initialized = true;
    },

    /** Call this from your own activity-generating code (e.g. after a successful fetch) */
    resetTimer: function () {
      if (this._initialized) this._touch();
    },

    /** Pause (e.g. during a file upload or GPS heartbeat) */
    pause: function () { this._paused = true; },

    /** Resume after pause */
    resume: function () { this._paused = false; this._touch(); },

    // ── Token helpers ──────────────────────────────────────────────────────────

    _getToken: function () {
      const s = this._cfg.tokenStorage === 'sessionStorage' ? sessionStorage : localStorage;
      return s.getItem(this._cfg.tokenKey);
    },

    _clearToken: function () {
      const s = this._cfg.tokenStorage === 'sessionStorage' ? sessionStorage : localStorage;
      s.removeItem(this._cfg.tokenKey);
    },

    _activityStorageKey: function () {
      return 'dc_last_activity_' + this._cfg.tokenKey;
    },

    // ── Activity tracking ──────────────────────────────────────────────────────

    _touch: function () {
      if (this._paused) return;
      this._lastActivity = Date.now();
      localStorage.setItem(this._activityStorageKey(), String(this._lastActivity));
      if (this._warningShown) this._hideWarning();
    },

    _bindActivityEvents: function () {
      const events = ['mousedown', 'mousemove', 'keydown', 'touchstart', 'touchmove', 'scroll', 'click'];
      let throttle = null;
      const handler = () => {
        if (throttle) return;
        throttle = setTimeout(() => { this._touch(); throttle = null; }, 1000);
      };
      events.forEach(e => document.addEventListener(e, handler, { passive: true }));

      // Reset timer on successful API responses (fetch intercept)
      const origFetch = global.fetch;
      const self = this;
      global.fetch = function () {
        return origFetch.apply(this, arguments).then(function (resp) {
          if (resp.ok) self._touch();
          return resp;
        });
      };
    },

    _bindVisibilityChange: function () {
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
          // Tab went background — record this as the last active moment
          // so the 15-min clock ticks from now even while hidden
          this._lastActivity = Date.now();
          localStorage.setItem(this._activityStorageKey(), String(this._lastActivity));
        } else {
          // Tab is visible again — immediately check if timeout expired
          this._check();
        }
      });
    },

    _bindStorageSync: function () {
      window.addEventListener('storage', (e) => {
        // Cross-tab activity sync
        if (e.key === this._activityStorageKey() && e.newValue) {
          const t = parseInt(e.newValue, 10);
          if (t > this._lastActivity) {
            this._lastActivity = t;
            if (this._warningShown) this._hideWarning();
          }
        }
        // Cross-tab logout sync (token removed in another tab)
        if (e.key === this._cfg.tokenKey && !e.newValue && this._cfg.tokenStorage === 'localStorage') {
          console.log('[DC-INACTIVITY] Cross-tab logout detected for', this._cfg.portalName);
          this._cleanup();
          window.location.href = this._cfg.loginUrl;
        }
      });
    },

    // ── Inactivity check ───────────────────────────────────────────────────────

    _check: function () {
      if (this._paused) return;
      if (!this._getToken()) { this._cleanup(); return; }

      // Always read from storage so cross-tab activity is respected
      const stored = parseInt(localStorage.getItem(this._activityStorageKey()) || '0', 10);
      if (stored > this._lastActivity) this._lastActivity = stored;

      const idle = Date.now() - (this._lastActivity || Date.now());

      if (idle >= INACTIVITY_MS) {
        this._autoLogout();
      } else if (idle >= WARNING_MS && !this._warningShown) {
        this._showWarning(Math.ceil((INACTIVITY_MS - idle) / 1000));
      } else if (idle < WARNING_MS && this._warningShown) {
        this._hideWarning();
      }
    },

    // ── Warning modal ──────────────────────────────────────────────────────────

    _showWarning: function (secondsLeft) {
      if (this._warningShown) return;
      this._warningShown = true;
      this._remainingSeconds = secondsLeft || 120;

      const modal = document.getElementById(MODAL_ID);
      if (modal) {
        modal.style.display = 'flex';
        this._updateCountdown();
        this._countdownTimer = setInterval(() => {
          this._remainingSeconds--;
          this._updateCountdown();
          if (this._remainingSeconds <= 0) clearInterval(this._countdownTimer);
        }, 1000);
      }
      console.log('[DC-INACTIVITY] Warning shown for', this._cfg.portalName);
    },

    _hideWarning: function () {
      this._warningShown = false;
      if (this._countdownTimer) { clearInterval(this._countdownTimer); this._countdownTimer = null; }
      const modal = document.getElementById(MODAL_ID);
      if (modal) modal.style.display = 'none';
    },

    _updateCountdown: function () {
      const el = document.getElementById('dcInactivityCountdown');
      if (el) {
        const m = Math.floor(this._remainingSeconds / 60);
        const s = this._remainingSeconds % 60;
        el.textContent = m + ':' + String(s).padStart(2, '0');
      }
    },

    stayLoggedIn: function () {
      this._touch();
      this._hideWarning();
    },

    logoutNow: function () {
      this._hideWarning();
      this._performLogout();
    },

    // ── Logout ─────────────────────────────────────────────────────────────────

    _autoLogout: function () {
      this._hideWarning();
      console.log('[DC-INACTIVITY] Auto-logout: 15 min inactivity on', this._cfg.portalName);
      sessionStorage.setItem('dc_logout_reason_' + this._cfg.tokenKey, 'INACTIVITY_TIMEOUT');
      this._performLogout();
    },

    _performLogout: function () {
      if (!this._getToken()) { this._cleanup(); return; }
      this._cleanup();

      // Call custom logout function first (e.g. API call to invalidate server session)
      if (typeof this._cfg.logoutFn === 'function') {
        try { this._cfg.logoutFn(); } catch (_) {}
      }

      this._clearToken();
      // Clear companion keys (configured per portal)
      (this._cfg.companionKeys || []).forEach(k => {
        localStorage.removeItem(k);
        sessionStorage.removeItem(k);
      });

      window.location.href = this._cfg.loginUrl;
    },

    _cleanup: function () {
      if (this._checkTimer) { clearInterval(this._checkTimer); this._checkTimer = null; }
      if (this._countdownTimer) { clearInterval(this._countdownTimer); this._countdownTimer = null; }
      this._initialized = false;
    },

    // ── Modal HTML ─────────────────────────────────────────────────────────────

    _createModal: function () {
      if (document.getElementById(MODAL_ID)) return;
      const accent = this._cfg.accentColor || '#7c3aed';
      const portal = this._cfg.portalName || 'Portal';
      const el = document.createElement('div');
      el.id = MODAL_ID;
      el.style.cssText = 'display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.6);z-index:999999;justify-content:center;align-items:center;backdrop-filter:blur(4px)';
      el.innerHTML = `
        <div style="background:#fff;border-radius:18px;padding:36px 32px;max-width:400px;width:92%;text-align:center;box-shadow:0 24px 64px rgba(0,0,0,.28);animation:dcImSlideIn .3s ease-out">
          <div style="width:64px;height:64px;background:${accent}18;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 20px">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="${accent}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <h3 style="margin:0 0 8px;font-size:19px;font-weight:700;color:#1a1a2e">Session Expiring</h3>
          <p style="margin:0 0 6px;color:#6b7280;font-size:14px">You have been inactive on <strong>${portal}</strong>.</p>
          <p style="margin:0 0 24px;color:#6b7280;font-size:13px">You will be signed out in</p>
          <div id="dcInactivityCountdown" style="font-size:42px;font-weight:800;color:${accent};letter-spacing:-1px;margin-bottom:28px;font-variant-numeric:tabular-nums">2:00</div>
          <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
            <button onclick="DCInactivityManager.logoutNow()" style="padding:11px 22px;border-radius:9px;border:1.5px solid #e5e7eb;background:#f9fafb;color:#6b7280;font-size:14px;font-weight:600;cursor:pointer">Sign Out Now</button>
            <button onclick="DCInactivityManager.stayLoggedIn()" style="padding:11px 28px;border-radius:9px;border:none;background:${accent};color:#fff;font-size:14px;font-weight:700;cursor:pointer">Stay Signed In</button>
          </div>
          <p style="margin:18px 0 0;font-size:11px;color:#9ca3af">For your security, sessions expire after 15 minutes of inactivity.</p>
        </div>
      `;
      document.body.appendChild(el);

      // Inject keyframe if not already done
      if (!document.getElementById('dcImKeyframes')) {
        const style = document.createElement('style');
        style.id = 'dcImKeyframes';
        style.textContent = '@keyframes dcImSlideIn{from{opacity:0;transform:translateY(-20px)}to{opacity:1;transform:translateY(0)}}';
        document.head.appendChild(style);
      }
    },
  };

  global.DCInactivityManager = DCInactivityManager;

}(window));
