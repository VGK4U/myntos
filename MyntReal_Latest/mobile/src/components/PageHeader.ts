/**
 * Page Header Component
 * DC Protocol: DC_MOBILE_HEADER_001
 */

import { routerService } from '../services/router.service';
import { portalService } from '../services/portal.service';
import { authService } from '../services/auth.service';
import { getSideDrawer } from './SideDrawer';

interface HeaderOptions {
  title: string;
  showBack?: boolean;
  showLogout?: boolean;
  rightAction?: { icon: string; onClick: () => void };
  subtitle?: string;
  showMenu?: boolean;
}

export class PageHeader {
  static render(options: HeaderOptions): string {
    let { title, showBack = false, showLogout = false, rightAction, subtitle, showMenu } = options;

    const portal = portalService.getPortal();
    const currentRoute = routerService.getCurrentRoute();
    const isRootRoute = ['progress', 'dashboard', 'attendance', 'journeys', 'announcements', 'profile', 'mnr-dashboard', 'partner-dashboard', 'vgk-member-hub'].includes(currentRoute);

    if (showMenu === undefined) {
      showMenu = isRootRoute || !showBack;
    }

    if (portal === 'vgk') {
      showLogout = true;
      if (!subtitle) {
        const authState = authService.getAuthState();
        const user = authState.user || {};
        const name = user.name || user.partner_name || '';
        const code = user.partner_code || '';
        if (name || code) {
          subtitle = code ? `${name} (${code})` : name;
        }
      }
    }

    return `
      <header class="page-header" style="display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: #0f172a; border-bottom: 1px solid #1e293b; position: sticky; top: 0; z-index: 100;">
        <div class="header-left" style="display: flex; align-items: center; gap: 10px;">
          ${showMenu ? `
            <button class="header-btn hamburger-btn" id="hamburgerBtn" title="Open Navigation Menu" style="width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); color: #fff; border-radius: 8px; cursor: pointer; flex-shrink: 0;">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="3" y1="12" x2="21" y2="12"/>
                <line x1="3" y1="6" x2="21" y2="6"/>
                <line x1="3" y1="18" x2="21" y2="18"/>
              </svg>
            </button>
          ` : ''}
          ${showBack ? `
            <button class="header-btn back-btn" id="backBtn" title="Back" style="width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); color: #fff; border-radius: 8px; cursor: pointer; flex-shrink: 0;">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="15 18 9 12 15 6"/>
              </svg>
            </button>
          ` : ''}
          <div class="header-title-wrapper" style="display:flex; flex-direction:column; gap:2px">
            <h1 class="header-title" style="margin:0; font-size:16px; font-weight:700; color:#fff;">${title}</h1>
            ${subtitle ? `<span class="header-subtitle" style="font-size:11px; color:rgba(255,255,255,0.65); font-weight:500">${subtitle}</span>` : ''}
          </div>
        </div>
        <div class="header-right">
          ${rightAction ? `
            <button class="header-btn action-btn" id="headerActionBtn">
              ${rightAction.icon}
            </button>
          ` : ''}
          ${showLogout ? `
            <button class="header-btn logout-btn" id="logoutBtn" style="padding: 6px; display: flex; align-items: center; justify-content: center;">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
            </button>
          ` : ''}
        </div>
      </header>
    `;
  }

  private static getPortalDashboard(): 'progress' | 'mnr-dashboard' | 'partner-dashboard' | 'vgk-member-hub' {
    const portal = portalService.getPortal();
    if (portal === 'mnr') return 'mnr-dashboard';
    if (portal === 'partner') return 'partner-dashboard';
    if (portal === 'vgk') return 'vgk-member-hub';
    return 'progress';
  }

  static attachListeners(options: HeaderOptions): void {
    let { showMenu = false, showBack = false, rightAction, showLogout = false } = options;
    
    const portal = portalService.getPortal();
    if (portal === 'vgk') {
      showLogout = true;
    }

    if (showMenu) {
      document.getElementById('hamburgerBtn')?.addEventListener('click', () => {
        getSideDrawer().open();
      });
    }

    if (showBack) {
      document.getElementById('backBtn')?.addEventListener('click', () => {
        if (!routerService.goBack()) {
          routerService.navigate(PageHeader.getPortalDashboard());
        }
      });
    }

    if (rightAction) {
      document.getElementById('headerActionBtn')?.addEventListener('click', rightAction.onClick);
    }

    if (showLogout) {
      document.getElementById('logoutBtn')?.addEventListener('click', async () => {
        if (confirm('Are you sure you want to logout?')) {
          await authService.logout();
        }
      });
    }
  }

  static attachBackHandler(): void {
    document.getElementById('backBtn')?.addEventListener('click', () => {
      if (!routerService.goBack()) {
        routerService.navigate(PageHeader.getPortalDashboard());
      }
    });
  }
}
