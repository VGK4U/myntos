/**
 * Service Queue Page - Enhanced Version
 * DC Protocol: DC_MOBILE_SERVICE_QUEUE_001
 * Full parity with web: View and manage service tickets queue with all actions
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';

interface ServiceTicket {
  id: number;
  ticket_number: string;
  customer_name: string;
  customer_mobile: string;
  vehicle_number: string;
  vehicle_model?: string;
  issue_category: string;
  issue_description: string;
  priority: string;
  status: string;
  sub_status?: string;
  created_at: string;
  assigned_to?: string;
  service_technician_id?: number;
  service_technician_name?: string;
  partner_id?: number;
  partner_name?: string;
  diagnosis_notes?: string;
  resolution_summary?: string;
  tat_due_at?: string;
  sla_status?: string;
  ticket_type?: string;
  labor_charges?: number;
  spares_total?: number;
  total_amount?: number;
}

interface Partner {
  id: number;
  partner_name: string;
  category: string;
}

interface Technician {
  id: number;
  full_name: string;
  emp_code: string;
}

interface QueueStats {
  new: number;
  acknowledged: number;
  in_progress: number;
  pending_spares: number;
  completed: number;
  sla_breached: number;
}

export class ServiceQueuePage {
  private container: HTMLElement;
  private tickets: ServiceTicket[] = [];
  private filteredTickets: ServiceTicket[] = [];
  private partners: Partner[] = [];
  private technicians: Technician[] = [];
  private loading: boolean = true;
  private filterStatus: string = 'all';
  private filterPriority: string = 'all';
  private filterPartner: string = 'all';
  private filterTicketType: string = 'all';
  private searchQuery: string = '';
  private selectedTicket: ServiceTicket | null = null;
  private expandedTicketId: number | null = null;
  private stats: QueueStats = { new: 0, acknowledged: 0, in_progress: 0, pending_spares: 0, completed: 0, sla_breached: 0 };
  private pendingTimers: ReturnType<typeof setTimeout>[] = [];

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadData();
  }

  private async loadData(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      const [queueRes, partnersRes] = await Promise.all([
        apiService.get<any>('/tickets/service/queue'),
        apiService.get<any>('/tickets/partners').catch(() => ({ success: true, data: [] }))
      ]);

      if (queueRes.success && queueRes.data) {
        this.tickets = Array.isArray(queueRes.data) ? queueRes.data : (queueRes.data.tickets || []);
        this.calculateStats();
      }

      if (partnersRes.success && partnersRes.data) {
        this.partners = partnersRes.data || [];
      }
    } catch (error) {
      console.error('[ServiceQueuePage] Failed to load:', error);
    }

    this.loading = false;
    this.applyFilters();
    this.renderStats();
  }

  private calculateStats(): void {
    this.stats = {
      new: this.tickets.filter(t => (t.sub_status || t.status)?.toLowerCase() === 'new' || t.status?.toLowerCase() === 'open').length,
      acknowledged: this.tickets.filter(t => (t.sub_status || t.status)?.toLowerCase() === 'acknowledged').length,
      in_progress: this.tickets.filter(t => (t.sub_status || t.status)?.toLowerCase().includes('progress')).length,
      pending_spares: this.tickets.filter(t => (t.sub_status || t.status)?.toLowerCase().includes('spares') || (t.sub_status || t.status)?.toLowerCase().includes('awaiting')).length,
      completed: this.tickets.filter(t => (t.sub_status || t.status)?.toLowerCase() === 'completed' || (t.sub_status || t.status)?.toLowerCase() === 'work_complete').length,
      sla_breached: this.tickets.filter(t => t.sla_status?.toLowerCase().includes('breach')).length
    };
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container service-queue-page">
        ${PageHeader.render({ title: 'Service Queue', showBack: true })}
        
        <!-- Stats Grid -->
        <div class="stats-grid-compact" id="statsGrid">
          ${this.renderStatsCards()}
        </div>

        <!-- Search & Filters -->
        <div class="search-filter-section">
          <div class="search-bar">
            <input type="text" id="searchInput" class="search-input" placeholder="Search ticket#, customer, vehicle..." value="${this.searchQuery}">
          </div>
          
          <div class="filter-row">
            <select id="filterTicketType" class="filter-select">
              <option value="all">All Types</option>
              <option value="technical">Technical</option>
              <option value="spares">Spare Parts</option>
              <option value="general">General</option>
            </select>
            
            <select id="filterPriority" class="filter-select">
              <option value="all">All Priority</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            
            <select id="filterPartner" class="filter-select">
              <option value="all">All Partners</option>
            </select>
          </div>
        </div>

        <!-- Status Tabs -->
        <div class="filter-tabs scrollable" id="statusTabs">
          <button class="filter-tab ${this.filterStatus === 'all' ? 'active' : ''}" data-status="all">
            All <span class="tab-count">${this.tickets.length}</span>
          </button>
          <button class="filter-tab ${this.filterStatus === 'new' ? 'active' : ''}" data-status="new">
            New <span class="tab-count">${this.stats.new}</span>
          </button>
          <button class="filter-tab ${this.filterStatus === 'acknowledged' ? 'active' : ''}" data-status="acknowledged">
            Acknowledged <span class="tab-count">${this.stats.acknowledged}</span>
          </button>
          <button class="filter-tab ${this.filterStatus === 'in_progress' ? 'active' : ''}" data-status="in_progress">
            In Progress <span class="tab-count">${this.stats.in_progress}</span>
          </button>
          <button class="filter-tab ${this.filterStatus === 'pending_spares' ? 'active' : ''}" data-status="pending_spares">
            Pending Spares <span class="tab-count">${this.stats.pending_spares}</span>
          </button>
          <button class="filter-tab ${this.filterStatus === 'completed' ? 'active' : ''}" data-status="completed">
            Completed <span class="tab-count">${this.stats.completed}</span>
          </button>
        </div>

        <!-- Tickets List -->
        <div class="list-container" id="ticketsList">
          <div class="loading-state">Loading tickets...</div>
        </div>

        <!-- FAB -->
        <button class="fab" id="addTicketFab">
          <span>+</span>
        </button>
      </div>

      <!-- Ticket Detail Modal -->
      <div class="modal-overlay" id="ticketModal" style="display: none;">
        <div class="modal-content modal-lg">
          <div class="modal-header">
            <h4 id="modalTitle">Ticket Details</h4>
            <button class="modal-close" id="closeModal">&times;</button>
          </div>
          <div class="modal-body" id="modalBody"></div>
          <div class="modal-footer" id="modalFooter"></div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachListeners();
    this.populatePartnerFilter();
  }

  private renderStatsCards(): string {
    return `
      <div class="stat-mini new">
        <span class="stat-icon">📋</span>
        <span class="stat-value">${this.stats.new}</span>
        <span class="stat-label">New</span>
      </div>
      <div class="stat-mini acknowledged">
        <span class="stat-icon">✓</span>
        <span class="stat-value">${this.stats.acknowledged}</span>
        <span class="stat-label">Ack'd</span>
      </div>
      <div class="stat-mini in-progress">
        <span class="stat-icon">🔧</span>
        <span class="stat-value">${this.stats.in_progress}</span>
        <span class="stat-label">In Prog</span>
      </div>
      <div class="stat-mini pending">
        <span class="stat-icon">⏳</span>
        <span class="stat-value">${this.stats.pending_spares}</span>
        <span class="stat-label">Spares</span>
      </div>
      <div class="stat-mini completed">
        <span class="stat-icon">✅</span>
        <span class="stat-value">${this.stats.completed}</span>
        <span class="stat-label">Done</span>
      </div>
      ${this.stats.sla_breached > 0 ? `
      <div class="stat-mini breached">
        <span class="stat-icon">⚠️</span>
        <span class="stat-value">${this.stats.sla_breached}</span>
        <span class="stat-label">SLA!</span>
      </div>
      ` : ''}
    `;
  }

  private renderStats(): void {
    const statsGrid = document.getElementById('statsGrid');
    if (statsGrid) {
      statsGrid.innerHTML = this.renderStatsCards();
    }
    this.updateTabCounts();
  }

  private updateTabCounts(): void {
    const tabs = document.getElementById('statusTabs');
    if (!tabs) return;

    const counts: Record<string, number> = {
      all: this.tickets.length,
      new: this.stats.new,
      acknowledged: this.stats.acknowledged,
      in_progress: this.stats.in_progress,
      pending_spares: this.stats.pending_spares,
      completed: this.stats.completed
    };

    tabs.querySelectorAll('.filter-tab').forEach(tab => {
      const status = (tab as HTMLElement).dataset.status || 'all';
      const countEl = tab.querySelector('.tab-count');
      if (countEl) countEl.textContent = String(counts[status] || 0);
    });
  }

  private populatePartnerFilter(): void {
    const select = document.getElementById('filterPartner') as HTMLSelectElement;
    if (!select) return;

    this.partners.forEach(p => {
      const option = document.createElement('option');
      option.value = String(p.id);
      option.textContent = p.partner_name;
      select.appendChild(option);
    });
  }

  private attachListeners(): void {
    this.container.querySelectorAll('.filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.filterStatus = (tab as HTMLElement).dataset.status || 'all';
        this.container.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.applyFilters();
      });
    });

    const searchInput = document.getElementById('searchInput') as HTMLInputElement;
    searchInput?.addEventListener('input', () => {
      this.searchQuery = searchInput.value.toLowerCase();
      this.applyFilters();
    });

    document.getElementById('filterTicketType')?.addEventListener('change', (e) => {
      this.filterTicketType = (e.target as HTMLSelectElement).value;
      this.applyFilters();
    });

    document.getElementById('filterPriority')?.addEventListener('change', (e) => {
      this.filterPriority = (e.target as HTMLSelectElement).value;
      this.applyFilters();
    });

    document.getElementById('filterPartner')?.addEventListener('change', (e) => {
      this.filterPartner = (e.target as HTMLSelectElement).value;
      this.applyFilters();
    });

    document.getElementById('addTicketFab')?.addEventListener('click', () => {
      routerService.navigate('staff-tickets');
    });

    document.getElementById('closeModal')?.addEventListener('click', () => this.hideModal());
  }

  private applyFilters(): void {
    this.filteredTickets = this.tickets.filter(ticket => {
      const ticketStatus = (ticket.sub_status || ticket.status)?.toLowerCase().replace(/\s+/g, '_') || '';
      
      const matchesStatus = this.filterStatus === 'all' || 
        ticketStatus === this.filterStatus ||
        (this.filterStatus === 'new' && (ticketStatus === 'new' || ticketStatus === 'open')) ||
        (this.filterStatus === 'in_progress' && ticketStatus.includes('progress')) ||
        (this.filterStatus === 'pending_spares' && (ticketStatus.includes('spares') || ticketStatus.includes('awaiting'))) ||
        (this.filterStatus === 'completed' && (ticketStatus === 'completed' || ticketStatus === 'work_complete'));

      const matchesPriority = this.filterPriority === 'all' ||
        ticket.priority?.toLowerCase() === this.filterPriority;

      const matchesPartner = this.filterPartner === 'all' ||
        String(ticket.partner_id) === this.filterPartner;

      const matchesTicketType = this.filterTicketType === 'all' ||
        ticket.ticket_type?.toLowerCase() === this.filterTicketType;

      const matchesSearch = !this.searchQuery ||
        ticket.ticket_number?.toLowerCase().includes(this.searchQuery) ||
        ticket.customer_name?.toLowerCase().includes(this.searchQuery) ||
        ticket.customer_mobile?.includes(this.searchQuery) ||
        ticket.vehicle_number?.toLowerCase().includes(this.searchQuery) ||
        ticket.partner_name?.toLowerCase().includes(this.searchQuery);

      return matchesStatus && matchesPriority && matchesPartner && matchesTicketType && matchesSearch;
    });
    this.updateList();
  }

  private updateList(): void {
    const listContainer = document.getElementById('ticketsList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state"><div class="spinner"></div>Loading tickets...</div>';
      return;
    }

    if (this.filteredTickets.length === 0) {
      listContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📋</div>
          <h4>No Tickets Found</h4>
          <p>No ${this.filterStatus === 'all' ? '' : this.filterStatus.replace('_', ' ')} tickets match your filters</p>
        </div>
      `;
      return;
    }

    listContainer.innerHTML = this.filteredTickets.map(ticket => this.renderTicketCard(ticket)).join('');
    this.attachCardListeners();
  }

  private renderTicketCard(ticket: ServiceTicket): string {
    const statusClass = this.getStatusClass(ticket.sub_status || ticket.status);
    const priorityClass = ticket.priority?.toLowerCase() || 'medium';
    const createdDate = new Date(ticket.created_at).toLocaleDateString('en-IN', { 
      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' 
    });

    const isSlaBreached = ticket.sla_status?.toLowerCase().includes('breach');
    const tatWarning = this.getTatWarning(ticket);
    const isExpanded = this.expandedTicketId === ticket.id;

    return `
      <div class="ticket-wrapper" data-ticket-id="${ticket.id}">
        <div class="list-card service-ticket-card ${isSlaBreached ? 'sla-breached' : ''} ${isExpanded ? 'expanded' : ''}" data-id="${ticket.id}">
          <div class="ticket-header-row">
            <div class="ticket-id-section">
              <span class="ticket-number">${ticket.ticket_number || `#${ticket.id}`}</span>
              ${isSlaBreached ? '<span class="sla-badge">SLA!</span>' : ''}
            </div>
            <div class="ticket-header-right">
              <span class="priority-badge ${priorityClass}">${ticket.priority || 'Medium'}</span>
              <span class="expand-indicator">${isExpanded ? '▲' : '▼'}</span>
            </div>
          </div>
          
          <div class="ticket-customer-row">
            <span class="customer-name">${ticket.customer_name || 'Unknown Customer'}</span>
            <a href="tel:${ticket.customer_mobile}" class="phone-link" onclick="event.stopPropagation();">
              📞 ${ticket.customer_mobile || ''}
            </a>
          </div>

          <div class="ticket-vehicle-row">
            <span class="vehicle-badge">${ticket.vehicle_number || 'N/A'}</span>
            ${ticket.vehicle_model ? `<span class="vehicle-model">${ticket.vehicle_model}</span>` : ''}
          </div>

          <div class="ticket-issue-row">
            <span class="issue-category">${ticket.issue_category || 'General Service'}</span>
            ${ticket.partner_name ? `<span class="partner-tag">${ticket.partner_name}</span>` : ''}
          </div>

          ${ticket.service_technician_name ? `
          <div class="ticket-technician-row">
            <span class="technician-badge">👨‍🔧 ${ticket.service_technician_name}</span>
          </div>
          ` : ''}

          <div class="ticket-footer-row">
            <span class="ticket-date">${createdDate}</span>
            ${tatWarning ? `<span class="tat-warning">${tatWarning}</span>` : ''}
            <span class="status-badge ${statusClass}">${ticket.sub_status || ticket.status || 'Open'}</span>
          </div>
        </div>
        
        ${isExpanded ? this.renderInlineDetails(ticket) : ''}
      </div>
    `;
  }

  private renderInlineDetails(ticket: ServiceTicket): string {
    return `
      <div class="inline-ticket-details" data-detail-id="${ticket.id}">
        <div class="inline-detail-tabs">
          <button class="inline-tab active" data-tab="info" data-ticket-id="${ticket.id}">Info</button>
          <button class="inline-tab" data-tab="spares" data-ticket-id="${ticket.id}">Spares</button>
          <button class="inline-tab" data-tab="media" data-ticket-id="${ticket.id}">Media</button>
          <button class="inline-tab" data-tab="timeline" data-ticket-id="${ticket.id}">Timeline</button>
          <button class="inline-tab" data-tab="billing" data-ticket-id="${ticket.id}">Billing</button>
        </div>
        
        <div class="inline-tab-content" id="inlineTabContent-${ticket.id}">
          ${this.renderInfoTab(ticket)}
        </div>
        
        <div class="inline-action-buttons">
          ${this.getActionButtons(ticket)}
        </div>
      </div>
    `;
  }

  private getStatusClass(status: string | undefined): string {
    const s = (status || 'open').toLowerCase().replace(/\s+/g, '-');
    const statusMap: Record<string, string> = {
      'new': 'new',
      'open': 'new',
      'acknowledged': 'acknowledged',
      'diagnosing': 'diagnosing',
      'in-progress': 'in-progress',
      'awaiting-spares': 'pending-spares',
      'pending-spares': 'pending-spares',
      'ready-for-work': 'ready',
      'work-complete': 'completed',
      'completed': 'completed',
      'closed': 'closed'
    };
    return statusMap[s] || 'open';
  }

  private getTatWarning(ticket: ServiceTicket): string | null {
    if (!ticket.tat_due_at) return null;
    
    const due = new Date(ticket.tat_due_at);
    const now = new Date();
    const hoursLeft = (due.getTime() - now.getTime()) / (1000 * 60 * 60);
    
    if (hoursLeft < 0) return '⚠️ Overdue';
    if (hoursLeft < 4) return `⏰ ${Math.round(hoursLeft)}h left`;
    return null;
  }

  private attachCardListeners(): void {
    this.container.querySelectorAll('.service-ticket-card').forEach(card => {
      card.addEventListener('click', () => {
        const id = parseInt((card as HTMLElement).dataset.id || '0');
        this.toggleInlineExpansion(id);
      });
    });
    
    this.attachInlineTabListeners();
    this.attachInlineActionListeners();
  }

  private toggleInlineExpansion(id: number): void {
    if (this.expandedTicketId === id) {
      this.expandedTicketId = null;
    } else {
      this.expandedTicketId = id;
      this.selectedTicket = this.tickets.find(t => t.id === id) || null;
    }
    this.updateList();
    
    if (this.expandedTicketId) {
      setTimeout(() => {
        const wrapper = this.container.querySelector(`[data-ticket-id="${id}"]`);
        if (wrapper) {
          wrapper.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 50);
    }
  }

  private attachInlineTabListeners(): void {
    this.container.querySelectorAll('.inline-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        e.stopPropagation();
        const ticketId = parseInt((tab as HTMLElement).dataset.ticketId || '0');
        const tabName = (tab as HTMLElement).dataset.tab || 'info';
        const ticket = this.tickets.find(t => t.id === ticketId);
        if (!ticket) return;
        
        this.selectedTicket = ticket;
        
        const tabContainer = tab.closest('.inline-detail-tabs');
        if (tabContainer) {
          tabContainer.querySelectorAll('.inline-tab').forEach(t => t.classList.remove('active'));
          tab.classList.add('active');
        }
        
        const tabContent = document.getElementById(`inlineTabContent-${ticketId}`);
        if (tabContent) {
          if (tabName === 'info') tabContent.innerHTML = this.renderInfoTab(ticket);
          else if (tabName === 'spares') this.loadInlineSpares(ticketId, tabContent);
          else if (tabName === 'media') this.loadInlineMedia(ticketId, tabContent);
          else if (tabName === 'timeline') this.loadInlineTimeline(ticketId, tabContent);
          else if (tabName === 'billing') this.loadInlineBilling(ticketId, tabContent);
        }
      });
    });
  }

  private attachInlineActionListeners(): void {
    this.container.querySelectorAll('.inline-action-buttons .action-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const action = (btn as HTMLElement).dataset.action;
        const ticketId = parseInt((btn as HTMLElement).closest('.inline-ticket-details')?.getAttribute('data-detail-id') || '0');
        const ticket = this.tickets.find(t => t.id === ticketId);
        if (!ticket) return;
        
        this.selectedTicket = ticket;
        this.handleInlineAction(action || '', ticket);
      });
    });
  }

  private handleInlineAction(action: string, ticket: ServiceTicket): void {
    switch(action) {
      case 'acknowledge': this.acknowledgeTicket(); break;
      case 'diagnose': this.showDiagnoseModal(); break;
      case 'assign': this.showAssignTechModal(); break;
      case 'spares': this.showRequestSparesModal(); break;
      case 'checkSpares': this.checkSpares(); break;
      case 'complete': this.showCompleteModal(); break;
      case 'createBill': this.createBilling(); break;
      case 'confirmBill': this.confirmBilling(); break;
      case 'close': this.closeTicket(); break;
      case 'priority': this.showUpdatePriorityModal(); break;
      case 'reassign': this.showReassignPartnerModal(); break;
      case 'viewFull': this.showTicketDetails(ticket.id); break;
    }
  }

  private async loadInlineSpares(ticketId: number, container: HTMLElement): Promise<void> {
    container.innerHTML = '<div class="loading-inline">Loading spares...</div>';
    await this.loadSpareRequests(ticketId);
    const tabContent = document.getElementById('tabContent');
    if (tabContent) container.innerHTML = tabContent.innerHTML;
  }

  private async loadInlineMedia(ticketId: number, container: HTMLElement): Promise<void> {
    container.innerHTML = '<div class="loading-inline">Loading media...</div>';
    await this.loadMedia(ticketId);
    const tabContent = document.getElementById('tabContent');
    if (tabContent) container.innerHTML = tabContent.innerHTML;
  }

  private async loadInlineTimeline(ticketId: number, container: HTMLElement): Promise<void> {
    container.innerHTML = '<div class="loading-inline">Loading timeline...</div>';
    await this.loadTimeline(ticketId);
    const tabContent = document.getElementById('tabContent');
    if (tabContent) container.innerHTML = tabContent.innerHTML;
  }

  private async loadInlineBilling(ticketId: number, container: HTMLElement): Promise<void> {
    container.innerHTML = '<div class="loading-inline">Loading billing...</div>';
    await this.loadBilling(ticketId);
    const tabContent = document.getElementById('tabContent');
    if (tabContent) container.innerHTML = tabContent.innerHTML;
  }

  private async showTicketDetails(id: number): Promise<void> {
    this.selectedTicket = this.tickets.find(t => t.id === id) || null;
    if (!this.selectedTicket) return;

    const t = this.selectedTicket;
    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');
    const modalTitle = document.getElementById('modalTitle');
    const modal = document.getElementById('ticketModal');

    if (modalTitle) {
      modalTitle.textContent = `${t.ticket_number || `Ticket #${t.id}`}`;
    }

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="ticket-detail-tabs">
          <button class="detail-tab active" data-tab="info">Info</button>
          <button class="detail-tab" data-tab="spares">Spares</button>
          <button class="detail-tab" data-tab="media">Media</button>
          <button class="detail-tab" data-tab="timeline">Timeline</button>
          <button class="detail-tab" data-tab="billing">Billing</button>
        </div>

        <div id="tabContent">
          ${this.renderInfoTab(t)}
        </div>
      `;

      modalBody.querySelectorAll('.detail-tab').forEach(tab => {
        tab.addEventListener('click', () => {
          modalBody.querySelectorAll('.detail-tab').forEach(t => t.classList.remove('active'));
          tab.classList.add('active');
          const tabName = (tab as HTMLElement).dataset.tab;
          const tabContent = document.getElementById('tabContent');
          if (tabContent) {
            if (tabName === 'info') tabContent.innerHTML = this.renderInfoTab(t);
            else if (tabName === 'spares') this.loadSpareRequests(t.id);
            else if (tabName === 'media') this.loadMedia(t.id);
            else if (tabName === 'timeline') this.loadTimeline(t.id);
            else if (tabName === 'billing') this.loadBilling(t.id);
          }
        });
      });
    }

    if (modalFooter) {
      modalFooter.innerHTML = this.getActionButtons(t);
      this.attachActionListeners();
    }

    if (modal) modal.style.display = 'flex';
  }

  private renderInfoTab(t: ServiceTicket): string {
    return `
      <div class="ticket-detail-section">
        <div class="detail-grid">
          <div class="detail-item">
            <span class="detail-label">Status</span>
            <span class="status-badge ${this.getStatusClass(t.sub_status || t.status)}">${t.sub_status || t.status}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Priority</span>
            <span class="priority-badge ${t.priority?.toLowerCase()}">${t.priority}</span>
          </div>
          ${t.sla_status ? `
          <div class="detail-item">
            <span class="detail-label">SLA</span>
            <span class="sla-tag ${t.sla_status.includes('Breach') ? 'breached' : ''}">${t.sla_status}</span>
          </div>
          ` : ''}
        </div>
      </div>

      <div class="ticket-detail-section">
        <h5>👤 Customer</h5>
        <div class="detail-content">
          <p class="customer-name-large">${t.customer_name}</p>
          <a href="tel:${t.customer_mobile}" class="phone-link-large">📞 ${t.customer_mobile}</a>
        </div>
      </div>

      <div class="ticket-detail-section">
        <h5>🚗 Vehicle</h5>
        <div class="detail-grid">
          <div class="detail-item">
            <span class="detail-label">Number</span>
            <span class="detail-value">${t.vehicle_number}</span>
          </div>
          ${t.vehicle_model ? `
          <div class="detail-item">
            <span class="detail-label">Model</span>
            <span class="detail-value">${t.vehicle_model}</span>
          </div>
          ` : ''}
        </div>
      </div>

      <div class="ticket-detail-section">
        <h5>🔧 Issue</h5>
        <div class="detail-item">
          <span class="detail-label">Category</span>
          <span class="detail-value">${t.issue_category}</span>
        </div>
        <div class="issue-description-box">${t.issue_description || 'No description provided'}</div>
      </div>

      ${t.partner_name ? `
      <div class="ticket-detail-section">
        <h5>🏢 Partner</h5>
        <div class="detail-value">${t.partner_name}</div>
      </div>
      ` : ''}

      ${t.service_technician_name ? `
      <div class="ticket-detail-section">
        <h5>👨‍🔧 Assigned Technician</h5>
        <div class="detail-value">${t.service_technician_name}</div>
      </div>
      ` : ''}

      ${t.diagnosis_notes ? `
      <div class="ticket-detail-section">
        <h5>📋 Diagnosis</h5>
        <div class="notes-box">${t.diagnosis_notes}</div>
      </div>
      ` : ''}

      ${t.resolution_summary ? `
      <div class="ticket-detail-section">
        <h5>✅ Resolution</h5>
        <div class="notes-box">${t.resolution_summary}</div>
      </div>
      ` : ''}

      ${(t.labor_charges || t.spares_total) ? `
      <div class="ticket-detail-section">
        <h5>💰 Billing Summary</h5>
        <div class="billing-summary">
          <div class="billing-row">
            <span>Labor Charges</span>
            <span>₹${(t.labor_charges || 0).toLocaleString()}</span>
          </div>
          <div class="billing-row">
            <span>Spares Total</span>
            <span>₹${(t.spares_total || 0).toLocaleString()}</span>
          </div>
          <div class="billing-row total">
            <span>Total Amount</span>
            <span>₹${(t.total_amount || 0).toLocaleString()}</span>
          </div>
        </div>
      </div>
      ` : ''}
    `;
  }

  private async loadSpareRequests(ticketId: number): Promise<void> {
    const tabContent = document.getElementById('tabContent');
    if (!tabContent) return;

    tabContent.innerHTML = '<div class="loading-state">Loading spare requests...</div>';

    try {
      const response = await apiService.get<any>(`/tickets/service/${ticketId}/spare-requests`);
      const data = response as any;
      const spares: any[] = data.spare_requests || [];

      if (spares.length === 0) {
        tabContent.innerHTML = `
          <div class="empty-state">
            <p>No spare parts requested yet</p>
            <button class="btn btn-primary" id="addSpareBtn">Request Spares</button>
          </div>
        `;
        document.getElementById('addSpareBtn')?.addEventListener('click', () => this.showRequestSparesModal());
        return;
      }

      tabContent.innerHTML = `
        <div class="spares-list">
          ${spares.map((spare: any) => {
            const qty = parseInt(spare.quantity || 1);
            const R = (v: number) => `₹${v.toFixed(2)}`;
            // Marketplace pricing — single source of truth (matches web + marketplace-config)
            let priceHtml = '';
            if (spare.display_mrp != null) {
              const mrp      = parseFloat(spare.display_mrp || 0) * qty;
              const zvDisc   = parseFloat(spare.mrp_discount_amount || 0) * qty;
              const zvPct    = parseFloat(spare.mrp_discount_pct || 0);
              const idMode   = (spare.discount_mode || '').toUpperCase();
              const idDisc   = parseFloat(spare.discount_amount_unit || 0) * qty;
              const netAmt   = parseFloat(spare.net_before_tax_unit || 0) * qty;
              const gstR     = parseFloat(spare.gst_percent_mkt || 0);
              const taxAmt   = parseFloat(spare.gst_amount_unit || 0) * qty;
              const total    = parseFloat(spare.final_price_unit || 0) * qty;
              const specs    = [spare.mkt_specs, spare.mkt_color].filter(Boolean).join(' · ');
              priceHtml = `
                <div class="spare-price-breakup">
                  ${specs ? `<div style="font-size:11px;color:#0369a1;margin-bottom:4px;">${specs}</div>` : ''}
                  <table style="width:100%;font-size:11px;border-collapse:collapse;">
                    <tr><td style="color:#6b7280;">Base Cost (MRP)</td><td style="text-align:right;font-weight:600;">${R(mrp)}</td></tr>
                    <tr><td style="color:#ef4444;">Zynova Discount (${zvPct}%)</td><td style="text-align:right;color:#ef4444;">− ${R(zvDisc)}</td></tr>
                    ${idDisc > 0 ? `<tr><td style="color:#2563eb;">${idMode} Discount</td><td style="text-align:right;color:#2563eb;font-weight:700;">− ${R(idDisc)}</td></tr>` : ''}
                    <tr><td style="color:#374151;">Price after Discount</td><td style="text-align:right;font-weight:600;color:#0369a1;">${R(netAmt)}</td></tr>
                    <tr><td style="color:#6b7280;">Tax (${gstR}%)</td><td style="text-align:right;color:#6b7280;">${R(taxAmt)}</td></tr>
                    <tr style="border-top:1.5px solid #d1fae5;"><td style="font-weight:700;color:#166534;">Total with Tax</td><td style="text-align:right;font-weight:700;color:#166534;">${R(total)}</td></tr>
                  </table>
                </div>`;
            } else {
              // Fallback for custom spares
              const up  = parseFloat(spare.unit_price || 0);
              const gstR = parseFloat(spare.gst_rate || 18);
              const gstAmt = parseFloat(spare.gst_amount || (up * qty * gstR / 100));
              const total = parseFloat(spare.total_with_gst || (up * qty + gstAmt));
              if (up > 0) priceHtml = `
                <div class="spare-price-breakup">
                  <table style="width:100%;font-size:11px;border-collapse:collapse;">
                    <tr><td style="color:#374151;">Price after Discount</td><td style="text-align:right;font-weight:600;color:#0369a1;">${R(up * qty)}</td></tr>
                    <tr><td style="color:#6b7280;">Tax (${gstR}%)</td><td style="text-align:right;color:#6b7280;">${R(gstAmt)}</td></tr>
                    <tr style="border-top:1.5px solid #d1fae5;"><td style="font-weight:700;color:#166534;">Total with Tax</td><td style="text-align:right;font-weight:700;color:#166534;">${R(total)}</td></tr>
                  </table>
                </div>`;
            }
            const statusLabel = this._spareStatusLabel(spare.procurement_status);
            return `
              <div class="spare-card" data-spare-id="${spare.id}">
                <div class="spare-header">
                  <span class="spare-name">${spare.name || '—'}</span>
                  <span class="spare-status ${this.getSpareStatusClass(spare.procurement_status)}">${statusLabel}</span>
                </div>
                <div class="spare-details">
                  ${spare.code ? `<div class="spare-code">Code: ${spare.code}</div>` : ''}
                  <div class="spare-qty">Qty: <strong>${qty}</strong></div>
                  ${priceHtml}
                </div>
                ${spare.is_custom ? `<span class="custom-spare-tag">Custom Entry</span>` : ''}
                ${spare.marketplace_po_number ? `<div class="spare-po-badge"><span class="zypo-badge">ZYPO: ${spare.marketplace_po_number}</span></div>`
                  : spare.marketplace_procurement_number ? `<div class="spare-pr-badge"><span class="zypr-badge">ZYPR: ${spare.marketplace_procurement_number}</span></div>` : ''}
                ${spare.payment_amount ? `
                  <div class="spare-payment-info">
                    💰 ₹${parseFloat(spare.payment_amount).toFixed(2)} via ${spare.payment_mode || ''}
                    ${spare.payment_reference ? ` | Ref: ${spare.payment_reference}` : ''}
                  </div>` : ''}
                ${spare.dispatched_at ? `
                  <div class="spare-dispatch-info">
                    🚚 Dispatched ${new Date(spare.dispatched_at).toLocaleDateString('en-IN')}
                  </div>` : ''}
                ${this._renderMobileSpareActions({...spare, ticket_id: ticketId})}
              </div>
            `;
          }).join('')}
        </div>
        <button class="btn btn-primary btn-full" id="addMoreSparesBtn">+ Add More Spares</button>
      `;

      document.getElementById('addMoreSparesBtn')?.addEventListener('click', () => this.showRequestSparesModal());

      tabContent.querySelectorAll('.spare-action-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          const el = e.target as HTMLElement;
          const spareId = parseInt(el.getAttribute('data-spare-id') || '0');
          const tId = parseInt(el.getAttribute('data-ticket-id') || '0') || ticketId;
          const action = el.getAttribute('data-action');
          if (action === 'accept') await this._mobileSpareAccept(spareId, tId);
          else if (action === 'cancel') await this._mobileSpareCancel(spareId, tId);
          else if (action === 'payment') this._mobileSpareShowPayment(spareId, tId);
          else if (action === 'dispatch') await this._mobileSpareDispatch(spareId, tId);
        });
      });

    } catch (error) {
      tabContent.innerHTML = '<div class="error-state">Failed to load spare requests</div>';
    }
  }

  private async _mobileSpareAccept(spareId: number, ticketId: number): Promise<void> {
    if (!confirm('Accept this spare request? Stock will be checked and ZYPO/ZYPR auto-created if needed.')) return;
    try {
      const r = await fetch(`/api/v1/tickets/service/spares/${spareId}/accept`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('staff_token') || localStorage.getItem('token')}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes: 'Accepted via mobile' })
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Failed');
      const msg = d.marketplace_po_number ? `Accepted — ZYPO ${d.marketplace_po_number} created`
                : d.marketplace_procurement_number ? `Accepted — ZYPR ${d.marketplace_procurement_number} raised (out of stock)`
                : 'Spare accepted';
      alert(msg);
      await this.loadSpareRequests(ticketId);
    } catch (e: any) { alert('Error: ' + e.message); }
  }

  private async _mobileSpareCancel(spareId: number, ticketId: number): Promise<void> {
    const reason = prompt('Reason for cancellation:');
    if (!reason) return;
    try {
      const r = await fetch(`/api/v1/tickets/service/spares/${spareId}/cancel`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('staff_token') || localStorage.getItem('token')}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason })
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Failed');
      await this.loadSpareRequests(ticketId);
    } catch (e: any) { alert('Error: ' + e.message); }
  }

  private _mobileSpareShowPayment(spareId: number, ticketId: number): void {
    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');
    if (!modalBody || !modalFooter) return;
    const today = new Date().toISOString().slice(0, 10);
    modalBody.innerHTML = `
      <div class="form-section">
        <h5>Record Spare Payment</h5>
        <div class="form-group">
          <label>Amount (₹) *</label>
          <input type="number" id="mSpPmtAmt" class="form-input" min="0.01" step="0.01" placeholder="0.00">
        </div>
        <div class="form-group">
          <label>Payment Mode *</label>
          <div class="pmt-mode-group">
            ${['CASH','UPI','NEFT','CARD','BANK','CHEQUE'].map(m =>
              `<button type="button" class="pmt-mode-btn" data-mode="${m}" onclick="this.parentElement.querySelectorAll('.pmt-mode-btn').forEach(b=>b.classList.remove('active'));this.classList.add('active');document.getElementById('mSpPmtMode').value='${m}'">${m}</button>`
            ).join('')}
          </div>
          <input type="hidden" id="mSpPmtMode">
        </div>
        <div class="form-group">
          <label>Transaction Reference / UTR</label>
          <input type="text" id="mSpPmtRef" class="form-input" placeholder="UTR / Cheque no...">
        </div>
        <div class="form-group">
          <label>Payment Date</label>
          <input type="date" id="mSpPmtDate" class="form-input" value="${today}">
        </div>
        <div class="form-group">
          <label>Notes</label>
          <textarea id="mSpPmtNotes" class="form-textarea" rows="2" placeholder="Additional notes..."></textarea>
        </div>
        <div class="info-note">Recording payment will create an Income Entry in Accounts automatically.</div>
      </div>
    `;
    modalFooter.innerHTML = `
      <button class="btn btn-secondary" id="mSpPmtCancelBtn">Cancel</button>
      <button class="btn btn-success" id="mSpPmtSubmitBtn">Confirm Payment</button>
    `;
    document.getElementById('mSpPmtCancelBtn')?.addEventListener('click', () => this.loadSpareRequests(ticketId));
    document.getElementById('mSpPmtSubmitBtn')?.addEventListener('click', async () => {
      const amount = parseFloat((document.getElementById('mSpPmtAmt') as HTMLInputElement)?.value || '0');
      const mode = (document.getElementById('mSpPmtMode') as HTMLInputElement)?.value;
      const ref = (document.getElementById('mSpPmtRef') as HTMLInputElement)?.value?.trim() || null;
      const dateVal = (document.getElementById('mSpPmtDate') as HTMLInputElement)?.value || null;
      const notes = (document.getElementById('mSpPmtNotes') as HTMLTextAreaElement)?.value?.trim() || null;
      if (!amount || amount <= 0) { alert('Enter a valid amount'); return; }
      if (!mode) { alert('Select a payment mode'); return; }
      try {
        const r = await fetch(`/api/v1/tickets/service/spares/${spareId}/payment`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${localStorage.getItem('staff_token') || localStorage.getItem('token')}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ amount, payment_mode: mode, payment_reference: ref, payment_date: dateVal, payment_notes: notes })
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'Payment failed');
        const ieMsg = d.income_entry_number ? `\nIncome Entry: ${d.income_entry_number}` : '';
        alert(`Payment of ₹${amount.toFixed(2)} via ${mode} recorded${ieMsg}`);
        await this.loadSpareRequests(ticketId);
      } catch (e: any) { alert('Error: ' + e.message); }
    });
  }

  private async _mobileSpareDispatch(spareId: number, ticketId: number): Promise<void> {
    const notes = prompt('Dispatch notes (optional):', '') ?? null;
    if (notes === null) return;
    try {
      const r = await fetch(`/api/v1/tickets/service/spares/${spareId}/dispatch`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('staff_token') || localStorage.getItem('token')}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes: notes || null })
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Failed');
      alert('Spare marked as dispatched to technician');
      await this.loadSpareRequests(ticketId);
    } catch (e: any) { alert('Error: ' + e.message); }
  }

  private getSpareStatusClass(status: string): string {
    const statusClasses: Record<string, string> = {
      'pending':            'status-pending',
      'acknowledged':       'status-acknowledged',
      'payment_received':   'status-received',
      'waiting_for_spares': 'status-ordered',
      'dispatched':         'status-released',
      'ordered':            'status-ordered',
      'received':           'status-received',
      'released':           'status-released',
      'cancelled':          'status-cancelled',
    };
    return statusClasses[status] || 'status-default';
  }

  private _spareStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      'pending':            'Pending',
      'acknowledged':       'Acknowledged',
      'payment_received':   'Payment Received',
      'waiting_for_spares': 'Waiting for Spares',
      'dispatched':         'Dispatched',
      'ordered':            'Ordered',
      'received':           'Received',
      'released':           'Released',
      'cancelled':          'Cancelled',
    };
    return labels[status] || status;
  }

  private _renderMobileSpareActions(spare: any): string {
    const st = spare.procurement_status || 'pending';
    const id = spare.id;
    const ticketId = spare.ticket_id || 0;
    const btns: string[] = [];
    if (st === 'pending') {
      btns.push(`<button class="spare-action-btn accept-btn" data-spare-id="${id}" data-ticket-id="${ticketId}" data-action="accept">✓ Accept</button>`);
      btns.push(`<button class="spare-action-btn cancel-btn" data-spare-id="${id}" data-ticket-id="${ticketId}" data-action="cancel">✕ Cancel</button>`);
    }
    if (st === 'acknowledged') {
      btns.push(`<button class="spare-action-btn payment-btn" data-spare-id="${id}" data-ticket-id="${ticketId}" data-action="payment">💳 Payment</button>`);
      btns.push(`<button class="spare-action-btn cancel-btn" data-spare-id="${id}" data-ticket-id="${ticketId}" data-action="cancel">✕ Cancel</button>`);
    }
    if (st === 'payment_received' || st === 'waiting_for_spares') {
      btns.push(`<button class="spare-action-btn dispatch-btn" data-spare-id="${id}" data-ticket-id="${ticketId}" data-action="dispatch">🚚 Dispatch</button>`);
    }
    return btns.length ? `<div class="spare-lifecycle-actions">${btns.join('')}</div>` : '';
  }

  private showEditSpareModal(spare: any): void {
    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="form-section">
          <h5>Edit Spare Request</h5>
          <div class="spare-status-display">
            <span>Current Status: </span>
            <span class="spare-status ${this.getSpareStatusClass(spare.procurement_status)}">${spare.procurement_status}</span>
          </div>
          
          <div class="form-group">
            <label>Part Name *</label>
            <input type="text" id="editSpareName" class="form-input" value="${spare.spare_item_name}">
          </div>
          
          <div class="form-row">
            <div class="form-group flex-1">
              <label>Quantity *</label>
              <input type="number" id="editSpareQty" class="form-input" value="${spare.quantity_required}" min="1">
            </div>
            <div class="form-group flex-1">
              <label>Est. Cost (₹)</label>
              <input type="number" id="editSpareCost" class="form-input" value="${spare.estimated_cost || ''}">
            </div>
          </div>
          
          <div class="form-group">
            <label>Notes</label>
            <textarea id="editSpareNotes" class="form-textarea" rows="2">${spare.request_notes || ''}</textarea>
          </div>
        </div>
      `;
    }

    if (modalFooter) {
      modalFooter.innerHTML = `
        <button class="btn btn-secondary" id="cancelEditSpare">Cancel</button>
        <button class="btn btn-primary" id="saveEditSpare">Save Changes</button>
      `;

      document.getElementById('cancelEditSpare')?.addEventListener('click', () => {
        if (this.selectedTicket) this.loadSpareRequests(this.selectedTicket.id);
      });
      document.getElementById('saveEditSpare')?.addEventListener('click', () => this.saveSpareEdit(spare.id));
    }
  }

  private async saveSpareEdit(spareId: number): Promise<void> {
    const name = (document.getElementById('editSpareName') as HTMLInputElement)?.value.trim();
    const qty = parseInt((document.getElementById('editSpareQty') as HTMLInputElement)?.value) || 1;
    const cost = parseFloat((document.getElementById('editSpareCost') as HTMLInputElement)?.value) || null;
    const notes = (document.getElementById('editSpareNotes') as HTMLTextAreaElement)?.value.trim();

    if (!name) {
      this.showToast('Please enter part name', 'error');
      return;
    }

    try {
      const response = await apiService.put(`/tickets/service/spares/${spareId}/update`, {
        spare_item_name: name,
        quantity_required: qty,
        estimated_cost: cost,
        request_notes: notes || null
      });

      if (response.success) {
        this.showToast('Spare request updated');
        if (this.selectedTicket) this.loadSpareRequests(this.selectedTicket.id);
      } else {
        this.showToast((response as any).error || 'Failed to update', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to update', 'error');
    }
  }

  private async loadMedia(ticketId: number): Promise<void> {
    const tabContent = document.getElementById('tabContent');
    if (!tabContent) return;

    tabContent.innerHTML = '<div class="loading-state">Loading media...</div>';

    try {
      const response = await apiService.get<any>(`/tickets/service/${ticketId}/attachments`);
      if (response.success && response.data) {
        const attachments = response.data || [];
        if (attachments.length === 0) {
          tabContent.innerHTML = '<div class="empty-state">No media uploaded</div>';
        } else {
          const images = attachments.filter((a: any) => a.media_type === 'image' || a.file_type?.startsWith('image'));
          const videos = attachments.filter((a: any) => a.media_type === 'video' || a.file_type?.startsWith('video'));

          tabContent.innerHTML = `
            <div class="media-section">
              ${images.length > 0 ? `
                <div class="media-group">
                  <h5>📷 Images (${images.length})</h5>
                  <div class="media-grid">
                    ${images.map((img: any) => `
                      <div class="media-item" data-url="${img.compressed_url || img.file_url}">
                        <img src="${img.compressed_url || img.file_url}" alt="${img.file_name || 'Image'}" loading="lazy">
                        <div class="media-info">
                          <span class="media-name">${img.file_name || 'Image'}</span>
                          ${img.is_compressed ? '<span class="compressed-badge">Compressed</span>' : ''}
                        </div>
                      </div>
                    `).join('')}
                  </div>
                </div>
              ` : ''}
              ${videos.length > 0 ? `
                <div class="media-group">
                  <h5>🎬 Videos (${videos.length})</h5>
                  <div class="video-list">
                    ${videos.map((vid: any) => `
                      <div class="video-item">
                        <video controls preload="metadata" class="video-player">
                          <source src="${vid.compressed_url || vid.file_url}" type="${vid.file_type || 'video/mp4'}">
                          Your browser does not support the video tag.
                        </video>
                        <div class="video-info">
                          <span class="video-name">${vid.file_name || 'Video'}</span>
                          ${vid.video_duration_seconds ? `<span class="video-duration">${Math.floor(vid.video_duration_seconds / 60)}:${(vid.video_duration_seconds % 60).toString().padStart(2, '0')}</span>` : ''}
                          ${vid.is_compressed ? '<span class="compressed-badge">Compressed</span>' : ''}
                        </div>
                      </div>
                    `).join('')}
                  </div>
                </div>
              ` : ''}
              ${images.length === 0 && videos.length === 0 ? '<div class="empty-state">No media available</div>' : ''}
            </div>
          `;

          tabContent.querySelectorAll('.media-item').forEach(item => {
            item.addEventListener('click', () => {
              const url = (item as HTMLElement).dataset.url;
              if (url) this.showImageViewer(url);
            });
          });
        }
      } else {
        tabContent.innerHTML = '<div class="empty-state">No media uploaded</div>';
      }
    } catch (error) {
      tabContent.innerHTML = '<div class="error-state">Failed to load media</div>';
    }
  }

  private showImageViewer(imageUrl: string): void {
    const viewer = document.createElement('div');
    viewer.className = 'image-viewer-overlay';
    viewer.innerHTML = `
      <div class="image-viewer-container">
        <button class="close-viewer">&times;</button>
        <img src="${imageUrl}" alt="Full size image">
      </div>
    `;
    viewer.addEventListener('click', (e) => {
      if (e.target === viewer || (e.target as HTMLElement).classList.contains('close-viewer')) {
        viewer.remove();
      }
    });
    document.body.appendChild(viewer);
  }

  private async loadTimeline(ticketId: number): Promise<void> {
    const tabContent = document.getElementById('tabContent');
    if (!tabContent) return;

    tabContent.innerHTML = '<div class="loading-state">Loading timeline...</div>';

    try {
      const response = await apiService.get<any>(`/tickets/${ticketId}`);
      if (response.success && response.data) {
        const comments = response.data.comments || [];
        if (comments.length === 0) {
          tabContent.innerHTML = '<div class="empty-state">No timeline events</div>';
        } else {
          tabContent.innerHTML = `
            <div class="timeline">
              ${comments.map((c: any) => `
                <div class="timeline-item">
                  <div class="timeline-dot"></div>
                  <div class="timeline-content">
                    <div class="timeline-header">
                      <span class="timeline-author">${c.user_name || 'System'}</span>
                      <span class="timeline-date">${new Date(c.created_at).toLocaleString('en-IN')}</span>
                    </div>
                    <div class="timeline-text">${c.content}</div>
                  </div>
                </div>
              `).join('')}
            </div>
          `;
        }
      }
    } catch (error) {
      tabContent.innerHTML = '<div class="error-state">Failed to load timeline</div>';
    }
  }

  private async loadBilling(ticketId: number): Promise<void> {
    const tabContent = document.getElementById('tabContent');
    if (!tabContent) return;

    tabContent.innerHTML = '<div class="loading-state">Loading billing...</div>';

    try {
      const response = await apiService.get<any>(`/tickets/service/${ticketId}/billing`);
      if (response.success && response.data) {
        const billing = response.data;
        const canEdit = billing.status !== 'CONFIRMED' && billing.status !== 'PAID';
        tabContent.innerHTML = `
          <div class="billing-details">
            <div class="billing-header">
              <span class="billing-status ${billing.status?.toLowerCase()}">${billing.status || 'Pending'}</span>
              ${canEdit ? '<button class="btn btn-sm btn-outline" id="editBillingBtn">Edit</button>' : ''}
            </div>
            
            <div class="billing-section">
              <h6>Items</h6>
              ${billing.items?.length > 0 ? `
                <div class="billing-items">
                  ${billing.items.map((item: any) => `
                    <div class="billing-item-row">
                      <span class="item-name">${item.description}</span>
                      <span class="item-qty">x${item.quantity}</span>
                      <span class="item-amount">₹${item.amount?.toLocaleString()}</span>
                    </div>
                  `).join('')}
                </div>
              ` : '<div class="empty-mini">No items added</div>'}
              ${canEdit ? '<button class="btn btn-sm btn-primary mt-2" id="addBillingItemBtn">+ Add Item</button>' : ''}
            </div>

            <div class="billing-totals">
              <div class="total-row">
                <span>Labor</span>
                <span id="laborDisplay">₹${(billing.labor_charges || 0).toLocaleString()}</span>
                ${canEdit ? '<button class="btn-icon" id="editLaborBtn" title="Edit">✏️</button>' : ''}
              </div>
              <div class="total-row">
                <span>Spares</span>
                <span>₹${(billing.spares_total || 0).toLocaleString()}</span>
              </div>
              <div class="total-row grand">
                <span>Total</span>
                <span>₹${(billing.total_amount || 0).toLocaleString()}</span>
              </div>
            </div>
          </div>
        `;
        // DC_BILLING_EDIT_001: Attach billing edit handlers
        this.attachBillingEditHandlers(ticketId, billing);
      } else {
        tabContent.innerHTML = `
          <div class="empty-state">
            <p>No billing created yet</p>
            <button class="btn btn-primary" id="createBillingBtn">Create Billing</button>
          </div>
        `;
        document.getElementById('createBillingBtn')?.addEventListener('click', () => this.createBilling());
      }
    } catch (error) {
      tabContent.innerHTML = `
        <div class="empty-state">
          <p>No billing created yet</p>
          <button class="btn btn-primary" id="createBillingBtn">Create Billing</button>
        </div>
      `;
      document.getElementById('createBillingBtn')?.addEventListener('click', () => this.createBilling());
    }
  }

  private attachBillingEditHandlers(ticketId: number, billing: any): void {
    document.getElementById('addBillingItemBtn')?.addEventListener('click', () => {
      this.showAddBillingItemModal(ticketId, billing.id);
    });
    document.getElementById('editLaborBtn')?.addEventListener('click', () => {
      this.showAddLaborModal(ticketId, billing.id);
    });
  }

  private showAddBillingItemModal(ticketId: number, billingId: number): void {
    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="form-section">
          <h5>Add Billing Item</h5>
          <div class="form-group">
            <label>Description *</label>
            <input type="text" id="itemDescription" class="form-input" placeholder="e.g., Battery replacement">
          </div>
          <div class="form-row">
            <div class="form-group flex-1">
              <label>Quantity *</label>
              <input type="number" id="itemQty" class="form-input" value="1" min="1">
            </div>
            <div class="form-group flex-1">
              <label>Unit Price (₹) *</label>
              <input type="number" id="itemPrice" class="form-input" placeholder="0">
            </div>
          </div>
          <div class="form-group">
            <label>Type</label>
            <select id="itemType" class="form-select">
              <option value="spare">Spare Part</option>
              <option value="service">Service</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>
      `;
    }

    if (modalFooter) {
      modalFooter.innerHTML = `
        <button class="btn btn-secondary" id="cancelAddItem">Cancel</button>
        <button class="btn btn-primary" id="submitAddItem">Add Item</button>
      `;

      document.getElementById('cancelAddItem')?.addEventListener('click', () => {
        this.loadBilling(ticketId);
      });
      document.getElementById('submitAddItem')?.addEventListener('click', () => {
        this.submitBillingItem(ticketId, billingId);
      });
    }
  }

  private async submitBillingItem(ticketId: number, billingId: number): Promise<void> {
    const description = (document.getElementById('itemDescription') as HTMLInputElement)?.value.trim();
    const quantity = parseInt((document.getElementById('itemQty') as HTMLInputElement)?.value) || 1;
    const unitPrice = parseFloat((document.getElementById('itemPrice') as HTMLInputElement)?.value) || 0;
    const itemType = (document.getElementById('itemType') as HTMLSelectElement)?.value || 'spare';

    if (!description) {
      this.showToast('Please enter item description', 'error');
      return;
    }
    if (unitPrice <= 0) {
      this.showToast('Please enter valid price', 'error');
      return;
    }

    try {
      // DC_BILLING_API_001: Use backend's add-item endpoint with correct params
      const response = await apiService.post(`/tickets/service/billing/${billingId}/add-item`, {
        description: description,
        quantity: quantity,
        rate: unitPrice,
        item_type: itemType,
        tax_rate: 0,
        is_intrastate: true
      });

      if (response.success) {
        this.showToast('Item added');
        this.loadBilling(ticketId);
      } else {
        this.showToast(response.error || 'Failed to add item', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to add item', 'error');
    }
  }

  private showAddLaborModal(ticketId: number, billingId: number): void {
    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="form-section">
          <h5>Add Labor Charges</h5>
          <div class="form-group">
            <label>Description</label>
            <input type="text" id="laborDesc" class="form-input" value="Labor Charges" placeholder="e.g., Repair labor">
          </div>
          <div class="form-group">
            <label>Amount (₹) *</label>
            <input type="number" id="laborAmount" class="form-input" placeholder="0" min="0">
          </div>
        </div>
      `;
    }

    if (modalFooter) {
      modalFooter.innerHTML = `
        <button class="btn btn-secondary" id="cancelLabor">Cancel</button>
        <button class="btn btn-primary" id="submitLabor">Add</button>
      `;

      document.getElementById('cancelLabor')?.addEventListener('click', () => {
        this.loadBilling(ticketId);
      });
      document.getElementById('submitLabor')?.addEventListener('click', () => {
        this.addLaborCharges(ticketId, billingId);
      });
    }
  }

  private async addLaborCharges(ticketId: number, billingId: number): Promise<void> {
    const laborDesc = (document.getElementById('laborDesc') as HTMLInputElement)?.value.trim() || 'Labor Charges';
    const laborAmount = parseFloat((document.getElementById('laborAmount') as HTMLInputElement)?.value) || 0;

    if (laborAmount <= 0) {
      this.showToast('Please enter a valid amount', 'error');
      return;
    }

    try {
      // DC_BILLING_API_002: Use add-item endpoint for labor charges
      const response = await apiService.post(`/tickets/service/billing/${billingId}/add-item`, {
        description: laborDesc,
        quantity: 1,
        rate: laborAmount,
        item_type: 'labour',
        tax_rate: 0,
        is_intrastate: true
      });

      if (response.success) {
        this.showToast('Labor charges added');
        this.loadBilling(ticketId);
      } else {
        this.showToast(response.error || 'Failed to add', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to add', 'error');
    }
  }

  private getActionButtons(ticket: ServiceTicket): string {
    const status = (ticket.sub_status || ticket.status)?.toLowerCase().replace(/\s+/g, '_');
    let buttons = '<button class="btn btn-secondary action-btn" data-action="viewFull" id="closeDetails">View Full</button>';

    switch (status) {
      case 'new':
      case 'open':
        buttons += '<button class="btn btn-primary action-btn" data-action="acknowledge" id="acknowledgeBtn">Acknowledge</button>';
        break;
      case 'acknowledged':
        buttons += '<button class="btn btn-info action-btn" data-action="assign" id="assignTechBtn">Assign Tech</button>';
        buttons += '<button class="btn btn-primary action-btn" data-action="diagnose" id="diagnoseBtn">Diagnose</button>';
        break;
      case 'diagnosing':
      case 'in_progress':
      case 'in-progress':
      case 'ready_for_work':
        buttons += '<button class="btn btn-warning action-btn" data-action="spares" id="requestSparesBtn">Request Spares</button>';
        buttons += '<button class="btn btn-success action-btn" data-action="complete" id="completeBtn">Complete</button>';
        break;
      case 'awaiting_spares':
      case 'pending_spares':
        buttons += '<button class="btn btn-info action-btn" data-action="checkSpares" id="checkSparesBtn">Check Spares</button>';
        break;
      case 'work_complete':
      case 'completed':
        if (!ticket.total_amount) {
          buttons += '<button class="btn btn-primary action-btn" data-action="createBill" id="createBillBtn">Create Bill</button>';
        } else {
          buttons += '<button class="btn btn-success action-btn" data-action="confirmBill" id="confirmBillBtn">Confirm Payment</button>';
        }
        buttons += '<button class="btn btn-danger action-btn" data-action="close" id="closeTicketBtn">Close Ticket</button>';
        break;
    }

    buttons += '<button class="btn btn-outline action-btn" data-action="priority" id="updatePriorityBtn">Priority</button>';
    
    if (ticket.partner_id) {
      buttons += '<button class="btn btn-outline action-btn" data-action="reassign" id="reassignPartnerBtn">Reassign Partner</button>';
    }

    return buttons;
  }

  private attachActionListeners(): void {
    document.getElementById('closeDetails')?.addEventListener('click', () => this.hideModal());
    document.getElementById('acknowledgeBtn')?.addEventListener('click', () => this.acknowledgeTicket());
    document.getElementById('diagnoseBtn')?.addEventListener('click', () => this.showDiagnoseModal());
    document.getElementById('assignTechBtn')?.addEventListener('click', () => this.showAssignTechModal());
    document.getElementById('requestSparesBtn')?.addEventListener('click', () => this.showRequestSparesModal());
    document.getElementById('checkSparesBtn')?.addEventListener('click', () => this.checkSpares());
    document.getElementById('completeBtn')?.addEventListener('click', () => this.showCompleteModal());
    document.getElementById('createBillBtn')?.addEventListener('click', () => this.createBilling());
    document.getElementById('confirmBillBtn')?.addEventListener('click', () => this.confirmBilling());
    document.getElementById('reassignPartnerBtn')?.addEventListener('click', () => this.showReassignPartnerModal());
    document.getElementById('closeTicketBtn')?.addEventListener('click', () => this.closeTicket());
    document.getElementById('updatePriorityBtn')?.addEventListener('click', () => this.showUpdatePriorityModal());
  }

  private showReassignPartnerModal(): void {
    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="form-section">
          <h5>Reassign Partner</h5>
          <div class="current-partner-info card" style="margin-bottom:16px;padding:12px;">
            <small>Current Partner</small>
            <div style="font-weight:600;">${this.selectedTicket?.partner_name || 'N/A'}</div>
          </div>
          <div class="form-group">
            <label>Select New Partner *</label>
            <select id="newPartnerSelect" class="form-select">
              <option value="">-- Select Partner --</option>
              ${this.partners.map(p => `
                <option value="${p.id}" ${p.id === this.selectedTicket?.partner_id ? 'disabled' : ''}>
                  ${p.partner_name} (${p.category})
                </option>
              `).join('')}
            </select>
          </div>
          <div class="form-group">
            <label>Reason for Reassignment *</label>
            <textarea id="reassignReason" class="form-textarea" rows="3" placeholder="Enter reason for reassignment (required for audit)..."></textarea>
          </div>
        </div>
      `;
    }

    if (modalFooter) {
      modalFooter.innerHTML = `
        <button class="btn btn-secondary" id="cancelReassign">Cancel</button>
        <button class="btn btn-primary" id="submitReassign">Reassign</button>
      `;

      document.getElementById('cancelReassign')?.addEventListener('click', () => {
        this.showTicketDetails(this.selectedTicket!.id);
      });
      document.getElementById('submitReassign')?.addEventListener('click', () => this.submitPartnerReassignment());
    }
  }

  private async submitPartnerReassignment(): Promise<void> {
    if (!this.selectedTicket) return;

    const newPartnerId = (document.getElementById('newPartnerSelect') as HTMLSelectElement)?.value;
    const reason = (document.getElementById('reassignReason') as HTMLTextAreaElement)?.value.trim();

    if (!newPartnerId) {
      this.showToast('Please select a new partner', 'error');
      return;
    }

    if (!reason) {
      this.showToast('Please provide a reason for reassignment', 'error');
      return;
    }

    try {
      const response = await apiService.put(`/tickets/${this.selectedTicket.id}/reassign-partner`, {
        new_partner_id: parseInt(newPartnerId),
        change_reason: reason
      });

      if (response.success) {
        this.showToast('Partner reassigned successfully');
        this.hideModal();
        await this.loadData();
      } else {
        this.showToast((response as any).message || response.error || 'Failed to reassign', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to reassign partner', 'error');
    }
  }

  private async acknowledgeTicket(): Promise<void> {
    if (!this.selectedTicket) return;

    try {
      const response = await apiService.post(`/tickets/service/${this.selectedTicket.id}/acknowledge`, {});
      if (response.success) {
        this.showToast('Ticket acknowledged successfully');
        this.hideModal();
        await this.loadData();
      } else {
        this.showToast(response.error || 'Failed to acknowledge', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to acknowledge', 'error');
    }
  }

  private showDiagnoseModal(): void {
    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="form-section">
          <h5>Enter Diagnosis</h5>
          <div class="form-group">
            <label>Diagnosis Notes *</label>
            <textarea id="diagnosisNotes" class="form-textarea" rows="4" placeholder="Describe the issue found and recommended repairs..."></textarea>
          </div>
          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" id="sparesRequired">
              <span>Spare parts will be required</span>
            </label>
          </div>
          <div class="form-group">
            <label>Estimated Labor (₹)</label>
            <input type="number" id="estimatedLabor" class="form-input" placeholder="0">
          </div>
        </div>
      `;
    }

    if (modalFooter) {
      modalFooter.innerHTML = `
        <button class="btn btn-secondary" id="cancelDiagnose">Cancel</button>
        <button class="btn btn-primary" id="submitDiagnose">Submit Diagnosis</button>
      `;

      document.getElementById('cancelDiagnose')?.addEventListener('click', () => {
        this.showTicketDetails(this.selectedTicket!.id);
      });
      document.getElementById('submitDiagnose')?.addEventListener('click', () => this.submitDiagnosis());
    }
  }

  private async submitDiagnosis(): Promise<void> {
    if (!this.selectedTicket) return;

    const notes = (document.getElementById('diagnosisNotes') as HTMLTextAreaElement)?.value.trim();
    const sparesRequired = (document.getElementById('sparesRequired') as HTMLInputElement)?.checked;
    const estimatedLabor = parseFloat((document.getElementById('estimatedLabor') as HTMLInputElement)?.value) || 0;

    if (!notes) {
      this.showToast('Please enter diagnosis notes', 'error');
      return;
    }

    try {
      const response = await apiService.post(`/tickets/service/${this.selectedTicket.id}/diagnose`, {
        diagnosis_notes: notes,
        spares_required: sparesRequired,
        estimated_labor: estimatedLabor
      });

      if (response.success) {
        this.showToast('Diagnosis submitted');
        await this.loadData();
        // DC_SPARE_FLOW_001: Auto-show spare parts modal if spares required
        if (sparesRequired) {
          this.showRequestSparesModal();
        } else {
          this.hideModal();
        }
      } else {
        this.showToast(response.error || 'Failed to submit diagnosis', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to submit diagnosis', 'error');
    }
  }

  private showAssignTechModal(): void {
    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="form-section">
          <h5>Assign Technician</h5>
          <div class="form-group">
            <label>Select Technician *</label>
            <select id="technicianSelect" class="form-select">
              <option value="">-- Select Technician --</option>
            </select>
          </div>
          <div class="form-group">
            <label>Notes</label>
            <textarea id="assignNotes" class="form-textarea" rows="2" placeholder="Assignment notes (optional)"></textarea>
          </div>
        </div>
        <div class="loading-state" id="loadingTechs">Loading technicians...</div>
      `;
      
      this.loadTechnicians();
    }

    if (modalFooter) {
      modalFooter.innerHTML = `
        <button class="btn btn-secondary" id="cancelAssign">Cancel</button>
        <button class="btn btn-primary" id="submitAssign">Assign</button>
      `;

      document.getElementById('cancelAssign')?.addEventListener('click', () => {
        this.showTicketDetails(this.selectedTicket!.id);
      });
      document.getElementById('submitAssign')?.addEventListener('click', () => this.submitAssignment());
    }
  }

  private async loadTechnicians(): Promise<void> {
    try {
      const response = await apiService.get<any>('/staff/employees?role=technician');
      const loadingEl = document.getElementById('loadingTechs');
      const select = document.getElementById('technicianSelect') as HTMLSelectElement;
      
      if (loadingEl) loadingEl.style.display = 'none';
      
      if (response.success && response.data && select) {
        const techs = response.data.employees || response.data || [];
        techs.forEach((tech: any) => {
          const option = document.createElement('option');
          option.value = String(tech.id);
          option.textContent = `${tech.full_name} (${tech.emp_code})`;
          select.appendChild(option);
        });
      }
    } catch (error) {
      console.error('Failed to load technicians:', error);
    }
  }

  private async submitAssignment(): Promise<void> {
    if (!this.selectedTicket) return;

    const techId = (document.getElementById('technicianSelect') as HTMLSelectElement)?.value;
    const notes = (document.getElementById('assignNotes') as HTMLTextAreaElement)?.value.trim();

    if (!techId) {
      this.showToast('Please select a technician', 'error');
      return;
    }

    try {
      const response = await apiService.post(`/tickets/${this.selectedTicket.id}/assign`, {
        assigned_to: techId,
        assignment_reason: notes || 'Assigned via mobile app'
      });

      if (response.success) {
        this.showToast('Technician assigned');
        this.hideModal();
        await this.loadData();
      } else {
        this.showToast(response.error || 'Failed to assign', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to assign', 'error');
    }
  }

  private selectedStockItem: any = null;
  private selectedMarketplaceItem: any = null;  // catalog-pick mode
  private spareMode: 'catalog' | 'manual' = 'catalog';
  private catalogDiscountMode: string = '';
  private spareMediaFiles: File[] = [];
  private spareVideoFile: File | null = null;
  private searchDebounceTimer: any = null;
  private catalogSearchTimer: any = null;
  private pendingSpareItems: Array<{name: string; code: string | null; quantity: number; estimated_cost: number | null; gst_rate: number; hsn_code: string | null; notes: string | null; stock_item_id: number | null; marketplace_spare_id?: number | null; discount_mode?: string | null}> = [];

  private showRequestSparesModal(): void {
    if (!this.selectedTicket) return;
    
    const ticketStatus = (this.selectedTicket.sub_status || this.selectedTicket.status || '').toLowerCase();
    const allowedStatuses = ['diagnosing', 'awaiting_spares', 'in_progress', 'in-progress', 'ready_for_work'];
    
    if (!allowedStatuses.includes(ticketStatus)) {
      this.showToast(`Cannot request spares in "${ticketStatus}" status. Ticket must be in Diagnosing or In Progress status.`, 'error');
      return;
    }
    
    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');
    this.selectedStockItem = null;
    this.selectedMarketplaceItem = null;
    this.spareMode = 'catalog';
    this.catalogDiscountMode = '';
    this.spareMediaFiles = [];
    this.spareVideoFile = null;
    this.pendingSpareItems = [];

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="form-section">
          <h5>Request Spare Parts</h5>

          <div id="pendingItemsList" class="pending-items-list" style="display:none;"></div>

          <!-- Mode toggle -->
          <div class="spare-mode-toggle" style="display:flex;gap:8px;margin-bottom:12px;">
            <button id="modeCatalogBtn" class="btn btn-sm btn-primary" style="flex:1;">🔍 Catalog</button>
            <button id="modeManualBtn" class="btn btn-sm btn-outline" style="flex:1;">✏️ Manual</button>
          </div>

          <!-- CATALOG MODE -->
          <div id="catalogModeSection">
            <div class="form-group">
              <label>Discount (optional)</label>
              <select id="catalogDiscountSelect" class="form-input" style="margin-bottom:6px;">
                <option value="">No Discount</option>
                <option value="mnr">MNR Member (3%)</option>
                <option value="student">ETC Student (10%)</option>
                <option value="partner">Partner (12%)</option>
              </select>
            </div>
            <div class="form-group">
              <label>Search Catalog *</label>
              <input type="text" id="catalogSearchInput" class="form-input" placeholder="Search: name, SKU, category…">
              <div id="catalogSearchResults" style="max-height:200px;overflow-y:auto;margin-top:4px;"></div>
            </div>
            <div id="selectedCatalogInfo" style="display:none;background:#f0fdf4;border:1px solid #86efac;border-radius:6px;padding:8px;margin-bottom:8px;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                  <div id="selectedCatalogName" style="font-weight:600;font-size:13px;"></div>
                  <div id="selectedCatalogPrice" style="font-size:12px;color:#166534;"></div>
                </div>
                <button type="button" id="clearCatalogSelection" class="btn-icon">&times;</button>
              </div>
            </div>
          </div>

          <!-- MANUAL MODE -->
          <div id="manualModeSection" style="display:none;">
            <div class="form-group">
              <label>Search Stock Items</label>
              <input type="text" id="stockSearch" class="form-input" placeholder="Type to search stock items...">
              <div id="stockSearchResults" class="stock-search-results"></div>
            </div>
            <div id="selectedStockInfo" class="selected-stock-info" style="display:none;">
              <div class="stock-item-badge">
                <span id="selectedStockName"></span>
                <button type="button" id="clearStockSelection" class="btn-icon">&times;</button>
              </div>
            </div>
            <div class="form-group">
              <label>Part Name *</label>
              <input type="text" id="spareName" class="form-input" placeholder="e.g., Battery Pack 48V">
              <small class="form-hint">Or enter custom part name if not in stock</small>
            </div>
            <div class="form-group">
              <label>Part Code</label>
              <input type="text" id="partNumber" class="form-input" placeholder="Optional part code/SKU">
            </div>
            <div class="form-row">
              <div class="form-group flex-1">
                <label>Unit Price (₹)</label>
                <input type="number" id="estPrice" class="form-input" placeholder="0">
              </div>
              <div class="form-group flex-1">
                <label>GST Rate (%)</label>
                <input type="number" id="gstRate" class="form-input" value="18" min="0" max="28">
              </div>
            </div>
            <div class="form-group">
              <label>HSN Code</label>
              <input type="text" id="hsnCode" class="form-input" placeholder="Optional">
            </div>
          </div>

          <!-- Shared: Quantity + Notes -->
          <div class="form-row">
            <div class="form-group flex-1">
              <label>Quantity *</label>
              <input type="number" id="quantity" class="form-input" value="1" min="1">
            </div>
          </div>
          <div class="form-group">
            <label>Notes</label>
            <textarea id="spareNotes" class="form-textarea" rows="2" placeholder="Additional details..."></textarea>
          </div>

          <div class="media-choice-label">Upload Images OR Video (not both)</div>
          <div class="form-group">
            <label>Images (up to 10)</label>
            <input type="file" id="spareImages" accept="image/*" multiple class="form-input-file">
            <div id="imagePreviewContainer" class="media-preview-container"></div>
          </div>
          <div class="media-or-divider">— OR —</div>
          <div class="form-group">
            <label>Video (max 3 mins)</label>
            <input type="file" id="spareVideo" accept="video/*" class="form-input-file">
            <div id="videoPreviewContainer" class="media-preview-container"></div>
          </div>
        </div>
      `;

      this.attachSpareMediaHandlers();
      this.attachStockSearchHandler();
      this.attachCatalogSearchHandler();
      this.attachModeSwitchHandlers();
    }

    if (modalFooter) {
      modalFooter.innerHTML = `
        <button class="btn btn-secondary" id="cancelSpares">Cancel</button>
        <button class="btn btn-outline" id="addAnotherSpare">+ Add Item</button>
        <button class="btn btn-warning" id="submitSpares">Submit All</button>
      `;

      document.getElementById('cancelSpares')?.addEventListener('click', () => {
        this.pendingSpareItems = [];
        this.showTicketDetails(this.selectedTicket!.id);
      });
      document.getElementById('addAnotherSpare')?.addEventListener('click', () => this.addSpareToList());
      document.getElementById('submitSpares')?.addEventListener('click', () => this.submitSparesRequest());
    }
  }
  
  private addSpareToList(): void {
    const quantity = parseInt((document.getElementById('quantity') as HTMLInputElement)?.value) || 1;
    const notes = (document.getElementById('spareNotes') as HTMLTextAreaElement)?.value.trim();

    if (this.spareMode === 'catalog') {
      if (!this.selectedMarketplaceItem) {
        this.showToast('Please search and select a catalog item', 'error');
        return;
      }
      const item = this.selectedMarketplaceItem;
      this.pendingSpareItems.push({
        name: item.name,
        code: item.sku || null,
        quantity,
        estimated_cost: item.final_price || null,
        gst_rate: item.gst_percent || 18,
        hsn_code: item.hsn_code || null,
        notes: notes || null,
        stock_item_id: null,
        marketplace_spare_id: item.id,
        discount_mode: this.catalogDiscountMode || null,
      });
      this.clearSpareForm();
      this.renderPendingItemsList();
      this.showToast(`Added "${item.name}" from catalog (${this.pendingSpareItems.length} items)`);
    } else {
      const spareName = (document.getElementById('spareName') as HTMLInputElement)?.value.trim();
      const partNumber = (document.getElementById('partNumber') as HTMLInputElement)?.value.trim();
      const estPrice = parseFloat((document.getElementById('estPrice') as HTMLInputElement)?.value) || 0;
      const gstRate = parseFloat((document.getElementById('gstRate') as HTMLInputElement)?.value) || 18;
      const hsnCode = (document.getElementById('hsnCode') as HTMLInputElement)?.value.trim();

      if (!spareName) {
        this.showToast('Please enter spare part name', 'error');
        return;
      }

      this.pendingSpareItems.push({
        name: spareName,
        code: partNumber || null,
        quantity,
        estimated_cost: estPrice || null,
        gst_rate: gstRate,
        hsn_code: hsnCode || null,
        notes: notes || null,
        stock_item_id: this.selectedStockItem?.id || null,
        marketplace_spare_id: null,
        discount_mode: null,
      });
      this.clearSpareForm();
      this.renderPendingItemsList();
      this.showToast(`Added "${spareName}" to list (${this.pendingSpareItems.length} items)`);
    }
  }

  private clearSpareForm(): void {
    const trySet = (id: string, val: string) => {
      const el = document.getElementById(id) as HTMLInputElement | HTMLTextAreaElement | null;
      if (el) el.value = val;
    };
    trySet('spareName', '');
    trySet('partNumber', '');
    trySet('quantity', '1');
    trySet('estPrice', '');
    trySet('gstRate', '18');
    trySet('hsnCode', '');
    trySet('spareNotes', '');
    trySet('stockSearch', '');
    trySet('catalogSearchInput', '');
    const stockResults = document.getElementById('stockSearchResults');
    if (stockResults) stockResults.innerHTML = '';
    const catResults = document.getElementById('catalogSearchResults');
    if (catResults) catResults.innerHTML = '';
    const stockInfo = document.getElementById('selectedStockInfo');
    if (stockInfo) stockInfo.style.display = 'none';
    const catInfo = document.getElementById('selectedCatalogInfo');
    if (catInfo) catInfo.style.display = 'none';
    this.selectedStockItem = null;
    this.selectedMarketplaceItem = null;
  }
  
  private renderPendingItemsList(): void {
    const container = document.getElementById('pendingItemsList');
    if (!container) return;
    
    if (this.pendingSpareItems.length === 0) {
      container.style.display = 'none';
      return;
    }
    
    container.style.display = 'block';
    container.innerHTML = `
      <div class="pending-items-header">
        <strong>Items to Submit (${this.pendingSpareItems.length})</strong>
      </div>
      <div class="pending-items-grid">
        ${this.pendingSpareItems.map((item, idx) => `
          <div class="pending-item">
            <div class="pending-item-info">
              <span class="item-name">${item.name}</span>
              <span class="item-qty">x${item.quantity}</span>
              ${item.estimated_cost ? `<span class="item-price">₹${item.estimated_cost}</span>` : ''}
            </div>
            <button class="btn-icon remove-pending" data-idx="${idx}">&times;</button>
          </div>
        `).join('')}
      </div>
    `;
    
    container.querySelectorAll('.remove-pending').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const idx = parseInt((e.target as HTMLElement).getAttribute('data-idx') || '0');
        this.pendingSpareItems.splice(idx, 1);
        this.renderPendingItemsList();
      });
    });
  }

  private attachStockSearchHandler(): void {
    const searchInput = document.getElementById('stockSearch') as HTMLInputElement;
    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
      const query = (e.target as HTMLInputElement).value.trim();
      if (this.searchDebounceTimer) clearTimeout(this.searchDebounceTimer);
      
      if (query.length < 2) {
        document.getElementById('stockSearchResults')!.innerHTML = '';
        return;
      }

      this.searchDebounceTimer = setTimeout(() => this.searchStockItems(query), 300);
    });

    document.getElementById('clearStockSelection')?.addEventListener('click', () => {
      this.clearStockSelection();
    });
  }

  private async searchStockItems(query: string): Promise<void> {
    const resultsContainer = document.getElementById('stockSearchResults');
    if (!resultsContainer) return;

    resultsContainer.innerHTML = '<div class="search-loading">Searching...</div>';

    try {
      const response = await apiService.get<{items: any[]}>(`/tickets/service/stock-items/search?q=${encodeURIComponent(query)}`);
      const data = response as any;
      
      if (response.success && data.items?.length > 0) {
        resultsContainer.innerHTML = data.items.map((item: any) => `
          <div class="stock-result-item" data-item-id="${item.id}" data-item='${JSON.stringify(item).replace(/'/g, "&#39;")}'>
            <div class="stock-item-name">${item.item_name}</div>
            <div class="stock-item-details">
              <span class="stock-code">${item.item_code || ''}</span>
              <span class="stock-price">₹${item.selling_rate || 0}</span>
              <span class="stock-gst">GST: ${item.default_gst_rate || 18}%</span>
            </div>
          </div>
        `).join('');

        resultsContainer.querySelectorAll('.stock-result-item').forEach(el => {
          el.addEventListener('click', () => {
            const itemData = JSON.parse(el.getAttribute('data-item') || '{}');
            this.selectStockItem(itemData);
          });
        });
      } else {
        resultsContainer.innerHTML = '<div class="no-results">No stock items found. Enter custom part name below.</div>';
      }
    } catch (error) {
      resultsContainer.innerHTML = '<div class="search-error">Search failed. Enter part name manually.</div>';
    }
  }

  private selectStockItem(item: any): void {
    this.selectedStockItem = item;
    
    (document.getElementById('spareName') as HTMLInputElement).value = item.item_name || '';
    (document.getElementById('partNumber') as HTMLInputElement).value = item.item_code || '';
    (document.getElementById('estPrice') as HTMLInputElement).value = item.selling_rate || '0';
    (document.getElementById('gstRate') as HTMLInputElement).value = item.default_gst_rate || '18';
    (document.getElementById('hsnCode') as HTMLInputElement).value = item.hsn_code || '';
    
    document.getElementById('stockSearchResults')!.innerHTML = '';
    (document.getElementById('stockSearch') as HTMLInputElement).value = '';
    
    const selectedInfo = document.getElementById('selectedStockInfo');
    const selectedName = document.getElementById('selectedStockName');
    if (selectedInfo && selectedName) {
      selectedName.textContent = `✓ ${item.item_name} (${item.item_code || 'No code'})`;
      selectedInfo.style.display = 'block';
    }

    document.getElementById('clearStockSelection')?.addEventListener('click', () => {
      this.clearStockSelection();
    });
  }

  private clearStockSelection(): void {
    this.selectedStockItem = null;
    const info = document.getElementById('selectedStockInfo');
    if (info) info.style.display = 'none';
    const trySet = (id: string, val: string) => {
      const el = document.getElementById(id) as HTMLInputElement | null;
      if (el) el.value = val;
    };
    trySet('spareName', '');
    trySet('partNumber', '');
    trySet('estPrice', '');
    trySet('gstRate', '18');
    trySet('hsnCode', '');
  }

  private attachModeSwitchHandlers(): void {
    const catalogBtn = document.getElementById('modeCatalogBtn');
    const manualBtn = document.getElementById('modeManualBtn');
    const catalogSection = document.getElementById('catalogModeSection');
    const manualSection = document.getElementById('manualModeSection');

    catalogBtn?.addEventListener('click', () => {
      this.spareMode = 'catalog';
      catalogBtn.className = 'btn btn-sm btn-primary';
      catalogBtn.style.flex = '1';
      if (manualBtn) { manualBtn.className = 'btn btn-sm btn-outline'; manualBtn.style.flex = '1'; }
      if (catalogSection) catalogSection.style.display = '';
      if (manualSection) manualSection.style.display = 'none';
    });

    manualBtn?.addEventListener('click', () => {
      this.spareMode = 'manual';
      manualBtn.className = 'btn btn-sm btn-primary';
      manualBtn.style.flex = '1';
      if (catalogBtn) { catalogBtn.className = 'btn btn-sm btn-outline'; catalogBtn.style.flex = '1'; }
      if (manualSection) manualSection.style.display = '';
      if (catalogSection) catalogSection.style.display = 'none';
    });
  }

  private attachCatalogSearchHandler(): void {
    const searchInput = document.getElementById('catalogSearchInput') as HTMLInputElement;
    const discountSelect = document.getElementById('catalogDiscountSelect') as HTMLSelectElement;

    discountSelect?.addEventListener('change', () => {
      this.catalogDiscountMode = discountSelect.value;
      if (searchInput?.value.trim().length >= 2) {
        this.runCatalogSearch(searchInput.value.trim());
      }
    });

    searchInput?.addEventListener('input', () => {
      const q = searchInput.value.trim();
      if (this.catalogSearchTimer) clearTimeout(this.catalogSearchTimer);
      const resultsEl = document.getElementById('catalogSearchResults');
      if (q.length < 2) { if (resultsEl) resultsEl.innerHTML = ''; return; }
      this.catalogSearchTimer = setTimeout(() => this.runCatalogSearch(q), 350);
    });

    document.getElementById('clearCatalogSelection')?.addEventListener('click', () => {
      this.selectedMarketplaceItem = null;
      const info = document.getElementById('selectedCatalogInfo');
      if (info) info.style.display = 'none';
      const inp = document.getElementById('catalogSearchInput') as HTMLInputElement;
      if (inp) inp.value = '';
      const res = document.getElementById('catalogSearchResults');
      if (res) res.innerHTML = '';
    });
  }

  private async runCatalogSearch(q: string): Promise<void> {
    const resultsEl = document.getElementById('catalogSearchResults');
    if (!resultsEl) return;
    resultsEl.innerHTML = '<div style="padding:6px;font-size:12px;color:#6b7280;">Searching…</div>';
    try {
      const params = new URLSearchParams({ q, limit: '20' });
      if (this.catalogDiscountMode) params.set('discount_mode', this.catalogDiscountMode);
      const res = await apiService.get<any>(`/marketplace/catalog-search?${params}`);
      const items: any[] = Array.isArray(res) ? res : (res.data || res.items || []);
      if (items.length === 0) {
        resultsEl.innerHTML = '<div style="padding:6px;font-size:12px;color:#6b7280;">No results found</div>';
        return;
      }
      resultsEl.innerHTML = items.map((item: any) => {
        const stockBadge = item.available_qty > 0
          ? `<span style="background:#dcfce7;color:#166534;font-size:10px;padding:1px 5px;border-radius:8px;">In Stock (${item.available_qty})</span>`
          : `<span style="background:#fee2e2;color:#991b1b;font-size:10px;padding:1px 5px;border-radius:8px;">Out → ZYPR</span>`;
        const discBadge = item.discount_amount > 0
          ? `<span style="color:#d97706;font-size:10px;margin-left:4px;">-₹${(item.discount_amount || 0).toFixed(0)}</span>` : '';
        return `
          <div class="catalog-result-item" data-id="${item.id}" style="border:1px solid #e5e7eb;border-radius:6px;padding:8px;margin-bottom:4px;cursor:pointer;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <div>
                <div style="font-weight:600;font-size:13px;">${item.name}</div>
                <div style="font-size:11px;color:#6b7280;">${item.sku || ''} · ${item.category_name || ''}</div>
              </div>
              ${stockBadge}
            </div>
            <div style="margin-top:4px;font-size:12px;">
              ₹${(item.final_price || 0).toFixed(2)} incl. GST${discBadge}
            </div>
          </div>
        `;
      }).join('');

      resultsEl.querySelectorAll('.catalog-result-item').forEach(el => {
        el.addEventListener('click', () => {
          const id = parseInt(el.getAttribute('data-id') || '0');
          const item = items.find((i: any) => i.id === id);
          if (!item) return;
          this.selectedMarketplaceItem = item;
          const nameEl = document.getElementById('selectedCatalogName');
          const priceEl = document.getElementById('selectedCatalogPrice');
          const infoEl = document.getElementById('selectedCatalogInfo');
          if (nameEl) nameEl.textContent = `${item.name} (${item.sku || ''})`;
          if (priceEl) priceEl.textContent = `₹${(item.final_price || 0).toFixed(2)} incl. GST · ${item.available_qty > 0 ? `Stock: ${item.available_qty}` : 'Out of stock → ZYPR will be raised'}`;
          if (infoEl) infoEl.style.display = '';
          resultsEl.innerHTML = '';
          (document.getElementById('catalogSearchInput') as HTMLInputElement).value = '';
        });
      });
    } catch {
      resultsEl.innerHTML = '<div style="padding:6px;font-size:12px;color:#dc2626;">Search failed</div>';
    }
  }

  private attachSpareMediaHandlers(): void {
    const imageInput = document.getElementById('spareImages') as HTMLInputElement;
    const videoInput = document.getElementById('spareVideo') as HTMLInputElement;

    imageInput?.addEventListener('change', (e) => {
      const files = Array.from((e.target as HTMLInputElement).files || []);
      if (files.length > 10) {
        this.showToast('Maximum 10 images allowed', 'error');
        imageInput.value = '';
        return;
      }
      if (this.spareVideoFile) {
        this.showToast('Clear video first - upload images OR video', 'error');
        imageInput.value = '';
        return;
      }
      this.spareMediaFiles = files;
      this.renderImagePreviews();
    });

    videoInput?.addEventListener('change', async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      if (this.spareMediaFiles.length > 0) {
        this.showToast('Clear images first - upload images OR video', 'error');
        videoInput.value = '';
        return;
      }

      const video = document.createElement('video');
      video.preload = 'metadata';
      video.src = URL.createObjectURL(file);
      
      video.onloadedmetadata = () => {
        URL.revokeObjectURL(video.src);
        if (video.duration > 180) {
          this.showToast('Video must be under 3 minutes', 'error');
          videoInput.value = '';
          this.spareVideoFile = null;
          return;
        }
        this.spareVideoFile = file;
        this.renderVideoPreview();
      };
    });
  }

  private renderImagePreviews(): void {
    const container = document.getElementById('imagePreviewContainer');
    if (!container) return;

    container.innerHTML = this.spareMediaFiles.map((file, idx) => `
      <div class="media-preview-item">
        <img src="${URL.createObjectURL(file)}" alt="Preview ${idx + 1}">
        <button type="button" class="remove-media" data-idx="${idx}">&times;</button>
      </div>
    `).join('');

    container.querySelectorAll('.remove-media').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const idx = parseInt((e.target as HTMLElement).getAttribute('data-idx') || '0');
        this.spareMediaFiles.splice(idx, 1);
        this.renderImagePreviews();
      });
    });
  }

  private renderVideoPreview(): void {
    const container = document.getElementById('videoPreviewContainer');
    if (!container || !this.spareVideoFile) {
      if (container) container.innerHTML = '';
      return;
    }

    container.innerHTML = `
      <div class="media-preview-item video-preview">
        <video src="${URL.createObjectURL(this.spareVideoFile)}" controls></video>
        <button type="button" class="remove-video">&times;</button>
      </div>
    `;

    container.querySelector('.remove-video')?.addEventListener('click', () => {
      this.spareVideoFile = null;
      (document.getElementById('spareVideo') as HTMLInputElement).value = '';
      this.renderVideoPreview();
    });
  }

  private async submitSparesRequest(): Promise<void> {
    if (!this.selectedTicket) return;

    const spareName = (document.getElementById('spareName') as HTMLInputElement)?.value.trim();
    const partNumber = (document.getElementById('partNumber') as HTMLInputElement)?.value.trim();
    const quantity = parseInt((document.getElementById('quantity') as HTMLInputElement)?.value) || 1;
    const estPrice = parseFloat((document.getElementById('estPrice') as HTMLInputElement)?.value) || 0;
    const gstRate = parseFloat((document.getElementById('gstRate') as HTMLInputElement)?.value) || 18;
    const hsnCode = (document.getElementById('hsnCode') as HTMLInputElement)?.value.trim();
    const notes = (document.getElementById('spareNotes') as HTMLTextAreaElement)?.value.trim();

    const allItems = [...this.pendingSpareItems];

    if (this.spareMode === 'catalog' && this.selectedMarketplaceItem) {
      const item = this.selectedMarketplaceItem;
      allItems.push({
        name: item.name,
        code: item.sku || null,
        quantity,
        estimated_cost: item.final_price || null,
        gst_rate: item.gst_percent || 18,
        hsn_code: item.hsn_code || null,
        notes: notes || null,
        stock_item_id: null,
        marketplace_spare_id: item.id,
        discount_mode: this.catalogDiscountMode || null,
      });
    }

    if (this.spareMode === 'manual' && spareName) {
      allItems.push({
        name: spareName,
        code: partNumber || null,
        quantity: quantity,
        estimated_cost: estPrice || null,
        gst_rate: gstRate,
        hsn_code: hsnCode || null,
        notes: notes || null,
        stock_item_id: this.selectedStockItem?.id || null,
        marketplace_spare_id: null,
        discount_mode: null,
      });
    }

    if (allItems.length === 0) {
      this.showToast('Please add at least one spare part', 'error');
      return;
    }

    try {
      const response = await apiService.post(`/tickets/service/${this.selectedTicket.id}/request-spares`, allItems);

      const data = response as any;
      if (response.success) {
        const spareRequests = data.spare_requests || [];
        
        if (spareRequests.length > 0 && (this.spareMediaFiles.length > 0 || this.spareVideoFile)) {
          await this.uploadSpareMedia(spareRequests[0].id);
        }

        this.showToast(`${allItems.length} spare part(s) requested successfully`);
        this.pendingSpareItems = [];
        this.hideModal();
        await this.loadData();
      } else {
        this.showToast(data.message || response.error || 'Failed to request spares', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to request spares', 'error');
    }
  }

  private async uploadSpareMedia(spareId: number): Promise<void> {
    const formData = new FormData();

    this.spareMediaFiles.forEach((file, idx) => {
      formData.append('images', file);
    });

    if (this.spareVideoFile) {
      formData.append('video', this.spareVideoFile);
    }

    try {
      await apiService.postFormData(`/tickets/service/spare-requests/${spareId}/media`, formData);
    } catch (error) {
      console.error('Failed to upload spare media:', error);
    }
  }

  private async checkSpares(): Promise<void> {
    routerService.navigate('staff-service-procurement');
  }

  private showCompleteModal(): void {
    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="form-section">
          <h5>Complete Service</h5>
          <div class="form-group">
            <label>Resolution Summary *</label>
            <textarea id="resolutionSummary" class="form-textarea" rows="4" placeholder="Describe the work completed..."></textarea>
          </div>
          <div class="form-group">
            <label>Final Labor Charges (₹)</label>
            <input type="number" id="laborCharges" class="form-input" placeholder="0">
          </div>
        </div>
      `;
    }

    if (modalFooter) {
      modalFooter.innerHTML = `
        <button class="btn btn-secondary" id="cancelComplete">Cancel</button>
        <button class="btn btn-success" id="submitComplete">Mark Complete</button>
      `;

      document.getElementById('cancelComplete')?.addEventListener('click', () => {
        this.showTicketDetails(this.selectedTicket!.id);
      });
      document.getElementById('submitComplete')?.addEventListener('click', () => this.submitComplete());
    }
  }

  private async submitComplete(): Promise<void> {
    if (!this.selectedTicket) return;

    const summary = (document.getElementById('resolutionSummary') as HTMLTextAreaElement)?.value.trim();
    const laborCharges = parseFloat((document.getElementById('laborCharges') as HTMLInputElement)?.value) || 0;

    if (!summary) {
      this.showToast('Please enter resolution summary', 'error');
      return;
    }

    try {
      const response = await apiService.post(`/tickets/service/${this.selectedTicket.id}/complete`, {
        resolution_summary: summary,
        labor_charges: laborCharges
      });

      if (response.success) {
        this.showToast('Service marked complete');
        this.hideModal();
        await this.loadData();
      } else {
        this.showToast(response.error || 'Failed to complete', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to complete', 'error');
    }
  }

  private async createBilling(): Promise<void> {
    if (!this.selectedTicket) return;

    try {
      const response = await apiService.post(`/tickets/service/${this.selectedTicket.id}/billing/create`, {});

      if (response.success) {
        this.showToast('Billing created');
        routerService.navigate('staff-service-revenue');
      } else {
        this.showToast(response.error || 'Failed to create billing', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to create billing', 'error');
    }
  }

  private async confirmBilling(): Promise<void> {
    if (!this.selectedTicket) return;

    try {
      const billingRes = await apiService.get<any>(`/tickets/service/${this.selectedTicket.id}/billing`);
      if (billingRes.success && billingRes.data?.id) {
        const response = await apiService.post(`/tickets/service/billing/${billingRes.data.id}/confirm`, {});
        if (response.success) {
          this.showToast('Payment confirmed');
          this.hideModal();
          await this.loadData();
        } else {
          this.showToast(response.error || 'Failed to confirm', 'error');
        }
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to confirm payment', 'error');
    }
  }

  private async closeTicket(): Promise<void> {
    if (!this.selectedTicket) return;
    
    if (!confirm('Are you sure you want to close this ticket?')) return;

    try {
      const response = await apiService.post(`/tickets/service/${this.selectedTicket.id}/close`, {});

      if (response.success) {
        this.showToast('Ticket closed');
        this.hideModal();
        await this.loadData();
      } else {
        this.showToast(response.error || 'Failed to close', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to close', 'error');
    }
  }

  private showUpdatePriorityModal(): void {
    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');

    if (modalBody) {
      const currentPriority = this.selectedTicket?.priority?.toLowerCase() || 'medium';
      modalBody.innerHTML = `
        <div class="form-section">
          <h5>Update Priority</h5>
          <div class="priority-options">
            <label class="priority-option ${currentPriority === 'low' ? 'selected' : ''}">
              <input type="radio" name="priority" value="Low" ${currentPriority === 'low' ? 'checked' : ''}>
              <span class="priority-badge low">Low</span>
            </label>
            <label class="priority-option ${currentPriority === 'medium' ? 'selected' : ''}">
              <input type="radio" name="priority" value="Medium" ${currentPriority === 'medium' ? 'checked' : ''}>
              <span class="priority-badge medium">Medium</span>
            </label>
            <label class="priority-option ${currentPriority === 'high' ? 'selected' : ''}">
              <input type="radio" name="priority" value="High" ${currentPriority === 'high' ? 'checked' : ''}>
              <span class="priority-badge high">High</span>
            </label>
            <label class="priority-option ${currentPriority === 'critical' ? 'selected' : ''}">
              <input type="radio" name="priority" value="Critical" ${currentPriority === 'critical' ? 'checked' : ''}>
              <span class="priority-badge critical">Critical</span>
            </label>
          </div>
        </div>
      `;

      modalBody.querySelectorAll('.priority-option input').forEach(input => {
        input.addEventListener('change', () => {
          modalBody.querySelectorAll('.priority-option').forEach(opt => opt.classList.remove('selected'));
          (input as HTMLInputElement).closest('.priority-option')?.classList.add('selected');
        });
      });
    }

    if (modalFooter) {
      modalFooter.innerHTML = `
        <button class="btn btn-secondary" id="cancelPriority">Cancel</button>
        <button class="btn btn-primary" id="submitPriority">Update</button>
      `;

      document.getElementById('cancelPriority')?.addEventListener('click', () => {
        this.showTicketDetails(this.selectedTicket!.id);
      });
      document.getElementById('submitPriority')?.addEventListener('click', () => this.submitPriorityUpdate());
    }
  }

  private async submitPriorityUpdate(): Promise<void> {
    if (!this.selectedTicket) return;

    const priority = (document.querySelector('input[name="priority"]:checked') as HTMLInputElement)?.value;
    if (!priority) return;

    try {
      const response = await apiService.put(`/tickets/${this.selectedTicket.id}/update`, {
        priority: priority
      });

      if (response.success) {
        this.showToast('Priority updated');
        this.hideModal();
        await this.loadData();
      } else {
        this.showToast(response.error || 'Failed to update', 'error');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to update', 'error');
    }
  }

  private hideModal(): void {
    const modal = document.getElementById('ticketModal');
    if (modal) modal.style.display = 'none';
    this.selectedTicket = null;
  }

  private showToast(message: string, type: 'success' | 'error' = 'success'): void {
    const existing = document.querySelector('.toast-notification');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    const t1 = setTimeout(() => toast.classList.add('show'), 10);
    const t2 = setTimeout(() => {
      toast.classList.remove('show');
      const t3 = setTimeout(() => toast.remove(), 300);
      this.pendingTimers.push(t3);
    }, 3000);
    this.pendingTimers.push(t1, t2);
  }

  cleanup(): void {
    this.pendingTimers.forEach(t => clearTimeout(t));
    this.pendingTimers = [];
    if (this.searchDebounceTimer) {
      clearTimeout(this.searchDebounceTimer);
      this.searchDebounceTimer = null;
    }
  }
}
