/**
 * CRM Handler Support Confirmation — Single Source of Truth
 * DC Protocol Apr 2026 (v2)
 *
 * ARCHITECTURE RULE:
 *   - This is the ONE place where confirmation-toggle logic lives.
 *   - All CRM lead pages use this module — never duplicate logic in page files.
 *   - To add a new handler type: add it to HC_CONFIG_STANDARD or HC_CONFIG_MASTER here ONLY.
 *   - Data always comes from the API lead object — never read from DOM elements directly.
 *
 * PUBLIC API:
 *   CRMHandlerConfirm.open(sectionId, rowsId, lead, handlerConfig)
 *     — Call once when a modal opens. Seeds state from API lead object.
 *   CRMHandlerConfirm.syncField(fieldName, id, name)
 *     — KEY FIX (Apr 2026): Call whenever a handler assignment changes INSIDE the
 *       open modal (guru auto-fill, telecaller selected, showroom cleared, etc.).
 *       Updates _lead immediately and re-renders — so the confirmation section always
 *       reflects the CURRENT form state, not the stale API snapshot from open().
 *   CRMHandlerConfirm.setVal(key, val)
 *     — Called by Yes/Pending/No buttons (auto-wired via onclick in rendered HTML).
 *   CRMHandlerConfirm.getValues()
 *     — Returns { guru_supported: bool|null, ... } — merge into save payload.
 *   CRMHandlerConfirm.getAssignment()
 *     — Returns { field_staff_id, associated_partner_id } if showroom was assigned
 *       inline from the confirmation section. Merge into save payload.
 *   CRMHandlerConfirm.loadAuditLog(leadId, containerId)
 *     — Fetches and renders the lead audit log into the given container element.
 *
 * HANDLER CONFIGS:
 *   Each entry: { key, idField, nameField, label [, idFieldFallback, nameFallbackField,
 *                  always_show, inline_search] }
 *   key              — DB boolean column name (e.g. 'guru_supported')
 *   idField          — lead field holding the handler's primary ID
 *   nameField        — lead field holding the handler's primary display name
 *   label            — UI prefix shown before the name
 *   idFieldFallback  — (opt) secondary ID field when primary is null
 *   nameFallbackField— (opt) secondary name field used when falling back
 *   always_show      — (opt) always show this row even if no handler assigned
 *   inline_search    — (opt) show inline partner/staff search when no handler assigned
 */

/* Handler Chain: Source=L1 manual, Senior=L2 auto, Extended=L3 auto, Core=L4 auto, Support=L5 manual.
 * DB column names: guru(L1), z_guru(L2), adi_guru(L3), core(L4) — unchanged for backward compat.
 * auto_fetch: true → person auto-populated from upliner chain; shows AUTO badge, no search UI,
 *   but Yes/Pending/No confirmation buttons remain active.
 */
window.HC_CONFIG_STANDARD = [
  { key: 'guru_supported',     idField: 'guru_id',     nameField: 'guru_name',     label: 'Source',   always_show: true },
  { key: 'z_guru_supported',   idField: 'z_guru_id',   nameField: 'z_guru_name',   label: 'Senior',   always_show: true,  auto_fetch: true },
  { key: 'adi_guru_supported', idField: 'adi_guru_id', nameField: 'adi_guru_name', label: 'Extended', always_show: true,  auto_fetch: true },
  { key: 'core_supported',     idField: 'core_id',     nameField: 'core_name',     label: 'Core',     always_show: false, auto_fetch: true },
  {
    key: 'showroom_supported', idField: 'field_staff_id', nameField: 'field_staff_name',
    idFieldFallback: 'associated_partner_id', nameFallbackField: 'associated_partner_name',
    label: 'Support', always_show: true, inline_search: true
  }
];

