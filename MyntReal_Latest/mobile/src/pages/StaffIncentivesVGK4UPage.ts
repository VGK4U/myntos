/**
 * Staff Incentives VGK4U Page
 * DC Protocol: DC_MOBILE_STAFF_VGK4U_001
 * Full parity with /staff/incentives/vgk4u: hierarchy tree, stats, promote modal, details
 */

import { PageHeader } from '../components/PageHeader';
import { APP_CONFIG } from '../config/app.config';
import { getStoredToken } from '../utils/token';

export class StaffIncentivesVGK4UPage {
  private container: HTMLElement;
  static readonly slug = 'staff-incentives-vgk4u';
  static readonly label = 'All VGK4U Members';
  static readonly icon = 'fas fa-sitemap';
  static readonly color = '#7c3aed';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.container.innerHTML = await this.render();
    PageHeader.attachBackHandler();
  }

  async render(): Promise<string> {
    const token = getStoredToken();
    const srcUrl = `${APP_CONFIG.MEDIA_BASE_URL}/staff/incentives/vgk4u?embed=true&token=${encodeURIComponent(token)}`;
    return `
      <div style="background:#f8fafc;min-height:100vh;padding-bottom:70px">
        ${PageHeader.render({ title: 'All VGK4U Members', showBack: true })}
        <div style="padding:8px 6px;min-height:calc(100vh - 110px)">
          <iframe
            id="staff-incentives-vgk4u-frame"
            src="${srcUrl}"
            allow="microphone; autoplay"
            style="width:100%;height:calc(100vh - 120px);border:0;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08)"
            loading="lazy"
            title="All VGK4U Members"
          ></iframe>
        </div>
      </div>
    `;
  }
}

export default StaffIncentivesVGK4UPage;
