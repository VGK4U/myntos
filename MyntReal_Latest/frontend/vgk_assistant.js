/**
 * VGK Assistant — AI Voice & Text Assistant
 * DC_VGK_001 | Multi-language: English, Hindi, Telugu
 * Role-based access: intents limited to user's MENU_MASTER permissions
 * Portals: Staff, Partner | Works on all authenticated pages
 */
(function () {
  if (window.__VGK_LOADED__) return;
  window.__VGK_LOADED__ = true;

  // ─── Config ───────────────────────────────────────────────────────────────
  const VGK_VERSION = '1.0.0';
  const LOGO_URL = '/public/vgk4u-logo-100.png';

  const MENU_INTENT_MAP = {
    create_task:           ['staff_task_tracker', 'staff_tasks_assigned_by_me', 'staff_tasks_assigned_to_me'],
    edit_task:             ['staff_task_tracker', 'staff_tasks_assigned_by_me'],
    create_lead:           ['staff_crm_dashboard', 'staff_leads', 'staff_my_leads', 'rvz_crm_leads'],
    create_service_ticket: ['staff_service_queue', 'staff_service_tickets', 'service_queue'],
    start_journey:         ['staff_my_journeys', 'staff_all_journeys', 'staff_vgk4u_journeys'],
    end_journey:           ['staff_my_journeys', 'staff_all_journeys', 'staff_vgk4u_journeys'],
    marketplace_search:    ['staff_marketplace', 'marketplace', 'staff_zynova_po'],
    query_crm_segment:     ['staff_crm_dashboard', 'staff_leads', 'staff_my_leads', 'staff_team_leads', 'rvz_crm_leads'],
    query_open_leads:      ['staff_crm_dashboard', 'staff_leads', 'staff_my_leads', 'staff_team_leads', 'rvz_crm_leads'],
    query_today_leads:     ['staff_crm_dashboard', 'staff_leads', 'staff_my_leads', 'staff_team_leads', 'rvz_crm_leads'],
    query_overdue_leads:   ['staff_crm_dashboard', 'staff_leads', 'staff_my_leads', 'staff_team_leads', 'rvz_crm_leads'],
    query_walkin_leads:    ['staff_crm_dashboard', 'staff_leads', 'staff_my_leads', 'staff_team_leads', 'rvz_crm_leads'],
    query_day_planner:     ['staff_day_planner'],
    query_tasks:           ['staff_task_tracker', 'staff_tasks_assigned_to_me', 'staff_tasks_assigned_by_me'],
    query_talk_time:       ['call_tracking_dashboard'],
    general_help:          [],
  };

  const LABELS = {
    en: {
      title: 'VGK Assistant', placeholder: 'Type or speak…',
      greeting: "Hi! I'm VGK Assistant 👋\nWhat would you like to do today?",
      speak_greeting: "Hi, I'm VGK Assistant. What would you like to do?",
      listening: 'Listening…', error_mic: 'Microphone access denied.',
      confirm_btn: 'Confirm & Create', cancel_btn: 'Cancel',
      done: '✅ Done!', sending: 'Processing…',
      error_api: 'Something went wrong. Please try again.',
      confirm_header: '📋 Please confirm:', suggestions: 'Suggestions:',
      marketplace_placeholder: 'Say a product name or category…',
    },
    hi: {
      title: 'VGK सहायक', placeholder: 'टाइप करें या बोलें…',
      greeting: "नमस्ते! मैं VGK सहायक हूँ 👋\nआज आप क्या करना चाहते हैं?",
      speak_greeting: "नमस्ते, मैं VGK सहायक हूँ। आप क्या करना चाहते हैं?",
      listening: 'सुन रहा हूँ…', error_mic: 'माइक्रोफ़ोन की अनुमति नहीं मिली।',
      confirm_btn: 'पुष्टि करें', cancel_btn: 'रद्द करें',
      done: '✅ हो गया!', sending: 'प्रोसेस हो रहा है…',
      error_api: 'कुछ गलत हो गया। कृपया फिर कोशिश करें।',
      confirm_header: '📋 कृपया पुष्टि करें:', suggestions: 'सुझाव:',
      marketplace_placeholder: 'उत्पाद नाम या श्रेणी बोलें…',
    },
    te: {
      title: 'VGK సహాయకుడు', placeholder: 'టైప్ చేయండి లేదా మాట్లాడండి…',
      greeting: "హలో! నేను VGK సహాయకుడిని 👋\nఈరోజు మీరు ఏం చేయాలనుకుంటున్నారు?",
      speak_greeting: "హలో, నేను VGK సహాయకుడిని. మీరు ఏం చేయాలనుకుంటున్నారు?",
      listening: 'వింటున్నాను…', error_mic: 'మైక్రోఫోన్ అనుమతి నిరాకరించబడింది.',
      confirm_btn: 'నిర్ధారించు', cancel_btn: 'రద్దు చేయి',
      done: '✅ పూర్తయింది!', sending: 'ప్రాసెస్ అవుతోంది…',
      error_api: 'ఏదో తప్పు జరిగింది. దయచేసి మళ్ళీ ప్రయత్నించండి.',
      confirm_header: '📋 దయచేసి నిర్ధారించండి:', suggestions: 'సూచనలు:',
      marketplace_placeholder: 'ఉత్పత్తి పేరు లేదా వర్గం చెప్పండి…',
    },
  };

  const LANG_SPEECH = { en: 'en-IN', hi: 'hi-IN', te: 'te-IN' };

  // ─── State ─────────────────────────────────────────────────────────────────
  let state = {
    open: false,
    lang: 'en',
    portalType: 'staff',
    token: null,
    allowedIntents: null,
    conversationHistory: [],
    listening: false,
    recognition: null,
    pending: false,
    currentIntent: null,
    resolvedData: {},
  };

  // ─── Helpers ───────────────────────────────────────────────────────────────
  function L(key) { return (LABELS[state.lang] || LABELS.en)[key] || key; }

  function getCookie(name) {
    return (document.cookie.split(';').map(c => c.trim()).find(c => c.startsWith(name + '=')) || '').split('=').slice(1).join('=') || null;
  }

  function detectPortalAndToken() {
    const isMarketplacePage = window.location.pathname === '/marketplace'
      || window.location.pathname.startsWith('/marketplace')
      || window.location.pathname === '/ecom'
      || window.location.pathname.startsWith('/ecom');
    if (isMarketplacePage) {
      state.portalType = 'marketplace';
      state.token = null;
      return;
    }
    const partnerCookie = getCookie('partner_token');
    const staffCookie = getCookie('staff_token');
    const partnerLocal = localStorage.getItem('partner_token');
    const staffLocal = localStorage.getItem('staff_token');
    const partnerToken = partnerCookie || partnerLocal;
    const staffToken = staffCookie || staffLocal;
    if (partnerToken) { state.portalType = 'partner'; state.token = partnerToken; }
    else if (staffToken) { state.portalType = 'staff'; state.token = staffToken; }
    else { state.token = null; }
  }

  function computeAllowedIntents() {
    if (state.portalType === 'marketplace') {
      // DC: Marketplace is a public page — limit to product search only
      state.allowedIntents = ['general_help', 'marketplace_search'];
      return;
    }
    // DC: For authenticated staff and partners — allow ALL intents (no restriction by menu codes)
    // The backend enforces access control per intent via role/permissions
    state.allowedIntents = null;
  }

  function escHtml(str) {
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/\n/g,'<br>');
  }

  // ─── CSS Injection ─────────────────────────────────────────────────────────
  function injectCSS() {
    if (document.getElementById('vgk-css')) return;
    const style = document.createElement('style');
    style.id = 'vgk-css';
    style.textContent = `
      :root { --vgk-purple: #6c3de8; --vgk-blue: #4361ee; --vgk-grad: linear-gradient(135deg, #6c3de8, #4361ee); }

      #vgkFab {
        position: fixed; bottom: 24px; right: 24px; z-index: 99998;
        width: 60px; height: 60px; border-radius: 50%;
        background: var(--vgk-grad); border: none; cursor: grab;
        box-shadow: 0 4px 20px rgba(108,61,232,.45);
        display: flex; align-items: center; justify-content: center;
        transition: transform .2s, box-shadow .2s;
        animation: vgkPulse 3s infinite;
        user-select: none; -webkit-user-select: none; touch-action: none;
      }
      #vgkFab:hover { transform: scale(1.1); box-shadow: 0 6px 28px rgba(108,61,232,.6); }
      #vgkFab.vgk-dragging { cursor: grabbing; transform: scale(1.08); animation: none !important; transition: none !important; }
      #vgkFab.vgk-snapping { transition: left .45s cubic-bezier(.34,1.56,.64,1), top .45s cubic-bezier(.34,1.56,.64,1) !important; }
      #vgkFab img { width: 42px; height: 42px; border-radius: 50%; object-fit: contain; background: rgba(255,255,255,.92); padding: 3px; }
      @keyframes vgkPulse {
        0%,100% { box-shadow: 0 4px 20px rgba(108,61,232,.45); }
        50% { box-shadow: 0 4px 28px rgba(108,61,232,.75), 0 0 0 8px rgba(108,61,232,.12); }
      }

      #vgkOverlay {
        display: none; position: fixed; inset: 0; z-index: 99997;
        background: transparent;
      }
      #vgkOverlay.vgk-open { display: block; }

      #vgkModal {
        position: fixed; bottom: 96px; right: 24px; z-index: 99999;
        width: 360px; max-width: calc(100vw - 32px);
        background: #fff; border-radius: 20px;
        box-shadow: 0 16px 56px rgba(0,0,0,.22);
        display: flex; flex-direction: column;
        transform: translateY(20px) scale(.95); opacity: 0;
        pointer-events: none; transition: all .25s cubic-bezier(.34,1.56,.64,1);
        overflow: hidden; max-height: 520px;
      }
      #vgkModal.vgk-open { transform: none; opacity: 1; pointer-events: auto; }

      .vgk-header {
        background: var(--vgk-grad); color: #fff;
        padding: 12px 14px; display: flex; align-items: center; gap: 10px;
        flex-shrink: 0;
      }
      .vgk-header img { width: 32px; height: 32px; border-radius: 50%; border: 2px solid rgba(255,255,255,.5); }
      .vgk-header-title { flex: 1; font-weight: 700; font-size: 14px; letter-spacing: .3px; }
      .vgk-header-sub { font-size: 10px; opacity: .8; }
      .vgk-lang-btns { display: flex; gap: 4px; }
      .vgk-lang-btn {
        background: rgba(255,255,255,.2); border: 1px solid rgba(255,255,255,.4);
        color: #fff; font-size: 11px; font-weight: 600;
        border-radius: 20px; padding: 3px 8px; cursor: pointer; transition: .15s;
      }
      .vgk-lang-btn.active { background: rgba(255,255,255,.9); color: var(--vgk-purple); }
      .vgk-close {
        background: rgba(255,255,255,.2); border: none; color: #fff;
        width: 28px; height: 28px; border-radius: 50%; cursor: pointer;
        font-size: 16px; line-height: 1; display: flex; align-items: center; justify-content: center;
        transition: .15s; flex-shrink: 0;
      }
      .vgk-close:hover { background: rgba(255,255,255,.35); }

      .vgk-body { flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
      .vgk-body::-webkit-scrollbar { width: 4px; }
      .vgk-body::-webkit-scrollbar-thumb { background: #ddd; border-radius: 4px; }

      .vgk-bubble {
        max-width: 85%; padding: 9px 12px; border-radius: 16px;
        font-size: 13px; line-height: 1.5; word-wrap: break-word;
      }
      .vgk-bubble.assistant {
        background: #f0edfb; color: #1a1a2e; border-bottom-left-radius: 4px; align-self: flex-start;
      }
      .vgk-bubble.user {
        background: var(--vgk-grad); color: #fff; border-bottom-right-radius: 4px; align-self: flex-end;
      }
      .vgk-bubble.loading { display: flex; align-items: center; gap: 6px; }
      .vgk-dots span {
        display: inline-block; width: 6px; height: 6px; background: #9b8ec4;
        border-radius: 50%; animation: vgkDot .9s infinite;
      }
      .vgk-dots span:nth-child(2) { animation-delay: .2s; }
      .vgk-dots span:nth-child(3) { animation-delay: .4s; }
      @keyframes vgkDot { 0%,80%,100%{transform:scale(.7);opacity:.4} 40%{transform:scale(1);opacity:1} }

      .vgk-options { padding: 0 14px 6px; display: flex; flex-wrap: wrap; gap: 6px; }
      .vgk-chip {
        background: #ede9fc; color: var(--vgk-purple); border: 1px solid #c9bef7;
        border-radius: 20px; padding: 5px 12px; font-size: 12px; font-weight: 600;
        cursor: pointer; transition: .15s; white-space: nowrap;
      }
      .vgk-chip:hover { background: var(--vgk-purple); color: #fff; }

      .vgk-confirm-card {
        background: #f0fdf4; border: 1.5px solid #22c55e; border-radius: 12px;
        padding: 12px; font-size: 12.5px; margin: 0 14px 8px;
      }
      .vgk-confirm-card h6 { color: #15803d; font-weight: 700; margin: 0 0 8px; font-size: 13px; }
      .vgk-confirm-card table { width: 100%; border-collapse: collapse; }
      .vgk-confirm-card td { padding: 3px 0; }
      .vgk-confirm-card td:first-child { color: #555; width: 40%; font-weight: 600; }
      .vgk-confirm-btns { display: flex; gap: 8px; margin-top: 10px; }
      .vgk-btn-confirm {
        flex: 1; background: #22c55e; color: #fff; border: none;
        border-radius: 8px; padding: 8px; font-size: 13px; font-weight: 700; cursor: pointer;
        transition: .15s;
      }
      .vgk-btn-confirm:hover { background: #16a34a; }
      .vgk-btn-cancel {
        background: #f1f5f9; color: #64748b; border: none; border-radius: 8px;
        padding: 8px 14px; font-size: 13px; cursor: pointer; transition: .15s;
      }
      .vgk-btn-cancel:hover { background: #e2e8f0; }

      .vgk-footer { padding: 10px 14px; border-top: 1px solid #eee; flex-shrink: 0; }
      .vgk-input-row { display: flex; gap: 8px; align-items: center; }
      .vgk-text-input {
        flex: 1; border: 1.5px solid #ddd; border-radius: 24px;
        padding: 9px 14px; font-size: 13px; outline: none; transition: .15s;
        background: #fafafa;
      }
      .vgk-text-input:focus { border-color: var(--vgk-purple); background: #fff; }
      .vgk-mic-btn, .vgk-send-btn {
        width: 38px; height: 38px; border-radius: 50%; border: none;
        cursor: pointer; display: flex; align-items: center; justify-content: center;
        font-size: 16px; transition: .15s; flex-shrink: 0;
      }
      .vgk-mic-btn { background: #f0edfb; color: var(--vgk-purple); }
      .vgk-mic-btn.vgk-listening { background: #fee2e2; color: #ef4444; animation: vgkPulse 1s infinite; }
      .vgk-send-btn { background: var(--vgk-grad); color: #fff; }
      .vgk-send-btn:hover { opacity: .85; }
      .vgk-status-bar { font-size: 11px; color: #888; text-align: center; margin-top: 5px; min-height: 16px; }

      @media (max-width: 480px) {
        #vgkModal { right: 12px; bottom: 88px; width: calc(100vw - 24px); max-height: 65vh; }
        #vgkFab { bottom: 18px; right: 16px; width: 54px; height: 54px; }
      }
    `;
    document.head.appendChild(style);
  }

  // ─── DOM Build ─────────────────────────────────────────────────────────────
  function buildDOM() {
    if (document.getElementById('vgkFab')) return;

    document.body.insertAdjacentHTML('beforeend', `
      <div id="vgkOverlay"></div>
      <button id="vgkFab" title="VGK Assistant" aria-label="Open VGK Assistant">
        <img src="${LOGO_URL}" onerror="this.style.display='none';this.parentElement.innerHTML='<span style=\\'font-size:26px\\'>🤖</span>'">
      </button>
      <div id="vgkModal" role="dialog" aria-label="VGK Assistant">
        <div class="vgk-header">
          <img src="${LOGO_URL}" onerror="this.style.display='none'">
          <div style="flex:1">
            <div class="vgk-header-title" id="vgkTitle">VGK Assistant</div>
            <div class="vgk-header-sub">AI Voice &amp; Text Assistant</div>
          </div>
          <div class="vgk-lang-btns">
            <button class="vgk-lang-btn active" data-lang="en">EN</button>
            <button class="vgk-lang-btn" data-lang="hi">हि</button>
            <button class="vgk-lang-btn" data-lang="te">తె</button>
          </div>
          <button class="vgk-close" id="vgkClose">✕</button>
        </div>
        <div class="vgk-body" id="vgkBody"></div>
        <div class="vgk-options" id="vgkOptions"></div>
        <div id="vgkConfirmArea"></div>
        <div class="vgk-footer">
          <div class="vgk-input-row">
            <input type="text" class="vgk-text-input" id="vgkInput" autocomplete="off">
            <button class="vgk-mic-btn" id="vgkMic" title="Voice input">🎤</button>
            <button class="vgk-send-btn" id="vgkSend" title="Send">➤</button>
          </div>
          <div class="vgk-status-bar" id="vgkStatus"></div>
        </div>
      </div>
    `);
  }

  // ─── Core UI ───────────────────────────────────────────────────────────────
  function toggleModal(open) {
    state.open = (open !== undefined) ? open : !state.open;
    if (state.open) positionModalNearFab();
    else resetModalPosition();
    document.getElementById('vgkModal').classList.toggle('vgk-open', state.open);
    document.getElementById('vgkOverlay').classList.toggle('vgk-open', state.open);
    if (state.open && document.getElementById('vgkBody').children.length === 0) {
      addBubble('assistant', L('greeting'));
      speak(L('speak_greeting'));
    }
    if (state.open) document.getElementById('vgkInput').focus();
    if (!state.open) stopListening();
  }

  function addBubble(role, text, isLoading) {
    const body = document.getElementById('vgkBody');
    const div = document.createElement('div');
    div.className = `vgk-bubble ${role}`;
    if (isLoading) {
      div.classList.add('loading');
      div.innerHTML = `<div class="vgk-dots"><span></span><span></span><span></span></div>`;
      div.id = 'vgkLoading';
    } else {
      div.innerHTML = escHtml(text);
    }
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
    return div;
  }

  function removeLoading() {
    const el = document.getElementById('vgkLoading');
    if (el) el.remove();
  }

  function showOptions(options) {
    const area = document.getElementById('vgkOptions');
    area.innerHTML = '';
    options.forEach(opt => {
      const btn = document.createElement('button');
      btn.className = 'vgk-chip';
      btn.textContent = opt.label;
      btn.onclick = () => { area.innerHTML = ''; sendMessage(opt.label, opt.value); };
      area.appendChild(btn);
    });
  }

  function clearOptions() { document.getElementById('vgkOptions').innerHTML = ''; }

  function showConfirmCard(resolvedData, intent) {
    const area = document.getElementById('vgkConfirmArea');
    const rows = Object.entries(resolvedData)
      .filter(([k]) => !k.includes('_id') && k !== 'portal_type')
      .map(([k, v]) => `<tr><td>${k.replace(/_/g,' ')}:</td><td><strong>${escHtml(String(v))}</strong></td></tr>`)
      .join('');
    area.innerHTML = `
      <div class="vgk-confirm-card">
        <h6>${L('confirm_header')}</h6>
        <table>${rows}</table>
        <div class="vgk-confirm-btns">
          <button class="vgk-btn-confirm" id="vgkConfirmBtn">${L('confirm_btn')}</button>
          <button class="vgk-btn-cancel" id="vgkCancelBtn">${L('cancel_btn')}</button>
        </div>
      </div>`;
    document.getElementById('vgkConfirmBtn').onclick = () => executeAction(intent, resolvedData);
    document.getElementById('vgkCancelBtn').onclick = () => {
      area.innerHTML = '';
      reset();
      addBubble('assistant', L('greeting'));
    };
  }

  function setStatus(text) { document.getElementById('vgkStatus').textContent = text; }

  function reset() {
    state.conversationHistory = [];
    state.currentIntent = null;
    state.resolvedData = {};
    clearOptions();
    document.getElementById('vgkConfirmArea').innerHTML = '';
  }

  // ─── Language ──────────────────────────────────────────────────────────────
  function setLanguage(lang) {
    state.lang = lang;
    document.getElementById('vgkTitle').textContent = L('title');
    const ph = state.portalType === 'marketplace' ? (L('marketplace_placeholder') || L('placeholder')) : L('placeholder');
    document.getElementById('vgkInput').placeholder = ph;
    document.querySelectorAll('.vgk-lang-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.lang === lang);
    });
  }

  // ─── Voice ─────────────────────────────────────────────────────────────────
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const hasSpeech = !!SR;

  function speak(text) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(text);
    utt.lang = LANG_SPEECH[state.lang] || 'en-IN';
    utt.rate = 0.95; utt.pitch = 1.05;
    window.speechSynthesis.speak(utt);
  }

  function startListening() {
    if (!hasSpeech) { setStatus(L('error_mic')); return; }
    if (state.listening) { stopListening(); return; }

    const micLang = LANG_SPEECH[state.lang] || 'en-IN';
    const listeningStatus = L('listening');

    function _startRec(lang, statusText) {
      const rec = new SR();
      rec.lang = lang;
      rec.continuous = false;
      rec.interimResults = true;
      rec.onstart = () => {
        state.listening = true;
        document.getElementById('vgkMic').classList.add('vgk-listening');
        setStatus(statusText);
      };
      rec.onresult = (e) => {
        let interim = '', final = '';
        for (let i = e.resultIndex; i < e.results.length; i++) {
          if (e.results[i].isFinal) final += e.results[i][0].transcript;
          else interim += e.results[i][0].transcript;
        }
        const inp = document.getElementById('vgkInput');
        if (inp) inp.value = final || interim;
        if (final) { stopListening(); sendMessage(final); }
      };
      rec.onerror = (e) => {
        stopListening();
        if (e.error === 'not-allowed') {
          setStatus(L('error_mic'));
        } else if (e.error === 'language-not-supported' && lang !== 'en-IN') {
          // hi-IN failed on this device — silently retry with en-IN
          setTimeout(() => _startRec('en-IN', L('listening')), 300);
        } else {
          setStatus('');
        }
      };
      rec.onend = () => stopListening();
      state.recognition = rec;
      try { rec.start(); } catch (e) { stopListening(); }
    }

    _startRec(micLang, listeningStatus);
  }

  function stopListening() {
    state.listening = false;
    if (state.recognition) { try { state.recognition.stop(); } catch(e) {} state.recognition = null; }
    document.getElementById('vgkMic').classList.remove('vgk-listening');
    setStatus('');
  }

  // ─── API Call ──────────────────────────────────────────────────────────────
  async function callVGK(userMessage) {
    const endpoint = state.portalType === 'marketplace'
      ? '/api/v1/vgk/public/process'
      : state.portalType === 'partner'
        ? '/api/v1/vgk/partner/process'
        : '/api/v1/vgk/staff/process';

    const body = {
      user_message: userMessage,
      conversation_history: state.conversationHistory,
      language: state.lang,
      company_id: window.__VGK_COMPANY_ID__ || window.__MARKETPLACE_COMPANY_ID__ || null,
      allowed_intents: state.allowedIntents,
      accessible_routes: window.__VGK_MENU_ROUTES__ || null,
    };

    const headers = { 'Content-Type': 'application/json' };
    if (state.token) headers['Authorization'] = `Bearer ${state.token}`;

    const resp = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  }

  // ─── Action Execution ──────────────────────────────────────────────────────
  async function executeAction(intent, data) {
    document.getElementById('vgkConfirmArea').innerHTML = '';
    addBubble(null, null, true);
    setStatus(L('sending'));

    try {
      let resultMsg = L('done');

      if (intent === 'create_task') {
        const assigneeId = parseInt(data.primary_assignee_id || data.assignee_id || 0, 10);
        if (!assigneeId) throw new Error('Could not resolve assignee. Please specify a name clearly.');
        const payload = {
          title: data.title || 'New Task',
          primary_assignee_id: assigneeId,
          due_date: data.due_date || null,
          priority: data.priority || 'medium',
          description: data.description || '',
          secondary_assignee_ids: [],
          phases: [],
        };
        const r = await fetch('/api/v1/staff/tasks/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${state.token}` },
          body: JSON.stringify(payload),
        });
        const j = await r.json();
        if (!r.ok) throw new Error(j.detail || 'Task creation failed');
        resultMsg = `✅ Task created: ${j.task_code || j.task_id || ''}`;
        speak(resultMsg);

      } else if (intent === 'start_journey') {
        const companyId = data.company_id || data.selected_company_id;
        if (!companyId) { removeLoading(); addBubble('assistant', 'Please select a company first.'); return; }
        const pos = await new Promise((res, rej) =>
          navigator.geolocation.getCurrentPosition(res, rej, { timeout: 8000 }));
        const payload = {
          company_id: parseInt(companyId),
          purpose: data.purpose || 'other',
          transport_mode: data.transport_mode || 'bike',
          location: { latitude: pos.coords.latitude, longitude: pos.coords.longitude, accuracy: pos.coords.accuracy },
        };
        const r = await fetch('/api/v1/staff/journeys/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${state.token}` },
          body: JSON.stringify(payload),
        });
        const j = await r.json();
        if (!r.ok) throw new Error(j.detail || 'Could not start journey');
        resultMsg = `✅ Journey started for ${data.company_name || ''}!`;
        speak(resultMsg);

      } else if (intent === 'create_lead') {
        const companyId = window.__VGK_COMPANY_ID__ || data.company_id || 1;
        const payload = {
          name: data.lead_name || data.name,
          phone: data.phone || null,
          source: 'VGK Assistant',
          source_details: 'Created via VGK AI Assistant',
        };
        const r = await fetch(`/api/v1/crm/leads/?company_id=${companyId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${state.token}` },
          body: JSON.stringify(payload),
        });
        const j = await r.json();
        if (!r.ok) throw new Error(j.detail || 'Lead creation failed');
        resultMsg = `✅ Lead created for ${payload.name}! (ID: ${j.lead_id || ''})`;
        speak(resultMsg);

      } else if (intent === 'create_service_ticket') {
        const payload = {
          issue_category: data.issue_category || 'General Complaint',
          issue_description: data.issue_description || data.description,
          ticket_type: data.ticket_type || 'general',
          customer_name: data.customer_name || null,
          customer_phone: data.phone || data.customer_phone || null,
          source_channel: 'VGK',
        };
        const r = await fetch('/api/v1/tickets/service/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${state.token}` },
          body: JSON.stringify(payload),
        });
        const j = await r.json();
        if (!r.ok) throw new Error(j.detail || 'Ticket creation failed');
        resultMsg = `✅ Ticket raised for ${payload.customer_name || 'customer'}! (${j.ticket_id || ''})`;
        speak(resultMsg);

      } else if (intent === 'end_journey') {
        const journeyId = data.journey_id;
        if (!journeyId) throw new Error('No active journey found to end.');
        const pos = await new Promise((res, rej) =>
          navigator.geolocation.getCurrentPosition(res, rej, { timeout: 8000, maximumAge: 30000 })
        ).catch(() => null);
        const payload = {
          location: pos ? { latitude: pos.coords.latitude, longitude: pos.coords.longitude, accuracy: pos.coords.accuracy } : null,
        };
        const r = await fetch(`/api/v1/staff/journeys/${journeyId}/end`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${state.token}` },
          body: JSON.stringify(payload),
        });
        const j = await r.json();
        if (!r.ok) throw new Error(j.detail || 'Could not end journey');
        resultMsg = `✅ Journey ended! Distance: ${(j.total_distance_km || 0).toFixed(1)} km`;
        speak(resultMsg);

      } else if (intent === 'query_crm_segment') {
        const route = data.route || data.resolved_data?.route || '/staff/crm/team-leads';
        const segName = data.segment_name || data.resolved_data?.segment_name || 'CRM';
        removeLoading();
        addBubble('assistant', resultMsg || `📋 Opening ${segName} leads…`);
        speak(`Opening ${segName} leads now.`);
        setStatus('');
        setTimeout(() => { window.location.href = route; }, 900);
        return;

      } else if (intent === 'navigate') {
        const route = data.route || data.resolved_data?.route;
        if (!route) throw new Error('No page route specified.');
        removeLoading();
        addBubble('assistant', `✅ Navigating to ${route}…`);
        speak('Opening page now.');
        setStatus('');
        setTimeout(() => { window.location.href = route; }, 800);
        return;

      } else if (intent === 'query_kra') {
        const route = data.route || '/staff/kra';
        removeLoading();
        addBubble('assistant', `✅ Opening KRA page…`);
        speak('Opening KRA page.');
        setStatus('');
        setTimeout(() => { window.location.href = route; }, 800);
        return;

      } else if (intent === 'log_call') {
        removeLoading();
        addBubble('assistant', `Opening Call Management to log your call…`);
        speak('Opening call management page.');
        setStatus('');
        setTimeout(() => { window.location.href = '/staff/call-management'; }, 800);
        return;

      } else if (intent === 'create_walkin') {
        const payload = {
          customer_name:  data.customer_name || '',
          customer_phone: data.customer_phone || '',
          visit_purpose:  data.visit_purpose || 'general',
          lead_source:    'walk_in',
        };
        if (!payload.customer_name || !payload.customer_phone)
          throw new Error('Missing customer name or phone for walk-in.');
        const r = await fetch('/api/v1/partner/walkins', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${state.token}` },
          body: JSON.stringify(payload),
        });
        const j = await r.json();
        if (!r.ok) throw new Error(j.detail || 'Walk-in creation failed');
        resultMsg = `✅ Walk-in #${j.id || ''} recorded for ${payload.customer_name}!`;
        speak('Walk-in recorded successfully.');
        setTimeout(() => { window.location.href = '/partner/walkins'; }, 1200);

      } else if (intent === 'query_partner_activity') {
        removeLoading();
        addBubble('assistant', resultMsg || data.reply_text || 'Here are your followups.');
        speak('Today\'s followup activity loaded.');
        setStatus('');
        return;

      } else if (intent === 'query_attendance') {
        const attMsg = resultMsg || 'Attendance info loaded.';
        removeLoading();
        const body = document.getElementById('vgkBody');
        const wrap = document.createElement('div');
        wrap.style.cssText = 'margin:4px 0;';
        const bubble = document.createElement('div');
        bubble.className = 'vgk-bubble vgk-bubble-assistant';
        bubble.textContent = attMsg;
        wrap.appendChild(bubble);
        const navBtn = document.createElement('button');
        navBtn.style.cssText = 'width:100%;background:linear-gradient(135deg,#0ea5e9,#0284c7);color:#fff;border:none;border-radius:8px;padding:7px 10px;font-size:12px;font-weight:700;cursor:pointer;margin-top:5px;display:flex;align-items:center;justify-content:center;gap:5px;';
        navBtn.innerHTML = '<i class="fas fa-calendar-check"></i> View Attendance Page';
        navBtn.onclick = () => { window.location.href = '/staff/timesheet'; };
        wrap.appendChild(navBtn);
        body.appendChild(wrap);
        body.scrollTop = body.scrollHeight;
        speak('Attendance info ready.');
        setStatus('');
        return;

      } else if (intent === 'query_open_leads' || intent === 'query_today_leads' ||
                 intent === 'query_overdue_leads' || intent === 'query_walkin_leads') {
        const route = data.route || data.resolved_data?.route || '/staff/crm/team-leads';
        const filterLabel = data.filter_label || data.resolved_data?.filter_label || 'Leads';
        const leadCount = data.lead_count ?? data.resolved_data?.lead_count;
        const infoMsg = resultMsg || `📋 Opening ${filterLabel}…`;
        removeLoading();
        const body = document.getElementById('vgkBody');
        const wrap = document.createElement('div');
        wrap.style.cssText = 'margin:4px 0;';
        const bubble = document.createElement('div');
        bubble.className = 'vgk-bubble vgk-bubble-assistant';
        bubble.textContent = infoMsg;
        wrap.appendChild(bubble);
        const navBtn = document.createElement('button');
        navBtn.style.cssText = 'width:100%;background:linear-gradient(135deg,#6c3de8,#9b59b6);color:#fff;border:none;border-radius:8px;padding:7px 10px;font-size:12px;font-weight:700;cursor:pointer;margin-top:5px;display:flex;align-items:center;justify-content:center;gap:5px;';
        const countLabel = leadCount != null ? ` (${leadCount})` : '';
        navBtn.innerHTML = `<i class="fas fa-users"></i> View ${filterLabel}${countLabel} →`;
        navBtn.onclick = () => { window.location.href = route; };
        wrap.appendChild(navBtn);
        body.appendChild(wrap);
        body.scrollTop = body.scrollHeight;
        speak(`Opening ${filterLabel} now.`);
        setStatus('');
        return;
      }

      removeLoading();
      addBubble('assistant', resultMsg);
      setStatus('');
      setTimeout(() => { reset(); }, 2000);

    } catch (err) {
      removeLoading();
      const msg = `⚠️ ${err.message || L('error_api')}`;
      addBubble('assistant', msg);
      speak(msg);
      setStatus('');
    }
  }

  // ─── VGK Marketplace Product Cards ────────────────────────────────────────
  function renderVGKProductCards(products, lastQuery) {
    if (!products || !products.length) return;
    const body = document.getElementById('vgkBody');
    const wrap = document.createElement('div');
    wrap.style.cssText = 'margin:6px 0 4px 0;';

    const filterBtn = document.createElement('button');
    filterBtn.style.cssText = 'width:100%;background:linear-gradient(135deg,#6c3de8,#9b59b6);color:#fff;border:none;border-radius:8px;padding:6px 10px;font-size:11px;font-weight:700;cursor:pointer;margin-bottom:6px;display:flex;align-items:center;justify-content:center;gap:5px;';
    filterBtn.innerHTML = '<i class="fas fa-filter"></i> Show these on page';
    filterBtn.onclick = () => {
      if (typeof window.vgkFilterMarketplace === 'function') window.vgkFilterMarketplace(lastQuery || '');
    };
    wrap.appendChild(filterBtn);

    products.forEach(prod => {
      const card = document.createElement('div');
      card.style.cssText = 'display:flex;align-items:center;gap:8px;background:#f8faff;border:1px solid #e0e7ff;border-radius:8px;padding:7px 9px;margin-bottom:5px;';

      const imgWrap = document.createElement('div');
      imgWrap.style.cssText = 'width:40px;height:40px;flex-shrink:0;border-radius:5px;background:#fff;overflow:hidden;display:flex;align-items:center;justify-content:center;border:1px solid #e5e7eb;';
      if (prod.image_url) {
        const img = document.createElement('img');
        img.src = prod.image_url;
        img.alt = prod.name;
        img.style.cssText = 'width:100%;height:100%;object-fit:contain;';
        img.onerror = () => { imgWrap.innerHTML = '<i class="fas fa-bolt" style="color:#9ca3af;font-size:14px;"></i>'; };
        imgWrap.appendChild(img);
      } else {
        imgWrap.innerHTML = '<i class="fas fa-bolt" style="color:#9ca3af;font-size:14px;"></i>';
      }
      card.appendChild(imgWrap);

      if (typeof window.vgkRegisterProduct === 'function') window.vgkRegisterProduct(prod);
      const info = document.createElement('div');
      info.style.cssText = 'flex:1;min-width:0;';
      const specLine = prod.specifications ? `<div style="font-size:10px;color:#7c5a00;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escHtml(prod.specifications)}">📐 ${escHtml(prod.specifications)}</div>` : '';
      info.innerHTML = `<div style="font-size:12px;font-weight:700;color:#1a2e4a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escHtml(prod.name)}</div>
        <div style="font-size:10px;color:#6b7280;font-family:monospace;">${escHtml(prod.sku)}</div>
        ${specLine}
        <div style="font-size:12px;color:#15803d;font-weight:700;">${prod.price > 0 ? '₹' + prod.price.toLocaleString('en-IN') : '—'}</div>`;
      card.appendChild(info);

      const btns = document.createElement('div');
      btns.style.cssText = 'display:flex;flex-direction:column;gap:3px;flex-shrink:0;';

      const addBtn = document.createElement('button');
      addBtn.dataset.pid = prod.id;
      addBtn.style.cssText = 'background:#22c55e;color:#fff;border:none;border-radius:5px;padding:4px 8px;font-size:10px;font-weight:700;cursor:pointer;white-space:nowrap;';
      addBtn.innerHTML = '<i class="fas fa-plus"></i> Add';
      addBtn.onclick = () => {
        if (typeof window.vgkAddToBasket === 'function') {
          window.vgkAddToBasket(prod.id);
          addBtn.innerHTML = '<i class="fas fa-check"></i> Added';
          addBtn.style.background = '#15803d';
        }
      };

      const viewBtn = document.createElement('button');
      viewBtn.style.cssText = 'background:#e0e7ff;color:#6c3de8;border:none;border-radius:5px;padding:4px 8px;font-size:10px;font-weight:700;cursor:pointer;white-space:nowrap;';
      viewBtn.innerHTML = '<i class="fas fa-eye"></i> View';
      viewBtn.onclick = () => {
        if (typeof window.vgkScrollToProduct === 'function') window.vgkScrollToProduct(prod.id);
      };

      btns.appendChild(addBtn);
      btns.appendChild(viewBtn);
      card.appendChild(btns);
      wrap.appendChild(card);
    });

    body.appendChild(wrap);
    body.scrollTop = body.scrollHeight;
  }

  // ─── Send Message ──────────────────────────────────────────────────────────
  async function sendMessage(displayText, rawValue) {
    const text = (displayText || '').trim();
    if (!text || state.pending) return;
    clearOptions();
    document.getElementById('vgkInput').value = '';
    addBubble('user', text);
    addBubble(null, null, true);
    state.pending = true;
    setStatus(L('sending'));

    const apiText = rawValue || text;

    try {
      const resp = await callVGK(apiText);
      removeLoading();
      setStatus('');

      state.conversationHistory.push({ role: 'user', text: apiText });
      state.conversationHistory.push({ role: 'assistant', text: resp.reply_text });
      if (state.conversationHistory.length > 20) state.conversationHistory = state.conversationHistory.slice(-20);

      addBubble('assistant', resp.reply_text);
      if (resp.speak_text) speak(resp.speak_text);

      if (resp.products && resp.products.length && state.portalType === 'marketplace') {
        renderVGKProductCards(resp.products, apiText);
      }

      state.currentIntent = resp.intent;
      if (resp.resolved_data) Object.assign(state.resolvedData, resp.resolved_data);

      if (resp.options && resp.options.length) showOptions(resp.options);
      if (resp.action_ready && resp.intent !== 'general_help') {
        if (['navigate', 'query_kra', 'log_call', 'query_open_leads', 'query_today_leads', 'query_overdue_leads', 'query_walkin_leads'].includes(resp.intent)) {
          executeAction(resp.intent, state.resolvedData);
        } else {
          showConfirmCard(state.resolvedData, resp.intent);
        }
      }

    } catch (err) {
      removeLoading();
      setStatus('');
      addBubble('assistant', L('error_api'));
    } finally {
      state.pending = false;
    }
  }

  // ─── Draggable FAB ─────────────────────────────────────────────────────────
  let _fabDragged = false;
  let _snapTimer  = null;
  const FAB_DEFAULT = { bottom: 24, right: 24 };

  function makeFabDraggable() {
    const fab = document.getElementById('vgkFab');
    let isDragging = false, dragStartX, dragStartY, fabStartL, fabStartT;

    function fabRect() { return fab.getBoundingClientRect(); }

    function snapToDefault() {
      const rect = fabRect();
      fab.style.transition = 'none';
      fab.style.right = ''; fab.style.bottom = '';
      fab.style.left = rect.left + 'px'; fab.style.top = rect.top + 'px';
      // Force reflow then animate
      fab.offsetWidth;
      fab.classList.add('vgk-snapping');
      fab.style.left = (window.innerWidth  - 60 - FAB_DEFAULT.right)  + 'px';
      fab.style.top  = (window.innerHeight - 60 - FAB_DEFAULT.bottom) + 'px';
      setTimeout(() => {
        fab.classList.remove('vgk-snapping');
        fab.style.left = ''; fab.style.top = '';
        fab.style.right  = FAB_DEFAULT.right  + 'px';
        fab.style.bottom = FAB_DEFAULT.bottom + 'px';
        fab.style.animation = 'vgkPulse 3s infinite';
        _fabDragged = false;
      }, 460);
    }

    function resetSnapTimer() {
      clearTimeout(_snapTimer);
      _snapTimer = setTimeout(snapToDefault, 2 * 60 * 1000);
    }

    function onStart(e) {
      if (state.open) return;
      const pt = e.touches ? e.touches[0] : e;
      isDragging = false;
      dragStartX = pt.clientX; dragStartY = pt.clientY;
      const r = fabRect();
      fabStartL = r.left; fabStartT = r.top;
      document.addEventListener('mousemove', onMove);
      document.addEventListener('touchmove', onMove, { passive: false });
      document.addEventListener('mouseup',   onEnd);
      document.addEventListener('touchend',  onEnd);
    }

    function onMove(e) {
      const pt = e.touches ? e.touches[0] : e;
      const dx = pt.clientX - dragStartX, dy = pt.clientY - dragStartY;
      if (!isDragging) {
        if (Math.abs(dx) < 5 && Math.abs(dy) < 5) return;
        isDragging = true;
        fab.classList.add('vgk-dragging');
        fab.style.animation = 'none';
        fab.style.right = ''; fab.style.bottom = '';
        fab.style.left = fabStartL + 'px'; fab.style.top = fabStartT + 'px';
      }
      e.preventDefault();
      const W = window.innerWidth, H = window.innerHeight;
      fab.style.left = Math.max(8, Math.min(W - 68, fabStartL + dx)) + 'px';
      fab.style.top  = Math.max(8, Math.min(H - 68, fabStartT + dy)) + 'px';
    }

    function onEnd() {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('touchmove', onMove);
      document.removeEventListener('mouseup',   onEnd);
      document.removeEventListener('touchend',  onEnd);
      if (isDragging) {
        fab.classList.remove('vgk-dragging');
        _fabDragged = true;
        resetSnapTimer();
      }
      isDragging = false;
    }

    fab.addEventListener('mousedown',  onStart);
    fab.addEventListener('touchstart', onStart, { passive: true });
  }

  // ─── Reposition modal near current FAB location ────────────────────────────
  function positionModalNearFab() {
    const fab   = document.getElementById('vgkFab');
    const modal = document.getElementById('vgkModal');
    if (!_fabDragged || !fab || !modal) return;
    const r  = fab.getBoundingClientRect();
    const W  = window.innerWidth, H = window.innerHeight;
    const mW = Math.min(360, W - 32);
    const mH = 520;
    // Prefer opening above; fall back to below
    let top  = r.top - mH - 12;
    let left = r.left + 30 - mW / 2;
    if (top < 8) top = r.bottom + 12;
    left = Math.max(8, Math.min(W - mW - 8, left));
    top  = Math.max(8, Math.min(H - mH - 8, top));
    modal.style.bottom = ''; modal.style.right = '';
    modal.style.top = top + 'px'; modal.style.left = left + 'px';
    modal.style.width = mW + 'px';
  }

  function resetModalPosition() {
    const modal = document.getElementById('vgkModal');
    if (!modal) return;
    modal.style.top = ''; modal.style.left = '';
    modal.style.bottom = '96px'; modal.style.right = '24px';
    modal.style.width = '';
  }

  // ─── Event Wiring ──────────────────────────────────────────────────────────
  function wireEvents() {
    const fab = document.getElementById('vgkFab');
    // Only fire click if it wasn't a drag gesture
    let _mdTime = 0;
    fab.addEventListener('mousedown',  () => { _mdTime = Date.now(); });
    fab.addEventListener('touchstart', () => { _mdTime = Date.now(); }, { passive: true });
    fab.addEventListener('click', () => {
      if (Date.now() - _mdTime < 200) toggleModal();
    });
    document.getElementById('vgkClose').onclick   = () => toggleModal(false);
    document.getElementById('vgkOverlay').onclick  = () => toggleModal(false);
    document.getElementById('vgkMic').onclick      = startListening;
    if (!hasSpeech) document.getElementById('vgkMic').style.display = 'none';

    const input = document.getElementById('vgkInput');
    input.placeholder = state.portalType === 'marketplace' ? (L('marketplace_placeholder') || L('placeholder')) : L('placeholder');
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendMessage(input.value); });
    document.getElementById('vgkSend').onclick = () => sendMessage(input.value);

    document.querySelectorAll('.vgk-lang-btn').forEach(btn => {
      btn.onclick = () => setLanguage(btn.dataset.lang);
    });
  }

  // ─── Init ──────────────────────────────────────────────────────────────────
  function init() {
    injectCSS();
    buildDOM();
    detectPortalAndToken();
    computeAllowedIntents();
    wireEvents();
    makeFabDraggable();
    console.log(`[VGK] Assistant v${VGK_VERSION} ready | portal: ${state.portalType} | intents: ${state.allowedIntents ? state.allowedIntents.join(',') : 'all'}`);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // ─── Public API ────────────────────────────────────────────────────────────
  window.VGKAssistant = { open: () => toggleModal(true), close: () => toggleModal(false), reset };

})();

