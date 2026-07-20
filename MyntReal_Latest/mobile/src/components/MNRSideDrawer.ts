/**
 * MNR Side Drawer Component
 * DC Protocol: DC_MOBILE_MNR_SIDEBAR_001
 * Matches web MNR user sidebar structure exactly
 */

import { routerService, PageRoute } from '../services/router.service';
import { authService } from '../services/auth.service';

interface MenuItem {
  menu_code: string;
  label: string;
  route: PageRoute;
  icon?: string;
}

interface MenuSection {
  section_code: string;
  section_label: string;
  icon: string;
  order: number;
  items: MenuItem[];
}

const TOP_MENU_ITEMS: MenuItem[] = [
  { menu_code: "HOME_DASHBOARD", label: "Home Dashboard", route: "mnr-dashboard", icon: "home" },
  { menu_code: "VIEW_PROFILE", label: "View Profile", route: "mnr-profile", icon: "user" },
  { menu_code: "ADD_MEMBER", label: "Add Member", route: "mnr-add-member", icon: "user-plus" }
];

const MNR_MENU_MASTER: MenuSection[] = [
  {
    section_code: "ANNOUNCEMENTS",
    section_label: "📢 Community Updates",
    icon: "bullhorn",
    order: 1,
    items: [
      { menu_code: "PUBLIC_ANNOUNCEMENTS", label: "📢 Official Updates", route: "mnr-announcements" },
      { menu_code: "MY_SUBMISSIONS", label: "📋 My Submissions", route: "mnr-my-announcements" },
      { menu_code: "PENDING", label: "⏳ Pending", route: "mnr-announcements-pending" },
      { menu_code: "APPROVED", label: "✅ Approved", route: "mnr-announcements-approved" },
      { menu_code: "REJECTED", label: "❌ Rejected", route: "mnr-announcements-rejected" }
    ]
  },
  {
    section_code: "COUPON_MODULES",
    section_label: "🎫 Coupon Modules",
    icon: "ticket",
    order: 2,
    items: [
      { menu_code: "BUY_COUPON", label: "🛒 Buy Coupon", route: "mnr-coupon-buy" },
      { menu_code: "ACTIVATE_COUPON", label: "✅ Activate Coupon", route: "mnr-coupon-activate" },
      { menu_code: "COUPON_STATUS", label: "🎫 Coupon Status", route: "mnr-coupon-status" },
      { menu_code: "COUPON_PROGRESS", label: "📊 Coupon Progress", route: "mnr-coupon-progress" },
      { menu_code: "COUPON_TRANSFER", label: "🔄 Coupon Transfer", route: "mnr-coupon-transfer" }
    ]
  },
  {
    section_code: "MEMBERS",
    section_label: "👥 My Connections",
    icon: "users",
    order: 3,
    items: [
      { menu_code: "ALL_MEMBERS", label: "👥 All Connections", route: "mnr-members-all" },
      { menu_code: "DIRECT_REFERRALS", label: "🔗 Direct Connections", route: "mnr-referrals" },
      { menu_code: "PICTURE_VIEW", label: "🌳 Connections Gallery", route: "mnr-members-picture" },
      { menu_code: "VED_TEAM", label: "👑 Leadership Group (VED)", route: "mnr-members-ved" }
    ]
  },
  {
    section_code: "MNR",
    section_label: "💰 Facilitation & Recognition",
    icon: "coins",
    order: 4,
    items: [
      { menu_code: "EARNINGS_SUMMARY", label: "📊 Earnings Overview", route: "mnr-earnings-summary" },
      { menu_code: "DIRECT_REFERRAL", label: "💰 Direct Business Facilitation", route: "mnr-income-direct" },
      { menu_code: "MATCHING_REFERRAL", label: "🤝 Group Performance Recognition", route: "mnr-income-matching" },
      { menu_code: "VED_INCOME", label: "👑 VED Leadership Recognition", route: "mnr-income-ved" },
      { menu_code: "GURUDAKSHINA", label: "🙏 Mentorship Contribution Benefit", route: "mnr-income-guru" },
      { menu_code: "FIELD_ALLOWANCE", label: "🚗 Field Allowances", route: "mnr-income-field" },
      { menu_code: "WITHDRAWALS", label: "💸 Withdrawals", route: "mnr-withdrawals" },
      { menu_code: "COUPON_BENEFITS", label: "🎁 Coupon Benefits", route: "mnr-benefits" },
      { menu_code: "MNR_POINTS", label: "🎯 Points Utilisation", route: "mnr-points" }
    ]
  },
  {
    section_code: "MYNTREAL",
    section_label: "💎 MyntReal",
    icon: "gem",
    order: 5,
    items: [
      { menu_code: "MY_LEADS", label: "📋 My Leads", route: "mnr-my-leads" },
      { menu_code: "FRANCHISE_EARNINGS", label: "🏪 Franchise Earnings", route: "mnr-franchise-earnings" }
    ]
  },
  {
    section_code: "ZYNOVA",
    section_label: "⭐ Zynova",
    icon: "crown",
    order: 6,
    items: [
      { menu_code: "VGK_REAL_DREAMS", label: "🏠 VGK Real Dreams (Real Estate)", route: "zynova-real-estate" },
      { menu_code: "VGK_CARE", label: "🛡️ VGK Care (Insurance)", route: "zynova-insurance" },
      { menu_code: "ETC", label: "🎓 EVolution Training Center (ETC)", route: "zynova-training" }
    ]
  },
  {
    section_code: "AWARDS_BONANZA",
    section_label: "🏆 Awards & Bonanza",
    icon: "trophy",
    order: 7,
    items: [
      { menu_code: "AWARDS", label: "🏆 Awards", route: "mnr-awards" },
      { menu_code: "BONANZA_AWARDS", label: "🎉 Bonanza Awards", route: "mnr-bonanza" }
    ]
  }
];

