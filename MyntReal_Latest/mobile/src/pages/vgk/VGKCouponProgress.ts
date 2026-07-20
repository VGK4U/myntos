/**
 * Coupon Progress — VGK4U Member Parity (Task #34 Phase 2, write-flow)
 * DC Protocol: DC_MOBILE_VGK4U_PARITY_002 (May 2026)
 *
 * Mobile member page for the "Coupon Progress" write module. Embeds the
 * shared /vgk/coupon-progress responsive web view so we inherit form handling,
 * audience scoping (?audience=vgk4u), Zero-Default Access toggle gate,
 * and WVV verification logic without duplicating UI.
 */
import { PageHeader } from '../../components/PageHeader';

export class VGKCouponProgressPage {
  private container: HTMLElement;
  static readonly slug = 'coupon-progress';
  static readonly label = 'Coupon Progress';
  static readonly icon = 'fas fa-chart-line';
  static readonly color = '#10b981';
  static readonly endpoint = '/vgk/coupon-progress';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.container.innerHTML = await this.render();
    await this.afterRender();
  }

  async render(): Promise<string> {
    return `
      ${PageHeader.render({ title: 'Coupon Progress', showBack: true })}
      <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
        <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #10b981;border-radius:12px;padding:14px 16px;margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
            <i class="fas fa-chart-line" style="color:#10b981;font-size:20px"></i> Coupon Progress
          </div>
          <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Write-Flow · Phase 2</div>
        </div>
        <iframe
          id="vgk4u-coupon-progress-frame"
          src="/vgk/coupon-progress"
          style="width:100%;height:calc(100vh - 200px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
          loading="lazy"
          title="Coupon Progress (VGK4U)"
        ></iframe>
      </div>
    `;
  }

  async afterRender(): Promise<void> {
    /* No-op: the embedded /vgk/coupon-progress page handles its own data fetch
       with audience=vgk4u, Zero-Default toggle gate, and full WVV verification. */
  }
}

export default VGKCouponProgressPage;
