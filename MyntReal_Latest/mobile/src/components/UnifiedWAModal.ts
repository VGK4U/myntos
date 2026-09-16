/**
 * Unified WhatsApp Dispatch Modal for Mobile
 * DC Protocol: DC_MOBILE_WA_MODAL_001
 * 
 * Features:
 * - Direct dispatch via Scanned Connected Bot (Port 5002 /api/v1/whatsapp/send-message)
 * - Automatic sender identification & signature appending for complete staff tracking
 * - Direct WhatsApp (wa.me) fallback
 * - Quick contextual templates
 * - Live dispatch feedback
 */

import { apiService } from '../services/api.service';
import { authService } from '../services/auth.service';

export interface WAModalOptions {
  phone: string;
  name?: string;
  leadId?: number | string;
  context?: string;
  defaultMessage?: string;
}

const QUICK_TEMPLATES: Record<string, { label: string; text: string }> = {
  greeting: {
    label: '👋 Welcome & Introduction',
    text: 'Namaskaram! Thank you for connecting with MyntReal. I am your dedicated relationship manager. Please let me know how I may assist you with your project today.'
  },
  bank_update: {
    label: '🏦 Bank Loan Update',
    text: 'Dear Customer, your bank file is currently under active processing. Our team is following up with the branch for swift approval and sanction.'
  },
  net_meter: {
    label: '⚡ Net Meter & EB',
    text: 'Dear Customer, your DISCOM Net Metering and EB service documentation is progressing as scheduled. We will update you once the inspection is cleared.'
  },
  payment: {
    label: '💰 Payment / Balance Follow-up',
    text: 'Dear Customer, this is a gentle reminder regarding the pending balance for your project. Kindly arrange the clearance at your earliest convenience.'
  },
  site_visit: {
    label: '📍 Location & Site Visit',
    text: 'Dear Customer, our technical field staff is scheduled to visit your site. Kindly let us know if you need to coordinate the visit time.'
  }
};

class UnifiedWAModal {
  private modalEl: HTMLElement | null = null;
  private currentOptions: WAModalOptions | null = null;
  private activeMode: 'scanned' | 'meta_api' = 'scanned';

  private canonicalTemplates: any[] = [];
  private selectedCanonicalBody: string = '';

  private getSenderSignature(): string {
    const authState = authService.getAuthState();
    const user: any = authState.user || {};
    const fullName = user.full_name || user.name || `${user.first_name || ''} ${user.last_name || ''}`.trim() || 'Staff';
    let ext = user.extension || user.ext || (typeof window !== 'undefined' ? (window as any).__STAFF_EXTENSION__ : null);
    if (!ext && user.emp_code) {
      const m = String(user.emp_code).match(/(\d{2,4})$/);
      if (m) ext = m[1].replace(/^0+/, '') || m[1];
    }
    if (ext && String(ext).trim() && !['none', 'null', 'undefined', 'n/a'].includes(String(ext).trim().toLowerCase())) {
      return `\n\nRegards,\n${fullName}\n📞 +91 85858 52738 | +91 8897797667\nExt: ${String(ext).trim()}`;
    }
    return `\n\nRegards,\n${fullName}\n📞 +91 85858 52738 | +91 8897797667`;
  }

