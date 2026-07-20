/**
 * MNR My Leads Page
 * DC Protocol: DC_MOBILE_MNR_LEADS_001
 * Full CRM lead management matching web parity
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface Lead {
  id: number;
  name: string;
  phone: string;
  phone_primary_whatsapp: boolean;
  alternate_phone: string;
  email: string;
  category: string;
  category_name: string;
  company: string;
  status: string;
  priority: string;
  created_at: string;
  updated_at: string;
  submit_date?: string | null;
  complete_date?: string | null;
  last_activity: string | null;
  next_followup_date: string | null;
  notes: string | null;
  source: string;
  requirements: string;
  looking_for: string;
  budget_min: number | null;
  budget_max: number | null;
  address: string;
  area: string;
  city: string;
  state: string;
  pincode: string;
}

interface LeadStats {
  my_leads: number;
  assigned_leads: number;
  fresh_leads: number;
  won_deals: number;
}

type TabType = 'my' | 'assigned';

interface Company {
  id: number;
  name: string;
}

export class MNRMyLeads {
  private container: HTMLElement;
  private leads: Lead[] = [];
  private stats: LeadStats = { my_leads: 0, assigned_leads: 0, fresh_leads: 0, won_deals: 0 };
  private loading: boolean = true;
  private activeTab: TabType = 'my';
  private searchQuery: string = '';
  private statusFilter: string = '';
  private priorityFilter: string = '';
  private dateFilter: string = '';
  private roleFilter: string = '';
  private searchTimeout: number | null = null;
  private companies: Company[] = [];
  private selectedCompanyId: number | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadCompanies();
    await this.loadData();
  }

  private async loadCompanies(): Promise<void> {
    try {
      const response = await apiService.get<any>('/crm/my-companies');
      if (response.success && response.data) {
        this.companies = response.data;
      } else {
        this.companies = [
          { id: 1, name: 'MNR' },
          { id: 2, name: 'MyntReal' },
          { id: 3, name: 'VGK Care' }
        ];
      }
    } catch (error) {
      console.error('[MNRMyLeads] Failed to load companies:', error);
      this.companies = [
        { id: 1, name: 'MNR' },
        { id: 2, name: 'MyntReal' },
        { id: 3, name: 'VGK Care' }
      ];
    }
  }

  private async lookupPincode(pincodeInput: HTMLInputElement): Promise<void> {
    const pincode = pincodeInput.value.trim();
    if (!pincode || pincode.length !== 6) return;

    try {
      const response = await fetch(`https://api.postalpincode.in/pincode/${pincode}`);
      const data = await response.json();

      if (data[0]?.Status === 'Success' && data[0]?.PostOffice?.length > 0) {
        const po = data[0].PostOffice[0];
        const areaInput = document.getElementById('leadArea') as HTMLInputElement;
        const cityInput = document.getElementById('leadCity') as HTMLInputElement;
        const stateInput = document.getElementById('leadState') as HTMLInputElement;

        if (areaInput) areaInput.value = po.Name || '';
        if (cityInput) cityInput.value = po.District || '';
        if (stateInput) stateInput.value = po.State || '';
      }
    } catch (error) {
      console.error('[MNRMyLeads] Pincode lookup failed:', error);
    }
  }

  private async loadData(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      await Promise.all([
        this.loadStats(),
        this.loadLeads()
      ]);
    } catch (error) {
      console.error('[MNRMyLeads] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private async loadStats(): Promise<void> {
    try {
      const [myRes, assignedRes] = await Promise.all([
        apiService.get<any>('/crm/unified-my-leads?segment=my&role=mnr'),
        apiService.get<any>('/crm/unified-my-leads?segment=assigned&role=mnr')
      ]);

      const myLeads = myRes.success ? (myRes.data?.leads || myRes.data || []) : [];
      const assignedLeads = assignedRes.success ? (assignedRes.data?.leads || assignedRes.data || []) : [];

      this.stats = {
        my_leads: myLeads.length,
        assigned_leads: assignedLeads.length,
        fresh_leads: 0,
        won_deals: myLeads.filter((l: Lead) => l.status?.toLowerCase() === 'won').length
      };
    } catch (error) {
      console.error('[MNRMyLeads] Stats load failed:', error);
    }
  }

  private async loadLeads(): Promise<void> {
    try {
      const params = new URLSearchParams();
      params.append('segment', this.activeTab);
      params.append('role', 'mnr');
      if (this.selectedCompanyId) params.append('company_id', this.selectedCompanyId.toString());
      if (this.searchQuery) params.append('search', this.searchQuery);
      if (this.statusFilter) params.append('status', this.statusFilter);
      if (this.priorityFilter) params.append('priority', this.priorityFilter);
      if (this.dateFilter) params.append('quick_filter', this.dateFilter);
      if (this.roleFilter) params.append('role_filter', this.roleFilter);

      const response = await apiService.get<any>(`/crm/unified-my-leads?${params.toString()}`);
      
      if (response.success && response.data) {
        const rawLeads = response.data.leads || response.data || [];
        this.leads = rawLeads.map((l: any) => ({
          id: l.id,
          name: l.name || l.lead_name || '',
          phone: l.phone || l.mobile || '',
          phone_primary_whatsapp: l.phone_primary_whatsapp || false,
          alternate_phone: l.alternate_phone || '',
          email: l.email || '',
          category: l.category || l.category_id || '',
          category_name: l.category_name || l.category || 'General',
          company: l.company || l.company_name || '',
          status: l.status || 'new',
          priority: l.priority || 'medium',
          created_at: l.created_at || '',
          updated_at: l.updated_at || l.last_updated || '',
          last_activity: l.last_activity || l.last_followup_date || null,
          next_followup_date: l.next_followup_date || null,
          notes: l.notes || l.description || l.remarks || null,
          source: l.source || 'Direct',
          requirements: l.requirements || '',
          looking_for: l.looking_for || '',
          budget_min: l.budget_min || null,
          budget_max: l.budget_max || null,
          address: l.address || '',
          area: l.area || '',
          city: l.city || '',
          state: l.state || '',
          pincode: l.pincode || ''
        }));
      }
    } catch (error) {
      console.error('[MNRMyLeads] Leads load failed:', error);
    }
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        .leads-page .lead-card { background: rgba(30, 58, 95, 0.5); border-radius: 12px; padding: 14px; margin-bottom: 12px; cursor: pointer; }
        .leads-page .lead-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
        .leads-page .lead-info { flex: 1; }
        .leads-page .lead-name { font-size: 16px; font-weight: 600; color: #e6f1ff; margin: 0 0 4px 0; }
        .leads-page .lead-contact-row { display: flex; align-items: center; gap: 8px; }
        .leads-page .lead-phone-link { color: #10b981; font-size: 14px; text-decoration: none; }
        .leads-page .lead-phone-link:hover { text-decoration: underline; }
        .leads-page .whatsapp-link { color: #25d366; font-size: 16px; text-decoration: none; }
        .leads-page .lead-meta { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 12px; font-size: 12px; color: #a8c0d8; }
        .leads-page .meta-item { background: rgba(255,255,255,0.05); padding: 3px 8px; border-radius: 6px; }
        .leads-page .meta-item.category { color: #60a5fa; }
        .leads-page .meta-item.date { color: #9ca3af; }
        .leads-page .lead-actions { display: flex; gap: 8px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 12px; }
        .leads-page .action-btn { flex: 1; display: flex; align-items: center; justify-content: center; gap: 4px; padding: 10px 8px; border-radius: 8px; font-size: 14px; font-weight: 500; text-decoration: none; border: none; cursor: pointer; }
        .leads-page .action-btn.call { background: rgba(16, 185, 129, 0.15); color: #10b981; }
        .leads-page .action-btn.whatsapp { background: rgba(37, 211, 102, 0.15); color: #25d366; }
        .leads-page .action-btn.view { background: rgba(96, 165, 250, 0.15); color: #60a5fa; }
        .leads-page .action-btn.edit { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }
        .leads-page .status-badge { padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: capitalize; }
        .leads-page .status-badge.new { background: rgba(96, 165, 250, 0.2); color: #60a5fa; }
        .leads-page .status-badge.contacted { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }
        .leads-page .status-badge.interested { background: rgba(16, 185, 129, 0.2); color: #10b981; }
        .leads-page .status-badge.negotiation { background: rgba(168, 85, 247, 0.2); color: #a855f7; }
        .leads-page .status-badge.won { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
        .leads-page .status-badge.lost { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
        .leads-page .priority-badge { padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; text-transform: capitalize; }
        .leads-page .priority-badge.high { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
        .leads-page .priority-badge.medium { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }
        .leads-page .priority-badge.low { background: rgba(107, 114, 128, 0.2); color: #9ca3af; }
        .leads-page .filter-row { display: flex; gap: 8px; margin-top: 10px; }
        .leads-page .filter-select { flex: 1; padding: 10px 12px; background: rgba(30, 58, 95, 0.6); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #e6f1ff; font-size: 13px; }
      </style>
      <div class="page-container leads-page">
        ${PageHeader.render({ 
          title: 'My Leads', 
          showBack: true
        })}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'My Leads', showBack: true });
    
    const addBtn = document.getElementById('btnAddLead');
    if (addBtn) {
      addBtn.addEventListener('click', () => this.showAddLeadModal());
    }
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    content.innerHTML = `
      <style>
        .stats-row { display: flex; gap: 8px; margin-bottom: 16px; padding: 0 4px; }
        .stats-row .stat-item { flex: 1; display: flex; align-items: center; gap: 8px; background: linear-gradient(135deg, rgba(30, 58, 95, 0.8) 0%, rgba(13, 27, 42, 0.9) 100%); padding: 12px 14px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08); }
        .stats-row .stat-item .stat-value { font-size: 22px; font-weight: 700; color: #10b981; min-width: 24px; }
        .stats-row .stat-item .stat-label { font-size: 11px; color: #a8c0d8; text-transform: uppercase; letter-spacing: 0.5px; }
        .stats-row .stat-item.active { border-color: #10b981; background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(4, 120, 87, 0.15) 100%); }
        .company-filter-row { margin-bottom: 12px; }
        .company-filter-row select { width: 100%; padding: 12px 14px; background: rgba(30, 58, 95, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 10px; color: #e6f1ff; font-size: 14px; }
      </style>
      
      <div class="stats-row">
        <div class="stat-item ${this.activeTab === 'my' ? 'active' : ''}" data-tab="my">
          <span class="stat-value">${this.stats.my_leads}</span>
          <span class="stat-label">Total</span>
        </div>
        <div class="stat-item" style="cursor: default;">
          <span class="stat-value" style="color: #22c55e;">${this.stats.won_deals}</span>
          <span class="stat-label">Converted</span>
        </div>
        <div class="stat-item ${this.activeTab === 'assigned' ? 'active' : ''}" data-tab="assigned">
          <span class="stat-value" style="color: #60a5fa;">${this.stats.assigned_leads}</span>
          <span class="stat-label">Active</span>
        </div>
      </div>

      <div class="company-filter-row">
        <select id="companyFilter" class="filter-select">
          <option value="">All Companies</option>
          ${this.companies.map(c => `<option value="${c.id}" ${this.selectedCompanyId === c.id ? 'selected' : ''}>${c.name}</option>`).join('')}
        </select>
      </div>

      <div class="tabs-container">
        <button class="tab-btn ${this.activeTab === 'my' ? 'active' : ''}" data-tab="my">
          <span class="tab-icon">📋</span> My Leads
        </button>
        <button class="tab-btn ${this.activeTab === 'assigned' ? 'active' : ''}" data-tab="assigned">
          <span class="tab-icon">👤</span> Assigned
        </button>
      </div>

      <div class="filters-section">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" id="leadSearch" placeholder="Search leads..." value="${this.searchQuery}">
        </div>
        <div class="filter-row">
          <select id="dateFilter" class="filter-select">
            <option value="">All Leads</option>
            <option value="today" ${this.dateFilter === 'today' ? 'selected' : ''}>Today's Leads</option>
            <option value="overdue" ${this.dateFilter === 'overdue' ? 'selected' : ''}>Overdue</option>
            <option value="followup_today" ${this.dateFilter === 'followup_today' ? 'selected' : ''}>Follow-up Today</option>
            <option value="this_week" ${this.dateFilter === 'this_week' ? 'selected' : ''}>This Week</option>
            <option value="future" ${this.dateFilter === 'future' ? 'selected' : ''}>Future Leads</option>
          </select>
          <select id="roleFilter" class="filter-select">
            <option value="">All Roles</option>
            <option value="primary_holder" ${this.roleFilter === 'primary_holder' ? 'selected' : ''}>As Primary Holder</option>
            <option value="handler" ${this.roleFilter === 'handler' ? 'selected' : ''}>As Handler</option>
          </select>
        </div>
        <div class="filter-row">
          <select id="statusFilter" class="filter-select">
            <option value="">All Status</option>
            <option value="new" ${this.statusFilter === 'new' ? 'selected' : ''}>New</option>
            <option value="contacted" ${this.statusFilter === 'contacted' ? 'selected' : ''}>Contacted</option>
            <option value="interested" ${this.statusFilter === 'interested' ? 'selected' : ''}>Interested</option>
            <option value="negotiation" ${this.statusFilter === 'negotiation' ? 'selected' : ''}>Negotiation</option>
            <option value="won" ${this.statusFilter === 'won' ? 'selected' : ''}>Won</option>
            <option value="lost" ${this.statusFilter === 'lost' ? 'selected' : ''}>Lost</option>
          </select>
        </div>
      </div>

      <div class="leads-list">
        ${this.leads.length === 0 ? `
          <div class="empty-state card">
            <div class="empty-icon">👥</div>
            <h3>No leads found</h3>
            <p>${this.getEmptyMessage()}</p>
            ${this.activeTab === 'my' ? `
              <button class="btn-primary" id="btnAddLeadEmpty">+ Add Lead</button>
            ` : ''}
          </div>
        ` : this.leads.map(lead => this.renderLeadCard(lead)).join('')}
      </div>
    `;

    this.attachEventListeners();
  }

  private renderLeadCard(lead: Lead): string {
    const statusClass = lead.status.toLowerCase().replace(/\s+/g, '-');
    const priorityClass = lead.priority.toLowerCase();
    const date = this.formatDate(lead.updated_at || lead.created_at);
    const phone = lead.phone || '';
    const whatsappNumber = phone.replace(/\D/g, '');

    return `
      <div class="lead-card card" data-lead-id="${lead.id}">
        <div class="lead-header" data-action="view" data-id="${lead.id}">
          <div class="lead-info">
            <h4 class="lead-name">${lead.name}</h4>
            <div class="lead-contact-row">
              <a href="tel:${phone}" class="lead-phone-link" onclick="event.stopPropagation()">${phone || 'No phone'}</a>
              ${phone ? `<a href="https://wa.me/91${whatsappNumber}" class="whatsapp-link" target="_blank" onclick="event.stopPropagation()">💬</a>` : ''}
            </div>
          </div>
          <span class="status-badge ${statusClass}">${lead.status}</span>
        </div>
        <div class="lead-meta" data-action="view" data-id="${lead.id}">
          <span class="meta-item category">${lead.category_name || 'General'}</span>
          <span class="priority-badge ${priorityClass}">${lead.priority}</span>
          <span class="meta-item date">${date}</span>
          ${lead.submit_date ? `<span class="meta-item" style="font-size:10px;color:#6b7280">📤 ${this.formatDate(lead.submit_date)}</span>` : ''}
          ${lead.complete_date ? `<span class="meta-item" style="font-size:10px;color:#059669">✅ ${this.formatDate(lead.complete_date)}</span>` : ''}
        </div>
        <div class="lead-actions">
          <a href="tel:${phone}" class="action-btn call" onclick="event.stopPropagation()">
            <span>📞</span>
          </a>
          <a href="https://wa.me/91${whatsappNumber}" class="action-btn whatsapp" target="_blank" onclick="event.stopPropagation()">
            <span>💬</span>
          </a>
          <button class="action-btn view" data-action="view" data-id="${lead.id}">
            <span>👁</span>
          </button>
          <button class="action-btn edit" data-action="edit" data-id="${lead.id}">
            <span>✏️</span>
          </button>
        </div>
      </div>
    `;
  }

  private attachEventListeners(): void {
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.activeTab = btn.getAttribute('data-tab') as TabType;
        this.loadLeads().then(() => this.updateContent());
      });
    });

    document.querySelectorAll('.stat-item[data-tab]').forEach(item => {
      item.addEventListener('click', () => {
        const tab = item.getAttribute('data-tab') as TabType;
        if (tab) {
          this.activeTab = tab;
          this.loadLeads().then(() => this.updateContent());
        }
      });
    });

    const companySelect = document.getElementById('companyFilter') as HTMLSelectElement;
    if (companySelect) {
      companySelect.addEventListener('change', () => {
        this.selectedCompanyId = companySelect.value ? parseInt(companySelect.value) : null;
        this.loadLeads().then(() => this.updateContent());
      });
    }

    const searchInput = document.getElementById('leadSearch') as HTMLInputElement;
    if (searchInput) {
      searchInput.addEventListener('input', () => {
        if (this.searchTimeout) clearTimeout(this.searchTimeout);
        this.searchTimeout = window.setTimeout(() => {
          this.searchQuery = searchInput.value;
          this.loadLeads().then(() => this.updateContent());
        }, 300);
      });
    }

    const statusSelect = document.getElementById('statusFilter') as HTMLSelectElement;
    if (statusSelect) {
      statusSelect.addEventListener('change', () => {
        this.statusFilter = statusSelect.value;
        this.loadLeads().then(() => this.updateContent());
      });
    }

    const prioritySelect = document.getElementById('priorityFilter') as HTMLSelectElement;
    if (prioritySelect) {
      prioritySelect.addEventListener('change', () => {
        this.priorityFilter = prioritySelect.value;
        this.loadLeads().then(() => this.updateContent());
      });
    }

    const dateSelect = document.getElementById('dateFilter') as HTMLSelectElement;
    if (dateSelect) {
      dateSelect.addEventListener('change', () => {
        this.dateFilter = dateSelect.value;
        this.loadLeads().then(() => this.updateContent());
      });
    }

    const roleSelect = document.getElementById('roleFilter') as HTMLSelectElement;
    if (roleSelect) {
      roleSelect.addEventListener('change', () => {
        this.roleFilter = roleSelect.value;
        this.loadLeads().then(() => this.updateContent());
      });
    }

    document.querySelectorAll('.lead-card').forEach(card => {
      card.addEventListener('click', (e) => {
        const target = e.target as HTMLElement;
        if (target.closest('a') || target.closest('.action-btn')) return;
        const id = card.getAttribute('data-lead-id');
        if (id) this.viewLeadDetails(parseInt(id));
      });
    });

    document.querySelectorAll('.action-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const action = btn.getAttribute('data-action');
        const id = btn.getAttribute('data-id');
        if (action === 'view' && id) {
          this.viewLeadDetails(parseInt(id));
        } else if (action === 'edit' && id) {
          this.showEditLeadModal(parseInt(id));
        }
      });
    });

    const addLeadEmpty = document.getElementById('btnAddLeadEmpty');
    if (addLeadEmpty) {
      addLeadEmpty.addEventListener('click', () => this.showAddLeadModal());
    }
  }

  private getEmptyMessage(): string {
    switch (this.activeTab) {
      case 'my': return 'Add your first lead to get started';
      case 'assigned': return 'No leads have been assigned to you';
      default: return 'No leads found';
    }
  }

  private async showAddLeadModal(): Promise<void> {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.id = 'addLeadModal';
    modal.innerHTML = `
      <style>
        #addLeadModal {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.7);
          backdrop-filter: blur(4px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 9999;
          padding: 16px;
        }
        #addLeadModal .modal-content {
          max-height: 90vh;
          width: 100%;
          max-width: 420px;
          background: linear-gradient(180deg, #1e3a5f 0%, #0d1b2a 100%);
          border-radius: 20px;
          display: flex;
          flex-direction: column;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.1);
          animation: slideUp 0.3s ease-out;
        }
        @keyframes slideUp {
          from { transform: translateY(30px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        #addLeadModal .modal-header {
          background: linear-gradient(135deg, #10b981 0%, #047857 100%);
          padding: 20px 24px;
          border-radius: 20px 20px 0 0;
          display: flex;
          justify-content: space-between;
          align-items: center;
          position: relative;
          overflow: hidden;
        }
        #addLeadModal .modal-header::before {
          content: '';
          position: absolute;
          top: -50%;
          right: -20%;
          width: 100px;
          height: 100px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 50%;
        }
        #addLeadModal .modal-header h3 {
          margin: 0;
          color: white;
          font-size: 20px;
          font-weight: 700;
          display: flex;
          align-items: center;
          gap: 10px;
          position: relative;
          z-index: 1;
        }
        #addLeadModal .modal-header h3 .icon {
          width: 36px;
          height: 36px;
          background: rgba(255, 255, 255, 0.2);
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 18px;
        }
        #addLeadModal .modal-close {
          background: rgba(255, 255, 255, 0.2);
          border: none;
          color: white;
          width: 36px;
          height: 36px;
          border-radius: 10px;
          font-size: 22px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
          position: relative;
          z-index: 1;
        }
        #addLeadModal .modal-close:hover {
          background: rgba(255, 255, 255, 0.3);
          transform: scale(1.05);
        }
        #addLeadModal .modal-body {
          padding: 24px;
          overflow-y: auto;
          flex: 1;
          max-height: calc(90vh - 180px);
        }
        #addLeadModal .modal-body::-webkit-scrollbar {
          width: 6px;
        }
        #addLeadModal .modal-body::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 3px;
        }
        #addLeadModal .modal-body::-webkit-scrollbar-thumb {
          background: rgba(16, 185, 129, 0.5);
          border-radius: 3px;
        }
        #addLeadModal .form-section {
          margin-bottom: 20px;
        }
        #addLeadModal .section-title {
          font-size: 12px;
          font-weight: 600;
          color: #10b981;
          text-transform: uppercase;
          letter-spacing: 1px;
          margin-bottom: 12px;
          padding-bottom: 8px;
          border-bottom: 1px solid rgba(16, 185, 129, 0.2);
          display: flex;
          align-items: center;
          gap: 8px;
        }
        #addLeadModal .form-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 14px;
        }
        #addLeadModal .form-group {
          margin-bottom: 16px;
        }
        #addLeadModal .form-group.full-width {
          grid-column: 1 / -1;
        }
        #addLeadModal .form-group label {
          display: flex;
          align-items: center;
          gap: 6px;
          color: #a8c0d8;
          font-size: 13px;
          font-weight: 500;
          margin-bottom: 8px;
        }
        #addLeadModal .form-group label .field-icon {
          font-size: 14px;
          opacity: 0.8;
        }
        #addLeadModal .form-group label .required {
          color: #f87171;
          font-weight: bold;
        }
        #addLeadModal .input-wrapper {
          position: relative;
        }
        #addLeadModal .form-group input,
        #addLeadModal .form-group select,
        #addLeadModal .form-group textarea {
          width: 100%;
          padding: 14px 16px;
          border-radius: 12px;
          border: 2px solid rgba(255, 255, 255, 0.08);
          background: rgba(13, 27, 42, 0.6);
          color: #e6f1ff;
          font-size: 15px;
          transition: all 0.2s;
          box-sizing: border-box;
        }
        #addLeadModal .form-group input::placeholder,
        #addLeadModal .form-group textarea::placeholder {
          color: rgba(168, 192, 216, 0.5);
        }
        #addLeadModal .form-group input:focus,
        #addLeadModal .form-group select:focus,
        #addLeadModal .form-group textarea:focus {
          outline: none;
          border-color: #10b981;
          background: rgba(16, 185, 129, 0.08);
          box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
        }
        #addLeadModal .form-group select {
          appearance: none;
          background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%2310b981' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
          background-repeat: no-repeat;
          background-position: right 14px center;
          padding-right: 40px;
          cursor: pointer;
        }
        #addLeadModal .form-group select option {
          background: #1e3a5f;
          color: #e6f1ff;
          padding: 10px;
        }
        #addLeadModal .checkbox-row {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-top: 10px;
          padding: 10px 14px;
          background: rgba(16, 185, 129, 0.08);
          border-radius: 8px;
          border: 1px solid rgba(16, 185, 129, 0.2);
        }
        #addLeadModal .checkbox-row input[type="checkbox"] {
          width: 20px;
          height: 20px;
          accent-color: #10b981;
          cursor: pointer;
        }
        #addLeadModal .checkbox-row label {
          color: #a8c0d8;
          font-size: 13px;
          margin: 0;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        #addLeadModal .checkbox-row label .whatsapp-icon {
          color: #25D366;
        }
        #addLeadModal .form-group textarea {
          resize: vertical;
          min-height: 80px;
        }
        #addLeadModal .modal-footer {
          padding: 20px 24px;
          border-top: 1px solid rgba(255, 255, 255, 0.08);
          display: flex;
          gap: 12px;
          justify-content: stretch;
          flex-shrink: 0;
          background: rgba(13, 27, 42, 0.5);
          border-radius: 0 0 20px 20px;
        }
        #addLeadModal .btn-cancel {
          flex: 1;
          padding: 16px 20px;
          background: rgba(255, 255, 255, 0.08);
          border: 2px solid rgba(255, 255, 255, 0.15);
          color: #a8c0d8;
          border-radius: 12px;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        }
        #addLeadModal .btn-cancel:hover {
          background: rgba(255, 255, 255, 0.12);
          border-color: rgba(255, 255, 255, 0.25);
        }
        #addLeadModal .btn-submit {
          flex: 1.5;
          padding: 16px 20px;
          background: linear-gradient(135deg, #10b981 0%, #047857 100%);
          border: none;
          color: white;
          border-radius: 12px;
          font-size: 15px;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.2s;
          box-shadow: 0 4px 15px rgba(16, 185, 129, 0.35);
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }
        #addLeadModal .btn-submit:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(16, 185, 129, 0.45);
        }
        #addLeadModal .btn-submit:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          transform: none;
          box-shadow: none;
        }
        #addLeadModal .priority-options {
          display: flex;
          gap: 10px;
        }
        #addLeadModal .priority-option {
          flex: 1;
          padding: 12px;
          border-radius: 10px;
          border: 2px solid rgba(255, 255, 255, 0.1);
          background: rgba(13, 27, 42, 0.4);
          cursor: pointer;
          text-align: center;
          transition: all 0.2s;
        }
        #addLeadModal .priority-option:hover {
          border-color: rgba(255, 255, 255, 0.2);
        }
        #addLeadModal .priority-option.selected {
          border-color: var(--priority-color);
          background: var(--priority-bg);
        }
        #addLeadModal .priority-option.high { --priority-color: #ef4444; --priority-bg: rgba(239, 68, 68, 0.15); }
        #addLeadModal .priority-option.medium { --priority-color: #f59e0b; --priority-bg: rgba(245, 158, 11, 0.15); }
        #addLeadModal .priority-option.low { --priority-color: #10b981; --priority-bg: rgba(16, 185, 129, 0.15); }
        #addLeadModal .priority-option .priority-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          margin: 0 auto 6px;
        }
        #addLeadModal .priority-option.high .priority-dot { background: #ef4444; }
        #addLeadModal .priority-option.medium .priority-dot { background: #f59e0b; }
        #addLeadModal .priority-option.low .priority-dot { background: #10b981; }
        #addLeadModal .priority-option .priority-label {
          font-size: 13px;
          font-weight: 600;
          color: #a8c0d8;
        }
        #addLeadModal .priority-option.selected .priority-label {
          color: var(--priority-color);
        }
      </style>
      <div class="modal-content">
        <div class="modal-header">
          <h3><span class="icon">+</span> Add New Lead</h3>
          <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-section">
            <div class="section-title"><span>1</span> Basic Information</div>
            <div class="form-row">
              <div class="form-group">
                <label><span class="field-icon">*</span> Name <span class="required">*</span></label>
                <input type="text" id="leadName" placeholder="Full name" required>
              </div>
              <div class="form-group">
                <label><span class="field-icon">@</span> Email</label>
                <input type="email" id="leadEmail" placeholder="email@example.com">
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title"><span>2</span> Contact Details</div>
            <div class="form-group">
              <label><span class="field-icon">#</span> Mobile Number <span class="required">*</span></label>
              <input type="tel" id="leadMobile" placeholder="10-digit mobile number" required maxlength="10" inputmode="numeric">
              <div class="checkbox-row">
                <input type="checkbox" id="leadPhoneWhatsapp" checked>
                <label for="leadPhoneWhatsapp"><span class="whatsapp-icon">W</span> WhatsApp Available</label>
              </div>
            </div>
            <div class="form-group">
              <label><span class="field-icon">#</span> Alternate Mobile</label>
              <input type="tel" id="leadMobileSecondary" placeholder="Alternate number (optional)" maxlength="10" inputmode="numeric">
              <div class="checkbox-row">
                <input type="checkbox" id="leadPhoneSecondaryWhatsapp">
                <label for="leadPhoneSecondaryWhatsapp"><span class="whatsapp-icon">W</span> WhatsApp Available</label>
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title"><span>3</span> Lead Classification</div>
            <div class="form-row">
              <div class="form-group">
                <label><span class="field-icon">B</span> Company <span class="required">*</span></label>
                <select id="leadCompany" required>
                  <option value="">Select company...</option>
                  ${this.companies.map(c => `<option value="${c.id}">${c.name}</option>`).join('')}
                </select>
              </div>
              <div class="form-group">
                <label><span class="field-icon">T</span> Category</label>
                <select id="leadCategory">
                  <option value="">Select category...</option>
                  <option value="ev">EV</option>
                  <option value="real_estate">Real Estate</option>
                  <option value="insurance">Insurance</option>
                  <option value="franchise">Franchise</option>
                  <option value="solar">Solar</option>
                  <option value="general">General</option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label><span class="field-icon">S</span> Lead Source</label>
                <select id="leadSource">
                  <option value="">Select source...</option>
                  <option value="referral">Referral</option>
                  <option value="website">Website</option>
                  <option value="social_media">Social Media</option>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="direct">Direct</option>
                  <option value="event">Event</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div class="form-group">
                <label><span class="field-icon">!</span> Priority</label>
                <select id="leadPriority">
                  <option value="medium">Normal</option>
                  <option value="high">High</option>
                  <option value="low">Low</option>
                </select>
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title"><span>4</span> Requirements & Budget</div>
            <div class="form-group">
              <label><span class="field-icon">L</span> Looking For</label>
              <input type="text" id="leadLookingFor" placeholder="What is the lead looking for?">
            </div>
            <div class="form-group">
              <label><span class="field-icon">R</span> Requirements</label>
              <textarea id="leadRequirements" placeholder="Detailed requirements..." rows="2"></textarea>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label><span class="field-icon">₹</span> Budget Min</label>
                <input type="number" id="leadBudgetMin" placeholder="Min budget" inputmode="numeric">
              </div>
              <div class="form-group">
                <label><span class="field-icon">₹</span> Budget Max</label>
                <input type="number" id="leadBudgetMax" placeholder="Max budget" inputmode="numeric">
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title"><span>5</span> Location Details</div>
            <div class="form-group">
              <label><span class="field-icon">#</span> Pincode <span style="font-size:10px;color:#10b981;">(Auto-detect)</span></label>
              <div style="display:flex;gap:8px;">
                <input type="text" id="leadPincode" placeholder="6-digit PIN" maxlength="6" inputmode="numeric" style="flex:1;">
                <button type="button" id="btnLookupPincode" style="padding:10px 14px;background:rgba(16,185,129,0.2);border:1px solid #10b981;color:#10b981;border-radius:10px;font-size:12px;cursor:pointer;">Lookup</button>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label><span class="field-icon">A</span> Area</label>
                <input type="text" id="leadArea" placeholder="Area/Locality">
              </div>
              <div class="form-group">
                <label><span class="field-icon">C</span> City</label>
                <input type="text" id="leadCity" placeholder="City">
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label><span class="field-icon">S</span> State</label>
                <input type="text" id="leadState" placeholder="State">
              </div>
              <div class="form-group">
                <label><span class="field-icon">P</span> Address</label>
                <input type="text" id="leadAddress" placeholder="Street address">
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title"><span>6</span> Follow-up & Notes</div>
            <div class="form-row">
              <div class="form-group">
                <label><span class="field-icon">D</span> Expected Close Date</label>
                <input type="date" id="leadExpectedCloseDate">
              </div>
              <div class="form-group">
                <label><span class="field-icon">F</span> Next Follow-up</label>
                <input type="date" id="leadNextFollowupDate">
              </div>
            </div>
            <div class="form-group">
              <label><span class="field-icon">T</span> Tags</label>
              <input type="text" id="leadTags" placeholder="Comma separated tags">
            </div>
            <div class="form-group">
              <label><span class="field-icon">N</span> Notes</label>
              <textarea id="leadNotes" placeholder="Additional notes or requirements..." rows="3"></textarea>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" id="btnCancelLead">Cancel</button>
          <button class="btn-submit" id="btnSaveLead"><span>+</span> Create Lead</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // DC Protocol: Apply styles via JavaScript to bypass WebView CSS parsing issues
    this.applyModalStyles(modal);

    modal.querySelector('.modal-close')?.addEventListener('click', () => modal.remove());
    modal.querySelector('#btnCancelLead')?.addEventListener('click', () => modal.remove());
    modal.querySelector('#btnSaveLead')?.addEventListener('click', () => this.saveLead(modal));
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.remove();
    });

    const pincodeInput = modal.querySelector('#leadPincode') as HTMLInputElement;
    const lookupBtn = modal.querySelector('#btnLookupPincode') as HTMLButtonElement;
    if (pincodeInput) {
      if (lookupBtn) {
        lookupBtn.addEventListener('click', () => this.lookupPincode(pincodeInput));
      }
      pincodeInput.addEventListener('input', () => {
        if (pincodeInput.value.length === 6) {
          this.lookupPincode(pincodeInput);
        }
      });
    }
  }

  private applyModalStyles(modal: HTMLElement): void {
    // Modal overlay
    Object.assign(modal.style, {
      position: 'fixed', top: '0', left: '0', right: '0', bottom: '0',
      background: 'rgba(0, 0, 0, 0.7)', backdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: '9999', padding: '16px'
    });

    // Modal content
    const content = modal.querySelector('.modal-content') as HTMLElement;
    if (content) {
      Object.assign(content.style, {
        maxHeight: '90vh', width: '100%', maxWidth: '420px',
        background: 'linear-gradient(180deg, #1e3a5f 0%, #0d1b2a 100%)',
        borderRadius: '20px', padding: '0', display: 'flex', flexDirection: 'column',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5)'
      });
    }

    // Modal header
    const header = modal.querySelector('.modal-header') as HTMLElement;
    if (header) {
      Object.assign(header.style, {
        background: 'linear-gradient(135deg, #10b981 0%, #047857 100%)',
        padding: '20px 24px', borderRadius: '20px 20px 0 0',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center'
      });
    }

    // Header title
    const headerTitle = modal.querySelector('.modal-header h3') as HTMLElement;
    if (headerTitle) {
      Object.assign(headerTitle.style, {
        margin: '0', color: 'white', fontSize: '20px', fontWeight: '700',
        display: 'flex', alignItems: 'center', gap: '10px'
      });
    }

    // Close button
    const closeBtn = modal.querySelector('.modal-close') as HTMLElement;
    if (closeBtn) {
      Object.assign(closeBtn.style, {
        background: 'rgba(255, 255, 255, 0.2)', border: 'none', color: 'white',
        width: '36px', height: '36px', borderRadius: '10px', fontSize: '22px',
        cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center'
      });
    }

    // Modal body
    const body = modal.querySelector('.modal-body') as HTMLElement;
    if (body) {
      Object.assign(body.style, {
        padding: '24px', overflowY: 'auto', flex: '1', maxHeight: 'calc(90vh - 180px)'
      });
    }

    // Section titles
    modal.querySelectorAll('.section-title').forEach((el) => {
      Object.assign((el as HTMLElement).style, {
        fontSize: '12px', fontWeight: '600', color: '#10b981',
        textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px',
        paddingBottom: '8px', borderBottom: '1px solid rgba(16, 185, 129, 0.2)'
      });
    });

    // Form groups
    modal.querySelectorAll('.form-group').forEach((el) => {
      Object.assign((el as HTMLElement).style, { marginBottom: '16px' });
    });

    // Labels
    modal.querySelectorAll('.form-group label').forEach((el) => {
      Object.assign((el as HTMLElement).style, {
        display: 'flex', alignItems: 'center', gap: '6px', color: '#a8c0d8',
        fontSize: '13px', fontWeight: '500', marginBottom: '8px'
      });
    });

    // Inputs, selects, textareas
    modal.querySelectorAll('input, select, textarea').forEach((el) => {
      Object.assign((el as HTMLElement).style, {
        width: '100%', padding: '14px 16px', borderRadius: '12px',
        border: '2px solid rgba(255, 255, 255, 0.08)',
        background: 'rgba(13, 27, 42, 0.6)', color: '#e6f1ff', fontSize: '15px',
        boxSizing: 'border-box'
      });
    });

    // Form rows
    modal.querySelectorAll('.form-row').forEach((el) => {
      Object.assign((el as HTMLElement).style, {
        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px'
      });
    });

    // Modal footer
    const footer = modal.querySelector('.modal-footer') as HTMLElement;
    if (footer) {
      Object.assign(footer.style, {
        padding: '20px 24px', borderTop: '1px solid rgba(255, 255, 255, 0.08)',
        display: 'flex', gap: '12px', background: 'rgba(13, 27, 42, 0.5)',
        borderRadius: '0 0 20px 20px'
      });
    }

    // Cancel button
    const cancelBtn = modal.querySelector('.btn-cancel') as HTMLElement;
    if (cancelBtn) {
      Object.assign(cancelBtn.style, {
        flex: '1', padding: '16px 20px', background: 'rgba(255, 255, 255, 0.08)',
        border: '2px solid rgba(255, 255, 255, 0.15)', color: '#a8c0d8',
        borderRadius: '12px', fontSize: '15px', fontWeight: '600', cursor: 'pointer'
      });
    }

    // Submit button
    const submitBtn = modal.querySelector('.btn-submit') as HTMLElement;
    if (submitBtn) {
      Object.assign(submitBtn.style, {
        flex: '1.5', padding: '16px 20px',
        background: 'linear-gradient(135deg, #10b981 0%, #047857 100%)',
        border: 'none', color: 'white', borderRadius: '12px', fontSize: '15px',
        fontWeight: '700', cursor: 'pointer', boxShadow: '0 4px 15px rgba(16, 185, 129, 0.35)'
      });
    }
  }

  private async saveLead(modal: HTMLElement): Promise<void> {
    // Get all form field values
    const name = (document.getElementById('leadName') as HTMLInputElement)?.value?.trim();
    const phone = (document.getElementById('leadMobile') as HTMLInputElement)?.value?.trim();
    const email = (document.getElementById('leadEmail') as HTMLInputElement)?.value?.trim();
    const categoryId = (document.getElementById('leadCategory') as HTMLSelectElement)?.value;
    const priority = (document.getElementById('leadPriority') as HTMLSelectElement)?.value;
    const description = (document.getElementById('leadNotes') as HTMLTextAreaElement)?.value?.trim();
    const companyId = (document.getElementById('leadCompany') as HTMLSelectElement)?.value;
    const source = (document.getElementById('leadSource') as HTMLSelectElement)?.value;
    const alternatePhone = (document.getElementById('leadMobileSecondary') as HTMLInputElement)?.value?.trim();
    const address = (document.getElementById('leadAddress') as HTMLInputElement)?.value?.trim();
    const phonePrimaryWhatsapp = (document.getElementById('leadPhoneWhatsapp') as HTMLInputElement)?.checked;
    const phoneSecondaryWhatsapp = (document.getElementById('leadPhoneSecondaryWhatsapp') as HTMLInputElement)?.checked;
    
    // Additional fields from web version
    const requirements = (document.getElementById('leadRequirements') as HTMLTextAreaElement)?.value?.trim();
    const lookingFor = (document.getElementById('leadLookingFor') as HTMLInputElement)?.value?.trim();
    const budgetMin = (document.getElementById('leadBudgetMin') as HTMLInputElement)?.value;
    const budgetMax = (document.getElementById('leadBudgetMax') as HTMLInputElement)?.value;
    const area = (document.getElementById('leadArea') as HTMLInputElement)?.value?.trim();
    const city = (document.getElementById('leadCity') as HTMLInputElement)?.value?.trim();
    const state = (document.getElementById('leadState') as HTMLInputElement)?.value?.trim();
    const pincode = (document.getElementById('leadPincode') as HTMLInputElement)?.value?.trim();
    const expectedCloseDate = (document.getElementById('leadExpectedCloseDate') as HTMLInputElement)?.value;
    const nextFollowupDate = (document.getElementById('leadNextFollowupDate') as HTMLInputElement)?.value;
    const tags = (document.getElementById('leadTags') as HTMLInputElement)?.value?.trim();

    if (!name || !phone) {
      alert('Please enter name and mobile number');
      return;
    }

    if (phone.length !== 10 || !/^\d{10}$/.test(phone)) {
      alert('Please enter a valid 10-digit mobile number');
      return;
    }

    const submitBtn = document.getElementById('btnSaveLead') as HTMLButtonElement;
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Creating...';
    }

    try {
      // Build payload with correct API field names matching LeadCreate schema
      const payload: any = {
        name,
        phone,  // API expects 'phone' not 'mobile'
        email: email || null,
        category_id: categoryId ? parseInt(categoryId) : null,
        priority: priority || 'medium',
        status: 'new',
        description: description || null,  // API expects 'description' not 'notes'
        source: source || 'mobile_app',
        phone_primary_whatsapp: phonePrimaryWhatsapp || false,
        alternate_phone: alternatePhone || null,  // API expects 'alternate_phone' not 'mobile_secondary'
        phone_secondary_whatsapp: phoneSecondaryWhatsapp || false,
        address: address || null,
        requirements: requirements || null,
        looking_for: lookingFor || null,
        budget_min: budgetMin ? parseFloat(budgetMin) : null,
        budget_max: budgetMax ? parseFloat(budgetMax) : null,
        area: area || null,
        city: city || null,
        state: state || null,
        pincode: pincode || null,
        expected_close_date: expectedCloseDate || null,
        next_followup_date: nextFollowupDate || null,
        tags: tags || null
      };

      // Only add company_id if explicitly selected (API will default to MNR company for members)
      if (companyId && parseInt(companyId) > 0) {
        payload.company_id = parseInt(companyId);
      }

      const response = await apiService.post<any>('/crm/unified-my-leads?role=mnr', payload);

      if (response.success) {
        modal.remove();
        alert('Lead added successfully!');
        await this.loadData();
      } else {
        alert(response.error || 'Failed to add lead');
      }
    } catch (error: any) {
      console.error('[MNRMyLeads] Add lead failed:', error);
      alert(error.message || 'Failed to add lead. Please try again.');
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Lead';
      }
    }
  }


  private async viewLeadDetails(leadId: number): Promise<void> {
    try {
      const response = await apiService.get<any>(`/crm/unified-my-leads/${leadId}/details?role=mnr`);
      
      if (response.success && response.data) {
        const lead = response.data;
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
          <div class="modal-content lead-details-modal">
            <div class="modal-header">
              <h3>Lead Details</h3>
              <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body">
              <div class="lead-detail-section">
                <h4>${lead.name}</h4>
                <p class="lead-status-large ${lead.status?.toLowerCase()}">${lead.status}</p>
              </div>
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="label">Mobile</span>
                  <span class="value">${lead.phone || 'N/A'}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Email</span>
                  <span class="value">${lead.email || 'N/A'}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Category</span>
                  <span class="value">${lead.category_name || lead.category || 'General'}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Priority</span>
                  <span class="value priority-${lead.priority?.toLowerCase()}">${lead.priority || 'Medium'}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Source</span>
                  <span class="value">${lead.source || 'Direct'}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Created</span>
                  <span class="value">${this.formatDate(lead.created_at)}</span>
                </div>
              </div>
              ${lead.notes ? `
                <div class="notes-section">
                  <h5>Notes</h5>
                  <p>${lead.notes}</p>
                </div>
              ` : ''}
            </div>
            <div class="modal-footer">
              <a href="tel:${lead.phone}" class="btn-primary">📞 Call</a>
              <button class="btn-warning" id="btnEditLead" data-id="${lead.id}">✏️ Edit</button>
              <button class="btn-secondary modal-close-btn">Close</button>
            </div>
          </div>
        `;

        document.body.appendChild(modal);
        modal.querySelector('.modal-close')?.addEventListener('click', () => modal.remove());
        modal.querySelector('.modal-close-btn')?.addEventListener('click', () => modal.remove());
        modal.querySelector('#btnEditLead')?.addEventListener('click', () => {
          modal.remove();
          this.showEditLeadModal(lead);
        });
        modal.addEventListener('click', (e) => {
          if (e.target === modal) modal.remove();
        });
      }
    } catch (error) {
      console.error('[MNRMyLeads] View details failed:', error);
    }
  }

  private async showEditLeadModal(lead: any): Promise<void> {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
      <div class="modal-content">
        <div class="modal-header">
          <h3>Update Lead Status</h3>
          <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
          <div class="lead-info-summary">
            <strong>${lead.name}</strong>
            <p>${lead.phone || 'No mobile'}</p>
          </div>
          <div class="form-group">
            <label>Status</label>
            <select id="editLeadStatus">
              <option value="new" ${lead.status === 'new' ? 'selected' : ''}>New</option>
              <option value="contacted" ${lead.status === 'contacted' ? 'selected' : ''}>Contacted</option>
              <option value="interested" ${lead.status === 'interested' ? 'selected' : ''}>Interested</option>
              <option value="negotiation" ${lead.status === 'negotiation' ? 'selected' : ''}>Negotiation</option>
              <option value="won" ${lead.status === 'won' ? 'selected' : ''}>Won</option>
              <option value="lost" ${lead.status === 'lost' ? 'selected' : ''}>Lost</option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" id="btnCancelEdit">Cancel</button>
          <button class="btn-primary" id="btnSaveEdit">Update Status</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    modal.querySelector('.modal-close')?.addEventListener('click', () => modal.remove());
    modal.querySelector('#btnCancelEdit')?.addEventListener('click', () => modal.remove());
    modal.querySelector('#btnSaveEdit')?.addEventListener('click', () => this.updateLead(lead.id, modal));
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.remove();
    });
  }

  private async updateLead(leadId: number, modal: HTMLElement): Promise<void> {
    const status = (document.getElementById('editLeadStatus') as HTMLSelectElement)?.value;

    try {
      const response = await apiService.put<any>(`/crm/unified-my-leads/${leadId}/mnr-assignment?role=mnr`, {
        status
      });

      if (response.success) {
        modal.remove();
        await this.loadData();
      } else {
        alert(response.error || 'Failed to update lead');
      }
    } catch (error) {
      console.error('[MNRMyLeads] Update lead failed:', error);
      alert('Failed to update lead. Please try again.');
    }
  }

  private maskMobile(mobile: string): string {
    if (!mobile || mobile.length < 6) return mobile || 'N/A';
    return mobile.slice(0, 2) + 'XXXX' + mobile.slice(-4);
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric'
      });
    } catch {
      return dateStr;
    }
  }
}
