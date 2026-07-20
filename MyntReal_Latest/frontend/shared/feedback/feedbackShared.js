// Shared utilities for Announcements System
// Provides auth, API client, toast notifications, and common UI helpers

// ========== AUTH & SESSION ==========
export function getSessionToken() {
  const urlParams = new URLSearchParams(window.location.search);
  // DC Protocol: Multiple token sources for maximum compatibility
  // 1. URL parameter (for direct links)
  // 2. sessionStorage.session_token (set by page inline script via server template)
  // 3. window.sessionToken (set by server template global)
  // 4. sessionStorage.staff_token (fallback)
  // 5. localStorage.staff_token (staff login stores here)
  // 6. Cookie staff_token (cookie-based session)
  const urlToken = urlParams.get('session');
  const storageToken = sessionStorage.getItem('session_token');
  const windowToken = typeof window !== 'undefined' ? window.sessionToken : null;
  const sessionStaffToken = sessionStorage.getItem('staff_token');
  const localStaffToken = typeof localStorage !== 'undefined' ? localStorage.getItem('staff_token') : null;
  const cookieToken = (() => {
    try {
      const v = `; ${document.cookie}`;
      const parts = v.split('; staff_token=');
      if (parts.length === 2) return parts.pop().split(';').shift();
    } catch (_) {}
    return null;
  })();

  const token = urlToken || storageToken || windowToken || sessionStaffToken || localStaffToken || cookieToken || '';

  console.log('[feedbackShared] Token sources:', {
    urlToken: !!urlToken,
    storageToken: !!storageToken,
    windowToken: !!windowToken,
    sessionStaffToken: !!sessionStaffToken,
    localStaffToken: !!localStaffToken,
    cookieToken: !!cookieToken,
    finalToken: token ? 'present' : 'missing'
  });

  return token;
}

export function getUserRole() {
  return sessionStorage.getItem('user_role') || '';
}

export function getUserId() {
  return sessionStorage.getItem('user_id') || '';
}

// ========== API CLIENT ==========
const API_BASE = '/api/v1/feedback';

