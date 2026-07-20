/**
 * VGK My Registrations Page — DC-VGK-STAFF-REG-001
 * Shows Channel Partners registered by the logged-in VGK member.
 * [DC-PHONE-OTP-001] Registration form with WhatsApp OTP phone verification.
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface VGKMember {
  id: number;
  partner_code: string;
  partner_name: string;
  phone: string;
  is_active: boolean;
  vgk_role: string;
  created_at: string;
  vgk_activated_at: string | null;
}

interface RegData {
  partner_code: string;
  partner_name: string;
  phone: string;
  password: string;
}

export class VGKMyRegistrations {
  private container: HTMLElement;
  private members: VGKMember[] = [];
  private total: number = 0;
  private thisMonth: number = 0;
  private loading: boolean = true;
  private page: number = 1;
  private readonly pageSize: number = 25;

  private regOtpSent: boolean = false;
  private regPhoneVerifiedToken: string = '';
  private lastRegData: RegData | null = null;
  private refLookupTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    this.attachEvents();
    await this.loadData();
  }

  private async loadData(): Promise<void> {
    this.loading = true;
    this.updateList();
    try {
      const url = `/vgk/my-registrations?page=${this.page}&page_size=${this.pageSize}`;
      const res = await apiService.get<any>(url);
      if (res.success) {
        this.members   = res.data || [];
        this.total     = res.total || 0;
        this.thisMonth = res.this_month || 0;
      } else {
        this.members = [];
      }
    } catch (e) {
      console.error('[VGKMyRegistrations] load error:', e);
      this.members = [];
    } finally {
      this.loading = false;
      this.updateList();
      this.updateStats();
    }
  }

  private fmtDate(iso: string | null): string {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' });
  }

  private render(): void {
    const stored = JSON.parse(localStorage.getItem('vgk_partner') || '{}');
    const myCode = stored.partner_code || '';

    this.container.innerHTML = `
      <div style="background:#f8f5ff;min-height:100vh;padding-bottom:80px">
        ${PageHeader.render({ title: 'My VGK Registrations', showBack: true })}

        <!-- Stats + Register button strip -->
        <div style="display:flex;gap:10px;padding:12px 16px;flex-wrap:wrap;align-items:stretch" id="myRegStats">
          <div style="flex:1;min-width:90px;background:white;border-radius:10px;padding:12px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.07)">
            <div style="font-size:10px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:4px">Total</div>
            <div style="font-size:22px;font-weight:800;color:#7c3aed" id="statTotal">—</div>
          </div>
          <div style="flex:1;min-width:90px;background:white;border-radius:10px;padding:12px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.07)">
            <div style="font-size:10px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:4px">This Month</div>
            <div style="font-size:22px;font-weight:800;color:#059669" id="statThisMonth">—</div>
          </div>
          <button id="regOpenBtn" style="flex:0 0 auto;background:linear-gradient(135deg,#4c1d95,#7c3aed);color:#fff;border:none;border-radius:10px;padding:12px 16px;font-size:13px;font-weight:700;cursor:pointer;display:flex;align-items:center;gap:6px;box-shadow:0 2px 8px rgba(124,58,237,.35)">
            <i class="fas fa-user-plus"></i> Register
          </button>
        </div>

        <!-- Registration form card (hidden by default) -->
        <div id="regFormCard" style="display:none;margin:0 12px 16px;background:white;border-radius:14px;box-shadow:0 2px 12px rgba(124,58,237,.12);border:1.5px solid #ede9fe;overflow:hidden">
          <div style="background:linear-gradient(135deg,#4c1d95,#7c3aed);padding:14px 16px;display:flex;justify-content:space-between;align-items:center">
            <div style="font-size:14px;font-weight:800;color:#fff"><i class="fas fa-user-plus me-2"></i>Register a New Channel Partner</div>
            <button id="regCloseBtn" style="background:rgba(255,255,255,.2);border:none;color:#fff;border-radius:8px;padding:4px 10px;font-size:12px;cursor:pointer">✕ Close</button>
          </div>
          <div style="padding:16px">
            <p style="font-size:12.5px;color:#6b7280;margin:0 0 14px">Refer someone to join VGK. They will be placed under you as referrer.</p>

            <!-- Success panel -->
            <div id="regSuccess" style="display:none;background:#f0fdf4;border:1.5px solid #22c55e;border-radius:12px;padding:18px;text-align:center;margin-bottom:12px">
              <i class="fas fa-check-circle" style="font-size:28px;color:#22c55e"></i>
              <p style="font-weight:700;margin:8px 0 4px;color:#166534">Channel Partner Registered!</p>
              <div style="font-size:20px;font-weight:800;color:#7c3aed;letter-spacing:1px" id="regNewId"></div>
              <p style="font-size:12px;color:#6b7280;margin-top:6px">Account is <strong>pending activation</strong>. Pay ₹5,000 to activate and receive <strong>50,000 bonus points</strong>.</p>
              <div style="display:flex;flex-direction:column;gap:8px;margin-top:12px">
                <button id="regShareBtn" style="background:#25D366;border:none;color:#fff;font-weight:700;padding:10px 18px;border-radius:9px;cursor:pointer;font-size:13px;display:flex;align-items:center;justify-content:center;gap:6px">
                  <i class="fab fa-whatsapp"></i>Share Login Details via WhatsApp
                </button>
                <button id="regAnotherBtn" style="background:#7c3aed;border:none;color:#fff;font-weight:700;padding:9px 22px;border-radius:9px;cursor:pointer;font-size:13px"><i class="fas fa-plus me-1"></i>Add Another</button>
              </div>
            </div>

            <!-- Error -->
            <div id="regError" style="display:none;background:#fef2f2;border:1.5px solid #fca5a5;border-radius:9px;padding:10px 14px;font-size:12.5px;color:#dc2626;margin-bottom:12px"></div>

            <!-- Form -->
            <form id="regForm" novalidate autocomplete="off">
              <!-- Name -->
              <div style="margin-bottom:12px">
                <label style="font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;display:block;margin-bottom:5px">Title &amp; Name <span style="color:#e11d48">*</span></label>
                <div style="display:flex;gap:6px;flex-wrap:wrap">
                  <select id="regTitle" style="flex:0 0 80px;padding:8px 6px;border:1.5px solid #e5e7eb;border-radius:8px;font-size:13px">
                    <option value="">Title</option>
                    <option value="Mr.">Mr.</option>
                    <option value="Ms.">Ms.</option>
                    <option value="Mrs.">Mrs.</option>
                  </select>
                  <input type="text" id="regFirstName" placeholder="First name" required style="flex:1;min-width:90px;padding:8px 10px;border:1.5px solid #e5e7eb;border-radius:8px;font-size:13px">
                  <input type="text" id="regLastName"  placeholder="Last name"  required style="flex:1;min-width:90px;padding:8px 10px;border:1.5px solid #e5e7eb;border-radius:8px;font-size:13px">
                </div>
              </div>

              <!-- Gender -->
              <div style="margin-bottom:12px">
                <label style="font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;display:block;margin-bottom:5px">Gender <span style="font-size:10px;color:#9ca3af;text-transform:none">(optional)</span></label>
                <select id="regGender" style="width:100%;padding:8px 10px;border:1.5px solid #e5e7eb;border-radius:8px;font-size:13px">
                  <option value="">-- Select --</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <!-- Phone + OTP (DC-PHONE-OTP-001) -->
              <div style="margin-bottom:12px">
                <label style="font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;display:block;margin-bottom:5px">Phone <span style="color:#e11d48">*</span></label>
                <div style="display:flex;gap:6px">
                  <input type="tel" id="regPhone" placeholder="10-digit mobile" required maxlength="10"
                    style="flex:1;padding:8px 10px;border:1.5px solid #e5e7eb;border-radius:8px;font-size:13px">
                  <button type="button" id="regSendOtpBtn"
                    style="background:#7c3aed;color:#fff;border:none;padding:8px 12px;border-radius:8px;font-size:12px;font-weight:700;white-space:nowrap;cursor:pointer;flex-shrink:0">
                    Send OTP
                  </button>
                </div>
                <div style="font-size:11px;color:#f87171;margin-top:4px"><i class="fas fa-shield-alt" style="margin-right:3px"></i>WhatsApp OTP verification required.</div>

                <!-- OTP input block (hidden until Send OTP clicked) -->
                <div id="regOtpBlock" style="display:none;margin-top:10px;background:#f0fdf4;border:1.5px solid #86efac;border-radius:9px;padding:10px 12px">
                  <div style="font-size:12px;color:#166534;margin-bottom:7px"><i class="fab fa-whatsapp" style="margin-right:4px"></i>OTP sent to WhatsApp. Enter below:</div>
                  <div style="display:flex;gap:6px">
                    <input type="text" id="regOtpInput" maxlength="6" placeholder="6-digit OTP"
                      style="flex:1;padding:8px 10px;border-radius:8px;border:1.5px solid #86efac;font-size:16px;font-weight:700;letter-spacing:4px;text-align:center">
                    <button type="button" id="regVerifyBtn"
                      style="background:#16a34a;color:#fff;border:none;padding:8px 12px;border-radius:8px;font-size:12px;font-weight:700;cursor:pointer;flex-shrink:0">
                      Verify
                    </button>
                  </div>
                  <div style="margin-top:5px;font-size:11px;color:#6b7280">
                    Didn't receive? <span id="regResendLink" style="color:#7c3aed;cursor:pointer;text-decoration:underline">Resend OTP</span>
                  </div>
                </div>
                <div id="regOtpVerifiedBadge" style="display:none;margin-top:8px;background:#f0fdf4;border:1.5px solid #16a34a;border-radius:8px;padding:7px 10px;color:#166534;font-size:12px;font-weight:700">
                  <i class="fas fa-check-circle" style="margin-right:4px"></i>Phone verified ✓
                </div>
              </div>

              <!-- Email -->
              <div style="margin-bottom:12px">
                <label style="font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;display:block;margin-bottom:5px">Email <span style="font-size:10px;color:#9ca3af;text-transform:none">(optional)</span></label>
                <input type="email" id="regEmail" placeholder="email@example.com"
                  style="width:100%;padding:8px 10px;border:1.5px solid #e5e7eb;border-radius:8px;font-size:13px;box-sizing:border-box">
              </div>

              <!-- Password -->
              <div style="margin-bottom:12px">
                <label style="font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;display:block;margin-bottom:5px">Password <span style="color:#e11d48">*</span></label>
                <input type="text" id="regPassword" placeholder="Set initial password" required
                  style="width:100%;padding:8px 10px;border:1.5px solid #e5e7eb;border-radius:8px;font-size:13px;box-sizing:border-box">
              </div>

              <!-- Referrer -->
              <div style="margin-bottom:16px">
                <label style="font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;display:block;margin-bottom:5px">Referrer Channel Partner ID</label>
                <input type="text" id="regReferrer" placeholder="Pre-filled with your ID" value="${myCode}"
                  style="width:100%;padding:8px 10px;border:1.5px solid #e5e7eb;border-radius:8px;font-size:13px;box-sizing:border-box" autocomplete="off">
                <div id="regReferrerName" style="font-size:12px;margin-top:5px;min-height:16px"></div>
                <div style="font-size:11px;color:#9ca3af;margin-top:2px">By default you are the referrer. Change to place under someone else.</div>
              </div>

              <!-- Submit -->
              <button type="submit" id="regSubmitBtn"
                style="width:100%;background:linear-gradient(135deg,#4c1d95,#7c3aed);border:none;color:#fff;font-weight:700;font-size:14px;padding:12px;border-radius:10px;cursor:pointer">
                <span id="regSubmitText"><i class="fas fa-user-plus" style="margin-right:6px"></i>Register Channel Partner</span>
                <span id="regSubmitSpinner" style="display:none"><i class="fas fa-spinner fa-spin" style="margin-right:6px"></i>Registering…</span>
              </button>
            </form>
          </div>
        </div>

        <!-- List -->
        <div style="padding:0 12px" id="myRegList">
          <div style="text-align:center;padding:40px;color:#9ca3af">
            <i class="fas fa-spinner fa-spin" style="font-size:22px"></i>
          </div>
        </div>
      </div>`;
    PageHeader.attachListeners({ title: 'My VGK Registrations', showBack: true });
  }

  private attachEvents(): void {
    this.container.querySelector('#regOpenBtn')?.addEventListener('click', () => {
      const card = this.container.querySelector('#regFormCard') as HTMLElement;
      if (card) { card.style.display = 'block'; card.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    });
    this.container.querySelector('#regCloseBtn')?.addEventListener('click', () => {
      this.closeRegForm();
    });
    this.container.querySelector('#regAnotherBtn')?.addEventListener('click', () => {
      this.resetRegForm();
    });
    this.container.querySelector('#regShareBtn')?.addEventListener('click', () => {
      if (this.lastRegData) this.showShareOverlay(this.lastRegData);
    });

    this.container.querySelector('#regReferrer')?.addEventListener('input', () => this.lookupReferrer());
    if ((this.container.querySelector('#regReferrer') as HTMLInputElement)?.value) this.lookupReferrer();
    this.container.querySelector('#regPhone')?.addEventListener('input', () => this.resetOtpState());
    this.container.querySelector('#regSendOtpBtn')?.addEventListener('click', () => this.sendOTP());
    this.container.querySelector('#regVerifyBtn')?.addEventListener('click', () => this.verifyOTP());
    this.container.querySelector('#regResendLink')?.addEventListener('click', () => this.sendOTP());

    this.container.querySelector('#regForm')?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.submitRegistration();
    });
  }

  private lookupReferrer(): void {
    const refEl = this.container.querySelector('#regReferrer') as HTMLInputElement | null;
    const outEl = this.container.querySelector('#regReferrerName') as HTMLElement | null;
    if (!outEl) return;
    const code = (refEl?.value || '').trim().toUpperCase();
    if (this.refLookupTimer) clearTimeout(this.refLookupTimer);
    if (code.length < 3) { outEl.innerHTML = ''; return; }
    outEl.innerHTML = '<span style="color:#9ca3af"><i class="fas fa-spinner fa-spin" style="margin-right:4px"></i>Looking up…</span>';
    this.refLookupTimer = setTimeout(async () => {
      try {
        const res = await apiService.get<any>(`/vgk/public/member-lookup?q=${encodeURIComponent(code)}`);
        if (res.results && res.results.length > 0) {
          const match = res.results.find((x: any) => x.partner_code.toUpperCase() === code) || res.results[0];
          outEl.innerHTML = `<span style="color:#16a34a;font-weight:700"><i class="fas fa-check-circle" style="margin-right:4px"></i>${match.partner_name} <span style="color:#9ca3af;font-weight:400">(${match.partner_code})</span></span>`;
        } else {
          outEl.innerHTML = '<span style="color:#dc2626"><i class="fas fa-times-circle" style="margin-right:4px"></i>VGK ID not found</span>';
        }
      } catch (_) {
        outEl.innerHTML = '<span style="color:#dc2626"><i class="fas fa-times-circle" style="margin-right:4px"></i>VGK ID not found</span>';
      }
    }, 500);
  }

  private resetOtpState(): void {
    this.regOtpSent = false;
    this.regPhoneVerifiedToken = '';
    const el = (id: string) => this.container.querySelector(`#${id}`) as HTMLElement | null;
    const inp = this.container.querySelector('#regOtpInput') as HTMLInputElement | null;
    const btn = this.container.querySelector('#regSendOtpBtn') as HTMLButtonElement | null;
    if (el('regOtpBlock'))       el('regOtpBlock')!.style.display = 'none';
    if (el('regOtpVerifiedBadge')) el('regOtpVerifiedBadge')!.style.display = 'none';
    if (inp) inp.value = '';
    if (btn) btn.textContent = 'Send OTP';
  }

  private async sendOTP(): Promise<void> {
    const phoneEl  = this.container.querySelector('#regPhone') as HTMLInputElement;
    const errEl    = this.container.querySelector('#regError') as HTMLElement;
    const phone    = (phoneEl?.value || '').trim();
    if (!phone || !/^\d{10}$/.test(phone)) {
      errEl.textContent = 'Please enter a valid 10-digit phone number before sending OTP.';
      errEl.style.display = 'block'; return;
    }
    errEl.style.display = 'none';
    const btn = this.container.querySelector('#regSendOtpBtn') as HTMLButtonElement;
    btn.disabled = true; btn.textContent = 'Sending…';
    try {
      const res = await apiService.post<any>('/vgk/auth/signup/send-otp', { phone });
      if (res.success) {
        this.regOtpSent = true;
        const otpBlock = this.container.querySelector('#regOtpBlock') as HTMLElement;
        const badge    = this.container.querySelector('#regOtpVerifiedBadge') as HTMLElement;
        const otpInp   = this.container.querySelector('#regOtpInput') as HTMLInputElement;
        if (otpBlock) otpBlock.style.display = 'block';
        if (badge)    badge.style.display = 'none';
        if (otpInp)   { otpInp.value = ''; otpInp.focus(); }
        this.regPhoneVerifiedToken = '';
        btn.textContent = 'Resend OTP';
      } else {
        errEl.textContent = res.message || 'Failed to send OTP. Please try again.';
        errEl.style.display = 'block';
        btn.textContent = 'Send OTP';
      }
    } catch (e: any) {
      errEl.textContent = e?.detail || e?.message || 'Failed to send OTP. Please try again.';
      errEl.style.display = 'block';
      btn.textContent = 'Send OTP';
    } finally { btn.disabled = false; }
  }

  private async verifyOTP(): Promise<void> {
    const phoneEl  = this.container.querySelector('#regPhone') as HTMLInputElement;
    const otpEl    = this.container.querySelector('#regOtpInput') as HTMLInputElement;
    const errEl    = this.container.querySelector('#regError') as HTMLElement;
    const phone    = (phoneEl?.value || '').trim();
    const otpCode  = (otpEl?.value || '').trim();
    if (!otpCode || otpCode.length !== 6) {
      errEl.textContent = 'Please enter the 6-digit OTP from WhatsApp.';
      errEl.style.display = 'block'; return;
    }
    errEl.style.display = 'none';
    const btn = this.container.querySelector('#regVerifyBtn') as HTMLButtonElement;
    btn.disabled = true; btn.textContent = 'Verifying…';
    try {
      const res = await apiService.post<any>('/vgk/auth/signup/verify-otp', { phone, otp_code: otpCode });
      if (res.success && res.phone_verified_token) {
        this.regPhoneVerifiedToken = res.phone_verified_token;
        const otpBlock = this.container.querySelector('#regOtpBlock') as HTMLElement;
        const badge    = this.container.querySelector('#regOtpVerifiedBadge') as HTMLElement;
        if (otpBlock) otpBlock.style.display = 'none';
        if (badge)    badge.style.display = 'block';
      } else {
        errEl.textContent = res.message || 'Invalid OTP. Please try again.';
        errEl.style.display = 'block';
      }
    } catch (e: any) {
      errEl.textContent = e?.detail || e?.message || 'Invalid OTP. Please try again.';
      errEl.style.display = 'block';
    } finally { btn.disabled = false; btn.textContent = 'Verify'; }
  }

  private async submitRegistration(): Promise<void> {
    const g = (id: string) => (this.container.querySelector(`#${id}`) as HTMLInputElement | null)?.value?.trim() || '';
    const errEl = this.container.querySelector('#regError') as HTMLElement;
    errEl.style.display = 'none';

    const firstName = g('regFirstName');
    const lastName  = g('regLastName');
    const phone     = g('regPhone');
    const password  = g('regPassword');
    const title     = g('regTitle');
    const gender    = g('regGender');
    const email     = g('regEmail');
    const referrer  = g('regReferrer');
    const name      = [title, firstName, lastName].filter(Boolean).join(' ');

    if (!firstName || !lastName) { errEl.textContent = 'Please enter both first name and last name.'; errEl.style.display = 'block'; return; }
    if (!phone || phone.length < 10) { errEl.textContent = 'Please enter a valid 10-digit phone number.'; errEl.style.display = 'block'; return; }
    if (!this.regPhoneVerifiedToken) {
      errEl.textContent = 'Phone verification required — enter the phone number, tap "Send OTP", enter the code from WhatsApp, then tap "Verify".';
      errEl.style.display = 'block'; return;
    }
    if (!password || password.length < 6) { errEl.textContent = 'Password must be at least 6 characters.'; errEl.style.display = 'block'; return; }

    const submitBtn = this.container.querySelector('#regSubmitBtn') as HTMLButtonElement;
    const submitText = this.container.querySelector('#regSubmitText') as HTMLElement;
    const submitSpinner = this.container.querySelector('#regSubmitSpinner') as HTMLElement;
    submitBtn.disabled = true;
    submitText.style.display = 'none';
    submitSpinner.style.display = '';

    try {
      const payload: any = {
        partner_name: name, phone, password,
        name_title: title || null,
        first_name: firstName || null,
        last_name:  lastName  || null,
        gender:     gender    || null,
        phone_verified_token: this.regPhoneVerifiedToken,
      };
      if (email)    payload.email = email;
      if (referrer) payload.referrer_code = referrer;

      const res = await apiService.post<any>('/vgk/auth/signup', payload);
      if (res.success) {
        const form    = this.container.querySelector('#regForm') as HTMLElement;
        const success = this.container.querySelector('#regSuccess') as HTMLElement;
        const newId   = this.container.querySelector('#regNewId') as HTMLElement;
        if (form)    form.style.display = 'none';
        if (newId)   newId.textContent  = res.partner_code || '';
        if (success) success.style.display = 'block';

        this.lastRegData = { partner_code: res.partner_code || '', partner_name: name, phone, password };
        this.showShareOverlay(this.lastRegData);

        await this.loadData();
      } else {
        errEl.textContent = res.message || 'Registration failed. Please try again.';
        errEl.style.display = 'block';
      }
    } catch (e: any) {
      errEl.textContent = e?.detail || e?.message || 'Registration failed. Please try again.';
      errEl.style.display = 'block';
    } finally {
      submitBtn.disabled = false;
      submitText.style.display = '';
      submitSpinner.style.display = 'none';
    }
  }

  private buildShareMsg(lang: string, d: RegData): string {
    const code = d.partner_code;
    const name = d.partner_name;
    const pwd  = d.password;
    const ref  = `https://vgk4u.com/vgk/login?tab=signup&ref=${encodeURIComponent(code)}`;
    const yt   = 'https://www.youtube.com/@VGK4YOU';
    if (lang === 'hindi') return (
      `🎉 बधाई हो ${name} जी! 🎉\n\nVGK4U में आपका स्वागत है! आपके खाते में कुल 15,000 रिवॉर्ड पॉइंट्स जमा हो गए हैं:\n🎁 10,000 पॉइंट्स — वेलकम बोनस\n🤝 5,000 पॉइंट्स — रेफरल बोनस\n\nइन पॉइंट्स को इन सेवाओं पर उपयोग करें:\n⚡ Solar Solutions\n🛵 EV (इलेक्ट्रिक वाहन)\n🛡 Insurance\n🏡 Real Estate और अन्य VGK सेवाएं\n\nलॉगिन विवरण:\n🌐 Website: www.vgk4u.com\n👤 Username: ${code}\n🔐 Password: ${pwd}\n🔗 आपका Referral Link:\n${ref}\n\n▶️ पूरी कमाई प्रक्रिया समझने के लिए हमारा YouTube channel देखें:\n${yt}\n\n👉 नियमित अपडेट और training के लिए subscribe करें।\n\nअपना dashboard explore करें और अपने rewards का पूरा लाभ उठाएं!`
    );
    if (lang === 'telugu') return (
      `🎉 అభినందనలు ${name} గారు! 🎉\n\nVGK4U లో స్వాగతం! మీ ఖాతాలో మొత్తం 15,000 రివార్డ్ పాయింట్లు జమ అయ్యాయి:\n🎁 10,000 పాయింట్లు — వెల్కమ్ బోనస్\n🤝 5,000 పాయింట్లు — రెఫెరల్ బోనస్\n\nఈ పాయింట్లను ఉపయోగించవచ్చు:\n⚡ Solar Solutions\n🛵 EV (ఎలక్ట్రిక్ వాహనాలు)\n🛡 Insurance\n🏡 Real Estate మరియు ఇతర VGK సేవలు\n\nలాగిన్ వివరాలు:\n🌐 Website: www.vgk4u.com\n👤 Username: ${code}\n🔐 Password: ${pwd}\n🔗 మీ Referral Link:\n${ref}\n\n▶️ పూర్తి ఆదాయ ప్రక్రియ తెలుసుకోవడానికి మా YouTube చానల్ చూడండి:\n${yt}\n\n👉 రెగ్యులర్ అప్డేట్స్, ట్రైనింగ్ కోసం సబ్స్క్రైబ్ చేయండి.\n\nమీ డాష్బోర్డ్ అన్వేషించండి మరియు మీ రివార్డ్స్ ను సద్వినియోగం చేసుకోండి!`
    );
    if (lang === 'tamil') return (
      `🎉 வாழ்த்துகள் ${name}! 🎉\n\nVGK4U-வில் உங்களை வரவேற்கிறோம்! உங்கள் கணக்கில் மொத்தம் 15,000 வெகுமதி புள்ளிகள் சேர்க்கப்பட்டுள்ளன:\n🎁 10,000 புள்ளிகள் — வரவேற்பு போனஸ்\n🤝 5,000 புள்ளிகள் — பரிந்துரை போனஸ்\n\nஇந்த புள்ளிகளை பயன்படுத்தலாம்:\n⚡ Solar Solutions\n🛵 EV (மின்சார வாகனங்கள்)\n🛡 Insurance\n🏡 Real Estate மற்றும் மற்ற VGK சேவைகள்\n\nஉள்நுழைவு விவரங்கள்:\n🌐 Website: www.vgk4u.com\n👤 Username: ${code}\n🔐 Password: ${pwd}\n🔗 உங்கள் Referral Link:\n${ref}\n\n▶️ முழு வருமான செயல்முறையை புரிந்துகொள்ள எங்கள் YouTube சேனலை பாருங்கள்:\n${yt}\n\n👉 தொடர் புதுப்பிப்புகள் மற்றும் பயிற்சிக்கு subscribe செய்யுங்கள்.\n\nஉங்கள் dashboard-ஐ ஆராய்ந்து உங்கள் வெகுமதிகளை சரியாக பயன்படுத்துங்கள்!`
    );
    if (lang === 'kannada') return (
      `🎉 ಅಭಿನಂದನೆಗಳು ${name}! 🎉\n\nVGK4U ಗೆ ಸ್ವಾಗತ! ನಿಮ್ಮ ಖಾತೆಗೆ ಒಟ್ಟು 15,000 ರಿವಾರ್ಡ್ ಪಾಯಿಂಟ್‌ಗಳು ಸೇರ್ಪಡೆಯಾಗಿವೆ:\n🎁 10,000 ಪಾಯಿಂಟ್‌ಗಳು — ವೆಲ್ಕಮ್ ಬೋನಸ್\n🤝 5,000 ಪಾಯಿಂಟ್‌ಗಳು — ರೆಫೆರಲ್ ಬೋನಸ್\n\nಈ ಪಾಯಿಂಟ್‌ಗಳನ್ನು ಬಳಸಬಹುದು:\n⚡ Solar Solutions\n🛵 EV (ಎಲೆಕ್ಟ್ರಿಕ್ ವಾಹನಗಳು)\n🛡 Insurance\n🏡 Real Estate ಮತ್ತು ಇತರ VGK ಸೇವೆಗಳು\n\nಲಾಗಿನ್ ವಿವರಗಳು:\n🌐 Website: www.vgk4u.com\n👤 Username: ${code}\n🔐 Password: ${pwd}\n🔗 ನಿಮ್ಮ Referral Link:\n${ref}\n\n▶️ ಸಂಪೂರ್ಣ ಗಳಿಕೆ ಪ್ರಕ್ರಿಯೆ ಅರ್ಥಮಾಡಿಕೊಳ್ಳಲು ನಮ್ಮ YouTube ಚಾನೆಲ್ ನೋಡಿ:\n${yt}\n\n👉 ನಿಯಮಿತ ಅಪ್‌ಡೇಟ್‌ಗಳು ಮತ್ತು ತರಬೇತಿಗಾಗಿ subscribe ಮಾಡಿ.\n\nನಿಮ್ಮ dashboard ಅನ್ವೇಷಿಸಿ ಮತ್ತು ನಿಮ್ಮ ರಿವಾರ್ಡ್‌ಗಳನ್ನು ಉತ್ತಮವಾಗಿ ಬಳಸಿ!`
    );
    return (
      `🎉 Congratulations ${name}! 🎉\n\nWelcome to VGK4U! A total of 15,000 reward points have been credited to your account:\n🎁 10,000 pts — Welcome Bonus\n🤝 5,000 pts — Referral Bonus (joined via a member's referral)\n\nUse your points on:\n⚡ Solar Solutions\n🛵 EV (Electric Vehicles)\n🛡 Insurance\n🏡 Real Estate and other VGK services\n\nYour login details:\n🌐 Website: www.vgk4u.com\n👤 Username: ${code}\n🔐 Password: ${pwd}\n🔗 Your Referral Link:\n${ref}\n\n▶️ To understand the full earning process and how to use your benefits, watch our official YouTube channel:\n${yt}\n\n👉 Make sure to subscribe for regular updates, training, and income strategies.\n\nStart exploring your dashboard and make the most out of your rewards and opportunities!`
    );
  }

  private showShareOverlay(d: RegData): void {
    const existing = document.getElementById('vgkMobShareOverlay');
    if (existing) existing.remove();

    const esc = (s: string) => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    const rawPhone = d.phone.replace(/\D/g, '');
    const waPhone  = rawPhone.length === 10 ? '91' + rawPhone : rawPhone;

    const overlay = document.createElement('div');
    overlay.id = 'vgkMobShareOverlay';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:99999;display:flex;align-items:flex-end;justify-content:center';

    overlay.innerHTML = `
      <div style="background:#fff;border-radius:20px 20px 0 0;width:100%;max-height:92vh;overflow-y:auto;padding:20px 16px 32px">
        <div style="text-align:center;margin-bottom:14px">
          <div style="width:40px;height:4px;background:#e5e7eb;border-radius:4px;margin:0 auto 14px"></div>
          <div style="font-size:26px">🎉</div>
          <h5 style="font-weight:800;color:#4c1d95;margin:6px 0 2px;font-size:17px">VGK4U Account Created!</h5>
          <p style="font-size:12px;color:#6b7280;margin:0">Share login details with the new member</p>
        </div>

        <!-- Details card -->
        <div style="background:#f5f3ff;border:1.5px solid #ddd6fe;border-radius:12px;padding:12px 14px;margin-bottom:14px">
          <div style="display:flex;justify-content:space-between;margin-bottom:6px">
            <span style="font-size:12px;color:#6b7280">Name</span>
            <strong style="font-size:13px;color:#1f2937">${esc(d.partner_name)}</strong>
          </div>
          <div style="display:flex;justify-content:space-between;margin-bottom:6px">
            <span style="font-size:12px;color:#6b7280">VGK4U ID</span>
            <strong style="font-size:13px;color:#7c3aed">${esc(d.partner_code)}</strong>
          </div>
          <div style="display:flex;justify-content:space-between;margin-bottom:6px">
            <span style="font-size:12px;color:#6b7280">Phone</span>
            <strong style="font-size:13px;color:#1f2937">${esc(d.phone)}</strong>
          </div>
          <div style="display:flex;justify-content:space-between">
            <span style="font-size:12px;color:#6b7280">Password</span>
            <strong style="font-size:13px;color:#059669;font-family:monospace">${esc(d.password)}</strong>
          </div>
        </div>

        <!-- Language + message -->
        <div style="margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <label style="font-size:12px;font-weight:700;color:#374151">Share Message</label>
            <select id="vgkMobShareLang" style="font-size:12px;border:1px solid #ddd;border-radius:6px;padding:4px 8px">
              <option value="english">English</option>
              <option value="hindi">हिंदी</option>
              <option value="telugu">తెలుగు</option>
              <option value="tamil">தமிழ்</option>
              <option value="kannada">ಕನ್ನಡ</option>
            </select>
          </div>
          <textarea id="vgkMobShareMsg" rows="8" style="width:100%;font-size:12.5px;border:1.5px solid #ddd6fe;border-radius:8px;padding:10px;resize:vertical;font-family:inherit;line-height:1.55;box-sizing:border-box"></textarea>
        </div>

        <!-- Action buttons -->
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">
          <button id="vgkMobShareCopyBtn" style="flex:1;min-width:80px;padding:11px 8px;border:1.5px solid #7c3aed;background:#fff;color:#7c3aed;border-radius:10px;font-weight:700;font-size:13px;cursor:pointer">
            <i class="fas fa-copy me-1"></i>Copy
          </button>
          <button id="vgkMobShareWABtn" style="flex:2;min-width:140px;padding:11px 8px;background:#25D366;color:#fff;border:none;border-radius:10px;font-weight:700;font-size:13px;cursor:pointer">
            <i class="fab fa-whatsapp me-1"></i>Share on WhatsApp
          </button>
        </div>
        <button id="vgkMobShareCloseBtn" style="width:100%;padding:10px;background:#f3f4f6;color:#374151;border:none;border-radius:10px;font-weight:700;font-size:13px;cursor:pointer">
          Close
        </button>
      </div>`;

    document.body.appendChild(overlay);

    const msgEl = document.getElementById('vgkMobShareMsg') as HTMLTextAreaElement;
    msgEl.value = this.buildShareMsg('english', d);

    document.getElementById('vgkMobShareLang')?.addEventListener('change', (e) => {
      msgEl.value = this.buildShareMsg((e.target as HTMLSelectElement).value, d);
    });

    document.getElementById('vgkMobShareCopyBtn')?.addEventListener('click', () => {
      const msg = msgEl.value;
      const btn = document.getElementById('vgkMobShareCopyBtn') as HTMLButtonElement;
      if (navigator.clipboard) {
        navigator.clipboard.writeText(msg).then(() => {
          const orig = btn.innerHTML;
          btn.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
          btn.style.background = '#ede9fe';
          setTimeout(() => { btn.innerHTML = orig; btn.style.background = '#fff'; }, 2000);
        });
      } else {
        prompt('Copy this message:', msg);
      }
    });

    document.getElementById('vgkMobShareWABtn')?.addEventListener('click', () => {
      const msg = msgEl.value;
      const url = waPhone
        ? `https://wa.me/${waPhone}?text=${encodeURIComponent(msg)}`
        : `https://wa.me/?text=${encodeURIComponent(msg)}`;
      window.open(url, '_blank');
    });

    document.getElementById('vgkMobShareCloseBtn')?.addEventListener('click', () => overlay.remove());
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
  }

  private closeRegForm(): void {
    const card = this.container.querySelector('#regFormCard') as HTMLElement;
    if (card) card.style.display = 'none';
    this.resetRegForm();
  }

  private resetRegForm(): void {
    const form    = this.container.querySelector('#regForm') as HTMLFormElement | null;
    const success = this.container.querySelector('#regSuccess') as HTMLElement | null;
    const errEl   = this.container.querySelector('#regError') as HTMLElement | null;
    if (form)    { form.reset(); form.style.display = ''; }
    if (success) success.style.display = 'none';
    if (errEl)   errEl.style.display   = 'none';
    this.resetOtpState();
    const stored = JSON.parse(localStorage.getItem('vgk_partner') || '{}');
    const ref = this.container.querySelector('#regReferrer') as HTMLInputElement | null;
    if (ref && stored.partner_code) ref.value = stored.partner_code;
  }

  private updateStats(): void {
    const statTotal = this.container.querySelector('#statTotal');
    const statThisMonth = this.container.querySelector('#statThisMonth');
    if (statTotal) statTotal.textContent = String(this.total);
    if (statThisMonth) statThisMonth.textContent = String(this.thisMonth);
  }

  private updateList(): void {
    const listEl = this.container.querySelector('#myRegList');
    if (!listEl) return;
    if (this.loading) {
      listEl.innerHTML = `<div style="text-align:center;padding:40px;color:#9ca3af"><i class="fas fa-spinner fa-spin" style="font-size:22px"></i></div>`;
      return;
    }
    if (this.members.length === 0) {
      listEl.innerHTML = `<div style="text-align:center;padding:40px;color:#9ca3af">
        <i class="fas fa-user-plus" style="font-size:28px;margin-bottom:8px;display:block"></i>
        <div style="font-size:14px">No registrations yet.<br>Tap <b>Register</b> above to add a new Channel Partner.</div>
      </div>`;
      return;
    }
    listEl.innerHTML = this.members.map(m => `
      <div style="background:white;border-radius:12px;padding:14px 16px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,.07)">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
          <div>
            <span style="font-family:monospace;font-size:11px;font-weight:700;color:#7c3aed;background:#ede9fe;padding:2px 7px;border-radius:5px">${m.partner_code || '—'}</span>
            <span style="margin-left:8px;font-size:13px;font-weight:700;color:#111827">${m.partner_name || '—'}</span>
          </div>
          <span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px;${m.is_active ? 'background:#d1fae5;color:#065f46' : 'background:#fee2e2;color:#991b1b'}">${m.is_active ? 'Active' : 'Inactive'}</span>
        </div>
        <div style="display:flex;gap:16px;font-size:11.5px;color:#6b7280">
          <span><i class="fas fa-phone" style="margin-right:4px;color:#9ca3af"></i>${m.phone || '—'}</span>
          <span><i class="fas fa-calendar-alt" style="margin-right:4px;color:#9ca3af"></i>Reg: ${this.fmtDate(m.created_at)}</span>
        </div>
      </div>`).join('');
  }
}
