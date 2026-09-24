/**
 * Universal Lead History Modal for Mobile Web and Capacitor (Android / iOS)
 * Unified 3-Tab Experience:
 *   1. Calls & Recordings
 *   2. Messages / Chat
 *   3. Lead Change History
 */

import { apiService } from '../services/api.service';
import { UniversalQualityReviewModal } from './UniversalQualityReviewModal';

export interface UniversalHistoryModalOptions {
  entityType?: 'crm_lead' | 'vgk_member';
  entityId?: number | string;
  leadId?: number | string;
  memberId?: number | string;
  name?: string;
  phone?: string;
  category?: string;
  status?: string;
  stage?: string;
  assignedTo?: string;
}

export class UniversalLeadHistoryModal {
  public static open(options: UniversalHistoryModalOptions): void {
    universalLeadHistoryModal.open(options);
  }

  public static close(): void {
    universalLeadHistoryModal.close();
  }

  private currentEntity: any = null;
  private activeTab: 'calls' | 'messages' | 'changes' = 'calls';
  private changesSubfilter: string = 'all';
  private activeAudio: HTMLAudioElement | null = null;
  private cache: { calls: any; messages: any; changes: Record<string, any> } = {
    calls: null,
    messages: null,
    changes: {}
  };

  public open(options: UniversalHistoryModalOptions): void {
    if (!options || (!options.entityId && !options.leadId && !options.memberId && !options.phone)) {
      console.warn('[UniversalLeadHistoryModal] Invalid options:', options);
      return;
    }

    this.injectDOM();
    this.stopAudio();

    const entityType = options.entityType || (options.memberId ? 'vgk_member' : 'crm_lead');
    const entityId = parseInt(String(options.entityId || options.leadId || options.memberId || 0), 10) || 0;

    this.currentEntity = {
      entityType,
      entityId,
      name: options.name || '',
      phone: options.phone || '',
      category: options.category || '',
      status: options.status || '',
      stage: options.stage || '',
      assignedTo: options.assignedTo || ''
    };

    this.cache = { calls: null, messages: null, changes: {} };
    this.activeTab = 'calls';
    this.changesSubfilter = 'all';

    this.populateHeader();

    const root = document.getElementById('mobileUhmRoot');
    if (root) root.style.display = 'flex';

    this.switchTab('calls');

    // Async fetch summary to update badges and names
    void this.fetchSummary();
  }

  public close(): void {
    this.stopAudio();
    const root = document.getElementById('mobileUhmRoot');
    if (root) root.style.display = 'none';
  }

