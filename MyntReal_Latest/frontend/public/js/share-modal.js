/**
 * Universal Share Modal Component - DC Protocol Compliant
 * MyntReal Platform - Unified social sharing across all pages
 * 
 * Usage:
 *   MyntShareModal.show({
 *     url: 'https://example.com/page',
 *     title: 'Page Title',
 *     text: 'Share this content',
 *     type: 'referral' | 'announcement' | 'property' | 'general'
 *   });
 * 
 * Or via data attributes:
 *   <button data-share-url="..." data-share-title="..." data-share-type="referral">Share</button>
 */

;(function(window) {
    'use strict';

    const MyntShareModal = {
        modalId: 'myntShareModal',
        
        socialPlatforms: [
            {
                id: 'copy',
                name: 'Copy Link',
                icon: 'fas fa-link',
                color: '#6b7280',
                bgColor: '#ffffff',
                borderColor: '#d1d5db',
                action: 'copy'
            },
            {
                id: 'whatsapp',
                name: 'WhatsApp',
                icon: 'fab fa-whatsapp',
                color: '#ffffff',
                bgColor: '#25D366',
                borderColor: '#25D366',
                action: 'whatsapp'
            },
            {
                id: 'facebook',
                name: 'Facebook',
                icon: 'fab fa-facebook-f',
                color: '#ffffff',
                bgColor: '#1877F2',
                borderColor: '#1877F2',
                action: 'facebook'
            },
            {
                id: 'twitter',
                name: 'X (Twitter)',
                icon: 'fab fa-x-twitter',
                color: '#ffffff',
                bgColor: '#000000',
                borderColor: '#000000',
                action: 'twitter'
            },
            {
                id: 'linkedin',
                name: 'LinkedIn',
                icon: 'fab fa-linkedin-in',
                color: '#ffffff',
                bgColor: '#0A66C2',
                borderColor: '#0A66C2',
                action: 'linkedin'
            }
        ],

        langTemplates: {
            english: function(name, url, baseText, senderName, referrerId) {
                var greeting = name ? ('Hi ' + name + '!\n\n') : '';
                var body = 'Join VGK4U — the Loyalty Rewards Platform for Solar, EV, Insurance & Real Estate!\n\nSign up for FREE and get *10,000 Welcome Points* + an extra *5,000 bonus points* when you use my referral link:';
                var refNote = referrerId ? ('\n\nReferral ID: *' + referrerId + '*') : '';
                var footer = '\n\n1 PT = ₹1 value. Start earning real rewards today!';
                var regards = '\n\nRegards,' + (senderName ? ('\n' + senderName) : '');
                return greeting + body + '\n\n' + url + refNote + footer + regards;
            },
            hindi: function(name, url, baseText, senderName, referrerId) {
                var greeting = name ? ('नमस्ते ' + name + '!\n\n') : '';
                var refNote = referrerId ? ('\n\nरेफरल ID: *' + referrerId + '*') : '';
                var regards = '\n\nधन्यवाद,' + (senderName ? ('\n' + senderName) : '');
                return greeting + 'VGK4U से जुड़ें — Solar, EV, Insurance और Real Estate के लिए लॉयल्टी रिवॉर्ड प्लेटफॉर्म!\n\nFREE में साइन अप करें और पाएं *10,000 Welcome Points* + मेरे लिंक से जुड़ने पर अतिरिक्त *5,000 bonus points*:\n\n' + url + refNote + '\n\n1 PT = ₹1 मूल्य। आज ही कमाना शुरू करें!' + regards;
            },
            telugu: function(name, url, baseText, senderName, referrerId) {
                var greeting = name ? ('హలో ' + name + '!\n\n') : '';
                var refNote = referrerId ? ('\n\nరెఫరల్ ID: *' + referrerId + '*') : '';
                var regards = '\n\nధన్యవాదాలు,' + (senderName ? ('\n' + senderName) : '');
                return greeting + 'VGK4U లో చేరండి — Solar, EV, Insurance & Real Estate కోసం లాయల్టీ రివార్డ్స్ ప్లాట్‌ఫారమ్!\n\nFREE గా సైన్ అప్ చేసుకోండి మరియు *10,000 వెల్కమ్ పాయింట్లు* + నా లింక్ ద్వారా చేరితే అదనంగా *5,000 బోనస్ పాయింట్లు* పొందండి:\n\n' + url + refNote + '\n\n1 PT = ₹1 విలువ. ఈరోజే సంపాదించడం ప్రారంభించండి!' + regards;
            },
            tamil: function(name, url, baseText, senderName, referrerId) {
                var greeting = name ? ('வணக்கம் ' + name + '!\n\n') : '';
                var refNote = referrerId ? ('\n\nரெஃபரல் ID: *' + referrerId + '*') : '';
                var regards = '\n\nநன்றி,' + (senderName ? ('\n' + senderName) : '');
                return greeting + 'VGK4U-ல் சேருங்கள் — Solar, EV, Insurance & Real Estate-க்கான Loyalty Rewards Platform!\n\nFREE-யாக பதிவு செய்து *10,000 Welcome Points* + என் லிங்க் வழியாக சேர்ந்தால் கூடுதலாக *5,000 bonus points* பெறுங்கள்:\n\n' + url + refNote + '\n\n1 PT = ₹1 மதிப்பு. இன்றே சம்பாதிக்கத் தொடங்குங்கள்!' + regards;
            },
            kannada: function(name, url, baseText, senderName, referrerId) {
                var greeting = name ? ('ನಮಸ್ಕಾರ ' + name + '!\n\n') : '';
                var refNote = referrerId ? ('\n\nರೆಫರಲ್ ID: *' + referrerId + '*') : '';
                var regards = '\n\nಧನ್ಯವಾದಗಳು,' + (senderName ? ('\n' + senderName) : '');
                return greeting + 'VGK4U ಗೆ ಸೇರಿ — Solar, EV, Insurance & Real Estate ಗಾಗಿ Loyalty Rewards Platform!\n\nFREE ಆಗಿ ನೋಂದಾಯಿಸಿ ಮತ್ತು *10,000 Welcome Points* + ನನ್ನ ಲಿಂಕ್ ಮೂಲಕ ಸೇರಿದರೆ ಹೆಚ್ಚುವರಿ *5,000 bonus points* ಪಡೆಯಿರಿ:\n\n' + url + refNote + '\n\n1 PT = ₹1 ಮೌಲ್ಯ. ಇಂದೇ ಸಂಪಾದಿಸಲು ಪ್ರಾರಂಭಿಸಿ!' + regards;
            }
        },

        getModalStyles: function() {
            return `
                .mynt-share-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.6);
                    z-index: 99999;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 1rem;
                    animation: myntShareFadeIn 0.2s ease-out;
                    overflow-y: auto;
                }
                @keyframes myntShareFadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes myntShareSlideUp {
                    from { transform: translateY(20px); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
                .mynt-share-modal {
                    background: white;
                    border-radius: 1rem;
                    padding: 1.25rem;
                    max-width: 420px;
                    width: 100%;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
                    animation: myntShareSlideUp 0.3s ease-out;
                    max-height: 90vh;
                    overflow-y: auto;
                }
                .mynt-share-header {
                    text-align: center;
                    margin-bottom: 1rem;
                    padding-bottom: 0.75rem;
                    border-bottom: 1px solid #f3f4f6;
                }
                .mynt-share-header h3 {
                    font-size: 1.15rem;
                    font-weight: 700;
                    color: #1f2937;
                    margin: 0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 0.5rem;
                }
                .mynt-share-header h3 i { color: #10b981; }
                .mynt-share-header p {
                    color: #6b7280;
                    font-size: 0.8rem;
                    margin: 0.3rem 0 0 0;
                }
                .mynt-share-compose {
                    margin-bottom: 1rem;
                }
                .mynt-share-compose-row {
                    display: flex;
                    gap: 0.5rem;
                    margin-bottom: 0.5rem;
                }
                .mynt-share-compose-row label {
                    font-size: 0.75rem;
                    font-weight: 600;
                    color: #4b5563;
                    display: block;
                    margin-bottom: 3px;
                }
                .mynt-share-compose-row .field-wrap {
                    flex: 1;
                }
                .mynt-share-input {
                    width: 100%;
                    padding: 0.5rem 0.75rem;
                    border: 1px solid #d1d5db;
                    border-radius: 0.5rem;
                    font-size: 0.85rem;
                    color: #1f2937;
                    background: #fafafa;
                    outline: none;
                    box-sizing: border-box;
                }
                .mynt-share-input:focus {
                    border-color: #7c3aed;
                    background: #fff;
                }
                .mynt-share-textarea {
                    width: 100%;
                    padding: 0.6rem 0.75rem;
                    border: 1px solid #d1d5db;
                    border-radius: 0.5rem;
                    font-size: 0.82rem;
                    color: #374151;
                    background: #fafafa;
                    resize: vertical;
                    min-height: 90px;
                    outline: none;
                    font-family: inherit;
                    line-height: 1.4;
                    box-sizing: border-box;
                }
                .mynt-share-textarea:focus {
                    border-color: #7c3aed;
                    background: #fff;
                }
                .mynt-share-link-row {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    background: #f3e8ff;
                    border: 1px solid #c4b5fd;
                    border-radius: 0.5rem;
                    padding: 0.5rem 0.75rem;
                    margin-bottom: 0.75rem;
                }
                .mynt-share-link-text {
                    flex: 1;
                    font-size: 0.78rem;
                    color: #4c1d95;
                    font-weight: 500;
                    word-break: break-all;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                .mynt-share-link-copy {
                    background: #7c3aed;
                    color: white;
                    border: none;
                    border-radius: 0.375rem;
                    padding: 0.35rem 0.75rem;
                    font-size: 0.78rem;
                    font-weight: 600;
                    cursor: pointer;
                    white-space: nowrap;
                    flex-shrink: 0;
                }
                .mynt-share-link-copy:hover { background: #6d28d9; }
                .mynt-share-divider {
                    text-align: center;
                    font-size: 0.75rem;
                    color: #9ca3af;
                    margin: 0.75rem 0 0.5rem;
                    position: relative;
                }
                .mynt-share-divider::before,
                .mynt-share-divider::after {
                    content: '';
                    position: absolute;
                    top: 50%;
                    width: 40%;
                    height: 1px;
                    background: #e5e7eb;
                }
                .mynt-share-divider::before { left: 0; }
                .mynt-share-divider::after { right: 0; }
                .mynt-share-buttons {
                    display: flex;
                    flex-direction: column;
                    gap: 0.5rem;
                }
                .mynt-share-btn {
                    width: 100%;
                    padding: 0.65rem 1rem;
                    border-radius: 0.5rem;
                    font-size: 0.9rem;
                    font-weight: 500;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 0.625rem;
                    transition: all 0.2s ease;
                    border: 1px solid;
                }
                .mynt-share-btn:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                }
                .mynt-share-btn:active { transform: translateY(0); }
                .mynt-share-btn i { font-size: 1rem; }
                .mynt-share-cancel {
                    margin-top: 0.5rem;
                    width: 100%;
                    padding: 0.6rem;
                    border: 1px solid #e5e7eb;
                    background: #f9fafb;
                    color: #6b7280;
                    border-radius: 0.5rem;
                    font-size: 0.875rem;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                .mynt-share-cancel:hover { background: #f3f4f6; color: #374151; }
                .mynt-share-success {
                    position: fixed;
                    bottom: 2rem;
                    left: 50%;
                    transform: translateX(-50%);
                    background: #10b981;
                    color: white;
                    padding: 0.75rem 1.5rem;
                    border-radius: 0.5rem;
                    font-weight: 500;
                    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
                    z-index: 100000;
                    animation: myntShareSlideUp 0.3s ease-out;
                    white-space: nowrap;
                }
            `;
        },

        injectStyles: function() {
            if (document.getElementById('mynt-share-styles')) return;
            const style = document.createElement('style');
            style.id = 'mynt-share-styles';
            style.textContent = this.getModalStyles();
            document.head.appendChild(style);
        },

        show: function(options) {
            var self = this;
            var url             = options.url             || window.location.href;
            var title           = options.title           || 'MyntReal';
            var text            = options.text            || 'Check this out from MyntReal!';
            var type            = options.type            || 'general';
            var subtitle        = options.subtitle        || '';
            var thumbnail       = options.thumbnail       || '';
            var statsCard       = options.statsCard       || null;
            var recipientName   = options.recipientName   || '';
            var senderName      = options.senderName      || '';
            var referrerId        = options.referrerId        || '';
            var defaultReferrerId = options.defaultReferrerId || '';
            var composeEnabled  = options.composeEnabled  !== undefined ? options.composeEnabled : (type === 'referral');
            var langSupport     = options.langSupport     !== undefined ? options.langSupport     : (type === 'referral');
            var showReferrer    = options.showReferrer    !== undefined ? options.showReferrer    : (type === 'referral');
            var isReferral = (type === 'referral');

            self.injectStyles();
            self.close();

            var overlay = document.createElement('div');
            overlay.id = self.modalId;
            overlay.className = 'mynt-share-overlay';

            var modal = document.createElement('div');
            modal.className = 'mynt-share-modal';

            var headerIcon = isReferral ? 'fa-user-plus' :
                             type === 'announcement'  ? 'fa-bullhorn'     :
                             type === 'property'      ? 'fa-home'         :
                             type === 'progress'      ? 'fa-chart-line'   :
                             type === 'performance'   ? 'fa-trophy'       : 'fa-share-alt';
            var headerText = isReferral ? 'Share Referral Link' :
                             type === 'announcement'  ? 'Share Announcement' :
                             type === 'property'      ? 'Share Property'     :
                             type === 'progress'      ? 'Share Progress'     :
                             type === 'performance'   ? 'Share Performance'  : 'Share';

            var initRef    = referrerId || defaultReferrerId;
            var initUrl    = (initRef && (isReferral || langSupport))
                ? url + (url.indexOf('?') >= 0 ? '&' : '?') + 'ref=' + encodeURIComponent(initRef)
                : url;
            var defaultMsg = (isReferral || langSupport)
                ? self.langTemplates.english(recipientName, initUrl, text, senderName, initRef)
                : (text.indexOf(url) >= 0 ? text : text + '\n\n' + url);

            // ── Thumbnail / icon strip ────────────────────────────────────
            var thumbHtml = '';
            if (thumbnail) {
                var isEmoji = thumbnail.length <= 4 && !/^https?:\/\//.test(thumbnail);
                if (isEmoji) {
                    thumbHtml = '<div style="text-align:center;font-size:36px;margin-bottom:6px;">' + thumbnail + '</div>';
                } else {
                    thumbHtml = '<div style="text-align:center;margin-bottom:8px;"><img src="' + thumbnail + '" style="max-height:80px;border-radius:8px;object-fit:cover;" /></div>';
                }
            }

            // ── Subtitle under header ─────────────────────────────────────
            var subtitleHtml = subtitle
                ? '<p style="color:#6366f1;font-size:12px;font-weight:600;margin:2px 0 0;">' + subtitle + '</p>'
                : '<p>Share with your friends and family</p>';

            // ── Stats preview card ────────────────────────────────────────
            var statsHtml = '';
            if (statsCard && statsCard.length) {
                statsHtml = '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:10px 14px;margin-bottom:10px;display:flex;gap:10px;flex-wrap:wrap;justify-content:center;">';
                statsCard.forEach(function(s) {
                    var col = s.color || '#6366f1';
                    statsHtml += '<div style="text-align:center;min-width:60px;">'
                        + '<div style="font-size:18px;font-weight:800;color:' + col + ';">' + (s.value || '—') + '</div>'
                        + '<div style="font-size:10px;color:#6b7280;margin-top:1px;">' + (s.label || '') + '</div>'
                        + '</div>';
                });
                statsHtml += '</div>';
            }

            // ── Compose area ──────────────────────────────────────────────
            var composeHtml = '';
            if (composeEnabled) {
                var nameField = '<div class="field-wrap">'
                    + '<label>Recipient\'s Name (optional)</label>'
                    + '<input id="msm-name" class="mynt-share-input" type="text" placeholder="e.g. Ravi, Priya…" value="' + (recipientName || '') + '" />'
                    + '</div>';
                var langField = langSupport ? (
                    '<div class="field-wrap">'
                    + '<label>Language</label>'
                    + '<select id="msm-lang" class="mynt-share-input">'
                    + '<option value="english">English</option>'
                    + '<option value="hindi">Hindi</option>'
                    + '<option value="telugu">Telugu</option>'
                    + '<option value="tamil">Tamil</option>'
                    + '<option value="kannada">Kannada</option>'
                    + '</select></div>'
                ) : '';
                var senderRow = showReferrer ? (
                    '<div class="mynt-share-compose-row" style="margin-bottom:0.5rem">'
                    + '<div class="field-wrap">'
                    + '<label>Your Partner Code / VGK ID</label>'
                    + '<div style="display:flex;gap:6px;align-items:center">'
                    + '<input id="msm-refid" class="mynt-share-input" type="text" placeholder="e.g. VGK123456" value="' + (referrerId || defaultReferrerId || '') + '" style="text-transform:uppercase;flex:1" />'
                    + '<button id="msm-refid-search" type="button" style="background:#7c3aed;color:#fff;border:none;border-radius:6px;padding:6px 11px;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap;flex-shrink:0"><i class="fas fa-search"></i></button>'
                    + '</div>'
                    + '<div id="msm-refid-status" style="font-size:11px;margin-top:3px;min-height:15px"></div>'
                    + '</div>'
                    + '<div class="field-wrap">'
                    + '<label>Your Name (auto-filled / sign-off)</label>'
                    + '<input id="msm-sender" class="mynt-share-input" type="text" placeholder="Found from VGK ID…" value="' + (senderName || '') + '" />'
                    + '</div>'
                    + '</div>'
                ) : '';
                composeHtml =
                    '<div class="mynt-share-compose">' +
                        '<div class="mynt-share-compose-row">' + nameField + langField + '</div>' +
                        senderRow +
                        '<label style="font-size:.75rem;font-weight:600;color:#4b5563;display:block;margin-bottom:3px">Message (edit as you like)</label>' +
                        '<textarea id="msm-msg" class="mynt-share-textarea">' + defaultMsg.replace(/</g,'&lt;') + '</textarea>' +
                    '</div>';
            }

            var linkRow =
                '<div class="mynt-share-link-row">' +
                    '<span class="mynt-share-link-text" id="msm-link-preview">' + initUrl + '</span>' +
                    '<button class="mynt-share-link-copy" id="msm-copy-btn"><i class="fas fa-copy"></i> Copy Message</button>' +
                '</div>';

            var buttonsHtml = '<div class="mynt-share-divider">Share via</div><div class="mynt-share-buttons">';
            self.socialPlatforms.filter(function(p){ return p.action !== 'copy'; }).forEach(function(platform) {
                var btnStyle = 'background:' + platform.bgColor + ';color:' + platform.color + ';border-color:' + platform.borderColor + ';';
                buttonsHtml += '<button class="mynt-share-btn" data-action="' + platform.action + '" style="' + btnStyle + '">';
                buttonsHtml += '<i class="' + platform.icon + '"></i>' + platform.name;
                buttonsHtml += '</button>';
            });
            buttonsHtml += '</div>';

            modal.innerHTML =
                thumbHtml +
                '<div class="mynt-share-header"><h3><i class="fas ' + headerIcon + '"></i>' + headerText + '</h3>' + subtitleHtml + '</div>' +
                statsHtml +
                composeHtml +
                linkRow +
                buttonsHtml +
                '<button class="mynt-share-cancel">Cancel</button>';

            overlay.appendChild(modal);
            document.body.appendChild(overlay);

            function getCurrentMsg() {
                var ta = modal.querySelector('#msm-msg');
                if (ta) return ta.value;
                return text.indexOf(url) >= 0 ? text : (text + '\n\n' + url);
            }

            if (composeEnabled) {
                var nameEl   = modal.querySelector('#msm-name');
                var langEl   = modal.querySelector('#msm-lang');
                var msgEl    = modal.querySelector('#msm-msg');
                var senderEl = modal.querySelector('#msm-sender');
                var refIdEl  = modal.querySelector('#msm-refid');
                var linkPrev = modal.querySelector('#msm-link-preview');
                var baseText = options.text || '';
                var activeUrl = initUrl;

                function rebuildMsg() {
                    var n   = nameEl   ? nameEl.value.trim()   : '';
                    var sn  = senderEl ? senderEl.value.trim() : '';
                    var rid = refIdEl  ? refIdEl.value.trim().toUpperCase() : '';
                    var l   = langEl   ? (langEl.value || 'english') : 'english';
                    var effectiveRef = rid || defaultReferrerId;

                    activeUrl = url + (url.indexOf('?') >= 0 ? '&' : '?') + 'ref=' + encodeURIComponent(effectiveRef);
                    modal._activeUrl = activeUrl;
                    if (linkPrev) linkPrev.textContent = activeUrl;

                    var fn = (langSupport && self.langTemplates[l]) ? self.langTemplates[l] : function(nm, u, bt, snm, ri) {
                        var gr = nm ? ('Hi ' + nm + '!\n\n') : '';
                        var refNote = ri ? ('\n\nMy Partner Code: *' + ri + '*') : '';
                        var reg = '\n\nRegards,' + (snm ? ('\n' + snm) : '');
                        return gr + (bt || '') + '\n\n' + u + refNote + reg;
                    };
                    if (msgEl) msgEl.value = fn(n, activeUrl, baseText, sn, effectiveRef);
                }
                if (nameEl)   nameEl.addEventListener('input', rebuildMsg);
                if (langEl)   langEl.addEventListener('change', rebuildMsg);
                if (senderEl) senderEl.addEventListener('input', rebuildMsg);

                // ── VGK ID live search (single input listener handles both rebuild + debounced search) ──
                var statusEl    = modal.querySelector('#msm-refid-status');
                var searchBtn   = modal.querySelector('#msm-refid-search');
                var searchTimer = null;

                function setStatus(msg, color) {
                    if (!statusEl) return;
                    statusEl.style.color = color || '#6b7280';
                    statusEl.innerHTML = msg;
                }

                function doLookup() {
                    var q = refIdEl ? refIdEl.value.trim() : '';
                    if (!q || q.length < 3) { setStatus('', ''); return; }
                    setStatus('<i class="fas fa-spinner fa-spin"></i> Searching…', '#7c3aed');
                    fetch('/api/v1/vgk/public/member-lookup?q=' + encodeURIComponent(q))
                        .then(function(r) { return r.json(); })
                        .then(function(data) {
                            var found = (data.results && data.results[0]) ? data.results[0] : null;
                            if (found && found.partner_name) {
                                setStatus('<i class="fas fa-check-circle"></i> Found: <strong>' + found.partner_name + '</strong> (' + found.partner_code + ')', '#059669');
                                if (senderEl && !senderEl.value.trim()) {
                                    senderEl.value = found.partner_name;
                                    rebuildMsg();
                                }
                                if (refIdEl && refIdEl.value.trim().toUpperCase() !== found.partner_code) {
                                    refIdEl.value = found.partner_code;
                                }
                                rebuildMsg();
                            } else {
                                setStatus('<i class="fas fa-times-circle"></i> No member found', '#dc2626');
                            }
                        })
                        .catch(function() {
                            setStatus('<i class="fas fa-times-circle"></i> No member found', '#dc2626');
                        });
                }

                if (refIdEl) {
                    refIdEl.addEventListener('input', function() {
                        clearTimeout(searchTimer);
                        setStatus('', '');
                        searchTimer = setTimeout(doLookup, 650);
                        rebuildMsg();
                    });
                }
                if (searchBtn) {
                    searchBtn.addEventListener('click', function(e) {
                        e.stopPropagation();
                        clearTimeout(searchTimer);
                        doLookup();
                    });
                }

                if (refIdEl && refIdEl.value.trim().length >= 3) {
                    setTimeout(doLookup, 200);
                }

                modal._activeUrl = activeUrl;
            }

            var copyBtn = modal.querySelector('#msm-copy-btn');
            if (copyBtn) {
                copyBtn.addEventListener('click', function() {
                    var textToCopy = getCurrentMsg();
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        navigator.clipboard.writeText(textToCopy).then(function() {
                            self.showSuccess('Message copied to clipboard!');
                        }).catch(function() { self.fallbackCopy(textToCopy); });
                    } else {
                        self.fallbackCopy(textToCopy);
                    }
                    copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
                    copyBtn.style.background = '#059669';
                    setTimeout(function() {
                        copyBtn.innerHTML = '<i class="fas fa-copy"></i> Copy Message';
                        copyBtn.style.background = '#7c3aed';
                    }, 2000);
                });
            }

            modal.querySelectorAll('.mynt-share-btn').forEach(function(btn) {
                btn.addEventListener('click', function() {
                    var action = this.getAttribute('data-action');
                    var msg = getCurrentMsg();
                    var shareUrl = modal._activeUrl || url;
                    self.handleAction(action, shareUrl, msg, title, msg);
                });
            });

            modal.querySelector('.mynt-share-cancel').addEventListener('click', function() {
                self.close();
            });

            modal.addEventListener('click', function(e) {
                e.stopPropagation();
            });
            overlay.addEventListener('click', function(e) {
                if (!modal.contains(e.target)) { self.close(); }
            });

            document.addEventListener('keydown', function escHandler(e) {
                if (e.key === 'Escape') {
                    self.close();
                    document.removeEventListener('keydown', escHandler);
                }
            });
        },

        handleAction: function(action, url, text, title, fullText) {
            const self = this;
            const encodedUrl = encodeURIComponent(url);
            const encodedText = encodeURIComponent(text);
            const encodedTitle = encodeURIComponent(title);
            const encodedFullText = encodeURIComponent(fullText);

            switch(action) {
                case 'copy': {
                    var copyTarget = fullText || text || url;
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        navigator.clipboard.writeText(copyTarget).then(function() {
                            self.showSuccess('Message copied to clipboard!');
                            self.close();
                        }).catch(function() {
                            self.fallbackCopy(copyTarget);
                        });
                    } else {
                        self.fallbackCopy(copyTarget);
                    }
                    break;
                }

                case 'whatsapp':
                    (function(encoded) {
                        var isMob = /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
                        if (isMob) {
                            location.href = 'whatsapp://send?text=' + encoded;
                            setTimeout(function() {
                                window.open('https://wa.me/?text=' + encoded, '_blank');
                            }, 1500);
                        } else {
                            window.open('https://wa.me/?text=' + encoded, '_blank');
                        }
                    })(encodedFullText);
                    self.close();
                    break;

                case 'facebook':
                    window.open('https://www.facebook.com/sharer/sharer.php?u=' + encodedUrl + '&quote=' + encodedText, '_blank');
                    self.close();
                    break;

                case 'twitter':
                    window.open('https://twitter.com/intent/tweet?text=' + encodedText + '&url=' + encodedUrl, '_blank');
                    self.close();
                    break;

                case 'linkedin':
                    window.open('https://www.linkedin.com/sharing/share-offsite/?url=' + encodedUrl, '_blank');
                    self.close();
                    break;
            }
        },

        fallbackCopy: function(text) {
            const self = this;
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            textarea.select();
            try {
                document.execCommand('copy');
                self.showSuccess('Link copied to clipboard!');
                self.close();
            } catch (err) {
                alert('Failed to copy link. Please copy manually: ' + text);
            }
            document.body.removeChild(textarea);
        },

        showSuccess: function(message) {
            const existing = document.querySelector('.mynt-share-success');
            if (existing) existing.remove();

            const toast = document.createElement('div');
            toast.className = 'mynt-share-success';
            toast.innerHTML = '<i class="fas fa-check-circle" style="margin-right: 0.5rem;"></i>' + message;
            document.body.appendChild(toast);

            setTimeout(function() {
                toast.style.opacity = '0';
                toast.style.transition = 'opacity 0.3s ease';
                setTimeout(function() {
                    if (toast.parentNode) toast.parentNode.removeChild(toast);
                }, 300);
            }, 2500);
        },

        /**
         * shareAnnouncement — DC Protocol: universal announcement share format
         * Works identically across MNR, Staff, VGK4U, and public portals.
         * Only the signerName changes per portal.
         *
         * opts: { id, title, description, categoryName, userName, city, signerName }
         */
        shareAnnouncement: function(opts) {
            var id           = opts.id           || '';
            var title        = opts.title        || 'Announcement';
            var description  = opts.description  || '';
            var categoryName = opts.categoryName || 'MNR Business Access Program';
            var userName     = opts.userName     || '';
            var city         = opts.city         || '';
            var signerName   = opts.signerName   || (window._shareSignature || 'Myntreal');
            var url          = 'https://mnrteam.com/public/announcement?id=' + id + '&shared=true';

            var lines = [];
            lines.push('🏠 ' + categoryName);
            lines.push('');
            lines.push(title);
            if (description) lines.push(description);
            lines.push('');
            var metaLine = '';
            if (userName) metaLine += '🧑 ' + userName;
            if (city)     metaLine += (metaLine ? ' · ' : '') + '📍 ' + city;
            if (metaLine) lines.push(metaLine);
            lines.push('');
            lines.push('👁 View: ' + url);
            lines.push('');
            lines.push('Regards,');
            lines.push(signerName);

            var shareText = lines.join('\n');

            this.show({
                url:           url,
                title:         title,
                text:          shareText,
                type:          'announcement',
                subtitle:      categoryName,
                composeEnabled: true,
                langSupport:   false,
            });
        },

        close: function() {
            const modal = document.getElementById(this.modalId);
            if (modal) {
                modal.style.opacity = '0';
                modal.style.transition = 'opacity 0.2s ease';
                setTimeout(function() {
                    if (modal.parentNode) modal.parentNode.removeChild(modal);
                }, 200);
            }
        },

        initTriggers: function() {
            const self = this;
            document.addEventListener('click', function(e) {
                const trigger = e.target.closest('[data-share-url]');
                if (trigger) {
                    e.preventDefault();
                    self.show({
                        url: trigger.getAttribute('data-share-url'),
                        title: trigger.getAttribute('data-share-title') || 'MyntReal',
                        text: trigger.getAttribute('data-share-text') || 'Check this out!',
                        type: trigger.getAttribute('data-share-type') || 'general'
                    });
                }
            });
        }
    };

    window.MyntShareModal = MyntShareModal;
    console.log('[DC] MyntShareModal component loaded successfully - 5 social platforms available');

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            MyntShareModal.initTriggers();
        });
    } else {
        MyntShareModal.initTriggers();
    }

})(window);
