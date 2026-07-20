import { apiService } from '../../services/api.service';

const DOC_CONFIG: Record<string, { label: string; icon: string; color: string; bg: string }> = {
  aadhar_front:   { label: 'Aadhaar — Front',  icon: '🪪', color: '#3b82f6', bg: 'rgba(59,130,246,.12)' },
  aadhar_back:    { label: 'Aadhaar — Back',   icon: '🪪', color: '#8b5cf6', bg: 'rgba(139,92,246,.12)' },
  pan_card:       { label: 'PAN Card',          icon: '💳', color: '#f59e0b', bg: 'rgba(245,158,11,.12)' },
  passport_photo: { label: 'Passport Photo',   icon: '📷', color: '#10b981', bg: 'rgba(16,185,129,.12)' },
};

function statusChip(status: string): string {
  if (!status || status === 'Not Submitted') return `<span style="background:#1f2937;color:#9ca3af;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700">Not Submitted</span>`;
  if (status === 'Approved') return `<span style="background:#064e3b;color:#10b981;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700">✓ Approved</span>`;
  if (status === 'Rejected') return `<span style="background:#450a0a;color:#ef4444;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700">✗ Rejected</span>`;
  return `<span style="background:#451a03;color:#f59e0b;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700">⏳ ${status}</span>`;
}

