/**
 * MNR My Announcements Page
 * DC Protocol: DC_MOBILE_MNR_MYANN_001
 * View and manage user's announcement submissions
 * Matches web: /mnr/my-announcements
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';
import { routerService } from '../../services/router.service';

interface CategoryResponse {
  id: number;
  name: string;
  category_name: string;
}

interface MediaResponse {
  id: number;
  file_path: string;
  file_type: string;
  media_type: string;
  media_status: string;
}

interface SubmissionResponse {
  id: number;
  title: string;
  description: string | null;
  submission_type: string;
  category: CategoryResponse;
  status: string;
  is_visible: boolean;
  submitted_at: string;
  approved_at: string | null;
  media: MediaResponse[];
  user_name: string;
  user_id: string;
}

export class MNRMyAnnouncements {
  private container: HTMLElement;
  private announcements: SubmissionResponse[] = [];
  private loading: boolean = true;
  private activeTab: 'all' | 'pending' | 'approved' | 'rejected' = 'all';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadAnnouncements();
  }

  private async loadAnnouncements(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<SubmissionResponse[]>('/feedback/my-submissions');
      if (response.success && response.data) {
        this.announcements = Array.isArray(response.data) ? response.data : [];
      }
    } catch (error) {
      console.error('[MNRMyAnnouncements] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private getFilteredAnnouncements(): SubmissionResponse[] {
    if (this.activeTab === 'all') return this.announcements;
    return this.announcements.filter(a => a.status.toLowerCase() === this.activeTab);
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: '📋 My Submissions', showBack: true })}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: '📋 My Submissions', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const filtered = this.getFilteredAnnouncements();
    const counts = {
      all: this.announcements.length,
      pending: this.announcements.filter(a => a.status.toLowerCase() === 'pending').length,
      approved: this.announcements.filter(a => a.status.toLowerCase() === 'approved').length,
      rejected: this.announcements.filter(a => a.status.toLowerCase() === 'rejected').length
    };

    content.innerHTML = `
      <button class="btn btn-primary submit-btn" id="submitNewBtn">
        + Submit New Announcement
      </button>

      <div class="announcement-tabs">
        <button class="tab ${this.activeTab === 'all' ? 'active' : ''}" data-tab="all">All (${counts.all})</button>
        <button class="tab ${this.activeTab === 'pending' ? 'active' : ''}" data-tab="pending">Pending (${counts.pending})</button>
        <button class="tab ${this.activeTab === 'approved' ? 'active' : ''}" data-tab="approved">Approved (${counts.approved})</button>
        <button class="tab ${this.activeTab === 'rejected' ? 'active' : ''}" data-tab="rejected">Rejected (${counts.rejected})</button>
      </div>

      ${filtered.length > 0 ? `
        <div class="announcements-list">
          ${filtered.map(a => this.renderSubmissionCard(a)).join('')}
        </div>
      ` : `
        <div class="empty-state card">
          <div class="empty-icon">📢</div>
          <p>No ${this.activeTab === 'all' ? '' : this.activeTab} announcements</p>
        </div>
      `}
    `;

    this.attachListeners();
  }

  private renderSubmissionCard(ann: SubmissionResponse): string {
    const statusClass = ann.status.toLowerCase();
    const categoryName = ann.category?.name || ann.category?.category_name || 'General';
    const mediaCount = ann.media?.length || 0;
    
    return `
      <div class="announcement-card card ${statusClass}">
        <div class="ann-header">
          <h4>${ann.title}</h4>
          <span class="status-badge ${statusClass}">${this.formatStatus(ann.status)}</span>
        </div>
        
        <div class="ann-category">
          <span class="category-tag">${categoryName}</span>
        </div>
        
        <p class="ann-description">${ann.description || ''}</p>
        
        ${this.renderMediaThumbnails(ann.media)}
        
        <div class="ann-meta">
          <span>📅 ${this.formatDate(ann.submitted_at)}</span>
          <span>📁 ${mediaCount} file(s)</span>
        </div>
        
        ${ann.status.toLowerCase() === 'approved' && ann.approved_at ? `
          <div class="approval-info">
            ✅ Approved: ${this.formatDate(ann.approved_at)}
          </div>
        ` : ''}
      </div>
    `;
  }

  private renderMediaThumbnails(media: MediaResponse[]): string {
    if (!media || media.length === 0) return '';
    
    const visibleMedia = media.slice(0, 4);
    const moreCount = media.length > 4 ? media.length - 4 : 0;
    
    return `
      <div class="media-thumbnails">
        ${visibleMedia.map((m, idx) => `
          <div class="thumb ${m.media_type === 'video' ? 'video' : 'image'}">
            ${m.media_type === 'video' 
              ? `<span class="play-icon">▶</span>`
              : `<img src="${apiService.getMediaUrl(m.file_path)}" alt="Media ${idx + 1}" loading="lazy" onerror="this.style.display='none'" />`
            }
            ${m.media_status !== 'approved' ? `<span class="media-status ${m.media_status}">${m.media_status}</span>` : ''}
          </div>
        `).join('')}
        ${moreCount > 0 ? `<div class="thumb more">+${moreCount}</div>` : ''}
      </div>
    `;
  }

  private formatStatus(status: string): string {
    const statusMap: Record<string, string> = {
      'pending': 'Pending Review',
      'under_review': 'Under Review',
      'approved': 'Approved',
      'rejected': 'Rejected',
      'partially_approved': 'Partially Approved'
    };
    return statusMap[status.toLowerCase()] || status;
  }

  private attachListeners(): void {
    document.getElementById('submitNewBtn')?.addEventListener('click', () => {
      routerService.navigate('mnr-create-announcement');
    });

    document.querySelectorAll('.announcement-tabs .tab').forEach(btn => {
      btn.addEventListener('click', () => {
        this.activeTab = btn.getAttribute('data-tab') as any;
        this.updateContent();
      });
    });
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-IN', { 
        day: '2-digit', 
        month: 'short', 
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  }
}
