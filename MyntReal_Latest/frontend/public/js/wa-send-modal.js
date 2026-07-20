/**
 * DC-WA-TRACK-001: Shared WhatsApp Send Modal
 * Provides a reusable sendViaWA(leadId, phone, name, segment) function.
 * Uses only Meta-APPROVED templates from /api/v1/whatsapp-config/templates/approved.
 * Logs sends to crm_wa_sends via /api/v1/whatsapp-config/crm-lead-send/{lead_id}.
 */
(function () {
  'use strict';

  // ── Inject modal HTML once ─────────────────────────────────────────────────
  function ensureModalDOM() {
    if (document.getElementById('dcWaSendModal')) return;
    const el = document.createElement('div');
    el.innerHTML = `
<div id="dcWaSendModal" style="display:none;position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.55);
  align-items:center;justify-content:center;padding:16px">
  <div style="background:#fff;border-radius:14px;width:100%;max-width:560px;max-height:92vh;overflow-y:auto;
    box-shadow:0 20px 60px rgba(0,0,0,0.25);padding:0">

    <!-- Header -->
    <div style="display:flex;align-items:center;justify-content:space-between;padding:18px 20px 14px;
      border-bottom:1.5px solid #e5e7eb;position:sticky;top:0;background:#fff;z-index:2">
      <div>
        <div style="font-size:15px;font-weight:700;color:#111827;display:flex;align-items:center;gap:8px">
          <i class="fab fa-whatsapp" style="color:#25d366;font-size:18px"></i>
          Send WhatsApp
        </div>
        <div style="font-size:12px;color:#6b7280;margin-top:2px">
          To: <strong id="dcWaModalName">—</strong>
          &nbsp;·&nbsp;
          <span id="dcWaModalPhone">—</span>
        </div>
      </div>
      <button onclick="closeWaSendModal()"
        style="background:#f3f4f6;border:none;border-radius:7px;width:32px;height:32px;font-size:16px;
        cursor:pointer;color:#374151;display:flex;align-items:center;justify-content:center">
        ✕
      </button>
    </div>

    <!-- Body -->
    <div style="padding:18px 20px">

      <!-- Segment filter -->
      <div style="display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap;align-items:center">
        <span style="font-size:12px;color:#6b7280;white-space:nowrap">Filter:</span>
        <select id="dcWaSegFilter" onchange="dcWaLoadTemplates()"
          style="flex:1;min-width:140px;padding:6px 9px;border:1.5px solid #d1d5db;border-radius:7px;font-size:12px;color:#374151">
          <option value="">All segments</option>
          <option value="general">MNR General</option>
          <option value="solar">Solar</option>
          <option value="myntreal_real">Myntreal Real</option>
          <option value="ev_b2b">EV B2B</option>
          <option value="ev_b2c">EV B2C</option>
          <option value="etc_training">ETC Training</option>
          <option value="real_estate">Real Estate</option>
          <option value="vgk">VGK Members</option>
          <option value="system">System</option>
        </select>
        <select id="dcWaCatFilter" onchange="dcWaLoadTemplates()"
          style="padding:6px 9px;border:1.5px solid #d1d5db;border-radius:7px;font-size:12px;color:#374151">
          <option value="">All categories</option>
          <option value="MARKETING">Marketing</option>
          <option value="UTILITY">Utility</option>
        </select>
      </div>

      <!-- Template picker -->
      <div style="margin-bottom:14px">
        <label style="font-size:12px;font-weight:600;color:#374151;display:block;margin-bottom:5px">
          Template <span style="color:#9ca3af;font-weight:400">(Meta-approved)</span>
        </label>
        <select id="dcWaTemplateSelect" onchange="dcWaOnTemplateChange()"
          style="width:100%;padding:8px 10px;border:1.5px solid #d1d5db;border-radius:8px;font-size:13px;
          color:#374151;background:#fff">
          <option value="">— Loading templates… —</option>
        </select>
      </div>

      <!-- Preview panel -->
      <div id="dcWaPreview" style="display:none;background:#f0fdf4;border:1.5px solid #86efac;border-radius:10px;
        padding:12px 14px;margin-bottom:14px;font-size:13px;color:#166534;white-space:pre-wrap;
        word-break:break-word;line-height:1.5"></div>

      <!-- Context vars (auto-filled) -->
      <div id="dcWaVarsSection" style="display:none;margin-bottom:14px">
        <label style="font-size:12px;font-weight:600;color:#374151;display:block;margin-bottom:6px">
          <i class="fas fa-magic me-1" style="color:#7c3aed"></i> Fill in variables
        </label>
        <div id="dcWaVarsGrid" style="display:flex;flex-direction:column;gap:6px"></div>
      </div>

      <!-- Custom message override -->
      <div style="margin-bottom:14px">
        <label style="font-size:12px;font-weight:600;color:#374151;display:block;margin-bottom:5px">
          Message <span style="color:#9ca3af;font-weight:400">(auto-filled from template, or write custom)</span>
        </label>
        <textarea id="dcWaMessage" rows="5"
          style="width:100%;padding:9px 11px;border:1.5px solid #d1d5db;border-radius:8px;font-size:13px;
          color:#374151;resize:vertical;box-sizing:border-box"
          placeholder="Select a template above, or type a custom message…"></textarea>
      </div>

      <!-- Result banner -->
      <div id="dcWaResult" style="display:none;padding:10px 13px;border-radius:8px;font-size:13px;margin-bottom:10px"></div>

      <!-- Footer actions -->
      <div style="display:flex;gap:10px;justify-content:flex-end;align-items:center">
        <button onclick="closeWaSendModal()"
          style="padding:9px 18px;font-size:13px;border:1.5px solid #d1d5db;background:#fff;
          color:#374151;border-radius:8px;cursor:pointer">
          Cancel
        </button>
        <button id="dcWaSendBtn" onclick="dcWaDoSend()"
          style="padding:9px 22px;font-size:13px;background:#25d366;color:#fff;border:none;
          border-radius:8px;cursor:pointer;display:flex;align-items:center;gap:7px;font-weight:600">
          <i class="fab fa-whatsapp"></i> Send
        </button>
      </div>
    </div>
  </div>
</div>`;
    document.body.appendChild(el);
  }

  // ── State ──────────────────────────────────────────────────────────────────
  let _waState = { leadId: null, phone: null, name: null, segment: null };
  let _waTemplates = [];

  // ── Public API ─────────────────────────────────────────────────────────────
  window.sendViaWA = function (leadId, phone, name, segment) {
    ensureModalDOM();
    _waState = { leadId, phone, name, segment: segment || '' };
    document.getElementById('dcWaModalName').textContent = name || phone;
    document.getElementById('dcWaModalPhone').textContent = phone;
    document.getElementById('dcWaResult').style.display = 'none';
    document.getElementById('dcWaMessage').value = '';
    document.getElementById('dcWaPreview').style.display = 'none';
    document.getElementById('dcWaPreview').textContent = '';
    document.getElementById('dcWaVarsSection').style.display = 'none';
    document.getElementById('dcWaVarsGrid').innerHTML = '';
    // Pre-set segment filter if provided
    const segSel = document.getElementById('dcWaSegFilter');
    if (segSel) segSel.value = segment || '';
    document.getElementById('dcWaCatFilter').value = '';
    document.getElementById('dcWaSendBtn').disabled = false;
    document.getElementById('dcWaSendBtn').innerHTML = '<i class="fab fa-whatsapp"></i> Send';
    document.getElementById('dcWaSendModal').style.display = 'flex';
    dcWaLoadTemplates();
  };

  window.closeWaSendModal = function () {
    const m = document.getElementById('dcWaSendModal');
    if (m) m.style.display = 'none';
  };

  // ── Load approved templates ────────────────────────────────────────────────
  window.dcWaLoadTemplates = async function () {
    const seg = (document.getElementById('dcWaSegFilter')?.value || '').trim();
    const cat = (document.getElementById('dcWaCatFilter')?.value || '').trim();
    const sel = document.getElementById('dcWaTemplateSelect');
    sel.innerHTML = '<option value="">— Loading… —</option>';
    document.getElementById('dcWaPreview').style.display = 'none';
    document.getElementById('dcWaVarsSection').style.display = 'none';
    document.getElementById('dcWaVarsGrid').innerHTML = '';
    try {
      let url = '/api/v1/whatsapp-config/templates/approved';
      const params = [];
      if (seg) params.push(`segment=${encodeURIComponent(seg)}`);
      if (cat) params.push(`category=${encodeURIComponent(cat)}`);
      if (params.length) url += '?' + params.join('&');
      const fetchFn = typeof staffFetch === 'function' ? staffFetch : fetch;
      const r = await fetchFn(url);
      const d = await r.json();
      _waTemplates = d.templates || [];
      sel.innerHTML = '<option value="">— Choose a template —</option>';
      if (_waTemplates.length === 0) {
        sel.innerHTML += '<option disabled>No approved templates found</option>';
      }
      const bySegment = {};
      _waTemplates.forEach(t => {
        if (!bySegment[t.segment]) bySegment[t.segment] = [];
        bySegment[t.segment].push(t);
      });
      const segLabels = {
        ev_b2b: 'EV B2B', ev_b2c: 'EV B2C', etc_training: 'ETC Training',
        real_estate: 'Real Estate', general: 'MNR General',
        vgk: 'VGK Members', system: 'System',
        solar: 'Solar', myntreal_real: 'Myntreal Real'
      };
      Object.entries(bySegment).forEach(([s, tmps]) => {
        const grp = document.createElement('optgroup');
        grp.label = segLabels[s] || s;
        tmps.forEach(t => {
          const opt = document.createElement('option');
          opt.value = t.id;
          opt.textContent = t.name + (t.meta_category ? ` [${t.meta_category}]` : '');
          opt.dataset.body = t.body_text || '';
          opt.dataset.name = t.name;
          grp.appendChild(opt);
        });
        sel.appendChild(grp);
      });
      sel.innerHTML = '<option value="">— Choose an approved template —</option>' + sel.innerHTML.replace('<option value="">— Choose an approved template —</option>', '');
    } catch (e) {
      console.error('[dcWaSendModal] template load error:', e);
      sel.innerHTML = '<option value="">— Error loading templates —</option>';
    }
  };

  // ── Template change: show preview + variable inputs ────────────────────────
  window.dcWaOnTemplateChange = function () {
    const sel = document.getElementById('dcWaTemplateSelect');
    const opt = sel.options[sel.selectedIndex];
    const preview = document.getElementById('dcWaPreview');
    const varsSection = document.getElementById('dcWaVarsSection');
    const varsGrid = document.getElementById('dcWaVarsGrid');
    const msgArea = document.getElementById('dcWaMessage');

    if (!opt || !opt.value) {
      preview.style.display = 'none';
      varsSection.style.display = 'none';
      varsGrid.innerHTML = '';
      return;
    }

    const body = opt.dataset.body || '';
    msgArea.value = body;

    // Detect positional variables {{1}}, {{2}}, …
    const varMatches = [...new Set((body.match(/\{\{\d+\}\}/g) || []))];
    varsGrid.innerHTML = '';
    if (varMatches.length > 0) {
      varsSection.style.display = '';
      varMatches.forEach(v => {
        const num = v.replace(/\{\{|\}\}/g, '');
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;align-items:center;gap:8px';
        row.innerHTML = `
          <span style="font-size:12px;font-weight:600;color:#7c3aed;min-width:32px">${v}</span>
          <input type="text" data-var="${v}"
            placeholder="Value for ${v}"
            style="flex:1;padding:6px 9px;border:1.5px solid #d1d5db;border-radius:7px;font-size:12px"
            oninput="dcWaUpdatePreview()">`;
        varsGrid.appendChild(row);
      });
      // Pre-fill {{1}} with lead name if available
      const firstInput = varsGrid.querySelector('input[data-var="{{1}}"]');
      if (firstInput && _waState.name) {
        firstInput.value = _waState.name;
        dcWaUpdatePreview();
        return;
      }
    } else {
      varsSection.style.display = 'none';
    }

    // Show preview
    preview.textContent = body;
    preview.style.display = '';
  };

  // ── Update preview with variable substitution ─────────────────────────────
  window.dcWaUpdatePreview = function () {
    const sel = document.getElementById('dcWaTemplateSelect');
    const opt = sel.options[sel.selectedIndex];
    if (!opt || !opt.value) return;
    let body = opt.dataset.body || '';
    const inputs = document.querySelectorAll('#dcWaVarsGrid input[data-var]');
    inputs.forEach(inp => {
      body = body.replaceAll(inp.dataset.var, inp.value || inp.dataset.var);
    });
    document.getElementById('dcWaPreview').textContent = body;
    document.getElementById('dcWaPreview').style.display = '';
    document.getElementById('dcWaMessage').value = body;
  };

  // ── Send ───────────────────────────────────────────────────────────────────
  window.dcWaDoSend = async function () {
    const msg = (document.getElementById('dcWaMessage')?.value || '').trim();
    const tplId = document.getElementById('dcWaTemplateSelect')?.value || null;
    const res = document.getElementById('dcWaResult');
    const btn = document.getElementById('dcWaSendBtn');

    if (!msg) {
      res.style.cssText = 'display:block;background:#fef2f2;border:1.5px solid #fca5a5;border-radius:8px;color:#991b1b;padding:10px 13px;font-size:13px;margin-bottom:10px';
      res.textContent = 'Please select a template or write a message.';
      return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending…';
    res.style.display = 'none';

    try {
      const fetchFn = typeof staffFetch === 'function' ? staffFetch : fetch;
      const r = await fetchFn(
        `/api/v1/whatsapp-config/crm-lead-send/${_waState.leadId}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            phone: _waState.phone,
            custom_message: msg,
            template_id: tplId ? parseInt(tplId) : null,
            send_method: 'crm_modal',
          }),
        }
      );
      const d = await r.json();
      if (d.success) {
        res.style.cssText = 'display:block;background:#f0fdf4;border:1.5px solid #86efac;border-radius:8px;color:#166534;padding:10px 13px;font-size:13px;margin-bottom:10px';
        res.innerHTML = '<i class="fas fa-check-circle me-1"></i> Message sent successfully!';
        btn.innerHTML = '<i class="fas fa-check"></i> Sent';
        setTimeout(() => closeWaSendModal(), 1800);
        // Notify host page if it defined a success callback
        if (typeof window.onWaSendSuccess === 'function') {
          window.onWaSendSuccess({ leadId: _waState.leadId, phone: _waState.phone, wamid: d.wamid });
        }
      } else {
        res.style.cssText = 'display:block;background:#fef2f2;border:1.5px solid #fca5a5;border-radius:8px;color:#991b1b;padding:10px 13px;font-size:13px;margin-bottom:10px';
        res.textContent = d.reason || 'Send failed. Please try again.';
        btn.disabled = false;
        btn.innerHTML = '<i class="fab fa-whatsapp"></i> Retry';
      }
    } catch (e) {
      console.error('[dcWaSendModal] send error:', e);
      res.style.cssText = 'display:block;background:#fef2f2;border:1.5px solid #fca5a5;border-radius:8px;color:#991b1b;padding:10px 13px;font-size:13px;margin-bottom:10px';
      res.textContent = 'Network error. Please try again.';
      btn.disabled = false;
      btn.innerHTML = '<i class="fab fa-whatsapp"></i> Retry';
    }
  };

  // Close on backdrop click
  document.addEventListener('click', function (e) {
    const modal = document.getElementById('dcWaSendModal');
    if (modal && e.target === modal) closeWaSendModal();
  });
})();
