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
app.use(express.json());

const PORT = process.env.PORT || 5002;
const AUTH_DIR = path.join(__dirname, 'auth_info');
const DEFAULT_INVITE_CODE = "LfX8mGootXa7SpwNIz7P5C";

let sock = null;
let currentQr = null;
let connectionStatus = 'disconnected';
let targetJid = null;

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
        const { message, inviteCode, groupId } = req.body;
        if (!message) {
            return res.status(400).json({ success: false, error: "message parameter required" });
        }

        if (connectionStatus !== 'connected' || !sock) {
            return res.status(503).json({
                success: false,
                error: "WhatsApp bot not connected. Scan QR code at http://localhost:5002/qr",
                status: connectionStatus
            });
        }

        let destinationJid = groupId;
        const codeToUse = inviteCode || DEFAULT_INVITE_CODE;

        if (!destinationJid && codeToUse) {
            if (jidCache[codeToUse]) {
                destinationJid = jidCache[codeToUse];
            } else {
                // Try Group Invite lookup
                try {
                    const groupInfo = await sock.groupGetInviteInfo(codeToUse);
                    if (groupInfo && groupInfo.id) {
                        destinationJid = groupInfo.id.includes('@g.us') ? groupInfo.id : `${groupInfo.id}@g.us`;
                        jidCache[codeToUse] = destinationJid;
                    }
                } catch (invErr) {
                    // Try WhatsApp Channel (Newsletter) lookup
                    try {
                        if (typeof sock.newsletterMetadata === 'function') {
                            const newsInfo = await sock.newsletterMetadata('invite', codeToUse);
                            if (newsInfo && newsInfo.id) {
                                destinationJid = newsInfo.id.includes('@newsletter') ? newsInfo.id : `${newsInfo.id}@newsletter`;
                                jidCache[codeToUse] = destinationJid;
                            }
                        }
                    } catch (newsErr) {
                        console.log(`Newsletter lookup note: ${newsErr.message}`);
                    }
                }
            }
        }

        if (!destinationJid) {
            destinationJid = targetJid;
        }

        if (!destinationJid) {
            return res.status(404).json({ success: false, error: "Could not resolve WhatsApp group JID from invite code" });
        }

        const sentMsg = await sock.sendMessage(destinationJid, { text: message });
        return res.json({
            success: true,
            group_jid: destinationJid,
            message_id: sentMsg?.key?.id
        });

    } catch (err) {
        console.error("❌ Error sending group message:", err);
        return res.status(500).json({ success: false, error: err.message });
    }
});

app.listen(PORT, () => {
    console.log(`🚀 Self-Hosted WhatsApp Web Group Bot running on http://localhost:${PORT}`);
    startWhatsAppBot();
});
