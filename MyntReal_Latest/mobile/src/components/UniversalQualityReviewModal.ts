/**
 * Universal Quality Review Modal for Mobile Web and Capacitor (Android / iOS)
 * Parity with Web Universal Quality Review Modal (/staff/call-quality and staff_crm_dashboard)
 * DC Protocol: DC_MOBILE_QUALITY_REVIEW_001
 */

import { apiService } from '../services/api.service';

export interface QualityReviewModalOptions {
  callLogId?: number | string;
  callSessionId?: string;
  phone?: string;
  leadId?: number | string;
  onSaved?: (review: any) => void;
}

export class UniversalQualityReviewModal {
  public static open(options: QualityReviewModalOptions): void {
    universalQualityReviewModal.open(options);
  }

  public static close(): void {
    universalQualityReviewModal.close();
  }

  private currentReview: any = null;
  private onSavedCallback: ((review: any) => void) | null = null;
  private scores: Record<string, number> = {
    script_adherence_score: 5,
    tone_attitude_score: 5,
    info_accuracy_score: 5,
    objection_handling_score: 5,
    closing_technique_score: 5,
    disposition_accuracy_score: 5
  };

  public async open(options: QualityReviewModalOptions): Promise<void> {
    this.injectDOM();
    this.onSavedCallback = options.onSaved || null;

    const root = document.getElementById('mobileUqrRoot');
    const content = document.getElementById('mobileUqrContent');
    if (!root || !content) return;

    root.style.display = 'flex';
    content.innerHTML = `
      <div style="text-align:center; padding:36px 16px; color:#64748b;">
        <i class="fas fa-spinner fa-spin" style="font-size:24px; color:#4f46e5; margin-bottom:12px;"></i>
        <div style="font-size:13px; font-weight:600;">Opening Call Quality Audit…</div>
      </div>
    `;

    try {
      const res: any = await apiService.post('/api/v1/call-quality/reviews/open-or-create', {
        call_log_id: Number(options.callLogId) || null,
        call_session_id: options.callSessionId || null,
        phone: options.phone || null,
        lead_id: Number(options.leadId) || null
      });

      if (!res || !res.success) {
        content.innerHTML = `
          <div style="text-align:center; padding:30px 16px; color:#ef4444;">
            <i class="fas fa-exclamation-circle" style="font-size:24px; margin-bottom:8px;"></i>
            <div style="font-size:13px; font-weight:700;">Unable to open review</div>
            <div style="font-size:11.5px; color:#64748b; margin-top:4px;">${this.escape(res?.error || res?.detail || 'Call record not found')}</div>
            <button id="mobileUqrCloseErrBtn" style="margin-top:14px; background:#f1f5f9; border:1px solid #cbd5e1; border-radius:6px; padding:6px 16px; font-size:12px; cursor:pointer;">Close</button>
          </div>
        `;
        document.getElementById('mobileUqrCloseErrBtn')?.addEventListener('click', () => this.close());
        return;
      }

      this.currentReview = res.data?.review || res.data;
      this.initScores(this.currentReview);
      this.renderReviewView(this.currentReview);
    } catch (err: any) {
      content.innerHTML = `
        <div style="text-align:center; padding:30px 16px; color:#ef4444;">
          <i class="fas fa-exclamation-triangle" style="font-size:24px; margin-bottom:8px;"></i>
          <div style="font-size:13px; font-weight:700;">Error opening review</div>
          <div style="font-size:11.5px; color:#64748b; margin-top:4px;">${this.escape(err.message || String(err))}</div>
          <button id="mobileUqrCloseErrBtn" style="margin-top:14px; background:#f1f5f9; border:1px solid #cbd5e1; border-radius:6px; padding:6px 16px; font-size:12px; cursor:pointer;">Close</button>
        </div>
      `;
      document.getElementById('mobileUqrCloseErrBtn')?.addEventListener('click', () => this.close());
    }
  }

  public close(): void {
    const root = document.getElementById('mobileUqrRoot');
    if (root) root.style.display = 'none';
    const audio = root?.querySelector('audio');
    if (audio) {
      try { audio.pause(); } catch (_) {}
    }
    this.currentReview = null;
  }

  private initScores(rev: any): void {
    this.scores = {
      script_adherence_score: Number(rev.script_adherence_score) || 5,
      tone_attitude_score: Number(rev.tone_attitude_score) || 5,
      info_accuracy_score: Number(rev.info_accuracy_score) || 5,
      objection_handling_score: Number(rev.objection_handling_score) || 5,
      closing_technique_score: Number(rev.closing_technique_score) || 5,
      disposition_accuracy_score: Number(rev.disposition_accuracy_score) || 5
    };
  }

