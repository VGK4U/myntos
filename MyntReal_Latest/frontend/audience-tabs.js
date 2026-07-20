/**
 * VGK4U Member Parity — Phase 1
 * Reusable audience-tab component for staff admin pages.
 *
 * Adds an MNR Members | VGK4U Members tab strip at the top of any admin page.
 * Tabs control a global `window.AUDIENCE` value ('mnr' | 'vgk4u') and dispatch
 * an `audience:changed` CustomEvent so each page can refetch its own data.
 *
 * Usage:
 *   <script src="/audience-tabs.js"></script>
 *   <script>
 *     AudienceTabs.mount({
 *       container: 'audienceTabsHost',          // element id (created if missing)
 *       defaultAudience: 'mnr',                  // 'mnr' | 'vgk4u'
 *       onChange: (audience) => loadData(audience),
 *       page: 'admin_birthdays',                 // for audit-log context
 *     });
 *
 *     // or read at any time:
 *     const a = AudienceTabs.current();          // 'mnr' | 'vgk4u'
 *     fetch(`/api/v1/admin/birthdays-today?audience=${a}`)
 *   </script>
 */
(function () {
  // [DC_T33_DEFAULT_MNR_001] Default audience MUST be MNR on every page mount.
  // Storage key intentionally retained for in-page session continuity, but
  // it is NOT consulted at mount time — opening any admin page begins with
  // the zero-change baseline (MNR), preserving backward-compat UX.
  const STORAGE_KEY = 'vgk4u_audience_session';
  const DEFAULT_AUDIENCE = 'mnr';

  function writeStored(value) {
    try { sessionStorage.setItem(STORAGE_KEY, value); } catch (_) {}
  }

  function getISTTimestamp() {
    // [DC-IST-001] Project standard: never `.toISOString()` (UTC). Build
    // an Asia/Kolkata-local "YYYY-MM-DD HH:mm:ss" string instead.
    try {
      const opts = {
        timeZone: 'Asia/Kolkata',
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
        hour12: false,
      };
      const parts = new Intl.DateTimeFormat('en-GB', opts).formatToParts(new Date());
      const get = (t) => (parts.find((p) => p.type === t) || {}).value || '';
      return `${get('year')}-${get('month')}-${get('day')} ${get('hour')}:${get('minute')}:${get('second')} IST`;
    } catch (_) {
      return '';
    }
  }

  function ensureContainer(id) {
    let el = document.getElementById(id);
    if (el) return el;
    el = document.createElement('div');
    el.id = id;
    document.body.insertBefore(el, document.body.firstChild);
    return el;
  }

  function injectStyles() {
    if (document.getElementById('audience-tabs-styles')) return;
    const css = `
      .audience-tabs-bar { display:flex; gap:8px; padding:10px 14px; background:#0f172a;
        border-bottom:2px solid #1e293b; position:sticky; top:0; z-index:1040; }
      .audience-tabs-bar .at-label { color:#94a3b8; font-size:12px; align-self:center;
        margin-right:6px; text-transform:uppercase; letter-spacing:.5px; font-weight:600; }
      .audience-tabs-bar button.at-tab { background:transparent; color:#cbd5e1;
        border:1px solid #334155; border-radius:8px; padding:6px 14px; font-size:13px;
        font-weight:500; cursor:pointer; transition:all .15s; display:flex; align-items:center; gap:6px; }
      .audience-tabs-bar button.at-tab:hover { border-color:#3b82f6; color:#fff; }
      .audience-tabs-bar button.at-tab.active { background:#3b82f6; color:#fff;
        border-color:#3b82f6; font-weight:600; }
      .audience-tabs-bar button.at-tab.vgk.active { background:#0ea5e9; border-color:#0ea5e9; }
      .audience-tabs-bar .at-meta { margin-left:auto; align-self:center; color:#64748b; font-size:11px; }
    `;
    const style = document.createElement('style');
    style.id = 'audience-tabs-styles';
    style.textContent = css;
    document.head.appendChild(style);
  }

  async function logAudit(page, from, to) {
    // [DC-AUDIT] non-blocking audit log for audience tab switch
    try {
      const token = localStorage.getItem('authToken') ||
                    localStorage.getItem('staff_token') || '';
      if (!token) return;
      await fetch('/api/v1/audit/audience-switch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ page, from, to, ts: getISTTimestamp() }),
      }).catch(() => {});
    } catch (_) {}
  }

  const AudienceTabs = {
    _audience: DEFAULT_AUDIENCE,
    _page: '',
    // [DC_T36_TOGGLE_GATE_001] When the page has declared `data-flag="..."`
    // and the Super-Admin toggle for that module is OFF, we hide the VGK4U
    // tab entirely and force MNR-only mode so VGK4U-side pages fall back to
    // an MNR view on next render. `null` = unknown / no gate applied.
    _vgk4uEnabled: null,
    _flagKey: '',

    current() { return this._audience; },
    isVgk4uEnabled() { return this._vgk4uEnabled !== false; },

    set(audience) {
      const v = (audience === 'vgk4u') ? 'vgk4u' : 'mnr';
      const prev = this._audience;
      if (v === prev) return;
      this._audience = v;
      writeStored(v);
      this._render();
      logAudit(this._page, prev, v);
      document.dispatchEvent(new CustomEvent('audience:changed', { detail: { audience: v, previous: prev } }));
    },

    mount(opts) {
      opts = opts || {};
      injectStyles();
      this._page = opts.page || (location.pathname || '').replace(/^\//, '') || 'unknown';
      this._flagKey = opts.flagKey || '';
      // [DC_T33_DEFAULT_MNR_001] Always start from MNR baseline at mount time.
      // We deliberately do NOT consult any stored value here so every admin
      // page opens with the unchanged pre-Task-#33 view; user can manually
      // switch tabs as needed within the page.
      this._audience = (opts.defaultAudience === 'vgk4u') ? 'vgk4u' : 'mnr';

      this._host = ensureContainer(opts.container || 'audienceTabsHost');
      this._render();

      if (typeof opts.onChange === 'function') {
        document.addEventListener('audience:changed', (e) => {
          try { opts.onChange(e.detail.audience); } catch (err) { console.error('audience onChange failed', err); }
        });
        // Fire once on mount
        try { opts.onChange(this._audience); } catch (err) { console.error(err); }
      }

      // [DC_T36_TOGGLE_GATE_001] Resolve the per-module flag in the
      // background. The page renders immediately with the optimistic
      // baseline; once the flag arrives, we re-render and (if OFF)
      // dispatch audience:changed so the page falls back to MNR-only.
      if (this._flagKey) {
        Promise.resolve().then(() => this._applyFlagGate());
      }
    },

    _render() {
      if (!this._host) return;
      const a = this._audience;
      const vgkOff = this._vgk4uEnabled === false;
      // [DC_T36_TOGGLE_GATE_001] Hide the VGK4U tab when the per-module
      // flag is OFF. Page falls back to MNR-only mode (single tab visible).
      const vgkBtn = vgkOff ? '' : `
          <button type="button" class="at-tab vgk ${a === 'vgk4u' ? 'active' : ''}" data-aud="vgk4u" role="tab" aria-selected="${a === 'vgk4u'}">
            <i class="bi bi-stars"></i> VGK4U Members
          </button>`;
      const meta = vgkOff
        ? `<span class="at-meta" title="VGK4U disabled by Super-Admin"><i class="bi bi-info-circle"></i> VGK4U module disabled — MNR-only</span>`
        : `<span class="at-meta">Showing: <strong>${a === 'vgk4u' ? 'VGK4U' : 'MNR'}</strong></span>`;
      this._host.innerHTML = `
        <div class="audience-tabs-bar" role="tablist" aria-label="Audience selector">
          <span class="at-label">Audience:</span>
          <button type="button" class="at-tab mnr ${a === 'mnr' ? 'active' : ''}" data-aud="mnr" role="tab" aria-selected="${a === 'mnr'}">
            <i class="bi bi-people-fill"></i> MNR Members
          </button>${vgkBtn}
          ${meta}
        </div>
      `;
      const self = this;
      this._host.querySelectorAll('button.at-tab').forEach((btn) => {
        btn.addEventListener('click', () => self.set(btn.getAttribute('data-aud')));
      });
    },

    // [DC_T36_TOGGLE_GATE_001] Fetch the public Super-Admin flag map and,
    // if this page declared `data-flag="<col>"`, apply the gate. When the
    // flag is OFF we force the active audience to MNR and dispatch
    // `audience:changed` so the host page re-fetches its data in MNR mode.
    async _applyFlagGate() {
      if (!this._flagKey) return;
      try {
        const res = await fetch('/api/v1/super-admin/config/vgk4u-flags', {
          headers: { 'Accept': 'application/json' },
        });
        if (!res.ok) return;
        const j = await res.json();
        const flags = (j && j.flags) || {};
        // Default-True semantics: only treat an explicit `false` as OFF.
        const enabled = flags[this._flagKey] !== false;
        this._vgk4uEnabled = enabled;
        if (!enabled) {
          const prev = this._audience;
          this._audience = 'mnr';
          this._render();
          if (prev !== 'mnr') {
            try {
              document.dispatchEvent(new CustomEvent('audience:changed', { detail: { audience: 'mnr', previous: prev, reason: 'flag_off' } }));
              window.dispatchEvent(new CustomEvent('audience:changed', { detail: { audience: 'mnr', previous: prev, reason: 'flag_off' } }));
            } catch (_) {}
          } else {
            // Even when audience didn't change, signal so the page can
            // re-render any "VGK4U disabled" notice if it cares.
            try {
              document.dispatchEvent(new CustomEvent('audience:flag-resolved', { detail: { flag: this._flagKey, enabled: false } }));
            } catch (_) {}
          }
        } else {
          this._render();
          try {
            document.dispatchEvent(new CustomEvent('audience:flag-resolved', { detail: { flag: this._flagKey, enabled: true } }));
          } catch (_) {}
        }
      } catch (_) {
        // On any error, leave the tab visible (fail-open) — matches the
        // backend's default-True semantics for missing/unknown flags.
      }
    },

    /** Helper that appends ?audience=… to a URL, only if non-default. */
    withParam(url) {
      const a = this._audience;
      if (a === 'mnr') return url;
      const sep = url.includes('?') ? '&' : '?';
      return `${url}${sep}audience=${encodeURIComponent(a)}`;
    },
  };

  window.AudienceTabs = AudienceTabs;

  // ---------------------------------------------------------------------
  // [DC-AT-AUTOMOUNT-001] Auto-mount + jQuery.ajax interceptor
  //
  // Pages that include this script via <script src="/audience-tabs.js" data-page="X">
  // will get the MNR | VGK4U strip auto-mounted and ALL outgoing
  // jQuery.ajax requests to /api/v1/banners/admin/* /api/v1/admin/* will
  // automatically receive ?audience=<current> appended (only when current
  // !== 'mnr', preserving backward compatibility for default-audience calls).
  //
  // To opt-out per page, add data-noauto on the script tag.
  // ---------------------------------------------------------------------

  function pageNameFromScript() {
    try {
      const scripts = document.querySelectorAll('script[src*="/audience-tabs.js"]');
      const last = scripts[scripts.length - 1];
      return (last && last.getAttribute('data-page')) || (location.pathname || '').replace(/^\//, '') || 'unknown';
    } catch (_) { return 'unknown'; }
  }

  // [DC_T36_TOGGLE_GATE_001] Pages that want flag-gated VGK4U tabs declare
  // their AppSettings flag column on the script tag itself, e.g.:
  //   <script src="/audience-tabs.js"
  //           data-page="vgk_member_birthdays"
  //           data-flag="birthdays_vgk4u_enabled"></script>
  function flagKeyFromScript() {
    try {
      const scripts = document.querySelectorAll('script[src*="/audience-tabs.js"]');
      const last = scripts[scripts.length - 1];
      return (last && last.getAttribute('data-flag')) || '';
    } catch (_) { return ''; }
  }

  function shouldAppendAudienceTo(url) {
    if (typeof url !== 'string') return false;
    // Only inject for admin-scoped APIs to avoid breaking unrelated calls
    return /\/api\/v1\/(?:admin|banners\/admin|banners\/top-performers|super-admin\/awards|finance\/awards|rvz\/awards|ev-discount\/admin)/.test(url);
  }

  function patchJqueryAjax() {
    const $ = window.jQuery || window.$;
    if (!$ || !$.ajaxPrefilter || $._audienceTabsPatched) return;
    $._audienceTabsPatched = true;
    $.ajaxPrefilter(function (options /* , originalOptions, jqXHR */) {
      try {
        const a = AudienceTabs.current();
        if (a === 'mnr') return; // Default — never mutate URL
        if (!shouldAppendAudienceTo(options.url)) return;
        // Skip if caller already supplied audience explicitly
        if (/[?&]audience=/.test(options.url)) return;
        const sep = options.url.indexOf('?') === -1 ? '?' : '&';
        options.url = options.url + sep + 'audience=' + encodeURIComponent(a);
      } catch (_) {}
    });
  }

  // [DC_T33_FETCH_PATCH_001] Mirror the jQuery prefilter for native fetch().
  // Many admin pages use fetch() (not jQuery) — without this patch, audience
  // selection would only affect jQuery callers and silently default to MNR
  // for everything else, defeating the purpose of the tab switch.
  function patchWindowFetch() {
    if (typeof window.fetch !== 'function' || window._audienceTabsFetchPatched) return;
    window._audienceTabsFetchPatched = true;
    const original = window.fetch.bind(window);

    function rewriteUrl(rawUrl) {
      try {
        const a = AudienceTabs.current();
        if (a === 'mnr') return rawUrl;                      // Default — never mutate
        if (typeof rawUrl !== 'string') return rawUrl;       // Request object handled below
        if (!shouldAppendAudienceTo(rawUrl)) return rawUrl;
        if (/[?&]audience=/.test(rawUrl)) return rawUrl;     // Caller already set it
        const sep = rawUrl.indexOf('?') === -1 ? '?' : '&';
        return rawUrl + sep + 'audience=' + encodeURIComponent(a);
      } catch (_) {
        return rawUrl;
      }
    }

    window.fetch = function (input, init) {
      try {
        // Case 1: string URL — most common path used by admin pages.
        if (typeof input === 'string') {
          return original(rewriteUrl(input), init);
        }
        // Case 2: Request object — clone with rewritten URL when needed.
        if (typeof Request !== 'undefined' && input instanceof Request) {
          const rewritten = rewriteUrl(input.url);
          if (rewritten === input.url) return original(input, init);
          // Preserve method, headers, body, mode, etc.
          return original(new Request(rewritten, input), init);
        }
      } catch (_) {
        // Fall through to untouched call on any unexpected error
      }
      return original(input, init);
    };
  }

  function autoMount() {
    // Skip auto-mount if explicitly disabled OR if a page already mounted manually
    const scripts = document.querySelectorAll('script[src*="/audience-tabs.js"]');
    const last = scripts[scripts.length - 1];
    if (last && last.hasAttribute('data-noauto')) return;
    if (document.getElementById('audience-tabs-styles') && AudienceTabs._host) return; // already mounted
    AudienceTabs.mount({
      container: 'audienceTabsHost',
      page: pageNameFromScript(),
      flagKey: flagKeyFromScript(),
      onChange: function () {
        // Best-effort: trigger a window event so existing pages can refetch
        try {
          window.dispatchEvent(new CustomEvent('audience:changed', {
            detail: { audience: AudienceTabs.current() }
          }));
        } catch (_) {}
      },
    });
  }

  // Patch fetch() immediately (not deferred) so any early in-page fetch
  // (e.g. fired from inline <script> blocks before DOMContentLoaded) is
  // also covered. jQuery prefilter is patched on DOM ready when jQuery
  // is available.
  patchWindowFetch();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { autoMount(); patchJqueryAjax(); patchWindowFetch(); });
  } else {
    autoMount();
    patchJqueryAjax();
    patchWindowFetch();
  }
})();