export const feedbackApi = {
  // Categories
  getCategories: async () => {
    const token = getSessionToken();
    const endpoint = token ? `${API_BASE}/categories` : `${API_BASE}/public/categories`;
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
    
    const res = await fetch(endpoint, { headers });
    if (!res.ok) throw new Error('Failed to fetch categories');
    return res.json();
  },

  createCategory: async (name, description) => {
    const res = await fetch(`${API_BASE}/categories`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getSessionToken()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ category_name: name, category_description: description || '' })
    });
    if (!res.ok) throw new Error('Failed to create category');
    return res.json();
  },

  updateCategory: async (id, name, description) => {
    const res = await fetch(`${API_BASE}/categories/${id}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${getSessionToken()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ category_name: name, category_description: description || '' })
    });
    if (!res.ok) throw new Error('Failed to update category');
    return res.json();
  },

  deleteCategory: async (id) => {
    const res = await fetch(`${API_BASE}/categories/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${getSessionToken()}` }
    });
    if (!res.ok) throw new Error('Failed to delete category');
    return res.json();
  },

  // Submissions
  getMySubmissions: async () => {
    const res = await fetch(`${API_BASE}/my-submissions`, {
      headers: { 'Authorization': `Bearer ${getSessionToken()}` }
    });
    if (!res.ok) throw new Error('Failed to fetch submissions');
    return res.json();
  },

  getPendingSubmissions: async () => {
    const res = await fetch(`${API_BASE}/pending`, {
      headers: { 'Authorization': `Bearer ${getSessionToken()}` }
    });
    if (!res.ok) throw new Error('Failed to fetch pending submissions');
    return res.json();
  },

  approveSubmission: async (id, comment = '') => {
    const headers = { 'Authorization': `Bearer ${getSessionToken()}` };
    const options = { method: 'POST', headers };
    
    if (comment) {
      const formData = new URLSearchParams();
      formData.append('comment', comment);
      headers['Content-Type'] = 'application/x-www-form-urlencoded';
      options.body = formData.toString();
    }
    
    const res = await fetch(`${API_BASE}/approve/${id}`, options);
    if (!res.ok) throw new Error('Failed to approve submission');
    return res.json();
  },

  rejectSubmission: async (id, comment) => {
    const formData = new URLSearchParams();
    formData.append('comment', comment);
    
    const res = await fetch(`${API_BASE}/reject/${id}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getSessionToken()}`,
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: formData.toString()
    });
    if (!res.ok) throw new Error('Failed to reject submission');
    return res.json();
  },

  deleteMedia: async (media_id) => {
    const res = await fetch(`${API_BASE}/media/${media_id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${getSessionToken()}`
      }
    });
    if (!res.ok) throw new Error('Failed to delete media');
    return res.json();
  },

  replaceMedia: async (media_id, file) => {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_BASE}/media/replace/${media_id}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getSessionToken()}`
      },
      body: formData
    });
    if (!res.ok) throw new Error('Failed to replace media');
    return res.json();
  },

  addMedia: async (submission_id, file) => {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_BASE}/media/add/${submission_id}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getSessionToken()}`
      },
      body: formData
    });
    if (!res.ok) throw new Error('Failed to add media');
    return res.json();
  },

  // Announcements
  getAnnouncements: async (filters = {}) => {
    const token = getSessionToken();
    const params = new URLSearchParams();
    if (filters.category_id) params.append('category_id', filters.category_id);
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    if (filters.include_hidden) params.append('include_hidden', 'true');
    
    console.log('[feedbackShared] getAnnouncements:', { hasToken: !!token, filters });
    
    // DC Protocol: Try authenticated endpoint first, fall back to public on auth errors
    if (token) {
      try {
        const authEndpoint = `${API_BASE}/announcements?${params}`;
        const res = await fetch(authEndpoint, { 
          headers: { 'Authorization': `Bearer ${token}` } 
        });
        
        if (res.ok) {
          const data = await res.json();
          console.log('[feedbackShared] Authenticated announcements:', data.length, 'items');
          return data;
        }
        
        // On 401/403, fall through to public endpoint
        console.warn('[feedbackShared] Auth endpoint failed:', res.status, '- falling back to public');
      } catch (err) {
        console.error('[feedbackShared] Auth fetch error:', err.message);
      }
    }
    
    // Fall back to public endpoint
    const publicEndpoint = `${API_BASE}/public/announcements?limit=100`;
    const res = await fetch(publicEndpoint);
    if (!res.ok) {
      console.error('[feedbackShared] Public endpoint failed:', res.status);
      throw new Error(`Failed to fetch announcements: ${res.status}`);
    }
    const data = await res.json();
    console.log('[feedbackShared] Public announcements:', data.length, 'items');
    return data;
  },

  hideAnnouncement: async (id) => {
    const res = await fetch(`${API_BASE}/hide/${id}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${getSessionToken()}` }
    });
    if (!res.ok) throw new Error('Failed to hide announcement');
    return res.json();
  },

  unhideAnnouncement: async (id) => {
    const res = await fetch(`${API_BASE}/unhide/${id}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${getSessionToken()}` }
    });
    if (!res.ok) throw new Error('Failed to unhide announcement');
    return res.json();
  },

  trackShare: async (id) => {
    const res = await fetch(`${API_BASE}/public/announcement/${id}?track_share=true`, {
      method: 'GET'
    });
    if (!res.ok) throw new Error('Failed to track share');
    return res.json();
  },

  deleteAnnouncement: async (id) => {
    const res = await fetch(`${API_BASE}/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${getSessionToken()}` }
    });
    if (!res.ok) throw new Error('Failed to delete announcement');
    return res.json();
  },

  // DC Protocol: Soft delete announcement (can be restored)
  softDeleteAnnouncement: async (id) => {
    const res = await fetch(`${API_BASE}/announcements/${id}/soft`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${getSessionToken()}` }
    });
    if (!res.ok) throw new Error('Failed to soft delete announcement');
    return res.json();
  },

  // DC Protocol: Hard delete announcement (permanent)
  hardDeleteAnnouncement: async (id) => {
    const res = await fetch(`${API_BASE}/announcements/${id}/hard`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${getSessionToken()}` }
    });
    if (!res.ok) throw new Error('Failed to hard delete announcement');
    return res.json();
  },

  // DC Protocol: Restore soft-deleted announcement
  restoreAnnouncement: async (id) => {
    const res = await fetch(`${API_BASE}/announcements/${id}/restore`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${getSessionToken()}` }
    });
    if (!res.ok) throw new Error('Failed to restore announcement');
    return res.json();
  },

  // DC Protocol: List soft-deleted announcements
  getDeletedAnnouncements: async () => {
    const res = await fetch(`${API_BASE}/announcements/deleted`, {
      headers: { 'Authorization': `Bearer ${getSessionToken()}` }
    });
    if (!res.ok) throw new Error('Failed to fetch deleted announcements');
    return res.json();
  },

  // DC Protocol: Staff announcements with all status filters
  getAnnouncementsStaff: async (filters = {}) => {
    const token = getSessionToken();
    const params = new URLSearchParams();
    if (filters.category_id) params.append('category_id', filters.category_id);
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    if (filters.city) params.append('city', filters.city);
    if (filters.user_id) params.append('user_id', filters.user_id);
    if (filters.user_name) params.append('user_name', filters.user_name);
    if (filters.status) params.append('status', filters.status);
    if (filters.include_hidden) params.append('include_hidden', 'true');
    if (filters.include_deleted) params.append('include_deleted', 'true');
    if (filters.include_all_statuses) params.append('include_all_statuses', 'true');
    
    console.log('[feedbackShared] getAnnouncementsStaff:', { hasToken: !!token, filters });
    
    const res = await fetch(`${API_BASE}/announcements/staff?${params}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (!res.ok) {
      const errorText = await res.text();
      console.error('[feedbackShared] Staff announcements failed:', res.status, errorText);
      throw new Error(`Failed to fetch staff announcements: ${res.status}`);
    }
    
    const data = await res.json();
    console.log('[feedbackShared] Staff announcements:', data.length, 'items');
    return data;
  }
};

// ========== TOAST NOTIFICATIONS ==========
export function showToast(message, type = 'info') {
  const toastContainer = document.getElementById('toastContainer') || createToastContainer();
  
  const toast = document.createElement('div');
  toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} border-0`;
  toast.setAttribute('role', 'alert');
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>
  `;
  
  toastContainer.appendChild(toast);
  const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
  bsToast.show();
  
  toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

function createToastContainer() {
  const container = document.createElement('div');
  container.id = 'toastContainer';
  container.className = 'toast-container position-fixed top-0 end-0 p-3';
  container.style.zIndex = '9999';
  document.body.appendChild(container);
  return container;
}

// ========== MODAL HELPERS ==========
export function showConfirmModal(title, message, onConfirm) {
  const modalId = 'confirmModal' + Date.now();
  const modal = document.createElement('div');
  modal.className = 'modal fade';
  modal.id = modalId;
  modal.innerHTML = `
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">${title}</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">${message}</div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
          <button type="button" class="btn btn-primary" id="${modalId}Confirm">Confirm</button>
        </div>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  const bsModal = new bootstrap.Modal(modal);
  
  document.getElementById(`${modalId}Confirm`).addEventListener('click', () => {
    bsModal.hide();
    onConfirm();
  });
  
  modal.addEventListener('hidden.bs.modal', () => modal.remove());
  bsModal.show();
}

// ========== DATE FORMATTING ==========
export function formatDate(dateString) {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-IN', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

// ========== MEDIA PREVIEW ==========
export function showMediaLightbox(mediaItems) {
  if (!mediaItems || mediaItems.length === 0) {
    showToast('This announcement has no media files', 'info');
    return;
  }
  
  const modalId = 'mediaLightbox' + Date.now();
  const modal = document.createElement('div');
  modal.className = 'modal fade';
  modal.id = modalId;
  
  // DC Protocol: Safari-compatible video with preload and time fragment for first frame
  const carouselItems = mediaItems.map((item, index) => {
    const isVideo = item.media_type === 'video';
    const safariVideoUrl = item.file_path + (item.file_path.includes('#') ? '' : '#t=0.001');
    const videoMimeType = item.file_type || 'video/mp4';
    return `
      <div class="carousel-item ${index === 0 ? 'active' : ''}">
        ${isVideo 
          ? `<video controls playsinline muted preload="metadata" class="d-block w-100" style="max-height: 80vh;"
                   onloadedmetadata="this.play().catch(e => console.log('Autoplay blocked:', e))">
               <source src="${safariVideoUrl}" type="${videoMimeType}">
             </video>`
          : `<img src="${item.file_path}" class="d-block w-100" style="max-height: 80vh; object-fit: contain;">`
        }
      </div>
    `;
  }).join('');
  
  modal.innerHTML = `
    <div class="modal-dialog modal-xl modal-dialog-centered">
      <div class="modal-content bg-dark">
        <div class="modal-header border-0">
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body p-0">
          <div id="mediaCarousel${modalId}" class="carousel slide" data-bs-ride="carousel">
            <div class="carousel-inner">${carouselItems}</div>
            ${mediaItems.length > 1 ? `
              <button class="carousel-control-prev" type="button" data-bs-target="#mediaCarousel${modalId}" data-bs-slide="prev">
                <span class="carousel-control-prev-icon"></span>
              </button>
              <button class="carousel-control-next" type="button" data-bs-target="#mediaCarousel${modalId}" data-bs-slide="next">
                <span class="carousel-control-next-icon"></span>
              </button>
            ` : ''}
          </div>
        </div>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  const bsModal = new bootstrap.Modal(modal);
  modal.addEventListener('hidden.bs.modal', () => modal.remove());
  bsModal.show();
}

// ========== LOADING SPINNER ==========
export function showSpinner(container) {
  container.innerHTML = `
    <div class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
    </div>
  `;
}

export function showEmptyState(container, message, icon = 'inbox') {
  container.innerHTML = `
    <div class="text-center py-5 text-muted">
      <i class="fas fa-${icon} fa-4x mb-3"></i>
      <p class="fs-5">${message}</p>
    </div>
  `;
}

// ========== SECURITY ==========
export function escapeHTML(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
