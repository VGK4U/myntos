/**
 * Staff Service Queue Page
 * DC Protocol: DC_MOBILE_SERVICE_QUEUE_001
 * View and manage service ticket queue
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface ServiceTicket {
  id: number;
  ticket_number: string;
  customer_name: string;
  customer_phone: string;
  vehicle_model: string;
  vehicle_reg: string;
  issue_type: string;
  issue_description: string;
  priority: string;
  status: string;
  assigned_to?: string;
  created_at: string;
  sla_deadline: string;
  is_sla_breached: boolean;
}

export class StaffServiceQueuePage {
  private container: HTMLElement;
  private tickets: ServiceTicket[] = [];
  private loading: boolean = true;
  private filterPriority: string = '';
  private filterStatus: string = '';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadTickets();
  }

  private async loadTickets(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      let endpoint = '/tickets/service/queue';
      const params: string[] = [];
      if (this.filterPriority) params.push(`priority=${this.filterPriority}`);
      if (this.filterStatus) params.push(`sub_status=${this.filterStatus}`);
      if (params.length) endpoint += '?' + params.join('&');

      const response = await apiService.get<any>(endpoint);
      console.log('[StaffServiceQueuePage] API response:', response);

      if (response.success && response.data) {
        this.tickets = response.data.tickets || response.data || [];
      }
    } catch (error) {
      console.error('[StaffServiceQueuePage] Failed to load:', error);
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Service Queue', showBack: true })}
        
        <div class="filter-row">
          <select id="priorityFilter" class="filter-select">
            <option value="">All Priority</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="normal">Normal</option>
            <option value="low">Low</option>
          </select>
          <select id="statusFilter" class="filter-select">
            <option value="">All Status</option>
            <option value="new">New</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="diagnosing">Diagnosing</option>
            <option value="awaiting_spares">Awaiting Spares</option>
            <option value="procurement_in_progress">Procurement In Progress</option>
            <option value="ready_for_work">Ready for Work</option>
            <option value="work_complete">Work Complete</option>
            <option value="closed">Closed</option>
          </select>
        </div>

        <div class="stats-row">
          <div class="stat-card mini danger">
            <span class="stat-value" id="criticalCount">0</span>
            <span class="stat-label">Critical</span>
          </div>
          <div class="stat-card mini warning">
            <span class="stat-value" id="breachedCount">0</span>
            <span class="stat-label">SLA Breached</span>
          </div>
          <div class="stat-card mini">
            <span class="stat-value" id="totalCount">0</span>
            <span class="stat-label">Total</span>
          </div>
        </div>

        <div class="list-container" id="ticketsList">
          <div class="loading-state">Loading tickets...</div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    document.getElementById('priorityFilter')?.addEventListener('change', (e) => {
      this.filterPriority = (e.target as HTMLSelectElement).value;
      this.loadTickets();
    });

    document.getElementById('statusFilter')?.addEventListener('change', (e) => {
      this.filterStatus = (e.target as HTMLSelectElement).value;
      this.loadTickets();
    });
  }

  private updateList(): void {
    const listContainer = document.getElementById('ticketsList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading tickets...</div>';
      return;
    }

    const criticalEl = document.getElementById('criticalCount');
    const breachedEl = document.getElementById('breachedCount');
    const totalEl = document.getElementById('totalCount');
    if (criticalEl) criticalEl.textContent = this.tickets.filter(t => t.priority === 'critical').length.toString();
    if (breachedEl) breachedEl.textContent = this.tickets.filter(t => t.is_sla_breached).length.toString();
    if (totalEl) totalEl.textContent = this.tickets.length.toString();

    if (this.tickets.length === 0) {
      listContainer.innerHTML = '<div class="empty-state">No tickets in queue</div>';
      return;
    }

    listContainer.innerHTML = this.tickets.map(ticket => `
      <div class="list-card service-ticket-card ${ticket.is_sla_breached ? 'sla-breached' : ''}">
        <div class="ticket-header">
          <div class="ticket-number">${ticket.ticket_number}</div>
          <span class="priority-badge ${ticket.priority}">${ticket.priority}</span>
        </div>

        <div class="customer-info">
          <div class="customer-name">${ticket.customer_name}</div>
          <div class="customer-phone">${ticket.customer_phone}</div>
        </div>

        <div class="vehicle-info">
          <span class="vehicle-model">${ticket.vehicle_model}</span>
          <span class="vehicle-reg">${ticket.vehicle_reg}</span>
        </div>

        <div class="issue-type-badge">${ticket.issue_type}</div>
        <div class="issue-desc">${ticket.issue_description?.substring(0, 80)}${ticket.issue_description?.length > 80 ? '...' : ''}</div>

        <div class="ticket-meta">
          <span class="status-badge ${ticket.status}">${ticket.status?.replace('_', ' ')}</span>
          ${ticket.assigned_to ? `<span class="assigned-to">Assigned: ${ticket.assigned_to}</span>` : '<span class="unassigned">Unassigned</span>'}
        </div>

        <div class="ticket-timing">
          <span class="created">Created: ${this.formatDate(ticket.created_at)}</span>
          <span class="sla ${ticket.is_sla_breached ? 'breached' : ''}">SLA: ${this.formatDate(ticket.sla_deadline)}</span>
        </div>
      </div>
    `).join('');
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
