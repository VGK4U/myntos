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
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px">',
    '<button type="button" onclick="window._lwaApplyQuick(\'thanks_connecting\')" style="background:#ecfdf5;border:1.5px solid #a7f3d0;color:#065f46;border-radius:9px;padding:8px 10px;font-size:12px;font-weight:700;cursor:pointer;text-align:left;display:flex;align-items:center;gap:6px"><span style="font-size:16px">🙏</span><div><div>Thanks for Connecting</div><small style="font-size:9.5px;font-weight:400;opacity:.8">Service tailored</small></div></button>',
    '<button type="button" onclick="window._lwaApplyQuick(\'trying_to_reach\')" style="background:#fef3c7;border:1.5px solid #fde68a;color:#92400e;border-radius:9px;padding:8px 10px;font-size:12px;font-weight:700;cursor:pointer;text-align:left;display:flex;align-items:center;gap:6px"><span style="font-size:16px">📞</span><div><div>Trying to Reach</div><small style="font-size:9.5px;font-weight:400;opacity:.8">Call missed / inquiry</small></div></button>',
    '</div>',

    /* 1-tap digital catalog share option */
    '<div style="background:#f0fdf4;border:1.5px solid #86efac;border-radius:10px;padding:10px 12px;margin-bottom:14px">',
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;gap:8px;flex-wrap:wrap">',
    '<div style="display:flex;align-items:center;gap:6px;flex:1;min-width:180px">',
    '<i class="fas fa-book-open" style="color:#15803d;font-size:13px"></i>',
    '<select id="_lwaCatSel" onchange="window._lwaOnCatalogSelect(this.value)" style="flex:1;font-size:11.5px;font-weight:700;color:#166534;background:#fff;border:1.5px solid #86efac;border-radius:6px;padding:3px 6px;cursor:pointer;outline:none">',
    '<option value="solar">☀️ Solar Rooftop & EPC</option>',
    '<option value="industrial_hub">🏢 MyntReal Hub (5-in-1 Franchise)</option>',
    '<option value="customer_ev_pricing">⚡ Customer 2W EV Pricing & Models</option>',
    '<option value="hub_pricing">🏷️ Hub Commercials & Pricing (24h)</option>',
    '<option value="ev_b2b">🚚 Commercial EV Fleet & Cargo (B2B)</option>',
    '<option value="ev_b2c">⚡ Smart Electric 2-Wheelers (B2C)</option>',
    '<option value="ev_spares">⚙️ EV Spares, Chargers & Batteries</option>',
    '<option value="etc_training">🎓 ETC EV Technician Certifications</option>',
    '<option value="real_estate">🏡 Premium Real Estate & Townships</option>',
    '<option value="insurance">🛡️ Comprehensive Insurance Advisory</option>',
    '</select>',
    '</div>',
    '<div style="display:flex;gap:4px" id="_lwaCatLangPills">',
    '<button type="button" onclick="window._lwaApplyCatalog(\'te\')" class="_lwaCatLang" data-lang="te" style="padding:2px 8px;border-radius:5px;border:1px solid #16a34a;background:#16a34a;color:#fff;font-size:11px;font-weight:700;cursor:pointer">తెలుగు</button>',
    '<button type="button" onclick="window._lwaApplyCatalog(\'en\')" class="_lwaCatLang" data-lang="en" style="padding:2px 8px;border-radius:5px;border:1px solid #d1d5db;background:#fff;color:#374151;font-size:11px;font-weight:600;cursor:pointer">EN</button>',
    '<button type="button" onclick="window._lwaApplyCatalog(\'hi\')" class="_lwaCatLang" data-lang="hi" style="padding:2px 8px;border-radius:5px;border:1px solid #d1d5db;background:#fff;color:#374151;font-size:11px;font-weight:600;cursor:pointer">हिन्दी</button>',
    '<button type="button" onclick="window._lwaApplyCatalog(\'ta\')" class="_lwaCatLang" data-lang="ta" style="padding:2px 8px;border-radius:5px;border:1px solid #d1d5db;background:#fff;color:#374151;font-size:11px;font-weight:600;cursor:pointer">தமிழ்</button>',
    '</div>',
    '</div>',
    '<div id="_lwaCatDesc" style="font-size:11px;color:#15803d;line-height:1.45;margin-bottom:8px">Sends personalized Har Ghar Solar Digital Catalog link with 90% savings, ₹78,000 subsidy &amp; ₹1 scheme details.</div>',
    '<button type="button" id="_lwaCatInsertBtn" onclick="window._lwaApplyCatalog()" style="width:100%;padding:7px 12px;background:#15803d;color:#fff;border:none;border-radius:7px;font-size:12px;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px"><i class="fas fa-link"></i> <span id="_lwaCatBtnText">Insert Personalized Solar Catalog Link</span></button>',
    '</div>',

    /* filters & add template header */
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">',
    '<div style="font-size:10.5px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:.04em">📂 Segment &amp; Template Selection</div>',
    '<button type="button" onclick="window._lwaToggleAddTpl()" style="padding:3px 9px;background:#059669;color:#fff;border:none;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer;display:flex;align-items:center;gap:4px" title="Create a new template for any segment"><i class="fas fa-plus"></i> Add New Template</button>',
    '</div>',

    '<div id="_lwaFilters" style="display:flex;gap:8px;margin-bottom:8px">',
    '<select id="_lwaSeg" onchange="window._lwaLoadTpls()" style="flex:1;font-size:12px;padding:6px 8px;border:1px solid #e5e7eb;border-radius:7px;background:#fff">',
    '<option value="">🏢 All Segments</option>',
    '<option value="solar">☀️ Solar</option>',
    '<option value="real_estate">🏡 Real Estate</option>',
    '<option value="myntreal_real">🏢 Myntreal Real</option>',
    '<option value="ev_b2c">⚡ EV B2C</option>',
    '<option value="ev_b2b">⚡ EV B2B</option>',
    '<option value="EV_SPARES">⚙️ EV Spares</option>',
    '<option value="etc_training">🎓 ETC Training</option>',
    '<option value="partner">🤝 Partner</option>',
    '<option value="leads">🎯 Leads</option>',
    '<option value="staff">👔 Staff</option>',
    '<option value="vgk">⭐ VGK Members</option>',
    '<option value="general">🌐 MNR General</option>',
    '<option value="system">🤖 System</option>',
    '</select>',
    '<select id="_lwaCat" onchange="window._lwaLoadTpls()" style="flex:1;font-size:12px;padding:6px 8px;border:1px solid #e5e7eb;border-radius:7px;background:#fff">',
    '<option value="">All Categories</option>',
    '<option value="MARKETING">Marketing</option>',
    '<option value="UTILITY">Utility</option>',
    '<option value="AUTHENTICATION">Authentication</option>',
    '</select>',
    '</div>',

    /* search bar for template content / name */
    '<div style="position:relative;margin-bottom:8px">',
    '<input type="text" id="_lwaTplSearch" placeholder="🔍 Search template content or name..." oninput="window._lwaFilterTpls()" style="width:100%;font-size:12px;border:1px solid #e5e7eb;border-radius:7px;padding:6px 10px;box-sizing:border-box">',
    '</div>',

    /* template selector */
    '<div style="margin-bottom:12px">',
    '<label id="_lwaTplLbl" style="font-size:10.5px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;display:block;margin-bottom:4px">Template (Approved &amp; Ready)</label>',
    '<select id="_lwaTpl" onchange="window._lwaTplChange()" style="width:100%;font-size:12px;border:1px solid #e5e7eb;border-radius:7px;padding:6px 9px;background:#fff;box-sizing:border-box">',
    '<option value="">— Loading templates… —</option>',
    '</select>',
    '<div id="_lwaNoTpl" style="display:none;margin-top:6px;font-size:11px;color:#b45309;background:#fef3c7;border:1px solid #fde68a;border-radius:6px;padding:8px 10px">',
    '<i class="fas fa-exclamation-triangle me-1"></i>No approved templates found for this filter. <a href="javascript:void(0)" onclick="window._lwaToggleAddTpl(true)" style="color:#b45309;font-weight:700;text-decoration:underline">Click here to add one now.</a>',
    '</div>',
    '</div>',

    /* inline Add Template Form Card */
    '<div id="_lwaAddTplCard" style="display:none;background:#f8fafc;border:1.5px solid #cbd5e1;border-radius:10px;padding:12px;margin-bottom:12px">',
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">',
    '<div style="font-size:12px;font-weight:800;color:#0f172a"><i class="fas fa-plus-circle text-success me-1"></i> Create &amp; Approve New Segment Template</div>',
    '<button type="button" onclick="window._lwaToggleAddTpl(false)" style="background:none;border:none;color:#64748b;font-size:16px;cursor:pointer">&times;</button>',
    '</div>',
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">',
    '<div><label style="font-size:10px;font-weight:700;color:#475569;display:block;margin-bottom:2px">Template Name</label><input type="text" id="_lwaNewTplName" placeholder="e.g. Solar Site Visit Alert" style="width:100%;font-size:11.5px;border:1px solid #cbd5e1;border-radius:6px;padding:5px 8px;box-sizing:border-box"></div>',
    '<div><label style="font-size:10px;font-weight:700;color:#475569;display:block;margin-bottom:2px">Segment</label><select id="_lwaNewTplSeg" style="width:100%;font-size:11.5px;border:1px solid #cbd5e1;border-radius:6px;padding:5px 8px;background:#fff;box-sizing:border-box">',
    '<option value="solar">Solar</option>',
    '<option value="general">MNR General</option>',
    '<option value="real_estate">Real Estate</option>',
    '<option value="myntreal_real">Myntreal Real</option>',
    '<option value="ev_b2c">EV B2C</option>',
    '<option value="ev_b2b">EV B2B</option>',
    '<option value="EV_SPARES">EV Spares</option>',
    '<option value="etc_training">ETC Training</option>',
    '<option value="partner">Partner</option>',
    '<option value="leads">Leads</option>',
    '<option value="staff">Staff</option>',
    '<option value="vgk">VGK</option>',
    '<option value="system">System</option>',
    '</select></div>',
    '</div>',
    '<div style="margin-bottom:8px"><label style="font-size:10px;font-weight:700;color:#475569;display:block;margin-bottom:2px">Category</label><select id="_lwaNewTplCat" style="width:100%;font-size:11.5px;border:1px solid #cbd5e1;border-radius:6px;padding:5px 8px;background:#fff;box-sizing:border-box"><option value="MARKETING">Marketing</option><option value="UTILITY">Utility</option></select></div>',
    '<div style="margin-bottom:8px">',
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px">',
    '<label style="font-size:10px;font-weight:700;color:#475569">Message Body</label>',
    '<span style="font-size:10px;color:#64748b">Use <code>{{1}}</code>, <code>{{2}}</code> for variables</span>',
    '</div>',
    '<textarea id="_lwaNewTplBody" rows="3" style="width:100%;font-size:12px;border:1px solid #cbd5e1;border-radius:6px;padding:6px 8px;box-sizing:border-box" placeholder="Namaskaram {{1}}! Here are your project details..."></textarea>',
    '</div>',
    '<div style="display:flex;justify-content:flex-end;gap:6px">',
    '<button type="button" onclick="window._lwaToggleAddTpl(false)" style="padding:5px 10px;border:1px solid #cbd5e1;border-radius:6px;background:#fff;font-size:11px;cursor:pointer">Cancel</button>',
    '<button type="button" id="_lwaSaveTplBtn" onclick="window._lwaSaveNewTpl()" style="padding:5px 12px;background:#059669;color:#fff;border:none;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer"><i class="fas fa-save me-1"></i> Save &amp; Approve for WhatsApp API</button>',
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
    '<div style="display:flex;gap:6px">',
    '<input type="tel" id="_lwaPhoneInp" style="flex:1;font-size:13px;border:1px solid #e5e7eb;border-radius:7px;padding:7px 10px;box-sizing:border-box" placeholder="10-digit mobile number">',
    '<button type="button" id="_lwaPhoneEditBtn" onclick="window._lwaUnlockPhone()" style="display:none;padding:7px 12px;border:1px solid #d1d5db;border-radius:7px;background:#f9fafb;color:#374151;font-size:12px;cursor:pointer" title="Change Number"><i class="fas fa-edit"></i></button>',
    '</div>',
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
  function _toggleAddTpl(show) {
    var card = document.getElementById('_lwaAddTplCard');
    if (!card) return;
    var isVis = card.style.display !== 'none';
    var nextVis = (show !== undefined) ? show : !isVis;
    card.style.display = nextVis ? 'block' : 'none';
    if (nextVis) {
      var currentSeg = document.getElementById('_lwaSeg') ? document.getElementById('_lwaSeg').value : 'solar';
      var newSegSel = document.getElementById('_lwaNewTplSeg');
      if (newSegSel && currentSeg) newSegSel.value = currentSeg;
      var nameInp = document.getElementById('_lwaNewTplName');
      if (nameInp) { nameInp.value = ''; nameInp.focus(); }
      var bodyInp = document.getElementById('_lwaNewTplBody');
      if (bodyInp) bodyInp.value = '';
    }
  }

  function _saveNewTpl() {
    var nameInp = document.getElementById('_lwaNewTplName');
    var segSel = document.getElementById('_lwaNewTplSeg');
    var catSel = document.getElementById('_lwaNewTplCat');
    var bodyInp = document.getElementById('_lwaNewTplBody');
    var saveBtn = document.getElementById('_lwaSaveTplBtn');

    var name = nameInp ? nameInp.value.trim() : '';
    var seg = segSel ? segSel.value : 'general';
    var cat = catSel ? catSel.value : 'MARKETING';
    var body = bodyInp ? bodyInp.value.trim() : '';

    if (!name || !body) {
      _showRes('Please provide both Template Name and Message Body.', false);
      return;
    }

    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting & Approving…';
    }

    function _getAuthToken() {
      try {
        return localStorage.getItem('token') || localStorage.getItem('staff_token') || '';
      } catch(e) { return ''; }
    }
    var token = _getAuthToken();
    var authHeaders = { 'Content-Type': 'application/json' };
    if (token) authHeaders['Authorization'] = 'Bearer ' + token;

    fetch(API + '/templates', {
      method: 'POST',
      credentials: 'include',
      headers: authHeaders,
      body: JSON.stringify({
        name: name,
        segment: seg,
        meta_category: cat,
        body_text: body,
        usage_scope: 'all',
        is_meta_approved: true,
        meta_approval_status: 'APPROVED'
      })
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="fas fa-save me-1"></i> Save &amp; Approve for WhatsApp API';
      }
      if (d.id || d.success) {
        var newId = d.id || (d.template && d.template.id);
        _showRes('✅ Template "' + _esc(name) + '" created & approved for WhatsApp API!', true);
        _toggleAddTpl(false);
        var segFilter = document.getElementById('_lwaSeg');
        if (segFilter) segFilter.value = seg;
        _loadTpls(newId);
      } else {
        _showRes('❌ Error saving template: ' + (d.detail || d.message || 'Submission failed'), false);
      }
    })
    .catch(function(e) {
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="fas fa-save me-1"></i> Save &amp; Approve for WhatsApp API';
      }
      _showRes('❌ Network error: ' + e.message, false);
    });
  }

  function _filterTpls() {
    var query = document.getElementById('_lwaTplSearch') ? document.getElementById('_lwaTplSearch').value.toLowerCase().trim() : '';
    var sel = document.getElementById('_lwaTpl');
    if (!sel || !_s.tpls) return;

    var filtered = _s.tpls;
    if (query) {
      filtered = _s.tpls.filter(function(t) {
        var tName = (t.template_name || t.name || '').toLowerCase();
        var tBody = (t.body_text || t.content || t.body || '').toLowerCase();
        var tSeg = (t.segment || '').toLowerCase();
        return tName.includes(query) || tBody.includes(query) || tSeg.includes(query);
      });
    }

    if (!filtered.length) {
      sel.innerHTML = '<option value="">— No matching templates found —</option><option value="__create_new__">➕ Create / Add New Template for this Segment...</option>';
      document.getElementById('_lwaNoTpl').style.display = 'block';
      return;
    }

    document.getElementById('_lwaNoTpl').style.display = 'none';
    var optHtml = '<option value="">— Select a template (' + filtered.length + ' available) —</option>';
    optHtml += '<option value="__create_new__">➕ Create / Add New Template for this Segment...</option>';
    filtered.forEach(function (t) {
      optHtml += '<option value="' + t.id + '">' + _esc(t.template_name || t.name) + ' (' + (t.category || 'MARKETING') + ' · ' + (t.segment || 'General') + ')</option>';
    });
    sel.innerHTML = optHtml;
  }

  function _loadTpls(selectTplId) {
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
          sel.innerHTML = '<option value="">— No approved templates found —</option><option value="__create_new__">➕ Create / Add New Template for this Segment...</option>';
          document.getElementById('_lwaNoTpl').style.display = 'block';
          return;
        }

        var optHtml = '<option value="">— Select a template (' + _s.tpls.length + ' available) —</option>';
        optHtml += '<option value="__create_new__">➕ Create / Add New Template for this Segment...</option>';
        _s.tpls.forEach(function (t) {
          optHtml += '<option value="' + t.id + '">' + _esc(t.template_name || t.name) + ' (' + (t.category || 'MARKETING') + ' · ' + (t.segment || 'General') + ')</option>';
        });
        sel.innerHTML = optHtml;

        if (selectTplId) {
          sel.value = String(selectTplId);
          _onTplChange();
        } else {
          var searchInp = document.getElementById('_lwaTplSearch');
          if (searchInp && searchInp.value.trim()) {
            _filterTpls();
          }
        }
      })
      .catch(function () {
        sel.innerHTML = '<option value="">— Error loading templates —</option>';
      });
  }

  /* ── Template change handler ─────────────────────────────────────────────── */
  function _onTplChange() {
    var sel = document.getElementById('_lwaTpl');
    var tplId = sel ? sel.value : null;
    var varBox = document.getElementById('_lwaVarBox');
    var varWrap = document.getElementById('_lwaVars');
    var msgBox = document.getElementById('_lwaMsg');

    if (tplId === '__create_new__') {
      _toggleAddTpl(true);
      return;
    }

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
    var rawPhone = (phoneInput && (phoneInput.value.includes('•') || phoneInput.value.includes('*')))
        ? (phoneInput.dataset.rawPhone || '')
        : (phoneInput ? phoneInput.value : '');
    var targetPhone = rawPhone || _s.phone || '';
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
        if (!ext && u.emp_code) {
          var m = String(u.emp_code).match(/(\d{2,4})$/);
          if (m) ext = m[1].replace(/^0+/, '') || m[1];
        }
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
    var rawPhone = (phoneInput && (phoneInput.value.includes('•') || phoneInput.value.includes('*')))
        ? (phoneInput.dataset.rawPhone || '')
        : (phoneInput ? phoneInput.value : '');
    var targetPhone = rawPhone || _s.phone || '';
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

  function _maskPhone(p) {
    if (!p) return '-';
    var digits = String(p).replace(/\D/g, '');
    if (digits.length >= 10) {
      return '+91 ' + digits.slice(-10, -8) + '••••' + digits.slice(-4);
    }
    if (digits.length >= 4) {
      return '••••' + digits.slice(-4);
    }
    return '••••';
  }

  /* ── Digital Catalog Quick Link Generator ───────────────────────────────── */
  var DIGITAL_CATALOGS = {
    solar: {
      name: 'Solar Rooftop & EPC',
      btnLabel: 'Solar',
      segmentSlug: 'solar',
      catalogSlug: 'commercial-residential-solar',
      desc: 'Sends personalized Har Ghar Solar Digital Catalog link with 90% savings, ₹78,000 subsidy & ₹1 scheme details.',
      messages: {
        te: function(cName, url) {
          return 'నమస్కారం ' + cName + ' గారు! 🙏\n\n' +
            'MyntReal Har Ghar Solar డిజిటల్ క్యాటలాగ్ & సబ్సిడీ కాలిక్యులేటర్ లింక్ ఇక్కడ చూడవచ్చు:\n' +
            '👉 ' + url + '\n\n' +
            '⚡ ముఖ్య వివరాలు:\n' +
            '• కరెంట్ బిల్లు 90% వరకు ఆదా\n' +
            '• ₹78,000 కేంద్ర ప్రభుత్వ సబ్సిడీ (PM Surya Ghar)\n' +
            '• ₹1 కే సోలార్ & సులభ బ్యాంక్ లోన్ EMI ఆప్షన్స్\n' +
            '• Tier-1 బ్రాండ్లు & 25 సంవత్సరాల వారంటీ\n\n' +
            'పై లింక్ ఓపెన్ చేసి మీ ఇంటి కరెంట్ బిల్లుకు సరిపోయే ప్లాన్ మరియు సేవింగ్స్ కాలిక్యులేట్ చేసుకోగలరు.';
        },
        en: function(cName, url) {
          return 'Namaskaram ' + cName + '! 🙏\n\n' +
            'Here is your official MyntReal Har Ghar Solar Digital Catalog & Subsidy Estimator link:\n' +
            '👉 ' + url + '\n\n' +
            '⚡ Highlights:\n' +
            '• Reduce your power bill by up to 90%\n' +
            '• Up to ₹78,000 Central Govt Subsidy (PM Surya Ghar)\n' +
            '• "Solar for ₹1" zero-collateral bank EMI plans\n' +
            '• Authorized Tier-1 Brands & 25-Year Performance Warranty\n\n' +
            'Click the link above to calculate your recommended capacity, savings & instant quotation.';
        },
        hi: function(cName, url) {
          return 'नमस्ते ' + cName + ' जी! 🙏\n\n' +
            'MyntReal हर घर सोलर डिजिटल कैटलॉग और सब्सिडी कैलकुलेटर लिंक यहाँ देखें:\n' +
            '👉 ' + url + '\n\n' +
            '⚡ मुख्य लाभ:\n' +
            '• बिजली बिल में 90% तक बचत\n' +
            '• ₹78,000 तक केंद्र सरकारी सब्सिडी (PM सूर्य घर योजना)\n' +
            '• ₹1 में सोलर और आसान बैंक लोन ईएमआई\n' +
            '• टियर-1 सोलर ब्रांड्स और 25 साल की वारंटी\n\n' +
            'कृपया ऊपर दिए गए लिंक पर क्लिक करें और अपनी मासिक बचत की गणना करें।';
        },
        ta: function(cName, url) {
          return 'வணக்கம் ' + cName + '! 🙏\n\n' +
            'MyntReal ஹர் கர் சோலார் டிஜிட்டல் கேட்லாக் மற்றும் மானிய கால்குலேட்டர் லிங்க்:\n' +
            '👉 ' + url + '\n\n' +
            '⚡ முக்கிய சிறப்பம்சங்கள்:\n' +
            '• 90% வரை மின் கட்டண சேமிப்பு\n' +
            '• ₹78,000 மத்திய அரசு மானியம் (PM சூர்யா கர்)\n' +
            '• ₹1 சோலார் & எளிய வங்கி லோன் EMI தவணைகள்\n' +
            '• Tier-1 சோலார் பிராண்டுகள் & 25 வருட வாரண்டி\n\n' +
            'மேலே உள்ள இணைப்பைக் கிளிக் செய்து உங்கள் மின்சார சேமிப்பைக் கணக்கிடுங்கள்.';
        }
      }
    },
    real_estate: {
      name: 'Premium Real Estate & Townships',
      btnLabel: 'Real Estate',
      segmentSlug: 'real-dreams',
      catalogSlug: 'real-dreams-premium-properties',
      desc: 'Sends Real Dreams catalog with RERA-approved luxury villas, gated open plots & prime commercial spaces.',
      messages: {
        te: function(cName, url) {
          return 'నమస్కారం ' + cName + ' గారు! 🙏\n\n' +
            'MyntReal Real Dreams ప్రీమియం ప్రాపర్టీస్ డిజిటల్ క్యాటలాగ్ లింక్ ఇక్కడ చూడవచ్చు:\n' +
            '👉 ' + url + '\n\n' +
            '🏡 ప్రాజెక్ట్ విశేషాలు:\n' +
            '• RERA మరియు VMRDA/DTCP ఆమోదిత లేఅవుట్స్\n' +
            '• గేటెడ్ కమ్యూనిటీ ఓపెన్ ప్లాట్స్, లగ్జరీ విల్లాస్ & కమర్షియల్ స్పేసెస్\n' +
            '• సోలార్ స్ట్రీట్ లైటింగ్, భూగర్భ విద్యుత్ & 100% వాస్తు\n' +
            '• వేగవంతమైన ల్యాండ్ అప్రిసియేషన్ & తక్షణ రిజిస్ట్రేషన్\n\n' +
            'పై లింక్ ద్వారా లేఅవుట్ మ్యాప్స్, ధరలు మరియు సైట్ విజిట్ వివరాలు వీక్షించగలరు.';
        },
        en: function(cName, url) {
          return 'Namaskaram ' + cName + '! 🙏\n\n' +
            'Here is your official MyntReal Real Dreams Premium Properties Digital Catalog link:\n' +
            '👉 ' + url + '\n\n' +
            '🏡 Key Highlights:\n' +
            '• RERA & DTCP/VMRDA Approved Premium Layouts\n' +
            '• Gated Community Open Plots, Luxury Villas & Commercial Spaces\n' +
            '• Solar-Powered Infrastructure & Underground Utilities\n' +
            '• High Land Appreciation Potential & Clear Marketable Title\n\n' +
            'Click the link above to explore master layouts, pricing & schedule a VIP site visit.';
        },
        hi: function(cName, url) {
          return 'नमस्ते ' + cName + ' जी! 🙏\n\n' +
            'MyntReal Real Dreams प्रीमियम प्रॉपर्टीज डिजिटल कैटलॉग लिंक यहाँ देखें:\n' +
            '👉 ' + url + '\n\n' +
            '🏡 मुख्य विशेषताएं:\n' +
            '• RERA और टाउनशिप अनुमोदित प्रीमियम प्लॉट्स एवं विला\n' +
            '• गेटेड कम्युनिटी, सोलर इन्फ्रास्ट्रक्चर और आधुनिक सुविधाएं\n' +
            '• उच्च पूंजी वृद्धि (Land Appreciation) एवं तत्काल रजिस्ट्री\n\n' +
            'कृपया ऊपर दिए गए लिंक पर क्लिक करके लेआउट मैप्स और प्रोजेक्ट डिटेल्स देखें।';
        },
        ta: function(cName, url) {
          return 'வணக்கம் ' + cName + '! 🙏\n\n' +
            'MyntReal Real Dreams பிரீமியம் ரியல் எஸ்டேட் டிஜிட்டல் கேட்லாக் லிங்க்:\n' +
            '👉 ' + url + '\n\n' +
            '🏡 முக்கிய சிறப்பம்சங்கள்:\n' +
            '• RERA & அரசு அங்கீகாரம் பெற்ற ஓபன் பிளாட்கள் & வில்லாக்கள்\n' +
            '• நவீன வசதிகளுடன் கூடிய கேடட் கம்யூனிட்டி டவுன்ஷிப்\n' +
            '• வேகமான முதலீட்டு மதிப்பு உயர்வு & உடனடி பதிவு\n\n' +
            'மேலே உள்ள இணைப்பைக் கிளிக் செய்து விவரங்கள் மற்றும் விலைப்பட்டியலைக் காண்க.';
        }
      }
    },
    ev_b2c: {
      name: 'Smart Electric 2-Wheelers (B2C)',
      btnLabel: 'EV 2W',
      segmentSlug: 'ev-b2c',
      catalogSlug: 'ev-smart-commuter',
      desc: 'Sends Smart Electric 2W catalog with 120km range, LFP battery, mobile app & ₹0.25/km running cost.',
      messages: {
        te: function(cName, url) {
          return 'నమస్కారం ' + cName + ' గారు! 🙏\n\n' +
            'MyntReal Smart Electric 2-Wheelers డిజిటల్ క్యాటలాగ్ లింక్ ఇక్కడ చూడవచ్చు:\n' +
            '👉 ' + url + '\n\n' +
            '⚡ ముఖ్య విశేషాలు:\n' +
            '• ఒక్క ఛార్జ్‌తో 120+ కి.మీ రియల్-వరల్డ్ రేంజ్\n' +
            '• అధునాతన LFP బ్యాటరీ టెక్నాలజీ & లాంగ్ లైఫ్\n' +
            '• డిజిటల్ స్మార్ట్ కన్సోల్, GPS ట్రాకింగ్ & రీజెనరేటివ్ బ్రేకింగ్\n' +
            '• అతి తక్కువ రన్నింగ్ కాస్ట్ — కి.మీ కి కేవలం 25 పైసలు\n\n' +
            'పై లింక్ క్లిక్ చేసి లేటెస్ట్ ఈవీ మోడల్స్, ఫీచర్లు మరియు టెస్ట్ రైడ్ బుక్ చేసుకోండి.';
        },
        en: function(cName, url) {
          return 'Namaskaram ' + cName + '! 🙏\n\n' +
            'Here is your official MyntReal Smart Electric 2-Wheelers Digital Catalog link:\n' +
            '👉 ' + url + '\n\n' +
            '⚡ Key Highlights:\n' +
            '• 120+ km Real-World Range on a single charge\n' +
            '• Ultra-safe LFP Battery with extended warranty\n' +
            '• Smart Mobile App Connectivity, GPS & Digital Cockpit\n' +
            '• Running cost as low as ₹0.25 per kilometer\n\n' +
            'Click the link above to explore EV models, color variants & book your free test ride.';
        },
        hi: function(cName, url) {
          return 'नमस्ते ' + cName + ' जी! 🙏\n\n' +
            'MyntReal स्मार्ट इलेक्ट्रिक 2-व्हीलर्स डिजिटल कैटलॉग लिंक यहाँ देखें:\n' +
            '👉 ' + url + '\n\n' +
            '⚡ मुख्य विशेषताएं:\n' +
            '• सिंगल चार्ज में 120+ किमी की रेंज\n' +
            '• आधुनिक सुरक्षित LFP बैटरी एवं लंबी वारंटी\n' +
            '• स्मार्ट मोबाइल कनेक्टिविटी और डिजिटल फीचर्स\n' +
            '• पेट्रोल की तुलना में 85% तक की बचत (25 पैसे/किमी)\n\n' +
            'कृपया ऊपर दिए गए लिंक पर क्लिक करें और मॉडल्स देखें व फ्री टेस्ट राइड बुक करें।';
        },
        ta: function(cName, url) {
          return 'வணக்கம் ' + cName + '! 🙏\n\n' +
            'MyntReal ஸ்மார்ட் எலக்ட்ரிக் 2-வீலர் டிஜிட்டல் கேட்லாக் லிங்க்:\n' +
            '👉 ' + url + '\n\n' +
            '⚡ முக்கிய சிறப்பம்சங்கள்:\n' +
            '• ஒரு சார்ஜில் 120+ கிமீ ரேஞ்ச்\n' +
            '• அதிநவீன LFP பேட்டரி & நீண்ட கால உத்தரவாதம்\n' +
            '• பெட்ரோல் செலவில் 85% மிச்சம்\n\n' +
            'மேலே உள்ள இணைப்பைக் கிளிக் செய்து ஈவி மாடல்களைப் பார்வையிட்டு டெஸ்ட் ரைடு புக் செய்யுங்கள்.';
        }
      }
    },
    ev_b2b: {
      name: 'Commercial EV Fleet & Cargo (B2B)',
      btnLabel: 'EV Commercial Fleet',
      segmentSlug: 'ev-b2b',
      catalogSlug: 'ev-commercial-fleet',
      desc: 'Sends Commercial Fleet catalog with 75% logistics savings, reinforced chassis & 2-min battery swap.',
      messages: {
        te: function(cName, url) {
          return 'నమస్కారం ' + cName + ' గారు! 🙏\n\n' +
            'MyntReal Commercial EV Fleet & B2B Cargo డిజిటల్ క్యాటలాగ్ లింక్ ఇక్కడ చూడవచ్చు:\n' +
            '👉 ' + url + '\n\n' +
            '🚚 ముఖ్య ప్రయోజనాలు:\n' +
            '• లాజిస్టిక్స్ రన్నింగ్ ఖర్చుల్లో 75% భారీ ఆదా\n' +
            '• భారీ పేలోడ్ సామర్థ్యం కలిగిన హెవీ-డ్యూటీ చాసిస్\n' +
            '• 2 నిమిషాల క్విక్ బ్యాటరీ స్వాప్పింగ్ & స్మార్ట్ టెలిమాటిక్స్ ఫ్లీట్ ట్రాకింగ్\n' +
            '• డెలివరీ & బిజినెస్ ఫ్లీట్‌లకు ప్రత్యేక కార్పొరేట్ ఫైనాన్స్\n\n' +
            'పై లింక్ క్లిక్ చేసి B2B ఫ్లీట్ మోడల్స్ మరియు ROI కాలిక్యులేటర్ చూడండి.';
        },
        en: function(cName, url) {
          return 'Namaskaram ' + cName + '! 🙏\n\n' +
            'Here is your official MyntReal Commercial EV Fleet & B2B Cargo Digital Catalog link:\n' +
            '👉 ' + url + '\n\n' +
            '🚚 Commercial Fleet Highlights:\n' +
            '• Slash last-mile logistics operating expenses by 75%\n' +
            '• Heavy-duty reinforced chassis engineered for Indian cargo loads\n' +
            '• 2-Minute rapid battery swapping & real-time IoT fleet telematics\n' +
            '• Attractive commercial leasing & zero-downpayment corporate finance\n\n' +
            'Click the link above to review vehicle specifications & calculate fleet ROI.';
        },
        hi: function(cName, url) {
          return 'नमस्ते ' + cName + ' जी! 🙏\n\n' +
            'MyntReal कमर्शियल ईवी फ्लीट और B2B कार्गो डिजिटल कैटलॉग लिंक यहाँ देखें:\n' +
            '👉 ' + url + '\n\n' +
            '🚚 प्रमुख लाभ:\n' +
            '• डिलीवरी और लॉजिस्टिक्स खर्च में 75% तक कटौती\n' +
            '• भारी माल वहन क्षमता एवं मजबूत चेसिस\n' +
            '• 2 मिनट की बैटरी स्वैपिंग और लाइव जीपीएस फ्लीट ट्रैकिंग\n' +
            '• आकर्षक कॉर्पोरेट फाइनेंस और लीजिंग विकल्प\n\n' +
            'कृपया ऊपर दिए गए लिंक पर क्लिक करके कमर्शियल वाहन विवरण देखें।';
        },
        ta: function(cName, url) {
          return 'வணக்கம் ' + cName + '! 🙏\n\n' +
            'MyntReal கமர்ஷியல் இ-வாகன கடற்படை (EV Cargo) டிஜிட்டல் கேட்லாக் லிங்க்:\n' +
            '👉 ' + url + '\n\n' +
            '🚚 முக்கிய நன்மைகள்:\n' +
            '• போக்குவரத்து செலவில் 75% பெரும் சேமிப்பு\n' +
            '• அதிக எடை சுமக்கும் திறன் மற்றும் நீண்ட ஆயுள்\n' +
            '• 2 நிமிட பேட்டரி ஸ்வாப் & லைவ் GPS டிராக்கிங்\n\n' +
            'மேலே உள்ள இணைப்பைக் கிளிக் செய்து விவரங்கள் மற்றும் கார்ப்பரேட் சலுகைகளைக் காண்க.';
        }
      }
    },
    ev_spares: {
      name: 'EV Spares, Chargers & Batteries',
      btnLabel: 'EV Spares',
      segmentSlug: 'ev-spares',
      catalogSlug: 'ev-spares-and-chargers',
      desc: 'Sends EV Spares catalog with OEM components, DC fast chargers, smart BMS & replacement lithium packs.',
      messages: {
        te: function(cName, url) {
          return 'నమస్కారం ' + cName + ' గారు! 🙏\n\n' +
            'MyntReal Genuine EV Spares, Chargers & Batteries డిజిటల్ క్యాటలాగ్ లింక్ ఇక్కడ చూడవచ్చు:\n' +
            '👉 ' + url + '\n\n' +
            '⚙️ ప్రొడక్ట్ వివరాలు:\n' +
            '• అన్ని ప్రముఖ బ్రాండ్ల ఒరిజినల్ OEM-గ్రేడ్ EV స్పేర్ పార్ట్స్\n' +
            '• హై-పవర్ DC ఫాస్ట్ ఛార్జర్లు & పోర్టబుల్ హోమ్ ఛార్జర్లు\n' +
            '• స్మార్ట్ BMS కలిగిన అధునాతన లిథియం-అయాన్ & LFP బ్యాటరీ ప్యాక్స్\n' +
            '• కంట్రోలర్లు, వైరింగ్ హార్నెస్ & బ్రేకింగ్ కాంపోనెంట్స్\n\n' +
            'పై లింక్ క్లిక్ చేసి కాంపోనెంట్స్ లిస్ట్, స్పెసిఫికేషన్స్ మరియు హోల్‌సేల్ ధరలు చూడగలరు.';
        },
        en: function(cName, url) {
          return 'Namaskaram ' + cName + '! 🙏\n\n' +
            'Here is your official MyntReal EV Spares, Chargers & Battery Systems Digital Catalog link:\n' +
            '👉 ' + url + '\n\n' +
            '⚙️ Component Highlights:\n' +
            '• Certified OEM-grade replacement spares for all major EV makes\n' +
            '• High-power DC Fast Chargers & Smart Home AC Charging units\n' +
            '• Advanced Lithium-ion & LFP battery packs with intelligent BMS\n' +
            '• High-efficiency motor controllers, harnesses & mechanical components\n\n' +
            'Click the link above to view catalog inventory, compatibility & dealer pricing.';
        },
        hi: function(cName, url) {
          return 'नमस्ते ' + cName + ' जी! 🙏\n\n' +
            'MyntReal जेन्युइन ईवी स्पेयर पार्ट्स, चार्जर्स और बैटरी डिजिटल कैटलॉग लिंक यहाँ देखें:\n' +
            '👉 ' + url + '\n\n' +
            '⚙️ मुख्य उत्पाद:\n' +
            '• प्रमुख ईवी ब्रांड्स के लिए OEM-ग्रेड प्रमाणित स्पेयर पार्ट्स\n' +
            '• हाई-पावर डीसी फास्ट चार्जर्स और स्मार्ट होम चार्जर्स\n' +
            '• स्मार्ट बीएमएस (BMS) से लैस एडवांस लिथियम बैटरी पैक्स\n\n' +
            'कृपया ऊपर दिए गए लिंक पर क्लिक करके पार्ट्स लिस्ट और कीमतें देखें।';
        },
        ta: function(cName, url) {
          return 'வணக்கம் ' + cName + '! 🙏\n\n' +
            'MyntReal ஈவி உதிரிபாகங்கள், சார்ஜர்கள் & பேட்டரி டிஜிட்டல் கேட்லாக் லிங்க்:\n' +
            '👉 ' + url + '\n\n' +
            '⚙️ முக்கிய தயாரிப்புகள்:\n' +
            '• அசல் OEM சான்றளிக்கப்பட்ட ஈவி உதிரிபாகங்கள்\n' +
            '• அதிவேக DC ஃபாஸ்ட் சார்ஜர்கள் & ஸ்மார்ட் சார்ஜிங் சாதனங்கள்\n' +
            '• ஸ்மார்ட் BMS கொண்ட லித்தியம் பேட்டரி பேக்குகள்\n\n' +
            'மேலே உள்ள இணைப்பைக் கிளிக் செய்து முழு விவரங்களையும் காண்க.';
        }
      }
    },
    etc_training: {
      name: 'ETC EV Technician Certifications',
      btnLabel: 'ETC Training',
      segmentSlug: 'etc',
      catalogSlug: 'etc-renewable-certifications',
      desc: 'Sends ETC Training catalog: 1-week EV certification at Govt. Poly Pendurthi, ₹10,000 scholarship discount.',
      messages: {
        te: function(cName, url) {
          return 'నమస్కారం ' + cName + ' గారు! 🙏\n\n' +
            'EVolution Training Centre (ETC) ప్రొఫెషనల్ EV సర్టిఫికేషన్ డిజిటల్ క్యాటలాగ్ లింక్ ఇక్కడ చూడవచ్చు:\n' +
            '👉 ' + url + '\n\n' +
            '🎓 కోర్సు విశేషాలు:\n' +
            '• 1-వారం ప్రాక్టికల్ EV టెక్నీషియన్ & ఎంటర్‌ప్రెన్యూర్‌షిప్ ప్రోగ్రామ్\n' +
            '• Govt. Polytechnic College, Pendurthi లో ప్రత్యక్ష ప్రాక్టికల్ ల్యాబ్స్\n' +
            '• BLDC మోటార్లు, బ్యాటరీ ప్యాక్ అసెంబ్లీ & BMS డయాగ్నోస్టిక్స్ లో శిక్షణ\n' +
            '• ఫీజు ₹19,999 కి బదులుగా ₹10,000 స్కాలర్‌షిప్‌తో కేవలం ₹9,999 మాత్రమే!\n' +
            '• 100% ప్లేస్‌మెంట్ అసిస్టెన్స్ & సర్వీస్ సెంటర్ బిజినెస్ గైడెన్స్\n\n' +
            'పై లింక్ క్లిక్ చేసి సిలబస్ మరియు తదుపరి బ్యాచ్ వివరాలు చూడండి.';
        },
        en: function(cName, url) {
          return 'Namaskaram ' + cName + '! 🙏\n\n' +
            'Here is your official MyntReal EVolution Training Centre (ETC) Professional EV Certifications Digital Catalog link:\n' +
            '👉 ' + url + '\n\n' +
            '🎓 Certification Highlights:\n' +
            '• 1-Week Intensive Hands-on EV Technician & Entrepreneurship Certification\n' +
            '• Conducted at Govt. Polytechnic College, Pendurthi with live lab equipment\n' +
            '• Deep training on BLDC motors, Lithium battery pack assembly & BMS debugging\n' +
            '• Standard Fee ₹19,999 discounted by ₹10,000 Scholarship — Final Fee ₹9,999 only!\n' +
            '• 100% Career placement assistance & EV service franchise support\n\n' +
            'Click the link above to view curriculum, batch dates & reserve your seat.';
        },
        hi: function(cName, url) {
          return 'नमस्ते ' + cName + ' जी! 🙏\n\n' +
            'EVolution Training Centre (ETC) प्रोफेशनल ईवी सर्टिफिकेशन डिजिटल कैटलॉग लिंक यहाँ देखें:\n' +
            '👉 ' + url + '\n\n' +
            '🎓 कोर्स की मुख्य विशेषताएं:\n' +
            '• 1-सप्ताह का हैंड्स-ऑन ईवी तकनीशियन एवं उद्यमिता प्रमाणन\n' +
            '• Govt. Polytechnic College, Pendurthi में व्यावहारिक प्रयोगशाला प्रशिक्षण\n' +
            '• BLDC मोटर्स, लिथियम बैटरी पैक असेंबली और BMS डायग्नोस्टिक्स में महारत\n' +
            '• ₹19,999 फीस पर ₹10,000 स्कॉलरशिप छूट — केवल ₹9,999!\n' +
            '• 100% जॉब प्लेसमेंट सहायता एवं ईवी सर्विस सेंटर शुरू करने हेतु मार्गदर्शन\n\n' +
            'कृपया ऊपर दिए गए लिंक पर क्लिक करके बैच डेट्स और सीट रिजर्व करें।';
        },
        ta: function(cName, url) {
          return 'வணக்கம் ' + cName + '! 🙏\n\n' +
            'EVolution Training Centre (ETC) தொழில்முறை ஈவி சான்றிதழ் டிஜிட்டல் கேட்லாக் லிங்க்:\n' +
            '👉 ' + url + '\n\n' +
            '🎓 பாடப்பிரிவின் சிறப்பம்சங்கள்:\n' +
            '• 1 வார தீவிர செய்முறை ஈவி தொழில்நுட்ப வல்லுநர் பயிற்சி\n' +
            '• அரசு பாலிடெக்னிக் கல்லூரி, பெந்துர்த்தியில் நேரடி பயிற்சி கூடங்கள்\n' +
            '• BLDC மோட்டார், லித்தியம் பேட்டரி மற்றும் BMS பழுதுபார்ப்பு பயிற்சி\n' +
            '• ₹19,999 கட்டணத்தில் ₹10,000 கல்வி உதவித்தொகை — கட்டணம் ₹9,999 மட்டுமே!\n' +
            '• 100% வேலைவாய்ப்பு உதவி & தொழில் தொடங்க ஆதரவு\n\n' +
            'மேலே உள்ள இணைப்பைக் கிளிக் செய்து பாடத்திட்டம் மற்றும் சேர்க்கை விவரங்களை அறிக.';
        }
      }
    },
    insurance: {
      name: 'Comprehensive Insurance Advisory',
      btnLabel: 'Insurance',
      segmentSlug: 'insurance',
      catalogSlug: 'comprehensive-insurance-advisory',
      desc: 'Sends Insurance catalog with complete risk protection for EV fleets, solar rooftop plants, health & life.',
      messages: {
        te: function(cName, url) {
          return 'నమస్కారం ' + cName + ' గారు! 🙏\n\n' +
            'MyntReal Comprehensive Insurance Advisory డిజిటల్ క్యాటలాగ్ లింక్ ఇక్కడ చూడవచ్చు:\n' +
            '👉 ' + url + '\n\n' +
            '🛡️ ఇన్సూరెన్స్ రక్షణ వివరాలు:\n' +
            '• ఎలక్ట్రిక్ వెహికల్స్ (EV) & కమర్షియల్ ఫ్లీట్ ఇన్సూరెన్స్\n' +
            '• సోలార్ రూఫ్‌టాప్ ప్లాంట్ ఆల్-రిస్క్ ప్రొటెక్షన్ పాలసీలు\n' +
            '• సమగ్ర హెల్త్ ఇన్సూరెన్స్ (Cashless Hospitalization) & టర్మ్ లైఫ్ కవర్\n' +
            '• బిజినెస్, షాప్ & ఫ్యాక్టరీ ప్రాపర్టీ ఇన్సూరెన్స్\n' +
            '• వేగవంతమైన క్లెయిమ్స్ అసిస్టెన్స్ & డెడికేటెడ్ రిలేషన్‌షిప్ మేనేజర్\n\n' +
            'పై లింక్ క్లిక్ చేసి ఇన్సూరెన్స్ పాలసీల వివరాలు మరియు తక్షణ కొటేషన్ పొందండి.';
        },
        en: function(cName, url) {
          return 'Namaskaram ' + cName + '! 🙏\n\n' +
            'Here is your official MyntReal Comprehensive Insurance Advisory Digital Catalog link:\n' +
            '👉 ' + url + '\n\n' +
            '🛡️ Advisory Highlights:\n' +
            '• Specialized EV & Commercial Fleet motor insurance policies\n' +
            '• Solar Rooftop Installation All-Risk & Generation Loss Protection\n' +
            '• Comprehensive Health & Family Term Life plans with cashless network\n' +
            '• Business, Warehouse & Commercial Property Risk Shield\n' +
            '• Dedicated claims assistance team for rapid settlement\n\n' +
            'Click the link above to view plans, compare coverage & receive a customized quote.';
        },
        hi: function(cName, url) {
          return 'नमस्ते ' + cName + ' जी! 🙏\n\n' +
            'MyntReal व्यापक बीमा सलाहकार (Insurance Advisory) डिजिटल कैटलॉग लिंक यहाँ देखें:\n' +
            '👉 ' + url + '\n\n' +
            '🛡️ बीमा सुरक्षा के मुख्य लाभ:\n' +
            '• इलेक्ट्रिक वाहन (EV) और कमर्शियल फ्लीट विशेष बीमा\n' +
            '• सोलर रूफटॉप प्लांट ऑल-रिस्क कवरेज\n' +
            '• फैमिली हेल्थ एवं टर्म लाइफ इंश्योरेंस प्लान्स (कैशलेस सुविधा)\n' +
            '• व्यापार और कमर्शियल प्रॉपर्टी प्रोटेक्शन\n' +
            '• त्वरित क्लेम निपटान सहायता\n\n' +
            'कृपया ऊपर दिए गए लिंक पर क्लिक करके बीमा योजनाओं की तुलना करें और कोटेशन पाएं।';
        },
        ta: function(cName, url) {
          return 'வணக்கம் ' + cName + '! 🙏\n\n' +
            'MyntReal விரிவான காப்பீட்டு ஆலோசனை (Insurance Advisory) டிஜிட்டல் கேட்லாக் லிங்க்:\n' +
            '👉 ' + url + '\n\n' +
            '🛡️ காப்பீட்டு சிறப்பம்சங்கள்:\n' +
            '• எலக்ட்ரிக் வாகனங்கள் மற்றும் வணிக கடற்படைக்கான சிறப்பு காப்பீடு\n' +
            '• சோலார் ஆலைக்கான முழுமையான இடர் பாதுகாப்பு\n' +
            '• விரிவான மருத்துவ & ஆயுள் காப்பீட்டு திட்டங்கள்\n' +
            '• உடனடி க்ளைம் தீர்வு உதவி\n\n' +
            'மேலே உள்ள இணைப்பைக் கிளிக் செய்து பாலிசி விவரங்களை அறிந்து உடனடி கொட்டேஷன் பெறுங்கள்.';
        }
      }
    },
    industrial_hub: {
      name: 'MyntReal Hub (5-in-1 Franchise)',
      btnLabel: 'MyntReal Hub',
      segmentSlug: 'industrial-hub',
      catalogSlug: 'industrial-hub-franchise',
      desc: 'Sends MyntReal Hub catalog: 5-in-1 investor franchise (EV, Solar, Insurance, Real Estate & Training) with ₹12–15L investment & 140% ROI.',
      messages: {
        te: function(cName, url) {
          return 'నమస్కారం ' + cName + ' గారు! 🙏\n\n' +
            'MyntReal Hub (5-in-1 ఇన్వెస్టర్ ఫ్రాంచైజ్) అధికారిక డిజిటల్ క్యాటలాగ్ లింక్:\n' +
            '👉 ' + url + '\n\n' +
            '🏢 ఒకే హబ్ — 5 లాభదాయక వ్యాపార మార్గాలు:\n' +
            '• మంత్ర ఈవీ షోరూమ్ & స్పేర్స్ డిపో (యూనిట్‌కు ₹7,000 మార్జిన్)\n' +
            '• హర్ ఘర్ సోలార్ రూఫ్‌టాప్ EPC (₹78,000 సబ్సిడీ & ప్రాజెక్ట్‌కు ₹20,000 మార్జిన్)\n' +
            '• VGK కేర్ ఇన్సూరెన్స్ అడ్వైజరీ (40+ ఇన్సూరర్లు, పాలసీకి ₹3,000 మార్జిన్)\n' +
            '• VGK రియల్ డ్రీమ్స్ టౌన్‌షిప్స్ & విల్లాస్ బ్రోకరేజ్\n' +
            '• EVolution ట్రైనింగ్ సెంటర్ (గవర్నమెంట్ పాలిటెక్నిక్ కాలేజ్ పార్టనర్)\n\n' +
            '💼 పెట్టుబడి: ₹12–15 లక్షలు | బ్రేక్-ఈవెన్: 6-9 నెలలు | వార్షిక నికర ఆదాయం: ₹19.8 లక్షలు+\n' +
            '🎁 ఫ్రాంచైజీతో పాటు కంప్యూటర్, 43" స్మార్ట్ టీవీ, కలర్ ప్రింటర్, షోరూమ్ బ్రాండింగ్ & 12 నెలల లీడ్ సపోర్ట్ ఉచితం!\n\n' +
            'పై లింక్ క్లిక్ చేసి పూర్తి ప్రాస్పెక్టస్, ROI మోడల్ & వివరాలు చూడగలరు.';
        },
        en: function(cName, url) {
          return 'Namaskaram ' + cName + '! 🙏\n\n' +
            'Here is your official MyntReal Hub (5-in-1 Investor Franchise) Digital Catalog link:\n' +
            '👉 ' + url + '\n\n' +
            '🏢 One Hub — 5 High-Demand Business Streams:\n' +
            '• Manthra EV Dealership & Spares (₹7,000 / unit margin)\n' +
            '• Har Ghar Solar EPC (₹78,000 DBT subsidy & ₹20,000 / system margin)\n' +
            '• VGK Care Insurance Advisory (40+ Insurers, ₹3,000 / policy margin)\n' +
            '• VGK Real Dreams Townships & Luxury Villas (High-ticket brokerage)\n' +
            '• EVolution Training Centre (Govt. Polytechnic College Campus)\n\n' +
            '💼 Investment: ₹12 – 15 Lakhs | Break-even: 6–9 Months | Base Net: ₹19.80 Lakhs / yr\n' +
            '🎁 Turnkey Setup: Business PC with MyntOS ERP, 43" Smart TV, Color Printer, Complete Showroom Branding & 12 Months Lead Support included!\n\n' +
            'Click the link above to review complete deliverables, financial models & territory rights.';
        },
        hi: function(cName, url) {
          return 'नमस्ते ' + cName + ' जी! 🙏\n\n' +
            'MyntReal Hub (5-इन-1 इन्वेस्टर फ्रैंचाइज़) आधिकारिक डिजिटल कैटलॉग लिंक यहाँ देखें:\n' +
            '👉 ' + url + '\n\n' +
            '🏢 एक हब — 5 उच्च मुनाफे वाले व्यापार:\n' +
            '• मंत्रा ईवी डीलरशिप एवं स्पेयर पार्ट्स (₹7,000 प्रति वाहन मार्जिन)\n' +
            '• हर घर सोलर रूफटॉप ईपीसी (₹78,000 सब्सिडी एवं ₹20,000 प्रति सिस्टम मार्जिन)\n' +
            '• वीजीके केयर बीमा सलाहकार (40+ बीमा कंपनियाँ, ₹3,000 प्रति पॉलिसी मार्जिन)\n' +
            '• वीजीके रियल ड्रीम्स टाउनशिप एवं विला ब्रोकरेज\n' +
            '• ईवीोल्यूशन ट्रेनिंग सेंटर (गवर्नमेंट पॉलिटेक्निक कॉलेज पार्टनर)\n\n' +
            '💼 निवेश: ₹12–15 लाख | ब्रेक-ईवन: 6–9 महीने | अनुमानित शुद्ध वार्षिक आय: ₹19.8 लाख+\n' +
            '🎁 टर्नकी सेटअप: बिजनेस पीसी, 43" स्मार्ट टीवी, कलर प्रिंटर, शोरूम ब्रांडिंग और 12 महीने का लीड सपोर्ट शामिल!\n\n' +
            'कृपया ऊपर दिए गए लिंक पर क्लिक करके पूरी जानकारी और आरओआई मॉडल देखें।';
        },
        ta: function(cName, url) {
          return 'வணக்கம் ' + cName + '! 🙏\n\n' +
            'MyntReal Hub (5-இன்-1 முதலீட்டு ஃபிரான்சைஸ்) அதிகாரப்பூர்வ டிஜிட்டல் கேட்லாக் லிங்க்:\n' +
            '👉 ' + url + '\n\n' +
            '🏢 ஒரே மையம் — 5 லாபகரமான வணிக வழிகள்:\n' +
            '• மாந்த்ரா இ-வாகன விற்பனை & உதிரிபாகங்கள் மையம்\n' +
            '• ஹர் கர் சோலார் கூரை மின் உற்பத்தி EPC (₹78,000 மானியம்)\n' +
            '• VGK கேர் விரிவான காப்பீட்டு ஆலோசனை (40+ நிறுவனங்கள்)\n' +
            '• VGK ரியல் ட்ரீம்ஸ் நிலம் & சொத்து விற்பனை\n' +
            '• EVolution தொழில்முறை இ-வாகன பயிற்சி மையம்\n\n' +
            '💼 முதலீடு: ₹12–15 லட்சம் | முதலீடு மீட்பு: 6–9 மாதங்கள் | ஆண்டு நிகர வருமானம்: ₹19.80 லட்சம்+\n' +
            '🎁 கணினி, 43" ஸ்மார்ட் டிவி, கலர் பிரிண்டர், பிராண்டிங் மற்றும் 12 மாத லீட் ஆதரவு முற்றிலும் இலவசம்!\n\n' +
            'முழு விவரங்களையும் நிதி மாதிரியையும் காண மேலே உள்ள இணைப்பைக் கிளிக் செய்க.';
        }
      }
    },
    customer_ev_pricing: {
      name: 'Customer 2W EV Pricing & Catalog',
      btnLabel: 'Customer EV',
      segmentSlug: 'customer-2w-ev-pricing',
      catalogSlug: 'customer-2w-ev-pricing',
      desc: 'Sends official retail Manthra EV 2-Wheeler catalog with customer on-road prices, battery specs (Graphene 9 Mo / LFP 3 Yrs), savings calculator & YouTube video.',
      messages: {
        te: function(cName, url) {
          return 'నమస్కారం ' + cName + ' గారు! 🙏\n\n' +
            'మాంత్రా EV (Manthra EV) అధికారిక 2-వీలర్ ఎలక్ట్రిక్ స్కూటర్లు & కస్టమర్ ధరల పట్టిక:\n' +
            '👉 ' + url + '\n\n' +
            '⚡ ప్రధాన ప్రయోజనాలు & 5 మోడల్స్:\n' +
            '• 5 మోడల్స్: Pro GT, Power Plus (హెవీ కార్గో), M99 Flagship, Royal Sling, Beast Pro\n' +
            '• నాన్-RTO లో-స్పీడ్ (<25 km/h) — డ్రైవింగ్ లైసెన్స్ & రిజిస్ట్రేషన్ అవసరం లేదు!\n' +
            '• రన్నింగ్ ఖర్చు కేవలం ₹0.15/కి.మీ — నెలకు ₹3,000+ పెట్రోల్ ఆదా\n' +
            '• గ్రాఫేన్ 48V 32Ah: 9 నెలల బ్యాటరీ & ఛార్జర్ వారంటీ\n' +
            '• స్మార్ట్ LFP బ్యాటరీలు: 2+1 సంవత్సరాల (3 ఏళ్ల) వారంటీ & 4–5 గంటల ఫాస్ట్ ఛార్జ్\n' +
            '• 3 సంవత్సరాల సమగ్ర వాహన వారంటీ & ఆథరైజ్డ్ సర్వీస్ నెట్‌వర్క్\n\n' +
            'పై లింక్ క్లిక్ చేసి మోడల్-వైజ్ ధరలు, స్పెసిఫికేషన్లు & అధికారిక వీడియో చూడగలరు. ఉచిత టెస్ట్ డ్రైవ్ బుక్ చేసుకోండి!';
        },
        en: function(cName, url) {
          return 'Namaskaram ' + cName + '! 🙏\n\n' +
            'Here is your official Manthra EV 2-Wheeler Electric Scooters Customer Pricing & Specifications Catalog:\n' +
            '👉 ' + url + '\n\n' +
            '⚡ Customer Highlights & 5 Certified Models:\n' +
            '• Models: Pro GT, Power Plus (Heavy Cargo), M99 Flagship, Royal Sling & Beast Pro\n' +
            '• Certified Non-RTO Low-Speed (<25 km/h) — Zero Driving License & Zero RTO Needed!\n' +
            '• Ultra-low running cost of ₹0.15 / km — Save ₹3,000+ every month vs petrol\n' +
            '• Graphene 48V 32Ah: 9 Months Battery Warranty & 9 Months Charger Warranty\n' +
            '• Smart LTM / LFP: 2+1 Years (3 Years) Battery Warranty & 4–5 Hrs Smart Fast Charge\n' +
            '• 3 Years Comprehensive Vehicle Warranty with local authorized spares & service\n\n' +
            'Click the link above to explore model-wise prices, interactive savings calculator & official video showcase. Book your free test ride today!';
        },
        hi: function(cName, url) {
          return 'नमस्ते ' + cName + ' जी! 🙏\n\n' +
            'मंत्रा EV (Manthra EV) आधिकारिक 2-व्हीलर इलेक्ट्रिक स्कूटर्स एवं कस्टमर प्राइसिंग कैटलॉग लिंक यहाँ देखें:\n' +
            '👉 ' + url + '\n\n' +
            '⚡ मुख्य विशेषताएं एवं 5 मॉडल:\n' +
            '• 5 मॉडल्स: Pro GT, Power Plus (कार्गो), M99 Flagship, Royal Sling और Beast Pro\n' +
            '• प्रमाणित नॉन-RTO (<25 km/h) — बिना ड्राइविंग लाइसेंस और बिना रजिस्ट्रेशन!\n' +
            '• मात्र ₹0.15 प्रति किमी खर्च — हर महीने ₹3,000+ पेट्रोल की बचत\n' +
            '• ग्रैफीन 48V 32Ah: 9 महीने की बैटरी एवं चार्जर वारंटी\n' +
            '• स्मार्ट LFP बैटरियां: 2+1 वर्ष (3 साल) वारंटी एवं 4–5 घंटे में फास्ट चार्ज\n' +
            '• 3 साल की व्यापक वाहन वारंटी एवं पूर्ण सर्विस सपोर्ट\n\n' +
            'कृपया ऊपर दिए गए लिंक पर क्लिक करके मॉडल-वाइज कीमतें और वीडियो देखें। आज ही फ्री टेस्ट ड्राइव बुक करें!';
        },
        ta: function(cName, url) {
          return 'வணக்கம் ' + cName + '! 🙏\n\n' +
            'மாந்த்ரா EV (Manthra EV) அதிகாரப்பூர்வ இருசக்கர மின்சார வாகனங்கள் மற்றும் வாடிக்கையாளர் விலை பட்டியல்:\n' +
            '👉 ' + url + '\n\n' +
            '⚡ வாடிக்கையாளர் சிறப்பம்சங்கள்:\n' +
            '• 5 சிறந்த மாடல்கள்: Pro GT, Power Plus, M99 Flagship, Royal Sling, Beast Pro\n' +
            '• நான்-RTO குறைந்த வேகம் (<25 km/h) — ஓட்டுநர் உரிமம் அல்லது பதிவு தேவையில்லை!\n' +
            '• கி.மீக்கு 15 பைசா மட்டுமே — மாதம் ₹3,000+ பெட்ரோல் செலவு மிச்சம்\n' +
            '• கிராபீன் 48V 32Ah: 9 மாதங்கள் பேட்டரி மற்றும் சார்ஜர் உத்தரவாதம்\n' +
            '• ஸ்மார்ட் LFP: 2+1 ஆண்டுகள் (3 ஆண்டுகள்) உத்தரவாதம் மற்றும் விரைவு சார்ஜிங்\n' +
            '• 3 ஆண்டுகள் முழுமையான வாகன உத்தரவாதம்\n\n' +
            'மேலே உள்ள இணைப்பைக் கிளிக் செய்து மாடல் விலைகளை அறிந்து இலவச டெஸ்ட் டிரைவ் முன்பதிவு செய்யுங்கள்!';
        }
      }
    },
    hub_pricing: {
      name: 'Hub Commercials & Pricing (24h)',
      btnLabel: 'Hub Pricing (24h)',
      segmentSlug: 'hub-pricing',
      catalogSlug: 'hub-ev-pricing',
      desc: 'Sends confidential MyntReal Hub EV & Solar Commercial Pricing catalog with wholesale costs, dealer margins & 24h auto-expiry security.',
      messages: {
        te: function(cName, url) {
          return 'నమస్కారం ' + cName + ' గారు! 🙏\n\n' +
            'MyntReal Hub — గోప్యమైన EV & సోలార్ కమర్షియల్ ప్రైసింగ్ & డీలర్ మార్జిన్స్ క్యాటలాగ్ లింక్ (24 గంటలు మాత్రమే చెల్లుబాటు):\n' +
            '👉 ' + url + '\n\n' +
            '⚡ కమర్షియల్ ప్రైసింగ్ & మార్జిన్ వివరాలు:\n' +
            '• 5 మోడల్స్ EV వాహనాల హోల్‌సేల్ ధరలు & 12% హబ్ మార్జిన్ (~₹7,200/వాహనం)\n' +
            '• డైరెక్ట్ కస్టమర్ సేల్స్ పై +10.5% అదనపు VGK4U కమిషన్ (మొత్తం 22.5% మార్జిన్)\n' +
            '• గ్రాఫేన్ & LFP బ్యాటరీలు మరియు ఫాస్ట్ ఛార్జర్ల విడి భాగాల ధరల పట్టిక\n' +
            '• సోలార్ EPC 1kW–10kW మాతృక: ₹1,99,999 సిస్టమ్‌పై ₹7,000 షోరూమ్ + ₹13,000 డైరెక్ట్ మార్జిన్\n' +
            '• 3-దశల యూనిట్ ఎకనామిక్స్ & లైవ్ డైరెక్ట్ సేల్స్ ROI సిమ్యులేటర్\n\n' +
            '⚠️ గమనిక: ఈ లింక్ కేవలం 24 గంటలు మాత్రమే యాక్టివ్‌గా ఉంటుంది.\n\n' +
            'పై లింక్ క్లిక్ చేసి పూర్తి హోల్‌సేల్ కాస్ట్ షీట్ & ROI వివరాలు వెంటనే చూడగలరు.';
        },
        en: function(cName, url) {
          return 'Namaskaram ' + cName + '! 🙏\n\n' +
            'Here is your Confidential MyntReal Hub — EV & Solar Commercial Pricing & Dealer Margins Prospectus (Strictly Valid for 24 Hours):\n' +
            '👉 ' + url + '\n\n' +
            '⚡ Commercial Highlights:\n' +
            '• OEM Wholesale Central Pricing & 12% Hub Dealer Margin (~₹7,200 avg/vehicle)\n' +
            '• Direct Customer Sale: +10.5% VGK4U Bonus (Total 22.5% combined spread)\n' +
            '• Standalone Graphene & LFP Batteries + Smart Fast Chargers Cost Matrix\n' +
            '• Solar EPC 1kW–10kW: ₹1,99,999 Flagship gives ₹7,000 Showroom + ₹13,000 Direct Margin\n' +
            '• 3-Scenario Financial Viability & Interactive Investor ROI Simulator\n\n' +
            '⚠️ Note: This confidential link expires automatically in 24 hours.\n\n' +
            'Click the link above to review wholesale cost sheets & calculate your net returns.';
        },
        hi: function(cName, url) {
          return 'नमस्ते ' + cName + ' जी! 🙏\n\n' +
            'MyntReal Hub — गोपनीय EV और सोलर कमर्शियल प्राइसिंग एवं डीलर मार्जिन कैटलॉग लिंक (केवल 24 घंटे मान्य):\n' +
            '👉 ' + url + '\n\n' +
            '⚡ मुख्य व्यावसायिक विवरण:\n' +
            '• 5 मॉडल्स EV वाहनों की थोक खरीद लागत और 12% हब डीलर मार्जिन\n' +
            '• डायरेक्ट सेल पर +10.5% अतिरिक्त VGK4U कमीशन (कुल 22.5% मार्जिन)\n' +
            '• ग्रैफीन एवं LFP बैटरियां और फास्ट चार्जर कंपोनेंट लागत सूची\n' +
            '• सोलर EPC 1kW–10kW: ₹1,99,999 प्लांट पर ₹7,000 शोरूम + ₹13,000 डायरेक्ट मार्जिन\n' +
            '• 3-सिनेरियो यूनिट इकोनॉमिक्स और लाइव ROI सिम्युलेटर\n\n' +
            '⚠️ ध्यान दें: यह लिंक केवल 24 घंटे के लिए सक्रिय है।\n\n' +
            'कृपया तुरंत ऊपर दिए गए लिंक पर क्लिक करके पूरी कॉस्ट शीट देखें।';
        },
        ta: function(cName, url) {
          return 'வணக்கம் ' + cName + '! 🙏\n\n' +
            'MyntReal Hub — ரகசியமான EV & சோலார் வணிக விலை & டீலர் மார்ஜின் கேட்லாக் லிங்க் (24 மணிநேரம் மட்டுமே செல்லுபடியாகும்):\n' +
            '👉 ' + url + '\n\n' +
            '⚡ வணிக சிறப்பம்சங்கள்:\n' +
            '• 5 மாடல் மின்சார வாகன மொத்த விலை & 12% ஹப் டீலர் மார்ஜின்\n' +
            '• நேரடி விற்பனையில் +10.5% கூடுதல் VGK4U கமிஷன் (மொத்தம் 22.5% லாபம்)\n' +
            '• கிராபீன் & LFP பேட்டரிகள் மற்றும் பாஸ்ட் சார்ஜர் உதிரிபாகங்கள் விலை பட்டியல்\n' +
            '• சோலார் EPC 1kW–10kW: ₹1,99,999 அமைப்பில் ₹7,000 ஷோரூம் + ₹13,000 நேரடி மார்ஜின்\n' +
            '• 3-நிலை நிதி சாத்தியக்கூறு ஆய்வு & நேரடி ROI கால்குலேட்டர்\n\n' +
            '⚠️ குறிப்பு: இந்த ரகசிய இணைப்பு 24 மணிநேரத்திற்கு மட்டுமே செல்லுபடியாகும்.\n\n' +
            'முழு விலை மற்றும் வருவாய் விவரங்களை அறிய மேலே உள்ள இணைப்பை கிளிக் செய்யவும்.';
        }
      }
    }
  };

  var _selectedCatalogKey  = 'solar';
  var _selectedCatalogLang = 'te';

  function _onCatalogSelect(catKey) {
    if (catKey && DIGITAL_CATALOGS[catKey]) {
      _selectedCatalogKey = catKey;
    }
    var cat = DIGITAL_CATALOGS[_selectedCatalogKey] || DIGITAL_CATALOGS.solar;
    var descEl = document.getElementById('_lwaCatDesc');
    if (descEl) descEl.textContent = cat.desc;
    var btnTextEl = document.getElementById('_lwaCatBtnText');
    if (btnTextEl) btnTextEl.textContent = 'Insert Personalized ' + (cat.btnLabel || cat.name) + ' Catalog Link';
  }

  function _getCatalogMessage(catKey, lang, customerName) {
    var cat = DIGITAL_CATALOGS[catKey] || DIGITAL_CATALOGS.solar;
    var cName = (customerName || 'Customer').trim();
    var origin = (typeof window !== 'undefined' && window.location && window.location.origin) ? window.location.origin : 'https://www.myntreal.com';
    var catalogUrl = origin + '/catalog/' + cat.segmentSlug + '/' + cat.catalogSlug + '?lang=' + encodeURIComponent(lang || 'te');
    if (catKey === 'hub_pricing' && !catalogUrl.includes('exp=')) {
      catalogUrl += '&exp=' + (Math.floor(Date.now() / 1000) + 86400);
    }

    var l = (lang || 'te').toLowerCase();
    var msgFn = (cat.messages && cat.messages[l]) ? cat.messages[l] : (cat.messages && cat.messages.en);
    if (typeof msgFn === 'function') {
      return msgFn(cName, catalogUrl);
    }
    return 'Namaskaram ' + cName + '! Here is your catalog link:\n👉 ' + catalogUrl;
  }

  function _applyCatalog(lang) {
    if (lang) {
      _selectedCatalogLang = lang;
      var pills = document.querySelectorAll('._lwaCatLang');
      pills.forEach(function(b) {
        var isThis = b.getAttribute('data-lang') === lang;
        b.style.background = isThis ? '#16a34a' : '#fff';
        b.style.color = isThis ? '#fff' : '#374151';
        b.style.borderColor = isThis ? '#16a34a' : '#d1d5db';
        b.style.fontWeight = isThis ? '700' : '600';
      });
    }
    var sel = document.getElementById('_lwaCatSel');
    if (sel && sel.value) {
      _selectedCatalogKey = sel.value;
    }
    var msg = _getCatalogMessage(_selectedCatalogKey, _selectedCatalogLang, _s.name);
    var sig = _getStaffSignature();
    var msgBox = document.getElementById('_lwaMsg');
    if (msgBox) {
      msgBox.value = msg + sig;
      msgBox.focus();
    }
  }

  /* ── Expose window functions (called from inline HTML) ───────────────────── */
  function _bindGlobals() {
    window._lwaClose           = function() { document.getElementById('_lwaModal').style.display = 'none'; };
    window._lwaMode            = function(m) { _s.mode = m; _applyModeStyle(); _loadTpls(); };
    window._lwaLoadTpls        = function() { _loadTpls(); };
    window._lwaTplChange       = function() { _onTplChange(); };
    window._lwaPreview         = function() { _buildPreview(); };
    window._lwaDoSend          = function() { _doSend(); };
    window._lwaDirectWeb       = function() { _directWeb(); };
    window._lwaCopyText        = function() { _copyText(); };
    window._lwaApplyQuick      = function(a) { _applyQuick(a); };
    window._lwaOnCatalogSelect = function(c) { _onCatalogSelect(c); };
    window._lwaApplyCatalog    = function(l) { _applyCatalog(l); };
    window._lwaToggleAddTpl    = function(s) { _toggleAddTpl(s); };
    window._lwaSaveNewTpl      = function() { _saveNewTpl(); };
    window._lwaFilterTpls      = function() { _filterTpls(); };
    window._lwaUnlockPhone = function() {
      var _inp = document.getElementById('_lwaPhoneInp');
      if (_inp) {
        _inp.readOnly = false;
        _inp.value = '';
        _inp.dataset.rawPhone = '';
        _inp.focus();
      }
      var _ebtn = document.getElementById('_lwaPhoneEditBtn');
      if (_ebtn) _ebtn.style.display = 'none';
    };
  }

  /* ── Public entry point ──────────────────────────────────────────────────── */
  window.openLeadWAModal = function(leadId, phone, name, companyId, initialMessage, context) {
    _ensure();
    _bindGlobals();
    var cleanP = phone ? String(phone).replace(/\D/g, '').slice(-10) : '';
    _s = { leadId: leadId, phone: cleanP, name: name, companyId: companyId, mode: 'scanned', tpls: [], bodyTpl: '', context: context || '' };

    /* reset UI */
    document.getElementById('_lwaSub').textContent     = (name || 'Contact') + (cleanP ? (' · ' + _maskPhone(cleanP)) : '');
    var _inp = document.getElementById('_lwaPhoneInp');
    var _ebtn = document.getElementById('_lwaPhoneEditBtn');
    if (_inp) {
      _inp.dataset.rawPhone = cleanP;
      _inp.value = cleanP ? _maskPhone(cleanP) : '';
      _inp.readOnly = !!cleanP;
    }
    if (_ebtn) {
      _ebtn.style.display = cleanP ? 'inline-block' : 'none';
    }

    /* Contextual catalog & segment auto-selection (always editable by user) */
    var initialSeg = '';
    var initialCatKey = 'solar';
    var ctxLower = (context || '').toLowerCase();
    if (ctxLower.indexOf('solar') !== -1 || companyId === 4 || companyId === '4') {
      initialSeg = 'solar';
      initialCatKey = 'solar';
    } else if (ctxLower.indexOf('real') !== -1 || ctxLower.indexOf('property') !== -1) {
      initialSeg = 'real_estate';
      initialCatKey = 'real_estate';
    } else if (ctxLower.indexOf('spare') !== -1) {
      initialSeg = 'EV_SPARES';
      initialCatKey = 'ev_spares';
    } else if (ctxLower.indexOf('cargo') !== -1 || ctxLower.indexOf('fleet') !== -1 || ctxLower.indexOf('b2b') !== -1) {
      initialSeg = 'ev_b2b';
      initialCatKey = 'ev_b2b';
    } else if (ctxLower.indexOf('ev') !== -1 || companyId === 2 || companyId === '2') {
      initialSeg = 'ev_b2c';
      initialCatKey = 'ev_b2c';
    } else if (ctxLower.indexOf('etc') !== -1 || ctxLower.indexOf('train') !== -1) {
      initialSeg = 'etc_training';
      initialCatKey = 'etc_training';
    } else if (ctxLower.indexOf('insur') !== -1) {
      initialCatKey = 'insurance';
    } else if (ctxLower.indexOf('pricing') !== -1 || ctxLower.indexOf('margin') !== -1 || ctxLower.indexOf('commercial') !== -1) {
      initialCatKey = 'hub_pricing';
    } else if (ctxLower.indexOf('hub') !== -1 || ctxLower.indexOf('franchise') !== -1) {
      initialCatKey = 'industrial_hub';
    }

    var segEl = document.getElementById('_lwaSeg');
    if (segEl) segEl.value = initialSeg;
    var searchEl = document.getElementById('_lwaTplSearch');
    if (searchEl) searchEl.value = '';
    _toggleAddTpl(false);

    var catSel = document.getElementById('_lwaCatSel');
    if (catSel) catSel.value = initialCatKey;
    _onCatalogSelect(initialCatKey);

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
