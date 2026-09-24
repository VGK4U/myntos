/**
 * Universal Lead History Modal — MyntOS Single Source of Truth
 * Exactly Three Primary Tabs:
 *   1. Calls & Recordings (Plivo WebRTC, Native GSM, MyOperator, AutoDialer with audio player)
 *   2. Messages / Chat (Inbound & Outbound WhatsApp/SMS conversation feed)
 *   3. Lead Change History (Timeline of Audit Edits, Notes, Follow-ups, Assignments with sub-filters)
 *
 * Supported Entities:
 *   - 'crm_lead': Standard CRM Leads across all categories and workflows
 *   - 'vgk_member': VGK Channel Partners (OfficialPartner) preserving existing member data
 *
 * Global Entrypoints:
 *   window.openUniversalHistory({ entityType, entityId, name, phone, category, status, stage, assignedTo })
 *   window.closeUniversalHistory()
 */

(function () {
  'use strict';

  var _currentEntity = null;
  var _activeTab = 'calls'; // 'calls' | 'messages' | 'changes'
  var _changesSubfilter = 'all'; // 'all' | 'notes' | 'followups' | 'assignments' | 'audit'
  var _activeAudio = null;
  var _cache = { calls: null, messages: null, changes: null, summary: null };

  function _getAuthToken() {
    if (typeof localStorage === 'undefined') return '';
    var cookieToken = '';
    if (typeof document !== 'undefined') {
      var m = (document.cookie || '').match(/(?:staff_token|token|access_token)=([^;]+)/);
      if (m && m[1]) cookieToken = decodeURIComponent(m[1].trim());
    }
    return (
      localStorage.getItem('staff_token') ||
      localStorage.getItem('token') ||
      (typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('staff_token') : '') ||
      localStorage.getItem('staff_auth_token') ||
      (typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('staff_auth_token') : '') ||
      localStorage.getItem('authToken') ||
      localStorage.getItem('staffToken') ||
      localStorage.getItem('partner_token') ||
      (typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('partner_token') : '') ||
      localStorage.getItem('vgkAuthToken') ||
      localStorage.getItem('auth_token') ||
      cookieToken ||
      ''
    );
  }

  function _esc(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function _fmtDate(isoStr) {
    if (!isoStr) return '—';
    try {
      var d = new Date(isoStr);
      if (isNaN(d.getTime())) return String(isoStr);
      return d.toLocaleString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (_) {
      return String(isoStr);
    }
  }

  function _formatDuration(seconds) {
    var s = parseInt(seconds, 10) || 0;
    if (s <= 0) return '0s';
    var hrs = Math.floor(s / 3600);
    var mins = Math.floor((s % 3600) / 60);
    var remSec = s % 60;
    if (hrs > 0) {
      return (hrs + 'h ' + (mins > 0 ? mins + 'm ' : '') + (remSec > 0 ? remSec + 's' : '')).trim();
    }
    if (mins > 0) {
      return (mins + 'm ' + (remSec > 0 ? remSec + 's' : '')).trim();
    }
    return remSec + 's';
  }

  function _stopAudio() {
    if (_activeAudio) {
      try {
        _activeAudio.pause();
      } catch (_) {}
      _activeAudio = null;
    }
    // Also pause any audio elements in the modal
    var audios = document.querySelectorAll('#uhmModalRoot audio');
    audios.forEach(function (a) {
      try {
        a.pause();
      } catch (_) {}
    });
  }

  function _injectModalDOM() {
    if (document.getElementById('uhmModalRoot')) return;

    var style = document.createElement('style');
    style.id = 'uhmModalStyles';
    style.textContent = `
      #uhmModalRoot {
        position: fixed;
        inset: 0;
        z-index: 100000001;
        display: none;
        align-items: center;
        justify-content: center;
        background: rgba(15, 23, 42, 0.72);
        backdrop-filter: blur(4px);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      }
      #uhmDialog {
        background: #ffffff;
        width: 95%;
        max-width: 860px;
        height: 85vh;
        max-height: 850px;
        border-radius: 14px;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        display: flex;
        flex-direction: column;
        overflow: hidden;
        animation: uhmFadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);
      }
      @keyframes uhmFadeIn {
        from { opacity: 0; transform: scale(0.97); }
        to { opacity: 1; transform: scale(1); }
      }
      .uhm-header {
        padding: 16px 20px;
        background: #f8fafc;
        border-bottom: 1px solid #e2e8f0;
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .uhm-title-area {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }
      .uhm-name-row {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .uhm-name {
        font-size: 18px;
        font-weight: 700;
        color: #0f172a;
      }
      .uhm-badge {
        font-size: 11px;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 9999px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
      .uhm-badge-lead { background: #dbeafe; color: #1e40af; }
      .uhm-badge-vgk { background: #f3e8ff; color: #6b21a8; }
      .uhm-meta-row {
        font-size: 13px;
        color: #64748b;
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
      }
      .uhm-close-btn {
        background: none;
        border: none;
        font-size: 22px;
        color: #64748b;
        cursor: pointer;
        padding: 4px 8px;
        border-radius: 6px;
        line-height: 1;
      }
      .uhm-close-btn:hover {
        background: #e2e8f0;
        color: #0f172a;
      }
      .uhm-tabs-bar {
        display: flex;
        border-bottom: 2px solid #e2e8f0;
        background: #ffffff;
        padding: 0 16px;
      }
      .uhm-tab-btn {
        padding: 12px 18px;
        font-size: 14px;
        font-weight: 600;
        color: #64748b;
        background: none;
        border: none;
        border-bottom: 2px solid transparent;
        margin-bottom: -2px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 8px;
        transition: all 0.15s ease;
      }
      .uhm-tab-btn:hover {
        color: #1e293b;
      }
      .uhm-tab-btn.active {
        color: #2563eb;
        border-bottom-color: #2563eb;
      }
      .uhm-count-badge {
        background: #f1f5f9;
        color: #475569;
        font-size: 11px;
        padding: 1px 7px;
        border-radius: 9999px;
      }
      .uhm-tab-btn.active .uhm-count-badge {
        background: #dbeafe;
        color: #1e40af;
      }
      .uhm-subfilter-bar {
        display: flex;
        gap: 6px;
        padding: 10px 18px;
        background: #f8fafc;
        border-bottom: 1px solid #e2e8f0;
        overflow-x: auto;
      }
      .uhm-subchip {
        font-size: 12px;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 6px;
        border: 1px solid #cbd5e1;
        background: #ffffff;
        color: #475569;
        cursor: pointer;
        white-space: nowrap;
      }
      .uhm-subchip.active {
        background: #2563eb;
        color: #ffffff;
        border-color: #2563eb;
      }
      .uhm-tab-content {
        flex: 1;
        overflow-y: auto;
        padding: 16px 20px;
        background: #f8fafc;
      }
      .uhm-empty-state {
        text-align: center;
        padding: 40px 20px;
        color: #94a3b8;
        font-size: 14px;
      }
      /* Calls list cards */
      .uhm-call-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 10px;
        display: flex;
        flex-direction: column;
        gap: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
      }
      .uhm-call-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .uhm-call-meta {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .uhm-direction-icon {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 11px;
      }
      .uhm-dir-out { background: #e0f2fe; color: #0369a1; }
      .uhm-dir-in { background: #dcfce7; color: #15803d; }
      .uhm-call-source-tag {
        font-size: 11px;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 4px;
        background: #f1f5f9;
        color: #475569;
      }
      /* Chat layout */
      .uhm-chat-container {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      .uhm-chat-row {
        display: flex;
        flex-direction: column;
        max-width: 82%;
      }
      .uhm-chat-row.inbound {
        align-self: flex-start;
      }
      .uhm-chat-row.outbound {
        align-self: flex-end;
      }
      .uhm-bubble {
        padding: 10px 14px;
        border-radius: 12px;
        font-size: 13px;
        line-height: 1.45;
        word-break: break-word;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
      }
      .uhm-chat-row.inbound .uhm-bubble {
        background: #ffffff;
        color: #0f172a;
        border: 1px solid #e2e8f0;
        border-top-left-radius: 2px;
      }
      .uhm-chat-row.outbound .uhm-bubble {
        background: #d9fdd3;
        color: #0f172a;
        border: 1px solid #bbf7d0;
        border-top-right-radius: 2px;
      }
      .uhm-chat-sender {
        font-size: 11px;
        font-weight: 600;
        margin-bottom: 3px;
        color: #64748b;
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .uhm-chat-row.outbound .uhm-chat-sender {
        justify-content: flex-end;
      }
      .uhm-chat-meta-bar {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 6px;
        margin-top: 6px;
        padding-top: 4px;
        border-top: 1px solid rgba(0,0,0,0.05);
        font-size: 11px;
      }
      .uhm-chat-time {
        font-size: 10.5px;
        color: #64748b;
      }
      .uhm-status-badge {
        display: inline-flex;
        align-items: center;
        gap: 3px;
        font-size: 11px;
        font-weight: 700;
      }
      .uhm-status-failed {
        background: #fee2e2;
        color: #dc2626;
        padding: 2px 7px;
        border-radius: 4px;
        border: 1px solid #fecaca;
        font-size: 11px;
        font-weight: 700;
        cursor: help;
        display: inline-flex;
        align-items: center;
        gap: 4px;
      }
      .uhm-error-snippet {
        margin-top: 6px;
        padding: 6px 10px;
        background: #fff1f2;
        border-left: 3px solid #ef4444;
        border-radius: 4px;
        color: #b91c1c;
        font-size: 11.5px;
        line-height: 1.35;
      }
      .uhm-media-img-box {
        margin-top: 8px;
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #cbd5e1;
        background: #f8fafc;
        max-width: 320px;
      }
      .uhm-media-img-box img {
        width: 100%;
        max-height: 240px;
        object-fit: cover;
        display: block;
        cursor: pointer;
        transition: opacity 0.2s;
      }
      .uhm-media-img-box img:hover {
        opacity: 0.92;
      }
      .uhm-media-img-bar {
        padding: 5px 10px;
        background: rgba(255,255,255,0.95);
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-top: 1px solid #e2e8f0;
        font-size: 11px;
      }
      .uhm-media-name {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 200px;
        font-weight: 600;
        color: #334155;
      }
      .uhm-dl-btn {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        color: #059669;
        font-weight: 700;
        text-decoration: none;
        padding: 2px 6px;
        border-radius: 4px;
        transition: background 0.15s;
        font-size: 11px;
      }
      .uhm-dl-btn:hover {
        background: #ecfdf5;
        color: #047857;
      }
      .uhm-media-doc-box {
        margin-top: 8px;
        padding: 8px 12px;
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        max-width: 340px;
      }
      .uhm-doc-view-btn {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 8px;
        background: #f1f5f9;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        color: #1e293b;
        text-decoration: none;
        font-size: 11.5px;
        font-weight: 600;
      }
      .uhm-doc-view-btn:hover {
        background: #e2e8f0;
      }
      /* Timeline / Change history */
      .uhm-timeline-item {
        position: relative;
        padding-left: 24px;
        padding-bottom: 16px;
        border-left: 2px solid #e2e8f0;
      }
      .uhm-timeline-item:last-child {
        border-left-color: transparent;
      }
      .uhm-timeline-dot {
        position: absolute;
        left: -6px;
        top: 2px;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #2563eb;
      }
      .uhm-timeline-dot.dot-audit { background: #7c3aed; }
      .uhm-timeline-dot.dot-note { background: #059669; }
      .uhm-timeline-dot.dot-followup { background: #d97706; }
      .uhm-timeline-dot.dot-assignment { background: #2563eb; }
      .uhm-timeline-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 10px 12px;
      }
      .uhm-timeline-title {
        font-size: 13px;
        font-weight: 600;
        color: #1e293b;
        display: flex;
        justify-content: space-between;
      }
      .uhm-timeline-body {
        font-size: 12px;
        color: #475569;
        margin-top: 4px;
        white-space: pre-wrap;
      }
    `;
    document.head.appendChild(style);

    var root = document.createElement('div');
    root.id = 'uhmModalRoot';
    root.innerHTML = `
      <div id="uhmDialog">
        <div class="uhm-header">
          <div class="uhm-title-area">
            <div class="uhm-name-row">
              <span id="uhmEntityName" class="uhm-name">Lead History</span>
              <span id="uhmEntityBadge" class="uhm-badge uhm-badge-lead">CRM Lead</span>
            </div>
            <div class="uhm-meta-row">
              <span id="uhmEntityPhone"><i class="fas fa-phone-alt"></i> —</span>
              <span id="uhmEntityCategory"><i class="fas fa-tag"></i> —</span>
              <span id="uhmEntityStatus"><i class="fas fa-info-circle"></i> —</span>
              <span id="uhmEntityAssigned"><i class="fas fa-user-check"></i> —</span>
            </div>
          </div>
          <button class="uhm-close-btn" onclick="window.closeUniversalHistory()" title="Close (Esc)">&times;</button>
        </div>

        <div class="uhm-tabs-bar">
          <button class="uhm-tab-btn active" id="uhmTabCalls" onclick="window.switchUniversalHistoryTab('calls')">
            <i class="fas fa-phone"></i> Calls & Recordings
            <span id="uhmCountCalls" class="uhm-count-badge">0</span>
          </button>
          <button class="uhm-tab-btn" id="uhmTabMessages" onclick="window.switchUniversalHistoryTab('messages')">
            <i class="fas fa-comments"></i> Messages / Chat
            <span id="uhmCountMessages" class="uhm-count-badge">0</span>
          </button>
          <button class="uhm-tab-btn" id="uhmTabChanges" onclick="window.switchUniversalHistoryTab('changes')">
            <i class="fas fa-history"></i> Lead Change History
            <span id="uhmCountChanges" class="uhm-count-badge">0</span>
          </button>
        </div>

        <div id="uhmSubfilterBar" class="uhm-subfilter-bar" style="display:none">
          <button class="uhm-subchip active" onclick="window.setUniversalHistorySubfilter('all')">All Changes</button>
          <button class="uhm-subchip" onclick="window.setUniversalHistorySubfilter('calls')">Calls</button>
          <button class="uhm-subchip" onclick="window.setUniversalHistorySubfilter('notes')">Notes</button>
          <button class="uhm-subchip" onclick="window.setUniversalHistorySubfilter('followups')">Follow-ups</button>
          <button class="uhm-subchip" onclick="window.setUniversalHistorySubfilter('assignments')">Assignments</button>
          <button class="uhm-subchip" onclick="window.setUniversalHistorySubfilter('audit')">Field Edits</button>
        </div>

        <div id="uhmTabContent" class="uhm-tab-content">
          <div class="uhm-empty-state"><i class="fas fa-spinner fa-spin me-2"></i>Loading history…</div>
        </div>
      </div>
    `;

    root.addEventListener('click', function (e) {
      if (e.target === root) {
        window.closeUniversalHistory();
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && root.style.display === 'flex') {
        window.closeUniversalHistory();
      }
    });

    document.body.appendChild(root);
  }

  function _renderCallFromBadge(c) {
    var page = (c.dialed_page || c.call_from || c.source || '').trim();
    var lower = page.toLowerCase();
    var devId = (c.device_call_id || c.call_session_id || '').toLowerCase();
    var type = (c.call_type || c.direction || '').toUpperCase();

    // 1. Auto Dialer
    if (lower.includes('auto') || lower.includes('dialer') || devId.includes('cda_') || type === 'DIALER') {
      return '<span class="badge" style="background:#f5f3ff;color:#6b21a8;border:1px solid #ddd6fe;font-size:0.72rem;font-weight:600;padding:2px 7px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-robot me-1" style="color:#6b21a8;"></i>Auto Dialer</span>';
    }
    // 2. My Leads
    if (lower.includes('my lead') || lower === 'my leads') {
      return '<span class="badge" style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;font-size:0.72rem;font-weight:600;padding:2px 7px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-user-check me-1" style="color:#1d4ed8;"></i>My Leads</span>';
    }
    // 3. Staff Leads
    if (lower.includes('staff lead') || lower === 'staff leads') {
      return '<span class="badge" style="background:#f0fdf4;color:#15803d;border:1px solid #bbf7d0;font-size:0.72rem;font-weight:600;padding:2px 7px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-users me-1" style="color:#15803d;"></i>Staff Leads</span>';
    }
    // 4. CRM Dashboard
    if (lower.includes('crm dashboard') || lower.includes('dashboard')) {
      return '<span class="badge" style="background:#fdf2f8;color:#be185d;border:1px solid #fbcfe8;font-size:0.72rem;font-weight:600;padding:2px 7px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-chart-line me-1" style="color:#be185d;"></i>CRM Dashboard</span>';
    }
    // 5. Softphone Center / Hub
    if (lower.includes('softphone center') || lower.includes('softphone hub') || lower === 'softphone' || lower === 'plivo webrtc') {
      return '<span class="badge" style="background:#e0f2fe;color:#0369a1;border:1px solid #bae6fd;font-size:0.72rem;font-weight:600;padding:2px 7px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-headset me-1" style="color:#0369a1;"></i>Softphone Center</span>';
    }
    // 6. Operator Calls
    if (lower.includes('operator')) {
      return '<span class="badge" style="background:#fffbeb;color:#b45309;border:1px solid #fde68a;font-size:0.72rem;font-weight:600;padding:2px 7px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-head-side-headphones me-1" style="color:#b45309;"></i>Operator Calls</span>';
    }
    // 7. WhatsApp Center
    if (lower.includes('whatsapp')) {
      return '<span class="badge" style="background:#f0fdf4;color:#16a34a;border:1px solid #86efac;font-size:0.72rem;font-weight:600;padding:2px 7px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fab fa-whatsapp me-1" style="color:#16a34a;"></i>WhatsApp Center</span>';
    }
    // 8. Day Planner
    if (lower.includes('planner')) {
      return '<span class="badge" style="background:#faf5ff;color:#7e22ce;border:1px solid #e9d5ff;font-size:0.72rem;font-weight:600;padding:2px 7px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-calendar-day me-1" style="color:#7e22ce;"></i>Day Planner</span>';
    }
    // 9. Tasks
    if (lower.includes('task')) {
      return '<span class="badge" style="background:#f1f5f9;color:#334155;border:1px solid #cbd5e1;font-size:0.72rem;font-weight:600;padding:2px 7px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-tasks me-1" style="color:#334155;"></i>Tasks</span>';
    }
    // 10. Master Leads
    if (lower.includes('master')) {
      return '<span class="badge" style="background:#fef3c7;color:#92400e;border:1px solid #fcd34d;font-size:0.72rem;font-weight:600;padding:2px 7px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-database me-1" style="color:#92400e;"></i>Master Leads</span>';
    }
    // 11. Bank Wise Leads
    if (lower.includes('bank')) {
      return '<span class="badge" style="background:#ecfdf5;color:#065f46;border:1px solid #a7f3d0;font-size:0.72rem;font-weight:600;padding:2px 7px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-landmark me-1" style="color:#065f46;"></i>Bank Wise Leads</span>';
    }
    // 12. Inbound DID / Incoming
    if (lower.includes('inbound') || lower.includes('did') || type === 'INCOMING' || type === 'INBOUND') {
      return '<span class="badge" style="background:#ecfdf5;color:#047857;border:1px solid #a7f3d0;font-size:0.72rem;font-weight:600;padding:2px 7px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-phone-arrow-down-left me-1" style="color:#047857;"></i>Inbound DID</span>';
    }
    // 13. Mobile App / Native SIM
    if (lower.includes('mobile') || lower.includes('sim') || lower.includes('native')) {
      return '<span class="badge" style="background:#ecfdf5;color:#047857;border:1px solid #a7f3d0;font-size:0.72rem;font-weight:600;padding:2px 7px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-sim-card me-1" style="color:#047857;"></i>Native SIM</span>';
    }

    // Fallback
    return '<span class="badge" style="background:#f8fafc;color:#475569;border:1px solid #cbd5e1;font-size:0.72rem;font-weight:600;padding:2px 7px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-file-alt me-1 text-secondary"></i>' + _esc(page || 'My Leads') + '</span>';
  }

  function _renderCalls(items) {
    if (!items || !items.length) {
      return '<div class="uhm-empty-state"><i class="fas fa-phone-slash me-2"></i>No call records or recordings found.</div>';
    }

    return items
      .map(function (c) {
        var isOut = (c.direction || '').toLowerCase() === 'outbound';
        var iconHtml = isOut
          ? '<span class="uhm-direction-icon uhm-dir-out"><i class="fas fa-arrow-up"></i></span>'
          : '<span class="uhm-direction-icon uhm-dir-in"><i class="fas fa-arrow-down"></i></span>';

        var durText = _formatDuration(c.duration_seconds);
        var durSec = Number(c.duration_seconds || 0);
        var recHtml = '';
        if (c.has_recording && c.recording_url) {
          recHtml = `
            <div style="margin-top:6px;padding-top:6px;border-top:1px dashed #e2e8f0;">
              <audio controls style="width:100%;height:32px" preload="none" onplay="window._onAudioPlay(this)">
                <source src="${_esc(c.recording_url)}" type="audio/mpeg">
                <source src="${_esc(c.recording_url)}" type="audio/wav">
                Audio playback not supported.
              </audio>
            </div>
          `;
        } else if (durSec === 0) {
          recHtml = `
            <div style="margin-top:5px;font-size:11px;color:#94a3b8;display:flex;align-items:center;gap:5px;">
              <i class="fas fa-phone-slash" style="font-size:10px;"></i>
              <span>Unanswered / Missed (0s — no audio captured)</span>
            </div>
          `;
        } else {
          recHtml = `
            <div style="margin-top:5px;font-size:11px;color:#94a3b8;display:flex;align-items:center;gap:5px;">
              <i class="fas fa-volume-mute" style="font-size:10px;"></i>
              <span>Audio recording unavailable</span>
            </div>
          `;
        }

        var callLogId = (c.id && String(c.id).startsWith('scl_')) ? (c.raw_id || 0) : 0;
        var callSessionId = c.call_session_id || '';
        var rawPhone = (_currentEntity && _currentEntity.phone) || c.phone || '';
        var safePhone = _esc(rawPhone);
        var leadId = (_currentEntity && _currentEntity.entityId) ? _currentEntity.entityId : 0;

        var qaScoreBadge = '';
        if (c.quality_score != null && c.quality_score !== undefined) {
          qaScoreBadge = `<span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;background:#ecfdf5;color:#047857;border:1px solid #a7f3d0;" title="Quality Audit Score"><i class="fas fa-star text-amber-500 me-1"></i>${c.quality_score}% QA</span>`;
        }

        var hasRecordingAvailable = Boolean(c.has_recording && c.recording_url);
        var reviewBtn = '';
        if (hasRecordingAvailable || c.quality_score != null) {
          reviewBtn = `
            <button type="button" class="btn btn-sm" style="font-size:11px;padding:2px 8px;border-radius:4px;background:#fef3c7;color:#92400e;border:1px solid #fde68a;font-weight:600;display:inline-flex;align-items:center;cursor:pointer;" onclick="window._openQualityReviewFromHistory(${callLogId}, '${_esc(callSessionId)}', '${safePhone}', ${leadId})" title="Open Quality Review Audit">
              <i class="fas fa-clipboard-check me-1"></i>${c.quality_score != null ? 'QA Reviewed' : 'Review Call'}
            </button>
          `;
        }

        return `
          <div class="uhm-call-card">
            <div class="uhm-call-header">
              <div class="uhm-call-meta">
                ${iconHtml}
                <div>
                  <span style="font-size:13px;font-weight:600;color:#1e293b">${_esc(c.details || 'Call')}</span>
                  <div style="font-size:11px;color:#475569;margin-top:2px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                    <span>${_esc(_fmtDate(c.timestamp))}</span>
                    <span>&bull;</span>
                    <span style="font-weight:700;background:#e0f2fe;color:#0369a1;padding:1px 6px;border-radius:4px;font-size:11px;">
                      <i class="fas fa-headset me-1"></i>Handled by: ${_esc(c.handled_by || c.staff_name || 'Staff')}
                    </span>
                  </div>
                </div>
              </div>
              <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;justify-content:flex-end;">
                ${_renderCallFromBadge(c)}
                <span style="font-size:11px;font-weight:600;padding:2px 8px;border-radius:4px;background:#f1f5f9;color:#334155">${_esc(c.status || durText)}</span>
                ${qaScoreBadge}
                ${reviewBtn}
              </div>
            </div>
            ${recHtml}
          </div>
        `;
      })
      .join('');
  }

  function _renderMessages(items) {
    if (!items || !items.length) {
      return '<div class="uhm-empty-state"><i class="fas fa-comment-slash me-2"></i>No message or chat history found.</div>';
    }

    var html = '<div class="uhm-chat-container">';
    items.forEach(function (m) {
      var isOut = (m.direction || '').toLowerCase() === 'outbound';
      var cls = isOut ? 'outbound' : 'inbound';
      var mediaHtml = '';
      var mediaUrl = m.media_url || '';
      var mediaType = (m.media_type || '').toLowerCase();
      var mediaName = m.media_name || 'Attachment';
      var mime = (m.media_mime_type || '').toLowerCase();

      if (mediaUrl) {
        var isPdf = (mediaType === 'document' && (mediaName.toLowerCase().endsWith('.pdf') || mime.includes('pdf'))) || mediaUrl.toLowerCase().includes('.pdf');
        var isImg = mediaType === 'image' || mime.startsWith('image/') || /\.(jpg|jpeg|png|webp|gif)(\?.*)?$/i.test(mediaUrl);
        var isAudio = mediaType === 'audio' || mime.startsWith('audio/') || /\.(mp3|ogg|wav|aac|m4a)(\?.*)?$/i.test(mediaUrl);

        if (isImg) {
          mediaHtml = `
            <div class="uhm-media-img-box">
              <a href="${_esc(mediaUrl)}" target="_blank" rel="noopener noreferrer">
                <img src="${_esc(mediaUrl)}" alt="${_esc(mediaName)}" onerror="this.style.display='none';this.parentElement.nextElementSibling.querySelector('.uhm-media-name').textContent='[Image attachment]';" />
              </a>
              <div class="uhm-media-img-bar">
                <span class="uhm-media-name" title="${_esc(mediaName)}">${_esc(mediaName)}</span>
                <a href="${_esc(mediaUrl)}" download="${_esc(mediaName)}" class="uhm-dl-btn" title="Download Image">
                  <i class="fas fa-download"></i> Download
                </a>
              </div>
            </div>
          `;
        } else if (isAudio) {
          mediaHtml = `
            <div style="margin-top:6px">
              <audio controls style="width:100%;height:32px" preload="none">
                <source src="${_esc(mediaUrl)}" type="${_esc(mime || 'audio/mpeg')}">
                Audio playback not supported.
              </audio>
            </div>
          `;
        } else {
          // Document / PDF
          var iconClass = isPdf ? 'fas fa-file-pdf' : 'fas fa-file-alt';
          var iconColor = isPdf ? '#ef4444' : '#2563eb';
          mediaHtml = `
            <div class="uhm-media-doc-box">
              <div style="display:flex;align-items:center;gap:8px;min-width:0;flex:1;">
                <i class="${iconClass}" style="font-size:20px;color:${iconColor};flex-shrink:0;"></i>
                <div style="min-width:0;flex:1;">
                  <div class="uhm-media-name" title="${_esc(mediaName)}">${_esc(mediaName)}</div>
                  <div style="font-size:10px;color:#64748b;">${_esc(mime || (isPdf ? 'PDF Document' : 'Document Attachment'))}</div>
                </div>
              </div>
              <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">
                <a href="${_esc(mediaUrl)}" target="_blank" rel="noopener noreferrer" class="uhm-doc-view-btn" title="View Document">
                  <i class="fas fa-external-link-alt"></i>
                </a>
                <a href="${_esc(mediaUrl)}" download="${_esc(mediaName)}" class="uhm-dl-btn" title="Download Document">
                  <i class="fas fa-download"></i>
                </a>
              </div>
            </div>
          `;
        }
      }

      var msgStatus = (m.status || '').toLowerCase();
      var statusHtml = '';
      if (isOut) {
        if (msgStatus === 'failed') {
          statusHtml = `<span class="uhm-status-failed" title="${_esc(m.failure_reason || m.error_message || 'Delivery failed')}"><i class="fas fa-exclamation-circle"></i> Failed${m.error_code ? ' (' + _esc(m.error_code) + ')' : ''}</span>`;
        } else if (msgStatus === 'read') {
          statusHtml = `<span class="uhm-status-badge" style="color:#0284c7" title="Read ${_esc(_fmtDate(m.read_at || m.timestamp))}"><span style="letter-spacing:-1px">✓✓</span> Read</span>`;
        } else if (msgStatus === 'delivered') {
          statusHtml = `<span class="uhm-status-badge" style="color:#64748b" title="Delivered ${_esc(_fmtDate(m.delivered_at || m.timestamp))}"><span style="letter-spacing:-1px">✓✓</span> Delivered</span>`;
        } else if (msgStatus === 'queued') {
          statusHtml = `<span class="uhm-status-badge" style="color:#d97706" title="Queued in dispatch"><i class="fas fa-clock me-1"></i>Queued</span>`;
        } else {
          statusHtml = `<span class="uhm-status-badge" style="color:#64748b" title="Sent">✓ Sent</span>`;
        }
      } else {
        statusHtml = `<span class="uhm-status-badge" style="color:#059669" title="Received"><i class="fas fa-arrow-down-left me-1"></i>Received</span>`;
      }

      var errSnippet = '';
      if (isOut && msgStatus === 'failed' && (m.failure_reason || m.error_message)) {
        errSnippet = `<div class="uhm-error-snippet"><i class="fas fa-info-circle me-1"></i>${_esc(m.failure_reason || m.error_message)}</div>`;
      }

      var bodyText = m.message_text ? `<div style="white-space:pre-wrap">${_esc(m.message_text)}</div>` : '';

      html += `
        <div class="uhm-chat-row ${cls}">
          <div class="uhm-chat-sender">
            <span>${_esc(m.sender_name || (isOut ? 'Staff' : 'Customer'))}</span>
            <span style="font-weight:normal;opacity:0.75">&bull; ${_esc(m.channel || 'WhatsApp')}</span>
          </div>
          <div class="uhm-bubble">
            ${bodyText}
            ${mediaHtml}
            ${errSnippet}
            <div class="uhm-chat-meta-bar">
              <span class="uhm-chat-time">${_esc(_fmtDate(m.timestamp))}</span>
              ${statusHtml}
            </div>
          </div>
        </div>
      `;
    });
    html += '</div>';
    return html;
  }

  function _renderChanges(items) {
    if (!items || !items.length) {
      return '<div class="uhm-empty-state"><i class="fas fa-clipboard-list me-2"></i>No change history or notes recorded for this record.</div>';
    }

    // Group changes into a single box per specific date
    var groups = [];
    var groupMap = {};

    items.forEach(function (ch) {
      var d = ch.timestamp ? new Date(ch.timestamp) : null;
      var dateKey = 'General History';
      if (d && !isNaN(d.getTime())) {
        dateKey = d.toLocaleDateString('en-IN', {
          day: '2-digit',
          month: 'short',
          year: 'numeric'
        });
      }
      var key = dateKey;

      if (!groupMap[key]) {
        groupMap[key] = {
          dateKey: dateKey,
          items: []
        };
        groups.push(groupMap[key]);
      }
      groupMap[key].items.push(ch);
    });

    var html = '<div style="padding-top:4px;display:flex;flex-direction:column;gap:12px;">';
    groups.forEach(function (grp) {
      var dotClass = 'dot-audit';
      var changesHtml = '';

      grp.items.forEach(function (ch) {
        var oldNewHtml = '';
        if (ch.old_val || ch.new_val) {
          oldNewHtml = `
            <div style="font-size:11px;margin-top:3px;word-break:break-word;">
              ${ch.old_val ? '<span style="color:#ef4444;text-decoration:line-through;margin-right:6px">' + _esc(ch.old_val) + '</span> &rarr; ' : ''}
              <span style="color:#10b981;font-weight:600">${_esc(ch.new_val || '')}</span>
            </div>
          `;
        }

        var isCall = ch.category === 'call';
        var isNote = ch.category === 'note';
        var isAsgn = ch.category === 'assignment';
        var isFu   = ch.category === 'followup';

        var rowBg = '#f8fafc';
        var rowBorder = '#e2e8f0';
        var titleColor = '#1e293b';
        var iconHtml = '<i class="fas fa-edit text-slate-400 me-1"></i>';

        if (isCall) {
          rowBg = '#f0fdf4';
          rowBorder = '#bbf7d0';
          titleColor = '#166534';
          iconHtml = '<i class="fas fa-phone-alt text-emerald-600 me-1"></i>';
        } else if (isNote) {
          rowBg = '#fffbeb';
          rowBorder = '#fde68a';
          titleColor = '#92400e';
          iconHtml = '<i class="fas fa-sticky-note text-amber-500 me-1"></i>';
        } else if (isFu) {
          rowBg = '#f5f3ff';
          rowBorder = '#ddd6fe';
          titleColor = '#5b21b6';
          iconHtml = '<i class="fas fa-calendar-check text-purple-500 me-1"></i>';
        } else if (isAsgn) {
          rowBg = '#eff6ff';
          rowBorder = '#bfdbfe';
          titleColor = '#1e40af';
          iconHtml = '<i class="fas fa-user-tag text-blue-500 me-1"></i>';
        }

        var recHtml = '';
        if (isCall && ch.has_recording && ch.recording_url) {
          recHtml = `
            <div style="margin-top:6px;padding-top:6px;border-top:1px dashed #cbd5e1;">
              <audio controls style="width:100%;height:30px" preload="none" onplay="window._onAudioPlay(this)">
                <source src="${_esc(ch.recording_url)}" type="audio/mpeg">
                <source src="${_esc(ch.recording_url)}" type="audio/wav">
                Audio playback not supported.
              </audio>
            </div>
          `;
        }

        var handledOrAuthorInfo = '';
        if (isCall) {
          handledOrAuthorInfo = `<span style="font-size:11px;font-weight:700;color:#15803d;background:#dcfce7;padding:1px 6px;border-radius:4px;"><i class="fas fa-headset me-1"></i>Handled by: ${_esc(ch.handled_by || ch.author_name || 'Staff')}</span>`;
        } else {
          handledOrAuthorInfo = `<span style="font-size:11px;font-weight:600;color:#475569;background:#e2e8f0;padding:1px 6px;border-radius:4px;"><i class="fas fa-user me-1"></i>By: ${_esc(ch.author_name || ch.handled_by || 'Staff')}</span>`;
        }

        var itemTime = '';
        if (ch.timestamp) {
          try {
            var itemDate = new Date(ch.timestamp);
            if (!isNaN(itemDate.getTime())) {
              itemTime = itemDate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
            }
          } catch (_) {}
        }

        changesHtml += `
          <div style="background:${rowBg};border:1px solid ${rowBorder};border-radius:6px;padding:8px 10px;margin-bottom:6px;">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;flex-wrap:wrap;">
              <span style="font-size:12.5px;font-weight:600;color:${titleColor}">${iconHtml}${_esc(ch.title || ch.event_type || 'Change')}</span>
              <div style="display:flex;align-items:center;gap:6px;">
                ${handledOrAuthorInfo}
                ${itemTime ? '<span style="font-size:11px;color:#94a3b8;font-weight:normal">' + _esc(itemTime) + '</span>' : ''}
              </div>
            </div>
            ${ch.details ? `<div style="font-size:11.5px;color:#475569;margin-top:3px;word-break:break-word;">${_esc(ch.details)}</div>` : ''}
            ${oldNewHtml}
            ${recHtml}
          </div>
        `;
      });

      html += `
        <div class="uhm-timeline-item">
          <div class="uhm-timeline-dot ${dotClass}"></div>
          <div class="uhm-timeline-card" style="border:1px solid #cbd5e1;background:#ffffff;box-shadow:0 1px 3px rgba(0,0,0,0.05);padding:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #f1f5f9;padding-bottom:8px;margin-bottom:8px;flex-wrap:wrap;gap:6px;">
              <div style="display:flex;align-items:center;gap:6px;">
                <span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:#e0e7ff;color:#3730a3;font-size:11px;">
                  <i class="far fa-calendar-alt"></i>
                </span>
                <span style="font-size:13px;font-weight:700;color:#0f172a">${_esc(grp.dateKey)}</span>
                <span style="font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;background:#e0f2fe;color:#0369a1;border:1px solid #bae6fd;">
                  ${grp.items.length} ${grp.items.length === 1 ? 'change' : 'changes'}
                </span>
              </div>
            </div>
            <div style="display:flex;flex-direction:column;">
              ${changesHtml}
            </div>
          </div>
        </div>
      `;
    });
    html += '</div>';
    return html;
  }

  function _loadTabData(tabName) {
    var contentEl = document.getElementById('uhmTabContent');
    if (!contentEl || !_currentEntity) return;

    _stopAudio();

    var token = _getAuthToken();
    var headers = token ? { Authorization: 'Bearer ' + token } : {};

    if (tabName === 'calls') {
      if (_cache.calls) {
        contentEl.innerHTML = _renderCalls(_cache.calls.items);
        return;
      }
      contentEl.innerHTML = '<div class="uhm-empty-state"><i class="fas fa-spinner fa-spin me-2"></i>Loading call logs & recordings…</div>';
      var url = `/api/v1/crm/universal-history/calls?entity_type=${encodeURIComponent(_currentEntity.entityType)}&entity_id=${_currentEntity.entityId || 0}&phone=${encodeURIComponent(_currentEntity.phone || '')}&name=${encodeURIComponent(_currentEntity.name || '')}&limit=100`;
      fetch(url, { headers: headers })
        .then(function (r) {
          if (!r.ok) {
            return r.json().catch(function () { return {}; }).then(function (err) {
              throw new Error(err.detail || err.message || ('Server error (' + r.status + ')'));
            });
          }
          return r.json();
        })
        .then(function (res) {
          if (res.success) {
            _cache.calls = res;
            var cnt = document.getElementById('uhmCountCalls');
            if (cnt) cnt.textContent = res.total_calls || 0;
            contentEl.innerHTML = _renderCalls(res.items);
          } else {
            contentEl.innerHTML = `<div class="uhm-empty-state" style="color:#ef4444">${_esc(res.detail || 'Failed to load calls')}</div>`;
          }
        })
        .catch(function (err) {
          contentEl.innerHTML = `<div class="uhm-empty-state" style="color:#ef4444">Error loading calls: ${_esc(err.message)}</div>`;
        });
    } else if (tabName === 'messages') {
      if (_cache.messages) {
        contentEl.innerHTML = _renderMessages(_cache.messages.items);
        return;
      }
      contentEl.innerHTML = '<div class="uhm-empty-state"><i class="fas fa-spinner fa-spin me-2"></i>Loading messages & chat…</div>';
      var urlM = `/api/v1/crm/universal-history/messages?entity_type=${encodeURIComponent(_currentEntity.entityType)}&entity_id=${_currentEntity.entityId || 0}&phone=${encodeURIComponent(_currentEntity.phone || '')}&name=${encodeURIComponent(_currentEntity.name || '')}&limit=100`;
      fetch(urlM, { headers: headers })
        .then(function (r) {
          if (!r.ok) {
            return r.json().catch(function () { return {}; }).then(function (err) {
              throw new Error(err.detail || err.message || ('Server error (' + r.status + ')'));
            });
          }
          return r.json();
        })
        .then(function (res) {
          if (res.success) {
            _cache.messages = res;
            var cntM = document.getElementById('uhmCountMessages');
            if (cntM) cntM.textContent = res.total_messages || 0;
            contentEl.innerHTML = _renderMessages(res.items);
          } else {
            contentEl.innerHTML = `<div class="uhm-empty-state" style="color:#ef4444">${_esc(res.detail || 'Failed to load messages')}</div>`;
          }
        })
        .catch(function (err) {
          contentEl.innerHTML = `<div class="uhm-empty-state" style="color:#ef4444">Error loading messages: ${_esc(err.message)}</div>`;
        });
    } else if (tabName === 'changes') {
      var sub = _changesSubfilter || 'all';
      if (_cache.changes && _cache.changes[sub]) {
        contentEl.innerHTML = _renderChanges(_cache.changes[sub].items);
        return;
      }
      contentEl.innerHTML = '<div class="uhm-empty-state"><i class="fas fa-spinner fa-spin me-2"></i>Loading change history & notes…</div>';
      var urlC = `/api/v1/crm/universal-history/changes?entity_type=${encodeURIComponent(_currentEntity.entityType)}&entity_id=${_currentEntity.entityId || 0}&phone=${encodeURIComponent(_currentEntity.phone || '')}&name=${encodeURIComponent(_currentEntity.name || '')}&subfilter=${sub}&limit=100`;
      fetch(urlC, { headers: headers })
        .then(function (r) {
          if (!r.ok) {
            return r.json().catch(function () { return {}; }).then(function (err) {
              throw new Error(err.detail || err.message || ('Server error (' + r.status + ')'));
            });
          }
          return r.json();
        })
        .then(function (res) {
          if (res.success) {
            _cache.changes = _cache.changes || {};
            _cache.changes[sub] = res;
            if (sub === 'all') {
              var cntC = document.getElementById('uhmCountChanges');
              if (cntC) cntC.textContent = res.total_changes || 0;
            }
            contentEl.innerHTML = _renderChanges(res.items);
          } else {
            contentEl.innerHTML = `<div class="uhm-empty-state" style="color:#ef4444">${_esc(res.detail || 'Failed to load change history')}</div>`;
          }
        })
        .catch(function (err) {
          contentEl.innerHTML = `<div class="uhm-empty-state" style="color:#ef4444">Error loading changes: ${_esc(err.message)}</div>`;
        });
    }
  }

  // --- Public APIs ---

  window.openUniversalHistory = function (options) {
    if (!options || (!options.entityId && !options.leadId && !options.memberId)) {
      console.warn('[UniversalHistory] openUniversalHistory called with invalid options:', options);
      return;
    }

    _injectModalDOM();
    _stopAudio();

    var entityType = options.entityType || (options.memberId ? 'vgk_member' : 'crm_lead');
    var entityId = parseInt(options.entityId || options.leadId || options.memberId || 0, 10) || 0;

    _currentEntity = {
      entityType: entityType,
      entityId: entityId,
      name: options.name || '',
      phone: options.phone || options.mobile_number || '',
      category: options.category || '',
      status: options.status || '',
      stage: options.stage || '',
      assignedTo: options.assignedTo || options.assigned_staff_name || ''
    };

    _cache = { calls: null, messages: null, changes: null, summary: null };
    _activeTab = 'calls';
    _changesSubfilter = 'all';

    // Populate header info immediately
    var nameEl = document.getElementById('uhmEntityName');
    if (nameEl) nameEl.textContent = _currentEntity.name || (entityType === 'vgk_member' ? 'Channel Partner' : 'CRM Lead #' + entityId);

    var badgeEl = document.getElementById('uhmEntityBadge');
    if (badgeEl) {
      if (entityType === 'vgk_member') {
        badgeEl.textContent = 'VGK Member';
        badgeEl.className = 'uhm-badge uhm-badge-vgk';
      } else {
        badgeEl.textContent = 'CRM Lead';
        badgeEl.className = 'uhm-badge uhm-badge-lead';
      }
    }

    var phoneEl = document.getElementById('uhmEntityPhone');
    if (phoneEl) phoneEl.innerHTML = '<i class="fas fa-phone-alt me-1"></i> ' + _esc(_currentEntity.phone || '—');

    var catEl = document.getElementById('uhmEntityCategory');
    if (catEl) catEl.innerHTML = '<i class="fas fa-tag me-1"></i> ' + _esc(_currentEntity.category || 'General');

    var stEl = document.getElementById('uhmEntityStatus');
    if (stEl) stEl.innerHTML = '<i class="fas fa-info-circle me-1"></i> ' + _esc(_currentEntity.stage || _currentEntity.status || 'Active');

    var asgnEl = document.getElementById('uhmEntityAssigned');
    if (asgnEl) asgnEl.innerHTML = '<i class="fas fa-user-check me-1"></i> ' + _esc(_currentEntity.assignedTo || 'Unassigned');

    // Reset badges
    ['Calls', 'Messages', 'Changes'].forEach(function (k) {
      var el = document.getElementById('uhmCount' + k);
      if (el) el.textContent = '…';
    });

    // Show modal root
    var root = document.getElementById('uhmModalRoot');
    if (root) root.style.display = 'flex';

    window.switchUniversalHistoryTab('calls');

    // Async fetch full summary to update badges and verify authority
    var sToken = _getAuthToken();
    var sHeaders = sToken ? { Authorization: 'Bearer ' + sToken } : {};
    fetch(`/api/v1/crm/universal-history/entity-summary?entity_type=${entityType}&entity_id=${entityId}&phone=${encodeURIComponent(_currentEntity.phone || '')}&name=${encodeURIComponent(_currentEntity.name || '')}`, {
      headers: sHeaders
    })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res.success && res.entity) {
          if (res.entity.name && nameEl) nameEl.textContent = res.entity.name;
          if (phoneEl) phoneEl.innerHTML = '<i class="fas fa-phone-alt me-1"></i> ' + _esc(res.entity.display_phone || res.entity.primary_phone || '—');
          if (catEl) catEl.innerHTML = '<i class="fas fa-tag me-1"></i> ' + _esc(res.entity.category || 'General');
          if (stEl) stEl.innerHTML = '<i class="fas fa-info-circle me-1"></i> ' + _esc(res.entity.stage || res.entity.status || 'Active');
          if (asgnEl) asgnEl.innerHTML = '<i class="fas fa-user-check me-1"></i> ' + _esc(res.entity.assigned_to || 'Unassigned');

          if (res.counts) {
            var cCalls = document.getElementById('uhmCountCalls');
            if (cCalls) cCalls.textContent = res.counts.calls || 0;
            var cMsgs = document.getElementById('uhmCountMessages');
            if (cMsgs) cMsgs.textContent = res.counts.messages || 0;
            var cChgs = document.getElementById('uhmCountChanges');
            if (cChgs) cChgs.textContent = res.counts.changes || 0;
          }
        }
      })
      .catch(function (err) {
        console.warn('[UniversalHistory] Failed to load entity summary:', err);
      });
  };

  window.closeUniversalHistory = function () {
    _stopAudio();
    var root = document.getElementById('uhmModalRoot');
    if (root) root.style.display = 'none';
  };

  window.switchUniversalHistoryTab = function (tabName) {
    _activeTab = tabName;
    ['Calls', 'Messages', 'Changes'].forEach(function (k) {
      var btn = document.getElementById('uhmTab' + k);
      if (!btn) return;
      if (k.toLowerCase() === tabName.toLowerCase()) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    var subBar = document.getElementById('uhmSubfilterBar');
    if (subBar) {
      subBar.style.display = tabName === 'changes' ? 'flex' : 'none';
    }

    _loadTabData(tabName);
  };

  window.setUniversalHistorySubfilter = function (subfilter) {
    _changesSubfilter = subfilter;
    var chips = document.querySelectorAll('#uhmSubfilterBar .uhm-subchip');
    chips.forEach(function (c) {
      c.classList.remove('active');
      if (c.textContent.toLowerCase().includes(subfilter.toLowerCase()) ||
          (subfilter === 'all' && c.textContent.toLowerCase().includes('all')) ||
          (subfilter === 'audit' && c.textContent.toLowerCase().includes('field'))) {
        c.classList.add('active');
      }
    });
    _loadTabData('changes');
  };

  window._onAudioPlay = function (audioEl) {
    if (_activeAudio && _activeAudio !== audioEl) {
      try {
        _activeAudio.pause();
      } catch (_) {}
    }
    _activeAudio = audioEl;
  };

  window._openQualityReviewFromHistory = function (callLogId, callSessionId, phone, leadId) {
    var doOpen = function () {
      if (typeof window.openUniversalQualityReview === 'function') {
        window.openUniversalQualityReview({
          callLogId: callLogId || 0,
          callSessionId: callSessionId || '',
          phone: phone || '',
          leadId: leadId || 0
        });
      } else {
        alert('Quality Review modal could not be initialized.');
      }
    };

    if (typeof window.openUniversalQualityReview === 'function') {
      doOpen();
      return;
    }

    var script = document.createElement('script');
    script.src = '/public/js/universal-quality-review-modal.js';
    script.onload = doOpen;
    script.onerror = function () {
      alert('Quality Review script could not be loaded.');
    };
    document.head.appendChild(script);
  };
})();
