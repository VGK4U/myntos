/**
 * Staff Service Center Dashboard Page
 * DC Protocol: DC_MOBILE_STAFF_SERVICE_001
 * EV Service ticket management
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface ServiceStats {
  total_tickets: number;
  open_tickets: number;
  in_progress: number;
  resolved_today: number;
  avg_resolution_time: string;
  pending_parts: number;
}

interface ServiceTicket {
  id: number;
  ticket_number: string;
  customer_name: string;
  vehicle_model: string;
  issue_type: string;
  priority: string;
  status: string;
  created_at: string;
  tat_remaining: string | null;
}

export class StaffServicePage {
  private container: HTMLElement;
  private stats: ServiceStats | null = null;
  private tickets: ServiceTicket[] = [];
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
      const [statsRes, ticketsRes] = await Promise.all([
        apiService.get<any>('/tickets/service/dashboard-stats'),
        apiService.get<any>('/tickets/service/queue?limit=10')
      ]);

      if (statsRes.success && statsRes.data) {
        this.stats = statsRes.data;
      }
      if (ticketsRes.success && ticketsRes.data) {
        this.tickets = ticketsRes.data.tickets || ticketsRes.data || [];
      }
    } catch (error) {
      console.error('[StaffService] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Service Center', showBack: true })}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'Service Center', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    content.innerHTML = `
      <div class="service-stats card">
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-value open">${this.stats?.open_tickets || 0}</span>
            <span class="stat-label">Open</span>
          </div>
          <div class="stat-item">
            <span class="stat-value progress">${this.stats?.in_progress || 0}</span>
            <span class="stat-label">In Progress</span>
          </div>
          <div class="stat-item">
            <span class="stat-value resolved">${this.stats?.resolved_today || 0}</span>
            <span class="stat-label">Resolved Today</span>
          </div>
        </div>
      </div>

      <div class="quick-actions">
        <button class="action-card card" id="raiseTicketBtn">
          <span class="action-icon">➕</span>
          <span>Raise Ticket</span>
        </button>
        <button class="action-card card" id="queueBtn">
          <span class="action-icon">📋</span>
          <span>Queue</span>
        </button>
      </div>

      <h4 class="section-title">My Active Tickets</h4>
      ${this.tickets.length > 0 ? `
        <div class="tickets-list">
          ${this.tickets.slice(0, 10).map(t => this.renderTicket(t)).join('')}
        </div>
      ` : `
        <div class="empty-state card">
          <div class="empty-icon">🔧</div>
          <p>No active service tickets</p>
        </div>
      `}

      ${this.stats?.pending_parts ? `
        <div class="notice-card card warning">
          <h4>⚠️ Parts Pending</h4>
          <p>${this.stats.pending_parts} tickets waiting for spare parts</p>
        </div>
      ` : ''}
    `;

    document.getElementById('raiseTicketBtn')?.addEventListener('click', () => {
      alert('Please use the web portal to raise new service tickets');
    });

    document.getElementById('queueBtn')?.addEventListener('click', () => {
      alert('Please use the web portal for full queue management');
    });
  }

  private renderTicket(ticket: ServiceTicket): string {
    const statusClass = ticket.status.toLowerCase().replace(' ', '-');
    const priorityClass = ticket.priority.toLowerCase();
    const date = new Date(ticket.created_at).toLocaleDateString('en', { day: 'numeric', month: 'short' });

    return `
      <div class="service-ticket-card card ${statusClass}">
        <div class="ticket-header">
          <span class="ticket-number">#${ticket.ticket_number}</span>
          <span class="priority-badge ${priorityClass}">${ticket.priority}</span>
        </div>
        <div class="ticket-info">
          <h4>${ticket.customer_name}</h4>
          <p class="vehicle-info">${ticket.vehicle_model}</p>
        </div>
        <div class="ticket-issue">
          <span class="issue-type">${ticket.issue_type}</span>
          <span class="status-badge ${statusClass}">${ticket.status}</span>
        </div>
        <div class="ticket-meta">
          <span>${date}</span>
          ${ticket.tat_remaining ? `<span class="tat">TAT: ${ticket.tat_remaining}</span>` : ''}
        </div>
      </div>
    `;
  }
}
