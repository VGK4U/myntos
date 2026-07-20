/**
 * Staff Support Tickets Page
 * DC Protocol: DC_MOBILE_STAFF_TICKETS_001
 * View and submit support tickets
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface Ticket {
  id: number;
  ticket_number: string;
  subject: string;
  category: string;
  priority: string;
  status: string;
  created_at: string;
  updated_at: string;
  last_reply: string | null;
}

export class StaffTicketsPage {
  private container: HTMLElement;
  private tickets: Ticket[] = [];
  private loading: boolean = true;
  private showForm: boolean = false;

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
      const response = await apiService.get<any>('/tickets/my-tickets');
      if (response.success && response.data) {
        this.tickets = response.data.tickets || response.data || [];
      }
    } catch (error) {
      console.error('[StaffTickets] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Support Tickets', showBack: true })}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'Support Tickets', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const open = this.tickets.filter(t => t.status === 'open' || t.status === 'pending').length;
    const closed = this.tickets.filter(t => t.status === 'closed' || t.status === 'resolved').length;

    content.innerHTML = `
      <button class="btn btn-primary submit-btn" id="newTicketBtn">
        + New Support Ticket
      </button>

      ${this.showForm ? this.renderForm() : ''}

      <div class="tickets-summary card">
        <div class="summary-grid">
          <div class="summary-item">
            <span class="summary-value">${this.tickets.length}</span>
            <span class="summary-label">Total</span>
          </div>
          <div class="summary-item">
            <span class="summary-value open">${open}</span>
            <span class="summary-label">Open</span>
          </div>
          <div class="summary-item">
            <span class="summary-value closed">${closed}</span>
            <span class="summary-label">Resolved</span>
          </div>
        </div>
      </div>

      <h4 class="section-title">My Tickets</h4>
      ${this.tickets.length > 0 ? `
        <div class="tickets-list">
          ${this.tickets.map(t => this.renderTicket(t)).join('')}
        </div>
      ` : `
        <div class="empty-state card">
          <div class="empty-icon">🎫</div>
          <p>No support tickets</p>
        </div>
      `}
    `;

    this.attachListeners();
  }

  private renderForm(): string {
    return `
      <div class="ticket-form card">
        <h4>Submit New Ticket</h4>
        <div class="form-group">
          <label>Category</label>
          <select id="ticketCategory" class="form-input">
            <option value="">Select Category</option>
            <option value="technical">Technical Issue</option>
            <option value="account">Account Issue</option>
            <option value="hr">HR Query</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div class="form-group">
          <label>Priority</label>
          <select id="ticketPriority" class="form-input">
            <option value="low">Low</option>
            <option value="medium" selected>Medium</option>
            <option value="high">High</option>
          </select>
        </div>
        <div class="form-group">
          <label>Subject</label>
          <input type="text" id="ticketSubject" class="form-input" placeholder="Brief subject">
        </div>
        <div class="form-group">
          <label>Description</label>
          <textarea id="ticketDescription" class="form-input" rows="4" placeholder="Describe your issue..."></textarea>
        </div>
        <div class="form-actions">
          <button class="btn btn-secondary" id="cancelFormBtn">Cancel</button>
          <button class="btn btn-primary" id="submitTicketBtn">Submit</button>
        </div>
      </div>
    `;
  }

  private renderTicket(ticket: Ticket): string {
    const statusClass = ticket.status.toLowerCase();
    const priorityClass = ticket.priority.toLowerCase();
    const date = new Date(ticket.created_at).toLocaleDateString('en', { day: 'numeric', month: 'short' });

    return `
      <div class="ticket-card card ${statusClass}">
        <div class="ticket-header">
          <span class="ticket-number">#${ticket.ticket_number}</span>
          <span class="status-badge ${statusClass}">${ticket.status}</span>
        </div>
        <h4 class="ticket-subject">${ticket.subject}</h4>
        <div class="ticket-meta">
          <span class="ticket-category">${ticket.category}</span>
          <span class="priority-badge ${priorityClass}">${ticket.priority}</span>
          <span class="ticket-date">${date}</span>
        </div>
      </div>
    `;
  }

  private attachListeners(): void {
    document.getElementById('newTicketBtn')?.addEventListener('click', () => {
      this.showForm = !this.showForm;
      this.updateContent();
    });

    document.getElementById('cancelFormBtn')?.addEventListener('click', () => {
      this.showForm = false;
      this.updateContent();
    });

    document.getElementById('submitTicketBtn')?.addEventListener('click', () => this.submitTicket());
  }

  private async submitTicket(): Promise<void> {
    const category = (document.getElementById('ticketCategory') as HTMLSelectElement)?.value;
    const priority = (document.getElementById('ticketPriority') as HTMLSelectElement)?.value;
    const subject = (document.getElementById('ticketSubject') as HTMLInputElement)?.value?.trim();
    const description = (document.getElementById('ticketDescription') as HTMLTextAreaElement)?.value?.trim();

    if (!category || !subject || !description) {
      alert('Please fill in all required fields');
      return;
    }

    try {
      const response = await apiService.post<any>('/tickets/create', {
        category, priority, subject, description
      });

      if (response.success) {
        alert('Ticket submitted successfully!');
        this.showForm = false;
        await this.loadTickets();
      } else {
        alert(response.error || 'Failed to submit ticket');
      }
    } catch (error) {
      console.error('[StaffTickets] Submit error:', error);
      alert('Failed to submit ticket');
    }
  }
}
