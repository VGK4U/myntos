import { PageHeader } from '../components/PageHeader';
import { APP_CONFIG } from '../config/app.config';

export class StaffMyEarningsPage {
  private container: HTMLElement;
  static readonly slug = 'staff-my-earnings';
  static readonly label = 'My Earnings';
  static readonly icon = 'fas fa-trending-up';
  static readonly color = '#10b981';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.container.innerHTML = await this.render();
    PageHeader.attachBackHandler();
  }

  async render(): Promise<string> {
    const srcUrl = `${APP_CONFIG.MEDIA_BASE_URL}/staff/my-lead-incentives`;
    return `
      <div style="background:#f3f4f6;min-height:100vh;padding-bottom:80px">
        ${PageHeader.render({ title: 'My Earnings', showBack: true })}
        <div style="padding:12px;min-height:calc(100vh - 120px)">
          <iframe
            id="staff-earnings-frame"
            src="${srcUrl}"
            style="width:100%;height:calc(100vh - 140px);border:0;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.05)"
            loading="lazy"
            title="My Earnings"
          ></iframe>
        </div>
      </div>
    `;
  }
}

export default StaffMyEarningsPage;
