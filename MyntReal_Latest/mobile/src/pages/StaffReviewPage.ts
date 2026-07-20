/**
 * Staff Review Dashboard Page
 * DC Protocol: DC_MOBILE_STAFF_REVIEW_001
 * Progress review dashboard with performance metrics
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface ProgressMetrics {
  tasks_completed: number;
  tasks_pending: number;
  tasks_overdue: number;
  kra_score: number;
  attendance_percentage: number;
  leaves_taken: number;
  journeys_count: number;
  total_distance: number;
}

interface TeamMember {
  id: number;
  name: string;
  emp_code: string;
  department: string;
  designation: string;
  tasks_pending: number;
  kra_score: number;
  attendance_percentage: number;
}

export class StaffReviewPage {
  private container: HTMLElement;
  private metrics: ProgressMetrics | null = null;
  private teamMembers: TeamMember[] = [];
  private loading: boolean = true;
  private viewType: 'my' | 'team' = 'my';
  private dateRange: string = 'month';

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
      if (this.viewType === 'my') {
        const response = await apiService.get<any>(`/staff/progress/my?range=${this.dateRange}`);
        console.log('[StaffReviewPage] My progress:', response);
        if (response.success && response.data) {
          this.metrics = response.data;
        }
      } else {
        const response = await apiService.get<any>(`/staff/progress/team?range=${this.dateRange}`);
        console.log('[StaffReviewPage] Team progress:', response);
        if (response.success && response.data) {
          this.teamMembers = response.data.members || response.data || [];
        }
      }
    } catch (error) {
      console.error('[StaffReviewPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Review Dashboard', showBack: true })}
        
        <div class="view-toggle">
          <button class="toggle-btn ${this.viewType === 'my' ? 'active' : ''}" data-view="my">
            My Progress
          </button>
          <button class="toggle-btn ${this.viewType === 'team' ? 'active' : ''}" data-view="team">
            Team Progress
          </button>
        </div>

        <div class="date-filter">
          <select id="dateRange" class="filter-select">
            <option value="week" ${this.dateRange === 'week' ? 'selected' : ''}>This Week</option>
            <option value="month" ${this.dateRange === 'month' ? 'selected' : ''}>This Month</option>
            <option value="quarter" ${this.dateRange === 'quarter' ? 'selected' : ''}>This Quarter</option>
            <option value="year" ${this.dateRange === 'year' ? 'selected' : ''}>This Year</option>
          </select>
        </div>

        <div class="content-area" id="contentArea">
          <div class="loading-state">Loading progress data...</div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    this.container.querySelectorAll('.toggle-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.viewType = (btn as HTMLElement).dataset.view as 'my' | 'team';
        this.container.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.loadData();
      });
    });

    document.getElementById('dateRange')?.addEventListener('change', (e) => {
      this.dateRange = (e.target as HTMLSelectElement).value;
      this.loadData();
    });
  }

  private updateContent(): void {
    const contentArea = document.getElementById('contentArea');
    if (!contentArea) return;

    if (this.loading) {
      contentArea.innerHTML = '<div class="loading-state">Loading progress data...</div>';
      return;
    }

    if (this.viewType === 'my') {
      this.renderMyProgress(contentArea);
    } else {
      this.renderTeamProgress(contentArea);
    }
  }

  private renderMyProgress(container: HTMLElement): void {
    if (!this.metrics) {
      container.innerHTML = '<div class="empty-state">No progress data available</div>';
      return;
    }

    const m = this.metrics;
    container.innerHTML = `
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-icon tasks">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
          </div>
          <div class="metric-info">
            <div class="metric-value">${m.tasks_completed}</div>
            <div class="metric-label">Tasks Completed</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon pending">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <div class="metric-info">
            <div class="metric-value">${m.tasks_pending}</div>
            <div class="metric-label">Tasks Pending</div>
          </div>
        </div>

        <div class="metric-card ${m.tasks_overdue > 0 ? 'alert' : ''}">
          <div class="metric-icon overdue">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          </div>
          <div class="metric-info">
            <div class="metric-value">${m.tasks_overdue}</div>
            <div class="metric-label">Overdue</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon kra">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <circle cx="12" cy="12" r="6"/>
              <circle cx="12" cy="12" r="2"/>
            </svg>
          </div>
          <div class="metric-info">
            <div class="metric-value">${m.kra_score}%</div>
            <div class="metric-label">KRA Score</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon attendance">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
              <line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/>
              <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
          </div>
          <div class="metric-info">
            <div class="metric-value">${m.attendance_percentage}%</div>
            <div class="metric-label">Attendance</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon leaves">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 22c6-3 10-8 10-14a10 10 0 0 0-20 0c0 6 4 11 10 14z"/>
            </svg>
          </div>
          <div class="metric-info">
            <div class="metric-value">${m.leaves_taken}</div>
            <div class="metric-label">Leaves Taken</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon journeys">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="10" r="3"/>
              <path d="M12 21.7C17.3 17 20 13 20 10a8 8 0 1 0-16 0c0 3 2.7 7 8 11.7z"/>
            </svg>
          </div>
          <div class="metric-info">
            <div class="metric-value">${m.journeys_count}</div>
            <div class="metric-label">Journeys</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon distance">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6 6 18"/>
              <path d="M6 6l12 12"/>
            </svg>
          </div>
          <div class="metric-info">
            <div class="metric-value">${m.total_distance} km</div>
            <div class="metric-label">Distance</div>
          </div>
        </div>
      </div>
    `;
  }

  private renderTeamProgress(container: HTMLElement): void {
    if (this.teamMembers.length === 0) {
      container.innerHTML = '<div class="empty-state">No team members found</div>';
      return;
    }

    container.innerHTML = `
      <div class="team-list">
        ${this.teamMembers.map(member => `
          <div class="list-card team-member-card">
            <div class="member-avatar">${this.getInitials(member.name)}</div>
            <div class="member-info">
              <div class="member-name">${member.name}</div>
              <div class="member-meta">${member.emp_code} • ${member.designation || 'Employee'}</div>
            </div>
            <div class="member-stats">
              <div class="stat-item">
                <span class="stat-val">${member.tasks_pending}</span>
                <span class="stat-lbl">Pending</span>
              </div>
              <div class="stat-item">
                <span class="stat-val">${member.kra_score}%</span>
                <span class="stat-lbl">KRA</span>
              </div>
              <div class="stat-item">
                <span class="stat-val">${member.attendance_percentage}%</span>
                <span class="stat-lbl">Attend</span>
              </div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  private getInitials(name: string): string {
    return name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '??';
  }
}