  private getVerticalQuickMessage(action: 'thanks_connecting' | 'trying_to_reach'): string {
    const cName = (this.currentOptions?.name || 'Customer').trim();
    const ctx = (this.currentOptions?.context || '').toLowerCase();
    
    let vertical: 'solar' | 'real_estate' | 'insurance' | 'ev' | 'etc' | 'general' = 'general';
    if (ctx.includes('solar')) {
      vertical = 'solar';
    } else if (ctx.includes('real') || ctx.includes('property') || ctx.includes('estate')) {
      vertical = 'real_estate';
    } else if (ctx.includes('insur') || ctx.includes('care')) {
      vertical = 'insurance';
    } else if (ctx.includes('ev') || ctx.includes('spare') || ctx.includes('zynova') || ctx.includes('vehicle')) {
      vertical = 'ev';
    } else if (ctx.includes('etc') || ctx.includes('train') || ctx.includes('skill')) {
      vertical = 'etc';
    }

    if (action === 'thanks_connecting') {
      switch (vertical) {
        case 'solar':
          return `నమస్కారం ${cName} గారు! 🙏 MyntReal Solar Rooftop గురించి మాతో మాట్లాడినందుకు ధన్యవాదాలు. మీ ఇంటి లేదా కమర్షియల్ కరెంట్ బిల్లును 90% వరకు తగ్గించుకుంటూ, Government Subsidy పొందే పూర్తి వివరాలు & Customized Solar Quotation త్వరలోనే మా సోలార్ ఎక్స్‌పర్ట్ మీకు షేర్ చేస్తారు. ఏవైనా డౌట్స్ ఉంటే దయచేసి ఇక్కడ మెసేజ్ చేయండి.`;
        case 'real_estate':
          return `నమస్కారం ${cName} గారు! 🙏 MyntReal Properties తో కనెక్ట్ అయినందుకు ధన్యవాదాలు. మీ బడ్జెట్ మరియు రిక్వైర్‌మెంట్‌కు తగినట్లుగా బెస్ట్ వెరిఫైడ్ ఓపెన్ ప్లాట్స్, గేటెడ్ కమ్యూనిటీ విల్లాస్ మరియు అపార్ట్‌మెంట్స్ వివరాలను మా ప్రాపర్టీ స్పెషలిస్ట్ త్వరలోనే మీకు షేర్ చేస్తారు. సైట్ విజిట్ కోసం ఎప్పుడైనా సంప్రదించవచ్చు.`;
        case 'insurance':
          return `నమస్కారం ${cName} గారు! 🙏 MyntReal Insurance & Protection తో మాట్లాడినందుకు ధన్యవాదాలు. మీకు మరియు మీ కుటుంబానికి సరిపోయే బెస్ట్ Health, Life మరియు General Insurance పాలసీ కొటేషన్లను మా ఇన్సూరెన్స్ అడ్వైజర్ మీకు పంపిస్తారు. పూర్తి క్లెయిమ్ సపోర్ట్ మా బాధ్యత.`;
        case 'ev':
          return `నమస్కారం ${cName} గారు! 🙏 MyntReal EV & Spares గురించి మాతో కనెక్ట్ అయినందుకు ధన్యవాదాలు. లేటెస్ట్ ఎలక్ట్రిక్ వెహికల్ మోడల్స్, రేంజ్, బ్యాటరీ వారంటీ, ఫైనాన్స్ ఆప్షన్స్ మరియు టెస్ట్ రైడ్ వివరాలను మా ఈవీ స్పెషలిస్ట్ మీకు త్వరలోనే అందిస్తారు.`;
        case 'etc':
          return `నమస్కారం ${cName} గారు! 🙏 MyntReal ETC Skill Training ప్రోగ్రామ్స్ గురించి మాట్లాడినందుకు ధన్యవాదాలు. మీ కెరీర్ గ్రోత్‌కు అవసరమైన సర్టిఫైడ్ ట్రైనింగ్ కోర్సులు, బ్యాచ్ టైమింగ్స్ మరియు జాబ్ అసిస్టెన్స్ వివరాలు మా కోఆర్డినేటర్ మీకు పంపిస్తారు.`;
        default:
          return `నమస్కారం ${cName} గారు! 🙏 MyntReal తో కనెక్ట్ అయినందుకు చాలా ధన్యవాదాలు. మా అన్ని ప్రీమియర్ సర్వీసెస్ మీ సేవలో అందుబాటులో ఉన్నాయి:\n☀️ Solar Rooftop & Renewable Energy (కరెంట్ బిల్లు 90% వరకు ఆదా & Govt సబ్సిడీ)\n🏡 Real Estate & Premier Properties (ఓపెన్ ప్లాట్స్, విల్లాస్ & అపార్ట్‌మెంట్స్)\n🛡️ Insurance & Protection Solutions (హెల్త్, లైఫ్ & జనరల్ పాలసీలు)\n🛵 EV Vehicles & Genuine Spares (ఎకో-ఫ్రెండ్లీ ఎలక్ట్రిక్ బైక్స్ & సర్వీస్)\n🎓 ETC Skill Training & Career Certifications (ఉద్యోగ నైపుణ్య శిక్షణ)\n\nమా Relationship Manager మీకు పూర్తి వివరాలు అందిస్తారు. మీకు ఏ సమాచారం కావాలన్నా దయచేసి ఇక్కడ మెసేజ్ చేయగలరు!`;
      }
    } else {
      switch (vertical) {
        case 'solar':
          return `నమస్కారం ${cName} గారు! 📞 మీ Solar Rooftop ఎంక్వైరీ కోసం MyntReal నుండి ఇప్పుడే కాల్ చేశాము, కానీ కాల్ కలవలేదు. మీరు ఫ్రీగా ఉన్నప్పుడు దయచేసి ఈ మెసేజ్‌కి రిప్లై ఇవ్వండి లేదా కాల్ బ్యాక్ చేయండి. సోలార్ సబ్సిడీ మరియు సేవింగ్స్ వివరాలు తెలియజేస్తాము.`;
        case 'real_estate':
          return `నమస్కారం ${cName} గారు! 📞 మీ Real Estate ప్రాపర్టీ ఎంక్వైరీ గురించి MyntReal నుండి కాల్ చేశాము, మాట్లాడటం కుదరలేదు. మీకు అనుకూలమైన టైమ్‌లో దయచేసి రిప్లై ఇవ్వండి లేదా కాల్ చేయండి. మీ రిక్వైర్‌మెంట్‌కు సరిపడే బెస్ట్ ప్రాపర్టీ ఆప్షన్స్ మీకు పంపిస్తాము.`;
        case 'insurance':
          return `నమస్కారం ${cName} గారు! 📞 మీ Insurance ఎంక్వైరీ గురించి MyntReal నుండి కాల్ చేశాము, కాల్ కలవలేదు. మీకు ఫ్రీ టైమ్ ఉన్నప్పుడు దయచేసి ఇక్కడ రిప్లై ఇవ్వండి. మీకు అనువైన బెస్ట్ ఇన్సూరెన్స్ ప్లాన్స్ వివరాలు చర్చిద్దాం.`;
        case 'ev':
          return `నమస్కారం ${cName} గారు! 📞 మీ EV Vehicle & Spares ఎంక్వైరీ కోసం MyntReal నుండి కాల్ చేశాము, మాట్లాడటం వీలుపడలేదు. మీరు వీలైనప్పుడు రిప్లై ఇవ్వండి లేదా కాల్ చేయండి. టెస్ట్ రైడ్ మరియు మోడల్స్ వివరాలు మీకు తెలియజేస్తాము.`;
        case 'etc':
          return `నమస్కారం ${cName} గారు! 📞 మీ ETC Skill Training కోర్సు వివరాల కోసం MyntReal నుండి కాల్ చేశాము, కాల్ కనెక్ట్ అవ్వలేదు. మీరు ఫ్రీగా ఉన్నప్పుడు దయచేసి మెసేజ్ చేయండి. అప్‌కమింగ్ బ్యాచ్ టైమింగ్స్ మరియు ఫీజు వివరాలు చర్చిద్దాం.`;
        default:
          return `నమస్కారం ${cName} గారు! 📞 MyntReal నుండి మీతో మాట్లాడటానికి ఇప్పుడే కాల్ చేశాము, కానీ కాల్ కలవలేదు / మీరు బిజీగా ఉన్నట్లున్నారు. మేము మీకు క్రింది సర్వీసెస్‌లో ఉత్తమ సేవలు అందిస్తున్నాము:\n☀️ Solar Energy (సోలార్ రూఫ్‌టాప్ & సబ్సిడీ)\n🏡 Real Estate (వెరిఫైడ్ ప్రాపర్టీస్ & సైట్ విజిట్స్)\n🛡️ Insurance (హెల్త్ & లైఫ్ ఇన్సూరెన్స్)\n🛵 EV Vehicles & Spares (ఎలక్ట్రిక్ స్కూటర్లు & స్పేర్స్)\n🎓 ETC Skill Training (నైపుణ్య శిక్షణ & కెరీర్)\n\nమీకు అనుకూలమైన సమయంలో దయచేసి ఇక్కడ మెసేజ్ చేయండి లేదా కాల్ బ్యాక్ చేయగలరు!`;
      }
    }
  }

