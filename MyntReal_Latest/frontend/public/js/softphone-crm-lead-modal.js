/**
 * softphone-crm-lead-modal.js
 * Unified Auto-Dialer Style CRM Lead Modal for Softphone Center Call Logs
 * 
 * Provides:
 *   window.openSoftphoneCRMLeadModal(leadId, phone, name, companyId, onSavedCallback)
 *   window.openCRMLeadModal(...) (alias)
 * 
 * Complies with VGK4U System Rules:
 *   - Frozen Telephony Lock: Zero modifications to softphone/WebRTC core.
 *   - SSR / Environment safe checks.
 *   - No hardcoded local machine paths.
 */

(function () {
  'use strict';

  // Prevent double definition
  if (window._SoftphoneCRMLeadModalLoaded) return;
  window._SoftphoneCRMLeadModalLoaded = true;

  let currentLead = null;
  let currentLeadId = null;
  let currentCompanyId = null;
  let onSavedHook = null;
  let categoriesCache = [];

  const STATUS_LABELS = {
    'new': 'New',
    'tried to contact': 'Tried to Contact',
    'contacted': 'Contacted',
    'interested': 'Interested',
    'qualified': 'Qualified',
    'proposal': 'Proposal Sent',
    'on_hold': 'On Hold',
    'waiting_for_bank_loan': 'Waiting for Bank Loan',
    'bank_loan_rejected': 'Bank Loan Rejected',
    'loan_process': 'Loan Process',
    'won': 'Won',
    'order_placed': 'Order Placed',
    'dispatched': 'Dispatched',
    'delivered': 'Delivered',
    'installed': 'Installed',
    'completed': 'Completed',
    'lost': 'Lost',
    'do_not_call': 'Do Not Call (DNC)'
  };

  const STATUS_BADGE_COLORS = {
    'new': '#3b82f6',
    'tried to contact': '#f59e0b',
    'contacted': '#06b6d4',
    'interested': '#10b981',
    'qualified': '#8b5cf6',
    'proposal': '#a855f7',
    'on_hold': '#64748b',
    'waiting_for_bank_loan': '#eab308',
    'bank_loan_rejected': '#ef4444',
    'loan_process': '#3b82f6',
    'won': '#22c55e',
    'order_placed': '#10b981',
    'dispatched': '#06b6d4',
    'delivered': '#14b8a6',
    'installed': '#16a34a',
    'completed': '#15803d',
    'lost': '#dc2626',
    'do_not_call': '#991b1b'
  };

  function getToken() {
    if (typeof localStorage === 'undefined') return '';
    return localStorage.getItem('staff_token') ||
           localStorage.getItem('token') ||
           (typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('staff_token') : '') ||
           (typeof document !== 'undefined' ? (document.cookie.match(/staff_token=([^;]+)/) || [])[1] : '') || '';
  }

  async function apiFetch(url, options = {}) {
    const token = getToken();
    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...(options.headers || {})
    };
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Request failed with status ${res.status}`);
    }
    return res.json();
  }

  function esc(str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatIST(isoStr) {
    if (!isoStr) return '—';
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return String(isoStr);
      return d.toLocaleString('en-IN', {
        timeZone: 'Asia/Kolkata',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
      });
    } catch (e) {
      return String(isoStr);
    }
  }

  function showToast(msg, type = 'success') {
    if (typeof window.showToast === 'function') {
      window.showToast(msg, type);
      return;
    }
    const toast = document.createElement('div');
    toast.className = 'crm-modal-toast';
    toast.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: ${type === 'error' ? '#ef4444' : '#10b981'};
      color: white;
      padding: 12px 20px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      z-index: 10000000;
      box-shadow: 0 10px 25px rgba(0,0,0,0.3);
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.3s ease;
    `;
    toast.innerHTML = `<i class="fa-solid ${type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-check'}"></i> <span>${esc(msg)}</span>`;
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  /* ── DOM Injection ────────────────────────────────────────────────────────── */
  function ensureModalDOM() {
    let overlay = document.getElementById('softphoneCrmLeadModalOverlay');
    if (overlay) return;

    overlay = document.createElement('div');
    overlay.id = 'softphoneCrmLeadModalOverlay';
    overlay.style.cssText = `
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.75);
      backdrop-filter: blur(4px);
      -webkit-backdrop-filter: blur(4px);
      z-index: 999999;
      align-items: center;
      justify-content: center;
      padding: 16px;
      box-sizing: border-box;
      opacity: 0;
      transition: opacity 0.2s ease;
    `;

    overlay.innerHTML = `
      <div id="softphoneCrmLeadModalCard" style="
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 16px;
        width: 100%;
        max-width: 820px;
        max-height: 92vh;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.7);
        color: #f8fafc;
        transform: scale(0.96);
        transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
      ">
        <!-- HEADER -->
        <div style="
          background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
          border-bottom: 1px solid #334155;
          padding: 16px 20px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          flex-wrap: wrap;
        ">
          <div style="display: flex; align-items: center; gap: 12px; min-width: 0;">
            <div style="
              width: 44px;
              height: 44px;
              border-radius: 12px;
              background: linear-gradient(135deg, #f59e0b, #d97706);
              color: white;
              display: flex;
              align-items: center;
              justify-content: center;
              font-size: 20px;
              font-weight: 800;
              flex-shrink: 0;
              box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
            ">
              <i class="fa-solid fa-address-card"></i>
            </div>
            <div style="min-width: 0;">
              <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <h5 id="scrmLeadName" style="margin: 0; font-size: 17px; font-weight: 800; color: #ffffff; letter-spacing: -0.2px;">Loading Lead…</h5>
                <span id="scrmLeadIdBadge" class="badge" style="background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.3); color: #fbbf24; font-size: 11px; font-weight: 700; font-family: monospace;">#—</span>
                <span id="scrmLeadStatusBadge" class="badge" style="background: #3b82f6; font-size: 11px; font-weight: 700;">New</span>
                <span id="scrmLeadPriorityBadge" class="badge" style="background: rgba(148, 163, 184, 0.2); border: 1px solid #475569; color: #cbd5e1; font-size: 11px;">Normal</span>
              </div>
              <div style="display: flex; align-items: center; gap: 8px; font-size: 12px; color: #94a3b8; margin-top: 3px; flex-wrap: wrap;">
                <span id="scrmLeadPhoneText" style="color: #60a5fa; font-weight: 600;"><i class="fa-solid fa-phone me-1"></i>—</span>
                <span>·</span>
                <span id="scrmLeadCategoryText"><i class="fa-solid fa-tag me-1 text-warning"></i>—</span>
                <span>·</span>
                <span id="scrmLeadLocationText"><i class="fa-solid fa-location-dot me-1 text-danger"></i>—</span>
              </div>
            </div>
          </div>

          <!-- Quick Header Action Buttons -->
          <div style="display: flex; align-items: center; gap: 8px;">
            <button id="scrmHeaderCallBtn" type="button" class="btn btn-sm" style="background: #10b981; color: white; font-weight: 700; border-radius: 8px; padding: 6px 12px; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3);">
              <i class="fa-solid fa-phone"></i> Call
            </button>
            <button id="scrmHeaderWaBtn" type="button" class="btn btn-sm" style="background: #25D366; color: white; font-weight: 700; border-radius: 8px; padding: 6px 12px; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 2px 6px rgba(37, 211, 102, 0.3);">
              <i class="fab fa-whatsapp"></i> WA
            </button>
            <button type="button" onclick="window.closeSoftphoneCRMLeadModal()" style="
              background: rgba(255, 255, 255, 0.08);
              border: 1px solid rgba(255, 255, 255, 0.15);
              color: #cbd5e1;
              border-radius: 8px;
              width: 32px;
              height: 32px;
              display: flex;
              align-items: center;
              justify-content: center;
              cursor: pointer;
              font-size: 16px;
              transition: all 0.15s ease;
            " title="Close Modal">&times;</button>
          </div>
        </div>

        <!-- TABS NAV -->
        <div style="
          background: #131d2f;
          border-bottom: 1px solid #334155;
          padding: 6px 20px;
          display: flex;
          align-items: center;
          gap: 10px;
        ">
          <button id="scrmTabBtnDetails" type="button" onclick="window._scrmSwitchTab('details')" style="
            background: rgba(245, 158, 11, 0.15);
            border: 1px solid rgba(245, 158, 11, 0.3);
            color: #fbbf24;
            padding: 7px 14px;
            border-radius: 8px;
            font-size: 12.5px;
            font-weight: 700;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
          ">
            <i class="fa-solid fa-sliders"></i> Lead Classification &amp; Status
          </button>
          <button id="scrmTabBtnComments" type="button" onclick="window._scrmSwitchTab('comments')" style="
            background: transparent;
            border: 1px solid transparent;
            color: #94a3b8;
            padding: 7px 14px;
            border-radius: 8px;
            font-size: 12.5px;
            font-weight: 700;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
          ">
            <i class="fa-solid fa-comments"></i> Comments &amp; Updates (<span id="scrmNotesCountBadge">0</span>)
          </button>
          <button id="scrmTabBtnAudit" type="button" onclick="window._scrmSwitchTab('audit')" style="
            background: transparent;
            border: 1px solid transparent;
            color: #94a3b8;
            padding: 7px 14px;
            border-radius: 8px;
            font-size: 12.5px;
            font-weight: 700;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.15s ease;
          ">
            <i class="fa-solid fa-clock-rotate-left"></i> Field Changes &amp; Updates (<span id="scrmAuditCountBadge">0</span>)
          </button>
        </div>

        <!-- BODY -->
        <div id="scrmModalScrollBody" style="
          padding: 20px;
          overflow-y: auto;
          flex: 1;
        ">
          <!-- Loading State -->
          <div id="scrmLoadingState" style="text-align: center; padding: 40px 20px;">
            <div class="spinner-border text-warning" role="status" style="width: 2.5rem; height: 2.5rem;"></div>
            <div style="margin-top: 14px; color: #94a3b8; font-weight: 600; font-size: 13.5px;">Loading CRM lead details…</div>
          </div>

          <!-- TAB 1: DETAILS & STATUS (AUTO DIALER MODEL) -->
          <div id="scrmTabContentDetails" style="display: none;">
            <div style="background: rgba(15, 23, 42, 0.5); border: 1px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 16px;">
              <div style="font-size: 12px; font-weight: 800; color: #fbbf24; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; display: flex; align-items: center; gap: 6px;">
                <i class="fa-solid fa-diagram-project"></i> Pipeline Stage &amp; Classification
              </div>
              <div class="row g-3">
                <div class="col-md-5">
                  <label style="font-size: 12px; font-weight: 700; color: #cbd5e1; margin-bottom: 4px; display: block;">Lead Status *</label>
                  <select id="scrmEditStatus" class="form-select" style="background: #0f172a; border-color: #3b82f6; color: #ffffff; font-weight: 700; font-size: 13px;" onchange="window._scrmOnStatusChange(this.value)">
                    <optgroup label="Pipeline Stages">
                      <option value="new">New</option>
                      <option value="tried to contact">Tried to Contact</option>
                      <option value="contacted">Contacted</option>
                      <option value="interested">Interested</option>
                      <option value="qualified">Qualified</option>
                      <option value="proposal">Proposal Sent</option>
                      <option value="on_hold">On Hold</option>
                    </optgroup>
                    <optgroup label="Bank Loan Stages">
                      <option value="waiting_for_bank_loan">Waiting for Bank Loan</option>
                      <option value="bank_loan_rejected">Bank Loan Rejected</option>
                      <option value="loan_process">Loan Process</option>
                    </optgroup>
                    <optgroup label="Won &amp; Implementation">
                      <option value="won">Won</option>
                      <option value="order_placed">Order Placed</option>
                      <option value="dispatched">Dispatched</option>
                      <option value="delivered">Delivered</option>
                      <option value="installed">Installed</option>
                      <option value="completed">Completed</option>
                    </optgroup>
                    <optgroup label="Closed">
                      <option value="lost">Lost</option>
                      <option value="do_not_call">Do Not Call (DNC)</option>
                    </optgroup>
                  </select>
                </div>

                <div class="col-md-3">
                  <label style="font-size: 12px; font-weight: 700; color: #cbd5e1; margin-bottom: 4px; display: block;">Priority</label>
                  <select id="scrmEditPriority" class="form-select" style="background: #0f172a; border-color: #475569; color: #ffffff; font-size: 13px;">
                    <option value="normal">Normal</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>

                <div class="col-md-4">
                  <label style="font-size: 12px; font-weight: 700; color: #cbd5e1; margin-bottom: 4px; display: block;">Category / Vertical</label>
                  <select id="scrmEditCategory" class="form-select" style="background: #0f172a; border-color: #475569; color: #ffffff; font-size: 13px;">
                    <option value="">Select Category…</option>
                  </select>
                </div>
              </div>
            </div>

            <!-- CONTACT DETAILS -->
            <div style="background: rgba(15, 23, 42, 0.5); border: 1px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 16px;">
              <div style="font-size: 12px; font-weight: 800; color: #60a5fa; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; display: flex; align-items: center; gap: 6px;">
                <i class="fa-solid fa-user"></i> Customer Information
              </div>
              <div class="row g-3">
                <div class="col-md-6">
                  <label style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 4px; display: block;">Customer Name *</label>
                  <input type="text" id="scrmEditName" class="form-control" style="background: #0f172a; border-color: #475569; color: #ffffff; font-size: 13px;">
                </div>
                <div class="col-md-6">
                  <label style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 4px; display: block;">Email</label>
                  <input type="email" id="scrmEditEmail" class="form-control" style="background: #0f172a; border-color: #475569; color: #ffffff; font-size: 13px;">
                </div>
                <div class="col-md-6">
                  <label style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 4px; display: block;">Primary Phone</label>
                  <input type="tel" id="scrmEditPhone" class="form-control" style="background: #0f172a; border-color: #475569; color: #ffffff; font-size: 13px;" readonly>
                </div>
                <div class="col-md-6">
                  <label style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 4px; display: block;">Alternate Phone</label>
                  <input type="tel" id="scrmEditAltPhone" class="form-control" style="background: #0f172a; border-color: #475569; color: #ffffff; font-size: 13px;">
                </div>
              </div>
            </div>

            <!-- LOCATION & BUDGET -->
            <div style="background: rgba(15, 23, 42, 0.5); border: 1px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 16px;">
              <div style="font-size: 12px; font-weight: 800; color: #34d399; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; display: flex; align-items: center; gap: 6px;">
                <i class="fa-solid fa-map-location-dot"></i> Location &amp; Project Budget
              </div>
              <div class="row g-3">
                <div class="col-md-4">
                  <label style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 4px; display: block;">City</label>
                  <input type="text" id="scrmEditCity" class="form-control" style="background: #0f172a; border-color: #475569; color: #ffffff; font-size: 13px;">
                </div>
                <div class="col-md-4">
                  <label style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 4px; display: block;">Area / Locality</label>
                  <input type="text" id="scrmEditArea" class="form-control" style="background: #0f172a; border-color: #475569; color: #ffffff; font-size: 13px;">
                </div>
                <div class="col-md-4">
                  <label style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 4px; display: block;">Source</label>
                  <input type="text" id="scrmEditSource" class="form-control" style="background: #0f172a; border-color: #475569; color: #ffffff; font-size: 13px;">
                </div>
                <div class="col-md-4">
                  <label style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 4px; display: block;">Budget Min (₹)</label>
                  <input type="number" id="scrmEditBudgetMin" class="form-control" style="background: #0f172a; border-color: #475569; color: #ffffff; font-size: 13px;">
                </div>
                <div class="col-md-4">
                  <label style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 4px; display: block;">Budget Max (₹)</label>
                  <input type="number" id="scrmEditBudgetMax" class="form-control" style="background: #0f172a; border-color: #475569; color: #ffffff; font-size: 13px;">
                </div>
                <div class="col-md-4">
                  <label style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 4px; display: block;">Next Follow-up</label>
                  <input type="datetime-local" id="scrmEditFollowup" class="form-control" style="background: #0f172a; border-color: #475569; color: #ffffff; font-size: 13px;">
                </div>
              </div>
            </div>

            <!-- DESCRIPTION & REQUIREMENTS -->
            <div style="background: rgba(15, 23, 42, 0.5); border: 1px solid #334155; border-radius: 12px; padding: 16px;">
              <div style="font-size: 12px; font-weight: 800; color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; display: flex; align-items: center; gap: 6px;">
                <i class="fa-solid fa-file-lines"></i> Project Details &amp; Requirements
              </div>
              <div class="row g-3">
                <div class="col-md-6">
                  <label style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 4px; display: block;">Description</label>
                  <textarea id="scrmEditDescription" class="form-control" rows="2" style="background: #0f172a; border-color: #475569; color: #ffffff; font-size: 13px;" placeholder="Lead context, notes on property/site..."></textarea>
                </div>
                <div class="col-md-6">
                  <label style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 4px; display: block;">Requirements</label>
                  <textarea id="scrmEditRequirements" class="form-control" rows="2" style="background: #0f172a; border-color: #475569; color: #ffffff; font-size: 13px;" placeholder="Customer specifications, size, capacities..."></textarea>
                </div>
              </div>
            </div>
          </div>

          <!-- TAB 2: COMMENTS & UPDATES TIMELINE -->
          <div id="scrmTabContentComments" style="display: none;">
            
            <!-- ADD NEW COMMENT SECTION -->
            <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid #f59e0b; border-radius: 12px; padding: 16px; margin-bottom: 20px;">
              <div style="font-size: 12.5px; font-weight: 800; color: #fbbf24; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                <i class="fa-solid fa-pen-to-square"></i> Add New Comment / Call Outcome
              </div>

              <!-- Quick outcome chips -->
              <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px;">
                <button type="button" class="btn btn-sm" onclick="window._scrmApplyOutcomeChip('Answered - Interested', 'interested')" style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); color: #34d399; font-size: 11.5px; font-weight: 700; border-radius: 20px; padding: 3px 10px;">
                  ✅ Answered - Interested
                </button>
                <button type="button" class="btn btn-sm" onclick="window._scrmApplyOutcomeChip('Follow-up Required', 'contacted')" style="background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.4); color: #60a5fa; font-size: 11.5px; font-weight: 700; border-radius: 20px; padding: 3px 10px;">
                  📞 Follow-up Required
                </button>
                <button type="button" class="btn btn-sm" onclick="window._scrmApplyOutcomeChip('Busy / No Answer', 'tried to contact')" style="background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); color: #fbbf24; font-size: 11.5px; font-weight: 700; border-radius: 20px; padding: 3px 10px;">
                  📳 Busy / No Answer
                </button>
                <button type="button" class="btn btn-sm" onclick="window._scrmApplyOutcomeChip('Callback Requested', 'contacted')" style="background: rgba(168, 85, 247, 0.15); border: 1px solid rgba(168, 85, 247, 0.4); color: #c084fc; font-size: 11.5px; font-weight: 700; border-radius: 20px; padding: 3px 10px;">
                  🔁 Callback Requested
                </button>
                <button type="button" class="btn btn-sm" onclick="window._scrmApplyOutcomeChip('Quotation / Price Sent', 'proposal')" style="background: rgba(20, 184, 166, 0.15); border: 1px solid rgba(20, 184, 166, 0.4); color: #2dd4bf; font-size: 11.5px; font-weight: 700; border-radius: 20px; padding: 3px 10px;">
                  💰 Quotation Sent
                </button>
                <button type="button" class="btn btn-sm" onclick="window._scrmApplyOutcomeChip('Not Interested', 'lost')" style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); color: #f87171; font-size: 11.5px; font-weight: 700; border-radius: 20px; padding: 3px 10px;">
                  ❌ Not Interested
                </button>
              </div>

              <textarea id="scrmNewCommentInput" class="form-control" rows="2" placeholder="Type comments or updates on this customer lead..." style="background: #0f172a; border-color: #475569; color: #ffffff; font-size: 13px;"></textarea>
            </div>

            <!-- COMMENTS & NOTES TIMELINE LIST -->
            <div style="font-size: 12.5px; font-weight: 800; color: #cbd5e1; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between;">
              <span><i class="fa-solid fa-history me-1 text-info"></i> Activity &amp; Comments History</span>
              <span id="scrmTimelineCount" style="font-size: 11px; color: #94a3b8; font-weight: 500;">0 entries</span>
            </div>

            <div id="scrmNotesTimelineContainer" style="display: flex; flex-direction: column; gap: 10px;">
              <!-- Populated dynamically -->
            </div>
          </div>

          <!-- TAB 3: FIELD-WISE CHANGES & AUDIT -->
          <div id="scrmTabContentAudit" style="display: none;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; background: rgba(15, 23, 42, 0.5); border: 1px solid #334155; border-radius: 10px; padding: 10px 14px;">
              <div style="font-size: 12px; font-weight: 800; color: #fbbf24; text-transform: uppercase; letter-spacing: 0.5px; display: flex; align-items: center; gap: 6px;">
                <i class="fa-solid fa-clock-rotate-left"></i> Field-Wise Changes History
              </div>
              <div style="font-size: 11.5px; color: #94a3b8;">
                Changes made by attendants during calls &amp; CRM updates
              </div>
            </div>
            <div id="scrmAuditListContainer">
              <!-- Populated dynamically by renderAuditList -->
            </div>
          </div>

        </div>

        <!-- FOOTER -->
        <div style="
          background: #0f172a;
          border-top: 1px solid #334155;
          padding: 14px 20px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          flex-wrap: wrap;
        ">
          <div>
            <button id="scrmOpenFullCrmBtn" type="button" class="btn btn-sm btn-outline-secondary" style="border-color: #475569; color: #94a3b8; font-size: 12px; font-weight: 600;">
              <i class="fa-solid fa-arrow-up-right-from-square me-1"></i> Open in Full CRM
            </button>
          </div>

          <div style="display: flex; align-items: center; gap: 10px;">
            <button type="button" class="btn btn-sm btn-secondary" onclick="window.closeSoftphoneCRMLeadModal()" style="background: #334155; border-color: #475569; color: #f8fafc; font-weight: 600; padding: 6px 16px;">
              Cancel
            </button>
            <button id="scrmSaveBtn" type="button" class="btn btn-sm btn-warning" onclick="window._scrmSaveLeadUpdates()" style="background: #f59e0b; border-color: #d97706; color: #0f172a; font-weight: 800; padding: 6px 20px; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3);">
              <i class="fa-solid fa-check"></i> <span id="scrmSaveBtnText">Save Lead Updates</span>
            </button>
          </div>
        </div>

      </div>
    `;

    document.body.appendChild(overlay);

    // Close on backdrop click
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        window.closeSoftphoneCRMLeadModal();
      }
    });

    // Escape key listener
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && overlay.style.display === 'flex') {
        window.closeSoftphoneCRMLeadModal();
      }
    });
  }

  /* ── Tab Switcher ─────────────────────────────────────────────────────────── */
  window._scrmSwitchTab = function (tabName) {
    const btnDetails = document.getElementById('scrmTabBtnDetails');
    const btnComments = document.getElementById('scrmTabBtnComments');
    const btnAudit = document.getElementById('scrmTabBtnAudit');
    const contentDetails = document.getElementById('scrmTabContentDetails');
    const contentComments = document.getElementById('scrmTabContentComments');
    const contentAudit = document.getElementById('scrmTabContentAudit');

    [btnDetails, btnComments, btnAudit].forEach(btn => {
      if (btn) {
        btn.style.background = 'transparent';
        btn.style.borderColor = 'transparent';
        btn.style.color = '#94a3b8';
      }
    });

    [contentDetails, contentComments, contentAudit].forEach(c => {
      if (c) c.style.display = 'none';
    });

    if (tabName === 'details') {
      if (btnDetails) {
        btnDetails.style.background = 'rgba(245, 158, 11, 0.15)';
        btnDetails.style.borderColor = 'rgba(245, 158, 11, 0.3)';
        btnDetails.style.color = '#fbbf24';
      }
      if (contentDetails) contentDetails.style.display = 'block';
    } else if (tabName === 'comments') {
      if (btnComments) {
        btnComments.style.background = 'rgba(245, 158, 11, 0.15)';
        btnComments.style.borderColor = 'rgba(245, 158, 11, 0.3)';
        btnComments.style.color = '#fbbf24';
      }
      if (contentComments) contentComments.style.display = 'block';
    } else if (tabName === 'audit') {
      if (btnAudit) {
        btnAudit.style.background = 'rgba(245, 158, 11, 0.15)';
        btnAudit.style.borderColor = 'rgba(245, 158, 11, 0.3)';
        btnAudit.style.color = '#fbbf24';
      }
      if (contentAudit) contentAudit.style.display = 'block';
    }
  };

  /* ── Outcome Chips ────────────────────────────────────────────────────────── */
  window._scrmApplyOutcomeChip = function (noteText, suggestedStatus) {
    const input = document.getElementById('scrmNewCommentInput');
    if (input) {
      const prev = input.value.trim();
      input.value = prev ? `${prev} | ${noteText}` : noteText;
      input.focus();
    }
    if (suggestedStatus) {
      const statusSelect = document.getElementById('scrmEditStatus');
      if (statusSelect) {
        statusSelect.value = suggestedStatus;
        window._scrmOnStatusChange(suggestedStatus);
      }
    }
  };

  window._scrmOnStatusChange = function (newStatus) {
    const badge = document.getElementById('scrmLeadStatusBadge');
    if (badge) {
      badge.textContent = STATUS_LABELS[newStatus] || newStatus;
      badge.style.background = STATUS_BADGE_COLORS[newStatus] || '#3b82f6';
    }
  };

  /* ── Load Categories ──────────────────────────────────────────────────────── */
  async function loadCategories(companyId) {
    try {
      const coId = companyId || (currentLead && currentLead.company_id) || 4;
      const res = await apiFetch(`/api/v1/signup-categories/list?company_id=${coId}`);
      if (res && res.success && Array.isArray(res.categories)) {
        categoriesCache = res.categories;
        const sel = document.getElementById('scrmEditCategory');
        if (sel) {
          const curVal = sel.value;
          sel.innerHTML = '<option value="">Select Category…</option>';
          res.categories.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.name;
            sel.appendChild(opt);
          });
          if (curVal) sel.value = curVal;
        }
      }
    } catch (e) {
      console.warn('[CRM-MODAL] Categories load warning:', e.message);
    }
  }

  /* ── Render Notes List ────────────────────────────────────────────────────── */
  function renderNotesList(notes, lead) {
    const container = document.getElementById('scrmNotesTimelineContainer');
    const countBadge = document.getElementById('scrmNotesCountBadge');
    const countLabel = document.getElementById('scrmTimelineCount');
    if (!container) return;

    let items = [];

    // 1. Looking For
    if (lead && lead.looking_for && String(lead.looking_for).trim()) {
      items.push({
        type: 'Looking For',
        color: '#8b5cf6',
        bg: 'rgba(139, 92, 246, 0.1)',
        border: 'rgba(139, 92, 246, 0.3)',
        author: 'Lead Requirement',
        time: lead.created_at,
        content: String(lead.looking_for).trim()
      });
    }

    // 2. Recent Comments
    if (lead && lead.recent_comments && String(lead.recent_comments).trim()) {
      items.push({
        type: 'Recent Comment',
        color: '#0ea5e9',
        bg: 'rgba(14, 165, 233, 0.1)',
        border: 'rgba(14, 165, 233, 0.3)',
        author: 'Staff Update',
        time: lead.updated_at || lead.created_at,
        content: String(lead.recent_comments).trim()
      });
    }

    // 3. Notes from DB
    if (Array.isArray(notes)) {
      notes.forEach(n => {
        const text = n.note || n.content || '';
        if (!text.trim()) return;
        const author = n.created_by_name || n.created_by_id || n.created_by_type || 'Staff';
        items.push({
          type: n.note_type || 'Note',
          color: '#10b981',
          bg: 'rgba(16, 185, 129, 0.08)',
          border: 'rgba(16, 185, 129, 0.25)',
          author: author,
          time: n.created_at,
          content: text
        });
      });
    }

    const totalCount = items.length;
    if (countBadge) countBadge.textContent = totalCount;
    if (countLabel) countLabel.textContent = `${totalCount} item${totalCount === 1 ? '' : 's'}`;

    if (!items.length) {
      container.innerHTML = `
        <div style="text-align: center; padding: 24px; color: #64748b; font-size: 13px;">
          <i class="fa-solid fa-comment-slash fa-lg mb-2" style="display: block; opacity: 0.6;"></i>
          No comments or updates recorded on this lead yet. Use the box above to add the first comment.
        </div>
      `;
      return;
    }

    container.innerHTML = items.map(item => `
      <div style="
        background: ${item.bg};
        border-left: 3px solid ${item.color};
        border-top: 1px solid ${item.border};
        border-right: 1px solid ${item.border};
        border-bottom: 1px solid ${item.border};
        border-radius: 8px;
        padding: 10px 14px;
      ">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; flex-wrap: wrap; gap: 6px;">
          <span style="font-size: 11px; font-weight: 700; color: ${item.color}; text-transform: uppercase; letter-spacing: 0.4px;">
            <i class="fa-solid fa-tag me-1"></i>${esc(item.type)}
          </span>
          <div style="font-size: 11px; color: #94a3b8; display: flex; align-items: center; gap: 8px;">
            <span><i class="fa-solid fa-user me-1 text-secondary"></i>${esc(item.author)}</span>
            <span>·</span>
            <span><i class="fa-solid fa-clock me-1 text-secondary"></i>${formatIST(item.time)}</span>
          </div>
        </div>
        <div style="font-size: 12.5px; color: #f1f5f9; line-height: 1.5; white-space: pre-wrap; word-break: break-word;">${esc(item.content)}</div>
      </div>
    `).join('');
  }

  /* ── Field Changes Audit Renderer ─────────────────────────────────────────── */
  function renderAuditList(changes = []) {
    const container = document.getElementById('scrmAuditListContainer');
    const countBadge = document.getElementById('scrmAuditCountBadge');
    if (countBadge) countBadge.textContent = changes.length;
    if (!container) return;

    if (!changes || changes.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 48px 20px; background: rgba(15, 23, 42, 0.4); border: 1px dashed #334155; border-radius: 12px;">
          <div style="width: 48px; height: 48px; border-radius: 50%; background: rgba(100, 116, 139, 0.15); display: inline-flex; align-items: center; justify-content: center; color: #94a3b8; font-size: 20px; margin-bottom: 12px;">
            <i class="fa-solid fa-file-circle-check"></i>
          </div>
          <div style="font-size: 14px; font-weight: 700; color: #e2e8f0; margin-bottom: 4px;">No Details Updated</div>
          <div style="font-size: 12px; color: #64748b;">No field changes or comments were updated for this lead yet.</div>
        </div>
      `;
      return;
    }

    // Group changes into sessions (same attendant & within the same 60 seconds)
    const sessions = [];
    changes.forEach(c => {
      const dtStr = c.changed_at ? String(c.changed_at).slice(0, 16) : 'unknown';
      const authorStr = c.changed_by_name || 'Staff';
      const key = `${dtStr}_${authorStr}`;
      let group = sessions.find(s => s.key === key);
      if (!group) {
        group = {
          key,
          author: authorStr,
          emp_code: c.changed_by_id,
          time_iso: c.changed_at,
          items: []
        };
        sessions.push(group);
      }
      group.items.push(c);
    });

    container.innerHTML = sessions.map(s => {
      const timeFormatted = formatIST(s.time_iso);
      return `
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid #334155; border-radius: 12px; padding: 14px 16px; margin-bottom: 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.25);">
          <!-- Session Header: Attendant + Time -->
          <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 10px; margin-bottom: 10px; flex-wrap: wrap; gap: 8px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <div style="width: 28px; height: 28px; border-radius: 50%; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.3); display: flex; align-items: center; justify-content: center; color: #38bdf8; font-size: 12px;">
                <i class="fa-solid fa-user-check"></i>
              </div>
              <div>
                <span style="font-size: 12.5px; font-weight: 700; color: #f8fafc;">${esc(s.author)}</span>
                ${s.emp_code && !s.author.includes(s.emp_code) ? `<span style="font-size: 11px; color: #94a3b8; margin-left: 4px; font-family: monospace;">(${esc(s.emp_code)})</span>` : ''}
              </div>
            </div>
            <div style="font-size: 11.5px; color: #fbbf24; font-weight: 600; display: inline-flex; align-items: center; gap: 5px; background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 12px; padding: 2px 10px;">
              <i class="fa-regular fa-clock fa-xs"></i> ${esc(timeFormatted)}
            </div>
          </div>

          <!-- Changes Table -->
          <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
              <thead>
                <tr style="color: #94a3b8; font-weight: 700; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid rgba(255,255,255,0.06);">
                  <th style="padding: 6px 8px; text-align: left; width: 30%;">Field Changed</th>
                  <th style="padding: 6px 8px; text-align: left; width: 35%;">Before (Previous)</th>
                  <th style="padding: 6px 8px; text-align: left; width: 35%;">Present (Updated)</th>
                </tr>
              </thead>
              <tbody>
                ${s.items.map(item => {
                  const isComment = item.change_category === 'comments' || (item.field_name && item.field_name.includes('comment'));
                  const beforeDisp = item.before_display || '—';
                  const presentDisp = item.present_display || '—';
                  return `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.04);">
                      <td style="padding: 8px; font-weight: 700; color: #cbd5e1; vertical-align: top;">
                        <span style="display: inline-flex; align-items: center; gap: 5px;">
                          ${isComment ? '<i class="fa-solid fa-comment-dots text-info fa-xs"></i>' : '<i class="fa-solid fa-pen-to-square text-warning fa-xs"></i>'}
                          ${esc(item.field_label || item.field_name)}
                        </span>
                      </td>
                      <td style="padding: 8px; vertical-align: top;">
                        <span style="display: inline-block; padding: 2px 8px; border-radius: 6px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.25); color: #f87171; font-family: ${isComment ? 'inherit' : 'monospace'}; font-size: 11.5px; max-width: 100%; word-break: break-word; white-space: pre-wrap;">
                          ${esc(beforeDisp)}
                        </span>
                      </td>
                      <td style="padding: 8px; vertical-align: top;">
                        <span style="display: inline-block; padding: 2px 8px; border-radius: 6px; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.35); color: #34d399; font-weight: 600; font-family: ${isComment ? 'inherit' : 'monospace'}; font-size: 11.5px; max-width: 100%; word-break: break-word; white-space: pre-wrap;">
                          ${esc(presentDisp)}
                        </span>
                      </td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;
    }).join('');
  }

  /* ── Open CRM Lead Modal Entrypoint ───────────────────────────────────────── */
  window.openSoftphoneCRMLeadModal = async function (leadId, phone = '', name = '', companyId = null, onSavedCallback = null) {
    if (!leadId) {
      alert('Lead ID is missing or invalid.');
      return;
    }

    currentLeadId = leadId;
    currentCompanyId = companyId;
    onSavedHook = onSavedCallback;

    ensureModalDOM();

    const overlay = document.getElementById('softphoneCrmLeadModalOverlay');
    const loadingState = document.getElementById('scrmLoadingState');
    const detailsTab = document.getElementById('scrmTabContentDetails');
    const commentsTab = document.getElementById('scrmTabContentComments');

    // Show overlay immediately
    overlay.style.display = 'flex';
    requestAnimationFrame(() => {
      overlay.style.opacity = '1';
      document.getElementById('softphoneCrmLeadModalCard').style.transform = 'scale(1)';
    });

    loadingState.style.display = 'block';
    detailsTab.style.display = 'none';
    commentsTab.style.display = 'none';
    window._scrmSwitchTab('details');

    // Initial placeholder bindings
    document.getElementById('scrmLeadName').textContent = name || 'Loading…';
    document.getElementById('scrmLeadIdBadge').textContent = `#${leadId}`;
    const cleanPhone = (phone || '').replace(/\D/g, '').slice(-10);
    document.getElementById('scrmLeadPhoneText').innerHTML = `<i class="fa-solid fa-phone me-1"></i>${cleanPhone || '—'}`;

    // Header buttons action bindings
    const callBtn = document.getElementById('scrmHeaderCallBtn');
    if (callBtn) {
      callBtn.onclick = () => {
        if (cleanPhone) {
          if (typeof window.triggerDialFromBtn === 'function') {
            const fakeBtn = document.createElement('button');
            fakeBtn.dataset.phone = cleanPhone;
            fakeBtn.dataset.name = name;
            fakeBtn.dataset.leadId = leadId;
            window.triggerDialFromBtn(fakeBtn);
          } else if (window.PlivoSoftphone && typeof window.PlivoSoftphone.makeCall === 'function') {
            window.PlivoSoftphone.makeCall(cleanPhone, leadId, name);
          } else {
            window.location.href = `tel:${cleanPhone}`;
          }
        }
      };
    }

    const waBtn = document.getElementById('scrmHeaderWaBtn');
    if (waBtn) {
      waBtn.onclick = () => {
        if (typeof window.openLeadWAModal === 'function') {
          window.openLeadWAModal(leadId, cleanPhone, name, companyId);
        } else {
          window.open(`https://wa.me/91${cleanPhone}`, '_blank');
        }
      };
    }

    const fullCrmBtn = document.getElementById('scrmOpenFullCrmBtn');
    if (fullCrmBtn) {
      fullCrmBtn.onclick = () => {
        window.open(`/staff_my_leads.html?lead_id=${leadId}`, '_blank');
      };
    }

    // Clear comment input
    const commentInput = document.getElementById('scrmNewCommentInput');
    if (commentInput) commentInput.value = '';

    try {
      // 1. Fetch Lead Details
      const coQuery = companyId ? `?company_id=${companyId}` : '';
      const leadRes = await apiFetch(`/api/v1/crm/leads/${leadId}${coQuery}`);
      if (!leadRes || !leadRes.data) throw new Error('Lead record not found');
      const lead = leadRes.data;
      currentLead = lead;
      currentCompanyId = lead.company_id || companyId;

      // 2. Load Categories
      await loadCategories(currentCompanyId);

      // 3. Populate Header
      document.getElementById('scrmLeadName').textContent = lead.name || name || 'Customer Lead';
      document.getElementById('scrmLeadIdBadge').textContent = `#${lead.id}`;
      
      const st = lead.status || 'new';
      window._scrmOnStatusChange(st);

      const pri = lead.priority || 'normal';
      const priBadge = document.getElementById('scrmLeadPriorityBadge');
      if (priBadge) {
        priBadge.textContent = pri.charAt(0).toUpperCase() + pri.slice(1);
        priBadge.style.color = pri === 'high' ? '#f87171' : (pri === 'medium' ? '#fbbf24' : '#cbd5e1');
        priBadge.style.borderColor = pri === 'high' ? '#ef4444' : (pri === 'medium' ? '#f59e0b' : '#475569');
      }

      const pVal = lead.phone || phone || '';
      const pClean = pVal.replace(/\D/g, '').slice(-10);
      document.getElementById('scrmLeadPhoneText').innerHTML = `<i class="fa-solid fa-phone me-1"></i>${pClean || '—'}`;
      document.getElementById('scrmLeadCategoryText').innerHTML = `<i class="fa-solid fa-tag me-1 text-warning"></i>${esc(lead.category_name || 'General')}`;
      
      const loc = [lead.city, lead.area].filter(Boolean).join(', ');
      document.getElementById('scrmLeadLocationText').innerHTML = `<i class="fa-solid fa-location-dot me-1 text-danger"></i>${esc(loc || 'Location —')}`;

      // 4. Populate Form Fields
      const statusSelect = document.getElementById('scrmEditStatus');
      if (statusSelect) {
        statusSelect.value = st;
        // Dynamically add option if missing to prevent stale value overwrite
        if (statusSelect.value !== st) {
          const opt = document.createElement('option');
          opt.value = st;
          opt.textContent = st.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
          statusSelect.appendChild(opt);
          statusSelect.value = st;
        }
      }

      const priSelect = document.getElementById('scrmEditPriority');
      if (priSelect) priSelect.value = pri;

      const catSelect = document.getElementById('scrmEditCategory');
      if (catSelect && lead.category_id) catSelect.value = lead.category_id;

      const nameInput = document.getElementById('scrmEditName');
      if (nameInput) nameInput.value = lead.name || '';

      const emailInput = document.getElementById('scrmEditEmail');
      if (emailInput) emailInput.value = lead.email || '';

      const phoneInput = document.getElementById('scrmEditPhone');
      if (phoneInput) phoneInput.value = lead.phone || phone || '';

      const altPhoneInput = document.getElementById('scrmEditAltPhone');
      if (altPhoneInput) altPhoneInput.value = lead.alternate_phone || '';

      const cityInput = document.getElementById('scrmEditCity');
      if (cityInput) cityInput.value = lead.city || '';

      const areaInput = document.getElementById('scrmEditArea');
      if (areaInput) areaInput.value = lead.area || '';

      const sourceInput = document.getElementById('scrmEditSource');
      if (sourceInput) sourceInput.value = lead.source || '';

      const bMinInput = document.getElementById('scrmEditBudgetMin');
      if (bMinInput) bMinInput.value = lead.budget_min != null ? lead.budget_min : '';

      const bMaxInput = document.getElementById('scrmEditBudgetMax');
      if (bMaxInput) bMaxInput.value = lead.budget_max != null ? lead.budget_max : '';

      const descInput = document.getElementById('scrmEditDescription');
      if (descInput) descInput.value = lead.description || '';

      const reqInput = document.getElementById('scrmEditRequirements');
      if (reqInput) reqInput.value = lead.requirements || '';

      const folInput = document.getElementById('scrmEditFollowup');
      if (folInput) {
        if (lead.next_followup_date) {
          try {
            folInput.value = String(lead.next_followup_date).replace(' ', 'T').slice(0, 16);
          } catch (e) {
            folInput.value = '';
          }
        } else {
          folInput.value = '';
        }
      }

      // 5. Populate Notes History
      renderNotesList(lead.notes || [], lead);

      // 6. Populate Field Changes Audit History
      let auditChanges = lead.field_audit_changes;
      if (!Array.isArray(auditChanges)) {
        try {
          const auditRes = await apiFetch(`/api/v1/crm/leads/${leadId}/field-audit-history${coQuery}`);
          auditChanges = auditRes?.changes || [];
        } catch (e) {
          auditChanges = [];
        }
      }
      renderAuditList(auditChanges || []);

      // Hide spinner, show content
      loadingState.style.display = 'none';
      detailsTab.style.display = 'block';

    } catch (err) {
      console.error('[CRM-MODAL] Error opening modal:', err);
      loadingState.innerHTML = `
        <div style="color: #ef4444; padding: 30px;">
          <i class="fa-solid fa-triangle-exclamation fa-2x mb-2"></i>
          <div style="font-weight: 700; font-size: 15px;">Failed to Load Lead Details</div>
          <div style="font-size: 12px; margin-top: 6px; opacity: 0.85;">${esc(err.message)}</div>
          <button type="button" class="btn btn-sm btn-outline-light mt-3" onclick="window.closeSoftphoneCRMLeadModal()">Close</button>
        </div>
      `;
    }
  };

  // Alias
  window.openCRMLeadModal = window.openSoftphoneCRMLeadModal;

  /* ── Close Modal ──────────────────────────────────────────────────────────── */
  window.closeSoftphoneCRMLeadModal = function () {
    const overlay = document.getElementById('softphoneCrmLeadModalOverlay');
    if (!overlay) return;
    overlay.style.opacity = '0';
    const card = document.getElementById('softphoneCrmLeadModalCard');
    if (card) card.style.transform = 'scale(0.96)';
    setTimeout(() => {
      overlay.style.display = 'none';
    }, 200);
  };

  /* ── Save Lead Updates ────────────────────────────────────────────────────── */
  window._scrmSaveLeadUpdates = async function () {
    if (!currentLeadId) return;

    const saveBtn = document.getElementById('scrmSaveBtn');
    const saveBtnText = document.getElementById('scrmSaveBtnText');
    const originalText = saveBtnText ? saveBtnText.textContent : 'Save Lead Updates';

    try {
      if (saveBtn) saveBtn.disabled = true;
      if (saveBtnText) saveBtnText.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span> Saving…';

      const effectiveCompanyId = currentCompanyId || (currentLead && currentLead.company_id) || 4;

      const payload = {
        name: document.getElementById('scrmEditName')?.value?.trim() || currentLead.name,
        email: document.getElementById('scrmEditEmail')?.value?.trim() || null,
        alternate_phone: document.getElementById('scrmEditAltPhone')?.value?.trim() || null,
        status: document.getElementById('scrmEditStatus')?.value || currentLead.status,
        priority: document.getElementById('scrmEditPriority')?.value || currentLead.priority,
        city: document.getElementById('scrmEditCity')?.value?.trim() || null,
        area: document.getElementById('scrmEditArea')?.value?.trim() || null,
        source: document.getElementById('scrmEditSource')?.value?.trim() || null,
        description: document.getElementById('scrmEditDescription')?.value?.trim() || null,
        requirements: document.getElementById('scrmEditRequirements')?.value?.trim() || null
      };

      const catVal = document.getElementById('scrmEditCategory')?.value;
      if (catVal) payload.category_id = parseInt(catVal, 10);

      const bMin = document.getElementById('scrmEditBudgetMin')?.value;
      if (bMin !== '' && !isNaN(bMin)) payload.budget_min = parseFloat(bMin);

      const bMax = document.getElementById('scrmEditBudgetMax')?.value;
      if (bMax !== '' && !isNaN(bMax)) payload.budget_max = parseFloat(bMax);

      const folVal = document.getElementById('scrmEditFollowup')?.value;
      if (folVal) payload.next_followup_date = folVal;

      // 1. Submit PUT /crm/leads/{lead_id}?company_id={coId}
      const putRes = await apiFetch(`/api/v1/crm/leads/${currentLeadId}?company_id=${effectiveCompanyId}`, {
        method: 'PUT',
        body: JSON.stringify(payload)
      });

      // 2. Check if a new note comment was entered
      const newComment = document.getElementById('scrmNewCommentInput')?.value?.trim();
      if (newComment) {
        await apiFetch(`/api/v1/crm/leads/${currentLeadId}/notes?company_id=${effectiveCompanyId}`, {
          method: 'POST',
          body: JSON.stringify({
            note: newComment,
            is_private: false
          })
        });
        document.getElementById('scrmNewCommentInput').value = '';
      }

      showToast(`Lead #${currentLeadId} updated successfully!`);

      // Update local state
      if (putRes && putRes.data) {
        currentLead = { ...currentLead, ...putRes.data };
      }

      // Notify external caller/table
      if (typeof onSavedHook === 'function') {
        try {
          onSavedHook(currentLead);
        } catch (e) {
          console.warn('[CRM-MODAL] onSavedHook error:', e);
        }
      }

      // Dispatch global custom event
      document.dispatchEvent(new CustomEvent('crmLeadUpdated', {
        detail: {
          leadId: currentLeadId,
          status: payload.status,
          priority: payload.priority,
          name: payload.name,
          updatedLead: currentLead
        }
      }));

      // Reload lead details in background to refresh notes list
      const refreshedRes = await apiFetch(`/api/v1/crm/leads/${currentLeadId}?company_id=${effectiveCompanyId}`);
      if (refreshedRes && refreshedRes.data) {
        currentLead = refreshedRes.data;
        renderNotesList(currentLead.notes || [], currentLead);
        renderAuditList(currentLead.field_audit_changes || []);
        window._scrmOnStatusChange(currentLead.status);
      }

    } catch (err) {
      console.error('[CRM-MODAL] Save error:', err);
      showToast(`Failed to save: ${err.message}`, 'error');
    } finally {
      if (saveBtn) saveBtn.disabled = false;
      if (saveBtnText) saveBtnText.textContent = originalText;
    }
  };

})();
