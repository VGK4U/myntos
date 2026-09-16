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
import { callController } from '../services/call-controller';
import { APP_CONFIG } from '../config/app.config';

export class StaffWhatsAppInboxPage {
  private container: HTMLElement;
  private activeTab: 'messenger' | 'team' | 'company' | 'all' | 'broadcasts' | 'inbox' | 'templates' | 'automations' | 'audit' = 'messenger';

  // ── Gateway & QR State ─────────────────────────────────────────────────────
  private gatewayConnected: boolean = true;
  private gatewayQr: string = '';
  private gatewayStatus: string = 'checking';
  private lastStatusTimestamp: number = 0;
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
  private activeScope: string = 'assigned_tagged';
  private chatOriginTab: 'messenger' | 'team' | 'company' | 'all' | 'broadcasts' | 'inbox' = 'messenger';
  private fMsgSearch: string = '';
  private chatHistory: any[] = [];
  private chatLoading: boolean = false;

  // ── Composer & Emoji State ─────────────────────────────────────────────────
  private showEmojiTray: boolean = false;
  private activeEmojiCat: 'smileys' | 'hands' | 'realestate' | 'reactions' | 'travel' = 'smileys';
  private showAttachMenu: boolean = false;
  private activeAttachment: { type: string; name: string; url?: string } | null = null;
  private activeReplyContext: { wamid: string; text: string; sender: string } | null = null;

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

  private isKeyLeadershipOrAdmin(): boolean {
    const authState = authService.getAuthState();
    const user = authState.user || {};
    const empCode = (user.emp_code || '').toUpperCase().trim();
    const roleCode = (user.role_code || user.role?.role_code || '').toLowerCase().trim();
    const roleName = (user.role_name || user.role?.role_name || user.designation || '').toUpperCase().trim();
    const name = (user.name || user.full_name || '').toLowerCase().trim();
    return empCode === 'MR10001' || empCode === 'MR10016' || empCode === 'MR10018' || 
           roleCode === 'vgk4u' || roleCode === 'ea' || roleCode === 'key_leadership' || 
           roleName.includes('KEY LEADERSHIP') || roleName.includes('CHIEF') || roleName.includes('DIRECTOR') || 
           name.includes('yaswanth') || name.includes('jagannadh');
  }

  private isAllMessagesAuthorized(): boolean {
    try {
      const authState = authService.getAuthState();
      const user = authState.user || {};
      const roleCode = (user.role_code || user.role?.role_code || '').toLowerCase().trim();
      const roleName = (user.role_name || user.role?.role_name || user.designation || '').toUpperCase().trim();
      const adminScope = (user.admin_scope || '').toUpperCase().trim();
      const staffType = (user.staff_type || '').toUpperCase().trim();
      const level = parseInt(user.hierarchy_level || user.role?.hierarchy_level || '0', 10);

      // Canonical check: Admin scope, Leadership role, or Hierarchy Level >= 80
      if (['PLATFORM', 'TENANT_ADMIN', 'COMPANY_ADMIN', 'SEGMENT_A', 'SEGMENT_B'].includes(adminScope)) return true;
      if (['vgk4u', 'vgk4u_supreme', 'admin', 'super_admin', 'ea', 'key_leadership', 'saas_segment_admin'].includes(roleCode)) return true;
      if (['VGK4U', 'VGK4U SUPREME', 'KEY LEADERSHIP', 'EA', 'SUPER_ADMIN', 'ADMIN'].includes(roleName)) return true;
      if (['VGK4U_SUPREME', 'KEY_LEADERSHIP', 'SUPER_ADMIN', 'SAAS_SEGMENT_ADMIN'].includes(staffType)) return true;
      if (level >= 80) return true;

      return this.isWhatsAppAdmin();
    } catch {
      return false;
    }
  }