  private applyVerticalQuick(action: 'thanks_connecting' | 'trying_to_reach'): void {
    const text = this.getVerticalQuickMessage(action);
    const sig = this.getSenderSignature();
    const textEl = document.getElementById('uwaMessageText') as HTMLTextAreaElement;
    if (textEl) {
      textEl.value = text + sig;
      textEl.focus();
    }
  }

  private async loadCanonicalTemplates(): Promise<void> {
    const sel = document.getElementById('uwaCanonicalTpl') as HTMLSelectElement;
    const noTpl = document.getElementById('uwaNoTplNotice');
    if (!sel) return;

    sel.innerHTML = '<option value="">— Loading templates… —</option>';
    if (noTpl) noTpl.style.display = 'none';

    const segEl = document.getElementById('uwaCanonicalSeg') as HTMLSelectElement;
    const catEl = document.getElementById('uwaCanonicalCat') as HTMLSelectElement;
    const seg = segEl?.value || '';
    const cat = catEl?.value || '';
    const mode = this.activeMode === 'scanned' ? 'scanned' : 'company';

    let url = `/whatsapp-config/templates?mode=${encodeURIComponent(mode)}`;
    if (seg) url += `&segment=${encodeURIComponent(seg)}`;
    if (cat) url += `&category=${encodeURIComponent(cat)}`;

    try {
      const res = await apiService.get<any>(url);
      const list = res?.templates || res?.data || res || [];
      this.canonicalTemplates = Array.isArray(list) ? list : [];

      if (!this.canonicalTemplates.length) {
        sel.innerHTML = '<option value="">— No approved templates found —</option>';
        if (noTpl) noTpl.style.display = 'block';
        return;
      }

      let optHtml = `<option value="">— Select template (${this.canonicalTemplates.length} available) —</option>`;
      this.canonicalTemplates.forEach(t => {
        optHtml += `<option value="${t.id}">${this.escapeHtml(t.template_name || t.name || 'Template #' + t.id)} (${t.category || 'MARKETING'})</option>`;
      });
      sel.innerHTML = optHtml;
    } catch {
      sel.innerHTML = '<option value="">— Error loading templates —</option>';
    }
  }

