import { PageHeader } from '../components/PageHeader';
import { APP_CONFIG } from '../config/app.config';
import { getStoredToken } from '../utils/token';

export class StaffVGKMembersPage {
  private container: HTMLElement;
  static readonly slug = 'staff-vgk-members';
  static readonly label = 'VGK Channel Partners';
  static readonly icon = 'fas fa-users';
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
    const srcUrl = `${APP_CONFIG.MEDIA_BASE_URL}/staff/vgk/members?embed=true&token=${encodeURIComponent(token)}`;
    return `
      <div style="background:#f8fafc;min-height:100vh;padding-bottom:70px">
        ${PageHeader.render({ title: 'VGK Channel Partners', showBack: true })}
        <div style="padding:8px 6px;min-height:calc(100vh - 110px);-webkit-overflow-scrolling:touch;">
          <iframe
            id="staff-vgk-members-frame"
            src="${srcUrl}"
            allow="microphone; camera; autoplay; clipboard-write; geolocation"
            style="width:100%;height:calc(100vh - 120px);border:0;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08);touch-action:auto;"
            loading="lazy"
            title="VGK Channel Partners"
          ></iframe>
        </div>
      </div>
    `;
  }
}

export default StaffVGKMembersPage;
