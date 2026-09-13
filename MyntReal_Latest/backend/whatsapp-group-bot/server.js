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

const IS_PRODUCTION = (process.env.ENVIRONMENT === 'production' || process.env.NODE_ENV === 'production');

// Security Boundary: Non-production environments MUST NEVER use prod_baileys!
let effectiveSessionId = process.env.WA_SESSION_ID;
if (!IS_PRODUCTION) {
    if (!effectiveSessionId || effectiveSessionId === 'prod_baileys') {
        effectiveSessionId = 'dev_baileys';
    }
} else {
    effectiveSessionId = effectiveSessionId || 'prod_baileys';
}
const SESSION_ID = effectiveSessionId;

// Local Dev Guard: Local development runs in safe standby mode by default.
// Only connects a live socket if explicitly permitted via ALLOW_LOCAL_WHATSAPP_SOCKET='true'.
const ALLOW_LOCAL_SOCKET = IS_PRODUCTION || (process.env.ALLOW_LOCAL_WHATSAPP_SOCKET === 'true');

let sock = null;
let currentQr = null;
let connectionStatus = ALLOW_LOCAL_SOCKET ? 'disconnected' : 'dev_standby';
let targetJid = null;
let clientGen = 0;
let skipRestoreOnce = false;

// Prevent process exit on background Baileys socket disconnection (1006 / connection reset)
const BACKEND_API_BASE = process.env.BACKEND_API_URL || 'http://127.0.0.1:8000';

// ── Multi-Instance Distributed Leader Election & Coordination ────────────────
const os = require('os');

function getPrivateIp() {
    try {
        const interfaces = os.networkInterfaces();
        for (const devName in interfaces) {
            const iface = interfaces[devName];
            for (let i = 0; i < iface.length; i++) {
                const alias = iface[i];
                if (alias.family === 'IPv4' && !alias.internal) {
                    return alias.address;
                }
            }
        }
    } catch (e) {}
    return '127.0.0.1';
}

const INSTANCE_HOST = getPrivateIp();
const INSTANCE_ID = `${os.hostname()}-${process.pid}`;

let isLeader = false;
let leaderHost = null;
let lastSuccessfulLeaseRenewal = 0;
let clusterState = {
    status: 'disconnected',
    qr: null,
    qr_url: null,
    can_send_now: false,
    generation_id: 0,
    target_jid: null
};
let isHeartbeatRunning = false;

function stopWhatsAppSocket() {
    if (sock) {
        try {
            sock.ev.removeAllListeners();
            sock.ws?.close();
        } catch (e) {}
        sock = null;
    }
    currentQr = null;
    connectionStatus = 'disconnected';
}

let isProcessingQueue = false;
async function processOutboundQueue() {
    if (isProcessingQueue || !sock || connectionStatus !== 'connected') return;
    isProcessingQueue = true;
    try {
        const resp = await fetch(`${BACKEND_API_BASE}/api/v1/whatsapp/bot-queue-poll?limit=5`);
        if (!resp.ok) return;
        const data = await resp.json();
        const items = data.items || [];
        for (const item of items) {
            const target = item.target_jid || item.phone;
            if (!target) continue;
            try {
                let contentPayload = { text: item.message || '' };
                if (item.media_url) {
                    contentPayload = {
                        image: { url: item.media_url },
                        caption: item.message || ''
                    };
                }
                const sentMsg = await sock.sendMessage(target, contentPayload);
                const wamid = sentMsg?.key?.id || null;
                await fetch(`${BACKEND_API_BASE}/api/v1/whatsapp/bot-queue-complete`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        queue_id: item.id,
                        status: 'sent',
                        result_payload: {
                            wamid: wamid,
                            target_jid: target,
                            timestamp: Date.now()
                        }
                    })
                });
            } catch (sendErr) {
                console.error(`❌ [OUTBOUND-QUEUE] Failed to send message to ${target}:`, sendErr.message);
                await fetch(`${BACKEND_API_BASE}/api/v1/whatsapp/bot-queue-complete`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        queue_id: item.id,
                        status: 'failed',
                        error_message: sendErr.message
                    })
                });
            }
        }
    } catch (qErr) {
        // queue note
    } finally {
        isProcessingQueue = false;
    }
}

