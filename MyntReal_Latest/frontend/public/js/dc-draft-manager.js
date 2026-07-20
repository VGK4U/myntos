/* DC Draft Manager — DC-DRAFT-001
 * Universal partial-save system for every form in the MNR/VGK4U platform.
 * Strategy: localStorage (instant) + backend sync every 30s + beforeunload capture.
 * TTL: 7 days. Restore banner shown on page load when a draft exists.
 *
 * DC-DRAFT-USER-SCOPE-001: key includes user-id so different staff on the same
 *   browser never see each other's drafts.
 * DC-DRAFT-CHANGE-DETECT-001: initial snapshot taken at init; draft is only saved
 *   and banner only shown when current data actually differs from the initial state.
 */
(function () {
  'use strict';

  var STORAGE_PREFIX = 'dc_draft_v1_';
  var SYNC_INTERVAL_MS = 30000;
  var DEBOUNCE_MS = 1500;
  var TTL_DAYS = 7;
  var API_BASE = '/api/v1/drafts';

  var SKIP_PAGES = [
    '/staff/login', '/partner/login', '/mnr/login', '/vgk/login',
    '/login', '/b2b-signup', '/public/', '/privacy-policy',
  ];

  function DCDraftManagerClass() {
    this._key = null;
    this._getDataFn = null;
    this._setDataFn = null;
    this._syncTimer = null;
    this._debounceTimer = null;
    this._banner = null;
    this._bannerEntry = null;
    this._initialized = false;
    this._initialSnapshot = null;
  }

  DCDraftManagerClass.prototype._getToken = function () {
    return localStorage.getItem('staff_token') ||
      localStorage.getItem('token') ||
      localStorage.getItem('partner_token') ||
      localStorage.getItem('member_token') || null;
  };

  // DC-DRAFT-USER-SCOPE-001: decode JWT payload to extract a stable user identifier.
  // Falls back to 'anon' so the draft still works even if decoding fails.
  DCDraftManagerClass.prototype._getUserId = function () {
    var token = this._getToken();
    if (!token) return 'anon';
    try {
      var parts = token.split('.');
      if (parts.length < 2) return 'anon';
      var payload = JSON.parse(atob(parts[1]));
      return String(payload.sub || payload.emp_code || payload.id || payload.email || 'anon');
    } catch (e) { return 'anon'; }
  };

  DCDraftManagerClass.prototype._deriveKey = function () {
    var path = location.pathname.replace(/^\/+|\/+$/g, '').replace(/\//g, '-') || 'home';
    return path + '_u' + this._getUserId();
  };

  DCDraftManagerClass.prototype._shouldSkip = function () {
    var path = location.pathname;
    for (var i = 0; i < SKIP_PAGES.length; i++) {
      if (path.indexOf(SKIP_PAGES[i]) === 0) return true;
    }
    return false;
  };

  DCDraftManagerClass.prototype._genericGetData = function () {
    var data = {};
    var inputs = document.querySelectorAll(
      'input:not([type=hidden]):not([type=password]):not([type=file]),' +
      'select, textarea'
    );
    inputs.forEach(function (el) {
      var key = el.id || (el.name ? ('_n_' + el.name) : null);
      if (!key) return;
      if (el.type === 'checkbox' || el.type === 'radio') {
        data[key] = el.checked;
      } else {
        var v = el.value || '';
        if (v !== '') data[key] = v;
      }
    });
    return data;
  };

  DCDraftManagerClass.prototype._genericSetData = function (data) {
    if (!data) return;
    Object.keys(data).forEach(function (key) {
      var value = data[key];
      var el;
      if (key.indexOf('_n_') === 0) {
        el = document.querySelector('[name="' + key.slice(3) + '"]:not([id])');
      } else {
        el = document.getElementById(key);
      }
      if (!el) return;
      try {
        if (el.type === 'checkbox' || el.type === 'radio') {
          el.checked = !!value;
          // DC-DRAFT-CASCADE-FIX-001: bubbles:false prevents draft restore from
          // cascading into oninput/onchange handlers (e.g. efNetSearch) which would
          // fire live API searches using stale values from a previous lead's session.
          el.dispatchEvent(new Event('change', { bubbles: false }));
        } else if (el.tagName === 'SELECT') {
          el.value = value;
          if (el.value !== value) {
            var opt = document.createElement('option');
            opt.value = value;
            opt.textContent = value;
            el.appendChild(opt);
            el.value = value;
          }
          el.dispatchEvent(new Event('change', { bubbles: false }));
        } else {
          el.value = value;
          el.dispatchEvent(new Event('input', { bubbles: false }));
        }
      } catch (e) {}
    });
  };

  // DC-DRAFT-CHANGE-DETECT-001: return true only if current form state differs
  // from the snapshot taken at init time. Prevents saving/showing banner when
  // the user never touched anything (e.g. filter inputs have default values).
  DCDraftManagerClass.prototype._hasChanges = function () {
    if (this._initialSnapshot === null) return false;
    var getFn = this._getDataFn || (function (self) {
      return function () { return self._genericGetData(); };
    })(this);
    var current = JSON.stringify(getFn());
    return current !== this._initialSnapshot;
  };

  DCDraftManagerClass.prototype._saveLocal = function (data) {
    if (!this._key || !data || Object.keys(data).length === 0) return;
    try {
      var entry = { data: data, ts: Date.now(), key: this._key, url: location.pathname };
      localStorage.setItem(STORAGE_PREFIX + this._key, JSON.stringify(entry));
    } catch (e) {}
  };

  DCDraftManagerClass.prototype._loadLocal = function () {
    if (!this._key) return null;
    try {
      var raw = localStorage.getItem(STORAGE_PREFIX + this._key);
      if (!raw) return null;
      var entry = JSON.parse(raw);
      if (Date.now() - entry.ts > TTL_DAYS * 86400000) {
        localStorage.removeItem(STORAGE_PREFIX + this._key);
        return null;
      }
      return entry;
    } catch (e) { return null; }
  };

  DCDraftManagerClass.prototype._syncToBackend = function () {
    var self = this;
    var token = self._getToken();
    if (!token || !self._key) return;
    // DC-DRAFT-CHANGE-DETECT-001: never sync to backend if nothing changed
    if (!self._hasChanges()) return;
    try {
      var getFn = self._getDataFn || function () { return self._genericGetData(); };
      var formData = getFn();
      if (!formData || Object.keys(formData).length === 0) return;
      fetch(API_BASE + '/' + encodeURIComponent(self._key), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token,
        },
        body: JSON.stringify({ draft_data: JSON.stringify(formData), page_url: location.pathname }),
        keepalive: true,
      }).catch(function () {});
    } catch (e) {}
  };

  DCDraftManagerClass.prototype._loadFromBackend = function () {
    var self = this;
    var token = self._getToken();
    if (!token || !self._key) return Promise.resolve(null);
    return fetch(API_BASE + '/' + encodeURIComponent(self._key), {
      headers: { 'Authorization': 'Bearer ' + token },
    }).then(function (r) {
      if (!r.ok) return null;
      return r.json().then(function (d) {
        try { return d.draft_data ? JSON.parse(d.draft_data) : null; } catch (e) { return null; }
      });
    }).catch(function () { return null; });
  };

  DCDraftManagerClass.prototype._timeAgo = function (ts) {
    var diff = Math.floor((Date.now() - ts) / 1000);
    if (diff < 120) return 'just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    return Math.floor(diff / 86400) + 'd ago';
  };

  DCDraftManagerClass.prototype._showRestoreBanner = function (entry) {
    if (this._banner || !entry) return;
    var self = this;
    var ago = self._timeAgo(entry.ts || Date.now());
    var banner = document.createElement('div');
    banner.id = 'dc-draft-restore-banner';
    banner.setAttribute('style',
      'position:fixed;top:0;left:0;right:0;z-index:2147483647;' +
      'background:linear-gradient(90deg,#1e3a8a,#1d4ed8);color:#fff;' +
      'padding:10px 16px;display:flex;align-items:center;gap:10px;' +
      'font-size:13px;font-family:system-ui,-apple-system,sans-serif;' +
      'box-shadow:0 3px 12px rgba(0,0,0,.3);'
    );
    banner.innerHTML =
      '<span style="font-size:16px;">💾</span>' +
      '<span style="flex:1;line-height:1.4;">Unsaved draft found from <strong>' + ago + '</strong> — your work was partially saved before the page closed.</span>' +
      '<button id="dc-draft-restore-btn" style="background:#fff;color:#1d4ed8;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-weight:700;font-size:12px;white-space:nowrap;">↩ Restore Draft</button>' +
      '<button id="dc-draft-discard-btn" style="background:rgba(255,255,255,.15);color:#fff;border:1px solid rgba(255,255,255,.35);padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px;white-space:nowrap;">✕ Discard</button>';
    this._banner = banner;
    this._bannerEntry = entry;
    document.body.insertBefore(banner, document.body.firstChild);
    document.getElementById('dc-draft-restore-btn').addEventListener('click', function () { self._restoreFromBanner(); });
    document.getElementById('dc-draft-discard-btn').addEventListener('click', function () { self._dismissBanner(); });
  };

  DCDraftManagerClass.prototype._restoreFromBanner = function () {
    if (!this._bannerEntry) return;
    var setFn = this._setDataFn || (function (self) {
      return function (d) { self._genericSetData(d); };
    })(this);
    setFn(this._bannerEntry.data);
    if (this._banner) { this._banner.remove(); this._banner = null; }
    this._bannerEntry = null;
    if (window.showToast) showToast('Draft restored successfully', 'success');
  };

  DCDraftManagerClass.prototype._dismissBanner = function () {
    if (this._banner) { this._banner.remove(); this._banner = null; }
    this._bannerEntry = null;
    this.clear();
  };

  DCDraftManagerClass.prototype._onInput = function () {
    var self = this;
    clearTimeout(self._debounceTimer);
    self._debounceTimer = setTimeout(function () {
      // DC-DRAFT-CHANGE-DETECT-001: only save if something actually changed
      if (!self._hasChanges()) return;
      var getFn = self._getDataFn || function () { return self._genericGetData(); };
      var data = getFn();
      if (data && Object.keys(data).length > 0) self._saveLocal(data);
    }, DEBOUNCE_MS);
  };

  DCDraftManagerClass.prototype.clear = function () {
    if (!this._key) return;
    try { localStorage.removeItem(STORAGE_PREFIX + this._key); } catch (e) {}
    var token = this._getToken();
    if (token) {
      fetch(API_BASE + '/' + encodeURIComponent(this._key), {
        method: 'DELETE',
        headers: { 'Authorization': 'Bearer ' + token },
        keepalive: true,
      }).catch(function () {});
    }
  };

  DCDraftManagerClass.prototype.init = function (key, getDataFn, setDataFn) {
    // DC-DRAFT-USER-SCOPE-001: always suffix the key with the current user's id
    // so two different staff members on the same browser never share a draft.
    var userId = this._getUserId();
    var scopedKey = key + '_u' + userId;
    if (this._initialized && this._key === scopedKey) return;
    if (this._shouldSkip()) return;

    this._key = scopedKey;
    this._getDataFn = getDataFn || null;
    this._setDataFn = setDataFn || null;
    this._initialized = true;

    var self = this;

    // DC-DRAFT-CHANGE-DETECT-001: take an initial snapshot of the form state
    // so we can detect whether the user actually changed anything.
    // Defer by one tick so page scripts have time to set default values first.
    setTimeout(function () {
      var getFn = self._getDataFn || function () { return self._genericGetData(); };
      self._initialSnapshot = JSON.stringify(getFn());
    }, 0);

    document.addEventListener('input', function () { self._onInput(); }, true);
    document.addEventListener('change', function () { self._onInput(); }, true);

    if (self._syncTimer) clearInterval(self._syncTimer);
    self._syncTimer = setInterval(function () { self._syncToBackend(); }, SYNC_INTERVAL_MS);

    window.addEventListener('beforeunload', function () {
      // DC-DRAFT-CHANGE-DETECT-001: only capture on unload if something changed
      if (!self._hasChanges()) return;
      var getFn = self._getDataFn || function () { return self._genericGetData(); };
      var data = getFn();
      if (!data || Object.keys(data).length === 0) return;
      self._saveLocal(data);
      self._syncToBackend();
    });

    var localEntry = self._loadLocal();
    if (localEntry && localEntry.data && Object.keys(localEntry.data).length > 0) {
      // DC-DRAFT-CHANGE-DETECT-001: compare saved draft against initial page state.
      // Defer so the page has finished rendering its default values before we compare.
      setTimeout(function () {
        var getFn = self._getDataFn || function () { return self._genericGetData(); };
        var pageNow = JSON.stringify(getFn());
        var savedStr = JSON.stringify(localEntry.data);
        if (savedStr !== pageNow) {
          self._showRestoreBanner(localEntry);
        }
      }, 200);
    } else {
      self._loadFromBackend().then(function (data) {
        if (data && Object.keys(data).length > 0) {
          setTimeout(function () {
            var getFn = self._getDataFn || function () { return self._genericGetData(); };
            var pageNow = JSON.stringify(getFn());
            var savedStr = JSON.stringify(data);
            if (savedStr !== pageNow) {
              var backendEntry = { data: data, ts: Date.now() - 300000 };
              self._showRestoreBanner(backendEntry);
            }
          }, 200);
        }
      });
    }
  };

  DCDraftManagerClass.prototype.autoWire = function () {
    if (this._shouldSkip()) return;
    var key = window.DC_DRAFT_KEY || this._deriveKey();
    this.init(key, null, null);
  };

  var instance = new DCDraftManagerClass();
  window.DCDraftManager = instance;

  function tryAutoWire() {
    // DC-DRAFT-OPT-IN-001: Only auto-wire on pages that explicitly set
    // window.DC_DRAFT_ENABLED = true.  Prevents the restore-draft banner
    // from appearing on view/list pages (members, dashboard, etc.) that
    // happen to have filter inputs but no actual save action.
    if (!window.DC_DRAFT_ENABLED) return;
    if (instance._initialized) return;
    instance.autoWire();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', tryAutoWire);
  } else {
    tryAutoWire();
  }
})();
