/**
 * VGK4U Member Hub (Task #33 Phase 1 — Read-Only Modules)
 * DC Protocol: DC_MOBILE_VGK4U_PARITY_001 (May 2026)
 *
 * Lightweight launcher that opens each VGK4U member page in the in-app
 * web view. The web pages already do all data fetching with ?audience=vgk4u.
 */

import { PageHeader } from '../../components/PageHeader';
import { routerService } from '../../services/router.service';
import { authService } from '../../services/auth.service';
import { APP_CONFIG } from '../../config/app.config';

const NATIVE_ROUTES: Record<string, string> = {
  'birthdays':          'vgk-birthdays',
  'top-earners':        'vgk-top-earners',
  'awards':             'vgk-awards',
  'daywise-income':     'vgk-daywise-income',
  'income-types':       'vgk-income-types',
  'direct-summary':     'vgk-direct-summary',
  'matching-summary':   'vgk-matching-summary',
  'guru-summary':       'vgk-guru-summary',
  'ved-summary':        'vgk-ved-summary',
  'ev-benefits':        'vgk-ev-benefits',
  'ev-discount':        'vgk-ev-discount',
  'franchise-earnings': 'vgk-franchise-earnings',
  'insurance':          'vgk-insurance',
  'training':           'vgk-training',
  'coupon-benefits':    'vgk-coupon-benefits',
  'my-submissions':     'vgk-my-submissions',
  'bonanza-rewards':    'vgk-bonanza-rewards',
  'points-balance':     'vgk-points-balance',
};

interface ParityModule {
  slug: string;
  label: string;
  icon: string;
  color: string;
}

const MODULES: ParityModule[] = [
  { slug: 'birthdays',          label: 'Birthdays',         icon: '🎂', color: '#0ea5e9' },
  { slug: 'top-earners',        label: 'Top Earners',       icon: '🏆', color: '#f59e0b' },
  { slug: 'awards',             label: 'My Awards',         icon: '🥇', color: '#a21caf' },
  { slug: 'daywise-income',     label: 'Daywise Income',    icon: '📅', color: '#059669' },
  { slug: 'income-types',       label: 'Income Types',      icon: '📊', color: '#2563eb' },
  { slug: 'direct-summary',     label: 'Direct (L1)',       icon: '①',  color: '#475569' },
  { slug: 'matching-summary',   label: 'Matching (L2)',     icon: '②',  color: '#475569' },
  { slug: 'guru-summary',       label: 'Senior (L3)',         icon: '③',  color: '#475569' },
  { slug: 'ved-summary',        label: 'VED (L5)',          icon: '⑤',  color: '#475569' },
  { slug: 'ev-benefits',        label: 'EV Benefits',       icon: '⚡', color: '#16a34a' },
  { slug: 'ev-discount',        label: 'EV Discount',       icon: '🏷️', color: '#16a34a' },
  { slug: 'franchise-earnings', label: 'Franchise',         icon: '🏪', color: '#ea580c' },
  { slug: 'insurance',          label: 'Insurance',         icon: '🛡️', color: '#4f46e5' },
  { slug: 'training',           label: 'Training',          icon: '🎓', color: '#db2777' },
  { slug: 'coupon-benefits',    label: 'Coupon Benefits',   icon: '🎟️', color: '#e11d48' },
  { slug: 'my-submissions',     label: 'My Submissions',    icon: '📄', color: '#7c3aed' },
  { slug: 'bonanza-rewards',    label: 'Bonanza Rewards',   icon: '🏆', color: '#7c3aed' },
  { slug: 'points-balance',     label: 'Points Balance',    icon: '⭐', color: '#5b21b6' },
];

export class VGKMemberHubPage {
  private container: HTMLElement;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    const params = routerService.getRouteParams();
    const activeTab = params.tab || 'earnings';
    
