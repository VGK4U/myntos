/**
 * Staff VGK Promo Codes Page
 * DC Protocol: DC_MOBILE_STAFF_VGK_PROMOS_001
 * Full parity with /staff/vgk/promo-codes: Promo code creation, status, and tracking
 */

import { PageHeader } from '../components/PageHeader';
import { APP_CONFIG } from '../config/app.config';
import { getStoredToken } from '../utils/token';

export class StaffVGKPromoCodesPage {
  private container: HTMLElement;
  static readonly slug = 'staff-vgk-promo-codes';
  static readonly label = 'VGK Promo Codes';
  static readonly icon = 'fas fa-tags';
  static readonly color = '#ec4899';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.container.innerHTML = await this.render();
    PageHeader.attachBackHandler();
  }

  async render(): Promise<string> {
    const token = getStoredToken();
    const srcUrl = `${APP_CONFIG.MEDIA_BASE_URL}/staff/vgk/promo-codes?embed=true&token=${encodeURIComponent(token)}`;
    return `
      <div style="background:#f8fafc;min-height:100vh;padding-bottom:70px">
        ${PageHeader.render({ title: 'VGK Promo Codes', showBack: true })}
        <div style="padding:8px 6px;min-height:calc(100vh - 110px)">
          <iframe
            id="staff-vgk-promo-codes-frame"
            src="${srcUrl}"
            allow="microphone; autoplay"
            style="width:100%;height:calc(100vh - 120px);border:0;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08)"
            loading="lazy"
            title="VGK Promo Codes"
          ></iframe>
        </div>
      </div>
    `;
  }
}

export default StaffVGKPromoCodesPage;
