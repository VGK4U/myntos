/**
 * Self-Hosted WhatsApp Web Group Bot Gateway (Baileys)
 * Listens on port 5002.
 * Posts messages to WhatsApp Group (e.g. LfX8mGootXa7SpwNIz7P5C).
 */

const express = require('express');
const cors = require('cors');
const qrcodeTerminal = require('qrcode-terminal');
const pino = require('pino');
const path = require('path');
const fs = require('fs');

const {
    default: makeWASocket,
    useMultiFileAuthState,
    DisconnectReason,
    fetchLatestBaileysVersion,
    Browsers
} = require('@whiskeysockets/baileys');

const app = express();
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: true }));

const PORT = process.env.PORT || 5002;
const AUTH_DIR = path.join(__dirname, 'auth_info');
const DEFAULT_INVITE_CODE = "120363410784518818@g.us";

let sock = null;
let currentQr = null;
let connectionStatus = 'disconnected';
let targetJid = null;
let clientGen = 0;
let skipRestoreOnce = false;

// Prevent process exit on background Baileys socket disconnection (1006 / connection reset)
process.on('unhandledRejection', (reason, promise) => {
    console.log('⚠️ Process captured unhandledRejection (socket reset/reconnect):', reason?.message || reason);
});
const BACKEND_API_BASE = process.env.BACKEND_API_URL || 'http://127.0.0.1:8000';

// ── S3 Cloud Session Sync Functions (Zero PostgreSQL Contention) ─────────────
async function restoreSessionFromDatabase() {
    if (skipRestoreOnce) {
        console.log(`[S3-SESSION-SYNC] ℹ️ Skipping session restore (flagged fresh start after terminal logout).`);
        skipRestoreOnce = false;
        return false;
    }
    try {
        const resp = await fetch(`${BACKEND_API_BASE}/api/v1/whatsapp/bot-session-restore?session_id=default_baileys`);
        if (resp.ok) {
            const data = await resp.json();
            if (data.success && data.files && Object.keys(data.files).length > 0) {
                if (!fs.existsSync(AUTH_DIR)) fs.mkdirSync(AUTH_DIR, { recursive: true });
                for (const [fileKey, fileData] of Object.entries(data.files)) {
                    const filePath = path.join(AUTH_DIR, fileKey);
                    fs.writeFileSync(filePath, fileData, 'utf8');
                }
                console.log(`[S3-SESSION-SYNC] ✅ Restored ${Object.keys(data.files).length} WhatsApp session files from S3 (${data.source || 's3'})!`);
                return true;
            }
        }
    } catch (err) {
        console.log(`[S3-SESSION-SYNC] ℹ️ Session restore check: ${err.message}`);
    }
    return false;
}