    const tabTitles: Record<string, string> = {
      earnings: 'VGK4U Member Hub',
      profile: 'Profile',
      mycard: 'My Card & Progress',
      addmember: 'Add Channel Partner',
      coupons: 'Coupons',
      network: 'Team',
      points: 'Points Balance',
      ledger: 'My Earnings',
      leads: 'My Leads',
      tickets: 'Service Tickets',
      bonanza: 'Bonanza Rewards',
      vendors: 'Vendor Shops',
      media: 'Media Hub',
      orders: 'Orders'
    };
    const title = tabTitles[activeTab] || 'VGK4U Member Hub';

    const authState = authService.getAuthState();
    const user = authState.user || {};
    const name = user.name || user.partner_name || 'Member';
    const code = user.partner_code || '';
    const subtitle = code ? `${name} (${code})` : name;

    const iframe = document.getElementById('vgk4u-dashboard-frame') as HTMLIFrameElement;
    if (iframe && iframe.contentWindow) {
      // Iframe already exists! Just switch the tab inside it and update header titles
      iframe.contentWindow.postMessage({ type: 'vgk_switch_tab', tab: activeTab }, '*');
      
      const titleEl = document.querySelector('.header-title');
      if (titleEl) titleEl.textContent = title;
      
      const subtitleEl = document.querySelector('.header-subtitle');
      if (subtitleEl) subtitleEl.textContent = subtitle;
      
      localStorage.setItem('vgk_active_tab', activeTab);
    } else {
      // First load: render full page layout
      this.container.innerHTML = await this.render();
      await this.afterRender();
    }
  }

  async render(): Promise<string> {
    const authState = authService.getAuthState();
    const user = authState.user || {};
    const name = user.name || user.partner_name || 'Member';
    const code = user.partner_code || '';
    const subtitle = code ? `${name} (${code})` : name;

    const params = routerService.getRouteParams();
    const activeTab = params.tab || 'earnings';
    
    const tabTitles: Record<string, string> = {
      earnings: 'VGK4U Member Hub',
      profile: 'Profile',
      mycard: 'My Card & Progress',
      addmember: 'Add Channel Partner',
      coupons: 'Coupons',
      network: 'Team',
      points: 'Points Balance',
      ledger: 'My Earnings',
      leads: 'My Leads',
      tickets: 'Service Tickets',
      bonanza: 'Bonanza Rewards',
      vendors: 'Vendor Shops',
      media: 'Media Hub',
      orders: 'Orders'
    };
    const title = tabTitles[activeTab] || 'VGK4U Member Hub';

    return `
      ${PageHeader.render({ title, showBack: false, showLogout: true, subtitle, showMenu: true })}
      <div style="background:#f6f9fc;min-height:calc(100vh - 64px)">
        <iframe
          id="vgk4u-dashboard-frame"
          src="${APP_CONFIG.MEDIA_BASE_URL}/vgk/dashboard?embed=true&tab=${activeTab}&token=${encodeURIComponent(localStorage.getItem("auth_token") || "")}"
          style="width:100%;height:calc(100vh - 64px);border:0;background:#f6f9fc;"
          loading="lazy"
          title="VGK4U Dashboard"
        ></iframe>
      </div>
    `;
  }

  async afterRender(): Promise<void> {
    const authState = authService.getAuthState();
    const user = authState.user || {};
    const name = user.name || user.partner_name || 'Member';
    const code = user.partner_code || '';
    const subtitle = code ? `${name} (${code})` : name;

    const params = routerService.getRouteParams();
    const activeTab = params.tab || 'earnings';
    
    const tabTitles: Record<string, string> = {
      earnings: 'VGK4U Member Hub',
      profile: 'Profile',
      mycard: 'My Card & Progress',
      addmember: 'Add Channel Partner',
      coupons: 'Coupons',
      network: 'Team',
      points: 'Points Balance',
      ledger: 'My Earnings',
      leads: 'My Leads',
      tickets: 'Service Tickets',
      bonanza: 'Bonanza Rewards',
      vendors: 'Vendor Shops',
      media: 'Media Hub',
      orders: 'Orders'
    };
    const title = tabTitles[activeTab] || 'VGK4U Member Hub';

    PageHeader.attachListeners({ title, showBack: false, showLogout: true, subtitle, showMenu: true });
  }
}

export default VGKMemberHubPage;