  private onCanonicalTplChange(): void {
    const sel = document.getElementById('uwaCanonicalTpl') as HTMLSelectElement;
    const varsWrap = document.getElementById('uwaCanonicalVarsWrap');
    const varsBox = document.getElementById('uwaCanonicalVarsBox');
    const tplId = sel?.value;

    if (!tplId) {
      if (varsWrap) varsWrap.style.display = 'none';
      if (varsBox) varsBox.innerHTML = '';
      return;
    }

    const tpl = this.canonicalTemplates.find(t => String(t.id) === String(tplId));
    if (!tpl) return;

    this.selectedCanonicalBody = tpl.body_text || tpl.content || tpl.body || '';

    const matches = this.selectedCanonicalBody.match(/\{\{(\d+)\}\}/g) || [];
    const uniqueIndices: string[] = [];
    matches.forEach(m => {
      const idx = m.replace(/[\{\}]/g, '');
      if (!uniqueIndices.includes(idx)) uniqueIndices.push(idx);
    });
    uniqueIndices.sort((a, b) => Number(a) - Number(b));

    if (uniqueIndices.length && varsBox && varsWrap) {
      varsWrap.style.display = 'block';
      let html = '';
      uniqueIndices.forEach(idx => {
        const defaultVal = (idx === '1') ? (this.currentOptions?.name || '') : '';
        html += `
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
            <label style="font-size:11px; font-weight:700; width:28px; color:#475569;">#${idx}</label>
            <input type="text" class="uwa-canonical-var-inp" data-var-idx="${idx}" value="${this.escapeHtml(defaultVal)}" placeholder="Value for {{${idx}}}" style="flex:1; font-size:12px; border:1px solid #cbd5e1; border-radius:6px; padding:4px 8px;" />
          </div>
        `;
      });
      varsBox.innerHTML = html;

      varsBox.querySelectorAll('.uwa-canonical-var-inp').forEach(inp => {
        inp.addEventListener('input', () => this.buildCanonicalPreview());
      });
    } else {
      if (varsWrap) varsWrap.style.display = 'none';
      if (varsBox) varsBox.innerHTML = '';
    }

    this.buildCanonicalPreview();
  }

