/**
 * Staff Task Reviews Page
 * DC Protocol: DC_MOBILE_TASK_REVIEWS_001
 * Review and rate completed tasks
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface TaskReview {
  id: number;
  task_id: number;
  task_title: string;
  employee_name: string;
  emp_code: string;
  completed_at: string;
  rating?: number;
  feedback?: string;
  reviewer_name?: string;
  reviewed_at?: string;
  status: string;
}

export class StaffTaskReviewsPage {
  private container: HTMLElement;
  private reviews: TaskReview[] = [];
  private loading: boolean = true;
  private filterStatus: string = 'pending';
  private selectedReview: TaskReview | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadReviews();
  }

  private async loadReviews(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      // DC Protocol: Match web's endpoint exactly
      const response = await apiService.get<any>(`/staff/tasks/manager-review/pending?status=${this.filterStatus}`);
      console.log('[StaffTaskReviewsPage] API response:', response);

      // DC Protocol: Handle multiple response formats
      const data = response.data as any;
      if (response.success !== false && data) {
        if (data.tasks) {
          this.reviews = data.tasks;
        } else if (data.reviews) {
          this.reviews = data.reviews;
        } else if (Array.isArray(data)) {
          this.reviews = data;
        } else {
          this.reviews = [];
        }
        console.log('[StaffTaskReviewsPage] Loaded reviews:', this.reviews.length);
      } else {
        this.reviews = [];
      }
    } catch (error) {
      console.error('[StaffTaskReviewsPage] Failed to load:', error);
      this.reviews = [];
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Task Reviews', showBack: true })}
        
        <div class="filter-tabs">
          <button class="filter-tab ${this.filterStatus === 'pending' ? 'active' : ''}" data-status="pending">
            Pending Review
          </button>
          <button class="filter-tab ${this.filterStatus === 'reviewed' ? 'active' : ''}" data-status="reviewed">
            Reviewed
          </button>
        </div>

        <div class="stats-row">
          <div class="stat-card mini pending">
            <span class="stat-value" id="pendingCount">0</span>
            <span class="stat-label">Pending</span>
          </div>
          <div class="stat-card mini success">
            <span class="stat-value" id="reviewedCount">0</span>
            <span class="stat-label">Reviewed</span>
          </div>
        </div>

        <div class="list-container" id="reviewsList">
          <div class="loading-state">Loading reviews...</div>
        </div>
      </div>

      <!-- Review Modal -->
      <div class="modal-overlay" id="reviewModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Rate Task</h4>
            <button class="modal-close" id="closeModal">&times;</button>
          </div>
          <div class="modal-body" id="modalBody"></div>
          <div class="modal-footer" id="modalFooter"></div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    this.container.querySelectorAll('.filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.filterStatus = (tab as HTMLElement).dataset.status || 'pending';
        this.container.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.loadReviews();
      });
    });

    document.getElementById('closeModal')?.addEventListener('click', () => this.hideModal());
  }

  private updateList(): void {
    const listContainer = document.getElementById('reviewsList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading reviews...</div>';
      return;
    }

    const pendingEl = document.getElementById('pendingCount');
    const reviewedEl = document.getElementById('reviewedCount');
    if (pendingEl) pendingEl.textContent = this.reviews.filter(r => r.status === 'pending').length.toString();
    if (reviewedEl) reviewedEl.textContent = this.reviews.filter(r => r.status === 'reviewed').length.toString();

    if (this.reviews.length === 0) {
      listContainer.innerHTML = `<div class="empty-state">No ${this.filterStatus === 'pending' ? 'pending' : 'reviewed'} tasks</div>`;
      return;
    }

    listContainer.innerHTML = this.reviews.map(review => `
      <div class="list-card review-card">
        <div class="review-header">
          <div class="review-task">${review.task_title}</div>
          <span class="status-badge ${review.status}">${review.status}</span>
        </div>
        <div class="review-employee">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
          <span>${review.employee_name} (${review.emp_code})</span>
        </div>
        <div class="review-meta">
          <span class="meta-item">Completed: ${this.formatDate(review.completed_at)}</span>
        </div>
        
        ${review.rating ? `
          <div class="review-rating">
            <span class="rating-label">Rating:</span>
            <span class="rating-stars">${this.renderStars(review.rating)}</span>
          </div>
          ${review.feedback ? `<div class="review-feedback">"${review.feedback}"</div>` : ''}
          ${review.reviewer_name ? `<div class="reviewer-info">Reviewed by ${review.reviewer_name} on ${this.formatDate(review.reviewed_at)}</div>` : ''}
        ` : `
          <button class="btn btn-primary btn-block review-btn" data-id="${review.id}">
            Rate This Task
          </button>
        `}
      </div>
    `).join('');

    this.container.querySelectorAll('.review-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = parseInt((btn as HTMLElement).dataset.id || '0');
        this.showReviewModal(id);
      });
    });
  }

  private showReviewModal(id: number): void {
    this.selectedReview = this.reviews.find(r => r.id === id) || null;
    if (!this.selectedReview) return;

    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');
    const modal = document.getElementById('reviewModal');

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="modal-summary">
          <p><strong>${this.selectedReview.task_title}</strong></p>
          <p>Completed by: ${this.selectedReview.employee_name}</p>
        </div>
        <div class="form-group">
          <label>Rating</label>
          <div class="star-rating" id="starRating">
            ${[1, 2, 3, 4, 5].map(i => `
              <span class="star" data-rating="${i}">★</span>
            `).join('')}
          </div>
          <input type="hidden" id="ratingValue" value="0">
        </div>
        <div class="form-group">
          <label>Feedback (Optional)</label>
          <textarea id="reviewFeedback" class="form-textarea" rows="3" placeholder="Enter feedback..."></textarea>
        </div>
      `;

      const stars = modalBody.querySelectorAll('.star');
      const ratingInput = document.getElementById('ratingValue') as HTMLInputElement;
      stars.forEach(star => {
        star.addEventListener('click', () => {
          const rating = parseInt((star as HTMLElement).dataset.rating || '0');
          if (ratingInput) ratingInput.value = rating.toString();
          stars.forEach((s, idx) => {
            s.classList.toggle('active', idx < rating);
          });
        });
      });
    }

    if (modalFooter) {
      modalFooter.innerHTML = `
        <button class="btn btn-secondary" id="cancelReview">Cancel</button>
        <button class="btn btn-primary" id="submitReview">Submit Review</button>
      `;

      document.getElementById('cancelReview')?.addEventListener('click', () => this.hideModal());
      document.getElementById('submitReview')?.addEventListener('click', () => this.submitReview());
    }

    if (modal) modal.style.display = 'flex';
  }

  private async submitReview(): Promise<void> {
    if (!this.selectedReview) return;

    const rating = parseInt((document.getElementById('ratingValue') as HTMLInputElement)?.value || '0');
    const feedback = (document.getElementById('reviewFeedback') as HTMLTextAreaElement)?.value || '';

    if (rating === 0) {
      alert('Please select a rating');
      return;
    }

    try {
      // DC Protocol: Match web's endpoint exactly
      const response = await apiService.post(`/staff/tasks/manager-review/approve`, {
        task_id: this.selectedReview.task_id,
        rating,
        feedback
      });

      if (response.success) {
        alert('Review submitted successfully');
        this.hideModal();
        this.loadReviews();
      } else {
        alert(response.error || 'Failed to submit review');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to submit review');
    }
  }

  private hideModal(): void {
    const modal = document.getElementById('reviewModal');
    if (modal) modal.style.display = 'none';
    this.selectedReview = null;
  }

  private renderStars(rating: number): string {
    return Array(5).fill(0).map((_, i) => 
      `<span class="star ${i < rating ? 'active' : ''}">★</span>`
    ).join('');
  }

  private formatDate(dateStr: string | undefined): string {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  }
}
