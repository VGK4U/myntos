/**
 * Staff VGK Vendor Management Page
 * DC Protocol: DC_MOBILE_STAFF_VGK_VENDORS_001
 * Full parity with /staff/vgk/vendors: Vendor master, categories, products, transactions
 */

import { PageHeader } from '../components/PageHeader';
import { APP_CONFIG } from '../config/app.config';
import { getStoredToken } from '../utils/token';

export class StaffVGKVendorsManagementPage {
  private container: HTMLElement;
  static readonly slug = 'staff-vgk-vendors';
  static readonly label = 'Vendor Management';
  static readonly icon = 'fas fa-store';
  static readonly color = '#0284c7';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.container.innerHTML = await this.render();
    PageHeader.attachBackHandler();
  }

  async render(): Promise<string> {
    const token = getStoredToken();
    const srcUrl = `${APP_CONFIG.MEDIA_BASE_URL}/staff/vgk/vendors?embed=true&token=${encodeURIComponent(token)}`;
    return `
      <div style="background:#f8fafc;min-height:100vh;padding-bottom:70px">
        ${PageHeader.render({ title: 'Vendor Management', showBack: true })}
        <div style="padding:8px 6px;min-height:calc(100vh - 110px)">
          <iframe
            id="staff-vgk-vendors-frame"
            src="${srcUrl}"
            allow="microphone; autoplay"
            style="width:100%;height:calc(100vh - 120px);border:0;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08)"
            loading="lazy"
            title="Vendor Management"
          ></iframe>
        </div>
      </div>
    `;
  }
}

export default StaffVGKVendorsManagementPage;
