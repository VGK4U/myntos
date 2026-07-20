/**
 * Service Performance Page
 * DC Protocol: DC_MOBILE_SERVICE_PERF_001
 * View performance metrics and analytics
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface PerformanceStats {
  total_tickets: number;
  resolved_tickets: number;
  avg_resolution_time: number;
  avg_tat_hours: number;
  sla_compliance: number;
  customer_satisfaction: number;
  pending_tickets: number;
  overdue_tickets: number;
}

interface TechnicianPerformance {
  technician_name: string;
  emp_code: string;
  tickets_handled: number;
  resolved: number;
  avg_tat: number;
  satisfaction: number;
}

export class ServicePerformancePage {
  private container: HTMLElement;
  private stats: PerformanceStats | null = null;
  private technicians: TechnicianPerformance[] = [];
  private loading: boolean = true;
  private period: string = 'month';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadPerformance();
  }

  private async loadPerformance(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>(`/tickets/service/dashboard-stats?period=${this.period}`);
      if (response.success && response.data) {
        this.stats = response.data;
        this.technicians = response.data.technicians || [];
      }
    } catch (error) {
      console.error('[ServicePerformancePage] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Performance', showBack: true })}
        
        <div class="period-selector">
          <button class="period-btn ${this.period === 'week' ? 'active' : ''}" data-period="week">This Week</button>
          <button class="period-btn ${this.period === 'month' ? 'active' : ''}" data-period="month">This Month</button>
          <button class="period-btn ${this.period === 'quarter' ? 'active' : ''}" data-period="quarter">Quarter</button>
        </div>

        <div id="performanceContent">
          <div class="loading-state">Loading performance data...</div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachListeners();
  }

  private attachListeners(): void {
    this.container.querySelectorAll('.period-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.period = (btn as HTMLElement).dataset.period || 'month';
        this.container.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.loadPerformance();
      });
    });
  }

  private updateContent(): void {
    const content = document.getElementById('performanceContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading performance data...</div>';
      return;
    }

    content.innerHTML = `
      <div class="section-card">
        <h4>Overview</h4>
        <div class="stats-grid-2x2">
          <div class="stat-item">
            <span class="stat-value">${this.stats?.total_tickets || 0}</span>
            <span class="stat-label">Total Tickets</span>
          </div>
          <div class="stat-item success">
            <span class="stat-value">${this.stats?.resolved_tickets || 0}</span>
            <span class="stat-label">Resolved</span>
          </div>
          <div class="stat-item warning">
            <span class="stat-value">${this.stats?.pending_tickets || 0}</span>
            <span class="stat-label">Pending</span>
          </div>
          <div class="stat-item danger">
            <span class="stat-value">${this.stats?.overdue_tickets || 0}</span>
            <span class="stat-label">Overdue</span>
          </div>
        </div>
      </div>

      <div class="section-card">
        <h4>Key Metrics</h4>
        <div class="metrics-list">
          <div class="metric-row">
            <span class="metric-label">Avg Resolution Time</span>
            <span class="metric-value">${this.stats?.avg_resolution_time?.toFixed(1) || 0}h</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">Avg TAT</span>
            <span class="metric-value">${this.stats?.avg_tat_hours?.toFixed(1) || 0}h</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">SLA Compliance</span>
            <span class="metric-value ${this.getSlaClass()}">${this.stats?.sla_compliance?.toFixed(0) || 0}%</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">Customer Satisfaction</span>
            <span class="metric-value">${this.stats?.customer_satisfaction?.toFixed(1) || 0}/5</span>
          </div>
        </div>
      </div>

      ${this.technicians.length > 0 ? `
      <div class="section-card">
        <h4>Technician Performance</h4>
        <div class="technician-list">
          ${this.technicians.map(tech => this.renderTechnicianCard(tech)).join('')}
        </div>
      </div>
      ` : ''}
    `;
  }

  private getSlaClass(): string {
    const sla = this.stats?.sla_compliance || 0;
    if (sla >= 90) return 'text-success';
    if (sla >= 70) return 'text-warning';
    return 'text-danger';
  }

  private renderTechnicianCard(tech: TechnicianPerformance): string {
    return `
      <div class="technician-row">
        <div class="tech-info">
          <span class="tech-name">${tech.technician_name}</span>
          <span class="tech-code">${tech.emp_code}</span>
        </div>
        <div class="tech-stats">
          <span class="tech-stat">${tech.tickets_handled} handled</span>
          <span class="tech-stat">${tech.avg_tat?.toFixed(1) || 0}h TAT</span>
          <span class="tech-stat">${tech.satisfaction?.toFixed(1) || 0}/5</span>
        </div>
      </div>
    `;
  }
}
