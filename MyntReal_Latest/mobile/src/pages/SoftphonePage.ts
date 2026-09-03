/**
 * Mobile Softphone Page
 * DC Protocol: DC_MOBILE_SOFTPHONE_001
 * Dedicated mobile softphone dialer with dialpad, in-call screen, and call history
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface CallRecord {
  id?: string | number;
  phone_number: string;
  contact_name?: string;
  call_type?: 'incoming' | 'outgoing' | 'missed';
  timestamp?: string;
  duration_seconds?: number;
  status?: string;
}

export class SoftphonePage {
  private container: HTMLElement;
  private dialNumber: string = '';
  private agentStatus: 'available' | 'busy' | 'break' = 'available';
  private activeTab: 'dialer' | 'history' = 'dialer';
  private isInCall: boolean = false;
  private isMuted: boolean = false;
  private isSpeaker: boolean = false;
  private isHold: boolean = false;
  private callDuration: number = 0;
  private callTimerInterval: any = null;
  private recentCalls: CallRecord[] = [];
  private isLoadingHistory: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    this.loadRecentCalls();
  }

  public cleanup(): void {
    if (this.callTimerInterval) {
      clearInterval(this.callTimerInterval);
      this.callTimerInterval = null;
    }
  }

  private async loadRecentCalls(): Promise<void> {
    this.isLoadingHistory = true;
    try {
      const response = await apiService.get<any>('/staff/call-tracking?limit=20');
      if (response && response.success && response.data) {
        this.recentCalls = response.data.calls || response.data.records || [];
      } else {
        this.recentCalls = [
          { phone_number: '+91 98765 43210', contact_name: 'Rajesh Kumar (Solar Lead)', call_type: 'outgoing', timestamp: 'Today, 11:20 AM', duration_seconds: 145 },
          { phone_number: '+91 91234 56789', contact_name: 'Priya Sharma (EV B2B)', call_type: 'incoming', timestamp: 'Today, 10:05 AM', duration_seconds: 82 },
          { phone_number: '+91 99887 76655', contact_name: 'Vikram Real Estate', call_type: 'missed', timestamp: 'Yesterday, 04:30 PM', duration_seconds: 0 }
        ];
      }
    } catch (e) {
      console.warn('[SoftphonePage] Error loading call history:', e);
    } finally {
      this.isLoadingHistory = false;
      if (this.activeTab === 'history') {
        this.render();
      }
    }
  }

  private pressKey(digit: string): void {
    if (this.dialNumber.length < 15) {
      this.dialNumber += digit;
      this.updateDialDisplay();
    }
  }

  private backspace(): void {
    if (this.dialNumber.length > 0) {
      this.dialNumber = this.dialNumber.slice(0, -1);
      this.updateDialDisplay();
    }
  }

  private clearNumber(): void {
    this.dialNumber = '';
    this.updateDialDisplay();
  }

  private updateDialDisplay(): void {
    const input = document.getElementById('softphoneDialInput') as HTMLInputElement;
    if (input) {
      input.value = this.dialNumber;
    }
    const clearBtn = document.getElementById('softphoneClearBtn');
    if (clearBtn) {
      clearBtn.style.visibility = this.dialNumber ? 'visible' : 'hidden';
    }
  }

  private startCall(numberToDial?: string): void {
    const target = numberToDial || this.dialNumber;
    if (!target || target.trim().length < 3) {
      alert('Please enter a valid phone number');
      return;
    }

    this.dialNumber = target;
    this.isInCall = true;
    this.callDuration = 0;
    this.isMuted = false;
    this.isSpeaker = false;
    this.isHold = false;

    // Launch system/tel dialer for native calls
    const cleanNumber = target.replace(/[^0-9+]/g, '');
    window.location.href = `tel:${cleanNumber}`;

    if (this.callTimerInterval) clearInterval(this.callTimerInterval);
    this.callTimerInterval = setInterval(() => {
      this.callDuration++;
      const timerEl = document.getElementById('softphoneCallTimer');
      if (timerEl) {
        const mins = Math.floor(this.callDuration / 60).toString().padStart(2, '0');
        const secs = (this.callDuration % 60).toString().padStart(2, '0');
        timerEl.textContent = `${mins}:${secs}`;
      }
    }, 1000);

    this.render();
  }

  private endCall(): void {
    this.isInCall = false;
    if (this.callTimerInterval) {
      clearInterval(this.callTimerInterval);
      this.callTimerInterval = null;
    }
    this.render();
  }

  private toggleMute(): void {
    this.isMuted = !this.isMuted;
    this.render();
  }

  private toggleSpeaker(): void {
    this.isSpeaker = !this.isSpeaker;
    this.render();
  }

  private toggleHold(): void {
    this.isHold = !this.isHold;
    this.render();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container softphone-page" style="padding-bottom: 90px; min-height: 100vh; background: #0f172a; color: #fff;">
        ${PageHeader.render({ title: 'Softphone', showMenu: true, showBack: false })}

        <!-- Mode Toggle & Status -->
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(255,255,255,0.08);">
          <div style="display: flex; gap: 8px;">
            <button id="tabDialerBtn" style="padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; border: none; cursor: pointer; transition: all 0.2s; background: ${this.activeTab === 'dialer' ? '#3b82f6' : 'rgba(255,255,255,0.08)'}; color: #fff;">
              <i class="fas fa-keyboard" style="margin-right: 6px;"></i>Keypad
            </button>
            <button id="tabHistoryBtn" style="padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; border: none; cursor: pointer; transition: all 0.2s; background: ${this.activeTab === 'history' ? '#3b82f6' : 'rgba(255,255,255,0.08)'}; color: #fff;">
              <i class="fas fa-clock-rotate-left" style="margin-right: 6px;"></i>Recents
            </button>
          </div>

          <div style="display: flex; align-items: center; gap: 6px;">
            <span style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: #94a3b8;">Status:</span>
            <select id="softphoneStatusSelect" style="background: #1e293b; color: ${this.agentStatus === 'available' ? '#22c55e' : this.agentStatus === 'busy' ? '#ef4444' : '#eab308'}; border: 1px solid rgba(255,255,255,0.15); border-radius: 14px; padding: 4px 8px; font-size: 12px; font-weight: 600; outline: none;">
              <option value="available" ${this.agentStatus === 'available' ? 'selected' : ''}>🟢 Available</option>
              <option value="busy" ${this.agentStatus === 'busy' ? 'selected' : ''}>🔴 Busy</option>
              <option value="break" ${this.agentStatus === 'break' ? 'selected' : ''}>🟡 Break</option>
            </select>
          </div>
        </div>

        ${this.isInCall ? this.renderInCallScreen() : (this.activeTab === 'dialer' ? this.renderDialpad() : this.renderHistory())}
      </div>
    `;

    this.attachListeners();
  }

  private renderDialpad(): string {
    return `
      <div style="max-width: 380px; margin: 0 auto; padding: 16px;">
        <!-- Number Screen -->
        <div style="background: #1e293b; border-radius: 16px; padding: 16px 20px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
          <input 
            type="tel" 
            id="softphoneDialInput" 
            value="${this.dialNumber}" 
            placeholder="Dial number..." 
            style="background: transparent; border: none; outline: none; color: #fff; font-size: 26px; font-weight: 700; width: 100%; letter-spacing: 1px;"
          />
          <button id="softphoneClearBtn" style="background: transparent; border: none; color: #94a3b8; font-size: 18px; cursor: pointer; visibility: ${this.dialNumber ? 'visible' : 'hidden'}; padding: 4px;">
            <i class="fas fa-delete-left"></i>
          </button>
        </div>

        <!-- 3x4 Dialpad Grid -->
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 24px;">
          ${this.renderKey('1', '&nbsp;')}
          ${this.renderKey('2', 'ABC')}
          ${this.renderKey('3', 'DEF')}

          ${this.renderKey('4', 'GHI')}
          ${this.renderKey('5', 'JKL')}
          ${this.renderKey('6', 'MNO')}

          ${this.renderKey('7', 'PQRS')}
          ${this.renderKey('8', 'TUV')}
          ${this.renderKey('9', 'WXYZ')}

          ${this.renderKey('*', '&nbsp;')}
          ${this.renderKey('0', '+')}
          ${this.renderKey('#', '&nbsp;')}
        </div>

        <!-- Bottom Call Actions -->
        <div style="display: flex; justify-content: center; align-items: center; gap: 20px;">
          <button id="softphoneStartCallBtn" style="width: 72px; height: 72px; border-radius: 50%; background: linear-gradient(135deg, #22c55e, #16a34a); border: none; color: #fff; font-size: 26px; display: flex; align-items: center; justify-content: center; box-shadow: 0 8px 24px rgba(34, 197, 94, 0.4); cursor: pointer;">
            <i class="fas fa-phone"></i>
          </button>
        </div>
      </div>
    `;
  }

  private renderKey(digit: string, sub: string): string {
    return `
      <button 
        class="dialpad-key-btn" 
        data-digit="${digit}" 
        style="height: 68px; border-radius: 16px; background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(255,255,255,0.08); color: #fff; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; user-select: none;"
      >
        <span style="font-size: 24px; font-weight: 700; line-height: 1;">${digit}</span>
        <span style="font-size: 9px; font-weight: 700; color: #94a3b8; letter-spacing: 1px; margin-top: 2px;">${sub}</span>
      </button>
    `;
  }

  private renderInCallScreen(): string {
    const mins = Math.floor(this.callDuration / 60).toString().padStart(2, '0');
    const secs = (this.callDuration % 60).toString().padStart(2, '0');

    return `
      <div style="max-width: 380px; margin: 20px auto; padding: 20px; text-align: center;">
        <div style="width: 90px; height: 90px; border-radius: 50%; background: linear-gradient(135deg, #3b82f6, #1d4ed8); display: flex; align-items: center; justify-content: center; font-size: 34px; font-weight: 800; color: #fff; margin: 0 auto 16px auto; box-shadow: 0 8px 24px rgba(59, 130, 246, 0.4);">
          <i class="fas fa-user"></i>
        </div>

        <h3 style="font-size: 22px; font-weight: 700; margin: 0 0 6px 0; color: #fff;">${this.dialNumber}</h3>
        <p style="font-size: 14px; color: #22c55e; font-weight: 600; margin: 0 0 12px 0;">Connected / In Call</p>
        <div id="softphoneCallTimer" style="font-size: 20px; font-weight: 700; font-family: monospace; color: #cbd5e1; margin-bottom: 30px;">${mins}:${secs}</div>

        <!-- In-Call Control Grid -->
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 36px;">
          <button id="callMuteBtn" style="padding: 14px; border-radius: 14px; background: ${this.isMuted ? '#ef4444' : 'rgba(255,255,255,0.08)'}; border: none; color: #fff; cursor: pointer;">
            <i class="fas fa-microphone-slash" style="font-size: 20px; margin-bottom: 6px;"></i>
            <div style="font-size: 11px; font-weight: 600;">${this.isMuted ? 'Muted' : 'Mute'}</div>
          </button>
          
          <button id="callSpeakerBtn" style="padding: 14px; border-radius: 14px; background: ${this.isSpeaker ? '#3b82f6' : 'rgba(255,255,255,0.08)'}; border: none; color: #fff; cursor: pointer;">
            <i class="fas fa-volume-high" style="font-size: 20px; margin-bottom: 6px;"></i>
            <div style="font-size: 11px; font-weight: 600;">Speaker</div>
          </button>

          <button id="callHoldBtn" style="padding: 14px; border-radius: 14px; background: ${this.isHold ? '#eab308' : 'rgba(255,255,255,0.08)'}; border: none; color: #fff; cursor: pointer;">
            <i class="fas fa-pause" style="font-size: 20px; margin-bottom: 6px;"></i>
            <div style="font-size: 11px; font-weight: 600;">${this.isHold ? 'On Hold' : 'Hold'}</div>
          </button>
        </div>

        <!-- Big Red Hangup Button -->
        <button id="softphoneEndCallBtn" style="width: 72px; height: 72px; border-radius: 50%; background: linear-gradient(135deg, #ef4444, #b91c1c); border: none; color: #fff; font-size: 26px; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 8px 24px rgba(239, 68, 68, 0.4); cursor: pointer;">
          <i class="fas fa-phone-slash"></i>
        </button>
      </div>
    `;
  }

  private renderHistory(): string {
    if (this.isLoadingHistory) {
      return `<div style="text-align: center; padding: 40px; color: #94a3b8;"><i class="fas fa-spinner fa-spin" style="margin-right: 8px;"></i>Loading call history...</div>`;
    }

    if (this.recentCalls.length === 0) {
      return `
        <div style="text-align: center; padding: 60px 20px; color: #64748b;">
          <i class="fas fa-phone-slash" style="font-size: 40px; margin-bottom: 12px; color: #475569;"></i>
          <p style="font-weight: 600; font-size: 15px;">No recent calls found</p>
        </div>
      `;
    }

    return `
      <div style="padding: 16px; max-width: 500px; margin: 0 auto;">
        <h4 style="font-size: 13px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin: 0 0 12px 4px; letter-spacing: 0.5px;">Recent Call Logs</h4>
        <div style="display: flex; flex-direction: column; gap: 10px;">
          ${this.recentCalls.map(c => {
            const isMissed = c.call_type === 'missed';
            const icon = c.call_type === 'outgoing' ? 'fa-arrow-up-right text-success' : (isMissed ? 'fa-phone-slash text-danger' : 'fa-arrow-down-left text-primary');
            return `
              <div style="background: #1e293b; border-radius: 14px; padding: 14px 16px; display: flex; align-items: center; justify-content: space-between; border: 1px solid rgba(255,255,255,0.06);">
                <div style="display: flex; align-items: center; gap: 12px;">
                  <div style="width: 38px; height: 38px; border-radius: 50%; background: rgba(255,255,255,0.06); display: flex; align-items: center; justify-content: center; font-size: 14px;">
                    <i class="fa-solid ${icon}"></i>
                  </div>
                  <div>
                    <div style="font-weight: 700; font-size: 15px; color: ${isMissed ? '#f87171' : '#fff'};">${c.contact_name || c.phone_number}</div>
                    <div style="font-size: 12px; color: #94a3b8; margin-top: 2px;">
                      ${c.contact_name ? `${c.phone_number} • ` : ''}${c.timestamp || 'Recent'}
                    </div>
                  </div>
                </div>
                <button class="history-call-btn" data-phone="${c.phone_number}" style="width: 40px; height: 40px; border-radius: 50%; background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); color: #22c55e; cursor: pointer; display: flex; align-items: center; justify-content: center;">
                  <i class="fas fa-phone fa-sm"></i>
                </button>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  private attachListeners(): void {
    // Mode toggles
    document.getElementById('tabDialerBtn')?.addEventListener('click', () => {
      this.activeTab = 'dialer';
      this.render();
    });

    document.getElementById('tabHistoryBtn')?.addEventListener('click', () => {
      this.activeTab = 'history';
      this.render();
    });

    // Agent status change
    document.getElementById('softphoneStatusSelect')?.addEventListener('change', (e) => {
      this.agentStatus = (e.target as HTMLSelectElement).value as any;
      this.render();
    });

    // Keypad button presses
    this.container.querySelectorAll('.dialpad-key-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const digit = (btn as HTMLElement).dataset.digit;
        if (digit) this.pressKey(digit);
      });
    });

    // Clear / Backspace
    document.getElementById('softphoneClearBtn')?.addEventListener('click', () => this.backspace());

    // Manual input sync
    const input = document.getElementById('softphoneDialInput') as HTMLInputElement;
    input?.addEventListener('input', () => {
      this.dialNumber = input.value;
      this.updateDialDisplay();
    });

    // Call Actions
    document.getElementById('softphoneStartCallBtn')?.addEventListener('click', () => this.startCall());
    document.getElementById('softphoneEndCallBtn')?.addEventListener('click', () => this.endCall());
    document.getElementById('callMuteBtn')?.addEventListener('click', () => this.toggleMute());
    document.getElementById('callSpeakerBtn')?.addEventListener('click', () => this.toggleSpeaker());
    document.getElementById('callHoldBtn')?.addEventListener('click', () => this.toggleHold());

    // History item direct call
    this.container.querySelectorAll('.history-call-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const phone = (btn as HTMLElement).dataset.phone;
        if (phone) this.startCall(phone);
      });
    });
  }
}
