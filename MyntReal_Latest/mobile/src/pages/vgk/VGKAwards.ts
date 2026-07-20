/**
 * VGK4U Awards Page
 * DC Protocol: DC_MOBILE_VGK_AWARDS_001
 *
 * Phase A1 (audit task #35 follow-up) — read-only foundation page.
 *
 * Mobile read-only view of VGK4U awards. Consumes the audience-aware
 * `/unified-awards/list?audience=vgk4u` endpoint. The backend currently
 * short-circuits VGK4U to an empty list with a `note` and `vgk4u_enabled`
 * flag because the VGK4U award programme is on a separate roadmap; this
 * page renders that empty state cleanly and surfaces the master switch
 * status so admins can distinguish "no data yet" from "feature disabled".
 *
 * Auth scope: the unified awards endpoint uses `get_current_user_hybrid`
 * but is functionally a staff admin tool, so this page ships under the
 * **staff** portal.
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface AwardEntry {
  award_id?: string | number;
  award_name?: string;
  gift_name?: string;
  user_id?: string;
  user_name?: string;
  partner_name?: string;
  status?: string;
  achievement_date?: string;
}

interface AwardsResponse {
  awards: AwardEntry[];
  total_count: number;
  filtered_count?: number;
  summary?: { direct_total?: number; matching_total?: number; bonanza_total?: number };
  audience?: string;
  audience_label?: string;
  vgk4u_enabled?: boolean;
  note?: string;
}

export class VGKAwards {
  private container: HTMLElement;
  private awards: AwardEntry[] = [];
  private loading: boolean = true;
  private vgk4uEnabled: boolean = true;
  private note: string = '';
  private audienceLabel: string = 'VGK4U Members';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadAwards();
  }

  private async loadAwards(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<AwardsResponse>(
        '/unified-awards/list?audience=vgk4u'
      );
      if (response.success && response.data) {
        this.awards = response.data.awards || [];
        this.vgk4uEnabled = response.data.vgk4u_enabled !== false;
        this.note = response.data.note || '';
        this.audienceLabel = response.data.audience_label || 'VGK4U Members';
      } else {
        this.awards = [];
      }
    } catch (error) {
      console.error('[VGKAwards] Failed to load:', error);
      this.awards = [];
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: '🏆 VGK4U Awards', showBack: true })}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;
    PageHeader.attachListeners({ title: '🏆 VGK4U Awards', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const switchPill = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin:8px 16px;">
        <div style="font-size:12px;color:#6366f1;">Audience: ${this.escape(this.audienceLabel)}</div>
        <span style="
          padding:2px 10px;border-radius:999px;font-size:11px;font-weight:600;
          background:${this.vgk4uEnabled ? '#dcfce7' : '#fef3c7'};
          color:${this.vgk4uEnabled ? '#166534' : '#92400e'};
        ">
          Master switch ${this.vgk4uEnabled ? 'ON' : 'OFF'}
        </span>
      </div>
    `;

    if (this.awards.length === 0) {
      content.innerHTML = `
        ${switchPill}
        <div class="empty-state card" style="padding:24px;text-align:center;">
          <div class="empty-icon" style="font-size:48px;">🏆</div>
          <p style="font-weight:600;margin:8px 0 4px;">No VGK4U awards yet</p>
          <p style="font-size:12px;color:#666;">
            ${this.escape(this.note || 'The VGK4U award programme is on a separate roadmap.')}
          </p>
        </div>
      `;
      return;
    }

    content.innerHTML = `
      ${switchPill}
      <div class="awards-list">
        ${this.awards.map((a) => this.renderAwardCard(a)).join('')}
      </div>
    `;
  }

  private renderAwardCard(a: AwardEntry): string {
    const title = a.award_name || a.gift_name || 'Award';
    const who = a.user_name || a.partner_name || a.user_id || '';
    const status = a.status || '';
    return `
      <div class="day-card card" style="padding:12px;margin:8px 16px;">
        <div style="font-weight:600;">${this.escape(title)}</div>
        <div style="font-size:12px;color:#666;margin-top:2px;">
          ${this.escape(who)}${status ? ` · ${this.escape(status)}` : ''}
        </div>
      </div>
    `;
  }

  private escape(s: string): string {
    return String(s ?? '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    } as Record<string, string>)[c]);
  }
}
