/**
 * VGK4U Top Earners Page
 * DC Protocol: DC_MOBILE_VGK_TOP_EARNERS_001
 *
 * Mobile read-only leaderboard of top VGK4U earners (separate from MNR
 * leaderboard). Consumes the audience-aware /banners/top-performers endpoint
 * with `audience=vgk4u` (DC_AUDIENCE_001) — backed by vgk_team_income_entries.
 *
 * Phase A1 (Task #35 follow-up) — read-only foundation page.
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface TopEarner {
  user_id: string;
  name: string;
  total_earnings: number;
  rank: number;
  badge?: string | null;
  photo_url?: string | null;
  latest_earning_date?: string | null;
}

interface TopEarnersResponse {
  top_performers: TopEarner[];
  total_count: number;
  excluded_count: number;
  latest_earning_date: string | null;
  audience?: string;
}

export class VGKTopEarners {
  private container: HTMLElement;
  private earners: TopEarner[] = [];
  private latestDate: string | null = null;
  private loading: boolean = true;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadEarners();
  }

  private async loadEarners(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<TopEarnersResponse>(
        '/banners/top-performers?limit=10&audience=vgk4u'
      );
      if (response.success && response.data) {
        this.earners = response.data.top_performers || [];
        this.latestDate = response.data.latest_earning_date || null;
      } else {
        this.earners = [];
      }
    } catch (error) {
      console.error('[VGKTopEarners] Failed to load:', error);
      this.earners = [];
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: '🏆 VGK4U Top Earners', showBack: true })}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;
    PageHeader.attachListeners({ title: '🏆 VGK4U Top Earners', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const subtitle = this.latestDate
      ? `Latest earning day: ${this.latestDate}`
      : 'No qualifying earnings yet';

    content.innerHTML = `
      <div class="audience-pill" style="margin:8px 16px;font-size:12px;color:#6366f1;">
        Audience: VGK4U Members · ${this.escape(subtitle)}
      </div>

      ${this.earners.length > 0 ? `
        <div class="leaderboard">
          ${this.earners.map((e) => this.renderEarnerCard(e)).join('')}
        </div>
      ` : `
        <div class="empty-state card">
          <div class="empty-icon">🏆</div>
          <p>No VGK4U top earners yet</p>
          <p style="font-size:12px;color:#888;">Top performers appear once VGK income entries cross ₹1,000 in a single day.</p>
        </div>
      `}
    `;
  }

  private renderEarnerCard(e: TopEarner): string {
    const medal = e.rank === 1 ? '🥇' : e.rank === 2 ? '🥈' : e.rank === 3 ? '🥉' : `#${e.rank}`;
    return `
      <div class="day-card card" style="display:flex;align-items:center;gap:12px;padding:12px;">
        <div style="font-size:20px;font-weight:700;min-width:40px;text-align:center;">${medal}</div>
        <div style="flex:1;">
          <div style="font-weight:600;">${this.escape(e.name)}</div>
          <div style="font-size:11px;color:#888;">VGK4U · ${this.escape(e.user_id)}</div>
          ${e.badge ? `<div style="font-size:11px;margin-top:2px;">${this.escape(e.badge)}</div>` : ''}
        </div>
        <div style="font-weight:700;color:#10b981;">
          ₹${(e.total_earnings || 0).toLocaleString('en-IN')}
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