  private calcOverallScore(): { score: number; label: string; bg: string; color: string } {
    const sum = Object.values(this.scores).reduce((a, b) => a + b, 0);
    const pct = Math.round((sum / 30) * 100);
    if (pct >= 85) return { score: pct, label: 'Excellent', bg: '#ecfdf5', color: '#047857' };
    if (pct >= 70) return { score: pct, label: 'Good', bg: '#eff6ff', color: '#1d4ed8' };
    if (pct >= 50) return { score: pct, label: 'Average', bg: '#fef3c7', color: '#b45309' };
    return { score: pct, label: 'Needs Improvement', bg: '#fef2f2', color: '#b91c1c' };
  }

  private formatCallDuration(secs: number): string {
    const s = parseInt(String(secs), 10) || 0;
    if (s <= 0) return '0s';
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const r = s % 60;
    if (h > 0) return `${h}h ${m > 0 ? m + 'm ' : ''}${r > 0 ? r + 's' : ''}`.trim();
    if (m > 0) return `${m}m ${r > 0 ? r + 's' : ''}`.trim();
    return `${r}s`;
  }

  private renderReviewView(rev: any): void {
    const content = document.getElementById('mobileUqrContent');
    if (!content) return;

    const ident = rev.call_identity || {};
    const callerName = ident.caller_name || rev.staff_name || 'Staff';
    const recipientName = ident.recipient_name || rev.customer_name || 'Customer';
    const phone = ident.customer_phone || rev.phone_number || rev.customer_phone || '—';
    const direction = (ident.direction || rev.direction || 'outbound').toLowerCase();
    const duration = this.formatCallDuration(ident.duration_seconds || rev.duration_seconds || 0);
    const callTime = rev.sample_date || rev.call_datetime || '—';
    const recUrl = rev.recording_url || ident.recording_url;

    const overall = this.calcOverallScore();

    content.innerHTML = `
      <!-- Header Call Info -->
      <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:12px; margin-bottom:14px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <div style="display:flex; align-items:center; gap:6px;">
            <span style="background:${direction === 'outbound' ? '#dbeafe' : '#e0e7ff'}; color:${direction === 'outbound' ? '#1d4ed8' : '#4338ca'}; font-size:10px; font-weight:800; padding:2px 8px; border-radius:4px; text-transform:uppercase;">
              ${direction === 'outbound' ? '↗ Outbound' : '↙ Inbound'}
            </span>
            <span style="font-size:11px; font-weight:700; color:#334155;">${this.escape(duration)}</span>
          </div>
          <div id="mobileUqrScoreBadge" style="background:${overall.bg}; color:${overall.color}; border:1px solid currentColor; font-size:11px; font-weight:800; padding:2px 8px; border-radius:12px;">
            ${overall.score}% · ${overall.label}
          </div>
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center; font-size:12px; margin-bottom:4px;">
          <div><strong style="color:#0f172a;">${this.escape(callerName)}</strong> <span style="font-size:10px; color:#64748b;">(Caller)</span></div>
          <i class="fas fa-arrow-right" style="color:#94a3b8; font-size:10px;"></i>
          <div><strong style="color:#0f172a;">${this.escape(recipientName)}</strong> <span style="font-size:10px; color:#64748b;">(Recipient)</span></div>
        </div>

        <div style="font-size:11px; color:#64748b; display:flex; justify-content:space-between; align-items:center; margin-top:6px; border-top:1px dashed #e2e8f0; padding-top:6px;">
          <div><i class="fas fa-phone-alt me-1" style="color:#3b82f6;"></i>${this.escape(phone)}</div>
          <div><i class="fas fa-clock me-1"></i>${this.escape(callTime)}</div>
        </div>

        ${recUrl ? `
          <div style="margin-top:10px; padding-top:8px; border-top:1px solid #e2e8f0;">
            <audio controls style="width:100%; height:32px;" preload="metadata">
              <source src="${this.escape(recUrl)}" type="audio/mpeg">
              <source src="${this.escape(recUrl)}" type="audio/wav">
              Audio player not supported.
            </audio>
          </div>
        ` : '<div style="margin-top:8px; font-size:10.5px; color:#94a3b8; text-align:center;"><i class="fas fa-info-circle me-1"></i>No audio recording attached to this session</div>'}
      </div>

      <!-- Rating Parameters (6 Criteria) -->
      <div style="font-size:12px; font-weight:800; color:#1e293b; margin-bottom:8px; display:flex; align-items:center; gap:6px;">
        <i class="fas fa-star" style="color:#f59e0b;"></i> Quality Scoring Parameters (1 - 5 Stars)
      </div>

      <div style="display:flex; flex-direction:column; gap:10px; margin-bottom:14px;">
        ${this.renderStarRow('script_adherence_score', 'Script & Flow Adherence', 'Followed standard script, pitch, and mandatory disclaimers')}
        ${this.renderStarRow('tone_attitude_score', 'Tone & Professionalism', 'Warm, polite, energetic, and professional customer engagement')}
        ${this.renderStarRow('info_accuracy_score', 'Product & Info Accuracy', 'Accurate pricing, scheme parameters, and specifications explained')}
        ${this.renderStarRow('objection_handling_score', 'Customer Handling & Objections', 'Listened attentively and resolved objections effectively')}
        ${this.renderStarRow('closing_technique_score', 'Closing & Next Steps', 'Clear next steps, scheduled follow-up or site visit confirmed')}
        ${this.renderStarRow('disposition_accuracy_score', 'Disposition & CRM Accuracy', 'Correct call outcome, stage, and CRM logging status')}
      </div>

      <!-- Remarks / Audit Notes -->
      <div style="margin-bottom:14px;">
        <label style="font-size:11.5px; font-weight:700; color:#334155; display:block; margin-bottom:4px;">
          Auditor Remarks &amp; Feedback
        </label>
        <textarea id="mobileUqrRemarks" rows="2" placeholder="Enter quality feedback, strengths, or training points..." style="width:100%; box-sizing:border-box; font-size:12px; padding:8px 10px; border:1px solid #cbd5e1; border-radius:8px; resize:vertical;">${this.escape(rev.remarks || '')}</textarea>
      </div>

      <!-- Save & Actions -->
      <div style="display:flex; gap:8px;">
        <button id="mobileUqrSaveBtn" style="flex:2; background:#4f46e5; color:#ffffff; border:none; border-radius:8px; padding:10px; font-size:13px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
          <i class="fas fa-save"></i> Save Quality Review
        </button>
        <button id="mobileUqrCancelBtn" style="flex:1; background:#f1f5f9; color:#475569; border:1px solid #cbd5e1; border-radius:8px; padding:10px; font-size:13px; font-weight:600; cursor:pointer;">
          Cancel
        </button>
      </div>
    `;

    this.bindStarEvents();

    document.getElementById('mobileUqrSaveBtn')?.addEventListener('click', () => this.submitReview());
    document.getElementById('mobileUqrCancelBtn')?.addEventListener('click', () => this.close());
  }