async function syncClusterCoordinator() {
    if (!ALLOW_LOCAL_SOCKET) {
        // Local dev does not compete for cluster leadership or live sockets
        return;
    }
    if (isHeartbeatRunning) return;
    isHeartbeatRunning = true;
    try {
        const payload = {
            instance_id: INSTANCE_ID,
            instance_host: INSTANCE_HOST
        };

        if (isLeader) {
            payload.status = connectionStatus;
            payload.can_send_now = (connectionStatus === 'connected');
            payload.generation_id = clientGen;
            payload.target_jid = targetJid;
            if (currentQr) {
                payload.qr_data = currentQr;
                payload.qr_url = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(currentQr)}`;
            }
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 4000);

        const resp = await fetch(`${BACKEND_API_BASE}/api/v1/whatsapp/bot-cluster-heartbeat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (!resp.ok) {
            if (isLeader && lastSuccessfulLeaseRenewal > 0 && (Date.now() - lastSuccessfulLeaseRenewal > 15000)) {
                console.warn(`⚠️ [CLUSTER-COORDINATOR] Lease heartbeat failed (HTTP ${resp.status}) and renewal timed out (>15s). Fencing socket to prevent split-brain dual connections.`);
                isLeader = false;
                stopWhatsAppSocket();
            }
            return;
        }
        const data = await resp.json();

        if (data.is_leader) {
            lastSuccessfulLeaseRenewal = Date.now();
            if (!isLeader) {
                console.log(`👑 [CLUSTER-COORDINATOR] Instance ${INSTANCE_ID} ACQUIRED LEADER LEASE! Initializing Baileys Socket...`);
                isLeader = true;
                leaderHost = INSTANCE_HOST;
                startWhatsAppBot();
            }
            if (data.command === 'logout') {
                console.log(`🚪 [CLUSTER-COORDINATOR] Received remote 'logout' command from cluster.`);
                await logoutBotSession();
            } else if (data.command === 'reconnect') {
                console.log(`🔄 [CLUSTER-COORDINATOR] Received remote 'reconnect' command from cluster.`);
                connectionStatus = 'reconnecting';
                currentQr = null;
                startWhatsAppBot();
            }

            if (connectionStatus === 'connected' && sock) {
                await processOutboundQueue();
            }
        } else {
            if (isLeader) {
                console.log(`🛡️ [CLUSTER-COORDINATOR] Lease stepped down from leader to follower. Halting local socket to avoid multi-instance conflicts...`);
                isLeader = false;
                stopWhatsAppSocket();
            }
            leaderHost = data.leader_host;
            if (data.leader_state) {
                clusterState = {
                    status: data.leader_state.status || 'qr_ready',
                    qr: data.leader_state.qr_data || null,
                    qr_url: data.leader_state.qr_url || (data.leader_state.qr_data ? `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(data.leader_state.qr_data)}` : null),
                    can_send_now: !!data.leader_state.can_send_now,
                    generation_id: data.leader_state.generation_id || 0,
                    target_jid: data.leader_state.target_jid || null
                };
            }
        }
    } catch (err) {
        if (isLeader && lastSuccessfulLeaseRenewal > 0 && (Date.now() - lastSuccessfulLeaseRenewal > 15000)) {
            console.warn(`⚠️ [CLUSTER-COORDINATOR] Lease heartbeat network error and renewal timed out (>15s): ${err.message}. Fencing socket to prevent split-brain dual connections.`);
            isLeader = false;
            stopWhatsAppSocket();
        }
    } finally {
        isHeartbeatRunning = false;
    }
}

// ── S3 Cloud Session Sync Functions (Zero PostgreSQL Contention) ─────────────
function isSessionRegistered() {
    const credsPath = path.join(AUTH_DIR, 'creds.json');
    if (!fs.existsSync(credsPath)) return false;
    try {
        const raw = fs.readFileSync(credsPath, 'utf8');
        const creds = JSON.parse(raw);
        return Boolean(creds && (creds.registered === true || (creds.me && creds.me.id)));
    } catch {
        return false;
    }
}

async function restoreSessionFromDatabase() {
    if (!ALLOW_LOCAL_SOCKET) {
        console.log(`[S3-SESSION-SYNC] 🛡️ Local development socket disabled. Skipping S3 session restore.`);
        return false;
    }
    if (!IS_PRODUCTION && SESSION_ID === 'prod_baileys') {
        console.warn(`[S3-SESSION-SYNC] 🛑 Security violation: Non-production instance attempted to restore prod_baileys. Aborted.`);
        return false;
    }
    if (skipRestoreOnce) {
        console.log(`[S3-SESSION-SYNC] ℹ️ Skipping session restore (flagged fresh start after terminal logout).`);
        skipRestoreOnce = false;
        return false;
    }
    try {
        const resp = await fetch(`${BACKEND_API_BASE}/api/v1/whatsapp/bot-session-restore?session_id=${SESSION_ID}`);
        if (resp.ok) {
            const data = await resp.json();
            if (data.success && data.files && Object.keys(data.files).length > 0) {
                // Guard: If restored payload has no authenticated identity (no creds.me.id), do not restore
                const rawCreds = data.files['creds.json'];
                if (rawCreds) {
                    try {
                        const parsed = JSON.parse(rawCreds);
                        const hasIdentity = Boolean(parsed && parsed.me && parsed.me.id);
                        if (!hasIdentity && parsed && parsed.registered === false) {
                            console.log(`[S3-SESSION-SYNC] ℹ️ Session payload for '${SESSION_ID}' has no authenticated identity. Skipping unauthenticated restore.`);
                            return false;
                        }
                        if (hasIdentity && parsed.registered !== true) {
                            parsed.registered = true;
                            data.files['creds.json'] = JSON.stringify(parsed);
                        }
                    } catch (_) {}
                }
                if (!fs.existsSync(AUTH_DIR)) fs.mkdirSync(AUTH_DIR, { recursive: true });
                for (const [fileKey, fileData] of Object.entries(data.files)) {
                    const filePath = path.join(AUTH_DIR, fileKey);
                    fs.writeFileSync(filePath, fileData, 'utf8');
                }
                console.log(`[S3-SESSION-SYNC] ✅ Restored ${Object.keys(data.files).length} WhatsApp session files for '${SESSION_ID}' from S3 (${data.source || 's3'})!`);
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
        const resp = await fetch(`${BACKEND_API_BASE}/api/v1/whatsapp/bot-session-clear?session_id=${SESSION_ID}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        if (resp.ok) {
            console.log(`[S3-SESSION-SYNC] 🧹 Purged dead session '${SESSION_ID}' from S3 durable storage.`);
        }
    } catch (err) {
        console.log(`[S3-SESSION-SYNC] ⚠️ Note on S3 purge: ${err.message}`);
    }
}

let isBackingUp = false;
let hasPendingChanges = false;
let backupDebounceTimer = null;

async function backupSessionToDatabase() {
    // Architectural Guard: Never backup unauthenticated or unregistered credentials to durable storage
    if (!isSessionRegistered()) {
        return;
    }
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
                session_id: SESSION_ID,
                files: files
            }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (resp.ok) {
            const data = await resp.json();
            if (data.success) {
                console.log(`[S3-SESSION-SYNC] 💾 Synced ${Object.keys(files).length} session files for '${SESSION_ID}' to S3 durable storage.`);
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
    if (!ALLOW_LOCAL_SOCKET) {
        console.log(`[WA-LIFECYCLE] 🛡️ Local development socket disabled (ALLOW_LOCAL_WHATSAPP_SOCKET !== 'true'). Running in safe 'dev_standby' mode to protect production authoritative socket.`);
        connectionStatus = 'dev_standby';
        currentQr = null;
        return;
    }
    clientGen += 1;
    const thisGen = clientGen;
    console.log(`[WA-LIFECYCLE] 🚀 Initializing WhatsApp Socket (Generation ID: ${thisGen})...`);

    if (!fs.existsSync(AUTH_DIR)) {
        fs.mkdirSync(AUTH_DIR, { recursive: true });
    }

    // Inspect existing creds.json: purge only if corrupted syntax (prevents crash on invalid JSON)
    const credsPath = path.join(AUTH_DIR, 'creds.json');
    if (fs.existsSync(credsPath)) {
        try {
            JSON.parse(fs.readFileSync(credsPath, 'utf8'));
        } catch (e) {
            console.error(`[WA-LIFECYCLE] Corrupt creds.json detected, resetting auth dir:`, e.message);
            fs.rmSync(AUTH_DIR, { recursive: true, force: true });
            fs.mkdirSync(AUTH_DIR, { recursive: true });
        }
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
        browser: Browsers.macOS('Desktop'),
        syncFullHistory: false,
        connectTimeoutMs: 60000,
        keepAliveIntervalMs: 30000,
        qrTimeout: 180000,
        defaultQueryTimeoutMs: 60000,
        emitOwnEvents: false
    });

    let backupDebounceTimer = null;
    sock.ev.on('creds.update', async () => {
        if (thisGen !== clientGen) return; // Stale client guard
        await saveCreds();
        if (isSessionRegistered()) {
            scheduleDebouncedBackup();
        }
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
        syncClusterCoordinator();
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
        syncClusterCoordinator();
    }

    if (connection === 'close') {
        const errDetail = lastDisconnect?.error?.message || lastDisconnect?.error;
        const statusCode = lastDisconnect?.error?.output?.statusCode || lastDisconnect?.error?.statusCode;
        
        // Only consider genuinely logged out if explicit 401 DisconnectReason.loggedOut is received
        const isLoggedOut = statusCode === DisconnectReason.loggedOut || statusCode === 401;
        const isConflict = statusCode === DisconnectReason.connectionReplaced || statusCode === 440 || String(errDetail).includes('Stream Errored (conflict)');
        const isRestartRequired = statusCode === DisconnectReason.restartRequired || statusCode === 515;
        
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
        } else if (isConflict) {
            connectionStatus = 'session_conflict';
            currentQr = null;
            console.warn(`🛑 [WA-LIFECYCLE] WhatsApp session conflict detected (Status 440: Connection Replaced / Conflict, Gen: ${thisGen}). Another instance or device is active with session '${SESSION_ID}'. Halting automatic reconnect loop. Call POST /api/reconnect, POST /api/reclaim, or visit /qr to reclaim.`);
            // Safely reconcile in-flight queue items without blind resends
            fetch(`${BACKEND_API_BASE}/api/v1/whatsapp/bot-queue-reconcile-inflight`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason: 'session_conflict', instance_id: INSTANCE_ID })
            }).catch(() => {});
        } else if (isRestartRequired) {
            connectionStatus = 'reconnecting';
            console.log(`[WA-LIFECYCLE] 🔄 Restart required by WhatsApp server (Status: 515, Gen: ${thisGen}). Reconnecting in 1s to finalize device pairing handshake...`);
            setTimeout(() => {
                if (thisGen === clientGen) startWhatsAppBot();
            }, 1000);
        } else {
            // Check if socket was authenticated before disconnect
            const registered = isSessionRegistered();
            if (!registered) {
                // Expected unauthenticated WhatsApp pairing window expiration (Status 428 / 408)
                // Keep connectionStatus in qr_ready and initiate controlled socket refresh in 2s
                connectionStatus = 'qr_ready';
                console.log(`[WA-LIFECYCLE] ℹ️ Unauthenticated pairing socket reset (Status: ${statusCode || '428/408'}). Controlled refresh in 2s (Gen ${thisGen})...`);
                setTimeout(() => {
                    if (thisGen === clientGen) startWhatsAppBot();
                }, 2000);
            } else {
                // Transient disconnect of authenticated session (428 connectionClosed, 408 timedOut, ECONNRESET, etc.)
                // ALWAYS preserve AUTH_DIR so Baileys re-reads saved creds.json and auto-reconnects seamlessly without re-scanning QR.
                connectionStatus = 'reconnecting';
                console.log(`⚠️ [WA-LIFECYCLE] Temporary authenticated socket reset (Status: ${statusCode || 'unknown'}, Reason: ${errDetail || 'Connection lost'}). Preserving session credentials and auto-reconnecting in 3s...`);
                setTimeout(() => {
                    if (thisGen === clientGen) startWhatsAppBot();
                }, 3000);
            }
        }
        syncClusterCoordinator();
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
    let result;
    if (isLeader) {
        result = await logoutBotSession();
    } else {
        console.log(`[CLUSTER] Sending remote 'logout' command from follower ${INSTANCE_ID}...`);
        try {
            await fetch(`${BACKEND_API_BASE}/api/v1/whatsapp/bot-cluster-command`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: 'logout' })
            });
            if (fs.existsSync(AUTH_DIR)) {
                fs.rmSync(AUTH_DIR, { recursive: true, force: true });
            }
            clusterState.status = 'qr_ready';
            clusterState.qr = null;
            clusterState.qr_url = null;
            clusterState.can_send_now = false;
            result = { success: true, message: "Logged out cluster session." };
        } catch (e) {
            result = { success: false, error: e.message };
        }
    }
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

app.all(['/reconnect', '/api/reconnect', '/reclaim', '/api/reclaim'], async (req, res) => {
    console.log(`[WA-LIFECYCLE] 🔄 Manual reconnect/reclaim requested for session '${SESSION_ID}' (Current Status: ${isLeader ? connectionStatus : clusterState.status})...`);
    if (isLeader) {
        connectionStatus = 'reconnecting';
        currentQr = null;
        startWhatsAppBot();
    } else {
        try {
            await fetch(`${BACKEND_API_BASE}/api/v1/whatsapp/bot-cluster-command`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: 'reconnect' })
            });
            clusterState.status = 'reconnecting';
            clusterState.qr = null;
            clusterState.qr_url = null;
        } catch (e) {}
    }
    return res.json({
        success: true,
        message: "WhatsApp bot reconnect sequence initiated",
        status: isLeader ? connectionStatus : clusterState.status,
        generation_id: isLeader ? clientGen : clusterState.generation_id,
        session_id: SESSION_ID,
        is_leader: isLeader
    });
});

app.get('/status', (req, res) => {
    if (!ALLOW_LOCAL_SOCKET) {
        return res.json({
            status: 'dev_standby',
            connection_state: 'dev_standby',
            can_send_now: false,
            qr_available: false,
            session_id: SESSION_ID,
            is_conflict: false,
            generation_id: 0,
            target_jid: DEFAULT_INVITE_CODE,
            invite_code: DEFAULT_INVITE_CODE,
            is_leader: false,
            leader_host: null,
            instance_id: INSTANCE_ID,
            message: 'Local WhatsApp socket is in standby mode. Production is the sole authoritative WhatsApp gateway.',
            timestamp: Date.now()
        });
    }

    const effectiveStatus = isLeader ? connectionStatus : (clusterState.status || 'disconnected');
    const effectiveQr = isLeader ? currentQr : clusterState.qr;
    const effectiveCanSend = isLeader ? (connectionStatus === 'connected') : clusterState.can_send_now;
    const effectiveGen = isLeader ? clientGen : clusterState.generation_id;
    const effectiveTargetJid = isLeader ? targetJid : clusterState.target_jid;

    return res.json({
        status: effectiveStatus,
        connection_state: effectiveStatus,
        can_send_now: effectiveCanSend,
        qr_available: !!effectiveQr && (effectiveStatus === 'qr_ready' || effectiveStatus === 'disconnected'),
        session_id: SESSION_ID,
        is_conflict: effectiveStatus === 'session_conflict',
        generation_id: effectiveGen,
        target_jid: effectiveTargetJid,
        invite_code: DEFAULT_INVITE_CODE,
        is_leader: isLeader,
        leader_host: leaderHost,
        instance_id: INSTANCE_ID,
        timestamp: Date.now()
    });
});

app.get('/qr-data', (req, res) => {
    if (!ALLOW_LOCAL_SOCKET) {
        return res.json({
            status: 'dev_standby',
            connection_state: 'dev_standby',
            can_send_now: false,
            qr: null,
            qr_url: null,
            qr_available: false,
            session_id: SESSION_ID,
            is_conflict: false,
            generation_id: 0,
            is_leader: false,
            instance_id: INSTANCE_ID,
            message: 'Local WhatsApp socket is in standby mode.',
            timestamp: Date.now()
        });
    }

    const effectiveStatus = isLeader ? connectionStatus : (clusterState.status || 'disconnected');
    const effectiveQr = isLeader ? currentQr : clusterState.qr;
    const effectiveCanSend = isLeader ? (connectionStatus === 'connected') : clusterState.can_send_now;
    const effectiveGen = isLeader ? clientGen : clusterState.generation_id;
    const effectiveQrUrl = effectiveQr
        ? `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(effectiveQr)}`
        : (clusterState.qr_url || null);

    return res.json({
        status: effectiveStatus,
        connection_state: effectiveStatus,
        can_send_now: effectiveCanSend,
        qr: effectiveQr,
        qr_url: effectiveQrUrl,
        qr_available: !!effectiveQr && (effectiveStatus === 'qr_ready' || effectiveStatus === 'disconnected'),
        session_id: SESSION_ID,
        is_conflict: effectiveStatus === 'session_conflict',
        generation_id: effectiveGen,
        is_leader: isLeader,
        instance_id: INSTANCE_ID,
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
    if (!ALLOW_LOCAL_SOCKET) {
        return res.send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>WhatsApp Gateway - Standby Mode</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="font-family: system-ui, -apple-system, sans-serif; text-align: center; padding: 50px 15px; background: #f8fafc; color: #1e293b;">
                <div style="background: white; max-width: 500px; margin: 0 auto; padding: 36px 24px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
                    <div style="font-size: 48px; margin-bottom: 12px;">🛡️</div>
                    <h2 style="color: #0f172a; margin: 0 0 10px 0; font-size: 20px; font-weight: 800;">Local WhatsApp Gateway — Standby Mode</h2>
                    <p style="color: #64748b; font-size: 13.5px; line-height: 1.6; margin-bottom: 20px;">
                        The production server on AWS is the <strong>sole authoritative owner</strong> of the company WhatsApp Web socket.
                    </p>
                    <div style="background: #f1f5f9; padding: 14px; border-radius: 10px; font-size: 12.5px; color: #334155; text-align: left; margin-bottom: 20px; line-height: 1.5;">
                        <strong>Architectural Safeguard:</strong><br>
                        • Live WebSocket disabled locally to prevent <code>connectionReplaced (440)</code> kicks on production.<br>
                        • Local direct and group message API dispatches are safely simulated.
                    </div>
                </div>
            </body>
            </html>
        `);
    }

    const effectiveStatus = isLeader ? connectionStatus : (clusterState.status || 'disconnected');
    const effectiveQr = isLeader ? currentQr : clusterState.qr;
    const effectiveQrUrl = effectiveQr
        ? `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(effectiveQr)}`
        : (clusterState.qr_url || null);
    const effectiveTargetJid = isLeader ? targetJid : (clusterState.target_jid || '120363410784518818@g.us');

    if (effectiveStatus === 'session_conflict') {
        return res.send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>WhatsApp Bot - Session Conflict</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="font-family: system-ui, -apple-system, sans-serif; text-align: center; padding: 50px 15px; background: #f4f6f9; color: #1e293b;">
                <div style="background: white; max-width: 480px; margin: 0 auto; padding: 36px 24px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
                    <h1 style="color: #f59e0b; font-size: 56px; margin: 0 0 12px 0;">⚠️</h1>
                    <h2 style="color: #b45309; margin: 0 0 8px 0; font-size: 20px; font-weight: 800;">Session Conflict Detected (Status 440)</h2>
                    <p style="color: #64748b; font-size: 13.5px; margin-bottom: 24px; line-height: 1.5;">
                        Another instance or phone is currently active using session <code style="background: #f1f5f9; padding: 3px 8px; border-radius: 6px; font-weight: 600; color: #0f172a;">${SESSION_ID}</code>.<br>
                        Auto-reconnect was stopped to prevent a continuous kick loop.
                    </p>
                    <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
                        <button onclick="doReconnect()" style="background: #3b82f6; color: white; border: none; padding: 12px 20px; border-radius: 12px; font-weight: 700; font-size: 14px; cursor: pointer;">
                            🔄 Reclaim Session
                        </button>
                        <button onclick="doLogout()" style="background: #ef4444; color: white; border: none; padding: 12px 20px; border-radius: 12px; font-weight: 700; font-size: 14px; cursor: pointer;">
                            🚪 Reset & Scan New QR
                        </button>
                    </div>
                    <p id="actionMsg" style="margin-top: 16px; font-size: 13px; font-weight: 600; color: #64748b; display: none;"></p>
                </div>
                <script>
                    async function doReconnect() {
                        const msg = document.getElementById('actionMsg');
                        msg.style.display = 'block';
                        msg.style.color = '#3b82f6';
                        msg.textContent = '⏳ Reconnecting WhatsApp bot...';
                        try {
                            const res = await fetch('/api/reconnect', { method: 'POST' });
                            const data = await res.json();
                            msg.textContent = data.message || 'Connecting...';
                            setTimeout(() => { window.location.reload(); }, 2500);
                        } catch(e) { msg.textContent = '❌ ' + e.message; }
                    }
                    async function doLogout() {
                        if (!confirm("Are you sure? This will clear the session and generate a new QR code.")) return;
                        const msg = document.getElementById('actionMsg');
                        msg.style.display = 'block';
                        msg.style.color = '#ef4444';
                        msg.textContent = '⏳ Resetting session...';
                        try {
                            const res = await fetch('/api/logout', { method: 'POST' });
                            setTimeout(() => { window.location.href = '/qr'; }, 1500);
                        } catch(e) { msg.textContent = '❌ ' + e.message; }
                    }
                </script>
            </body>
            </html>
        `);
    }
    if (effectiveStatus === 'connected') {
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
                    <p style="color: #64748b; font-size: 13.5px; margin-bottom: 24px;">Target JID: <code style="background: #f1f5f9; padding: 3px 8px; border-radius: 6px; font-weight: 600; color: #0f172a;">${effectiveTargetJid}</code></p>
                    
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
    const initialQrUrl = effectiveQrUrl;
    return res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Scan WhatsApp Group Bot QR</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                .timer-pill { background: #e0f2fe; color: #0369a1; padding: 6px 16px; border-radius: 20px; font-weight: 700; font-size: 13.5px; display: inline-flex; align-items: center; gap: 6px; }
            </style>
        </head>
        <body style="font-family: system-ui, -apple-system, sans-serif; text-align: center; padding: 30px 15px; background: #f4f6f9; color: #1e293b;">
            <h2 style="font-size: 22px; margin-bottom: 8px;">📱 Scan QR Code to Link WhatsApp Bot</h2>
            <p style="color: #64748b; font-size: 14px; margin-top: 0; margin-bottom: 12px;">Open WhatsApp on phone ➔ Linked Devices ➔ Link a Device</p>

            <div class="timer-pill" id="timerBadge">
                ⏳ Active Pairing Session: <span id="timerText" style="font-family: monospace; font-size: 14px;">Live Socket</span>
            </div>
            
            <div id="qrContainer" style="margin: 20px auto; background: white; display: inline-block; padding: 24px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.08); min-width: 300px; min-height: 300px;">
                ${initialQrUrl 
                    ? '<img id="qrImg" src="' + initialQrUrl + '" width="300" height="300" style="display:block; border-radius: 8px;" />'
                    : '<div style="padding:100px 20px; font-size: 15px; color: #64748b; font-weight: 600;">⏳ Generating QR Code...<br><span style="font-size:12px; font-weight:400; color:#94a3b8">Will load automatically in a moment.</span></div>'
                }
            </div>
            
            <p id="statusMsg" style="font-size: 13.5px; font-weight: 600; color: #3b82f6;">
                ${initialQrUrl ? '🟢 QR Code Ready — Scan with WhatsApp Linked Devices...' : '⏳ Initializing WhatsApp Socket...'}
            </p>

            <script>
                let lastQrUrl = "${initialQrUrl || ''}";

                async function checkStatus() {
                    try {
                        const res = await fetch('/qr-data');
                        const data = await res.json();
                        if (data.status === 'connected') {
                            window.location.reload();
                        } else if (data.status === 'reconnecting') {
                            const msg = document.getElementById('statusMsg');
                            if (msg) {
                                msg.style.color = '#f59e0b';
                                msg.textContent = '🔄 Device Scanned! Finalizing WhatsApp connection, please wait...';
                            }
                        } else if (data.qr_url || data.qr) {
                            const newQrSrc = data.qr_url || (data.qr && (data.qr.startsWith('data:') ? data.qr : ('data:image/png;base64,' + data.qr)));
                            if (newQrSrc && newQrSrc !== lastQrUrl) {
                                lastQrUrl = newQrSrc;
                                const img = document.getElementById('qrImg');
                                if (img) {
                                    img.src = newQrSrc;
                                } else {
                                    const container = document.getElementById('qrContainer');
                                    if (container) {
                                        container.innerHTML = '<img id="qrImg" src="' + newQrSrc + '" width="300" height="300" style="display:block; border-radius: 8px;" />';
                                    }
                                }
                            }
                            const timerText = document.getElementById('timerText');
                            if (timerText && data.generation_id) {
                                timerText.textContent = 'Active (Gen ' + data.generation_id + ')';
                            }
                            const msg = document.getElementById('statusMsg');
                            if (msg) {
                                msg.style.color = '#3b82f6';
                                msg.textContent = '🟢 QR Code Ready — Scan with WhatsApp Linked Devices...';
                            }
                        }
                    } catch (e) {}
                }

                setInterval(checkStatus, 2000);
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

        if (!ALLOW_LOCAL_SOCKET) {
            console.log(`[WA-BOT] 🛡️ [DEV-STANDBY] Mocked group message dispatch: ${message || '[Media]'}`);
            return res.json({
                success: true,
                mocked: true,
                sent_count: 1,
                failed_count: 0,
                results: [{ success: true, message_id: 'mock_dev_' + Date.now() }],
                message: 'Dev mode: Simulated group broadcast (live socket disabled in dev)'
            });
        }

        if (!isLeader) {
            if (!clusterState.can_send_now) {
                return res.status(503).json({
                    success: false,
                    error: "WhatsApp bot not connected. Scan QR code at /qr",
                    status: clusterState.status,
                    can_send_now: false
                });
            }
            try {
                let queueTargetJid = groupId || null;
                if (!queueTargetJid && !req.body.inviteCode && !req.body.inviteCodes && !req.body.groupName) {
                    queueTargetJid = DEFAULT_INVITE_CODE;
                }
                if (!queueTargetJid) {
                    return res.status(400).json({
                        success: false,
                        error: "Target resolution required for non-leader queue dispatch."
                    });
                }
                const enqResp = await fetch(`${BACKEND_API_BASE}/api/v1/whatsapp/bot-queue-enqueue`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        target_type: 'group',
                        target_jid: queueTargetJid,
                        message: message || '',
                        media_url: mediaSource,
                        instance_id: INSTANCE_ID
                    })
                });
                const enqData = await enqResp.json();
                if (!enqData.success) {
                    return res.status(500).json({ success: false, error: enqData.error });
                }
                const queueId = enqData.queue_id;
                const startWait = Date.now();
                while ((Date.now() - startWait) < 5000) {
                    await new Promise(r => setTimeout(r, 400));
                    const chkResp = await fetch(`${BACKEND_API_BASE}/api/v1/whatsapp/bot-queue-check?queue_id=${queueId}`);
                    if (chkResp.ok) {
                        const chkData = await chkResp.json();
                        if (chkData.status === 'sent') {
                            return res.json({
                                success: true,
                                results: [{ success: true, message_id: chkData.result_payload?.message_id }],
                                message_id: chkData.result_payload?.message_id,
                                via_queue: true
                            });
                        } else if (chkData.status === 'failed') {
                            return res.status(500).json({ success: false, error: chkData.error_message });
                        }
                    }
                }
                return res.json({ success: true, queued: true, queue_id: queueId });
            } catch (e) {
                return res.status(500).json({ success: false, error: e.message });
            }
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
                : "WhatsApp bot not connected. Scan QR code at /qr";
            return res.status(503).json({
                success: false,
                error: err_msg,
                status: connectionStatus,
                can_send_now: false
            });
        }

        let codesToUse;
        if (req.body.inviteCodes) {
            codesToUse = Array.isArray(req.body.inviteCodes) ? req.body.inviteCodes : [req.body.inviteCodes];
        } else if (req.body.inviteCode) {
            codesToUse = [req.body.inviteCode];
        } else if (!req.body.groupName && !req.body.groupId) {
            codesToUse = [DEFAULT_INVITE_CODE];
        } else {
            codesToUse = [''];
        }
        const targetCodes = Array.from(new Set(codesToUse));
        
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
                if (codeToUse.endsWith('@g.us') || codeToUse.includes('@newsletter')) {
                    destinationJid = codeToUse;
                    jidCache[codeToUse] = destinationJid;
                } else if (jidCache[codeToUse]) {
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
                if (!req.body.groupName && !req.body.inviteCode && !req.body.inviteCodes && targetJid) {
                    destinationJid = targetJid;
                    console.log(`[WA-BOT] Used pre-resolved startup targetJid: ${destinationJid}`);
                }
            }

            // STRICT TARGET TYPE & RESOLUTION VALIDATION
            if (!destinationJid) {
                const targetDesc = req.body.groupName || rawCode || 'unspecified';
                console.warn(`[WA-BOT] ❌ Target resolution failed for '${targetDesc}' (Type: ${targetType}).`);
                failedCount++;
                results.push({
                    intended_target: targetDesc,
                    clean_code: codeToUse,
                    target_type: targetType,
                    resolved_jid: null,
                    success: false,
                    error: `TARGET_RESOLUTION_FAILED: Could not find or access group/channel '${targetDesc}'`,
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

            const sendOptions = {};
            const replyWamid = req.body.quoted_message_id || req.body.reply_to_wamid || req.body.reply_to_id;
            if (replyWamid) {
                sendOptions.quoted = {
                    key: {
                        id: replyWamid,
                        remoteJid: destinationJid,
                        fromMe: false
                    },
                    message: {
                        conversation: req.body.quoted_text || req.body.reply_to_text || ''
                    }
                };
            }

            try {
                const sendRes = await sock.sendMessage(destinationJid, contentPayload, sendOptions);
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
                    if (targetType === 'channel' || String(destinationJid).includes('@newsletter')) {
                        userFriendlyErr = "CHANNEL PERMISSION DENIED: The connected WhatsApp phone account is not an Admin or Owner of this WhatsApp Channel. In WhatsApp Channels, only Channel Admins can publish messages. Please make the connected WhatsApp phone an Admin of the channel.";
                    } else {
                        userFriendlyErr = `GROUP PERMISSION DENIED: In this WhatsApp group, only Admins can send messages. Please promote the connected WhatsApp phone to Admin or set group settings to 'All Participants'.`;
                    }
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

        let cleanPhone = String(phone).replace(/\D/g, '');
        if (cleanPhone.length === 10) cleanPhone = '91' + cleanPhone;
        const recipientJid = cleanPhone.includes('@s.whatsapp.net') ? cleanPhone : `${cleanPhone}@s.whatsapp.net`;

        // [DC-VGK-BLOCKED-001] Strict Suppression Check for Blocked Channel Partners
        try {
            const chkBlockResp = await fetch(`${BACKEND_API_BASE}/api/v1/whatsapp/check-blocked?phone=${cleanPhone}`);
            if (chkBlockResp.ok) {
                const blockData = await chkBlockResp.json();
                if (blockData.is_blocked) {
                    console.log(`[WA-BOT] 🛡️ [BLOCKED-SUPPRESSION] Refusing direct dispatch to blocked partner: ${cleanPhone}`);
                    return res.status(403).json({
                        success: false,
                        blocked: true,
                        error: "Recipient is a Blocked Channel Partner. Communications are strictly suppressed."
                    });
                }
            }
        } catch (blkErr) {
            // Non-blocking fallback if backend check momentarily unreachable
        }

        if (!ALLOW_LOCAL_SOCKET) {
            console.log(`[WA-BOT] 🛡️ [DEV-STANDBY] Mocked direct message dispatch to ${cleanPhone}: ${message || '[Media]'}`);
            return res.json({
                success: true,
                mocked: true,
                recipient_jid: recipientJid,
                message_id: 'mock_dev_' + Date.now(),
                message: 'Dev mode: Simulated direct message (live socket disabled in dev)'
            });
        }

        if (!isLeader) {
            if (!clusterState.can_send_now) {
                return res.status(503).json({
                    success: false,
                    error: "WhatsApp bot not connected. Scan QR code at /qr",
                    status: clusterState.status,
                    can_send_now: false
                });
            }
            try {
                const enqResp = await fetch(`${BACKEND_API_BASE}/api/v1/whatsapp/bot-queue-enqueue`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        target_type: 'direct',
                        target_jid: recipientJid,
                        message: message || '',
                        media_url: mediaSource,
                        instance_id: INSTANCE_ID
                    })
                });
                const enqData = await enqResp.json();
                if (!enqData.success) {
                    return res.status(500).json({ success: false, error: enqData.error });
                }
                const queueId = enqData.queue_id;
                const startWait = Date.now();
                while ((Date.now() - startWait) < 5000) {
                    await new Promise(r => setTimeout(r, 400));
                    const chkResp = await fetch(`${BACKEND_API_BASE}/api/v1/whatsapp/bot-queue-check?queue_id=${queueId}`);
                    if (chkResp.ok) {
                        const chkData = await chkResp.json();
                        if (chkData.status === 'sent') {
                            if (!req.body.skip_backend_log && !req.body.skipBackendLog) {
                                logDispatchToBackend(cleanPhone, message || '[Media Attachment]', req.body.recipientName || 'Staff Lead Dispatch');
                            }
                            return res.json({
                                success: true,
                                recipient_jid: recipientJid,
                                message_id: chkData.result_payload?.message_id,
                                via_queue: true
                            });
                        } else if (chkData.status === 'failed') {
                            return res.status(500).json({ success: false, error: chkData.error_message });
                        }
                    }
                }
                return res.json({ success: true, queued: true, queue_id: queueId, recipient_jid: recipientJid });
            } catch (e) {
                return res.status(500).json({ success: false, error: e.message });
            }
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
                    : "WhatsApp bot not connected. Scan QR code at /qr",
                status: connectionStatus,
                can_send_now: false
            });
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
                contentPayload = (message && message.trim()) ? { image: imgBuffer, caption: message.trim(), mimetype: 'image/png' } : { image: imgBuffer, mimetype: 'image/png' };
            }
        }

        const sendOptions = {};
        const replyWamid = req.body.quoted_message_id || req.body.reply_to_wamid || req.body.reply_to_id;
        if (replyWamid) {
            sendOptions.quoted = {
                key: {
                    id: replyWamid,
                    remoteJid: recipientJid,
                    fromMe: false
                },
                message: {
                    conversation: req.body.quoted_text || req.body.reply_to_text || ''
                }
            };
        }

        const sentMsg = await sock.sendMessage(recipientJid, contentPayload, sendOptions);
        if (!req.body.skip_backend_log && !req.body.skipBackendLog) {
            logDispatchToBackend(cleanPhone, message || '[Media Attachment]', req.body.recipientName || 'Staff Lead Dispatch');
        }

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
        console.log(`🚀 Self-Hosted WhatsApp Web Group Bot running on http://localhost:${PORT} [Instance: ${INSTANCE_ID}]`);
        // Start cluster coordinator loop immediately and every 5 seconds
        syncClusterCoordinator();
        setInterval(syncClusterCoordinator, 5000);
    });
}

module.exports = {
    app,
    processConnectionUpdate,
    startWhatsAppBot,
    logoutBotSession,
    restoreSessionFromDatabase,
    purgeS3Session,
    syncClusterCoordinator,
    stopWhatsAppSocket,
    processOutboundQueue,
    getConnectionStatus: () => connectionStatus,
    setConnectionStatus: (s) => { connectionStatus = s; },
    getClientGen: () => clientGen,
    setClientGen: (g) => { clientGen = g; },
    getSkipRestoreOnce: () => skipRestoreOnce,
    setSkipRestoreOnce: (b) => { skipRestoreOnce = b; },
    getIsLeader: () => isLeader,
    setIsLeader: (l) => { isLeader = l; },
    getClusterState: () => clusterState,
    setClusterState: (s) => { clusterState = s; },
    AUTH_DIR,
    ALLOW_LOCAL_SOCKET,
    IS_PRODUCTION,
    SESSION_ID
};