async function purgeS3Session() {
    try {
        const resp = await fetch(`${BACKEND_API_BASE}/api/v1/whatsapp/bot-session-clear?session_id=default_baileys`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        if (resp.ok) {
            console.log(`[S3-SESSION-SYNC] 🧹 Purged dead session from S3 durable storage.`);
        }
    } catch (err) {
        console.log(`[S3-SESSION-SYNC] ⚠️ Note on S3 purge: ${err.message}`);
    }
}

let isBackingUp = false;
let hasPendingChanges = false;
let backupDebounceTimer = null;

async function backupSessionToDatabase() {
    if (isBackingUp) {
        hasPendingChanges = true;
        return;
    }
    isBackingUp = true;
    hasPendingChanges = false;
    try {
        if (!fs.existsSync(AUTH_DIR)) return;
        const fileNames = fs.readdirSync(AUTH_DIR);
        if (!fileNames || fileNames.length === 0) return;

        const files = {};
        for (const f of fileNames) {
            const fPath = path.join(AUTH_DIR, f);
            if (fs.statSync(fPath).isFile()) {
                files[f] = fs.readFileSync(fPath, 'utf8');
            }
        }

        if (Object.keys(files).length === 0) return;

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000);

        const resp = await fetch(`${BACKEND_API_BASE}/api/v1/whatsapp/bot-session-backup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: 'default_baileys',
                files: files
            }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (resp.ok) {
            const data = await resp.json();
            if (data.success) {
                console.log(`[S3-SESSION-SYNC] 💾 Synced ${Object.keys(files).length} session files to S3 durable storage.`);
            }
        }
    } catch (err) {
        console.log(`[S3-SESSION-SYNC] ⚠️ Backup error: ${err.message}`);
    } finally {
        isBackingUp = false;
        if (hasPendingChanges) {
            hasPendingChanges = false;
            scheduleDebouncedBackup();
        }
    }
}

function scheduleDebouncedBackup() {
    if (isBackingUp) {
        hasPendingChanges = true;
    }
    if (backupDebounceTimer) clearTimeout(backupDebounceTimer);
    backupDebounceTimer = setTimeout(() => {
        backupDebounceTimer = null;
        backupSessionToDatabase();
    }, 3000);
}

let backupIntervalStarted = false;

async function startWhatsAppBot() {
    clientGen += 1;
    const thisGen = clientGen;
    console.log(`[WA-LIFECYCLE] 🚀 Initializing WhatsApp Socket (Generation ID: ${thisGen})...`);

    if (!fs.existsSync(AUTH_DIR)) {
        fs.mkdirSync(AUTH_DIR, { recursive: true });
    }

    // Attempt restoring session from RDS/S3 database before loading auth state
    if (!fs.existsSync(path.join(AUTH_DIR, 'creds.json'))) {
        await restoreSessionFromDatabase();
    }

    if (sock) {
        try {
            sock.ev.removeAllListeners();
            sock.ws?.close();
        } catch (e) {}
    }

    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
    const { version } = await fetchLatestBaileysVersion();

    sock = makeWASocket({
        version,
        auth: state,
        logger: pino({ level: 'silent' }),
        printQRInTerminal: false,
        browser: ['MyntOS Group Dispatcher', 'Chrome', '1.0.0'],
        syncFullHistory: false,
        connectTimeoutMs: 60000,
        qrTimeout: 180000,
        keepAliveIntervalMs: 30000,
        emitOwnEvents: false
    });

    let backupDebounceTimer = null;
    sock.ev.on('creds.update', async () => {
        if (thisGen !== clientGen) return; // Stale client guard
        await saveCreds();
        scheduleDebouncedBackup();
    });

    // Schedule background DB backup every 300 seconds (singleton)
    if (!backupIntervalStarted) {
        backupIntervalStarted = true;
        setInterval(backupSessionToDatabase, 300000);
    }

    sock.ev.on('connection.update', async (update) => {
        await processConnectionUpdate(thisGen, update);
    });
}

async function processConnectionUpdate(thisGen, update) {
    if (thisGen !== clientGen) {
        console.log(`[WA-LIFECYCLE] 🛡️ Ignored event from obsolete Client Generation ${thisGen} (Current: ${clientGen})`);
        return { dropped: true, gen: thisGen, currentGen: clientGen };
    }

    const { connection, lastDisconnect, qr } = update;

    if (qr) {
        currentQr = qr;
        connectionStatus = 'qr_ready';
        console.log("\n==================================================");
        console.log(`📲 SCAN THIS QR CODE WITH YOUR WHATSAPP PHONE (Gen ${thisGen}):`);
        console.log("==================================================");
        qrcodeTerminal.generate(qr, { small: true });
        console.log(`\nAlternatively, open: http://localhost:${PORT}/qr in browser.\n`);
    }

    if (connection === 'open') {
        connectionStatus = 'connected';
        currentQr = null;
        console.log(`✅ [WA-LIFECYCLE] WHATSAPP CONNECTED (Gen ${thisGen})! Session is active and authoritative.`);
        await backupSessionToDatabase();

        // If DEFAULT_INVITE_CODE is already a Group JID (ends with @g.us or contains @), assign directly
        if (DEFAULT_INVITE_CODE && (DEFAULT_INVITE_CODE.includes('@g.us') || DEFAULT_INVITE_CODE.includes('@'))) {
            targetJid = DEFAULT_INVITE_CODE;
            console.log(`📌 Using Direct Target Group JID: ${targetJid}`);
        } else if (DEFAULT_INVITE_CODE && sock) {
            try {
                const groupInfo = await sock.groupGetInviteInfo(DEFAULT_INVITE_CODE);
                if (groupInfo && groupInfo.id) {
                    targetJid = groupInfo.id.includes('@g.us') ? groupInfo.id : `${groupInfo.id}@g.us`;
                    console.log(`📌 Resolved Target Group JID: ${targetJid} (${groupInfo.subject || 'Sales Group'})`);
                }
            } catch (err) {
                console.log(`ℹ️ Group invite lookup note: ${err.message}`);
            }
        }
    }

    if (connection === 'close') {
        const errDetail = lastDisconnect?.error?.message || lastDisconnect?.error;
        const statusCode = lastDisconnect?.error?.output?.statusCode || lastDisconnect?.error?.statusCode;
        
        // Only consider genuinely logged out if explicit 401 DisconnectReason.loggedOut is received
        const isLoggedOut = statusCode === DisconnectReason.loggedOut || statusCode === 401;
        
        if (isLoggedOut) {
            connectionStatus = 'qr_ready';
            currentQr = null;
            console.log(`🧹 [WA-LIFECYCLE] Terminal logout confirmed (Status: ${statusCode}, Gen: ${thisGen}). Purging dead session and preparing fresh QR...`);
            skipRestoreOnce = true;
            await purgeS3Session();
            try {
                if (fs.existsSync(AUTH_DIR)) {
                    fs.rmSync(AUTH_DIR, { recursive: true, force: true });
                }
            } catch (e) {
                console.error("Error clearing auth_info:", e.message);
            }
            setTimeout(() => {
                if (thisGen === clientGen) startWhatsAppBot();
            }, 2000);
        } else {
            // Transient disconnect (428 connectionClosed, 408 timedOut, 515 restartRequired, 503 unavailableService, ECONNRESET, etc.)
            // ALWAYS preserve AUTH_DIR so Baileys re-reads saved creds.json and auto-reconnects seamlessly without re-scanning QR.
            connectionStatus = 'reconnecting';
            console.log(`⚠️ [WA-LIFECYCLE] Temporary socket reset (Status: ${statusCode || 'unknown'}, Reason: ${errDetail || 'Connection lost'}). Preserving session credentials and auto-reconnecting in 3s...`);
            setTimeout(() => {
                if (thisGen === clientGen) startWhatsAppBot();
            }, 3000);
        }
    }
    return { dropped: false, status: connectionStatus };
}

// ── API ENDPOINTS ─────────────────────────────────────────────────────────────

async function logoutBotSession() {
    try {
        console.log("🚪 Logging out WhatsApp Bot session...");
        connectionStatus = 'logging_out';
        if (sock) {
            try {
                await sock.logout();
            } catch (e) {
                try { sock.end(new Error('Logout requested')); } catch (e2) {}
            }
            sock = null;
        }
        currentQr = null;
        targetJid = null;

        skipRestoreOnce = true;
        await purgeS3Session();

        if (fs.existsSync(AUTH_DIR)) {
            fs.rmSync(AUTH_DIR, { recursive: true, force: true });
            console.log("✅ Cleared auth_info session directory.");
        }

        connectionStatus = 'disconnected';
        setTimeout(startWhatsAppBot, 1000);
        return { success: true, message: "Logged out and reset session successfully." };
    } catch (err) {
        console.error("❌ Logout error:", err);
        return { success: false, error: err.message || String(err) };
    }
}

app.all(['/logout', '/api/logout'], async (req, res) => {
    const result = await logoutBotSession();
    if (req.headers.accept && req.headers.accept.includes('text/html')) {
        return res.send(`
            <!DOCTYPE html>
            <html>
            <head><title>Logging out...</title><meta http-equiv="refresh" content="2;url=/qr"></head>
            <body style="font-family: system-ui, sans-serif; text-align: center; padding: 60px 15px; background: #f4f6f9;">
                <h2 style="color: #ef4444;">🚪 WhatsApp Bot Logged Out</h2>
                <p style="color: #64748b;">Session cleared. Redirecting to QR code scanner...</p>
                <a href="/qr" style="color: #3b82f6; font-weight: bold; text-decoration: none;">Click here if not redirected automatically</a>
            </body>
            </html>
        `);
    }
    return res.json(result);
});

app.get('/status', (req, res) => {
    return res.json({
        status: connectionStatus,
        connection_state: connectionStatus,
        can_send_now: connectionStatus === 'connected',
        qr_available: !!currentQr && (connectionStatus === 'qr_ready' || connectionStatus === 'disconnected'),
        generation_id: clientGen,
        target_jid: targetJid,
        invite_code: DEFAULT_INVITE_CODE,
        timestamp: Date.now()
    });
});

app.get('/qr-data', (req, res) => {
    return res.json({
        status: connectionStatus,
        connection_state: connectionStatus,
        can_send_now: connectionStatus === 'connected',
        qr: currentQr,
        qr_url: currentQr ? `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(currentQr)}` : null,
        qr_available: !!currentQr && (connectionStatus === 'qr_ready' || connectionStatus === 'disconnected'),
        generation_id: clientGen,
        timestamp: Date.now()
    });
});

app.get('/api/groups', async (req, res) => {
    try {
        if (!sock || connectionStatus !== 'connected') {
            return res.status(503).json({ success: false, error: "Not connected" });
        }
        const participating = await sock.groupFetchAllParticipating();
        const groups = Object.values(participating || {}).map(g => ({
            id: g.id,
            subject: g.subject,
            participants_count: g.participants ? g.participants.length : 0,
            announce: g.announce || false // true = only admins can send messages
        }));
        return res.json({ success: true, count: groups.length, groups });
    } catch (e) {
        return res.status(500).json({ success: false, error: e.message });
    }
});

app.get('/qr-data', (req, res) => {
    return res.json({
        status: connectionStatus,
        qr: currentQr,
        qr_url: currentQr ? `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(currentQr)}` : null
    });
});

app.get('/api/list-groups', async (req, res) => {
    if (!sock || connectionStatus !== 'connected') {
        return res.status(503).json({ success: false, error: 'WhatsApp bot not connected' });
    }
    try {
        const participating = await sock.groupFetchAllParticipating();
        const groups = Object.values(participating || {}).map(g => ({
            id: g.id,
            subject: g.subject,
            participants_count: g.participants ? g.participants.length : 0
        }));
        return res.json({ success: true, count: groups.length, groups });
    } catch (e) {
        return res.status(500).json({ success: false, error: e.message });
    }
});

app.get('/qr', (req, res) => {
    if (connectionStatus === 'connected') {
        return res.send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>WhatsApp Bot Connected</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="font-family: system-ui, -apple-system, sans-serif; text-align: center; padding: 50px 15px; background: #f4f6f9; color: #1e293b;">
                <div style="background: white; max-width: 480px; margin: 0 auto; padding: 36px 24px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
                    <h1 style="color: #10b981; font-size: 56px; margin: 0 0 12px 0;">✅</h1>
                    <h2 style="color: #065f46; margin: 0 0 8px 0; font-size: 22px; font-weight: 800;">WhatsApp Web Bot is CONNECTED & ACTIVE!</h2>
                    <p style="color: #64748b; font-size: 13.5px; margin-bottom: 24px;">Target JID: <code style="background: #f1f5f9; padding: 3px 8px; border-radius: 6px; font-weight: 600; color: #0f172a;">${targetJid || '120363410784518818@g.us'}</code></p>
                    
                    <div style="border-top: 1px solid #e2e8f0; margin-top: 24px; padding-top: 24px;">
                        <button id="logoutBtn" onclick="doLogout()" style="background: #ef4444; color: white; border: none; padding: 12px 24px; border-radius: 12px; font-weight: 700; font-size: 14px; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; box-shadow: 0 4px 14px rgba(239, 68, 68, 0.3); transition: all 0.2s;" onmouseover="this.style.background='#dc2626'" onmouseout="this.style.background='#ef4444'">
                            🚪 Logout & Disconnect WhatsApp Bot
                        </button>
                    </div>
                    <p id="logoutMsg" style="margin-top: 16px; font-size: 13px; font-weight: 600; color: #64748b; display: none;"></p>
                </div>

                <script>
                    async function doLogout() {
                        if (!confirm("Are you sure you want to log out and disconnect the WhatsApp Web Bot session? You will need to scan the QR code again.")) return;
                        const btn = document.getElementById('logoutBtn');
                        const msg = document.getElementById('logoutMsg');
                        btn.disabled = true;
                        btn.style.opacity = '0.6';
                        msg.style.display = 'block';
                        msg.style.color = '#ef4444';
                        msg.textContent = '⏳ Logging out and resetting WhatsApp session...';
                        try {
                            const res = await fetch('/api/logout', { method: 'POST' });
                            const data = await res.json();
                            if (data.success) {
                                msg.style.color = '#10b981';
                                msg.textContent = '✅ Logged out successfully! Loading new QR code...';
                                setTimeout(() => { window.location.href = '/qr'; }, 1200);
                            } else {
                                msg.textContent = '❌ Logout error: ' + (data.error || 'Failed');
                                btn.disabled = false;
                                btn.style.opacity = '1';
                            }
                        } catch (err) {
                            msg.textContent = '❌ Logout error: ' + err.message;
                            btn.disabled = false;
                            btn.style.opacity = '1';
                        }
                    }
                </script>
            </body>
            </html>
        `);
    }
    const initialQrUrl = currentQr ? `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(currentQr)}` : null;
    return res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Scan WhatsApp Group Bot QR (3-Min Window)</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                .timer-pill { background: #e0f2fe; color: #0369a1; padding: 6px 16px; border-radius: 20px; font-weight: 700; font-size: 13.5px; display: inline-flex; align-items: center; gap: 6px; }
            </style>
        </head>
        <body style="font-family: system-ui, -apple-system, sans-serif; text-align: center; padding: 30px 15px; background: #f4f6f9; color: #1e293b;">
            <h2 style="font-size: 22px; margin-bottom: 8px;">📱 Scan QR Code to Link WhatsApp Bot</h2>
            <p style="color: #64748b; font-size: 14px; margin-top: 0; margin-bottom: 12px;">Open WhatsApp on phone ➔ Linked Devices ➔ Link a Device</p>

            <div class="timer-pill" id="timerBadge">
                ⏳ QR Code Extended Window: <span id="timerText" style="font-family: monospace; font-size: 15px;">03:00</span>
            </div>
            
            <div id="qrContainer" style="margin: 20px auto; background: white; display: inline-block; padding: 24px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.08); min-width: 300px; min-height: 300px;">
                ${initialQrUrl 
                    ? `<img id="qrImg" src="${initialQrUrl}" width="300" height="300" style="display:block; border-radius: 8px;" />`
                    : `<div style="padding:100px 20px; font-size: 15px; color: #64748b; font-weight: 600;">⏳ Generating QR Code...<br><span style="font-size:12px; font-weight:400; color:#94a3b8">Will load automatically in a moment.</span></div>`
                }
            </div>
            
            <p id="statusMsg" style="font-size: 13.5px; font-weight: 600; color: #3b82f6;">
                ${initialQrUrl ? '🟢 QR Code Ready — Take your time to scan (3-Minute Window)...' : '⏳ Initializing WhatsApp Socket...'}
            </p>

            <script>
                let secondsLeft = 180;
                let lastQrUrl = '${initialQrUrl || ''}';

                function updateCountdown() {
                    if (secondsLeft > 0) {
                        secondsLeft--;
                        const m = Math.floor(secondsLeft / 60);
                        const s = secondsLeft % 60;
                        document.getElementById('timerText').textContent = 
                            String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
                    }
                }

                async function checkStatus() {
                    try {
                        const res = await fetch('/qr-data');
                        const data = await res.json();
                        if (data.status === 'connected') {
                            window.location.reload();
                        } else if (data.qr_url) {
                            if (data.qr_url !== lastQrUrl) {
                                lastQrUrl = data.qr_url;
                                secondsLeft = 180; // Reset 3-minute timer on fresh QR
                                const container = document.getElementById('qrContainer');
                                if (container) {
                                    container.innerHTML = '<img id="qrImg" src="' + data.qr_url + '" width="300" height="300" style="display:block; border-radius: 8px;" />';
                                }
                            }
                            const msg = document.getElementById('statusMsg');
                            if (msg) msg.textContent = '🟢 QR Code Ready — Take your time to scan (3-Minute Window)...';
                        }
                    } catch (e) {}
                }

                setInterval(checkStatus, 2000);
                setInterval(updateCountdown, 1000);
                checkStatus();
            </script>
        </body>
        </html>
    `);
});

