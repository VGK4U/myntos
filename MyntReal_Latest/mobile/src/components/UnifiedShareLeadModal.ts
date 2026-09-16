/**
 * Unified Share Lead Modal for Mobile & Web
 * DC Protocol: DC_SHARE_LEAD_MODAL_001
 * 
 * Allows telecallers and sales executives to share full lead details
 * with any active staff colleague for secondary follow-up.
 * Features:
 * - Searchable staff directory (filtered by active status and organization)
 * - Structured follow-up type selection (Site Visit, Secondary Call, Quotation, Escalation)
 * - Customizable follow-up notes / instructions
 * - In-CRM secondary handler assignment (field_staff_id / depends_on_staff_id)
 * - Automatic WhatsApp dispatch with formatted lead card & softphone direct call link
 */

import { apiService } from '../services/api.service';
import { authService } from '../services/auth.service';

export interface ShareLeadOptions {
  leadId: number | string;
  name: string;
  phone: string;
  alternatePhone?: string;
  category?: string;
  area?: string;
  city?: string;
  budgetMin?: number;
  budgetMax?: number;
  requirements?: string;
  notes?: string;
  companyId?: number;
  onShared?: (result: any) => void;
}

export interface ShareableStaff {
  id: number;
  emp_code: string;
  name: string;
  phone: string;
  role?: string;
  department?: string;
}

class UnifiedShareLeadModal {
  private modalEl: HTMLElement | null = null;
  private currentOptions: ShareLeadOptions | null = null;
  private staffList: ShareableStaff[] = [];
  private isLoadingStaff: boolean = false;

  public async open(options: ShareLeadOptions): Promise<void> {
    this.currentOptions = options;
    this.render();
    await this.loadStaff();
  }

