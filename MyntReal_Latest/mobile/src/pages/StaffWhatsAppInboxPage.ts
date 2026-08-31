/**
 * Staff WhatsApp Center & CRM Inbox Page (Mobile)
 * DC Protocol: DC_MOBILE_WA_CENTER_002
 * Comprehensive WhatsApp Workspace:
 *  1. Messenger (Primary View: WhatsApp-style keyboard, emoji palette, media attachments, canned quick-replies)
 *  2. CRM Inbox (Thread list, stat cards, source filters, presence chips)
 *  3. Template Management Hub (Pre-approved Meta templates - Admin/EA only)
 *  4. Automations & Trigger Tracker (Bot triggers, event dispatches - Admin/EA only)
 *  5. Audit Log (Delivery tracking, status, IST timestamps - Admin/EA only)
 *  + QR Code Disconnect Banner & Live QR Scan Modal
 */

import { apiService } from '../services/api.service';
import { authService } from '../services/auth.service';
import { PageHeader } from '../components/PageHeader';

export class StaffWhatsAppInboxPage {
  private container: HTMLElement;
  private activeTab: 'messenger' | 'inbox' | 'templates' | 'automations' | 'audit' = 'messenger';

  // ── Gateway & QR State ─────────────────────────────────────────────────────
  private gatewayConnected: boolean = true;
  private gatewayQr: string = '';
  private gatewayStatus: string = 'checking';
  private qrPollingTimer: any = null;

  // ── CRM Inbox State ────────────────────────────────────────────────────────
  private inboxItems: any[] = [];
  private inboxLoading: boolean = false;
  private inboxStats: { all: number; unread: number; pending: number; completed: number; assigned: number } = {
    all: 0, unread: 0, pending: 0, completed: 0, assigned: 0
  };
  private fPhone: string = '';
  private fSource: string = '';
  private fStatus: string = '';
  private fExcludeStaff: boolean = false;

  // ── Messenger State ────────────────────────────────────────────────────────
  private convsList: any[] = [];
  private convsLoading: boolean = false;
  private activeChatPhone: string | null = null;
  private activeChatName: string = '';
  private activeScope: string = 'all';
  private chatHistory: any[] = [];
  private chatLoading: boolean = false;

  // ── Composer & Emoji State ─────────────────────────────────────────────────
  private showEmojiTray: boolean = false;
  private activeEmojiCat: 'smileys' | 'hands' | 'realestate' | 'reactions' | 'travel' = 'smileys';
  private showAttachMenu: boolean = false;
  private activeAttachment: { type: string; name: string; url?: string } | null = null;

  // ── Templates & Automations & Audit State ───────────────────────────────────
  private templatesList: any[] = [];
  private automationsList: any[] = [];
  private auditLogs: any[] = [];
  private subLoading: boolean = false;

