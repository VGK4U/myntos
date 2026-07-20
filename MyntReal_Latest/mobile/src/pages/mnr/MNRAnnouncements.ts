/**
 * MNR Announcements Page (Public Announcements)
 * DC Protocol: DC_MOBILE_MNR_ANNOUNCEMENTS_001
 * View approved public announcements with media gallery
 * Matches web: /mnr/announcements
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';
import { Clipboard } from '@capacitor/clipboard';
import { Share } from '@capacitor/share';
import { APP_CONFIG } from '../../config/app.config';

// DC Protocol: Use centralized configuration from APP_CONFIG
const PUBLIC_DOMAIN = APP_CONFIG.MEDIA_BASE_URL;

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
}

interface AnnouncementResponse {
  id: number;
  title: string;
  description: string | null;
  submission_type: string;
  category: CategoryResponse;
  approved_at: string;
  updated_at: string;
  is_visible: boolean;
  media: MediaResponse[];
  user_id: string;
  user_name: string;
  city: string | null;
  average_rating: number;
  total_ratings: number;
  shares_count: number;
  views_count: number;
}

export class MNRAnnouncements {
  private container: HTMLElement;
  private announcements: AnnouncementResponse[] = [];
  private loading: boolean = true;
  private currentMedia: MediaResponse[] = [];
  private currentMediaIndex: number = 0;
  private currentRotation: number = 0;

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
      const response = await apiService.get<AnnouncementResponse[]>('/feedback/announcements');
      if (response.success && response.data) {
        this.announcements = Array.isArray(response.data) ? response.data : [];
      }
    } catch (error) {
      console.error('[MNRAnnouncements] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: '📢 Community Updates', showBack: true })}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
      ${this.renderLightbox()}
    `;

    PageHeader.attachListeners({ title: '📢 Community Updates', showBack: true });
    this.attachLightboxListeners();
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
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>
          <h3>No Updates</h3>
          <p>Check back later for updates</p>
        </div>
      `;
      return;
    }

    content.innerHTML = `
      <div class="announcement-count">${this.announcements.length} announcement${this.announcements.length !== 1 ? 's' : ''}</div>
      <div class="announcements-list">
        ${this.announcements.map(ann => this.renderAnnouncementCard(ann)).join('')}
      </div>
    `;

    this.attachCardListeners();
  }

  private renderAnnouncementCard(ann: AnnouncementResponse): string {
    const categoryName = ann.category?.name || ann.category?.category_name || 'General';
    const categoryClass = categoryName.toLowerCase().replace(/\s+/g, '-');
    
    return `
      <div class="announcement-card card" data-id="${ann.id}">
        <div class="announcement-header">
          <h4 class="announcement-title">${ann.title}</h4>
          <span class="category-badge ${categoryClass}">${categoryName}</span>
        </div>
        
        <p class="announcement-description">${ann.description || ''}</p>
        
        ${this.renderMediaGallery(ann.media, ann.id)}
        
        <div class="announcement-meta">
          <div class="meta-row">
            <span class="meta-item">
              <span class="meta-icon">👤</span>
              <span class="meta-label">Posted By:</span>
              <span class="meta-value">${ann.user_name || 'Unknown'}</span>
            </span>
            <span class="meta-item">
              <span class="meta-icon">🆔</span>
              <span class="meta-label">User ID:</span>
              <span class="meta-value">${ann.user_id || 'N/A'}</span>
            </span>
          </div>
          <div class="meta-row">
            <span class="meta-item">
              <span class="meta-icon">📍</span>
              <span class="meta-label">Location:</span>
              <span class="meta-value">${ann.city || 'N/A'}</span>
            </span>
            <span class="meta-item">
              <span class="meta-icon">⭐</span>
              <span class="meta-value">${ann.average_rating?.toFixed(1) || '0.0'} (${ann.total_ratings || 0})</span>
            </span>
          </div>
        </div>
        
        <div class="announcement-footer">
          <span class="announcement-date">
            📅 ${this.formatDate(ann.approved_at || ann.updated_at)}
          </span>
          <span class="shares-count">${ann.shares_count || 0} shares</span>
        </div>
        
        <div class="announcement-actions">
          <button class="action-btn copy-link-btn" data-id="${ann.id}">
            📋 Copy Link
          </button>
          <button class="action-btn share-whatsapp-btn" data-id="${ann.id}" data-title="${ann.title}">
            💬 Share on WhatsApp
          </button>
        </div>
      </div>
    `;
  }

  private renderMediaGallery(media: MediaResponse[], announcementId: number): string {
    if (!media || media.length === 0) return '';
    
    const visibleMedia = media.slice(0, 6);
    const moreCount = media.length > 6 ? media.length - 6 : 0;
    const mediaJson = encodeURIComponent(JSON.stringify(media));
    
    return `
      <div class="media-gallery" data-announcement-id="${announcementId}" data-media='${mediaJson}'>
        ${visibleMedia.map((m, idx) => {
          const mediaUrl = apiService.getMediaUrl(m.file_path);
          return `
          <div class="media-thumb ${m.media_type === 'video' ? 'video-thumb' : ''}" data-index="${idx}">
            ${m.media_type === 'video' 
              ? `<video src="${mediaUrl}" preload="metadata"></video><span class="play-icon">▶</span>`
              : `<img src="${mediaUrl}" alt="Media ${idx + 1}" loading="lazy" onerror="this.style.display='none'" />`
            }
          </div>
        `}).join('')}
        ${moreCount > 0 ? `<div class="media-more" data-index="6">+${moreCount} more</div>` : ''}
      </div>
      <div class="file-count">📁 ${media.length} file(s)</div>
    `;
  }

  private renderLightbox(): string {
    return `
      <div id="mediaLightbox" class="media-lightbox hidden">
        <div class="lightbox-overlay"></div>
        <div class="lightbox-content">
          <button class="lightbox-close" id="lightboxClose">✕</button>
          <button class="lightbox-nav lightbox-prev" id="lightboxPrev">❮</button>
          <div class="lightbox-media-container" id="lightboxMediaContainer">
            <img id="lightboxImage" class="lightbox-image" src="" alt="Media" />
            <video id="lightboxVideo" class="lightbox-video hidden" controls></video>
          </div>
          <button class="lightbox-nav lightbox-next" id="lightboxNext">❯</button>
          <div class="lightbox-controls">
            <button class="lightbox-rotate" id="lightboxRotate">🔄 Rotate</button>
            <span class="lightbox-counter" id="lightboxCounter">1 / 1</span>
          </div>
        </div>
      </div>
    `;
  }

  private openLightbox(media: MediaResponse[], startIndex: number = 0): void {
    this.currentMedia = media;
    this.currentMediaIndex = startIndex;
    this.currentRotation = 0;
    this.updateLightboxMedia();
    const lightbox = document.getElementById('mediaLightbox');
    if (lightbox) {
      lightbox.classList.remove('hidden');
      document.body.style.overflow = 'hidden';
    }
  }

  private closeLightbox(): void {
    const lightbox = document.getElementById('mediaLightbox');
    if (lightbox) {
      lightbox.classList.add('hidden');
      document.body.style.overflow = '';
    }
    this.currentRotation = 0;
  }

  private updateLightboxMedia(): void {
    if (this.currentMedia.length === 0) return;
    
    const media = this.currentMedia[this.currentMediaIndex];
    const mediaUrl = apiService.getMediaUrl(media.file_path);
    const imageEl = document.getElementById('lightboxImage') as HTMLImageElement;
    const videoEl = document.getElementById('lightboxVideo') as HTMLVideoElement;
    const counterEl = document.getElementById('lightboxCounter');
    
    if (media.media_type === 'video') {
      imageEl?.classList.add('hidden');
      videoEl?.classList.remove('hidden');
      if (videoEl) {
        videoEl.src = mediaUrl;
        videoEl.style.transform = `rotate(${this.currentRotation}deg)`;
      }
    } else {
      videoEl?.classList.add('hidden');
      imageEl?.classList.remove('hidden');
      if (imageEl) {
        imageEl.src = mediaUrl;
        imageEl.style.transform = `rotate(${this.currentRotation}deg)`;
      }
    }
    
    if (counterEl) {
      counterEl.textContent = `${this.currentMediaIndex + 1} / ${this.currentMedia.length}`;
    }
    
    const prevBtn = document.getElementById('lightboxPrev');
    const nextBtn = document.getElementById('lightboxNext');
    if (prevBtn) prevBtn.style.visibility = this.currentMediaIndex > 0 ? 'visible' : 'hidden';
    if (nextBtn) nextBtn.style.visibility = this.currentMediaIndex < this.currentMedia.length - 1 ? 'visible' : 'hidden';
  }

  private navigateLightbox(direction: number): void {
    const newIndex = this.currentMediaIndex + direction;
    if (newIndex >= 0 && newIndex < this.currentMedia.length) {
      this.currentMediaIndex = newIndex;
      this.currentRotation = 0;
      this.updateLightboxMedia();
    }
  }

  private rotateLightbox(): void {
    this.currentRotation = (this.currentRotation + 90) % 360;
    const imageEl = document.getElementById('lightboxImage') as HTMLImageElement;
    const videoEl = document.getElementById('lightboxVideo') as HTMLVideoElement;
    if (imageEl && !imageEl.classList.contains('hidden')) {
      imageEl.style.transform = `rotate(${this.currentRotation}deg)`;
    }
    if (videoEl && !videoEl.classList.contains('hidden')) {
      videoEl.style.transform = `rotate(${this.currentRotation}deg)`;
    }
  }

  private attachLightboxListeners(): void {
    document.getElementById('lightboxClose')?.addEventListener('click', () => this.closeLightbox());
    document.getElementById('lightboxPrev')?.addEventListener('click', () => this.navigateLightbox(-1));
    document.getElementById('lightboxNext')?.addEventListener('click', () => this.navigateLightbox(1));
    document.getElementById('lightboxRotate')?.addEventListener('click', () => this.rotateLightbox());
    
    document.querySelector('.lightbox-overlay')?.addEventListener('click', () => this.closeLightbox());
    
    document.querySelectorAll('.media-gallery').forEach(gallery => {
      gallery.addEventListener('click', (e) => {
        const target = e.target as HTMLElement;
        const thumb = target.closest('.media-thumb, .media-more');
        if (thumb) {
          const mediaJson = gallery.getAttribute('data-media');
          if (mediaJson) {
            try {
              const media = JSON.parse(decodeURIComponent(mediaJson));
              const index = parseInt(thumb.getAttribute('data-index') || '0', 10);
              this.openLightbox(media, Math.min(index, media.length - 1));
            } catch (err) {
              console.error('[MNRAnnouncements] Failed to parse media:', err);
            }
          }
        }
      });
    });
  }

  private attachCardListeners(): void {
    document.querySelectorAll('.copy-link-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = (e.target as HTMLElement).closest('.action-btn')?.getAttribute('data-id');
        if (id) this.copyLink(id);
      });
    });

    document.querySelectorAll('.share-whatsapp-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const el = (e.target as HTMLElement).closest('.action-btn');
        const id = el?.getAttribute('data-id');
        const title = el?.getAttribute('data-title');
        if (id && title) this.shareOnWhatsApp(id, title);
      });
    });

    document.querySelectorAll('.media-gallery').forEach(gallery => {
      gallery.addEventListener('click', (e) => {
        const target = e.target as HTMLElement;
        const thumb = target.closest('.media-thumb, .media-more');
        if (thumb) {
          const mediaJson = gallery.getAttribute('data-media');
          if (mediaJson) {
            try {
              const media = JSON.parse(decodeURIComponent(mediaJson));
              const index = parseInt(thumb.getAttribute('data-index') || '0', 10);
              this.openLightbox(media, Math.min(index, media.length - 1));
            } catch (err) {
              console.error('[MNRAnnouncements] Failed to parse media:', err);
            }
          }
        }
      });
    });
  }

  private async copyLink(announcementId: string): Promise<void> {
    const url = `${PUBLIC_DOMAIN}/public/announcement?id=${announcementId}&shared=true`;
    try {
      await Clipboard.write({ string: url });
      this.showToast('Link copied to clipboard!');
    } catch (error) {
      console.error('[MNRAnnouncements] Clipboard write failed:', error);
      this.showToast('Failed to copy link');
    }
  }

  private async shareOnWhatsApp(announcementId: string, title: string): Promise<void> {
    const url = `${PUBLIC_DOMAIN}/public/announcement?id=${announcementId}&shared=true`;
    const text = `Check out this announcement: ${title}\n${url}`;
    try {
      await Share.share({
        title: title,
        text: text,
        url: url,
        dialogTitle: 'Share Announcement'
      });
    } catch (error) {
      console.error('[MNRAnnouncements] Share failed:', error);
      window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
    }
  }

  private showToast(message: string): void {
    const toast = document.createElement('div');
    toast.className = 'toast-message';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
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
