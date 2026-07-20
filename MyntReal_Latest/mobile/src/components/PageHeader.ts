/**
 * Page Header Component
 * DC Protocol: DC_MOBILE_HEADER_001
 */

import { routerService } from '../services/router.service';
import { portalService } from '../services/portal.service';

interface HeaderOptions {
  title: string;
  showBack?: boolean;
  showLogout?: boolean;
  rightAction?: { icon: string; onClick: () => void };
}

export class PageHeader {
  static render(options: HeaderOptions): string {
    const { title, showBack = false, showLogout = false, rightAction } = options;

    return `
      <header class="page-header">
        <div class="header-left">
          ${showBack ? `
            <button class="header-btn back-btn" id="backBtn">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="15 18 9 12 15 6"/>
              </svg>
            </button>
          ` : ''}
          <h1 class="header-title">${title}</h1>
        </div>
        <div class="header-right">
          ${rightAction ? `
            <button class="header-btn action-btn" id="headerActionBtn">
              ${rightAction.icon}
            </button>
          ` : ''}
          ${showLogout ? `
            <button class="header-btn logout-btn" id="logoutBtn">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
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

  private static getPortalDashboard(): 'dashboard' | 'mnr-dashboard' | 'partner-dashboard' {
    const portal = portalService.getPortal();
    if (portal === 'mnr') return 'mnr-dashboard';
    if (portal === 'partner') return 'partner-dashboard';
    return 'dashboard';
  }

  static attachListeners(options: HeaderOptions): void {
    if (options.showBack) {
      document.getElementById('backBtn')?.addEventListener('click', () => {
        if (!routerService.goBack()) {
          routerService.navigate(PageHeader.getPortalDashboard());
        }
      });
    }

    if (options.rightAction) {
      document.getElementById('headerActionBtn')?.addEventListener('click', options.rightAction.onClick);
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
