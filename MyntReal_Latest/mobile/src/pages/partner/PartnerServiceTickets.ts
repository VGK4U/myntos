/**
 * Partner Service Tickets Page
 * DC Protocol: DC_MOBILE_PARTNER_SERVICE_001
 * View and raise service tickets for partners
 */

import { apiService } from '../../services/api.service';
import { authService } from '../../services/auth.service';
import { PageHeader } from '../../components/PageHeader';
import { MobileTable } from '../../components/MobileTable';
import { routerService } from '../../services/router.service';

interface ServiceTicket {
  id: number;
  ticket_number: string;
  subject: string;
  category: string;
  priority: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface CustomerSpare {
  id: number;
  ticket_number: string;
  spare_item_name: string;
  spare_item_code: string;
  quantity_required: number;
  status_label: string;
  customer_name: string;
  vehicle_model: string;
  requested_at: string;
  sub_ticket_number: string;
}

export class PartnerServiceTickets {
  private container: HTMLElement;
  private tickets: ServiceTicket[] = [];
  private customerSpares: CustomerSpare[] = [];
  private loading = true;
  private sparesLoading = false;
  private sparesLoaded = false;
  private statusFilter = '';
  private activeTab: 'tickets' | 'spares' = 'tickets';

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
      const params = new URLSearchParams();
      if (this.statusFilter) params.append('status', this.statusFilter);
      
      const response = await apiService.get<any>(`/tickets/my-tickets?${params}`);
      
