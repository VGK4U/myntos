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
const DEFAULT_INVITE_CODE = "LfX8mGootXa7SpwNIz7P5C";

let sock = null;
let currentQr = null;
let connectionStatus = 'disconnected';
let targetJid = null;

// Prevent process exit on background Baileys socket disconnection (1006 / connection reset)
process.on('unhandledRejection', (reason, promise) => {
    console.log('⚠️ Process captured unhandledRejection (socket reset/reconnect):', reason?.message || reason);
});
process.on('uncaughtException', (err) => {
    console.log('⚠️ Process captured uncaughtException:', err?.message || err);
});

async function startWhatsAppBot() {
    if (!fs.existsSync(AUTH_DIR)) {
        fs.mkdirSync(AUTH_DIR, { recursive: true });
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
        keepAliveIntervalMs: 25000,
        emitOwnEvents: false
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            currentQr = qr;
            connectionStatus = 'qr_ready';
            console.log("\n==================================================");
            console.log("📲 SCAN THIS QR CODE WITH YOUR WHATSAPP PHONE:");
            console.log("==================================================");
            qrcodeTerminal.generate(qr, { small: true });
            console.log(`\nAlternatively, open: http://localhost:${PORT}/qr in browser.\n`);
        }

        if (connection === 'open') {
            connectionStatus = 'connected';
            currentQr = null;
            console.log("✅ WHATSAPP WEB GROUP BOT CONNECTED SUCCESSFULLY!");

            // Attempt to resolve target group JID via invite code
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

        if (connection === 'close') {
            connectionStatus = 'disconnected';
            const errDetail = lastDisconnect?.error?.message || lastDisconnect?.error;
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            const shouldReconnect = (statusCode !== DisconnectReason.loggedOut);
            console.log(`⚠️ Connection closed (Status: ${statusCode}, Err: ${errDetail}). Reconnecting: ${shouldReconnect}`);
            if (shouldReconnect) {
                setTimeout(startWhatsAppBot, 5000);
            }
        }
    });
}

// ── API ENDPOINTS ─────────────────────────────────────────────────────────────

app.get('/status', (req, res) => {
    return res.json({
        status: connectionStatus,
        qr_available: !!currentQr,
        target_jid: targetJid,
        invite_code: DEFAULT_INVITE_CODE
    });
});

app.get('/qr', (req, res) => {
    if (connectionStatus === 'connected') {
        return res.send(`<h2>✅ WhatsApp Web Bot is already CONNECTED and ACTIVE!</h2><p>Group JID: ${targetJid || 'Ready'}</p>`);
    }
    if (!currentQr) {
        return res.send(`<h2>⏳ Generating QR Code... Please refresh in 5 seconds.</h2>`);
    }
    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(currentQr)}`;
    return res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Scan WhatsApp Group Bot QR</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: system-ui, -apple-system, sans-serif; text-align: center; padding: 30px 15px; background: #f4f6f9; color: #1e293b;">
            <h2 style="font-size: 22px; margin-bottom: 8px;">📱 Scan QR Code to Link WhatsApp Bot</h2>
            <p style="color: #64748b; font-size: 14px; margin-top: 0;">Open WhatsApp on phone ➔ Linked Devices ➔ Link a Device</p>
            <div style="margin: 24px auto; background: white; display: inline-block; padding: 24px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.08);">
                <img id="qrImg" src="${qrUrl}" alt="QR Code" width="300" height="300" style="display:block; border-radius: 8px;" />
            </div>
            <p id="statusMsg" style="font-size: 13px; font-weight: 600; color: #3b82f6;">🟢 QR Code Ready — Waiting for Phone Scan...</p>
            <script>
                // Async status check — no full page reload so camera scanning is smooth & uninterrupted
                setInterval(async () => {
                    try {
                        const res = await fetch('/status');
                        const data = await res.json();
                        if (data.status === 'connected') {
                            document.body.innerHTML = \`
                                <div style="padding-top: 60px;">
                                    <h1 style="color: #10b981; font-size: 48px;">✅</h1>
                                    <h2 style="color: #065f46;">WhatsApp Bot Successfully CONNECTED!</h2>
                                    <p style="color: #374151;">Group Bot is active and ready to send WhatsApp alerts.</p>
                                </div>
                            \`;
                        }
                    } catch (e) {}
                }, 3000);
            </script>
        </body>
        </html>
    `);
});

const jidCache = {};

