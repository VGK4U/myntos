/**
 * Announcements Page
 * DC Protocol: DC_MOBILE_ANNOUNCEMENTS_001
 * View company announcements
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface Announcement {
  id: number;
  title: string;
  content: string;
  category: string;
  priority: string;
  created_at: string;
  author_name: string;
  image_url: string | null;
  is_read: boolean;
}

export class AnnouncementsPage {
  private container: HTMLElement;
  private announcements: Announcement[] = [];
  private loading: boolean = true;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadAnnouncements();
  }

  private async loadAnnouncements(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      const response = await apiService.fetch<{ announcements: Announcement[] }>(
        '/staff/announcements'
      );

      if (response.success && response.data) {
        this.announcements = response.data.announcements || [];
      } else {
        this.announcements = [];
      }
    } catch (error) {
      console.error('[AnnouncementsPage] Failed to load:', error);
      this.announcements = [];
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Announcements', showBack: false })}
        
        <div class="list-container" id="announcementsList">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'Announcements', showBack: false });
  }

  private updateList(): void {
    const listContainer = document.getElementById('announcementsList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    if (this.announcements.length === 0) {
      listContainer.innerHTML = '<div class="empty-state">No announcements</div>';
      return;
    }

    listContainer.innerHTML = this.announcements.map(item => `
      <div class="list-item card announcement-card ${item.is_read ? '' : 'unread'}">
        <div class="item-header">
          <span class="priority-badge ${item.priority?.toLowerCase() || 'normal'}">${item.priority || 'Normal'}</span>
          <span class="item-date">${this.formatDate(item.created_at)}</span>
        </div>
        ${item.image_url ? `<img src="${item.image_url}" class="announcement-image" alt="" />` : ''}
        <h3 class="announcement-title">${item.title}</h3>
        <p class="announcement-content">${this.truncate(item.content, 150)}</p>
        <div class="announcement-meta">
          <span class="category-tag">${item.category || 'General'}</span>
          <span class="author">By ${item.author_name || 'Admin'}</span>
        </div>
      </div>
    `).join('');
  }

  private formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
  }

  private truncate(text: string, maxLength: number): string {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  }
}
