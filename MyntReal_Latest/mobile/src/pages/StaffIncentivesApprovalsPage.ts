/**
 * Staff Incentives Approvals Page
 * DC Protocol: DC_MOBILE_STAFF_INCENTIVE_APP_001
 * Full parity with /staff/incentives/approvals: Pending, Approved, Rejected queues, bulk action
 */

import { PageHeader } from '../components/PageHeader';
import { APP_CONFIG } from '../config/app.config';
import { getStoredToken } from '../utils/token';

export class StaffIncentivesApprovalsPage {
  private container: HTMLElement;
  static readonly slug = 'staff-incentives-approvals';
  static readonly label = 'Incentive Approvals';
  static readonly icon = 'fas fa-clipboard-check';
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
    const srcUrl = `${APP_CONFIG.MEDIA_BASE_URL}/staff/incentives/approvals?embed=true&token=${encodeURIComponent(token)}`;
    return `
      <div style="background:#f8fafc;min-height:100vh;padding-bottom:70px">
        ${PageHeader.render({ title: 'Incentive Approvals', showBack: true })}
        <div style="padding:8px 6px;min-height:calc(100vh - 110px)">
          <iframe
            id="staff-incentives-approvals-frame"
            src="${srcUrl}"
            allow="microphone; autoplay"
            style="width:100%;height:calc(100vh - 120px);border:0;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08)"
            loading="lazy"
            title="Incentive Approvals"
          ></iframe>
        </div>
      </div>
    `;
  }
}

export default StaffIncentivesApprovalsPage;
