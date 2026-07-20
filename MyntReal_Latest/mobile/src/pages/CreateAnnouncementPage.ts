/**
 * Create Announcement Page
 * DC Protocol: DC_MOBILE_CREATE_ANNOUNCEMENT_001
 * Submit announcements with mixed media (photos + videos)
 * Minimum 3 files, Photos up to 10, Videos max 3 minutes
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';

interface Category {
  id: number;
  name: string;
}

interface SelectedFile {
  file: File;
  type: 'image' | 'video';
  preview: string;
  duration?: number;
}

export class CreateAnnouncementPage {
  private container: HTMLElement;
  private categories: Category[] = [];
  private selectedFiles: SelectedFile[] = [];
  private submitting: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadCategories();
  }

  private async loadCategories(): Promise<void> {
    try {
      const response = await apiService.get<any>('/feedback/categories');
      if (response.success && response.data) {
        this.categories = Array.isArray(response.data) ? response.data : (response.data.categories || []);
        this.updateCategoryDropdown();
      }
    } catch (error) {
      console.error('[CreateAnnouncementPage] Failed to load categories:', error);
    }
  }

  private updateCategoryDropdown(): void {
    const select = document.getElementById('categorySelect') as HTMLSelectElement;
    if (!select) return;
    
    const options = this.categories.map(c => `<option value="${c.id}">${c.name}</option>`);
    select.innerHTML = '<option value="">Select Category</option>' + options.join('');
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Create Announcement', showBack: true })}
        
        <form id="announcementForm" class="form-container">
          <div class="form-section">
            <div class="form-group">
              <label>Category *</label>
              <select id="categorySelect" class="form-select" required>
                <option value="">Select Category</option>
              </select>
            </div>

            <div class="form-group">
              <label>Title *</label>
              <input type="text" id="titleInput" class="form-input" placeholder="Announcement title" maxlength="200" required>
            </div>

            <div class="form-group">
              <label>Description</label>
              <textarea id="descriptionInput" class="form-textarea" rows="4" placeholder="Enter announcement details..."></textarea>
            </div>
          </div>

          <div class="form-section">
            <h4>Media Files (Photos & Videos)</h4>
            <p class="hint-text">Minimum 3 files | Photos up to 10 | Videos max 3 minutes</p>
            
            <div class="file-upload-area" id="fileUploadArea">
              <input type="file" id="mediaInput" accept="image/*,video/*" multiple style="display: none;">
              <button type="button" class="btn btn-outline" id="selectFilesBtn">
                <span class="icon">📁</span> Select Photos & Videos
              </button>
            </div>

            <div id="mediaPreview" class="media-preview-grid"></div>
            <div id="validationErrors" class="validation-errors"></div>
            <div id="mediaCount" class="media-count"></div>
          </div>

          <div class="form-actions sticky-bottom">
            <button type="button" class="btn btn-secondary" id="cancelBtn">Cancel</button>
            <button type="submit" class="btn btn-primary" id="submitBtn">Submit Announcement</button>
          </div>
        </form>
      </div>

      <style>
        .file-upload-area { padding: 16px; text-align: center; margin-bottom: 16px; }
        .media-preview-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
        .media-preview-item { width: 80px; height: 80px; position: relative; border-radius: 8px; overflow: hidden; }
        .media-preview-item img, .media-preview-item video { width: 100%; height: 100%; object-fit: cover; }
        .media-preview-item .remove-btn { position: absolute; top: 2px; right: 2px; background: rgba(255,0,0,0.8); color: white; border: none; border-radius: 50%; width: 20px; height: 20px; font-size: 12px; cursor: pointer; }
        .media-preview-item .type-badge { position: absolute; bottom: 2px; left: 2px; background: rgba(0,0,0,0.7); color: white; padding: 2px 4px; border-radius: 4px; font-size: 8px; }
        .validation-errors { color: #ef4444; font-size: 12px; margin-bottom: 8px; }
        .media-count { color: #888; font-size: 12px; }
        .hint-text { color: #888; font-size: 12px; margin-bottom: 12px; }
      </style>
    `;

    PageHeader.attachBackHandler();
    this.attachListeners();
  }

  private attachListeners(): void {
    document.getElementById('cancelBtn')?.addEventListener('click', () => {
      routerService.goBack();
    });

    document.getElementById('selectFilesBtn')?.addEventListener('click', () => {
      document.getElementById('mediaInput')?.click();
    });

    document.getElementById('mediaInput')?.addEventListener('change', (e) => {
      this.handleFileSelection(e);
    });

    document.getElementById('announcementForm')?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.submitAnnouncement();
    });
  }

  private async handleFileSelection(e: Event): Promise<void> {
    const input = e.target as HTMLInputElement;
    const files = Array.from(input.files || []);
    
    const imageExts = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif'];
    const videoExts = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.3gp'];

    for (const file of files) {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase();
      const isImage = imageExts.includes(ext);
      const isVideo = videoExts.includes(ext);

      if (isImage || isVideo) {
        const selectedFile: SelectedFile = {
          file,
          type: isVideo ? 'video' : 'image',
          preview: URL.createObjectURL(file)
        };

        if (isVideo) {
          selectedFile.duration = await this.getVideoDuration(file);
        }

        this.selectedFiles.push(selectedFile);
      }
    }

    this.updateMediaPreview();
    input.value = '';
  }

  private getVideoDuration(file: File): Promise<number> {
    return new Promise((resolve) => {
      const video = document.createElement('video');
      video.preload = 'metadata';
      video.onloadedmetadata = () => {
        URL.revokeObjectURL(video.src);
        resolve(video.duration);
      };
      video.onerror = () => resolve(0);
      video.src = URL.createObjectURL(file);
    });
  }

  private updateMediaPreview(): void {
    const preview = document.getElementById('mediaPreview');
    const errors = document.getElementById('validationErrors');
    const count = document.getElementById('mediaCount');
    if (!preview || !errors || !count) return;

    const imageCount = this.selectedFiles.filter(f => f.type === 'image').length;
    const videoCount = this.selectedFiles.filter(f => f.type === 'video').length;
    const totalCount = this.selectedFiles.length;

    preview.innerHTML = this.selectedFiles.map((sf, idx) => `
      <div class="media-preview-item">
        ${sf.type === 'video' ? 
          `<video src="${sf.preview}"></video>` :
          `<img src="${sf.preview}" alt="Preview">`
        }
        <button type="button" class="remove-btn" data-index="${idx}">&times;</button>
        <span class="type-badge">${sf.type === 'video' ? 'VIDEO' : 'PHOTO'}</span>
      </div>
    `).join('');

    preview.querySelectorAll('.remove-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const index = parseInt((e.target as HTMLElement).dataset.index || '0');
        URL.revokeObjectURL(this.selectedFiles[index].preview);
        this.selectedFiles.splice(index, 1);
        this.updateMediaPreview();
      });
    });

    const errorMessages: string[] = [];
    if (totalCount < 3) {
      errorMessages.push('Minimum 3 media files required');
    }
    if (imageCount > 10) {
      errorMessages.push('Maximum 10 photos allowed');
    }
    const longVideos = this.selectedFiles.filter(f => f.type === 'video' && (f.duration || 0) > 180);
    longVideos.forEach(v => {
      errorMessages.push(`Video "${v.file.name}" exceeds 3 minute limit`);
    });

    errors.innerHTML = errorMessages.map(e => `<div>⚠️ ${e}</div>`).join('');
    count.textContent = `Selected: ${imageCount} photo(s), ${videoCount} video(s)`;
  }

  private async submitAnnouncement(): Promise<void> {
    if (this.submitting) return;

    const categoryId = (document.getElementById('categorySelect') as HTMLSelectElement).value;
    const title = (document.getElementById('titleInput') as HTMLInputElement).value.trim();
    const description = (document.getElementById('descriptionInput') as HTMLTextAreaElement).value.trim();

    if (!categoryId) {
      alert('Please select a category');
      return;
    }
    if (!title) {
      alert('Please enter a title');
      return;
    }
    if (this.selectedFiles.length < 3) {
      alert('Minimum 3 media files required');
      return;
    }

    const imageCount = this.selectedFiles.filter(f => f.type === 'image').length;
    if (imageCount > 10) {
      alert('Maximum 10 photos allowed');
      return;
    }

    const longVideos = this.selectedFiles.filter(f => f.type === 'video' && (f.duration || 0) > 180);
    if (longVideos.length > 0) {
      alert('Some videos exceed 3 minute limit');
      return;
    }

    this.submitting = true;
    const submitBtn = document.getElementById('submitBtn') as HTMLButtonElement;
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Submitting...';
    }

    try {
      const formData = new FormData();
      formData.append('category_id', categoryId);
      formData.append('submission_type', 'mixed');
      formData.append('title', title);
      formData.append('description', description);
      
      for (const sf of this.selectedFiles) {
        formData.append('files', sf.file);
      }

      const response = await apiService.postFormData('/feedback/submit', formData);

      if (response.success) {
        alert('Announcement submitted successfully!');
        routerService.navigate('announcements');
      } else {
        alert(response.error || 'Failed to submit announcement');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to submit announcement');
    } finally {
      this.submitting = false;
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Announcement';
      }
    }
  }
}
