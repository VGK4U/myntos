// DC_PARTNER_AUTH_001 — Partner Login Page Script
// All JavaScript for partner_login.html — external file, zero inline scripts
// Loads at end of <body>: all DOM elements guaranteed to exist on execution.

(function () {
    'use strict';

    /* ─────────────────────────────────────────────
       ELEMENT REFERENCES
    ───────────────────────────────────────────── */
    var form            = document.getElementById('loginForm');
    var codeInput       = document.getElementById('partnerCode');
    var passInput       = document.getElementById('password');
    var loginBtn        = document.getElementById('loginBtn');
    var togglePwdBtn    = document.getElementById('togglePassword');
    var togglePwdIcon   = document.getElementById('togglePasswordIcon');
    var alertBox        = document.getElementById('alertContainer');
    var forgotBtn       = document.getElementById('forgotPasswordBtn');
    var homeBtn         = document.getElementById('homeBtn');

    /* ─────────────────────────────────────────────
       HELPERS
    ───────────────────────────────────────────── */
    function showAlert(msg, type) {
        alertBox.innerHTML = '<div class="alert alert-' + type + '">' + msg + '</div>';
    }
    function clearAlert() { alertBox.innerHTML = ''; }

    function setLoading(on) {
        loginBtn.disabled = on;
        var t = loginBtn.querySelector('.btn-text');
        var s = loginBtn.querySelector('.spinner-border');
        if (t) t.textContent = on ? 'Signing in...' : 'Sign In';
        if (s) s.classList.toggle('d-none', !on);
    }

    function validateField(field) {
        var val = field.id === 'password' ? field.value : field.value.trim();
        var ok  = field.id === 'partnerCode' ? (val.length >= 3 && val.length <= 30)
                                              : val.length >= 1;
        field.classList.toggle('is-valid',   ok);
        field.classList.toggle('is-invalid', !ok);
        return ok;
    }

    /* ─────────────────────────────────────────────
       PASSWORD TOGGLE
    ───────────────────────────────────────────── */
    if (togglePwdBtn) {
        togglePwdBtn.addEventListener('click', function () {
            passInput.type = passInput.type === 'password' ? 'text' : 'password';
            if (togglePwdIcon) {
                togglePwdIcon.classList.toggle('fa-eye');
                togglePwdIcon.classList.toggle('fa-eye-slash');
            }
        });
    }

    /* ─────────────────────────────────────────────
       HOME BUTTON HOVER
    ───────────────────────────────────────────── */
    if (homeBtn) {
        homeBtn.addEventListener('mouseover', function () { this.style.background = 'rgba(0,0,0,0.42)'; });
        homeBtn.addEventListener('mouseout',  function () { this.style.background = 'rgba(0,0,0,0.28)'; });
    }

    /* ─────────────────────────────────────────────
       REAL-TIME VALIDATION
    ───────────────────────────────────────────── */
    if (codeInput) codeInput.addEventListener('input', function () { validateField(this); });
    if (passInput) passInput.addEventListener('input', function () { validateField(this); });

    /* ─────────────────────────────────────────────
       LOGIN FORM SUBMIT
    ───────────────────────────────────────────── */
    if (form) {
        form.addEventListener('submit', async function (e) {
            e.preventDefault();
            e.stopPropagation();

            var code = codeInput.value.trim().toUpperCase();
            var pass = passInput.value;

            var codeOk = validateField(codeInput);
            var passOk = validateField(passInput);
            if (!codeOk || !passOk) {
                showAlert('<i class="fas fa-exclamation-circle me-2"></i>Please fill in Partner Code and Password.', 'warning');
                return;
            }

            setLoading(true);
            clearAlert();

            try {
                var resp = await fetch('/api/v1/partner/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ partner_code: code, password: pass })
                });
                var data = await resp.json();

                if (data.success) {
                    localStorage.setItem('partner_token', data.access_token);
                    localStorage.setItem('partner_info', JSON.stringify(data.partner || {}));
                    document.cookie = 'partner_token=' + encodeURIComponent(data.access_token)
                                    + '; path=/; max-age=604800; SameSite=Lax';
                    showAlert('<i class="fas fa-check-circle me-2"></i>Login successful! Redirecting…', 'success');
                    var dest = (data.partner && data.partner.category === 'VENDOR')
                                ? '/partner/solar-vendor'
                                : '/partner/dashboard';
                    setTimeout(function () { window.location.href = dest; }, 900);
                } else {
                    showAlert('<i class="fas fa-exclamation-triangle me-2"></i>'
                              + (data.message || data.detail || 'Invalid credentials. Please try again.'), 'danger');
                    setLoading(false);
                }
            } catch (err) {
                showAlert('<i class="fas fa-exclamation-triangle me-2"></i>Connection error. Please try again.', 'danger');
                setLoading(false);
            }
        });
    }

    /* ─────────────────────────────────────────────
       AUTO-REDIRECT (already logged in)
    ───────────────────────────────────────────── */
    var existingToken = localStorage.getItem('partner_token');
    var hasCt = new URLSearchParams(window.location.search).get('ct');

    if (existingToken && !hasCt) {
        fetch('/api/v1/partner/auth/me', {
            headers: { 'Authorization': 'Bearer ' + existingToken }
        }).then(function (r) {
            if (r.ok) {
                document.cookie = 'partner_token=' + encodeURIComponent(existingToken)
                                + '; path=/; max-age=604800; SameSite=Lax';
                showAlert('<i class="fas fa-check-circle me-2"></i>Already logged in — redirecting…', 'success');
                if (loginBtn) loginBtn.disabled = true;
                setTimeout(function () { window.location.href = '/partner/dashboard'; }, 800);
            } else {
                localStorage.removeItem('partner_token');
                localStorage.removeItem('partner_info');
                document.cookie = 'partner_token=; path=/; max-age=0; SameSite=Lax';
            }
        }).catch(function () {
            localStorage.removeItem('partner_token');
            localStorage.removeItem('partner_info');
            document.cookie = 'partner_token=; path=/; max-age=0; SameSite=Lax';
        });
    }

    /* ─────────────────────────────────────────────
       CROSS-AUTH: ?ct= token (portal switch)
    ───────────────────────────────────────────── */
    if (hasCt) {
        document.body.style.opacity = '0.5';
        window.history.replaceState({}, '', '/partner/login');
        fetch('/api/v1/promo/cross-auth/redeem-to-partner', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cross_token: hasCt })
        }).then(async function (resp) {
            var data = await resp.json();
            if (resp.ok && data.success) {
                localStorage.setItem('partner_token', data.access_token);
                localStorage.setItem('partner_info', JSON.stringify(data.partner || {}));
                document.cookie = 'partner_token=' + encodeURIComponent(data.access_token)
                                + '; path=/; max-age=604800; SameSite=Lax';
                window.location.href = (data.partner && data.partner.category === 'VENDOR')
                                       ? '/partner/solar-vendor' : '/partner/dashboard';
            } else {
                document.body.style.opacity = '1';
                showAlert('<i class="fas fa-exclamation-triangle me-2"></i>'
                          + (data.detail || 'Switch link expired. Please log in manually.'), 'warning');
            }
        }).catch(function () {
            document.body.style.opacity = '1';
        });
    }

    /* ─────────────────────────────────────────────
       AUTO-FOCUS
    ───────────────────────────────────────────── */
    if (codeInput) codeInput.focus();

    /* ─────────────────────────────────────────────
       FORGOT PASSWORD — OTP RESET (DC-OTP-RESET-001)
    ───────────────────────────────────────────── */
    var prForgotOpen = false;

    function prMsg(txt, color) {
        var el = document.getElementById('prForgotMsg');
        if (el) { el.style.color = color || '#0369a1'; el.textContent = txt; }
    }

    function prToggleForgot() {
        prForgotOpen = !prForgotOpen;
        var panel = document.getElementById('prForgotPanel');
        if (panel) panel.style.display = prForgotOpen ? 'block' : 'none';
    }

    async function prSendOTP(resend) {
        var uid = (document.getElementById('prUserId') || {}).value;
        if (!uid) { prMsg('Please enter your Partner Code', '#dc2626'); return; }
        uid = uid.trim().toUpperCase();
        if (!uid) { prMsg('Please enter your Partner Code', '#dc2626'); return; }
        prMsg('Sending OTP…', '#0369a1');
        try {
            var r = await fetch('/api/v1/password-reset/portal/dealer_partner/forgot-password', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: uid })
            });
            var d = await r.json();
            if (d.success || r.ok) {
                document.getElementById('prStep1').style.display = 'none';
                document.getElementById('prStep2').style.display = 'block';
                prMsg('OTP sent! Check your WhatsApp.', '#059669');
            } else {
                prMsg(d.detail || 'Could not send OTP', '#dc2626');
            }
        } catch (e) { prMsg('Network error. Please try again.', '#dc2626'); }
    }

    async function prVerifyOTP() {
        var uid = (document.getElementById('prUserId') || {}).value;
        var otp = (document.getElementById('prOtp') || {}).value;
        if (!uid || !otp) return;
        uid = uid.trim().toUpperCase();
        otp = otp.trim();
        if (otp.length !== 6) { prMsg('Enter the 6-digit OTP', '#dc2626'); return; }
        prMsg('Verifying…', '#0369a1');
        try {
            var r = await fetch('/api/v1/password-reset/portal/dealer_partner/verify-otp', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: uid, otp_code: otp })
            });
            var d = await r.json();
            if (d.success) {
                document.getElementById('prStep2').style.display = 'none';
                document.getElementById('prStep3').style.display = 'block';
                prMsg('OTP verified! Set your new password.', '#059669');
            } else {
                prMsg(d.detail || 'Invalid OTP', '#dc2626');
            }
        } catch (e) { prMsg('Network error.', '#dc2626'); }
    }

    async function prResetPwd() {
        var uid = (document.getElementById('prUserId') || {}).value;
        var otp = (document.getElementById('prOtp') || {}).value;
        var np  = (document.getElementById('prNewPwd') || {}).value;
        var cp  = (document.getElementById('prConfPwd') || {}).value;
        if (!uid || !otp) return;
        if (np.length < 6) { prMsg('Password must be at least 6 characters', '#dc2626'); return; }
        if (np !== cp)     { prMsg('Passwords do not match', '#dc2626'); return; }
        prMsg('Resetting password…', '#0369a1');
        try {
            var r = await fetch('/api/v1/password-reset/portal/dealer_partner/reset-password', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: uid.trim().toUpperCase(), otp_code: otp.trim(), new_password: np })
            });
            var d = await r.json();
            if (d.success) {
                prMsg('\u2705 ' + d.message, '#059669');
                setTimeout(function () {
                    var panel = document.getElementById('prForgotPanel');
                    if (panel) panel.style.display = 'none';
                    prForgotOpen = false;
                }, 3000);
            } else {
                prMsg(d.detail || 'Reset failed', '#dc2626');
            }
        } catch (e) { prMsg('Network error.', '#dc2626'); }
    }

    // Wire forgot-password buttons via addEventListener (no inline onclick in HTML)
    if (forgotBtn) forgotBtn.addEventListener('click', prToggleForgot);

    var prSendBtn   = document.getElementById('prSendOTPBtn');
    var prVerifyBtn = document.getElementById('prVerifyOTPBtn');
    var prResendBtn = document.getElementById('prResendBtn');
    var prResetBtn  = document.getElementById('prResetPwdBtn');

    if (prSendBtn)   prSendBtn.addEventListener('click',   function () { prSendOTP(false); });
    if (prVerifyBtn) prVerifyBtn.addEventListener('click', prVerifyOTP);
    if (prResendBtn) prResendBtn.addEventListener('click', function () { prSendOTP(true); });
    if (prResetBtn)  prResetBtn.addEventListener('click',  prResetPwd);

    /* ─────────────────────────────────────────────
       ANNOUNCEMENTS
    ───────────────────────────────────────────── */
    var annData    = [];
    var annIdx     = 0;
    var annTimer   = null;
    var annPaused  = false;

    function escH(s) { var d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }
    function relD(iso) {
        if (!iso) return '';
        return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
    }

    function annRender(idx) {
        var ann = annData[idx];
        if (!ann) return;
        annIdx = idx;

        var mediaHTML = '';
        if (ann.media && ann.media.length > 0) {
            var m = ann.media[0];
            if (m.file_type && m.file_type.startsWith('image/')) {
                mediaHTML = '<div style="position:relative;cursor:zoom-in" data-ann-lightbox="' + ann.id + '">'
                          + '<img src="' + escH(m.file_path) + '" style="width:100%;max-height:140px;object-fit:cover;border-radius:8px;margin-bottom:8px;" onerror="this.style.display=\'none\'">'
                          + '</div>';
            } else if (m.file_type && m.file_type.startsWith('video/')) {
                mediaHTML = '<div style="position:relative">'
                          + '<video controls playsinline muted preload="metadata" style="width:100%;max-height:140px;border-radius:8px;background:#000;margin-bottom:8px;">'
                          + '<source src="' + escH(m.file_path) + '" type="' + (m.file_type || 'video/mp4') + '"></video>'
                          + '<button data-ann-lightbox="' + ann.id + '" style="position:absolute;top:6px;left:6px;background:rgba(0,0,0,.7);color:#fff;border:none;padding:4px 8px;border-radius:6px;font-size:10px;cursor:pointer;z-index:5;display:flex;align-items:center;gap:3px">'
                          + '<i class="fas fa-expand"></i> Expand</button></div>';
            }
        }

        var rKey    = 'partner_ann_react_' + ann.id;
        var cKey    = 'partner_ann_react_counts_' + ann.id;
        var myReact = localStorage.getItem(rKey) || '';
        var cnts    = JSON.parse(localStorage.getItem(cKey) || '{"like":0,"love":0,"celebrate":0}');

        function rBtn(emoji, type, label) {
            var active = myReact === type, cnt = cnts[type] || 0;
            return '<button data-react-ann="' + ann.id + '" data-react-type="' + type + '" title="' + label + '" '
                 + 'style="display:inline-flex;align-items:center;gap:3px;padding:4px 8px;border-radius:20px;'
                 + 'border:1px solid ' + (active ? 'rgba(168,85,247,.8)' : 'rgba(255,255,255,.2)') + ';'
                 + 'background:' + (active ? 'rgba(168,85,247,.3)' : 'rgba(255,255,255,.08)') + ';cursor:pointer;font-size:12px;color:#fff;">'
                 + emoji + (cnt > 0 ? '<span style="font-size:10px;opacity:.8">' + cnt + '</span>' : '') + '</button>';
        }

        var viewUrl      = '/public/announcement?id=' + encodeURIComponent(ann.id);
        var sharePopupId = 'pSharePopup_' + ann.id;
        var catName      = ann.category && ann.category.name ? escH(ann.category.name) : '';
        var shortDesc    = escH((ann.description || '').length > 100
                                ? (ann.description || '').substring(0, 100) + '\u2026'
                                : (ann.description || ''));

        var reactHTML = '<div style="display:flex;align-items:center;gap:5px;margin-top:8px;flex-wrap:wrap;">'
                      + rBtn('\ud83d\udc4d', 'like', 'Like')
                      + rBtn('\u2764\ufe0f', 'love', 'Love')
                      + rBtn('\ud83c\udf89', 'celebrate', 'Celebrate')
                      + '<div style="flex:1"></div>'
                      + '<a href="' + viewUrl + '" target="_blank" style="display:inline-flex;align-items:center;gap:4px;padding:4px 9px;border-radius:20px;border:1px solid rgba(168,85,247,.35);background:rgba(168,85,247,.1);color:#d8b4fe;font-size:11.5px;font-weight:600;text-decoration:none;flex-shrink:0"><i class="fas fa-eye"></i> View</a>'
                      + '<div style="position:relative;display:inline-block;flex-shrink:0">'
                      + '<button data-share-ann="' + ann.id + '" style="display:inline-flex;align-items:center;gap:4px;padding:4px 9px;border-radius:20px;border:1px solid rgba(168,85,247,.5);background:rgba(168,85,247,.25);cursor:pointer;color:#d8b4fe;font-size:11.5px;font-weight:600;"><i class="fas fa-share-alt"></i> Share</button>'
                      + '<div id="' + sharePopupId + '" style="display:none;position:absolute;bottom:calc(100% + 6px);right:0;background:#1a0533;border:1px solid rgba(168,85,247,.5);border-radius:10px;padding:8px;width:185px;z-index:99;box-shadow:0 8px 24px rgba(0,0,0,.5)">'
                      + '<div style="font-size:10px;font-weight:700;color:rgba(255,255,255,.45);text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;padding:0 4px">Share via</div>'
                      + '<a href="' + window.location.origin + '/public/announcement?id=' + encodeURIComponent(ann.id) + '&shared=true" target="_blank" rel="noopener" style="display:flex;align-items:center;gap:7px;padding:5px 7px;border-radius:7px;color:#a5b4fc;font-size:11.5px;font-weight:600;text-decoration:none;background:rgba(99,102,241,.1);margin-bottom:4px"><i class="fas fa-external-link-alt"></i> View Full Page</a>'
                      + '<a href="https://wa.me/?text=' + encodeURIComponent((ann.title || 'Announcement') + '\n\n' + (ann.description || '').slice(0, 120) + '\n\n' + window.location.origin + '/public/announcement?id=' + ann.id + '&shared=true') + '" target="_blank" rel="noopener" style="display:flex;align-items:center;gap:7px;padding:5px 7px;border-radius:7px;color:#4ade80;font-size:11.5px;font-weight:600;text-decoration:none;background:rgba(74,222,128,.08);margin-bottom:4px"><i class="fab fa-whatsapp" style="font-size:14px"></i> WhatsApp</a>'
                      + '<button data-copy-ann="' + ann.id + '" style="display:flex;align-items:center;gap:7px;padding:5px 7px;border-radius:7px;color:#d8b4fe;font-size:11.5px;font-weight:600;background:rgba(168,85,247,.1);border:none;cursor:pointer;width:100%;text-align:left"><i class="fas fa-copy" style="font-size:12px"></i> Copy Link + Text</button>'
                      + '</div></div></div>';

        var contentEl = document.getElementById('partnerAnnContent');
        if (contentEl) {
            contentEl.innerHTML = '<div style="background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.12);border-radius:10px;padding:12px;">'
                + mediaHTML
                + (catName ? '<span style="display:inline-block;font-size:10px;font-weight:700;background:rgba(168,85,247,0.3);color:#d8b4fe;padding:2px 8px;border-radius:12px;margin-bottom:5px;">' + catName + '</span>' : '')
                + '<div style="font-size:13px;font-weight:700;color:#fff;margin-bottom:3px;">' + escH(ann.title || 'Announcement') + '</div>'
                + (shortDesc ? '<div style="font-size:12px;color:rgba(255,255,255,0.7);line-height:1.4;">' + shortDesc + '</div>' : '')
                + '<div style="font-size:11px;color:rgba(255,255,255,0.45);margin-top:5px;"><i class="fas fa-calendar-alt" style="margin-right:4px;"></i>' + relD(ann.approved_at || ann.created_at) + '</div>'
                + reactHTML + '</div>';
        }

        var dotsEl = document.getElementById('partnerAnnDots');
        if (dotsEl) {
            dotsEl.innerHTML = annData.map(function (_, i) {
                return '<div data-ann-goto="' + (i - annIdx) + '" style="width:' + (i === idx ? '18px' : '7px') + ';height:7px;border-radius:4px;background:' + (i === idx ? '#a855f7' : 'rgba(255,255,255,0.3)') + ';cursor:pointer;transition:all 0.3s;"></div>';
            }).join('');
        }
    }

    function annNav(dir) {
        if (!annData.length) return;
        annIdx = (annIdx + dir + annData.length) % annData.length;
        annRender(annIdx);
        clearInterval(annTimer);
        annStartTimer();
    }

    function annStartTimer() {
        if (annData.length > 1) {
            annTimer = setInterval(function () {
                if (!annPaused) {
                    annIdx = (annIdx + 1) % annData.length;
                    annRender(annIdx);
                }
            }, 6000);
        }
    }

    // Announcements button wiring (prev / play-pause / next)
    var annPrev = document.getElementById('annPrevBtn');
    var annPlay = document.getElementById('annPlayPauseBtn');
    var annNext = document.getElementById('annNextBtn');
    if (annPrev) annPrev.addEventListener('click', function () { annNav(-1); });
    if (annNext) annNext.addEventListener('click', function () { annNav(1); });
    if (annPlay) {
        annPlay.addEventListener('click', function () {
            annPaused = !annPaused;
            var ic = document.getElementById('partnerAnnPlayPauseIcon');
            if (ic) ic.className = annPaused ? 'fas fa-play' : 'fas fa-pause';
        });
    }

    // Event delegation for dynamically-injected announcement buttons
    document.addEventListener('click', function (e) {
        var t = e.target;

        // Lightbox
        var lb = t.closest ? t.closest('[data-ann-lightbox]') : null;
        if (lb) {
            e.preventDefault();
            var ann = annData.find(function (a) { return String(a.id) === lb.dataset.annLightbox; });
            if (ann && ann.media && ann.media.length > 0 && typeof MNRLightbox !== 'undefined') {
                var items = ann.media.map(function (m) {
                    return { url: m.file_path, file_type: m.file_type,
                             type: (m.media_type === 'video' || (m.file_type && m.file_type.startsWith('video/'))) ? 'video' : 'image',
                             title: ann.title || 'Media' };
                });
                MNRLightbox.open(items, 0);
            }
            return;
        }

        // Reaction
        var rb = t.closest ? t.closest('[data-react-ann]') : null;
        if (rb) {
            var annId = rb.dataset.reactAnn;
            var type  = rb.dataset.reactType;
            var rKey  = 'partner_ann_react_' + annId;
            var cKey  = 'partner_ann_react_counts_' + annId;
            var prev  = localStorage.getItem(rKey) || '';
            var cnts  = JSON.parse(localStorage.getItem(cKey) || '{"like":0,"love":0,"celebrate":0}');
            if (prev === type) { localStorage.removeItem(rKey); cnts[type] = Math.max(0, (cnts[type] || 0) - 1); }
            else { if (prev) cnts[prev] = Math.max(0, (cnts[prev] || 0) - 1); localStorage.setItem(rKey, type); cnts[type] = (cnts[type] || 0) + 1; }
            localStorage.setItem(cKey, JSON.stringify(cnts));
            annRender(annIdx);
            return;
        }

        // Share popup
        var sb = t.closest ? t.closest('[data-share-ann]') : null;
        if (sb) {
            var popup = document.getElementById('pSharePopup_' + sb.dataset.shareAnn);
            if (!popup) return;
            var isOpen = popup.style.display !== 'none';
            document.querySelectorAll('[id^="pSharePopup_"]').forEach(function (p) { p.style.display = 'none'; });
            if (!isOpen) {
                popup.style.display = 'block';
                setTimeout(function () {
                    document.addEventListener('click', function h(ev) {
                        if (!popup.contains(ev.target)) { popup.style.display = 'none'; document.removeEventListener('click', h); }
                    });
                }, 10);
            }
            return;
        }

        // Copy announcement
        var cb = t.closest ? t.closest('[data-copy-ann]') : null;
        if (cb) {
            var ann2 = annData.find(function (a) { return String(a.id) === cb.dataset.copyAnn; });
            if (!ann2) return;
            var link = window.location.origin + '/public/announcement?id=' + ann2.id + '&shared=true';
            var text = (ann2.title ? ann2.title + '\n\n' : '') + (ann2.description || '').slice(0, 200) + '\n\n' + link + '\n\nVia VGK4U Partner';
            var pop  = document.getElementById('pSharePopup_' + ann2.id);
            navigator.clipboard.writeText(text).then(function () {
                if (pop) { pop.innerHTML = '<div style="text-align:center;padding:8px;color:#4ade80;font-size:12px;font-weight:700"><i class="fas fa-check-circle" style="margin-right:4px"></i>Copied!</div>'; setTimeout(function () { pop.style.display = 'none'; }, 1200); }
            }).catch(function () { alert('Could not copy.'); });
            return;
        }

        // Dot navigation
        var dot = t.closest ? t.closest('[data-ann-goto]') : null;
        if (dot) { annNav(parseInt(dot.dataset.annGoto, 10) || 0); }
    });

    // Load announcements from API
    async function loadAnnouncements() {
        try {
            var resp  = await fetch('/api/v1/feedback/public/announcements?limit=10&platform=mnr');
            var data  = await resp.json();
            var items = Array.isArray(data) ? data : (data.data || []);
            var loadEl = document.getElementById('partnerAnnLoading');
            if (loadEl) loadEl.style.display = 'none';
            if (items.length > 0) {
                annData = items;
                var sec = document.getElementById('partnerAnnouncementSection');
                var cnt = document.getElementById('partnerAnnContent');
                var ctl = document.getElementById('partnerAnnControls');
                if (sec) sec.style.display = 'block';
                if (cnt) cnt.style.display = 'block';
                if (ctl) ctl.style.display = 'flex';
                annRender(0);
                if (items.length > 1) annStartTimer();
            }
        } catch (e) {
            var loadEl2 = document.getElementById('partnerAnnLoading');
            if (loadEl2) loadEl2.innerHTML = '<span style="color:rgba(255,255,255,0.5);font-size:12px;">Unable to load announcements</span>';
        }
    }

    loadAnnouncements();

})();
