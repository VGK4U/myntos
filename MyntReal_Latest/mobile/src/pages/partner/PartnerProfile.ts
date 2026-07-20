import { apiService } from '../../services/api.service';

export class PartnerProfile {
  private container: HTMLElement;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.container.innerHTML = this.renderSkeleton();
    try {
      const token = localStorage.getItem('partner_token');
      const companyId = localStorage.getItem('partner_company_id') || '';
      const base = apiService.getBaseUrl();
      const r = await fetch(`${base}/api/v1/partner/auth/me?company_id=${companyId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const d = await r.json();
      if (d.success || d.partner_code) {
        this.render(d.partner || d);
      } else {
        this.renderError('Failed to load profile');
      }
    } catch (e) {
      this.renderError('Network error. Please try again.');
    }
  }

  private renderSkeleton(): string {
    return `
      <div style="padding:20px">
        <div style="height:24px;background:#e5e7eb;border-radius:6px;width:40%;margin-bottom:20px"></div>
        ${Array(5).fill('<div style="height:16px;background:#f3f4f6;border-radius:4px;margin-bottom:12px"></div>').join('')}
      </div>`;
  }

  private render(p: any): void {
    const kv = (label: string, val: string | null) =>
      val ? `<div style="display:flex;gap:12px;padding:10px 0;border-bottom:1px solid #f3f4f6">
        <span style="font-size:12px;color:#6b7280;min-width:130px;font-weight:600">${label}</span>
        <span style="font-size:13px;color:#111827;font-weight:500">${val}</span>
      </div>` : '';

    this.container.innerHTML = `
      <div style="padding:20px;max-width:480px;margin:0 auto">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
          <button onclick="window.routerService?.navigate('partner-dashboard')"
            style="background:none;border:none;color:#6b7280;cursor:pointer;padding:4px">
            <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>
          <h2 style="margin:0;font-size:18px;font-weight:700;color:#111827">My Profile</h2>
        </div>

        <div style="background:#fff;border-radius:14px;padding:18px 20px;box-shadow:0 2px 8px rgba(0,0,0,.07);margin-bottom:16px">
          <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;padding-bottom:14px;border-bottom:2px solid #f3f4f6">
            <div style="width:52px;height:52px;border-radius:50%;background:linear-gradient(135deg,#1d4ed8,#7c3aed);display:flex;align-items:center;justify-content:center;color:#fff;font-size:20px;font-weight:800">
              ${(p.partner_name || p.contact_person || 'P').charAt(0).toUpperCase()}
            </div>
            <div>
              <div style="font-size:16px;font-weight:700;color:#111827">${p.partner_name || '—'}</div>
              <div style="font-size:12px;color:#7c3aed;font-weight:600">${p.partner_code || ''}</div>
            </div>
          </div>
          ${kv('Contact Person', p.contact_person)}
          ${kv('Phone', p.phone)}
          ${kv('Email', p.email)}
          ${kv('WhatsApp', p.whatsapp_number)}
          ${kv('Category', p.category)}
          ${kv('GST Number', p.gst_number)}
          ${kv('PAN Number', p.pan_number)}
        </div>

        <div style="background:#fff;border-radius:14px;padding:18px 20px;box-shadow:0 2px 8px rgba(0,0,0,.07);margin-bottom:16px">
          <div style="font-size:13px;font-weight:700;color:#374151;margin-bottom:12px">Address</div>
          ${kv('Address', p.address)}
          ${kv('City', p.city)}
          ${kv('State', p.state)}
          ${kv('Pincode', p.pincode)}
        </div>

        <div style="background:#fff;border-radius:14px;padding:18px 20px;box-shadow:0 2px 8px rgba(0,0,0,.07)">
          <div style="font-size:13px;font-weight:700;color:#374151;margin-bottom:12px">Account</div>
          ${kv('Status', p.login_status ? p.login_status.toUpperCase() : null)}
          ${kv('Last Login', p.last_login ? new Date(p.last_login).toLocaleString('en-IN') : null)}
          ${kv('KYC Status', p.kyc_status)}
        </div>

        <div style="margin-top:20px;text-align:center">
          <button onclick="window.routerService?.navigate('partner-dashboard')"
            style="background:#1d4ed8;color:#fff;border:none;border-radius:10px;padding:12px 28px;font-size:14px;font-weight:600;cursor:pointer">
            Back to Dashboard
          </button>
        </div>
      </div>`;
  }

  private renderError(msg: string): void {
    this.container.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:50vh;padding:24px;text-align:center">
        <svg width="48" height="48" fill="none" stroke="#ef4444" stroke-width="2" viewBox="0 0 24 24" style="margin-bottom:16px">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <p style="color:#6b7280;margin:0 0 16px">${msg}</p>
        <button onclick="window.routerService?.navigate('partner-dashboard')"
          style="background:#1d4ed8;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-size:13px;cursor:pointer">
          Back to Dashboard
        </button>
      </div>`;
  }
}
