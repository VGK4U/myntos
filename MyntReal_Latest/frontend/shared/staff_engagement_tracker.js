/**
 * Staff Engagement & Screen Time Tracker (DC Protocol Compliant)
 * 
 * Tracks:
 * 1. On-Screen Time: Tab/Window is visible to user
 * 2. Actively Engaged Time: User is interacting (mouse, typing, touch, scrolling) or on active softphone call
 * 3. Passive event listeners with throttling for zero CPU overhead
 * 4. Batched sync every 3 minutes + navigator.sendBeacon on exit
 * 5. Rule 6 Compliant: Softphone controller is immutable; only session state is inspected
 */

(function (global) {
  'use strict';

  const SYNC_INTERVAL_MS = 3 * 60 * 1000; // Sync every 3 minutes
  const IDLE_THRESHOLD_MS = 60 * 1000;     // 60 seconds without input = idle

  function getTodayKey() {
    const d = new Date();
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  }

  const StaffEngagementTracker = {
    _initialized: false,
    _lastInteraction: Date.now(),
    _timer: null,
    _syncTimer: null,
    _deltaActiveSeconds: 0,
    _deltaScreenSeconds: 0,
    _todayDateStr: getTodayKey(),

    init: function () {
      if (this._initialized) return;

      const token = localStorage.getItem('staff_token') || localStorage.getItem('token');
      if (!token) return;

      this._todayDateStr = getTodayKey();
      this._lastInteraction = Date.now();
      this._bindEvents();
      this._startTick();
      this._startSyncSchedule();
      this._initialized = true;
      console.log('[DC-TRACKER] Engagement & Screen Time Tracker initialized');
    },

    _bindEvents: function () {
      const markActive = () => {
        const now = Date.now();
        // Throttle to update timestamp at most once every 5 seconds
        if (now - this._lastInteraction > 5000) {
          this._lastInteraction = now;
        }
      };

      const opts = { passive: true, capture: true };
      window.addEventListener('mousemove', markActive, opts);
      window.addEventListener('mousedown', markActive, opts);
      window.addEventListener('keydown', markActive, opts);
      window.addEventListener('touchstart', markActive, opts);
      window.addEventListener('scroll', markActive, opts);

      // Flush delta when visibility changes or user navigates away
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
          this._flush(true);
        } else {
          this._lastInteraction = Date.now();
        }
      });

      window.addEventListener('pagehide', () => this._flush(true));
      window.addEventListener('beforeunload', () => this._flush(true));
    },

    _isSoftphoneActive: function () {
      try {
        if (global.PlivoSoftphone && global.PlivoSoftphone.currentSession && global.PlivoSoftphone.currentSession.state === 'connected') {
          return true;
        }
        if (global.softphoneService && typeof global.softphoneService.isCallActive === 'function' && global.softphoneService.isCallActive()) {
          return true;
        }
      } catch (e) {}
      return false;
    },

    _startTick: function () {
      this._timer = setInterval(() => {
        const isVisible = document.visibilityState === 'visible';
        if (!isVisible) return;

        this._deltaScreenSeconds++;

        const isInteracting = (Date.now() - this._lastInteraction) < IDLE_THRESHOLD_MS;
        const isCalling = this._isSoftphoneActive();

        if (isInteracting || isCalling) {
          this._deltaActiveSeconds++;
        }
      }, 1000);
    },

    _startSyncSchedule: function () {
      this._syncTimer = setInterval(() => {
        this._flush(false);
      }, SYNC_INTERVAL_MS);
    },

    _flush: function (isBeacon) {
      if (this._deltaActiveSeconds <= 0 && this._deltaScreenSeconds <= 0) return;

      const payload = {
        active_seconds: this._deltaActiveSeconds,
        screen_seconds: this._deltaScreenSeconds,
        date: this._todayDateStr
      };

      // Reset local deltas immediately to avoid double-counting
      const sendActive = this._deltaActiveSeconds;
      const sendScreen = this._deltaScreenSeconds;
      this._deltaActiveSeconds = 0;
      this._deltaScreenSeconds = 0;

      const token = localStorage.getItem('staff_token') || localStorage.getItem('token');
      if (!token) return;

      const endpoint = '/api/v1/staff/attendance/heartbeat-activity';

      if (isBeacon && typeof navigator.sendBeacon === 'function') {
        try {
          const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
          const sent = navigator.sendBeacon(endpoint, blob);
          if (sent) return;
        } catch (e) {}
      }

      fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload),
        keepalive: true
      }).catch(err => {
        // Restore deltas if network failed so time is not lost
        this._deltaActiveSeconds += sendActive;
        this._deltaScreenSeconds += sendScreen;
      });
    }
  };

  // Auto-initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => StaffEngagementTracker.init());
  } else {
    StaffEngagementTracker.init();
  }

  global.StaffEngagementTracker = StaffEngagementTracker;
})(typeof window !== 'undefined' ? window : this);
