/**
   * My Submissions — VGK4U Member Parity (Task #33 Phase 1, read-only)
   * DC Protocol: DC_MOBILE_VGK4U_PARITY_001 (May 2026)
   *
   * Mobile member page for the "My Submissions" module. Phase 1 is read-only:
   * the page reuses the existing /vgk/my-submissions responsive web view so we
   * inherit all formatting, audience scoping (?audience=vgk4u) and company
   * segregation logic from the backend without duplicating UI work.
   */

  import { PageHeader } from '../../components/PageHeader';

  export class VGKMySubmissionsPage {
  private container: HTMLElement;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.container.innerHTML = await this.render();
    await this.afterRender();
  }

    static readonly slug = 'my-submissions';
    static readonly label = 'My Submissions';
    static readonly icon = '📄';
    static readonly color = '#7c3aed';
    /** Backend endpoint (already audience-scoped). Tracked here for Phase 2 native build-out. */
    static readonly endpoint = '/api/v1/admin/my-submissions?audience=vgk4u';

    async render(): Promise<string> {
      return `
        ${PageHeader.render({ title: 'My Submissions', showBack: true })}
        <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
          <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:12px;padding:14px 16px;margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
              <span style="font-size:22px">📄</span> My Submissions
            </div>
            <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Read-Only · Phase 1</div>
          </div>
          <iframe
            id="vgk4u-my-submissions-frame"
            src="/vgk/my-submissions"
            style="width:100%;height:calc(100vh - 180px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
            loading="lazy"
            title="My Submissions (VGK4U)"
          ></iframe>
        </div>
      `;
    }

    async afterRender(): Promise<void> {
      // No-op: the embedded /vgk/my-submissions page handles its own data fetch
      // with audience=vgk4u and company-scoped backend filtering.
    }
  }

  export default VGKMySubmissionsPage;
  