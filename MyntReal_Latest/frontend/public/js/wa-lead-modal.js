/**
 * wa-lead-modal.js  — DC Protocol: Unified WhatsApp Lead Send Modal
 * Used by: staff_leads.html, staff_team_leads.html, staff_my_leads.html,
 *          staff_crm_team_leads.html
 *
 * Entry point: window.openLeadWAModal(leadId, phone, name, companyId)
 * Uses native fetch() with credentials — no dependency on page's staffFetch.
 */
(function () {
  'use strict';

  var API = '/api/v1/whatsapp-config';

  /* ── Modal HTML ──────────────────────────────────────────────────────────── */
  var MODAL_HTML = [
    '<div id="_lwaModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:99999;align-items:center;justify-content:center;padding:16px;box-sizing:border-box">',
    '<div style="background:#fff;border-radius:16px;width:100%;max-width:540px;max-height:92vh;overflow-y:auto;box-shadow:0 24px 80px rgba(0,0,0,.3)">',

    /* header */
    '<div style="background:linear-gradient(135deg,#128c7e,#25D366);color:#fff;padding:14px 18px;border-radius:16px 16px 0 0;display:flex;justify-content:space-between;align-items:flex-start;position:sticky;top:0;z-index:2">',
    '<div><div style="font-weight:700;font-size:15px"><i class="fab fa-whatsapp"></i> Send WhatsApp</div>',
    '<div id="_lwaSub" style="font-size:11px;opacity:.85;margin-top:2px"></div></div>',
    '<button onclick="window._lwaClose()" style="background:none;border:none;color:#fff;font-size:22px;cursor:pointer;line-height:1;padding:0 2px">&times;</button>',
    '</div>',

    /* body */
    '<div style="padding:18px">',

    /* mode toggle */
    '<div style="display:flex;gap:6px;margin-bottom:16px;background:#f3f4f6;border-radius:10px;padding:4px">',
    '<button id="_lwaBtnComp" onclick="window._lwaMode(\'company\')" style="flex:1;padding:8px 6px;border:none;border-radius:7px;font-size:12px;font-weight:700;cursor:pointer;transition:all .15s"><i class="fas fa-building"></i> Company WA<small style="display:block;font-weight:400;font-size:10px;margin-top:1px">Via Meta API · Gets logged</small></button>',
    '<button id="_lwaBtnDir"  onclick="window._lwaMode(\'direct\')"  style="flex:1;padding:8px 6px;border:none;border-radius:7px;font-size:12px;font-weight:700;cursor:pointer;transition:all .15s"><i class="fab fa-whatsapp"></i> Direct WA<small style="display:block;font-weight:400;font-size:10px;margin-top:1px">Opens WhatsApp app/web</small></button>',
    '</div>',

    /* filters */
    '<div id="_lwaFilters" style="display:flex;gap:8px;margin-bottom:12px">',
    '<select id="_lwaSeg" onchange="window._lwaLoadTpls()" style="flex:1;font-size:12px;padding:6px 8px;border:1px solid #e5e7eb;border-radius:7px;background:#fff">',
    '<option value="">All Segments</option>',
    '<option value="general">MNR General</option>',
    '<option value="solar">Solar</option>',
    '<option value="myntreal_real">Myntreal Real</option>',
    '<option value="ev_b2c">EV B2C</option>',
    '<option value="ev_b2b">EV B2B</option>',
    '<option value="real_estate">Real Estate</option>',
    '<option value="etc_training">ETC Training</option>',
    '<option value="vgk">VGK Members</option>',
    '<option value="system">System</option>',
    '</select>',
    '<select id="_lwaCat" onchange="window._lwaLoadTpls()" style="flex:1;font-size:12px;padding:6px 8px;border:1px solid #e5e7eb;border-radius:7px;background:#fff">',
    '<option value="">All Categories</option>',
    '<option value="MARKETING">Marketing</option>',
    '<option value="UTILITY">Utility</option>',
    '<option value="AUTHENTICATION">Authentication</option>',
    '</select>',
    '</div>',

    /* template selector */
    '<div style="margin-bottom:12px">',
    '<label id="_lwaTplLbl" style="font-size:10.5px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;display:block;margin-bottom:4px">Template (Meta-approved)</label>',
    '<select id="_lwaTpl" onchange="window._lwaTplChange()" style="width:100%;font-size:12px;border:1px solid #e5e7eb;border-radius:7px;padding:6px 9px;background:#fff;box-sizing:border-box">',
    '<option value="">— Loading templates… —</option>',
    '</select>',
    '<div id="_lwaNoTpl" style="display:none;margin-top:6px;font-size:11px;color:#b45309;background:#fef3c7;border:1px solid #fde68a;border-radius:6px;padding:8px 10px">',
    '<i class="fas fa-exclamation-triangle me-1"></i>No approved templates for this filter. Change filters or ask an admin to submit a template for Meta approval.',
    '</div>',
    '</div>',

    /* variable fill */
    '<div id="_lwaVars" style="display:none;margin-bottom:12px">',
    '<div style="font-size:10.5px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;margin-bottom:7px">Fill in variables</div>',
    '<div id="_lwaVarBox"></div>',
    '</div>',

    /* message */
    '<div style="margin-bottom:12px">',
    '<label style="font-size:10.5px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;display:block;margin-bottom:4px">Message <small style="text-transform:none;font-weight:400">(auto-filled from template, or write custom)</small></label>',
    '<textarea id="_lwaMsg" rows="6" style="width:100%;font-size:13px;font-family:\'Segoe UI\',system-ui,-apple-system,sans-serif;line-height:1.55;border:1px solid #e5e7eb;border-radius:7px;padding:10px;resize:vertical;box-sizing:border-box;white-space:pre-wrap" placeholder="Select a template above or type your message…"></textarea>',
    '</div>',

    /* result */
    '<div id="_lwaResult" style="display:none;padding:9px 12px;border-radius:8px;font-size:12px;margin-bottom:12px"></div>',

    /* buttons */
    '<div style="display:flex;gap:8px;justify-content:flex-end">',
    '<button onclick="window._lwaClose()" style="padding:8px 18px;border:1.5px solid #e5e7eb;border-radius:8px;background:#fff;color:#374151;font-size:12px;cursor:pointer">Cancel</button>',
    '<button id="_lwaSend" onclick="window._lwaDoSend()" style="padding:8px 20px;background:#25D366;color:#fff;border:none;border-radius:8px;font-size:12px;font-weight:700;cursor:pointer;min-width:140px"><i class="fab fa-whatsapp"></i> <span id="_lwaSendLbl">Send via Meta</span></button>',
    '</div>',

    '</div></div></div>'
  ].join('');

  /* ── State ───────────────────────────────────────────────────────────────── */
  var _s = { leadId: null, phone: null, name: null, companyId: null, mode: 'company', tpls: [], bodyTpl: '' };

  /* ── Inject modal ────────────────────────────────────────────────────────── */
  function _ensure() {
    if (document.getElementById('_lwaModal')) return;
    var wrap = document.createElement('div');
    wrap.innerHTML = MODAL_HTML;
    document.body.appendChild(wrap.firstElementChild);
  }

  /* ── Helpers ─────────────────────────────────────────────────────────────── */
  function _esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function _showRes(msg, ok) {
    var el = document.getElementById('_lwaResult');
    if (!msg) { el.style.display = 'none'; return; }
    el.style.display = 'block';
    el.style.background = ok === true ? '#f0fdf4' : ok === null ? '#f0f9ff' : '#fef2f2';
    el.style.color      = ok === true ? '#166534' : ok === null ? '#0369a1' : '#991b1b';
    el.textContent = msg;
  }

  function _applyModeStyle() {
    var isComp = _s.mode === 'company';
    var btnComp = document.getElementById('_lwaBtnComp');
    var btnDir  = document.getElementById('_lwaBtnDir');
    [btnComp, btnDir].forEach(function(b) {
      b.style.background  = 'none';
      b.style.boxShadow   = 'none';
      b.style.color       = '#6b7280';
    });
    var active = isComp ? btnComp : btnDir;
    active.style.background = '#fff';
    active.style.boxShadow  = '0 1px 4px rgba(0,0,0,.12)';
    active.style.color      = '#065f46';
    document.getElementById('_lwaTplLbl').textContent = isComp
      ? 'Template (Meta-approved only)'
      : 'Template (optional — any active)';
    document.getElementById('_lwaSendLbl').textContent = isComp ? 'Send via Meta' : 'Open WhatsApp';
    document.getElementById('_lwaSend').style.background = isComp ? '#25D366' : '#0d9488';
  }

  /* ── Load templates ───────────────────────────────────────────────────────── */
  function _loadTpls() {
    var seg = (document.getElementById('_lwaSeg') || {}).value || '';
    var cat = (document.getElementById('_lwaCat') || {}).value || '';
    var sel = document.getElementById('_lwaTpl');
    sel.innerHTML = '<option value="">— Loading… —</option>';
    var url;
    if (_s.mode === 'company') {
      url = API + '/templates/approved?';
      if (seg) url += 'segment=' + encodeURIComponent(seg) + '&';
      if (cat) url += 'category=' + encodeURIComponent(cat);
    } else {
      url = API + '/templates?is_active=true';
      if (seg) url += '&segment=' + encodeURIComponent(seg);
    }
    return fetch(url, { credentials: 'include' })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        _s.tpls = d.templates || [];
        sel.innerHTML = '<option value="">— Write custom message —</option>';
        var noTpl = document.getElementById('_lwaNoTpl');
        if (_s.mode === 'company' && _s.tpls.length === 0) {
          noTpl.style.display = 'block';
        } else {
          noTpl.style.display = 'none';
        }
        var bySegment = {};
        _s.tpls.forEach(function(t) {
          if (!bySegment[t.segment]) bySegment[t.segment] = [];
          bySegment[t.segment].push(t);
        });
        var segLabels = { ev_b2b:'EV B2B', ev_b2c:'EV B2C', etc_training:'ETC Training', real_estate:'Real Estate', general:'MNR General', system:'System', vgk:'VGK Members', solar:'Solar', myntreal_real:'Myntreal Real' };
        Object.keys(bySegment).forEach(function(sg) {
          var grp = document.createElement('optgroup');
          grp.label = segLabels[sg] || sg;
          bySegment[sg].forEach(function(t) {
            var opt = document.createElement('option');
            opt.value = t.id;
            opt.textContent = t.name + (t.meta_category ? ' (' + t.meta_category + ')' : '');
            opt.dataset.body     = t.body_text || '';
            opt.dataset.examples = JSON.stringify(t.example_values || []);
            grp.appendChild(opt);
          });
          sel.appendChild(grp);
        });
        /* auto-select if exactly one */
        if (_s.tpls.length === 1) { sel.value = String(_s.tpls[0].id); _onTplChange(); }
      })
      .catch(function(e) {
        sel.innerHTML = '<option value="">— Failed to load —</option>';
        console.error('[lwa] template load error', e);
      });
  }

  /* ── Template change ─────────────────────────────────────────────────────── */
  function _onTplChange() {
    var sel  = document.getElementById('_lwaTpl');
    var opt  = sel.options[sel.selectedIndex];
    var vars = document.getElementById('_lwaVars');
    var box  = document.getElementById('_lwaVarBox');
    if (!opt || !opt.value) {
      vars.style.display = 'none';
      box.innerHTML = '';
      document.getElementById('_lwaMsg').value = '';
      _s.bodyTpl = '';
      return;
    }
    _s.bodyTpl = opt.dataset.body || '';
    var examples = [];
    try { examples = JSON.parse(opt.dataset.examples || '[]'); } catch(e) {}
    /* detect {{n}} placeholders, deduplicated, in order */
    var seen = {};
    var keys = [];
    (_s.bodyTpl.match(/\{\{(\w+)\}\}/g) || []).forEach(function(m) {
      var k = m.replace(/[{}]/g, '');
      if (!seen[k]) { seen[k] = true; keys.push(k); }
    });
    if (keys.length > 0) {
      vars.style.display = 'block';
      box.innerHTML = keys.map(function(v, i) {
        var ex      = examples[i] != null ? examples[i] : '';
        var prefill = (v === '1') ? (_s.name || ex) : ex;
        return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:7px">'
          + '<span style="font-size:11px;font-weight:700;color:#374151;white-space:nowrap;min-width:36px">{{' + v + '}}</span>'
          + '<input id="_lwaV_' + _esc(v) + '" type="text" value="' + _esc(prefill) + '" placeholder="' + (_esc(ex) || 'Value for {{' + v + '}}') + '" oninput="window._lwaPreview()" style="flex:1;font-size:12px;border:1px solid #e5e7eb;border-radius:6px;padding:5px 8px;box-sizing:border-box">'
          + '</div>';
      }).join('');
    } else {
      vars.style.display = 'none';
      box.innerHTML = '';
    }
    _buildPreview();
  }

  /* ── Live preview ────────────────────────────────────────────────────────── */
  function _buildPreview() {
    if (!_s.bodyTpl) return;
    var preview = _s.bodyTpl;
    var inputs  = document.getElementById('_lwaVarBox').querySelectorAll('input');
    inputs.forEach(function(inp) {
      var k = inp.id.replace('_lwaV_', '');
      var re = new RegExp('\\{\\{' + k + '\\}\\}', 'g');
      preview = preview.replace(re, inp.value || ('{{' + k + '}}'));
    });
    document.getElementById('_lwaMsg').value = preview;
  }

  /* ── Collect variable_values from inputs ─────────────────────────────────── */
  function _collectVars() {
    var out = {};
    document.getElementById('_lwaVarBox').querySelectorAll('input').forEach(function(inp) {
      out[inp.id.replace('_lwaV_', '')] = inp.value;
    });
    return out;
  }

  /* ── Send ────────────────────────────────────────────────────────────────── */
  function _doSend() {
    var msg    = (document.getElementById('_lwaMsg').value || '').trim();
    var tplId  = document.getElementById('_lwaTpl').value;
    var btn    = document.getElementById('_lwaSend');
    var varVals = _collectVars();

    if (!msg) { _showRes('Please enter a message or select a template.', false); return; }

    if (_s.mode === 'direct') {
      var cleaned = (_s.phone || '').replace(/\D/g, '').slice(-10);
      var waUrl   = cleaned
        ? 'https://wa.me/91' + cleaned + '?text=' + encodeURIComponent(msg)
        : 'https://wa.me/?text=' + encodeURIComponent(msg);
      window.open(waUrl, '_blank');
      _showRes('WhatsApp opened — logging action…', null);
      fetch(API + '/crm-lead-send/' + _s.leadId + '/log-direct', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: _s.phone, message_preview: msg.slice(0, 200), message_body: msg, template_id: tplId ? parseInt(tplId, 10) : null })
      }).catch(function(e) { console.warn('[lwa] log-direct non-fatal', e); });
      _showRes('✅ WhatsApp opened. Activity logged to lead.', true);
      setTimeout(function() { document.getElementById('_lwaModal').style.display = 'none'; }, 2500);
      return;
    }

    /* Company send */
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending…';
    _showRes('', null);
    fetch(API + '/crm-lead-send/' + _s.leadId, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        phone: _s.phone,
        template_id: tplId ? parseInt(tplId, 10) : null,
        custom_message: !tplId ? msg : null,
        variable_values: varVals,
        send_mode: 'company'
      })
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.success) {
        btn.innerHTML = '<i class="fas fa-check"></i> Sent ✓';
        _showRes('✅ Sent via Meta. WAMID: ' + (d.wamid || 'N/A') + ' — delivery status updates in ~6 s.', true);
        setTimeout(function() { document.getElementById('_lwaModal').style.display = 'none'; }, 3000);
      } else {
        var reason = d.reason || 'Unknown error';
        _showRes('❌ ' + reason, false);
        btn.disabled = false;
        btn.innerHTML = '<i class="fab fa-whatsapp"></i> <span id="_lwaSendLbl">Send via Meta</span>';
      }
    })
    .catch(function(e) {
      _showRes('Network error: ' + e.message, false);
      btn.disabled = false;
      btn.innerHTML = '<i class="fab fa-whatsapp"></i> <span id="_lwaSendLbl">Send via Meta</span>';
    });
  }

  /* ── Expose window functions (called from inline HTML) ───────────────────── */
  function _bindGlobals() {
    window._lwaClose     = function() { document.getElementById('_lwaModal').style.display = 'none'; };
    window._lwaMode      = function(m) { _s.mode = m; _applyModeStyle(); _loadTpls(); };
    window._lwaLoadTpls  = function() { _loadTpls(); };
    window._lwaTplChange = function() { _onTplChange(); };
    window._lwaPreview   = function() { _buildPreview(); };
    window._lwaDoSend    = function() { _doSend(); };
  }

  /* ── Public entry point ──────────────────────────────────────────────────── */
  window.openLeadWAModal = function(leadId, phone, name, companyId) {
    _ensure();
    _bindGlobals();
    _s = { leadId: leadId, phone: phone, name: name, companyId: companyId, mode: 'company', tpls: [], bodyTpl: '' };

    /* reset UI */
    document.getElementById('_lwaSub').textContent     = (name || '') + ' · ' + (phone || '');
    document.getElementById('_lwaSeg').value           = '';
    document.getElementById('_lwaCat').value           = '';
    document.getElementById('_lwaMsg').value           = '';
    document.getElementById('_lwaVars').style.display  = 'none';
    document.getElementById('_lwaVarBox').innerHTML    = '';
    document.getElementById('_lwaNoTpl').style.display = 'none';
    document.getElementById('_lwaResult').style.display= 'none';
    document.getElementById('_lwaSend').disabled       = false;
    document.getElementById('_lwaSend').innerHTML      = '<i class="fab fa-whatsapp"></i> <span id="_lwaSendLbl">Send via Meta</span>';
    _applyModeStyle();

    document.getElementById('_lwaModal').style.display = 'flex';
    _loadTpls();
  };

})();