window.HC_CONFIG_MASTER = [
  { key: 'guru_supported',          idField: 'guru_id',              nameField: 'guru_name',              label: 'Source',       always_show: true },
  { key: 'z_guru_supported',        idField: 'z_guru_id',            nameField: 'z_guru_name',            label: 'Senior',       always_show: true,  auto_fetch: true },
  { key: 'adi_guru_supported',      idField: 'adi_guru_id',          nameField: 'adi_guru_name',          label: 'Extended',     always_show: true,  auto_fetch: true },
  { key: 'core_supported',          idField: 'core_id',              nameField: 'core_name',              label: 'Core',         always_show: true,  auto_fetch: true },
  { key: 'field_support_supported', idField: 'field_support_ref_id', nameField: 'field_support_ref_name', label: 'Field Support',always_show: true },
  { key: 'telecaller_supported',    idField: 'telecaller_id',        nameField: 'telecaller_name',        label: 'Telecaller',   always_show: true },
  {
    key: 'showroom_supported', idField: 'field_staff_id', nameField: 'field_staff_name',
    idFieldFallback: 'associated_partner_id', nameFallbackField: 'associated_partner_name',
    label: 'Support', always_show: true, inline_search: true
  },
  { key: 'technical_supported',     idField: 'technical_id',         nameField: 'technical_name',         label: 'Technical',    always_show: true }
];

/* HC_CONFIG_STAFF_UPGRADED — used in staff_leads.html (VGK5-level labels + Core row).
 * DC-HANDLER-CONFIRM-GATE-001
 */
window.HC_CONFIG_STAFF_UPGRADED = [
  { key: 'guru_supported',          idField: 'guru_id',              nameField: 'guru_name',              label: 'Source',       always_show: true },
  { key: 'z_guru_supported',        idField: 'z_guru_id',            nameField: 'z_guru_name',            label: 'Senior',       always_show: true,  auto_fetch: true },
  { key: 'adi_guru_supported',      idField: 'adi_guru_id',          nameField: 'adi_guru_name',          label: 'Extended',     always_show: true,  auto_fetch: true },
  { key: 'core_supported',          idField: 'core_id',              nameField: 'core_name',              label: 'Core',         always_show: true,  auto_fetch: true },
  { key: 'field_support_supported', idField: 'field_support_ref_id', nameField: 'field_support_ref_name', label: 'Field Support',always_show: true },
  { key: 'telecaller_supported',    idField: 'telecaller_id',        nameField: 'telecaller_name',        label: 'Telecaller',   always_show: true },
  {
    key: 'showroom_supported', idField: 'field_staff_id', nameField: 'field_staff_name',
    idFieldFallback: 'associated_partner_id', nameFallbackField: 'associated_partner_name',
    label: 'Support', always_show: true, inline_search: true
  }
];

/* HC_CONFIG_ETC — for ETC Training direct student modal (3 handler roles) */
window.HC_CONFIG_ETC = [
  { key: 'handler_confirmed',    idField: 'handler_emp_code',    nameField: 'handler_name',    label: 'Source / Handler', always_show: true },
  { key: 'telecaller_confirmed', idField: 'telecaller_emp_code', nameField: 'telecaller_name', label: 'Telecaller',       always_show: true },
  { key: 'field_staff_confirmed', idField: 'field_staff_emp_code', nameField: 'field_staff_name', label: 'Field Staff',   always_show: true },
];

