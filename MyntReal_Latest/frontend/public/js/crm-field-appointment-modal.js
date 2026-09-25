/**
 * crm-field-appointment-modal.js — DC Protocol: Universal Field Appointment & Supporting Staff Modal
 * Parity across Web CRM, Dialers, and Lead Management screens.
 * 
 * Creates physical appointments for:
 *   Option 1: Visit Bank (Physical visit to Bank/Branch)
 *   Option 2: Visit Customer Location (Physical visit to Customer Address)
 *   Option 3: Others (Free-text purpose, location, contact, e.g. Registrar, Site, etc.)
 *
 * Entry points:
 *   - window.openFixAppointmentModal(leadData, onCreatedCallback)
 *   - window.closeFixAppointmentModal()
 *   - window.renderLeadFieldAppointments(leadId, containerId)
 */
(function () {
  'use strict';

  var API_BASE = '/api/v1/crm/field-appointments';
  var _staffList = [];
  var _isLoadingStaff = false;
  var _currentLead = null;
  var _onCreatedCallback = null;

  function _getTodayStr() {
    var d = new Date();
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
  }

  var MODAL_HTML = [
    '<div id="_famModal" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.8);backdrop-filter:blur(3px);z-index:1000000;align-items:center;justify-content:center;padding:16px;box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif">',
    '<div style="background:#0f172a;color:#f8fafc;border:1px solid rgba(255,255,255,0.15);border-radius:16px;width:100%;max-width:580px;max-height:94vh;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 25px 80px rgba(0,0,0,.7)">',

    /* Header */
    '<div style="background:linear-gradient(135deg,#059669 0%,#047857 100%);color:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,0.1)">',
    '<div style="display:flex;align-items:center;gap:10px">',
    '<div style="background:rgba(255,255,255,0.2);width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px">📍</div>',
    '<div>',
    '<div style="font-weight:800;font-size:15.5px;line-height:1.2">Fix Field Appointment</div>',
    '<div id="_famSubtitle" style="font-size:11.5px;color:rgba(255,255,255,0.9);margin-top:2px">Supporting Staff Physical Visit Assignment</div>',
    '</div>',
    '</div>',
    '<button type="button" onclick="window.closeFixAppointmentModal()" style="background:rgba(255,255,255,0.2);border:none;color:#fff;width:30px;height:30px;border-radius:8px;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;line-height:1">&times;</button>',
    '</div>',

    /* Body */
    '<div style="padding:16px 18px;overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:14px">',

    /* Lead info summary box */
    '<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:10px 14px;font-size:12px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">',
    '<div>',
    '<span style="color:#94a3b8;font-size:11px">LEAD:</span> <strong id="_famLeadName" style="color:#38bdf8;font-size:13px">—</strong>',
    '<span id="_famLeadPhone" style="color:#cbd5e1;margin-left:8px;font-family:monospace;font-size:12px"></span>',
    '</div>',
    '<div><span id="_famLeadLocation" class="badge" style="background:#334155;color:#94a3b8;font-size:11px"></span></div>',
    '</div>',

    /* Visit Type Tabs (3 Options) */
    '<div>',
    '<label style="display:block;font-size:11px;font-weight:700;color:#94a3b8;margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px">Select Visit Type <span style="color:#ef4444">*</span></label>',
    '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px">',
    '<button type="button" id="_famTabBank" onclick="window._famSetVisitType(\'visit_bank\')" style="padding:8px 6px;border-radius:8px;border:1.5px solid #059669;background:#059669;color:#fff;font-weight:700;font-size:12px;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:3px;text-align:center">',
    '<span>🏦 Option 1</span><span style="font-size:10px;font-weight:500;opacity:0.9">Visit Bank</span>',
    '</button>',
    '<button type="button" id="_famTabCustomer" onclick="window._famSetVisitType(\'visit_customer\')" style="padding:8px 6px;border-radius:8px;border:1.5px solid #334155;background:#1e293b;color:#94a3b8;font-weight:700;font-size:12px;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:3px;text-align:center">',
    '<span>👤 Option 2</span><span style="font-size:10px;font-weight:500;opacity:0.9">Visit Customer</span>',
    '</button>',
    '<button type="button" id="_famTabOthers" onclick="window._famSetVisitType(\'others\')" style="padding:8px 6px;border-radius:8px;border:1.5px solid #334155;background:#1e293b;color:#94a3b8;font-weight:700;font-size:12px;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:3px;text-align:center">',
    '<span>🏢 Option 3</span><span style="font-size:10px;font-weight:500;opacity:0.9">Others</span>',
    '</button>',
    '</div>',
    '</div>',

    /* Dynamic Section 1: Bank Visit */
    '<div id="_famSectionBank" style="display:flex;flex-direction:column;gap:10px;background:#1e293b;padding:12px;border-radius:10px;border:1px solid #334155">',
    '<div style="font-size:11.5px;font-weight:700;color:#10b981;display:flex;align-items:center;gap:6px"><i class="fas fa-university"></i> Bank & Branch Details</div>',
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">',
    '<div><label style="font-size:11px;color:#94a3b8;font-weight:600">Bank Name *</label><input type="text" id="_famBankName" placeholder="e.g. SBI, HDFC, ICICI" style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#fff;padding:6px 10px;font-size:12px;box-sizing:border-box"></div>',
    '<div><label style="font-size:11px;color:#94a3b8;font-weight:600">Branch Name</label><input type="text" id="_famBankBranch" placeholder="e.g. Banjara Hills Branch" style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#fff;padding:6px 10px;font-size:12px;box-sizing:border-box"></div>',
    '</div>',
    '<div><label style="font-size:11px;color:#94a3b8;font-weight:600">Bank Address</label><input type="text" id="_famBankAddress" placeholder="Street, landmark, city" style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#fff;padding:6px 10px;font-size:12px;box-sizing:border-box"></div>',
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">',
    '<div><label style="font-size:11px;color:#94a3b8;font-weight:600">Bank Contact Person</label><input type="text" id="_famBankContactPerson" placeholder="Branch Manager / Loan Officer" style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#fff;padding:6px 10px;font-size:12px;box-sizing:border-box"></div>',
    '<div><label style="font-size:11px;color:#94a3b8;font-weight:600">Bank Contact Phone</label><input type="text" id="_famBankContactPhone" placeholder="Mobile / landline" style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#fff;padding:6px 10px;font-size:12px;box-sizing:border-box"></div>',
    '</div>',
    '<div><label style="font-size:11px;color:#94a3b8;font-weight:600">Google Maps Link (Optional)</label><input type="url" id="_famBankMapsUrl" placeholder="https://maps.app.goo.gl/..." style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#fff;padding:6px 10px;font-size:12px;box-sizing:border-box"></div>',
    '</div>',

    /* Dynamic Section 2: Customer Visit */
    '<div id="_famSectionCustomer" style="display:none;flex-direction:column;gap:10px;background:#1e293b;padding:12px;border-radius:10px;border:1px solid #334155">',
    '<div style="font-size:11.5px;font-weight:700;color:#38bdf8;display:flex;align-items:center;gap:6px"><i class="fas fa-home"></i> Customer Location Details</div>',
    '<div><label style="font-size:11px;color:#94a3b8;font-weight:600">Customer Address *</label><textarea id="_famCustAddress" rows="2" placeholder="House/Flat No, Apartment, Street, Landmark" style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#fff;padding:6px 10px;font-size:12px;box-sizing:border-box;resize:none"></textarea></div>',
    '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">',
    '<div><label style="font-size:11px;color:#94a3b8;font-weight:600">City</label><input type="text" id="_famCustCity" placeholder="City" style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#fff;padding:6px 10px;font-size:12px;box-sizing:border-box"></div>',
    '<div><label style="font-size:11px;color:#94a3b8;font-weight:600">Area</label><input type="text" id="_famCustArea" placeholder="Area / Locality" style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#fff;padding:6px 10px;font-size:12px;box-sizing:border-box"></div>',
    '<div><label style="font-size:11px;color:#94a3b8;font-weight:600">Pincode</label><input type="text" id="_famCustPincode" placeholder="Pincode" style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#fff;padding:6px 10px;font-size:12px;box-sizing:border-box"></div>',
    '</div>',
    '<div><label style="font-size:11px;color:#94a3b8;font-weight:600">Google Maps Link (Optional)</label><input type="url" id="_famCustMapsUrl" placeholder="https://maps.app.goo.gl/..." style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#fff;padding:6px 10px;font-size:12px;box-sizing:border-box"></div>',
    '</div>',

    /* Dynamic Section 3: Others Visit */
    '<div id="_famSectionOthers" style="display:none;flex-direction:column;gap:10px;background:#1e293b;padding:12px;border-radius:10px;border:1px solid #334155">',
    '<div style="font-size:11.5px;font-weight:700;color:#f59e0b;display:flex;align-items:center;gap:6px"><i class="fas fa-map-marker-alt"></i> Other Location Details</div>',
    '<div><label style="font-size:11px;color:#94a3b8;font-weight:600">Location Title / Office Name *</label><input type="text" id="_famOtherTitle" placeholder="e.g. Sub-Registrar Office, Architect Office, Project Site" style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#fff;padding:6px 10px;font-size:12px;box-sizing:border-box"></div>',
    '<div><label style="font-size:11px;color:#94a3b8;font-weight:600">Full Address *</label><textarea id="_famOtherAddress" rows="2" placeholder="Address, area, landmark" style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#fff;padding:6px 10px;font-size:12px;box-sizing:border-box;resize:none"></textarea></div>',
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">',
    '<div><label style="font-size:11px;color:#94a3b8;font-weight:600">Contact Person Name</label><input type="text" id="_famOtherContactPerson" placeholder="Officer / In-charge name" style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#fff;padding:6px 10px;font-size:12px;box-sizing:border-box"></div>',
    '<div><label style="font-size:11px;color:#94a3b8;font-weight:600">Contact Person Phone</label><input type="text" id="_famOtherContactPhone" placeholder="Mobile number" style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#fff;padding:6px 10px;font-size:12px;box-sizing:border-box"></div>',
    '</div>',
    '<div><label style="font-size:11px;color:#94a3b8;font-weight:600">Google Maps Link (Optional)</label><input type="url" id="_famOtherMapsUrl" placeholder="https://maps.app.goo.gl/..." style="width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#fff;padding:6px 10px;font-size:12px;box-sizing:border-box"></div>',
    '</div>',

    /* Scheduling: Date & Preferred Time */
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">',
    '<div>',
    '<label style="display:block;font-size:11px;font-weight:700;color:#94a3b8;margin-bottom:4px;text-transform:uppercase;letter-spacing:.5px">Appointment Date <span style="color:#ef4444">*</span></label>',
    '<input type="date" id="_famApptDate" style="width:100%;background:#1e293b;border:1px solid #334155;border-radius:8px;color:#f8fafc;padding:8px 10px;font-size:12.5px;box-sizing:border-box">',
    '</div>',
    '<div>',
    '<label style="display:block;font-size:11px;font-weight:700;color:#94a3b8;margin-bottom:4px;text-transform:uppercase;letter-spacing:.5px">Preferred Time</label>',
    '<select id="_famPrefTime" style="width:100%;background:#1e293b;border:1px solid #334155;border-radius:8px;color:#f8fafc;padding:8px 10px;font-size:12.5px;box-sizing:border-box">',
    '<option value="10:00 AM">10:00 AM</option>',
    '<option value="11:00 AM">11:00 AM</option>',
    '<option value="11:30 AM" selected>11:30 AM</option>',
    '<option value="12:30 PM">12:30 PM</option>',
    '<option value="02:00 PM">02:00 PM</option>',
    '<option value="03:30 PM">03:30 PM</option>',
    '<option value="04:30 PM">04:30 PM</option>',
    '<option value="05:30 PM">05:30 PM</option>',
    '</select>',
    '</div>',
    '</div>',

    /* Supporting Staff Selection (Any Active Employee) */
    '<div>',
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">',
    '<label style="font-size:11px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px">Assign Supporting Staff Member <span style="color:#ef4444">*</span></label>',
    '<span style="font-size:10px;color:#10b981;font-weight:600">Any active employee across departments</span>',
    '</div>',
    '<select id="_famStaffSelect" style="width:100%;background:#1e293b;border:1px solid #334155;border-radius:8px;color:#f8fafc;padding:9px 12px;font-size:12.5px;box-sizing:border-box;cursor:pointer">',
    '<option value="">— Loading staff members… —</option>',
    '</select>',
    '</div>',

    /* Purpose / Objective (Free-text) */
    '<div>',
    '<label style="display:block;font-size:11px;font-weight:700;color:#94a3b8;margin-bottom:4px;text-transform:uppercase;letter-spacing:.5px">Purpose / Objective of Visit</label>',
    '<input type="text" id="_famPurpose" placeholder="e.g. Collect loan application form & bank statement / Property inspection" style="width:100%;background:#1e293b;border:1px solid #334155;border-radius:8px;color:#f8fafc;padding:8px 10px;font-size:12px;box-sizing:border-box">',
    '</div>',

    /* Telecaller Instructions for Staff */
    '<div>',
    '<label style="display:block;font-size:11px;font-weight:700;color:#94a3b8;margin-bottom:4px;text-transform:uppercase;letter-spacing:.5px">Telecaller Instructions for Supporting Staff</label>',
    '<textarea id="_famInstructions" rows="2" placeholder="e.g. Customer is free after 11:30 AM. Call before reaching. Collect 3 passport photos and signed ECS mandate." style="width:100%;background:#1e293b;border:1px solid #334155;border-radius:8px;color:#f8fafc;padding:8px 10px;font-size:12px;box-sizing:border-box;resize:none"></textarea>',
    '</div>',

    /* Error / Warning Alert Banner */
    '<div id="_famAlert" style="display:none;background:rgba(239,68,68,0.15);border:1px solid #ef4444;border-radius:8px;padding:8px 12px;color:#fca5a5;font-size:12px"></div>',

    '</div>',

    /* Footer */
    '<div style="background:#1e293b;border-top:1px solid #334155;padding:12px 18px;display:flex;justify-content:flex-end;gap:10px">',
    '<button type="button" onclick="window.closeFixAppointmentModal()" style="background:#334155;border:none;color:#cbd5e1;padding:8px 16px;border-radius:8px;font-size:12.5px;font-weight:600;cursor:pointer">Cancel</button>',
    '<button type="button" id="_famSubmitBtn" onclick="window._famSubmitAppointment()" style="background:linear-gradient(135deg,#059669,#047857);border:none;color:#fff;padding:8px 20px;border-radius:8px;font-size:12.5px;font-weight:700;cursor:pointer;display:flex;align-items:center;gap:6px">',
    '<i class="fas fa-check-circle"></i> Confirm &amp; Fix Appointment',
    '</button>',
    '</div>',

    '</div>',
    '</div>'
  ].join('');

  var _currentVisitType = 'visit_bank';

  function _ensureModalInjected() {
    if (!document.getElementById('_famModal')) {
      var d = document.createElement('div');
      d.innerHTML = MODAL_HTML;
      document.body.appendChild(d.firstElementChild);
    }
  }

  async function _loadSupportingStaff() {
    if (_staffList.length > 0) {
      _renderStaffOptions();
      return;
    }
    if (_isLoadingStaff) return;
    _isLoadingStaff = true;
    try {
      var r = typeof staffFetch === 'function' 
        ? await staffFetch(API_BASE + '/supporting-staff')
        : await fetch(API_BASE + '/supporting-staff', { credentials: 'include' });
      if (r.ok) {
        var res = await r.json();
        _staffList = res.data || [];
        _renderStaffOptions();
      }
    } catch (e) {
      console.warn('[FieldAppointment] Error loading staff:', e);
    } finally {
      _isLoadingStaff = false;
    }
  }

  function _renderStaffOptions() {
    var sel = document.getElementById('_famStaffSelect');
    if (!sel) return;
    if (_staffList.length === 0) {
      sel.innerHTML = '<option value="">No staff members found</option>';
      return;
    }
    var html = '<option value="">— Select Active Staff Member —</option>';
    _staffList.forEach(function (s) {
      var deptStr = s.department ? ' (' + s.department + ')' : '';
      var roleStr = s.role ? ' [' + s.role + ']' : '';
      html += '<option value="' + s.id + '">' + (s.full_name || 'Staff #' + s.id) + ' — ' + (s.emp_code || '') + deptStr + roleStr + '</option>';
    });
    sel.innerHTML = html;
  }

  window._famSetVisitType = function (vType) {
    _currentVisitType = vType;
    var tabBank = document.getElementById('_famTabBank');
    var tabCust = document.getElementById('_famTabCustomer');
    var tabOther = document.getElementById('_famTabOthers');

    var secBank = document.getElementById('_famSectionBank');
    var secCust = document.getElementById('_famSectionCustomer');
    var secOther = document.getElementById('_famSectionOthers');

    if (!tabBank || !secBank) return;

    // Reset styles
    [tabBank, tabCust, tabOther].forEach(function (t) {
      t.style.border = '1.5px solid #334155';
      t.style.background = '#1e293b';
      t.style.color = '#94a3b8';
    });

    secBank.style.display = 'none';
    secCust.style.display = 'none';
    secOther.style.display = 'none';

    if (vType === 'visit_bank') {
      tabBank.style.border = '1.5px solid #059669';
      tabBank.style.background = '#059669';
      tabBank.style.color = '#fff';
      secBank.style.display = 'flex';
    } else if (vType === 'visit_customer') {
      tabCust.style.border = '1.5px solid #0284c7';
      tabCust.style.background = '#0284c7';
      tabCust.style.color = '#fff';
      secCust.style.display = 'flex';
    } else {
      tabOther.style.border = '1.5px solid #d97706';
      tabOther.style.background = '#d97706';
      tabOther.style.color = '#fff';
      secOther.style.display = 'flex';
    }
  };

  window.openFixAppointmentModal = function (leadData, onCreated) {
    _ensureModalInjected();
    _currentLead = leadData || {};
    _onCreatedCallback = onCreated || null;

    // Fill Lead Header
    document.getElementById('_famLeadName').textContent = _currentLead.name || 'Lead #' + (_currentLead.id || '');
    document.getElementById('_famLeadPhone').textContent = _currentLead.phone ? '📞 ' + _currentLead.phone : '';
    document.getElementById('_famLeadLocation').textContent = (_currentLead.area || '') + (_currentLead.city ? ', ' + _currentLead.city : '');

    // Pre-populate customer details if present
    document.getElementById('_famCustAddress').value = _currentLead.address || '';
    document.getElementById('_famCustCity').value = _currentLead.city || '';
    document.getElementById('_famCustArea').value = _currentLead.area || '';
    document.getElementById('_famCustPincode').value = _currentLead.pincode || '';
    document.getElementById('_famCustMapsUrl').value = _currentLead.google_maps_url || _currentLead.location_url || '';

    // Pre-populate bank details if present
    document.getElementById('_famBankName').value = _currentLead.bank_name || '';
    document.getElementById('_famBankBranch').value = _currentLead.bank_branch || '';
    document.getElementById('_famBankAddress').value = _currentLead.bank_address || '';
    document.getElementById('_famBankContactPerson').value = _currentLead.bank_contact_person || '';
    document.getElementById('_famBankContactPhone').value = _currentLead.bank_contact_phone || '';
    document.getElementById('_famBankMapsUrl').value = _currentLead.bank_google_maps_url || (_currentLead.bank_name ? (_currentLead.google_maps_url || '') : '');

    document.getElementById('_famOtherTitle').value = _currentLead.other_location_title || '';
    document.getElementById('_famOtherAddress').value = _currentLead.other_location_address || '';
    document.getElementById('_famOtherContactPerson').value = _currentLead.other_contact_person || '';
    document.getElementById('_famOtherContactPhone').value = _currentLead.other_contact_phone || '';
    document.getElementById('_famOtherMapsUrl').value = _currentLead.other_google_maps_url || '';

    document.getElementById('_famPurpose').value = _currentLead.purpose || '';
    document.getElementById('_famInstructions').value = _currentLead.instructions || '';

    // Date defaults to today
    var apptDateEl = document.getElementById('_famApptDate');
    apptDateEl.value = _getTodayStr();
    apptDateEl.min = _getTodayStr();

    var alertEl = document.getElementById('_famAlert');
    alertEl.style.display = 'none';
    alertEl.textContent = '';

    // Reset button
    var submitBtn = document.getElementById('_famSubmitBtn');
    submitBtn.disabled = false;
    submitBtn.innerHTML = '<i class="fas fa-check-circle"></i> Confirm &amp; Fix Appointment';

    // Set visit type based on lead context or preference
    var initialVisitType = _currentLead.default_visit_type || (_currentLead.bank_name ? 'visit_bank' : (_currentLead.address ? 'visit_customer' : 'visit_bank'));
    window._famSetVisitType(initialVisitType);

    // Load staff
    _loadSupportingStaff();

    // Show modal
    var modal = document.getElementById('_famModal');
    modal.style.display = 'flex';
  };

  // Provide alias for seamless interoperability
  window.openFieldAppointmentModal = window.openFixAppointmentModal;

  window.closeFixAppointmentModal = function () {
    var modal = document.getElementById('_famModal');
    if (modal) modal.style.display = 'none';
  };

  window._famSubmitAppointment = async function () {
    var alertEl = document.getElementById('_famAlert');
    alertEl.style.display = 'none';
    alertEl.textContent = '';

    if (!_currentLead || !_currentLead.id) {
      alertEl.textContent = 'Invalid lead selected. Please reopen the modal.';
      alertEl.style.display = 'block';
      return;
    }

    var apptDate = document.getElementById('_famApptDate').value;
    if (!apptDate) {
      alertEl.textContent = 'Please choose an appointment date.';
      alertEl.style.display = 'block';
      return;
    }

    var staffId = document.getElementById('_famStaffSelect').value;
    if (!staffId) {
      alertEl.textContent = 'Please select a supporting staff member to assign.';
      alertEl.style.display = 'block';
      return;
    }

    var payload = {
      lead_id: parseInt(_currentLead.id),
      visit_type: _currentVisitType,
      appointment_date: apptDate,
      preferred_time: document.getElementById('_famPrefTime').value,
      assigned_to_id: parseInt(staffId),
      purpose: document.getElementById('_famPurpose').value.trim() || null,
      telecaller_instructions: document.getElementById('_famInstructions').value.trim() || null
    };

    if (_currentVisitType === 'visit_bank') {
      var bName = document.getElementById('_famBankName').value.trim();
      if (!bName) {
        alertEl.textContent = 'Please provide the Bank Name for Option 1.';
        alertEl.style.display = 'block';
        return;
      }
      payload.bank_name = bName;
      payload.bank_branch = document.getElementById('_famBankBranch').value.trim() || null;
      payload.bank_address = document.getElementById('_famBankAddress').value.trim() || null;
      payload.bank_contact_person = document.getElementById('_famBankContactPerson').value.trim() || null;
      payload.bank_contact_phone = document.getElementById('_famBankContactPhone').value.trim() || null;
      payload.bank_google_maps_url = document.getElementById('_famBankMapsUrl').value.trim() || null;
    } else if (_currentVisitType === 'visit_customer') {
      var cAddr = document.getElementById('_famCustAddress').value.trim();
      if (!cAddr) {
        alertEl.textContent = 'Please provide the Customer Address for Option 2.';
        alertEl.style.display = 'block';
        return;
      }
      payload.customer_address = cAddr;
      payload.customer_city = document.getElementById('_famCustCity').value.trim() || null;
      payload.customer_area = document.getElementById('_famCustArea').value.trim() || null;
      payload.customer_pincode = document.getElementById('_famCustPincode').value.trim() || null;
      payload.customer_google_maps_url = document.getElementById('_famCustMapsUrl').value.trim() || null;
    } else {
      var oTitle = document.getElementById('_famOtherTitle').value.trim();
      var oAddr = document.getElementById('_famOtherAddress').value.trim();
      if (!oTitle || !oAddr) {
        alertEl.textContent = 'Please provide Location Title and Address for Option 3.';
        alertEl.style.display = 'block';
        return;
      }
      payload.other_location_title = oTitle;
      payload.other_location_address = oAddr;
      payload.other_contact_person = document.getElementById('_famOtherContactPerson').value.trim() || null;
      payload.other_contact_phone = document.getElementById('_famOtherContactPhone').value.trim() || null;
      payload.other_google_maps_url = document.getElementById('_famOtherMapsUrl').value.trim() || null;
    }

    var submitBtn = document.getElementById('_famSubmitBtn');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

    try {
      var r = typeof staffFetch === 'function'
        ? await staffFetch(API_BASE, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          })
        : await fetch(API_BASE, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });

      var res = await r.json();
      if (!r.ok) {
        alertEl.textContent = res.detail || res.message || 'Failed to create appointment.';
        alertEl.style.display = 'block';
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-check-circle"></i> Confirm &amp; Fix Appointment';
        return;
      }

      window.closeFixAppointmentModal();

      if (typeof window.showToast === 'function') {
        window.showToast('Field Appointment ' + res.appointment.appointment_code + ' created successfully!', 'success');
      } else {
        alert('Field Appointment ' + res.appointment.appointment_code + ' created successfully!');
      }

      if (typeof _onCreatedCallback === 'function') {
        _onCreatedCallback(res.appointment);
      }
    } catch (e) {
      alertEl.textContent = 'Network or server error: ' + e.message;
      alertEl.style.display = 'block';
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-check-circle"></i> Confirm &amp; Fix Appointment';
    }
  };

  /**
   * Helper to render appointment list inside Lead Details
   */
  window.renderLeadFieldAppointments = async function (leadId, containerId) {
    var container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '<div style="color:#94a3b8;font-size:12px;padding:8px 0"><i class="fas fa-spinner fa-spin me-1"></i> Loading field appointments…</div>';

    try {
      var r = typeof staffFetch === 'function'
        ? await staffFetch(API_BASE + '/lead/' + leadId)
        : await fetch(API_BASE + '/lead/' + leadId, { credentials: 'include' });

      if (!r.ok) {
        container.innerHTML = '<div style="color:#94a3b8;font-size:12px">No field appointments scheduled.</div>';
        return;
      }

      var res = await r.json();
      var appts = res.data || [];

      var countEl = document.getElementById('leadFieldAppointmentsCount');
      if (countEl) {
        countEl.textContent = appts.length;
        countEl.style.display = appts.length > 0 ? 'inline-block' : 'none';
      }

      if (appts.length === 0) {
        container.innerHTML = '<div style="color:#94a3b8;font-size:12px;padding:6px 0">No field appointments scheduled for this lead.</div>';
        return;
      }

      var html = '<div style="display:flex;flex-direction:column;gap:10px">';
      appts.forEach(function (apt) {
        var vTypeBadge = '';
        var destStr = '';
        if (apt.visit_type === 'visit_bank') {
          vTypeBadge = '<span class="badge" style="background:#059669;color:#fff;font-size:10px"><i class="fas fa-university me-1"></i>Bank Visit</span>';
          destStr = (apt.bank_name || '') + (apt.bank_branch ? ' (' + apt.bank_branch + ')' : '');
        } else if (apt.visit_type === 'visit_customer') {
          vTypeBadge = '<span class="badge" style="background:#0284c7;color:#fff;font-size:10px"><i class="fas fa-home me-1"></i>Customer Visit</span>';
          destStr = apt.customer_address || 'Customer Location';
        } else {
          vTypeBadge = '<span class="badge" style="background:#d97706;color:#fff;font-size:10px"><i class="fas fa-map-marker-alt me-1"></i>' + (apt.other_location_title || 'Other Visit') + '</span>';
          destStr = apt.other_location_address || '';
        }

        var statusColors = {
          assigned: 'background:#3b82f6;color:#fff',
          accepted: 'background:#06b6d4;color:#fff',
          in_progress: 'background:#6366f1;color:#fff',
          reached: 'background:#8b5cf6;color:#fff',
          completed: 'background:#10b981;color:#fff',
          rescheduled: 'background:#f59e0b;color:#fff',
          unable_to_visit: 'background:#ef4444;color:#fff',
          cancelled: 'background:#6b7280;color:#fff'
        };
        var sBadge = '<span class="badge" style="' + (statusColors[apt.status] || 'background:#6b7280;color:#fff') + ';font-size:10px;text-transform:uppercase">' + apt.status.replace(/_/g, ' ') + '</span>';

        var staffName = apt.assigned_to ? apt.assigned_to.full_name + ' (' + (apt.assigned_to.emp_code || '') + ')' : 'Assigned Staff #' + apt.assigned_to_id;

        var proofHtml = '';
        if (apt.photo_url || apt.photo_path) {
          var pUrl = apt.photo_url || apt.photo_path;
          proofHtml = '<div style="margin-top:6px"><a href="' + pUrl + '" target="_blank" style="font-size:11px;color:#10b981;text-decoration:none;font-weight:600"><i class="fas fa-camera me-1"></i>View Visit Photo Proof</a></div>';
        }

        var gpsBadge = apt.is_gps_verified 
          ? '<span class="badge bg-success ms-1" style="font-size:9.5px"><i class="fas fa-satellite-dish me-1"></i>GPS Verified</span>'
          : '';

        var onTimeBadge = '';
        if (apt.visited_on_time === true) {
          onTimeBadge = '<span class="badge bg-success ms-1" style="font-size:9.5px"><i class="fas fa-clock me-1"></i>On-Time</span>';
        } else if (apt.visited_on_time === false) {
          onTimeBadge = '<span class="badge bg-warning text-dark ms-1" style="font-size:9.5px"><i class="fas fa-clock me-1"></i>Delayed</span>';
        }

        var reachedStr = apt.reached_at 
          ? '<div style="font-size:11px;color:#a855f7;margin-top:3px"><i class="fas fa-check-double me-1"></i>Reached: ' + new Date(apt.reached_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) + '</div>'
          : '';

        var outcomeStr = apt.outcome_status
          ? '<div style="font-size:11px;color:#e2e8f0;margin-top:4px;padding:4px 8px;background:rgba(255,255,255,0.04);border-radius:4px"><b>Outcome:</b> ' + apt.outcome_status.toUpperCase() + (apt.outcome_summary ? ' — ' + apt.outcome_summary : '') + '</div>'
          : '';

        html += [
          '<div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:10px 12px;font-size:12px">',
          '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">',
          '<div style="display:flex;align-items:center;gap:6px">' + vTypeBadge + ' ' + sBadge + gpsBadge + onTimeBadge + '</div>',
          '<span style="font-size:11px;font-family:monospace;color:#94a3b8;font-weight:700">' + apt.appointment_code + '</span>',
          '</div>',
          '<div style="font-weight:700;color:#f8fafc;margin-bottom:3px">' + destStr + '</div>',
          '<div style="color:#94a3b8;font-size:11.5px"><i class="fas fa-calendar-alt me-1"></i>' + apt.appointment_date + ' (' + (apt.preferred_time || 'Anytime') + ') &bull; <i class="fas fa-user-check me-1"></i>' + staffName + '</div>',
          (apt.purpose ? '<div style="font-size:11px;color:#cbd5e1;margin-top:4px"><i class="fas fa-bullseye me-1 text-info"></i>' + apt.purpose + '</div>' : ''),
          reachedStr,
          outcomeStr,
          proofHtml,
          '</div>'
        ].join('');
      });
      html += '</div>';

      container.innerHTML = html;
    } catch (e) {
      container.innerHTML = '<div style="color:#ef4444;font-size:11.5px">Failed to load appointments: ' + e.message + '</div>';
    }
  };

})();
