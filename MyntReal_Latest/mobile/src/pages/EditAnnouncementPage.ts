/**
 * Edit Announcement Page
 * DC Protocol: DC_MOBILE_EDIT_ANNOUNCEMENT_001
 * Edit announcement with media management (add/delete photos and videos)
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';

interface MediaItem {
  id: number;
  url: string;
  file_type: string;
  selected: boolean;
}

interface Announcement {
  id: number;
  title: string;
  description: string;
  media: MediaItem[];
}

export class EditAnnouncementPage {
  private container: HTMLElement;
  private announcementId: number = 0;
  private announcement: Announcement | null = null;
  private newFiles: File[] = [];
  private loading: boolean = true;
  private saving: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    const params = new URLSearchParams(window.location.hash.split('?')[1] || '');
    this.announcementId = parseInt(params.get('id') || '0');
    
    this.render();
    if (this.announcementId) {
      await this.loadAnnouncement();
    }
  }

  private async loadAnnouncement(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>(`/feedback/submissions/${this.announcementId}`);
      if (response.success && response.data) {
        this.announcement = {
          id: response.data.id,
          title: response.data.title,
          description: response.data.description || '',
          media: (response.data.media || []).map((m: any) => ({
            id: m.id,
            url: m.url || m.file_path,
            file_type: m.file_type || 'image',
            selected: false
          }))
        };
      }
    } catch (error) {
      console.error('[EditAnnouncementPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Edit Announcement', showBack: true })}
        <div id="editContent"></div>
      </div>

      <style>
        .media-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
        .media-item { width: 100px; height: 100px; position: relative; border-radius: 8px; overflow: hidden; border: 2px solid transparent; }
        .media-item.selected { border-color: #ef4444; }
        .media-item img, .media-item video { width: 100%; height: 100%; object-fit: cover; }
        .media-item .checkbox { position: absolute; top: 4px; right: 4px; width: 24px; height: 24px; }
        .media-item .type-badge { position: absolute; bottom: 4px; left: 4px; background: rgba(0,0,0,0.7); color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; }
        .new-file-item { width: 80px; height: 80px; position: relative; border-radius: 8px; overflow: hidden; border: 2px solid #10b981; }
        .new-file-item .remove-btn { position: absolute; top: 2px; right: 2px; background: #ef4444; color: white; border: none; border-radius: 50%; width: 20px; height: 20px; font-size: 12px; }
        .action-bar { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
        .media-count { color: #888; font-size: 12px; margin-bottom: 8px; }
      </style>
    `;

    PageHeader.attachBackHandler();
    this.updateContent();
  }

  private updateContent(): void {
    const content = document.getElementById('editContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    if (!this.announcement) {
      content.innerHTML = '<div class="empty-state">Announcement not found</div>';
      return;
    }

    const existingMedia = this.announcement.media || [];
    const selectedCount = existingMedia.filter(m => m.selected).length;

    content.innerHTML = `
      <form id="editForm" class="form-container">
        <div class="form-section">
          <div class="form-group">
            <label>Title *</label>
            <input type="text" id="titleInput" class="form-input" value="${this.escapeHtml(this.announcement.title)}" required>
          </div>

          <div class="form-group">
            <label>Description</label>
            <textarea id="descriptionInput" class="form-textarea" rows="4">${this.escapeHtml(this.announcement.description)}</textarea>
          </div>
        </div>

        <div class="form-section">
          <h4>Existing Media</h4>
          <p class="media-count">${existingMedia.length} files (min 3 required) - Tap to select for deletion</p>
          
          <div class="media-grid" id="existingMediaGrid">
            ${existingMedia.map(m => `
              <div class="media-item ${m.selected ? 'selected' : ''}" data-id="${m.id}">
                ${m.file_type?.startsWith('video') ? 
                  `<video src="${m.url}"></video>` :
                  `<img src="${m.url}" alt="">`
                }
                <input type="checkbox" class="checkbox" ${m.selected ? 'checked' : ''}>
                <span class="type-badge">${m.file_type?.startsWith('video') ? 'VIDEO' : 'PHOTO'}</span>
              </div>
            `).join('')}
          </div>

          <div class="action-bar">
            <button type="button" class="btn btn-danger btn-sm" id="deleteSelectedBtn" ${selectedCount === 0 ? 'disabled' : ''}>
              Delete Selected (${selectedCount})
            </button>
          </div>
        </div>

        <div class="form-section">
          <h4>Add More Media</h4>
          <input type="file" id="newMediaInput" accept="image/*,video/*" multiple style="display: none;">
          <button type="button" class="btn btn-outline" id="addMediaBtn">
            <span class="icon">📁</span> Select Files
          </button>

          <div class="media-grid" id="newMediaGrid" style="margin-top: 12px;">
            ${this.newFiles.map((f, idx) => `
              <div class="new-file-item">
                ${f.type.startsWith('video') ? 
                  `<video src="${URL.createObjectURL(f)}"></video>` :
                  `<img src="${URL.createObjectURL(f)}" alt="">`
                }
                <button type="button" class="remove-btn" data-index="${idx}">&times;</button>
              </div>
            `).join('')}
          </div>
          ${this.newFiles.length > 0 ? `
            <button type="button" class="btn btn-success btn-sm" id="uploadNewBtn" style="margin-top: 8px;">
              Upload ${this.newFiles.length} New File(s)
            </button>
          ` : ''}
        </div>

        <div class="form-actions sticky-bottom">
          <button type="button" class="btn btn-secondary" id="cancelBtn">Cancel</button>
          <button type="submit" class="btn btn-primary" id="saveBtn">Save Changes</button>
        </div>
      </form>
    `;

    this.attachFormListeners();
  }

  private attachFormListeners(): void {
    document.getElementById('cancelBtn')?.addEventListener('click', () => {
      routerService.goBack();
    });

    document.getElementById('existingMediaGrid')?.querySelectorAll('.media-item').forEach(item => {
      item.addEventListener('click', () => {
        const id = parseInt(item.getAttribute('data-id') || '0');
        const media = this.announcement?.media.find(m => m.id === id);
        if (media) {
          media.selected = !media.selected;
          this.updateContent();
        }
      });
    });

    document.getElementById('deleteSelectedBtn')?.addEventListener('click', () => {
      this.deleteSelectedMedia();
    });

    document.getElementById('addMediaBtn')?.addEventListener('click', () => {
      document.getElementById('newMediaInput')?.click();
    });

    document.getElementById('newMediaInput')?.addEventListener('change', (e) => {
      const input = e.target as HTMLInputElement;
      const files = Array.from(input.files || []);
      this.newFiles.push(...files);
      input.value = '';
      this.updateContent();
    });

    document.getElementById('newMediaGrid')?.querySelectorAll('.remove-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const index = parseInt((e.target as HTMLElement).dataset.index || '0');
        this.newFiles.splice(index, 1);
        this.updateContent();
      });
    });

    document.getElementById('uploadNewBtn')?.addEventListener('click', () => {
      this.uploadNewMedia();
    });

    document.getElementById('editForm')?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.saveChanges();
    });
  }

  private async deleteSelectedMedia(): Promise<void> {
    if (!this.announcement) return;
    
    const selected = this.announcement.media.filter(m => m.selected);
    if (selected.length === 0) return;

    const remaining = this.announcement.media.length - selected.length;
    if (remaining < 3) {
      alert('Cannot delete - minimum 3 media files required');
      return;
    }

    if (!confirm(`Delete ${selected.length} media file(s)?`)) return;

    for (const media of selected) {
      try {
        await apiService.delete(`/staff/mnr-user/announcements/${this.announcementId}/media/${media.id}`);
      } catch (error) {
        console.error('[EditAnnouncementPage] Delete failed:', error);
        alert('Failed to delete some files');
        return;
      }
    }

    alert(`Deleted ${selected.length} file(s)`);
    await this.loadAnnouncement();
  }

  private async uploadNewMedia(): Promise<void> {
    if (this.newFiles.length === 0) return;

    const formData = new FormData();
    for (const file of this.newFiles) {
      formData.append('files', file);
    }

    try {
      const response = await apiService.postFormData(
        `/staff/mnr-user/announcements/${this.announcementId}/media`,
        formData
      );

      if (response.success) {
        alert(`Added ${this.newFiles.length} file(s)`);
        this.newFiles = [];
        await this.loadAnnouncement();
      } else {
        alert(response.error || 'Failed to upload files');
      }
    } catch (error: any) {
      alert(error.message || 'Upload failed');
    }
  }

  private async saveChanges(): Promise<void> {
    if (this.saving || !this.announcement) return;

    const title = (document.getElementById('titleInput') as HTMLInputElement).value.trim();
    const description = (document.getElementById('descriptionInput') as HTMLTextAreaElement).value.trim();

    if (!title) {
      alert('Title is required');
      return;
    }

    this.saving = true;
    const saveBtn = document.getElementById('saveBtn') as HTMLButtonElement;
    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.textContent = 'Saving...';
    }

    try {
      const formData = new FormData();
      formData.append('title', title);
      formData.append('description', description);

      const response = await apiService.putFormData(
        `/staff/mnr-user/announcements/${this.announcementId}/edit`,
        formData
      );

      if (response.success) {
        alert('Announcement updated successfully!');
        routerService.goBack();
      } else {
        alert(response.error || 'Failed to update');
      }
    } catch (error: any) {
      alert(error.message || 'Update failed');
    } finally {
      this.saving = false;
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save Changes';
      }
    }
  }

  private escapeHtml(str: string): string {
    return str.replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c] || c));
  }
}
