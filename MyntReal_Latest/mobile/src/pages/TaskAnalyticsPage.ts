/**
 * Task Analytics Page - Personal Task Dashboard
 * DC Protocol: DC_MOBILE_TASK_ANALYTICS_001
 * Summary of personal task performance
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface TaskSummary {
  total: number;
  pending: number;
  in_progress: number;
  completed: number;
  overdue: number;
  completion_rate: number;
  avg_completion_time: number;
  on_time_rate: number;
}

interface TaskByCategory {
  category: string;
  count: number;
  completed: number;
}

interface TaskByPriority {
  priority: string;
  count: number;
  completed: number;
}

export class TaskAnalyticsPage {
  private container: HTMLElement;
  private loading: boolean = true;
  private summary: TaskSummary | null = null;
  private byCategory: TaskByCategory[] = [];
  private byPriority: TaskByPriority[] = [];

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadAnalytics();
  }

  private async loadAnalytics(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>('/staff/tasks/analytics/my-summary');
      console.log('[TaskAnalyticsPage] API response:', response);

      // DC Protocol: Handle multiple response formats
      const data = response.data as any;
      if (response.success !== false && data) {
        this.summary = data.summary || data;
        this.byCategory = data.by_category || [];
        this.byPriority = data.by_priority || [];
        console.log('[TaskAnalyticsPage] Loaded analytics');
      } else {
        this.summary = null;
        this.byCategory = [];
        this.byPriority = [];
      }
    } catch (error) {
      console.error('[TaskAnalyticsPage] Failed to load:', error);
      this.summary = null;
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Task Analytics', showBack: true })}
        
        <div id="analyticsContent">
          <div class="loading-state">Loading analytics...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'Task Analytics', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('analyticsContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading analytics...</div>';
      return;
    }

    if (!this.summary) {
      content.innerHTML = '<div class="empty-state">No analytics data available</div>';
      return;
    }

    const s = this.summary;

    content.innerHTML = `
      <div class="analytics-overview">
        <div class="stats-grid">
          <div class="stat-card primary">
            <span class="stat-value">${s.total}</span>
            <span class="stat-label">Total Tasks</span>
          </div>
          <div class="stat-card success">
            <span class="stat-value">${s.completed}</span>
            <span class="stat-label">Completed</span>
          </div>
          <div class="stat-card warning">
            <span class="stat-value">${s.in_progress}</span>
            <span class="stat-label">In Progress</span>
          </div>
          <div class="stat-card danger">
            <span class="stat-value">${s.overdue}</span>
            <span class="stat-label">Overdue</span>
          </div>
        </div>

        <div class="performance-section card">
          <h4>Performance Metrics</h4>
          
          <div class="metric-row">
            <span class="metric-label">Completion Rate</span>
            <div class="metric-bar-container">
              <div class="metric-bar" style="width: ${s.completion_rate || 0}%; background: ${this.getPercentColor(s.completion_rate)}"></div>
            </div>
            <span class="metric-value">${Math.round(s.completion_rate || 0)}%</span>
          </div>

          <div class="metric-row">
            <span class="metric-label">On-Time Rate</span>
            <div class="metric-bar-container">
              <div class="metric-bar" style="width: ${s.on_time_rate || 0}%; background: ${this.getPercentColor(s.on_time_rate)}"></div>
            </div>
            <span class="metric-value">${Math.round(s.on_time_rate || 0)}%</span>
          </div>

          ${s.avg_completion_time ? `
            <div class="metric-row">
              <span class="metric-label">Avg. Completion Time</span>
              <span class="metric-value">${this.formatDuration(s.avg_completion_time)}</span>
            </div>
          ` : ''}
        </div>

        ${this.byPriority.length > 0 ? `
          <div class="breakdown-section card">
            <h4>By Priority</h4>
            <div class="breakdown-list">
              ${this.byPriority.map(p => `
                <div class="breakdown-item">
                  <span class="priority-badge ${p.priority?.toLowerCase()}">${p.priority}</span>
                  <div class="breakdown-stats">
                    <span>${p.completed}/${p.count} completed</span>
                    <div class="mini-progress">
                      <div class="mini-fill" style="width: ${p.count > 0 ? (p.completed / p.count * 100) : 0}%"></div>
                    </div>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}

        ${this.byCategory.length > 0 ? `
          <div class="breakdown-section card">
            <h4>By Category</h4>
            <div class="breakdown-list">
              ${this.byCategory.map(c => `
                <div class="breakdown-item">
                  <span class="category-name">${this.formatCategory(c.category)}</span>
                  <div class="breakdown-stats">
                    <span>${c.completed}/${c.count} completed</span>
                    <div class="mini-progress">
                      <div class="mini-fill" style="width: ${c.count > 0 ? (c.completed / c.count * 100) : 0}%"></div>
                    </div>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}

        <div class="quick-actions card">
          <h4>Quick Actions</h4>
          <div class="action-buttons">
            <button class="btn btn-outline" onclick="window.routerService?.navigate('tasks')">
              View All Tasks
            </button>
            <button class="btn btn-outline" onclick="window.routerService?.navigate('tasks-assigned')">
              Tasks I Assigned
            </button>
            <button class="btn btn-outline" onclick="window.routerService?.navigate('tasks-received')">
              Tasks Assigned to Me
            </button>
          </div>
        </div>
      </div>
    `;
  }

  private getPercentColor(value: number): string {
    if (value >= 80) return '#10b981';
    if (value >= 60) return '#3b82f6';
    if (value >= 40) return '#f59e0b';
    return '#ef4444';
  }

  private formatDuration(hours: number): string {
    if (hours < 24) return `${Math.round(hours)}h`;
    const days = Math.floor(hours / 24);
    return `${days}d ${Math.round(hours % 24)}h`;
  }

  private formatCategory(category: string): string {
    if (!category) return 'Other';
    return category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }
}
