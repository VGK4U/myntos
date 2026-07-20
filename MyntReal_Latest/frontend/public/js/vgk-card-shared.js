/**
 * vgk-card-shared.js — SINGLE SOURCE OF TRUTH for VGK4U card rendering & download.
 * Loaded by both vgk_dashboard.html (member) and staff_vgk_members.html (staff).
 * Any card layout or download change MUST be made here ONLY.
 * v20260508v — DC-AUTH-FETCH-001 + DC-QR-CANVAS-001 + DC-VCARD-RERENDER-001
 */
(function (global) {
    'use strict';

    function _e(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    /* Formats an Indian mobile as +91 XXXXX XXXXX. Returns '' for missing/empty input. */
    function _fmtPhone(rawPhone) {
        if (!rawPhone) return '';
        const clean = String(rawPhone).replace(/^\+91\s*|^0/, '').replace(/\D/g, '');
        if (!clean) return '';
        if (clean.length >= 10) return '+91 ' + clean.slice(0, 5) + ' ' + clean.slice(5, 10);
        if (clean.length > 5)   return '+91 ' + clean.slice(0, 5) + ' ' + clean.slice(5);
        return '+91 ' + clean;
    }

    /* ── Inline SVG icon helper ───────────────────────────────────────────── */
    var _P = {
        phone:   ['0 0 512 512', 'M493.4 24.6l-104-24c-11.3-2.6-22.9 3.3-27.5 13.9l-48 112c-4.2 9.8-1.4 21.3 6.9 28l60.6 49.6c-36 76.7-98.9 140.5-177.2 177.2l-49.6-60.6c-6.8-8.3-18.2-11.1-28-6.9l-112 48C3.9 366.5-2 378.1.6 389.4l24 104C27.1 504.2 36.7 512 48 512c256.1 0 464-207.5 464-464 0-11.2-7.7-20.9-18.6-23.4z'],
        globe:   ['0 0 496 512', 'M336.5 160C322 70.7 287.8 8 248 8s-74 62.7-88.5 152h177zM152 256c0 22.2 1.2 43.5 3.3 64h185.3c2.1-20.5 3.3-41.8 3.3-64s-1.2-43.5-3.3-64H155.3c-2.1 20.5-3.3 41.8-3.3 64zm324.7-96c-28.6-67.9-86.5-120.4-158-141.6 24.4 33.8 41.2 84.7 50 141.6h108zM177.2 18.4C105.8 39.6 47.8 92.1 19.3 160h108c8.7-56.9 25.5-107.8 49.9-141.6zM487.4 192H372.7c2.1 21 3.3 42.5 3.3 64s-1.2 43-3.3 64h114.6c5.5-20.5 8.6-41.8 8.6-64s-3.1-43.5-8.5-64zM120 256c0-21.5 1.2-43 3.3-64H8.6C3.2 212.5 0 233.8 0 256s3.2 43.5 8.6 64h114.6c-2-21-3.2-42.5-3.2-64zm39.5 96c14.5 89.3 48.7 152 88.5 152s74-62.7 88.5-152h-177zm159.3 141.6c71.4-21.2 129.4-73.7 158-141.6h-108c-8.8 56.9-25.6 107.8-50 141.6zM19.3 352c28.6 67.9 86.5 120.4 158 141.6-24.4-33.8-41.2-84.7-50-141.6H19.3z'],
        pin:     ['0 0 384 512', 'M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0zM192 272c44.183 0 80-35.817 80-80s-35.817-80-80-80-80 35.817-80 80 35.817 80 80 80z'],
        solar:   ['0 0 640 512', 'M32 0C14.3 0 0 14.3 0 32V384c0 17.7 14.3 32 32 32h576c17.7 0 32-14.3 32-32V32C640 14.3 625.7 0 608 0H32zM160 96h96v96h-96V96zm0 128h96v96h-96v-96zm128-128h96v96h-96V96zm0 128h96v96h-96v-96zm128-128h96v96h-96V96zm0 128h96v96h-96v-96zM288 448h64v32h-64v-32z'],
        sun:     ['0 0 512 512', 'M256 160c-52.9 0-96 43.1-96 96s43.1 96 96 96 96-43.1 96-96-43.1-96-96-96zm246.4 80.5l-94.7-47.3 33.5-100.4c4.5-13.6-8.4-26.5-21.9-21.9l-100.4 33.5-47.4-94.8c-6.4-12.8-24.6-12.8-31 0l-47.3 94.7L92.7 70.8c-13.6-4.5-26.5 8.4-21.9 21.9l33.5 100.4-94.7 47.4c-12.8 6.4-12.8 24.6 0 31l94.7 47.3-33.5 100.5c-4.5 13.6 8.4 26.5 21.9 21.9l100.4-33.5 47.3 94.7c6.4 12.8 24.6 12.8 31 0l47.3-94.7 100.4 33.5c13.6 4.5 26.5-8.4 21.9-21.9l-33.5-100.4 94.7-47.3c13-6.5 13-24.7.2-31.1zm-155.9 106c-49.9 49.9-131.1 49.9-181 0-49.9-49.9-49.9-131.1 0-181 49.9-49.9 131.1-49.9 181 0 49.9 49.9 49.9 131.1 0 181z'],
        car:     ['0 0 512 312', 'M499.99 80H440.12L423.48 38.4C406.38 15.63 365.57 0 319.5 0h-127C146.43 0 105.62 15.63 88.52 38.4L71.88 80H12.01C4.7 80-1.38 87.2.71 94.14l20 74.97C21.93 173.51 26.67 177 32 177h20.07C50.67 188.91 48 201.11 48 214v8c0 13.25 10.75 24 24 24h16c13.25 0 24-10.75 24-24v-8H400v8c0 13.25 10.75 24 24 24h16c13.25 0 24-10.75 24-24v-8c0-12.89-2.67-25.09-4.07-37H464c5.33 0 10.07-3.49 11.29-8.89l20-74.97C497.38 87.2 491.3 80 499.99 80zM148 144c-17.67 0-32-14.33-32-32s14.33-32 32-32 32 14.33 32 32-14.33 32-32 32zm216 0c-17.67 0-32-14.33-32-32s14.33-32 32-32 32 14.33 32 32-14.33 32-32 32z'],
        /* Bootstrap Icons bi-scooter (viewBox 0 0 16 16) — 2-wheeler scooter for EV Solutions */
        scooter: ['0 0 16 16', 'M6.5 0a.5.5 0 0 0 0 1H8v1.293l-3.707 3.707A1 1 0 0 0 4 6.707V9H.5A1.5 1.5 0 0 0 0 10.5v2A1.5 1.5 0 0 0 1.5 14H2a3 3 0 0 0 6 0h2.5a1 1 0 0 0 .894-.553l2.853-5.706A1 1 0 0 0 14.25 7H9V6.707a1 1 0 0 0-.293-.707L5 2.293V1h1.5a.5.5 0 0 0 0-1h-2zm3 14a2 2 0 1 1-4 0 2 2 0 0 1 4 0zm5-4a2 2 0 1 1-4 0 2 2 0 0 1 4 0'],
        bolt:    ['0 0 320 512', 'M296 160H180.6l42.6-129.8C227.2 15 215.7 0 200 0H56C44 0 33.8 8.9 32.2 20.8l-32 240C-1.7 275.2 9.5 288 24 288h118.7L96.6 482.1c-3.8 17.2 18.2 30.5 30 16.3l160-200C298.6 283.4 290.3 272 280 272H176l54.4-80.2C243.4 172.3 236.1 160 224 160h72c14.1 0 22.3-16.2 13-26.4z'],
        shield:  ['0 0 512 512', 'M466.5 83.7l-192-80a48.15 48.15 0 0 0-36.9 0l-192 80C27.7 91.1 16 108.6 16 128c0 198.5 114.5 335.7 221.5 380.3 11.8 4.9 25.1 4.9 36.9 0C360.1 472.6 496 349.3 496 128c0-19.4-11.7-36.9-29.5-44.3zM256.1 446.3l-.1-381 175.9 73.3c-3.3 151.4-82.1 261.1-175.8 307.7z'],
        check:   ['0 0 512 512', 'M173.9 439.4l-166.4-166.4c-10-10-10-26.2 0-36.2l36.2-36.2c10-10 26.2-10 36.2 0L192 312.7 432.1 72.6c10-10 26.2-10 36.2 0l36.2 36.2c10 10 10 26.2 0 36.2l-294.4 294.4c-10 10-26.2 10-36.2 0z'],
        home:    ['0 0 576 512', 'M280.37 148.26L96 300.11V464a16 16 0 0 0 16 16l112.06-.29a16 16 0 0 0 15.92-16V368a16 16 0 0 1 16-16h64a16 16 0 0 1 16 16v95.64a16 16 0 0 0 16 16.05L464 480a16 16 0 0 0 16-16V300L295.67 148.26a12.19 12.19 0 0 0-15.3 0zM571.6 251.47L488 182.56V44.05a12 12 0 0 0-12-12h-56a12 12 0 0 0-12 12v72.61L318.47 43a48 48 0 0 0-61 0L4.34 251.47a12 12 0 0 0-1.6 16.9l25.5 31A12 12 0 0 0 45.15 301l235.22-193.74a12.19 12.19 0 0 1 15.3 0L530.9 301a12 12 0 0 0 16.9-1.6l25.5-31a12 12 0 0 0-1.7-16.93z'],
        badge:   ['0 0 384 512', 'M336 0H48C21.5 0 0 21.5 0 48v416c0 26.5 21.5 48 48 48h288c26.5 0 48-21.5 48-48V48c0-26.5-21.5-48-48-48zM144 32h96c8.8 0 16 7.2 16 16s-7.2 16-16 16h-96c-8.8 0-16-7.2-16-16s7.2-16 16-16zm48 128c35.3 0 64 28.7 64 64s-28.7 64-64 64-64-28.7-64-64 28.7-64 64-64zm112 236.8c0 10.6-10 19.2-22.4 19.2H102.4C90 416 80 407.4 80 396.8v-19.2c0-31.8 30.1-57.6 67.2-57.6h5c12.3 5.1 25.7 8 39.8 8s27.6-2.9 39.8-8h5c37.1 0 67.2 25.8 67.2 57.6v19.2z']
    };

    function _si(key, sz, fill, extra) {
        var p = _P[key];
        if (!p) return '';
        var st = 'width:' + sz + ';height:' + sz + ';fill:' + fill + ';display:inline-block;vertical-align:middle;flex-shrink:0;pointer-events:none' + (extra ? ';' + extra : '');
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="' + p[0] + '" style="' + st + '"><path d="' + p[1] + '"/></svg>';
    }

    /* ── Smart name-fit: tries single line, reduces font, then last-word-only wrap ── */
    /* [DC-NAME-FIT-002] After rendering, call _fitAllNames(containerEl) to auto-fit.
       Fix: block elements with overflow:visible report scrollWidth==offsetWidth (no overflow
       detected). Probe uses display:inline-block so el sizes to text content, then compare
       with parent clientWidth. Also fixed NBSP→space so last word actually wraps. */
    function _fitNameEl(el) {
        if (!el) return;
        var rawText = (el.getAttribute('data-vgk-name') || el.textContent || '').trim();
        if (!rawText) return;

        var MIN_SIZE = 10;
        var cur = parseFloat(el.style.fontSize) || 13;
        el.style.whiteSpace = 'nowrap';

        /* Temporarily switch to inline-block so el.offsetWidth = intrinsic text width.
           For overflow:visible block elements scrollWidth == offsetWidth (box width),
           making overflow undetectable. inline-block sizes to content. */
        var origDisplay = el.style.display;
        el.style.display = 'inline-block';
        var containerW = el.parentElement ? el.parentElement.clientWidth : 0;

        /* Step 1: reduce font until text fits or we hit MIN_SIZE */
        if (containerW > 0) {
            while (cur > MIN_SIZE && el.offsetWidth > containerW) {
                cur -= 0.5;
                el.style.fontSize = cur + 'px';
            }
        }
        var overflows = containerW > 0 && el.offsetWidth > containerW;

        /* Restore display before any innerHTML change */
        el.style.display = origDisplay;

        /* Step 2: if still overflows at MIN_SIZE, allow only last word to wrap */
        if (overflows) {
            var words = rawText.split(/\s+/);
            if (words.length > 1) {
                var allButLast = words.slice(0, -1).join(' ');
                var lastWord   = words[words.length - 1];
                el.style.whiteSpace = 'normal';
                el.style.wordBreak  = 'keep-all';
                /* Use a regular space (not NBSP) after the span so the browser
                   can break there and wrap the last word to the next line */
                el.innerHTML = '<span style="white-space:nowrap">' + _e(allButLast) + '</span> ' + _e(lastWord);
            } else {
                /* Single-word name — allow overflow-wrap as last resort */
                el.style.whiteSpace   = 'normal';
                el.style.overflowWrap = 'break-word';
            }
        }
    }

    function _fitAllNames(containerEl) {
        if (!containerEl) return;
        var els = containerEl.querySelectorAll('[data-vgk-name]');
        for (var i = 0; i < els.length; i++) _fitNameEl(els[i]);
    }

    /* ── Visiting Card FRONT ─────────────────────────────────────────────── */
    function _vcardFrontHtml(cd) {
        const name         = _e(cd.display_name || '—');
        const vgkId        = _e(cd.partner_code || '—');
        const city         = _e(cd.location || cd.city || '');
        const qrSrc        = cd.qr_b64 || '';
        const designation  = _e(cd.designation_label || 'Channel Partner');
        const companyPh    = '+91 858585 2738';
        const phoneDisplay = _e(_fmtPhone(cd.phone));

        return `<div id="vcardFront" style="background:linear-gradient(135deg,#f0f7ff 0%,#e0eef9 100%);border-radius:10px;overflow:hidden;box-shadow:0 3px 14px rgba(0,0,0,.13);font-family:'Segoe UI',sans-serif;width:340px;height:194px;display:flex;flex-direction:column">
    <div style="flex:1;min-height:0;padding:10px 12px 8px;display:flex;gap:8px;align-items:flex-start;overflow:hidden">
        <div style="flex:1.15;min-width:0">
            <div data-vgk-name="${name}" style="font-size:13px;font-weight:900;color:#1e1b4b;letter-spacing:-.3px;line-height:1.2;margin-bottom:4px;white-space:nowrap;overflow:visible">${name}</div>
            <div style="width:38px;height:3px;background:#f97316;border-radius:2px;margin-bottom:7px"></div>
            <div style="font-size:8px;color:#374151;font-weight:600;margin-bottom:4px">${designation} \u2013 VGK4U</div>
            <div style="font-size:7px;color:#1d4ed8;font-weight:800;letter-spacing:.04em;margin-bottom:7px">ID: ${vgkId}</div>
            <div style="display:flex;flex-direction:column;gap:6px">
                <div style="display:flex;align-items:center;gap:7px;font-size:10px;color:#111">
                    <div style="width:17px;height:17px;background:#1d4ed8;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0">${_si('phone','7.5px','#fff')}</div>
                    <span style="font-weight:700;white-space:nowrap">${phoneDisplay}</span>
                </div>
                <div style="display:flex;align-items:center;gap:7px;font-size:10px;color:#111">
                    <div style="width:17px;height:17px;background:#6b7280;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0">${_si('phone','7.5px','#fff')}</div>
                    <span style="font-weight:700;white-space:nowrap">${companyPh}</span>
                </div>
                ${city ? `<div style="display:flex;align-items:center;gap:7px;font-size:10px;color:#111">
                    <div style="width:17px;height:17px;background:#1d4ed8;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0">${_si('pin','7.5px','#fff')}</div>
                    <span>${city}</span>
                </div>` : ''}
            </div>
        </div>
        ${qrSrc ? `<div style="flex-shrink:0;text-align:center;padding:0 3px">
            <div style="border:1.5px solid #e5e7eb;border-radius:7px;padding:4px;background:#fff;display:inline-block">
                <img src="${qrSrc}" style="width:80px;height:80px;display:block" alt="Referral QR">
            </div>
            <div style="font-size:6.5px;font-weight:900;color:#1f2937;margin-top:4px;letter-spacing:.06em">SCAN TO CONNECT</div>
            <div style="font-size:6px;color:#555;margin-top:1px">Website / WhatsApp</div>
        </div>` : ''}
        <div style="flex:.9;text-align:right;padding-top:3px">
            <div style="font-size:7.5px;color:#6b7280;margin-bottom:5px;font-style:italic">Specialists in</div>
            <div style="font-size:11.5px;font-weight:900;line-height:1.55">
                <span style="color:#f97316">SOLAR</span> <span style="color:#6b7280;font-weight:400">|</span> <span style="color:#16a34a">EV</span>
            </div>
            <div style="font-size:11.5px;font-weight:900;color:#1d4ed8;line-height:1.55">INSURANCE</div>
            <div style="font-size:11.5px;font-weight:900;color:#f97316;line-height:1.55">REAL ESTATE</div>
            <div style="font-size:6.5px;color:#9ca3af;margin-top:6px;font-style:italic;line-height:1.5">Sustainable Solutions.<br>Reliable Tomorrow.</div>
        </div>
    </div>
    <div style="flex-shrink:0;padding:5px 12px;background:#1e3a8a;display:flex;align-items:center;justify-content:space-between">
        <div style="background:#fff;border-radius:4px;padding:2px 5px;display:inline-flex;align-items:center">
            <img src="/public/vgk4u-logo.png" alt="VGK4U" style="height:18px;object-fit:contain"
                 onerror="this.outerHTML='<span style=\'font-size:12px;font-weight:900;color:#1e1b4b\'>VGK<span style=\'color:#f97316\'>4</span>U</span>'">
        </div>
        <div style="display:flex;align-items:center;gap:4px;font-size:9px;font-weight:700;color:#fff">
            ${_si('globe','8px','#fff')}
            <span>www.vgk4u.com</span>
        </div>
        <div style="background:#fff;border-radius:4px;padding:2px 5px;display:inline-flex;align-items:center">
            <img src="/public/hub/Assets/Myntreal.logo.png" alt="MyntReal" style="height:22px;object-fit:contain"
                 onerror="this.outerHTML='<span style=\'font-size:9px;font-weight:800;color:#059669\'>MyntReal</span>'">
        </div>
    </div>
</div>`;
    }

    /* ── Visiting Card BACK ──────────────────────────────────────────────── */
    function _vcardBackHtml(cd) {
        const vgkId        = _e(cd.partner_code || '—');
        const designation  = _e(cd.designation_label || 'Channel Partner');
        const phoneDisplay = _e(_fmtPhone(cd.phone));

        return `<div id="vcardBack" style="width:340px;height:194px;border-radius:10px;overflow:hidden;box-shadow:0 3px 14px rgba(0,0,0,.15);font-family:'Segoe UI',sans-serif;display:flex;flex-direction:column">
    <div style="flex:1;display:flex;min-height:0">
        <div style="width:212px;flex-shrink:0;background:linear-gradient(135deg,#f0f7ff 0%,#e0eef9 100%);padding:10px 12px 8px;display:flex;flex-direction:column;justify-content:space-between">
            <div>
                <img src="/public/vgk4u-logo.png" alt="VGK4U" style="height:46px;object-fit:contain;display:block;margin-bottom:2px"
                     onerror="this.outerHTML='<div style=\'font-size:30px;font-weight:900;letter-spacing:-1px;line-height:1;color:#1e3a8a\'>VGK<span style=\'color:#f97316\'>4</span>U</div>'">
                <div style="font-size:6px;color:#374151;font-style:italic;font-weight:600;margin-bottom:7px;letter-spacing:.02em">Innovating for a Better Tomorrow</div>
                <div style="display:inline-block;border:1.5px solid #1d4ed8;border-radius:4px;padding:3px 8px">
                    <div style="font-size:6.5px;font-weight:900;color:#1d4ed8;letter-spacing:.08em;white-space:nowrap">${designation.toUpperCase()}</div>
                </div>
            </div>
            <div style="display:flex;gap:6px">
                <div style="text-align:center">
                    <div style="width:34px;height:34px;background:linear-gradient(135deg,#fef3c7,#fde68a);border:1.5px solid #f59e0b;border-radius:8px;display:flex;align-items:center;justify-content:center;margin:0 auto 2px;position:relative;overflow:hidden">
                        ${_si('solar','13px','#d97706','position:relative;z-index:1')}
                        ${_si('sun','7px','#fbbf24','position:absolute;top:3px;right:3px')}
                    </div>
                    <div style="font-size:5.5px;font-weight:800;color:#333;letter-spacing:.03em;white-space:nowrap">SOLAR</div>
                </div>
                <div style="text-align:center">
                    <div style="width:34px;height:34px;background:linear-gradient(135deg,#d1fae5,#a7f3d0);border:1.5px solid #10b981;border-radius:8px;display:flex;align-items:center;justify-content:center;margin:0 auto 2px;position:relative;overflow:hidden">
                        ${_si('scooter','12px','#059669','position:relative;z-index:1')}
                        ${_si('bolt','7px','#34d399','position:absolute;top:3px;right:3px')}
                    </div>
                    <div style="font-size:5.5px;font-weight:800;color:#333;letter-spacing:.03em;white-space:nowrap">EV SOLUTIONS</div>
                </div>
                <div style="text-align:center">
                    <div style="width:34px;height:34px;background:linear-gradient(135deg,#dbeafe,#bfdbfe);border:1.5px solid #3b82f6;border-radius:8px;display:flex;align-items:center;justify-content:center;margin:0 auto 2px;position:relative">
                        ${_si('shield','14px','#1d4ed8')}
                        ${_si('check','6px','#fff','position:absolute;top:50%;left:50%;transform:translate(-50%,-50%)')}
                    </div>
                    <div style="font-size:5.5px;font-weight:800;color:#333;letter-spacing:.03em;white-space:nowrap">INSURANCE</div>
                </div>
                <div style="text-align:center">
                    <div style="width:34px;height:34px;background:linear-gradient(135deg,#fee2e2,#fecaca);border:1.5px solid #f43f5e;border-radius:8px;display:flex;align-items:center;justify-content:center;margin:0 auto 2px">
                        ${_si('home','14px','#e11d48')}
                    </div>
                    <div style="font-size:5.5px;font-weight:800;color:#333;letter-spacing:.03em;white-space:nowrap">REAL ESTATE</div>
                </div>
            </div>
        </div>
        <div style="flex:1;background:linear-gradient(135deg,#e0f2fe 0%,#bae6fd 100%);border-left:3px solid #0ea5e9;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:7px;padding:12px 10px">
            <img src="/public/hub/Assets/Myntreal.logo.png" alt="MyntReal" style="height:36px;object-fit:contain"
                 onerror="this.outerHTML='<div style=\'font-size:10px;font-weight:900;color:#0c4a6e;text-align:center;letter-spacing:.06em\'>MYNTREAL</div>'">
            <div style="width:52px;height:1.5px;background:linear-gradient(90deg,transparent,#0ea5e9,transparent)"></div>
            <div style="font-size:6.5px;font-weight:800;color:#0ea5e9;text-align:center;letter-spacing:.09em">Redefining Future</div>
        </div>
    </div>
    <div style="background:#1e3a8a;padding:5px 12px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0">
        <div style="display:flex;align-items:center;gap:5px">
            ${_si('badge','9px','#fbbf24')}
            <span style="font-size:9px;color:#fbbf24;font-weight:800">${vgkId}</span>
        </div>
        <div style="display:flex;align-items:center;gap:5px">
            ${_si('phone','9px','#93c5fd')}
            <span style="font-size:9.5px;color:#fff;font-weight:700">${phoneDisplay}</span>
        </div>
        <div style="display:flex;align-items:center;gap:5px">
            ${_si('globe','9px','#93c5fd')}
            <span style="font-size:9.5px;color:#fff">www.vgk4u.com</span>
        </div>
    </div>
</div>`;
    }

    /* ── ID Card (canonical) ─────────────────────────────────────────────── */
    function _idcardHtml(cd) {
        const name  = _e(cd.display_name || '—');
        const vgkId        = _e(cd.partner_code || '—');
        const bg           = _e(cd.blood_group || '');
        const qrSrc        = cd.qr_b64 || '';
        const title        = (cd.name_title || '').toLowerCase().trim();
        const phoneFormatted = _fmtPhone(cd.phone);
        const isFemale = ['ms','ms.','mrs','mrs.','miss','miss.'].includes(title);
        const avatarSvg = isFemale
            ? `<svg viewBox='0 0 100 120' xmlns='http://www.w3.org/2000/svg' width='100%' height='100%'><rect width='100' height='120' fill='#eef2ff'/><circle cx='50' cy='38' r='22' fill='#818cf8'/><path d='M10 120 Q10 80 50 80 Q90 80 90 120Z' fill='#818cf8'/></svg>`
            : `<svg viewBox='0 0 100 120' xmlns='http://www.w3.org/2000/svg' width='100%' height='100%'><rect width='100' height='120' fill='#dbeafe'/><circle cx='50' cy='38' r='22' fill='#1d4ed8'/><path d='M10 120 Q10 80 50 80 Q90 80 90 120Z' fill='#1d4ed8'/></svg>`;
        const photoUrl = cd.passport_photo_url || '';
        const avatarContent = photoUrl
            ? `<img src="${photoUrl}" alt="Photo" style="width:100%;height:100%;object-fit:cover;object-position:center top;display:block" onerror="this.outerHTML='${avatarSvg}'">`
            : avatarSvg;

        return `<div style="display:flex;justify-content:center;margin-bottom:-1px">
    <div style="width:36px;height:12px;background:#c0c0c0;border-radius:4px 4px 0 0;border:1.5px solid #aaa;border-bottom:none"></div>
</div>
<div id="idcardFront" style="background:#fff;border:3px solid #1d4ed8;border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(29,78,216,.18);display:flex;flex-direction:column;min-height:419px;width:258px;font-family:'Segoe UI',Arial,sans-serif">
    <div style="background:linear-gradient(90deg,#1a3fa8,#2563eb,#1a3fa8);height:10px;flex-shrink:0"></div>
    <div style="height:3px;background:linear-gradient(90deg,#d97706,#fbbf24,#d97706);flex-shrink:0"></div>
    <div style="padding:10px 14px 6px;text-align:center;flex-shrink:0">
        <img src="/public/vgk4u-logo.png" alt="VGK4U" style="height:38px;object-fit:contain;display:block;margin:0 auto">
    </div>
    <div style="height:3px;background:linear-gradient(90deg,#d97706,#fbbf24,#d97706);flex-shrink:0"></div>
    <div style="display:flex;flex-direction:column;padding:12px 12px 8px;flex:1;justify-content:space-between">
        <div style="display:flex;gap:10px;align-items:flex-start">
            <div style="flex-shrink:0;width:80px;height:100px;border:2.5px solid #1d4ed8;border-radius:8px;overflow:hidden;background:#dbeafe">${avatarContent}</div>
            <div style="flex:1;min-width:0;padding-top:2px">
                <div style="font-size:11px;font-weight:800;color:#d97706;letter-spacing:.04em;margin-bottom:2px">VGK ID</div>
                <div style="display:inline-block;background:#1d4ed8;color:#fff;font-size:10.5px;font-weight:900;padding:2px 10px;border-radius:5px;margin-bottom:6px">${vgkId}</div>
                <div data-vgk-name="${name}" style="font-size:12px;font-weight:900;color:#111;line-height:1.2;margin-bottom:3px;white-space:nowrap;overflow:visible">${name}</div>
                <div style="font-size:9px;color:#6b7280;font-style:italic">~\u00b7~ Channel Partner</div>
            </div>
        </div>
        <div style="display:flex;gap:10px;justify-content:center;padding-top:8px">
            <div style="text-align:center">
                <div style="width:44px;height:44px;background:linear-gradient(135deg,#fef3c7,#fde68a);border:1.5px solid #f59e0b;border-radius:9px;display:flex;align-items:center;justify-content:center;margin:0 auto 3px;position:relative;overflow:hidden">
                    ${_si('solar','16px','#d97706','position:relative;z-index:1')}
                    ${_si('sun','8px','#fbbf24','position:absolute;top:3px;right:3px')}
                </div>
                <div style="font-size:6px;font-weight:800;color:#444;letter-spacing:.03em;white-space:nowrap">SOLAR</div>
            </div>
            <div style="text-align:center">
                <div style="width:44px;height:44px;background:linear-gradient(135deg,#d1fae5,#a7f3d0);border:1.5px solid #10b981;border-radius:9px;display:flex;align-items:center;justify-content:center;margin:0 auto 3px;position:relative;overflow:hidden">
                    ${_si('scooter','16px','#059669','position:relative;z-index:1')}
                    ${_si('bolt','8px','#34d399','position:absolute;top:3px;right:3px')}
                </div>
                <div style="font-size:6px;font-weight:800;color:#444;letter-spacing:.03em;white-space:nowrap">EV SOLUTIONS</div>
            </div>
            <div style="text-align:center">
                <div style="width:44px;height:44px;background:linear-gradient(135deg,#dbeafe,#bfdbfe);border:1.5px solid #3b82f6;border-radius:9px;display:flex;align-items:center;justify-content:center;margin:0 auto 3px;position:relative">
                    ${_si('shield','18px','#1d4ed8')}
                    ${_si('check','7px','#fff','position:absolute;top:50%;left:50%;transform:translate(-50%,-50%)')}
                </div>
                <div style="font-size:6px;font-weight:800;color:#444;letter-spacing:.03em;white-space:nowrap">INSURANCE</div>
            </div>
            <div style="text-align:center">
                <div style="width:44px;height:44px;background:linear-gradient(135deg,#fee2e2,#fecaca);border:1.5px solid #f43f5e;border-radius:9px;display:flex;align-items:center;justify-content:center;margin:0 auto 3px">
                    ${_si('home','18px','#e11d48')}
                </div>
                <div style="font-size:6px;font-weight:800;color:#444;letter-spacing:.03em;white-space:nowrap">REAL ESTATE</div>
            </div>
        </div>
    </div>
    <div style="display:flex;align-items:flex-end;justify-content:space-between;padding:8px 12px 10px;border-top:1px solid #e5e7eb;flex-shrink:0">
        <div style="flex:1">
            <div style="display:flex;align-items:center;gap:5px;margin-bottom:5px">
                <span style="font-size:13px">&#127470;&#127475;</span>
                <span style="font-size:10.5px;font-weight:700;color:#1f2937">${bg ? bg + ' (Blood Group)' : '\u2014 (Blood Group)'}</span>
            </div>
            ${phoneFormatted ? `<div style="font-size:10.5px;font-weight:700;color:#1f2937;white-space:nowrap">${_e(phoneFormatted)}</div>` : ''}
            <div style="font-size:9.5px;font-weight:600;color:#6b7280;margin-top:3px;white-space:nowrap">+91 858585 2738</div>
        </div>
        ${qrSrc ? `<div style="flex-shrink:0;margin-left:10px"><img src="${qrSrc}" style="width:70px;height:70px;display:block;border:1px solid #e5e7eb;border-radius:4px" alt="QR"><div style="font-size:6px;color:#6b7280;font-weight:700;margin-top:2px;text-align:center">SCAN TO JOIN</div></div>` : ''}
    </div>
    <div style="background:linear-gradient(90deg,#1a3fa8,#2563eb,#1a3fa8);padding:6px;text-align:center;flex-shrink:0">
        <div style="color:#fff;font-size:10px;font-weight:700;letter-spacing:.1em">www.vgk4u.com</div>
    </div>
    <div style="background:#fff;padding:4px 12px;text-align:center;border-top:1px solid #e5e7eb;flex-shrink:0">
        <div style="font-size:7.5px;color:#374151">Independent Channel Partner empowered to represent VGK4U offerings</div>
    </div>
</div>`;
    }

    /* Auth headers for fetching protected storage URLs (set via VgkCard.setFetchHeaders). */
    var _fetchHeaders = {};

    /* ── dom-to-image-more loader ─────────────────────────────────────────── */
    /* [DC-DTIM-LOCAL-001] Load from local path first (served by frontend server),
       fall back to CDN if local fails. Prevents download errors when CDN is slow. */
    async function _loadDomToImage() {
        if (window.domtoimage) return;
        /* Try local copy first */
        await new Promise(function(res, rej) {
            var s = document.createElement('script');
            s.src = '/public/js/dom-to-image-more.min.js';
            s.onload = res;
            s.onerror = function() {
                /* Local failed — fall back to CDN */
                var s2 = document.createElement('script');
                s2.src = 'https://cdn.jsdelivr.net/npm/dom-to-image-more@3.4.0/dist/dom-to-image-more.min.js';
                s2.onload = res; s2.onerror = rej;
                document.head.appendChild(s2);
            };
            document.head.appendChild(s);
        });
    }

    /* Pre-fetches ALL images as data URLs and patches them into the clone so
       dom-to-image-more never needs to re-fetch them cross-origin.
       [DC-PATCH-LOGOS-003] Handles relative paths, absolute same-origin paths,
       http/https URLs (with stored auth headers), and data: URIs (re-encoded
       via canvas to fix dom-to-image-more large-data-URL rendering bug).      */
    async function _patchLogos(clone) {
        var imgs = Array.from(clone.querySelectorAll('img[src]'));
        var origin = window.location.origin;
        await Promise.all(imgs.map(function(img) {
            var src = img.getAttribute('src') || '';
            if (!src) return Promise.resolve();

            /* [DC-QR-CANVAS-001] Data URLs (e.g. QR code base64) — re-encode through
               canvas so dom-to-image-more gets a freshly decoded image, not a raw
               base64 string that can silently fail to render in the captured PNG. */
            if (src.startsWith('data:')) {
                return new Promise(function(res) {
                    var tmp = new Image();
                    tmp.onload = function() {
                        try {
                            var c = document.createElement('canvas');
                            c.width  = tmp.naturalWidth  || 100;
                            c.height = tmp.naturalHeight || 100;
                            c.getContext('2d').drawImage(tmp, 0, 0);
                            img.src = c.toDataURL('image/png');
                        } catch(e) { /* keep original on error */ }
                        res();
                    };
                    tmp.onerror = res;
                    tmp.src = src;
                });
            }

            /* Build an absolute URL so fetch always works regardless of base */
            var absUrl = src.startsWith('http') ? src
                       : src.startsWith('//') ? (window.location.protocol + src)
                       : origin + (src.startsWith('/') ? src : '/' + src);

            /* [DC-AUTH-FETCH-001] Use stored auth headers for protected /storage/ URLs
               (JWT bearer token). Falls back to same-origin credentials otherwise. */
            var fetchOpts = { credentials: 'same-origin' };
            if (_fetchHeaders && _fetchHeaders['Authorization']) {
                fetchOpts.headers = { 'Authorization': _fetchHeaders['Authorization'] };
            }

            return fetch(absUrl, fetchOpts)
                .then(function(r) { return r.ok ? r.blob() : null; })
                .then(function(blob) {
                    if (!blob) return;
                    return new Promise(function(res) {
                        var reader = new FileReader();
                        reader.onloadend = function() { img.src = reader.result; res(); };
                        reader.onerror   = res;
                        reader.readAsDataURL(blob);
                    });
                })
                .catch(function() {});
        }));
    }

    /* Waits for every <img> in the clone to either load or error out, so
       dom-to-image-more sees fully resolved images (no blank placeholders). */
    function _waitForImages(clone) {
        var imgs = Array.from(clone.querySelectorAll('img'));
        var promises = imgs.map(function(img) {
            if (img.complete) return Promise.resolve();
            return new Promise(function(res) {
                img.addEventListener('load',  res, { once: true });
                img.addEventListener('error', res, { once: true });
                setTimeout(res, 3000); /* safety timeout per image */
            });
        });
        return Promise.all(promises);
    }

    /* ── Canvas capture (shared by download) ─────────────────────────────── */
    async function captureCanvas(el, bgColor) {
        await _loadDomToImage();

        var SCALE = 4;

        var clone = el.cloneNode(true);
        clone.style.position      = 'fixed';
        clone.style.left          = '-9999px';
        clone.style.top           = '0';
        clone.style.zIndex        = '-9999';
        clone.style.pointerEvents = 'none';
        clone.style.visibility    = 'visible';
        clone.style.opacity       = '1';
        document.body.appendChild(clone);

        /* [DC-NAME-FIT-001] Apply name fitting to clone so the captured image
           reflects the exact layout seen on screen (names already fitted on live DOM,
           but clone must be re-fitted since scrollWidth/offsetWidth re-evaluate). */
        _fitAllNames(clone);

        var dataUrl;
        try {
            /* Wait for images already in the browser's load queue to settle
               before patching so onerror replacements are also captured.   */
            await _waitForImages(clone);
            await _patchLogos(clone);
            await document.fonts.ready;

            var naturalW = clone.offsetWidth  || 360;
            var naturalH = clone.offsetHeight || 194;

            dataUrl = await domtoimage.toPng(clone, {
                bgcolor : bgColor !== undefined ? bgColor : '#ffffff',
                width   : naturalW,
                height  : naturalH,
                scale   : SCALE
            });
        } finally {
            document.body.removeChild(clone);
        }

        var img = new Image();
        /* DC Protocol Fix (Apr 2026): img.onerror = rej prevents silent promise hang if dataUrl is malformed */
        await new Promise(function(res, rej) { img.onload = res; img.onerror = rej; img.src = dataUrl; });
        var canvas = document.createElement('canvas');
        canvas.width  = img.width;
        canvas.height = img.height;
        var ctx = canvas.getContext('2d');
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(img, 0, 0);
        return canvas;
    }

    /* ── Public download function ────────────────────────────────────────── */
    async function downloadCard(elId, filename) {
        var el = typeof elId === 'string' ? document.getElementById(elId) : elId;
        if (!el) return;
        try {
            var canvas = await captureCanvas(el, '#ffffff');
            var a = document.createElement('a');
            a.href = canvas.toDataURL('image/png');
            a.download = 'VGK4U_' + filename + '.png';
            a.click();
        } catch(e) { console.error('Card download error:', e); alert('Download failed. Please try again.'); }
    }

    /* ── Public API ──────────────────────────────────────────────────────── */
    global.VgkCard = {
        /** Returns HTML string: visiting card front + back (no wrapper, no buttons) */
        vcardHtml: function(cd) {
            return _vcardFrontHtml(cd) + '\n' + _vcardBackHtml(cd);
        },
        /** Returns HTML string: ID card inner content (clip + idcardFront div, no wrapper, no buttons) */
        idcardHtml: _idcardHtml,

        /** [DC-AUTH-FETCH-001] Store auth headers so _patchLogos can fetch protected
            /storage/ images with a JWT token during card download. Call this once on
            page load after the auth token is available. */
        setFetchHeaders: function(h) { _fetchHeaders = h || {}; },

        /** Renders visiting card into containerId element */
        renderVcard: function(cd, containerId) {
            const el = typeof containerId === 'string'
                ? document.getElementById(containerId)
                : containerId;
            if (!el || !cd) return;
            el.innerHTML = '<div id="vcardInnerWrap" data-download-width="360" style="width:360px;margin:0 auto;display:flex;flex-direction:column;gap:10px;background:linear-gradient(135deg,#dbeafe 0%,#bfdbfe 60%,#e0f2fe 100%);padding:10px;border-radius:14px">'
                + _vcardFrontHtml(cd) + '\n' + _vcardBackHtml(cd)
                + '</div>';
            /* [DC-NAME-FIT-001] Fit names after DOM is ready */
            requestAnimationFrame(function() { _fitAllNames(el); });
        },

        /** Renders ID card into containerId element */
        renderIdCard: function(cd, containerId) {
            const el = typeof containerId === 'string'
                ? document.getElementById(containerId)
                : containerId;
            if (!el || !cd) return;
            el.innerHTML = '<div style="width:264px;margin:0 auto;font-family:\'Segoe UI\',Arial,sans-serif">'
                + _idcardHtml(cd)
                + '</div>';
            /* [DC-NAME-FIT-001] Fit names after DOM is ready */
            requestAnimationFrame(function() { _fitAllNames(el); });
        },

        /** Captures an element as a high-res canvas (scale:4). Returns Promise<HTMLCanvasElement>. */
        captureCanvas: captureCanvas,

        /** Downloads a card element as a PNG. elId can be a string ID or element. */
        downloadCard: downloadCard
    };

}(window));
