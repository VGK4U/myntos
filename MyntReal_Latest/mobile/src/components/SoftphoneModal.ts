/**
 * Central Softphone Dialer Modal & Floating Call Window — MyntOS Mobile
 * Unified multi-state calling window mounted to document.body with WebKit compositing safety.
 * Decouples UI visibility lifecycle from Telephony Session lifecycle:
 * UI States: CLOSED -> DIALER -> ACTIVE_FLOATING <-> MINIMIZED -> ENDED_SUMMARY -> CLOSED
 * Features:
 *  - Persistent floating window throughout dialing, ringing, connected, and held states.
 *  - Non-blocking backdrop during active calls so underlying CRM/leads page remains fully interactive.
 *  - Minimize to compact floating pill with live timer and status.
 *  - Restore full floating window preserving caller info, duration, and audio control states.
 *  - Touch/Pointer draggable with viewport boundary clamping and safe-area awareness.
 *  - Explicit red End Call button terminates the session; X/— minimizes without hanging up.
 */

import { telephonyService, TelephonyCallSession } from '../services/telephony.service';

export interface SoftphoneModalOptions {
  phoneNumber: string;
  name?: string;
  entityType?: string;
  entityId?: string | number | null;
  source?: string;
  autoStart?: boolean;
}

export type SoftphoneUIState = 'CLOSED' | 'DIALER' | 'ACTIVE_FLOATING' | 'MINIMIZED' | 'ENDED_SUMMARY';

class SoftphoneModal {
  private modalEl: HTMLElement | null = null;
  private uiState: SoftphoneUIState = 'CLOSED';
  private currentOptions: SoftphoneModalOptions | null = null;
  private enteredNumber: string = '';
  private isDtmfOpen: boolean = false;
  private unsubscribeTelephony: (() => void) | null = null;
  private currentSession: TelephonyCallSession | null = null;

