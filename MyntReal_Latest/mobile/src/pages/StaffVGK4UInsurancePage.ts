/**
 * Staff VGK4U Insurance Page
 * DC Protocol: DC_MOBILE_STAFF_VGK4U_INS_001
 * Full parity with /staff/vgk4u/insurance: Insurance volume, members, promotions
 */

import { PageHeader } from '../components/PageHeader';
import { APP_CONFIG } from '../config/app.config';
import { getStoredToken } from '../utils/token';

export class StaffVGK4UInsurancePage {
  private container: HTMLElement;
  static readonly slug = 'staff-vgk4u-insurance';
  static readonly label = 'VGK Care (ZC)';
  static readonly icon = 'fas fa-shield-alt';
  static readonly color = '#059669';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.container.innerHTML = await this.render();
    PageHeader.attachBackHandler();
  }

  async render(): Promise<string> {
    const token = getStoredToken();
    const srcUrl = `${APP_CONFIG.MEDIA_BASE_URL}/staff/vgk4u/insurance?embed=true&token=${encodeURIComponent(token)}`;
    return `
      <div style="background:#f8fafc;min-height:100vh;padding-bottom:70px">
        ${PageHeader.render({ title: 'VGK Care (ZC)', showBack: true })}
        <div style="padding:8px 6px;min-height:calc(100vh - 110px)">
          <iframe
            id="staff-vgk4u-insurance-frame"
            src="${srcUrl}"
            allow="microphone; autoplay"
            style="width:100%;height:calc(100vh - 120px);border:0;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08)"
            loading="lazy"
            title="VGK Care (ZC)"
          ></iframe>
        </div>
      </div>
    `;
  }
}

export default StaffVGK4UInsurancePage;
