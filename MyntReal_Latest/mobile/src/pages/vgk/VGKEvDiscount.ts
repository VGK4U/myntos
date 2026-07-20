/**
   * EV Discount — VGK4U Member Parity (Task #33 Phase 1, read-only)
   * DC Protocol: DC_MOBILE_VGK4U_PARITY_001 (May 2026)
   *
   * Mobile member page for the "EV Discount" module. Phase 1 is read-only:
   * the page reuses the existing /vgk/ev-discount responsive web view so we
   * inherit all formatting, audience scoping (?audience=vgk4u) and company
   * segregation logic from the backend without duplicating UI work.
   */

  import { PageHeader } from '../../components/PageHeader';

  export class VGKEvDiscountPage {
  private container: HTMLElement;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.container.innerHTML = await this.render();
    await this.afterRender();
  }

    static readonly slug = 'ev-discount';
    static readonly label = 'EV Discount';
    static readonly icon = '🏷️';
    static readonly color = '#16a34a';
    /** Backend endpoint (already audience-scoped). Tracked here for Phase 2 native build-out. */
    static readonly endpoint = '/api/v1/ev-discount/admin/ev-discount-stats?audience=vgk4u';

    async render(): Promise<string> {
      return `
        ${PageHeader.render({ title: 'EV Discount', showBack: true })}
        <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
          <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #16a34a;border-radius:12px;padding:14px 16px;margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
              <span style="font-size:22px">🏷️</span> EV Discount
            </div>
            <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Read-Only · Phase 1</div>
          </div>
          <iframe
            id="vgk4u-ev-discount-frame"
            src="/vgk/ev-discount"
            style="width:100%;height:calc(100vh - 180px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
            loading="lazy"
            title="EV Discount (VGK4U)"
          ></iframe>
        </div>
      `;
    }

    async afterRender(): Promise<void> {
      // No-op: the embedded /vgk/ev-discount page handles its own data fetch
      // with audience=vgk4u and company-scoped backend filtering.
    }
  }

  export default VGKEvDiscountPage;
  