  private renderStarRow(key: string, title: string, subtitle: string): string {
    const curVal = this.scores[key] || 5;
    let starsHtml = '';
    for (let i = 1; i <= 5; i++) {
      const active = i <= curVal;
      starsHtml += `
        <button type="button" class="uqr-star-btn" data-key="${key}" data-val="${i}" style="background:none; border:none; padding:2px; font-size:18px; cursor:pointer; color:${active ? '#f59e0b' : '#cbd5e1'};">
          ★
        </button>
      `;
    }

    return `
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:8px 10px; display:flex; justify-content:space-between; align-items:center;">
        <div style="max-width:60%;">
          <div style="font-size:12px; font-weight:700; color:#0f172a;">${title}</div>
          <div style="font-size:10px; color:#64748b;">${subtitle}</div>
        </div>
        <div style="display:flex; align-items:center;">
          ${starsHtml}
          <span class="uqr-star-val" data-val-for="${key}" style="font-size:11px; font-weight:800; color:#0f172a; margin-left:6px; min-width:14px; text-align:right;">${curVal}</span>
        </div>
      </div>
    `;
  }

  private bindStarEvents(): void {
    const content = document.getElementById('mobileUqrContent');
    if (!content) return;

    content.querySelectorAll('.uqr-star-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const t = e.currentTarget as HTMLElement;
        const key = t.dataset.key;
        const val = Number(t.dataset.val);
        if (!key || !val) return;

        this.scores[key] = val;

        // Update star visual for this row
        const row = t.closest('div');
        if (row) {
          row.querySelectorAll('.uqr-star-btn').forEach(s => {
            const sVal = Number((s as HTMLElement).dataset.val);
            (s as HTMLElement).style.color = sVal <= val ? '#f59e0b' : '#cbd5e1';
          });
          const valEl = row.querySelector(`[data-val-for="${key}"]`);
          if (valEl) valEl.textContent = String(val);
        }

        // Update overall badge
        const overall = this.calcOverallScore();
        const badge = document.getElementById('mobileUqrScoreBadge');
        if (badge) {
          badge.style.background = overall.bg;
          badge.style.color = overall.color;
          badge.textContent = `${overall.score}% · ${overall.label}`;
        }
      });
    });
  }

  private async submitReview(): Promise<void> {
    if (!this.currentReview || !this.currentReview.id) return;

    const saveBtn = document.getElementById('mobileUqrSaveBtn') as HTMLButtonElement | null;
    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving…';
    }

    const remarksEl = document.getElementById('mobileUqrRemarks') as HTMLTextAreaElement | null;
    const remarks = remarksEl?.value?.trim() || '';

    try {
      const payload = {
        script_adherence_score: this.scores.script_adherence_score,
        tone_attitude_score: this.scores.tone_attitude_score,
        info_accuracy_score: this.scores.info_accuracy_score,
        objection_handling_score: this.scores.objection_handling_score,
        closing_technique_score: this.scores.closing_technique_score,
        disposition_accuracy_score: this.scores.disposition_accuracy_score,
        remarks: remarks
      };

      const res: any = await apiService.post(`/api/v1/call-quality/reviews/${this.currentReview.id}/submit`, payload);

      if (res && res.success) {
        alert('Quality review saved successfully!');
        if (this.onSavedCallback) {
          this.onSavedCallback(res.data?.review || res.data);
        }
        this.close();

        // Trigger dynamic refresh if on CRM page or Lead History
        if (typeof (window as any).refreshCrmQualityData === 'function') {
          (window as any).refreshCrmQualityData();
        }
      } else {
        alert('Failed to save review: ' + (res?.error || res?.detail || 'Unknown error'));
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.innerHTML = '<i class="fas fa-save"></i> Save Quality Review';
        }
      }
    } catch (err: any) {
      alert('Error saving review: ' + (err.message || String(err)));
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="fas fa-save"></i> Save Quality Review';
      }
    }
  }

  private injectDOM(): void {
    if (document.getElementById('mobileUqrRoot')) return;

    const root = document.createElement('div');
    root.id = 'mobileUqrRoot';
    root.style.cssText = `
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.7);
      z-index: 100000005;
      display: none;
      align-items: flex-end;
      justify-content: center;
      backdrop-filter: blur(2px);
      box-sizing: border-box;
    `;

    root.innerHTML = `
      <div id="mobileUqrCard" style="background:#ffffff; width:100%; max-width:600px; max-height:92vh; border-radius:18px 18px 0 0; display:flex; flex-direction:column; box-shadow:0 -4px 20px rgba(0,0,0,0.15); animation:muqrSlideUp 0.25s ease-out;">
        <div style="padding:14px 16px; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center;">
          <div style="font-size:14px; font-weight:800; color:#0f172a; display:flex; align-items:center; gap:8px;">
            <i class="fas fa-clipboard-check" style="color:#4f46e5;"></i> Dynamic Call Quality Audit
          </div>
          <button id="mobileUqrCloseTopBtn" style="background:none; border:none; font-size:22px; color:#64748b; cursor:pointer; line-height:1; padding:2px 6px;">&times;</button>
        </div>
        <div id="mobileUqrContent" style="padding:14px 16px; overflow-y:auto; flex:1; -webkit-overflow-scrolling:touch;"></div>
      </div>
      <style>
        @keyframes muqrSlideUp {
          from { transform: translateY(100%); }
          to { transform: translateY(0); }
        }
      </style>
    `;

    root.addEventListener('click', (e) => {
      if (e.target === root) this.close();
    });

    document.body.appendChild(root);

    document.getElementById('mobileUqrCloseTopBtn')?.addEventListener('click', () => this.close());
  }

  private escape(str: string): string {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }
}

export const universalQualityReviewModal = new UniversalQualityReviewModal();

// Register globally on window for mobile inline triggers
if (typeof window !== 'undefined') {
  (window as any).openUniversalQualityReview = (opts: any) => universalQualityReviewModal.open(opts);
  (window as any).closeUniversalQualityReview = () => universalQualityReviewModal.close();
}