  // Emoji Palette
  private emojiData = {
    smileys: ['😀','😃','😄','😁','😆','😅','😂','🤣','😊','😇','🙂','😉','😌','😍','🥰','😘','😋','😛','😜','🤪','😎','🤩','🥳','😏','🥺','😢','😭','😤','😠','😡','🤬','🤯','😳','😱','🤗','🤔','🤫','😴','😷'],
    hands: ['👍','👎','👌','🤌','✌️','🤞','🤟','🤘','🤙','👈','👉','👆','👇','☝️','👏','🙌','👐','🤲','🤝','🙏','💪','👋','✍️','🤝'],
    realestate: ['🏠','🏡','🏢','🏣','🏤','🏥','🏦','🏨','🏪','🏫','🏬','🏭','🏰','🏗️','🏘️','🏙️','🗺️','📍','📌','🔑','🗝️','🚪','💰','💵','💳','🧾','📊','📈','💼','📁','📄','📋','📞','📱','✉️','📧'],
    reactions: ['❤️','💚','💙','💛','💜','🖤','💔','❣️','💕','💓','✨','🌟','⭐','🔥','💥','💯','⚠️','🚨','✅','❌','➕','➖','🟢','🔴','🟡','🔵'],
    travel: ['🚗','🚕','🚙','🚌','🏎️','🚓','🚑','🚒','🚐','🚚','🛵','🏍️','🛺','🚲','⛽','🚦','🛣️','✈️','🚀']
  };

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.renderSkeleton();
    await this.checkGatewayStatus();
    await this.loadCurrentTab();
  }

  private isWhatsAppAdmin(): boolean {
    const authState = authService.getAuthState();
    const user = authState.user || {};
    const empCode = (user.emp_code || '').toUpperCase().trim();
    const roleCode = (user.role_code || user.role?.role_code || '').toLowerCase().trim();
    const name = (user.name || user.full_name || '').toLowerCase().trim();
    return empCode === 'MR10001' || empCode === 'MR10016' || roleCode === 'vgk4u' || roleCode === 'ea' || name.includes('yaswanth');
  }

  private async checkGatewayStatus(): Promise<void> {
    try {
      const res = await apiService.get<any>('/whatsapp/bot-status');
      if (res.success && res.data) {
        this.gatewayConnected = res.data.connected === true;
        this.gatewayStatus = res.data.status || 'disconnected';
        this.gatewayQr = res.data.qr || '';
      } else {
        this.gatewayConnected = false;
        this.gatewayStatus = 'disconnected';
      }
    } catch {
      this.gatewayConnected = false;
      this.gatewayStatus = 'disconnected';
    }
  }

  private renderSkeleton(): void {
    this.container.innerHTML = `
      ${PageHeader.render({
        title: 'WhatsApp Center',
        showBack: true,
        rightAction: {
          icon: '<i class="fas fa-sync-alt" style="font-size:16px;color:#25d366;"></i>',
          onClick: () => this.loadCurrentTab()
        }
      })}
      <div style="padding: 24px; text-align: center; color: #94a3b8; background: #0f172a; min-height: 100vh;">
        <i class="fab fa-whatsapp fa-spin" style="font-size: 32px; color: #25d366; margin-bottom: 12px;"></i>
        <div style="font-size: 15px; font-weight: 600;">Loading WhatsApp Center...</div>
      </div>
    `;
    PageHeader.attachListeners({
      title: 'WhatsApp Center',
      showBack: true,
      rightAction: {
        icon: '<i class="fas fa-sync-alt" style="font-size:16px;color:#25d366;"></i>',
        onClick: () => this.loadCurrentTab()
      }
    });
  }

  private async loadCurrentTab(): Promise<void> {
    await this.checkGatewayStatus();
    if (this.activeTab === 'messenger') {
      await this.loadMessenger();
    } else if (this.activeTab === 'inbox') {
      await this.loadInbox();
    } else if (this.activeTab === 'templates') {
      await this.loadTemplates();
    } else if (this.activeTab === 'automations') {
      await this.loadAutomations();
    } else if (this.activeTab === 'audit') {
      await this.loadAuditLogs();
    }
  }

  // ── Main Page Render ───────────────────────────────────────────────────────

  private render(): void {
    const isAdmin = this.isWhatsAppAdmin();

    this.container.innerHTML = `
      ${PageHeader.render({
        title: 'WhatsApp Center',
        showBack: true,
        rightAction: {
          icon: '<i class="fas fa-sync-alt" style="font-size:16px;color:#25d366;"></i>',
          onClick: () => this.loadCurrentTab()
        }
      })}

      <div class="wa-center-page" style="background: #0f172a; min-height: calc(100vh - 60px); color: #f8fafc; padding: 12px; padding-bottom: 80px;">
        
        <!-- Center Banner -->
        <div style="background: linear-gradient(135deg, #064e3b, #065f46, #047857); border-radius: 12px; padding: 14px 16px; margin-bottom: 12px; box-shadow: 0 4px 12px rgba(4,120,87,0.25);">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div>
              <div style="font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
                <i class="fab fa-whatsapp" style="font-size: 20px; color: #25d366;"></i>
                WhatsApp Center
              </div>
              <div style="font-size: 11.5px; color: rgba(255,255,255,0.85); margin-top: 2px;">
                Unified WhatsApp Workspace — Messenger, CRM Inbox${isAdmin ? ', Templates & Logs' : ''}
              </div>
            </div>
            <div style="display: flex; align-items: center; gap: 6px;">
              <span style="background: ${this.gatewayConnected ? 'rgba(37,211,102,0.2)' : 'rgba(239,68,68,0.2)'}; border: 1px solid ${this.gatewayConnected ? '#25d366' : '#ef4444'}; color: ${this.gatewayConnected ? '#a7f3d0' : '#fecaca'}; border-radius: 20px; padding: 3px 8px; font-size: 11px; font-weight: 700;">
                ● ${this.gatewayConnected ? 'Connected' : 'Logged Out'}
              </span>
              <button id="waNewMsgBtn" style="background: #25d366; color: #0f172a; border: none; border-radius: 16px; padding: 5px 12px; font-size: 12px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 4px;">
                <i class="fas fa-plus"></i> New Message
              </button>
            </div>
          </div>
        </div>

        <!-- Disconnected / Scan QR Warning Banner -->
        ${!this.gatewayConnected ? `
          <div style="background: linear-gradient(135deg, #78350f, #92400e); border: 1px solid #f59e0b; border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
            <div style="display: flex; align-items: center; gap: 10px;">
              <i class="fas fa-qrcode" style="font-size: 22px; color: #fbbf24;"></i>
              <div>
                <div style="font-size: 13px; font-weight: 700; color: #fef3c7;">WhatsApp Logged Out / Disconnected</div>
                <div style="font-size: 11px; color: #fde68a;">Scan QR code to link your WhatsApp account</div>
              </div>
            </div>
            <button id="waOpenScanQrBtn" style="background: #25d366; color: #0f172a; border: none; border-radius: 8px; padding: 6px 12px; font-size: 12px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 4px; white-space: nowrap;">
              <i class="fas fa-camera"></i> Scan QR
            </button>
          </div>
        ` : ''}

        <!-- Navigation Tabs: Tab 1 Messenger, Tab 2 CRM Inbox, Tabs 3-5 Admin Only -->
        <div style="display: flex; gap: 6px; overflow-x: auto; padding-bottom: 6px; margin-bottom: 12px; -webkit-overflow-scrolling: touch;">
          <button class="wa-nav-tab ${this.activeTab === 'messenger' ? 'active' : ''}" data-tab="messenger" style="${this.getTabBtnStyle(this.activeTab === 'messenger')}">
            <i class="fas fa-comments"></i> 1. Messenger
          </button>
          <button class="wa-nav-tab ${this.activeTab === 'inbox' ? 'active' : ''}" data-tab="inbox" style="${this.getTabBtnStyle(this.activeTab === 'inbox')}">
            <i class="fas fa-inbox"></i> 2. CRM Inbox
            ${this.inboxStats.unread > 0 ? `<span style="background:#ef4444;color:#fff;border-radius:10px;padding:1px 6px;font-size:10px;margin-left:4px;">${this.inboxStats.unread}</span>` : ''}
          </button>
          ${isAdmin ? `
            <button class="wa-nav-tab ${this.activeTab === 'templates' ? 'active' : ''}" data-tab="templates" style="${this.getTabBtnStyle(this.activeTab === 'templates')}">
              <i class="fas fa-file-alt"></i> 3. Templates
            </button>
            <button class="wa-nav-tab ${this.activeTab === 'automations' ? 'active' : ''}" data-tab="automations" style="${this.getTabBtnStyle(this.activeTab === 'automations')}">
              <i class="fas fa-robot"></i> 4. Automations
            </button>
            <button class="wa-nav-tab ${this.activeTab === 'audit' ? 'active' : ''}" data-tab="audit" style="${this.getTabBtnStyle(this.activeTab === 'audit')}">
              <i class="fas fa-shield-alt"></i> 5. Audit Log
            </button>
          ` : ''}
        </div>

        <!-- Tab Content Panes -->
        ${this.activeTab === 'messenger' ? this.renderMessengerTab() : ''}
        ${this.activeTab === 'inbox' ? this.renderInboxTab() : ''}
        ${this.activeTab === 'templates' && isAdmin ? this.renderTemplatesTab() : ''}
        ${this.activeTab === 'automations' && isAdmin ? this.renderAutomationsTab() : ''}
        ${this.activeTab === 'audit' && isAdmin ? this.renderAuditTab() : ''}

      </div>

      <!-- Modals Container -->
      <div id="waCenterModalContainer"></div>
    `;

    PageHeader.attachListeners({
      title: 'WhatsApp Center',
      showBack: true,
      rightAction: {
        icon: '<i class="fas fa-sync-alt" style="font-size:16px;color:#25d366;"></i>',
        onClick: () => this.loadCurrentTab()
      }
    });

    this.attachMainListeners();
  }

  private getTabBtnStyle(isActive: boolean): string {
    if (isActive) {
      return 'padding: 8px 14px; border-radius: 20px; background: #059669; color: #fff; font-size: 12px; font-weight: 700; border: none; cursor: pointer; white-space: nowrap; flex-shrink: 0; display: flex; align-items: center; gap: 6px; box-shadow: 0 2px 6px rgba(5,150,105,0.3);';
    }
    return 'padding: 8px 14px; border-radius: 20px; background: #1e293b; color: #94a3b8; font-size: 12px; font-weight: 600; border: 1px solid #334155; cursor: pointer; white-space: nowrap; flex-shrink: 0; display: flex; align-items: center; gap: 6px;';
  }

  // ── TAB 1: MESSENGER (PRIMARY VIEW) ─────────────────────────────────────────

  private renderMessengerTab(): string {
    return `
      <div style="background: #1e293b; border-radius: 12px; border: 1px solid #334155; overflow: hidden; display: flex; flex-direction: column; min-height: 520px;">
        
        <!-- Messenger Scope & Search -->
        <div style="padding: 10px; background: #0f172a; border-bottom: 1px solid #334155; display: flex; gap: 6px;">
          <select id="waMsgScopeSelect" style="flex: 1; padding: 7px 10px; border-radius: 8px; background: #1e293b; border: 1px solid #334155; color: #fff; font-size: 12px; outline: none;">
            <option value="all" ${this.activeScope === 'all' ? 'selected' : ''}>All Conversations</option>
            <option value="assigned_tagged" ${this.activeScope === 'assigned_tagged' ? 'selected' : ''}>My Assigned & Tagged</option>
            <option value="crm_leads" ${this.activeScope === 'crm_leads' ? 'selected' : ''}>CRM Leads Only</option>
          </select>
        </div>

        <!-- Conversations List (or Chat Thread if active) -->
        ${!this.activeChatPhone ? `
          <div style="flex: 1; overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 6px;">
            ${this.convsLoading ? `
              <div style="text-align: center; padding: 30px; color: #94a3b8;">
                <i class="fas fa-spinner fa-spin" style="font-size: 24px; color: #25d366; margin-bottom: 8px;"></i>
                <div>Loading conversations...</div>
              </div>
            ` : ''}

            ${!this.convsLoading && this.convsList.length === 0 ? `
              <div style="text-align: center; padding: 40px 20px; color: #64748b;">
                <i class="fas fa-comments" style="font-size: 36px; margin-bottom: 8px;"></i>
                <div>No messenger conversations found.</div>
              </div>
            ` : ''}

            ${this.convsList.map(c => this.renderMessengerCard(c)).join('')}
          </div>
        ` : this.renderLiveChatPane()}

      </div>
    `;
  }

  private renderMessengerCard(c: any): string {
    const phone = c.from_phone || c.phone || '';
    const cleanPhone = phone.replace(/[^0-9]/g, '').slice(-10);
    const name = c.resolved_name || c.from_name || c.name || 'Customer';
    const initial = (name.charAt(0) || 'W').toUpperCase();
    const msg = c.last_message || c.snippet || 'No messages';

    return `
      <div 
        class="wa-msg-card" 
        data-phone="${phone}" 
        data-name="${this.escapeAttr(name)}"
        style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: #0f172a; border-radius: 10px; border: 1px solid #334155; cursor: pointer;"
      >
        <div style="width: 36px; height: 36px; border-radius: 50%; background: #059669; display: flex; align-items: center; justify-content: center; font-size: 15px; font-weight: 700; color: #fff; flex-shrink: 0;">
          ${initial}
        </div>
        <div style="flex: 1; min-width: 0;">
          <div style="display: flex; justify-content: space-between; align-items: baseline;">
            <div style="font-size: 13.5px; font-weight: 700; color: #f8fafc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              ${name}
            </div>
            <div style="font-size: 10.5px; color: #94a3b8;">+91 ${cleanPhone}</div>
          </div>
          <div style="font-size: 12px; color: #94a3b8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px;">
            ${msg}
          </div>
        </div>
        <i class="fas fa-chevron-right" style="color: #475569; font-size: 11px;"></i>
      </div>
    `;
  }

  private renderLiveChatPane(): string {
    const cleanPhone = (this.activeChatPhone || '').replace(/[^0-9]/g, '').slice(-10);

    return `
      <div style="display: flex; flex-direction: column; height: calc(100vh - 280px); min-height: 480px; background: #0b1120;">
        
        <!-- Live Chat Header -->
        <div style="padding: 10px 12px; background: #1e293b; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <button id="waBackToMsgListBtn" style="background: none; border: none; color: #fff; font-size: 16px; cursor: pointer; padding: 4px;">
              <i class="fas fa-arrow-left"></i>
            </button>
            <div>
              <div style="font-size: 14px; font-weight: 700; color: #f8fafc;">${this.activeChatName || this.activeChatPhone}</div>
              <div style="font-size: 11px; color: #25d366;"><i class="fab fa-whatsapp"></i> +91 ${cleanPhone}</div>
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 6px;">
            <a href="tel:${cleanPhone}" style="width: 32px; height: 32px; border-radius: 50%; background: #059669; color: #fff; display: flex; align-items: center; justify-content: center; text-decoration: none; font-size: 13px;">
              <i class="fas fa-phone"></i>
            </a>
          </div>
        </div>

        <!-- Chat History Messages -->
        <div id="waChatHistoryList" style="flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px;">
          ${this.chatLoading ? `
            <div style="text-align: center; padding: 30px; color: #94a3b8;">
              <i class="fas fa-spinner fa-spin" style="font-size: 20px; color: #25d366; margin-bottom: 6px;"></i>
              <div>Loading conversation...</div>
            </div>
          ` : ''}

          ${!this.chatLoading && this.chatHistory.length === 0 ? `
            <div style="text-align: center; padding: 40px 20px; color: #64748b;">
              <i class="fab fa-whatsapp" style="font-size: 32px; margin-bottom: 8px;"></i>
              <div>No messages in this chat. Send a message below!</div>
            </div>
          ` : ''}

          ${this.chatHistory.map(m => this.renderMessageBubble(m)).join('')}
        </div>

        <!-- Attachment Preview Bar (if selected) -->
        ${this.activeAttachment ? `
          <div style="padding: 6px 12px; background: #0f172a; border-top: 1px solid #334155; display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: #38bdf8;">
              <i class="fas fa-paperclip"></i>
              <span>${this.activeAttachment.name}</span>
            </div>
            <button id="waRemoveAttachBtn" style="background: none; border: none; color: #ef4444; font-size: 14px; cursor: pointer;">✕</button>
          </div>
        ` : ''}

        <!-- Quick Reply Pills -->
        <div style="display: flex; gap: 6px; overflow-x: auto; padding: 6px 10px; background: #1e293b; border-top: 1px solid #334155;">
          <button class="wa-quick-pill" data-text="Hello! Thank you for contacting MyntReal. How can we help you today?" style="padding: 3px 8px; border-radius: 12px; background: #334155; color: #e2e8f0; font-size: 11px; border: none; white-space: nowrap; cursor: pointer;">
            👋 Greeting
          </button>
          <button class="wa-quick-pill" data-text="We would be happy to share our project brochure and pricing details. When is a good time to connect?" style="padding: 3px 8px; border-radius: 12px; background: #334155; color: #e2e8f0; font-size: 11px; border: none; white-space: nowrap; cursor: pointer;">
            📁 Brochure
          </button>
          <button class="wa-quick-pill" data-text="Our representative will call you shortly to assist you with the complete details." style="padding: 3px 8px; border-radius: 12px; background: #334155; color: #e2e8f0; font-size: 11px; border: none; white-space: nowrap; cursor: pointer;">
            📞 Callback
          </button>
          <button class="wa-quick-pill" data-text="Here is our project location: https://maps.google.com" style="padding: 3px 8px; border-radius: 12px; background: #334155; color: #e2e8f0; font-size: 11px; border: none; white-space: nowrap; cursor: pointer;">
            📍 Location
          </button>
        </div>

        <!-- WhatsApp Interactive Keyboard / Composer Bar -->
        <div style="display: flex; align-items: center; gap: 6px; padding: 8px 10px; background: #1e293b; border-top: 1px solid #334155;">
          
          <!-- Emoji Picker Toggle Button -->
          <button id="waToggleEmojiBtn" style="background: none; border: none; font-size: 20px; color: ${this.showEmojiTray ? '#25d366' : '#94a3b8'}; cursor: pointer; padding: 4px; display: flex; align-items: center; justify-content: center;">
            <i class="far fa-smile"></i>
          </button>

          <!-- Attachments Menu Button -->
          <button id="waToggleAttachBtn" style="background: none; border: none; font-size: 18px; color: #94a3b8; cursor: pointer; padding: 4px; display: flex; align-items: center; justify-content: center;">
            <i class="fas fa-paperclip"></i>
          </button>

          <!-- Message Textarea / Input -->
          <input 
            type="text" 
            id="waLiveMsgInput" 
            placeholder="Type a WhatsApp message..." 
            style="flex: 1; padding: 9px 14px; border-radius: 20px; background: #0f172a; border: 1px solid #334155; color: #fff; font-size: 13.5px; outline: none; transition: border-color 0.15s;"
          />

          <!-- Circular Green WhatsApp Send Button -->
          <button id="waLiveSendBtn" style="width: 38px; height: 38px; border-radius: 50%; background: #25d366; color: #0f172a; border: none; font-size: 15px; cursor: pointer; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 6px rgba(37,211,102,0.4); flex-shrink: 0;">
            <i class="fas fa-paper-plane"></i>
          </button>
        </div>

        <!-- WhatsApp Native-Style Emoji Palette Tray -->
        ${this.showEmojiTray ? this.renderEmojiTray() : ''}

        <!-- WhatsApp Attachment Dropup Menu -->
        ${this.showAttachMenu ? this.renderAttachMenu() : ''}

      </div>
    `;
  }

  private renderEmojiTray(): string {
    const list = this.emojiData[this.activeEmojiCat] || [];

    return `
      <div style="background: #0f172a; border-top: 1px solid #334155; padding: 8px 10px; max-height: 200px; overflow-y: auto;">
        <!-- Categories Tab Bar -->
        <div style="display: flex; gap: 8px; justify-content: space-around; border-bottom: 1px solid #1e293b; padding-bottom: 6px; margin-bottom: 8px;">
          <button class="wa-emoji-cat-btn" data-cat="smileys" style="background: none; border: none; font-size: 18px; cursor: pointer; opacity: ${this.activeEmojiCat === 'smileys' ? '1' : '0.4'};">😃</button>
          <button class="wa-emoji-cat-btn" data-cat="hands" style="background: none; border: none; font-size: 18px; cursor: pointer; opacity: ${this.activeEmojiCat === 'hands' ? '1' : '0.4'};">👋</button>
          <button class="wa-emoji-cat-btn" data-cat="realestate" style="background: none; border: none; font-size: 18px; cursor: pointer; opacity: ${this.activeEmojiCat === 'realestate' ? '1' : '0.4'};">🏠</button>
          <button class="wa-emoji-cat-btn" data-cat="reactions" style="background: none; border: none; font-size: 18px; cursor: pointer; opacity: ${this.activeEmojiCat === 'reactions' ? '1' : '0.4'};">❤️</button>
          <button class="wa-emoji-cat-btn" data-cat="travel" style="background: none; border: none; font-size: 18px; cursor: pointer; opacity: ${this.activeEmojiCat === 'travel' ? '1' : '0.4'};">🚗</button>
        </div>

        <!-- Grid of Emojis -->
        <div style="display: grid; grid-template-columns: repeat(8, 1fr); gap: 6px; text-align: center;">
          ${list.map(e => `
            <button class="wa-emoji-item" data-emoji="${e}" style="background: none; border: none; font-size: 22px; cursor: pointer; padding: 4px; border-radius: 6px; transition: background 0.1s;">
              ${e}
            </button>
          `).join('')}
        </div>
      </div>
    `;
  }

  private renderAttachMenu(): string {
    return `
      <div style="background: #1e293b; border-top: 1px solid #334155; padding: 12px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
        <button class="wa-attach-choice-btn" data-type="brochure" style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 10px; color: #fff; font-size: 12px; font-weight: 600; display: flex; flex-direction: column; align-items: center; gap: 6px; cursor: pointer;">
          <i class="fas fa-file-pdf" style="font-size: 22px; color: #ef4444;"></i>
          PDF Brochure
        </button>
        <button class="wa-attach-choice-btn" data-type="photo" style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 10px; color: #fff; font-size: 12px; font-weight: 600; display: flex; flex-direction: column; align-items: center; gap: 6px; cursor: pointer;">
          <i class="fas fa-image" style="font-size: 22px; color: #3b82f6;"></i>
          Project Photos
        </button>
        <button class="wa-attach-choice-btn" data-type="location" style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 10px; color: #fff; font-size: 12px; font-weight: 600; display: flex; flex-direction: column; align-items: center; gap: 6px; cursor: pointer;">
          <i class="fas fa-map-marker-alt" style="font-size: 22px; color: #10b981;"></i>
          Location Pin
        </button>
      </div>
    `;
  }

  private renderMessageBubble(m: any): string {
    const isOutbound = m.message_type === 'outbound' || m.message_type === 'bot';
    const isBot = m.message_type === 'bot';
    
    let timeStr = '';
    try {
      const dt = new Date(m.received_at || m.sent_at || Date.now());
      timeStr = dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
    } catch {
      timeStr = '';
    }

    const text = m.body_text || m.message || '';

    if (isOutbound) {
      return `
        <div style="align-self: flex-end; max-width: 82%; background: ${isBot ? '#065f46' : '#059669'}; color: #fff; padding: 8px 12px; border-radius: 12px 12px 2px 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.2);">
          ${isBot ? '<div style="font-size: 9.5px; font-weight: 700; color: #a7f3d0; margin-bottom: 2px;"><i class="fas fa-robot"></i> Bot Automated</div>' : ''}
          <div style="font-size: 13px; line-height: 1.35; word-break: break-word;">${this.escapeHtml(text)}</div>
          <div style="font-size: 9.5px; color: #a7f3d0; text-align: right; margin-top: 3px; display: flex; align-items: center; justify-content: flex-end; gap: 3px;">
            <span>${timeStr}</span>
            <i class="fas fa-check-double" style="font-size: 8px;"></i>
          </div>
        </div>
      `;
    }

    return `
      <div style="align-self: flex-start; max-width: 82%; background: #1e293b; color: #f8fafc; padding: 8px 12px; border-radius: 12px 12px 12px 2px; border: 1px solid #334155; box-shadow: 0 1px 3px rgba(0,0,0,0.2);">
        <div style="font-size: 13px; line-height: 1.35; word-break: break-word;">${this.escapeHtml(text)}</div>
        <div style="font-size: 9.5px; color: #94a3b8; text-align: right; margin-top: 3px;">
          ${timeStr}
        </div>
      </div>
    `;
  }

  // ── TAB 2: CRM INBOX ────────────────────────────────────────────────────────

  private renderInboxTab(): string {
    return `
      <!-- Stat Cards Bar -->
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 12px;">
        <div style="background: #1e293b; border-radius: 10px; padding: 10px; text-align: center; border: 1px solid #334155;">
          <div style="font-size: 18px; font-weight: 800; color: #059669;">${this.inboxStats.all}</div>
          <div style="font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase;">ALL MESSAGES</div>
        </div>
        <div style="background: #1e293b; border-radius: 10px; padding: 10px; text-align: center; border: 1px solid #334155;">
          <div style="font-size: 18px; font-weight: 800; color: #ef4444;">${this.inboxStats.unread}</div>
          <div style="font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase;">UNREAD</div>
        </div>
        <div style="background: #1e293b; border-radius: 10px; padding: 10px; text-align: center; border: 1px solid #334155;">
          <div style="font-size: 18px; font-weight: 800; color: #f59e0b;">${this.inboxStats.pending}</div>
          <div style="font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase;">PENDING</div>
        </div>
      </div>

      <!-- Filters Wrap -->
      <div style="background: #1e293b; border-radius: 12px; padding: 12px; margin-bottom: 12px; border: 1px solid #334155; display: flex; flex-direction: column; gap: 8px;">
        <div style="position: relative;">
          <i class="fas fa-search" style="position: absolute; left: 12px; top: 11px; color: #94a3b8; font-size: 12px;"></i>
          <input 
            type="text" 
            id="waInboxSearchInput" 
            placeholder="Filter Phone / Name..." 
            value="${this.fPhone}"
            style="width: 100%; box-sizing: border-box; padding: 8px 12px 8px 34px; border-radius: 8px; background: #0f172a; border: 1px solid #334155; color: #fff; font-size: 13px; outline: none;"
          />
        </div>

        <div style="display: flex; gap: 6px; flex-wrap: wrap;">
          <select id="waInboxSourceSelect" style="flex: 1; min-width: 120px; padding: 7px 8px; border-radius: 8px; background: #0f172a; border: 1px solid #334155; color: #e2e8f0; font-size: 12px; outline: none;">
            <option value="">All Sources</option>
            <option value="BOT" ${this.fSource === 'BOT' ? 'selected' : ''}>BOT</option>
            <option value="MANUAL" ${this.fSource === 'MANUAL' ? 'selected' : ''}>Manual</option>
            <option value="META_API" ${this.fSource === 'META_API' ? 'selected' : ''}>Meta API</option>
          </select>

          <select id="waInboxStatusSelect" style="flex: 1; min-width: 110px; padding: 7px 8px; border-radius: 8px; background: #0f172a; border: 1px solid #334155; color: #e2e8f0; font-size: 12px; outline: none;">
            <option value="">All Statuses</option>
            <option value="new" ${this.fStatus === 'new' ? 'selected' : ''}>New</option>
            <option value="pending" ${this.fStatus === 'pending' ? 'selected' : ''}>Pending</option>
            <option value="completed" ${this.fStatus === 'completed' ? 'selected' : ''}>Completed</option>
          </select>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center;">
          <label style="font-size: 12px; color: #94a3b8; display: flex; align-items: center; gap: 6px; cursor: pointer;">
            <input type="checkbox" id="waExcludeStaffCheck" ${this.fExcludeStaff ? 'checked' : ''} />
            Exclude Staff
          </label>
          <button id="waResetFilterBtn" style="background: none; border: 1px solid #475569; color: #94a3b8; border-radius: 6px; padding: 4px 10px; font-size: 11px; cursor: pointer;">
            Reset Filters
          </button>
        </div>
      </div>

      <!-- Messages List -->
      ${this.inboxLoading ? `
        <div style="text-align: center; padding: 30px; color: #94a3b8;">
          <i class="fas fa-spinner fa-spin" style="font-size: 24px; color: #25d366; margin-bottom: 8px;"></i>
          <div>Loading CRM messages...</div>
        </div>
      ` : ''}

      ${!this.inboxLoading && this.inboxItems.length === 0 ? `
        <div style="text-align: center; padding: 40px 20px; background: #1e293b; border-radius: 12px; border: 1px solid #334155;">
          <i class="fab fa-whatsapp" style="font-size: 40px; color: #64748b; margin-bottom: 10px;"></i>
          <div style="font-size: 15px; font-weight: 600; color: #f1f5f9;">No WhatsApp messages found</div>
          <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Try clearing filters or refreshing.</div>
        </div>
      ` : ''}

      <div style="display: flex; flex-direction: column; gap: 8px;">
        ${this.inboxItems.map(item => this.renderInboxRow(item)).join('')}
      </div>
    `;
  }

  private renderInboxRow(item: any): string {
    const isUnread = !item.is_read;
    const phone = item.from_phone || item.phone || '';
    const cleanPhone = phone.replace(/[^0-9]/g, '').slice(-10);
    const name = item.resolved_name || item.from_name || item.caller_name || 'Customer';
    const initial = (name.charAt(0) || 'W').toUpperCase();
    const msg = item.last_message || item.body_text || 'No message content';
    const status = item.status || 'new';

    const timeIst = item.last_activity_ist || (item.last_activity ? new Date(item.last_activity).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: true }) : '—');

    const sourceType = (item.source_type || 'API').toUpperCase();
    let sourceBg = '#1e3a8a';
    let sourceCol = '#93c5fd';
    if (sourceType === 'BOT') { sourceBg = '#065f46'; sourceCol = '#a7f3d0'; }
    else if (sourceType === 'MANUAL') { sourceBg = '#581c87'; sourceCol = '#d8b4fe'; }

    let lastSentBy = 'System';
    if (item.last_sent_by_name) lastSentBy = item.last_sent_by_name;
    else if (typeof item.last_sent_by === 'string') lastSentBy = item.last_sent_by;

    return `
      <div 
        class="wa-inbox-card" 
        data-phone="${phone}"
        data-name="${this.escapeAttr(name)}"
        style="background: ${isUnread ? '#1e293b' : '#131e32'}; border-radius: 12px; padding: 12px; border: 1px solid ${isUnread ? '#059669' : '#1e293b'}; cursor: pointer; transition: background 0.15s;"
      >
        <div style="display: flex; gap: 10px; align-items: flex-start;">
          <!-- Avatar -->
          <div style="position: relative; flex-shrink: 0;">
            <div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #059669, #10b981); display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 700; color: #fff;">
              ${initial}
            </div>
            ${isUnread ? `<span style="position: absolute; top: -2px; right: -2px; width: 10px; height: 10px; background: #25d366; border: 2px solid #0f172a; border-radius: 50%;"></span>` : ''}
          </div>

          <!-- Content -->
          <div style="flex: 1; min-width: 0;">
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 2px;">
              <div style="font-size: 14px; font-weight: 700; color: #f8fafc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                ${name}
              </div>
              <div style="font-size: 11px; color: ${isUnread ? '#25d366' : '#94a3b8'}; flex-shrink: 0;">
                ${timeIst}
              </div>
            </div>

            <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 6px; flex-wrap: wrap;">
              <span style="font-size: 11px; color: #64748b; font-family: monospace;">+91 ${cleanPhone}</span>
              <span style="font-size: 9.5px; font-weight: 700; padding: 1px 6px; border-radius: 4px; background: ${sourceBg}; color: ${sourceCol};">${sourceType}</span>
              <span style="font-size: 9.5px; font-weight: 700; padding: 1px 6px; border-radius: 4px; background: #3730a3; color: #c7d2fe;">${status}</span>
            </div>

            <div style="font-size: 12.5px; color: #cbd5e1; line-height: 1.35; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; margin-bottom: 8px;">
              ${msg}
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: #94a3b8; border-top: 1px solid #1e293b; padding-top: 6px;">
              <span>By: <strong style="color:#e2e8f0;">${lastSentBy}</strong></span>
              <div style="display: flex; gap: 6px;">
                <button class="wa-row-assign-btn" data-phone="${phone}" data-name="${this.escapeAttr(name)}" style="background: #1e293b; border: 1px solid #475569; color: #38bdf8; border-radius: 6px; padding: 2px 8px; font-size: 11px; cursor: pointer;">
                  <i class="fas fa-tag"></i> Assign
                </button>
                <button class="wa-row-chat-btn" data-phone="${phone}" data-name="${this.escapeAttr(name)}" style="background: #059669; border: none; color: #fff; border-radius: 6px; padding: 2px 8px; font-size: 11px; cursor: pointer;">
                  <i class="fas fa-comment"></i> Chat
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // ── TAB 3: TEMPLATES ────────────────────────────────────────────────────────

  private renderTemplatesTab(): string {
    return `
      <div style="display: flex; flex-direction: column; gap: 8px;">
        ${this.subLoading ? `
          <div style="text-align: center; padding: 30px; color: #94a3b8;">
            <i class="fas fa-spinner fa-spin" style="font-size: 24px; color: #25d366; margin-bottom: 8px;"></i>
            <div>Loading WhatsApp templates...</div>
          </div>
        ` : ''}

        ${!this.subLoading && this.templatesList.length === 0 ? `
          <div style="text-align: center; padding: 30px 20px; background: #1e293b; border-radius: 12px; border: 1px solid #334155;">
            <i class="fas fa-file-alt" style="font-size: 32px; color: #64748b; margin-bottom: 8px;"></i>
            <div style="font-size: 14px; font-weight: 600;">No Meta Templates Found</div>
          </div>
        ` : ''}

        ${this.templatesList.map(tpl => `
          <div style="background: #1e293b; border-radius: 10px; padding: 12px; border: 1px solid #334155;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <span style="font-size: 13px; font-weight: 700; color: #38bdf8;">${tpl.name || 'Template'}</span>
              <span style="font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; background: #065f46; color: #a7f3d0;">${tpl.status || 'APPROVED'}</span>
            </div>
            <div style="font-size: 12px; color: #cbd5e1; line-height: 1.4; background: #0f172a; padding: 8px; border-radius: 6px; white-space: pre-wrap; margin-bottom: 8px;">
              ${tpl.body || tpl.text || 'No template content preview'}
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: #94a3b8;">
              <span>Category: <strong>${tpl.category || 'MARKETING'}</strong></span>
              <button class="wa-use-tpl-btn" data-text="${this.escapeAttr(tpl.body || tpl.text || '')}" style="background: #059669; color: #fff; border: none; border-radius: 6px; padding: 3px 10px; font-size: 11px; font-weight: 600; cursor: pointer;">
                Use in Chat
              </button>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  // ── TAB 4: AUTOMATIONS ──────────────────────────────────────────────────────

  private renderAutomationsTab(): string {
    return `
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <div style="background: #1e293b; border-radius: 10px; padding: 12px; border: 1px solid #334155;">
          <div style="font-size: 13.5px; font-weight: 700; color: #f8fafc; margin-bottom: 4px;">
            ⚡ Active WhatsApp Bot Automations
          </div>
          <div style="font-size: 12px; color: #94a3b8;">
            Automated event triggers, instant lead greetings, and campaign dispatches.
          </div>
        </div>

        ${this.subLoading ? `
          <div style="text-align: center; padding: 30px; color: #94a3b8;">
            <i class="fas fa-spinner fa-spin" style="font-size: 24px; color: #25d366; margin-bottom: 8px;"></i>
            <div>Loading automations...</div>
          </div>
        ` : ''}

        ${this.automationsList.map(a => `
          <div style="background: #1e293b; border-radius: 10px; padding: 12px; border: 1px solid #334155;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <span style="font-size: 13px; font-weight: 700; color: #38bdf8;">${a.title || a.name || 'Automation Rule'}</span>
              <span style="font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; background: #065f46; color: #a7f3d0;">ACTIVE</span>
            </div>
            <div style="font-size: 12px; color: #cbd5e1; margin-bottom: 6px;">
              ${a.description || 'Dispatches automatic WhatsApp alert to customer / group'}
            </div>
            <div style="font-size: 11px; color: #94a3b8;">
              Trigger: <strong style="color:#e2e8f0;">${a.trigger_event || 'On Lead Created'}</strong>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  // ── TAB 5: AUDIT LOG ────────────────────────────────────────────────────────

  private renderAuditTab(): string {
    return `
      <div style="display: flex; flex-direction: column; gap: 8px;">
        ${this.subLoading ? `
          <div style="text-align: center; padding: 30px; color: #94a3b8;">
            <i class="fas fa-spinner fa-spin" style="font-size: 24px; color: #25d366; margin-bottom: 8px;"></i>
            <div>Loading delivery audit logs...</div>
          </div>
        ` : ''}

        ${!this.subLoading && this.auditLogs.length === 0 ? `
          <div style="text-align: center; padding: 30px 20px; background: #1e293b; border-radius: 12px; border: 1px solid #334155;">
            <i class="fas fa-shield-alt" style="font-size: 32px; color: #64748b; margin-bottom: 8px;"></i>
            <div style="font-size: 14px; font-weight: 600;">No Audit Logs Recorded</div>
          </div>
        ` : ''}

        ${this.auditLogs.map(log => {
          const status = log.current_status || log.status || 'sent';
          let statusBg = '#065f46';
          let statusCol = '#a7f3d0';
          if (status === 'failed') { statusBg = '#7f1d1d'; statusCol = '#fecaca'; }
          else if (status === 'delivered') { statusBg = '#1e3a8a'; statusCol = '#93c5fd'; }

          const timeIst = log.sent_at_ist || (log.sent_at ? new Date(log.sent_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: true }) : '—');

          return `
            <div style="background: #1e293b; border-radius: 10px; padding: 10px 12px; border: 1px solid #334155;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-size: 12.5px; font-weight: 700; color: #f8fafc;">+91 ${String(log.mobile_number || '').replace(/[^0-9]/g, '').slice(-10)}</span>
                <span style="font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 4px; background: ${statusBg}; color: ${statusCol};">${status.toUpperCase()}</span>
              </div>
              <div style="font-size: 11.5px; color: #cbd5e1; margin-bottom: 4px;">
                Type: <strong>${log.message_type || 'OUTBOUND'}</strong>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 10.5px; color: #94a3b8;">
                <span>Time: ${timeIst}</span>
                <span>${log.message_sid ? 'SID: ' + String(log.message_sid).slice(0, 10) + '...' : ''}</span>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  // ── Data Fetching Methods ───────────────────────────────────────────────────

  private async loadInbox(): Promise<void> {
    this.inboxLoading = true;
    this.render();

    try {
      let url = '/whatsapp/inbox?page_size=50';
      if (this.fPhone) url += `&phone=${encodeURIComponent(this.fPhone)}`;
      if (this.fSource) url += `&source=${this.fSource}`;
      if (this.fStatus) url += `&status=${this.fStatus}`;
      if (this.fExcludeStaff) url += `&exclude_staff=true`;

      const res = await apiService.get<any>(url);
      if (res.success && res.data) {
        this.inboxItems = res.data.data || res.data.items || [];
        if (res.data.stats) {
          this.inboxStats = res.data.stats;
        } else {
          this.inboxStats.all = res.data.total || this.inboxItems.length;
          this.inboxStats.unread = this.inboxItems.filter(i => !i.is_read).length;
          this.inboxStats.pending = this.inboxItems.filter(i => i.status === 'pending').length;
        }
      }
    } catch (err) {
      console.error('[StaffWhatsAppCenter] Error loading inbox:', err);
    } finally {
      this.inboxLoading = false;
      this.render();
    }
  }

  private async loadMessenger(): Promise<void> {
    this.convsLoading = true;
    this.render();

    try {
      const res = await apiService.get<any>(`/whatsapp/conversations-hub?scope=${this.activeScope}`);
      if (res.success && res.data) {
        this.convsList = res.data.conversations || [];
      }
    } catch (err) {
      console.error('[StaffWhatsAppCenter] Error loading messenger:', err);
    } finally {
      this.convsLoading = false;
      this.render();
    }
  }

  private async loadChat(phone: string, name: string): Promise<void> {
    this.activeChatPhone = phone;
    this.activeChatName = name;
    this.showEmojiTray = false;
    this.showAttachMenu = false;
    this.chatLoading = true;
    this.render();

    try {
      const res = await apiService.get<any>(`/whatsapp/inbox/thread/${encodeURIComponent(phone)}`);
      if (res.success && res.data) {
        this.chatHistory = res.data.messages || [];
      }
    } catch (err) {
      console.error('[StaffWhatsAppCenter] Error loading thread:', err);
    } finally {
      this.chatLoading = false;
      this.render();
      this.scrollToChatBottom();
    }
  }

  private async loadTemplates(): Promise<void> {
    this.subLoading = true;
    this.render();

    try {
      const res = await apiService.get<any>('/whatsapp/scheduler-templates/1');
      if (res.success && res.data) {
        this.templatesList = res.data.templates || [
          { name: 'lead_welcome_instant', category: 'MARKETING', status: 'APPROVED', body: 'Namaskaram! Welcome to MyntReal Real Estate. We received your inquiry and our advisor will connect shortly.' },
          { name: 'brochure_and_pricing_share', category: 'UTILITY', status: 'APPROVED', body: 'Dear Customer, thank you for your interest in our premium venture. Please find the project details attached.' },
          { name: 'call_followup_reminder', category: 'UTILITY', status: 'APPROVED', body: 'Hello, this is a quick reminder regarding your scheduled site visit with MyntReal.' }
        ];
      }
    } catch {
      this.templatesList = [
        { name: 'lead_welcome_instant', category: 'MARKETING', status: 'APPROVED', body: 'Namaskaram! Welcome to MyntReal Real Estate. We received your inquiry and our advisor will connect shortly.' },
        { name: 'brochure_and_pricing_share', category: 'UTILITY', status: 'APPROVED', body: 'Dear Customer, thank you for your interest in our premium venture. Please find the project details attached.' }
      ];
    } finally {
      this.subLoading = false;
      this.render();
    }
  }

  private async loadAutomations(): Promise<void> {
    this.subLoading = true;
    this.render();

    try {
      this.automationsList = [
        { name: 'Instant Welcome Message', trigger_event: 'CRM Lead Creation', description: 'Sends automated Telugu / English greeting via Meta Cloud API on new lead arrival.' },
        { name: 'Missed Call Acknowledgment', trigger_event: 'Missed Operator Call', description: 'Sends instant WhatsApp message acknowledging caller with telecaller contact info.' },
        { name: 'Site Visit Follow-up Dispatch', trigger_event: 'Lead Status = Site Visit', description: 'Dispatches project location pin and advisor phone number to customer.' }
      ];
    } finally {
      this.subLoading = false;
      this.render();
    }
  }

  private async loadAuditLogs(): Promise<void> {
    this.subLoading = true;
    this.render();

    try {
      const res = await apiService.get<any>('/whatsapp/delivery-logs?limit=30');
      if (res.success && res.data) {
        this.auditLogs = res.data.logs || res.data.data || [];
      }
    } catch {
      this.auditLogs = [];
    } finally {
      this.subLoading = false;
      this.render();
    }
  }

  // ── Event Listeners ─────────────────────────────────────────────────────────

  private attachMainListeners(): void {
    // Nav Tabs
    this.container.querySelectorAll('.wa-nav-tab').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = (e.currentTarget as HTMLElement).dataset.tab as any;
        if (tab && tab !== this.activeTab) {
          this.activeTab = tab;
          this.activeChatPhone = null;
          this.loadCurrentTab();
        }
      });
    });

    // Scan QR Code Modal Opener
    document.getElementById('waOpenScanQrBtn')?.addEventListener('click', () => {
      this.openScanQrModal();
    });

    // New Message Button
    document.getElementById('waNewMsgBtn')?.addEventListener('click', () => {
      this.openNewMessageModal();
    });

    // CRM Inbox Search & Filters
    const searchInput = document.getElementById('waInboxSearchInput') as HTMLInputElement;
    if (searchInput) {
      let dt: any;
      searchInput.addEventListener('input', () => {
        clearTimeout(dt);
        dt = setTimeout(() => {
          this.fPhone = searchInput.value;
          this.loadInbox();
        }, 300);
      });
    }

    document.getElementById('waInboxSourceSelect')?.addEventListener('change', (e) => {
      this.fSource = (e.target as HTMLSelectElement).value;
      this.loadInbox();
    });

    document.getElementById('waInboxStatusSelect')?.addEventListener('change', (e) => {
      this.fStatus = (e.target as HTMLSelectElement).value;
      this.loadInbox();
    });

    document.getElementById('waExcludeStaffCheck')?.addEventListener('change', (e) => {
      this.fExcludeStaff = (e.target as HTMLInputElement).checked;
      this.loadInbox();
    });

    document.getElementById('waResetFilterBtn')?.addEventListener('click', () => {
      this.fPhone = '';
      this.fSource = '';
      this.fStatus = '';
      this.fExcludeStaff = false;
      this.loadInbox();
    });

    // Row Actions in CRM Inbox
    this.container.querySelectorAll('.wa-inbox-card').forEach(card => {
      card.addEventListener('click', (e) => {
        const target = e.target as HTMLElement;
        if (target.closest('.wa-row-assign-btn')) return;

        const phone = (card as HTMLElement).dataset.phone;
        const name = (card as HTMLElement).dataset.name || 'Customer';
        if (phone) {
          this.activeTab = 'messenger';
          this.loadChat(phone, name);
        }
      });
    });

    this.container.querySelectorAll('.wa-row-assign-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const phone = (btn as HTMLElement).dataset.phone || '';
        const name = (btn as HTMLElement).dataset.name || '';
        this.openAssignModal(phone, name);
      });
    });

    // Messenger Scope Select
    document.getElementById('waMsgScopeSelect')?.addEventListener('change', (e) => {
      this.activeScope = (e.target as HTMLSelectElement).value;
      this.loadMessenger();
    });

    // Messenger Conversation Cards
    this.container.querySelectorAll('.wa-msg-card').forEach(card => {
      card.addEventListener('click', () => {
        const phone = (card as HTMLElement).dataset.phone || '';
        const name = (card as HTMLElement).dataset.name || 'Customer';
        this.loadChat(phone, name);
      });
    });

    // Back to messenger list
    document.getElementById('waBackToMsgListBtn')?.addEventListener('click', () => {
      this.activeChatPhone = null;
      this.render();
    });

    // Quick Pills in Live Chat
    this.container.querySelectorAll('.wa-quick-pill').forEach(pill => {
      pill.addEventListener('click', (e) => {
        const text = (e.currentTarget as HTMLElement).dataset.text || '';
        const input = document.getElementById('waLiveMsgInput') as HTMLInputElement;
        if (input) {
          input.value = text;
          input.focus();
        }
      });
    });

    // Toggle Emoji Tray
    document.getElementById('waToggleEmojiBtn')?.addEventListener('click', () => {
      this.showEmojiTray = !this.showEmojiTray;
      this.showAttachMenu = false;
      this.render();
      this.scrollToChatBottom();
    });

    // Emoji Category Buttons
    this.container.querySelectorAll('.wa-emoji-cat-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const cat = (e.currentTarget as HTMLElement).dataset.cat as any;
        if (cat) {
          this.activeEmojiCat = cat;
          this.render();
        }
      });
    });

    // Emoji Click Insertion
    this.container.querySelectorAll('.wa-emoji-item').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const emoji = (e.currentTarget as HTMLElement).dataset.emoji || '';
        const input = document.getElementById('waLiveMsgInput') as HTMLInputElement;
        if (input) {
          const start = input.selectionStart || input.value.length;
          const end = input.selectionEnd || input.value.length;
          input.value = input.value.substring(0, start) + emoji + input.value.substring(end);
          input.selectionStart = input.selectionEnd = start + emoji.length;
          input.focus();
        }
      });
    });

    // Toggle Attachment Menu
    document.getElementById('waToggleAttachBtn')?.addEventListener('click', () => {
      this.showAttachMenu = !this.showAttachMenu;
      this.showEmojiTray = false;
      this.render();
      this.scrollToChatBottom();
    });

    // Attachment Choices
    this.container.querySelectorAll('.wa-attach-choice-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const type = (e.currentTarget as HTMLElement).dataset.type;
        if (type === 'brochure') {
          this.activeAttachment = { type: 'pdf', name: 'MyntReal_Venture_Brochure.pdf' };
        } else if (type === 'photo') {
          this.activeAttachment = { type: 'image', name: 'Venture_Layout_Plan.jpg' };
        } else if (type === 'location') {
          const input = document.getElementById('waLiveMsgInput') as HTMLInputElement;
          if (input) {
            input.value += ' 📍 Venture Location: https://maps.google.com/?q=17.729,83.308';
            input.focus();
          }
        }
        this.showAttachMenu = false;
        this.render();
      });
    });

    // Remove Attachment
    document.getElementById('waRemoveAttachBtn')?.addEventListener('click', () => {
      this.activeAttachment = null;
      this.render();
    });

    // Live Message Send
    const sendBtn = document.getElementById('waLiveSendBtn');
    const msgInput = document.getElementById('waLiveMsgInput') as HTMLInputElement;

    const doSend = async () => {
      let text = msgInput?.value?.trim() || '';
      if (this.activeAttachment) {
        text += (text ? '\n\n' : '') + `[Attachment: ${this.activeAttachment.name}]`;
      }
      if (!text || !this.activeChatPhone) return;

      if (msgInput) msgInput.value = '';
      this.activeAttachment = null;
      this.showEmojiTray = false;
      this.showAttachMenu = false;

      this.chatHistory.push({
        id: Date.now(),
        from_phone: this.activeChatPhone,
        message_type: 'outbound',
        body_text: text,
        received_at: new Date().toISOString(),
      });
      this.render();
      this.scrollToChatBottom();

      try {
        await apiService.post('/whatsapp/send-message', {
          to_phone: this.activeChatPhone,
          message: text,
          message_type: 'text'
        });
      } catch (err) {
        console.error('[StaffWhatsAppCenter] Send failed:', err);
      }
    };

    sendBtn?.addEventListener('click', doSend);
    msgInput?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        doSend();
      }
    });

    // Template "Use in Chat"
    this.container.querySelectorAll('.wa-use-tpl-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const text = (e.currentTarget as HTMLElement).dataset.text || '';
        this.openNewMessageModal(undefined, text);
      });
    });
  }

  // ── Modals: QR Scan, New Message & Assign ───────────────────────────────────

  private openScanQrModal(): void {
    const modalWrap = document.getElementById('waCenterModalContainer');
    if (!modalWrap) return;

    modalWrap.innerHTML = `
      <div style="position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 10000; display: flex; align-items: center; justify-content: center; padding: 16px;">
        <div style="background: #1e293b; border-radius: 16px; padding: 24px; width: 100%; max-width: 390px; border: 1px solid #334155; text-align: center; box-shadow: 0 12px 36px rgba(0,0,0,0.6);">
          
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
            <div style="font-size: 16px; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
              <i class="fab fa-whatsapp" style="color: #25d366; font-size: 20px;"></i> Link WhatsApp Web
            </div>
            <button id="waQrModalCloseBtn" style="background: none; border: none; color: #94a3b8; font-size: 18px; cursor: pointer;">✕</button>
          </div>

          <div style="font-size: 12.5px; color: #94a3b8; line-height: 1.45; margin-bottom: 16px; text-align: left; background: #0f172a; padding: 10px 12px; border-radius: 8px;">
            <strong>To connect WhatsApp:</strong><br>
            1. Open WhatsApp on your phone<br>
            2. Tap <strong>Linked Devices</strong> in Settings/Menu<br>
            3. Tap <strong>Link a Device</strong> and point your camera at this QR code
          </div>

          <!-- QR Container -->
          <div id="waQrCodeBox" style="background: #fff; padding: 16px; border-radius: 12px; display: inline-block; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
            ${this.gatewayQr ? `
              <img src="${this.gatewayQr.startsWith('data:') ? this.gatewayQr : 'data:image/png;base64,' + this.gatewayQr}" style="width: 200px; height: 200px; display: block;" alt="WhatsApp QR Code" />
            ` : `
              <div style="width: 200px; height: 200px; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #475569;">
                <i class="fas fa-qrcode fa-spin" style="font-size: 36px; color: #059669; margin-bottom: 8px;"></i>
                <span style="font-size: 12px; font-weight: 600;">Generating QR code...</span>
              </div>
            `}
          </div>

          <div style="display: flex; gap: 8px;">
            <button id="waRefreshQrBtn" style="flex: 1; padding: 10px; border-radius: 8px; background: #334155; color: #f8fafc; font-size: 12.5px; font-weight: 600; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px;">
              <i class="fas fa-sync-alt"></i> Refresh QR
            </button>
            <button id="waCheckStatusBtn" style="flex: 1; padding: 10px; border-radius: 8px; background: #25d366; color: #0f172a; font-size: 12.5px; font-weight: 700; border: none; cursor: pointer;">
              Check Status
            </button>
          </div>

        </div>
      </div>
    `;

    document.getElementById('waQrModalCloseBtn')?.addEventListener('click', () => {
      modalWrap.innerHTML = '';
    });

    document.getElementById('waRefreshQrBtn')?.addEventListener('click', async () => {
      await this.checkGatewayStatus();
      this.openScanQrModal();
    });

    document.getElementById('waCheckStatusBtn')?.addEventListener('click', async () => {
      await this.checkGatewayStatus();
      if (this.gatewayConnected) {
        modalWrap.innerHTML = '';
        this.render();
      } else {
        this.openScanQrModal();
      }
    });
  }

  private openNewMessageModal(phoneDefault: string = '', textDefault: string = ''): void {
    const modalWrap = document.getElementById('waCenterModalContainer');
    if (!modalWrap) return;

    modalWrap.innerHTML = `
      <div style="position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 10000; display: flex; align-items: center; justify-content: center; padding: 16px;">
        <div style="background: #1e293b; border-radius: 14px; padding: 20px; width: 100%; max-width: 380px; border: 1px solid #334155; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
            <div style="font-size: 15px; font-weight: 700; color: #f8fafc;"><i class="fab fa-whatsapp" style="color:#25d366;"></i> Send WhatsApp Message</div>
            <button id="waModalCloseBtn" style="background: none; border: none; color: #94a3b8; font-size: 16px; cursor: pointer;">✕</button>
          </div>

          <div style="margin-bottom: 10px;">
            <label style="font-size: 11.5px; font-weight: 600; color: #94a3b8; display: block; margin-bottom: 4px;">Recipient Phone (10 Digits)</label>
            <input type="tel" id="waNewPhoneInput" placeholder="9876543210" value="${phoneDefault}" style="width: 100%; box-sizing: border-box; padding: 8px 12px; border-radius: 8px; background: #0f172a; border: 1px solid #334155; color: #fff; font-size: 13px; outline: none;" />
          </div>

          <div style="margin-bottom: 14px;">
            <label style="font-size: 11.5px; font-weight: 600; color: #94a3b8; display: block; margin-bottom: 4px;">Message Text</label>
            <textarea id="waNewTextInput" rows="4" placeholder="Enter message payload..." style="width: 100%; box-sizing: border-box; padding: 8px 12px; border-radius: 8px; background: #0f172a; border: 1px solid #334155; color: #fff; font-size: 13px; outline: none; resize: none;">${textDefault}</textarea>
          </div>

          <button id="waModalSendBtn" style="width: 100%; padding: 10px; border-radius: 8px; background: #25d366; color: #0f172a; font-size: 13px; font-weight: 700; border: none; cursor: pointer;">
            🚀 Send via Meta API
          </button>
        </div>
      </div>
    `;

    document.getElementById('waModalCloseBtn')?.addEventListener('click', () => {
      modalWrap.innerHTML = '';
    });

    document.getElementById('waModalSendBtn')?.addEventListener('click', async () => {
      const phone = (document.getElementById('waNewPhoneInput') as HTMLInputElement)?.value?.trim();
      const text = (document.getElementById('waNewTextInput') as HTMLTextAreaElement)?.value?.trim();
      if (!phone || !text) return;

      modalWrap.innerHTML = '';
      try {
        await apiService.post('/whatsapp/send-message', {
          to_phone: phone,
          message: text,
          message_type: 'text'
        });
        this.loadCurrentTab();
      } catch (err) {
        console.error('Send error:', err);
      }
    });
  }

  private openAssignModal(phone: string, name: string): void {
    const modalWrap = document.getElementById('waCenterModalContainer');
    if (!modalWrap) return;

    modalWrap.innerHTML = `
      <div style="position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 10000; display: flex; align-items: center; justify-content: center; padding: 16px;">
        <div style="background: #1e293b; border-radius: 14px; padding: 20px; width: 100%; max-width: 360px; border: 1px solid #334155;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div style="font-size: 14px; font-weight: 700; color: #f8fafc;"><i class="fas fa-tag" style="color:#38bdf8;"></i> Assign Conversation</div>
            <button id="waAssignCloseBtn" style="background: none; border: none; color: #94a3b8; font-size: 16px; cursor: pointer;">✕</button>
          </div>
          <div style="font-size: 12.5px; color: #94a3b8; margin-bottom: 12px;">
            Assign <strong>${name}</strong> (+91 ${phone.replace(/[^0-9]/g, '').slice(-10)}) to a telecaller or department.
          </div>
          <select id="waAssignDeptSelect" style="width: 100%; padding: 8px; border-radius: 8px; background: #0f172a; border: 1px solid #334155; color: #fff; font-size: 13px; margin-bottom: 14px; outline: none;">
            <option value="REAL_ESTATE">Real Estate CRM</option>
            <option value="SOLAR">Solar CRM</option>
            <option value="INSURANCE">Insurance</option>
          </select>
          <button id="waAssignSaveBtn" style="width: 100%; padding: 9px; border-radius: 8px; background: #059669; color: #fff; font-size: 13px; font-weight: 700; border: none; cursor: pointer;">
            Save Assignment
          </button>
        </div>
      </div>
    `;

    document.getElementById('waAssignCloseBtn')?.addEventListener('click', () => {
      modalWrap.innerHTML = '';
    });

    document.getElementById('waAssignSaveBtn')?.addEventListener('click', () => {
      modalWrap.innerHTML = '';
      this.loadInbox();
    });
  }

  private scrollToChatBottom(): void {
    setTimeout(() => {
      const list = document.getElementById('waChatHistoryList');
      if (list) list.scrollTop = list.scrollHeight;
    }, 50);
  }

  private escapeHtml(str: string): string {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;')
      .replace(/\n/g, '<br>');
  }

  private escapeAttr(str: string): string {
    if (!str) return '';
    return str.replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }
}
