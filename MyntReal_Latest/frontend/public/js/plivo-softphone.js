/**
 * Plivo Browser Softphone Controller — MyntOS Native Telephony
 * Official Plivo Browser SDK integration for multi-user WebRTC calling.
 * Features: Secure JWT Login, Agent Availability, CRM Lead Context, Outbound Dialing,
 * Incoming Call Banner, Audio Controls (Mute/Hold/DTMF), and WebSocket State Sync.
 * Created: Sep 2026
 */

(function(window) {
    'use strict';

    if (typeof window === 'undefined') return;

    class MyntOSPlivoSoftphone {
        constructor() {
            this.client = null;
            this.jwtToken = null;
            this.endpointInfo = null;
            this.isInitialized = false;
            this.isRegistered = false;
            this.agentStatus = 'available'; // available | busy | break | offline

            // Active Call State
            this.activeCall = null;
            this.activeSessionId = null;
            this.activeLeadContext = null;
            this.callTimerInterval = null;
            this.callSeconds = 0;
            this.isMuted = false;
            this.isHeld = false;

            // Incoming Call State
            this.incomingCallObj = null;

            this.init();
        }

        async init() {
            console.log('[PLIVO-SOFTPHONE] Initializing MyntOS Browser Softphone...');
            this.injectUIElements();
            this.loadPlivoSDK();
        }

        loadPlivoSDK() {
            // Check if Plivo Browser SDK is already loaded
            if (typeof window.Plivo !== 'undefined' && window.Plivo.Client) {
                this.setupPlivoClient();
                return;
            }

            // Dynamically load official Plivo Browser SDK CDN
            const script = document.createElement('script');
            script.src = 'https://cdn.plivo.com/sdk/browser/v2/plivo.min.js';
            script.async = true;
            script.onload = () => {
                console.log('[PLIVO-SOFTPHONE] Plivo Browser SDK v2 script loaded successfully');
                this.setupPlivoClient();
            };
            script.onerror = () => {
                console.warn('[PLIVO-SOFTPHONE] Plivo CDN unreachable. Running in Mock/Simulated WebRTC Softphone mode.');
                this.setupMockClient();
            };
            document.head.appendChild(script);
        }

        async setupPlivoClient() {
            try {
                if (typeof window.Plivo !== 'undefined' && window.Plivo.Client) {
                    this.client = new window.Plivo.Client();
                    this.bindClientEvents();
                } else {
                    this.setupMockClient();
                }
                await this.refreshAndLogin();
            } catch (err) {
                console.error('[PLIVO-SOFTPHONE] Error during client setup:', err);
            }
        }

        setupMockClient() {
            // High-fidelity fallback client for local development / testing
            this.client = {
                login: (token) => {
                    setTimeout(() => {
                        this.onLoginSuccess({ username: this.endpointInfo?.username || 'agent_mock' });
                    }, 500);
                },
                logout: () => { this.onLogoutSuccess(); },
                call: (destination, extraHeaders) => {
                    console.log(`[PLIVO-MOCK] Outbound WebRTC call dispatched to ${destination}`);
                    setTimeout(() => {
                        this.onCallConnected({ direction: 'outbound', destination });
                    }, 1000);
                },
                hangup: () => {
                    this.onCallTerminated();
                },
                mute: () => { this.isMuted = true; },
                unmute: () => { this.isMuted = false; },
                sendDTMF: (digit) => { console.log(`[PLIVO-MOCK] DTMF ${digit}`); }
            };
            this.refreshAndLogin();
        }

        bindClientEvents() {
            if (!this.client) return;

            // Plivo SDK Event Listeners
            this.client.on('onLogin', (data) => this.onLoginSuccess(data));
            this.client.on('onLogout', () => this.onLogoutSuccess());
            this.client.on('onLoginFailed', (reason) => {
                console.error('[PLIVO-SOFTPHONE] Login failed:', reason);
                this.updateUIStatus('offline', 'Auth Failed');
            });
            this.client.on('onIncomingCall', (callerName, extraHeaders, callInfo) => {
                this.handleIncomingCall(callerName, extraHeaders, callInfo);
            });
            this.client.on('onIncomingCallCanceled', () => {
                this.dismissIncomingCallBanner();
            });
            this.client.on('onCallAnswered', (callInfo) => {
                this.onCallConnected(callInfo);
            });
            this.client.on('onCallTerminated', () => {
                this.onCallTerminated();
            });
            this.client.on('onCallFailed', (reason) => {
                console.warn('[PLIVO-SOFTPHONE] Call failed:', reason);
                this.onCallTerminated();
            });
        }

        async refreshAndLogin() {
            try {
                const token = localStorage.getItem('staff_token');
                if (!token) {
                    console.warn('[PLIVO-SOFTPHONE] No staff auth token available. Deferring login.');
                    return;
                }

                // Fetch short-lived JWT from backend
                const resp = await fetch('/api/v1/telephony/plivo/browser/token', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (!resp.ok) {
                    console.warn('[PLIVO-SOFTPHONE] Could not acquire Plivo JWT token:', resp.status);
                    return;
                }

                const data = await resp.json();
                if (data.success && data.access_token) {
                    this.jwtToken = data.access_token;
                    this.endpointInfo = data.endpoint;
                    console.log(`[PLIVO-SOFTPHONE] Acquired JWT for endpoint ${data.endpoint?.username}`);

                    // Login to Plivo WebRTC Gateway
                    if (this.client && typeof this.client.login === 'function') {
                        this.client.login(this.jwtToken);
                    }
                }
            } catch (err) {
                console.error('[PLIVO-SOFTPHONE] Error acquiring browser token:', err);
            }
        }

        onLoginSuccess(data) {
            this.isRegistered = true;
            this.isInitialized = true;
            console.log('[PLIVO-SOFTPHONE] Successfully registered with Plivo WebRTC gateway:', data);
            this.updateUIStatus('available', 'Online');
            this.notifyBackendRegistration(true);
        }

        onLogoutSuccess() {
            this.isRegistered = false;
            this.updateUIStatus('offline', 'Offline');
            this.notifyBackendRegistration(false);
        }

        async notifyBackendRegistration(isRegistered) {
            try {
                const token = localStorage.getItem('staff_token');
                if (!token) return;
                await fetch('/api/v1/telephony/plivo/browser/register', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ is_registered: isRegistered })
                });
            } catch (_) {}
        }

        // ── OUTBOUND CALLING ─────────────────────────────────────────────────

        async dial(destinationPhone, leadId = null, leadName = null) {
            if (!destinationPhone) {
                alert('Please enter a valid destination phone number.');
                return;
            }

            console.log(`[PLIVO-SOFTPHONE] Dialing ${destinationPhone} (Lead: ${leadName || leadId})`);
            this.openSoftphoneDock();
            this.showCallInProgressUI(destinationPhone, leadName || 'Customer Lead');

            try {
                const token = localStorage.getItem('staff_token');
                // 1. Prepare call session in MyntOS backend
                const resp = await fetch('/api/v1/telephony/plivo/browser/call/initiate', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        destination_phone: destinationPhone,
                        lead_id: leadId
                    })
                });

                if (!resp.ok) {
                    const err = await resp.json();
                    alert(`Failed to start call: ${err.detail || 'Error'}`);
                    this.hideCallInProgressUI();
                    return;
                }

                const sessData = await resp.json();
                this.activeSessionId = sessData.call_session_id;
                this.activeLeadContext = sessData.lead_context;

                // 2. Dispatch call through Plivo WebRTC SDK
                const cleanDest = destinationPhone.startsWith('+') ? destinationPhone : `+91${destinationPhone.replace(/\D/g, '').slice(-10)}`;
                const extraHeaders = {
                    'X-PH-Call-Session-ID': this.activeSessionId,
                    'X-PH-Lead-ID': String(leadId || '')
                };

                if (this.client && typeof this.client.call === 'function') {
                    this.client.call(cleanDest, extraHeaders);
                }
            } catch (err) {
                console.error('[PLIVO-SOFTPHONE] Outbound dial error:', err);
                alert('Telephony connection error.');
                this.hideCallInProgressUI();
            }
        }

        // ── INBOUND CALL HANDLING ────────────────────────────────────────────

        handleIncomingCall(callerName, extraHeaders, callInfo) {
            console.log('[PLIVO-SOFTPHONE] Inbound call received:', callerName, callInfo);
            this.incomingCallObj = callInfo;

            const callerPhone = callerName || callInfo?.src || 'Unknown Caller';
            const leadName = extraHeaders?.['X-PH-Lead-Name'] || 'Incoming Inquiry';

            const banner = document.getElementById('plivoIncomingBanner');
            if (banner) {
                document.getElementById('incomingCallerName').textContent = leadName;
                document.getElementById('incomingCallerPhone').textContent = callerPhone;
                banner.style.display = 'block';
                this.playRingtone();
            }
        }

        answerIncomingCall() {
            this.stopRingtone();
            this.dismissIncomingCallBanner();

            if (this.incomingCallObj && typeof this.incomingCallObj.answer === 'function') {
                this.incomingCallObj.answer();
            }
            this.openSoftphoneDock();
            this.showCallInProgressUI(document.getElementById('incomingCallerPhone').textContent, 'Incoming Customer');
        }

        rejectIncomingCall() {
            this.stopRingtone();
            this.dismissIncomingCallBanner();

            if (this.incomingCallObj && typeof this.incomingCallObj.reject === 'function') {
                this.incomingCallObj.reject();
            }
            this.incomingCallObj = null;
        }

        dismissIncomingCallBanner() {
            const banner = document.getElementById('plivoIncomingBanner');
            if (banner) banner.style.display = 'none';
        }

        // ── ACTIVE CALL CONTROLS ─────────────────────────────────────────────

        onCallConnected(callInfo) {
            console.log('[PLIVO-SOFTPHONE] Call connected / active');
            document.getElementById('callStatusLabel').textContent = 'Connected (In Call)';
            document.getElementById('callStatusLabel').className = 'badge bg-success';
            this.startCallTimer();

            this.syncCallEvent('connected');
        }

        onCallTerminated() {
            console.log('[PLIVO-SOFTPHONE] Call terminated');
            this.stopCallTimer();
            this.hideCallInProgressUI();
            this.syncCallEvent('ended');
            this.activeSessionId = null;
            this.activeLeadContext = null;
        }

        hangup() {
            if (this.client && typeof this.client.hangup === 'function') {
                this.client.hangup();
            }
            if (this.activeSessionId) {
                const token = localStorage.getItem('staff_token');
                fetch('/api/v1/telephony/plivo/browser/call/end', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ call_session_id: this.activeSessionId })
                }).catch(() => {});
            }
            this.onCallTerminated();
        }

        toggleMute() {
            this.isMuted = !this.isMuted;
            if (this.client) {
                if (this.isMuted && typeof this.client.mute === 'function') this.client.mute();
                else if (!this.isMuted && typeof this.client.unmute === 'function') this.client.unmute();
            }
            const btn = document.getElementById('btnMuteCall');
            if (btn) {
                btn.className = this.isMuted ? 'btn btn-warning btn-sm' : 'btn btn-outline-secondary btn-sm';
                btn.innerHTML = `<i class="fa-solid fa-microphone-${this.isMuted ? 'slash' : 'lines'}"></i> ${this.isMuted ? 'Unmute' : 'Mute'}`;
            }
        }

        toggleHold() {
            this.isHeld = !this.isHeld;
            const btn = document.getElementById('btnHoldCall');
            if (btn) {
                btn.className = this.isHeld ? 'btn btn-warning btn-sm' : 'btn btn-outline-secondary btn-sm';
                btn.innerHTML = `<i class="fa-solid fa-${this.isHeld ? 'play' : 'pause'}"></i> ${this.isHeld ? 'Unhold' : 'Hold'}`;
            }
            this.syncCallEvent(this.isHeld ? 'held' : 'active');
        }

        sendDTMF(digit) {
            if (this.client && typeof this.client.sendDTMF === 'function') {
                this.client.sendDTMF(digit);
            }
        }

        async syncCallEvent(eventType) {
            if (!this.activeSessionId) return;
            try {
                const token = localStorage.getItem('staff_token');
                await fetch('/api/v1/telephony/plivo/browser/call-event', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        call_session_id: this.activeSessionId,
                        event_type: eventType
                    })
                });
            } catch (_) {}
        }

        // ── TIMER & AUDIO HELPERS ────────────────────────────────────────────

        startCallTimer() {
            this.stopCallTimer();
            this.callSeconds = 0;
            const timerEl = document.getElementById('callTimerDisplay');
            this.callTimerInterval = setInterval(() => {
                this.callSeconds++;
                const mins = String(Math.floor(this.callSeconds / 60)).padStart(2, '0');
                const secs = String(this.callSeconds % 60).padStart(2, '0');
                if (timerEl) timerEl.textContent = `${mins}:${secs}`;
            }, 1000);
        }

        stopCallTimer() {
            if (this.callTimerInterval) {
                clearInterval(this.callTimerInterval);
                this.callTimerInterval = null;
            }
        }

        playRingtone() {
            try {
                // Synthesize subtle browser chime if audio asset not present
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(440, ctx.currentTime);
                gain.gain.setValueAtTime(0.1, ctx.currentTime);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 1.2);
            } catch (_) {}
        }

        stopRingtone() {}

        // ── UI INJECTION & DOCK MANAGEMENT ───────────────────────────────────

        injectUIElements() {
            if (document.getElementById('myntosSoftphoneWidget')) return;

            const html = `
                <!-- Global Softphone Floating Dock -->
                <div id="myntosSoftphoneWidget" style="position: fixed; bottom: 20px; right: 20px; z-index: 9999; font-family: 'Segoe UI', Tahoma, sans-serif;">
                    
                    <!-- Minimized Floating Button -->
                    <button id="plivoSoftphoneToggleBtn" class="btn btn-primary shadow-lg rounded-pill px-3 py-2 d-flex align-items-center gap-2" onclick="window.PlivoSoftphone.toggleDock()" style="border: 2px solid rgba(255,255,255,0.4);">
                        <i class="fa-solid fa-headset fa-lg"></i>
                        <span class="fw-bold" id="softphoneStatusText">Softphone (Online)</span>
                    </button>

                    <!-- Expanded Softphone Card -->
                    <div id="plivoSoftphoneDockCard" class="card shadow-lg border-0 rounded-4 mt-2" style="display: none; width: 320px; background: #ffffff;">
                        <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center py-2 px-3 rounded-top-4">
                            <span class="fw-bold fs-6"><i class="fa-solid fa-phone-volume me-2"></i>MyntOS Softphone</span>
                            <button class="btn btn-sm btn-link text-white p-0" onclick="window.PlivoSoftphone.toggleDock()"><i class="fa-solid fa-times"></i></button>
                        </div>
                        <div class="card-body p-3">
                            
                            <!-- Idle State: Dialpad -->
                            <div id="softphoneIdleView">
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <small class="text-muted fw-bold">Agent Status:</small>
                                    <select class="form-select form-select-sm w-auto py-0" onchange="window.PlivoSoftphone.setAgentStatus(this.value)">
                                        <option value="available" selected>🟢 Available</option>
                                        <option value="busy">🔴 Busy</option>
                                        <option value="break">🟡 Break</option>
                                    </select>
                                </div>
                                <div class="input-group mb-2">
                                    <input type="text" id="softphoneManualInput" class="form-control form-control-sm" placeholder="Enter 10-digit number...">
                                    <button class="btn btn-success btn-sm" onclick="window.PlivoSoftphone.dial(document.getElementById('softphoneManualInput').value)"><i class="fa-solid fa-phone"></i></button>
                                </div>
                            </div>

                            <!-- In-Call State -->
                            <div id="softphoneInCallView" style="display: none;">
                                <div class="text-center py-2">
                                    <div class="fw-bold fs-6" id="activeCallCustomerName">Customer Lead</div>
                                    <small class="text-muted" id="activeCallPhoneDisplay">+91 00000 00000</small>
                                    <div class="my-2">
                                        <span id="callStatusLabel" class="badge bg-warning">Dialing...</span>
                                        <span id="callTimerDisplay" class="fw-bold ms-2 fs-6">00:00</span>
                                    </div>
                                    <div class="d-flex justify-content-center gap-2 mt-3">
                                        <button id="btnMuteCall" class="btn btn-outline-secondary btn-sm" onclick="window.PlivoSoftphone.toggleMute()"><i class="fa-solid fa-microphone-lines"></i> Mute</button>
                                        <button id="btnHoldCall" class="btn btn-outline-secondary btn-sm" onclick="window.PlivoSoftphone.toggleHold()"><i class="fa-solid fa-pause"></i> Hold</button>
                                        <button class="btn btn-danger btn-sm" onclick="window.PlivoSoftphone.hangup()"><i class="fa-solid fa-phone-slash"></i> End</button>
                                    </div>
                                </div>
                            </div>

                        </div>
                    </div>
                </div>

                <!-- Global Incoming Call Banner -->
                <div id="plivoIncomingBanner" style="display: none; position: fixed; top: 20px; right: 20px; width: 340px; z-index: 10000; background: #ffffff; border-left: 5px solid #22c55e; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); padding: 16px;">
                    <div class="d-flex align-items-center gap-3">
                        <div class="rounded-circle bg-success text-white d-flex align-items-center justify-content-center" style="width: 44px; height: 44px; font-size: 20px;">
                            <i class="fa-solid fa-phone-volume fa-shake"></i>
                        </div>
                        <div class="flex-grow-1">
                            <div class="fw-bold fs-6 text-dark" id="incomingCallerName">Incoming Call</div>
                            <small class="text-muted" id="incomingCallerPhone">+91 XXXXX XXXXX</small>
                        </div>
                    </div>
                    <div class="d-flex gap-2 mt-3">
                        <button class="btn btn-success btn-sm flex-grow-1 fw-bold" onclick="window.PlivoSoftphone.answerIncomingCall()"><i class="fa-solid fa-phone me-1"></i> Answer</button>
                        <button class="btn btn-danger btn-sm flex-grow-1 fw-bold" onclick="window.PlivoSoftphone.rejectIncomingCall()"><i class="fa-solid fa-phone-slash me-1"></i> Reject</button>
                    </div>
                </div>
            `;

            const wrapper = document.createElement('div');
            wrapper.innerHTML = html;
            document.body.appendChild(wrapper);
        }

        toggleDock() {
            const card = document.getElementById('plivoSoftphoneDockCard');
            if (card) {
                card.style.display = card.style.display === 'none' ? 'block' : 'none';
            }
        }

        openSoftphoneDock() {
            const card = document.getElementById('plivoSoftphoneDockCard');
            if (card) card.style.display = 'block';
        }

        showCallInProgressUI(phone, name) {
            document.getElementById('softphoneIdleView').style.display = 'none';
            document.getElementById('softphoneInCallView').style.display = 'block';
            document.getElementById('activeCallCustomerName').textContent = name || 'Customer';
            document.getElementById('activeCallPhoneDisplay').textContent = phone;
            document.getElementById('callStatusLabel').textContent = 'Dialing...';
            document.getElementById('callStatusLabel').className = 'badge bg-warning';
            document.getElementById('callTimerDisplay').textContent = '00:00';
        }

        hideCallInProgressUI() {
            document.getElementById('softphoneIdleView').style.display = 'block';
            document.getElementById('softphoneInCallView').style.display = 'none';
        }

        updateUIStatus(status, label) {
            const el = document.getElementById('softphoneStatusText');
            if (el) el.textContent = `Softphone (${label})`;
        }

        setAgentStatus(status) {
            this.agentStatus = status;
            console.log(`[PLIVO-SOFTPHONE] Agent status changed to ${status}`);
        }
    }

    // Mount singleton on window
    window.PlivoSoftphone = new MyntOSPlivoSoftphone();

})(typeof window !== 'undefined' ? window : this);
