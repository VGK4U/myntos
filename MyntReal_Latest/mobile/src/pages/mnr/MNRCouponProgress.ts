import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface CouponProgress {
  total_purchased: number;
  total_activated: number;
  total_transferred: number;
  total_available: number;
  total_amount: number;
}

export class MNRCouponProgress {
  private container: HTMLElement;
  private progress: CouponProgress = {
    total_purchased: 0,
    total_activated: 0,
    total_transferred: 0,
    total_available: 0,
    total_amount: 0
  };
  private pins: any[] = [];
  private loading: boolean = true;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadProgress();
  }

  private async loadProgress(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>('/users/pins');
      if (response.success && response.data) {
        const rawPins = response.data.pins || response.data || [];
        this.pins = rawPins;
        this.progress = {
          total_purchased: rawPins.length,
          total_activated: rawPins.filter((p: any) => 
            (p.status || '').toLowerCase() === 'used' || (p.status || '').toLowerCase() === 'activated'
          ).length,
          total_transferred: rawPins.filter((p: any) => 
            (p.status || '').toLowerCase() === 'transferred'
          ).length,
          total_available: rawPins.filter((p: any) => 
            (p.status || '').toLowerCase() === 'active' || (p.status || '').toLowerCase() === 'available'
          ).length,
          total_amount: rawPins.reduce((sum: number, p: any) => sum + (p.amount || p.value || 0), 0)
        };
      }
    } catch (error) {
      console.error('[MNRCouponProgress] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = PageHeader.render({
      title: 'Coupon Progress',
      showBack: true
    });

    const content = document.createElement('div');
    content.id = 'coupon-progress-content';
    content.className = 'page-content';
    this.container.appendChild(content);

    this.updateContent();
  }

  private updateContent(): void {
    const content = document.getElementById('coupon-progress-content');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = `
        <div style="display:flex;justify-content:center;align-items:center;padding:60px 20px;">
          <div style="width:36px;height:36px;border:3px solid #e2e8f0;border-top-color:#667eea;border-radius:50%;animation:spin 1s linear infinite;"></div>
        </div>
        <style>@keyframes spin{to{transform:rotate(360deg)}}</style>
      `;
      return;
    }

    const p = this.progress;
    const activationRate = p.total_purchased > 0 ? Math.round((p.total_activated / p.total_purchased) * 100) : 0;

    content.innerHTML = `
      <div style="padding:16px;">
        <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:16px;padding:20px;color:#fff;margin-bottom:16px;">
          <div style="font-size:13px;opacity:0.9;">Total Coupons Purchased</div>
          <div style="font-size:32px;font-weight:700;margin:4px 0;">${p.total_purchased}</div>
          <div style="font-size:13px;opacity:0.8;">Total Value: ₹${p.total_amount.toLocaleString('en-IN')}</div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">
          <div style="background:#fff;border-radius:12px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
            <div style="font-size:12px;color:#64748b;">Activated</div>
            <div style="font-size:24px;font-weight:700;color:#10b981;">${p.total_activated}</div>
          </div>
          <div style="background:#fff;border-radius:12px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
            <div style="font-size:12px;color:#64748b;">Available</div>
            <div style="font-size:24px;font-weight:700;color:#3b82f6;">${p.total_available}</div>
          </div>
          <div style="background:#fff;border-radius:12px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
            <div style="font-size:12px;color:#64748b;">Transferred</div>
            <div style="font-size:24px;font-weight:700;color:#f59e0b;">${p.total_transferred}</div>
          </div>
          <div style="background:#fff;border-radius:12px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
            <div style="font-size:12px;color:#64748b;">Activation Rate</div>
            <div style="font-size:24px;font-weight:700;color:#8b5cf6;">${activationRate}%</div>
          </div>
        </div>

        <div style="background:#fff;border-radius:12px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:16px;">
          <div style="font-size:14px;font-weight:600;color:#1e293b;margin-bottom:12px;">Progress</div>
          <div style="background:#e2e8f0;border-radius:8px;height:12px;overflow:hidden;">
            <div style="background:linear-gradient(90deg,#10b981,#3b82f6);height:100%;width:${activationRate}%;border-radius:8px;transition:width 0.5s ease;"></div>
          </div>
          <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:12px;color:#64748b;">
            <span>${p.total_activated} activated</span>
            <span>${p.total_purchased} total</span>
          </div>
        </div>

        ${this.pins.length === 0 ? `
          <div style="text-align:center;padding:40px 20px;color:#94a3b8;">
            <div style="font-size:48px;margin-bottom:12px;">🎫</div>
            <div style="font-size:16px;font-weight:500;">No Coupons Yet</div>
            <div style="font-size:13px;margin-top:4px;">Purchase coupons to see your progress here</div>
          </div>
        ` : `
          <div style="font-size:14px;font-weight:600;color:#1e293b;margin-bottom:8px;">Recent Activity</div>
          ${this.pins.slice(0, 10).map((pin: any) => `
            <div style="background:#fff;border-radius:10px;padding:12px 14px;margin-bottom:8px;box-shadow:0 1px 4px rgba(0,0,0,0.05);display:flex;justify-content:space-between;align-items:center;">
              <div>
                <div style="font-size:13px;font-weight:600;color:#1e293b;">${pin.coupon_code || pin.code || pin.pin_code || 'PIN'}</div>
                <div style="font-size:11px;color:#94a3b8;">${pin.coupon_type || pin.package_type || pin.type || 'Standard'}</div>
              </div>
              <div style="text-align:right;">
                <div style="font-size:12px;font-weight:600;padding:2px 10px;border-radius:20px;background:${this.getStatusColor(pin.status)};color:#fff;">
                  ${(pin.status || 'Unknown').toUpperCase()}
                </div>
                <div style="font-size:11px;color:#94a3b8;margin-top:4px;">₹${(pin.amount || pin.value || 0).toLocaleString('en-IN')}</div>
              </div>
            </div>
          `).join('')}
        `}
      </div>
    `;
  }

  private getStatusColor(status: string): string {
    switch ((status || '').toLowerCase()) {
      case 'active': case 'available': return '#3b82f6';
      case 'used': case 'activated': return '#10b981';
      case 'transferred': return '#f59e0b';
      case 'expired': return '#ef4444';
      default: return '#94a3b8';
    }
  }
}
