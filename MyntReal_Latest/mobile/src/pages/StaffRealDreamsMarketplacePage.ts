/**
 * Staff Real Dreams Marketplace Page
 * DC Protocol: DC_MOBILE_STAFF_RD_MARKETPLACE_001
 * Full parity with /staff/mnr/real-dreams/marketplace and /rvz/real-dreams/marketplace
 */

import { PageHeader } from '../components/PageHeader';
import { APP_CONFIG } from '../config/app.config';
import { getStoredToken } from '../utils/token';

export class StaffRealDreamsMarketplacePage {
  private container: HTMLElement;
  static readonly slug = 'real-dreams-marketplace';
  static readonly label = 'Property Marketplace';
  static readonly icon = 'fas fa-city';
  static readonly color = '#0ea5e9';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.container.innerHTML = await this.render();
    PageHeader.attachBackHandler();
  }

  async render(): Promise<string> {
    const token = getStoredToken();
    const srcUrl = `${APP_CONFIG.MEDIA_BASE_URL}/rvz/real-dreams/marketplace?embed=true&token=${encodeURIComponent(token)}`;
    return `
      <div style="background:#f8fafc;min-height:100vh;padding-bottom:70px">
        ${PageHeader.render({ title: 'Property Marketplace', showBack: true })}
        <div style="padding:8px 6px;min-height:calc(100vh - 110px)">
          <iframe
            id="staff-real-dreams-marketplace-frame"
            src="${srcUrl}"
            allow="microphone; autoplay"
            style="width:100%;height:calc(100vh - 120px);border:0;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08)"
            loading="lazy"
            title="Property Marketplace"
          ></iframe>
        </div>
      </div>
    `;
  }
}

export default StaffRealDreamsMarketplacePage;