const jidCache = {};

function cleanTargetCode(raw) {
    if (!raw) return '';
    let str = String(raw).trim();
    if (str.includes('whatsapp.com/channel/')) {
        str = str.split('whatsapp.com/channel/')[1].split('?')[0].split('#')[0].replace(/\/$/, '');
    } else if (str.includes('chat.whatsapp.com/')) {
        str = str.split('chat.whatsapp.com/')[1].split('?')[0].split('#')[0].replace(/\/$/, '');
    }
    return str;
}

app.post('/api/send-group-message', async (req, res) => {
    try {
        const { message, inviteCode, groupId, imageUrl, imagePath, media_url, mediaUrl } = req.body;
        const mediaSource = imageUrl || imagePath || media_url || mediaUrl || null;
        if (!message && !mediaSource) {
            return res.status(400).json({ success: false, error: "message or media parameter required" });
        }

        // Graceful wait if socket is actively reconnecting
        if (connectionStatus === 'reconnecting') {
            const startWait = Date.now();
            while (connectionStatus === 'reconnecting' && (Date.now() - startWait) < 4000) {
                await new Promise(r => setTimeout(r, 400));
            }
        }

        if (connectionStatus !== 'connected' || !sock) {
            const err_msg = connectionStatus === 'reconnecting'
                ? "WhatsApp bot is currently reconnecting. Saved credentials are valid — please retry in 5 seconds."
                : "WhatsApp bot not connected. Scan QR code at http://localhost:5002/qr";
            return res.status(503).json({
                success: false,
                error: err_msg,
                status: connectionStatus,
                can_send_now: false
            });
        }

        const codesToUse = req.body.inviteCodes || (req.body.inviteCode ? [req.body.inviteCode] : [DEFAULT_INVITE_CODE]);
        const targetCodes = Array.from(new Set(Array.isArray(codesToUse) ? codesToUse : [codesToUse]));
        
        let sentCount = 0;
        let failedCount = 0;
        const results = [];

        for (const rawCode of targetCodes) {
            const codeToUse = cleanTargetCode(rawCode);
            let destinationJid = groupId;
            let targetType = 'group';

            if (String(rawCode).includes('/channel/') || codeToUse.startsWith('0029') || codeToUse.includes('@newsletter')) {
                targetType = 'channel';
            }

            const { groupName } = req.body;
            if (!destinationJid && groupName) {
                try {
                    const participating = await sock.groupFetchAllParticipating();
                    const matchedGroup = Object.values(participating).find(g =>
                        g.subject && g.subject.trim().toLowerCase() === String(groupName).trim().toLowerCase()
                    ) || Object.values(participating).find(g =>
                        g.subject && g.subject.trim().toLowerCase().includes(String(groupName).trim().toLowerCase())
                    );

                    if (matchedGroup) {
                        destinationJid = matchedGroup.id;
                        console.log(`[WA-BOT] Resolved Group Name '${groupName}' to JID: ${destinationJid}`);
                    }
                } catch (gFetchErr) {
                    console.warn(`[WA-BOT] groupFetchAllParticipating error:`, gFetchErr.message);
                }
            }

            if (!destinationJid && codeToUse) {
                if (jidCache[codeToUse]) {
                    destinationJid = jidCache[codeToUse];
                } else {
                    const withTimeout = (promise, ms = 4000) => Promise.race([
                        promise,
                        new Promise((_, reject) => setTimeout(() => reject(new Error('Invite resolution timeout')), ms))
                    ]);

                    if (targetType === 'channel') {
                        try {
                            const meta = await withTimeout(sock.newsletterMetadata('invite', codeToUse), 4000);
                            if (meta && meta.id) {
                                destinationJid = meta.id.includes('@newsletter') ? meta.id : `${meta.id}@newsletter`;
                                jidCache[codeToUse] = destinationJid;
                                console.log(`[WA-BOT] Resolved WhatsApp Channel JID: ${destinationJid} (${meta.name || 'Channel'})`);
                            }
                        } catch (nlErr) {
                            console.log(`[WA-BOT] newsletterMetadata note for ${codeToUse}: ${nlErr.message}`);
                        }
                    } else {
                        try {
                            const groupInfo = await withTimeout(sock.groupGetInviteInfo(codeToUse), 4000);
                            if (groupInfo && groupInfo.id) {
                                destinationJid = groupInfo.id.includes('@g.us') ? groupInfo.id : `${groupInfo.id}@g.us`;
                                jidCache[codeToUse] = destinationJid;
                            }
                        } catch (invErr) {
                            console.log(`[WA-BOT] groupGetInviteInfo note for ${codeToUse}: ${invErr.message}`);
                        }

                        if (!destinationJid) {
                            try {
                                const joinedJid = await withTimeout(sock.groupAcceptInvite(codeToUse), 4000);
                                if (joinedJid) {
                                    destinationJid = joinedJid.includes('@g.us') ? joinedJid : `${joinedJid}@g.us`;
                                    jidCache[codeToUse] = destinationJid;
                                }
                            } catch (accErr) {
                                console.log(`[WA-BOT] groupAcceptInvite note: ${accErr.message}`);
                            }
                        }
                    }
                }
            }

            if (!destinationJid && targetType === 'group') {
                if (!req.body.groupName && !req.body.inviteCode && targetJid) {
                    destinationJid = targetJid;
                    console.log(`[WA-BOT] Used pre-resolved startup targetJid: ${destinationJid}`);
                }
            }

            // STRICT TARGET TYPE & RESOLUTION VALIDATION
            if (!destinationJid) {
                console.warn(`[WA-BOT] ❌ Target resolution failed for '${rawCode}' (Type: ${targetType}).`);
                failedCount++;
                results.push({
                    intended_target: rawCode,
                    clean_code: codeToUse,
                    target_type: targetType,
                    resolved_jid: null,
                    success: false,
                    error: "TARGET_RESOLUTION_FAILED",
                    fallback_used: false
                });
                continue;
            }

            if (targetType === 'channel' && !destinationJid.includes('@newsletter')) {
                console.warn(`[WA-BOT] ❌ Target type mismatch for Channel '${rawCode}'. Resolved JID '${destinationJid}' is not @newsletter.`);
                failedCount++;
                results.push({
                    intended_target: rawCode,
                    clean_code: codeToUse,
                    target_type: targetType,
                    resolved_jid: destinationJid,
                    success: false,
                    error: "TARGET_TYPE_MISMATCH",
                    fallback_used: false
                });
                continue;
            }

            let contentPayload = { text: message || '' };
            const mediaSrc = mediaSource;
            if (mediaSrc) {
                let imgBuffer = null;
                if (typeof mediaSrc === 'string' && (mediaSrc.startsWith('http://') || mediaSrc.startsWith('https://'))) {
                    imgBuffer = { url: mediaSrc };
                } else if (typeof mediaSrc === 'string' && mediaSrc.includes(';base64,')) {
                    const base64Data = mediaSrc.split(';base64,').pop().replace(/\s/g, '');
                    imgBuffer = Buffer.from(base64Data, 'base64');
                } else if (typeof mediaSrc === 'string' && fs.existsSync(mediaSrc)) {
                    imgBuffer = fs.readFileSync(mediaSrc);
                }
                if (imgBuffer) {
                    contentPayload = { image: imgBuffer, caption: message || '', mimetype: 'image/png' };
                }
            }

            try {
                const sendRes = await sock.sendMessage(destinationJid, contentPayload);
                sentCount++;
                logDispatchToBackend(destinationJid, message || '[Media Attachment]', req.body.groupName || 'Sales Team Group');
                results.push({
                    intended_target: rawCode,
                    clean_code: codeToUse,
                    target_type: targetType,
                    resolved_jid: destinationJid,
                    message_id: sendRes?.key?.id,
                    success: true,
                    fallback_used: false
                });
            } catch (sendErr) {
                console.error(`[WA-BOT] Send failed to ${destinationJid}: ${sendErr.message}`);
                failedCount++;
                let userFriendlyErr = sendErr.message || String(sendErr);
                if (String(sendErr.message).toLowerCase().includes('forbidden') || String(sendErr.message).includes('403')) {
                    userFriendlyErr = "GROUP PERMISSION DENIED: In 'Mynt Sales New Group', only Admins can send messages. Please promote the connected WhatsApp phone to Admin in WhatsApp Group Settings or change group settings to 'All Participants'.";
                }
                results.push({
                    intended_target: rawCode,
                    clean_code: codeToUse,
                    target_type: targetType,
                    resolved_jid: destinationJid,
                    success: false,
                    error: userFriendlyErr,
                    fallback_used: false
                });
            }
        }

        const isOverallSuccess = sentCount > 0 && failedCount === 0;
        return res.json({
            success: isOverallSuccess,
            sent_count: sentCount,
            failed_count: failedCount,
            results: results,
            message_id: results.find(r => r.message_id)?.message_id
        });

    } catch (err) {
        console.error("❌ Error sending group message:", err);
        return res.status(500).json({ success: false, error: err.message });
    }
});

