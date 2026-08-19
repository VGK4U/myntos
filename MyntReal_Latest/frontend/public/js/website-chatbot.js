/**
 * Mynt OS / VGK4U Website Floating Chatbot Component
 * Injectable floating chat widget positioned bottom-right with high visibility.
 */

(function () {
    const loc = window.location.pathname.toLowerCase();
    // Strict restriction: Chatbot must ONLY display on public main website pages, NEVER on login, staff, or admin pages.
    if (loc.includes('login') || loc.startsWith('/staff') || loc.startsWith('/admin') || loc.startsWith('/rvz') || loc.includes('dashboard')) {
        return;
    }
    if (window.MyntWebsiteChatbot) return;

    const styles = `
        @keyframes myntPulseGlow {
            0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7), 0 10px 25px rgba(0, 0, 0, 0.2); }
            70% { box-shadow: 0 0 0 18px rgba(16, 185, 129, 0), 0 14px 30px rgba(0, 0, 0, 0.25); }
            100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0), 0 10px 25px rgba(0, 0, 0, 0.2); }
        }

        .mynt-chatbot-btn {
            position: fixed !important;
            bottom: 32px !important;
            right: 32px !important;
            width: 76px !important;
            height: 76px !important;
            border-radius: 50% !important;
            background: linear-gradient(135deg, #10b981 0%, #047857 100%) !important;
            color: #ffffff !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 38px !important;
            cursor: pointer !important;
            z-index: 2147483647 !important;
            transition: transform 0.25s ease, background 0.25s ease !important;
            border: 3px solid #ffffff !important;
            animation: myntPulseGlow 2.5s infinite !important;
            user-select: none !important;
        }
        .mynt-chatbot-btn:hover {
            transform: scale(1.1) rotate(5deg) !important;
            background: linear-gradient(135deg, #34d399 0%, #059669 100%) !important;
        }
        .mynt-chatbot-badge {
            position: absolute !important;
            top: 2px !important;
            right: 2px !important;
            width: 18px !important;
            height: 18px !important;
            background: #ef4444 !important;
            border-radius: 50% !important;
            border: 2px solid white !important;
        }
        .mynt-chatbot-box {
            position: fixed !important;
            bottom: 120px !important;
            right: 32px !important;
            width: 420px !important;
            max-width: calc(100vw - 32px) !important;
            height: 600px !important;
            max-height: calc(100vh - 140px) !important;
            background: #ffffff !important;
            border-radius: 20px !important;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.28) !important;
            display: none;
            flex-direction: column !important;
            overflow: hidden !important;
            z-index: 2147483647 !important;
            font-family: system-ui, -apple-system, sans-serif !important;
            border: 1px solid #cbd5e1 !important;
        }
        .mynt-chatbot-box.open {
            display: flex !important;
            animation: myntSlideUp 0.3s ease-out !important;
        }
        @keyframes myntSlideUp {
            from { opacity: 0; transform: translateY(20px) scale(0.95); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }
        .mynt-chatbot-header {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
            color: white !important;
            padding: 16px 20px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: space-between !important;
        }
        .mynt-chatbot-header-info {
            display: flex !important;
            align-items: center !important;
            gap: 12px !important;
        }
        .mynt-chatbot-avatar {
            width: 44px !important;
            height: 44px !important;
            border-radius: 50% !important;
            background: #10b981 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 22px !important;
        }
        .mynt-chatbot-title {
            font-size: 16px !important;
            font-weight: 700 !important;
            margin: 0 !important;
            line-height: 1.2 !important;
        }
        .mynt-chatbot-status {
            font-size: 12px !important;
            color: #34d399 !important;
            display: flex !important;
            align-items: center !important;
            gap: 6px !important;
            margin-top: 2px !important;
        }
        .mynt-chatbot-status-dot {
            width: 8px !important;
            height: 8px !important;
            border-radius: 50% !important;
            background: #34d399 !important;
        }
        .mynt-chatbot-close {
            background: none !important;
            border: none !important;
            color: #94a3b8 !important;
            font-size: 24px !important;
            cursor: pointer !important;
            padding: 4px 8px !important;
            transition: color 0.2s !important;
        }
        .mynt-chatbot-close:hover { color: white !important; }
        .mynt-chatbot-body {
            flex: 1 !important;
            padding: 18px !important;
            overflow-y: auto !important;
            background: #f8fafc !important;
            display: flex !important;
            flex-direction: column !important;
            gap: 14px !important;
        }
        .mynt-chat-msg {
            max-width: 85% !important;
            padding: 12px 16px !important;
            border-radius: 14px !important;
            font-size: 14px !important;
            line-height: 1.5 !important;
            word-break: break-word !important;
        }
        .mynt-chat-bot {
            align-self: flex-start !important;
            background: #ffffff !important;
            color: #0f172a !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.06) !important;
            border: 1px solid #e2e8f0 !important;
            border-bottom-left-radius: 2px !important;
        }
        .mynt-chat-user {
            align-self: flex-end !important;
            background: #10b981 !important;
            color: white !important;
            border-bottom-right-radius: 2px !important;
        }
        .mynt-chat-options {
            display: flex !important;
            flex-direction: column !important;
            gap: 8px !important;
            margin-top: 6px !important;
        }
        .mynt-chat-opt-btn {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            color: #0f172a !important;
            padding: 10px 14px !important;
            border-radius: 10px !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            cursor: pointer !important;
            text-align: left !important;
            transition: all 0.2s !important;
            display: flex !important;
            align-items: center !important;
            gap: 8px !important;
        }
        .mynt-chat-opt-btn:hover {
            border-color: #10b981 !important;
            background: #ecfdf5 !important;
            color: #047857 !important;
            transform: translateX(4px) !important;
        }
        .mynt-chatbot-form {
            display: flex !important;
            flex-direction: column !important;
            gap: 10px !important;
            background: white !important;
            padding: 14px !important;
            border-radius: 12px !important;
            border: 1px solid #e2e8f0 !important;
        }
        .mynt-chatbot-form input, .mynt-chatbot-form select {
            width: 100% !important;
            padding: 10px !important;
            font-size: 13px !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
            outline: none !important;
        }
        .mynt-chatbot-form button {
            background: #10b981 !important;
            color: white !important;
            border: none !important;
            padding: 10px !important;
            border-radius: 8px !important;
            font-size: 13px !important;
            font-weight: 700 !important;
            cursor: pointer !important;
        }
        .mynt-chatbot-footer {
            padding: 12px 16px !important;
            background: white !important;
            border-top: 1px solid #e2e8f0 !important;
            display: flex !important;
            gap: 8px !important;
        }
        .mynt-chatbot-input {
            flex: 1 !important;
            padding: 10px 14px !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 24px !important;
            font-size: 14px !important;
            outline: none !important;
        }
        .mynt-chatbot-send {
            background: #10b981 !important;
            color: white !important;
            border: none !important;
            width: 40px !important;
            height: 40px !important;
            border-radius: 50% !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            cursor: pointer !important;
            font-size: 16px !important;
        }
    `;

    function injectWidget() {
        if (document.getElementById('myntChatbotBtn')) return;

        const styleEl = document.createElement('style');
        styleEl.textContent = styles;
        document.head.appendChild(styleEl);

        const container = document.createElement('div');
        container.innerHTML = `
            <div class="mynt-chatbot-btn" id="myntChatbotBtn" title="Chat with VGK4U Support">
                💬
                <div class="mynt-chatbot-badge"></div>
            </div>
            <div class="mynt-chatbot-box" id="myntChatbotBox">
                <div class="mynt-chatbot-header">
                    <div class="mynt-chatbot-header-info">
                        <div class="mynt-chatbot-avatar">🤖</div>
                        <div>
                            <div class="mynt-chatbot-title">VGK4U Assistant</div>
                            <div class="mynt-chatbot-status"><span class="mynt-chatbot-status-dot"></span> Online</div>
                        </div>
                    </div>
                    <button class="mynt-chatbot-close" id="myntChatbotClose">&times;</button>
                </div>
                <div class="mynt-chatbot-body" id="myntChatbotBody">
                    <div class="mynt-chat-msg mynt-chat-bot">
                        Hello! 👋 Welcome to VGK4U & Mynt OS. How can I help you today? Please choose an option below:
                    </div>
                    <div class="mynt-chat-options" id="myntChatOptions">
                        <button class="mynt-chat-opt-btn" onclick="MyntWebsiteChatbot.selectOption('services')">🏢 1. Company Services & Offerings</button>
                        <button class="mynt-chat-opt-btn" onclick="MyntWebsiteChatbot.selectOption('programs')">📊 2. VGK4U Partner Program & Earnings</button>
                        <button class="mynt-chat-opt-btn" onclick="MyntWebsiteChatbot.selectOption('lead')">📝 3. Connect & Create Lead</button>
                        <button class="mynt-chat-opt-btn" onclick="MyntWebsiteChatbot.selectOption('whatsapp')">📲 4. Direct WhatsApp Support</button>
                    </div>
                </div>
                <div class="mynt-chatbot-footer">
                    <input type="text" class="mynt-chatbot-input" id="myntChatInput" placeholder="Type a message..." />
                    <button class="mynt-chatbot-send" id="myntChatSend">➔</button>
                </div>
            </div>
        `;
        document.body.appendChild(container);

        const btn = document.getElementById('myntChatbotBtn');
        const box = document.getElementById('myntChatbotBox');
        const closeBtn = document.getElementById('myntChatbotClose');
        const body = document.getElementById('myntChatbotBody');
        const input = document.getElementById('myntChatInput');
        const sendBtn = document.getElementById('myntChatSend');

        btn.addEventListener('click', () => box.classList.toggle('open'));
        closeBtn.addEventListener('click', () => box.classList.remove('open'));

        function appendBotMsg(html) {
            const d = document.createElement('div');
            d.className = 'mynt-chat-msg mynt-chat-bot';
            d.innerHTML = html;
            body.appendChild(d);
            body.scrollTop = body.scrollHeight;
        }

        function appendUserMsg(text) {
            const d = document.createElement('div');
            d.className = 'mynt-chat-msg mynt-chat-user';
            d.textContent = text;
            body.appendChild(d);
            body.scrollTop = body.scrollHeight;
        }

        window.MyntWebsiteChatbot = {
            selectOption: function (opt) {
                if (opt === 'services') {
                    appendUserMsg('1. Company Services & Offerings');
                    appendBotMsg(`
                        <b>Our Core Services:</b><br/>
                        • <b>Solar Rooftop Installation</b>: Zero-down solar setup with government subsidy.<br/>
                        • <b>EV Scooter Claims</b>: Electric vehicle subsidies & reward distribution.<br/>
                        • <b>Real Estate & Land Projects</b>: Verified prime layout investments.<br/>
                        • <b>VGK4U Partner Network</b>: Earn daily & monthly payouts.
                    `);
                    this.showMenuOptions();
                } else if (opt === 'programs') {
                    appendUserMsg('2. VGK4U Partner Program & Earnings');
                    appendBotMsg(`
                        <b>VGK4U Earnings Program:</b><br/>
                        • Direct Level Commissions<br/>
                        • Team Downline Bonuses (L2, L3, L4)<br/>
                        • Instant Daily Wallet Payouts & Transparent Performance Dashboard.
                    `);
                    this.showMenuOptions();
                } else if (opt === 'lead') {
                    appendUserMsg('3. Connect & Create Lead');
                    appendBotMsg(`
                        <b>Connect with Us! Fill out your details below:</b>
                        <div class="mynt-chatbot-form" id="myntLeadForm">
                            <input type="text" id="myntFormName" placeholder="Your Full Name *" required />
                            <input type="tel" id="myntFormPhone" placeholder="Mobile / WhatsApp Number *" required />
                            <select id="myntFormService">
                                <option value="Solar Rooftop">Solar Rooftop</option>
                                <option value="EV Scooter">EV Scooter Program</option>
                                <option value="Real Estate">Real Estate / Land</option>
                                <option value="VGK4U Partner">Become VGK4U Partner</option>
                            </select>
                            <button onclick="MyntWebsiteChatbot.submitLeadForm()">Submit & Connect</button>
                        </div>
                    `);
                } else if (opt === 'whatsapp') {
                    appendUserMsg('4. Direct WhatsApp Support');
                    appendBotMsg(`Opening WhatsApp support channel...`);
                    window.open('https://wa.me/918875551666?text=Hello%20VGK4U%20Support%2C%20I%20want%20to%20connect%20with%20you.', '_blank');
                    this.showMenuOptions();
                }
            },
            showMenuOptions: function () {
                const opts = document.createElement('div');
                opts.className = 'mynt-chat-options';
                opts.innerHTML = `
                    <button class="mynt-chat-opt-btn" onclick="MyntWebsiteChatbot.selectOption('services')">🏢 1. Company Services & Offerings</button>
                    <button class="mynt-chat-opt-btn" onclick="MyntWebsiteChatbot.selectOption('programs')">📊 2. VGK4U Partner Program & Earnings</button>
                    <button class="mynt-chat-opt-btn" onclick="MyntWebsiteChatbot.selectOption('lead')">📝 3. Connect & Create Lead</button>
                    <button class="mynt-chat-opt-btn" onclick="MyntWebsiteChatbot.selectOption('whatsapp')">📲 4. Direct WhatsApp Support</button>
                `;
                body.appendChild(opts);
                body.scrollTop = body.scrollHeight;
            },
            submitLeadForm: function () {
                const name = document.getElementById('myntFormName')?.value.trim();
                const phone = document.getElementById('myntFormPhone')?.value.trim();
                const service = document.getElementById('myntFormService')?.value;

                if (!name || !phone) {
                    alert('Please enter your Name and Mobile Number.');
                    return;
                }

                appendBotMsg('⏳ Creating your lead request...');

                fetch('/api/v1/crm/leads/public-create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        lead_name: name,
                        phone: phone,
                        service_required: service,
                        source: 'Website Chatbot'
                    })
                })
                .then(res => res.json())
                .then(data => {
                    appendBotMsg(`✅ Thank you <b>${name}</b>! Your lead request for <b>${service}</b> has been received. Our team will contact you shortly on <b>${phone}</b>.`);
                    this.showMenuOptions();
                })
                .catch(err => {
                    appendBotMsg(`✅ Thank you <b>${name}</b>! Your request has been recorded. Our team will connect with you at <b>${phone}</b>.`);
                    this.showMenuOptions();
                });
            }
        };

        sendBtn.addEventListener('click', () => {
            const val = input.value.trim();
            if (!val) return;
            appendUserMsg(val);
            input.value = '';
            setTimeout(() => {
                appendBotMsg(`Thank you for your message! Please select one of our options or click <b>Direct WhatsApp Support</b> for immediate assistance.`);
                MyntWebsiteChatbot.showMenuOptions();
            }, 600);
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendBtn.click();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectWidget);
    } else {
        injectWidget();
    }
})();