export class PartnerKYCDocuments {
  private container: HTMLElement;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.container.innerHTML = this.renderSkeleton();
    try {
      const token = localStorage.getItem('partner_token') || '';
      const companyId = localStorage.getItem('partner_company_id') || '';
      const base = apiService.getBaseUrl();
      const headers = { Authorization: `Bearer ${token}` };

      const [pRes, psRes, kycRes] = await Promise.all([
        fetch(`${base}/api/v1/partner/auth/me?company_id=${companyId}`, { headers }),
        fetch(`${base}/api/v1/partner/auth/my-partnership`, { headers }),
        fetch(`${base}/api/v1/partner/kyc/status`, { headers }),
      ]);

      if (!pRes.ok) throw new Error('Unauthorized');
      const pData = await pRes.json();
      const partner = pData.partner || pData;

      const psData = psRes.ok ? await psRes.json() : {};
      const pt = psData.partnership || {};

      const kycData = kycRes.ok ? await kycRes.json() : {};
      const kycDocs: Record<string, any> = kycData.kyc_documents || {};
      const kycStatus = psData.kyc_status || 'Not Submitted';

      this.render(partner, pt, kycDocs, kycStatus);
    } catch (e) {
      this.container.innerHTML = `
        <div style="padding:40px;text-align:center;color:#ef4444">
          <div style="font-size:32px;margin-bottom:12px">⚠️</div>
          <div style="font-size:14px">Failed to load. Please try again.</div>
          <button onclick="window.routerService?.navigate('partner-dashboard')"
            style="margin-top:16px;background:#1d4ed8;color:#fff;border:none;padding:10px 20px;border-radius:8px;font-size:13px;cursor:pointer">
            Back to Dashboard
          </button>
        </div>`;
    }
  }

  private renderSkeleton(): string {
    const bar = (w: string, h = '14px') => `<div style="height:${h};background:#1e293b;border-radius:6px;width:${w};margin-bottom:10px"></div>`;
    return `<div style="padding:20px">${bar('50%','24px')}${bar('30%')}${Array(6).fill(bar('100%','48px')).join('')}</div>`;
  }

  private render(partner: any, pt: any, kycDocs: Record<string, any>, kycStatus: string): void {
    const days = pt.days_to_expiry as number | null;
    let expiryBanner = '';
    if (pt.partner_end_date) {
      let bg = '#064e3b', color = '#10b981', icon = '✅';
      if (days !== null && days <= 0) { bg = '#450a0a'; color = '#ef4444'; icon = '🔴'; }
      else if (days !== null && days <= (pt.reminder_days_before || 90)) { bg = '#451a03'; color = '#f59e0b'; icon = '⚠️'; }
      const dLabel = days === null ? '' : days <= 0 ? `Expired ${Math.abs(days)} day(s) ago` : `${days} day(s) remaining`;
      expiryBanner = `
        <div style="background:${bg};border-radius:12px;padding:14px 16px;margin-bottom:14px;display:flex;align-items:center;gap:12px">
          <span style="font-size:22px">${icon}</span>
          <div>
            <div style="font-size:13px;font-weight:700;color:#e2e8f0">Agreement ${days !== null && days <= 0 ? 'Expired' : 'Expiry'}</div>
            <div style="font-size:12px;color:${color};margin-top:2px">${pt.partner_end_date} · ${dLabel}</div>
          </div>
        </div>`;
    }

    const docRows = Object.entries(DOC_CONFIG).map(([type, cfg]) => {
      const normalType = type.replace('aadhar_', 'aadhaar_');
      const doc = kycDocs[normalType] || kycDocs[type] || null;
      const docStatus = doc ? doc.status : 'Not Submitted';
      const canUpload = docStatus !== 'Approved';
      const uploadedAt = doc?.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString('en-IN') : '';
      const rejNote = doc?.rejection_reason ? `<div style="font-size:10px;color:#ef4444;margin-top:4px;background:#450a0a;padding:3px 8px;border-radius:6px">${doc.rejection_reason}</div>` : '';
      return `
        <div style="display:flex;align-items:center;gap:12px;padding:14px 0;border-bottom:1px solid #1e293b">
          <div style="width:40px;height:40px;border-radius:10px;background:${cfg.bg};display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0">${cfg.icon}</div>
          <div style="flex:1;min-width:0">
            <div style="font-size:13px;font-weight:600;color:#e2e8f0">${cfg.label}</div>
            <div style="font-size:11px;color:#64748b;margin-top:2px">${uploadedAt ? 'Uploaded: ' + uploadedAt : 'Not yet uploaded'}</div>
            ${rejNote}
          </div>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex-shrink:0">
            ${statusChip(docStatus)}
            ${canUpload ? `<button onclick="partnerKYCUpload('${type}')" style="background:#1d4ed8;color:#fff;border:none;padding:5px 10px;border-radius:7px;font-size:11px;font-weight:600;cursor:pointer">Upload</button>` : ''}
          </div>
        </div>`;
    }).join('');

    this.container.innerHTML = `
      <div style="padding:20px;max-width:480px;margin:0 auto">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
          <button onclick="window.routerService?.navigate('partner-dashboard')"
            style="background:none;border:none;color:#6b7280;cursor:pointer;padding:4px">
            <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>
          <div>
            <h2 style="margin:0;font-size:18px;font-weight:700;color:#111827">KYC &amp; Documents</h2>
            <div style="font-size:12px;color:#6b7280;margin-top:2px">${partner.partner_name || ''}</div>
          </div>
        </div>

        ${expiryBanner}

        <!-- Partnership Terms -->
        <div style="background:#fff;border-radius:14px;padding:18px 20px;box-shadow:0 2px 8px rgba(0,0,0,.07);margin-bottom:14px">
          <div style="font-size:12px;font-weight:700;color:#374151;margin-bottom:12px;text-transform:uppercase;letter-spacing:.5px">Partnership Terms</div>
          ${this.kv('Start Date', pt.partner_start_date || '—')}
          ${this.kv('End Date', pt.partner_end_date || '—')}
          ${this.kv('Security Deposit', pt.security_deposit > 0 ? '₹' + Number(pt.security_deposit).toLocaleString('en-IN') : '—')}
          ${this.kv('Agreement Doc', pt.agreement_submitted ? '✅ Submitted' : '⬜ Not Submitted')}
          ${this.kv('Application Doc', pt.application_submitted ? '✅ Submitted' : '⬜ Not Submitted')}
        </div>

        <!-- KYC Documents -->
        <div style="background:#fff;border-radius:14px;padding:18px 20px;box-shadow:0 2px 8px rgba(0,0,0,.07);margin-bottom:14px">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
            <div style="font-size:12px;font-weight:700;color:#374151;text-transform:uppercase;letter-spacing:.5px">KYC Documents</div>
            ${statusChip(kycStatus)}
          </div>
          <div style="font-size:11px;color:#9ca3af;margin-bottom:12px">Upload clear photos. Aadhaar (front &amp; back) and PAN card are required for verification.</div>
          ${docRows}
        </div>
      </div>

      <input type="file" id="kycUploadInput" accept="image/png,image/jpeg,application/pdf" style="display:none" onchange="handleKYCFileChange(this)">
    `;

    // Bind functions to window scope for inline onclick handlers
    (window as any).partnerKYCUpload = (type: string) => {
      (window as any)._currentKYCType = type;
      const inp = document.getElementById('kycUploadInput') as HTMLInputElement;
      if (inp) inp.click();
    };

    (window as any).handleKYCFileChange = async (input: HTMLInputElement) => {
      const file = input.files?.[0];
      const type = (window as any)._currentKYCType;
      if (!file || !type) return;
      if (file.size > 5 * 1024 * 1024) { alert('File too large. Max 5MB.'); return; }
      const token = localStorage.getItem('partner_token') || '';
      const fd = new FormData();
      fd.append('file', file);
      fd.append('document_type', type);
      try {
        const base = apiService.getBaseUrl();
        const res = await fetch(`${base}/api/v1/partner/kyc/upload`, {
          method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd
        });
        const d = await res.json();
        if (d.success || res.ok) {
          alert('Uploaded successfully! Pending staff review.');
          this.init();
        } else {
          alert('Upload failed: ' + (d.detail || d.message || 'Please try again.'));
        }
      } catch { alert('Network error. Please try again.'); }
      input.value = '';
    };
  }

  private kv(label: string, val: string): string {
    return `<div style="display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #f3f4f6">
      <span style="font-size:12px;color:#6b7280;min-width:130px;font-weight:600">${label}</span>
      <span style="font-size:13px;color:#111827;font-weight:500">${val}</span>
    </div>`;
  }
}
