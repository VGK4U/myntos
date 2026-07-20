/**
 * VGK4U Member Hub (Task #33 Phase 1 — Read-Only Modules)
 * DC Protocol: DC_MOBILE_VGK4U_PARITY_001 (May 2026)
 *
 * Lightweight launcher that opens each VGK4U member page in the in-app
 * web view. The web pages already do all data fetching with ?audience=vgk4u.
 */

import { PageHeader } from '../../components/PageHeader';
import { routerService } from '../../services/router.service';

const NATIVE_ROUTES: Record<string, string> = {
  'bonanza-rewards':  'vgk-bonanza-rewards',
  'points-balance':   'vgk-points-balance',
};

interface ParityModule {
  slug: string;
  label: string;
  icon: string;
  color: string;
}

const MODULES: ParityModule[] = [
  { slug: 'birthdays',          label: 'Birthdays',         icon: '🎂', color: '#0ea5e9' },
  { slug: 'top-earners',        label: 'Top Earners',       icon: '🏆', color: '#f59e0b' },
  { slug: 'awards',             label: 'My Awards',         icon: '🥇', color: '#a21caf' },
  { slug: 'daywise-income',     label: 'Daywise Income',    icon: '📅', color: '#059669' },
  { slug: 'income-types',       label: 'Income Types',      icon: '📊', color: '#2563eb' },
  { slug: 'direct-summary',     label: 'Direct (L1)',       icon: '①',  color: '#475569' },
  { slug: 'matching-summary',   label: 'Matching (L2)',     icon: '②',  color: '#475569' },
  { slug: 'guru-summary',       label: 'Senior (L3)',         icon: '③',  color: '#475569' },
  { slug: 'ved-summary',        label: 'VED (L5)',          icon: '⑤',  color: '#475569' },
  { slug: 'ev-benefits',        label: 'EV Benefits',       icon: '⚡', color: '#16a34a' },
  { slug: 'ev-discount',        label: 'EV Discount',       icon: '🏷️', color: '#16a34a' },
  { slug: 'franchise-earnings', label: 'Franchise',         icon: '🏪', color: '#ea580c' },
  { slug: 'insurance',          label: 'Insurance',         icon: '🛡️', color: '#4f46e5' },
  { slug: 'training',           label: 'Training',          icon: '🎓', color: '#db2777' },
  { slug: 'coupon-benefits',    label: 'Coupon Benefits',   icon: '🎟️', color: '#e11d48' },
  { slug: 'my-submissions',     label: 'My Submissions',    icon: '📄', color: '#7c3aed' },
  { slug: 'bonanza-rewards',    label: 'Bonanza Rewards',   icon: '🏆', color: '#7c3aed' },
  { slug: 'points-balance',     label: 'Points Balance',    icon: '⭐', color: '#5b21b6' },
];

export class VGKMemberHubPage {
  private container: HTMLElement;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.container.innerHTML = await this.render();
    await this.afterRender();
  }

  async render(): Promise<string> {
    const cards = MODULES.map(m => `
      <div class="vgk4u-card" data-slug="${m.slug}" style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid ${m.color};border-radius:12px;padding:14px 16px;margin-bottom:10px;display:flex;align-items:center;gap:12px;cursor:pointer">
        <div style="font-size:24px;width:34px;text-align:center">${m.icon}</div>
        <div style="flex:1;font-weight:700;color:#0f172a;font-size:14px">${m.label}</div>
        <div style="color:#94a3b8">›</div>
      </div>
    `).join('');

    return `
      ${PageHeader.render({ title: 'VGK4U Member Hub', showBack: true })}
      <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
        <div style="background:#e0f2fe;border:1px solid #bae6fd;border-radius:10px;padding:10px 12px;font-size:12px;color:#0c4a6e;margin-bottom:14px">
          <strong>Phase 1 · Read-Only.</strong> All data is fetched via the existing endpoints with <code>?audience=vgk4u</code>.
        </div>

        <!-- DC Protocol AI_KB_COMPANY_001 — Mobile parity: verified registration block -->
        <div style="background:#f0f4ff;border:1.5px solid #c7d7fd;border-radius:12px;padding:14px 12px;margin-bottom:14px">
          <div style="font-size:13px;font-weight:700;color:#1e3a8a;margin-bottom:10px;display:flex;align-items:center;gap:6px">
            🏛️ Mynt Real LLP — Verified Registrations
          </div>
          <div style="display:flex;flex-direction:column;gap:6px">
            <div style="background:#fff;border-radius:8px;padding:10px 12px;display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:11px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.05em">MCA (LLPIN)</span>
              <span style="font-size:13px;font-weight:700;color:#111827">ACT-5518 · Active</span>
            </div>
            <div style="background:#fff;border-radius:8px;padding:10px 12px;display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:11px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.05em">GSTIN</span>
              <span style="font-size:13px;font-weight:700;color:#111827">37ACFM9S86Q1Z0</span>
            </div>
            <div style="background:#fff;border-radius:8px;padding:10px 12px;display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:11px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.05em">ISO</span>
              <span style="font-size:13px;font-weight:700;color:#111827">9001:2015 · E20260346985</span>
            </div>
          </div>
          <div style="font-size:10px;color:#6b7280;margin-top:8px;text-align:center">
            Verify: mca.gov.in (ACT-5518) · gst.gov.in (37ACFM9S86Q1Z0)
          </div>
        </div>

        ${cards}
      </div>
    `;
  }

  async afterRender(): Promise<void> {
    document.querySelectorAll<HTMLElement>('.vgk4u-card').forEach(el => {
      el.addEventListener('click', () => {
        const slug = el.getAttribute('data-slug');
        if (!slug) return;
        const nativeRoute = NATIVE_ROUTES[slug];
        if (nativeRoute) {
          routerService.navigate(nativeRoute as Parameters<typeof routerService.navigate>[0]);
        } else {
          window.location.href = `/vgk/${slug}`;
        }
      });
    });
  }
}

export default VGKMemberHubPage;
