/**
 * Zynova Training Page (EVolution Training Center - ETC)
 * DC Protocol: DC_MOBILE_ZYNOVA_TRAIN_001
 * Matches web page layout exactly
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';
import { routerService } from '../../services/router.service';

interface ZynovaTrainingData {
  is_member: boolean;
  leads_count: number;
  won_deals: number;
  total_earnings: number;
  message?: string;
}

export class ZynovaTraining {
  private container: HTMLElement;
  private data: ZynovaTrainingData | null = null;
  private loading: boolean = true;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadData();
  }

  private async loadData(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>('/users/zynova/training');
      if (response.success && response.data) {
        this.data = response.data;
      }
    } catch (error) {
      console.error('[ZynovaTraining] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        .zynova-training-page {
          background: #0d1b2a;
          min-height: 100vh;
        }
        .zynova-training-page .page-content {
          padding: 16px;
        }
        .zynova-header-card {
          background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: white;
        }
        .zynova-header-card .header-title {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 6px;
        }
        .zynova-header-card .header-title h2 {
          font-size: 18px;
          margin: 0;
          font-weight: 600;
        }
        .zynova-header-card .segment-badge {
          background: rgba(0,0,0,0.2);
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 600;
        }
        .zynova-header-card .header-subtitle {
          font-size: 13px;
          opacity: 0.9;
          margin: 0;
        }
        .requirements-card {
          background: #1a2744;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
        }
        .requirements-card .req-header {
          display: flex;
          align-items: center;
          gap: 8px;
          color: #f59e0b;
          font-weight: 600;
          font-size: 14px;
          margin-bottom: 12px;
        }
        .requirements-card .req-text {
          color: #8892b0;
          font-size: 13px;
          margin-bottom: 16px;
          line-height: 1.5;
        }
        .requirements-card .activities-header {
          color: #e6f1ff;
          font-weight: 600;
          font-size: 13px;
          margin-bottom: 10px;
        }
        .requirements-card .activities-list {
          list-style: none;
          padding: 0;
          margin: 0 0 16px 0;
        }
        .requirements-card .activities-list li {
          color: #8892b0;
          font-size: 13px;
          padding: 4px 0 4px 20px;
          position: relative;
        }
        .requirements-card .activities-list li::before {
          content: "•";
          position: absolute;
          left: 6px;
          color: #64ffda;
        }
        .requirements-card .note-text {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          color: #8892b0;
          font-size: 12px;
          padding: 12px;
          background: rgba(100, 255, 218, 0.05);
          border-radius: 8px;
          line-height: 1.4;
        }
        .requirements-card .note-text .note-icon {
          color: #64ffda;
          flex-shrink: 0;
        }
        .welcome-section {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          border-radius: 16px;
          padding: 32px 20px;
          text-align: center;
          color: white;
        }
        .welcome-section .welcome-icon {
          font-size: 48px;
          margin-bottom: 16px;
        }
        .welcome-section h3 {
          font-size: 20px;
          font-weight: 700;
          margin: 0 0 12px 0;
        }
        .welcome-section .quote {
          font-style: italic;
          font-size: 13px;
          opacity: 0.9;
          margin-bottom: 20px;
          line-height: 1.5;
        }
        .welcome-section .sub-header {
          font-weight: 600;
          font-size: 15px;
          margin-bottom: 8px;
        }
        .welcome-section .sub-text {
          font-size: 13px;
          opacity: 0.9;
          margin-bottom: 20px;
          line-height: 1.5;
        }
        .welcome-section .cta-btn {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          background: white;
          color: #059669;
          padding: 12px 24px;
          border-radius: 8px;
          font-weight: 600;
          font-size: 14px;
          border: none;
          cursor: pointer;
        }
        .welcome-section .progress-note {
          margin-top: 16px;
          font-size: 12px;
          opacity: 0.8;
        }
      </style>
      <div class="page-container zynova-training-page">
        ${PageHeader.render({ title: 'EVolution Training Center', showBack: true })}
        
        <div id="pageContent" class="page-content">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'EVolution Training Center', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    content.innerHTML = `
      <div class="zynova-header-card">
        <div class="header-title">
          <span>🎓</span>
          <h2>EVolution Training Center (ETC)</h2>
          <span class="segment-badge">Training</span>
        </div>
        <p class="header-subtitle">Track your training leads, won deals, and earnings from the ETC program</p>
      </div>

      <div class="requirements-card">
        <div class="req-header">
          <span>📹</span>
          <span>Feedback Video and Photos Requirement</span>
        </div>
        <p class="req-text">
          <strong>For Zynova incentive eligibility:</strong> Sharing feedback videos and photos is mandatory for members activated before 1st Dec 2025.
        </p>
        <div class="activities-header">Eligible Engagement Activities:</div>
        <ul class="activities-list">
          <li>Reels (video content)</li>
          <li>WhatsApp Status sharing</li>
          <li>Social Media posts</li>
          <li>Sharing & Ratings in Announcement sections</li>
          <li>Engaging with teams</li>
          <li>Attending Zoom calls</li>
        </ul>
        <div class="note-text">
          <span class="note-icon">ℹ️</span>
          <span>Please note: Submitted feedback videos and photos may be publicly displayed on our platforms for promotional and community engagement purposes. By sharing your content, you acknowledge and consent to this use.</span>
        </div>
      </div>

      <div class="welcome-section">
        <div class="welcome-icon">🎓</div>
        <h3>Transform Lives Through Knowledge</h3>
        <p class="quote">"An investment in knowledge pays the best interest." - Benjamin Franklin</p>
        <div class="sub-header">Create Self-Empowerment in Society</div>
        <p class="sub-text">Transform lives through education. Every student you refer is a step towards building a better future. Join the EVolution Training Center and be part of the change!</p>
        <button class="cta-btn" id="btnAddTrainingLead">
          <span>👤</span>
          <span>Add Training Lead</span>
        </button>
        <p class="progress-note">Start your journey by adding your first training lead</p>
      </div>
    `;

    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    const addLeadBtn = document.getElementById('btnAddTrainingLead');
    if (addLeadBtn) {
      addLeadBtn.addEventListener('click', () => {
        routerService.navigate('mnr-my-leads');
      });
    }
  }
}
