/**
 * Partner Service Page
 * DC Protocol: DC_MOBILE_PARTNER_SERVICE_001
 * View and manage service tickets for partner
 */

import { apiService } from '../../services/api.service';
import { authService } from '../../services/auth.service';
import { PageHeader } from '../../components/PageHeader';
import { routerService } from '../../services/router.service';

interface ServiceTicket {
  id: number;
  ticket_number: string;
  customer_name: string;
  customer_mobile: string;
  vehicle_number: string;
  vehicle_model?: string;
  issue_type: string;
  issue_description?: string;
  status: string;
  priority: string;
  created_at: string;
  updated_at?: string;
}

export class PartnerServicePage {
  private container: HTMLElement;
  private tickets: ServiceTicket[] = [];
  private loading: boolean = true;
  private filter: 'all' | 'open' | 'in_progress' | 'completed' = 'all';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadTickets();
  }

  private async loadTickets(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>('/partner/service-tickets');
      if (response.success && response.data) {
        this.tickets = Array.isArray(response.data) ? response.data : (response.data.tickets || []);
      }
    } catch (error) {
      console.error('[PartnerServicePage] Failed to load tickets:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container partner-service">
        ${PageHeader.render({ title: 'Service Tickets', showBack: false })}
        
        <div class="page-actions">
          <button id="raiseTicketBtn" class="btn btn-primary">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="16"/>
              <line x1="8" y1="12" x2="16" y2="12"/>
            </svg>
            Raise Ticket
          </button>
        </div>

        <div class="filter-tabs">
          <button class="filter-tab ${this.filter === 'all' ? 'active' : ''}" data-filter="all">All</button>
          <button class="filter-tab ${this.filter === 'open' ? 'active' : ''}" data-filter="open">Open</button>
          <button class="filter-tab ${this.filter === 'in_progress' ? 'active' : ''}" data-filter="in_progress">In Progress</button>
          <button class="filter-tab ${this.filter === 'completed' ? 'active' : ''}" data-filter="completed">Completed</button>
        </div>

        <div id="ticketsContent" class="tickets-list">
          <div class="loading-state">Loading tickets...</div>
        </div>
      </div>
    `;

    this.attachListeners();
  }

  private attachListeners(): void {
    document.getElementById('raiseTicketBtn')?.addEventListener('click', () => {
      routerService.navigate('partner-raise-ticket');
    });

    this.container.querySelectorAll('.filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.filter = tab.getAttribute('data-filter') as any;
        this.render();
        this.updateContent();
      });
    });
  }

  private updateContent(): void {
    const content = document.getElementById('ticketsContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading tickets...</div>';
      return;
    }

    const filtered = this.getFilteredTickets();

    if (filtered.length === 0) {
      content.innerHTML = `
        <div class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          <p>No ${this.filter === 'all' ? '' : this.filter.replace('_', ' ')} tickets found</p>
          <button id="raiseFirstTicket" class="btn btn-outline">Raise your first ticket</button>
        </div>
      `;
      document.getElementById('raiseFirstTicket')?.addEventListener('click', () => {
        routerService.navigate('partner-raise-ticket');
      });
      return;
    }

    content.innerHTML = filtered.map(ticket => this.renderTicketCard(ticket)).join('');

    content.querySelectorAll('.ticket-card').forEach(card => {
      card.addEventListener('click', () => {
        const ticketId = card.getAttribute('data-id');
        if (ticketId) {
          alert(`Ticket details coming soon for #${ticketId}`);
        }
      });
    });
  }

  private getFilteredTickets(): ServiceTicket[] {
    if (this.filter === 'all') return this.tickets;
    return this.tickets.filter(t => {
      if (this.filter === 'completed') return t.status === 'completed' || t.status === 'closed';
      if (this.filter === 'in_progress') return t.status === 'in_progress' || t.status === 'assigned';
      if (this.filter === 'open') return t.status === 'open' || t.status === 'pending';
      return true;
    });
  }

  private renderTicketCard(ticket: ServiceTicket): string {
    const statusClass = this.getStatusClass(ticket.status);
    const priorityClass = this.getPriorityClass(ticket.priority);
    const date = new Date(ticket.created_at);
    const dateStr = date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });

    return `
      <div class="ticket-card card" data-id="${ticket.id}">
        <div class="ticket-header">
          <span class="ticket-number">#${ticket.ticket_number}</span>
          <span class="ticket-status ${statusClass}">${this.formatStatus(ticket.status)}</span>
        </div>
        <div class="ticket-info">
          <h4 class="customer-name">${ticket.customer_name}</h4>
          <p class="vehicle-info">${ticket.vehicle_number} ${ticket.vehicle_model ? `• ${ticket.vehicle_model}` : ''}</p>
          <p class="issue-type">${ticket.issue_type}</p>
        </div>
        <div class="ticket-footer">
          <span class="ticket-priority ${priorityClass}">${ticket.priority}</span>
          <span class="ticket-date">${dateStr}</span>
        </div>
      </div>
    `;
  }

  private getStatusClass(status: string): string {
    const map: Record<string, string> = {
      open: 'status-open',
      pending: 'status-open',
      in_progress: 'status-progress',
      assigned: 'status-progress',
      completed: 'status-completed',
      closed: 'status-completed'
    };
    return map[status] || 'status-open';
  }

  private getPriorityClass(priority: string): string {
    const map: Record<string, string> = {
      high: 'priority-high',
      urgent: 'priority-high',
      medium: 'priority-medium',
      normal: 'priority-medium',
      low: 'priority-low'
    };
    return map[priority?.toLowerCase()] || 'priority-medium';
  }

  private formatStatus(status: string): string {
    return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }
}
