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
    fetchLatestBaileysVersion
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
        printQRInTerminal: false
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
            const shouldReconnect = (lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut);
            console.log(`⚠️ Connection closed. Reconnecting: ${shouldReconnect}`);
            if (shouldReconnect) {
                setTimeout(startWhatsAppBot, 3000);
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
        <head><title>Scan WhatsApp Group Bot QR</title></head>
        <body style="font-family: sans-serif; text-align: center; padding-top: 40px; background: #f4f6f9;">
            <h2>📱 Scan QR Code to Link Sales WhatsApp Group Bot</h2>
            <p>Open WhatsApp on phone ➔ Linked Devices ➔ Link a Device</p>
            <div style="margin: 20px auto; background: white; display: inline-block; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                <img src="${qrUrl}" alt="QR Code" width="300" height="300" />
            </div>
            <p><small>Status: ${connectionStatus}</small></p>
            <script>setTimeout(() => { location.reload(); }, 6000);</script>
        </body>
        </html>
    `);
});

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

        let destinationJid = groupId || targetJid;

        // Resolve invite code if JID not cached
        const codeToUse = inviteCode || DEFAULT_INVITE_CODE;
        if (!destinationJid && codeToUse) {
            try {
                const groupInfo = await sock.groupGetInviteInfo(codeToUse);
                if (groupInfo && groupInfo.id) {
                    destinationJid = groupInfo.id.includes('@g.us') ? groupInfo.id : `${groupInfo.id}@g.us`;
                    targetJid = destinationJid;
                }
            } catch (invErr) {
                // If bot is already in group, joinGroupViaInviteCode will succeed
                try {
                    destinationJid = await sock.groupAcceptInvite(codeToUse);
                } catch (acceptErr) {
                    console.log(`Invite accept note: ${acceptErr.message}`);
                }
            }
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