      if (response.success && response.data) {
        this.tickets = (response.data.tickets || response.data || []).map((t: any) => ({
          id: t.id,
          ticket_number: t.ticket_number || `TKT-${t.id}`,
          subject: t.subject || t.title || '-',
          category: t.category || 'General',
          priority: t.priority || 'Normal',
          status: t.status || 'Open',
          created_at: t.created_at || '',
          updated_at: t.updated_at || ''
        }));
      }
    } catch (error) {
      console.error('[PartnerServiceTickets] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        ${MobileTable.getStyles()}
        .service-page { padding: 16px; background: #0d1b2a; min-height: 100vh; }
        .raise-ticket-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          width: 100%;
          padding: 16px;
          background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
          border: none;
          border-radius: 12px;
          color: white;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          margin-bottom: 16px;
        }
        .raise-ticket-btn:active { opacity: 0.9; }
        .stats-row {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 10px;
          margin-bottom: 16px;
        }
        .stat-card {
          background: rgba(22, 33, 62, 0.9);
          border-radius: 10px;
          padding: 14px;
          text-align: center;
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .stat-value { font-size: 24px; font-weight: 700; color: #10b981; }
        .stat-label { font-size: 11px; color: #8892b0; margin-top: 4px; }
        .stat-card.open .stat-value { color: #fbbf24; }
        .stat-card.closed .stat-value { color: #10b981; }
        .filter-section {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 10px;
          padding: 14px;
          margin-bottom: 16px;
        }
        .filter-section label { display: block; font-size: 11px; color: #8892b0; margin-bottom: 6px; }
        .filter-section select {
          width: 100%;
          padding: 10px;
          border-radius: 6px;
          border: 1px solid rgba(255, 255, 255, 0.1);
          background: rgba(13, 27, 42, 0.8);
          color: #e6f1ff;
          font-size: 13px;
        }
        .table-header {
          background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
          padding: 12px 14px;
          border-radius: 8px 8px 0 0;
        }
        .table-header h5 { margin: 0; color: white; font-size: 13px; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; }
        .badge-open { background: #fbbf24; color: #451a03; }
        .badge-in-progress { background: #3b82f6; color: white; }
        .badge-resolved { background: #10b981; color: white; }
        .badge-closed { background: #6b7280; color: white; }
        .badge-high { background: #ef4444; color: white; }
        .badge-normal { background: #3b82f6; color: white; }
        .badge-low { background: #6b7280; color: white; }
        .loading-state { text-align: center; padding: 40px; color: #8892b0; }
        .empty-state { text-align: center; padding: 40px; color: #8892b0; }
      </style>
      ${PageHeader.render({ title: 'Service Tickets', showBack: true })}
      <div class="service-page" id="pageContent">
        <div class="loading-state">Loading...</div>
      </div>
    `;
    PageHeader.attachListeners({ title: 'Service Tickets', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading tickets...</div>';
      return;
    }

    const tabBar = `
      <div style="display:flex;border-bottom:2px solid rgba(255,255,255,0.1);margin-bottom:14px">
        <button id="tabTickets" style="flex:1;padding:10px;background:none;border:none;border-bottom:3px solid ${this.activeTab==='tickets'?'#10b981':'transparent'};color:${this.activeTab==='tickets'?'#10b981':'#8892b0'};font-size:13px;font-weight:600;cursor:pointer;margin-bottom:-2px">My Tickets</button>
        <button id="tabSpares" style="flex:1;padding:10px;background:none;border:none;border-bottom:3px solid ${this.activeTab==='spares'?'#10b981':'transparent'};color:${this.activeTab==='spares'?'#10b981':'#8892b0'};font-size:13px;font-weight:600;cursor:pointer;margin-bottom:-2px">Customer Spares</button>
      </div>`;

    if (this.activeTab === 'tickets') {
      const openCount = this.tickets.filter(t => t.status.toLowerCase() === 'open').length;
      const inProgressCount = this.tickets.filter(t => t.status.toLowerCase() === 'in progress' || t.status.toLowerCase() === 'in-progress').length;
      const closedCount = this.tickets.filter(t => t.status.toLowerCase() === 'closed' || t.status.toLowerCase() === 'resolved').length;

      const table = new MobileTable({
        columns: [
          { key: 'ticket_number', label: 'Ticket #', render: (v) => `<span style="color: #64d2ff; font-weight: 600;">${v}</span>` },
          { key: 'subject', label: 'Subject' },
          { key: 'category', label: 'Category' },
          { key: 'priority', label: 'Priority', render: (v) => this.getPriorityBadge(v) },
          { key: 'status', label: 'Status', render: (v) => this.getStatusBadge(v) },
          { key: 'created_at', label: 'Created', render: (v) => this.formatDate(v) }
        ],
        data: this.tickets,
        emptyMessage: 'No tickets found. Raise a new ticket to get started.'
      });

      content.innerHTML = tabBar + `
        <button class="raise-ticket-btn" id="raiseTicketBtn">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>
          </svg>
          Raise New Ticket
        </button>

        <div class="stats-row">
          <div class="stat-card open"><div class="stat-value">${openCount}</div><div class="stat-label">Open</div></div>
          <div class="stat-card"><div class="stat-value" style="color:#3b82f6">${inProgressCount}</div><div class="stat-label">In Progress</div></div>
          <div class="stat-card closed"><div class="stat-value">${closedCount}</div><div class="stat-label">Closed</div></div>
        </div>

        <div class="filter-section">
          <label>Filter by Status</label>
          <select id="statusFilter">
            <option value="">All Tickets</option>
            <option value="open" ${this.statusFilter === 'open' ? 'selected' : ''}>Open</option>
            <option value="in-progress" ${this.statusFilter === 'in-progress' ? 'selected' : ''}>In Progress</option>
            <option value="resolved" ${this.statusFilter === 'resolved' ? 'selected' : ''}>Resolved</option>
            <option value="closed" ${this.statusFilter === 'closed' ? 'selected' : ''}>Closed</option>
          </select>
        </div>

        <div class="table-header"><h5>My Tickets</h5></div>
        ${table.render()}
      `;
    } else {
      if (this.sparesLoading) {
        content.innerHTML = tabBar + '<div class="loading-state">Loading customer spares...</div>';
      } else if (this.customerSpares.length === 0) {
        content.innerHTML = tabBar + '<div class="empty-state">No customer spare requests linked to your account.</div>';
      } else {
        const sparesTable = new MobileTable({
          columns: [
            { key: 'sub_ticket_number', label: 'Sub-Ticket', render: (v) => `<span style="color:#64d2ff;font-weight:600">${v||'—'}</span>` },
            { key: 'spare_item_name', label: 'Item' },
            { key: 'spare_item_code', label: 'Code' },
            { key: 'quantity_required', label: 'Qty' },
            { key: 'customer_name', label: 'Customer' },
            { key: 'vehicle_model', label: 'Vehicle' },
            { key: 'status_label', label: 'Status', render: (v) => `<span style="font-size:10px;padding:2px 6px;border-radius:8px;background:rgba(16,185,129,0.15);color:#10b981">${v||'—'}</span>` },
            { key: 'requested_at', label: 'Date', render: (v) => this.formatDate(v) }
          ],
          data: this.customerSpares,
          emptyMessage: 'No customer spare requests found.'
        });
        content.innerHTML = tabBar + `
          <div class="table-header"><h5>Customer Spare Requests</h5></div>
          ${sparesTable.render()}`;
      }
    }

    this.attachListeners();
  }

  private async loadCustomerSpares(): Promise<void> {
    this.sparesLoading = true;
    this.updateContent();
    try {
      const response = await apiService.get<{ data: CustomerSpare[] }>('/partner/customer-spares?limit=50');
      if (response.success && response.data) {
        this.customerSpares = response.data.data || [];
      }
    } catch (error) {
      console.error('[PartnerServiceTickets] Customer spares load failed:', error);
    }
    this.sparesLoading = false;
    this.sparesLoaded = true;
    this.updateContent();
  }

  private attachListeners(): void {
    document.getElementById('raiseTicketBtn')?.addEventListener('click', () => {
      routerService.navigate('partner-raise-ticket');
    });

    document.getElementById('statusFilter')?.addEventListener('change', (e) => {
      this.statusFilter = (e.target as HTMLSelectElement).value;
      this.loadTickets();
    });

    document.getElementById('tabTickets')?.addEventListener('click', () => { this.activeTab = 'tickets'; this.updateContent(); });
    document.getElementById('tabSpares')?.addEventListener('click', () => {
      this.activeTab = 'spares';
      if (!this.sparesLoaded && !this.sparesLoading) this.loadCustomerSpares();
      else this.updateContent();
    });
  }

  private getStatusBadge(status: string): string {
    const s = status.toLowerCase();
    if (s === 'open') return '<span class="badge badge-open">Open</span>';
    if (s === 'in progress' || s === 'in-progress') return '<span class="badge badge-in-progress">In Progress</span>';
    if (s === 'resolved') return '<span class="badge badge-resolved">Resolved</span>';
    if (s === 'closed') return '<span class="badge badge-closed">Closed</span>';
    return `<span class="badge">${status}</span>`;
  }

  private getPriorityBadge(priority: string): string {
    const p = priority.toLowerCase();
    if (p === 'high' || p === 'urgent') return '<span class="badge badge-high">High</span>';
    if (p === 'normal' || p === 'medium') return '<span class="badge badge-normal">Normal</span>';
    if (p === 'low') return '<span class="badge badge-low">Low</span>';
    return `<span class="badge">${priority}</span>`;
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return '-';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
      return dateStr;
    }
  }
}