// ─── Marketplace Voice Search ───────────────────────────────────────────────
window.VGKMarketplaceVoice = (function () {
  const LANG_SPEECH = { en: 'en-IN', hi: 'hi-IN', te: 'te-IN' };
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;

  function attachToSearchBar(inputEl, lang) {
    if (!SR || !inputEl) return;
    if (inputEl.dataset.vgkVoice) return;
    inputEl.dataset.vgkVoice = '1';

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.title = 'Voice search';
    btn.style.cssText = 'background:none;border:none;cursor:pointer;font-size:18px;padding:0 6px;line-height:1;color:#6c3de8;transition:.15s;';
    btn.innerHTML = '🎤';
    inputEl.insertAdjacentElement('afterend', btn);

    btn.addEventListener('click', () => {
      const rec = new SR();
      rec.lang = LANG_SPEECH[lang || 'en'] || 'en-IN';
      rec.continuous = false; rec.interimResults = false;
      rec.onstart = () => { btn.innerHTML = '🔴'; btn.style.animation = 'vgkPulse 1s infinite'; };
      rec.onresult = (e) => {
        const t = e.results[0][0].transcript;
        inputEl.value = t;
        inputEl.dispatchEvent(new Event('input', { bubbles: true }));
        inputEl.dispatchEvent(new Event('keyup', { bubbles: true }));
      };
      rec.onend = () => { btn.innerHTML = '🎤'; btn.style.animation = ''; };
      rec.onerror = () => { btn.innerHTML = '🎤'; btn.style.animation = ''; };
      rec.start();
    });
  }

  return { attachToSearchBar };
})();