  public close(): void {
    if (this.modalEl) {
      this.modalEl.remove();
      this.modalEl = null;
    }
    this.currentOptions = null;
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  private maskPhone(phone: string): string {
    const p = (phone || '').replace(/\D/g, '');
    if (p.length < 6) return phone || '';
    return p.slice(0, 2) + '••••' + p.slice(-4);
  }

  private async loadStaff(): Promise<void> {
    const sel = document.getElementById('usmStaffSelect') as HTMLSelectElement;
    if (!sel) return;

    sel.innerHTML = '<option value="">— Loading staff members… —</option>';
    this.isLoadingStaff = true;

    try {
      const res = await apiService.get<any>('/crm/leads/shareable-staff');
      const staff: ShareableStaff[] = res?.staff || res?.data?.staff || [];
      this.staffList = staff;

      const authUser: any = authService.getAuthState().user || {};
      const currentUserId = authUser.id;

      if (!staff.length) {
        sel.innerHTML = '<option value="">No active staff members found</option>';
        return;
      }

      let optHtml = '<option value="">— Select Staff Member for Follow-up —</option>';
      staff.forEach(s => {
        const isMe = currentUserId && s.id === currentUserId;
        const roleDept = [s.role, s.department].filter(Boolean).join(' · ');
        optHtml += `<option value="${s.id}" data-phone="${s.phone || ''}">${this.escapeHtml(s.name)} (${s.emp_code})${roleDept ? ' — ' + this.escapeHtml(roleDept) : ''}${isMe ? ' [You]' : ''}</option>`;
      });
      sel.innerHTML = optHtml;
    } catch (err: any) {
      console.error('[UnifiedShareLeadModal] Failed to load staff:', err);
      sel.innerHTML = '<option value="">Failed to load staff list</option>';
    } finally {
      this.isLoadingStaff = false;
      this.updatePreview();
    }
  }

  private render(): void {
    if (this.modalEl) this.modalEl.remove();

    const opt = this.currentOptions;
    if (!opt) return;

    const modal = document.createElement('div');
    modal.id = 'unifiedShareLeadModal';
    modal.style.cssText = [
      'position: fixed', 'inset: 0', 'z-index: 100000',
      'background: rgba(0, 0, 0, 0.75)',
      'display: flex', 'align-items: flex-end', 'justify-content: center',
      'font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    ].join(';');

    const displayPhone = this.maskPhone(opt.phone);

    modal.innerHTML = `
      <div class="usm-content" style="
        background: #0f172a;
        width: 100%;
        max-width: 520px;
        max-height: 92vh;
        border-radius: 24px 24px 0 0;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        color: #f8fafc;
        border: 1px solid rgba(255,255,255,0.12);
        box-shadow: 0 -10px 40px rgba(0,0,0,0.8);
        animation: usmSlideUp 0.25s ease-out;
      ">
        <style>
          @keyframes usmSlideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
          .usm-btn { border:none; border-radius:12px; font-weight:700; cursor:pointer; transition:all 0.15s ease; }
          .usm-btn:active { transform: scale(0.98); }
          .usm-input { width:100%; background:#1e293b; border:1px solid #334155; border-radius:10px; color:#f8fafc; padding:10px 12px; font-size:14px; box-sizing:border-box; }
          .usm-input:focus { outline:none; border-color:#0ea5e9; }
        </style>

        <!-- Header -->
        <div style="background:linear-gradient(135deg, #0284c7 0%, #0369a1 100%); padding:16px 20px; display:flex; align-items:center; justify-content:space-between;">
          <div style="display:flex; align-items:center; gap:10px;">
            <div style="background:rgba(255,255,255,0.2); width:36px; height:36px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:18px;">
              📤
            </div>
            <div>
              <div style="font-size:16px; font-weight:800; color:white; line-height:1.2;">Share Lead Details</div>
              <div style="font-size:12px; color:rgba(255,255,255,0.85);">${this.escapeHtml(opt.name)} · ${displayPhone}</div>
            </div>
          </div>
          <button id="usmCloseBtn" style="background:rgba(255,255,255,0.2); border:none; color:white; width:32px; height:32px; border-radius:8px; font-size:18px; cursor:pointer; display:flex; align-items:center; justify-content:center;">✕</button>
        </div>

        <!-- Body -->
        <div style="padding:16px 20px; overflow-y:auto; flex:1; display:flex; flex-direction:column; gap:14px;">
          
          <!-- Lead Summary Card -->
          <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:12px 14px; font-size:12px; line-height:1.5;">
            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
              <span style="color:#94a3b8;">Lead ID:</span>
              <span style="font-weight:700; color:#38bdf8;">#${opt.leadId}</span>
            </div>
            ${opt.category ? `
            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
              <span style="color:#94a3b8;">Category:</span>
              <span style="font-weight:600; color:#cbd5e1;">${this.escapeHtml(opt.category)}</span>
            </div>` : ''}
            ${opt.area || opt.city ? `
            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
              <span style="color:#94a3b8;">Location:</span>
              <span style="font-weight:600; color:#cbd5e1;">${this.escapeHtml([opt.area, opt.city].filter(Boolean).join(', '))}</span>
            </div>` : ''}
            ${opt.requirements ? `
            <div style="margin-top:6px; padding-top:6px; border-top:1px dashed #334155; color:#e2e8f0;">
              <b style="color:#94a3b8;">Needs:</b> ${this.escapeHtml(opt.requirements)}
            </div>` : ''}
          </div>

          <!-- Staff Selector -->
          <div>
            <label style="display:block; font-size:12px; font-weight:700; color:#94a3b8; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px;">
              Select Staff Member for Follow-Up <span style="color:#ef4444;">*</span>
            </label>
            <select id="usmStaffSelect" class="usm-input" style="cursor:pointer;">
              <option value="">— Loading staff members… —</option>
            </select>
          </div>

          <!-- Follow-up Type -->
          <div>
            <label style="display:block; font-size:12px; font-weight:700; color:#94a3b8; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px;">
              Follow-Up Purpose / Reason
            </label>
            <select id="usmFollowupType" class="usm-input" style="cursor:pointer;">
              <option value="site_visit">📍 Site Visit / Field Inspection</option>
              <option value="secondary_followup" selected>🔄 Secondary Follow-Up Call</option>
              <option value="quotation">📑 Quotation & Pricing Discussion</option>
              <option value="technical">⚡ Technical / Rooftop Feasibility</option>
              <option value="escalation">⚠️ Senior Escalation / Special Handling</option>
              <option value="general">💼 General Lead Follow-Up</option>
            </select>
          </div>

          <!-- Notes / Instructions -->
          <div>
            <label style="display:block; font-size:12px; font-weight:700; color:#94a3b8; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px;">
              Instructions / Notes for Staff
            </label>
            <textarea id="usmNotes" class="usm-input" rows="2" placeholder="e.g., Customer is interested in 5kW On-grid solar. Please coordinate and visit tomorrow." style="resize:none;">${opt.notes || ''}</textarea>
          </div>

          <!-- Assign in CRM Checkbox -->
          <div style="display:flex; align-items:center; gap:8px; background:#1e293b; padding:10px 14px; border-radius:10px; border:1px solid #334155;">
            <input type="checkbox" id="usmAssignCheck" checked style="width:18px; height:18px; accent-color:#0ea5e9; cursor:pointer;">
            <label for="usmAssignCheck" style="font-size:13px; color:#e2e8f0; cursor:pointer; font-weight:600;">
              Assign as Secondary Follow-up in CRM
              <div style="font-size:11px; color:#94a3b8; font-weight:400;">Lead will appear in colleague's CRM & task queue</div>
            </label>
          </div>

          <!-- Message Preview Accordion -->
          <div style="background:#0b1329; border:1px solid #1e293b; border-radius:10px; padding:10px 12px;">
            <div style="font-size:11px; font-weight:700; color:#64748b; margin-bottom:4px; text-transform:uppercase;">
              WhatsApp Message Preview:
            </div>
            <div id="usmMessagePreview" style="font-size:11.5px; color:#94a3b8; white-space:pre-wrap; max-height:80px; overflow-y:auto; font-family:monospace; line-height:1.4;">
              Select a staff member to preview message...
            </div>
          </div>

        </div>

        <!-- Footer Actions -->
        <div style="padding:14px 20px; border-top:1px solid rgba(255,255,255,0.08); background:#0b1329; display:flex; flex-direction:column; gap:8px;">
          <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
            <button id="usmWaOnlyBtn" class="usm-btn" style="background:#25D366; color:white; padding:12px; font-size:13px; display:flex; align-items:center; justify-content:center; gap:6px;">
              💬 WhatsApp Only
            </button>
            <button id="usmCrmOnlyBtn" class="usm-btn" style="background:#334155; color:#f8fafc; padding:12px; font-size:13px; display:flex; align-items:center; justify-content:center; gap:6px;">
              📋 Assign in CRM
            </button>
          </div>
          <button id="usmCombinedBtn" class="usm-btn" style="background:linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%); color:white; padding:14px; font-size:14px; box-shadow:0 4px 14px rgba(14,165,233,0.4); display:flex; align-items:center; justify-content:center; gap:8px;">
            🚀 Assign & WhatsApp Colleague
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);
    this.modalEl = modal;

    // Attach event handlers
    document.getElementById('usmCloseBtn')?.addEventListener('click', () => this.close());
    modal.addEventListener('click', (e) => {
      if (e.target === modal) this.close();
    });

    const staffSelect = document.getElementById('usmStaffSelect') as HTMLSelectElement;
    staffSelect?.addEventListener('change', () => this.updatePreview());

    const followupSelect = document.getElementById('usmFollowupType') as HTMLSelectElement;
    followupSelect?.addEventListener('change', () => this.updatePreview());

    const notesInput = document.getElementById('usmNotes') as HTMLTextAreaElement;
    notesInput?.addEventListener('input', () => this.updatePreview());

    // Button actions
    document.getElementById('usmWaOnlyBtn')?.addEventListener('click', () => this.executeShare('wa_only'));
    document.getElementById('usmCrmOnlyBtn')?.addEventListener('click', () => this.executeShare('crm_only'));
    document.getElementById('usmCombinedBtn')?.addEventListener('click', () => this.executeShare('combined'));
  }

  private updatePreview(): void {
    const previewEl = document.getElementById('usmMessagePreview');
    if (!previewEl || !this.currentOptions) return;

    const staffSelect = document.getElementById('usmStaffSelect') as HTMLSelectElement;
    const targetStaffId = staffSelect?.value;
    const staff = this.staffList.find(s => String(s.id) === String(targetStaffId));

    const followupType = (document.getElementById('usmFollowupType') as HTMLSelectElement)?.value || 'secondary_followup';
    const notes = (document.getElementById('usmNotes') as HTMLTextAreaElement)?.value || '';

    const authUser: any = authService.getAuthState().user || {};
    const senderName = authUser.full_name || authUser.name || 'Telecaller';
    const opt = this.currentOptions;

    const purposeLabel = {
      site_visit: 'Site Visit / Field Inspection',
      secondary_followup: 'Secondary Follow-Up Call',
      quotation: 'Quotation & Pricing Discussion',
      technical: 'Technical / Rooftop Feasibility',
      escalation: 'Senior Escalation / Special Handling',
      general: 'General Lead Follow-Up'
    }[followupType] || 'Secondary Follow-Up';

    const budgetStr = (opt.budgetMin || opt.budgetMax)
      ? `₹${((opt.budgetMin || 0) / 100000).toFixed(1)}L - ₹${((opt.budgetMax || opt.budgetMin || 0) / 100000).toFixed(1)}L`
      : '';

    const softphoneLink = `https://www.myntreal.com/staff/softphone?lead_id=${opt.leadId}&auto_dial=1`;
    const crmLink = `https://www.myntreal.com/staff/leads?lead_id=${opt.leadId}`;

    const text = [
      `📢 *LEAD DETAILS FOR SECONDARY FOLLOW-UP*`,
      ``,
      `👤 *Customer*: ${opt.name}`,
      `📱 *Phone*: ${opt.phone}`,
      opt.area || opt.city ? `📍 *Location*: ${[opt.area, opt.city].filter(Boolean).join(', ')}` : null,
      opt.category ? `🏷️ *Category*: ${opt.category}` : null,
      `🎯 *Purpose*: ${purposeLabel}`,
      opt.requirements ? `📝 *Requirement*: ${opt.requirements}` : null,
      budgetStr ? `💰 *Budget*: ${budgetStr}` : null,
      notes ? `💬 *Notes*: ${notes}` : null,
      `👉 *Shared by*: ${senderName}`,
      ``,
      `📞 *Call via Softphone*: ${softphoneLink}`,
      `🔗 *View Lead in CRM*: ${crmLink}`
    ].filter(Boolean).join('\n');

    previewEl.textContent = text;
  }

  private async executeShare(mode: 'wa_only' | 'crm_only' | 'combined'): Promise<void> {
    const staffSelect = document.getElementById('usmStaffSelect') as HTMLSelectElement;
    const targetStaffId = parseInt(staffSelect?.value || '0', 10);
    if (!targetStaffId) {
      alert('Please select a staff member to share details with.');
      staffSelect?.focus();
      return;
    }

    const targetStaff = this.staffList.find(s => s.id === targetStaffId);
    if (!targetStaff) {
      alert('Selected staff member is invalid.');
      return;
    }

    const followupType = (document.getElementById('usmFollowupType') as HTMLSelectElement)?.value || 'secondary_followup';
    const notes = (document.getElementById('usmNotes') as HTMLTextAreaElement)?.value.trim() || '';
    const assignAsSecondary = (document.getElementById('usmAssignCheck') as HTMLInputElement)?.checked || false;

    const opt = this.currentOptions;
    if (!opt) return;

    // Set button loading state
    const primaryBtn = document.getElementById('usmCombinedBtn') as HTMLButtonElement;
    const crmBtn = document.getElementById('usmCrmOnlyBtn') as HTMLButtonElement;
    const waBtn = document.getElementById('usmWaOnlyBtn') as HTMLButtonElement;
    [primaryBtn, crmBtn, waBtn].forEach(b => { if (b) b.disabled = true; });

    try {
      let waUrl = '';
      let waText = '';

      // If CRM assignment or combined is selected, call backend endpoint
      if (mode === 'crm_only' || mode === 'combined' || assignAsSecondary) {
        const payload = {
          target_staff_id: targetStaffId,
          followup_type: followupType,
          notes: notes,
          assign_as_secondary: assignAsSecondary
        };

        const res = await apiService.post<any>(`/crm/leads/${opt.leadId}/share-details`, payload);
        if (res && res.success) {
          waUrl = res.wa_url || '';
          waText = res.wa_message || '';
          if (opt.onShared) opt.onShared(res);
        } else {
          throw new Error(res?.detail || res?.message || 'Failed to assign lead in CRM');
        }
      }

      // If WhatsApp dispatch requested
      if (mode === 'wa_only' || mode === 'combined') {
        if (!waUrl) {
          const cleanPhone = (targetStaff.phone || '').replace(/\D/g, '').slice(-10);
          if (!cleanPhone) {
            alert(`Colleague ${targetStaff.name} does not have a valid mobile number for WhatsApp.`);
          } else {
            const previewText = document.getElementById('usmMessagePreview')?.textContent || '';
            waUrl = `https://wa.me/91${cleanPhone}?text=${encodeURIComponent(previewText)}`;
          }
        }

        if (waUrl) {
          window.open(waUrl, '_blank');
        }
      }

      const modeMsg = mode === 'crm_only'
        ? `Lead successfully assigned to ${targetStaff.name} in CRM!`
        : mode === 'wa_only'
        ? `WhatsApp launched for ${targetStaff.name}!`
        : `Lead assigned in CRM and WhatsApp opened for ${targetStaff.name}!`;

      alert(`✅ ${modeMsg}`);
      this.close();
    } catch (err: any) {
      console.error('[UnifiedShareLeadModal] Share failed:', err);
      alert(`⚠️ Could not complete lead share: ${err.message || err}`);
    } finally {
      [primaryBtn, crmBtn, waBtn].forEach(b => { if (b) b.disabled = false; });
    }
  }
}

export const unifiedShareLeadModal = new UnifiedShareLeadModal();
