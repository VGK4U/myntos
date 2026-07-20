/**
 * VGK4U Birthdays Page
 * DC Protocol: DC_MOBILE_VGK_BIRTHDAYS_001
 *
 * Mobile read-only view of today's / tomorrow's / next-7-days VGK4U member
 * birthdays. Mirrors MNR pattern but consumes the audience-aware backend
 * endpoints (today/tomorrow/next-7-days) with `audience=vgk4u`
 * (DC_AUDIENCE_001).
 *
 * Phase A1 (Task #35 follow-up) — read-only foundation page.
 *
 * Auth scope: the underlying `/banners/admin/birthdays/*` endpoints are
 * staff-only (`get_banner_creator_user_hybrid`). This page is therefore
 * registered under the **staff** portal, not the MNR member portal.
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface BirthdayUser {
  user_id: string;
  name: string;
  location: string;
  birthday_date: string;
  has_photo: boolean;
}

interface BirthdayResponse {
  success: boolean;
  filter: string;
  date: string;
  users: BirthdayUser[];
  total_count: number;
  audience?: string;
}

type FilterMode = 'today' | 'tomorrow' | 'next-7-days';

export class VGKBirthdays {
  private container: HTMLElement;
  private users: BirthdayUser[] = [];
  private loading: boolean = true;
  private mode: FilterMode = 'today';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadBirthdays();
  }

  private async loadBirthdays(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<BirthdayResponse>(
        `/banners/admin/birthdays/${this.mode}?audience=vgk4u`
      );
      if (response.success && response.data) {
        this.users = response.data.users || [];
      } else {
        this.users = [];
      }
    } catch (error) {
      console.error('[VGKBirthdays] Failed to load:', error);
      this.users = [];
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: '🎂 VGK4U Birthdays', showBack: true })}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;
    PageHeader.attachListeners({ title: '🎂 VGK4U Birthdays', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    content.innerHTML = `
      <div class="filter-tabs card" style="display:flex;gap:8px;padding:8px;">
        <button data-mode="today"        class="filter-tab ${this.mode === 'today' ? 'active' : ''}">Today</button>
        <button data-mode="tomorrow"     class="filter-tab ${this.mode === 'tomorrow' ? 'active' : ''}">Tomorrow</button>
        <button data-mode="next-7-days"  class="filter-tab ${this.mode === 'next-7-days' ? 'active' : ''}">Next 7 Days</button>
      </div>

      <div class="audience-pill" style="margin:8px 16px;font-size:12px;color:#6366f1;">
        Audience: VGK4U Members
      </div>

      ${this.users.length > 0 ? `
        <div class="birthday-list">
          ${this.users.map((u) => this.renderUserCard(u)).join('')}
        </div>
      ` : `
        <div class="empty-state card">
          <div class="empty-icon">🎂</div>
          <p>No VGK4U birthdays for ${this.modeLabel()}</p>
        </div>
      `}
    `;

    content.querySelectorAll<HTMLButtonElement>('.filter-tab').forEach((btn) => {
      btn.addEventListener('click', () => {
        const mode = btn.getAttribute('data-mode') as FilterMode;
        if (mode && mode !== this.mode) {
          this.mode = mode;
          this.loadBirthdays();
        }
      });
    });
  }

  private renderUserCard(u: BirthdayUser): string {
    const dob = new Date(u.birthday_date);
    const day = dob.getDate();
    const month = dob.toLocaleDateString('en', { month: 'short' });
    return `
      <div class="day-card card" style="display:flex;align-items:center;gap:12px;padding:12px;">
        <div class="day-date" style="text-align:center;min-width:48px;">
          <div class="day-num" style="font-size:20px;font-weight:700;">${day}</div>
          <div class="day-name" style="font-size:11px;color:#888;">${month}</div>
        </div>
        <div style="flex:1;">
          <div style="font-weight:600;">${this.escape(u.name)}</div>
          <div style="font-size:12px;color:#666;">${this.escape(u.location)}</div>
          <div style="font-size:11px;color:#888;margin-top:2px;">VGK4U · ${this.escape(u.user_id)}</div>
        </div>
      </div>
    `;
  }

  private modeLabel(): string {
    return this.mode === 'today' ? 'today'
         : this.mode === 'tomorrow' ? 'tomorrow'
         : 'the next 7 days';
  }

  private escape(s: string): string {
    return String(s ?? '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    } as Record<string, string>)[c]);
  }
}
