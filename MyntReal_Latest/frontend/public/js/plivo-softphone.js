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

    // Guaranteed Singleton: Prevent duplicate script instances and redundant Plivo client connections
    if (window.PlivoSoftphone) {
        console.log('[PLIVO-SOFTPHONE] Reusing existing singleton instance on window.');
        return;
    }

    class MyntOSPlivoSoftphone {
        constructor() {
            this.client = null;
            this.jwtToken = null;
            this.endpointInfo = null;
            this.isInitialized = false;
            this.isRegistered = false;
            this.agentStatus = 'available'; // available | busy | break | offline

            // Registration State Machine
            this.registrationState = 'UNINITIALIZED'; // 'UNINITIALIZED' | 'CONNECTING' | 'REGISTERED' | 'REGISTRATION_FAILED'
            this.registrationPromise = null;
            this.registrationResolve = null;
            this.registrationReject = null;
            this.loginAttemptInProgress = false;

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

            if (document.readyState === 'loading' || !document.body) {
                document.addEventListener('DOMContentLoaded', () => this.init());
            } else {
                this.init();
            }
        }

        async init() {
            if (this.isInitialized) return;
            this.isInitialized = true;
            console.log('[PLIVO-SOFTPHONE] Initializing MyntOS Browser Softphone...');
            this.injectUIElements();
            this.ensureRemoteAudioElement();
            this.prewarmMicrophone();
            this.loadPlivoSDK();
        }

        ensureRemoteAudioElement() {
            if (!document.body) return;
            let audioEl = document.getElementById('plivoRemoteAudio');
            if (!audioEl) {
                audioEl = document.createElement('audio');
                audioEl.id = 'plivoRemoteAudio';
                audioEl.autoplay = true;
                audioEl.volume = 1.0;
                audioEl.muted = false;
                audioEl.setAttribute('playsinline', 'true');
                audioEl.style.display = 'none';
                document.body.appendChild(audioEl);
            } else {
                audioEl.volume = 1.0;
                audioEl.muted = false;
            }
        }

        async prewarmMicrophone() {
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({
                        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
                    });
                    // Verify tracks and stop test stream so Plivo SDK has exclusive, conflict-free mic access
                    stream.getTracks().forEach(t => t.stop());
                    console.log('[PLIVO-SOFTPHONE] Microphone verified and hardware AEC ready');
                } catch (micErr) {
                    console.warn('[PLIVO-SOFTPHONE] Mic pre-warm notice:', micErr);
                }
            }
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
                // Plivo WebRTC SDK requires HTTPS / secure context or localhost.
                // On insecure LAN HTTP (e.g. http://192.168.1.10:5001), navigator.mediaDevices may be restricted by modern mobile browsers.
                const isSecureOrLocal = window.isSecureContext || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
                const hasMedia = typeof navigator !== 'undefined' && navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === 'function';

                if (!isSecureOrLocal && !hasMedia) {
                    console.warn('[PLIVO-SOFTPHONE] Insecure HTTP context detected; Plivo WebRTC requires HTTPS or localhost. Direct SIM & MyOperator calling remain active.');
                    this.setupMockClient();
                    return;
                }

                const audioConstraints = {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                };

                if (typeof window.Plivo !== 'undefined') {
                    if (typeof window.Plivo === 'function') {
                        this.sdk = new window.Plivo({
                            allowMultipleIncomingCalls: true,
                            audioConstraints: audioConstraints,
                            audioElementOption: {
                                remoteAudioId: 'plivoRemoteAudio'
                            }
                        });
                        this.client = this.sdk.client || this.sdk;
                    } else if (window.Plivo.Client) {
                        this.client = new window.Plivo.Client({
                            audioConstraints: audioConstraints
                        });
                    }

                    // Attach remote audio element for Plivo WebRTC media stream negotiation
                    const audioEl = document.getElementById('plivoRemoteAudio');
                    if (audioEl && this.client) {
                        if (typeof this.client.setAudioElement === 'function') {
                            this.client.setAudioElement(audioEl);
                        } else if (typeof this.client.setAudioElementOption === 'function') {
                            this.client.setAudioElementOption({ remoteAudioId: 'plivoRemoteAudio' });
                        }
                    }

                    this.bindClientEvents();
                } else {
                    this.setupMockClient();
                }
                await this.refreshAndLogin();
            } catch (err) {
                console.warn('[PLIVO-SOFTPHONE] WebRTC client setup skipped (insecure context or unsupported environment):', err);
                this.setupMockClient();
            }
        }

        setupMockClient() {
            // Informative fallback client for local development / testing without live Plivo credentials
            this.client = {
                loginWithAccessToken: (token) => {
                    setTimeout(() => {
                        this.onLoginSuccess({ username: this.endpointInfo?.username || 'agent_mock' });
                    }, 500);
                },
                login: (token) => {
                    setTimeout(() => {
                        this.onLoginSuccess({ username: this.endpointInfo?.username || 'agent_mock' });
                    }, 500);
                },
                logout: () => { this.onLogoutSuccess(); },
                call: (destination, extraHeaders) => {
                    console.warn(`[PLIVO-MOCK] Outbound call to ${destination} blocked: Plivo API keys required in server environment.`);
                    alert(`To place live outbound phone calls to ${destination}, please configure the PLIVO_AUTH_ID and PLIVO_AUTH_TOKEN environment variables on the server.`);
                    this.onCallTerminated();
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
                this.onLoginFailed(reason);
            });
            this.client.on('onIncomingCall', (callerName, extraHeaders, callInfo) => {
                this.handleIncomingCall(callerName, extraHeaders, callInfo);
            });
            this.client.on('onIncomingCallCanceled', () => {
                this.dismissIncomingCallBanner();
            });
            this.client.on('onCallRinging', (callInfo) => {
                this.onCallRinging(callInfo);
            });
            this.client.on('onRinging', (callInfo) => {
                this.onCallRinging(callInfo);
            });
            this.client.on('onCallAnswered', (callInfo) => {
                this.onCallConnected(callInfo);
            });
            this.client.on('onMediaConnected', (callInfo) => {
                console.log('[PLIVO-SOFTPHONE] Media stream established / active');
                this.onMediaConnected(callInfo);
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
            if (this.isRegistered && this.registrationState === 'REGISTERED') {
                return true;
            }

            if (this.loginAttemptInProgress && this.registrationPromise) {
                console.log('[PLIVO-SOFTPHONE] Registration already in progress. Awaiting existing promise...');
                return this.registrationPromise;
            }

            this.loginAttemptInProgress = true;
            this.registrationState = 'CONNECTING';
            this.updateUIStatus('connecting', 'Connecting...');

            this.registrationPromise = new Promise((resolve, reject) => {
                this.registrationResolve = resolve;
                this.registrationReject = reject;
            });

            try {
                const token = localStorage.getItem('staff_token') || localStorage.getItem('token');
                if (!token) {
                    console.warn('[PLIVO-SOFTPHONE] No staff auth token available. Deferring login.');
                    this.registrationState = 'UNINITIALIZED';
                    this.loginAttemptInProgress = false;
                    if (this.registrationReject) this.registrationReject(new Error('No auth token'));
                    this.registrationPromise = null;
                    return false;
                }

                // Fetch short-lived JWT from backend
                const resp = await fetch('/api/v1/telephony/plivo/browser/token', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (!resp.ok) {
                    console.warn('[PLIVO-SOFTPHONE] Could not acquire Plivo JWT token:', resp.status);
                    this.registrationState = 'REGISTRATION_FAILED';
                    this.loginAttemptInProgress = false;
                    if (this.registrationReject) this.registrationReject(new Error(`HTTP ${resp.status}`));
                    this.registrationPromise = null;
                    return false;
                }

                const data = await resp.json();
                if (data.success && data.access_token) {
                    this.jwtToken = data.access_token;
                    this.endpointInfo = data.endpoint;
                    console.log(`[PLIVO-SOFTPHONE] Acquired JWT for endpoint ${data.endpoint?.username}`);

                    // Login to Plivo WebRTC Gateway
                    if (this.client) {
                        if (typeof this.client.loginWithAccessToken === 'function') {
                            this.client.loginWithAccessToken(this.jwtToken);
                        } else if (typeof this.client.login === 'function') {
                            this.client.login(this.jwtToken);
                        }

                        // Wait up to 4 seconds for onLoginSuccess event to set isRegistered = true
                        for (let i = 0; i < 20; i++) {
                            if (this.isRegistered) break;
                            await new Promise((r) => setTimeout(r, 200));
                        }
                    }
                } else {
                    this.registrationState = 'REGISTRATION_FAILED';
                    this.loginAttemptInProgress = false;
                    if (this.registrationReject) this.registrationReject(new Error('Invalid token response'));
                    this.registrationPromise = null;
                    return false;
                }
            } catch (err) {
                console.error('[PLIVO-SOFTPHONE] Error acquiring browser token:', err);
                this.registrationState = 'REGISTRATION_FAILED';
                this.loginAttemptInProgress = false;
                if (this.registrationReject) this.registrationReject(err);
                this.registrationPromise = null;
                return false;
            }

            return this.registrationPromise;
        }

        onLoginSuccess(data) {
            this.isRegistered = true;
            this.isInitialized = true;
            this.registrationState = 'REGISTERED';
            this.loginAttemptInProgress = false;
            console.log('[PLIVO-SOFTPHONE] Successfully registered with Plivo WebRTC gateway:', data);
            this.updateUIStatus('available', 'Online');
            this.notifyBackendRegistration(true);
            if (this.registrationResolve) {
                this.registrationResolve(true);
                this.registrationResolve = null;
                this.registrationReject = null;
            }
            this.registrationPromise = null;
        }

        onLoginFailed(reason) {
            console.warn('[PLIVO-SOFTPHONE] WebRTC registration failed:', reason);
            this.isRegistered = false;
            this.registrationState = 'REGISTRATION_FAILED';
            this.loginAttemptInProgress = false;
            this.updateUIStatus('offline', 'Offline');
            if (this.registrationReject) {
                this.registrationReject(new Error(typeof reason === 'string' ? reason : JSON.stringify(reason || 'Login failed')));
                this.registrationResolve = null;
                this.registrationReject = null;
            }
            this.registrationPromise = null;
            // Controlled auto-retry after delay if not active in call
            if (!this.isCallActive) {
                setTimeout(() => {
                    if (!this.isRegistered && this.registrationState !== 'CONNECTING') {
                        this.refreshAndLogin().catch(() => {});
                    }
                }, 5000);
            }
        }

        onLogoutSuccess() {
            this.isRegistered = false;
            this.registrationState = 'UNINITIALIZED';
            this.loginAttemptInProgress = false;
            this.updateUIStatus('offline', 'Offline');
            this.notifyBackendRegistration(false);
        }

        async ensureRegistered(timeoutMs = 12000) {
            if (this.isRegistered && this.registrationState === 'REGISTERED') {
                return true;
            }

            let promiseToAwait = this.registrationPromise;
            if (!promiseToAwait && !this.loginAttemptInProgress) {
                promiseToAwait = this.refreshAndLogin();
            }

            if (!promiseToAwait) {
                return this.isRegistered && this.registrationState === 'REGISTERED';
            }

            const timeoutPromise = new Promise((_, reject) =>
                setTimeout(() => reject(new Error('Registration timed out')), timeoutMs)
            );

            try {
                await Promise.race([promiseToAwait, timeoutPromise]);
                return this.isRegistered && this.registrationState === 'REGISTERED';
            } catch (err) {
                console.warn('[PLIVO-SOFTPHONE] ensureRegistered notice:', err.message || err);
                return this.isRegistered && this.registrationState === 'REGISTERED';
            }
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

        // ── OUTBOUND CALLING WITH MULTI-METHOD SELECTOR ──────────────────────

        dialOutboundCall(number, leadId = null, leadName = null) {
            return this.dial(number, leadId, leadName);
        }

        openDialpadAndCall(number, leadName = null, leadId = null) {
            return this.openCallDialer({ phoneNumber: number, name: leadName, entityId: leadId, autoStart: true });
        }

        openDialpad(phoneNumber = '', contactName = '', leadId = null) {
            return this.openCallDialer({ phoneNumber, name: contactName, entityId: leadId, autoStart: false });
        }

        openCallDialer(intent) {
            if (!intent) return;
            const phone = (typeof intent === 'string' ? intent : (intent.phoneNumber || intent.phone || '')).trim();
            const name = (typeof intent === 'object' ? (intent.name || intent.contactName || '') : '') || 'Contact Lead';
            const entityId = typeof intent === 'object' ? (intent.entityId || intent.leadId || null) : null;
            const autoStart = typeof intent === 'object' ? !!intent.autoStart : false;

            this.activeDestination = phone;
            this.activeLeadName = name;
            this.activeLeadId = entityId;

            this.openSoftphoneDock();
            this.switchTab('keypad');

            const input = document.getElementById('softphoneDisplayInput');
            if (input) {
                input.value = phone ? phone.replace(/\D/g, '').slice(-10) : '';
                this.onKeypadInputChange(input.value);
            }

            const headerNameEl = document.getElementById('softphoneHeaderLeadName');
            if (headerNameEl) {
                if (name && name !== 'Contact Lead') {
                    headerNameEl.textContent = `👤 ${name}`;
                    headerNameEl.style.display = 'block';
                } else {
                    headerNameEl.style.display = 'none';
                }
            }

            if (autoStart && phone) {
                setTimeout(() => {
                    this.dial(phone, entityId, name);
                }, 150);
            }
        }

        async dial(destinationPhone, leadId = null, leadName = null, forceMethod = null) {
            if (!destinationPhone) {
                alert('Please enter a valid destination phone number.');
                return;
            }

            const cleanDest = destinationPhone.startsWith('+') ? destinationPhone : `+91${destinationPhone.replace(/\D/g, '').slice(-10)}`;
            const savedPref = sessionStorage.getItem('myntos_preferred_call_method');
            const selectedMethod = forceMethod || savedPref;

            if (!selectedMethod) {
                this.showCallMethodModal(cleanDest, leadId, leadName);
                return;
            }

            if (selectedMethod === 'mobile') {
                this.executeMobileDial(cleanDest);
            } else if (selectedMethod === 'myoperator') {
                this.executeMyOperatorDial(cleanDest, leadId, leadName);
            } else {
                this.executePlivoDial(cleanDest, leadId, leadName);
            }
        }

        closeCallMethodModal() {
            const modal = document.getElementById('myntosCallMethodModal');
            if (modal) {
                modal.style.display = 'none';
            }
        }

        showCallMethodModal(destinationPhone, leadId = null, leadName = null) {
            let modal = document.getElementById('myntosCallMethodModal');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'myntosCallMethodModal';
                document.body.appendChild(modal);

                // Close on Escape key
                window.addEventListener('keydown', (e) => {
                    if (e.key === 'Escape') {
                        const m = document.getElementById('myntosCallMethodModal');
                        if (m && m.style.display !== 'none') {
                            this.closeCallMethodModal();
                        }
                    }
                });
            }

            // Always ensure the modal is a top-level child of body
            if (modal.parentElement !== document.body) {
                document.body.appendChild(modal);
            }

            modal.style.cssText = `
                position: fixed !important; top: 0 !important; left: 0 !important; right: 0 !important; bottom: 0 !important;
                width: 100vw !important; height: 100vh !important; z-index: 2147483647 !important;
                display: flex !important; align-items: center !important; justify-content: center !important;
                padding: 16px !important; box-sizing: border-box !important; pointer-events: auto !important;
                isolation: isolate !important; filter: none !important; -webkit-filter: none !important;
                backdrop-filter: none !important; -webkit-backdrop-filter: none !important;
                background: transparent !important;
            `;

            const displayName = String(leadName || 'Customer Lead').replace(/["'<>]/g, '').trim() || 'Customer Lead';
            const cleanPhoneDisplay = destinationPhone || '—';

            modal.innerHTML = `
                <!-- 1. Dedicated Backdrop: Blur & Darken strictly behind dialog -->
                <div id="myntosCallMethodModalBackdrop" style="position: absolute !important; inset: 0 !important; width: 100% !important; height: 100% !important; background: rgba(15, 23, 42, 0.75) !important; backdrop-filter: blur(8px) !important; -webkit-backdrop-filter: blur(8px) !important; z-index: 1 !important; pointer-events: auto !important;" onclick="window.PlivoSoftphone.closeCallMethodModal()"></div>

                <!-- 2. Foreground Modal Dialog Box (100% Opaque, Crisp, High-Contrast, Isolated Compositing Layer) -->
                <div id="myntosCallMethodDialog" class="myntos-call-method-dialog" style="position: relative !important; z-index: 10 !important; width: 100% !important; max-width: 480px !important; background: #ffffff !important; background-color: #ffffff !important; border-radius: 20px !important; box-shadow: 0 25px 60px -15px rgba(0,0,0,0.5), 0 0 0 1px rgba(226, 232, 240, 0.9) !important; overflow: hidden !important; pointer-events: auto !important; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important; -webkit-font-smoothing: antialiased !important; -moz-osx-font-smoothing: grayscale !important; text-rendering: optimizeLegibility !important; transform: translate3d(0, 0, 0) !important; -webkit-transform: translate3d(0, 0, 0) !important; will-change: transform, opacity !important; filter: none !important; -webkit-filter: none !important; opacity: 1 !important; isolation: isolate !important;">
                    
                    <!-- Header -->
                    <div style="background: linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%) !important; padding: 18px 22px !important; color: #ffffff !important; display: flex !important; align-items: center !important; justify-content: space-between !important; border-bottom: 1px solid rgba(255,255,255,0.15) !important;">
                        <div style="min-width: 0 !important; flex: 1 !important;">
                            <div style="font-size: 18px !important; font-weight: 700 !important; letter-spacing: -0.01em !important; color: #ffffff !important; line-height: 1.25 !important;">Choose Calling Method</div>
                            <div style="font-size: 13px !important; color: #e0e7ff !important; margin-top: 3px !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;">
                                Lead: <strong style="color: #ffffff !important; font-weight: 700 !important;">${displayName}</strong> <span style="opacity: 0.85 !important;">(${cleanPhoneDisplay})</span>
                            </div>
                        </div>
                        <button onclick="window.PlivoSoftphone.closeCallMethodModal()" style="background: rgba(255,255,255,0.18) !important; border: 1px solid rgba(255,255,255,0.25) !important; color: #ffffff !important; width: 32px !important; height: 32px !important; border-radius: 50% !important; cursor: pointer !important; font-size: 14px !important; display: flex !important; align-items: center !important; justify-content: center !important; flex-shrink: 0 !important; margin-left: 12px !important; transition: all 0.15s ease !important;" onmouseover="this.style.background='rgba(255,255,255,0.3)'; this.style.transform='scale(1.05)';" onmouseout="this.style.background='rgba(255,255,255,0.18)'; this.style.transform='scale(1)';" title="Close modal (Esc)">✕</button>
                    </div>

                    <!-- Body Options -->
                    <div style="padding: 20px 22px !important; display: flex !important; flex-direction: column !important; gap: 12px !important; background: #ffffff !important; background-color: #ffffff !important;">
                        
                        <!-- 1. Plivo Cloud Softphone -->
                        <div onclick="window.PlivoSoftphone.selectCallMethod('plivo', '${destinationPhone}', '${leadId || ''}', '${displayName.replace(/'/g, "\\'")}')" 
                             style="border: 2px solid #e2e8f0 !important; border-radius: 14px !important; padding: 14px 16px !important; cursor: pointer !important; display: flex !important; align-items: center !important; gap: 14px !important; transition: all 0.15s ease !important; background: #ffffff !important; background-color: #ffffff !important;"
                             onmouseover="this.style.borderColor='#2563eb'; this.style.background='#eff6ff'; this.style.transform='translateY(-1px)';"
                             onmouseout="this.style.borderColor='#e2e8f0'; this.style.background='#ffffff'; this.style.transform='none';">
                            <div style="width: 44px !important; height: 44px !important; border-radius: 12px !important; background: #dbeafe !important; color: #1d4ed8 !important; font-size: 22px !important; display: flex !important; align-items: center !important; justify-content: center !important; flex-shrink: 0 !important; border: 1px solid #bfdbfe !important;">🎧</div>
                            <div style="flex-grow: 1 !important;">
                                <div style="font-weight: 700 !important; font-size: 15px !important; color: #0f172a !important; line-height: 1.2 !important;">MyntOS Cloud Softphone</div>
                                <div style="font-size: 12px !important; color: #475569 !important; margin-top: 2px !important;">Plivo Cloud Trunk (+918031728899) with Call Recording &amp; AI</div>
                            </div>
                        </div>

                        <!-- 2. Direct Mobile Calling -->
                        <div onclick="window.PlivoSoftphone.selectCallMethod('mobile', '${destinationPhone}', '${leadId || ''}', '${displayName.replace(/'/g, "\\'")}')" 
                             style="border: 2px solid #e2e8f0 !important; border-radius: 14px !important; padding: 14px 16px !important; cursor: pointer !important; display: flex !important; align-items: center !important; gap: 14px !important; transition: all 0.15s ease !important; background: #ffffff !important; background-color: #ffffff !important;"
                             onmouseover="this.style.borderColor='#10b981'; this.style.background='#ecfdf5'; this.style.transform='translateY(-1px)';"
                             onmouseout="this.style.borderColor='#e2e8f0'; this.style.background='#ffffff'; this.style.transform='none';">
                            <div style="width: 44px !important; height: 44px !important; border-radius: 12px !important; background: #d1fae5 !important; color: #059669 !important; font-size: 22px !important; display: flex !important; align-items: center !important; justify-content: center !important; flex-shrink: 0 !important; border: 1px solid #a7f3d0 !important;">📱</div>
                            <div style="flex-grow: 1 !important;">
                                <div style="font-weight: 700 !important; font-size: 15px !important; color: #0f172a !important; line-height: 1.2 !important;">Direct Mobile Calling</div>
                                <div style="font-size: 12px !important; color: #475569 !important; margin-top: 2px !important;">Open phone app (SIM 1 / SIM 2 / Native Dialer)</div>
                            </div>
                        </div>

                        <!-- 3. MyOperator Calling -->
                        <div onclick="window.PlivoSoftphone.selectCallMethod('myoperator', '${destinationPhone}', '${leadId || ''}', '${displayName.replace(/'/g, "\\'")}')" 
                             style="border: 2px solid #e2e8f0 !important; border-radius: 14px !important; padding: 14px 16px !important; cursor: pointer !important; display: flex !important; align-items: center !important; gap: 14px !important; transition: all 0.15s ease !important; background: #ffffff !important; background-color: #ffffff !important;"
                             onmouseover="this.style.borderColor='#8b5cf6'; this.style.background='#f5f3ff'; this.style.transform='translateY(-1px)';"
                             onmouseout="this.style.borderColor='#e2e8f0'; this.style.background='#ffffff'; this.style.transform='none';">
                            <div style="width: 44px !important; height: 44px !important; border-radius: 12px !important; background: #ede9fe !important; color: #6d28d9 !important; font-size: 22px !important; display: flex !important; align-items: center !important; justify-content: center !important; flex-shrink: 0 !important; border: 1px solid #ddd6fe !important;">🏢</div>
                            <div style="flex-grow: 1 !important;">
                                <div style="font-weight: 700 !important; font-size: 15px !important; color: #0f172a !important; line-height: 1.2 !important;">MyOperator Office Trunk</div>
                                <div style="font-size: 12px !important; color: #475569 !important; margin-top: 2px !important;">Corporate OBD Bridge &amp; Smart IVR Office Routing</div>
                            </div>
                        </div>

                        <!-- Remember choice -->
                        <div style="display: flex !important; align-items: center !important; gap: 8px !important; margin-top: 4px !important; padding: 4px 2px !important;">
                            <input type="checkbox" id="chkRememberCallChoice" style="cursor: pointer !important; width: 16px !important; height: 16px !important; accent-color: #2563eb !important;">
                            <label for="chkRememberCallChoice" style="font-size: 13px !important; font-weight: 500 !important; color: #475569 !important; cursor: pointer !important; user-select: none !important;">Remember my choice for this session</label>
                        </div>
                    </div>
                </div>
            `;
            modal.style.display = 'flex';
        }

        selectCallMethod(method, destinationPhone, leadId, leadName) {
            const chk = document.getElementById('chkRememberCallChoice');
            if (chk && chk.checked) {
                sessionStorage.setItem('myntos_preferred_call_method', method);
            }
            this.closeCallMethodModal();

            if (method === 'mobile') {
                this.executeMobileDial(destinationPhone);
            } else if (method === 'myoperator') {
                this.executeMyOperatorDial(destinationPhone, leadId, leadName);
            } else {
                this.executePlivoDial(destinationPhone, leadId, leadName);
            }
        }

        executeMobileDial(destinationPhone) {
            const cleanNumber = destinationPhone.replace(/[^+\d]/g, '');
            window.location.href = `tel:${cleanNumber}`;
        }

        async executeMyOperatorDial(destinationPhone, leadId, leadName) {
            try {
                const token = localStorage.getItem('staff_token') || localStorage.getItem('token');
                const resp = await fetch('/api/v1/crm/dialer/click-to-call', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        customer_phone: destinationPhone,
                        lead_id: leadId ? parseInt(leadId) : null
                    })
                });
                const resData = await resp.json();
                if (resp.ok && resData.success) {
                    alert(`MyOperator call dispatched to ${destinationPhone}! Your office phone will ring shortly.`);
                } else {
                    alert(`MyOperator dispatch error: ${resData.error?.detail || resData.detail || 'Service unavailable'}`);
                }
            } catch (err) {
                alert(`Failed to trigger MyOperator call: ${err.message}`);
            }
        }

        async executePlivoDial(destinationPhone, leadId = null, leadName = null) {
            if (this.isCallActive) {
                console.warn('[PLIVO-SOFTPHONE] A call is already active. Duplicate dial ignored.');
                return;
            }

            // Await actual WebRTC gateway registration rather than assuming instant sync
            if (!this.isRegistered || this.registrationState !== 'REGISTERED') {
                console.log('[PLIVO-SOFTPHONE] Awaiting WebRTC gateway registration before dialing...');
                this.updateUIStatus('connecting', 'Connecting...');
                const isReady = await this.ensureRegistered(12000);
                if (!isReady || !this.isRegistered || !this.client || typeof this.client.call !== 'function') {
                    alert('Unable to connect to the telephony network. Please check your internet connection or reload the page.');
                    this.updateUIStatus('offline', 'Offline');
                    return;
                }
            }

            this.isCallActive = true;
            this.activeDestination = destinationPhone;
            this.activeLeadName = leadName;

            console.log(`[PLIVO-SOFTPHONE] Dialing ${destinationPhone} (Lead: ${leadName || leadId})`);
            this.openSoftphoneDock();
            this.showCallInProgressUI(destinationPhone, leadName || 'Customer Lead');

            // Ensure remote audio playback element is ready and at full volume
            this.ensureRemoteAudioElement();
            const prewarmAudio = document.getElementById('plivoRemoteAudio');
            if (prewarmAudio) {
                prewarmAudio.volume = 1.0;
                prewarmAudio.muted = false;
            }

            try {
                const token = localStorage.getItem('staff_token') || localStorage.getItem('token');
                const cleanLeadId = leadId && String(leadId).trim() !== '' && !isNaN(parseInt(leadId)) ? parseInt(leadId) : null;
                // 1. Prepare call session in MyntOS backend
                const resp = await fetch('/api/v1/telephony/plivo/browser/call/initiate', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        destination_phone: destinationPhone,
                        lead_id: cleanLeadId
                    })
                });

                let sessData = null;
                if (resp.ok) {
                    sessData = await resp.json();
                } else {
                    console.warn('[PLIVO-SOFTPHONE] Call initiate fallback');
                    sessData = { call_session_id: 'vcs_local_' + Date.now() };
                }

                this.activeSessionId = sessData.call_session_id || ('vcs_local_' + Date.now());

                // 2. Dispatch call through Plivo WebRTC SDK
                const cleanDest = destinationPhone.startsWith('+') ? destinationPhone : `+91${destinationPhone.replace(/\D/g, '').slice(-10)}`;
                const extraHeaders = {
                    'X-PH-Call-Session-ID': this.activeSessionId,
                    'X-PH-Lead-ID': String(leadId || '')
                };

                // Immediately dispatch dialing event for Hub and view synchronization
                document.dispatchEvent(new CustomEvent('plivo:call-dialing', {
                    detail: {
                        phone: cleanDest,
                        name: this.activeLeadName || 'Contact Lead',
                        sessionId: this.activeSessionId
                    }
                }));

                if (this.client && typeof this.client.call === 'function') {
                    this.client.call(cleanDest, extraHeaders);
                }
            } catch (err) {
                console.error('[PLIVO-SOFTPHONE] Outbound dial error:', err);
                this.onCallTerminated();
            }
        }

        // ── INBOUND CALL HANDLING ────────────────────────────────────────────

        handleIncomingCall(callerName, extraHeaders, callInfo) {
            console.log('[PLIVO-SOFTPHONE] Inbound call received:', callerName, callInfo);
            this.incomingCallObj = callInfo;

            const callerPhone = callerName || callInfo?.src || 'Unknown Caller';
            const leadName = extraHeaders?.['X-PH-Lead-Name'] || 'Incoming Inquiry';
            const maskedPhone = this.maskPhone(callerPhone);

            this.activeDestination = callerPhone;
            this.activeLeadName = leadName;

            const banner = document.getElementById('plivoIncomingBanner');
            if (banner) {
                const nameEl = document.getElementById('incomingCallerName');
                const phoneEl = document.getElementById('incomingCallerPhone');
                if (nameEl) nameEl.textContent = leadName;
                if (phoneEl) phoneEl.textContent = maskedPhone;
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
            this.showCallInProgressUI(this.activeDestination, this.activeLeadName || 'Incoming Customer');
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

        // ── ACTIVE CALL CONTROLS & CARRIER DISCONNECT POLLER ────────────────

        startSessionWatcher(sessionId) {
            this.stopSessionWatcher();
            if (!sessionId || sessionId.startsWith('vcs_local_')) return;
            const token = localStorage.getItem('staff_token') || localStorage.getItem('token');
            this.sessionWatcherInterval = setInterval(async () => {
                try {
                    const resp = await fetch(`/api/v1/telephony/plivo/calls/session-status/${sessionId}`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    if (resp.ok) {
                        const data = await resp.json();
                        if (data && data.success && data.is_terminal === true) {
                            console.log(`[PLIVO-SOFTPHONE] Carrier disconnected call ${sessionId} (Status: ${data.status}, Duration: ${data.duration_seconds}s)`);
                            this.stopSessionWatcher();
                            this.onCallTerminated();
                        }
                    }
                } catch (_) {}
            }, 3000);
        }

        stopSessionWatcher() {
            if (this.sessionWatcherInterval) {
                clearInterval(this.sessionWatcherInterval);
                this.sessionWatcherInterval = null;
            }
        }

        startHeartbeatLoop() {
            this.stopHeartbeatLoop();
            this.heartbeatInterval = setInterval(async () => {
                if (this.isCallActive) {
                    try {
                        const token = localStorage.getItem('staff_token') || localStorage.getItem('token');
                        if (token) {
                            await fetch('/api/v1/telephony/plivo/browser/register', {
                                method: 'POST',
                                headers: {
                                    'Authorization': `Bearer ${token}`,
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    is_registered: true,
                                    in_call: true,
                                    call_session_id: this.activeSessionId
                                })
                            });
                        }
                    } catch (_) {}
                }
            }, 15000);
        }

        onCallRinging(callInfo) {
            console.log('[PLIVO-SOFTPHONE] Destination phone ringing...');
            const statusLabel = document.getElementById('callStatusLabel');
            if (statusLabel) {
                statusLabel.textContent = 'Ringing...';
                statusLabel.className = 'badge bg-info px-2 py-1';
            }
            this.syncCallEvent('ringing');
            document.dispatchEvent(new CustomEvent('plivo:call-ringing', {
                detail: {
                    phone: this.activeDestination || callInfo?.destination || '',
                    name: this.activeLeadName || 'Contact Lead',
                    sessionId: this.activeSessionId
                }
            }));
        }

        onMediaConnected(callInfo) {
            console.log('[PLIVO-SOFTPHONE] WebRTC media track active');
            const remoteAudio = document.getElementById('plivoRemoteAudio');
            if (remoteAudio) {
                remoteAudio.volume = 1.0;
                remoteAudio.muted = false;
                if (typeof remoteAudio.play === 'function') {
                    remoteAudio.play().catch((err) => {
                        console.warn('[PLIVO-SOFTPHONE] Remote audio autoplay deferred/warning:', err);
                    });
                }
            }
            if (!this.isCallActive || !this.callTimerInterval) {
                this.onCallConnected(callInfo);
            }
        }

        onCallConnected(callInfo) {
            console.log('[PLIVO-SOFTPHONE] Call connected / active');
            this.isCallActive = true;
            const statusLabel = document.getElementById('callStatusLabel');
            if (statusLabel) {
                statusLabel.textContent = 'Connected (In Call)';
                statusLabel.className = 'badge bg-success px-2 py-1';
            }
            const remoteAudio = document.getElementById('plivoRemoteAudio');
            if (remoteAudio) {
                remoteAudio.volume = 1.0;
                remoteAudio.muted = false;
                if (typeof remoteAudio.play === 'function') {
                    remoteAudio.play().catch(() => {});
                }
            }
            if (!this.callTimerInterval) {
                this.startCallTimer();
            }
            this.startHeartbeatLoop();

            this.syncCallEvent('connected');

            // Start carrier status watcher to detect remote hangup
            if (this.activeSessionId) {
                this.startSessionWatcher(this.activeSessionId);
            }

            // Dispatch global event for hub page and listeners
            document.dispatchEvent(new CustomEvent('plivo:call-connected', {
                detail: {
                    phone: this.activeDestination || callInfo?.destination || '',
                    name: this.activeLeadName || 'Contact Lead',
                    sessionId: this.activeSessionId
                }
            }));
        }

        onCallTerminated() {
            console.log('[PLIVO-SOFTPHONE] Call terminated');
            this.stopSessionWatcher();
            this.stopHeartbeatLoop();
            this.isCallActive = false;
            
            const mins = String(Math.floor(this.callSeconds / 60)).padStart(2, '0');
            const secs = String(this.callSeconds % 60).padStart(2, '0');
            const finalDuration = `${mins}:${secs}`;
            const durSecs = this.callSeconds || 0;
            const sid = this.activeSessionId;

            this.stopCallTimer();

            const statusLabel = document.getElementById('callStatusLabel');
            if (statusLabel) {
                statusLabel.textContent = `Call Ended (${finalDuration})`;
                statusLabel.className = 'badge bg-danger px-2 py-1';
            }

            // Auto-submit quick disposition if selected
            this.submitQuickDisposition();

            // End session and sync terminal call duration to backend
            if (sid) {
                const token = localStorage.getItem('staff_token') || localStorage.getItem('token');
                fetch('/api/v1/telephony/plivo/browser/call/end', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        call_session_id: sid,
                        duration_seconds: durSecs
                    })
                }).catch(() => {});

                fetch('/api/v1/telephony/plivo/browser/call-event', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        call_session_id: sid,
                        event_type: 'ended',
                        duration_seconds: durSecs
                    })
                }).catch(() => {});
            }

            if (this.localAudioStream) {
                try {
                    this.localAudioStream.getTracks().forEach(t => t.stop());
                } catch (_) {}
                this.localAudioStream = null;
            }

            // Reset speakerphone and audio routing to normal communication mode
            if (this.isSpeakerOn) {
                this.isSpeakerOn = false;
                try {
                    if (window.Capacitor?.Plugins?.AudioRouting) {
                        window.Capacitor.Plugins.AudioRouting.setSpeakerphoneOn({ enabled: false });
                    }
                } catch (_) {}
            }

            this.activeSessionId = null;
            this.activeLeadContext = null;

            // Dispatch global event so all page UI resets immediately
            document.dispatchEvent(new CustomEvent('plivo:call-terminated', {
                detail: { sessionId: sid, duration: finalDuration }
            }));

            // Gracefully close overlay after 1.8s, returning user untouched to their existing window
            setTimeout(() => {
                if (!this.isCallActive) {
                    this.hideCallInProgressUI();
                    this.closeSoftphoneDock();
                }
            }, 1800);
        }

        async submitQuickDisposition() {
            try {
                const dispEl = document.getElementById('activeCallDispositionSelect');
                const noteEl = document.getElementById('activeCallQuickNote');
                const disposition = dispEl ? dispEl.value : '';
                const note = noteEl ? noteEl.value.trim() : '';

                if ((disposition || note) && this.activeDestination) {
                    const token = localStorage.getItem('staff_token') || localStorage.getItem('token');
                    await fetch('/api/v1/crm/dialer/attempt-outcome', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({
                            lead_id: this.activeLeadId ? parseInt(this.activeLeadId) : null,
                            customer_phone: this.activeDestination,
                            call_outcome: disposition || 'answered',
                            note: note || 'Softphone call completed',
                            duration_seconds: this.callSeconds || 0
                        })
                    });
                }
            } catch (err) {
                console.warn('[PLIVO-SOFTPHONE] Could not submit quick disposition:', err);
            }
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
                    body: JSON.stringify({ 
                        call_session_id: this.activeSessionId,
                        duration_seconds: this.callSeconds || 0
                    })
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

        async toggleSpeaker() {
            this.isSpeakerOn = !this.isSpeakerOn;
            const btn = document.getElementById('btnSpeakerCall');
            if (btn) {
                btn.style.background = this.isSpeakerOn ? 'rgba(59,130,246,0.35)' : 'rgba(255,255,255,0.1)';
                btn.style.color = this.isSpeakerOn ? '#38bdf8' : '#ffffff';
                btn.style.borderColor = this.isSpeakerOn ? '#38bdf8' : 'rgba(255,255,255,0.2)';
            }

            // Real WebRTC audio output device sink routing
            try {
                if (typeof navigator !== 'undefined' && navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
                    const devices = await navigator.mediaDevices.enumerateDevices();
                    const audioOutputs = devices.filter(d => d.kind === 'audiooutput');
                    const audioElements = Array.from(document.querySelectorAll('audio, video'));
                    
                    if (audioOutputs.length > 0 && audioElements.length > 0) {
                        const targetDevice = this.isSpeakerOn 
                            ? (audioOutputs.find(d => /speaker|loudspeaker|external/i.test(d.label)) || audioOutputs[0])
                            : (audioOutputs.find(d => /default|earpiece|headset|internal/i.test(d.label)) || audioOutputs[0]);
                            
                        for (const el of audioElements) {
                            if (typeof el.setSinkId === 'function' && targetDevice?.deviceId) {
                                await el.setSinkId(targetDevice.deviceId);
                                console.log(`[PLIVO-SOFTPHONE] WebRTC audio sink routed to: ${targetDevice.label || targetDevice.deviceId}`);
                            }
                        }
                    }
                }
                
                // Capacitor / Native Android audio routing bridge if present
                if (window.Capacitor?.Plugins?.AudioRouting) {
                    await window.Capacitor.Plugins.AudioRouting.setSpeakerphoneOn({ enabled: this.isSpeakerOn });
                }
            } catch (err) {
                console.warn('[PLIVO-SOFTPHONE] Audio routing notice:', err.message);
            }

            this.showToast(this.isSpeakerOn ? 'Speaker mode enabled' : 'Default audio output', 'info');
        }

        sendDTMF(digit) {
            if (this.client && typeof this.client.sendDTMF === 'function') {
                this.client.sendDTMF(digit);
            }
        }

        async syncCallEvent(eventType, extraData = {}) {
            if (!this.activeSessionId) return;
            try {
                const token = localStorage.getItem('staff_token');
                await fetch('/api/v1/telephony/plivo/browser/call-event', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        call_session_id: this.activeSessionId,
                        event_type: eventType,
                        duration_seconds: this.callSeconds || 0,
                        ...extraData
                    })
                });
            } catch (_) {}
        }

        // ── TIMER & AUDIO HELPERS ────────────────────────────────────────────

        startCallTimer() {
            this.stopCallTimer();
            this.callSeconds = 0;
            const timerEl = document.getElementById('callTimerDisplay');
            const pillTimer = document.getElementById('desktopPillTimer');
            this.callTimerInterval = setInterval(() => {
                this.callSeconds++;
                const mins = String(Math.floor(this.callSeconds / 60)).padStart(2, '0');
                const secs = String(this.callSeconds % 60).padStart(2, '0');
                const formatted = `${mins}:${secs}`;
                if (timerEl) timerEl.textContent = formatted;
                if (pillTimer) pillTimer.textContent = formatted;
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

        // ── UI INJECTION & MOBILE DIALER WITH CONTACT SEARCH ────────────────

        maskPhone(p) {
            if (!p || p === '—' || p === '-' || p === 'null') return '—';
            const s = String(p).trim();
            if (s.includes('@g.us') || s.includes('@broadcast') || s.includes('@lid')) return s;
            const digits = s.replace(/\D/g, '');
            if (digits.length < 6) return s;
            const clean10 = digits.slice(-10);
            return `+91 ${clean10.slice(0, 2)}••••${clean10.slice(-4)}`;
        }

        injectUIElements() {
            if (!document.body || document.getElementById('myntosSoftphoneWidget')) return;

            const html = `
                <!-- Mobile & Desktop Backdrop -->
                <div id="myntosSoftphoneBackdrop" style="display: none; position: fixed; inset: 0; width: 100vw; height: 100vh; background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); z-index: 2147483646; transition: opacity 0.2s ease;" onclick="window.PlivoSoftphone.onBackdropClick()"></div>

                <!-- Global Softphone Centered Modal -->
                <div id="myntosSoftphoneWidget" style="position: fixed; inset: 0; width: 100vw; height: 100vh; z-index: 2147483647; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; pointer-events: none; display: none; align-items: center; justify-content: center; padding: 16px; box-sizing: border-box; isolation: isolate;">

                    <!-- Expanded Softphone Modal Dialog Card -->
                    <div id="plivoSoftphoneDockCard" class="card shadow-lg border-0 rounded-4" style="display: none; width: 100%; max-width: 420px; background: #ffffff; box-shadow: 0 25px 60px -15px rgba(0,0,0,0.6), 0 0 0 1px rgba(226, 232, 240, 0.9) !important; overflow: hidden; border: none; position: relative; pointer-events: auto; margin: auto; animation: modalPopIn 0.18s cubic-bezier(0.16, 1, 0.3, 1);">
                        
                        <!-- Header -->
                        <div id="desktopSoftphoneHeader" style="background: linear-gradient(135deg, #1e293b, #0f172a); padding: 14px 16px; color: #ffffff; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.1); cursor: move; user-select: none;">
                            <div style="display: flex; align-items: center; gap: 8px; pointer-events: none;">
                                <div style="width: 32px; height: 32px; border-radius: 8px; background: rgba(37,99,235,0.25); color: #60a5fa; display: flex; align-items: center; justify-content: center; font-size: 14px;">
                                    <i class="fa-solid fa-phone"></i>
                                </div>
                                <div>
                                    <div style="font-weight: 700; font-size: 14px; line-height: 1.2;">MyntOS Softphone</div>
                                    <div id="softphoneHeaderLeadName" style="font-size: 11px; color: #38bdf8; font-weight: 600; display: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px;"></div>
                                </div>
                            </div>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <select class="form-select form-select-sm" style="background: #334155; color: #f8fafc; border: 1px solid #475569; font-size: 11px; padding: 2px 20px 2px 8px; border-radius: 6px; cursor: pointer;" onchange="window.PlivoSoftphone.setAgentStatus(this.value)">
                                    <option value="available" selected>🟢 Available</option>
                                    <option value="busy">🔴 Busy</option>
                                    <option value="break">🟡 Break</option>
                                </select>
                                <button onclick="window.PlivoSoftphone.minimizeSoftphone()" style="background: rgba(255,255,255,0.15); border: none; color: #cbd5e1; width: 28px; height: 28px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: bold;" title="Minimize call window">⚊</button>
                                <button onclick="window.PlivoSoftphone.closeSoftphoneDock()" style="background: rgba(255,255,255,0.15); border: none; color: #cbd5e1; width: 28px; height: 28px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 14px;" title="Minimize or close dialpad">✕</button>
                            </div>
                        </div>

                        <!-- Tab Navigation Bar -->
                        <div style="display: flex; background: #f8fafc; border-bottom: 1px solid #e2e8f0; padding: 6px 8px; gap: 6px;">
                            <button id="tabBtnKeypad" onclick="window.PlivoSoftphone.switchTab('keypad')" style="flex: 1; border: none; background: #ffffff; color: #2563eb; font-weight: 700; font-size: 12px; padding: 6px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 4px;">
                                <i class="fa-solid fa-grip-vertical"></i> Keypad
                            </button>
                            <button id="tabBtnContacts" onclick="window.PlivoSoftphone.switchTab('contacts')" style="flex: 1; border: none; background: transparent; color: #64748b; font-weight: 600; font-size: 12px; padding: 6px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 4px;">
                                <i class="fa-solid fa-address-book"></i> Contacts & Leads
                            </button>
                            <button id="tabBtnRecents" onclick="window.PlivoSoftphone.switchTab('recents')" style="flex: 1; border: none; background: transparent; color: #64748b; font-weight: 600; font-size: 12px; padding: 6px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 4px;">
                                <i class="fa-solid fa-clock-rotate-left"></i> Recents
                            </button>
                        </div>

                        <!-- Card Body (Tab Views) -->
                        <div class="card-body p-0" style="min-height: 400px; position: relative;">
                            
                            <!-- TAB 1: KEYPAD / MOBILE DIALER -->
                            <div id="softphoneTabKeypad" style="padding: 16px;">
                                
                                <!-- Number Display & Backspace -->
                                <div style="background: #f1f5f9; border-radius: 12px; padding: 8px 12px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; border: 1px solid #cbd5e1;">
                                    <input type="text" id="softphoneDisplayInput" placeholder="Enter number or name..." style="background: transparent; border: none; outline: none; font-size: 18px; font-weight: 700; color: #0f172a; width: 100%; letter-spacing: 0.5px;" oninput="window.PlivoSoftphone.onKeypadInputChange(this.value)" onkeydown="if(event.key==='Enter') window.PlivoSoftphone.dialCurrentKeypadNumber()">
                                    <button onclick="window.PlivoSoftphone.backspace()" style="background: transparent; border: none; color: #64748b; font-size: 16px; cursor: pointer; padding: 4px 6px;" title="Backspace">
                                        <i class="fa-solid fa-delete-left"></i>
                                    </button>
                                </div>

                                <!-- Dynamic Auto-Suggest Drawer for Keypad -->
                                <div id="keypadAutoSuggest" style="display: none; max-height: 120px; overflow-y: auto; margin-bottom: 10px; border-radius: 8px; background: #ffffff; border: 1px solid #e2e8f0; font-size: 12px;"></div>

                                <!-- 3x4 Mobile Phone Keypad Grid -->
                                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 14px;">
                                    
                                    <button class="sp-key-btn" onclick="window.PlivoSoftphone.pressKey('1')">
                                        <div class="sp-digit">1</div>
                                        <div class="sp-sub">&nbsp;</div>
                                    </button>
                                    <button class="sp-key-btn" onclick="window.PlivoSoftphone.pressKey('2')">
                                        <div class="sp-digit">2</div>
                                        <div class="sp-sub">ABC</div>
                                    </button>
                                    <button class="sp-key-btn" onclick="window.PlivoSoftphone.pressKey('3')">
                                        <div class="sp-digit">3</div>
                                        <div class="sp-sub">DEF</div>
                                    </button>

                                    <button class="sp-key-btn" onclick="window.PlivoSoftphone.pressKey('4')">
                                        <div class="sp-digit">4</div>
                                        <div class="sp-sub">GHI</div>
                                    </button>
                                    <button class="sp-key-btn" onclick="window.PlivoSoftphone.pressKey('5')">
                                        <div class="sp-digit">5</div>
                                        <div class="sp-sub">JKL</div>
                                    </button>
                                    <button class="sp-key-btn" onclick="window.PlivoSoftphone.pressKey('6')">
                                        <div class="sp-digit">6</div>
                                        <div class="sp-sub">MNO</div>
                                    </button>

                                    <button class="sp-key-btn" onclick="window.PlivoSoftphone.pressKey('7')">
                                        <div class="sp-digit">7</div>
                                        <div class="sp-sub">PQRS</div>
                                    </button>
                                    <button class="sp-key-btn" onclick="window.PlivoSoftphone.pressKey('8')">
                                        <div class="sp-digit">8</div>
                                        <div class="sp-sub">TUV</div>
                                    </button>
                                    <button class="sp-key-btn" onclick="window.PlivoSoftphone.pressKey('9')">
                                        <div class="sp-digit">9</div>
                                        <div class="sp-sub">WXYZ</div>
                                    </button>

                                    <button class="sp-key-btn" onclick="window.PlivoSoftphone.pressKey('*')">
                                        <div class="sp-digit" style="font-size: 24px; line-height: 1;">*</div>
                                        <div class="sp-sub">&nbsp;</div>
                                    </button>
                                    <button class="sp-key-btn" onclick="window.PlivoSoftphone.pressKey('0')">
                                        <div class="sp-digit">0</div>
                                        <div class="sp-sub">+</div>
                                    </button>
                                    <button class="sp-key-btn" onclick="window.PlivoSoftphone.pressKey('#')">
                                        <div class="sp-digit">#</div>
                                        <div class="sp-sub">&nbsp;</div>
                                    </button>
                                </div>

                                <!-- Big Green Dial Button -->
                                <div style="display: flex; justify-content: center; align-items: center; margin-top: 4px;">
                                    <button onclick="window.PlivoSoftphone.dialCurrentKeypadNumber()" style="width: 56px; height: 56px; border-radius: 50%; background: linear-gradient(135deg, #10b981, #059669); border: none; color: #ffffff; font-size: 22px; cursor: pointer; box-shadow: 0 8px 18px rgba(16,185,129,0.35); display: flex; align-items: center; justify-content: center; transition: all 0.15s ease;" onmouseover="this.style.transform='scale(1.06)'" onmouseout="this.style.transform='scale(1)'">
                                        <i class="fa-solid fa-phone"></i>
                                    </button>
                                </div>
                            </div>

                            <!-- TAB 2: CONTACTS & LEADS SEARCH -->
                            <div id="softphoneTabContacts" style="display: none; padding: 14px;">
                                
                                <!-- Search Bar -->
                                <div style="position: relative; margin-bottom: 10px;">
                                    <input type="text" id="softphoneContactSearchInput" placeholder="Search leads, staff, phone..." style="width: 100%; padding: 8px 32px 8px 12px; border-radius: 10px; border: 1px solid #cbd5e1; font-size: 13px; outline: none; background: #f8fafc;" oninput="window.PlivoSoftphone.performSearch(this.value)">
                                    <i class="fa-solid fa-magnifying-glass" style="position: absolute; right: 12px; top: 11px; color: #94a3b8; font-size: 13px;"></i>
                                </div>

                                <!-- Search Results Scroll List -->
                                <div id="softphoneSearchResults" style="height: 330px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; padding-right: 2px;">
                                    <div style="text-align: center; color: #94a3b8; font-size: 12px; padding: 40px 10px;">
                                        <i class="fa-solid fa-users-viewfinder fa-2x mb-2" style="opacity: 0.5;"></i>
                                        <div>Type a name, phone, or code to search CRM Leads & Staff Directory</div>
                                    </div>
                                </div>
                            </div>

                            <!-- TAB 3: RECENTS -->
                            <div id="softphoneTabRecents" style="display: none; padding: 14px;">
                                <div id="softphoneRecentsList" style="height: 360px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;">
                                    <div style="text-align: center; color: #94a3b8; font-size: 12px; padding: 40px 10px;">
                                        <i class="fa-solid fa-phone-slash fa-2x mb-2" style="opacity: 0.5;"></i>
                                        <div>No recent calls in this session</div>
                                    </div>
                                </div>
                            </div>

                            <!-- IN-CALL ACTIVE CALL SCREEN OVERLAY -->
                            <div id="softphoneInCallView" style="display: none; position: absolute; inset: 0; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); color: #ffffff; padding: 20px 18px; z-index: 10; display: flex; flex-direction: column; justify-content: space-between; align-items: center; border-radius: 0 0 16px 16px; overflow-y: auto;">
                                
                                <div style="text-align: center; margin-top: 4px; width: 100%;">
                                    <div style="width: 64px; height: 64px; border-radius: 50%; background: linear-gradient(135deg, #3b82f6, #1d4ed8); color: white; display: flex; align-items: center; justify-content: center; font-size: 26px; margin: 0 auto 10px auto; box-shadow: 0 0 20px rgba(59,130,246,0.5);">
                                        <i class="fa-solid fa-user"></i>
                                    </div>
                                    <div class="fw-bold fs-5" id="activeCallCustomerName" style="color: #ffffff; letter-spacing: -0.01em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0 10px;">Customer Lead</div>
                                    <div style="font-size: 13px; color: #94a3b8; margin-top: 2px;" id="activeCallPhoneDisplay">+91 XX••••XXXX</div>
                                    <div style="margin-top: 8px;">
                                        <span id="callStatusLabel" class="badge bg-warning text-dark px-2 py-1" style="font-size: 11px;">Dialing...</span>
                                        <span id="callTimerDisplay" class="fw-bold ms-2" style="font-size: 13px; color: #38bdf8;">00:00</span>
                                    </div>
                                </div>

                                <!-- Quick Call Disposition & Note (In-Call Log) -->
                                <div style="width: 100%; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); border-radius: 12px; padding: 10px 12px; margin: 10px 0; font-size: 12px;">
                                    <div style="font-size: 11px; font-weight: 700; color: #94a3b8; margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between;">
                                        <span>QUICK CALL DISPOSITION</span>
                                        <span style="color: #38bdf8; font-size: 10px;"><i class="fa-solid fa-bolt"></i> Auto-saves</span>
                                    </div>
                                    <select id="activeCallDispositionSelect" style="width: 100%; background: #0f172a; color: #ffffff; border: 1px solid #334155; border-radius: 6px; padding: 5px 8px; font-size: 11px; margin-bottom: 6px; outline: none;">
                                        <option value="">-- Select Call Outcome --</option>
                                        <option value="interested">✅ Interested / Followup</option>
                                        <option value="callback">📞 Callback Requested</option>
                                        <option value="no_answer">⏳ Ringing / No Answer</option>
                                        <option value="busy">🔴 Busy / Line Engaged</option>
                                        <option value="not_interested">❌ Not Interested</option>
                                        <option value="wrong_number">⚠️ Wrong / Invalid Number</option>
                                    </select>
                                    <input type="text" id="activeCallQuickNote" placeholder="Add quick note or key takeaways..." style="width: 100%; background: #0f172a; color: #ffffff; border: 1px solid #334155; border-radius: 6px; padding: 5px 8px; font-size: 11px; outline: none;">
                                </div>

                                <!-- In-Call Mini DTMF Keypad (Collapsible) -->
                                <div id="inCallDTMFPad" style="display: none; width: 100%; max-width: 220px; grid-template-columns: repeat(3, 1fr); gap: 6px; margin: 4px 0;">
                                    ${['1','2','3','4','5','6','7','8','9','*','0','#'].map(k => `
                                        <button onclick="window.PlivoSoftphone.sendDTMF('${k}')" style="background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.2); color: white; border-radius: 8px; font-weight: bold; padding: 6px; cursor: pointer;">${k}</button>
                                    `).join('')}
                                </div>

                                <!-- In-Call 4-Action Button Grid -->
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 12px; width: 100%;">
                                    <div style="display: flex; justify-content: center; gap: 12px; width: 100%;">
                                        <button id="btnMuteCall" onclick="window.PlivoSoftphone.toggleMute()" style="width: 46px; height: 46px; border-radius: 50%; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 14px; cursor: pointer;">
                                            <i class="fa-solid fa-microphone"></i>
                                            <span style="font-size: 9px; margin-top: 1px;">Mute</span>
                                        </button>
                                        <button id="btnSpeakerCall" onclick="window.PlivoSoftphone.toggleSpeaker()" style="width: 46px; height: 46px; border-radius: 50%; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 14px; cursor: pointer;">
                                            <i class="fa-solid fa-volume-high"></i>
                                            <span style="font-size: 9px; margin-top: 1px;">Speaker</span>
                                        </button>
                                        <button id="btnHoldCall" onclick="window.PlivoSoftphone.toggleHold()" style="width: 46px; height: 46px; border-radius: 50%; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 14px; cursor: pointer;">
                                            <i class="fa-solid fa-pause"></i>
                                            <span style="font-size: 9px; margin-top: 1px;">Hold</span>
                                        </button>
                                        <button onclick="window.PlivoSoftphone.toggleDTMFPad()" style="width: 46px; height: 46px; border-radius: 50%; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 14px; cursor: pointer;">
                                            <i class="fa-solid fa-grip"></i>
                                            <span style="font-size: 9px; margin-top: 1px;">Keypad</span>
                                        </button>
                                    </div>

                                    <!-- Hangup Red Button & Direct SIM Fallback -->
                                    <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
                                        <button onclick="window.PlivoSoftphone.hangup()" style="width: 52px; height: 52px; border-radius: 50%; background: linear-gradient(135deg, #ef4444, #dc2626); border: none; color: white; font-size: 20px; cursor: pointer; box-shadow: 0 8px 20px rgba(239,68,68,0.4); display: flex; align-items: center; justify-content: center;" title="End Call">
                                            <i class="fa-solid fa-phone-slash"></i>
                                        </button>
                                        <button onclick="window.PlivoSoftphone.executeMobileDial(window.PlivoSoftphone.activeDestination)" style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #38bdf8; border-radius: 12px; padding: 3px 10px; font-size: 11px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 4px;">
                                            <i class="fa-solid fa-mobile-screen"></i> Direct SIM Call
                                        </button>
                                    </div>
                                </div>
                            </div>

                        </div>
                    </div>
                </div>

                <!-- Desktop Minimized Floating Pill (Compact Draggable Widget) -->
                <div id="plivoSoftphoneMinimizedPill" style="display: none; position: fixed; bottom: 24px; right: 24px; z-index: 2147483647; align-items: center; gap: 8px; background: linear-gradient(135deg, #0f172a, #1e293b); color: #ffffff; border: 1px solid #38bdf8; border-radius: 9999px; padding: 8px 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.5), 0 0 15px rgba(56,189,248,0.3); cursor: move; pointer-events: auto; user-select: none; touch-action: none;">
                    <div style="width: 10px; height: 10px; border-radius: 50%; background: #22c55e; box-shadow: 0 0 8px #22c55e;"></div>
                    <div style="font-weight: 700; font-size: 12px; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" id="desktopPillName">Contact Lead</div>
                    <div style="color: #38bdf8; font-weight: 700; font-size: 12px;" id="desktopPillTimer">00:00</div>
                    <button onclick="window.PlivoSoftphone.restoreSoftphone()" style="background: rgba(56,189,248,0.2); border: 1px solid rgba(56,189,248,0.4); color: #38bdf8; border-radius: 50%; width: 24px; height: 24px; font-size: 11px; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; margin-left: 2px;" title="Restore call window">▲</button>
                </div>

                <!-- Global Incoming Call Banner -->
                <div id="plivoIncomingBanner" style="display: none; position: fixed; top: 20px; right: 20px; width: 340px; z-index: 100000; background: #ffffff; border-left: 5px solid #22c55e; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); padding: 16px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
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

                <!-- Responsive Styles -->
                <style>
                    .sp-key-btn {
                        background: #f8fafc;
                        border: 1px solid #e2e8f0;
                        border-radius: 12px;
                        padding: 8px 4px;
                        cursor: pointer;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        transition: all 0.1s ease;
                        user-select: none;
                    }
                    .sp-key-btn:hover {
                        background: #e2e8f0;
                        border-color: #cbd5e1;
                    }
                    .sp-key-btn:active {
                        background: #cbd5e1;
                        transform: scale(0.95);
                    }
                    .sp-digit {
                        font-size: 20px;
                        font-weight: 700;
                        color: #0f172a;
                        line-height: 1.1;
                    }
                    .sp-sub {
                        font-size: 9px;
                        font-weight: 600;
                        color: #64748b;
                        letter-spacing: 1px;
                        line-height: 1;
                        margin-top: 2px;
                    }

                    @keyframes modalPopIn {
                        0% { opacity: 0; transform: scale(0.95) translateY(8px); }
                        100% { opacity: 1; transform: scale(1) translateY(0); }
                    }

                    .myntos-call-method-dialog {
                        animation: modalPopIn 0.18s cubic-bezier(0.16, 1, 0.3, 1);
                    }

                    @media (max-width: 600px) {
                        #plivoSoftphoneDockCard {
                            position: fixed !important;
                            bottom: 0 !important;
                            left: 0 !important;
                            right: 0 !important;
                            width: 100% !important;
                            max-width: 100% !important;
                            border-radius: 20px 20px 0 0 !important;
                            margin: 0 !important;
                            max-height: 90vh !important;
                            box-shadow: 0 -10px 40px rgba(0,0,0,0.35) !important;
                            z-index: 100000 !important;
                        }
                    }
                </style>
            `;

            const wrapper = document.createElement('div');
            wrapper.innerHTML = html;
            document.body.appendChild(wrapper);
        }

        // ── MOBILE DIALER CONTROLS ──────────────────────────────────────────

        switchTab(tab) {
            const tabKeypad = document.getElementById('softphoneTabKeypad');
            const tabContacts = document.getElementById('softphoneTabContacts');
            const tabRecents = document.getElementById('softphoneTabRecents');
            const btnKeypad = document.getElementById('tabBtnKeypad');
            const btnContacts = document.getElementById('tabBtnContacts');
            const btnRecents = document.getElementById('tabBtnRecents');

            if (!tabKeypad) return;

            const tabs = [
                { id: 'keypad', pane: tabKeypad, btn: btnKeypad },
                { id: 'contacts', pane: tabContacts, btn: btnContacts },
                { id: 'recents', pane: tabRecents, btn: btnRecents }
            ];

            tabs.forEach(t => {
                if (t.id === tab) {
                    t.pane.style.display = 'block';
                    t.btn.style.background = '#ffffff';
                    t.btn.style.color = '#2563eb';
                    t.btn.style.fontWeight = '700';
                    t.btn.style.boxShadow = '0 1px 3px rgba(0,0,0,0.08)';
                } else {
                    t.pane.style.display = 'none';
                    t.btn.style.background = 'transparent';
                    t.btn.style.color = '#64748b';
                    t.btn.style.fontWeight = '600';
                    t.btn.style.boxShadow = 'none';
                }
            });

            if (tab === 'contacts') {
                const searchInput = document.getElementById('softphoneContactSearchInput');
                if (searchInput) {
                    searchInput.focus();
                    if (!searchInput.value.trim()) this.performSearch('');
                }
            } else if (tab === 'recents') {
                this.renderRecentsList();
            }
        }

        pressKey(val) {
            const input = document.getElementById('softphoneDisplayInput');
            if (input) {
                input.value += val;
                this.onKeypadInputChange(input.value);
            }
            this.playKeyTone();
        }

        backspace() {
            const input = document.getElementById('softphoneDisplayInput');
            if (input && input.value.length > 0) {
                input.value = input.value.slice(0, -1);
                this.onKeypadInputChange(input.value);
            }
        }

        playKeyTone() {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(350, ctx.currentTime);
                gain.gain.setValueAtTime(0.04, ctx.currentTime);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 0.05);
            } catch (_) {}
        }

        onKeypadInputChange(query) {
            const suggestBox = document.getElementById('keypadAutoSuggest');
            if (!query || query.trim().length < 2) {
                if (suggestBox) suggestBox.style.display = 'none';
                return;
            }
            this.fetchContactResults(query.trim(), (results) => {
                if (!suggestBox) return;
                if (!results || results.length === 0) {
                    suggestBox.style.display = 'none';
                    return;
                }
                suggestBox.style.display = 'block';
                suggestBox.innerHTML = results.slice(0, 4).map(item => `
                    <div onclick="window.PlivoSoftphone.dial('${item.phone}', '${item.lead_id || ''}', '${item.name.replace(/'/g, "\\'")}')" style="padding: 6px 10px; border-bottom: 1px solid #f1f5f9; display: flex; align-items: center; justify-content: space-between; cursor: pointer;" onmouseover="this.style.background='#eff6ff'" onmouseout="this.style.background='#ffffff'">
                        <div>
                            <div style="font-weight: 700; color: #0f172a;">${item.name}</div>
                            <div style="font-size: 11px; color: #64748b;">${item.phone} • ${item.badge}</div>
                        </div>
                        <div style="color: #10b981; font-size: 14px;"><i class="fa-solid fa-phone"></i></div>
                    </div>
                `).join('');
            });
        }

        dialCurrentKeypadNumber() {
            const input = document.getElementById('softphoneDisplayInput');
            const raw = (input ? input.value : '').trim();
            if (!raw) {
                alert('Please enter a phone number or select a contact.');
                return;
            }
            this.dial(raw);
        }

        // ── CONTACT & LEAD SEARCH ───────────────────────────────────────────

        async performSearch(query) {
            const resultsContainer = document.getElementById('softphoneSearchResults');
            if (!resultsContainer) return;

            if (!query || query.trim().length === 0) {
                // Show default popular/recent leads
                query = 'a';
            }

            resultsContainer.innerHTML = `
                <div style="text-align: center; color: #64748b; font-size: 12px; padding: 30px;">
                    <i class="fa-solid fa-spinner fa-spin fa-2x mb-2" style="color: #2563eb;"></i>
                    <div>Searching contacts & leads...</div>
                </div>
            `;

            this.fetchContactResults(query, (results) => {
                if (!results || results.length === 0) {
                    resultsContainer.innerHTML = `
                        <div style="text-align: center; color: #94a3b8; font-size: 12px; padding: 40px 10px;">
                            <i class="fa-solid fa-address-book fa-2x mb-2" style="opacity: 0.5;"></i>
                            <div>No contacts or leads matched "${query}"</div>
                        </div>
                    `;
                    return;
                }

                resultsContainer.innerHTML = results.map(item => {
                    const badgeColor = item.type === 'staff' ? '#8b5cf6' : item.type === 'member' ? '#10b981' : '#2563eb';
                    const badgeBg = item.type === 'staff' ? '#f5f3ff' : item.type === 'member' ? '#ecfdf5' : '#eff6ff';
                    const initials = (item.name || 'C').slice(0, 2).toUpperCase();

                    return `
                        <div style="border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px 12px; display: flex; align-items: center; justify-content: space-between; gap: 10px; background: #ffffff; transition: all 0.15s ease;" onmouseover="this.style.borderColor='#2563eb'; this.style.boxShadow='0 2px 6px rgba(0,0,0,0.06)';" onmouseout="this.style.borderColor='#e2e8f0'; this.style.boxShadow='none';">
                            <div style="display: flex; align-items: center; gap: 10px; overflow: hidden;">
                                <div style="width: 36px; height: 36px; border-radius: 50%; background: ${badgeBg}; color: ${badgeColor}; font-weight: 700; font-size: 13px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; border: 1px solid ${badgeColor}33;">
                                    ${initials}
                                </div>
                                <div style="overflow: hidden;">
                                    <div style="font-weight: 700; font-size: 13px; color: #0f172a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${item.name}</div>
                                    <div style="font-size: 11px; color: #64748b; margin-top: 1px;">${item.phone}</div>
                                    <div style="margin-top: 2px;">
                                        <span style="font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 4px; background: ${badgeBg}; color: ${badgeColor}; border: 1px solid ${badgeColor}33;">${item.badge}</span>
                                        <span style="font-size: 10px; color: #94a3b8; margin-left: 4px;">${item.subtitle || ''}</span>
                                    </div>
                                </div>
                            </div>
                            <button onclick="window.PlivoSoftphone.dial('${item.phone}', '${item.lead_id || ''}', '${item.name.replace(/'/g, "\\'")}')" style="width: 34px; height: 34px; border-radius: 50%; background: #10b981; border: none; color: white; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: transform 0.1s ease;" onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'" title="Call ${item.name}">
                                <i class="fa-solid fa-phone"></i>
                            </button>
                        </div>
                    `;
                }).join('');
            });
        }

        async fetchContactResults(query, callback) {
            try {
                const token = localStorage.getItem('staff_token') || localStorage.getItem('token');
                const resp = await fetch(`/api/v1/telephony/plivo/contacts/search?q=${encodeURIComponent(query)}&limit=20`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (resp.ok) {
                    const data = await resp.json();
                    callback(data.results || []);
                } else {
                    callback([]);
                }
            } catch (err) {
                console.warn('[SOFTPHONE] Contact search error:', err);
                callback([]);
            }
        }

        // ── RECENTS LIST ────────────────────────────────────────────────────

        addRecentCall(phone, name, direction = 'outbound') {
            if (!this.recentCalls) this.recentCalls = [];
            this.recentCalls.unshift({
                phone,
                name: name || 'Customer Lead',
                direction,
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            });
            if (this.recentCalls.length > 20) this.recentCalls.pop();
        }

        renderRecentsList() {
            const container = document.getElementById('softphoneRecentsList');
            if (!container) return;
            if (!this.recentCalls || this.recentCalls.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; color: #94a3b8; font-size: 12px; padding: 40px 10px;">
                        <i class="fa-solid fa-phone-slash fa-2x mb-2" style="opacity: 0.5;"></i>
                        <div>No recent calls in this session</div>
                    </div>
                `;
                return;
            }

            container.innerHTML = this.recentCalls.map(c => `
                <div style="border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px 12px; display: flex; align-items: center; justify-content: space-between; background: #ffffff;">
                    <div>
                        <div style="font-weight: 700; font-size: 13px; color: #0f172a;">${c.name}</div>
                        <div style="font-size: 11px; color: #64748b;">${c.phone} • <span style="color: #059669;"><i class="fa-solid fa-arrow-up-right-from-square" style="font-size: 10px;"></i> ${c.direction}</span> • ${c.time}</div>
                    </div>
                    <button onclick="window.PlivoSoftphone.dial('${c.phone}', null, '${c.name.replace(/'/g, "\\'")}')" style="width: 32px; height: 32px; border-radius: 50%; background: #10b981; border: none; color: white; font-size: 13px; cursor: pointer; display: flex; align-items: center; justify-content: center;">
                        <i class="fa-solid fa-phone"></i>
                    </button>
                </div>
            `).join('');
        }

        toggleDTMFPad() {
            const pad = document.getElementById('inCallDTMFPad');
            if (pad) {
                pad.style.display = pad.style.display === 'none' ? 'grid' : 'none';
            }
        }

        toggleDock() {
            if (window.location.pathname.includes('/staff/softphone-hub') || document.getElementById('hubInCallView')) {
                return;
            }
            const widget = document.getElementById('myntosSoftphoneWidget');
            const card = document.getElementById('plivoSoftphoneDockCard');
            const backdrop = document.getElementById('myntosSoftphoneBackdrop');
            const isOpening = !card || card.style.display === 'none' || !card.style.display;
            if (widget) widget.style.display = isOpening ? 'flex' : 'none';
            if (card) card.style.display = isOpening ? 'block' : 'none';
            if (backdrop) backdrop.style.display = isOpening ? 'block' : 'none';
        }

        openSoftphoneDock() {
            if (window.location.pathname.includes('/staff/softphone-hub') || document.getElementById('hubInCallView')) {
                return;
            }
            const widget = document.getElementById('myntosSoftphoneWidget');
            const card = document.getElementById('plivoSoftphoneDockCard');
            const backdrop = document.getElementById('myntosSoftphoneBackdrop');
            if (widget) widget.style.display = 'flex';
            if (card) card.style.display = 'block';
            if (backdrop && !this.isCallActive) backdrop.style.display = 'block';
            this.initDraggables();
        }

        closeSoftphoneDock() {
            if (this.isCallActive) {
                this.minimizeSoftphone();
                return;
            }
            const widget = document.getElementById('myntosSoftphoneWidget');
            const card = document.getElementById('plivoSoftphoneDockCard');
            const backdrop = document.getElementById('myntosSoftphoneBackdrop');
            const pill = document.getElementById('plivoSoftphoneMinimizedPill');
            if (widget) widget.style.display = 'none';
            if (card) card.style.display = 'none';
            if (backdrop) backdrop.style.display = 'none';
            if (pill) pill.style.display = 'none';
        }

        minimizeSoftphone() {
            const card = document.getElementById('plivoSoftphoneDockCard');
            const backdrop = document.getElementById('myntosSoftphoneBackdrop');
            const pill = document.getElementById('plivoSoftphoneMinimizedPill');
            if (card) card.style.display = 'none';
            if (backdrop) backdrop.style.display = 'none';
            if (pill) {
                pill.style.display = 'flex';
                const pillName = document.getElementById('desktopPillName');
                if (pillName) pillName.textContent = this.activeLeadName || 'Contact Lead';
                const pillTimer = document.getElementById('desktopPillTimer');
                if (pillTimer) {
                    const mins = String(Math.floor(this.callSeconds / 60)).padStart(2, '0');
                    const secs = String(this.callSeconds % 60).padStart(2, '0');
                    pillTimer.textContent = `${mins}:${secs}`;
                }
            }
            this.initDraggables();
        }

        restoreSoftphone() {
            const card = document.getElementById('plivoSoftphoneDockCard');
            const pill = document.getElementById('plivoSoftphoneMinimizedPill');
            if (pill) pill.style.display = 'none';
            if (card) card.style.display = 'block';
            const widget = document.getElementById('myntosSoftphoneWidget');
            if (widget) widget.style.display = 'flex';
        }

        onBackdropClick() {
            if (!this.isCallActive) {
                this.closeSoftphoneDock();
            }
        }

        showCallInProgressUI(phone, name) {
            this.openSoftphoneDock();
            const backdrop = document.getElementById('myntosSoftphoneBackdrop');
            if (backdrop) backdrop.style.display = 'none'; // Unblock underlying page

            const inCallView = document.getElementById('softphoneInCallView');
            if (inCallView) inCallView.style.display = 'flex';
            
            const nameEl = document.getElementById('activeCallCustomerName');
            if (nameEl) nameEl.textContent = name || 'Customer Lead';

            const phoneEl = document.getElementById('activeCallPhoneDisplay');
            if (phoneEl) phoneEl.textContent = this.maskPhone(phone);

            const statusEl = document.getElementById('callStatusLabel');
            if (statusEl) {
                statusEl.textContent = 'Dialing...';
                statusEl.className = 'badge bg-warning text-dark px-2 py-1';
            }

            const timerEl = document.getElementById('callTimerDisplay');
            if (timerEl) timerEl.textContent = '00:00';

            const noteInput = document.getElementById('activeCallQuickNote');
            if (noteInput) noteInput.value = '';

            const dispSelect = document.getElementById('activeCallDispositionSelect');
            if (dispSelect) dispSelect.value = '';

            this.addRecentCall(phone, name, 'outbound');
        }

        initDraggables() {
            if (this.draggablesInitialized) return;
            const header = document.getElementById('desktopSoftphoneHeader');
            const card = document.getElementById('plivoSoftphoneDockCard');
            const pill = document.getElementById('plivoSoftphoneMinimizedPill');

            if (header && card) {
                let isDragging = false;
                let startX = 0, startY = 0, initialLeft = 0, initialTop = 0;

                header.addEventListener('pointerdown', (e) => {
                    if (e.target.closest('button, select, input, a')) return;
                    isDragging = true;
                    startX = e.clientX;
                    startY = e.clientY;
                    const rect = card.getBoundingClientRect();
                    initialLeft = rect.left;
                    initialTop = rect.top;
                    card.style.position = 'fixed';
                    card.style.margin = '0';
                    card.style.left = `${initialLeft}px`;
                    card.style.top = `${initialTop}px`;
                    try { header.setPointerCapture(e.pointerId); } catch (_) {}
                    e.preventDefault();
                });

                header.addEventListener('pointermove', (e) => {
                    if (!isDragging) return;
                    const dx = e.clientX - startX;
                    const dy = e.clientY - startY;
                    const newLeft = Math.max(12, Math.min(window.innerWidth - card.offsetWidth - 12, initialLeft + dx));
                    const newTop = Math.max(12, Math.min(window.innerHeight - card.offsetHeight - 12, initialTop + dy));
                    card.style.left = `${newLeft}px`;
                    card.style.top = `${newTop}px`;
                });

                const stopDrag = (e) => {
                    if (isDragging) {
                        isDragging = false;
                        try { header.releasePointerCapture(e.pointerId); } catch (_) {}
                    }
                };
                header.addEventListener('pointerup', stopDrag);
                header.addEventListener('pointercancel', stopDrag);
            }

            if (pill) {
                let isDraggingPill = false;
                let pStartX = 0, pStartY = 0, pInitLeft = 0, pInitTop = 0;

                pill.addEventListener('pointerdown', (e) => {
                    if (e.target.closest('button')) return;
                    isDraggingPill = true;
                    pStartX = e.clientX;
                    pStartY = e.clientY;
                    const rect = pill.getBoundingClientRect();
                    pInitLeft = rect.left;
                    pInitTop = rect.top;
                    pill.style.right = 'auto';
                    pill.style.bottom = 'auto';
                    pill.style.left = `${pInitLeft}px`;
                    pill.style.top = `${pInitTop}px`;
                    try { pill.setPointerCapture(e.pointerId); } catch (_) {}
                    e.preventDefault();
                });

                pill.addEventListener('pointermove', (e) => {
                    if (!isDraggingPill) return;
                    const dx = e.clientX - pStartX;
                    const dy = e.clientY - pStartY;
                    const newLeft = Math.max(12, Math.min(window.innerWidth - pill.offsetWidth - 12, pInitLeft + dx));
                    const newTop = Math.max(12, Math.min(window.innerHeight - pill.offsetHeight - 12, pInitTop + dy));
                    pill.style.left = `${newLeft}px`;
                    pill.style.top = `${newTop}px`;
                });

                const stopPillDrag = (e) => {
                    if (isDraggingPill) {
                        isDraggingPill = false;
                        try { pill.releasePointerCapture(e.pointerId); } catch (_) {}
                    }
                };
                pill.addEventListener('pointerup', stopPillDrag);
                pill.addEventListener('pointercancel', stopPillDrag);
            }

            this.draggablesInitialized = true;
        }

        hideCallInProgressUI() {
            const inCallView = document.getElementById('softphoneInCallView');
            if (inCallView) inCallView.style.display = 'none';
            const pad = document.getElementById('inCallDTMFPad');
            if (pad) pad.style.display = 'none';
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
    const instance = new MyntOSPlivoSoftphone();
    window.PlivoSoftphone = instance;
    window.openCallDialer = (intent) => instance.openCallDialer(intent);

    window.triggerLeadCall = (phone, name, leadId) => {
        instance.openCallDialer({
            phoneNumber: phone,
            name: name || 'Contact Lead',
            entityId: leadId || null,
            entityType: 'lead',
            autoStart: true
        });
    };

    window.makeMyntOSCall = (phone, leadId, leadName) => {
        instance.openCallDialer({
            phoneNumber: phone,
            name: leadName || 'Contact Lead',
            entityId: leadId || null,
            entityType: 'lead',
            autoStart: true
        });
    };

    // Global interceptor for all telephone / dial buttons across CRM and Auto Dialer
    if (typeof document !== 'undefined') {
        document.addEventListener('DOMContentLoaded', () => {
            document.addEventListener('click', (e) => {
                const telLink = e.target.closest('a[href^="tel:"], .btn-dial, .make-call-btn, .crm-call-trigger, .action-btn.call, .action-btn.call-btn, .dial-btn-badge, .contact-call-btn, button[data-action="call"]');
                if (telLink && !telLink.closest('#myntosCallMethodModal') && !telLink.closest('#plivoSoftphoneDockCard') && !telLink.closest('#myntosSoftphoneWidget')) {
                    const rawHref = telLink.getAttribute('href') || '';
                    const phone = (rawHref.startsWith('tel:') ? rawHref.replace(/^tel:/i, '') : (telLink.getAttribute('data-phone') || telLink.getAttribute('data-destination') || '')) || '';
                    if (phone) {
                        e.preventDefault();
                        e.stopPropagation();
                        const leadCard = telLink.closest('[data-id], .lead-card, .card, tr');
                        const leadName = telLink.getAttribute('data-lead-name') || telLink.getAttribute('data-name') || leadCard?.querySelector('.lead-name, .customer-name, strong')?.textContent?.trim() || 'Contact Lead';
                        const leadId = telLink.getAttribute('data-lead-id') || telLink.getAttribute('data-id') || leadCard?.getAttribute('data-id') || null;
                        instance.openCallDialer({
                            phoneNumber: phone,
                            name: leadName,
                            entityId: leadId,
                            entityType: 'lead',
                            autoStart: true
                        });
                    }
                }
            }, true);
        });
    }

})(typeof window !== 'undefined' ? window : this);
