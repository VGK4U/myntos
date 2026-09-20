/**
 * Staff VGK Coupons Page
 * DC Protocol: DC_MOBILE_STAFF_VGK_COUPONS_001
 * Full parity with /staff/vgk/coupons/available: PIN Activation, Available, Assigned, Activated
 */

import { PageHeader } from '../components/PageHeader';
import { APP_CONFIG } from '../config/app.config';
import { getStoredToken } from '../utils/token';

export class StaffVGKCouponsPage {
  private container: HTMLElement;
  static readonly slug = 'staff-vgk-coupons';
  static readonly label = 'VGK PIN Activation';
  static readonly icon = 'fas fa-ticket-alt';
  static readonly color = '#6366f1';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.container.innerHTML = await this.render();
    PageHeader.attachBackHandler();
  }

  async render(): Promise<string> {
    const token = getStoredToken();
    const srcUrl = `${APP_CONFIG.MEDIA_BASE_URL}/staff/vgk/coupons/available?embed=true&token=${encodeURIComponent(token)}`;
    return `
      <div style="background:#f8fafc;min-height:100vh;padding-bottom:70px">
        ${PageHeader.render({ title: 'VGK PIN Activation', showBack: true })}
        <div style="padding:8px 6px;min-height:calc(100vh - 110px)">
          <iframe
            id="staff-vgk-coupons-frame"
            src="${srcUrl}"
            allow="microphone; autoplay"
            style="width:100%;height:calc(100vh - 120px);border:0;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08)"
            loading="lazy"
            title="VGK PIN Activation"
          ></iframe>
        </div>
      </div>
    `;
  }
}

export default StaffVGKCouponsPage;