async function logDispatchToBackend(target, message, targetName = "Scanned Bot Alert") {
    try {
        const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:8000/api/v1/whatsapp/log-bot-dispatch";
        await fetch(backendUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                phone_or_target: target,
                message: message || "[Media Attachment]",
                target_name: targetName,
                sender_type: "bot",
                sent_by_name: "Scanned Bot"
            })
        });
    } catch (e) {
        // Non-blocking log
    }
}

app.post('/api/send-message', async (req, res) => {
    try {
        const { phone, message, imageUrl, imagePath, media_url, mediaUrl } = req.body;
        const mediaSource = imageUrl || imagePath || media_url || mediaUrl || null;
        if (!phone || (!message && !mediaSource)) {
            return res.status(400).json({ success: false, error: "phone and message or media parameter required" });
        }

        // Graceful wait if socket is actively reconnecting
        if (connectionStatus === 'reconnecting') {
            const startWait = Date.now();
            while (connectionStatus === 'reconnecting' && (Date.now() - startWait) < 4000) {
                await new Promise(r => setTimeout(r, 400));
            }
        }

        if (connectionStatus !== 'connected' || !sock) {
            return res.status(503).json({
                success: false,
                error: connectionStatus === 'reconnecting' 
                    ? "WhatsApp bot is reconnecting. Please retry in a moment."
                    : "WhatsApp bot not connected. Scan QR code at http://localhost:5002/qr",
                status: connectionStatus,
                can_send_now: false
            });
        }

        let cleanPhone = String(phone).replace(/\D/g, '');
        if (cleanPhone.length === 10) cleanPhone = '91' + cleanPhone;
        const recipientJid = cleanPhone.includes('@s.whatsapp.net') ? cleanPhone : `${cleanPhone}@s.whatsapp.net`;

        let contentPayload = { text: message || '' };
        const mediaSrc = mediaSource;
        if (mediaSrc) {
            let imgBuffer = null;
            if (typeof mediaSrc === 'string' && (mediaSrc.startsWith('http://') || mediaSrc.startsWith('https://'))) {
                imgBuffer = { url: mediaSrc };
            } else if (typeof mediaSrc === 'string' && mediaSrc.includes(';base64,')) {
                const base64Data = mediaSrc.split(';base64,').pop().replace(/\s/g, '');
                imgBuffer = Buffer.from(base64Data, 'base64');
            } else if (typeof mediaSrc === 'string' && fs.existsSync(mediaSrc)) {
                imgBuffer = fs.readFileSync(mediaSrc);
            }
            if (imgBuffer) {
                contentPayload = (message && message.trim()) ? { image: imgBuffer, caption: message.trim(), mimetype: 'image/png' } : { image: imgBuffer, mimetype: 'image/png' };
            }
        }

        const sentMsg = await sock.sendMessage(recipientJid, contentPayload);
        logDispatchToBackend(cleanPhone, message || '[Media Attachment]', req.body.recipientName || 'Staff Lead Dispatch');

        return res.json({
            success: true,
            recipient_jid: recipientJid,
            message_id: sentMsg?.key?.id,
            key: sentMsg?.key
        });

    } catch (err) {
        console.error("❌ Error sending direct message:", err);
        return res.status(500).json({ success: false, error: err.message });
    }
});

if (require.main === module) {
    app.listen(PORT, () => {
        console.log(`🚀 Self-Hosted WhatsApp Web Group Bot running on http://localhost:${PORT}`);
        startWhatsAppBot();
    });
}

module.exports = {
    app,
    processConnectionUpdate,
    startWhatsAppBot,
    logoutBotSession,
    restoreSessionFromDatabase,
    purgeS3Session,
    getConnectionStatus: () => connectionStatus,
    setConnectionStatus: (s) => { connectionStatus = s; },
    getClientGen: () => clientGen,
    setClientGen: (g) => { clientGen = g; },
    getSkipRestoreOnce: () => skipRestoreOnce,
    setSkipRestoreOnce: (b) => { skipRestoreOnce = b; },
    AUTH_DIR
};
