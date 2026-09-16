/**
 * share-lead-modal.js — DC Protocol: Universal Share Lead Modal for Web CRM
 * Parity with Mobile UnifiedShareLeadModal.ts
 * 
 * Used by: staff_leads.html, staff_dialer.html, staff_team_leads.html,
 *          staff_crm_team_leads.html, crm_lead_editor.js
 *
 * Entry point: window.openShareLeadModal({ leadId, name, phone, alternatePhone, category, area, city, requirements, notes, companyId, onShared })
 * Uses native fetch() with credentials='include'.
 */
(function () {
  'use strict';

  var API_BASE = '/api/v1/crm';
  var _staffList = [];
  var _isLoadingStaff = false;
  var _currentLead = null;

  var MODAL_HTML = [
    '<div id="_slmModal" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.75);z-index:1000000;align-items:center;justify-content:center;padding:16px;box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif">',
    '<div style="background:#0f172a;color:#f8fafc;border:1px solid rgba(255,255,255,0.12);border-radius:18px;width:100%;max-width:520px;max-height:92vh;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 24px 80px rgba(0,0,0,.6)">',

    /* Header */
    '<div style="background:linear-gradient(135deg,#0284c7 0%,#0369a1 100%);color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center">',
    '<div style="display:flex;align-items:center;gap:10px">',
    '<div style="background:rgba(255,255,255,0.2);width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px">📤</div>',
    '<div>',
    '<div style="font-weight:800;font-size:15px;line-height:1.2">Share Lead Details</div>',
    '<div id="_slmSubtitle" style="font-size:11.5px;color:rgba(255,255,255,0.85);margin-top:2px"></div>',
    '</div>',
    '</div>',
    '<button onclick="window.closeShareLeadModal()" style="background:rgba(255,255,255,0.2);border:none;color:#fff;width:30px;height:30px;border-radius:8px;font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center;line-height:1">&times;</button>',
    '</div>',

    /* Body */
    '<div style="padding:16px 18px;overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:12px">',

    /* Lead preview card */
    '<div style="background:#1e293b;border:1px solid #334155;border-radius:12px;padding:12px 14px;font-size:12px;line-height:1.5">',
    '<div style="display:flex;justify-content:space-between;margin-bottom:3px"><span style="color:#94a3b8">Lead ID:</span><span id="_slmLeadId" style="font-weight:700;color:#38bdf8">#—</span></div>',
    '<div id="_slmCatRow" style="display:flex;justify-content:space-between;margin-bottom:3px"><span style="color:#94a3b8">Category:</span><span id="_slmCategory" style="font-weight:600;color:#cbd5e1">—</span></div>',
    '<div id="_slmLocRow" style="display:flex;justify-content:space-between;margin-bottom:3px"><span style="color:#94a3b8">Location:</span><span id="_slmLocation" style="font-weight:600;color:#cbd5e1">—</span></div>',
    '<div id="_slmReqRow" style="margin-top:6px;padding-top:6px;border-top:1px dashed #334155;color:#e2e8f0"><b style="color:#94a3b8">Needs:</b> <span id="_slmRequirements">—</span></div>',
    '</div>',

    /* Staff Selector */
    '<div>',
    '<label style="display:block;font-size:11.5px;font-weight:700;color:#94a3b8;margin-bottom:5px;text-transform:uppercase;letter-spacing:.5px">Select Staff Member for Follow-Up <span style="color:#ef4444">*</span></label>',
    '<select id="_slmStaffSelect" onchange="window._slmUpdatePreview()" style="width:100%;background:#1e293b;border:1px solid #334155;border-radius:10px;color:#f8fafc;padding:9px 12px;font-size:13px;box-sizing:border-box;cursor:pointer">',
    '<option value="">— Loading staff members… —</option>',
    '</select>',
    '</div>',

    /* Followup Purpose */
    '<div>',
    '<label style="display:block;font-size:11.5px;font-weight:700;color:#94a3b8;margin-bottom:5px;text-transform:uppercase;letter-spacing:.5px">Follow-Up Purpose / Reason</label>',
    '<select id="_slmPurpose" onchange="window._slmUpdatePreview()" style="width:100%;background:#1e293b;border:1px solid #334155;border-radius:10px;color:#f8fafc;padding:9px 12px;font-size:13px;box-sizing:border-box;cursor:pointer">',
    '<option value="secondary_followup" selected>🔄 Secondary Follow-Up Call</option>',
    '<option value="site_visit">📍 Site Visit / Field Inspection</option>',
    '<option value="quotation">📑 Quotation &amp; Pricing Discussion</option>',
    '<option value="technical">⚡ Technical / Rooftop Feasibility</option>',
    '<option value="escalation">⚠️ Senior Escalation / Special Handling</option>',
    '<option value="general">💼 General Lead Follow-Up</option>',
    '</select>',
    '</div>',

    /* Instructions/Notes */
    '<div>',
    '<label style="display:block;font-size:11.5px;font-weight:700;color:#94a3b8;margin-bottom:5px;text-transform:uppercase;letter-spacing:.5px">Instructions / Notes for Staff</label>',
    '<textarea id="_slmNotes" oninput="window._slmUpdatePreview()" rows="2" placeholder="e.g., Customer is interested in 5kW On-grid solar. Please coordinate and visit tomorrow." style="width:100%;background:#1e293b;border:1px solid #334155;border-radius:10px;color:#f8fafc;padding:9px 12px;font-size:13px;box-sizing:border-box;resize:none"></textarea>',
    '</div>',

    /* CRM Assignment Checkbox */
    '<div style="display:flex;align-items:center;gap:8px;background:#1e293b;padding:10px 12px;border-radius:10px;border:1px solid #334155">',
    '<input type="checkbox" id="_slmAssignCheck" checked style="width:18px;height:18px;accent-color:#0ea5e9;cursor:pointer">',
    '<label for="_slmAssignCheck" style="font-size:12.5px;color:#e2e8f0;cursor:pointer;font-weight:600;margin:0">',
    'Assign as Secondary Follow-up in CRM',
    '<div style="font-size:10.5px;color:#94a3b8;font-weight:400">Lead will appear in colleague\'s CRM &amp; task queue</div>',
    '</label>',
    '</div>',

    /* Message Preview */
    '<div style="background:#0b1329;border:1px solid #1e293b;border-radius:10px;padding:9px 11px">',
    '<div style="font-size:10.5px;font-weight:700;color:#64748b;margin-bottom:4px;text-transform:uppercase">WhatsApp Message Preview:</div>',
    '<div id="_slmMessagePreview" style="font-size:11px;color:#94a3b8;white-space:pre-wrap;max-height:75px;overflow-y:auto;font-family:monospace;line-height:1.4">Select a staff member to preview message...</div>',
    '</div>',

    /* Feedback Alert Box */
    '<div id="_slmAlert" style="display:none;padding:8px 12px;border-radius:8px;font-size:12px"></div>',

    '</div>',

    /* Footer Actions */
    '<div style="padding:12px 18px;border-top:1px solid rgba(255,255,255,0.08);background:#0b1329;display:flex;flex-direction:column;gap:8px">',
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">',
    '<button type="button" id="_slmWaOnlyBtn" onclick="window._slmExecute(\'wa_only\')" style="background:#25D366;color:#fff;border:none;border-radius:10px;padding:11px;font-size:12.5px;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px">💬 WhatsApp Only</button>',
    '<button type="button" id="_slmCrmOnlyBtn" onclick="window._slmExecute(\'crm_only\')" style="background:#334155;color:#f8fafc;border:none;border-radius:10px;padding:11px;font-size:12.5px;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px">📋 Assign in CRM</button>',
    '</div>',
    '<button type="button" id="_slmCombinedBtn" onclick="window._slmExecute(\'combined\')" style="background:linear-gradient(135deg,#0ea5e9 0%,#0284c7 100%);color:#fff;border:none;border-radius:10px;padding:12px;font-size:13.5px;font-weight:700;cursor:pointer;box-shadow:0 4px 14px rgba(14,165,233,0.4);display:flex;align-items:center;justify-content:center;gap:8px">🚀 Assign &amp; WhatsApp Colleague</button>',
    '</div>',

    '</div></div>'
  ].join('');

  function _ensureModal() {
    if (document.getElementById('_slmModal')) return;
    var wrap = document.createElement('div');
    wrap.innerHTML = MODAL_HTML;
    document.body.appendChild(wrap.firstElementChild);

    var modal = document.getElementById('_slmModal');
    if (modal) {
      modal.addEventListener('click', function (e) {
        if (e.target === modal) window.closeShareLeadModal();
      });
    }
  }

  function _esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function _maskPhone(phone) {
    var p = (phone || '').replace(/\D/g, '');
    if (p.length < 6) return phone || '';
    return p.slice(0, 2) + '••••' + p.slice(-4);
  }

  function _showAlert(msg, isSuccess) {
    var el = document.getElementById('_slmAlert');
    if (!el) return;
    if (!msg) { el.style.display = 'none'; return; }
    el.style.display = 'block';
    el.style.background = isSuccess ? '#ecfdf5' : '#fef2f2';
    el.style.color = isSuccess ? '#065f46' : '#991b1b';
    el.style.border = '1px solid ' + (isSuccess ? '#a7f3d0' : '#fecaca');
    el.innerHTML = msg;
  }

  async function _loadStaff() {
    var sel = document.getElementById('_slmStaffSelect');
    if (!sel) return;

    if (_staffList && _staffList.length > 0) {
      _renderStaffOptions();
      return;
    }

    sel.innerHTML = '<option value="">— Loading staff members… —</option>';
    _isLoadingStaff = true;

    try {
      var r = await fetch(API_BASE + '/leads/shareable-staff', { credentials: 'include' });
      var d = await r.json();
      _staffList = (d && d.staff) ? d.staff : [];
      _renderStaffOptions();
    } catch (e) {
      console.error('[share-lead-modal] Failed to load staff:', e);
      sel.innerHTML = '<option value="">Failed to load staff list</option>';
    } finally {
      _isLoadingStaff = false;
      window._slmUpdatePreview();
    }
  }

  function _renderStaffOptions() {
    var sel = document.getElementById('_slmStaffSelect');
    if (!sel) return;
    if (!_staffList.length) {
      sel.innerHTML = '<option value="">No active staff members found</option>';
      return;
    }

    var optHtml = '<option value="">— Select Staff Member for Follow-up —</option>';
    _staffList.forEach(function (s) {
      var roleDept = [s.role, s.department].filter(Boolean).join(' · ');
      optHtml += '<option value="' + s.id + '" data-phone="' + _esc(s.phone || '') + '">' +
        _esc(s.name) + ' (' + _esc(s.emp_code) + ')' +
        (roleDept ? ' — ' + _esc(roleDept) : '') +
        '</option>';
    });
    sel.innerHTML = optHtml;
  }

  window.openShareLeadModal = function (leadData) {
    if (!leadData) return;
    _currentLead = leadData;
    _ensureModal();

    var modal = document.getElementById('_slmModal');
    if (!modal) return;
    modal.style.display = 'flex';

    _showAlert('', false);

    var name = leadData.name || 'Lead';
    var phone = leadData.phone || '';
    document.getElementById('_slmSubtitle').textContent = name + ' · ' + _maskPhone(phone);
    document.getElementById('_slmLeadId').textContent = '#' + (leadData.leadId || leadData.id || '—');

    var catEl = document.getElementById('_slmCategory');
    var catRow = document.getElementById('_slmCatRow');
    if (leadData.category) {
      catEl.textContent = leadData.category;
      catRow.style.display = 'flex';
    } else {
      catRow.style.display = 'none';
    }

    var locEl = document.getElementById('_slmLocation');
    var locRow = document.getElementById('_slmLocRow');
    var locStr = [leadData.area, leadData.city].filter(Boolean).join(', ');
    if (locStr) {
      locEl.textContent = locStr;
      locRow.style.display = 'flex';
    } else {
      locRow.style.display = 'none';
    }

    var reqEl = document.getElementById('_slmRequirements');
    var reqRow = document.getElementById('_slmReqRow');
    if (leadData.requirements) {
      reqEl.textContent = leadData.requirements;
      reqRow.style.display = 'block';
    } else {
      reqRow.style.display = 'none';
    }

    var notesInp = document.getElementById('_slmNotes');
    if (notesInp) {
      notesInp.value = leadData.notes || '';
    }

    _loadStaff();
  };

  window.closeShareLeadModal = function () {
    var modal = document.getElementById('_slmModal');
    if (modal) modal.style.display = 'none';
    _currentLead = null;
  };

  window._slmUpdatePreview = function () {
    var previewEl = document.getElementById('_slmMessagePreview');
    if (!previewEl || !_currentLead) return;

    var staffSelect = document.getElementById('_slmStaffSelect');
    var targetStaffId = staffSelect ? staffSelect.value : '';
    var staff = _staffList.find(function (s) { return String(s.id) === String(targetStaffId); });

    var purposeSelect = document.getElementById('_slmPurpose');
    var followupType = purposeSelect ? purposeSelect.value : 'secondary_followup';
    var notes = (document.getElementById('_slmNotes') ? document.getElementById('_slmNotes').value : '').trim();

    var purposeMap = {
      site_visit: 'Site Visit / Field Inspection',
      secondary_followup: 'Secondary Follow-Up Call',
      quotation: 'Quotation & Pricing Discussion',
      technical: 'Technical / Rooftop Feasibility',
      escalation: 'Senior Escalation / Special Handling',
      general: 'General Lead Follow-Up'
    };
    var purposeLabel = purposeMap[followupType] || 'Secondary Follow-Up';

    var leadId = _currentLead.leadId || _currentLead.id;
    var softphoneLink = 'https://www.myntreal.com/staff/softphone?lead_id=' + leadId + '&auto_dial=1';
    var crmLink = 'https://www.myntreal.com/staff/leads?lead_id=' + leadId;

    var locStr = [_currentLead.area, _currentLead.city].filter(Boolean).join(', ');

    var textLines = [
      '📢 *LEAD DETAILS FOR SECONDARY FOLLOW-UP*',
      '',
      '👤 *Customer*: ' + (_currentLead.name || ''),
      '📱 *Phone*: ' + (_currentLead.phone || ''),
      locStr ? '📍 *Location*: ' + locStr : null,
      _currentLead.category ? '🏷️ *Category*: ' + _currentLead.category : null,
      '🎯 *Purpose*: ' + purposeLabel,
      _currentLead.requirements ? '📝 *Requirement*: ' + _currentLead.requirements : null,
      notes ? '💬 *Notes*: ' + notes : null,
      '',
      '📞 *Call via Softphone*: ' + softphoneLink,
      '🔗 *View Lead in CRM*: ' + crmLink
    ].filter(Boolean);

    previewEl.textContent = textLines.join('\n');
  };

  window._slmExecute = async function (mode) {
    if (!_currentLead) return;

    var staffSelect = document.getElementById('_slmStaffSelect');
    var targetStaffId = parseInt(staffSelect ? staffSelect.value : '0', 10);
    if (!targetStaffId) {
      _showAlert('Please select a staff member to share details with.', false);
      if (staffSelect) staffSelect.focus();
      return;
    }

    var targetStaff = _staffList.find(function (s) { return s.id === targetStaffId; });
    if (!targetStaff) {
      _showAlert('Selected staff member is invalid.', false);
      return;
    }

    var followupType = document.getElementById('_slmPurpose') ? document.getElementById('_slmPurpose').value : 'secondary_followup';
    var notes = (document.getElementById('_slmNotes') ? document.getElementById('_slmNotes').value : '').trim();
    var assignAsSecondary = document.getElementById('_slmAssignCheck') ? document.getElementById('_slmAssignCheck').checked : false;

    var leadId = _currentLead.leadId || _currentLead.id;
    var primaryBtn = document.getElementById('_slmCombinedBtn');
    var crmBtn = document.getElementById('_slmCrmOnlyBtn');
    var waBtn = document.getElementById('_slmWaOnlyBtn');
    [primaryBtn, crmBtn, waBtn].forEach(function (b) { if (b) b.disabled = true; });

    _showAlert('Processing…', null);

    try {
      var waUrl = '';

      if (mode === 'crm_only' || mode === 'combined' || assignAsSecondary) {
        var payload = {
          target_staff_id: targetStaffId,
          followup_type: followupType,
          notes: notes,
          assign_as_secondary: assignAsSecondary
        };

        var resp = await fetch(API_BASE + '/leads/' + leadId + '/share-details', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(payload)
        });

        var res = await resp.json();
        if (res && (res.success || resp.ok)) {
          waUrl = res.wa_url || '';
          if (_currentLead.onShared) _currentLead.onShared(res);
        } else {
          throw new Error(res.detail || res.message || 'Failed to assign lead in CRM');
        }
      }

      if (mode === 'wa_only' || mode === 'combined') {
        if (!waUrl) {
          var cleanPhone = (targetStaff.phone || '').replace(/\D/g, '').slice(-10);
          if (!cleanPhone) {
            _showAlert('Colleague ' + targetStaff.name + ' does not have a valid mobile number for WhatsApp.', false);
          } else {
            var previewText = document.getElementById('_slmMessagePreview') ? document.getElementById('_slmMessagePreview').textContent : '';
            waUrl = 'https://wa.me/91' + cleanPhone + '?text=' + encodeURIComponent(previewText);
          }
        }

        if (waUrl) {
          window.open(waUrl, '_blank');
        }
      }

      var successMsg = mode === 'crm_only'
        ? '✅ Lead successfully assigned to ' + targetStaff.name + ' in CRM!'
        : mode === 'wa_only'
        ? '✅ WhatsApp launched for ' + targetStaff.name + '!'
        : '✅ Lead assigned in CRM and WhatsApp opened for ' + targetStaff.name + '!';

      _showAlert(successMsg, true);

      setTimeout(function () {
        window.closeShareLeadModal();
      }, 1200);

    } catch (err) {
      console.error('[share-lead-modal] Error:', err);
      _showAlert('⚠️ ' + (err.message || 'Error occurred while sharing lead'), false);
    } finally {
      [primaryBtn, crmBtn, waBtn].forEach(function (b) { if (b) b.disabled = false; });
    }
  };

  // DC Protocol helper for generic CRM lead objects
  window.openUniversalShareLeadModal = function (leadObj) {
    if (!leadObj) return;
    window.openShareLeadModal({
      leadId: leadObj.id || leadObj.lead_id,
      name: leadObj.name,
      phone: leadObj.phone,
      alternatePhone: leadObj.alternate_phone,
      category: leadObj.category || leadObj.category_name,
      area: leadObj.area,
      city: leadObj.city,
      requirements: leadObj.requirements,
      notes: leadObj.notes || leadObj.recent_comments,
      companyId: leadObj.company_id
    });
  };

})();
