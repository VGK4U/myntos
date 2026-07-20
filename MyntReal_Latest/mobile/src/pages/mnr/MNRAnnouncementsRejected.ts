/**
 * MNR Announcements Rejected Page
 * DC Protocol: DC_MOBILE_MNR_ANNOUNCEMENTS_REJECTED_001
 * View user's rejected announcement submissions
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

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
  decision_comment: string | null;
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

export class MNRAnnouncementsRejected {
  private container: HTMLElement;
  private announcements: SubmissionResponse[] = [];
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
    this.updateContent();

    try {
      const response = await apiService.get<SubmissionResponse[]>('/feedback/my-submissions');
      if (response.success && response.data) {
        const allSubmissions = Array.isArray(response.data) ? response.data : [];
        this.announcements = allSubmissions.filter(a => a.status.toLowerCase() === 'rejected');
      }
    } catch (error) {
      console.error('[MNRAnnouncementsRejected] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: '❌ Not Approved', showBack: true })}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: '❌ Not Approved', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    if (this.announcements.length === 0) {
      content.innerHTML = `
        <div class="empty-state card">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          <h3>No Rejected Announcements</h3>
          <p>Your rejected announcements will appear here</p>
        </div>
      `;
      return;
    }

    content.innerHTML = `
      <div class="announcements-list">
        ${this.announcements.map(ann => this.renderCard(ann)).join('')}
      </div>
    `;
  }

  private renderCard(ann: SubmissionResponse): string {
    const categoryName = ann.category?.name || ann.category?.category_name || 'General';
    const mediaCount = ann.media?.length || 0;
    const rejectionReasons = ann.media
      ?.filter(m => m.decision_comment)
      .map(m => m.decision_comment)
      .filter((v, i, a) => a.indexOf(v) === i);
    
    return `
      <div class="announcement-card card rejected">
        <div class="status-badge rejected">Rejected</div>
        <div class="announcement-header">
          <span class="category-badge">${categoryName}</span>
          <span class="announcement-date">${this.formatDate(ann.submitted_at)}</span>
        </div>
        <h4 class="announcement-title">${ann.title}</h4>
        <p class="announcement-description">${ann.description || ''}</p>
        ${this.renderMediaThumbs(ann.media)}
        <div class="file-count">📁 ${mediaCount} file(s)</div>
        ${rejectionReasons && rejectionReasons.length > 0 ? `
          <div class="rejection-reason">
            <strong>Reason:</strong> ${rejectionReasons.join('; ')}
          </div>
        ` : ''}
      </div>
    `;
  }

  private renderMediaThumbs(media: MediaResponse[]): string {
    if (!media || media.length === 0) return '';
    const visibleMedia = media.slice(0, 4);
    return `
      <div class="media-thumbnails">
        ${visibleMedia.map((m, idx) => `
          <div class="thumb ${m.media_type} ${m.media_status === 'rejected' ? 'rejected' : ''}">
            ${m.media_type === 'video' 
              ? `<span class="play-icon">▶</span>`
              : `<img src="${apiService.getMediaUrl(m.file_path)}" alt="Media ${idx + 1}" loading="lazy" onerror="this.style.display='none'" />`
            }
            ${m.media_status === 'rejected' ? '<span class="rejected-x">✕</span>' : ''}
          </div>
        `).join('')}
        ${media.length > 4 ? `<div class="thumb more">+${media.length - 4}</div>` : ''}
      </div>
    `;
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString('en-IN', {
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