app.post('/api/send-group-message', async (req, res) => {
    try {
        const { message, inviteCode, groupId, imageUrl, imagePath } = req.body;
        if (!message && !imageUrl && !imagePath) {
            return res.status(400).json({ success: false, error: "message or image parameter required" });
        }

        if (connectionStatus !== 'connected' || !sock) {
            return res.status(503).json({
                success: false,
                error: "WhatsApp bot not connected. Scan QR code at http://localhost:5002/qr",
                status: connectionStatus
            });
        }

        const codesToUse = req.body.inviteCodes || (req.body.inviteCode ? [req.body.inviteCode] : [DEFAULT_INVITE_CODE]);
        const targetCodes = Array.from(new Set(Array.isArray(codesToUse) ? codesToUse : [codesToUse]));
        
        let sentCount = 0;
        let lastResult = null;

        for (const codeToUse of targetCodes) {
            let destinationJid = groupId;
            if (!destinationJid && codeToUse) {
                if (jidCache[codeToUse]) {
                    destinationJid = jidCache[codeToUse];
                } else {
                    const withTimeout = (promise, ms = 4000) => Promise.race([
                        promise,
                        new Promise((_, reject) => setTimeout(() => reject(new Error('Invite resolution timeout')), ms))
                    ]);

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
                                console.log(`[WA-BOT] Successfully joined group via invite code ${codeToUse}: ${destinationJid}`);
                            }
                        } catch (accErr) {
                            console.log(`[WA-BOT] groupAcceptInvite note: ${accErr.message}`);
                        }
                    }

                    if (!destinationJid) {
                        try {
                            const groups = await withTimeout(sock.groupFetchAllParticipating(), 4000);
                            const gList = Object.values(groups || {});
                            if (gList.length > 0) {
                                destinationJid = gList[0].id;
                                jidCache[codeToUse] = destinationJid;
                                console.log(`[WA-BOT] Fallback destinationJid: ${destinationJid} (${gList[0].subject})`);
                            }
                        } catch (fErr) {
                            console.log(`[WA-BOT] groupFetchAllParticipating note: ${fErr.message}`);
                        }
                    }
                }
            }

            if (!destinationJid) destinationJid = targetJid;
            if (!destinationJid) continue;

            let contentPayload = { text: message || '' };
            const mediaSrc = imageUrl || imagePath;
            if (mediaSrc) {
                let imgBuffer = null;
                if (typeof mediaSrc === 'string' && (mediaSrc.startsWith('http://') || mediaSrc.startsWith('https://'))) {
                    imgBuffer = { url: mediaSrc };
                } else if (typeof mediaSrc === 'string' && mediaSrc.startsWith('data:image/')) {
                    const base64Data = mediaSrc.replace(/^data:image\/\w+;base64,/, '');
                    imgBuffer = Buffer.from(base64Data, 'base64');
                } else if (typeof mediaSrc === 'string' && fs.existsSync(mediaSrc)) {
                    imgBuffer = fs.readFileSync(mediaSrc);
                }
                if (imgBuffer) {
                    contentPayload = { image: imgBuffer, caption: message || '' };
                }
            }

            try {
                lastResult = await sock.sendMessage(destinationJid, contentPayload);
                sentCount++;
            } catch (sendErr) {
                console.log(`[WA-BOT] Initial sendMessage failed (${sendErr.message}). Attempting groupAcceptInvite & retry...`);
                try {
                    const joinedJid = await sock.groupAcceptInvite(codeToUse);
                    if (joinedJid) {
                        destinationJid = joinedJid.includes('@g.us') ? joinedJid : `${joinedJid}@g.us`;
                        jidCache[codeToUse] = destinationJid;
                    }
                    lastResult = await sock.sendMessage(destinationJid, contentPayload);
                    sentCount++;
                } catch (retryErr) {
                    console.log(`[WA-BOT] Retry sendMessage failed: ${retryErr.message}`);
                    throw retryErr;
                }
            }
        }

        return res.json({
            success: true,
            sent_count: sentCount,
            message_id: lastResult?.key?.id
        });

    } catch (err) {
        console.error("❌ Error sending group message:", err);
        return res.status(500).json({ success: false, error: err.message });
    }
});

app.post('/api/send-message', async (req, res) => {
    try {
        const { phone, message, imageUrl, imagePath } = req.body;
        if (!phone || (!message && !imageUrl && !imagePath)) {
            return res.status(400).json({ success: false, error: "phone and message/image parameters required" });
        }

        if (connectionStatus !== 'connected' || !sock) {
            return res.status(503).json({
                success: false,
                error: "WhatsApp bot not connected. Scan QR code at http://localhost:5002/qr",
                status: connectionStatus
            });
        }

        const cleanPhone = String(phone).replace(/\D/g, '');
        const recipientJid = cleanPhone.includes('@s.whatsapp.net') ? cleanPhone : `${cleanPhone}@s.whatsapp.net`;

        let contentPayload = { text: message || '' };
        const mediaSrc = imageUrl || imagePath;
        if (mediaSrc) {
            let imgBuffer = null;
            if (typeof mediaSrc === 'string' && (mediaSrc.startsWith('http://') || mediaSrc.startsWith('https://'))) {
                imgBuffer = { url: mediaSrc };
            } else if (typeof mediaSrc === 'string' && mediaSrc.startsWith('data:image/')) {
                const base64Data = mediaSrc.replace(/^data:image\/\w+;base64,/, '');
                imgBuffer = Buffer.from(base64Data, 'base64');
            } else if (typeof mediaSrc === 'string' && fs.existsSync(mediaSrc)) {
                imgBuffer = fs.readFileSync(mediaSrc);
            }
            if (imgBuffer) {
                contentPayload = (message && message.trim()) ? { image: imgBuffer, caption: message.trim() } : { image: imgBuffer };
            }
        }

        const sentMsg = await sock.sendMessage(recipientJid, contentPayload);
        return res.json({
            success: true,
            recipient_jid: recipientJid,
            message_id: sentMsg?.key?.id
        });

    } catch (err) {
        console.error("❌ Error sending direct message:", err);
        return res.status(500).json({ success: false, error: err.message });
    }
});

app.listen(PORT, () => {
    console.log(`🚀 Self-Hosted WhatsApp Web Group Bot running on http://localhost:${PORT}`);
    startWhatsAppBot();
});
