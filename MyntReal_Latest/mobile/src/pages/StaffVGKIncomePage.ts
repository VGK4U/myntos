/**
 * Staff VGK Income Page
 * DC Protocol: DC_MOBILE_STAFF_VGK_INCOME_001
 * Full parity with /staff/vgk/income: Income management, calculations, payout logs
 */

import { PageHeader } from '../components/PageHeader';
import { APP_CONFIG } from '../config/app.config';
import { getStoredToken } from '../utils/token';

export class StaffVGKIncomePage {
  private container: HTMLElement;
  static readonly slug = 'staff-vgk-income';
  static readonly label = 'VGK Income Management';
  static readonly icon = 'fas fa-hand-holding-usd';
  static readonly color = '#10b981';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.container.innerHTML = await this.render();
    PageHeader.attachBackHandler();
  }

  async render(): Promise<string> {
    const token = getStoredToken();
    const srcUrl = `${APP_CONFIG.MEDIA_BASE_URL}/staff/vgk/income?embed=true&token=${encodeURIComponent(token)}`;
    return `
      <div style="background:#f8fafc;min-height:100vh;padding-bottom:70px">
        ${PageHeader.render({ title: 'VGK Income Management', showBack: true })}
        <div style="padding:8px 6px;min-height:calc(100vh - 110px)">
          <iframe
            id="staff-vgk-income-frame"
            src="${srcUrl}"
            allow="microphone; autoplay"
            style="width:100%;height:calc(100vh - 120px);border:0;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08)"
            loading="lazy"
            title="VGK Income Management"
          ></iframe>
        </div>
      </div>
    `;
  }
}

export default StaffVGKIncomePage;