// ─── DC-VOICE-FIELD-001: Global Field Voice — mic on every input/textarea ───
window.VGKFieldVoice = (function () {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return { init: function () {} };

  const SKIP_TYPES = new Set(['password', 'number', 'date', 'time', 'datetime-local',
    'month', 'week', 'range', 'color', 'file', 'checkbox', 'radio', 'submit',
    'reset', 'button', 'image', 'hidden']);

  let _activeRec = null;
  let _activeBtn = null;

  function _stopActive() {
    if (_activeRec) { try { _activeRec.stop(); } catch (_) {} _activeRec = null; }
    if (_activeBtn) { _activeBtn.innerHTML = '🎤'; _activeBtn.style.animation = ''; _activeBtn = null; }
  }

  function _getLang() {
    try {
      const s = localStorage.getItem('vgk_language') || document.documentElement.lang || 'en';
      return { en: 'en-IN', hi: 'hi-IN', te: 'te-IN' }[s] || 'en-IN';
    } catch (_) { return 'en-IN'; }
  }

  function _attachToInput(el) {
    if (!el || el.dataset.vgkVoice) return;
    if (el.readOnly || el.disabled) return;
    if (el.tagName === 'INPUT') {
      const t = (el.type || 'text').toLowerCase();
      if (SKIP_TYPES.has(t)) return;
    }
    el.dataset.vgkVoice = '1';

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.title = 'Voice input';
    btn.className = 'vgk-field-mic-btn';
    btn.style.cssText = [
      'display:inline-flex;align-items:center;justify-content:center;',
      'background:none;border:none;cursor:pointer;',
      'font-size:15px;padding:0 3px;line-height:1;color:#6c3de8;',
      'opacity:0.7;transition:opacity .15s;flex-shrink:0;',
      'vertical-align:middle;',
    ].join('');
    btn.innerHTML = '🎤';
    btn.onmouseenter = () => { btn.style.opacity = '1'; };
    btn.onmouseleave = () => { if (_activeBtn !== btn) btn.style.opacity = '0.7'; };

    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (_activeBtn === btn) { _stopActive(); return; }
      _stopActive();

      const rec = new SR();
      rec.lang = _getLang();
      rec.continuous = false;
      rec.interimResults = false;
      _activeRec = rec;
      _activeBtn = btn;

      rec.onstart = () => {
        btn.innerHTML = '🔴';
        btn.style.animation = 'vgkPulse 1s infinite';
        btn.style.opacity = '1';
      };
      rec.onresult = (ev) => {
        const transcript = ev.results[0][0].transcript;
        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
          const nativeInputSetter = Object.getOwnPropertyDescriptor(
            el.tagName === 'INPUT' ? HTMLInputElement.prototype : HTMLTextAreaElement.prototype,
            'value'
          );
          if (nativeInputSetter && nativeInputSetter.set) {
            nativeInputSetter.set.call(el, transcript);
          } else {
            el.value = transcript;
          }
          el.dispatchEvent(new Event('input',  { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
          el.dispatchEvent(new Event('keyup',  { bubbles: true }));
        } else if (el.contentEditable === 'true') {
          el.focus();
          const sel = window.getSelection();
          if (sel && sel.rangeCount > 0) {
            const range = sel.getRangeAt(0);
            range.deleteContents();
            range.insertNode(document.createTextNode(transcript));
            range.collapse(false);
          } else {
            el.textContent += transcript;
          }
          el.dispatchEvent(new Event('input', { bubbles: true }));
        }
      };
      rec.onend = () => {
        btn.innerHTML = '🎤';
        btn.style.animation = '';
        btn.style.opacity = '0.7';
        if (_activeRec === rec) { _activeRec = null; _activeBtn = null; }
      };
      rec.onerror = () => {
        btn.innerHTML = '🎤';
        btn.style.animation = '';
        btn.style.opacity = '0.7';
        if (_activeRec === rec) { _activeRec = null; _activeBtn = null; }
      };
      try { rec.start(); } catch (_) { _activeRec = null; _activeBtn = null; }
    });

    const parent = el.parentElement;
    if (!parent) return;

    const compStyle = window.getComputedStyle(parent);
    if (!['relative', 'absolute', 'fixed', 'sticky'].includes(compStyle.position)) {
      parent.style.position = 'relative';
    }

    if (el.tagName === 'TEXTAREA' || (el.contentEditable === 'true')) {
      btn.style.cssText += 'position:absolute;bottom:6px;right:6px;z-index:10;background:rgba(255,255,255,0.85);border-radius:50%;width:24px;height:24px;';
      parent.appendChild(btn);
    } else {
      el.insertAdjacentElement('afterend', btn);
    }
  }

  function _attachToQuill(el) {
    if (!el || el.dataset.vgkVoice) return;
    _attachToInput(el);
  }

  function _scanPage() {
    document.querySelectorAll(
      'input:not([data-vgk-voice]), textarea:not([data-vgk-voice])'
    ).forEach(_attachToInput);
    document.querySelectorAll(
      '.ql-editor:not([data-vgk-voice])'
    ).forEach(_attachToQuill);
  }

  function init() {
    _scanPage();

    const observer = new MutationObserver((mutations) => {
      let needsScan = false;
      for (const m of mutations) {
        if (!m.addedNodes.length) continue;
        for (const node of m.addedNodes) {
          if (node.nodeType !== 1) continue;
          if (node.matches && (
            node.matches('input, textarea, .ql-editor') ||
            node.querySelector('input, textarea, .ql-editor')
          )) {
            needsScan = true;
            break;
          }
        }
        if (needsScan) break;
      }
      if (needsScan) _scanPage();
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  return { init, scan: _scanPage };
})();
