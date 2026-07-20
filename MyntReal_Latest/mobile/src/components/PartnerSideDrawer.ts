/**
 * Partner Side Drawer Component
 * DC Protocol: DC_MOBILE_PARTNER_SIDEBAR_001
 * Left-side menu for Partner portal with Service Request at top
 */

import { routerService, PageRoute } from '../services/router.service';
import { authService } from '../services/auth.service';

interface MenuItem {
  menu_code: string;
  label: string;
  route: PageRoute;
  icon?: string;
  highlight?: boolean;
}

interface MenuSection {
  section_code: string;
  section_label: string;
  icon: string;
  order: number;
  items: MenuItem[];
}

const TOP_MENU_ITEMS: MenuItem[] = [
  { menu_code: "SERVICE_REQUEST", label: "Service Request", route: "partner-service", icon: "headset", highlight: true },
  { menu_code: "HOME_DASHBOARD", label: "Home Dashboard", route: "partner-dashboard", icon: "home" },
  { menu_code: "VIEW_PROFILE", label: "View Profile", route: "partner-profile", icon: "user" }
];

const PARTNER_MENU_MASTER: MenuSection[] = [
  {
    section_code: "ORDERS",
    section_label: "Orders",
    icon: "package",
    order: 1,
    items: [
      { menu_code: "ALL_ORDERS", label: "All Orders", route: "partner-orders" },
      { menu_code: "NEW_ORDER", label: "Create New Order", route: "partner-new-order" }
    ]
  },
  {
    section_code: "SERVICE",
    section_label: "Service Center",
    icon: "tool",
    order: 2,
    items: [
      { menu_code: "RAISE_TICKET", label: "Raise New Ticket", route: "partner-raise-ticket" },
      { menu_code: "MY_TICKETS", label: "My Tickets", route: "partner-service" },
      { menu_code: "TICKET_HISTORY", label: "Ticket History", route: "partner-ticket-history" }
    ]
  },
  {
    section_code: "FINANCE",
    section_label: "Finance",
    icon: "coins",
    order: 3,
    items: [
      { menu_code: "INVOICES", label: "Invoices", route: "partner-invoices" },
      { menu_code: "PAYMENTS", label: "Payments", route: "partner-payments" },
      { menu_code: "REVENUE", label: "Revenue Dashboard", route: "partner-revenue" }
    ]
  },
  {
    section_code: "LEADS",
    section_label: "Leads & CRM",
    icon: "users",
    order: 4,
    items: [
      { menu_code: "MY_LEADS", label: "My Leads", route: "partner-leads" }
    ]
  }
];

export class PartnerSideDrawer {
  private container: HTMLElement | null = null;
  private overlay: HTMLElement | null = null;
  private isOpen: boolean = false;
  private expandedSections: Set<string> = new Set();
  private user: any = null;

  constructor() {
    this.createElements();
  }

  private createElements(): void {
    this.overlay = document.createElement('div');
    this.overlay.className = 'partner-drawer-overlay';
    this.overlay.addEventListener('click', () => this.close());
    document.body.appendChild(this.overlay);

    this.container = document.createElement('div');
    this.container.className = 'partner-side-drawer';
    this.container.innerHTML = this.render();
    document.body.appendChild(this.container);

    this.injectStyles();
    this.attachEventListeners();
  }

