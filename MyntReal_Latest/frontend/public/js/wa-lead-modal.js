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
    '<div id="_lwaModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:1000000;align-items:center;justify-content:center;padding:16px;box-sizing:border-box">',
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
    '<div style="display:flex;gap:8px;margin-bottom:16px;background:#f3f4f6;border-radius:10px;padding:4px">',
    '<button id="_lwaBtnScanned" onclick="window._lwaMode(\'scanned\')" style="flex:1;padding:8px 6px;border:none;border-radius:7px;font-size:12px;font-weight:700;cursor:pointer;transition:all .15s"><i class="fas fa-qrcode text-success"></i> 📱 Scanned WhatsApp<small style="display:block;font-weight:400;font-size:10px;margin-top:1px">Employee Account · Scanned</small></button>',
    '<button id="_lwaBtnComp"    onclick="window._lwaMode(\'company\')" style="flex:1;padding:8px 6px;border:none;border-radius:7px;font-size:12px;font-weight:700;cursor:pointer;transition:all .15s"><i class="fas fa-building text-primary"></i> 🏢 Official WhatsApp<small style="display:block;font-weight:400;font-size:10px;margin-top:1px">Meta Cloud API · Verified</small></button>',
    '</div>',

    /* 1-tap quick responses */
    '<div style="font-size:10.5px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px">⚡ 1-Tap Quick Responses</div>',
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:14px">',
    '<button type="button" onclick="window._lwaApplyQuick(\'thanks_connecting\')" style="background:#ecfdf5;border:1.5px solid #a7f3d0;color:#065f46;border-radius:9px;padding:8px 10px;font-size:12px;font-weight:700;cursor:pointer;text-align:left;display:flex;align-items:center;gap:6px"><span style="font-size:16px">🙏</span><div><div>Thanks for Connecting</div><small style="font-size:9.5px;font-weight:400;opacity:.8">Service tailored</small></div></button>',
    '<button type="button" onclick="window._lwaApplyQuick(\'trying_to_reach\')" style="background:#fef3c7;border:1.5px solid #fde68a;color:#92400e;border-radius:9px;padding:8px 10px;font-size:12px;font-weight:700;cursor:pointer;text-align:left;display:flex;align-items:center;gap:6px"><span style="font-size:16px">📞</span><div><div>Trying to Reach</div><small style="font-size:9.5px;font-weight:400;opacity:.8">Call missed / inquiry</small></div></button>',
    '</div>',

    /* filters */
    '<div style="font-size:10.5px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px">Official Template Filters</div>',
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

    /* recipient phone */
    '<div style="margin-bottom:12px">',
    '<label style="font-size:10.5px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;display:block;margin-bottom:4px">Recipient Mobile Number</label>',
    '<input type="tel" id="_lwaPhoneInp" style="width:100%;font-size:13px;border:1px solid #e5e7eb;border-radius:7px;padding:7px 10px;box-sizing:border-box" placeholder="10-digit mobile number">',
    '</div>',

    /* message */
    '<div style="margin-bottom:12px">',
    '<label style="font-size:10.5px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;display:block;margin-bottom:4px">Message <small style="text-transform:none;font-weight:400">(auto-filled from template, or write custom)</small></label>',
    '<textarea id="_lwaMsg" rows="6" style="width:100%;font-size:13px;font-family:\'Segoe UI\',system-ui,-apple-system,sans-serif;line-height:1.55;border:1px solid #e5e7eb;border-radius:7px;padding:10px;resize:vertical;box-sizing:border-box;white-space:pre-wrap" placeholder="Select a template above or type your message…"></textarea>',
    '</div>',

    /* result */
    '<div id="_lwaResult" style="display:none;padding:9px 12px;border-radius:8px;font-size:12px;margin-bottom:12px"></div>',

    /* buttons */
    '<div style="display:flex;gap:8px;justify-content:space-between;align-items:center;flex-wrap:wrap">',
    '<div style="display:flex;gap:6px">',
    '<button type="button" onclick="window._lwaDirectWeb()" style="padding:8px 12px;background:#e0f2fe;color:#0369a1;border:1px solid #bae6fd;border-radius:8px;font-size:12px;font-weight:700;cursor:pointer" title="Open direct chat in WhatsApp Web"><i class="fab fa-whatsapp me-1"></i>Direct Web</button>',
    '<button type="button" onclick="window._lwaCopyText()" style="padding:8px 12px;background:#f3f4f6;color:#374151;border:1px solid #e5e7eb;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer" title="Copy message to clipboard"><i class="fas fa-copy me-1"></i>Copy</button>',
    '</div>',
    '<div style="display:flex;gap:8px">',
    '<button onclick="window._lwaClose()" style="padding:8px 16px;border:1.5px solid #e5e7eb;border-radius:8px;background:#fff;color:#374151;font-size:12px;cursor:pointer">Cancel</button>',
    '<button id="_lwaSend" onclick="window._lwaDoSend()" style="padding:8px 20px;background:#25D366;color:#fff;border:none;border-radius:8px;font-size:12px;font-weight:700;cursor:pointer;min-width:140px"><i class="fab fa-whatsapp"></i> <span id="_lwaSendLbl">Send via 📱 Scanned WhatsApp</span></button>',
    '</div>',
    '</div>',

    '</div></div></div>'
  ].join('');

  /* ── State ───────────────────────────────────────────────────────────────── */
  var _s = { leadId: null, phone: null, name: null, companyId: null, mode: 'scanned', tpls: [], bodyTpl: '' };

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
    if (!el) return;
    if (!msg) { el.style.display = 'none'; return; }
    el.style.display    = 'block';
    el.style.background = ok === true ? '#ecfdf5' : ok === false ? '#fef2f2' : '#f0f9ff';
    el.style.color      = ok === true ? '#065f46' : ok === false ? '#991b1b' : '#0369a1';
    el.style.border     = '1px solid ' + (ok === true ? '#a7f3d0' : ok === false ? '#fecaca' : '#bae6fd');
    el.innerHTML        = msg;
  }

  function _applyModeStyle() {
    var isScanned = _s.mode === 'scanned';
    var bScan = document.getElementById('_lwaBtnScanned');
    var bComp = document.getElementById('_lwaBtnComp');
    if (bScan && bComp) {
      bScan.style.background = isScanned ? '#fff' : 'transparent';
      bScan.style.color      = isScanned ? '#128c7e' : '#6b7280';
      bScan.style.boxShadow  = isScanned ? '0 1px 4px rgba(0,0,0,.1)' : 'none';

      bComp.style.background = !isScanned ? '#fff' : 'transparent';
      bComp.style.color      = !isScanned ? '#2563eb' : '#6b7280';
      bComp.style.boxShadow  = !isScanned ? '0 1px 4px rgba(0,0,0,.1)' : 'none';
    }

    var lbl = document.getElementById('_lwaSendLbl');
    if (lbl) lbl.textContent = isScanned ? 'Send via 📱 Scanned WhatsApp' : 'Send via 🏢 Official WhatsApp';

    var sendBtn = document.getElementById('_lwaSend');
    if (sendBtn) {
      sendBtn.style.background = isScanned ? '#128c7e' : '#2563eb';
    }

    var tplLbl = document.getElementById('_lwaTplLbl');
    if (tplLbl) {
      tplLbl.textContent = isScanned ? 'Template (Scanned Session Approved)' : 'Template (Meta Cloud Approved)';
    }
  }

  /* ── Load templates ──────────────────────────────────────────────────────── */
  function _loadTpls() {
    var seg = document.getElementById('_lwaSeg') ? document.getElementById('_lwaSeg').value : '';
    var cat = document.getElementById('_lwaCat') ? document.getElementById('_lwaCat').value : '';
    var sel = document.getElementById('_lwaTpl');
    if (!sel) return;

    sel.innerHTML = '<option value="">— Loading templates… —</option>';
    document.getElementById('_lwaNoTpl').style.display = 'none';

    var url = API + '/templates?mode=' + encodeURIComponent(_s.mode);
    if (seg) url += '&segment=' + encodeURIComponent(seg);
    if (cat) url += '&category=' + encodeURIComponent(cat);
    if (_s.companyId) url += '&company_id=' + encodeURIComponent(_s.companyId);

    fetch(url, { credentials: 'include' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var list = (d.templates || d.data || d || []);
        _s.tpls = Array.isArray(list) ? list : [];

        if (!_s.tpls.length) {
          sel.innerHTML = '<option value="">— No approved templates found —</option>';
          document.getElementById('_lwaNoTpl').style.display = 'block';
          return;
        }

        var optHtml = '<option value="">— Select a template (' + _s.tpls.length + ' available) —</option>';
        _s.tpls.forEach(function (t) {
          optHtml += '<option value="' + t.id + '">' + _esc(t.template_name || t.name) + ' (' + (t.category || 'MARKETING') + ')</option>';
        });
        sel.innerHTML = optHtml;
      })
      .catch(function () {
        sel.innerHTML = '<option value="">— Error loading templates —</option>';
      });
  }

  /* ── Template change handler ─────────────────────────────────────────────── */
  function _onTplChange() {
    var tplId = document.getElementById('_lwaTpl').value;
    var varBox = document.getElementById('_lwaVarBox');
    var varWrap = document.getElementById('_lwaVars');
    var msgBox = document.getElementById('_lwaMsg');

    if (!tplId) {
      varWrap.style.display = 'none';
      varBox.innerHTML = '';
      return;
    }

    var tpl = _s.tpls.find(function (t) { return String(t.id) === String(tplId); });
    if (!tpl) return;

    _s.bodyTpl = tpl.body_text || tpl.content || tpl.body || '';

    /* Parse {{1}}, {{2}}, etc. */
    var matches = _s.bodyTpl.match(/\{\{(\d+)\}\}/g) || [];
    var uniqueIndices = [];
    matches.forEach(function (m) {
      var idx = m.replace(/[\{\}]/g, '');
      if (uniqueIndices.indexOf(idx) === -1) uniqueIndices.push(idx);
    });
    uniqueIndices.sort(function (a, b) { return Number(a) - Number(b); });

    if (uniqueIndices.length) {
      var html = '';
      uniqueIndices.forEach(function (idx) {
        var defaultVal = (idx === '1') ? (_s.name || '') : '';
        html += '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">' +
          '<label style="font-size:11px;font-weight:600;width:30px">#' + idx + '</label>' +
          '<input type="text" id="_lwaVar_' + idx + '" value="' + _esc(defaultVal) + '" oninput="window._lwaPreview()" ' +
          'style="flex:1;font-size:12px;border:1px solid #e5e7eb;border-radius:6px;padding:5px 8px" placeholder="Value for {{' + idx + '}}">' +
          '</div>';
      });
      varBox.innerHTML = html;
      varWrap.style.display = 'block';
    } else {
      varWrap.style.display = 'none';
      varBox.innerHTML = '';
    }

    _buildPreview();
  }

  function _buildPreview() {
    var text = _s.bodyTpl || '';
    var matches = text.match(/\{\{(\d+)\}\}/g) || [];
    matches.forEach(function (m) {
      var idx = m.replace(/[\{\}]/g, '');
      var inp = document.getElementById('_lwaVar_' + idx);
      var val = inp ? (inp.value || m) : m;
      text = text.split(m).join(val);
    });
    if (document.getElementById('_lwaMsg')) {
      document.getElementById('_lwaMsg').value = text;
    }
  }

  /* ── Send dispatch ───────────────────────────────────────────────────────── */
  function _doSend() {
    var phoneInput = document.getElementById('_lwaPhoneInp');
    var targetPhone = (phoneInput ? phoneInput.value : '') || _s.phone || '';
    var targetNum = targetPhone.replace(/\D/g, '').slice(-10);

    if (!targetNum || targetNum.length < 10) {
      _showRes('Please provide a valid 10-digit recipient phone number.', false);
      return;
    }

    var tplId = document.getElementById('_lwaTpl') ? document.getElementById('_lwaTpl').value : null;
    var msg   = document.getElementById('_lwaMsg') ? document.getElementById('_lwaMsg').value.trim() : '';

    if (!msg && !tplId) {
      _showRes('Please enter a message or select a template.', false);
      return;
    }

    var varVals = {};
    var inputs = document.querySelectorAll('[id^="_lwaVar_"]');
    inputs.forEach(function (inp) {
      var k = inp.id.replace('_lwaVar_', '');
      varVals[k] = inp.value;
    });

    var btn = document.getElementById('_lwaSend');
    btn.disabled = true;

    function _getAuthToken() {
      try {
        return localStorage.getItem('token') || localStorage.getItem('staff_token') || '';
      } catch(e) { return ''; }
    }

    var token = _getAuthToken();
    var authHeaders = { 'Content-Type': 'application/json' };
    if (token) {
      authHeaders['Authorization'] = 'Bearer ' + token;
    }

    /* Scanned mode send */
    if (_s.mode === 'scanned') {
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending via Bot…';
      _showRes('', null);
      fetch('/api/v1/whatsapp/send-message', {
        method: 'POST', credentials: 'include',
        headers: authHeaders,
        body: JSON.stringify({
          recipient: targetNum,
          message: msg,
          recipient_type: 'individual',
          recipient_name: _s.name || 'Contact',
          template_id: tplId ? parseInt(tplId, 10) : null,
          variable_values: varVals,
          client_msg_id: 'lwa_modal_' + Date.now()
        })
      })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.success || d.status === 'sent') {
          btn.innerHTML = '<i class="fas fa-check"></i> Sent via Bot ✓';
          _showRes('✅ Sent via 📱 Scanned WhatsApp! (Dispatched & Tracked)', true);
          if (_s.leadId && _s.leadId !== 'new' && !isNaN(parseInt(_s.leadId, 10))) {
            fetch(API + '/crm-lead-send/' + _s.leadId + '/log-direct', {
              method: 'POST', credentials: 'include',
              headers: authHeaders,
              body: JSON.stringify({ phone: targetNum, message_preview: msg.slice(0, 200), message_body: msg, template_id: tplId ? parseInt(tplId, 10) : null })
            }).catch(function(e) { console.warn('[lwa] log-scanned non-fatal', e); });
          }
          setTimeout(function() { document.getElementById('_lwaModal').style.display = 'none'; }, 2500);
        } else {
          var errDetail = d.detail || d.message || d.error || d.reason || 'Gateway dispatch failed';
          _showRes('❌ ' + errDetail, false);
          btn.disabled = false;
          btn.innerHTML = '<i class="fas fa-qrcode"></i> <span id="_lwaSendLbl">Send via Scanned Bot</span>';
        }
      })
      .catch(function(e) {
        _showRes('Network error: ' + e.message, false);
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-qrcode"></i> <span id="_lwaSendLbl">Send via Scanned Bot</span>';
      });
      return;
    }

    /* Company mode send */
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending via Meta…';
    _showRes('', null);

    var isNumericLead = _s.leadId && !isNaN(parseInt(_s.leadId, 10)) && parseInt(_s.leadId, 10) > 0;
    var sendUrl = isNumericLead ? (API + '/crm-lead-send/' + _s.leadId) : (API + '/test-send');
    var sendPayload = isNumericLead ? {
      phone: targetNum,
      template_id: tplId ? parseInt(tplId, 10) : null,
      custom_message: !tplId ? msg : null,
      variable_values: varVals,
      send_mode: 'company'
    } : {
      phone: targetNum,
      company_id: _s.companyId || 4,
      template_id: tplId ? parseInt(tplId, 10) : null,
      custom_message: msg
    };

    fetch(sendUrl, {
      method: 'POST', credentials: 'include',
      headers: authHeaders,
      body: JSON.stringify(sendPayload)
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.success) {
        btn.innerHTML = '<i class="fas fa-check"></i> Sent ✓';
        _showRes('✅ Sent via 🏢 Official WhatsApp! WAMID: ' + (d.wamid || 'N/A') + ' (Dispatched & Tracked)', true);
        setTimeout(function() { document.getElementById('_lwaModal').style.display = 'none'; }, 3000);
      } else {
        var reason = d.reason || d.detail || d.error || 'Meta dispatch failed';
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

  function _getStaffSignature() {
    try {
      var raw = localStorage.getItem('mnr_auth_state') || localStorage.getItem('staff_user') || localStorage.getItem('user');
      if (raw) {
        var parsed = JSON.parse(raw);
        var u = parsed.user || parsed.employee || parsed;
        var name = u.full_name || u.name || (u.first_name ? u.first_name + ' ' + (u.last_name || '') : '') || 'Staff';
        var ext = u.extension || u.ext || (typeof window !== 'undefined' ? window.__STAFF_EXTENSION__ : null);
        if (ext && String(ext).trim() && !['none', 'null', 'undefined', 'n/a'].includes(String(ext).trim().toLowerCase())) {
          return '\n\nRegards,\n' + name + '\n📞 +91 85858 52738 | +91 8897797667\nExt: ' + String(ext).trim();
        }
        return '\n\nRegards,\n' + name + '\n📞 +91 85858 52738 | +91 8897797667';
      }
    } catch (e) {}
    return '\n\nRegards,\nStaff\n📞 +91 85858 52738 | +91 8897797667';
  }

  function _getVerticalQuickMessage(action, customerName, context) {
    var cName = (customerName || 'Customer').trim();
    var ctx = (context || '').toLowerCase();
    var vertical = 'general';
    if (ctx.indexOf('solar') !== -1) vertical = 'solar';
    else if (ctx.indexOf('real') !== -1 || ctx.indexOf('property') !== -1 || ctx.indexOf('estate') !== -1) vertical = 'real_estate';
    else if (ctx.indexOf('insur') !== -1 || ctx.indexOf('care') !== -1) vertical = 'insurance';
    else if (ctx.indexOf('ev') !== -1 || ctx.indexOf('spare') !== -1 || ctx.indexOf('zynova') !== -1 || ctx.indexOf('vehicle') !== -1) vertical = 'ev';
    else if (ctx.indexOf('etc') !== -1 || ctx.indexOf('train') !== -1 || ctx.indexOf('skill') !== -1) vertical = 'etc';

    if (action === 'thanks_connecting') {
      switch (vertical) {
        case 'solar':
          return 'నమస్కారం ' + cName + ' గారు! 🙏 MyntReal Solar Rooftop గురించి మాతో మాట్లాడినందుకు ధన్యవాదాలు. మీ ఇంటి లేదా కమర్షియల్ కరెంట్ బిల్లును 90% వరకు తగ్గించుకుంటూ, Government Subsidy పొందే పూర్తి వివరాలు & Customized Solar Quotation త్వరలోనే మా సోలార్ ఎక్స్‌పర్ట్ మీకు షేర్ చేస్తారు. ఏవైనా డౌట్స్ ఉంటే దయచేసి ఇక్కడ మెసేజ్ చేయండి.';
        case 'real_estate':
          return 'నమస్కారం ' + cName + ' గారు! 🙏 MyntReal Properties తో కనెక్ట్ అయినందుకు ధన్యవాదాలు. మీ బడ్జెట్ మరియు రిక్వైర్‌మెంట్‌కు తగినట్లుగా బెస్ట్ వెరిఫైడ్ ఓపెన్ ప్లాట్స్, గేటెడ్ కమ్యూనిటీ విల్లాస్ మరియు అపార్ట్‌మెంట్స్ వివరాలను మా ప్రాపర్టీ స్పెషలిస్ట్ త్వరలోనే మీకు షేర్ చేస్తారు. సైట్ విజిట్ కోసం ఎప్పుడైనా సంప్రదించవచ్చు.';
        case 'insurance':
          return 'నమస్కారం ' + cName + ' గారు! 🙏 MyntReal Insurance & Protection తో మాట్లాడినందుకు ధన్యవాదాలు. మీకు మరియు మీ కుటుంబానికి సరిపోయే బెస్ట్ Health, Life మరియు General Insurance పాలసీ కొటేషన్లను మా ఇన్సూరెన్స్ అడ్వైజర్ మీకు పంపిస్తారు. పూర్తి క్లెయిమ్ సపోర్ట్ మా బాధ్యత.';
        case 'ev':
          return 'నమస్కారం ' + cName + ' గారు! 🙏 MyntReal EV & Spares గురించి మాతో కనెక్ట్ అయినందుకు ధన్యవాదాలు. లేటెస్ట్ ఎలక్ట్రిక్ వెహికల్ మోడల్స్, రేంజ్, బ్యాటరీ వారంటీ, ఫైనాన్స్ ఆప్షన్స్ మరియు టెస్ట్ రైడ్ వివరాలను మా ఈవీ స్పెషలిస్ట్ మీకు త్వరలోనే అందిస్తారు.';
        case 'etc':
          return 'నమస్కారం ' + cName + ' గారు! 🙏 MyntReal ETC Skill Training ప్రోగ్రామ్స్ గురించి మాట్లాడినందుకు ధన్యవాదాలు. మీ కెరీర్ గ్రోత్‌కు అవసరమైన సర్టిఫైడ్ ట్రైనింగ్ కోర్సులు, బ్యాచ్ టైమింగ్స్ మరియు జాబ్ అసిస్టెన్స్ వివరాలు మా కోఆర్డినేటర్ మీకు పంపిస్తారు.';
        default:
          return 'నమస్కారం ' + cName + ' గారు! 🙏 MyntReal తో కనెక్ట్ అయినందుకు చాలా ధన్యవాదాలు. మా అన్ని ప్రీమియర్ సర్వీసెస్ మీ సేవలో అందుబాటులో ఉన్నాయి:\n☀️ Solar Rooftop & Renewable Energy (కరెంట్ బిల్లు 90% వరకు ఆదా & Govt సబ్సిడీ)\n🏡 Real Estate & Premier Properties (ఓపెన్ ప్లాట్స్, విల్లాస్ & అపార్ట్‌మెంట్స్)\n🛡️ Insurance & Protection Solutions (హెల్త్, లైఫ్ & జనరల్ పాలసీలు)\n🛵 EV Vehicles & Genuine Spares (ఎకో-ఫ్రెండ్లీ ఎలక్ట్రిక్ బైక్స్ & సర్వీస్)\n🎓 ETC Skill Training & Career Certifications (ఉద్యోగ నైపుణ్య శిక్షణ)\n\nమా Relationship Manager మీకు పూర్తి వివరాలు అందిస్తారు. మీకు ఏ సమాచారం కావాలన్నా దయచేసి ఇక్కడ మెసేజ్ చేయగలరు!';
      }
    } else {
      switch (vertical) {
        case 'solar':
          return 'నమస్కారం ' + cName + ' గారు! 📞 మీ Solar Rooftop ఎంక్వైరీ కోసం MyntReal నుండి ఇప్పుడే కాల్ చేశాము, కానీ కాల్ కలవలేదు. మీరు ఫ్రీగా ఉన్నప్పుడు దయచేసి ఈ మెసేజ్‌కి రిప్లై ఇవ్వండి లేదా కాల్ బ్యాక్ చేయండి. సోలార్ సబ్సిడీ మరియు సేవింగ్స్ వివరాలు తెలియజేస్తాము.';
        case 'real_estate':
          return 'నమస్కారం ' + cName + ' గారు! 📞 మీ Real Estate ప్రాపర్టీ ఎంక్వైరీ గురించి MyntReal నుండి కాల్ చేశాము, మాట్లాడటం కుదరలేదు. మీకు అనుకూలమైన టైమ్‌లో దయచేసి రిప్లై ఇవ్వండి లేదా కాల్ చేయండి. మీ రిక్వైర్‌మెంట్‌కు సరిపడే బెస్ట్ ప్రాపర్టీ ఆప్షన్స్ మీకు పంపిస్తాము.';
        case 'insurance':
          return 'నమస్కారం ' + cName + ' గారు! 📞 మీ Insurance ఎంక్వైరీ గురించి MyntReal నుండి కాల్ చేశాము, కాల్ కలవలేదు. మీకు ఫ్రీ టైమ్ ఉన్నప్పుడు దయచేసి ఇక్కడ రిప్లై ఇవ్వండి. మీకు అనువైన బెస్ట్ ఇన్సూరెన్స్ ప్లాన్స్ వివరాలు చర్చిద్దాం.';
        case 'ev':
          return 'నమస్కారం ' + cName + ' గారు! 📞 మీ EV Vehicle & Spares ఎంక్వైరీ కోసం MyntReal నుండి కాల్ చేశాము, మాట్లాడటం వీలుపడలేదు. మీరు వీలైనప్పుడు రిప్లై ఇవ్వండి లేదా కాల్ చేయండి. టెస్ట్ రైడ్ మరియు మోడల్స్ వివరాలు మీకు తెలియజేస్తాము.';
        case 'etc':
          return 'నమస్కారం ' + cName + ' గారు! 📞 మీ ETC Skill Training కోర్సు వివరాల కోసం MyntReal నుండి కాల్ చేశాము, కాల్ కనెక్ట్ అవ్వలేదు. మీరు ఫ్రీగా ఉన్నప్పుడు దయచేసి మెసేజ్ చేయండి. అప్‌కమింగ్ బ్యాచ్ టైమింగ్స్ మరియు ఫీజు వివరాలు చర్చిద్దాం.';
        default:
          return 'నమస్కారం ' + cName + ' గారు! 📞 MyntReal నుండి మీతో మాట్లాడటానికి ఇప్పుడే కాల్ చేశాము, కానీ కాల్ కలవలేదు / మీరు బిజీగా ఉన్నట్లున్నారు. మేము మీకు క్రింది సర్వీసెస్‌లో ఉత్తమ సేవలు అందిస్తున్నాము:\n☀️ Solar Energy (సోలార్ రూఫ్‌టాప్ & సబ్సిడీ)\n🏡 Real Estate (వెరిఫైడ్ ప్రాపర్టీస్ & సైట్ విజిట్స్)\n🛡️ Insurance (హెల్త్ & లైఫ్ ఇన్సూరెన్స్)\n🛵 EV Vehicles & Spares (ఎలక్ట్రిక్ స్కూటర్లు & స్పేర్స్)\n🎓 ETC Skill Training (నైపుణ్య శిక్షణ & కెరీర్)\n\nమీకు అనుకూలమైన సమయంలో దయచేసి ఇక్కడ మెసేజ్ చేయండి లేదా కాల్ బ్యాక్ చేయగలరు!';
      }
    }
  }

  function _applyQuick(action) {
    var msg = _getVerticalQuickMessage(action, _s.name, _s.context || '');
    var sig = _getStaffSignature();
    var msgBox = document.getElementById('_lwaMsg');
    if (msgBox) {
      msgBox.value = msg + sig;
      msgBox.focus();
    }
  }

  /* ── Direct Web WhatsApp & Copy Actions ─────────────────────────────────── */
  function _directWeb() {
    var phoneInput = document.getElementById('_lwaPhoneInp');
    var targetPhone = (phoneInput ? phoneInput.value : '') || _s.phone || '';
    var cleanP = targetPhone.replace(/\D/g, '').slice(-10);
    var msg = document.getElementById('_lwaMsg') ? document.getElementById('_lwaMsg').value : '';
    var url = cleanP ? ('https://wa.me/91' + cleanP + '?text=' + encodeURIComponent(msg)) : ('https://wa.me/?text=' + encodeURIComponent(msg));
    window.open(url, '_blank');
  }

  function _copyText() {
    var msg = document.getElementById('_lwaMsg') ? document.getElementById('_lwaMsg').value : '';
    if (!msg) return;
    navigator.clipboard.writeText(msg).then(function() {
      _showRes('📋 Message copied to clipboard!', true);
    }).catch(function() {
      var inp = document.getElementById('_lwaMsg');
      if (inp) { inp.select(); document.execCommand('copy'); _showRes('📋 Message copied to clipboard!', true); }
    });
  }

  /* ── Expose window functions (called from inline HTML) ───────────────────── */
  function _bindGlobals() {
    window._lwaClose      = function() { document.getElementById('_lwaModal').style.display = 'none'; };
    window._lwaMode       = function(m) { _s.mode = m; _applyModeStyle(); _loadTpls(); };
    window._lwaLoadTpls   = function() { _loadTpls(); };
    window._lwaTplChange  = function() { _onTplChange(); };
    window._lwaPreview    = function() { _buildPreview(); };
    window._lwaDoSend     = function() { _doSend(); };
    window._lwaDirectWeb  = function() { _directWeb(); };
    window._lwaCopyText   = function() { _copyText(); };
    window._lwaApplyQuick = function(a) { _applyQuick(a); };
  }

  /* ── Public entry point ──────────────────────────────────────────────────── */
  window.openLeadWAModal = function(leadId, phone, name, companyId, initialMessage, context) {
    _ensure();
    _bindGlobals();
    var cleanP = phone ? String(phone).replace(/\D/g, '').slice(-10) : '';
    _s = { leadId: leadId, phone: cleanP, name: name, companyId: companyId, mode: 'scanned', tpls: [], bodyTpl: '', context: context || '' };

    /* reset UI */
    document.getElementById('_lwaSub').textContent     = (name || 'Contact') + (cleanP ? (' · ' + cleanP) : '');
    if (document.getElementById('_lwaPhoneInp')) {
      document.getElementById('_lwaPhoneInp').value = cleanP;
    }
    document.getElementById('_lwaSeg').value           = '';
    document.getElementById('_lwaCat').value           = '';
    
    if (initialMessage) {
      document.getElementById('_lwaMsg').value = initialMessage;
    } else {
      document.getElementById('_lwaMsg').value = 'Namaskaram ' + (name || 'Customer') + '! ' + _getStaffSignature();
    }
    
    document.getElementById('_lwaVars').style.display  = 'none';
    document.getElementById('_lwaVarBox').innerHTML    = '';
    document.getElementById('_lwaNoTpl').style.display = 'none';
    document.getElementById('_lwaResult').style.display= 'none';
    document.getElementById('_lwaSend').disabled       = false;
    _applyModeStyle();

    document.getElementById('_lwaModal').style.display = 'flex';
    _loadTpls();
  };

})();
