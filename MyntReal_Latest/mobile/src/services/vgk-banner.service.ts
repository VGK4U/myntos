/**
 * VGK Banner Service — Mobile
 * DC Protocol N001: VGK4U member status banner for all mobile lead screens.
 * Shared service: AutoDialerPage, StaffLeadsPage, StaffTeamLeadsPage.
 *
 * Pattern: load(leadId, companyId, containerId) → async, non-blocking, silent-fail.
 * WhatsApp preference: localStorage key 'vgk_wa_pref' = 'business' | 'general'
 */

import { apiService } from './api.service';

const WA_PREF_KEY = 'vgk_wa_pref';
const REGARDS = '— Team VGK4U | 📞 +91 858585 2738 | 🌐 vgk4u.com/hargharsolar';

function _esc(s: string): string {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function _buildWaUrl(phone: string, message: string, pref: string): string {
  const ph = phone.replace(/\D/g, '');
  const num = ph.length === 10 ? '91' + ph : ph;
  const enc = encodeURIComponent(message);
  if (pref === 'business') {
    return `whatsapp://send?phone=${num}&text=${enc}`;
  }
  return `https://wa.me/${num}?text=${enc}`;
}

function _buildShareMsg(
  lang: string,
  name: string,
  code: string,
  pts: string,
  ref: string,
  yt: string,
  pwd?: string,
  isNew?: boolean
): string {
  if (lang === 'hindi') {
    if (isNew && pwd)
      return `🎉🎊 बधाई हो ${name} जी! 🎊🎉\n\n✨ VGK4U में आपका हार्दिक स्वागत है! ✨\n🏆 10,000 वेलकम बोनस पॉइंट्स जमा हो गए हैं!\n\n🔐 लॉगिन विवरण:\n🌐 www.vgk4u.com\n👤 Username: ${code}\n🔑 Password: ${pwd}\n💰 Points: ${pts} pts\n🔗 ${ref}\n🌞 दोस्तों के साथ शेयर करें और कमाएं!\n▶️ ${yt}\n\n${REGARDS}`;
    return `🙏 नमस्ते ${name} जी!\n\n✅ आपका VGK4U खाता:\n🌐 www.vgk4u.com\n👤 VGK ID: ${code}\n💰 ${pts} pts\n🔗 ${ref}\n\n${REGARDS}`;
  }
  if (lang === 'telugu') {
    if (isNew && pwd)
      return `🎉🎊 అభినందనలు ${name} గారు! 🎊🎉\n\n✨ VGK4U లో స్వాగతం! ✨\n🏆 10,000 వెల్కమ్ పాయింట్లు జమ అయ్యాయి!\n\n🔐 లాగిన్ వివరాలు:\n🌐 www.vgk4u.com\n👤 Username: ${code}\n🔑 Password: ${pwd}\n💰 Points: ${pts} pts\n🔗 ${ref}\n🌞 స్నేహితులతో షేర్ చేయండి, సంపాదించండి!\n▶️ ${yt}\n\n${REGARDS}`;
    return `🙏 నమస్కారం ${name} గారు!\n\n✅ మీ VGK4U వివరాలు:\n🌐 www.vgk4u.com\n👤 VGK ID: ${code}\n💰 ${pts} pts\n🔗 ${ref}\n\n${REGARDS}`;
  }
  if (isNew && pwd)
    return `🎉🎊 Congratulations ${name}! 🎊🎉\n\n✨ Welcome to VGK4U! ✨\n🏆 10,000 Welcome Bonus Points credited!\n\n🔐 Login Details:\n🌐 www.vgk4u.com\n👤 Username: ${code}\n🔑 Password: ${pwd}\n💰 Points: ${pts} pts\n🔗 ${ref}\n🌞 Share your link & start earning!\n▶️ ${yt}\n\n${REGARDS}`;
  return `👋 Hello ${name}!\n\n✅ Your VGK4U details:\n🌐 www.vgk4u.com\n👤 VGK ID: ${code}\n💰 ${pts} pts\n🔗 ${ref}\n▶️ ${yt}\n\n${REGARDS}`;
}

class VGKBannerService {
  /**
   * Load the VGK member status banner into a container div.
   * Call this AFTER the parent container has been added to the DOM.
   * Non-blocking, silent-fail. Does nothing if container not found or companyId missing.
   */
  async load(leadId: number, companyId: number | string, containerId: string): Promise<void> {
    const el = document.getElementById(containerId);
    if (!el || !leadId || !companyId) return;
    el.innerHTML = '<div style="font-size:12px;color:#9ca3af;padding:6px 4px"><span style="display:inline-block;width:12px;height:12px;border:2px solid #a78bfa;border-top-color:transparent;border-radius:50%;animation:spin 0.8s linear infinite;margin-right:6px;vertical-align:middle"></span>Checking VGK status…</div>';
    try {
      const res = await apiService.get(`/crm/leads/${leadId}/vgk-status?company_id=${companyId}`);
      const d = res.data as any;
      if (!res.success || !d) { el.innerHTML = ''; return; }
      if (d.is_vgk) {
        this._renderMember(el, d, leadId, Number(companyId));
      } else {
        this._renderNonMember(el, leadId, Number(companyId));
      }
    } catch (e) {
      el.innerHTML = '';
      console.warn('[DC-VGK-BANNER-MOB] Non-fatal:', e);
    }
  }

  private _renderMember(el: HTMLElement, member: any, leadId: number, companyId: number): void {
    const pts = (member.points_balance || 0).toLocaleString('en-IN');
    const activeLabel = member.is_active
      ? '<span style="background:#dcfce7;color:#166534;border-radius:10px;padding:2px 7px;font-size:10px;font-weight:700">✓ Active</span>'
      : '<span style="background:#fef9c3;color:#713f12;border-radius:10px;padding:2px 7px;font-size:10px;font-weight:700">⏳ Pending</span>';
    const memberJson = JSON.stringify(member).replace(/"/g, '&quot;');
    el.innerHTML = `
      <div style="background:linear-gradient(135deg,#f5f3ff,#ede9fe);border:1.5px solid #a78bfa;border-radius:10px;padding:10px 12px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
          <div style="width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#7c3aed,#4c1d95);display:flex;align-items:center;justify-content:center;flex-shrink:0">
            <span style="color:#fff;font-size:15px">🌐</span>
          </div>
          <div>
            <div style="font-weight:700;color:#4c1d95;font-size:13px">✅ VGK4U Member</div>
            <div style="font-size:11px;color:#6d28d9">
              <strong>${_esc(member.partner_code)}</strong>
              &nbsp;·&nbsp; 🪙 ${pts} pts
              &nbsp;·&nbsp; ${activeLabel}
            </div>
          </div>
        </div>
        <button
          style="background:#7c3aed;color:#fff;border:none;border-radius:8px;font-size:12px;font-weight:700;padding:6px 12px;cursor:pointer;white-space:nowrap"
          onclick="window._vgkBannerSvc.showShare(${JSON.stringify(member).replace(/'/g, "\\'").replace(/"/g, '&quot;')}, '${_esc(member.phone || '')}', false)">
          📤 Share Login
        </button>
      </div>`;
  }

  private _renderNonMember(el: HTMLElement, leadId: number, companyId: number): void {
    el.innerHTML = `
      <div style="background:linear-gradient(135deg,#fffbeb,#fef3c7);border:1.5px solid #f59e0b;border-radius:10px;padding:10px 12px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
        <div style="display:flex;align-items:center;gap:8px">
          <div style="width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#d97706,#f59e0b);display:flex;align-items:center;justify-content:center;flex-shrink:0">
            <span style="font-size:15px">➕</span>
          </div>
          <div>
            <div style="font-weight:700;color:#92400e;font-size:13px">Not a VGK4U Member</div>
            <div style="font-size:11px;color:#78350f">Register to share login &amp; earn commissions</div>
          </div>
        </div>
        <button id="vgk-mob-reg-btn-${leadId}"
          style="background:#d97706;color:#fff;border:none;border-radius:8px;font-size:12px;font-weight:700;padding:6px 14px;cursor:pointer;white-space:nowrap"
          onclick="window._vgkBannerSvc.register(${leadId}, ${companyId}, this)">
          ✚ Register as VGK
        </button>
      </div>`;
  }

  /** Called by inline onclick from non-member banner. */
  async register(leadId: number, companyId: number, btn: HTMLButtonElement): Promise<void> {
    if (!btn) return;
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '⏳ Registering…';
    try {
      const res = await apiService.post(`/crm/leads/${leadId}/register-as-vgk?company_id=${companyId}`, {});
      const d = res.data as any;
      if (d?.success) {
        // Re-render parent banner as member
        const parentEl = btn.closest('[id^="vgk-mob-"], div') as HTMLElement | null;
        const bannerWrap = btn.closest('div[style*="fffbeb"]') as HTMLElement | null;
        const container = bannerWrap?.parentElement;
        if (container) {
          this._renderMember(container, {
            partner_code: d.partner_code,
            partner_name: d.partner_name,
            phone: d.phone,
            points_balance: d.points_balance || 10000,
            is_active: false,
          }, leadId, companyId);
        }
        // Auto-open share modal for new registration
        this.showShare(d, d.phone || '', true, d.auto_password);
      } else {
        alert(d?.detail || 'Registration failed. Please try again.');
        btn.disabled = false;
        btn.innerHTML = orig;
      }
    } catch (e: any) {
      alert(e?.message || 'Registration failed. Please try again.');
      btn.disabled = false;
      btn.innerHTML = orig;
    }
  }

  /** Show the share modal. Accepts member object (from vgk-status or register response). */
  showShare(member: any, phone?: string, isNew = false, autoPwd?: string): void {
    const existingOverlay = document.getElementById('vgk-mob-share-overlay');
    if (existingOverlay) existingOverlay.remove();

    const name = member.partner_name || member.name || 'Member';
    const code = member.partner_code || '';
    const pts = (member.points_balance || 0).toLocaleString('en-IN');
    const pwd = autoPwd || member.auto_password || '';
    const ph = (phone || member.phone || '').replace(/\D/g, '').slice(-10);
    const ref = member.referral_link || `https://vgk4u.com/join/${code.toLowerCase()}`;
    const yt = member.yt_link || 'https://youtu.be/VGK4U-intro';

    const currentPref = localStorage.getItem(WA_PREF_KEY) || 'general';

    const buildMsg = (lang: string) => _buildShareMsg(lang, name, code, pts, ref, yt, pwd, isNew);

    const overlay = document.createElement('div');
    overlay.id = 'vgk-mob-share-overlay';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:999999;display:flex;align-items:flex-end;justify-content:center;padding:0';

    overlay.innerHTML = `
      <div style="background:#fff;border-radius:20px 20px 0 0;padding:20px 18px 32px;max-width:480px;width:100%;box-shadow:0 -8px 30px rgba(0,0,0,.25);max-height:88vh;overflow-y:auto">
        <div style="text-align:center;margin-bottom:14px">
          <div style="font-size:26px">${isNew ? '🎉' : '📋'}</div>
          <h5 style="font-weight:800;color:#4c1d95;margin:6px 0 4px;font-size:16px">${isNew ? 'VGK4U Account Created!' : 'VGK4U Member Details'}</h5>
        </div>

        <div style="background:#f5f3ff;border:1.5px solid #ddd6fe;border-radius:10px;padding:12px 14px;margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;margin-bottom:5px"><span style="font-size:12px;color:#6b7280">Name</span><strong style="font-size:13px">${_esc(name)}</strong></div>
          <div style="display:flex;justify-content:space-between;margin-bottom:5px"><span style="font-size:12px;color:#6b7280">VGK4U ID</span><strong style="font-size:13px;color:#7c3aed">${_esc(code)}</strong></div>
          ${pwd ? `<div style="display:flex;justify-content:space-between;margin-bottom:5px"><span style="font-size:12px;color:#6b7280">Password</span><strong style="font-size:13px;color:#059669;font-family:monospace">${_esc(pwd)}</strong></div>` : ''}
          <div style="display:flex;justify-content:space-between"><span style="font-size:12px;color:#6b7280">Points</span><strong style="font-size:13px;color:#7c3aed">🪙 ${pts}</strong></div>
        </div>

        <div style="margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <label style="font-size:12px;font-weight:700;color:#374151">Share Message</label>
            <select id="vgk-mob-lang" style="font-size:12px;border:1px solid #ddd;border-radius:6px;padding:3px 8px;background:#fff">
              <option value="english">English</option>
              <option value="hindi">हिंदी</option>
              <option value="telugu">తెలుగు</option>
            </select>
          </div>
          <textarea id="vgk-mob-share-msg" rows="8" style="width:100%;font-size:13px;border:1.5px solid #ddd6fe;border-radius:8px;padding:10px;resize:vertical;font-family:inherit;line-height:1.55;box-sizing:border-box"></textarea>
        </div>

        <!-- WhatsApp preference -->
        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:10px 12px;margin-bottom:12px">
          <div style="font-size:12px;font-weight:700;color:#166534;margin-bottom:8px">📱 WhatsApp App</div>
          <label style="display:flex;align-items:center;gap:8px;margin-bottom:6px;cursor:pointer">
            <input type="radio" name="vgk-wa-pref" value="general" ${currentPref === 'general' ? 'checked' : ''}>
            <span style="font-size:13px;color:#374151">General WhatsApp</span>
          </label>
          <label style="display:flex;align-items:center;gap:8px;margin-bottom:8px;cursor:pointer">
            <input type="radio" name="vgk-wa-pref" value="business" ${currentPref === 'business' ? 'checked' : ''}>
            <span style="font-size:13px;color:#374151">Business WhatsApp</span>
          </label>
          <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
            <input type="checkbox" id="vgk-wa-remember" checked>
            <span style="font-size:12px;color:#6b7280">Remember my choice</span>
          </label>
        </div>

        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button id="vgk-mob-copy-btn" style="flex:1;padding:11px;border:1.5px solid #7c3aed;background:#fff;color:#7c3aed;border-radius:10px;font-weight:700;font-size:13px;cursor:pointer">📋 Copy</button>
          <button id="vgk-mob-wa-btn" style="flex:1;padding:11px;background:#25D366;color:#fff;border:none;border-radius:10px;font-weight:700;font-size:13px;cursor:pointer">📤 WhatsApp</button>
          <button id="vgk-mob-close-btn" style="padding:11px 16px;background:#f3f4f6;color:#374151;border:none;border-radius:10px;font-weight:700;font-size:13px;cursor:pointer">✕</button>
        </div>
      </div>`;

    document.body.appendChild(overlay);

    const msgEl = overlay.querySelector<HTMLTextAreaElement>('#vgk-mob-share-msg')!;
    const langEl = overlay.querySelector<HTMLSelectElement>('#vgk-mob-lang')!;
    msgEl.value = buildMsg('english');

    langEl.addEventListener('change', () => {
      msgEl.value = buildMsg(langEl.value);
    });

    overlay.querySelector('#vgk-mob-copy-btn')!.addEventListener('click', () => {
      const txt = msgEl.value;
      if (navigator.clipboard?.writeText) {
        navigator.clipboard.writeText(txt).then(() => {
          const btn = overlay.querySelector<HTMLButtonElement>('#vgk-mob-copy-btn')!;
          const orig = btn.innerHTML;
          btn.innerHTML = '✅ Copied!';
          setTimeout(() => { btn.innerHTML = orig; }, 1500);
        });
      } else {
        msgEl.select();
        document.execCommand('copy');
      }
    });

    overlay.querySelector('#vgk-mob-wa-btn')!.addEventListener('click', () => {
      const selectedPref = (overlay.querySelector<HTMLInputElement>('input[name="vgk-wa-pref"]:checked')?.value) || 'general';
      const remember = (overlay.querySelector<HTMLInputElement>('#vgk-wa-remember')?.checked) ?? true;
      if (remember) localStorage.setItem(WA_PREF_KEY, selectedPref);
      const url = _buildWaUrl(ph, msgEl.value, selectedPref);
      window.open(url, '_blank');
    });

    overlay.querySelector('#vgk-mob-close-btn')!.addEventListener('click', () => overlay.remove());
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
  }
}

export const vgkBannerService = new VGKBannerService();

// Expose globally so inline onclick handlers can reach the service
(window as any)._vgkBannerSvc = vgkBannerService;