  private injectStyles(): void {
    if (document.getElementById('partner-drawer-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'partner-drawer-styles';
    style.textContent = `
      .partner-drawer-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.6);
        z-index: 9998;
        opacity: 0;
        visibility: hidden;
        transition: all 0.3s ease;
      }
      .partner-drawer-overlay.visible {
        opacity: 1;
        visibility: visible;
      }
      .partner-side-drawer {
        position: fixed;
        top: 0;
        left: -300px;
        width: 280px;
        height: 100%;
        background: linear-gradient(180deg, #0a1929 0%, #0d2137 100%);
        z-index: 9999;
        transition: left 0.3s ease;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }
      .partner-side-drawer.open {
        left: 0;
      }
      .partner-drawer-header {
        background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
        padding: 20px 16px;
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
      }
      .partner-drawer-user {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .partner-user-avatar {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.2);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 18px;
        color: white;
        border: 2px solid rgba(255, 255, 255, 0.3);
      }
      .partner-user-info {
        display: flex;
        flex-direction: column;
      }
      .partner-user-name {
        font-size: 16px;
        font-weight: 600;
        color: white;
      }
      .partner-user-code {
        font-size: 12px;
        color: #ffffff;
        background: rgba(255, 255, 255, 0.28);
        border: 1px solid rgba(255, 255, 255, 0.35);
        padding: 2px 8px;
        border-radius: 4px;
        margin-top: 4px;
        font-weight: 600;
        letter-spacing: 0.5px;
      }
      .partner-user-type {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.7);
        margin-top: 2px;
      }
      .partner-drawer-close {
        background: none;
        border: none;
        color: white;
        padding: 4px;
        cursor: pointer;
      }
      .partner-drawer-content {
        flex: 1;
        overflow-y: auto;
        padding: 12px 0;
        padding-bottom: calc(80px + env(safe-area-inset-bottom, 0px));
      }
      .partner-top-menu {
        padding: 0 12px 12px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 12px;
      }
      .partner-menu-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 14px;
        border-radius: 8px;
        color: #e0e0e0;
        cursor: pointer;
        transition: all 0.2s;
        margin-bottom: 4px;
      }
      .partner-menu-item:hover, .partner-menu-item:active {
        background: rgba(30, 136, 229, 0.2);
      }
      .partner-menu-item.highlight {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        font-weight: 600;
      }
      .partner-menu-item svg {
        flex-shrink: 0;
      }
      .partner-drawer-section {
        margin-bottom: 8px;
      }
      .partner-section-header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        color: #a0aec0;
        cursor: pointer;
        transition: all 0.2s;
      }
      .partner-section-header:hover {
        background: rgba(255, 255, 255, 0.05);
      }
      .partner-section-title {
        flex: 1;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
      .partner-section-arrow {
        transition: transform 0.2s;
      }
      .partner-section-arrow.expanded {
        transform: rotate(180deg);
      }
      .partner-section-items {
        max-height: 0;
        overflow: hidden;
        transition: max-height 0.3s ease;
      }
      .partner-section-items.expanded {
        max-height: 500px;
      }
      .partner-drawer-menu-item {
        display: block;
        padding: 10px 16px 10px 48px;
        color: #b0bec5;
        font-size: 13px;
        text-decoration: none;
        cursor: pointer;
        transition: all 0.2s;
      }
      .partner-drawer-menu-item:hover, .partner-drawer-menu-item:active {
        background: rgba(30, 136, 229, 0.15);
        color: #64b5f6;
      }
      .partner-bottom-menu {
        padding: 12px;
        padding-bottom: calc(80px + env(safe-area-inset-bottom, 0px));
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        margin-top: auto;
      }
      .partner-logout-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 14px;
        border-radius: 8px;
        color: #ef5350;
        cursor: pointer;
        transition: all 0.2s;
      }
      .partner-logout-item:hover {
        background: rgba(239, 83, 80, 0.15);
      }
    `;
    document.head.appendChild(style);
  }

  setUser(user: any): void {
    this.user = user;
    this.updateUI();
  }

  private getIcon(iconName: string): string {
    const icons: Record<string, string> = {
      'home': '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
      'user': '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
      'package': '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
      'tool': '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
      'coins': '<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',
      'users': '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
      'headset': '<path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/>',
      'logout': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>'
    };
    return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${icons[iconName] || ''}</svg>`;
  }

  private render(): string {
    const username = this.user?.name || this.user?.partner_name || 'Partner';
    const partnerCode = this.user?.partner_id || this.user?.partner_code || 'PARTNER';
    const partnerType = this.user?.partner_type || this.user?.type || 'Partner';
    const initials = username.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2);

    return `
      <div class="partner-drawer-header">
        <div class="partner-drawer-user">
          <div class="partner-user-avatar">${initials}</div>
          <div class="partner-user-info">
            <span class="partner-user-name">${username}</span>
            <span class="partner-user-code">${partnerCode}</span>
            <span class="partner-user-type">${partnerType}</span>
          </div>
        </div>
        <button class="partner-drawer-close" id="partnerDrawerClose">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      <div class="partner-drawer-content">
        <div class="partner-top-menu">
          ${TOP_MENU_ITEMS.map(item => `
            <div class="partner-menu-item ${item.highlight ? 'highlight' : ''}" data-route="${item.route}">
              ${this.getIcon(item.icon || 'home')}
              <span>${item.label}</span>
            </div>
          `).join('')}
        </div>

        ${PARTNER_MENU_MASTER.map(section => this.renderSection(section)).join('')}

        <div class="partner-bottom-menu">
          <div class="partner-logout-item" id="partnerLogoutBtn">
            ${this.getIcon('logout')}
            <span>Logout</span>
          </div>
        </div>
      </div>
    `;
  }

  private renderSection(section: MenuSection): string {
    const isExpanded = this.expandedSections.has(section.section_code);
    
    return `
      <div class="partner-drawer-section" data-section="${section.section_code}">
        <div class="partner-section-header" data-toggle="${section.section_code}">
          ${this.getIcon(section.icon)}
          <span class="partner-section-title">${section.section_label}</span>
          <svg class="partner-section-arrow ${isExpanded ? 'expanded' : ''}" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </div>
        <div class="partner-section-items ${isExpanded ? 'expanded' : ''}">
          ${section.items.map(item => `
            <a class="partner-drawer-menu-item" data-route="${item.route}">
              ${item.label}
            </a>
          `).join('')}
        </div>
      </div>
    `;
  }

  private attachEventListeners(): void {
    if (!this.container) return;

    document.getElementById('partnerDrawerClose')?.addEventListener('click', () => this.close());

    this.container.querySelectorAll('[data-toggle]').forEach(el => {
      el.addEventListener('click', (e) => {
        const code = (el as HTMLElement).dataset.toggle!;
        this.toggleSection(code);
        e.stopPropagation();
      });
    });

    this.container.querySelectorAll('[data-route]').forEach(el => {
      el.addEventListener('click', () => {
        const route = (el as HTMLElement).dataset.route!;
        routerService.navigate(route as PageRoute);
        this.close();
      });
    });

    document.getElementById('partnerLogoutBtn')?.addEventListener('click', async () => {
      if (confirm('Are you sure you want to logout?')) {
        await authService.logout();
        window.dispatchEvent(new CustomEvent('logout'));
        this.close();
      }
    });
  }

  private toggleSection(code: string): void {
    if (this.expandedSections.has(code)) {
      this.expandedSections.delete(code);
    } else {
      this.expandedSections.add(code);
    }
    this.updateUI();
  }

  private updateUI(): void {
    if (!this.container) return;
    this.container.innerHTML = this.render();
    this.attachEventListeners();
  }

  open(): void {
    if (this.isOpen) return;
    this.isOpen = true;
    this.container?.classList.add('open');
    this.overlay?.classList.add('visible');
    document.body.style.overflow = 'hidden';
  }

  close(): void {
    if (!this.isOpen) return;
    this.isOpen = false;
    this.container?.classList.remove('open');
    this.overlay?.classList.remove('visible');
    document.body.style.overflow = '';
  }

  toggle(): void {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  destroy(): void {
    this.container?.remove();
    this.overlay?.remove();
  }
}

export const partnerSideDrawer = new PartnerSideDrawer();
