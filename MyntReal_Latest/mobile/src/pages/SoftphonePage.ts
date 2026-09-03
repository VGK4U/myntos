/**
 * Mobile Softphone Page
 * DC Protocol: DC_MOBILE_SOFTPHONE_001
 * Dedicated mobile softphone dialer with in-app call engine, synced mobile call logs, and filters
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface CallRecord {
  id?: string | number;
  phone_number: string;
  contact_name?: string;
  call_type?: 'INCOMING' | 'OUTGOING' | 'MISSED' | 'REJECTED' | 'incoming' | 'outgoing' | 'missed';
  timestamp?: string;
  dialed_at?: string;
  duration_seconds?: number;
  source?: 'softphone' | 'native' | 'dialer';
  status?: string;
}

interface ContactItem {
  id?: string | number;
  name: string;
  phone: string;
  masked_phone?: string;
  source?: string;
  status?: string;
  badge_color?: string;
}

export class SoftphonePage {
  private container: HTMLElement;
  private dialNumber: string = '';
  private selectedContactName: string = '';
  private agentStatus: 'available' | 'busy' | 'break' = 'available';
  private activeTab: 'dialer' | 'contacts' | 'history' = 'dialer';
  private historyFilter: 'ALL' | 'SOFTPHONE' | 'MOBILE' = 'ALL';

  // In-App Call Engine
  private isInCall: boolean = false;
  private callStatusText: string = 'Calling...';
  private isMuted: boolean = false;
  private isSpeaker: boolean = false;
  private isHold: boolean = false;
  private callDuration: number = 0;
  private callTimerInterval: any = null;
  private callStartTime: number = 0;

  // History & Contacts
  private recentCalls: CallRecord[] = [];
  private isLoadingHistory: boolean = false;
  private contactsList: ContactItem[] = [];
  private searchContactsQuery: string = '';
  private isSearchingContacts: boolean = false;
  private searchDebounceTimer: any = null;
  private liveMatchingContacts: ContactItem[] = [];

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
      // 1. Fetch synced native & dialer history from backend API
      const response = await apiService.get<any>('/crm/dialer/call-history?per_page=50');
      let apiEntries: CallRecord[] = [];
      if (response && response.success && response.data && response.data.entries) {
        apiEntries = response.data.entries.map((e: any) => ({
          phone_number: e.phone || '',
          contact_name: e.name || e.contact_name || '',
          call_type: (e.call_type || 'OUTGOING').toUpperCase(),
          dialed_at: e.dialed_at,
          duration_seconds: e.duration_seconds || 0,
          source: (e.source === 'native' ? 'native' : 'dialer') as any
        }));
      } else if (response && response.entries) {
        apiEntries = response.entries.map((e: any) => ({
          phone_number: e.phone || '',
          contact_name: e.name || e.contact_name || '',
          call_type: (e.call_type || 'OUTGOING').toUpperCase(),
          dialed_at: e.dialed_at,
          duration_seconds: e.duration_seconds || 0,
          source: (e.source === 'native' ? 'native' : 'dialer') as any
        }));
      }

      // 2. Merge with locally saved in-app softphone calls
      let localSoftphoneCalls: CallRecord[] = [];
      try {
        const stored = localStorage.getItem('mnr_softphone_call_logs');
        if (stored) {
          localSoftphoneCalls = JSON.parse(stored);
        }
      } catch (e) {}

      // Combine and sort by timestamp descending
      const combined = [...localSoftphoneCalls, ...apiEntries];
      combined.sort((a, b) => {
        const tA = new Date(a.dialed_at || a.timestamp || 0).getTime();
        const tB = new Date(b.dialed_at || b.timestamp || 0).getTime();
        return tB - tA;
      });

      this.recentCalls = combined;
    } catch (e) {
      console.warn('[SoftphonePage] Error loading call history:', e);
    } finally {
      this.isLoadingHistory = false;
      if (this.activeTab === 'history') {
        this.renderHistoryList();
      }
    }
  }

  private saveSoftphoneCall(phone: string, name: string, duration: number): void {
    try {
      const record: CallRecord = {
        phone_number: phone,
        contact_name: name,
        call_type: 'OUTGOING',
        dialed_at: new Date().toISOString(),
        timestamp: this.formatRelativeTime(new Date().toISOString()),
        duration_seconds: duration,
        source: 'softphone',
        status: 'Completed'
      };

      let stored: CallRecord[] = [];
      const raw = localStorage.getItem('mnr_softphone_call_logs');
      if (raw) {
        stored = JSON.parse(raw);
      }
      stored.unshift(record);
      if (stored.length > 50) stored = stored.slice(0, 50);
      localStorage.setItem('mnr_softphone_call_logs', JSON.stringify(stored));

      // Prepend to current list
      this.recentCalls.unshift(record);
    } catch (e) {
      console.warn('[SoftphonePage] Could not save softphone log:', e);
    }
  }

  private async searchContacts(query: string): Promise<void> {
    const q = (query || '').trim();
    if (!q) {
      this.liveMatchingContacts = [];
      this.contactsList = [];
      this.updateMatchingDrawer();
      return;
    }

    this.isSearchingContacts = true;
    const spinner = document.getElementById('softphoneSearchSpinner');
    if (spinner) spinner.style.display = 'inline-block';

    try {
      const res = await apiService.get<any>(`/whatsapp/search-contacts?q=${encodeURIComponent(q)}`);
      if (res && res.success && res.data && res.data.contacts) {
        this.liveMatchingContacts = res.data.contacts;
        this.contactsList = res.data.contacts;
      } else if (res && res.contacts) {
        this.liveMatchingContacts = res.contacts;
        this.contactsList = res.contacts;
      } else {
        this.liveMatchingContacts = [];
      }
    } catch (err) {
      console.warn('[SoftphonePage] Contact search error:', err);
    } finally {
      this.isSearchingContacts = false;
      const spin = document.getElementById('softphoneSearchSpinner');
      if (spin) spin.style.display = 'none';
      if (this.activeTab === 'contacts') {
        this.renderContactsList();
      } else {
        this.updateMatchingDrawer();
      }
    }
  }

  private updateMatchingDrawer(): void {
    const drawer = document.getElementById('softphoneMatchingDrawer');
    const list = document.getElementById('softphoneMatchingList');
    if (!drawer || !list) return;

    if (this.liveMatchingContacts.length === 0 || !this.dialNumber) {
      drawer.style.display = 'none';
      return;
    }

    list.innerHTML = this.liveMatchingContacts.slice(0, 5).map(c => `
      <div 
        class="softphone-matched-item" 
        data-phone="${c.phone}" 
        data-name="${this.escapeAttr(c.name)}"
        style="display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-radius: 8px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.06); transition: background 0.15s; background: rgba(30, 41, 59, 0.95);"
      >
        <div style="display: flex; align-items: center; gap: 10px;">
          <div style="width: 32px; height: 32px; border-radius: 50%; background: ${c.badge_color || '#3b82f6'}; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; color: #fff;">
            ${(c.name ? c.name.charAt(0) : 'C').toUpperCase()}
          </div>
          <div>
            <div style="font-size: 13.5px; font-weight: 700; color: #fff;">${c.name}</div>
            <div style="font-size: 11px; color: #94a3b8; margin-top: 1px;">+91 ${c.phone}</div>
          </div>
        </div>
        <span style="font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 10px; background: rgba(255,255,255,0.1); color: ${c.badge_color || '#38bdf8'};">
          ${c.source || 'Contact'}
        </span>
      </div>
    `).join('');

    drawer.style.display = 'block';

    list.querySelectorAll('.softphone-matched-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const phone = target.dataset.phone || '';
        const name = target.dataset.name || '';
        this.selectMatchedContact(phone, name);
      });
    });
  }

  private selectMatchedContact(phone: string, name: string): void {
    this.dialNumber = phone;
    this.selectedContactName = name;
    this.liveMatchingContacts = [];
    const drawer = document.getElementById('softphoneMatchingDrawer');
    if (drawer) drawer.style.display = 'none';
    this.updateDialDisplay();
  }

  private pressKey(digit: string): void {
    if (this.dialNumber.length < 15) {
      this.dialNumber += digit;
      this.selectedContactName = '';
      this.updateDialDisplay();
      this.triggerLiveSearch();
    }
  }

  private backspace(): void {
    if (this.dialNumber.length > 0) {
      this.dialNumber = this.dialNumber.slice(0, -1);
      this.selectedContactName = '';
      this.updateDialDisplay();
      this.triggerLiveSearch();
    }
  }

  private clearNumber(): void {
    this.dialNumber = '';
    this.selectedContactName = '';
    this.liveMatchingContacts = [];
    this.updateDialDisplay();
    const drawer = document.getElementById('softphoneMatchingDrawer');
    if (drawer) drawer.style.display = 'none';
  }

  private triggerLiveSearch(): void {
    if (this.searchDebounceTimer) clearTimeout(this.searchDebounceTimer);
    if (!this.dialNumber || this.dialNumber.trim().length < 2) {
      this.liveMatchingContacts = [];
      this.updateMatchingDrawer();
      return;
    }

    this.searchDebounceTimer = setTimeout(() => {
      this.searchContacts(this.dialNumber);
    }, 200);
  }

  private updateDialDisplay(): void {
    const input = document.getElementById('softphoneDialInput') as HTMLInputElement;
    if (input) {
      input.value = this.dialNumber;
    }
    const nameLabel = document.getElementById('softphoneMatchedNameLabel');
    if (nameLabel) {
      if (this.selectedContactName) {
        nameLabel.textContent = `👤 ${this.selectedContactName}`;
        nameLabel.style.display = 'block';
      } else {
        nameLabel.style.display = 'none';
      }
    }
    const clearBtn = document.getElementById('softphoneClearBtn');
    if (clearBtn) {
      clearBtn.style.visibility = this.dialNumber ? 'visible' : 'hidden';
    }
  }

  private async dispatchBackendCall(phone: string): Promise<void> {
    const cleanDest = phone.startsWith('+') ? phone : `+91${phone.replace(/\D/g, '').slice(-10)}`;
    try {
      const resp = await apiService.post<any>('/crm/dialer/click-to-call', {
        customer_phone: cleanDest,
        lead_id: null
      });
      const statusEl = document.getElementById('softphoneCallStatusText');
      if (resp && resp.success) {
        if (statusEl) statusEl.textContent = 'Trunk Connected · Dialing...';
      } else {
        if (statusEl) statusEl.textContent = 'In-App Call Active';
      }
    } catch (e) {
      console.warn('[SoftphonePage] Server dispatch error:', e);
      const statusEl = document.getElementById('softphoneCallStatusText');
      if (statusEl) statusEl.textContent = 'In-App Call Active';
    }
  }

  private startCall(numberToDial?: string, contactName?: string, isDirectSim: boolean = false): void {
    const target = (numberToDial || this.dialNumber || '').trim();
    if (!target || target.replace(/[^0-9]/g, '').length < 3) {
      alert('Please enter a valid phone number');
      return;
    }

    const cleanNumber = target.replace(/[^0-9+]/g, '');
    this.dialNumber = target;
    if (contactName) this.selectedContactName = contactName;

    if (isDirectSim) {
      this.saveSoftphoneCall(target, this.selectedContactName, 0);
      window.location.href = `tel:${cleanNumber}`;
      return;
    }

    this.isInCall = true;
    this.callDuration = 0;
    this.callStartTime = Date.now();
    this.isMuted = false;
    this.isSpeaker = false;
    this.isHold = false;
    this.callStatusText = 'Connecting...';

    // Dispatch real telephone call to backend
    this.dispatchBackendCall(target);

    // Transition status to Connected
    setTimeout(() => {
      if (this.isInCall) {
        this.callStatusText = 'Connected / In Call';
        const st = document.getElementById('softphoneCallStatusText');
        if (st) st.textContent = this.callStatusText;
      }
    }, 1200);

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

  private triggerNativeSimCall(): void {
    const cleanNumber = (this.dialNumber || '').replace(/[^0-9+]/g, '');
    if (cleanNumber) {
      window.location.href = `tel:${cleanNumber}`;
    }
  }

  private endCall(): void {
    this.isInCall = false;
    if (this.callTimerInterval) {
      clearInterval(this.callTimerInterval);
      this.callTimerInterval = null;
    }

    // Save softphone call record
    if (this.dialNumber) {
      this.saveSoftphoneCall(this.dialNumber, this.selectedContactName, this.callDuration);
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

  private escapeAttr(str: string): string {
    return (str || '').replace(/"/g, '&quot;');
  }

  private formatRelativeTime(dateStr?: string): string {
    if (!dateStr) return 'Recent';
    try {
      const d = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      const timeStr = d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });

      if (diffDays === 0) return `Today, ${timeStr}`;
      if (diffDays === 1) return `Yesterday, ${timeStr}`;
      if (diffDays < 7) return `${diffDays}d ago, ${timeStr}`;
      return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) + `, ${timeStr}`;
    } catch {
      return dateStr;
    }
  }

  private formatDuration(seconds: number): string {
    if (!seconds || seconds <= 0) return '0s';
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const rem = seconds % 60;
    return rem > 0 ? `${mins}m ${rem}s` : `${mins}m`;
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container softphone-page" style="padding-bottom: 90px; min-height: 100vh; background: #0f172a; color: #fff;">
        ${PageHeader.render({ title: 'Softphone', showMenu: true, showBack: false })}

        <!-- Mode Toggle & Status -->
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(255,255,255,0.08);">
          <div style="display: flex; gap: 6px;">
            <button id="tabDialerBtn" style="padding: 6px 12px; border-radius: 20px; font-size: 12.5px; font-weight: 600; border: none; cursor: pointer; transition: all 0.2s; background: ${this.activeTab === 'dialer' ? '#3b82f6' : 'rgba(255,255,255,0.08)'}; color: #fff;">
              <i class="fas fa-keyboard" style="margin-right: 4px;"></i>Keypad
            </button>
            <button id="tabContactsBtn" style="padding: 6px 12px; border-radius: 20px; font-size: 12.5px; font-weight: 600; border: none; cursor: pointer; transition: all 0.2s; background: ${this.activeTab === 'contacts' ? '#3b82f6' : 'rgba(255,255,255,0.08)'}; color: #fff;">
              <i class="fas fa-address-book" style="margin-right: 4px;"></i>Contacts
            </button>
            <button id="tabHistoryBtn" style="padding: 6px 12px; border-radius: 20px; font-size: 12.5px; font-weight: 600; border: none; cursor: pointer; transition: all 0.2s; background: ${this.activeTab === 'history' ? '#3b82f6' : 'rgba(255,255,255,0.08)'}; color: #fff;">
              <i class="fas fa-clock-rotate-left" style="margin-right: 4px;"></i>Recents
            </button>
          </div>

          <div style="display: flex; align-items: center; gap: 6px;">
            <select id="softphoneStatusSelect" style="background: #1e293b; color: ${this.agentStatus === 'available' ? '#22c55e' : this.agentStatus === 'busy' ? '#ef4444' : '#eab308'}; border: 1px solid rgba(255,255,255,0.15); border-radius: 14px; padding: 4px 8px; font-size: 11.5px; font-weight: 600; outline: none;">
              <option value="available" ${this.agentStatus === 'available' ? 'selected' : ''}>🟢 Available</option>
              <option value="busy" ${this.agentStatus === 'busy' ? 'selected' : ''}>🔴 Busy</option>
              <option value="break" ${this.agentStatus === 'break' ? 'selected' : ''}>🟡 Break</option>
            </select>
          </div>
        </div>

        ${this.isInCall ? this.renderInCallScreen() : (this.activeTab === 'dialer' ? this.renderDialpad() : (this.activeTab === 'contacts' ? this.renderContacts() : this.renderHistory()))}
      </div>
    `;

    this.attachListeners();
  }

  private renderDialpad(): string {
    return `
      <div style="max-width: 380px; margin: 0 auto; padding: 16px; position: relative;">
        
        <!-- Number Screen & Contact Match Display -->
        <div style="background: #1e293b; border-radius: 16px; padding: 14px 18px; margin-bottom: 16px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 4px 12px rgba(0,0,0,0.3); position: relative;">
          
          <div id="softphoneMatchedNameLabel" style="display: ${this.selectedContactName ? 'block' : 'none'}; font-size: 12px; font-weight: 700; color: #38bdf8; margin-bottom: 4px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">
            👤 ${this.selectedContactName}
          </div>

          <div style="display: flex; align-items: center; justify-content: space-between;">
            <input 
              type="text" 
              id="softphoneDialInput" 
              value="${this.dialNumber}" 
              placeholder="Search name or dial number..." 
              style="background: transparent; border: none; outline: none; color: #fff; font-size: 22px; font-weight: 700; width: 100%; letter-spacing: 0.5px;"
            />
            <div style="display: flex; align-items: center; gap: 6px;">
              <span id="softphoneSearchSpinner" style="display: none; color: #38bdf8; font-size: 13px;">
                <i class="fas fa-spinner fa-spin"></i>
              </span>
              <button id="softphoneClearBtn" style="background: transparent; border: none; color: #94a3b8; font-size: 18px; cursor: pointer; visibility: ${this.dialNumber ? 'visible' : 'hidden'}; padding: 4px;">
                <i class="fas fa-delete-left"></i>
              </button>
            </div>
          </div>
        </div>

        <!-- Live Matching Contacts Dropdown Drawer -->
        <div id="softphoneMatchingDrawer" style="display: none; background: #1e293b; border: 1px solid #475569; border-radius: 12px; margin-bottom: 16px; max-height: 200px; overflow-y: auto; box-shadow: 0 8px 24px rgba(0,0,0,0.5);">
          <div id="softphoneMatchingList" style="padding: 4px;"></div>
        </div>

        <!-- 3x4 Dialpad Grid -->
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px;">
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

        <!-- Bottom Dual Call Actions: Softphone & Direct SIM -->
        <div style="display: flex; flex-direction: column; align-items: center; gap: 12px;">
          <div style="display: flex; align-items: center; justify-content: center; gap: 20px;">
            <button id="softphoneStartCallBtn" title="Call via Cloud Softphone" style="width: 68px; height: 68px; border-radius: 50%; background: linear-gradient(135deg, #22c55e, #16a34a); border: none; color: #fff; font-size: 24px; display: flex; align-items: center; justify-content: center; box-shadow: 0 8px 24px rgba(34, 197, 94, 0.4); cursor: pointer;">
              <i class="fas fa-phone"></i>
            </button>
          </div>

          <button id="softphoneDirectSimBtn" style="padding: 6px 14px; border-radius: 20px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); color: #38bdf8; font-size: 11.5px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;">
            <i class="fas fa-mobile-screen"></i> Direct SIM Call
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
        style="height: 64px; border-radius: 16px; background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(255,255,255,0.08); color: #fff; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; user-select: none;"
      >
        <span style="font-size: 22px; font-weight: 700; line-height: 1;">${digit}</span>
        <span style="font-size: 9px; font-weight: 700; color: #94a3b8; letter-spacing: 1px; margin-top: 2px;">${sub}</span>
      </button>
    `;
  }

  private renderContacts(): string {
    return `
      <div style="padding: 16px; max-width: 500px; margin: 0 auto;">
        <!-- Search Input Header -->
        <div style="background: #1e293b; border-radius: 12px; padding: 10px 14px; margin-bottom: 16px; display: flex; align-items: center; gap: 10px; border: 1px solid rgba(255,255,255,0.1);">
          <i class="fas fa-search" style="color: #94a3b8; font-size: 14px;"></i>
          <input 
            type="text" 
            id="softphoneContactsSearchInput" 
            value="${this.searchContactsQuery}" 
            placeholder="Search CRM leads, mobile contacts, staff..." 
            style="background: transparent; border: none; outline: none; color: #fff; font-size: 13.5px; width: 100%;"
          />
        </div>

        <div id="softphoneContactsContainer">
          ${this.renderContactsListHtml()}
        </div>
      </div>
    `;
  }

  private renderContactsList(): void {
    const container = document.getElementById('softphoneContactsContainer');
    if (container) {
      container.innerHTML = this.renderContactsListHtml();
      this.attachContactCardListeners();
    }
  }

  private renderContactsListHtml(): string {
    if (this.isSearchingContacts) {
      return `<div style="text-align: center; padding: 40px; color: #94a3b8;"><i class="fas fa-spinner fa-spin" style="margin-right: 8px;"></i>Searching contacts...</div>`;
    }

    if (this.contactsList.length === 0) {
      return `
        <div style="text-align: center; padding: 50px 20px; color: #64748b;">
          <i class="fas fa-address-book" style="font-size: 36px; margin-bottom: 12px; color: #475569;"></i>
          <p style="font-weight: 600; font-size: 14px;">${this.searchContactsQuery ? 'No contacts match your search' : 'Type name or phone number above to search'}</p>
        </div>
      `;
    }

    return `
      <div style="display: flex; flex-direction: column; gap: 10px;">
        ${this.contactsList.map(c => `
          <div style="background: #1e293b; border-radius: 14px; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; border: 1px solid rgba(255,255,255,0.06);">
            <div style="display: flex; align-items: center; gap: 12px;">
              <div style="width: 38px; height: 38px; border-radius: 50%; background: ${c.badge_color || '#3b82f6'}; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 700; color: #fff;">
                ${(c.name ? c.name.charAt(0) : 'C').toUpperCase()}
              </div>
              <div>
                <div style="font-weight: 700; font-size: 14px; color: #fff;">${c.name}</div>
                <div style="font-size: 12px; color: #94a3b8; margin-top: 2px;">
                  +91 ${c.phone} • <span style="color: ${c.badge_color || '#38bdf8'}; font-weight: 600;">${c.source || 'Lead'}</span>
                </div>
              </div>
            </div>
            <div style="display: flex; gap: 6px;">
              <button class="contact-call-btn" data-phone="${c.phone}" data-name="${this.escapeAttr(c.name)}" title="Softphone Call" style="width: 38px; height: 38px; border-radius: 50%; background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); color: #22c55e; cursor: pointer; display: flex; align-items: center; justify-content: center;">
                <i class="fas fa-phone fa-sm"></i>
              </button>
            </div>
          </div>
        `).join('')}
      </div>
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

        <h3 style="font-size: 22px; font-weight: 700; margin: 0 0 4px 0; color: #fff;">${this.selectedContactName || this.dialNumber}</h3>
        ${this.selectedContactName ? `<div style="font-size: 13px; color: #94a3b8; margin-bottom: 6px;">+91 ${this.dialNumber}</div>` : ''}
        <p id="softphoneCallStatusText" style="font-size: 14px; color: #22c55e; font-weight: 600; margin: 0 0 12px 0;">${this.callStatusText}</p>
        <div id="softphoneCallTimer" style="font-size: 22px; font-weight: 700; font-family: monospace; color: #cbd5e1; margin-bottom: 24px;">${mins}:${secs}</div>

        <!-- In-Call Control Grid -->
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 28px;">
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
        <div style="display: flex; flex-direction: column; align-items: center; gap: 16px;">
          <button id="softphoneEndCallBtn" style="width: 72px; height: 72px; border-radius: 50%; background: linear-gradient(135deg, #ef4444, #b91c1c); border: none; color: #fff; font-size: 26px; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 8px 24px rgba(239, 68, 68, 0.4); cursor: pointer;">
            <i class="fas fa-phone-slash"></i>
          </button>

          <button id="inCallSwitchSimBtn" style="padding: 7px 16px; border-radius: 20px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); color: #38bdf8; font-size: 12px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;">
            <i class="fas fa-mobile-screen"></i> Switch to Cellular SIM
          </button>
        </div>
      </div>
    `;
  }

  private renderHistory(): string {
    return `
      <div style="padding: 16px; max-width: 500px; margin: 0 auto;">
        
        <!-- Recents Filters: All, Softphone, Mobile -->
        <div style="display: flex; gap: 8px; margin-bottom: 16px; background: #1e293b; padding: 4px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);">
          <button id="filterAllCallsBtn" style="flex: 1; padding: 7px 8px; border-radius: 8px; font-size: 12px; font-weight: 700; border: none; cursor: pointer; transition: all 0.15s; background: ${this.historyFilter === 'ALL' ? '#3b82f6' : 'transparent'}; color: ${this.historyFilter === 'ALL' ? '#fff' : '#94a3b8'};">
            All Calls
          </button>
          <button id="filterSoftphoneCallsBtn" style="flex: 1; padding: 7px 8px; border-radius: 8px; font-size: 12px; font-weight: 700; border: none; cursor: pointer; transition: all 0.15s; background: ${this.historyFilter === 'SOFTPHONE' ? '#3b82f6' : 'transparent'}; color: ${this.historyFilter === 'SOFTPHONE' ? '#fff' : '#94a3b8'};">
            <i class="fas fa-phone" style="margin-right: 4px;"></i>Softphone
          </button>
          <button id="filterMobileCallsBtn" style="flex: 1; padding: 7px 8px; border-radius: 8px; font-size: 12px; font-weight: 700; border: none; cursor: pointer; transition: all 0.15s; background: ${this.historyFilter === 'MOBILE' ? '#3b82f6' : 'transparent'}; color: ${this.historyFilter === 'MOBILE' ? '#fff' : '#94a3b8'};">
            <i class="fas fa-mobile-screen" style="margin-right: 4px;"></i>Mobile
          </button>
        </div>

        <div id="softphoneHistoryContainer">
          ${this.renderHistoryListHtml()}
        </div>
      </div>
    `;
  }

  private renderHistoryList(): void {
    const container = document.getElementById('softphoneHistoryContainer');
    if (container) {
      container.innerHTML = this.renderHistoryListHtml();
      this.attachHistoryCardListeners();
    }
  }

  private renderHistoryListHtml(): string {
    if (this.isLoadingHistory) {
      return `<div style="text-align: center; padding: 40px; color: #94a3b8;"><i class="fas fa-spinner fa-spin" style="margin-right: 8px;"></i>Loading call history...</div>`;
    }

    // Filter calls based on selected filter
    const filtered = this.recentCalls.filter(c => {
      if (this.historyFilter === 'SOFTPHONE') return c.source === 'softphone' || c.source === 'dialer';
      if (this.historyFilter === 'MOBILE') return c.source === 'native' || !c.source;
      return true;
    });

    if (filtered.length === 0) {
      return `
        <div style="text-align: center; padding: 60px 20px; color: #64748b;">
          <i class="fas fa-phone-slash" style="font-size: 40px; margin-bottom: 12px; color: #475569;"></i>
          <p style="font-weight: 600; font-size: 14px;">No ${this.historyFilter === 'SOFTPHONE' ? 'softphone' : (this.historyFilter === 'MOBILE' ? 'mobile' : '')} calls found</p>
        </div>
      `;
    }

    return `
      <div style="display: flex; flex-direction: column; gap: 10px;">
        ${filtered.map(c => {
          const typeUpper = (c.call_type || 'OUTGOING').toUpperCase();
          const isMissed = typeUpper === 'MISSED' || typeUpper === 'REJECTED';
          const isIncoming = typeUpper === 'INCOMING';
          const icon = isIncoming ? 'fa-arrow-down-left text-primary' : (isMissed ? 'fa-phone-slash text-danger' : 'fa-arrow-up-right text-success');
          const isSoftphone = c.source === 'softphone' || c.source === 'dialer';
          const durationFormatted = this.formatDuration(c.duration_seconds || 0);
          const timeFormatted = this.formatRelativeTime(c.dialed_at || c.timestamp);

          return `
            <div style="background: #1e293b; border-radius: 14px; padding: 13px 16px; display: flex; align-items: center; justify-content: space-between; border: 1px solid rgba(255,255,255,0.06);">
              <div style="display: flex; align-items: center; gap: 12px;">
                <div style="width: 38px; height: 38px; border-radius: 50%; background: ${isSoftphone ? 'rgba(59, 130, 246, 0.15)' : 'rgba(255,255,255,0.06)'}; display: flex; align-items: center; justify-content: center; font-size: 14px;">
                  <i class="fa-solid ${icon}"></i>
                </div>
                <div>
                  <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="font-weight: 700; font-size: 14.5px; color: ${isMissed ? '#f87171' : '#fff'};">${c.contact_name || c.phone_number}</span>
                    <span style="font-size: 9.5px; font-weight: 700; padding: 1px 5px; border-radius: 4px; background: ${isSoftphone ? 'rgba(59, 130, 246, 0.2)' : 'rgba(148, 163, 184, 0.15)'}; color: ${isSoftphone ? '#60a5fa' : '#94a3b8'};">
                      ${isSoftphone ? 'Softphone' : 'Mobile'}
                    </span>
                  </div>
                  <div style="font-size: 11.5px; color: #94a3b8; margin-top: 2px;">
                    ${c.contact_name ? `${c.phone_number} • ` : ''}${timeFormatted} ${durationFormatted ? `(${durationFormatted})` : ''}
                  </div>
                </div>
              </div>
              <button class="history-call-btn" data-phone="${c.phone_number}" data-name="${this.escapeAttr(c.contact_name || '')}" style="width: 40px; height: 40px; border-radius: 50%; background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); color: #22c55e; cursor: pointer; display: flex; align-items: center; justify-content: center;">
                <i class="fas fa-phone fa-sm"></i>
              </button>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  private attachListeners(): void {
    // Mode toggles
    document.getElementById('tabDialerBtn')?.addEventListener('click', () => {
      this.activeTab = 'dialer';
      this.render();
    });

    document.getElementById('tabContactsBtn')?.addEventListener('click', () => {
      this.activeTab = 'contacts';
      this.render();
      if (this.contactsList.length === 0) {
        this.searchContacts('a');
      }
    });

    document.getElementById('tabHistoryBtn')?.addEventListener('click', () => {
      this.activeTab = 'history';
      this.render();
    });

    // Recents Filter Buttons
    document.getElementById('filterAllCallsBtn')?.addEventListener('click', () => {
      this.historyFilter = 'ALL';
      this.render();
    });
    document.getElementById('filterSoftphoneCallsBtn')?.addEventListener('click', () => {
      this.historyFilter = 'SOFTPHONE';
      this.render();
    });
    document.getElementById('filterMobileCallsBtn')?.addEventListener('click', () => {
      this.historyFilter = 'MOBILE';
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
      this.selectedContactName = '';
      this.updateDialDisplay();
      this.triggerLiveSearch();
    });

    // Contacts Tab search input
    const contactsSearchInput = document.getElementById('softphoneContactsSearchInput') as HTMLInputElement;
    contactsSearchInput?.addEventListener('input', () => {
      this.searchContactsQuery = contactsSearchInput.value;
      if (this.searchDebounceTimer) clearTimeout(this.searchDebounceTimer);
      this.searchDebounceTimer = setTimeout(() => {
        this.searchContacts(this.searchContactsQuery || 'a');
      }, 200);
    });

    // Call Actions
    document.getElementById('softphoneStartCallBtn')?.addEventListener('click', () => this.startCall());
    document.getElementById('softphoneDirectSimBtn')?.addEventListener('click', () => this.startCall(undefined, undefined, true));
    document.getElementById('inCallSwitchSimBtn')?.addEventListener('click', () => this.triggerNativeSimCall());
    document.getElementById('softphoneEndCallBtn')?.addEventListener('click', () => this.endCall());
    document.getElementById('callMuteBtn')?.addEventListener('click', () => this.toggleMute());
    document.getElementById('callSpeakerBtn')?.addEventListener('click', () => this.toggleSpeaker());
    document.getElementById('callHoldBtn')?.addEventListener('click', () => this.toggleHold());

    this.attachHistoryCardListeners();
    this.attachContactCardListeners();
  }

  private attachHistoryCardListeners(): void {
    this.container.querySelectorAll('.history-call-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const phone = (btn as HTMLElement).dataset.phone;
        const name = (btn as HTMLElement).dataset.name;
        if (phone) this.startCall(phone, name);
      });
    });
  }

  private attachContactCardListeners(): void {
    this.container.querySelectorAll('.contact-call-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const phone = (btn as HTMLElement).dataset.phone;
        const name = (btn as HTMLElement).dataset.name;
        if (phone) this.startCall(phone, name);
      });
    });
  }
}
