(function () {
  'use strict';
  // VGK4U Member Module Gate — Task #46
  // -----------------------------------
  // Each Phase-2 member page (vgk_member_feedback.html, _kyc.html, etc.)
  // includes this script with a data-flag attribute, e.g.:
  //   <script src="/vgk-member-module-gate.js" data-flag="kyc_vgk4u_enabled"></script>
  //
  // On load it fetches the public flag map and, if the page's flag is
  // false, replaces the page body with a "Module Disabled" overlay so
  // members get an immediate, page-level signal that Super-Admin has
  // turned this write surface off. Until the fetch resolves the page
  // remains visible (no flash-of-disabled), and on a transient fetch
  // failure we keep the page visible — the actual write endpoint is
  // the source of truth for blocking.
  //
  // Idempotent: the script tag is normally embedded once per page;
  // the global guard prevents double-execution if the page accidentally
  // includes the script twice.
  if (window.__vgk4uModuleGateLoaded) return;
  window.__vgk4uModuleGateLoaded = true;

  var script = document.currentScript;
  if (!script) {
    // Fallback for older renderers
    var scripts = document.getElementsByTagName('script');
    for (var i = scripts.length - 1; i >= 0; i--) {
      if (scripts[i].src && scripts[i].src.indexOf('vgk-member-module-gate.js') !== -1) {
        script = scripts[i];
        break;
      }
    }
  }
  var flagName = script && script.getAttribute('data-flag');
  if (!flagName) {
    console.warn('[vgk-member-module-gate] missing data-flag — gate not applied');
    return;
  }

  function showDisabledOverlay(humanLabel) {
    var label = humanLabel || flagName.replace(/_vgk4u_enabled$/, '').replace(/_/g, ' ');
    var html = ''
      + '<div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:#f6f9fc;padding:24px;font-family:Segoe UI,Roboto,sans-serif">'
      + '  <div style="max-width:480px;background:#fff;border:1px solid #fde68a;border-left:6px solid #f59e0b;border-radius:14px;padding:32px;text-align:center;box-shadow:0 4px 14px rgba(0,0,0,0.04)">'
      + '    <div style="font-size:48px;color:#f59e0b;margin-bottom:12px">⏸</div>'
      + '    <h2 style="font-size:20px;font-weight:800;color:#92400e;margin:0 0 8px">Module Disabled</h2>'
      + '    <p style="color:#475569;font-size:14px;margin:0 0 16px">'
      + '      The <strong>' + label + '</strong> module is currently turned off by your administrator.'
      + '      Please check back later or contact support if you need access.'
      + '    </p>'
      + '    <p style="color:#94a3b8;font-size:12px;margin:0">Flag: ' + flagName + '</p>'
      + '    <a href="/vgk/dashboard" style="display:inline-block;margin-top:18px;padding:8px 18px;background:#0d9488;color:#fff;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600">Back to Dashboard</a>'
      + '  </div>'
      + '</div>';
    if (document.body) {
      document.body.innerHTML = html;
    } else {
      document.addEventListener('DOMContentLoaded', function () { document.body.innerHTML = html; });
    }
  }

  fetch('/api/v1/super-admin/config/vgk4u-flags', { credentials: 'include' })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      if (!data || !data.flags) return; // fail-open on fetch error — endpoint already fails closed for Phase-2
      // Strict check: only hide when the server explicitly says false.
      // This matches the public endpoint's Zero-Default-Access semantics
      // for Phase-2 (default FALSE on the column → false in payload).
      if (data.flags[flagName] === false) {
        showDisabledOverlay(script && script.getAttribute('data-label'));
      }
    })
    .catch(function () { /* keep page visible on transient errors */ });
})();