window.CRMHandlerConfirm = (function () {
  var _sectionId    = '';
  var _rowsId       = '';
  var _lead         = null;
  var _config       = [];
  var _state        = {};
  var _newAssignment = null;
  var _searchTimer  = null;

  /* Map DB id-field → DB name-field for syncField() */
  var _NAME_FIELDS = {
    'guru_id':             'guru_name',
    'z_guru_id':           'z_guru_name',
    'adi_guru_id':         'adi_guru_name',
    'core_id':             'core_name',
    'telecaller_id':       'telecaller_name',
    'field_staff_id':      'field_staff_name',
    'associated_partner_id': 'associated_partner_name',
    'technical_id':        'technical_name',
    'field_support_ref_id': 'field_support_ref_name'
  };

  /* ── Public: open ───────────────────────────────────────────── */
  function open(sectionId, rowsId, lead, handlerConfig) {
    _sectionId     = sectionId;
    _rowsId        = rowsId;
    _lead          = lead ? Object.assign({}, lead) : {};
    _config        = handlerConfig || [];
    _state         = {};
    _newAssignment = null;
    _config.forEach(function (h) {
      _state[h.key] = (_lead[h.key] !== undefined && _lead[h.key] !== null)
        ? _lead[h.key]
        : null;
    });
    _render();
  }

  /* ── Public: syncField ─────────────────────────────────────────
   *  Call this whenever a handler assignment changes INSIDE the open modal.
   *  Examples:
   *    CRMHandlerConfirm.syncField('guru_id', d.data.guru.id, d.data.guru.name);
   *    CRMHandlerConfirm.syncField('telecaller_id', parseInt(id), name);
   *    CRMHandlerConfirm.syncField('field_staff_id', null, null);
   */
  function syncField(fieldName, id, name) {
    if (!_lead) return;
    _lead[fieldName] = id != null ? id : null;
    var nameField = _NAME_FIELDS[fieldName];
    if (nameField) _lead[nameField] = name || null;
    _render();
  }

  /* ── Public: setVal ────────────────────────────────────────── */
  function setVal(key, val) {
    _state[key] = val;
    _render();
  }

  /* ── Public: getValues ─────────────────────────────────────── */
  function getValues() {
    return Object.assign({}, _state);
  }

  /* ── Public: getAssignment ─────────────────────────────────── */
  function getAssignment() {
    if (!_newAssignment) return {};
    if (_newAssignment.type === 'staff') {
      return { field_staff_id: _newAssignment.id, associated_partner_id: null };
    }
    return { associated_partner_id: _newAssignment.id, field_staff_id: null };
  }

  /* ── Public: loadAuditLog ──────────────────────────────────── */
  function loadAuditLog(leadId, containerId) {
    var el = document.getElementById(containerId);
    if (!el || !leadId) return;
    var token = localStorage.getItem('staff_auth_token') || '';
    el.innerHTML = '<div style="font-size:11px;color:#9ca3af;padding:4px 0">Loading history\u2026</div>';
    fetch('/api/v1/crm/leads/' + leadId + '/audit-log?limit=30', {
      headers: { 'Authorization': 'Bearer ' + token }
    }).then(function (r) { return r.json(); })
    .then(function (data) {
      var entries = data.data || [];
      if (!entries.length) {
        el.innerHTML = '<div style="font-size:11px;color:#9ca3af;padding:4px 0">No changes recorded yet.</div>';
        return;
      }
      var catColors = { handler: '#2563eb', status: '#7c3aed', confirmation: '#059669', basic: '#d97706' };
      el.innerHTML = entries.map(function (e) {
        var when = '';
        try { when = e.changed_at ? new Date(e.changed_at).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : ''; } catch (_) {}
        var clr  = catColors[e.change_category] || '#6b7280';
        var fLbl = (e.field_name || '').replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
        var oldT = (e.old_value !== null && e.old_value !== undefined) ? String(e.old_value) : '\u2014';
        var newT = (e.new_value !== null && e.new_value !== undefined) ? String(e.new_value) : '\u2014';
        return '<div style="border-left:2px solid ' + clr + ';padding:4px 8px;margin-bottom:5px;background:#f9fafb;border-radius:0 4px 4px 0">'
          + '<div style="display:flex;justify-content:space-between;align-items:flex-start">'
          + '<div style="font-size:11px;font-weight:600;color:#1f2937">' + _esc(fLbl) + '</div>'
          + '<div style="font-size:10px;color:#6b7280;white-space:nowrap;margin-left:8px">' + _esc(when) + '</div>'
          + '</div>'
          + '<div style="font-size:11px;margin-top:2px">'
          + (e.old_value !== null && e.old_value !== undefined ? '<span style="color:#dc2626;text-decoration:line-through;margin-right:4px">' + _esc(oldT) + '</span>' : '')
          + '<span style="color:#6b7280">\u2192</span> <span style="color:#059669">' + _esc(newT) + '</span>'
          + '</div>'
          + '<div style="font-size:10px;color:#6b7280;margin-top:2px">by ' + _esc(e.changed_by_name || e.changed_by_id || 'Unknown') + ' (' + _esc(e.changed_by_type || '') + ')</div>'
          + '</div>';
      }).join('');
    })
    .catch(function () {
      if (el) el.innerHTML = '<div style="font-size:11px;color:#ef4444;padding:4px 0">Could not load history.</div>';
    });
  }

  /* ── Private: _inlineSearch ────────────────────────────────── */
  function _inlineSearch(q) {
    clearTimeout(_searchTimer);
    var el = document.getElementById('ef_hc_inline_results');
    if (!el) return;
    if (!q || q.length < 2) { el.style.display = 'none'; return; }
    _searchTimer = setTimeout(function () {
      var token = localStorage.getItem('staff_auth_token') || '';
      fetch('/api/v1/crm/network-search?q=' + encodeURIComponent(q), {
        headers: { 'Authorization': 'Bearer ' + token }
      }).then(function (r) { return r.json(); })
      .then(function (data) {
        var results = (data.results || data.data || []).filter(function (r) {
          return r.type === 'partner' || r.type === 'staff';
        });
        if (!el) return;
        if (!results.length) {
          el.innerHTML = '<div style="padding:6px 10px;font-size:11px;color:#6b7280">No results</div>';
          el.style.display = '';
          return;
        }
        el.innerHTML = results.slice(0, 8).map(function (r) {
          var badge = r.type === 'partner'
            ? '<span style="background:#059669;color:#fff;font-size:9px;padding:1px 4px;border-radius:3px;margin-right:4px">PARTNER</span>'
            : '<span style="background:#0891b2;color:#fff;font-size:9px;padding:1px 4px;border-radius:3px;margin-right:4px">STAFF</span>';
          var safeName = (r.name || r.display || '').replace(/\\/g, '\\\\').replace(/'/g, '\\\'');
          return '<div style="padding:5px 10px;font-size:11px;cursor:pointer;border-bottom:1px solid #f3f4f6;hover:background:#f9fafb" '
            + 'onmousedown="CRMHandlerConfirm._inlineSelect(\'' + r.type + '\',' + JSON.stringify(r.id) + ',\'' + safeName + '\')">'
            + badge + _esc(r.name || r.display || String(r.id)) + '</div>';
        }).join('');
        el.style.display = '';
      })
      .catch(function () { if (el) el.style.display = 'none'; });
    }, 300);
  }

  /* ── Private: _inlineSelect ────────────────────────────────── */
  function _inlineSelect(type, id, name) {
    _newAssignment = { type: type, id: id, name: name };
    if (type === 'staff') {
      _lead.field_staff_id          = id;
      _lead.field_staff_name        = name;
      _lead.associated_partner_id   = null;
      _lead.associated_partner_name = null;
    } else {
      _lead.associated_partner_id   = id;
      _lead.associated_partner_name = name;
      _lead.field_staff_id          = null;
      _lead.field_staff_name        = null;
    }
    var showroomIdEl   = document.getElementById('ef_showroom_id');
    var showroomTypeEl = document.getElementById('ef_showroom_type');
    if (showroomIdEl)   showroomIdEl.value   = id;
    if (showroomTypeEl) showroomTypeEl.value = type;
    if (typeof efRenderSelected === 'function') efRenderSelected('showroom', type, id, name);
    _render();
  }

  /* ── Private: _render ──────────────────────────────────────── */
  function _render() {
    var section   = document.getElementById(_sectionId);
    var container = document.getElementById(_rowsId);
    if (!section || !container) return;

    var rows = [];
    _config.forEach(function (h) {
      var id   = _lead[h.idField];
      var name = _lead[h.nameField];
      if (!id && h.idFieldFallback) {
        id   = _lead[h.idFieldFallback];
        name = _lead[h.nameFallbackField] || name;
      }
      if (id || h.always_show) {
        rows.push({ key: h.key, label: h.label, name: name, id: id, h: h,
                    searchable: !id && !!h.always_show && !!h.inline_search });
      }
    });

    if (rows.length === 0) {
      section.style.display = 'none';
      return;
    }

    section.style.display = '';
    container.innerHTML = rows.map(function (r) {
      if (r.searchable && r.h.inline_search) {
        return _renderSearchRow(r);
      }
      return _renderToggleRow(r);
    }).join('');
  }

  function _renderSearchRow(r) {
    return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap">'
      + '<span style="font-size:12px;color:#374151;min-width:120px;font-weight:500">' + _esc(r.h.label) + ':</span>'
      + '<div style="position:relative;flex:1;min-width:180px">'
      + '<input type="text" id="ef_hc_inline_search" placeholder="Search partner or staff\u2026" '
      + 'oninput="CRMHandlerConfirm._inlineSearch(this.value)" '
      + 'style="font-size:11px;height:28px;width:100%;border:1px solid #d1d5db;border-radius:4px;padding:0 8px;outline:none">'
      + '<div id="ef_hc_inline_results" style="position:absolute;top:100%;left:0;width:100%;z-index:1080;background:white;'
      + 'border:1px solid #e5e7eb;border-radius:4px;max-height:130px;overflow-y:auto;display:none;box-shadow:0 4px 12px rgba(0,0,0,.08)"></div>'
      + '</div>'
      + '<span style="font-size:10px;color:#9ca3af;font-style:italic">Not assigned</span>'
      + '</div>';
  }

  function _renderToggleRow(r) {
    var v         = _state[r.key];
    var isYes     = v === true;
    var isPend    = (v === null || v === undefined);
    var isNo      = v === false;
    var handlerTxt = r.name || r.id || '';
    var autoBadge = r.h.auto_fetch
      ? '<span style="background:#0284c7;color:#fff;font-size:9px;padding:1px 5px;border-radius:3px;margin-left:4px;vertical-align:middle">AUTO</span>'
      : '';
    var nameHtml  = handlerTxt
      ? (_esc(handlerTxt) + autoBadge)
      : (r.h.auto_fetch
          ? '<span style="color:#9ca3af;font-style:italic;font-weight:400">Auto — not resolved</span>'
          : '<span style="color:#9ca3af;font-style:italic;font-weight:400">Not assigned</span>');
    var label = r.h.label + ': ';
    return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap">'
      + '<span style="font-size:12px;color:#374151;min-width:210px;font-weight:500">' + _esc(label) + nameHtml + '</span>'
      + '<div class="btn-group btn-group-sm">'
      + '<button type="button" class="btn ' + (isYes ? 'btn-success' : 'btn-outline-success') + '" onclick="CRMHandlerConfirm.setVal(\'' + r.key + '\',true)"><i class="fas fa-check me-1"></i>Yes</button>'
      + '<button type="button" class="btn ' + (isPend ? 'btn-secondary' : 'btn-outline-secondary') + '" onclick="CRMHandlerConfirm.setVal(\'' + r.key + '\',null)">Pending</button>'
      + '<button type="button" class="btn ' + (isNo ? 'btn-danger' : 'btn-outline-danger') + '" onclick="CRMHandlerConfirm.setVal(\'' + r.key + '\',false)"><i class="fas fa-times me-1"></i>No</button>'
      + '</div></div>';
  }

  function _esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  return {
    open:          open,
    syncField:     syncField,
    setVal:        setVal,
    getValues:     getValues,
    getAssignment: getAssignment,
    loadAuditLog:  loadAuditLog,
    _inlineSearch: _inlineSearch,
    _inlineSelect: _inlineSelect
  };
})();