  private buildCanonicalPreview(): void {
    let text = this.selectedCanonicalBody || '';
    const matches = text.match(/\{\{(\d+)\}\}/g) || [];
    matches.forEach(m => {
      const idx = m.replace(/[\{\}]/g, '');
      const inp = document.querySelector(`.uwa-canonical-var-inp[data-var-idx="${idx}"]`) as HTMLInputElement;
      const val = inp?.value || `{{${idx}}}`;
      text = text.replace(new RegExp(`\\{\\{${idx}\\}\\}`, 'g'), val);
    });

    const sig = this.getSenderSignature();
    const textEl = document.getElementById('uwaMessageText') as HTMLTextAreaElement;
    if (textEl && text) {
      textEl.value = text + sig;
    }
  }

  open(options: WAModalOptions): void {
    this.currentOptions = options;
    this.activeMode = 'scanned';
    this.render();
  }

  close(): void {
    if (this.modalEl) {
      this.modalEl.remove();
      this.modalEl = null;
    }
  }

  private render(): void {
    this.close();

    if (!this.currentOptions) return;

    const { phone, name, context, defaultMessage } = this.currentOptions;
    const cleanPhone = (phone || '').replace(/\D/g, '').slice(-10);
    const signature = this.getSenderSignature();
    const initialText = (defaultMessage || this.getVerticalQuickMessage('thanks_connecting')) + signature;

    this.modalEl = document.createElement('div');
    this.modalEl.id = 'unifiedWAModal';
    this.modalEl.className = 'uwa-modal-backdrop';
    this.modalEl.innerHTML = `
      <div class="uwa-modal-sheet">
        <!-- Header -->
        <div class="uwa-header">
          <div class="uwa-header-info">
            <div class="uwa-badge-online">
              <span class="uwa-dot"></span> Common Number Connected
            </div>
            <h3 class="uwa-title"><i class="fab fa-whatsapp me-1"></i> Send WhatsApp</h3>
            <div class="uwa-recipient-sub">
              <strong>${this.escapeHtml(name || 'Customer')}</strong> · ${this.maskPhone(cleanPhone)}
              ${context ? `<span class="uwa-ctx-tag ms-1">${this.escapeHtml(context)}</span>` : ''}
            </div>
          </div>
          <button class="uwa-close-btn" id="uwaCloseBtn">&times;</button>
        </div>

        <!-- Mode Selector (Scanned WA vs Meta Cloud API) -->
        <div class="uwa-mode-bar">
          <button class="uwa-mode-btn ${this.activeMode === 'scanned' ? 'active' : ''}" id="uwaModeScannedBtn">
            <i class="fas fa-qrcode"></i>
            <div>
              <strong>📱 Scanned WhatsApp</strong>
              <small>Employee Account · Scanned</small>
            </div>
          </button>
          <button class="uwa-mode-btn ${this.activeMode === 'meta_api' ? 'active' : ''}" id="uwaModeMetaBtn">
            <i class="fas fa-building"></i>
            <div>
              <strong>🏢 Official WhatsApp</strong>
              <small>Meta Cloud API · Verified</small>
            </div>
          </button>
        </div>

        <!-- 1-Tap Vertical Quick Responses -->
        <div class="uwa-section-label">⚡ 1-Tap Quick Responses</div>
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px;">
          <button id="uwaQuickThanksBtn" type="button" style="background:#ecfdf5; border:1.5px solid #a7f3d0; color:#065f46; border-radius:10px; padding:8px 10px; font-size:12px; font-weight:700; cursor:pointer; text-align:left; display:flex; align-items:center; gap:6px;">
            <span style="font-size:16px;">🙏</span>
            <div>
              <div>Thanks for Connecting</div>
              <small style="font-size:9.5px; font-weight:normal; opacity:.8;">Service tailored</small>
            </div>
          </button>
          <button id="uwaQuickReachBtn" type="button" style="background:#fef3c7; border:1.5px solid #fde68a; color:#92400e; border-radius:10px; padding:8px 10px; font-size:12px; font-weight:700; cursor:pointer; text-align:left; display:flex; align-items:center; gap:6px;">
            <span style="font-size:16px;">📞</span>
            <div>
              <div>Trying to Reach</div>
              <small style="font-size:9.5px; font-weight:normal; opacity:.8;">Call missed / inquiry</small>
            </div>
          </button>
        </div>

        <!-- Official Meta / Database Templates -->
        <div class="uwa-section-label">📑 Select Official Template</div>
        <div style="display:flex; gap:6px; margin-bottom:8px;">
          <select id="uwaCanonicalSeg" style="flex:1; font-size:11.5px; padding:6px; border:1px solid #cbd5e1; border-radius:8px; background:#fff;">
            <option value="">All Segments</option>
            <option value="general">MNR General</option>
            <option value="solar">Solar</option>
            <option value="myntreal_real">Myntreal Real</option>
            <option value="ev_b2c">EV B2C</option>
            <option value="ev_b2b">EV B2B</option>
            <option value="real_estate">Real Estate</option>
            <option value="etc_training">ETC Training</option>
            <option value="vgk">VGK Members</option>
            <option value="system">System</option>
          </select>
          <select id="uwaCanonicalCat" style="flex:1; font-size:11.5px; padding:6px; border:1px solid #cbd5e1; border-radius:8px; background:#fff;">
            <option value="">All Categories</option>
            <option value="MARKETING">Marketing</option>
            <option value="UTILITY">Utility</option>
            <option value="AUTHENTICATION">Authentication</option>
          </select>
        </div>
        <div style="margin-bottom:10px;">
          <select id="uwaCanonicalTpl" style="width:100%; font-size:12px; border:1px solid #cbd5e1; border-radius:8px; padding:7px 10px; background:#fff;">
            <option value="">— Loading templates… —</option>
          </select>
          <div id="uwaNoTplNotice" style="display:none; font-size:11px; color:#b45309; background:#fef3c7; border:1px solid #fde68a; border-radius:6px; padding:6px 8px; margin-top:4px;">
            No approved templates found for this filter.
          </div>
        </div>

        <!-- Dynamic Variable Inputs -->
        <div id="uwaCanonicalVarsWrap" style="display:none; margin-bottom:10px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:8px 10px;">
          <div style="font-size:10px; font-weight:700; color:#64748b; text-transform:uppercase; margin-bottom:6px;">Fill Variables</div>
          <div id="uwaCanonicalVarsBox"></div>
        </div>

        <!-- Quick Template Chips -->
        <div class="uwa-section-label">Contextual Quick Chips</div>
        <div class="uwa-chips-row">
          ${Object.entries(QUICK_TEMPLATES).map(([key, tpl]) => `
            <button class="uwa-chip-btn" data-tpl-key="${key}">
              ${tpl.label}
            </button>
          `).join('')}
        </div>

        <!-- Message Composer -->
        <div class="uwa-section-label mt-2">
          Message
          <small class="text-muted" style="float:right; font-weight:normal; text-transform:none;">
            ✍️ Auto-signed with your staff identity
          </small>
        </div>
        <textarea id="uwaMessageText" class="uwa-textarea" rows="7" placeholder="Type your WhatsApp message...">${this.escapeHtml(initialText)}</textarea>

        <!-- Status & Result feedback -->
        <div id="uwaFeedbackBox" class="uwa-feedback-box" style="display:none;"></div>

        <!-- Action Footer -->
        <div class="uwa-footer">
          <button class="btn btn-outline uwa-cancel-btn" id="uwaCancelBtn">Cancel</button>
          <button class="btn btn-primary uwa-send-btn" id="uwaSendBtn">
            <i class="fas fa-paper-plane me-1"></i>
            <span id="uwaSendBtnLabel">Send via 📱 Scanned WhatsApp</span>
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(this.modalEl);
    this.attachEvents();
    void this.loadCanonicalTemplates();
  }

  private attachEvents(): void {
    if (!this.modalEl) return;

    document.getElementById('uwaCloseBtn')?.addEventListener('click', () => this.close());
    document.getElementById('uwaCancelBtn')?.addEventListener('click', () => this.close());

    // 1-Tap Quick Responses
    document.getElementById('uwaQuickThanksBtn')?.addEventListener('click', () => this.applyVerticalQuick('thanks_connecting'));
    document.getElementById('uwaQuickReachBtn')?.addEventListener('click', () => this.applyVerticalQuick('trying_to_reach'));

    // Canonical Template Engine Events
    document.getElementById('uwaCanonicalSeg')?.addEventListener('change', () => this.loadCanonicalTemplates());
    document.getElementById('uwaCanonicalCat')?.addEventListener('change', () => this.loadCanonicalTemplates());
    document.getElementById('uwaCanonicalTpl')?.addEventListener('change', () => this.onCanonicalTplChange());

    // Mode Toggle
    document.getElementById('uwaModeScannedBtn')?.addEventListener('click', () => {
      this.activeMode = 'scanned';
      this.updateModeUI();
      void this.loadCanonicalTemplates();
    });

    document.getElementById('uwaModeMetaBtn')?.addEventListener('click', () => {
      this.activeMode = 'meta_api';
      this.updateModeUI();
      void this.loadCanonicalTemplates();
    });

    // Template Chips
    this.modalEl.querySelectorAll('.uwa-chip-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const key = (e.currentTarget as HTMLElement).dataset.tplKey;
        if (key && QUICK_TEMPLATES[key]) {
          const signature = this.getSenderSignature();
          const textEl = document.getElementById('uwaMessageText') as HTMLTextAreaElement;
          if (textEl) {
            textEl.value = QUICK_TEMPLATES[key].text + signature;
            textEl.focus();
          }
        }
      });
    });

    // Send Button
    document.getElementById('uwaSendBtn')?.addEventListener('click', () => this.handleSend());
  }

  private updateModeUI(): void {
    const scannedBtn = document.getElementById('uwaModeScannedBtn');
    const metaBtn = document.getElementById('uwaModeMetaBtn');
    const sendBtnLabel = document.getElementById('uwaSendBtnLabel');
    const sendBtn = document.getElementById('uwaSendBtn') as HTMLButtonElement;

    if (this.activeMode === 'scanned') {
      scannedBtn?.classList.add('active');
      metaBtn?.classList.remove('active');
      if (sendBtnLabel) sendBtnLabel.textContent = 'Send via 📱 Scanned WhatsApp';
      if (sendBtn) sendBtn.style.background = '#16a34a';
    } else {
      scannedBtn?.classList.remove('active');
      metaBtn?.classList.add('active');
      if (sendBtnLabel) sendBtnLabel.textContent = 'Send via 🏢 Official WhatsApp';
      if (sendBtn) sendBtn.style.background = '#2563eb';
    }
  }

  private async handleSend(): Promise<void> {
    if (!this.currentOptions) return;

    const textEl = document.getElementById('uwaMessageText') as HTMLTextAreaElement;
    const sendBtn = document.getElementById('uwaSendBtn') as HTMLButtonElement;
    const sendBtnLabel = document.getElementById('uwaSendBtnLabel');

    let msg = (textEl?.value || '').trim();
    if (!msg) {
      this.showFeedback('Please enter a message to send.', 'error');
      return;
    }

    // Ensure sender signature is attached without duplicates
    const sig = this.getSenderSignature();
    if (!msg.toLowerCase().includes('regards,')) {
      msg = msg + sig;
    }

    const { phone, name, leadId } = this.currentOptions;
    const cleanPhone = (phone || '').replace(/\D/g, '').slice(-10);
    const hasValidLeadId = !!(leadId && leadId !== 'new' && !isNaN(Number(leadId)));

    if ((!cleanPhone || cleanPhone.length < 10) && !hasValidLeadId) {
      this.showFeedback('Invalid recipient phone number.', 'error');
      return;
    }

    if (sendBtn) sendBtn.disabled = true;

    // Mode 1: WhatsApp API (Meta Cloud)
    if (this.activeMode === 'meta_api') {
      if (sendBtnLabel) sendBtnLabel.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Sending via Meta API...';
      this.showFeedback('Dispatching via WhatsApp Cloud API...', 'info');

      try {
        const leadTargetId = hasValidLeadId ? Number(leadId) : 0;
        const response = await apiService.post<any>(`/whatsapp-config/crm-lead-send/${leadTargetId}`, {
          phone: cleanPhone.length >= 10 ? cleanPhone : undefined,
          custom_message: msg,
          send_mode: 'company'
        });

        if (response.success) {
          if (sendBtnLabel) sendBtnLabel.innerHTML = '<i class="fas fa-check me-1"></i> Sent Successfully ✓';
          this.showFeedback('✅ Dispatched via WhatsApp Meta Cloud API (Official Business)', 'success');
          setTimeout(() => this.close(), 2500);
        } else {
          const errorMsg = response.error || response.data?.reason || 'Meta API not available.';
          this.showFeedback(`❌ Meta API Error: ${errorMsg}`, 'error');
          if (sendBtn) sendBtn.disabled = false;
          if (sendBtnLabel) sendBtnLabel.textContent = 'Retry Send';
        }
      } catch (err: any) {
        console.warn('[UnifiedWAModal] Meta API failed:', err);
        this.showFeedback(`❌ Meta API Network error: ${err.message || 'Server unreachable'}`, 'error');
        if (sendBtn) sendBtn.disabled = false;
        if (sendBtnLabel) sendBtnLabel.textContent = 'Retry Send';
      }
      return;
    }

    // Mode 2: Scan WhatsApp (Personal / Common Number)
    if (sendBtnLabel) sendBtnLabel.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Sending via Personal WA...';
    this.showFeedback('Connecting to WhatsApp Bot Gateway...', 'info');

    try {
      const response = await apiService.post<any>('/whatsapp/send-message', {
        recipient: cleanPhone.length >= 10 ? cleanPhone : 'LEAD_RESOLVE',
        message: msg,
        recipient_type: 'individual',
        recipient_name: name || 'Customer',
        lead_id: hasValidLeadId ? Number(leadId) : (leadId || null)
      });

      if (response.success) {
        if (sendBtnLabel) sendBtnLabel.innerHTML = '<i class="fas fa-check me-1"></i> Sent Successfully ✓';
        this.showFeedback(`✅ Dispatched via Personal Scanned WhatsApp! Sender: ${this.escapeHtml(authService.getAuthState().user?.full_name || 'Staff')}`, 'success');
        setTimeout(() => this.close(), 2500);
      } else {
        const errorMsg = response.error || 'Personal WhatsApp Web is disconnected or unlinked.';
        this.showFeedback(`❌ Personal WA: ${errorMsg}. You can switch to "WhatsApp API" mode above to send via Official Meta Business.`, 'error');
        if (sendBtn) sendBtn.disabled = false;
        if (sendBtnLabel) sendBtnLabel.textContent = 'Retry Send';
      }
    } catch (err: any) {
      console.error('[UnifiedWAModal] Send error:', err);
      this.showFeedback(`❌ Personal WhatsApp Gateway offline. You can switch to "WhatsApp API" above to send via Meta Cloud.`, 'error');
      if (sendBtn) sendBtn.disabled = false;
      if (sendBtnLabel) sendBtnLabel.textContent = 'Retry Send';
    }
  }

  private showFeedback(msg: string, type: 'info' | 'success' | 'error'): void {
    const feedbackBox = document.getElementById('uwaFeedbackBox');
    if (!feedbackBox) return;
    feedbackBox.style.display = 'block';
    feedbackBox.className = `uwa-feedback-box ${type}`;
    feedbackBox.innerHTML = msg;
  }

  private maskPhone(p: string): string {
    if (!p) return '-';
    const digits = String(p).replace(/\D/g, '');
    if (digits.length >= 10) {
      return '+91 ' + digits.slice(-10, -8) + '••••' + digits.slice(-4);
    }
    if (digits.length >= 4) {
      return '••••' + digits.slice(-4);
    }
    return '••••';
  }

  private escapeHtml(text: string): string {
    const map: Record<string, string> = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    };
    return (text || '').replace(/[&<>"']/g, m => map[m]);
  }
}

export const unifiedWAModal = new UnifiedWAModal();
