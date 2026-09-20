/**
 * Staff VGK4U Real Estate Page
 * DC Protocol: DC_MOBILE_STAFF_VGK4U_RE_001
 * Full parity with /staff/vgk4u/real-estate: Real estate volume, members, promotions
 */

import { PageHeader } from '../components/PageHeader';
import { APP_CONFIG } from '../config/app.config';
import { getStoredToken } from '../utils/token';

export class StaffVGK4URealEstatePage {
  private container: HTMLElement;
  static readonly slug = 'staff-vgk4u-real-estate';
  static readonly label = 'VGK Real Dreams (ZR)';
  static readonly icon = 'fas fa-building';
  static readonly color = '#2563eb';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.container.innerHTML = await this.render();
    PageHeader.attachBackHandler();
  }

  async render(): Promise<string> {
    const token = getStoredToken();
    const srcUrl = `${APP_CONFIG.MEDIA_BASE_URL}/staff/vgk4u/real-estate?embed=true&token=${encodeURIComponent(token)}`;
    return `
      <div style="background:#f8fafc;min-height:100vh;padding-bottom:70px">
        ${PageHeader.render({ title: 'VGK Real Dreams (ZR)', showBack: true })}
        <div style="padding:8px 6px;min-height:calc(100vh - 110px)">
          <iframe
            id="staff-vgk4u-real-estate-frame"
            src="${srcUrl}"
            allow="microphone; autoplay"
            style="width:100%;height:calc(100vh - 120px);border:0;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08)"
            loading="lazy"
            title="VGK Real Dreams (ZR)"
          ></iframe>
        </div>
      </div>
    `;
  }
}

export default StaffVGK4URealEstatePage;
