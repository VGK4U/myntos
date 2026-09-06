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

  private getSenderSignature(): string {
    const authState = authService.getAuthState();
    const user = authState.user || {};
    const fullName = user.full_name || user.name || `${user.first_name || ''} ${user.last_name || ''}`.trim() || 'MyntReal Executive';
    const empCode = user.emp_code || user.employee_id || user.mnr_id || user.partner_code || '';
    const designation = user.designation || user.role_name || user.role || 'Sales & Operations';

    const codeStr = empCode ? ` (${empCode})` : '';
    return `\n\n—\nRegards,\n${fullName}${codeStr}\n${designation} | MyntReal Workflows`;
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
    const initialText = (defaultMessage || QUICK_TEMPLATES.greeting.text) + signature;

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
              <strong>${this.escapeHtml(name || 'Customer')}</strong> · +91 ${cleanPhone}
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
              <strong>Scan WhatsApp</strong>
              <small>Common Number · Port 5002 · Tracked</small>
            </div>
          </button>
          <button class="uwa-mode-btn ${this.activeMode === 'meta_api' ? 'active' : ''}" id="uwaModeMetaBtn">
            <i class="fas fa-building"></i>
            <div>
              <strong>WhatsApp API</strong>
              <small>Meta Cloud API · Verified</small>
            </div>
          </button>
        </div>

        <!-- Quick Template Chips -->
        <div class="uwa-section-label">Quick Templates</div>
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
            <span id="uwaSendBtnLabel">Send via Scan WhatsApp</span>
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(this.modalEl);
    this.attachEvents();
  }

  private attachEvents(): void {
    if (!this.modalEl) return;

    document.getElementById('uwaCloseBtn')?.addEventListener('click', () => this.close());
    document.getElementById('uwaCancelBtn')?.addEventListener('click', () => this.close());

    // Mode Toggle
    document.getElementById('uwaModeScannedBtn')?.addEventListener('click', () => {
      this.activeMode = 'scanned';
      this.updateModeUI();
    });

    document.getElementById('uwaModeMetaBtn')?.addEventListener('click', () => {
      this.activeMode = 'meta_api';
      this.updateModeUI();
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
      if (sendBtnLabel) sendBtnLabel.textContent = 'Send via Scan WhatsApp';
      if (sendBtn) sendBtn.style.background = '#16a34a';
    } else {
      scannedBtn?.classList.remove('active');
      metaBtn?.classList.add('active');
      if (sendBtnLabel) sendBtnLabel.textContent = 'Send via WhatsApp API';
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

    // Ensure sender signature is attached
    const sig = this.getSenderSignature();
    if (msg.indexOf('Regards,') === -1 && msg.indexOf('MyntReal') === -1) {
      msg = msg + sig;
    }

    const { phone, name, leadId } = this.currentOptions;
    const cleanPhone = (phone || '').replace(/\D/g, '').slice(-10);

    if (!cleanPhone || cleanPhone.length < 10) {
      this.showFeedback('Invalid recipient phone number.', 'error');
      return;
    }

    if (sendBtn) sendBtn.disabled = true;

    // Mode 1: WhatsApp API (Meta Cloud)
    if (this.activeMode === 'meta_api') {
      if (sendBtnLabel) sendBtnLabel.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Sending via Meta API...';
      this.showFeedback('Dispatching via WhatsApp Cloud API...', 'info');

      try {
        const leadTargetId = (leadId && leadId !== 'new' && !isNaN(Number(leadId))) ? Number(leadId) : 0;
        const response = await apiService.post<any>(`/whatsapp-config/crm-lead-send/${leadTargetId}`, {
          phone: cleanPhone,
          custom_message: msg,
          send_mode: 'company'
        });

        if (response.success) {
          if (sendBtnLabel) sendBtnLabel.innerHTML = '<i class="fas fa-check me-1"></i> Sent Successfully ✓';
          this.showFeedback('✅ Dispatched via WhatsApp Meta Cloud API (Signed & Tracked)', 'success');
          setTimeout(() => this.close(), 2500);
        } else {
          const errorMsg = response.error || response.data?.reason || 'Meta API not available. Switching to Scan WhatsApp...';
          this.showFeedback(`⚠️ ${errorMsg}`, 'error');
          // Auto-switch to Scanned WhatsApp
          setTimeout(() => {
            this.activeMode = 'scanned';
            this.updateModeUI();
            this.handleSend();
          }, 1500);
        }
      } catch (err: any) {
        console.warn('[UnifiedWAModal] Meta API failed, fallback to scan:', err);
        this.showFeedback(`⚠️ Meta API failed: ${err.message || 'Error'}. Falling back to Scan WhatsApp...`, 'error');
        setTimeout(() => {
          this.activeMode = 'scanned';
          this.updateModeUI();
          this.handleSend();
        }, 1500);
      }
      return;
    }

    // Mode 2: Scan WhatsApp (Common Number)
    if (sendBtnLabel) sendBtnLabel.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Sending via Common Bot...';
    this.showFeedback('Connecting to WhatsApp Bot Gateway...', 'info');

    try {
      const response = await apiService.post<any>('/whatsapp/send-message', {
        recipient: cleanPhone,
        message: msg,
        recipient_type: 'individual',
        recipient_name: name || 'Customer',
        lead_id: leadId || null
      });

      if (response.success) {
        if (sendBtnLabel) sendBtnLabel.innerHTML = '<i class="fas fa-check me-1"></i> Sent Successfully ✓';
        this.showFeedback(`✅ Dispatched via Scan WhatsApp (Common Number)! Sender: ${this.escapeHtml(authService.getAuthState().user?.full_name || 'Staff')}`, 'success');
        setTimeout(() => this.close(), 2500);
      } else {
        const errorMsg = response.error || 'Failed to dispatch via WhatsApp Gateway. Please verify the common QR bot is scanned.';
        this.showFeedback(`❌ ${errorMsg}`, 'error');
        if (sendBtn) sendBtn.disabled = false;
        if (sendBtnLabel) sendBtnLabel.textContent = 'Retry Send';
      }
    } catch (err: any) {
      console.error('[UnifiedWAModal] Send error:', err);
      this.showFeedback(`❌ Network error: ${err.message || 'Server unreachable'}`, 'error');
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
