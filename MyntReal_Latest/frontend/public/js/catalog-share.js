/**
 * DC Protocol (Feb 26, 2026): Catalog Share Modal
 * Extracted to external file — no template-literal escaping issues.
 * Used on both /user-home and /mnrcatalog pages.
 */
window.openCatalogShareModal = async function() {
    var existing = document.getElementById('_catalogShareOverlay');
    if (existing) existing.remove();

    var sessionToken = window.sessionToken || '';
    var userInfo = { id: '', name: '' };
    var bonanzas = [];

    try {
        var meRes = await fetch('/api/v1/auth/me', { headers: { 'Authorization': 'Bearer ' + sessionToken } });
        var meData = await meRes.json();
        var u = meData.data || meData.employee || meData;
        userInfo.id   = u.unique_id || u.mnr_id || '';
        userInfo.name = u.full_name || u.name   || '';
    } catch(e) { console.warn('[DC Catalog] Could not fetch user info', e); }

    try {
        var bRes = await fetch('/api/v1/catalog/public/bonanzas');
        var bData = await bRes.json();
        if (bData.success) bonanzas = bData.bonanzas || [];
    } catch(e) {}

    var lang = 'english';
    var prefixes = ['Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Mx.'];

    function buildMessage(prefix, recipientName, language, catalogUrl, senderName, senderId) {
        var r = (prefix ? prefix + ' ' : '') + (recipientName || '');
        var greeting = r ? ('Hello ' + r + '!') : 'Hello!';
        var sig = '';
        if (senderName || senderId) {
            sig = '\n\n--\nRegards,\n' + (senderName || '') + (senderId ? ' (' + senderId + ')' : '');
        }

        var refSuffix = senderId ? ('&ref=' + encodeURIComponent(senderId)) : '';

        if (language === 'telugu') {
            var te_greeting = r ? ('నమస్కారం ' + r + '!') : 'నమస్కారం!';
            return te_greeting +
                '\n\nమీతో MNR బిజినెస్ యాక్సెస్ ప్రోగ్రామ్ కేటలాగ్‌ను షేర్ చేయాలని ఆశపడుతున్నాను.' +
                '\n\nఇది ఒక క్రమబద్ధమైన బిజినెస్ యాక్సెస్ ప్రోగ్రామ్ — చైన్ స్కీమ్ కాదు.' +
                '\n\n📖 కేటలాగ్ చూడండి:\n' + catalogUrl +
                '\n\n🔗 చేరుకోవడానికి ఇక్కడ నమోదు చేసుకోండి:\n' + catalogUrl.replace(/\/mnrcatalog.*$/, '/create-member?signup=true') + refSuffix +
                sig;
        }

        return greeting +
            "\n\nI'd like to share the MNR Business Access Program Catalog with you." +
            "\n\nThis is a structured Business Access Program — not a chain scheme or money circulation." +
            "\n\n📖 View the Catalog here:\n" + catalogUrl +
            "\n\n🔗 Register to join us:\n" + catalogUrl.replace(/\/mnrcatalog.*$/, '/create-member?signup=true') + refSuffix +
            sig;
    }

    function bonanzaHTML() {
        if (!bonanzas.length) return '';
        var h = '<div style="margin-top:12px;padding:10px 12px;background:#fff8e1;border-left:3px solid #FFA500;border-radius:6px;">';
        h += '<div style="font-size:12px;font-weight:700;color:#e67e22;margin-bottom:6px;">\uD83C\uDF81 Active Bonanzas (Mention these!)</div>';
        bonanzas.forEach(function(b) {
            h += '<div style="font-size:12px;color:#555;margin-bottom:3px;">\u2022 <strong>' + b.name + '</strong> \u2014 ends ' + b.end_date + '</div>';
        });
        h += '</div>';
        return h;
    }

    var overlay = document.createElement('div');
    overlay.id = '_catalogShareOverlay';
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.65);z-index:99999;display:flex;align-items:center;justify-content:center;padding:16px;box-sizing:border-box;';

    var modal = document.createElement('div');
    modal.style.cssText = 'background:#fff;border-radius:14px;width:100%;max-width:420px;max-height:90vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,0.3);';

    var headerDiv = '<div style="background:linear-gradient(135deg,#FFA500,#e67e22);padding:16px 20px;border-radius:14px 14px 0 0;">';
    headerDiv += '<div style="display:flex;justify-content:space-between;align-items:center;">';
    headerDiv += '<div>';
    headerDiv += '<div style="font-size:16px;font-weight:700;color:#fff;">\uD83D\uDCD6 Share MNR Catalog</div>';
    headerDiv += '<div style="font-size:12px;color:rgba(255,255,255,0.85);margin-top:2px;">MNR Business Access Program</div>';
    headerDiv += '</div>';
    headerDiv += '<button id="_catCloseBtn" style="background:rgba(255,255,255,0.2);border:none;color:#fff;width:28px;height:28px;border-radius:50%;cursor:pointer;font-size:16px;line-height:1;">\u2715</button>';
    headerDiv += '</div></div>';

    var bodyDiv = '<div style="padding:18px 20px;">';
    bodyDiv += '<div style="font-size:11px;color:#888;margin-bottom:12px;padding:8px 10px;background:#f8f9fa;border-radius:6px;">';
    bodyDiv += '\uD83D\uDD12 Not a chain scheme or money circulation \u2014 a structured Business Access Program';
    bodyDiv += '</div>';

    if (userInfo.name || userInfo.id) {
        bodyDiv += '<div style="font-size:12px;color:#555;margin-bottom:12px;padding:6px 10px;background:#e8f5e9;border-radius:6px;border-left:3px solid #4CAF50;">';
        bodyDiv += '\uD83D\uDC64 Sharing as: <strong>' + (userInfo.name || '') + '</strong>';
        if (userInfo.id) bodyDiv += ' <span style="color:#888;">(' + userInfo.id + ')</span>';
        bodyDiv += '</div>';
    }

    bodyDiv += '<div style="margin-bottom:12px;">';
    bodyDiv += '<label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:4px;">Recipient (optional)</label>';
    bodyDiv += '<div style="display:flex;gap:6px;">';
    bodyDiv += '<select id="_catPrefix" style="padding:8px;border:1px solid #ddd;border-radius:6px;font-size:13px;width:90px;">';
    bodyDiv += '<option value="">Prefix</option>';
    prefixes.forEach(function(p) { bodyDiv += '<option value="' + p + '">' + p + '</option>'; });
    bodyDiv += '</select>';
    bodyDiv += '<input id="_catRecipientName" type="text" placeholder="Recipient name (optional)" style="flex:1;padding:8px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;" />';
    bodyDiv += '</div></div>';

    bodyDiv += '<div style="margin-bottom:12px;">';
    bodyDiv += '<label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:4px;">Language</label>';
    bodyDiv += '<div style="display:flex;gap:8px;">';
    bodyDiv += '<button id="_catLangEN" onclick="window._catSetLang(&apos;english&apos;)" style="flex:1;padding:7px;border:2px solid #FFA500;background:#FFA500;color:#fff;border-radius:6px;font-size:13px;cursor:pointer;font-weight:600;">English</button>';
    bodyDiv += '<button id="_catLangTE" onclick="window._catSetLang(&apos;telugu&apos;)" style="flex:1;padding:7px;border:2px solid #ddd;background:#fff;color:#555;border-radius:6px;font-size:13px;cursor:pointer;">Telugu</button>';
    bodyDiv += '</div></div>';

    bodyDiv += '<div style="margin-bottom:14px;">';
    bodyDiv += '<label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:4px;">Message Preview</label>';
    bodyDiv += '<textarea id="_catMsgPreview" rows="6" style="width:100%;padding:8px 10px;border:1px solid #ddd;border-radius:6px;font-size:12px;resize:vertical;box-sizing:border-box;color:#333;background:#f8f9fa;line-height:1.5;"></textarea>';
    bodyDiv += '</div>';

    bodyDiv += bonanzaHTML();

    bodyDiv += '<div style="margin-bottom:14px;">';
    bodyDiv += '<label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:8px;">Share via</label>';
    bodyDiv += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">';
    bodyDiv += '<button onclick="window._catShare(&apos;whatsapp&apos;)" style="display:flex;align-items:center;gap:8px;padding:10px 12px;background:#25D366;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;"><i class="fab fa-whatsapp"></i> WhatsApp</button>';
    bodyDiv += '<button onclick="window._catShare(&apos;telegram&apos;)" style="display:flex;align-items:center;gap:8px;padding:10px 12px;background:#0088cc;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;"><i class="fab fa-telegram"></i> Telegram</button>';
    bodyDiv += '<button onclick="window._catShare(&apos;sms&apos;)" style="display:flex;align-items:center;gap:8px;padding:10px 12px;background:#5c6bc0;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;"><i class="fas fa-sms"></i> SMS</button>';
    bodyDiv += '<button onclick="window._catShare(&apos;email&apos;)" style="display:flex;align-items:center;gap:8px;padding:10px 12px;background:#e53935;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;"><i class="fas fa-envelope"></i> Email</button>';
    bodyDiv += '</div>';
    bodyDiv += '<div style="display:flex;gap:8px;margin-top:8px;">';
    bodyDiv += '<button onclick="window._catShare(&apos;copy&apos;)" id="_catCopyBtn" style="display:flex;align-items:center;gap:8px;padding:10px 12px;background:#546e7a;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;flex:1;"><i class="fas fa-copy"></i> Copy Link</button>';
    if (navigator.share) {
        bodyDiv += '<button onclick="window._catShare(&apos;native&apos;)" style="display:flex;align-items:center;gap:8px;padding:10px 12px;background:#37474f;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;flex:1;"><i class="fas fa-share"></i> More...</button>';
    }
    bodyDiv += '</div>';
    bodyDiv += '</div>';
    bodyDiv += '</div>';

    modal.innerHTML = headerDiv + bodyDiv;
    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
    var closeBtn = document.getElementById('_catCloseBtn');
    if (closeBtn) closeBtn.addEventListener('click', function() { overlay.remove(); });

    window._catGetCatalogUrl = function(refCode) {
        return window.location.origin + '/mnrcatalog' + (refCode ? '?ref=' + refCode : '');
    };

    window._catUpdatePreview = function() {
        var prefix = (document.getElementById('_catPrefix') || {}).value || '';
        var name   = (document.getElementById('_catRecipientName') || {}).value || '';
        var prev   = document.getElementById('_catMsgPreview');
        if (prev) prev.value = buildMessage(prefix, name, lang, window._catGetCatalogUrl(''), userInfo.name, userInfo.id);
    };

    window._catSetLang = function(newLang) {
        lang = newLang;
        var enBtn = document.getElementById('_catLangEN');
        var teBtn = document.getElementById('_catLangTE');
        if (enBtn && teBtn) {
            if (lang === 'english') {
                enBtn.style.background = '#FFA500'; enBtn.style.borderColor = '#FFA500'; enBtn.style.color = '#fff'; enBtn.style.fontWeight = '600';
                teBtn.style.background = '#fff';    teBtn.style.borderColor = '#ddd';    teBtn.style.color = '#555'; teBtn.style.fontWeight = 'normal';
            } else {
                teBtn.style.background = '#FFA500'; teBtn.style.borderColor = '#FFA500'; teBtn.style.color = '#fff'; teBtn.style.fontWeight = '600';
                enBtn.style.background = '#fff';    enBtn.style.borderColor = '#ddd';    enBtn.style.color = '#555'; enBtn.style.fontWeight = 'normal';
            }
        }
        window._catUpdatePreview();
    };

    var prefixEl = document.getElementById('_catPrefix');
    var nameEl   = document.getElementById('_catRecipientName');
    if (prefixEl) prefixEl.addEventListener('change', window._catUpdatePreview);
    if (nameEl)   nameEl.addEventListener('input',  window._catUpdatePreview);

    window._catUpdatePreview();

    window._catShare = async function(platform) {
        var prefix = (document.getElementById('_catPrefix') || {}).value || '';
        var name   = (document.getElementById('_catRecipientName') || {}).value || '';
        var refCode = '';

        try {
            var sRes = await fetch('/api/v1/catalog/share', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + (window.sessionToken || '')
                },
                body: JSON.stringify({
                    platform:         platform,
                    language:         lang,
                    mnr_id:           userInfo.id   || '',
                    member_name:      userInfo.name || '',
                    recipient_name:   name   || null,
                    recipient_prefix: prefix || null
                })
            });
            var sData = await sRes.json();
            if (sData.success) refCode = sData.share_ref_code || '';
        } catch(e) { console.warn('[DC Catalog] Share record failed', e); }

        var catalogUrl = window._catGetCatalogUrl(refCode);
        var msgText = document.getElementById('_catMsgPreview')
            ? document.getElementById('_catMsgPreview').value
            : buildMessage(prefix, name, lang, catalogUrl, userInfo.name, userInfo.id);

        /* Replace placeholder URL with the tracked URL */
        msgText = msgText.replace(window._catGetCatalogUrl(''), catalogUrl);

        var encodedMsg = encodeURIComponent(msgText);
        var encodedUrl = encodeURIComponent(catalogUrl);

        if (platform === 'whatsapp') {
            window.open('https://wa.me/?text=' + encodedMsg, '_blank');
        } else if (platform === 'telegram') {
            var teleText = msgText.replace(catalogUrl, '').trim();
            window.open('https://t.me/share/url?url=' + encodedUrl + '&text=' + encodeURIComponent(teleText), '_blank');
        } else if (platform === 'sms') {
            window.location.href = 'sms:?body=' + encodedMsg;
        } else if (platform === 'email') {
            var subject = encodeURIComponent('MNR Business Access Program Catalog');
            window.location.href = 'mailto:?subject=' + subject + '&body=' + encodedMsg;
        } else if (platform === 'copy') {
            try {
                await navigator.clipboard.writeText(catalogUrl);
                var copyBtn = document.getElementById('_catCopyBtn');
                if (copyBtn) {
                    copyBtn.innerHTML = '\u2713 Copied!';
                    setTimeout(function() { copyBtn.innerHTML = '<i class="fas fa-copy"></i> Copy Link'; }, 2000);
                }
            } catch(e) {
                var ta = document.createElement('textarea');
                ta.value = catalogUrl;
                ta.style.cssText = 'position:fixed;opacity:0;';
                document.body.appendChild(ta); ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                alert('Link copied!');
            }
        } else if (platform === 'native' && navigator.share) {
            try { await navigator.share({ title: 'MNR Business Access Program', text: msgText, url: catalogUrl }); } catch(e) {}
        }

        if (refCode) {
            setTimeout(function() {
                var statsEl = document.getElementById('catalogShareStatsVal');
                if (!statsEl) return;
                fetch('/api/v1/catalog/my-stats', { headers: { 'Authorization': 'Bearer ' + (window.sessionToken || '') } })
                    .then(function(r) { return r.json(); })
                    .then(function(cs) {
                        var s = cs.total_shares || 0, v = cs.total_visits || 0, a = cs.avg_visits || 0;
                        statsEl.innerHTML =
                            '<span class="fw-bold text-primary">' + s + '</span>' +
                            '<span class="text-muted"> / </span>' +
                            '<span class="fw-bold text-success">' + v + '</span>' +
                            '<span class="text-muted"> / </span>' +
                            '<span class="fw-bold text-info">' + a + '</span>' +
                            ' <small class="text-muted">(Shared&nbsp;/&nbsp;Visits&nbsp;/&nbsp;Avg)</small>';
                    }).catch(function() {});
            }, 1500);
        }
    };
};
