/**
 * Universal Call Quality Review Modal — MyntOS Single Source of Truth
 * Exactly matches http://localhost:5001/staff/call-quality review modal:
 *   - Call Participants Flow Node (Caller -> Recipient, Type, Direction)
 *   - Call Timing Strip (Date & Time, exact duration with seconds, Phone)
 *   - Softphone Audio Scrubber Player with Seeking & Time Display
 *   - Status & Disposition tags
 *   - Call Notes & CRM Activity Stream
 *   - Previous Call History Timeline
 *   - 6 Quality Scoring Dimensions with Interactive Star Ratings (1-5★)
 *   - Overall Remarks & Coaching Feedback Textarea
 *   - Save Review, Skip, and Close Actions
 *
 * Global Entrypoints:
 *   window.openUniversalQualityReview({ callLogId, callSessionId, phone, leadId, onReviewSaved })
 *   window.closeUniversalQualityReview()
 */

(function () {
  'use strict';

  var _currentReviewId = null;
  var _currentReviewData = null;
  var _onSavedCallback = null;
  var _scores = {
    score_script: null,
    score_tone: null,
    score_info_accuracy: null,
    score_customer_handling: null,
    score_closing: null,
    score_disposition: null
  };
  var _activeAudio = null;
  var _activePlayerId = null;

  var PARAMS = [
    { key: 'score_script', label: 'Script Adherence', desc: 'Followed sales script & introduction?' },
    { key: 'score_tone', label: 'Tone & Attitude', desc: 'Professional, positive, respectful?' },
    { key: 'score_info_accuracy', label: 'Information Accuracy', desc: 'Correct product/service info given?' },
    { key: 'score_customer_handling', label: 'Customer Handling', desc: 'Handled objections & queries well?' },
    { key: 'score_closing', label: 'Closing Technique', desc: 'Proper follow-up commitment taken?' },
    { key: 'score_disposition', label: 'Disposition Accuracy', desc: 'CRM status updated correctly?' }
  ];

  function _getAuthToken() {
    if (typeof localStorage === 'undefined') return '';
    var cookieToken = '';
    if (typeof document !== 'undefined') {
      var m = (document.cookie || '').match(/(?:staff_token|token|access_token)=([^;]+)/);
      if (m && m[1]) cookieToken = decodeURIComponent(m[1].trim());
    }
    return (
      (typeof StaffTokenManager !== 'undefined' && StaffTokenManager.getToken ? StaffTokenManager.getToken() : null) ||
      localStorage.getItem('staff_token') ||
      localStorage.getItem('token') ||
      (typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('staff_token') : '') ||
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

  function _fmtDT(dtStr) {
    if (!dtStr) return '—';
    try {
      var d = new Date(dtStr);
      return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
        + ' at ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });
    } catch (e) {
      return dtStr;
    }
  }

  function _fmtDur(secs) {
    if (!secs || secs <= 0) return '0s';
    var s = Math.floor(secs % 60);
    var m = Math.floor((secs % 3600) / 60);
    var h = Math.floor(secs / 3600);
    if (h > 0) return h + 'h ' + m + 'm ' + (s < 10 ? '0' : '') + s + 's';
    if (m > 0) return m + 'm ' + (s < 10 ? '0' : '') + s + 's';
    return s + 's';
  }

  function _scoreLabel(score) {
    if (score === null || score === undefined) return '<span class="uqr-score-pill uqr-score-na">N/A</span>';
    var n = parseFloat(score);
    if (n >= 4.5) return '<span class="uqr-score-pill uqr-score-exc">' + n.toFixed(1) + ' ★ Excellent</span>';
    if (n >= 3.5) return '<span class="uqr-score-pill uqr-score-good">' + n.toFixed(1) + ' ★ Good</span>';
    if (n >= 2.5) return '<span class="uqr-score-pill uqr-score-avg">' + n.toFixed(1) + ' ★ Average</span>';
    return '<span class="uqr-score-pill uqr-score-poor">' + n.toFixed(1) + ' ★ Poor</span>';
  }

  function _injectStylesAndModal() {
    if (document.getElementById('universalQualityReviewModal')) return;

    var style = document.createElement('style');
    style.id = 'uqrModalStyles';
    style.textContent = `
      .uqr-backdrop {
        display: none;
        position: fixed;
        inset: 0;
        background: rgba(15, 23, 42, 0.65);
        z-index: 100000005;
        align-items: center;
        justify-content: center;
        backdrop-filter: blur(3px);
        padding: 14px;
        box-sizing: border-box;
      }
      .uqr-backdrop.open { display: flex !important; }
      .uqr-box {
        background: #ffffff;
        border-radius: 14px;
        width: 890px;
        max-width: 96vw;
        max-height: 94vh;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25), 0 0 0 1px rgba(0,0,0,0.06);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #1e293b;
        animation: uqrSlideIn 0.2s ease-out;
      }
      @keyframes uqrSlideIn {
        from { opacity: 0; transform: translateY(12px) scale(0.98); }
        to { opacity: 1; transform: translateY(0) scale(1); }
      }
      .uqr-hdr {
        padding: 14px 20px;
        border-bottom: 1px solid #e2e8f0;
        background: #f8fafc;
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .uqr-hdr h5 {
        font-size: 16px;
        font-weight: 700;
        color: #0f172a;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .uqr-close-btn {
        background: none;
        border: none;
        font-size: 20px;
        line-height: 1;
        cursor: pointer;
        color: #64748b;
        padding: 4px 8px;
        border-radius: 6px;
        transition: background 0.15s;
      }
      .uqr-close-btn:hover { background: #e2e8f0; color: #0f172a; }
      .uqr-body {
        flex: 1;
        overflow-y: auto;
        padding: 18px 22px;
        -webkit-overflow-scrolling: touch;
      }
      .uqr-ftr {
        padding: 12px 20px;
        border-top: 1px solid #e2e8f0;
        background: #f8fafc;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 8px;
      }
      .uqr-call-card {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid #cbd5e1;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 14px;
      }
      .uqr-flow {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
      }
      .uqr-node {
        flex: 1;
        background: #fff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 10px 14px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
      }
      .uqr-role-tag {
        font-size: 9.5px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .05em;
        display: inline-block;
        padding: 2px 6px;
        border-radius: 4px;
        margin-bottom: 4px;
      }
      .uqr-arrow {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-width: 90px;
        text-align: center;
      }
      .uqr-arrow-line {
        display: flex;
        align-items: center;
        gap: 4px;
        color: #0f766e;
        font-size: 14px;
        font-weight: 700;
      }
      .uqr-timing-strip {
        margin-top: 10px;
        padding-top: 8px;
        border-top: 1px solid #e2e8f0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 11.5px;
        color: #475569;
        flex-wrap: wrap;
        gap: 6px;
      }
      .uqr-audio-card {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 14px;
      }
      .uqr-audio-card-hdr {
        font-size: 12px;
        font-weight: 700;
        color: #38bdf8;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .uqr-audio-player {
        display: flex;
        align-items: center;
        gap: 10px;
        width: 100%;
      }
      .uqr-play-btn {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: #0284c7;
        color: #fff;
        border: none;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        cursor: pointer;
        flex-shrink: 0;
        transition: all 0.15s;
      }
      .uqr-play-btn:hover { background: #0369a1; transform: scale(1.06); }
      .uqr-slider {
        height: 5px;
        cursor: pointer;
        accent-color: #38bdf8;
        background: #334155;
        border-radius: 3px;
        outline: none;
        margin: 2px 0;
        width: 100%;
        flex: 1;
      }
      .uqr-time-label {
        font-size: 11px;
        color: #94a3b8;
        font-family: monospace;
        white-space: nowrap;
        margin-left: 6px;
      }
      .uqr-section-hdr {
        font-size: 12px;
        font-weight: 700;
        color: #1e293b;
        text-transform: uppercase;
        letter-spacing: .05em;
        margin: 16px 0 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .uqr-info-row {
        display: flex;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 12px;
      }
      .uqr-info-col {
        flex: 1;
        padding: 8px 12px;
        background: #f8fafc;
        font-size: 12px;
        line-height: 1.5;
      }
      .uqr-info-col:not(:last-child) { border-right: 1px solid #e2e8f0; }
      .uqr-info-col .lbl { font-weight: 700; color: #64748b; font-size: 10px; text-transform: uppercase; }
      .uqr-info-col .val { color: #0f172a; font-weight: 600; margin-top: 2px; }
      .uqr-note-item {
        border-left: 3px solid #0f766e;
        padding: 7px 12px;
        margin-bottom: 6px;
        font-size: 12px;
        background: #f8fafc;
        border-radius: 0 6px 6px 0;
        border-top: 1px solid #f1f5f9;
        border-right: 1px solid #f1f5f9;
        border-bottom: 1px solid #f1f5f9;
      }
      .uqr-note-item .author {
        font-weight: 700;
        color: #0f172a;
        font-size: 11px;
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .uqr-note-item .text { color: #334155; margin-top: 3px; font-size: 12px; }
      .uqr-hist-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 11.5px;
      }
      .uqr-hist-table th {
        padding: 6px 10px;
        text-align: left;
        background: #f8fafc;
        border-bottom: 1px solid #e2e8f0;
        color: #64748b;
        font-size: 10.5px;
        font-weight: 700;
        text-transform: uppercase;
      }
      .uqr-hist-table td {
        padding: 6px 10px;
        border-bottom: 1px solid #f1f5f9;
        vertical-align: middle;
      }
      .uqr-scores-wrap {
        background: #f8fafc;
        border-radius: 10px;
        padding: 12px 14px;
        border: 1px solid #e2e8f0;
        margin-bottom: 14px;
      }
      .uqr-score-row {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
        padding: 7px 12px;
        background: #fff;
        border-radius: 6px;
        border: 1px solid #f1f5f9;
      }
      .uqr-score-row .lbl-s {
        font-size: 12.5px;
        font-weight: 600;
        color: #334155;
        min-width: 220px;
        flex: 1;
      }
      .uqr-stars {
        display: flex;
        gap: 4px;
      }
      .uqr-star-btn {
        font-size: 22px;
        cursor: pointer;
        color: #cbd5e1;
        transition: all 0.15s;
        background: none;
        border: none;
        padding: 0 2px;
        line-height: 1;
      }
      .uqr-star-btn.active, .uqr-star-btn:hover {
        color: #f59e0b;
        transform: scale(1.15);
      }
      .uqr-score-val-label {
        font-size: 11.5px;
        color: #64748b;
        font-weight: 700;
        min-width: 40px;
        text-align: right;
      }
      .uqr-score-pill {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
      }
      .uqr-score-exc { background: #d1fae5; color: #065f46; }
      .uqr-score-good { background: #dbeafe; color: #1e40af; }
      .uqr-score-avg { background: #fef3c7; color: #92400e; }
      .uqr-score-poor { background: #fee2e2; color: #991b1b; }
      .uqr-score-na { background: #f1f5f9; color: #94a3b8; }
      .uqr-btn-save {
        background: #0f766e;
        color: #fff;
        border: none;
        border-radius: 6px;
        padding: 8px 20px;
        font-size: 13px;
        font-weight: 700;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 6px;
        transition: background 0.15s;
      }
      .uqr-btn-save:hover { background: #0d6460; }
      .uqr-btn-skip {
        background: #f1f5f9;
        color: #64748b;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.15s;
      }
      .uqr-btn-skip:hover { background: #e2e8f0; color: #334155; }
      .uqr-btn-close {
        background: #f1f5f9;
        color: #374151;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 8px 18px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
      }
      .uqr-spinner-wrap {
        text-align: center;
        padding: 40px;
        color: #0f766e;
      }
    `;
    document.head.appendChild(style);

    var modalHtml = `
      <div class="uqr-backdrop" id="universalQualityReviewModal">
        <div class="uqr-box">
          <div class="uqr-hdr">
            <h5 id="uqrModalTitle"><i class="fas fa-clipboard-check" style="color:#0f766e;"></i> Quality Review</h5>
            <button class="uqr-close-btn" onclick="window.closeUniversalQualityReview()" title="Close">&times;</button>
          </div>
          <div class="uqr-body" id="uqrModalBody">
            <div class="uqr-spinner-wrap"><i class="fas fa-spinner fa-spin fa-2x"></i><div style="margin-top:8px;font-size:12px;">Loading review details…</div></div>
          </div>
          <div class="uqr-ftr" id="uqrModalFtr">
            <button class="uqr-btn-close" onclick="window.closeUniversalQualityReview()">Close</button>
            <button class="uqr-btn-skip" id="uqrSkipBtn" onclick="window._uqrSkipReview()" style="display:none;">Skip</button>
            <button class="uqr-btn-save" id="uqrSaveBtn" onclick="window._uqrSubmitReview()" style="display:none;"><i class="fas fa-save"></i> Save Review</button>
          </div>
        </div>
      </div>
    `;
    var wrapper = document.createElement('div');
    wrapper.innerHTML = modalHtml;
    document.body.appendChild(wrapper.firstElementChild);

    // Escape listener
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && document.getElementById('universalQualityReviewModal')?.classList.contains('open')) {
        window.closeUniversalQualityReview();
      }
    });
  }

  function _stopAudio() {
    if (_activeAudio) {
      _activeAudio.pause();
      _activeAudio.src = '';
      _activeAudio = null;
    }
    _activePlayerId = null;
  }

  function _toggleAudio(url, id, defaultDuration) {
    if (!url) {
      alert('No audio recording file available for this session.');
      return;
    }
    var btn = document.getElementById('uqr-pbtn-' + id);
    var slider = document.getElementById('uqr-slider-' + id);
    var timer = document.getElementById('uqr-timer-' + id);

    if (_activeAudio && _activePlayerId === id) {
      if (_activeAudio.paused) {
        _activeAudio.play();
        if (btn) btn.innerHTML = '<i class="fas fa-pause"></i>';
      } else {
        _activeAudio.pause();
        if (btn) btn.innerHTML = '<i class="fas fa-play"></i>';
      }
      return;
    }

    _stopAudio();

    var token = _getAuthToken();
    var streamUrl = url;
    if (token) {
      streamUrl += (streamUrl.indexOf('?') >= 0 ? '&' : '?') + 'token=' + encodeURIComponent(token);
    }

    var audio = new Audio(streamUrl);
    _activeAudio = audio;
    _activePlayerId = id;

    if (btn) btn.innerHTML = '<i class="fas fa-pause"></i>';

    audio.addEventListener('timeupdate', function () {
      if (!audio.duration || isNaN(audio.duration)) return;
      var pct = (audio.currentTime / audio.duration) * 100;
      if (slider) slider.value = pct;
      if (timer) {
        var cur = _formatSecs(audio.currentTime);
        var tot = _formatSecs(audio.duration);
        timer.textContent = cur + ' / ' + tot;
      }
    });

    audio.addEventListener('ended', function () {
      if (btn) btn.innerHTML = '<i class="fas fa-play"></i>';
      if (slider) slider.value = 0;
      _stopAudio();
    });

    audio.play().catch(function (err) {
      console.warn('Audio play error:', err);
      if (btn) btn.innerHTML = '<i class="fas fa-play"></i>';
    });
  }

  function _formatSecs(s) {
    s = Math.floor(s || 0);
    var m = Math.floor(s / 60);
    var sec = s % 60;
    return (m < 10 ? '0' : '') + m + ':' + (sec < 10 ? '0' : '') + sec;
  }

  function _seekAudio(val, id) {
    if (_activeAudio && _activePlayerId === id && _activeAudio.duration) {
      _activeAudio.currentTime = (_activeAudio.duration * (val / 100));
    }
  }

  function _renderReviewData(r) {
    var ci = r.call_identity || {};
    var sd = r.status_disposition || {};
    var isIncoming = ci.direction === 'inbound';
    var isReviewed = r.status === 'reviewed';

    document.getElementById('uqrModalTitle').innerHTML = `
      <i class="fas fa-clipboard-check" style="color:#0f766e;"></i>
      <span>Review #${r.id}</span>
      <span class="badge ${isReviewed ? 'bg-success' : 'bg-warning text-dark'}" style="font-size:10px;margin-left:6px;text-transform:uppercase;">${_esc(r.status || 'pending')}</span>
    `;

    var html = '';

    // 1. Participant Flow Card
    html += `
    <div class="uqr-call-card">
      <div class="uqr-flow">
        <div class="uqr-node" style="border-left: 3px solid ${isIncoming ? '#059669' : '#2563eb'};">
          <span class="uqr-role-tag" style="background:${isIncoming ? '#dcfce7;color:#166534;' : '#dbeafe;color:#1e40af;'}">
            <i class="fas ${isIncoming ? 'fa-user' : 'fa-headset'} me-1"></i>Caller (${isIncoming ? 'Customer' : 'Executive'})
          </span>
          <div style="font-weight:700;font-size:13px;color:#0f172a;">${_esc(ci.caller_display || '—')}</div>
          <div style="font-size:11px;color:#64748b;">${_esc(ci.caller_sub || '')}</div>
        </div>

        <div class="uqr-arrow">
          <span style="font-size:10px;font-weight:700;color:#0f766e;text-transform:uppercase;letter-spacing:.05em;">${isIncoming ? 'Incoming Call' : 'Outgoing Call'}</span>
          <div class="uqr-arrow-line">──────▶</div>
          <span style="font-size:10px;color:#64748b;">${_esc(ci.type || 'Connected')}</span>
        </div>

        <div class="uqr-node" style="border-left: 3px solid ${isIncoming ? '#2563eb' : '#059669'};">
          <span class="uqr-role-tag" style="background:${isIncoming ? '#dbeafe;color:#1e40af;' : '#dcfce7;color:#166534;'}">
            <i class="fas ${isIncoming ? 'fa-headset' : 'fa-user'} me-1"></i>Recipient (${isIncoming ? 'Executive' : 'Customer'})
          </span>
          <div style="font-weight:700;font-size:13px;color:#0f172a;">${_esc(ci.recipient_display || '—')}</div>
          <div style="font-size:11px;color:#64748b;">${_esc(ci.recipient_sub || '')}</div>
        </div>
      </div>

      <div class="uqr-timing-strip">
        <div><i class="far fa-clock me-1" style="color:#0f766e;"></i><strong>Call Date &amp; Time:</strong> ${_fmtDT(ci.datetime || r.call_datetime || r.sample_date)}</div>
        <div><strong>Duration:</strong> ${_esc(ci.duration_formatted || _fmtDur(r.call_duration_seconds))} (${ci.duration_seconds || r.call_duration_seconds || 0}s)</div>
        <div><strong>Phone:</strong> <span style="font-family:monospace;font-weight:700;">${_esc(ci.phone || r.call_phone || '—')}</span></div>
      </div>
    </div>`;

    // 2. Audio Recording Player
    if (r.has_recording || r.recording_url) {
      var audioSrc = r.recording_url;
      html += `
      <div class="uqr-audio-card">
        <div class="uqr-audio-card-hdr">
          <span><i class="fas fa-play-circle me-1"></i>Call Audio Recording</span>
          <span style="font-size:11px;color:#94a3b8;font-family:monospace;">${_esc(ci.duration_formatted || _fmtDur(r.call_duration_seconds))}</span>
        </div>
        <div class="uqr-audio-player">
          <button class="uqr-play-btn" id="uqr-pbtn-main" onclick="window._uqrToggleAudio('${_esc(audioSrc)}', 'main', '${_esc(ci.duration_formatted || '')}')" title="Play Recording">
            <i class="fas fa-play"></i>
          </button>
          <input type="range" class="uqr-slider" id="uqr-slider-main" min="0" max="100" value="0" oninput="window._uqrSeekAudio(this.value, 'main')">
          <div class="uqr-time-label" id="uqr-timer-main">00:00 / ${_esc(ci.duration_formatted || _fmtDur(r.call_duration_seconds))}</div>
        </div>
      </div>`;
    } else {
      html += `
      <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 14px;margin-bottom:14px;font-size:11.5px;color:#64748b;display:flex;align-items:center;gap:8px;">
        <i class="fas fa-microphone-slash" style="color:#94a3b8;font-size:14px;"></i>
        <span>No audio recording available for this call session.</span>
      </div>`;
    }

    // 3. Status & Disposition
    html += `
    <div class="uqr-section-hdr"><i class="fas fa-tags me-1" style="color:#0f766e;"></i>Status &amp; Disposition</div>
    <div class="uqr-info-row">
      <div class="uqr-info-col">
        <div class="lbl">Call Outcome</div>
        <div class="val" style="text-transform:capitalize;">${_esc(sd.call_status || 'Ended')}</div>
      </div>
      <div class="uqr-info-col">
        <div class="lbl">CRM Lead Status</div>
        <div class="val">${sd.crm_lead_status ? '<span class="badge bg-primary" style="font-size:10px;">' + _esc(sd.crm_lead_status) + '</span>' : '<span style="color:#94a3b8;">—</span>'}</div>
      </div>
      <div class="uqr-info-col">
        <div class="lbl">Solar Pipeline Stage</div>
        <div class="val">${sd.solar_pipeline_status ? '<span class="badge bg-success" style="font-size:10px;">' + _esc(sd.solar_pipeline_status) + '</span>' : '<span style="color:#94a3b8;">—</span>'}</div>
      </div>
    </div>`;

    // 4. Call Notes & CRM Activity
    var hasNotes = (r.lead_notes && r.lead_notes.length) || (r.lead_followups && r.lead_followups.length);
    html += `<div class="uqr-section-hdr"><i class="fas fa-sticky-note me-1" style="color:#0f766e;"></i>Call Notes &amp; CRM Activity</div>`;
    if (hasNotes) {
      var notesHtml = '';
      (r.lead_notes || []).slice(0, 6).forEach(function (n) {
        notesHtml += `
        <div class="uqr-note-item">
          <div class="author">
            <span><i class="fas fa-user-edit me-1" style="color:#0f766e;"></i>${_esc(n.author || 'Staff')}</span>
            <span style="color:#94a3b8;font-weight:400;font-size:10px;">${_fmtDT(n.created_at)}</span>
          </div>
          <div class="text">${_esc(n.note)}</div>
        </div>`;
      });
      (r.lead_followups || []).slice(0, 4).forEach(function (f) {
        notesHtml += `
        <div class="uqr-note-item" style="border-left-color:#d97706;">
          <div class="author">
            <span><i class="fas fa-calendar-check me-1" style="color:#d97706;"></i>Follow-up (${_esc(f.status || 'Scheduled')})</span>
            <span style="color:#94a3b8;font-weight:400;font-size:10px;">Scheduled: ${_esc(f.scheduled_date || '')}</span>
          </div>
          <div class="text">${_esc(f.notes || 'No follow-up notes')}</div>
        </div>`;
      });
      html += `<div style="max-height:150px;overflow-y:auto;margin-bottom:12px;">${notesHtml}</div>`;
    } else {
      html += `<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:8px 12px;margin-bottom:12px;font-size:11.5px;color:#94a3b8;"><i class="fas fa-info-circle me-1"></i>No call notes or follow-up activity logged yet for this contact.</div>`;
    }

    // 5. Previous Call History
    var hist = r.call_history || [];
    html += `
    <div class="uqr-section-hdr">
      <span><i class="fas fa-history me-1" style="color:#0f766e;"></i>Previous Call History (${hist.length})</span>
      <span style="font-size:10.5px;color:#64748b;text-transform:none;">Contact History for <span style="font-family:monospace;font-weight:700;">${_esc(ci.clean_phone || 'Customer')}</span></span>
    </div>`;
    if (hist.length) {
      var histRows = '';
      hist.slice(0, 8).forEach(function (h, idx) {
        var isHIn = h.direction === 'inbound';
        histRows += `
        <tr>
          <td style="color:#94a3b8;">${idx + 1}</td>
          <td><span class="badge ${isHIn ? 'bg-success' : 'bg-primary'}" style="font-size:9.5px;">${isHIn ? 'IN' : 'OUT'}</span></td>
          <td>${_fmtDT(h.datetime)}</td>
          <td>${_esc(h.duration_formatted || _fmtDur(h.duration_seconds))}</td>
          <td>${_esc(h.operator_name || 'Executive')}</td>
          <td style="color:#64748b;">${_esc(h.notes || h.status || '—')}</td>
        </tr>`;
      });
      html += `
      <div style="max-height:140px;overflow-y:auto;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:14px;">
        <table class="uqr-hist-table">
          <thead>
            <tr><th>#</th><th>Dir</th><th>Date &amp; Time</th><th>Duration</th><th>Executive</th><th>Notes / Status</th></tr>
          </thead>
          <tbody>${histRows}</tbody>
        </table>
      </div>`;
    } else {
      html += `<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:8px 12px;margin-bottom:14px;font-size:11.5px;color:#94a3b8;"><i class="fas fa-info-circle me-1"></i>No previous calls found for this contact number.</div>`;
    }

    // 6. Quality Scoring Parameters (The 6 Stars)
    var currentAvg = r.overall_score;
    html += `
    <div class="uqr-section-hdr">
      <span><i class="fas fa-star me-1" style="color:#f59e0b;"></i>Quality Scores</span>
      <span id="uqrOverallScoreBadge">${_scoreLabel(currentAvg)}</span>
    </div>
    <div class="uqr-scores-wrap">`;

    PARAMS.forEach(function (p) {
      var currentVal = r[p.key] || 0;
      _scores[p.key] = currentVal || null;
      var starsHtml = '';
      for (var n = 1; n <= 5; n++) {
        starsHtml += `<button class="uqr-star-btn ${currentVal >= n ? 'active' : ''}" onclick="window._uqrSetScore('${p.key}', ${n}, this.closest('.uqr-stars'))" data-val="${n}">★</button>`;
      }
      html += `
      <div class="uqr-score-row">
        <div class="lbl-s">
          <div>${p.label}</div>
          <div style="font-size:10px;color:#94a3b8;font-weight:400;">${p.desc}</div>
        </div>
        <div class="uqr-stars" id="uqr_stars_${p.key}">${starsHtml}</div>
        <span class="uqr-score-val-label" id="uqr_sc_lbl_${p.key}">${currentVal ? currentVal + '/5' : '—'}</span>
      </div>`;
    });

    html += `</div>

    <!-- 7. Overall Remarks -->
    <div>
      <label style="font-size:12px;font-weight:700;color:#1e293b;display:block;margin-bottom:6px;">
        <i class="fas fa-comment-dots me-1" style="color:#0f766e;"></i>Overall Remarks &amp; Feedback
      </label>
      <textarea id="uqrRemarks" rows="3" style="width:100%;border:1px solid #cbd5e1;border-radius:8px;padding:8px 12px;font-size:13px;resize:vertical;box-sizing:border-box;" placeholder="Enter general feedback, specific coaching points, or remarks for the executive…">${_esc(r.overall_remarks || '')}</textarea>
    </div>`;

    document.getElementById('uqrModalBody').innerHTML = html;
    document.getElementById('uqrSaveBtn').style.display = 'inline-flex';
    document.getElementById('uqrSkipBtn').style.display = 'inline-block';
  }

  window._uqrSetScore = function (key, val, starsEl) {
    _scores[key] = val;
    if (starsEl) {
      starsEl.querySelectorAll('.uqr-star-btn').forEach(function (btn) {
        btn.classList.toggle('active', parseInt(btn.dataset.val, 10) <= val);
      });
    }
    var lbl = document.getElementById('uqr_sc_lbl_' + key);
    if (lbl) lbl.textContent = val + '/5';

    // Recompute real-time average
    var sum = 0, count = 0;
    PARAMS.forEach(function (p) {
      if (_scores[p.key]) {
        sum += _scores[p.key];
        count++;
      }
    });
    var avg = count > 0 ? (sum / count) : null;
    var badge = document.getElementById('uqrOverallScoreBadge');
    if (badge) badge.innerHTML = _scoreLabel(avg);
  };

  window._uqrToggleAudio = function (url, id, defaultDuration) {
    _toggleAudio(url, id, defaultDuration);
  };

  window._uqrSeekAudio = function (val, id) {
    _seekAudio(val, id);
  };

  window._uqrSubmitReview = async function () {
    if (!_currentReviewId) return;
    var btn = document.getElementById('uqrSaveBtn');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving…';
    }

    try {
      var token = _getAuthToken();
      var remarks = document.getElementById('uqrRemarks')?.value || '';
      var payload = {
        score_script: _scores.score_script,
        score_tone: _scores.score_tone,
        score_info_accuracy: _scores.score_info_accuracy,
        score_customer_handling: _scores.score_customer_handling,
        score_closing: _scores.score_closing,
        score_disposition: _scores.score_disposition,
        overall_remarks: remarks,
        status: 'reviewed'
      };

      var fetchFn = typeof window.staffFetch === 'function' ? window.staffFetch : fetch;
      var headers = {
        'Content-Type': 'application/json'
      };
      if (token) headers['Authorization'] = 'Bearer ' + token;

      var res = await fetchFn('/api/v1/call-quality/reviews/' + _currentReviewId + '/submit', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(payload)
      });
      var data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.error || 'Failed to submit review');

      if (typeof window.showToast === 'function') {
        window.showToast('Call Quality Review saved successfully!', 'success');
      } else {
        alert('Call Quality Review saved successfully!');
      }

      var savedReview = data.review || data;
      if (typeof _onSavedCallback === 'function') {
        _onSavedCallback(savedReview);
      }

      window.closeUniversalQualityReview();

      // If on CRM Dashboard, trigger quality report reload so Tab 4 instantly updates
      if (typeof window.loadQualityReport === 'function') {
        window.loadQualityReport();
      }

      // If universal history modal is open, refresh its calls list
      try {
        var uhmRoot = document.getElementById('universalHistoryModalRoot');
        if (uhmRoot && uhmRoot.style.display === 'flex' && typeof window.switchUniversalHistoryTab === 'function') {
          window.switchUniversalHistoryTab('calls');
        }
      } catch (_) {}
    } catch (e) {
      alert('Error saving review: ' + e.message);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-save"></i> Save Review';
      }
    }
  };

  window._uqrSkipReview = async function () {
    if (!_currentReviewId) return;
    var btn = document.getElementById('uqrSkipBtn');
    if (btn) btn.disabled = true;
    try {
      var token = _getAuthToken();
      var fetchFn = typeof window.staffFetch === 'function' ? window.staffFetch : fetch;
      var headers = {
        'Content-Type': 'application/json'
      };
      if (token) headers['Authorization'] = 'Bearer ' + token;

      await fetchFn('/api/v1/call-quality/reviews/' + _currentReviewId + '/submit', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ status: 'skipped', overall_remarks: 'Skipped by reviewer.' })
      });
      window.closeUniversalQualityReview();
      if (typeof window.loadQualityReport === 'function') {
        window.loadQualityReport();
      }
    } catch (e) {
      alert('Error skipping review: ' + e.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  };

  window.openUniversalQualityReview = async function (options) {
    options = options || {};
    _injectStylesAndModal();
    _stopAudio();

    _onSavedCallback = options.onReviewSaved || null;
    _currentReviewId = null;
    _currentReviewData = null;
    _scores = { score_script: null, score_tone: null, score_info_accuracy: null, score_customer_handling: null, score_closing: null, score_disposition: null };

    var modal = document.getElementById('universalQualityReviewModal');
    var body = document.getElementById('uqrModalBody');
    var saveBtn = document.getElementById('uqrSaveBtn');
    var skipBtn = document.getElementById('uqrSkipBtn');

    if (saveBtn) saveBtn.style.display = 'none';
    if (skipBtn) skipBtn.style.display = 'none';

    document.getElementById('uqrModalTitle').innerHTML = '<i class="fas fa-clipboard-check" style="color:#0f766e;"></i> Quality Review';
    body.innerHTML = '<div class="uqr-spinner-wrap"><i class="fas fa-spinner fa-spin fa-2x"></i><div style="margin-top:8px;font-size:12px;">Loading review details…</div></div>';

    modal.classList.add('open');

    try {
      var fetchFn = typeof window.staffFetch === 'function' ? window.staffFetch : fetch;
      var token = _getAuthToken();
      var headers = {
        'Content-Type': 'application/json'
      };
      if (token) headers['Authorization'] = 'Bearer ' + token;

      var res = await fetchFn('/api/v1/call-quality/reviews/open-or-create', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({
          call_log_id: options.callLogId || options.raw_id || null,
          call_session_id: options.callSessionId || null,
          phone: options.phone || null,
          lead_id: options.leadId || null
        })
      });

      if (!res.ok) {
        var errData = await res.json().catch(function () { return {}; });
        throw new Error(errData.detail || errData.error || ('Server returned HTTP ' + res.status));
      }

      var data = await res.json();
      _currentReviewId = data.id;
      _currentReviewData = data;
      _renderReviewData(data);
    } catch (e) {
      body.innerHTML = `
        <div style="text-align:center;padding:40px;color:#ef4444;">
          <i class="fas fa-exclamation-circle fa-2x"></i>
          <div style="font-weight:700;margin-top:8px;">Failed to load quality review</div>
          <div style="font-size:12px;color:#64748b;margin-top:4px;">${_esc(e.message)}</div>
          <button class="uqr-btn-close" onclick="window.closeUniversalQualityReview()" style="margin-top:16px;">Close</button>
        </div>
      `;
    }
  };

  window.closeUniversalQualityReview = function () {
    _stopAudio();
    var modal = document.getElementById('universalQualityReviewModal');
    if (modal) modal.classList.remove('open');
    _currentReviewId = null;
    _currentReviewData = null;
    _onSavedCallback = null;
  };

  // Pre-inject on script evaluation if DOM ready
  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', _injectStylesAndModal);
    } else {
      _injectStylesAndModal();
    }
  }
})();