  public switchTab(tab: 'calls' | 'messages' | 'changes'): void {
    this.activeTab = tab;
    this.stopAudio();

    ['Calls', 'Messages', 'Changes'].forEach(k => {
      const btn = document.getElementById('muhmTab' + k);
      if (!btn) return;
      if (k.toLowerCase() === tab.toLowerCase()) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    const subBar = document.getElementById('muhmSubfilterBar');
    if (subBar) {
      subBar.style.display = tab === 'changes' ? 'flex' : 'none';
    }

    void this.loadTabData(tab);
  }

  public setSubfilter(subfilter: string): void {
    this.changesSubfilter = subfilter;
    const chips = document.querySelectorAll('#muhmSubfilterBar .muhm-subchip');
    chips.forEach(c => {
      c.classList.remove('active');
      const txt = (c.textContent || '').toLowerCase();
      if (txt.includes(subfilter.toLowerCase()) ||
          (subfilter === 'all' && txt.includes('all')) ||
          (subfilter === 'audit' && txt.includes('field'))) {
        c.classList.add('active');
      }
    });
    void this.loadTabData('changes');
  }

  private stopAudio(): void {
    if (this.activeAudio) {
      try { this.activeAudio.pause(); } catch (_) {}
      this.activeAudio = null;
    }
    const audios = document.querySelectorAll('#mobileUhmRoot audio');
    audios.forEach(a => {
      try { (a as HTMLAudioElement).pause(); } catch (_) {}
    });
  }

  private populateHeader(): void {
    const nameEl = document.getElementById('muhmName');
    if (nameEl) nameEl.textContent = this.currentEntity.name || (this.currentEntity.entityType === 'vgk_member' ? 'Channel Partner' : `Lead #${this.currentEntity.entityId}`);

    const badgeEl = document.getElementById('muhmBadge');
    if (badgeEl) {
      if (this.currentEntity.entityType === 'vgk_member') {
        badgeEl.textContent = 'VGK Member';
        badgeEl.className = 'muhm-badge muhm-badge-vgk';
      } else {
        badgeEl.textContent = 'CRM Lead';
        badgeEl.className = 'muhm-badge muhm-badge-lead';
      }
    }

    const phoneEl = document.getElementById('muhmPhone');
    if (phoneEl) phoneEl.textContent = this.currentEntity.phone || '—';

    const metaEl = document.getElementById('muhmMeta');
    if (metaEl) {
      const parts = [];
      if (this.currentEntity.category) parts.push(this.currentEntity.category);
      if (this.currentEntity.stage || this.currentEntity.status) parts.push(this.currentEntity.stage || this.currentEntity.status);
      if (this.currentEntity.assignedTo) parts.push(`Assigned: ${this.currentEntity.assignedTo}`);
      metaEl.textContent = parts.join(' • ') || '—';
    }

    ['Calls', 'Messages', 'Changes'].forEach(k => {
      const el = document.getElementById('muhmCount' + k);
      if (el) el.textContent = '…';
    });
  }

  private async fetchSummary(): Promise<void> {
    try {
      const res: any = await apiService.get(
        `/api/v1/crm/universal-history/entity-summary?entity_type=${this.currentEntity.entityType}&entity_id=${this.currentEntity.entityId || 0}&phone=${encodeURIComponent(this.currentEntity.phone || '')}&name=${encodeURIComponent(this.currentEntity.name || '')}`
      );
      if (res && res.success && res.entity) {
        const nameEl = document.getElementById('muhmName');
        if (nameEl && res.entity.name) nameEl.textContent = res.entity.name;

        const phoneEl = document.getElementById('muhmPhone');
        if (phoneEl) phoneEl.textContent = res.entity.display_phone || res.entity.primary_phone || '—';

        if (res.counts) {
          const cC = document.getElementById('muhmCountCalls');
          if (cC) cC.textContent = String(res.counts.calls || 0);
          const cM = document.getElementById('muhmCountMessages');
          if (cM) cM.textContent = String(res.counts.messages || 0);
          const cCh = document.getElementById('muhmCountChanges');
          if (cCh) cCh.textContent = String(res.counts.changes || 0);
        }
      }
    } catch (err) {
      console.warn('[UniversalHistory] Failed to fetch mobile entity summary:', err);
    }
  }

  private async loadTabData(tabName: string): Promise<void> {
    const contentEl = document.getElementById('muhmContent');
    if (!contentEl || !this.currentEntity) return;

    if (tabName === 'calls') {
      const renderAndBind = (callsList: any[]) => {
        contentEl.innerHTML = this.renderCalls(callsList);
        contentEl.querySelectorAll('.muhm-review-call-btn').forEach(btn => {
          btn.addEventListener('click', (e) => {
            const t = e.currentTarget as HTMLElement;
            const callId = Number(t.dataset.callid) || 0;
            const sessionId = t.dataset.sessionid || '';
            const phone = t.dataset.phone || '';
            const leadId = Number(t.dataset.leadid) || 0;
            UniversalQualityReviewModal.open({
              callLogId: callId,
              callSessionId: sessionId,
              phone: phone,
              leadId: leadId,
              onSaved: () => {
                this.cache.calls = null;
                this.loadTabData('calls');
              }
            });
          });
        });
      };

      if (this.cache.calls) {
        renderAndBind(this.cache.calls.items);
        return;
      }
      contentEl.innerHTML = '<div class="muhm-loading">Loading calls & recordings…</div>';
      try {
        const res: any = await apiService.get(
          `/api/v1/crm/universal-history/calls?entity_type=${this.currentEntity.entityType}&entity_id=${this.currentEntity.entityId || 0}&phone=${encodeURIComponent(this.currentEntity.phone || '')}&name=${encodeURIComponent(this.currentEntity.name || '')}&limit=100`
        );
        if (res && res.success) {
          this.cache.calls = res;
          const cnt = document.getElementById('muhmCountCalls');
          if (cnt) cnt.textContent = String(res.total_calls || 0);
          renderAndBind(res.items);
        } else {
          contentEl.innerHTML = `<div class="muhm-empty">${this.escape(res?.detail || 'Failed to load calls')}</div>`;
        }
      } catch (err: any) {
        contentEl.innerHTML = `<div class="muhm-empty">Error loading calls: ${this.escape(err.message)}</div>`;
      }
    } else if (tabName === 'messages') {
      if (this.cache.messages) {
        contentEl.innerHTML = this.renderMessages(this.cache.messages.items);
        return;
      }
      contentEl.innerHTML = '<div class="muhm-loading">Loading messages & chat…</div>';
      try {
        const res: any = await apiService.get(
          `/api/v1/crm/universal-history/messages?entity_type=${this.currentEntity.entityType}&entity_id=${this.currentEntity.entityId || 0}&phone=${encodeURIComponent(this.currentEntity.phone || '')}&name=${encodeURIComponent(this.currentEntity.name || '')}&limit=100`
        );
        if (res && res.success) {
          this.cache.messages = res;
          const cnt = document.getElementById('muhmCountMessages');
          if (cnt) cnt.textContent = String(res.total_messages || 0);
          contentEl.innerHTML = this.renderMessages(res.items);
        } else {
          contentEl.innerHTML = `<div class="muhm-empty">${this.escape(res?.detail || 'Failed to load messages')}</div>`;
        }
      } catch (err: any) {
        contentEl.innerHTML = `<div class="muhm-empty">Error loading messages: ${this.escape(err.message)}</div>`;
      }
    } else if (tabName === 'changes') {
      const sub = this.changesSubfilter || 'all';
      if (this.cache.changes[sub]) {
        contentEl.innerHTML = this.renderChanges(this.cache.changes[sub].items);
        return;
      }
      contentEl.innerHTML = '<div class="muhm-loading">Loading change history…</div>';
      try {
        const res: any = await apiService.get(
          `/api/v1/crm/universal-history/changes?entity_type=${this.currentEntity.entityType}&entity_id=${this.currentEntity.entityId || 0}&phone=${encodeURIComponent(this.currentEntity.phone || '')}&name=${encodeURIComponent(this.currentEntity.name || '')}&subfilter=${sub}&limit=100`
        );
        if (res && res.success) {
          this.cache.changes[sub] = res;
          if (sub === 'all') {
            const cnt = document.getElementById('muhmCountChanges');
            if (cnt) cnt.textContent = String(res.total_changes || 0);
          }
          contentEl.innerHTML = this.renderChanges(res.items);
        } else {
          contentEl.innerHTML = `<div class="muhm-empty">${this.escape(res?.detail || 'Failed to load changes')}</div>`;
        }
      } catch (err: any) {
        contentEl.innerHTML = `<div class="muhm-empty">Error loading changes: ${this.escape(err.message)}</div>`;
      }
    }
  }

  private renderCallFromBadge(c: any): string {
    const page = (c.dialed_page || c.call_from || c.source || '').trim();
    const lower = page.toLowerCase();
    const devId = (c.device_call_id || c.call_session_id || '').toLowerCase();
    const type = (c.call_type || c.direction || '').toUpperCase();

    // 1. Auto Dialer
    if (lower.includes('auto') || lower.includes('dialer') || devId.includes('cda_') || type === 'DIALER') {
      return '<span style="background:#f5f3ff;color:#6b21a8;border:1px solid #ddd6fe;font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-robot" style="color:#6b21a8;margin-right:4px;"></i>Auto Dialer</span>';
    }
    // 2. My Leads
    if (lower.includes('my lead') || lower === 'my leads') {
      return '<span style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-user-check" style="color:#1d4ed8;margin-right:4px;"></i>My Leads</span>';
    }
    // 3. Staff Leads
    if (lower.includes('staff lead') || lower === 'staff leads') {
      return '<span style="background:#f0fdf4;color:#15803d;border:1px solid #bbf7d0;font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-users" style="color:#15803d;margin-right:4px;"></i>Staff Leads</span>';
    }
    // 4. CRM Dashboard
    if (lower.includes('crm dashboard') || lower.includes('dashboard')) {
      return '<span style="background:#fdf2f8;color:#be185d;border:1px solid #fbcfe8;font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-chart-line" style="color:#be185d;margin-right:4px;"></i>CRM Dashboard</span>';
    }
    // 5. Softphone Center / Hub
    if (lower.includes('softphone center') || lower.includes('softphone hub') || lower === 'softphone' || lower === 'plivo webrtc') {
      return '<span style="background:#e0f2fe;color:#0369a1;border:1px solid #bae6fd;font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-headset" style="color:#0369a1;margin-right:4px;"></i>Softphone Center</span>';
    }
    // 6. Operator Calls
    if (lower.includes('operator')) {
      return '<span style="background:#fffbeb;color:#b45309;border:1px solid #fde68a;font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-head-side-headphones" style="color:#b45309;margin-right:4px;"></i>Operator Calls</span>';
    }
    // 7. WhatsApp Center
    if (lower.includes('whatsapp')) {
      return '<span style="background:#f0fdf4;color:#16a34a;border:1px solid #86efac;font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fab fa-whatsapp" style="color:#16a34a;margin-right:4px;"></i>WhatsApp Center</span>';
    }
    // 8. Day Planner
    if (lower.includes('planner')) {
      return '<span style="background:#faf5ff;color:#7e22ce;border:1px solid #e9d5ff;font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-calendar-day" style="color:#7e22ce;margin-right:4px;"></i>Day Planner</span>';
    }
    // 9. Tasks
    if (lower.includes('task')) {
      return '<span style="background:#f1f5f9;color:#334155;border:1px solid #cbd5e1;font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-tasks" style="color:#334155;margin-right:4px;"></i>Tasks</span>';
    }
    // 10. Master Leads
    if (lower.includes('master')) {
      return '<span style="background:#fef3c7;color:#92400e;border:1px solid #fcd34d;font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-database" style="color:#92400e;margin-right:4px;"></i>Master Leads</span>';
    }
    // 11. Bank Wise Leads
    if (lower.includes('bank')) {
      return '<span style="background:#ecfdf5;color:#065f46;border:1px solid #a7f3d0;font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-landmark" style="color:#065f46;margin-right:4px;"></i>Bank Wise Leads</span>';
    }
    // 12. Inbound DID / Incoming
    if (lower.includes('inbound') || lower.includes('did') || type === 'INCOMING' || type === 'INBOUND') {
      return '<span style="background:#ecfdf5;color:#047857;border:1px solid #a7f3d0;font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-phone-arrow-down-left" style="color:#047857;margin-right:4px;"></i>Inbound DID</span>';
    }
    // 13. Mobile App / Native SIM
    if (lower.includes('mobile') || lower.includes('sim') || lower.includes('native')) {
      return '<span style="background:#ecfdf5;color:#047857;border:1px solid #a7f3d0;font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-sim-card" style="color:#047857;margin-right:4px;"></i>Native SIM</span>';
    }

    // Fallback
    return `<span style="background:#f8fafc;color:#475569;border:1px solid #cbd5e1;font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:4px;display:inline-flex;align-items:center;"><i class="fas fa-file-alt" style="margin-right:4px;color:#94a3b8;"></i>${this.escape(page || 'My Leads')}</span>`;
  }

  private renderCalls(items: any[]): string {
    if (!items || !items.length) {
      return '<div class="muhm-empty">No call records or recordings found.</div>';
    }

    return items.map(c => {
      const isOut = (c.direction || '').toLowerCase() === 'outbound';
      const dirSymbol = isOut ? '↗ Outbound' : '↙ Inbound';
      const durText = this.formatDuration(c.duration_seconds);

      const durSec = Number(c.duration_seconds || 0);
      let recHtml = '';
      if (c.has_recording && c.recording_url) {
        recHtml = `
          <div style="margin-top:6px;padding-top:6px;border-top:1px dashed #e2e8f0;">
            <audio controls style="width:100%;height:32px" preload="none">
              <source src="${this.escape(c.recording_url)}" type="audio/mpeg">
              <source src="${this.escape(c.recording_url)}" type="audio/wav">
              Audio not supported.
            </audio>
          </div>
        `;
      } else if (durSec === 0) {
        recHtml = `
          <div style="margin-top:5px;font-size:10.5px;color:#94a3b8;display:flex;align-items:center;gap:4px;">
            <i class="fas fa-phone-slash" style="font-size:9.5px;"></i>
            <span>Unanswered / Missed (0s — no audio captured)</span>
          </div>
        `;
      } else {
        recHtml = `
          <div style="margin-top:5px;font-size:10.5px;color:#94a3b8;display:flex;align-items:center;gap:4px;">
            <i class="fas fa-volume-mute" style="font-size:9.5px;"></i>
            <span>Audio recording unavailable</span>
          </div>
        `;
      }

      const callLogId = (c.id && String(c.id).startsWith('scl_')) ? (c.raw_id || 0) : 0;
      const callSessionId = c.call_session_id || '';
      const phone = this.escape(c.phone || (this.currentEntity && this.currentEntity.phone) || '');
      const leadId = (this.currentEntity && this.currentEntity.entityId) ? this.currentEntity.entityId : 0;

      let qaScoreBadge = '';
      if (c.quality_score != null && c.quality_score !== undefined) {
        qaScoreBadge = `<span style="font-size:10px;font-weight:700;padding:2px 6px;border-radius:4px;background:#ecfdf5;color:#047857;border:1px solid #a7f3d0;display:inline-flex;align-items:center;">★ ${c.quality_score}% QA</span>`;
      }

      const hasRecordingAvailable = Boolean(c.has_recording && c.recording_url);
      let reviewBtn = '';
      if (hasRecordingAvailable || c.quality_score != null) {
        reviewBtn = `
          <button class="muhm-review-call-btn" data-callid="${callLogId}" data-sessionid="${this.escape(callSessionId)}" data-phone="${phone}" data-leadid="${leadId}" style="background:#fef3c7;color:#92400e;border:1px solid #fde68a;border-radius:4px;padding:2px 8px;font-size:10.5px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;">
            <i class="fas fa-clipboard-check me-1"></i>${c.quality_score != null ? 'QA Reviewed' : 'Review Call'}
          </button>
        `;
      }

      return `
        <div class="muhm-card">
          <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
              <div style="font-weight:600;font-size:13px;color:#0f172a">${this.escape(c.details || 'Call')}</div>
              <div style="font-size:11px;color:#475569;margin-top:2px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                <span>${this.formatDate(c.timestamp)}</span>
                <span>•</span>
                <span style="font-weight:700;background:#e0f2fe;color:#0369a1;padding:1px 6px;border-radius:4px;font-size:10.5px;">
                  Handled by: ${this.escape(c.handled_by || c.staff_name || 'Staff')}
                </span>
              </div>
            </div>
            <div style="text-align:right">
              ${this.renderCallFromBadge(c)}
              <div style="font-size:11px;color:#334155;margin-top:2px;font-weight:500">${this.escape(c.status || durText)}</div>
            </div>
          </div>
          ${(qaScoreBadge || reviewBtn) ? `
            <div style="display:flex;justify-content:flex-end;align-items:center;gap:6px;margin-top:6px;">
              ${qaScoreBadge}
              ${reviewBtn}
            </div>
          ` : ''}
          ${recHtml}
        </div>
      `;
    }).join('');
  }

  private renderMessages(items: any[]): string {
    if (!items || !items.length) {
      return '<div class="muhm-empty">No messages or chat history found.</div>';
    }

    return '<div style="display:flex;flex-direction:column;gap:12px">' +
      items.map(m => {
        const isOut = (m.direction || '').toLowerCase() === 'outbound';
        const cls = isOut ? 'outbound' : 'inbound';
        let mediaHtml = '';
        const mediaUrl = m.media_url || '';
        const mediaType = (m.media_type || '').toLowerCase();
        const mediaName = m.media_name || 'Attachment';
        const mime = (m.media_mime_type || '').toLowerCase();

        if (mediaUrl) {
          const isPdf = (mediaType === 'document' && (mediaName.toLowerCase().endsWith('.pdf') || mime.includes('pdf'))) || mediaUrl.toLowerCase().includes('.pdf');
          const isImg = mediaType === 'image' || mime.startsWith('image/') || /\.(jpg|jpeg|png|webp|gif)(\?.*)?$/i.test(mediaUrl);
          const isAudio = mediaType === 'audio' || mime.startsWith('audio/') || /\.(mp3|ogg|wav|aac|m4a)(\?.*)?$/i.test(mediaUrl);

          if (isImg) {
            mediaHtml = `
              <div class="muhm-media-img-box">
                <a href="${this.escape(mediaUrl)}" target="_blank" rel="noopener noreferrer">
                  <img src="${this.escape(mediaUrl)}" alt="${this.escape(mediaName)}" onerror="this.style.display='none';this.parentElement.nextElementSibling.querySelector('.muhm-media-name').textContent='[Image attachment]';" />
                </a>
                <div class="muhm-media-img-bar">
                  <span class="muhm-media-name" title="${this.escape(mediaName)}">${this.escape(mediaName)}</span>
                  <a href="${this.escape(mediaUrl)}" download="${this.escape(mediaName)}" class="muhm-dl-btn" title="Download Image">
                    ⬇ Download
                  </a>
                </div>
              </div>
            `;
          } else if (isAudio) {
            mediaHtml = `
              <div style="margin-top:6px">
                <audio controls style="width:100%;height:32px" preload="none">
                  <source src="${this.escape(mediaUrl)}" type="${this.escape(mime || 'audio/mpeg')}">
                  Audio not supported.
                </audio>
              </div>
            `;
          } else {
            // PDF or Document
            mediaHtml = `
              <div class="muhm-media-doc-box">
                <div style="display:flex;align-items:center;gap:6px;min-width:0;flex:1;">
                  <span style="font-size:18px;color:${isPdf ? '#ef4444' : '#2563eb'};flex-shrink:0;">${isPdf ? '📄' : '📁'}</span>
                  <div style="min-width:0;flex:1;">
                    <div class="muhm-media-name" title="${this.escape(mediaName)}">${this.escape(mediaName)}</div>
                    <div style="font-size:9.5px;color:#64748b;">${this.escape(mime || (isPdf ? 'PDF Document' : 'Document'))}</div>
                  </div>
                </div>
                <div style="display:flex;align-items:center;gap:4px;flex-shrink:0;">
                  <a href="${this.escape(mediaUrl)}" target="_blank" rel="noopener noreferrer" class="muhm-doc-view-btn" title="View">View</a>
                  <a href="${this.escape(mediaUrl)}" download="${this.escape(mediaName)}" class="muhm-dl-btn" title="Download">⬇</a>
                </div>
              </div>
            `;
          }
        }

        const msgStatus = (m.status || '').toLowerCase();
        let statusHtml = '';
        if (isOut) {
          if (msgStatus === 'failed') {
            statusHtml = `<span class="muhm-status-failed" title="${this.escape(m.failure_reason || m.error_message || 'Delivery failed')}">⚠ Failed${m.error_code ? ' (' + this.escape(m.error_code) + ')' : ''}</span>`;
          } else if (msgStatus === 'read') {
            statusHtml = `<span class="muhm-status-badge" style="color:#0284c7" title="Read ${this.formatDate(m.read_at || m.timestamp)}"><span style="letter-spacing:-1px">✓✓</span> Read</span>`;
          } else if (msgStatus === 'delivered') {
            statusHtml = `<span class="muhm-status-badge" style="color:#64748b" title="Delivered ${this.formatDate(m.delivered_at || m.timestamp)}"><span style="letter-spacing:-1px">✓✓</span> Delivered</span>`;
          } else if (msgStatus === 'queued') {
            statusHtml = `<span class="muhm-status-badge" style="color:#d97706" title="Queued">⏳ Queued</span>`;
          } else {
            statusHtml = `<span class="muhm-status-badge" style="color:#64748b" title="Sent">✓ Sent</span>`;
          }
        } else {
          statusHtml = `<span class="muhm-status-badge" style="color:#059669" title="Received">↙ Received</span>`;
        }

        let errSnippet = '';
        if (isOut && msgStatus === 'failed' && (m.failure_reason || m.error_message)) {
          errSnippet = `<div class="muhm-error-snippet">ℹ ${this.escape(m.failure_reason || m.error_message)}</div>`;
        }

        const bodyText = m.message_text ? `<div style="white-space:pre-wrap">${this.escape(m.message_text)}</div>` : '';

        return `
          <div class="muhm-chat-row ${cls}">
            <div style="font-size:10.5px;color:#64748b;margin-bottom:2px;display:flex;align-items:center;gap:4px;${isOut ? 'justify-content:flex-end' : ''}">
              <span>${this.escape(m.sender_name || (isOut ? 'Staff' : 'Customer'))}</span>
              <span style="font-weight:normal;opacity:0.75">• ${this.escape(m.channel || 'WA')}</span>
            </div>
            <div class="muhm-bubble">
              ${bodyText}
              ${mediaHtml}
              ${errSnippet}
              <div class="muhm-chat-meta-bar">
                <span style="font-size:9.5px;color:#64748b">${this.formatDate(m.timestamp)}</span>
                ${statusHtml}
              </div>
            </div>
          </div>
        `;
      }).join('') +
    '</div>';
  }

  private renderChanges(items: any[]): string {
    if (!items || !items.length) {
      return '<div class="muhm-empty">No change history or notes found.</div>';
    }

    // Group changes into a single box per specific date
    const groups: Array<{ dateKey: string; items: any[] }> = [];
    const groupMap: Record<string, { dateKey: string; items: any[] }> = {};

    items.forEach(ch => {
      let dateKey = 'General History';
      if (ch.timestamp) {
        try {
          const d = new Date(ch.timestamp);
          if (!isNaN(d.getTime())) {
            dateKey = d.toLocaleDateString('en-IN', {
              day: '2-digit',
              month: 'short',
              year: 'numeric'
            });
          }
        } catch (_) {}
      }
      const key = dateKey;

      if (!groupMap[key]) {
        groupMap[key] = {
          dateKey,
          items: []
        };
        groups.push(groupMap[key]);
      }
      groupMap[key].items.push(ch);
    });

    return '<div style="padding-left:14px;border-left:2px solid #e2e8f0;display:flex;flex-direction:column;gap:12px">' +
      groups.map(grp => {
        let changesHtml = '';
        grp.items.forEach(ch => {
          let oldNewHtml = '';
          if (ch.old_val || ch.new_val) {
            oldNewHtml = `
              <div style="font-size:11px;margin-top:3px;word-break:break-word;">
                ${ch.old_val ? `<span style="color:#ef4444;text-decoration:line-through;margin-right:4px">${this.escape(ch.old_val)}</span> → ` : ''}
                <span style="color:#10b981;font-weight:600">${this.escape(ch.new_val || '')}</span>
              </div>
            `;
          }

          const isCall = ch.category === 'call';
          const isNote = ch.category === 'note';
          const isAsgn = ch.category === 'assignment';
          const isFu   = ch.category === 'followup';

          let rowBg = '#f8fafc';
          let rowBorder = '#e2e8f0';
          let titleColor = '#0f172a';
          let icon = '✏️ ';

          if (isCall) {
            rowBg = '#f0fdf4';
            rowBorder = '#bbf7d0';
            titleColor = '#166534';
            icon = '📞 ';
          } else if (isNote) {
            rowBg = '#fffbeb';
            rowBorder = '#fde68a';
            titleColor = '#92400e';
            icon = '📝 ';
          } else if (isFu) {
            rowBg = '#f5f3ff';
            rowBorder = '#ddd6fe';
            titleColor = '#5b21b6';
            icon = '📅 ';
          } else if (isAsgn) {
            rowBg = '#eff6ff';
            rowBorder = '#bfdbfe';
            titleColor = '#1e40af';
            icon = '👤 ';
          }

          let recHtml = '';
          if (isCall && ch.has_recording && ch.recording_url) {
            recHtml = `
              <div style="margin-top:6px;padding-top:6px;border-top:1px dashed #cbd5e1;">
                <audio controls style="width:100%;height:30px" preload="none">
                  <source src="${this.escape(ch.recording_url)}" type="audio/mpeg">
                  <source src="${this.escape(ch.recording_url)}" type="audio/wav">
                  Audio not supported.
                </audio>
              </div>
            `;
          }

          let handledOrAuthorBadge = '';
          if (isCall) {
            handledOrAuthorBadge = `<span style="font-size:10px;font-weight:700;color:#15803d;background:#dcfce7;padding:1px 5px;border-radius:4px;">Handled by: ${this.escape(ch.handled_by || ch.author_name || 'Staff')}</span>`;
          } else {
            handledOrAuthorBadge = `<span style="font-size:10px;font-weight:600;color:#475569;background:#e2e8f0;padding:1px 5px;border-radius:4px;">By: ${this.escape(ch.author_name || ch.handled_by || 'Staff')}</span>`;
          }

          let itemTime = '';
          if (ch.timestamp) {
            try {
              const dt = new Date(ch.timestamp);
              if (!isNaN(dt.getTime())) {
                itemTime = dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
              }
            } catch (_) {}
          }

          changesHtml += `
            <div style="background:${rowBg};border:1px solid ${rowBorder};border-radius:6px;padding:8px 10px;margin-bottom:6px;">
              <div style="display:flex;justify-content:space-between;align-items:center;gap:4px;flex-wrap:wrap;">
                <span style="font-size:12px;font-weight:600;color:${titleColor}">${icon}${this.escape(ch.title || ch.event_type || 'Change')}</span>
                <div style="display:flex;align-items:center;gap:4px;">
                  ${handledOrAuthorBadge}
                  ${itemTime ? `<span style="font-size:10px;color:#94a3b8">${this.escape(itemTime)}</span>` : ''}
                </div>
              </div>
              ${ch.details ? `<div style="font-size:11px;color:#475569;margin-top:2px;word-break:break-word;">${this.escape(ch.details)}</div>` : ''}
              ${oldNewHtml}
              ${recHtml}
            </div>
          `;
        });

        return `
          <div style="position:relative">
            <div class="muhm-dot"></div>
            <div class="muhm-card" style="margin:0;border:1px solid #cbd5e1;background:#ffffff;padding:10px 12px;">
              <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #f1f5f9;padding-bottom:6px;margin-bottom:8px;flex-wrap:wrap;gap:4px;">
                <div style="display:flex;align-items:center;gap:6px;">
                  <span style="font-size:12.5px;font-weight:700;color:#0f172a">📅 ${this.escape(grp.dateKey)}</span>
                  <span style="font-size:9.5px;font-weight:700;padding:1px 5px;border-radius:8px;background:#e0f2fe;color:#0369a1;">
                    ${grp.items.length} ${grp.items.length === 1 ? 'change' : 'changes'}
                  </span>
                </div>
              </div>
              <div style="display:flex;flex-direction:column;">
                ${changesHtml}
              </div>
            </div>
          </div>
        `;
      }).join('') +
    '</div>';
  }

  private injectDOM(): void {
    if (document.getElementById('mobileUhmRoot')) return;

    const style = document.createElement('style');
    style.id = 'mobileUhmStyles';
    style.textContent = `
      #mobileUhmRoot {
        position: fixed;
        inset: 0;
        z-index: 100000001;
        display: none;
        flex-direction: column;
        justify-content: flex-end;
        background: rgba(15, 23, 42, 0.65);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      }
      #mobileUhmSheet {
        background: #ffffff;
        width: 100%;
        max-height: 88vh;
        height: 88vh;
        border-top-left-radius: 16px;
        border-top-right-radius: 16px;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }
      .muhm-header {
        padding: 12px 16px;
        background: #f8fafc;
        border-bottom: 1px solid #e2e8f0;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .muhm-badge {
        font-size: 10px;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 4px;
        text-transform: uppercase;
      }
      .muhm-badge-lead { background: #dbeafe; color: #1e40af; }
      .muhm-badge-vgk { background: #f3e8ff; color: #6b21a8; }
      .muhm-tabs-bar {
        display: flex;
        background: #ffffff;
        border-bottom: 2px solid #e2e8f0;
      }
      .muhm-tab {
        flex: 1;
        padding: 10px 4px;
        font-size: 12.5px;
        font-weight: 600;
        color: #64748b;
        text-align: center;
        border: none;
        background: none;
        border-bottom: 2px solid transparent;
        margin-bottom: -2px;
      }
      .muhm-tab.active {
        color: #2563eb;
        border-bottom-color: #2563eb;
      }
      .muhm-subfilter-bar {
        display: flex;
        gap: 6px;
        padding: 8px 12px;
        background: #f8fafc;
        border-bottom: 1px solid #e2e8f0;
        overflow-x: auto;
      }
      .muhm-subchip {
        font-size: 11px;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid #cbd5e1;
        background: #ffffff;
        color: #475569;
        white-space: nowrap;
      }
      .muhm-subchip.active {
        background: #2563eb;
        color: #ffffff;
        border-color: #2563eb;
      }
      .muhm-content {
        flex: 1;
        overflow-y: auto;
        padding: 12px;
        background: #f8fafc;
      }
      .muhm-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 10px 12px;
        margin-bottom: 8px;
      }
      .muhm-tag {
        font-size: 10px;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 4px;
        background: #f1f5f9;
        color: #475569;
      }
      .muhm-chat-row {
        max-width: 85%;
        display: flex;
        flex-direction: column;
      }
      .muhm-chat-row.inbound { align-self: flex-start; }
      .muhm-chat-row.outbound { align-self: flex-end; }
      .muhm-bubble {
        padding: 9px 12px;
        border-radius: 12px;
        font-size: 12px;
        line-height: 1.4;
        word-break: break-word;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
      }
      .muhm-chat-row.inbound .muhm-bubble {
        background: #ffffff;
        color: #0f172a;
        border: 1px solid #e2e8f0;
        border-top-left-radius: 2px;
      }
      .muhm-chat-row.outbound .muhm-bubble {
        background: #d9fdd3;
        color: #0f172a;
        border: 1px solid #bbf7d0;
        border-top-right-radius: 2px;
      }
      .muhm-chat-meta-bar {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 6px;
        margin-top: 5px;
        padding-top: 3px;
        border-top: 1px solid rgba(0,0,0,0.05);
      }
      .muhm-status-badge {
        display: inline-flex;
        align-items: center;
        gap: 2px;
        font-size: 10px;
        font-weight: 700;
      }
      .muhm-status-failed {
        background: #fee2e2;
        color: #dc2626;
        padding: 1px 5px;
        border-radius: 3px;
        border: 1px solid #fecaca;
        font-size: 9.5px;
        font-weight: 700;
      }
      .muhm-error-snippet {
        margin-top: 5px;
        padding: 4px 8px;
        background: #fff1f2;
        border-left: 2px solid #ef4444;
        border-radius: 3px;
        color: #b91c1c;
        font-size: 10.5px;
        line-height: 1.3;
      }
      .muhm-media-img-box {
        margin-top: 6px;
        border-radius: 6px;
        overflow: hidden;
        border: 1px solid #cbd5e1;
        background: #f8fafc;
        max-width: 240px;
      }
      .muhm-media-img-box img {
        width: 100%;
        max-height: 180px;
        object-fit: cover;
        display: block;
      }
      .muhm-media-img-bar {
        padding: 4px 8px;
        background: rgba(255,255,255,0.95);
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-top: 1px solid #e2e8f0;
        font-size: 10px;
      }
      .muhm-media-name {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 140px;
        font-weight: 600;
        color: #334155;
      }
      .muhm-dl-btn {
        display: inline-flex;
        align-items: center;
        gap: 2px;
        color: #059669;
        font-weight: 700;
        text-decoration: none;
        padding: 1px 4px;
        border-radius: 3px;
        font-size: 10px;
      }
      .muhm-media-doc-box {
        margin-top: 6px;
        padding: 6px 10px;
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 6px;
        max-width: 260px;
      }
      .muhm-doc-view-btn {
        display: inline-flex;
        align-items: center;
        gap: 2px;
        padding: 2px 6px;
        background: #f1f5f9;
        border: 1px solid #cbd5e1;
        border-radius: 3px;
        color: #1e293b;
        text-decoration: none;
        font-size: 10px;
        font-weight: 600;
      }
      .muhm-dot {
        position: absolute;
        left: -19px;
        top: 6px;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #2563eb;
      }
      .muhm-loading, .muhm-empty {
        text-align: center;
        padding: 30px 16px;
        font-size: 13px;
        color: #94a3b8;
      }
    `;
    document.head.appendChild(style);

    const root = document.createElement('div');
    root.id = 'mobileUhmRoot';
    root.innerHTML = `
      <div id="mobileUhmSheet">
        <div class="muhm-header">
          <div style="flex:1;min-width:0">
            <div style="display:flex;align-items:center;gap:6px">
              <span id="muhmName" style="font-weight:700;font-size:15px;color:#0f172a;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">Lead History</span>
              <span id="muhmBadge" class="muhm-badge muhm-badge-lead">Lead</span>
            </div>
            <div style="font-size:11px;color:#64748b;margin-top:2px" id="muhmPhone">—</div>
            <div style="font-size:11px;color:#94a3b8;margin-top:1px" id="muhmMeta">—</div>
          </div>
          <button id="muhmCloseBtn" style="background:none;border:none;font-size:24px;color:#64748b;padding:4px 8px;cursor:pointer">&times;</button>
        </div>

        <div class="muhm-tabs-bar">
          <button class="muhm-tab active" id="muhmTabCalls">Calls (<span id="muhmCountCalls">0</span>)</button>
          <button class="muhm-tab" id="muhmTabMessages">Messages (<span id="muhmCountMessages">0</span>)</button>
          <button class="muhm-tab" id="muhmTabChanges">Changes (<span id="muhmCountChanges">0</span>)</button>
        </div>

        <div id="muhmSubfilterBar" class="muhm-subfilter-bar" style="display:none">
          <button class="muhm-subchip active" data-sub="all">All</button>
          <button class="muhm-subchip" data-sub="calls">Calls</button>
          <button class="muhm-subchip" data-sub="notes">Notes</button>
          <button class="muhm-subchip" data-sub="followups">Follow-ups</button>
          <button class="muhm-subchip" data-sub="assignments">Assignments</button>
          <button class="muhm-subchip" data-sub="audit">Field Edits</button>
        </div>

        <div id="muhmContent" class="muhm-content">
          <div class="muhm-loading">Loading…</div>
        </div>
      </div>
    `;

    root.addEventListener('click', (e) => {
      if (e.target === root) this.close();
    });

    document.body.appendChild(root);

    document.getElementById('muhmCloseBtn')?.addEventListener('click', () => this.close());
    document.getElementById('muhmTabCalls')?.addEventListener('click', () => this.switchTab('calls'));
    document.getElementById('muhmTabMessages')?.addEventListener('click', () => this.switchTab('messages'));
    document.getElementById('muhmTabChanges')?.addEventListener('click', () => this.switchTab('changes'));

    document.querySelectorAll('#muhmSubfilterBar .muhm-subchip').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const sub = (e.currentTarget as HTMLElement).getAttribute('data-sub') || 'all';
        this.setSubfilter(sub);
      });
    });
  }

  private formatDate(isoStr: string): string {
    if (!isoStr) return '—';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (_) {
      return String(isoStr);
    }
  }

  private formatDuration(seconds: number): string {
    const s = parseInt(String(seconds), 10) || 0;
    if (s <= 0) return '0s';
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (h > 0) return `${h}h ${m > 0 ? m + 'm ' : ''}${sec > 0 ? sec + 's' : ''}`.trim();
    if (m > 0) return `${m}m ${sec > 0 ? sec + 's' : ''}`.trim();
    return `${sec}s`;
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

export const universalLeadHistoryModal = new UniversalLeadHistoryModal();

// Register globally on window for mobile inline triggers
if (typeof window !== 'undefined') {
  (window as any).openUniversalHistory = (opts: any) => universalLeadHistoryModal.open(opts);
  (window as any).closeUniversalHistory = () => universalLeadHistoryModal.close();
}
