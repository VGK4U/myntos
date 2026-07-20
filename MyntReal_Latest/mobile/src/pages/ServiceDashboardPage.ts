/**
 * Service Dashboard Page - Enhanced Version
 * DC Protocol: DC_MOBILE_SERVICE_DASHBOARD_001
 * Overview of service tickets, stats, charts, and quick actions - full web parity
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';

interface DashboardStats {
  total_tickets: number;
  open_tickets: number;
  in_progress: number;
  pending_spares: number;
  completed_today: number;
  avg_tat_hours: number;
  total_revenue: number;
  pending_billing: number;
  sla_breached?: number;
  new_today?: number;
  resolved_today?: number;
  first_response_avg?: number;
}

interface RecentTicket {
  id: number;
  ticket_number: string;
  customer_name: string;
  vehicle_number: string;
  issue_type: string;
  issue_category?: string;
  ticket_type?: string;
  status: string;
  sub_status?: string;
  priority: string;
  created_at: string;
  assigned_to?: string;
  sla_status?: string;
}

interface TechnicianStats {
  id: number;
  name: string;
  emp_code: string;
  tickets_assigned: number;
  tickets_resolved: number;
  avg_tat: number;
}

export class ServiceDashboardPage {
  private container: HTMLElement;
  private stats: DashboardStats | null = null;
  private recentTickets: RecentTicket[] = [];
  private technicianStats: TechnicianStats[] = [];
  private loading: boolean = true;
  private activeTab: string = 'overview';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadDashboard();
  }

  private async loadDashboard(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const [statsRes, queueRes] = await Promise.all([
        apiService.get<any>('/tickets/service/dashboard-stats'),
        apiService.get<any>('/tickets/service/queue?limit=8')
      ]);

      if (statsRes.success && statsRes.data) {
        this.stats = statsRes.data;
      }
      if (queueRes.success && queueRes.data) {
        this.recentTickets = Array.isArray(queueRes.data) ? queueRes.data : (queueRes.data.tickets || []);
      }
    } catch (error) {
      console.error('[ServiceDashboardPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container service-dashboard-page">
        ${PageHeader.render({ title: 'Service Center', showBack: true })}
        
        <!-- Quick Actions Bar -->
        <div class="quick-actions-grid">
          <button class="action-card primary" id="raiseTicket">
            <span class="action-icon">+</span>
            <span class="action-text">New Ticket</span>
          </button>
          <button class="action-card" id="viewQueue">
            <span class="action-icon">📋</span>
            <span class="action-text">Queue</span>
          </button>
          <button class="action-card" id="viewProcurement">
            <span class="action-icon">🛒</span>
            <span class="action-text">Spares</span>
          </button>
          <button class="action-card" id="viewRevenue">
            <span class="action-icon">💰</span>
            <span class="action-text">Billing</span>
          </button>
        </div>

        <!-- Tab Navigation -->
        <div class="dashboard-tabs">
          <button class="dash-tab active" data-tab="overview">Overview</button>
          <button class="dash-tab" data-tab="performance">Performance</button>
          <button class="dash-tab" data-tab="tickets">Tickets</button>
        </div>

        <div id="dashboardContent">
          <div class="loading-state"><div class="spinner"></div>Loading dashboard...</div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachListeners();
  }

  private attachListeners(): void {
    document.getElementById('raiseTicket')?.addEventListener('click', () => {
      routerService.navigate('staff-tickets');
    });
    document.getElementById('viewQueue')?.addEventListener('click', () => {
      routerService.navigate('staff-service-queue');
    });
    document.getElementById('viewProcurement')?.addEventListener('click', () => {
      routerService.navigate('staff-service-procurement');
    });
    document.getElementById('viewRevenue')?.addEventListener('click', () => {
      routerService.navigate('staff-service-revenue');
    });

    this.container.querySelectorAll('.dash-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.activeTab = (tab as HTMLElement).dataset.tab || 'overview';
        this.container.querySelectorAll('.dash-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.updateContent();
      });
    });
  }

  private updateContent(): void {
    const content = document.getElementById('dashboardContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state"><div class="spinner"></div>Loading dashboard...</div>';
      return;
    }

    switch (this.activeTab) {
      case 'overview':
        content.innerHTML = this.renderOverviewTab();
        break;
      case 'performance':
        content.innerHTML = this.renderPerformanceTab();
        break;
      case 'tickets':
        content.innerHTML = this.renderTicketsTab();
        break;
    }

    this.attachContentListeners();
  }

  private renderOverviewTab(): string {
    return `
      <!-- Stats Grid -->
      <div class="stats-grid-2x2">
        <div class="stat-box open">
          <div class="stat-header">
            <span class="stat-icon-box">📥</span>
            <span class="stat-number">${this.stats?.open_tickets || 0}</span>
          </div>
          <span class="stat-title">Open Tickets</span>
        </div>
        <div class="stat-box progress">
          <div class="stat-header">
            <span class="stat-icon-box">🔧</span>
            <span class="stat-number">${this.stats?.in_progress || 0}</span>
          </div>
          <span class="stat-title">In Progress</span>
        </div>
        <div class="stat-box spares">
          <div class="stat-header">
            <span class="stat-icon-box">⏳</span>
            <span class="stat-number">${this.stats?.pending_spares || 0}</span>
          </div>
          <span class="stat-title">Pending Spares</span>
        </div>
        <div class="stat-box done">
          <div class="stat-header">
            <span class="stat-icon-box">✅</span>
            <span class="stat-number">${this.stats?.completed_today || 0}</span>
          </div>
          <span class="stat-title">Completed Today</span>
        </div>
      </div>

      ${this.stats?.sla_breached && this.stats.sla_breached > 0 ? `
      <div class="alert-card danger">
        <span class="alert-icon">⚠️</span>
        <div class="alert-content">
          <span class="alert-title">${this.stats.sla_breached} SLA Breached</span>
          <span class="alert-desc">Tickets requiring immediate attention</span>
        </div>
        <button class="alert-action" id="viewBreached">View</button>
      </div>
      ` : ''}

      <!-- Key Metrics -->
      <div class="section-card">
        <div class="section-header">
          <h3>Key Metrics</h3>
        </div>
        <div class="metrics-grid">
          <div class="metric-item">
            <span class="metric-value">${this.stats?.avg_tat_hours?.toFixed(1) || '0'}h</span>
            <span class="metric-label">Avg TAT</span>
          </div>
          <div class="metric-item">
            <span class="metric-value">${this.formatCurrency(this.stats?.total_revenue || 0)}</span>
            <span class="metric-label">Revenue</span>
          </div>
          <div class="metric-item">
            <span class="metric-value">${this.stats?.pending_billing || 0}</span>
            <span class="metric-label">Pending Bills</span>
          </div>
          <div class="metric-item">
            <span class="metric-value">${this.stats?.total_tickets || 0}</span>
            <span class="metric-label">Total Tickets</span>
          </div>
        </div>
      </div>

      <!-- Quick Stats Chart Placeholder -->
      <div class="section-card">
        <div class="section-header">
          <h3>Today's Activity</h3>
        </div>
        <div class="activity-summary">
          <div class="activity-item">
            <span class="activity-label">New Today</span>
            <div class="activity-bar">
              <div class="activity-fill new" style="width: ${Math.min((this.stats?.new_today || 0) * 10, 100)}%"></div>
            </div>
            <span class="activity-value">${this.stats?.new_today || 0}</span>
          </div>
          <div class="activity-item">
            <span class="activity-label">Resolved Today</span>
            <div class="activity-bar">
              <div class="activity-fill resolved" style="width: ${Math.min((this.stats?.resolved_today || 0) * 10, 100)}%"></div>
            </div>
            <span class="activity-value">${this.stats?.resolved_today || 0}</span>
          </div>
        </div>
      </div>
    `;
  }

  private renderPerformanceTab(): string {
    return `
      <!-- Performance Overview -->
      <div class="section-card">
        <div class="section-header">
          <h3>Performance Overview</h3>
        </div>
        <div class="perf-stats-grid">
          <div class="perf-stat">
            <div class="perf-circle">${this.stats?.avg_tat_hours?.toFixed(0) || 0}h</div>
            <span class="perf-label">Avg Resolution</span>
          </div>
          <div class="perf-stat">
            <div class="perf-circle">${this.calculateSlaCompliance()}%</div>
            <span class="perf-label">SLA Compliance</span>
          </div>
          <div class="perf-stat">
            <div class="perf-circle">${this.stats?.first_response_avg?.toFixed(0) || 15}m</div>
            <span class="perf-label">First Response</span>
          </div>
        </div>
      </div>

      <!-- Status Breakdown -->
      <div class="section-card">
        <div class="section-header">
          <h3>Ticket Status</h3>
        </div>
        <div class="status-breakdown">
          ${this.renderStatusBar('Open', this.stats?.open_tickets || 0, 'open')}
          ${this.renderStatusBar('In Progress', this.stats?.in_progress || 0, 'progress')}
          ${this.renderStatusBar('Pending Spares', this.stats?.pending_spares || 0, 'spares')}
          ${this.renderStatusBar('Completed', this.stats?.completed_today || 0, 'completed')}
        </div>
      </div>

      <!-- View Full Performance -->
      <button class="btn btn-block btn-outline" id="viewFullPerformance">
        View Full Performance Report
      </button>
    `;
  }

  private renderStatusBar(label: string, count: number, type: string): string {
    const total = (this.stats?.total_tickets || 1);
    const pct = Math.round((count / total) * 100);
    return `
      <div class="status-bar-item">
        <div class="status-bar-header">
          <span class="status-bar-label">${label}</span>
          <span class="status-bar-count">${count}</span>
        </div>
        <div class="status-bar-track">
          <div class="status-bar-fill ${type}" style="width: ${pct}%"></div>
        </div>
      </div>
    `;
  }

  private calculateSlaCompliance(): number {
    const total = this.stats?.total_tickets || 0;
    const breached = this.stats?.sla_breached || 0;
    if (total === 0) return 100;
    return Math.round(((total - breached) / total) * 100);
  }

  private renderTicketsTab(): string {
    return `
      <div class="section-card">
        <div class="section-header">
          <h3>Recent Tickets</h3>
          <button class="link-btn" id="viewAllTickets">View All</button>
        </div>
        <div class="tickets-list">
          ${this.recentTickets.length === 0 ? 
            '<div class="empty-mini">No recent tickets</div>' :
            this.recentTickets.map(t => this.renderTicketCard(t)).join('')
          }
        </div>
      </div>
    `;
  }

  private renderTicketCard(ticket: RecentTicket): string {
    const statusClass = this.getStatusClass(ticket.sub_status || ticket.status);
    const priorityClass = ticket.priority?.toLowerCase() || 'medium';
    const isSlaBreached = ticket.sla_status?.toLowerCase().includes('breach');
    
    return `
      <div class="ticket-row ${isSlaBreached ? 'sla-alert' : ''}" data-id="${ticket.id}">
        <div class="ticket-row-main">
          <div class="ticket-row-left">
            <span class="ticket-id">${ticket.ticket_number || `#${ticket.id}`}</span>
            <span class="ticket-customer">${ticket.customer_name || 'Unknown'}</span>
          </div>
          <div class="ticket-row-right">
            <span class="priority-dot ${priorityClass}"></span>
            <span class="status-badge mini ${statusClass}">${ticket.sub_status || ticket.status || 'Open'}</span>
          </div>
        </div>
        <div class="ticket-row-secondary">
          <span class="vehicle-tag">${ticket.vehicle_number || 'N/A'}</span>
          <span class="ticket-type-tag ${ticket.ticket_type || 'general'}">${(ticket.ticket_type || 'general').charAt(0).toUpperCase() + (ticket.ticket_type || 'general').slice(1)}</span>
          <span class="issue-tag">${ticket.issue_category || ticket.issue_type || 'General'}</span>
          ${isSlaBreached ? '<span class="sla-tag">SLA!</span>' : ''}
        </div>
      </div>
    `;
  }

  private getStatusClass(status: string | undefined): string {
    const s = (status || 'open').toLowerCase().replace(/\s+/g, '-');
    const statusMap: Record<string, string> = {
      'new': 'new', 'open': 'new', 'acknowledged': 'acknowledged',
      'in-progress': 'in-progress', 'completed': 'completed', 'closed': 'closed'
    };
    return statusMap[s] || 'open';
  }

  private attachContentListeners(): void {
    document.getElementById('viewAllTickets')?.addEventListener('click', () => {
      routerService.navigate('staff-service-queue');
    });

    document.getElementById('viewBreached')?.addEventListener('click', () => {
      routerService.navigate('staff-service-queue');
    });

    document.getElementById('viewFullPerformance')?.addEventListener('click', () => {
      routerService.navigate('staff-service-performance');
    });

    this.container.querySelectorAll('.ticket-row').forEach(row => {
      row.addEventListener('click', () => {
        const id = (row as HTMLElement).dataset.id;
        if (id) {
          routerService.navigate('staff-service-queue', { ticketId: id });
        }
      });
    });
  }

  private formatCurrency(amount: number): string {
    if (amount >= 100000) {
      return `₹${(amount / 100000).toFixed(1)}L`;
    } else if (amount >= 1000) {
      return `₹${(amount / 1000).toFixed(1)}K`;
    }
    return `₹${amount}`;
  }
}
