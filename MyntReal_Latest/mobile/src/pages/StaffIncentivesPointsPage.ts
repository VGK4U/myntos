/**
 * Staff Incentives Points Page
 * DC Protocol: DC_MOBILE_STAFF_INCENTIVE_PTS_001
 * Full parity with /staff/incentives/points: MNR Points & Deliverables Matrix
 */

import { PageHeader } from '../components/PageHeader';
import { APP_CONFIG } from '../config/app.config';
import { getStoredToken } from '../utils/token';

export class StaffIncentivesPointsPage {
  private container: HTMLElement;
  static readonly slug = 'staff-incentives-points';
  static readonly label = 'MNR Points';
  static readonly icon = 'fas fa-coins';
  static readonly color = '#f59e0b';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.container.innerHTML = await this.render();
    PageHeader.attachBackHandler();
  }

  async render(): Promise<string> {
    const token = getStoredToken();
    const srcUrl = `${APP_CONFIG.MEDIA_BASE_URL}/staff/incentives/points?embed=true&token=${encodeURIComponent(token)}`;
    return `
      <div style="background:#f8fafc;min-height:100vh;padding-bottom:70px">
        ${PageHeader.render({ title: 'MNR Points', showBack: true })}
        <div style="padding:8px 6px;min-height:calc(100vh - 110px)">
          <iframe
            id="staff-incentives-points-frame"
            src="${srcUrl}"
            allow="microphone; autoplay"
            style="width:100%;height:calc(100vh - 120px);border:0;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08)"
            loading="lazy"
            title="MNR Points"
          ></iframe>
        </div>
      </div>
    `;
  }
}

export default StaffIncentivesPointsPage;