  // Floating Window Positioning & Dragging
  private floatingPos: { x: number; y: number } = { x: 0, y: 0 };
  private pillPos: { x: number; y: number } = { x: 0, y: 0 };
  private isDraggingWindow: boolean = false;
  private isDraggingPill: boolean = false;
  private dragStartPointer: { x: number; y: number } = { x: 0, y: 0 };
  private dragStartPos: { x: number; y: number } = { x: 0, y: 0 };
  private hasInitializedPosition: boolean = false;

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.isOpen()) {
          if (this.uiState === 'ACTIVE_FLOATING') {
            this.minimize();
          } else if (this.uiState === 'DIALER') {
            this.close();
          }
        }
      });

      // Recalculate boundary on resize/orientation change
      window.addEventListener('resize', () => {
        if (this.isOpen()) {
          this.clampPositions();
          this.applyPositions();
        }
      });
    }
  }

  public isOpen(): boolean {
    return this.modalEl !== null && document.body.contains(this.modalEl) && this.uiState !== 'CLOSED';
  }

  public getUIState(): SoftphoneUIState {
    return this.uiState;
  }

  public open(options: SoftphoneModalOptions): void {
    this.currentOptions = options;
    this.enteredNumber = (options.phoneNumber || '').replace(/[^\d+]/g, '');
    this.isDtmfOpen = false;

    // Reset initial position anchor
    this.hasInitializedPosition = false;

    // Subscribe to telephony state
    if (this.unsubscribeTelephony) {
      this.unsubscribeTelephony();
    }
    this.unsubscribeTelephony = telephonyService.subscribe((session) => {
      this.currentSession = session;
      this.handleTelephonyStateUpdate(session);
    });

    const isAlreadyActive = telephonyService.isCallActive();
    this.uiState = isAlreadyActive ? 'ACTIVE_FLOATING' : 'DIALER';

    this.render();

    // If autoStart is requested, check readiness and initiate call via telephonyService
    if (options.autoStart && this.enteredNumber) {
      this.startCall();
    }
  }

  public minimize(): void {
    if (this.uiState === 'CLOSED') return;
    this.uiState = 'MINIMIZED';
    this.updateVisibility();
  }

  public restore(): void {
    if (this.uiState === 'CLOSED') return;
    this.uiState = 'ACTIVE_FLOATING';
    this.updateVisibility();
    this.updateSessionUI();
  }

  public close(): void {
    // If call is actively in-flight, X minimizes the window instead of hanging up
    if (this.currentSession && telephonyService.isCallActive()) {
      this.minimize();
      return;
    }

    this.teardown();
  }

  public forceCloseAndHangup(): void {
    if (this.currentSession && telephonyService.isCallActive()) {
      telephonyService.endCall();
    }
    this.teardown();
  }

  private teardown(): void {
    if (this.unsubscribeTelephony) {
      this.unsubscribeTelephony();
      this.unsubscribeTelephony = null;
    }

    if (this.modalEl) {
      this.modalEl.remove();
      this.modalEl = null;
    }
    this.uiState = 'CLOSED';
    this.currentOptions = null;
    this.currentSession = null;
    this.hasInitializedPosition = false;
  }

  private handleTelephonyStateUpdate(session: TelephonyCallSession): void {
    if (!this.modalEl || !document.body.contains(this.modalEl)) {
      if (session.state !== 'idle') {
        // Render if session is active but modal isn't mounted yet
        this.render();
      } else {
        return;
      }
    }

    const isCallActive = telephonyService.isCallActive();

    if (isCallActive) {
      if (this.uiState === 'DIALER') {
        this.uiState = 'ACTIVE_FLOATING';
      }
    } else if (session.state === 'ended') {
      this.uiState = 'ENDED_SUMMARY';
      setTimeout(() => {
        if (this.uiState === 'ENDED_SUMMARY') {
          this.teardown();
        }
      }, 1600);
    } else if (session.state === 'idle' && this.uiState !== 'DIALER') {
      this.teardown();
      return;
    }

    this.updateVisibility();
    this.updateSessionUI();
  }

  private maskPhone(s: string): string {
    if (!s) return '—';
    const digits = s.replace(/\D/g, '');
    if (digits.length < 6) return s;
    const clean10 = digits.slice(-10);
    return `+91 ${clean10.slice(0, 2)}••••${clean10.slice(-4)}`;
  }

  private formatDuration(seconds: number): string {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

  private initPositions(): void {
    if (this.hasInitializedPosition || typeof window === 'undefined') return;
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    // Center or bottom-dock floating window
    const dialogWidth = Math.min(400, vw - 24);
    const dialogHeight = 440;
    const initialX = Math.max(12, Math.round((vw - dialogWidth) / 2));
    const initialY = Math.max(20, Math.round((vh - dialogHeight) / 2));

    this.floatingPos = { x: initialX, y: initialY };
    this.pillPos = { x: Math.max(12, vw - 260), y: Math.max(20, vh - 100) };
    this.hasInitializedPosition = true;
  }

  private clampPositions(): void {
    if (typeof window === 'undefined') return;
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    // Clamp Floating Window
    const dialogWidth = Math.min(400, vw - 24);
    const dialogHeight = 440;
    const minX = 12;
    const maxX = Math.max(12, vw - dialogWidth - 12);
    const minY = 12;
    const maxY = Math.max(12, vh - dialogHeight - 12);

    this.floatingPos.x = Math.min(Math.max(this.floatingPos.x, minX), maxX);
    this.floatingPos.y = Math.min(Math.max(this.floatingPos.y, minY), maxY);

    // Clamp Minimized Pill
    const pillWidth = 240;
    const pillHeight = 54;
    const pillMinX = 12;
    const pillMaxX = Math.max(12, vw - pillWidth - 12);
    const pillMinY = 12;
    const pillMaxY = Math.max(12, vh - pillHeight - 12);

    this.pillPos.x = Math.min(Math.max(this.pillPos.x, pillMinX), pillMaxX);
    this.pillPos.y = Math.min(Math.max(this.pillPos.y, pillMinY), pillMaxY);
  }

  private applyPositions(): void {
    const dialogEl = this.modalEl?.querySelector('#spModalDialog') as HTMLElement;
    if (dialogEl && (this.uiState === 'ACTIVE_FLOATING' || this.uiState === 'DIALER')) {
      dialogEl.style.transform = `translate3d(${this.floatingPos.x}px, ${this.floatingPos.y}px, 0)`;
    }

    const pillEl = this.modalEl?.querySelector('#spMinimizedPill') as HTMLElement;
    if (pillEl && this.uiState === 'MINIMIZED') {
      pillEl.style.transform = `translate3d(${this.pillPos.x}px, ${this.pillPos.y}px, 0)`;
    }
  }

  private render(): void {
    if (this.modalEl) {
      this.modalEl.remove();
    }

    this.initPositions();
    this.clampPositions();

    const { name, entityType } = this.currentOptions || {};
    const displayName = name || 'Customer Lead';
    const displayTag = entityType ? entityType.toUpperCase() : 'LEAD';

    this.modalEl = document.createElement('div');
    this.modalEl.id = 'myntosCentralSoftphoneModal';
    this.modalEl.style.cssText = `
      position: fixed !important; top: 0 !important; left: 0 !important; right: 0 !important; bottom: 0 !important;
      width: 100vw !important; height: 100vh !important; z-index: 2147483647 !important;
      pointer-events: none !important;
      isolation: isolate !important; filter: none !important; -webkit-filter: none !important;
      background: transparent !important; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
    `;

    this.modalEl.innerHTML = `
      <!-- 1. Dedicated Backdrop (Active only during initial DIALER entry; hidden during active call) -->
      <div id="spModalBackdrop" style="position: absolute !important; inset: 0 !important; width: 100% !important; height: 100% !important; background: rgba(15, 23, 42, 0.7) !important; backdrop-filter: blur(6px) !important; -webkit-backdrop-filter: blur(6px) !important; z-index: 1 !important; pointer-events: auto !important; display: ${this.uiState === 'DIALER' ? 'block' : 'none'} !important;"></div>

      <!-- 2. Floating Modal Dialog Box (Pointer-events auto, Draggable) -->
      <div id="spModalDialog" class="sp-dialog-box" style="position: absolute !important; top: 0 !important; left: 0 !important; z-index: 10 !important; width: calc(100% - 24px) !important; max-width: 400px !important; background: #ffffff !important; border-radius: 20px !important; box-shadow: 0 25px 60px -15px rgba(0,0,0,0.6), 0 0 0 1px rgba(226, 232, 240, 0.9) !important; overflow: hidden !important; pointer-events: auto !important; transform: translate3d(${this.floatingPos.x}px, ${this.floatingPos.y}px, 0) !important; -webkit-transform: translate3d(${this.floatingPos.x}px, ${this.floatingPos.y}px, 0) !important; will-change: transform, opacity !important; isolation: isolate !important; touch-action: none !important;">
        
        <!-- Draggable Floating Header -->
        <div id="spFloatingHeader" style="background: linear-gradient(135deg, #1e293b, #0f172a) !important; padding: 12px 16px !important; color: #ffffff !important; display: flex !important; align-items: center !important; justify-content: space-between !important; border-bottom: 1px solid rgba(255,255,255,0.1) !important; cursor: move !important; user-select: none !important; -webkit-user-select: none !important;">
          <div style="display: flex !important; align-items: center !important; gap: 10px !important; pointer-events: none !important;">
            <div style="width: 30px !important; height: 30px !important; border-radius: 8px !important; background: rgba(56,189,248,0.2) !important; color: #38bdf8 !important; display: flex !important; align-items: center !important; justify-content: center !important; font-size: 13px !important;">
              📞
            </div>
            <div>
              <div style="font-weight: 700 !important; font-size: 14px !important; line-height: 1.2 !important; color: #ffffff !important;">Softphone Call</div>
              <div style="font-size: 10px !important; color: #94a3b8 !important;" id="spHeaderStatusText">🟢 Cloud Telephony Trunk</div>
            </div>
          </div>
          <div style="display: flex !important; align-items: center !important; gap: 8px !important;">
            <!-- Minimize Button (—) -->
            <button id="spMinimizeBtn" style="background: rgba(255,255,255,0.15) !important; border: none !important; color: #cbd5e1 !important; width: 28px !important; height: 28px !important; border-radius: 50% !important; cursor: pointer !important; font-size: 13px !important; font-weight: bold !important; display: flex !important; align-items: center !important; justify-content: center !important;" title="Minimize Call Window">⚊</button>
            <!-- Close / Minimize Button (✕) -->
            <button id="spCloseBtn" style="background: rgba(255,255,255,0.15) !important; border: none !important; color: #cbd5e1 !important; width: 28px !important; height: 28px !important; border-radius: 50% !important; cursor: pointer !important; font-size: 13px !important; display: flex !important; align-items: center !important; justify-content: center !important;" title="Minimize or Close">✕</button>
          </div>
        </div>

        <!-- Caller Context Banner -->
        <div style="background: #f8fafc !important; padding: 10px 16px !important; border-bottom: 1px solid #e2e8f0 !important; display: flex !important; align-items: center !important; justify-content: space-between !important;">
          <div style="min-width: 0 !important; flex: 1 !important;">
            <div style="display: flex !important; align-items: center !important; gap: 6px !important;">
              <span style="font-weight: 700 !important; font-size: 14px !important; color: #0f172a !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;" id="spCallerName">${displayName}</span>
              <span style="background: #e0f2fe !important; color: #0369a1 !important; font-size: 10px !important; font-weight: 700 !important; padding: 1px 6px !important; border-radius: 4px !important;">${displayTag}</span>
            </div>
            <div style="font-size: 12px !important; color: #64748b !important; margin-top: 1px !important;" id="spCallerPhoneDisplay">${this.maskPhone(this.enteredNumber)}</div>
          </div>
        </div>

        <!-- Body: Dialer & In-Call Views -->
        <div style="position: relative !important; min-height: 340px !important; background: #ffffff !important;">
          
          <!-- DIALER VIEW (Shown pre-call) -->
          <div id="spDialerView" style="padding: 14px 16px !important; display: ${this.uiState === 'DIALER' ? 'block' : 'none'} !important;">
            
            <!-- Number Display -->
            <div style="background: #f1f5f9 !important; border-radius: 12px !important; padding: 8px 12px !important; display: flex !important; align-items: center !important; justify-content: space-between !important; margin-bottom: 12px !important; border: 1px solid #cbd5e1 !important;">
              <input type="text" id="spDialInput" value="${this.enteredNumber}" placeholder="Enter phone number..." style="background: transparent !important; border: none !important; outline: none !important; font-size: 17px !important; font-weight: 700 !important; color: #0f172a !important; width: 100% !important; letter-spacing: 0.5px !important;" />
              <button id="spBackspaceBtn" style="background: transparent !important; border: none !important; color: #64748b !important; font-size: 16px !important; cursor: pointer !important; padding: 4px 6px !important;" title="Backspace">⌫</button>
            </div>

            <!-- 3x4 Keypad Grid -->
            <div style="display: grid !important; grid-template-columns: repeat(3, 1fr) !important; gap: 6px !important; margin-bottom: 12px !important;">
              ${[
                { k: '1', s: '&nbsp;' },
                { k: '2', s: 'ABC' },
                { k: '3', s: 'DEF' },
                { k: '4', s: 'GHI' },
                { k: '5', s: 'JKL' },
                { k: '6', s: 'MNO' },
                { k: '7', s: 'PQRS' },
                { k: '8', s: 'TUV' },
                { k: '9', s: 'WXYZ' },
                { k: '*', s: '&nbsp;' },
                { k: '0', s: '+' },
                { k: '#', s: '&nbsp;' }
              ]
                .map(
                  (item) => `
                <button class="sp-num-btn" data-key="${item.k}" style="background: #f8fafc !important; border: 1px solid #e2e8f0 !important; border-radius: 8px !important; padding: 6px 4px !important; cursor: pointer !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; user-select: none !important;">
                  <div style="font-size: 17px !important; font-weight: 700 !important; color: #0f172a !important; line-height: 1.1 !important;">${item.k}</div>
                  <div style="font-size: 8px !important; font-weight: 600 !important; color: #64748b !important; letter-spacing: 1px !important; line-height: 1 !important; margin-top: 1px !important;">${item.s}</div>
                </button>
              `
                )
                .join('')}
            </div>

            <!-- Action Controls -->
            <div style="display: flex !important; align-items: center !important; justify-content: space-between !important; gap: 8px !important; margin-top: 4px !important;">
              <button id="spDirectSimBtn" style="flex: 1 !important; padding: 8px 6px !important; border-radius: 8px !important; background: #ecfdf5 !important; border: 1px solid #a7f3d0 !important; color: #059669 !important; font-size: 11px !important; font-weight: 700 !important; cursor: pointer !important; display: flex !important; align-items: center !important; justify-content: center !important; gap: 4px !important;">
                📱 Direct SIM
              </button>

              <button id="spMainDialBtn" style="width: 50px !important; height: 50px !important; border-radius: 50% !important; background: linear-gradient(135deg, #10b981, #059669) !important; border: none !important; color: #ffffff !important; font-size: 20px !important; cursor: pointer !important; box-shadow: 0 6px 16px rgba(16,185,129,0.35) !important; display: flex !important; align-items: center !important; justify-content: center !important;" title="Place Call">
                📞
              </button>

              <button id="spMyOperatorBtn" style="flex: 1 !important; padding: 8px 6px !important; border-radius: 8px !important; background: #f5f3ff !important; border: 1px solid #ddd6fe !important; color: #7c3aed !important; font-size: 11px !important; font-weight: 700 !important; cursor: pointer !important; display: flex !important; align-items: center !important; justify-content: center !important; gap: 4px !important;">
                🏢 MyOperator
              </button>
            </div>

            <div id="spErrorBanner" style="display: none; margin-top: 10px !important; padding: 6px 10px !important; background: #fef2f2 !important; border: 1px solid #fecaca !important; border-radius: 6px !important; color: #dc2626 !important; font-size: 11px !important; text-align: center !important;"></div>
          </div>

          <!-- IN-CALL ACTIVE OVERLAY VIEW (Shown during active call) -->
          <div id="spInCallView" style="display: ${this.uiState === 'ACTIVE_FLOATING' || this.uiState === 'ENDED_SUMMARY' ? 'flex' : 'none'} !important; position: absolute !important; inset: 0 !important; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important; color: #ffffff !important; padding: 18px 16px !important; z-index: 20 !important; flex-direction: column !important; justify-content: space-between !important; align-items: center !important;">
            
            <div style="text-align: center !important; margin-top: 4px !important; width: 100% !important;">
              <div style="width: 54px !important; height: 54px !important; border-radius: 50% !important; background: linear-gradient(135deg, #3b82f6, #1d4ed8) !important; color: white !important; display: flex !important; align-items: center !important; justify-content: center !important; font-size: 22px !important; margin: 0 auto 8px auto !important; box-shadow: 0 0 20px rgba(59,130,246,0.5) !important;">
                👤
              </div>
              <div id="spActiveCallerName" style="font-weight: 700 !important; font-size: 16px !important; color: #ffffff !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;">${displayName}</div>
              <div id="spActiveCallerPhone" style="font-size: 12px !important; color: #94a3b8 !important; margin-top: 2px !important;">${this.maskPhone(this.enteredNumber)}</div>
              
              <div style="margin-top: 8px !important; display: flex !important; align-items: center !important; justify-content: center !important; gap: 8px !important;">
                <span id="spCallStateBadge" style="background: #f59e0b !important; color: #000000 !important; font-size: 11px !important; font-weight: 700 !important; padding: 2px 8px !important; border-radius: 12px !important;">Connecting...</span>
                <span id="spCallTimerDisplay" style="font-size: 14px !important; font-weight: 700 !important; color: #38bdf8 !important;">00:00</span>
              </div>
            </div>

            <!-- In-Call DTMF Pad -->
            <div id="spDtmfGrid" style="display: none; width: 100% !important; max-width: 200px !important; grid-template-columns: repeat(3, 1fr) !important; gap: 4px !important; margin: 6px auto !important;">
              ${['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#']
                .map(
                  (d) => `
                <button class="sp-dtmf-btn" data-dtmf="${d}" style="background: rgba(255,255,255,0.15) !important; border: 1px solid rgba(255,255,255,0.2) !important; color: white !important; border-radius: 6px !important; font-weight: bold !important; padding: 5px !important; font-size: 12px !important; cursor: pointer !important;">${d}</button>
              `
                )
                .join('')}
            </div>

            <!-- In-Call 4 Control Buttons (Mute, Speaker, Hold, DTMF) -->
            <div style="display: flex !important; flex-direction: column !important; align-items: center !important; gap: 12px !important; width: 100% !important;">
              <div style="display: flex !important; justify-content: center !important; gap: 10px !important; width: 100% !important;">
                <button id="spBtnMute" style="width: 44px !important; height: 44px !important; border-radius: 50% !important; background: rgba(255,255,255,0.1) !important; border: 1px solid rgba(255,255,255,0.2) !important; color: white !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; font-size: 13px !important; cursor: pointer !important;">
                  🎤
                  <span style="font-size: 8px !important; margin-top: 1px !important;">Mute</span>
                </button>

                <button id="spBtnSpeaker" style="width: 44px !important; height: 44px !important; border-radius: 50% !important; background: rgba(255,255,255,0.1) !important; border: 1px solid rgba(255,255,255,0.2) !important; color: white !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; font-size: 13px !important; cursor: pointer !important;">
                  🔊
                  <span style="font-size: 8px !important; margin-top: 1px !important;">Speaker</span>
                </button>

                <button id="spBtnHold" style="width: 44px !important; height: 44px !important; border-radius: 50% !important; background: rgba(255,255,255,0.1) !important; border: 1px solid rgba(255,255,255,0.2) !important; color: white !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; font-size: 13px !important; cursor: pointer !important;">
                  ⏸
                  <span style="font-size: 8px !important; margin-top: 1px !important;">Hold</span>
                </button>

                <button id="spBtnKeypad" style="width: 44px !important; height: 44px !important; border-radius: 50% !important; background: rgba(255,255,255,0.1) !important; border: 1px solid rgba(255,255,255,0.2) !important; color: white !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; font-size: 13px !important; cursor: pointer !important;">
                  🔢
                  <span style="font-size: 8px !important; margin-top: 1px !important;">Keypad</span>
                </button>
              </div>

              <!-- End Call (Hangup) Red Button -->
              <button id="spBtnHangup" style="width: 52px !important; height: 52px !important; border-radius: 50% !important; background: linear-gradient(135deg, #ef4444, #dc2626) !important; border: none !important; color: white !important; font-size: 20px !important; cursor: pointer !important; box-shadow: 0 8px 20px rgba(239,68,68,0.4) !important; display: flex !important; align-items: center !important; justify-content: center !important;" title="End Call">
                🛑
              </button>
            </div>

          </div>

        </div>
      </div>

      <!-- 3. Minimized Floating Pill (Compact Draggable Widget) -->
      <div id="spMinimizedPill" style="position: absolute !important; top: 0 !important; left: 0 !important; z-index: 20 !important; display: ${this.uiState === 'MINIMIZED' ? 'flex' : 'none'} !important; align-items: center !important; gap: 8px !important; background: linear-gradient(135deg, #0f172a, #1e293b) !important; color: #ffffff !important; border: 1px solid #38bdf8 !important; border-radius: 9999px !important; padding: 8px 14px !important; box-shadow: 0 10px 25px rgba(0,0,0,0.5), 0 0 15px rgba(56,189,248,0.3) !important; cursor: move !important; pointer-events: auto !important; transform: translate3d(${this.pillPos.x}px, ${this.pillPos.y}px, 0) !important; -webkit-transform: translate3d(${this.pillPos.x}px, ${this.pillPos.y}px, 0) !important; touch-action: none !important; user-select: none !important; -webkit-user-select: none !important;">
        <div style="width: 10px !important; height: 10px !important; border-radius: 50% !important; background: #22c55e !important; box-shadow: 0 0 8px #22c55e !important; animation: spPulse 1.5s infinite !important;"></div>
        <div style="min-width: 0 !important; max-width: 110px !important; overflow: hidden !important; text-overflow: ellipsis !important; white-space: nowrap !important; font-weight: 700 !important; font-size: 12px !important;" id="spPillCallerName">${displayName}</div>
        <div style="color: #38bdf8 !important; font-weight: 700 !important; font-size: 12px !important;" id="spPillTimerDisplay">00:00</div>
        <button id="spPillRestoreBtn" style="background: rgba(56,189,248,0.2) !important; border: 1px solid rgba(56,189,248,0.4) !important; color: #38bdf8 !important; border-radius: 50% !important; width: 24px !important; height: 24px !important; font-size: 11px !important; font-weight: bold !important; cursor: pointer !important; display: flex !important; align-items: center !important; justify-content: center !important; margin-left: 2px !important;" title="Restore Softphone Window">▲</button>
      </div>
    `;

    document.body.appendChild(this.modalEl);
    this.attachEventListeners();
    this.attachDragListeners();
    this.updateVisibility();
    this.updateSessionUI();
  }

  private attachDragListeners(): void {
    if (!this.modalEl) return;

    // 1. Dragging Floating Window via Header
    const header = this.modalEl.querySelector('#spFloatingHeader') as HTMLElement;
    const dialog = this.modalEl.querySelector('#spModalDialog') as HTMLElement;

    if (header && dialog) {
      header.addEventListener('pointerdown', (e: PointerEvent) => {
        const target = e.target as HTMLElement;
        if (target && target.closest('button, input, a')) return;

        this.isDraggingWindow = true;
        this.dragStartPointer = { x: e.clientX, y: e.clientY };
        this.dragStartPos = { x: this.floatingPos.x, y: this.floatingPos.y };

        try {
          header.setPointerCapture(e.pointerId);
        } catch (_) {}

        e.preventDefault();
        e.stopPropagation();
      });

      header.addEventListener('pointermove', (e: PointerEvent) => {
        if (!this.isDraggingWindow) return;

        const dx = e.clientX - this.dragStartPointer.x;
        const dy = e.clientY - this.dragStartPointer.y;

        this.floatingPos = {
          x: this.dragStartPos.x + dx,
          y: this.dragStartPos.y + dy
        };

        this.clampPositions();
        dialog.style.transform = `translate3d(${this.floatingPos.x}px, ${this.floatingPos.y}px, 0)`;
      });

      const stopWindowDrag = (e: PointerEvent) => {
        if (this.isDraggingWindow) {
          this.isDraggingWindow = false;
          try {
            header.releasePointerCapture(e.pointerId);
          } catch (_) {}
          this.clampPositions();
          dialog.style.transform = `translate3d(${this.floatingPos.x}px, ${this.floatingPos.y}px, 0)`;
        }
      };

      header.addEventListener('pointerup', stopWindowDrag);
      header.addEventListener('pointercancel', stopWindowDrag);
    }

    // 2. Dragging Minimized Pill
    const pill = this.modalEl.querySelector('#spMinimizedPill') as HTMLElement;
    if (pill) {
      let movedDuringDrag = false;

      pill.addEventListener('pointerdown', (e: PointerEvent) => {
        const target = e.target as HTMLElement;
        if (target && target.closest('#spPillRestoreBtn')) return;

        this.isDraggingPill = true;
        movedDuringDrag = false;
        this.dragStartPointer = { x: e.clientX, y: e.clientY };
        this.dragStartPos = { x: this.pillPos.x, y: this.pillPos.y };

        try {
          pill.setPointerCapture(e.pointerId);
        } catch (_) {}

        e.preventDefault();
        e.stopPropagation();
      });

      pill.addEventListener('pointermove', (e: PointerEvent) => {
        if (!this.isDraggingPill) return;

        const dx = e.clientX - this.dragStartPointer.x;
        const dy = e.clientY - this.dragStartPointer.y;

        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
          movedDuringDrag = true;
        }

        this.pillPos = {
          x: this.dragStartPos.x + dx,
          y: this.dragStartPos.y + dy
        };

        this.clampPositions();
        pill.style.transform = `translate3d(${this.pillPos.x}px, ${this.pillPos.y}px, 0)`;
      });

      const stopPillDrag = (e: PointerEvent) => {
        if (this.isDraggingPill) {
          this.isDraggingPill = false;
          try {
            pill.releasePointerCapture(e.pointerId);
          } catch (_) {}
          this.clampPositions();
          pill.style.transform = `translate3d(${this.pillPos.x}px, ${this.pillPos.y}px, 0)`;

          // If user tapped without dragging, restore full window
          if (!movedDuringDrag) {
            this.restore();
          }
        }
      };

      pill.addEventListener('pointerup', stopPillDrag);
      pill.addEventListener('pointercancel', stopPillDrag);
    }
  }

  private attachEventListeners(): void {
    if (!this.modalEl) return;

    // Backdrop Click (only in DIALER mode before a call starts)
    this.modalEl.querySelector('#spModalBackdrop')?.addEventListener('click', () => {
      if (this.uiState === 'DIALER') {
        this.close();
      }
    });

    // Minimize Button (—)
    this.modalEl.querySelector('#spMinimizeBtn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.minimize();
    });

    // Close Button (✕)
    this.modalEl.querySelector('#spCloseBtn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.close();
    });

    // Pill Restore Button (▲)
    this.modalEl.querySelector('#spPillRestoreBtn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.restore();
    });

    // Input Change
    const dialInput = this.modalEl.querySelector('#spDialInput') as HTMLInputElement;
    dialInput?.addEventListener('input', (e: any) => {
      this.enteredNumber = e.target.value;
      this.updateCallerPhoneDisplay();
    });

    // Backspace Button
    this.modalEl.querySelector('#spBackspaceBtn')?.addEventListener('click', () => {
      if (this.enteredNumber.length > 0) {
        this.enteredNumber = this.enteredNumber.slice(0, -1);
        if (dialInput) dialInput.value = this.enteredNumber;
        this.updateCallerPhoneDisplay();
        telephonyService.playKeyTone();
      }
    });

    // Keypad Buttons
    this.modalEl.querySelectorAll('.sp-num-btn').forEach((btn) => {
      btn.addEventListener('click', (e: any) => {
        const key = e.currentTarget.getAttribute('data-key');
        if (key && this.enteredNumber.length < 15) {
          this.enteredNumber += key;
          if (dialInput) dialInput.value = this.enteredNumber;
          this.updateCallerPhoneDisplay();
          telephonyService.playKeyTone();
        }
      });
    });

    // Main Dial Button
    this.modalEl.querySelector('#spMainDialBtn')?.addEventListener('click', () => {
      this.startCall();
    });

    // Direct SIM Button
    this.modalEl.querySelector('#spDirectSimBtn')?.addEventListener('click', () => {
      if (!this.enteredNumber) {
        this.showError('Please enter a phone number.');
        return;
      }
      telephonyService.triggerDirectSimCall(this.enteredNumber);
    });

    // MyOperator Button
    this.modalEl.querySelector('#spMyOperatorBtn')?.addEventListener('click', async () => {
      if (!this.enteredNumber) {
        this.showError('Please enter a phone number.');
        return;
      }
      try {
        const leadId = this.currentOptions?.entityId
          ? parseInt(String(this.currentOptions.entityId))
          : null;
        await telephonyService.triggerMyOperatorCall(this.enteredNumber, leadId);
        alert(`MyOperator call dispatched to ${this.enteredNumber}! Your office line will ring shortly.`);
      } catch (err: any) {
        this.showError(`MyOperator error: ${err.message}`);
      }
    });

    // In-Call Audio Controls
    this.modalEl.querySelector('#spBtnMute')?.addEventListener('click', () => {
      telephonyService.toggleMute();
    });

    this.modalEl.querySelector('#spBtnSpeaker')?.addEventListener('click', () => {
      telephonyService.toggleSpeaker();
    });

    this.modalEl.querySelector('#spBtnHold')?.addEventListener('click', () => {
      telephonyService.toggleHold();
    });

    this.modalEl.querySelector('#spBtnKeypad')?.addEventListener('click', () => {
      this.isDtmfOpen = !this.isDtmfOpen;
      const dtmfEl = this.modalEl?.querySelector('#spDtmfGrid') as HTMLElement;
      if (dtmfEl) {
        dtmfEl.style.display = this.isDtmfOpen ? 'grid' : 'none';
      }
    });

    // DTMF Buttons
    this.modalEl.querySelectorAll('.sp-dtmf-btn').forEach((btn) => {
      btn.addEventListener('click', (e: any) => {
        const d = e.currentTarget.getAttribute('data-dtmf');
        if (d) telephonyService.sendDTMF(d);
      });
    });

    // Explicit End Call Button
    this.modalEl.querySelector('#spBtnHangup')?.addEventListener('click', () => {
      telephonyService.endCall();
    });
  }

  private updateVisibility(): void {
    if (!this.modalEl) return;

    const backdrop = this.modalEl.querySelector('#spModalBackdrop') as HTMLElement;
    const dialog = this.modalEl.querySelector('#spModalDialog') as HTMLElement;
    const pill = this.modalEl.querySelector('#spMinimizedPill') as HTMLElement;
    const inCallView = this.modalEl.querySelector('#spInCallView') as HTMLElement;
    const dialerView = this.modalEl.querySelector('#spDialerView') as HTMLElement;

    if (this.uiState === 'DIALER') {
      if (backdrop) backdrop.style.display = 'block';
      if (dialog) dialog.style.display = 'block';
      if (pill) pill.style.display = 'none';
      if (dialerView) dialerView.style.display = 'block';
      if (inCallView) inCallView.style.display = 'none';
    } else if (this.uiState === 'ACTIVE_FLOATING') {
      if (backdrop) backdrop.style.display = 'none'; // Unblock underlying CRM page
      if (dialog) dialog.style.display = 'block';
      if (pill) pill.style.display = 'none';
      if (dialerView) dialerView.style.display = 'none';
      if (inCallView) inCallView.style.display = 'flex';
    } else if (this.uiState === 'MINIMIZED') {
      if (backdrop) backdrop.style.display = 'none';
      if (dialog) dialog.style.display = 'none';
      if (pill) pill.style.display = 'flex';
    } else if (this.uiState === 'ENDED_SUMMARY') {
      if (backdrop) backdrop.style.display = 'none';
      if (dialog) dialog.style.display = 'block';
      if (pill) pill.style.display = 'none';
      if (dialerView) dialerView.style.display = 'none';
      if (inCallView) inCallView.style.display = 'flex';
    }
  }

  private updateCallerPhoneDisplay(): void {
    const disp = this.modalEl?.querySelector('#spCallerPhoneDisplay');
    if (disp) {
      disp.textContent = this.maskPhone(this.enteredNumber);
    }
  }

  private showError(msg: string): void {
    const banner = this.modalEl?.querySelector('#spErrorBanner') as HTMLElement;
    if (banner) {
      banner.textContent = msg;
      banner.style.display = 'block';
    }
  }

  private hideError(): void {
    const banner = this.modalEl?.querySelector('#spErrorBanner') as HTMLElement;
    if (banner) {
      banner.style.display = 'none';
    }
  }

  private async startCall(): Promise<void> {
    this.hideError();
    if (!this.enteredNumber) {
      this.showError('Please enter a destination phone number.');
      return;
    }

    const name = this.currentOptions?.name || 'Contact Lead';
    const leadId = this.currentOptions?.entityId || null;

    this.uiState = 'ACTIVE_FLOATING';
    this.updateVisibility();

    const res = await telephonyService.startCall(this.enteredNumber, name, leadId);
    if (!res.success && res.error) {
      this.showError(res.error);
    }
  }

  private updateSessionUI(): void {
    if (!this.modalEl || !this.currentSession) return;

    const contactName = this.currentSession.contactName || this.currentOptions?.name || 'Contact Lead';
    const destPhone = this.currentSession.destinationPhone || this.enteredNumber;
    const durationText = this.formatDuration(this.currentSession.durationSeconds);

    // Update Floating Window
    const nameEl = this.modalEl.querySelector('#spActiveCallerName');
    if (nameEl) nameEl.textContent = contactName;

    const phoneEl = this.modalEl.querySelector('#spActiveCallerPhone');
    if (phoneEl) phoneEl.textContent = this.maskPhone(destPhone);

    const timerEl = this.modalEl.querySelector('#spCallTimerDisplay');
    if (timerEl) timerEl.textContent = durationText;

    // Update Minimized Pill
    const pillNameEl = this.modalEl.querySelector('#spPillCallerName');
    if (pillNameEl) pillNameEl.textContent = contactName;

    const pillTimerEl = this.modalEl.querySelector('#spPillTimerDisplay');
    if (pillTimerEl) pillTimerEl.textContent = durationText;

    // Update State Badge
    const stateBadge = this.modalEl.querySelector('#spCallStateBadge') as HTMLElement;
    if (stateBadge) {
      if (this.currentSession.state === 'connected') {
        stateBadge.textContent = '🟢 Connected';
        stateBadge.style.background = '#22c55e';
        stateBadge.style.color = '#ffffff';
      } else if (this.currentSession.state === 'ringing') {
        stateBadge.textContent = '📞 Ringing...';
        stateBadge.style.background = '#38bdf8';
        stateBadge.style.color = '#000000';
      } else if (this.currentSession.state === 'connecting') {
        stateBadge.textContent = '⏳ Connecting...';
        stateBadge.style.background = '#f59e0b';
        stateBadge.style.color = '#000000';
      } else if (this.currentSession.state === 'ended') {
        stateBadge.textContent = '🛑 Call Ended';
        stateBadge.style.background = '#ef4444';
        stateBadge.style.color = '#ffffff';
      }
    }

    // Update Audio Control States
    const muteBtn = this.modalEl.querySelector('#spBtnMute') as HTMLElement;
    if (muteBtn) {
      muteBtn.style.background = this.currentSession.isMuted
        ? 'rgba(239,68,68,0.6)'
        : 'rgba(255,255,255,0.1)';
      muteBtn.style.borderColor = this.currentSession.isMuted ? '#ef4444' : 'rgba(255,255,255,0.2)';
    }

    const speakerBtn = this.modalEl.querySelector('#spBtnSpeaker') as HTMLElement;
    if (speakerBtn) {
      speakerBtn.style.background = this.currentSession.isSpeaker
        ? 'rgba(56,189,248,0.6)'
        : 'rgba(255,255,255,0.1)';
      speakerBtn.style.borderColor = this.currentSession.isSpeaker
        ? '#38bdf8'
        : 'rgba(255,255,255,0.2)';
    }

    const holdBtn = this.modalEl.querySelector('#spBtnHold') as HTMLElement;
    if (holdBtn) {
      holdBtn.style.background = this.currentSession.isHeld
        ? 'rgba(245,158,11,0.6)'
        : 'rgba(255,255,255,0.1)';
      holdBtn.style.borderColor = this.currentSession.isHeld ? '#f59e0b' : 'rgba(255,255,255,0.2)';
    }
  }
}

export const softphoneModal = new SoftphoneModal();