  private async checkGatewayStatus(): Promise<void> {
    try {
      const res = await apiService.get<any>('/whatsapp/bot-status');
      if (res.success && res.data) {
        const respTs = res.data.timestamp || 0;
        if (respTs && this.lastStatusTimestamp && respTs < this.lastStatusTimestamp) {
          // Stale API response guard: drop out-of-order response
          return;
        }
        if (respTs) this.lastStatusTimestamp = respTs;
        this.gatewayStatus = res.data.connection_state || res.data.status || 'disconnected';
        this.gatewayConnected = (this.gatewayStatus === 'connected');
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
      this.activeScope = 'assigned_tagged';
      await this.loadMessenger();
    } else if (this.activeTab === 'team') {
      this.activeScope = 'downline';
      await this.loadMessenger();
    } else if (this.activeTab === 'company') {
      this.activeScope = 'company';
      await this.loadMessenger();
    } else if (this.activeTab === 'all') {
      this.activeScope = 'all';
      await this.loadMessenger();
    } else if (this.activeTab === 'broadcasts') {
      this.activeScope = 'broadcasts';
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
    const isKeyLeadership = this.isKeyLeadershipOrAdmin();
    const isAllAuthorized = this.isAllMessagesAuthorized();

    let statusPillText = '● Disconnected';
    let statusPillBg = 'rgba(239,68,68,0.2)';
    let statusPillBorder = '#ef4444';
    let statusPillCol = '#fecaca';

    if (this.gatewayStatus === 'connected') {
      statusPillText = '● Connected';
      statusPillBg = 'rgba(37,211,102,0.2)';
      statusPillBorder = '#25d366';
      statusPillCol = '#a7f3d0';
    } else if (this.gatewayStatus === 'reconnecting') {
      statusPillText = '● Reconnecting...';
      statusPillBg = 'rgba(245,158,11,0.2)';
      statusPillBorder = '#f59e0b';
      statusPillCol = '#fde68a';
    } else if (this.gatewayStatus === 'qr_ready') {
      statusPillText = '● Scan QR Required';
      statusPillBg = 'rgba(245,158,11,0.2)';
      statusPillBorder = '#f59e0b';
      statusPillCol = '#fde68a';
    }

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
              <span style="background: ${statusPillBg}; border: 1px solid ${statusPillBorder}; color: ${statusPillCol}; border-radius: 20px; padding: 3px 8px; font-size: 11px; font-weight: 700;">
                ${statusPillText}
              </span>
              <button id="waBannerRefreshBtn" title="Refresh WhatsApp Center" style="background: rgba(255,255,255,0.15); color: #fff; border: 1px solid rgba(255,255,255,0.3); border-radius: 16px; padding: 5px 10px; font-size: 12px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 4px;">
                <i class="fas fa-sync-alt" id="waBannerRefreshIcon"></i>
              </button>
              <button id="waNewMsgBtn" style="background: #25d366; color: #0f172a; border: none; border-radius: 16px; padding: 5px 12px; font-size: 12px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 4px;">
                <i class="fas fa-plus"></i> New Message
              </button>
            </div>
          </div>
        </div>

        <!-- Scan QR Required Warning Banner (ONLY when QR scan is genuinely required, NEVER on reconnecting) -->
        ${(this.gatewayStatus === 'qr_ready' || (this.gatewayStatus === 'disconnected' && this.gatewayQr)) ? `
          <div style="background: linear-gradient(135deg, #78350f, #92400e); border: 1px solid #f59e0b; border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
            <div style="display: flex; align-items: center; gap: 10px;">
              <i class="fas fa-qrcode" style="font-size: 22px; color: #fbbf24;"></i>
              <div>
                <div style="font-size: 13px; font-weight: 700; color: #fef3c7;">Link WhatsApp Account</div>
                <div style="font-size: 11px; color: #fde68a;">Scan QR code with your phone to link your WhatsApp session</div>
              </div>
            </div>
            <button id="waOpenScanQrBtn" style="background: #25d366; color: #0f172a; border: none; border-radius: 8px; padding: 6px 12px; font-size: 12px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 4px; white-space: nowrap;">
              <i class="fas fa-camera"></i> Scan QR
            </button>
          </div>
        ` : ''}

        <!-- Navigation Tabs: Complete Parity with Web (Tabs 1 to 9) -->
        <div style="display: flex; gap: 6px; overflow-x: auto; padding-bottom: 6px; margin-bottom: 12px; -webkit-overflow-scrolling: touch;">
          <button class="wa-nav-tab ${this.activeTab === 'messenger' ? 'active' : ''}" data-tab="messenger" style="${this.getTabBtnStyle(this.activeTab === 'messenger')}">
            <i class="fas fa-comments"></i> 1. My Messages
          </button>
          <button class="wa-nav-tab ${this.activeTab === 'team' ? 'active' : ''}" data-tab="team" style="${this.getTabBtnStyle(this.activeTab === 'team')}">
            <i class="fas fa-users"></i> 2. Team Messages
          </button>
          <button class="wa-nav-tab ${this.activeTab === 'company' ? 'active' : ''}" data-tab="company" style="${this.getTabBtnStyle(this.activeTab === 'company')}">
            <i class="fas fa-envelope-open-text"></i> 3. New Messages
          </button>
          ${isAllAuthorized ? `
            <button class="wa-nav-tab ${this.activeTab === 'all' ? 'active' : ''}" data-tab="all" style="${this.getTabBtnStyle(this.activeTab === 'all')}">
              <i class="fas fa-globe"></i> 4. All Messages
            </button>
          ` : ''}
          <button class="wa-nav-tab ${this.activeTab === 'broadcasts' ? 'active' : ''}" data-tab="broadcasts" style="${this.getTabBtnStyle(this.activeTab === 'broadcasts')}">
            <i class="fas fa-bullhorn"></i> 5. Broadcasts & Dispatches
          </button>
          ${isKeyLeadership ? `
            <button class="wa-nav-tab ${this.activeTab === 'inbox' ? 'active' : ''}" data-tab="inbox" style="${this.getTabBtnStyle(this.activeTab === 'inbox')}">
              <i class="fas fa-robot"></i> 6. WhatsApp API Bot
              ${this.inboxStats.unread > 0 ? `<span style="background:#ef4444;color:#fff;border-radius:10px;padding:1px 6px;font-size:10px;margin-left:4px;">${this.inboxStats.unread}</span>` : ''}
            </button>
          ` : ''}
          ${isAdmin ? `
            <button class="wa-nav-tab ${this.activeTab === 'templates' ? 'active' : ''}" data-tab="templates" style="${this.getTabBtnStyle(this.activeTab === 'templates')}">
              <i class="fas fa-file-alt"></i> 7. Templates
            </button>
            <button class="wa-nav-tab ${this.activeTab === 'automations' ? 'active' : ''}" data-tab="automations" style="${this.getTabBtnStyle(this.activeTab === 'automations')}">
              <i class="fas fa-cogs"></i> 8. Automations
            </button>
            <button class="wa-nav-tab ${this.activeTab === 'audit' ? 'active' : ''}" data-tab="audit" style="${this.getTabBtnStyle(this.activeTab === 'audit')}">
              <i class="fas fa-shield-alt"></i> 9. Audit Log
            </button>
          ` : ''}
        </div>

        <!-- Tab Content Panes -->
        ${(this.activeTab === 'messenger' || this.activeTab === 'team' || this.activeTab === 'company' || this.activeTab === 'all' || this.activeTab === 'broadcasts') ? this.renderMessengerTab() : ''}
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

  // ── TAB 1 & TAB 2: MESSENGER / TEAM VIEW ────────────────────────────────────

  private renderMessengerTab(): string {
    const isTeam = this.activeTab === 'team';
    const isCompany = this.activeTab === 'company';
    const isAll = this.activeTab === 'all';
    const isBroadcasts = this.activeTab === 'broadcasts';

    let headerIcon = 'fas fa-comments';
    let headerTitle = 'My Sent Messages & Assigned Leads';
    let searchPlaceholder = 'Search my messages / phone...';
    let emptyTitle = 'No personal conversations found.';
    let emptySubtitle = 'Tap "+ New Message" above to start a conversation.';

    if (isTeam) {
      headerIcon = 'fas fa-users';
      headerTitle = 'Downline Team Conversations';
      searchPlaceholder = 'Search team messages / phone...';
      emptyTitle = 'No downline team conversations found.';
      emptySubtitle = 'Team members assigned to you will appear here.';
    } else if (isCompany) {
      headerIcon = 'fas fa-envelope-open-text';
      headerTitle = 'New Messages & Unassigned Inquiries';
      searchPlaceholder = 'Search new messages / phone...';
      emptyTitle = 'No unassigned company messages found.';
      emptySubtitle = 'All incoming customer inquiries are assigned.';
    } else if (isAll) {
      headerIcon = 'fas fa-globe';
      headerTitle = 'All Organization Messages (Master View)';
      searchPlaceholder = 'Search all messages / phone / contact / body...';
      emptyTitle = 'No messages found in organization archive.';
      emptySubtitle = 'All organization outbound dispatches and conversations appear here.';
    } else if (isBroadcasts) {
      headerIcon = 'fas fa-bullhorn';
      headerTitle = 'Broadcasts & Dispatches';
      searchPlaceholder = 'Search broadcast dispatches / phone...';
      emptyTitle = 'No broadcast dispatches found.';
      emptySubtitle = 'Campaign and blast dispatches appear here.';
    }

    return `
      <div style="background: #1e293b; border-radius: 12px; border: 1px solid #334155; overflow: hidden; display: flex; flex-direction: column; min-height: 520px;">
        
        <!-- Search & Filter Header -->
        <div style="padding: 10px; background: #0f172a; border-bottom: 1px solid #334155; display: flex; flex-direction: column; gap: 8px;">
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <div style="font-size: 12px; font-weight: 700; color: #38bdf8;">
              <i class="${headerIcon}"></i> ${headerTitle}
            </div>
            <div style="font-size: 11px; color: #94a3b8;">
              ${this.convsList.length} conversation${this.convsList.length === 1 ? '' : 's'}
            </div>
          </div>
          <div style="position: relative;">
            <i class="fas fa-search" style="position: absolute; left: 10px; top: 9px; font-size: 12px; color: #64748b;"></i>
            <input 
              type="text" 
              id="waMsgSearchInput" 
              placeholder="${searchPlaceholder}" 
              value="${this.escapeAttr(this.fMsgSearch)}"
              style="width: 100%; box-sizing: border-box; padding: 7px 10px 7px 30px; border-radius: 8px; background: #1e293b; border: 1px solid #334155; color: #fff; font-size: 12px; outline: none;"
            />
          </div>
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
                <i class="${headerIcon}" style="font-size: 36px; margin-bottom: 8px;"></i>
                <div>${emptyTitle}</div>
                <div style="font-size: 11.5px; color: #475569; margin-top: 4px;">${emptySubtitle}</div>
              </div>
            ` : ''}

            ${this.convsList.map(c => this.renderMessengerCard(c)).join('')}
          </div>
        ` : this.renderLiveChatPane()}

      </div>
    `;
  }

  private maskPhone(phone: string): string {
    const s = String(phone || '').trim();
    if (s.includes('@g.us') || s.includes('@broadcast') || s.includes('@lid') || s.startsWith('120363') || s.length > 14) return s;
    const clean = s.replace(/[^0-9]/g, '').slice(-10);
    if (authService.isMR10001()) {
      return clean.length === 10 ? `+91 ${clean.slice(0, 5)} ${clean.slice(5)}` : s;
    }
    if (!clean || clean.length < 10) return '••••••••••';
    return `+91 ${clean.slice(0, 4)}••••${clean.slice(-2)}`;
  }

  private renderMessengerCard(c: any): string {
    const phone = c.from_phone || c.phone || '';
    const isGroup = c.recipient_type === 'group' || c.contact_type === 'GROUP' || (phone && (phone.includes('@g.us') || phone.startsWith('120363') || phone.length > 14));
    const cleanPhone = phone.replace(/[^0-9]/g, '').slice(-10);
    let rawName = c.resolved_name || c.from_name || c.name || '';
    const hasRealName = rawName && rawName !== '0' && rawName !== 'None' && rawName !== 'null' && !/^\d+$/.test(rawName) && !rawName.startsWith('Customer (+91') && !rawName.startsWith('Contact (+91');
    
    const displayName = isGroup ? (c.name || rawName || phone) : (hasRealName ? rawName : `Customer (${this.maskPhone(cleanPhone)})`);
    const initial = isGroup ? '👥' : (this.activeScope === 'all' ? '🌐' : (this.activeScope === 'company' ? '🏢' : (this.activeScope === 'broadcasts' ? '📡' : (displayName.charAt(0) || 'C').toUpperCase())));
    const msg = c.last_message || c.snippet || 'No messages';
    const time = c.last_time || '';

    return `
      <div 
        class="wa-msg-card" 
        data-phone="${phone}" 
        data-name="${this.escapeAttr(displayName)}"
        style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: #0f172a; border-radius: 10px; border: 1px solid #334155; cursor: pointer;"
      >
        <div style="width: 36px; height: 36px; border-radius: 50%; background: #059669; display: flex; align-items: center; justify-content: center; font-size: 15px; font-weight: 700; color: #fff; flex-shrink: 0;">
          ${initial}
        </div>
        <div style="flex: 1; min-width: 0;">
          <div style="display: flex; justify-content: space-between; align-items: baseline;">
            <div style="font-size: 13.5px; font-weight: 700; color: #f8fafc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              ${displayName}
            </div>
            <div style="font-size: 10.5px; color: #64748b; margin-left: 6px; white-space: nowrap;">${time}</div>
          </div>
          <div style="font-size: 12px; color: #94a3b8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px;">
            ${msg}
          </div>
        </div>
        ${!isGroup && cleanPhone ? `
          <button class="wa-card-call-btn" data-phone="${cleanPhone}" data-name="${this.escapeAttr(displayName)}" title="Call via Softphone" style="background: #14532d; border: 1px solid #22c55e; color: #4ade80; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; cursor: pointer; flex-shrink: 0; margin-right: 4px;">
            <i class="fas fa-phone-alt"></i>
          </button>
        ` : ''}
        <i class="fas fa-chevron-right" style="color: #475569; font-size: 11px;"></i>
      </div>
    `;
  }

  private renderLiveChatPane(): string {
    const isGroup = (this.activeChatPhone && (this.activeChatPhone.includes('@g.us') || this.activeChatPhone.startsWith('120363') || this.activeChatPhone.length > 14));
    const cleanPhone = (this.activeChatPhone || '').replace(/[^0-9]/g, '').slice(-10);
    const rawName = this.activeChatName || '';
    const hasRealName = rawName && rawName !== '0' && rawName !== 'None' && rawName !== 'null' && !/^\d+$/.test(rawName) && !rawName.startsWith('Customer (+91') && !rawName.startsWith('Contact (+91');
    const headerTitle = isGroup ? (rawName || this.activeChatPhone) : (hasRealName ? rawName : `Customer (${this.maskPhone(cleanPhone)})`);
    const headerSub = isGroup ? 'WhatsApp Group' : (hasRealName ? 'WhatsApp Contact' : this.maskPhone(cleanPhone));

    return `
      <div style="display: flex; flex-direction: column; height: calc(100vh - 280px); min-height: 480px; background: #0b1120;">
        
        <!-- Live Chat Header -->
        <div style="padding: 10px 12px; background: #1e293b; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <button id="waBackToMsgListBtn" style="background: none; border: none; color: #fff; font-size: 16px; cursor: pointer; padding: 4px;">
              <i class="fas fa-arrow-left"></i>
            </button>
            <div>
              <div style="font-size: 14px; font-weight: 700; color: #f8fafc;">${headerTitle}</div>
              <div style="font-size: 11px; color: #25d366;"><i class="fab fa-whatsapp"></i> ${headerSub}</div>
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 6px;">
            <button id="waChatGalleryBtn" title="Media & Attachments Gallery" style="width: 32px; height: 32px; border-radius: 50%; background: #1e3a8a; border: 1px solid #60a5fa; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 13px; cursor: pointer;">
              <i class="fas fa-images"></i>
            </button>
            ${!isGroup && cleanPhone ? `
              <button id="waHeaderSoftphoneBtn" data-phone="${cleanPhone}" data-name="${this.escapeAttr(headerTitle || '')}" title="Call via Softphone" style="width: 32px; height: 32px; border-radius: 50%; background: #15803d; border: 1px solid #86efac; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 12px; cursor: pointer;">
                <i class="fas fa-phone-alt"></i>
              </button>
            ` : ''}
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

          ${this.chatHistory.map((m, idx) => this.renderMessageBubble(m, idx)).join('')}
        </div>

        <!-- Quoted Reply Banner (if active) -->
        ${this.activeReplyContext ? `
          <div style="padding: 6px 12px; background: #064e3b; border-top: 1px solid #059669; border-left: 4px solid #10b981; display: flex; justify-content: space-between; align-items: center;">
            <div style="flex: 1; min-width: 0; margin-right: 8px;">
              <div style="font-size: 11px; font-weight: 700; color: #34d399; display: flex; align-items: center; gap: 4px;">
                <i class="fas fa-reply" style="font-size: 10px;"></i>
                <span>Replying to ${this.escapeHtml(this.activeReplyContext.sender || 'Contact')}</span>
              </div>
              <div style="font-size: 11.5px; color: #e2e8f0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px;">
                ${this.escapeHtml(this.activeReplyContext.text || '[Attachment]')}
              </div>
            </div>
            <button id="waRemoveReplyBtn" style="background: none; border: none; color: #a7f3d0; font-size: 14px; cursor: pointer; padding: 2px 6px;">✕</button>
          </div>
        ` : ''}

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
      <div style="background: #1e293b; border-top: 1px solid #334155; padding: 12px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;">
        <input type="file" id="waChatFileInput" accept="image/jpeg,image/png,image/webp,application/pdf" style="display: none;" />
        
        <button class="wa-attach-choice-btn" data-type="upload-image" style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 10px 4px; color: #fff; font-size: 11px; font-weight: 600; display: flex; flex-direction: column; align-items: center; gap: 6px; cursor: pointer;">
          <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(59,130,246,0.15); display: flex; align-items: center; justify-content: center;">
            <i class="fas fa-image" style="font-size: 16px; color: #3b82f6;"></i>
          </div>
          <span>Photos</span>
        </button>

        <button class="wa-attach-choice-btn" data-type="upload-doc" style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 10px 4px; color: #fff; font-size: 11px; font-weight: 600; display: flex; flex-direction: column; align-items: center; gap: 6px; cursor: pointer;">
          <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(239,68,68,0.15); display: flex; align-items: center; justify-content: center;">
            <i class="fas fa-file-pdf" style="font-size: 16px; color: #ef4444;"></i>
          </div>
          <span>Document</span>
        </button>

        <button class="wa-attach-choice-btn" data-type="brochure" style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 10px 4px; color: #fff; font-size: 11px; font-weight: 600; display: flex; flex-direction: column; align-items: center; gap: 6px; cursor: pointer;">
          <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(168,85,247,0.15); display: flex; align-items: center; justify-content: center;">
            <i class="fas fa-book-open" style="font-size: 16px; color: #a855f7;"></i>
          </div>
          <span>Brochure</span>
        </button>

        <button class="wa-attach-choice-btn" data-type="location" style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 10px 4px; color: #fff; font-size: 11px; font-weight: 600; display: flex; flex-direction: column; align-items: center; gap: 6px; cursor: pointer;">
          <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(16,185,129,0.15); display: flex; align-items: center; justify-content: center;">
            <i class="fas fa-map-marker-alt" style="font-size: 16px; color: #10b981;"></i>
          </div>
          <span>Location</span>
        </button>
      </div>
    `;
  }

  private renderMediaPreview(m: any): string {
    let url = m.media_url || m.url || '';
    if (!url) return '';
    url = String(url).trim();
    if (/^\d+$/.test(url)) {
      url = `/api/v1/whatsapp/media/${url}`;
    }
    // Prefix relative URLs with APP_CONFIG.MEDIA_BASE_URL for native Capacitor / mobile parity
    const fullUrl = (url.startsWith('/') && APP_CONFIG.MEDIA_BASE_URL)
      ? `${APP_CONFIG.MEDIA_BASE_URL}${url}`
      : url;

    const dlUrl = fullUrl.includes('?') ? `${fullUrl}&download=1` : `${fullUrl}?download=1`;
    const mime = (m.media_mime_type || '').toLowerCase();
    const type = (m.media_type || '').toLowerCase();
    const isPdf = (type === 'document') || mime.includes('pdf') || /\.pdf(\?.*)?$/i.test(fullUrl);
    const isImage = !isPdf && ((type === 'image') || mime.startsWith('image/') || (/\.(jpg|jpeg|png|webp|gif)(\?.*)?$/i.test(fullUrl)));
    
    let rawFilename = m.media_name || m.filename || (url.split('/').pop()?.split('?')[0]) || '';
    let displayFilename = rawFilename;
    if (!displayFilename || /^\d+$/.test(displayFilename)) {
      displayFilename = isImage ? 'Photo Attachment' : (isPdf ? 'Document Attachment' : 'Media Attachment');
    }

    if (isImage) {
      return `
        <div class="wa-media-card" style="margin-bottom: 6px; border-radius: 8px; overflow: hidden; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); position: relative;">
          <a href="${fullUrl}" target="_blank" rel="noopener noreferrer" style="display: block; position: relative; min-height: 120px; background: rgba(0,0,0,0.2);">
            <img src="${fullUrl}" alt="Photo" style="width: 100%; max-height: 240px; object-fit: cover; display: block;" 
                 loading="lazy"
                 onerror="this.onerror=null; this.parentElement.innerHTML='<div style=\\'padding: 24px 12px; text-align: center; color: #94a3b8; font-size: 11px;\\'><i class=\\'fas fa-image\\' style=\\'font-size: 28px; color: #64748b; margin-bottom: 6px; display: block;\\'></i>Photo Attachment</div>';" />
          </a>
          <div style="padding: 6px 8px; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: space-between;">
            <span style="font-size: 10.5px; color: #cbd5e1; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 170px;">
              <i class="fas fa-camera" style="margin-right: 4px; font-size: 9.5px; color: #38bdf8;"></i>${this.escapeHtml(displayFilename)}
            </span>
            <a href="${dlUrl}" download="${this.escapeAttr(displayFilename)}" style="display: inline-flex; align-items: center; gap: 4px; font-size: 10.5px; color: #34d399; font-weight: 700; text-decoration: none;">
              <i class="fas fa-download"></i> Download
            </a>
          </div>
        </div>
      `;
    }

    return `
      <div style="margin-bottom: 6px;">
        <div style="display: flex; align-items: center; gap: 8px; padding: 7px 10px; background: rgba(0,0,0,0.25); border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);">
          <i class="${isPdf ? 'fas fa-file-pdf' : 'fas fa-file-alt'}" style="font-size: 20px; color: ${isPdf ? '#ef4444' : '#38bdf8'}; flex-shrink: 0;"></i>
          <div style="flex: 1; min-width: 0;">
            <div style="font-size: 11.5px; font-weight: 600; color: #f8fafc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${this.escapeHtml(displayFilename)}</div>
            <div style="font-size: 9.5px; color: #94a3b8;">${isPdf ? 'PDF Document' : 'Attachment'}</div>
          </div>
          <a href="${fullUrl}" target="_blank" rel="noopener noreferrer" style="padding: 4px 8px; background: #0284c7; color: #fff; border-radius: 4px; font-size: 10px; text-decoration: none; font-weight: 600; margin-right: 4px;">View</a>
          <a href="${dlUrl}" download="${this.escapeAttr(displayFilename)}" style="padding: 4px 8px; background: #059669; color: #fff; border-radius: 4px; font-size: 10px; text-decoration: none; font-weight: 600;">Download</a>
        </div>
      </div>
    `;
  }

  private renderMessageBubble(m: any, idx: number = 0): string {
    const isOutbound = m.message_type === 'outbound' || m.message_type === 'bot' || m.message_type === 'manual_staff' || m.sender === 'bot' || m.sender_type === 'bot' || m.is_from_me;
    const isBot = m.message_type === 'bot' || m.sender_type === 'bot';
    
    let timeStr = m.sent_at || '';
    if (!timeStr) {
      try {
        const dt = new Date(m.received_at || m.timestamp || Date.now());
        timeStr = dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
      } catch {
        timeStr = '';
      }
    }

    const text = m.body_text || m.body || m.message || '';
    const ticks = m.status_ticks || '✓✓';
    const mediaHtml = this.renderMediaPreview(m);

    let quotedHtml = '';
    if (m.reply_to && (m.reply_to.text || m.reply_to.wamid)) {
      const qSender = m.reply_to.sender || 'Replied Message';
      const qText = m.reply_to.text || 'Attachment / Original Message';
      quotedHtml = `
        <div style="margin-bottom: 6px; padding: 5px 8px; border-left: 3px solid ${isOutbound ? '#a7f3d0' : '#10b981'}; background: rgba(0,0,0,0.2); border-radius: 4px; font-size: 11px;">
          <div style="font-weight: 700; color: ${isOutbound ? '#a7f3d0' : '#34d399'}; margin-bottom: 2px;">${this.escapeHtml(qSender)}</div>
          <div style="color: ${isOutbound ? '#e2e8f0' : '#cbd5e1'}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${this.escapeHtml(qText)}</div>
        </div>
      `;
    }

    if (isOutbound) {
      return `
        <div style="align-self: flex-end; max-width: 82%; background: ${isBot ? '#065f46' : '#059669'}; color: #fff; padding: 8px 12px; border-radius: 12px 12px 2px 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.2);">
          ${isBot ? '<div style="font-size: 9.5px; font-weight: 700; color: #a7f3d0; margin-bottom: 2px;"><i class="fas fa-robot"></i> Bot Automated</div>' : ''}
          ${quotedHtml}
          ${mediaHtml}
          ${text ? `<div style="font-size: 13px; line-height: 1.35; word-break: break-word; white-space: pre-wrap;">${this.escapeHtml(text)}</div>` : ''}
          <div style="font-size: 9.5px; color: #a7f3d0; text-align: right; margin-top: 3px; display: flex; align-items: center; justify-content: flex-end; gap: 4px;">
            <button class="wa-bubble-reply-btn" data-idx="${idx}" style="background: none; border: none; color: #a7f3d0; cursor: pointer; font-size: 10px; padding: 2px 4px; display: inline-flex; align-items: center;" title="Reply to message">
              <i class="fas fa-reply"></i>
            </button>
            <button class="wa-bubble-fwd-btn" data-msg="${this.escapeAttr(text)}" style="background: none; border: none; color: #a7f3d0; cursor: pointer; font-size: 10px; padding: 2px 4px; display: inline-flex; align-items: center;" title="Forward message">
              <i class="fas fa-share"></i>
            </button>
            <span>${timeStr}</span>
            <span style="font-size: 10px; color: #a7f3d0;">${ticks}</span>
          </div>
        </div>
      `;
    }

    return `
      <div style="align-self: flex-start; max-width: 82%; background: #1e293b; color: #f8fafc; padding: 8px 12px; border-radius: 12px 12px 12px 2px; border: 1px solid #334155; box-shadow: 0 1px 3px rgba(0,0,0,0.2);">
        ${quotedHtml}
        ${mediaHtml}
        ${text ? `<div style="font-size: 13px; line-height: 1.35; word-break: break-word; white-space: pre-wrap;">${this.escapeHtml(text)}</div>` : ''}
        <div style="font-size: 9.5px; color: #94a3b8; text-align: right; margin-top: 3px; display: flex; align-items: center; justify-content: flex-end; gap: 4px;">
          <button class="wa-bubble-reply-btn" data-idx="${idx}" style="background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 10px; padding: 2px 4px; display: inline-flex; align-items: center;" title="Reply to message">
            <i class="fas fa-reply"></i>
          </button>
          <button class="wa-bubble-fwd-btn" data-msg="${this.escapeAttr(text)}" style="background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 10px; padding: 2px 4px; display: inline-flex; align-items: center;" title="Forward message">
            <i class="fas fa-share"></i>
          </button>
          <span>${timeStr}</span>
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
    const rawName = item.resolved_name || item.from_name || item.caller_name || '';
    const hasRealName = rawName && rawName !== '0' && rawName !== 'None' && rawName !== 'null' && !/^\d+$/.test(rawName) && !rawName.startsWith('Customer (+91') && !rawName.startsWith('Contact (+91');
    const displayName = hasRealName ? rawName : `Customer (${this.maskPhone(cleanPhone)})`;
    const initial = (displayName.charAt(0) || 'W').toUpperCase();
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
        data-name="${this.escapeAttr(displayName)}"
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
                ${displayName}
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
                ${cleanPhone ? `
                  <button class="wa-row-call-btn" data-phone="${cleanPhone}" data-name="${this.escapeAttr(displayName)}" title="Call via Softphone" style="background: #14532d; border: 1px solid #22c55e; color: #4ade80; border-radius: 6px; padding: 2px 8px; font-size: 11px; font-weight: 700; cursor: pointer;">
                    <i class="fas fa-phone-alt"></i> Call
                  </button>
                ` : ''}
                <button class="wa-row-assign-btn" data-phone="${phone}" data-name="${this.escapeAttr(displayName)}" style="background: #1e293b; border: 1px solid #475569; color: #38bdf8; border-radius: 6px; padding: 2px 8px; font-size: 11px; cursor: pointer;">
                  <i class="fas fa-tag"></i> Assign
                </button>
                <button class="wa-row-chat-btn" data-phone="${phone}" data-name="${this.escapeAttr(displayName)}" style="background: #059669; border: none; color: #fff; border-radius: 6px; padding: 2px 8px; font-size: 11px; cursor: pointer;">
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
            Truthful background dispatch counts, live relational scheduler status, and 3-day history matrix.
          </div>
        </div>

        ${this.subLoading ? `
          <div style="text-align: center; padding: 30px; color: #94a3b8;">
            <i class="fas fa-spinner fa-spin" style="font-size: 24px; color: #25d366; margin-bottom: 8px;"></i>
            <div>Loading automations...</div>
          </div>
        ` : ''}

        ${!this.subLoading && this.automationsList.length === 0 ? `
          <div style="text-align: center; padding: 30px 20px; background: #1e293b; border-radius: 12px; border: 1px solid #334155;">
            <i class="fas fa-robot" style="font-size: 32px; color: #64748b; margin-bottom: 8px;"></i>
            <div style="font-size: 14px; font-weight: 600;">No Automations Found</div>
          </div>
        ` : ''}

        ${this.automationsList.map(a => {
          const st = a.latest_stats || { total_messages: 0, sent_count: 0, failed_count: 0, uncertain_count: 0 };
          const isDynamic = a.archetype === 'dynamic_segment';
          return `
            <div style="background: #1e293b; border-radius: 10px; padding: 12px; border: 1px solid #334155;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-size: 13px; font-weight: 700; color: #38bdf8;">${this.escapeHtml(a.name || a.title || a.job_id || 'Automation Rule')}</span>
                <span style="font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; background: ${isDynamic ? '#78350f' : '#065f46'}; color: ${isDynamic ? '#fef3c7' : '#a7f3d0'};">
                  ${isDynamic ? 'DYNAMIC' : 'STATIC'}
                </span>
              </div>
              <div style="font-size: 11.5px; color: #cbd5e1; margin-bottom: 6px;">
                Category: <strong>${this.escapeHtml(a.category || 'Automated')}</strong> • Schedule: <strong>${this.escapeHtml(a.schedule || 'Daily')}</strong>
              </div>
              <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 6px;">
                <span style="font-size: 10.5px; background: #0f172a; color: #a7f3d0; padding: 2px 6px; border-radius: 4px; border: 1px solid #059669;">
                  <i class="fas fa-check-circle"></i> ${st.sent_count || 0} Sent
                </span>
                ${st.uncertain_count > 0 ? `
                  <span style="font-size: 10.5px; background: #0f172a; color: #fde68a; padding: 2px 6px; border-radius: 4px; border: 1px solid #d97706;">
                    <i class="fas fa-exclamation-triangle"></i> ${st.uncertain_count} Uncertain
                  </span>
                ` : ''}
                ${st.failed_count > 0 ? `
                  <span style="font-size: 10.5px; background: #0f172a; color: #fecaca; padding: 2px 6px; border-radius: 4px; border: 1px solid #dc2626;">
                    <i class="fas fa-times-circle"></i> ${st.failed_count} Failed
                  </span>
                ` : ''}
              </div>
              <div style="font-size: 10.5px; color: #94a3b8; display: flex; justify-content: space-between; align-items: center;">
                <span>Next Run: <strong style="color:#a7f3d0;">${this.escapeHtml(a.next_run || 'Scheduled')}</strong></span>
              </div>
            </div>
          `;
        }).join('')}
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
        const raw = res.data;
        if (Array.isArray(raw)) {
          this.inboxItems = raw;
        } else if (raw && typeof raw === 'object') {
          this.inboxItems = Array.isArray(raw.items) ? raw.items : (Array.isArray(raw.data) ? raw.data : []);
          if (raw.stats) {
            this.inboxStats = raw.stats;
          }
        }
        if (this.inboxItems.length > 0 && (!this.inboxStats || !this.inboxStats.all)) {
          this.inboxStats.all = this.inboxItems.length;
          this.inboxStats.unread = this.inboxItems.filter((i: any) => !i.is_read).length;
          this.inboxStats.pending = this.inboxItems.filter((i: any) => i.status === 'pending').length;
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
      let url = `/whatsapp/conversations-hub?scope=${this.activeScope}`;
      if (this.fMsgSearch) {
        url += `&search=${encodeURIComponent(this.fMsgSearch.trim())}`;
      }
      const res = await apiService.get<any>(url);
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

  private async loadChat(phone: string, name: string, originTab?: 'messenger' | 'team' | 'company' | 'all' | 'broadcasts' | 'inbox'): Promise<void> {
    if (originTab) {
      this.chatOriginTab = originTab;
    } else if (['team', 'inbox', 'messenger', 'company', 'all', 'broadcasts'].includes(this.activeTab)) {
      this.chatOriginTab = this.activeTab as any;
    }

    const isGroup = (phone && (phone.includes('@g.us') || phone.startsWith('120363') || phone.length > 14));
    const cleanPhone = (phone || '').replace(/[^0-9]/g, '').slice(-10);
    let safeName = name;
    if (!safeName || safeName === '0' || safeName === 'None' || safeName === 'null' || /^\d+$/.test(safeName)) {
      safeName = isGroup ? (phone || 'WhatsApp Group') : `Customer (+91 ${cleanPhone})`;
    }
    this.activeChatPhone = phone;
    this.activeChatName = safeName;
    this.showEmojiTray = false;
    this.showAttachMenu = false;
    this.chatLoading = true;
    this.render();

    try {
      const recParam = isGroup ? '&recipient_type=group' : '&recipient_type=individual';
      const res = await apiService.get<any>(`/whatsapp/chat-history?phone=${encodeURIComponent(phone)}${recParam}`);
      if (res.success && res.data && res.data.messages && res.data.messages.length > 0) {
        this.chatHistory = res.data.messages;
      } else {
        const fallbackRes = await apiService.get<any>(`/whatsapp/inbox/thread/${encodeURIComponent(phone)}`);
        if (fallbackRes.success && fallbackRes.data) {
          this.chatHistory = fallbackRes.data.messages || [];
        } else {
          this.chatHistory = [];
        }
      }
    } catch (err) {
      console.error('[StaffWhatsAppCenter] Error loading thread:', err);
      this.chatHistory = [];
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
      const res = await apiService.get<any>('/whatsapp-config/templates');
      if (res.success && res.data && res.data.templates) {
        this.templatesList = res.data.templates.map((t: any) => ({
          name: t.name || t.template_name || 'Template',
          category: t.category || t.segment || 'UTILITY',
          status: t.status || 'APPROVED',
          body: t.body_text || t.content || t.body || ''
        }));
      } else if (res.templates) {
        this.templatesList = res.templates.map((t: any) => ({
          name: t.name || t.template_name || 'Template',
          category: t.category || t.segment || 'UTILITY',
          status: t.status || 'APPROVED',
          body: t.body_text || t.content || t.body || ''
        }));
      } else {
        const fallback = await apiService.get<any>('/whatsapp/scheduler-templates/1');
        if (fallback.success && fallback.data && fallback.data.templates) {
          this.templatesList = fallback.data.templates;
        }
      }
    } catch {
      try {
        const fallback = await apiService.get<any>('/whatsapp/scheduler-templates/1');
        if (fallback.success && fallback.data && fallback.data.templates) {
          this.templatesList = fallback.data.templates;
        }
      } catch {
        this.templatesList = [];
      }
    } finally {
      this.subLoading = false;
      this.render();
    }
  }

  private async loadAutomations(): Promise<void> {
    this.subLoading = true;
    this.render();

    try {
      const res = await apiService.get<any>('/whatsapp/scheduler-status');
      if (res.success && res.data && res.data.jobs) {
        this.automationsList = res.data.jobs;
      } else if (res.jobs) {
        this.automationsList = res.jobs;
      } else {
        this.automationsList = [];
      }
    } catch {
      this.automationsList = [];
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

    // Center Banner Refresh Button
    document.getElementById('waBannerRefreshBtn')?.addEventListener('click', async () => {
      const icon = document.getElementById('waBannerRefreshIcon');
      if (icon) icon.classList.add('fa-spin');
      await this.loadCurrentTab();
      if (icon) icon.classList.remove('fa-spin');
    });

    // Messenger & Team Messages Live Search
    const msgSearchInput = document.getElementById('waMsgSearchInput') as HTMLInputElement;
    if (msgSearchInput) {
      let dt: any;
      msgSearchInput.addEventListener('input', () => {
        clearTimeout(dt);
        dt = setTimeout(() => {
          this.fMsgSearch = msgSearchInput.value;
          this.loadMessenger();
        }, 300);
      });
    }

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
        if (target.closest('.wa-row-assign-btn') || target.closest('.wa-row-call-btn') || target.closest('.wa-row-chat-btn')) return;

        const phone = (card as HTMLElement).dataset.phone;
        const name = (card as HTMLElement).dataset.name || 'Customer';
        if (phone) {
          this.loadChat(phone, name, 'inbox');
        }
      });
    });

    this.container.querySelectorAll('.wa-row-call-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const phone = (btn as HTMLElement).dataset.phone || '';
        const name = (btn as HTMLElement).dataset.name || '';
        if (phone) {
          callController.openCallDialer({
            phoneNumber: phone,
            name: name || 'Customer',
            autoStart: true
          });
        }
      });
    });

    this.container.querySelectorAll('.wa-row-chat-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const phone = (btn as HTMLElement).dataset.phone || '';
        const name = (btn as HTMLElement).dataset.name || '';
        if (phone) {
          this.loadChat(phone, name, 'inbox');
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
      card.addEventListener('click', (e) => {
        const target = e.target as HTMLElement;
        if (target.closest('.wa-card-call-btn')) return;
        const phone = (card as HTMLElement).dataset.phone || '';
        const name = (card as HTMLElement).dataset.name || 'Customer';
        this.loadChat(phone, name, this.activeTab as any);
      });
    });

    this.container.querySelectorAll('.wa-card-call-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const phone = (btn as HTMLElement).dataset.phone || '';
        const name = (btn as HTMLElement).dataset.name || '';
        if (phone) {
          callController.openCallDialer({
            phoneNumber: phone,
            name: name || 'Customer',
            autoStart: true
          });
        }
      });
    });

    // Chat Media Gallery Button
    document.getElementById('waChatGalleryBtn')?.addEventListener('click', () => {
      this.openChatGalleryModal();
    });

    // Back to conversation list preserving origin tab
    document.getElementById('waBackToMsgListBtn')?.addEventListener('click', () => {
      this.activeChatPhone = null;
      this.activeTab = this.chatOriginTab;
      this.render();
    });

    // Intercept top header back button if chat is open
    document.getElementById('backBtn')?.addEventListener('click', (e) => {
      if (this.activeChatPhone) {
        e.stopImmediatePropagation();
        this.activeChatPhone = null;
        this.activeTab = this.chatOriginTab;
        this.render();
      }
    }, true);

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

    // File Input for Chat Attachments
    const chatFileInput = document.getElementById('waChatFileInput') as HTMLInputElement;
    chatFileInput?.addEventListener('change', async () => {
      const file = chatFileInput.files?.[0];
      if (!file) return;

      this.activeAttachment = {
        type: file.type.startsWith('image/') ? 'image' : 'document',
        name: `Uploading ${file.name}...`
      };
      this.showAttachMenu = false;
      this.render();

      try {
        const fd = new FormData();
        fd.append('file', file);
        const res = await apiService.uploadFile<any>('/whatsapp/media-upload', fd);
        if (res.success && res.data && res.data.media_url) {
          this.activeAttachment = {
            type: res.data.media_type || (file.type.startsWith('image/') ? 'image' : 'document'),
            name: res.data.filename || file.name,
            url: res.data.media_url
          };
        } else {
          alert(res.error || 'Failed to upload attachment.');
          this.activeAttachment = null;
        }
      } catch (err: any) {
        alert(`Upload failed: ${err.message || 'Network error'}`);
        this.activeAttachment = null;
      } finally {
        chatFileInput.value = '';
        this.render();
        this.scrollToChatBottom();
      }
    });

    // Attachment Choices
    this.container.querySelectorAll('.wa-attach-choice-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const type = (e.currentTarget as HTMLElement).dataset.type;
        if (type === 'upload-image') {
          if (chatFileInput) {
            chatFileInput.accept = 'image/jpeg,image/png,image/webp';
            chatFileInput.click();
          }
        } else if (type === 'upload-doc') {
          if (chatFileInput) {
            chatFileInput.accept = 'application/pdf';
            chatFileInput.click();
          }
        } else if (type === 'brochure') {
          this.activeAttachment = { 
            type: 'document', 
            name: 'MyntReal_Venture_Brochure.pdf',
            url: '/storage/wa_media/MyntReal_Venture_Brochure.pdf'
          };
          this.showAttachMenu = false;
          this.render();
        } else if (type === 'location') {
          const input = document.getElementById('waLiveMsgInput') as HTMLInputElement;
          if (input) {
            input.value += (input.value ? '\n' : '') + '📍 Venture Location: https://maps.google.com/?q=17.729,83.308';
            input.focus();
          }
          this.showAttachMenu = false;
          this.render();
        }
      });
    });

    // Remove Attachment
    document.getElementById('waRemoveAttachBtn')?.addEventListener('click', () => {
      this.activeAttachment = null;
      this.render();
    });

    // Remove Reply Context
    document.getElementById('waRemoveReplyBtn')?.addEventListener('click', () => {
      this.activeReplyContext = null;
      this.render();
    });

    // Bubble Reply Button
    document.querySelectorAll('.wa-bubble-reply-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const idxStr = (btn as HTMLElement).getAttribute('data-idx');
        if (idxStr !== null) {
          const idx = parseInt(idxStr, 10);
          const m = this.chatHistory[idx];
          if (m) {
            const isOut = m.message_type === 'outbound' || m.message_type === 'bot' || m.message_type === 'manual_staff' || m.sender === 'bot' || m.sender_type === 'bot';
            const sender = isOut ? 'You' : (this.activeChatName || 'Customer');
            let text = m.body_text || m.body || m.message || '';
            if (!text || text === '—') {
              text = m.media_url ? '[Attachment]' : '';
            }
            const wamid = m.wamid || (m.id ? String(m.id).replace('ml_', '').replace('wa_', '') : null);
            this.activeReplyContext = {
              wamid: wamid || `msg_${idx}`,
              text: text.length > 80 ? text.substring(0, 80) + '...' : text,
              sender: sender
            };
            this.render();
            const input = document.getElementById('waLiveMsgInput') as HTMLInputElement;
            if (input) input.focus();
          }
        }
      });
    });

    // Live Message Send
    const sendBtn = document.getElementById('waLiveSendBtn');
    const msgInput = document.getElementById('waLiveMsgInput') as HTMLInputElement;

    const doSend = async () => {
      let text = msgInput?.value?.trim() || '';
      const currentAttach = this.activeAttachment;

      if (!text && !currentAttach) return;
      if (!this.activeChatPhone) return;

      if (msgInput) msgInput.value = '';
      this.activeAttachment = null;
      this.showEmojiTray = false;
      this.showAttachMenu = false;

      const replyCtx = this.activeReplyContext;
      this.activeReplyContext = null;

      const user: any = authService.getAuthState().user || {};
      const staffName = user.full_name || user.name || 'Staff';
      let ext = user.extension || user.ext || (typeof window !== 'undefined' ? (window as any).__STAFF_EXTENSION__ : null);
      if (!ext && user.emp_code) {
        const m = String(user.emp_code).match(/(\d{2,4})$/);
        if (m) ext = m[1].replace(/^0+/, '') || m[1];
      }
      let signature = `\n\nRegards,\n${staffName}\n📞 +91 85858 52738 | +91 8897797667`;
      if (ext && String(ext).trim() && !['none', 'null', 'undefined', 'n/a'].includes(String(ext).trim().toLowerCase())) {
        signature = `\n\nRegards,\n${staffName}\n📞 +91 85858 52738 | +91 8897797667\nExt: ${String(ext).trim()}`;
      }
      const finalMsg = text ? (!text.toLowerCase().includes('regards,') ? `${text}${signature}` : text) : '';

      this.chatHistory.push({
        id: Date.now(),
        from_phone: this.activeChatPhone,
        message_type: 'outbound',
        body_text: finalMsg,
        media_url: currentAttach?.url || null,
        media_name: currentAttach?.name || null,
        media_type: currentAttach?.type || 'text',
        reply_to: replyCtx ? { wamid: replyCtx.wamid, text: replyCtx.text, sender: replyCtx.sender } : undefined,
        received_at: new Date().toISOString(),
        status_ticks: '✓✓'
      });
      this.render();
      this.scrollToChatBottom();

      try {
        const cleanPhone = (this.activeChatPhone || '').replace(/[^0-9]/g, '').slice(-10);
        await apiService.post('/whatsapp/send-message', {
          recipient: cleanPhone,
          to_phone: cleanPhone,
          phone: cleanPhone,
          message: finalMsg,
          media_url: currentAttach?.url || null,
          message_type: currentAttach ? currentAttach.type : 'text',
          recipient_type: 'individual',
          reply_to_wamid: replyCtx?.wamid || null,
          reply_to_text: replyCtx?.text || null,
          reply_to_sender: replyCtx?.sender || null
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

    // Header Softphone Call Button
    document.getElementById('waHeaderSoftphoneBtn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      const btn = e.currentTarget as HTMLElement;
      const phone = btn.dataset.phone;
      const name = btn.dataset.name;
      if (phone) {
        callController.openCallDialer({
          phoneNumber: phone,
          name: name || 'Customer',
          autoStart: true
        });
      }
    });

    // Message Bubble Forward Button
    this.container.querySelectorAll('.wa-bubble-fwd-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const msg = (btn as HTMLElement).dataset.msg || '';
        this.openForwardModal(msg);
      });
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

          <p style="font-size: 12px; color: #94a3b8; margin-bottom: 16px; line-height: 1.4;">
            Open WhatsApp on your phone > <strong>Linked Devices</strong> > <strong>Link a Device</strong> and point your camera here:
          </p>

          <div id="mobileQrBox" style="background: #fff; padding: 12px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 12px rgba(0,0,0,0.3); margin-bottom: 16px;">
            ${this.gatewayQr ? `
              <img id="mobileQrImg" src="${this.gatewayQr.startsWith('http') || this.gatewayQr.startsWith('data:') ? this.gatewayQr : `data:image/png;base64,${this.gatewayQr}`}" alt="QR Code" style="width: 200px; height: 200px; display: block; border-radius: 8px;" />
            ` : `
              <div id="mobileQrSpinner" style="width: 200px; height: 200px; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #64748b; font-size: 12px; gap: 8px;">
                <i class="fas fa-spinner fa-spin" style="font-size: 28px; color: #25d366;"></i>
                <span>Loading QR Code...</span>
              </div>
            `}
          </div>

          <div id="mobileQrStatusNote" style="font-size: 11px; color: #64748b;">
            Live WhatsApp Web Pairing Session
          </div>

        </div>
      </div>
    `;

    document.getElementById('waQrModalCloseBtn')?.addEventListener('click', () => {
      modalWrap.innerHTML = '';
      if (this.qrPollingTimer) clearInterval(this.qrPollingTimer);
      this.qrPollingTimer = null;
    });

    let lastRenderedQr = this.gatewayQr || '';
    if (this.qrPollingTimer) clearInterval(this.qrPollingTimer);
    this.qrPollingTimer = setInterval(async () => {
      await this.checkGatewayStatus();
      if (this.gatewayConnected) {
        clearInterval(this.qrPollingTimer);
        this.qrPollingTimer = null;
        modalWrap.innerHTML = '';
        this.render();
      } else if (this.gatewayQr && this.gatewayQr !== lastRenderedQr) {
        lastRenderedQr = this.gatewayQr;
        const normalizedSrc = this.gatewayQr.startsWith('http') || this.gatewayQr.startsWith('data:')
          ? this.gatewayQr
          : `data:image/png;base64,${this.gatewayQr}`;
        const img = document.getElementById('mobileQrImg') as HTMLImageElement;
        const spinner = document.getElementById('mobileQrSpinner');
        if (img) {
          img.src = normalizedSrc;
        } else {
          const qrBox = document.getElementById('mobileQrBox');
          if (qrBox) {
            if (spinner) spinner.remove();
            qrBox.innerHTML = `<img id="mobileQrImg" src="${normalizedSrc}" alt="QR Code" style="width: 200px; height: 200px; display: block; border-radius: 8px;" />`;
          }
        }
      }
    }, 2500);
  }

  private openNewMessageModal(phoneNum?: string, initialText?: string): void {
    const modalWrap = document.getElementById('waCenterModalContainer');
    if (!modalWrap) return;

    const user: any = authService.getAuthState().user || {};
    const staffName = user.full_name || user.name || 'Staff';
    let ext = user.extension || user.ext || (typeof window !== 'undefined' ? (window as any).__STAFF_EXTENSION__ : null);
    if (!ext && user.emp_code) {
      const m = String(user.emp_code).match(/(\d{2,4})$/);
      if (m) ext = m[1].replace(/^0+/, '') || m[1];
    }
    let defaultSig = `Regards,\n${staffName}\n📞 +91 85858 52738 | +91 8897797667`;
    if (ext && String(ext).trim() && !['none', 'null', 'undefined', 'n/a'].includes(String(ext).trim().toLowerCase())) {
      defaultSig = `Regards,\n${staffName}\n📞 +91 85858 52738 | +91 8897797667\nExt: ${String(ext).trim()}`;
    }

    let activeModalEmojiCat = 'smileys';
    let showModalEmoji = false;
    let currentMode: 'scanned' | 'company' = 'scanned';
    let selectedContactPhone = (phoneNum || '').replace(/[^0-9]/g, '').slice(-10);
    let selectedContactName = '';
    let selectedContactLeadId: string | null = null;
    let searchDebounceTimer: any = null;
    let fetchedTemplates: any[] = [];
    let selectedTemplateObj: any = null;
    let variableValues: Record<string, string> = {};

    modalWrap.innerHTML = `
      <div style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 10000; display: flex; align-items: center; justify-content: center; padding: 12px; backdrop-filter: blur(4px);">
        <div style="background: #1e293b; border-radius: 16px; width: 100%; max-width: 480px; max-height: 94vh; overflow-y: auto; border: 1px solid #334155; box-shadow: 0 20px 40px rgba(0,0,0,0.5); display: flex; flex-direction: column;">
          
          <!-- Header -->
          <div style="padding: 14px 16px; background: linear-gradient(135deg, #075e54, #128c7e); border-top-left-radius: 16px; border-top-right-radius: 16px; display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 10px;">
              <div style="width: 32px; height: 32px; border-radius: 50%; background: #25d366; display: flex; align-items: center; justify-content: center; color: #0f172a; font-size: 18px;">
                <i class="fab fa-whatsapp"></i>
              </div>
              <div>
                <div style="font-size: 15px; font-weight: 700; color: #fff;">Send WhatsApp Message</div>
                <div style="font-size: 11px; color: #a7f3d0;">Unified Gateway & Meta CRM Model</div>
              </div>
            </div>
            <button id="waModalCloseBtn" style="background: rgba(0,0,0,0.2); border: none; color: #fff; width: 28px; height: 28px; border-radius: 50%; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center;">✕</button>
          </div>

          <div style="padding: 16px; display: flex; flex-direction: column; gap: 12px;">
            
            <!-- Mode Switcher (Scan WhatsApp vs WhatsApp API) -->
            <div style="display: flex; gap: 8px; background: #0f172a; border-radius: 10px; padding: 4px; border: 1px solid #334155;">
              <button id="waModeScanBtn" style="flex: 1; padding: 8px 6px; border: none; border-radius: 8px; font-size: 12px; font-weight: 700; cursor: pointer; transition: all 0.15s; background: #059669; color: #fff; box-shadow: 0 1px 4px rgba(0,0,0,0.2);">
                <i class="fas fa-qrcode text-success"></i> Scan WhatsApp
                <small style="display: block; font-weight: 400; font-size: 10px; opacity: 0.9; margin-top: 2px;">Common Number · Gateway</small>
              </button>
              <button id="waModeCompBtn" style="flex: 1; padding: 8px 6px; border: none; border-radius: 8px; font-size: 12px; font-weight: 700; cursor: pointer; transition: all 0.15s; background: transparent; color: #94a3b8;">
                <i class="fas fa-building text-primary"></i> WhatsApp API
                <small style="display: block; font-weight: 400; font-size: 10px; opacity: 0.9; margin-top: 2px;">Meta Cloud API</small>
              </button>
            </div>

            <!-- Recipient Phone / Search Field -->
            <div style="position: relative;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                <label style="font-size: 11.5px; font-weight: 600; color: #94a3b8;">Recipient Contact / Phone</label>
                <span style="font-size: 10.5px; color: #38bdf8;"><i class="fas fa-search"></i> CRM & Mobile Synced</span>
              </div>

              <!-- Selected Contact Badge (if chosen) -->
              <div id="waSelectedContactBadge" style="${selectedContactPhone ? 'display: flex;' : 'display: none;'} align-items: center; justify-content: space-between; padding: 7px 10px; background: #064e3b; border: 1px solid #059669; border-radius: 8px; margin-bottom: 6px;">
                <div style="display: flex; align-items: center; gap: 8px; font-size: 12.5px; color: #ecfdf5;">
                  <i class="fas fa-check-circle" style="color: #25d366;"></i>
                  <span id="waSelectedContactLabel">${selectedContactName || selectedContactPhone} (${this.maskPhone(selectedContactPhone)})</span>
                </div>
                <button id="waClearSelectedContactBtn" style="background: none; border: none; color: #f87171; font-size: 13px; cursor: pointer;">✕</button>
              </div>

              <!-- Search Input -->
              <div id="waPhoneInputWrap" style="${selectedContactPhone ? 'display: none;' : 'display: flex;'} align-items: center; background: #0f172a; border: 1px solid #334155; border-radius: 10px; overflow: hidden;">
                <span style="padding: 9px 12px; background: #1e293b; color: #25d366; font-size: 12.5px; font-weight: 700; border-right: 1px solid #334155; display: flex; align-items: center; gap: 4px;">
                  🇮🇳 +91
                </span>
                <input 
                  type="text" 
                  id="waNewPhoneInput" 
                  value="${selectedContactPhone || ''}" 
                  placeholder="Search name or enter 10-digit number..."
                  autocomplete="off"
                  style="flex: 1; padding: 9px 12px; background: transparent; border: none; color: #fff; font-size: 13px; outline: none;"
                />
                <span id="waSearchSpinner" style="display: none; padding-right: 10px; color: #25d366; font-size: 12px;">
                  <i class="fas fa-spinner fa-spin"></i>
                </span>
              </div>

              <!-- Live Search Dropdown Drawer -->
              <div id="waSearchResultsDrawer" style="display: none; position: absolute; top: 100%; left: 0; right: 0; background: #1e293b; border: 1px solid #475569; border-radius: 10px; margin-top: 4px; max-height: 220px; overflow-y: auto; z-index: 10001; box-shadow: 0 10px 25px rgba(0,0,0,0.6);">
                <div id="waSearchResultsList" style="padding: 4px;"></div>
              </div>
            </div>

            <!-- CRM Filters (Segment & Category) -->
            <div>
              <div style="font-size: 11px; font-weight: 600; color: #94a3b8; margin-bottom: 5px;">Template Filters</div>
              <div style="display: flex; gap: 8px;">
                <select id="waSegSelect" style="flex: 1; font-size: 12px; padding: 7px 10px; border: 1px solid #334155; border-radius: 8px; background: #0f172a; color: #fff; outline: none;">
                  <option value="">All Segments</option>
                  <option value="general">MNR General</option>
                  <option value="solar">Solar</option>
                  <option value="myntreal_real">Myntreal Real</option>
                  <option value="ev_b2c">EV B2C</option>
                  <option value="ev_b2b">EV B2B</option>
                  <option value="real_estate">Real Estate</option>
                  <option value="etc_training">ETC Training</option>
                  <option value="vgk">VGK Members</option>
                  <option value="system">System</option>
                </select>
                <select id="waCatSelect" style="flex: 1; font-size: 12px; padding: 7px 10px; border: 1px solid #334155; border-radius: 8px; background: #0f172a; color: #fff; outline: none;">
                  <option value="">All Categories</option>
                  <option value="MARKETING">Marketing</option>
                  <option value="UTILITY">Utility</option>
                  <option value="AUTHENTICATION">Authentication</option>
                </select>
              </div>
            </div>

            <!-- Template Selector Dropdown -->
            <div>
              <label id="waTplLabel" style="display: block; font-size: 11px; font-weight: 600; color: #94a3b8; margin-bottom: 5px;">
                Template (Optional — Any Active)
              </label>
              <select id="waTplSelect" style="width: 100%; font-size: 12.5px; padding: 8px 10px; border: 1px solid #334155; border-radius: 8px; background: #0f172a; color: #fff; outline: none;">
                <option value="">— Select a template (optional) —</option>
              </select>
            </div>

            <!-- Dynamic Variables Fill-in Box -->
            <div id="waVarSection" style="display: none; background: #0f172a; border-radius: 10px; padding: 10px; border: 1px solid #334155;">
              <div style="font-size: 11px; font-weight: 700; color: #38bdf8; text-transform: uppercase; margin-bottom: 6px;">
                <i class="fas fa-sliders-h"></i> Fill in Variables
              </div>
              <div id="waVarInputsContainer" style="display: flex; flex-direction: column; gap: 6px;"></div>
            </div>

            <!-- WhatsApp Message Composer Box -->
            <div style="background: #0f172a; border-radius: 12px; border: 1px solid #334155; overflow: hidden;">
              
              <!-- Formatting Toolbar -->
              <div style="padding: 6px 10px; background: #1e293b; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 6px;">
                  <button id="waFmtBold" title="Bold" style="padding: 2px 7px; border-radius: 4px; background: #334155; color: #fff; font-weight: 700; font-size: 11.5px; border: none; cursor: pointer;">B</button>
                  <button id="waFmtItalic" title="Italic" style="padding: 2px 7px; border-radius: 4px; background: #334155; color: #fff; font-style: italic; font-size: 11.5px; border: none; cursor: pointer;">I</button>
                  <button id="waFmtStrike" title="Strikethrough" style="padding: 2px 7px; border-radius: 4px; background: #334155; color: #fff; text-decoration: line-through; font-size: 11.5px; border: none; cursor: pointer;">S</button>
                  <button id="waFmtMono" title="Monospace" style="padding: 2px 7px; border-radius: 4px; background: #334155; color: #fff; font-family: monospace; font-size: 11px; border: none; cursor: pointer;">&lt;/&gt;</button>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                  <!-- Attachment Trigger Button -->
                  <button id="waModalAttachBtn" title="Attach Photo or Document" style="background: rgba(56,189,248,0.15); border: 1px solid rgba(56,189,248,0.3); border-radius: 6px; padding: 2px 8px; font-size: 11.5px; color: #38bdf8; cursor: pointer; display: flex; align-items: center; gap: 4px; font-weight: 600;">
                    <i class="fas fa-paperclip"></i>
                    <span>Attach</span>
                  </button>
                  <input type="file" id="waModalFileInput" accept="image/jpeg,image/png,image/webp,application/pdf" style="display: none;" />

                  <!-- Emoji Picker Toggle -->
                  <button id="waModalEmojiToggle" style="background: none; border: none; font-size: 17px; color: #25d366; cursor: pointer; padding: 2px; display: flex; align-items: center;">
                    <i class="far fa-smile"></i>
                  </button>
                </div>
              </div>

              <!-- Message Textarea -->
              <textarea 
                id="waNewTextInput" 
                rows="4" 
                placeholder="Type a message as on WhatsApp or select template above..."
                style="width: 100%; box-sizing: border-box; padding: 10px 12px; background: transparent; border: none; color: #fff; font-size: 13px; outline: none; resize: vertical; line-height: 1.5; font-family: inherit;"
              >${initialText || ''}</textarea>

              <!-- Upload Progress Indicator -->
              <div id="waModalUploadProgress" style="display: none; padding: 7px 12px; background: #0f172a; border-top: 1px solid #334155; font-size: 11.5px; color: #38bdf8; align-items: center; gap: 6px;">
                <i class="fas fa-spinner fa-spin"></i>
                <span>Uploading attachment...</span>
              </div>

              <!-- Selected Attachment Preview Chip in Modal -->
              <div id="waModalAttachPreviewWrap" style="display: none; padding: 8px 12px; background: #1e293b; border-top: 1px solid #334155; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 8px; min-width: 0;">
                  <div id="waModalAttachIcon" style="width: 28px; height: 28px; border-radius: 6px; background: #0f172a; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                    <i class="fas fa-paperclip" style="color: #38bdf8;"></i>
                  </div>
                  <div style="min-width: 0;">
                    <div id="waModalAttachFileName" style="font-size: 12px; font-weight: 600; color: #f8fafc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">filename.pdf</div>
                    <div id="waModalAttachFileSize" style="font-size: 10px; color: #94a3b8;">Uploaded</div>
                  </div>
                </div>
                <button id="waModalRemoveAttachBtn" style="background: none; border: none; color: #ef4444; font-size: 14px; cursor: pointer; padding: 4px;">✕</button>
              </div>

              <!-- Expandable Emoji Tray in Modal -->
              <div id="waModalEmojiDrawer" style="display: none; background: #1e293b; border-top: 1px solid #334155; padding: 8px;">
                <div style="display: flex; gap: 4px; overflow-x: auto; padding-bottom: 6px; margin-bottom: 6px; border-bottom: 1px solid #334155;">
                  <button class="wa-modal-ecat active" data-cat="smileys" style="padding: 3px 8px; border-radius: 10px; background: #059669; color: #fff; border: none; font-size: 11px; cursor: pointer;">😀 Smileys</button>
                  <button class="wa-modal-ecat" data-cat="hands" style="padding: 3px 8px; border-radius: 10px; background: #334155; color: #94a3b8; border: none; font-size: 11px; cursor: pointer;">👍 Hands</button>
                  <button class="wa-modal-ecat" data-cat="realestate" style="padding: 3px 8px; border-radius: 10px; background: #334155; color: #94a3b8; border: none; font-size: 11px; cursor: pointer;">🏠 Real Estate</button>
                  <button class="wa-modal-ecat" data-cat="reactions" style="padding: 3px 8px; border-radius: 10px; background: #334155; color: #94a3b8; border: none; font-size: 11px; cursor: pointer;">❤️ Hearts</button>
                  <button class="wa-modal-ecat" data-cat="travel" style="padding: 3px 8px; border-radius: 10px; background: #334155; color: #94a3b8; border: none; font-size: 11px; cursor: pointer;">🚗 Travel</button>
                </div>
                <div id="waModalEmojiGrid" style="display: grid; grid-template-columns: repeat(8, 1fr); gap: 4px; max-height: 120px; overflow-y: auto; font-size: 18px; text-align: center;">
                  ${this.emojiData.smileys.map(em => `<span class="wa-modal-emo-item" style="cursor: pointer; padding: 3px; border-radius: 4px; user-select: none;">${em}</span>`).join('')}
                </div>
              </div>

            </div>

            <!-- Signature Toggle & Live Preview -->
            <div style="background: #0f172a; border-radius: 10px; border: 1px solid #334155; padding: 10px;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                <label style="display: flex; align-items: center; gap: 6px; font-size: 11.5px; color: #e2e8f0; cursor: pointer; font-weight: 600;">
                  <input type="checkbox" id="waAttachSigCheck" checked style="accent-color: #25d366;" />
                  Attach Staff Signature
                </label>
                <span style="font-size: 10.5px; color: #25d366;"><i class="fas fa-check-circle"></i> Sender Tracked</span>
              </div>
              
              <!-- Live WhatsApp Chat Bubble Preview -->
              <div style="font-size: 10.5px; color: #94a3b8; margin-bottom: 4px;">Live WhatsApp Message Preview:</div>
              <div style="background: #005c4b; border-radius: 10px; border-top-right-radius: 2px; padding: 10px 12px; color: #e9edef; font-size: 12.5px; line-height: 1.4; box-shadow: 0 1px 3px rgba(0,0,0,0.3);">
                <div id="waLivePreviewMedia" style="display: none; margin-bottom: 6px; border-radius: 6px; overflow: hidden; background: rgba(0,0,0,0.2);"></div>
                <div id="waLivePreviewText" style="white-space: pre-wrap; word-break: break-word;">Hello from MyntReal!</div>
                <div id="waLivePreviewSig" style="white-space: pre-wrap; font-size: 11px; color: #8696a0; margin-top: 6px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 4px;">${defaultSig}</div>
                <div style="text-align: right; font-size: 10px; color: #8696a0; margin-top: 4px; display: flex; align-items: center; justify-content: flex-end; gap: 4px;">
                  <span>Just now</span>
                  <span style="color: #53bdeb;">✓✓</span>
                </div>
              </div>
            </div>

            <!-- Send Action Button -->
            <div style="display: flex; gap: 8px;">
              <button id="waModalSendBtn" style="flex: 1; padding: 12px; border-radius: 10px; background: linear-gradient(135deg, #059669, #10b981); color: #fff; font-size: 14px; font-weight: 700; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; box-shadow: 0 4px 12px rgba(5,150,105,0.4);">
                <i class="fab fa-whatsapp" style="font-size: 18px;"></i>
                <span id="waModalSendBtnText">Send via Scan WhatsApp</span>
              </button>
            </div>

          </div>

        </div>
      </div>
    `;

    // Modal Close
    document.getElementById('waModalCloseBtn')?.addEventListener('click', () => {
      modalWrap.innerHTML = '';
    });

    const textInput = document.getElementById('waNewTextInput') as HTMLTextAreaElement;
    const phoneInput = document.getElementById('waNewPhoneInput') as HTMLInputElement;
    const searchDrawer = document.getElementById('waSearchResultsDrawer');
    const searchList = document.getElementById('waSearchResultsList');
    const searchSpinner = document.getElementById('waSearchSpinner');
    const selectedBadge = document.getElementById('waSelectedContactBadge');
    const selectedLabel = document.getElementById('waSelectedContactLabel');
    const phoneInputWrap = document.getElementById('waPhoneInputWrap');
    const previewText = document.getElementById('waLivePreviewText');
    const previewSig = document.getElementById('waLivePreviewSig');
    const sigCheck = document.getElementById('waAttachSigCheck') as HTMLInputElement;
    const emojiDrawer = document.getElementById('waModalEmojiDrawer');
    const emojiGrid = document.getElementById('waModalEmojiGrid');
    const segSelect = document.getElementById('waSegSelect') as HTMLSelectElement;
    const catSelect = document.getElementById('waCatSelect') as HTMLSelectElement;
    const tplSelect = document.getElementById('waTplSelect') as HTMLSelectElement;
    const tplLabel = document.getElementById('waTplLabel');
    const varSection = document.getElementById('waVarSection');
    const varInputsContainer = document.getElementById('waVarInputsContainer');
    const sendBtn = document.getElementById('waModalSendBtn') as HTMLButtonElement;
    const sendBtnText = document.getElementById('waModalSendBtnText');

    const btnScan = document.getElementById('waModeScanBtn');
    const btnComp = document.getElementById('waModeCompBtn');

    // Update Live Preview Bubble
    const updatePreview = () => {
      if (previewText) {
        previewText.textContent = textInput?.value || 'Hello from MyntReal!';
      }
      if (previewSig) {
        previewSig.style.display = sigCheck?.checked ? 'block' : 'none';
      }
    };

    textInput?.addEventListener('input', updatePreview);
    sigCheck?.addEventListener('change', updatePreview);
    updatePreview();

    // Mode Switcher Handler
    const applyMode = (mode: 'scanned' | 'company') => {
      currentMode = mode;
      if (mode === 'scanned') {
        if (btnScan) { btnScan.style.background = '#059669'; btnScan.style.color = '#fff'; }
        if (btnComp) { btnComp.style.background = 'transparent'; btnComp.style.color = '#94a3b8'; }
        if (tplLabel) tplLabel.textContent = 'Template (Optional — Any Active)';
        if (sendBtnText) sendBtnText.textContent = 'Send via Scan WhatsApp';
        if (sendBtn) sendBtn.style.background = 'linear-gradient(135deg, #059669, #10b981)';
      } else {
        if (btnComp) { btnComp.style.background = '#2563eb'; btnComp.style.color = '#fff'; }
        if (btnScan) { btnScan.style.background = 'transparent'; btnScan.style.color = '#94a3b8'; }
        if (tplLabel) tplLabel.textContent = 'Template (Meta-Approved Only)';
        if (sendBtnText) sendBtnText.textContent = 'Send via WhatsApp API';
        if (sendBtn) sendBtn.style.background = 'linear-gradient(135deg, #2563eb, #3b82f6)';
      }
      loadCrmTemplates();
    };

    btnScan?.addEventListener('click', () => applyMode('scanned'));
    btnComp?.addEventListener('click', () => applyMode('company'));

    // Load Templates matching Filters
    const loadCrmTemplates = async () => {
      if (!tplSelect) return;
      tplSelect.innerHTML = '<option value="">— Loading templates… —</option>';

      const seg = segSelect?.value || '';
      const cat = catSelect?.value || '';

      try {
        let url = currentMode === 'company' 
          ? `/whatsapp-config/templates/approved?1=1` 
          : `/whatsapp-config/templates?1=1`;
        if (seg) url += `&segment=${encodeURIComponent(seg)}`;
        if (cat && currentMode === 'company') url += `&category=${encodeURIComponent(cat)}`;

        const res = await apiService.get<any>(url);
        if (res.success && res.data) {
          const list = res.data.templates || (Array.isArray(res.data) ? res.data : []);
          fetchedTemplates = list;

          if (list.length === 0) {
            tplSelect.innerHTML = '<option value="">— No templates found for this filter —</option>';
          } else {
            tplSelect.innerHTML = '<option value="">— Select a template (optional) —</option>' + 
              list.map((t: any) => `
                <option value="${t.id || t.template_id}">${t.title || t.name} (${t.segment || 'general'})</option>
              `).join('');
          }
        }
      } catch (err) {
        console.error('Error loading CRM templates:', err);
        tplSelect.innerHTML = '<option value="">— Error loading templates —</option>';
      }
    };

    segSelect?.addEventListener('change', loadCrmTemplates);
    catSelect?.addEventListener('change', loadCrmTemplates);
    loadCrmTemplates();

    // Template Change Handler with Variable Extraction
    tplSelect?.addEventListener('change', () => {
      const tplId = tplSelect.value;
      if (!tplId) {
        selectedTemplateObj = null;
        if (varSection) varSection.style.display = 'none';
        return;
      }

      selectedTemplateObj = fetchedTemplates.find((t: any) => String(t.id || t.template_id) === String(tplId));
      if (!selectedTemplateObj) return;

      const bodyText = selectedTemplateObj.body_text || selectedTemplateObj.text || selectedTemplateObj.content || '';
      
      // Extract {{var}} placeholders
      const matches: string[] = bodyText.match(/\{\{([^}]+)\}\}/g) || [];
      const varKeys: string[] = Array.from(new Set(matches.map((m: string) => m.replace(/[{}]/g, '').trim())));

      variableValues = {};
      if (varKeys.length > 0 && varSection && varInputsContainer) {
        varSection.style.display = 'block';
        varInputsContainer.innerHTML = varKeys.map((k: string) => {
          let defaultVal = '';
          if (k === '1' || k === 'name' || k === 'customer_name') {
            defaultVal = selectedContactName || 'Customer';
          }
          variableValues[k] = defaultVal;

          return `
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
              <span style="font-size: 11.5px; color: #94a3b8; font-weight: 600; width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{${k}}}</span>
              <input 
                type="text" 
                class="wa-tpl-var-input" 
                data-key="${k}" 
                value="${defaultVal}" 
                placeholder="Value for {{${k}}}"
                style="flex: 1; padding: 5px 8px; border-radius: 6px; background: #1e293b; border: 1px solid #334155; color: #fff; font-size: 12px; outline: none;"
              />
            </div>
          `;
        }).join('');

        // Attach variable change listeners
        varInputsContainer.querySelectorAll('.wa-tpl-var-input').forEach(inp => {
          inp.addEventListener('input', (e) => {
            const el = e.target as HTMLInputElement;
            variableValues[el.dataset.key || ''] = el.value;
            renderTemplatedMessage();
          });
        });
      } else if (varSection) {
        varSection.style.display = 'none';
      }

      renderTemplatedMessage();
    });

    const renderTemplatedMessage = () => {
      if (!selectedTemplateObj || !textInput) return;
      let msg = selectedTemplateObj.body_text || selectedTemplateObj.text || selectedTemplateObj.content || '';
      for (const [k, v] of Object.entries(variableValues)) {
        msg = msg.split(`{{${k}}}`).join(v || `{{${k}}}`);
      }
      textInput.value = msg;
      updatePreview();
    };

    // Select Contact Helper
    const selectContact = (phone: string, name: string, sourceBadge?: string, leadId?: string) => {
      selectedContactPhone = phone.replace(/[^0-9]/g, '').slice(-10);
      selectedContactName = name || 'Customer';
      selectedContactLeadId = leadId || null;

      if (selectedBadge && selectedLabel && phoneInputWrap && searchDrawer) {
        selectedLabel.textContent = `${selectedContactName} (${this.maskPhone(selectedContactPhone)}) ${sourceBadge ? `[${sourceBadge}]` : ''}`;
        selectedBadge.style.display = 'flex';
        phoneInputWrap.style.display = 'none';
        searchDrawer.style.display = 'none';
      }

      // If variable 1 / customer_name is present, update it
      if (variableValues['1'] !== undefined) variableValues['1'] = selectedContactName;
      if (variableValues['customer_name'] !== undefined) variableValues['customer_name'] = selectedContactName;
      if (variableValues['name'] !== undefined) variableValues['name'] = selectedContactName;
      renderTemplatedMessage();
    };

    // Clear Selected Contact
    document.getElementById('waClearSelectedContactBtn')?.addEventListener('click', () => {
      selectedContactPhone = '';
      selectedContactName = '';
      selectedContactLeadId = null;
      if (selectedBadge && phoneInputWrap && phoneInput) {
        selectedBadge.style.display = 'none';
        phoneInputWrap.style.display = 'flex';
        phoneInput.value = '';
        phoneInput.focus();
      }
    });

    // Live Contact Search Listener
    phoneInput?.addEventListener('input', () => {
      const q = phoneInput.value.trim();
      if (searchDebounceTimer) clearTimeout(searchDebounceTimer);

      if (q.length < 1) {
        if (searchDrawer) searchDrawer.style.display = 'none';
        return;
      }

      const cleanDigits = q.replace(/[^0-9]/g, '');
      if (cleanDigits.length === 10) {
        selectedContactPhone = cleanDigits;
      }

      if (searchSpinner) searchSpinner.style.display = 'inline-block';

      searchDebounceTimer = setTimeout(async () => {
        try {
          const res = await apiService.get<any>(`/whatsapp/search-contacts?q=${encodeURIComponent(q)}`);
          if (searchSpinner) searchSpinner.style.display = 'none';

          if (res.success && res.data && res.data.contacts && res.data.contacts.length > 0) {
            const contacts = res.data.contacts;
            if (searchList && searchDrawer) {
              searchList.innerHTML = contacts.map((c: any) => `
                <div 
                  class="wa-search-item" 
                  data-phone="${c.phone}" 
                  data-name="${this.escapeAttr(c.name)}" 
                  data-source="${c.source || ''}"
                  data-lead-id="${c.id || ''}"
                  style="display: flex; align-items: center; justify-content: space-between; padding: 8px 10px; border-radius: 8px; cursor: pointer; border-bottom: 1px solid #334155; transition: background 0.15s;"
                >
                  <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 28px; height: 28px; border-radius: 50%; background: ${c.badge_color || '#059669'}; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: #fff;">
                      ${(c.name.charAt(0) || 'C').toUpperCase()}
                    </div>
                    <div>
                      <div style="font-size: 13px; font-weight: 700; color: #f8fafc;">${c.name}</div>
                      <div style="font-size: 10.5px; color: #94a3b8;">${c.masked_phone || this.maskPhone(c.phone)}</div>
                    </div>
                  </div>
                  <span style="font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 10px; background: rgba(255,255,255,0.1); color: ${c.badge_color || '#38bdf8'};">
                    ${c.source}
                  </span>
                </div>
              `).join('');

              searchDrawer.style.display = 'block';

              // Attach item click
              searchList.querySelectorAll('.wa-search-item').forEach(item => {
                item.addEventListener('click', (e) => {
                  const target = e.currentTarget as HTMLElement;
                  const phone = target.dataset.phone || '';
                  const name = target.dataset.name || '';
                  const src = target.dataset.source || '';
                  const lid = target.dataset.leadId || '';
                  selectContact(phone, name, src, lid);
                });
              });
            }
          } else {
            if (searchList && searchDrawer) {
              searchList.innerHTML = `<div style="padding: 10px; text-align: center; color: #94a3b8; font-size: 12px;">No matching contacts found. You can type the 10-digit number directly.</div>`;
              searchDrawer.style.display = 'block';
            }
          }
        } catch {
          if (searchSpinner) searchSpinner.style.display = 'none';
        }
      }, 200);
    });

    // Formatting Toolbar Helpers
    const wrapSelection = (before: string, after: string) => {
      if (!textInput) return;
      const start = textInput.selectionStart;
      const end = textInput.selectionEnd;
      const sel = textInput.value.substring(start, end);
      const rep = sel ? `${before}${sel}${after}` : `${before}text${after}`;
      textInput.setRangeText(rep, start, end, 'end');
      textInput.focus();
      updatePreview();
    };

    document.getElementById('waFmtBold')?.addEventListener('click', () => wrapSelection('*', '*'));
    document.getElementById('waFmtItalic')?.addEventListener('click', () => wrapSelection('_', '_'));
    document.getElementById('waFmtStrike')?.addEventListener('click', () => wrapSelection('~', '~'));
    document.getElementById('waFmtMono')?.addEventListener('click', () => wrapSelection('```', '```'));

    // Toggle Emoji Drawer in Modal
    document.getElementById('waModalEmojiToggle')?.addEventListener('click', () => {
      showModalEmoji = !showModalEmoji;
      if (emojiDrawer) {
        emojiDrawer.style.display = showModalEmoji ? 'block' : 'none';
      }
    });

    // Emoji Category Switcher in Modal
    modalWrap.querySelectorAll('.wa-modal-ecat').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const cat = (e.currentTarget as HTMLElement).dataset.cat as any;
        modalWrap.querySelectorAll('.wa-modal-ecat').forEach(b => {
          (b as HTMLElement).style.background = '#334155';
          (b as HTMLElement).style.color = '#94a3b8';
        });
        (e.currentTarget as HTMLElement).style.background = '#059669';
        (e.currentTarget as HTMLElement).style.color = '#fff';

        if (cat && (this.emojiData as any)[cat] && emojiGrid) {
          emojiGrid.innerHTML = (this.emojiData as any)[cat].map((em: string) => 
            `<span class="wa-modal-emo-item" style="cursor: pointer; padding: 3px; border-radius: 4px; user-select: none;">${em}</span>`
          ).join('');
          attachEmojiClick();
        }
      });
    });

    const attachEmojiClick = () => {
      modalWrap.querySelectorAll('.wa-modal-emo-item').forEach(item => {
        item.addEventListener('click', (e) => {
          const em = (e.currentTarget as HTMLElement).textContent || '';
          if (textInput && em) {
            const start = textInput.selectionStart;
            textInput.setRangeText(em, start, start, 'end');
            textInput.focus();
            updatePreview();
          }
        });
      });
    };
    attachEmojiClick();

    // Modal Attachment Handlers
    let attachedModalMedia: { url: string; name: string; type: string; size?: number } | null = null;
    const modalFileInput = document.getElementById('waModalFileInput') as HTMLInputElement;
    const modalAttachBtn = document.getElementById('waModalAttachBtn');
    const modalAttachPreviewWrap = document.getElementById('waModalAttachPreviewWrap');
    const modalAttachIcon = document.getElementById('waModalAttachIcon');
    const modalAttachFileName = document.getElementById('waModalAttachFileName');
    const modalAttachFileSize = document.getElementById('waModalAttachFileSize');
    const modalRemoveAttachBtn = document.getElementById('waModalRemoveAttachBtn');
    const modalUploadProgress = document.getElementById('waModalUploadProgress');
    const modalLivePreviewMedia = document.getElementById('waLivePreviewMedia');

    modalAttachBtn?.addEventListener('click', () => {
      modalFileInput?.click();
    });

    modalFileInput?.addEventListener('change', async () => {
      const file = modalFileInput.files?.[0];
      if (!file) return;

      if (modalUploadProgress) modalUploadProgress.style.display = 'flex';
      if (modalAttachPreviewWrap) modalAttachPreviewWrap.style.display = 'none';

      try {
        const fd = new FormData();
        fd.append('file', file);
        const res = await apiService.uploadFile<any>('/whatsapp/media-upload', fd);
        if (res.success && res.data && res.data.media_url) {
          attachedModalMedia = {
            url: res.data.media_url,
            name: res.data.filename || file.name,
            type: res.data.media_type || (file.type.startsWith('image/') ? 'image' : 'document'),
            size: res.data.file_size || file.size
          };

          if (modalAttachPreviewWrap) modalAttachPreviewWrap.style.display = 'flex';
          if (modalAttachFileName) modalAttachFileName.textContent = attachedModalMedia.name;
          if (modalAttachFileSize) modalAttachFileSize.textContent = `${(file.size / 1024).toFixed(0)} KB · Ready to send`;
          if (modalAttachIcon) {
            modalAttachIcon.innerHTML = attachedModalMedia.type === 'image'
              ? '<i class="fas fa-image" style="color: #3b82f6;"></i>'
              : '<i class="fas fa-file-pdf" style="color: #ef4444;"></i>';
          }

          if (modalLivePreviewMedia) {
            modalLivePreviewMedia.style.display = 'block';
            if (attachedModalMedia.type === 'image') {
              modalLivePreviewMedia.innerHTML = `<img src="${attachedModalMedia.url}" style="width:100%; max-height:160px; object-fit:cover; display:block;" />`;
            } else {
              modalLivePreviewMedia.innerHTML = `
                <div style="display:flex; align-items:center; gap:8px; padding:6px 8px; background:rgba(0,0,0,0.3); border-radius:6px;">
                  <i class="fas fa-file-pdf" style="font-size:20px; color:#ef4444;"></i>
                  <span style="font-size:11.5px; color:#fff; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${attachedModalMedia.name}</span>
                </div>
              `;
            }
          }
        } else {
          alert(res.error || 'Failed to upload attachment.');
        }
      } catch (err: any) {
        alert(`Upload failed: ${err.message || 'Network error'}`);
      } finally {
        if (modalUploadProgress) modalUploadProgress.style.display = 'none';
        modalFileInput.value = '';
      }
    });

    modalRemoveAttachBtn?.addEventListener('click', () => {
      attachedModalMedia = null;
      if (modalAttachPreviewWrap) modalAttachPreviewWrap.style.display = 'none';
      if (modalLivePreviewMedia) {
        modalLivePreviewMedia.style.display = 'none';
        modalLivePreviewMedia.innerHTML = '';
      }
    });

    // Unified Send Action
    document.getElementById('waModalSendBtn')?.addEventListener('click', async () => {
      let targetPhone = selectedContactPhone;
      if (!targetPhone) {
        const rawInput = phoneInput?.value?.trim() || '';
        targetPhone = rawInput.replace(/[^0-9]/g, '').slice(-10);
      }

      const text = textInput?.value?.trim();
      if (!targetPhone || targetPhone.length < 10) {
        alert('Please search and select a contact or enter a valid 10-digit phone number.');
        return;
      }
      if (!text && !attachedModalMedia) {
        alert('Please enter a message or attach a file.');
        return;
      }

      const attachSig = sigCheck?.checked ?? true;
      const signature = `\n\n${defaultSig}`;
      const finalMsg = text ? ((attachSig && !text.toLowerCase().includes('regards,')) ? `${text}${signature}` : text) : '';

      if (sendBtn) sendBtn.disabled = true;
      if (sendBtnText) sendBtnText.textContent = currentMode === 'company' ? 'Sending via Meta API...' : 'Sending via WhatsApp Bot...';

      try {
        if (currentMode === 'company') {
          // Meta Cloud API Send
          const tplId = selectedTemplateObj ? (selectedTemplateObj.id || selectedTemplateObj.template_id) : null;
          const leadId = selectedContactLeadId || '0';
          await apiService.post(`/whatsapp-config/crm-lead-send/${leadId}`, {
            phone: targetPhone,
            template_id: tplId ? parseInt(tplId, 10) : null,
            custom_message: !tplId ? (finalMsg || (attachedModalMedia ? `Attachment: ${attachedModalMedia.name}` : null)) : null,
            variable_values: variableValues,
            send_mode: 'company',
            media_url: attachedModalMedia?.url || null
          });
        } else {
          // Scanned Bot Gateway Send
          await apiService.post('/whatsapp/send-message', {
            recipient: targetPhone,
            to_phone: targetPhone,
            phone: targetPhone,
            message: finalMsg,
            media_url: attachedModalMedia?.url || null,
            message_type: attachedModalMedia ? attachedModalMedia.type : 'text',
            recipient_type: 'individual',
            recipient_name: selectedContactName || 'Customer'
          });
        }

        modalWrap.innerHTML = '';
        await this.loadCurrentTab();
      } catch (err: any) {
        alert(`Failed to send message: ${err.message || 'Unknown error'}`);
        if (sendBtn) sendBtn.disabled = false;
        if (sendBtnText) sendBtnText.textContent = currentMode === 'company' ? 'Send via WhatsApp API' : 'Send via Scan WhatsApp';
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

  private async openChatGalleryModal(): Promise<void> {
    if (!this.activeChatPhone) return;
    const modalWrap = document.getElementById('waCenterModalContainer');
    if (!modalWrap) return;

    const isGroup = (this.activeChatPhone && (this.activeChatPhone.includes('@g.us') || this.activeChatPhone.startsWith('120363') || this.activeChatPhone.length > 14));
    let activeCat = 'all';
    let galleryItems: any[] = [];

    const renderGalleryView = () => {
      const filtered = activeCat === 'all' ? galleryItems : galleryItems.filter(it => it.category === activeCat);
      const counts = {
        all: galleryItems.length,
        photos: galleryItems.filter(it => it.category === 'photos').length,
        documents: galleryItems.filter(it => it.category === 'documents').length,
        videos: galleryItems.filter(it => it.category === 'videos').length
      };

      const itemsHtml = filtered.length === 0 ? `
        <div style="padding: 40px 16px; text-align: center; color: #94a3b8;">
          <i class="far fa-folder-open" style="font-size: 32px; opacity: 0.5; margin-bottom: 8px;"></i>
          <div>No ${activeCat === 'all' ? 'attachments' : activeCat} found.</div>
        </div>
      ` : `
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; padding: 4px;">
          ${filtered.map(it => {
            const isAvail = it.is_available !== false;
            const url = it.file_url || '';
            const dlUrl = url.includes('?') ? `${url}&download=1` : `${url}?download=1`;
            const fname = it.file_name || 'Attachment';
            const isOut = it.direction === 'outbound';
            const dirBadge = isOut 
              ? '<span style="font-size: 9px; background: #1e3a8a; color: #93c5fd; padding: 2px 5px; border-radius: 4px; font-weight: 700;">📤 Sent</span>' 
              : '<span style="font-size: 9px; background: #064e3b; color: #a7f3d0; padding: 2px 5px; border-radius: 4px; font-weight: 700;">📥 Recv</span>';
            const timeStr = it.timestamp ? new Date(it.timestamp).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: true }) : '';

            if (it.category === 'photos') {
              return `
                <div style="background: #0f172a; border-radius: 8px; border: 1px solid #334155; overflow: hidden; display: flex; flex-direction: column;">
                  <div style="height: 100px; background: #1e293b; display: flex; align-items: center; justify-content: center; position: relative;">
                    ${isAvail ? `
                      <a href="${url}" target="_blank" style="width: 100%; height: 100%; display: block;">
                        <img src="${url}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.onerror=null;this.parentElement.innerHTML='<div style=\\'display:flex;align-items:center;justify-content:center;height:100%;color:#94a3b8;font-size:11px\\'><i class=\\'fas fa-image\\'></i></div>'"/>
                      </a>
                    ` : `
                      <div style="padding: 8px; text-align: center; color: #64748b; font-size: 10px;">
                        <i class="fas fa-cloud-download-alt" style="font-size: 20px; color: #94a3b8; margin-bottom: 4px;"></i><br>
                        <span>Archive File</span>
                      </div>
                    `}
                  </div>
                  <div style="padding: 6px; font-size: 10.5px; display: flex; flex-direction: column; justify-content: space-between; flex: 1;">
                    <div>
                      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                        ${dirBadge}
                        <span style="font-size: 9px; color: #64748b;">${timeStr}</span>
                      </div>
                      <div style="font-weight: 600; color: #f8fafc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${this.escapeAttr(fname)}">${this.escapeHtml(fname)}</div>
                    </div>
                    ${isAvail ? `
                      <div style="margin-top: 4px; text-align: right;">
                        <a href="${dlUrl}" download="${this.escapeAttr(fname)}" style="font-size: 10px; color: #34d399; font-weight: 700; text-decoration: none;"><i class="fas fa-download"></i> Save</a>
                      </div>
                    ` : ''}
                  </div>
                </div>
              `;
            } else if (it.category === 'documents') {
              return `
                <div style="background: #0f172a; border-radius: 8px; border: 1px solid #334155; padding: 8px; display: flex; flex-direction: column; justify-content: space-between;">
                  <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                      ${dirBadge}
                      <span style="font-size: 9px; color: #64748b;">${timeStr}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                      <i class="fas fa-file-pdf" style="font-size: 20px; color: #ef4444; flex-shrink: 0;"></i>
                      <div style="min-width: 0;">
                        <div style="font-weight: 600; font-size: 11px; color: #f8fafc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${this.escapeAttr(fname)}">${this.escapeHtml(fname)}</div>
                        <div style="font-size: 9px; color: #94a3b8;">Document</div>
                      </div>
                    </div>
                  </div>
                  <div style="margin-top: 6px; display: flex; justify-content: space-between; align-items: center;">
                    ${isAvail ? `
                      <a href="${url}" target="_blank" style="font-size: 10px; color: #38bdf8; font-weight: 600; text-decoration: none;">View</a>
                      <a href="${dlUrl}" download="${this.escapeAttr(fname)}" style="font-size: 10px; color: #34d399; font-weight: 700; text-decoration: none;"><i class="fas fa-download"></i> Save</a>
                    ` : `<span style="font-size: 9px; color: #64748b; font-style: italic;">Historical</span>`}
                  </div>
                </div>
              `;
            } else {
              return `
                <div style="background: #0f172a; border-radius: 8px; border: 1px solid #334155; padding: 8px; display: flex; flex-direction: column; justify-content: space-between;">
                  <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                      ${dirBadge}
                      <span style="font-size: 9px; color: #64748b;">${timeStr}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                      <i class="fas fa-video" style="font-size: 18px; color: #a855f7; flex-shrink: 0;"></i>
                      <div style="min-width: 0;">
                        <div style="font-weight: 600; font-size: 11px; color: #f8fafc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${this.escapeAttr(fname)}">${this.escapeHtml(fname)}</div>
                        <div style="font-size: 9px; color: #94a3b8;">Media</div>
                      </div>
                    </div>
                  </div>
                  <div style="margin-top: 6px; text-align: right;">
                    ${isAvail ? `
                      <a href="${url}" target="_blank" style="font-size: 10px; color: #38bdf8; font-weight: 600; text-decoration: none;">Open</a>
                    ` : `<span style="font-size: 9px; color: #64748b; font-style: italic;">Historical</span>`}
                  </div>
                </div>
              `;
            }
          }).join('')}
        </div>
      `;

      modalWrap.innerHTML = `
        <div style="position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 10000; display: flex; align-items: flex-end; justify-content: center;">
          <div style="background: #1e293b; border-radius: 16px 16px 0 0; padding: 16px; width: 100%; max-width: 480px; max-height: 85vh; display: flex; flex-direction: column; border-top: 1px solid #334155;">
            <!-- Header -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
              <div style="font-size: 14px; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
                <i class="fas fa-images" style="color: #38bdf8;"></i> Media Gallery
              </div>
              <button id="waGalleryCloseBtn" style="background: none; border: none; color: #94a3b8; font-size: 18px; cursor: pointer; padding: 4px;">✕</button>
            </div>

            <!-- Filter Pills -->
            <div style="display: flex; gap: 6px; overflow-x: auto; padding-bottom: 8px; margin-bottom: 8px;">
              <button class="wa-gal-cat-btn" data-cat="all" style="padding: 5px 10px; border-radius: 14px; font-size: 11px; font-weight: 700; border: none; cursor: pointer; white-space: nowrap; ${activeCat === 'all' ? 'background: #2563eb; color: #fff;' : 'background: #0f172a; color: #94a3b8;'}">
                All (${counts.all})
              </button>
              <button class="wa-gal-cat-btn" data-cat="photos" style="padding: 5px 10px; border-radius: 14px; font-size: 11px; font-weight: 700; border: none; cursor: pointer; white-space: nowrap; ${activeCat === 'photos' ? 'background: #2563eb; color: #fff;' : 'background: #0f172a; color: #94a3b8;'}">
                🖼️ Photos (${counts.photos})
              </button>
              <button class="wa-gal-cat-btn" data-cat="documents" style="padding: 5px 10px; border-radius: 14px; font-size: 11px; font-weight: 700; border: none; cursor: pointer; white-space: nowrap; ${activeCat === 'documents' ? 'background: #2563eb; color: #fff;' : 'background: #0f172a; color: #94a3b8;'}">
                📄 Documents (${counts.documents})
              </button>
              <button class="wa-gal-cat-btn" data-cat="videos" style="padding: 5px 10px; border-radius: 14px; font-size: 11px; font-weight: 700; border: none; cursor: pointer; white-space: nowrap; ${activeCat === 'videos' ? 'background: #2563eb; color: #fff;' : 'background: #0f172a; color: #94a3b8;'}">
                🎬 Videos (${counts.videos})
              </button>
            </div>

            <!-- Content Area -->
            <div style="flex: 1; overflow-y: auto; max-height: 60vh;">
              ${itemsHtml}
            </div>
          </div>
        </div>
      `;

      document.getElementById('waGalleryCloseBtn')?.addEventListener('click', () => {
        modalWrap.innerHTML = '';
      });

      modalWrap.querySelectorAll('.wa-gal-cat-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          activeCat = (e.currentTarget as HTMLElement).dataset.cat || 'all';
          renderGalleryView();
        });
      });
    };

    // Show initial loading
    modalWrap.innerHTML = `
      <div style="position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 10000; display: flex; align-items: flex-end; justify-content: center;">
        <div style="background: #1e293b; border-radius: 16px 16px 0 0; padding: 24px; width: 100%; max-width: 480px; text-align: center; color: #94a3b8;">
          <i class="fas fa-spinner fa-spin" style="font-size: 24px; color: #38bdf8; margin-bottom: 8px;"></i>
          <div>Loading media gallery...</div>
        </div>
      </div>
    `;

    try {
      const res = await apiService.get<any>(`/whatsapp/chat-gallery?phone=${encodeURIComponent(this.activeChatPhone)}&recipient_type=${isGroup ? 'group' : 'individual'}&category=all`);
      galleryItems = res?.items || [];
      renderGalleryView();
    } catch(err: any) {
      modalWrap.innerHTML = `
        <div style="position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 10000; display: flex; align-items: flex-end; justify-content: center;">
          <div style="background: #1e293b; border-radius: 16px 16px 0 0; padding: 20px; width: 100%; max-width: 480px; text-align: center; color: #ef4444;">
            <div>Failed to load gallery: ${this.escapeHtml(err?.message || 'Error')}</div>
            <button id="waGalErrClose" style="margin-top: 12px; padding: 6px 16px; background: #334155; color: #fff; border: none; border-radius: 6px; cursor: pointer;">Close</button>
          </div>
        </div>
      `;
      document.getElementById('waGalErrClose')?.addEventListener('click', () => { modalWrap.innerHTML = ''; });
    }
  }

  private openForwardModal(msgText: string, mediaUrl?: string): void {
    const modalWrap = document.getElementById('waCenterModalContainer');
    if (!modalWrap) return;

    let selectedTarget: { phone: string; name: string; type: string } | null = null;
    let searchDebounceTimer: any = null;

    modalWrap.innerHTML = `
      <div style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 10000; display: flex; align-items: flex-end; justify-content: center;">
        <div style="background: #1e293b; border-radius: 16px 16px 0 0; padding: 16px; width: 100%; max-width: 480px; max-height: 85vh; display: flex; flex-direction: column; border-top: 1px solid #334155;">
          
          <!-- Header -->
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div style="font-size: 15px; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
              <i class="fas fa-share" style="color: #25d366;"></i> Forward Message
            </div>
            <button id="waForwardCloseBtn" style="background: none; border: none; color: #94a3b8; font-size: 18px; cursor: pointer; padding: 4px;">✕</button>
          </div>

          <!-- Message Preview -->
          <div style="font-size: 10.5px; font-weight: 700; color: #64748b; text-transform: uppercase; margin-bottom: 4px;">Message to Forward</div>
          <div style="background: #0f172a; border-left: 3px solid #25d366; padding: 8px 10px; border-radius: 6px; font-size: 12px; color: #e2e8f0; max-height: 60px; overflow-y: auto; white-space: pre-wrap; margin-bottom: 12px;">${this.escapeHtml(msgText || (mediaUrl ? '[Media Attachment]' : ''))}</div>

          <!-- Search Input -->
          <div style="position: relative; margin-bottom: 10px;">
            <i class="fas fa-search" style="position: absolute; left: 10px; top: 10px; color: #94a3b8; font-size: 12px;"></i>
            <input 
              type="text" 
              id="waForwardSearchInp" 
              placeholder="Search contact name or phone..." 
              style="width: 100%; box-sizing: border-box; padding: 8px 12px 8px 30px; border-radius: 8px; background: #0f172a; border: 1px solid #334155; color: #fff; font-size: 12.5px; outline: none;"
            />
          </div>

          <!-- Recipients List -->
          <div style="font-size: 10.5px; font-weight: 700; color: #64748b; text-transform: uppercase; margin-bottom: 6px;">Recent Chats & Contacts</div>
          <div id="waForwardList" style="flex: 1; overflow-y: auto; max-height: 240px; border: 1px solid #334155; border-radius: 8px; background: #0f172a; margin-bottom: 12px;">
          </div>

          <!-- Selection & Send -->
          <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 6px; border-top: 1px solid #334155;">
            <div id="waForwardTargetLabel" style="font-size: 11.5px; color: #94a3b8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px;">
              Select a recipient
            </div>
            <div style="display: flex; gap: 8px;">
              <button id="waForwardCancelBtn" style="padding: 8px 14px; border-radius: 8px; background: #334155; color: #e2e8f0; border: none; font-size: 12px; font-weight: 600; cursor: pointer;">Cancel</button>
              <button id="waForwardSubmitBtn" disabled style="padding: 8px 16px; border-radius: 8px; background: #059669; color: #fff; border: none; font-size: 12px; font-weight: 700; cursor: pointer; opacity: 0.5;">
                <i class="fas fa-paper-plane"></i> Forward
              </button>
            </div>
          </div>

        </div>
      </div>
    `;

    const listEl = document.getElementById('waForwardList');
    const targetLabel = document.getElementById('waForwardTargetLabel');
    const submitBtn = document.getElementById('waForwardSubmitBtn') as HTMLButtonElement;
    const searchInp = document.getElementById('waForwardSearchInp') as HTMLInputElement;

    const renderList = (items: any[]) => {
      if (!listEl) return;
      if (!items || !items.length) {
        listEl.innerHTML = '<div style="padding: 20px; text-align: center; color: #64748b; font-size: 12px;">No contacts found.</div>';
        return;
      }
      listEl.innerHTML = items.map(c => {
        const phone = c.phone || c.from_phone || c.mobile_number || '';
        const cleanPhone = phone.replace(/[^0-9]/g, '').slice(-10);
        const name = c.name || c.contact_name || c.resolved_name || c.from_name || `Customer (${this.maskPhone(cleanPhone)})`;
        const badge = c.badge || (c.type === 'STAFF' ? '👔 Staff' : (c.recipient_type === 'group' || (phone && phone.includes('@g.us')) ? '👥 Group' : '👤 Contact'));
        const isSel = selectedTarget && selectedTarget.phone === cleanPhone;
        return `
          <div 
            class="wa-fwd-target-item" 
            data-phone="${cleanPhone}" 
            data-name="${this.escapeAttr(name)}"
            data-type="${c.recipient_type || (phone && phone.includes('@g.us') ? 'group' : 'individual')}"
            style="display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-bottom: 1px solid #1e293b; cursor: pointer; background: ${isSel ? '#064e3b' : 'transparent'};"
          >
            <div style="display: flex; align-items: center; gap: 8px; min-width: 0;">
              <div style="width: 28px; height: 28px; border-radius: 50%; background: #059669; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; color: #fff; flex-shrink: 0;">
                ${name.charAt(0).toUpperCase()}
              </div>
              <div style="min-width: 0;">
                <div style="font-size: 12.5px; font-weight: 600; color: #f8fafc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${this.escapeHtml(name)}</div>
                <div style="font-size: 10.5px; color: #64748b;">${this.maskPhone(cleanPhone)}</div>
              </div>
            </div>
            <span style="font-size: 9.5px; background: #1e293b; color: #94a3b8; padding: 2px 6px; border-radius: 4px; font-weight: 600;">${badge}</span>
          </div>
        `;
      }).join('');

      listEl.querySelectorAll('.wa-fwd-target-item').forEach(item => {
        item.addEventListener('click', () => {
          const el = item as HTMLElement;
          const phone = el.dataset.phone || '';
          const name = el.dataset.name || '';
          const type = el.dataset.type || 'individual';
          selectedTarget = { phone, name, type };
          if (targetLabel) {
            targetLabel.innerHTML = `To: <strong style="color: #25d366;">${this.escapeHtml(name)}</strong>`;
          }
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.style.opacity = '1';
          }
          renderList(items);
        });
      });
    };

    // Initial render from existing conversations
    renderList(this.convsList.length ? this.convsList : this.inboxItems);

    // Search handler
    searchInp?.addEventListener('input', () => {
      clearTimeout(searchDebounceTimer);
      const q = (searchInp.value || '').trim();
      if (!q) {
        renderList(this.convsList.length ? this.convsList : this.inboxItems);
        return;
      }
      searchDebounceTimer = setTimeout(async () => {
        try {
          if (listEl) listEl.innerHTML = '<div style="padding: 16px; text-align: center; color: #94a3b8; font-size: 11px;"><i class="fas fa-spinner fa-spin"></i> Searching...</div>';
          const res = await apiService.get<any>(`/whatsapp/contacts-search?query=${encodeURIComponent(q)}&scope=all`);
          renderList(res?.contacts || res?.results || []);
        } catch {
          if (listEl) listEl.innerHTML = '<div style="padding: 16px; text-align: center; color: #ef4444; font-size: 11px;">Search failed.</div>';
        }
      }, 300);
    });

    const closeModal = () => {
      modalWrap.innerHTML = '';
    };

    document.getElementById('waForwardCloseBtn')?.addEventListener('click', closeModal);
    document.getElementById('waForwardCancelBtn')?.addEventListener('click', closeModal);

    submitBtn?.addEventListener('click', async () => {
      if (!selectedTarget) return;
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';

      try {
        const payload = {
          recipient: selectedTarget.phone,
          recipient_type: selectedTarget.type,
          recipient_name: selectedTarget.name,
          message: msgText,
          media_url: mediaUrl || null,
          client_msg_id: `fwd_${Date.now()}`
        };

        const res = await apiService.post<any>('/whatsapp/send-message', payload);
        if (res && (res.success || res.status === 200 || (res.data && (res.data.success || res.data.status === 'sent')))) {
          alert(`Message forwarded to ${selectedTarget.name}!`);
          closeModal();
          // Switch to forwarded recipient conversation
          this.activeChatPhone = selectedTarget.phone;
          this.activeChatName = selectedTarget.name;
          this.renderSkeleton();
          await this.loadChat(selectedTarget.phone, selectedTarget.name);
        } else {
          alert((res && (res.message || res.error)) || 'Failed to forward message');
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Forward';
        }
      } catch (err: any) {
        alert(err?.message || 'Failed to forward message');
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Forward';
      }
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