const BOTTOM_ITEMS: MenuItem[] = [
  { menu_code: "THEME_MODE", label: "Theme Mode", route: "mnr-settings", icon: "headset" },
  { menu_code: "SECURITY_SETTINGS", label: "Security Settings", route: "mnr-change-password", icon: "headset" }
];

export class MNRSideDrawer {
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
    this.overlay.className = 'mnr-drawer-overlay';
    this.overlay.addEventListener('click', () => this.close());
    document.body.appendChild(this.overlay);

    this.container = document.createElement('div');
    this.container.className = 'mnr-side-drawer';
    this.container.innerHTML = this.render();
    document.body.appendChild(this.container);

    this.attachEventListeners();
  }

  setUser(user: any): void {
    this.user = user;
    this.updateUI();
  }

  private getIcon(iconName: string): string {
    const icons: Record<string, string> = {
      'home': '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
      'user': '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
      'user-plus': '<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>',
      'bullhorn': '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
      'ticket': '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>',
      'users': '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
      'coins': '<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',
      'gem': '<polygon points="12 2 2 12 12 22 22 12 12 2"/><polyline points="12 2 12 22"/>',
      'crown': '<path d="m2 4 3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14"/>',
      'trophy': '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
      'headset': '<path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/>',
      'logout': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>'
    };
    return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${icons[iconName] || ''}</svg>`;
  }

  private render(): string {
    const username = this.user?.name || 'MNR Member';
    const mnrId = this.user?.mnr_id || '';
    const initials = username.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2);

    return `
      <div class="mnr-drawer-header">
        <div class="mnr-drawer-user">
          <div class="mnr-user-avatar">${initials}</div>
          <div class="mnr-user-info">
            <span class="mnr-user-name">${username}</span>
            <span class="mnr-user-id">${mnrId}</span>
          </div>
        </div>
        <button class="mnr-drawer-close" id="mnrDrawerClose">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      <div class="mnr-drawer-content">
        <!-- Top menu items -->
        <div class="mnr-top-menu">
          ${TOP_MENU_ITEMS.map(item => `
            <div class="mnr-menu-item top-item" data-route="${item.route}">
              ${this.getIcon(item.icon || 'home')}
              <span>${item.label}</span>
            </div>
          `).join('')}
        </div>

        <!-- Section menus -->
        ${MNR_MENU_MASTER.map(section => this.renderSection(section)).join('')}

        <!-- Bottom items -->
        <div class="mnr-bottom-menu">
          ${BOTTOM_ITEMS.map(item => `
            <div class="mnr-menu-item bottom-item" data-route="${item.route}">
              ${this.getIcon(item.icon || 'help-circle')}
              <span>${item.label}</span>
            </div>
          `).join('')}
          <div class="mnr-menu-item logout-item" id="mnrLogoutBtn">
            ${this.getIcon('logout')}
            <span class="logout-text">Logout</span>
          </div>
        </div>
      </div>
    `;
  }

  private renderSection(section: MenuSection): string {
    const isExpanded = this.expandedSections.has(section.section_code);
    
    return `
      <div class="mnr-drawer-section" data-section="${section.section_code}">
        <div class="mnr-section-header" data-toggle="${section.section_code}">
          ${this.getIcon(section.icon)}
          <span class="mnr-section-title">${section.section_label}</span>
          <svg class="mnr-section-arrow ${isExpanded ? 'expanded' : ''}" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </div>
        <div class="mnr-section-items ${isExpanded ? 'expanded' : ''}">
          ${section.items.map(item => `
            <a class="mnr-drawer-menu-item" data-route="${item.route}">
              <span class="mnr-menu-label">${item.label}</span>
            </a>
          `).join('')}
        </div>
      </div>
    `;
  }

  private attachEventListeners(): void {
    if (!this.container) return;

    document.getElementById('mnrDrawerClose')?.addEventListener('click', () => this.close());

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

    document.getElementById('mnrLogoutBtn')?.addEventListener('click', async () => {
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

export const mnrSideDrawer = new MNRSideDrawer();
