/**
 * MNR Feedback Submit Page
 * DC Protocol: DC_MOBILE_MNR_FEEDBACK_001
 * Submit feedback and testimonials
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface Submission {
  id: number;
  type: string;
  title: string;
  status: string;
  created_at: string;
}

export class MNRFeedback {
  private container: HTMLElement;
  private submissions: Submission[] = [];
  private loading: boolean = true;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadSubmissions();
  }

  private async loadSubmissions(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>('/feedback/my-submissions');
      if (response.success && response.data) {
        this.submissions = response.data.submissions || response.data || [];
      }
    } catch (error) {
      console.error('[MNRFeedback] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Feedback & Submissions', showBack: true })}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'Feedback & Submissions', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    content.innerHTML = `
      <div class="feedback-hero card">
        <div class="hero-icon">📝</div>
        <h3>Share Your Experience</h3>
        <p>Submit feedback videos, photos, and testimonials</p>
      </div>

      <div class="submit-options">
        <button class="submit-option card" id="submitVideoBtn">
          <div class="option-icon">🎥</div>
          <div class="option-info">
            <h4>Video Testimonial</h4>
            <p>Share your success story</p>
          </div>
        </button>
        <button class="submit-option card" id="submitPhotoBtn">
          <div class="option-icon">📷</div>
          <div class="option-info">
            <h4>Photo Feedback</h4>
            <p>Share photos with team</p>
          </div>
        </button>
        <button class="submit-option card" id="submitReviewBtn">
          <div class="option-icon">⭐</div>
          <div class="option-info">
            <h4>Written Review</h4>
            <p>Write about your experience</p>
          </div>
        </button>
      </div>

      <h4 class="section-title">My Submissions</h4>
      ${this.submissions.length > 0 ? `
        <div class="submissions-list">
          ${this.submissions.map(s => this.renderSubmission(s)).join('')}
        </div>
      ` : `
        <div class="empty-state card">
          <div class="empty-icon">📝</div>
          <p>No submissions yet</p>
        </div>
      `}

      <div class="notice-card card warning">
        <h4>⚠️ Guidelines</h4>
        <ul>
          <li>Feedback may be publicly displayed</li>
          <li>Videos should be under 2 minutes</li>
          <li>Photos must be clear and relevant</li>
          <li>Review within 24-48 hours</li>
        </ul>
      </div>
    `;

    this.attachListeners();
  }

  private attachListeners(): void {
    document.getElementById('submitVideoBtn')?.addEventListener('click', () => {
      alert('Please use the web portal for video submissions');
    });

    document.getElementById('submitPhotoBtn')?.addEventListener('click', () => {
      alert('Please use the web portal for photo submissions');
    });

    document.getElementById('submitReviewBtn')?.addEventListener('click', () => {
      alert('Please use the web portal for written reviews');
    });
  }

  private renderSubmission(sub: Submission): string {
    const statusClass = sub.status.toLowerCase();
    const date = new Date(sub.created_at).toLocaleDateString('en', {
      day: 'numeric', month: 'short', year: 'numeric'
    });

    return `
      <div class="submission-card card ${statusClass}">
        <div class="sub-header">
          <span class="sub-type">${sub.type}</span>
          <span class="status-badge ${statusClass}">${sub.status}</span>
        </div>
        <h4>${sub.title}</h4>
        <span class="sub-date">${date}</span>
      </div>
    `;
  }
}
